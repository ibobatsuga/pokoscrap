import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import httpx
from fastapi import Body, Depends, HTTPException, Request, Response
from sqlalchemy import func, select

from . import db
from .core import clean, now

PLANS = {'free': {'credits': 30, 'price': 0, 'users': 1}, 'starter': {'credits': 1000, 'price': 99000, 'users': 1}, 'pro': {'credits': 5000, 'price': 249000, 'users': 10}}
BASE_URL = os.getenv('BASE_URL', 'http://127.0.0.1:8877').rstrip('/')
api_requests = {}


def resolve_session(request):
    authorization = request.headers.get('Authorization', '')
    if authorization.startswith('Bearer '):
        key_hash = hashlib.sha256(authorization[7:].encode()).hexdigest()
        with db.transaction(unscoped=True) as conn:
            key = db.one(conn, db.api_tokens, (db.api_tokens.c.id == key_hash) & (db.api_tokens.c.active == True))
            if not key:
                return None
            user = db.one(conn, db.users, db.users.c.id == key['user_id'])
            member = db.one(conn, db.memberships, (db.memberships.c.tenant_id == key['tenant_id']) & (db.memberships.c.user_id == key['user_id']) & (db.memberships.c.active == True))
            org = db.one(conn, db.organizations, db.organizations.c.id == key['tenant_id'])
            context = db.tenant_context.set(key['tenant_id'])
            try:
                sub = db.one(conn, db.subscriptions, db.subscriptions.c.tenant_id == key['tenant_id'])
            finally:
                db.tenant_context.reset(context)
            recent = [t for t in api_requests.get(key_hash, []) if time.time()-t < 3600]
            if not user or not user['active'] or not member or not org or org['status'] == 'suspended' or not sub or sub['plan_code'] != 'pro' or len(recent) >= 600:
                return None
            api_requests[key_hash] = recent+[time.time()]
            return {'id': user['id'], 'name': user['name'], 'email': user['email'], 'roles': [r for r in member['roles'] if r in ('Operator', 'Reviewer')]+(['Operator'] if any(r in member['roles'] for r in ('Owner', 'Admin')) else []), 'active': True, 'platform_admin': False, 'tenant_id': org['id'], 'organization_name': org['name'], 'api_key': True}
    hashed = hashlib.sha256(request.cookies.get('poko_session', '').encode()).hexdigest()
    with db.transaction(unscoped=True) as conn:
        session = db.one(conn, db.sessions, db.sessions.c.id == hashed)
        if not session or session['expires'] < now():
            return None
        user = db.one(conn, db.users, db.users.c.id == session['user_id'])
        if not user or not user['active'] or not user['verified']:
            return None
        member = db.one(conn, db.memberships, (db.memberships.c.tenant_id == session['tenant_id']) & (db.memberships.c.user_id == user['id']) & (db.memberships.c.active == True)) if session['tenant_id'] else None
        if session['tenant_id'] and not member:
            return None
        cfg = db.one(conn, db.settings, (db.settings.c.tenant_id == session['tenant_id']) & (db.settings.c.id == 'main')) if member else None
        idle = (cfg or {}).get('payload', {}).get('session_idle_minutes', 60)
        if session['last_seen'] < (datetime.now(timezone.utc)-timedelta(minutes=idle)).isoformat():
            return None
        org = db.one(conn, db.organizations, db.organizations.c.id == session['tenant_id']) if member else None
        if org and org['status'] == 'suspended':
            return None
        conn.execute(db.sessions.update().where(db.sessions.c.id == hashed).values(last_seen=now()))
        return {'id': user['id'], 'name': user['name'], 'email': user['email'], 'roles': member['roles'] if member else [], 'active': True, 'platform_admin': bool(user['platform_admin']), 'tenant_id': org['id'] if org else None, 'organization_name': org['name'] if org else ''}


def balance(conn):
    return int(conn.scalar(select(func.coalesce(func.sum(db.ledger.c.amount), 0)).where(db.ledger.c.tenant_id == db.tenant_context.get())) or 0)


def subscription(conn):
    row = db.one(conn, db.subscriptions, db.subscriptions.c.tenant_id == db.tenant_context.get())
    if not row:
        raise HTTPException(409, 'Buat organisasi terlebih dahulu.')
    if row['period_end'] and row['period_end'] < now() and row['status'] == 'active':
        if row['next_plan'] == 'free':
            values = dict(plan_code='free', status='trial', period_start=now(), period_end=None, next_plan=None, grace_until=None)
        else:
            grace = (datetime.fromisoformat(row['period_end'])+timedelta(days=7)).isoformat()
            values = dict(status='past_due', grace_until=grace, next_plan=None, plan_code=row['next_plan'] or row['plan_code'])
        conn.execute(db.subscriptions.update().values(**values))
        row.update(values)
    return row


def access_period(sub):
    if sub['status'] == 'past_due' and sub['grace_until'] and sub['grace_until'] < now():
        raise HTTPException(402, 'Masa tenggang sandbox 7 hari berakhir. Periksa billing organisasi.')


def lock_tenant(conn):
    tid = db.tenant_context.get()
    if not tid:
        raise HTTPException(409, 'Pilih organisasi terlebih dahulu.')
    statement = db.organizations.select().where(db.organizations.c.id == tid)
    if db.engine.dialect.name == 'postgresql':
        statement = statement.with_for_update()
    org = conn.execute(statement).mappings().first()
    if not org or org['status'] == 'suspended':
        raise HTTPException(403, 'Organisasi tidak aktif.')
    if db.engine.dialect.name == 'sqlite':
        # Acquire SQLite's write lock before calculating the balance.
        conn.execute(db.organizations.update().where(db.organizations.c.id == tid).values(status=org['status']))


def ledger_entry(conn, kind, amount, reference, actor):
    existing = db.one(conn, db.ledger, (db.ledger.c.reference == reference) & (db.ledger.c.tenant_id == db.tenant_context.get()))
    if existing:
        return existing
    current = balance(conn)
    if current+amount < 0:
        raise HTTPException(402, {'message': 'Kredit tidak mencukupi.', 'remaining': current, 'required': -amount})
    row = dict(id=db.uid(), tenant_id=db.tenant_context.get(), type=kind, amount=amount, balance_after=current+amount, reference=reference, actor=actor, created_at=now())
    conn.execute(db.ledger.insert().values(**row))
    return row


def reserve_job(conn, job_id, requested, user):
    lock_tenant(conn)
    access_period(subscription(conn))
    try:
        amount = int(requested)
        if amount < 1:
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(422, {'max_credits': 'Isi batas kredit job minimal 1.'})
    ledger_entry(conn, 'consume', -amount, 'reserve:'+job_id+':'+db.uid(), user['name'])


def job_reservation(conn, job_id):
    return conn.execute(db.ledger.select().where(db.ledger.c.tenant_id == db.tenant_context.get(), db.ledger.c.reference.like('reserve:'+job_id+':%')).order_by(db.ledger.c.created_at.desc()).limit(1)).mappings().first()


def settle_job(conn, job_id, spent, actor):
    lock_tenant(conn)
    reserve = job_reservation(conn, job_id)
    if not reserve:
        return
    refunded = -reserve['amount']-spent
    if refunded < 0:
        raise ValueError('Hasil membutuhkan kredit melebihi reservasi; ingestion ditahan.')
    ledger_entry(conn, 'refund', refunded, 'settle:'+reserve['id'], actor)


def gate_export(conn, count, filters):
    sub = subscription(conn)
    access_period(sub)
    if sub['plan_code'] == 'free' and count > 30:
        raise HTTPException(402, {'message': 'Export Free dibatasi 30 lead.', 'required': count, 'limit': 30})
    if sub['plan_code'] == 'free' and any(filters.get(k) for k in ('destination', 'product', 'suspected')):
        raise HTTPException(403, 'Filter ekspor tersedia mulai paket Starter.')


def send_email(email, subject, body):
    message = EmailMessage()
    message['From'] = os.getenv('SMTP_FROM', 'PokoScrap <noreply@pokoscrap.example>')
    message['To'], message['Subject'] = email, subject
    message.set_content(body)
    if os.getenv('SMTP_HOST'):
        with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.getenv('SMTP_PORT', 587)), timeout=15) as smtp:
            smtp.starttls()
            if os.getenv('SMTP_USER'):
                smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
            smtp.send_message(message)
    else:
        # Development outbox, excluded from source control and publication.
        folder = db.RUNTIME / 'outbox'
        folder.mkdir(exist_ok=True, mode=0o700)
        path = folder / (db.uid()+'.eml')
        path.write_text(message.as_string())
        path.chmod(0o600)


def issue_token(conn, user_id, kind, payload=None):
    token = secrets.token_urlsafe(40)
    conn.execute(db.tokens.insert().values(id=hashlib.sha256(token.encode()).hexdigest(), user_id=user_id, type=kind, expires=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(), payload=payload or {}))
    return token


def create_org(conn, user, name):
    if not clean(name):
        raise HTTPException(422, 'Nama organisasi wajib diisi.')
    org = dict(id=db.uid(), name=clean(name), owner_id=user['id'], status='trial', created_at=now())
    # A verified user owns this newly created tenant.
    conn.execute(db.organizations.insert().values(**org))
    token = db.tenant_context.set(org['id'])
    try:
        conn.execute(db.memberships.insert().values(id=db.uid(), user_id=user['id'], roles=['Owner'], active=True, tenant_id=org['id']))
        conn.execute(db.subscriptions.insert().values(tenant_id=org['id'], plan_code='free', status='trial', period_start=now(), period_end=None))
        ledger_entry(conn, 'grant', 30, 'free-initial', 'Sistem')
    finally:
        db.tenant_context.reset(token)
    return org


def tripay_config():
    if not all(os.getenv(k) for k in ('TRIPAY_API_KEY', 'TRIPAY_PRIVATE_KEY', 'TRIPAY_MERCHANT_CODE')):
        raise HTTPException(503, 'Tripay Sandbox belum dikonfigurasi. Isi kredensial sandbox pada environment server.')
    if not BASE_URL.startswith('https://'):
        raise HTTPException(503, 'Callback Tripay memerlukan BASE_URL HTTPS yang dapat dijangkau.')
    return os.environ['TRIPAY_API_KEY'], os.environ['TRIPAY_PRIVATE_KEY'], os.environ['TRIPAY_MERCHANT_CODE']


def platform_log(conn, user, tenant, action, reason, payload=None):
    conn.execute(db.platform_audit.insert().values(id=db.uid(), actor=user['name'], tenant_id=tenant, type=action, reason=reason, created_at=now(), payload=payload or {}))


def install(app):
    from .app import admin, auth, password_hash

    def owner(user=Depends(auth)):
        if 'Owner' not in user['roles']:
            raise HTTPException(403, 'Hanya Owner dapat mengelola langganan.')
        return user

    def platform(user=Depends(auth)):
        if not user['platform_admin']:
            raise HTTPException(403, 'Akses khusus Platform Admin.')
        return user

    @app.post('/api/register')
    def register(body: dict = Body(...)):
        if not clean(body.get('name')) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', body.get('email', '')) or len(body.get('password', '')) < 12:
            raise HTTPException(422, 'Isi nama, email valid, dan kata sandi minimal 12 karakter.')
        with db.transaction(unscoped=True) as conn:
            email = body['email'].lower()
            if not db.one(conn, db.users, db.users.c.email == email):
                user_id = db.uid()
                conn.execute(db.users.insert().values(id=user_id, name=clean(body['name']), email=email, password_hash=password_hash(body['password']), roles=[], active=True, verified=False, platform_admin=False))
                token = issue_token(conn, user_id, 'verify')
                send_email(email, 'Verifikasi akun PokoScrap', BASE_URL+'/?verify='+token)
        return {'message': 'Jika email dapat digunakan, instruksi verifikasi dikirim.'}

    @app.post('/api/verify')
    def verify(body: dict = Body(...)):
        with db.transaction(unscoped=True) as conn:
            key = hashlib.sha256(str(body.get('token', '')).encode()).hexdigest()
            token = db.one(conn, db.tokens, (db.tokens.c.id == key) & (db.tokens.c.type == 'verify'))
            if not token or token['expires'] < now():
                raise HTTPException(422, 'Tautan verifikasi tidak valid atau kedaluwarsa.')
            conn.execute(db.users.update().where(db.users.c.id == token['user_id']).values(verified=True))
            conn.execute(db.tokens.delete().where(db.tokens.c.id == key))
        return {'ok': True}

    @app.post('/api/forgot')
    def forgot(body: dict = Body(...)):
        with db.transaction(unscoped=True) as conn:
            user = db.one(conn, db.users, db.users.c.email == clean(body.get('email')).lower())
            if user and user['active']:
                token = issue_token(conn, user['id'], 'reset')
                send_email(user['email'], 'Pulihkan akun PokoScrap', BASE_URL+'/?reset='+token)
        return {'ok': True}

    @app.post('/api/reset')
    def reset(body: dict = Body(...)):
        if len(body.get('password', '')) < 12:
            raise HTTPException(422, 'Kata sandi minimal 12 karakter.')
        with db.transaction(unscoped=True) as conn:
            key = hashlib.sha256(str(body.get('token', '')).encode()).hexdigest()
            token = db.one(conn, db.tokens, (db.tokens.c.id == key) & (db.tokens.c.type == 'reset'))
            if not token or token['expires'] < now():
                raise HTTPException(422, 'Tautan pemulihan tidak valid atau kedaluwarsa.')
            conn.execute(db.users.update().where(db.users.c.id == token['user_id']).values(password_hash=password_hash(body['password'])))
            conn.execute(db.sessions.delete().where(db.sessions.c.user_id == token['user_id']))
            conn.execute(db.tokens.delete().where(db.tokens.c.user_id == token['user_id'], db.tokens.c.type == 'reset'))
        return {'ok': True}

    def _login_or_register_google_user(conn, email, name, google_id, avatar_url, response):
        from .app import public_user
        email = email.lower()
        name = name or email.split('@')[0].capitalize()

        user = db.one(conn, db.users, db.users.c.email == email)
        if not user:
            user_id = db.uid()
            user = {
                'id': user_id,
                'name': name,
                'email': email,
                'password_hash': password_hash(secrets.token_urlsafe(32)),
                'roles': ['Owner'],
                'active': True,
                'verified': True,
                'platform_admin': False
            }
            user_record = {**user, 'google_id': google_id, 'avatar_url': avatar_url}
            insert_data = {k: v for k, v in user_record.items() if k in db.users.c}
            conn.execute(db.users.insert().values(**insert_data))
            org_display_name = f"Workspace {name.split()[0]}" if name else "Workspace Utama"
            org = create_org(conn, user, org_display_name)
            membership = {'tenant_id': org['id'], 'roles': ['Owner']}
        else:
            update_vals = {'verified': True, 'active': True}
            if 'google_id' in db.users.c and google_id:
                update_vals['google_id'] = google_id
            if 'avatar_url' in db.users.c and avatar_url:
                update_vals['avatar_url'] = avatar_url
            conn.execute(db.users.update().where(db.users.c.id == user['id']).values(**update_vals))
            membership = conn.execute(db.memberships.select().where(db.memberships.c.user_id == user['id'], db.memberships.c.active == True).limit(1)).mappings().first()
            if not membership:
                org = create_org(conn, user, f"Workspace {user['name'].split()[0] if user['name'] else 'Poko'}")
                membership = {'tenant_id': org['id'], 'roles': ['Owner']}
            else:
                org = db.one(conn, db.organizations, db.organizations.c.id == membership['tenant_id'])

        token = secrets.token_urlsafe(48)
        conn.execute(db.sessions.insert().values(
            id=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user['id'],
            tenant_id=membership['tenant_id'],
            last_seen=now(),
            expires=(datetime.now(timezone.utc)+timedelta(days=7)).isoformat()
        ))
        conn.execute(db.platform_audit.insert().values(
            id=db.uid(),
            actor=user['name'],
            tenant_id=membership['tenant_id'],
            type='login_google',
            reason='Login Google terverifikasi',
            created_at=now(),
            payload={'email': email, 'google_id': google_id}
        ))

        response.set_cookie('poko_session', token, httponly=True, samesite='strict', secure=os.getenv('COOKIE_SECURE') == '1', max_age=604800)
        return {
            **public_user(user),
            'roles': membership['roles'] if membership else ['Owner'],
            'tenant_id': org['id'] if org else None,
            'organization_name': org['name'] if org else ''
        }

    @app.get('/api/auth/google/url')
    def google_auth_url(request: Request):
        client_id = os.getenv('GOOGLE_CLIENT_ID', '')
        proto = request.headers.get('x-forwarded-proto', 'https')
        host = request.headers.get('x-forwarded-host') or request.headers.get('host') or ''
        base = f"{proto}://{host}" if host else BASE_URL
        redirect_uri = f"{base}/api/auth/google/callback"
        configured = bool(client_id)
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=openid%20email%20profile&access_type=offline&prompt=consent" if configured else ""
        return {
            'configured': configured,
            'client_id': client_id,
            'auth_url': auth_url,
            'redirect_uri': redirect_uri
        }

    @app.get('/api/auth/google/callback')
    async def google_auth_callback(request: Request, response: Response, code: str = '', error: str = ''):
        if error or not code:
            return Response(content="<script>alert('Login Google dibatalkan atau gagal.'); location.href='/';</script>", media_type="text/html")
        client_id = os.getenv('GOOGLE_CLIENT_ID', '')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')
        proto = request.headers.get('x-forwarded-proto', 'https')
        host = request.headers.get('x-forwarded-host') or request.headers.get('host') or ''
        base = f"{proto}://{host}" if host else BASE_URL
        redirect_uri = f"{base}/api/auth/google/callback"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                token_resp = await client.post('https://oauth2.googleapis.com/token', data={
                    'code': code,
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code'
                })
                if token_resp.status_code != 200:
                    return Response(content=f"<script>alert('Gagal pertukaran token Google: {token_resp.text}'); location.href='/';</script>", media_type="text/html")
                tokens = token_resp.json()
                userinfo_resp = await client.get('https://www.googleapis.com/oauth2/v3/userinfo', headers={
                    'Authorization': f"Bearer {tokens.get('access_token')}"
                })
                if userinfo_resp.status_code != 200:
                    return Response(content="<script>alert('Gagal mengambil data akun Google.'); location.href='/';</script>", media_type="text/html")
                profile = userinfo_resp.json()
        except Exception as e:
            return Response(content=f"<script>alert('Gangguan koneksi Google: {str(e)}'); location.href='/';</script>", media_type="text/html")

        email = profile.get('email')
        name = profile.get('name') or profile.get('given_name') or (email.split('@')[0] if email else '')
        google_id = profile.get('sub')
        avatar_url = profile.get('picture')

        from fastapi.responses import RedirectResponse
        redir = RedirectResponse(url='/', status_code=302)
        with db.transaction(unscoped=True) as conn:
            _login_or_register_google_user(conn, email, name, google_id, avatar_url, redir)
        return redir

    @app.post('/api/auth/google')
    def google_auth(request: Request, response: Response, body: dict = Body(...)):
        from .app import public_user
        email = None
        name = None
        google_id = None
        avatar_url = None

        credential = body.get('credential')
        if credential:
            try:
                parts = str(credential).split('.')
                if len(parts) >= 2:
                    import base64
                    payload_b64 = parts[1]
                    payload_b64 += '=' * ((4 - len(payload_b64) % 4) % 4)
                    data = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
                    email = data.get('email')
                    name = data.get('name') or data.get('given_name') or (email.split('@')[0] if email else '')
                    google_id = data.get('sub')
                    avatar_url = data.get('picture')
            except Exception:
                pass

        if not email:
            email = clean(body.get('email'))
            name = clean(body.get('name'))
            google_id = body.get('google_id') or body.get('sub')
            avatar_url = body.get('avatar_url') or body.get('picture')

        if not email or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise HTTPException(422, 'Email Google valid diperlukan.')

        with db.transaction(unscoped=True) as conn:
            return _login_or_register_google_user(conn, email, name, google_id, avatar_url, response)


    @app.post('/api/billing/sandbox-upgrade')
    def sandbox_upgrade(body: dict = Body(...), user=Depends(owner)):
        plan = body.get('plan', 'pro')
        if plan not in ('free', 'starter', 'pro'):
            raise HTTPException(422, 'Paket tidak valid.')
        with db.transaction() as conn:
            conn.execute(db.subscriptions.update().where(db.subscriptions.c.tenant_id == user['tenant_id']).values(plan_code=plan, status='active'))
            if plan == 'pro':
                ledger_entry(conn, 'grant', 5000, f'sandbox-{plan}-upgrade', 'Sandbox Admin')
            elif plan == 'starter':
                ledger_entry(conn, 'grant', 1000, f'sandbox-{plan}-upgrade', 'Sandbox Admin')
        return {'ok': True, 'plan': plan}

    @app.get('/api/orgs')
    def orgs(user=Depends(auth)):
        with db.transaction(unscoped=True) as conn:
            memberships = db.rows(conn, db.memberships.select().where(db.memberships.c.user_id == user['id'], db.memberships.c.active == True))
            return [db.one(conn, db.organizations, db.organizations.c.id == m['tenant_id']) for m in memberships]

    @app.post('/api/orgs')
    def new_org(request: Request, body: dict = Body(...), user=Depends(auth)):
        with db.transaction(unscoped=True) as conn:
            org = create_org(conn, user, body.get('name'))
            hashed = hashlib.sha256(request.cookies.get('poko_session', '').encode()).hexdigest()
            conn.execute(db.sessions.update().where(db.sessions.c.id == hashed).values(tenant_id=org['id']))
        return org

    @app.post('/api/orgs/{org_id}/select')
    def select_org(org_id: str, request: Request, user=Depends(auth)):
        with db.transaction(unscoped=True) as conn:
            member = db.one(conn, db.memberships, (db.memberships.c.tenant_id == org_id) & (db.memberships.c.user_id == user['id']) & (db.memberships.c.active == True))
            org = db.one(conn, db.organizations, db.organizations.c.id == org_id)
            if not member or not org or org['status'] == 'suspended':
                raise HTTPException(404, 'Organisasi tidak tersedia.')
            conn.execute(db.sessions.update().where(db.sessions.c.id == hashlib.sha256(request.cookies.get('poko_session', '').encode()).hexdigest()).values(tenant_id=org_id))
        return {'ok': True}

    @app.post('/api/orgs/invite')
    def invite(body: dict = Body(...), user=Depends(admin)):
        email, member_role = clean(body.get('email')).lower(), body.get('role')
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or member_role not in ('Admin', 'Operator', 'Reviewer'):
            raise HTTPException(422, 'Email dan peran undangan tidak valid.')
        with db.transaction() as conn:
            if subscription(conn)['plan_code'] != 'pro':
                raise HTTPException(403, 'Multi-pengguna tersedia pada paket Pro.')
            count = conn.scalar(select(func.count()).select_from(db.memberships).where(db.memberships.c.active == True))
            if count >= PLANS['pro']['users']:
                raise HTTPException(422, 'Batas anggota paket tercapai.')
            token = secrets.token_urlsafe(40)
            conn.execute(db.invitations.insert().values(id=hashlib.sha256(token.encode()).hexdigest(), email=email, role=member_role, accepted=False, expires=(datetime.now(timezone.utc)+timedelta(days=3)).isoformat()))
            send_email(email, 'Undangan organisasi PokoScrap', BASE_URL+'/?invite='+token)
        return {'ok': True}

    @app.post('/api/orgs/invite/accept')
    def accept_invite(body: dict = Body(...), user=Depends(auth)):
        key = hashlib.sha256(str(body.get('token', '')).encode()).hexdigest()
        with db.transaction(unscoped=True) as conn:
            invitation = db.one(conn, db.invitations, db.invitations.c.id == key)
            if not invitation or invitation['accepted'] or invitation['email'] != user['email'] or invitation['expires'] < now():
                raise HTTPException(422, 'Undangan tidak valid atau kedaluwarsa.')
            member = db.one(conn, db.memberships, (db.memberships.c.user_id == user['id']) & (db.memberships.c.tenant_id == invitation['tenant_id']))
            sub = db.one(conn, db.subscriptions, db.subscriptions.c.tenant_id == invitation['tenant_id'])
            count = conn.scalar(select(func.count()).select_from(db.memberships).where(db.memberships.c.tenant_id == invitation['tenant_id'], db.memberships.c.active == True))
            if sub['plan_code'] != 'pro' or count >= PLANS['pro']['users']:
                raise HTTPException(403, 'Paket atau batas anggota tidak mengizinkan undangan.')
            if member:
                conn.execute(db.memberships.update().where(db.memberships.c.id == member['id']).values(active=True, roles=[invitation['role']]))
            else:
                conn.execute(db.memberships.insert().values(id=db.uid(), tenant_id=invitation['tenant_id'], user_id=user['id'], roles=[invitation['role']], active=True))
            conn.execute(db.invitations.update().where(db.invitations.c.id == key).values(accepted=True))
        return {'ok': True, 'tenant_id': invitation['tenant_id']}

    @app.get('/api/credits/balance')
    def credit_balance(user=Depends(auth)):
        with db.transaction() as conn:
            sub = subscription(conn)
            return {'balance': balance(conn), 'plan': sub['plan_code'].title()}

    @app.get('/api/credits/ledger')
    def credit_ledger(user=Depends(auth)):
        with db.transaction() as conn:
            return {'balance': balance(conn), 'ledger': db.rows(conn, db.ledger.select().order_by(db.ledger.c.created_at.desc()))}

    @app.get('/api/api-keys')
    def list_keys(user=Depends(admin)):
        with db.transaction() as conn:
            result = db.rows(conn, db.api_tokens.select().where(db.api_tokens.c.tenant_id == user['tenant_id'], db.api_tokens.c.active == True))
            return [{k: r[k] for k in ('name', 'prefix', 'created_at')} for r in result]

    @app.post('/api/api-keys')
    def new_key(body: dict = Body(...), user=Depends(admin)):
        with db.transaction() as conn:
            sub = subscription(conn)
            access_period(sub)
            if sub['plan_code'] != 'pro' or not clean(body.get('name')):
                raise HTTPException(403, 'Nama key dan paket Pro diperlukan.')
            key = 'psk_'+secrets.token_urlsafe(36)
            conn.execute(db.api_tokens.insert().values(id=hashlib.sha256(key.encode()).hexdigest(), tenant_id=user['tenant_id'], user_id=user['id'], name=clean(body['name']), prefix=key[:12], active=True, created_at=now()))
        return {'key': key, 'prefix': key[:12], 'requests_per_hour': 600}

    @app.post('/api/api-keys/revoke')
    def revoke_key(body: dict = Body(...), user=Depends(admin)):
        with db.transaction() as conn:
            conn.execute(db.api_tokens.update().where(db.api_tokens.c.tenant_id == user['tenant_id'], db.api_tokens.c.prefix == body.get('prefix')).values(active=False))
        return {'ok': True}

    @app.get('/api/billing/subscription')
    def billing(user=Depends(auth)):
        with db.transaction() as conn:
            sub = subscription(conn)
            tx = db.rows(conn, db.payments.select().order_by(db.payments.c.created_at.desc()))
            return {**sub, 'payments': [{k: p[k] for k in ('id', 'plan_code', 'amount', 'status', 'created_at', 'checkout_url')} for p in tx], 'sandbox': True, 'prices_provisional': True}

    @app.get('/api/billing/channels')
    def channels(user=Depends(owner)):
        key, _, _ = tripay_config()
        try:
            response = httpx.get('https://tripay.co.id/api-sandbox/merchant/payment-channel', headers={'Authorization': 'Bearer '+key}, timeout=20)
            result = response.json()
            if not response.is_success or not result.get('success'):
                raise ValueError()
            return [{'code': c['code'], 'name': c['name']} for c in result['data'] if c.get('active')]
        except (httpx.HTTPError, ValueError, KeyError):
            raise HTTPException(502, 'Channel Tripay Sandbox belum dapat dimuat.')

    @app.post('/api/billing/checkout')
    def checkout(body: dict = Body(...), user=Depends(owner)):
        if os.getenv('BILLING_BETA_ENABLED') != '1':
            raise HTTPException(503, 'Checkout sandbox belum diaktifkan. Tetapkan aturan beta dan konfigurasi merchant dahulu.')
        plan = body.get('plan')
        if plan not in ('starter', 'pro') or not clean(body.get('method')):
            raise HTTPException(422, 'Paket dan channel pembayaran wajib dipilih.')
        key, private_key, merchant = tripay_config()
        available = channels(user)
        if body['method'] not in [c['code'] for c in available]:
            raise HTTPException(422, 'Channel tidak aktif pada merchant sandbox.')
        invoice, amount = db.uid(), PLANS[plan]['price']
        signature = hmac.new(private_key.encode(), (merchant+invoice+str(amount)).encode(), hashlib.sha256).hexdigest()
        payload = {'method': body['method'], 'merchant_ref': invoice, 'amount': amount, 'customer_name': user['name'], 'customer_email': user['email'], 'order_items[0][sku]': plan, 'order_items[0][name]': 'PokoScrap '+plan+' — sandbox beta', 'order_items[0][price]': amount, 'order_items[0][quantity]': 1, 'return_url': BASE_URL+'/#/billing', 'callback_url': BASE_URL+'/api/billing/webhook', 'expired_time': int(time.time())+3600, 'signature': signature}
        with db.transaction() as conn:
            conn.execute(db.payments.insert().values(id=invoice, plan_code=plan, amount=amount, status='CREATING', created_at=now(), payload={}))
            conn.execute(db.payment_index.insert().values(id=invoice, tenant_id=db.tenant_context.get()))
        try:
            response = httpx.post('https://tripay.co.id/api-sandbox/transaction/create', data=payload, headers={'Authorization': 'Bearer '+key}, timeout=25)
            result = response.json()
            if not response.is_success or not result.get('success'):
                raise ValueError()
            tx = result['data']
            checkout_url = tx['checkout_url']
            if not checkout_url.startswith('https://tripay.co.id/'):
                raise ValueError()
            with db.transaction() as conn:
                conn.execute(db.payments.update().where(db.payments.c.id == invoice).values(status='UNPAID', reference=tx['reference'], checkout_url=checkout_url, payload={'gateway': tx}))
            return {'id': invoice, 'checkout_url': checkout_url}
        except (httpx.HTTPError, ValueError, KeyError):
            with db.transaction() as conn:
                conn.execute(db.payments.update().where(db.payments.c.id == invoice).values(status='UNKNOWN'))
            raise HTTPException(502, 'Status invoice sandbox belum diketahui. Periksa merchant sebelum mencoba lagi.')

    @app.post('/api/billing/webhook')
    async def webhook(request: Request):
        raw = await request.body()
        if len(raw) > 100000:
            raise HTTPException(413, 'Payload terlalu besar.')
        private_key = os.getenv('TRIPAY_PRIVATE_KEY', '')
        expected = hmac.new(private_key.encode(), raw, hashlib.sha256).hexdigest()
        if not private_key or not hmac.compare_digest(expected, request.headers.get('X-Callback-Signature', '')) or request.headers.get('X-Callback-Event') != 'payment_status':
            raise HTTPException(401, 'Signature webhook tidak valid.')
        try:
            payload = json.loads(raw)
        except ValueError:
            raise HTTPException(422, 'JSON webhook tidak valid.')
        with db.transaction(unscoped=True) as conn:
            invoice = db.one(conn, db.payment_index, db.payment_index.c.id == payload.get('merchant_ref'))
        if not invoice:
            raise HTTPException(404, 'Invoice tidak ditemukan.')
        token = db.tenant_context.set(invoice['tenant_id'])
        try:
            with db.transaction() as conn:
                lock_tenant(conn)
                tx = db.one(conn, db.payments, db.payments.c.id == invoice['id'])
                if tx['reference'] != payload.get('reference') or tx['amount'] != payload.get('amount') or payload.get('status') not in ('PAID', 'UNPAID', 'EXPIRED', 'FAILED', 'REFUND'):
                    raise HTTPException(422, 'Referensi, nominal, atau status webhook tidak cocok.')
                archive = {**tx['payload'], 'webhook': payload}
                if tx['status'] == 'PAID':
                    return {'success': True}
                conn.execute(db.payments.update().where(db.payments.c.id == tx['id']).values(status=payload['status'], payload=archive))
                if payload['status'] == 'PAID':
                    sub = subscription(conn)
                    current = datetime.now(timezone.utc)
                    if sub['plan_code'] == tx['plan_code'] and sub['period_end'] and sub['period_end'] > now():
                        current = datetime.fromisoformat(sub['period_end'])
                    conn.execute(db.subscriptions.update().values(plan_code=tx['plan_code'], status='active', period_start=now(), period_end=(current+timedelta(days=30)).isoformat(), next_plan=None, grace_until=None))
                    ledger_entry(conn, 'grant', PLANS[tx['plan_code']]['credits'], 'payment:'+tx['id'], 'Tripay Sandbox')
                    conn.execute(db.organizations.update().where(db.organizations.c.id == tx['tenant_id']).values(status='active'))
        finally:
            db.tenant_context.reset(token)
        return {'success': True}

    @app.post('/api/billing/downgrade')
    def downgrade(body: dict = Body(...), user=Depends(owner)):
        if body.get('plan') not in ('free', 'starter'):
            raise HTTPException(422, 'Paket tujuan tidak valid.')
        with db.transaction() as conn:
            sub = subscription(conn)
            if PLANS[body['plan']]['credits'] >= PLANS[sub['plan_code']]['credits']:
                raise HTTPException(422, 'Paket tujuan bukan downgrade.')
            conn.execute(db.subscriptions.update().values(next_plan=body['plan']))
        return {'ok': True}

    @app.get('/api/admin/tenants')
    def tenants(q: str = '', user=Depends(platform)):
        with db.transaction(unscoped=True) as conn:
            if db.engine.dialect.name == 'postgresql':
                result = [dict(r) for r in conn.conn.exec_driver_sql('SELECT * FROM platform_tenant_summary(%s)', (q,)).mappings()]
                platform_log(conn, user, None, 'tenant_list_viewed', 'Daftar ringkasan tenant')
                return {'total': len(result), 'page': 1, 'page_size': len(result), 'data': result}
            result = []
            for org in db.rows(conn, db.organizations.select().where(db.organizations.c.name.ilike('%'+q+'%'))):
                sub = db.one(conn, db.subscriptions, db.subscriptions.c.tenant_id == org['id'])
                value = conn.scalar(select(func.coalesce(func.sum(db.ledger.c.amount), 0)).where(db.ledger.c.tenant_id == org['id']))
                result.append({**org, 'plan_code': sub['plan_code'], 'balance': value})
            platform_log(conn, user, None, 'tenant_list_viewed', 'Daftar ringkasan tenant')
        return {'total': len(result), 'page': 1, 'page_size': len(result), 'data': result}

    @app.post('/api/admin/tenants/{tenant_id}/credits')
    def adjust(tenant_id: str, body: dict = Body(...), user=Depends(platform)):
        if not clean(body.get('reason')) or not isinstance(body.get('amount'), int) or body['amount'] == 0:
            raise HTTPException(422, 'Jumlah nonnol dan alasan wajib diisi.')
        token = db.tenant_context.set(tenant_id)
        try:
            with db.transaction() as conn:
                lock_tenant(conn)
                row = ledger_entry(conn, 'adjustment', body['amount'], 'admin:'+db.uid(), user['name'])
                platform_log(conn, user, tenant_id, 'credit_adjustment', body['reason'], {'amount': body['amount']})
                return row
        finally:
            db.tenant_context.reset(token)

    @app.post('/api/admin/tenants/{tenant_id}/status')
    def status(tenant_id: str, body: dict = Body(...), user=Depends(platform)):
        if not clean(body.get('reason')) or body.get('status') not in ('active', 'suspended'):
            raise HTTPException(422, 'Status dan alasan wajib diisi.')
        with db.transaction(unscoped=True) as conn:
            if not db.one(conn, db.organizations, db.organizations.c.id == tenant_id):
                raise HTTPException(404, 'Tenant tidak ditemukan.')
            conn.execute(db.organizations.update().where(db.organizations.c.id == tenant_id).values(status=body['status']))
            platform_log(conn, user, tenant_id, 'tenant_status', body['reason'], {'status': body['status']})
        return {'ok': True}

    @app.get('/api/admin/audit')
    def platform_audit(user=Depends(platform)):
        with db.transaction(unscoped=True) as conn:
            return db.rows(conn, db.platform_audit.select().order_by(db.platform_audit.c.created_at.desc()).limit(200))

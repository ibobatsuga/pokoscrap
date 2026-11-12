import csv
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from fastapi import Body, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, func, or_, select

from . import db
from .core import CONSENTS, COUNTRIES, CSV_FIELDS, GOSOM_HEADERS, PIPELINES, ROOT, clean, csv_export, fetch_public, fingerprint, map_row, normalized, now, origin, phone, read_rows, website

app = FastAPI(title='PokoScrap API', docs_url=None, redoc_url=None, openapi_url=None)
workers = {}
worker_lock = threading.Lock()
login_attempts = {}
DEFAULT_SETTINGS = {'engine_mode': 'quick', 'concurrency': 1, 'depth': 1, 'enrichment_pages': 10, 'session_idle_minutes': 60}


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ':' + hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()


def public_user(user):
    return {k: user.get(k) for k in ('id', 'name', 'email', 'roles', 'active', 'platform_admin', 'tenant_id', 'organization_name')}


def log(conn, actor, kind, payload=None, lead_id=None):
    if lead_id:
        conn.execute(db.activities.insert().values(id=db.uid(), lead_id=lead_id, actor=actor, type=kind, created_at=now(), payload=payload or {}))
    conn.execute(db.audit.insert().values(id=db.uid(), actor=actor, type=kind, created_at=now(), payload=payload or {}))


def config(conn):
    row = db.one(conn, db.settings, db.settings.c.id == 'main')
    return {**DEFAULT_SETTINGS, **(row['payload'] if row else {})}


def auth(request: Request):
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(401, 'Sesi berakhir. Silakan masuk kembali.')
    return user


def role(*allowed):
    def dependency(user=Depends(auth)):
        if not set(user['roles']).intersection(set(allowed) | ({'Owner'} if 'Admin' in allowed else set())):
            raise HTTPException(403, 'Peran Anda tidak memiliki akses tindakan ini.')
        return user
    return dependency


operator = role('Admin', 'Operator')
reviewer = role('Admin', 'Reviewer')
admin = role('Admin')


@app.middleware('http')
async def security(request, call_next):
    from .saas import resolve_session
    token = db.tenant_context.set(None)
    try:
        request.state.user = resolve_session(request)
        if request.state.user:
            db.tenant_context.set(request.state.user.get('tenant_id'))
        webhook = request.url.path == '/api/billing/webhook'
        is_bearer = request.headers.get('Authorization', '').startswith('Bearer ')
        is_mcp = request.url.path.startswith('/api/mcp')
        is_google_auth = request.url.path.startswith('/api/auth/google')
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.url.path.startswith('/api/') and not webhook and not is_bearer and not is_mcp and not is_google_auth:
            if request.headers.get('X-Poko-Request') != '1':
                return JSONResponse({'detail': 'Permintaan tidak valid.'}, status_code=403)
            referer = request.headers.get('origin')
            if referer and urlsplit(referer).netloc != request.headers.get('host'):
                return JSONResponse({'detail': 'Origin tidak diizinkan.'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        if response.status_code in (403, 404) and request.state.user:
            with db.transaction(unscoped=True) as conn:
                conn.execute(db.platform_audit.insert().values(id=db.uid(), actor=request.state.user['name'], tenant_id=request.state.user.get('tenant_id'), type='access_denied', reason='Permintaan ditolak', created_at=now(), payload={'path': request.url.path, 'status': response.status_code}))
        return response
    finally:
        db.tenant_context.reset(token)


@app.get('/api/health')
def health():
    return {'status': 'ok', 'demo': False}


@app.post('/api/login')
def login(request: Request, response: Response, body: dict = Body(...)):
    key = request.client.host
    attempts = [t for t in login_attempts.get(key, []) if time.time()-t < 900]
    if len(attempts) >= 10:
        raise HTTPException(429, 'Terlalu banyak percobaan. Coba lagi dalam 15 menit.')
    login_attempts[key] = attempts + [time.time()]
    with db.transaction(unscoped=True) as conn:
        user = db.one(conn, db.users, db.users.c.email == clean(body.get('email')).lower())
        stored = user['password_hash'] if user else password_hash('unavailable', 'dummy')
        valid = hmac.compare_digest(password_hash(str(body.get('password', '')), stored.split(':')[0]), stored)
        if not user or not user['active'] or not user['verified'] or not valid:
            raise HTTPException(401, 'Email atau kata sandi tidak valid, atau email belum diverifikasi.')
        membership = conn.execute(db.memberships.select().where(db.memberships.c.user_id == user['id'], db.memberships.c.active == True).limit(1)).mappings().first()
        token = secrets.token_urlsafe(48)
        conn.execute(db.sessions.insert().values(id=hashlib.sha256(token.encode()).hexdigest(), user_id=user['id'], tenant_id=membership['tenant_id'] if membership else None, last_seen=now(), expires=(datetime.now(timezone.utc)+timedelta(days=7)).isoformat()))
        conn.execute(db.platform_audit.insert().values(id=db.uid(), actor=user['name'], tenant_id=membership['tenant_id'] if membership else None, type='login', reason='Login terverifikasi', created_at=now(), payload={}))
        login_attempts.pop(key, None)
        response.set_cookie('poko_session', token, httponly=True, samesite='strict', secure=os.getenv('COOKIE_SECURE') == '1', max_age=604800)
        org = db.one(conn, db.organizations, db.organizations.c.id == membership['tenant_id']) if membership else None
        return {**public_user(user), 'roles': membership['roles'] if membership else [], 'tenant_id': org['id'] if org else None, 'organization_name': org['name'] if org else ''}


@app.get('/api/me')
def me(user=Depends(auth)):
    return user


@app.post('/api/logout')
def logout(request: Request, response: Response, user=Depends(auth)):
    with db.transaction() as conn:
        conn.execute(db.sessions.delete().where(db.sessions.c.id == hashlib.sha256(request.cookies.get('poko_session', '').encode()).hexdigest()))
    response.delete_cookie('poko_session')
    return {'ok': True}


@app.get('/api/countries')
def countries(user=Depends(auth)):
    return COUNTRIES


@app.get('/api/mcp')
def mcp_info(request: Request):
    from . import mcp
    user = getattr(request.state, 'user', None)
    return {
        'status': 'ok',
        'server': 'pokoscrap-mcp',
        'version': '1.0.0',
        'protocolVersion': '2024-11-05',
        'transport': 'http-jsonrpc',
        'authenticated': bool(user),
        'tools_count': len(mcp.MCP_TOOLS)
    }


@app.post('/api/mcp')
async def mcp_endpoint(request: Request):
    from . import mcp
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(401, 'Autentikasi Bearer token API key atau sesi pengguna diperlukan untuk MCP.')
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Invalid JSON format'}}, status_code=400)
    response = mcp.handle_mcp_message(body, user)
    return JSONResponse(response)


def job_public(row):
    return {**row['payload'], **{k: row[k] for k in ('id', 'name', 'status', 'created_at', 'created_by', 'archived')}}


def get_job(conn, job_id):
    row = db.one(conn, db.jobs, db.jobs.c.id == job_id)
    if not row:
        raise HTTPException(404, 'Job tidak ditemukan.')
    return row


def save_job(conn, job_id, **values):
    row = get_job(conn, job_id)
    status = values.pop('status', row['status'])
    conn.execute(db.jobs.update().where(db.jobs.c.id == job_id).values(status=status, payload={**row['payload'], **values}))


def validate_job(body):
    queries = body.get('queries', '')
    if isinstance(queries, str):
        queries = queries.splitlines()
    queries = list(dict.fromkeys(clean(q) for q in queries if clean(q)))
    errors = {}
    if not clean(body.get('name')):
        errors['name'] = 'Nama job wajib diisi.'
    if not queries or len(queries) > 100:
        errors['queries'] = 'Isi 1–100 kata kunci unik.'
    if any(len(q) > 300 or '\x00' in q for q in queries):
        errors['queries'] = 'Kata kunci maksimal 300 karakter.'
    mode = body.get('geo_mode', 'point')
    try:
        if mode == 'grid':
            bbox = [float(x) for x in str(body.get('grid_bbox', '')).split(',')]
            if len(bbox) != 4 or not (-90 <= bbox[0] < bbox[2] <= 90 and -180 <= bbox[1] < bbox[3] <= 180) or (bbox[2]-bbox[0])*(bbox[3]-bbox[1]) > 4:
                raise ValueError()
            body['grid_bbox'] = ','.join(str(v) for v in bbox)
        elif mode == 'point':
            body['latitude'], body['longitude'], body['radius_m'] = float(body['latitude']), float(body['longitude']), int(body['radius_m'])
            if not (-90 <= body['latitude'] <= 90 and -180 <= body['longitude'] <= 180 and 100 <= body['radius_m'] <= 50000):
                raise ValueError()
        else:
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        errors['area'] = 'Area tidak valid. Gunakan koordinat + radius atau kotak grid maksimal 4 derajat persegi.'
    if not re.fullmatch(r'[a-z]{2}(?:-[A-Z]{2})?', body.get('lang', 'id')):
        errors['lang'] = 'Kode bahasa tidak valid.'
    if errors:
        raise HTTPException(422, errors)
    allowed = ['geo_mode', 'latitude', 'longitude', 'radius_m', 'grid_bbox', 'lang', 'email_enabled', 'area_name', 'max_credits']
    return {k: body[k] for k in allowed if k in body} | {'queries': queries, 'lang': body.get('lang', 'id'), 'email_enabled': body.get('email_enabled', True), 'geo_mode': mode, 'found_count': 0, 'inserted_count': 0, 'duplicate_count': 0, 'error_count': 0, 'hit_result_cap': False, 'log_text': '', 'row_errors': []}


@app.post('/api/jobs')
def create_job(body: dict = Body(...), user=Depends(operator)):
    payload = validate_job(body)
    row = {'id': db.uid(), 'name': clean(body['name']), 'status': 'draft', 'created_by': user['name'], 'created_at': now(), 'archived': False, 'payload': payload}
    with db.transaction() as conn:
        from .saas import reserve_job
        if body.get('start', True):
            reserve_job(conn, row['id'], body.get('max_credits'), user)
        conn.execute(db.jobs.insert().values(**row))
        log(conn, user['name'], 'job_created', {'id': row['id']})
    if body.get('start', True):
        with db.transaction() as conn:
            save_job(conn, row['id'], status='queued')
    with db.transaction() as conn:
        return job_public(get_job(conn, row['id']))


@app.get('/api/jobs')
def list_jobs(status: str = '', user=Depends(auth)):
    with db.transaction() as conn:
        query = db.jobs.select().where(db.jobs.c.archived == False).order_by(db.jobs.c.created_at.desc())
        if status:
            query = query.where(db.jobs.c.status == status)
        data = [job_public(r) for r in db.rows(conn, query)]
        if 'Admin' not in user['roles']:
            for item in data:
                item.pop('log_text', None)
        return {'data': data, 'total': len(data), 'page': 1, 'page_size': len(data)}


@app.get('/api/jobs/{job_id}')
def job_detail(job_id: str, user=Depends(auth)):
    with db.transaction() as conn:
        job = job_public(get_job(conn, job_id))
        lead_rows = db.rows(conn, select(db.leads.c.payload).where(db.leads.c.id.in_(select(db.seen.c.lead_id).where(db.seen.c.job_id == job_id))))
        count = len(lead_rows)
        job['completeness'] = {key: {'count': sum(bool(r['payload'].get('has_'+key)) for r in lead_rows), 'total': count} for key in ('phone', 'whatsapp', 'email')}
        if 'Admin' not in user['roles']:
            job.pop('log_text', None)
        return job


@app.post('/api/jobs/{job_id}/start')
def start_job(job_id: str, user=Depends(operator)):
    with db.transaction() as conn:
        job = get_job(conn, job_id)
        if job['status'] not in ('draft', 'failed', 'stopped'):
            raise HTTPException(409, 'Job sedang berjalan atau sudah selesai.')
        from .saas import reserve_job
        reserve_job(conn, job_id, job['payload'].get('max_credits'), user)
        save_job(conn, job_id, status='queued', error='', finished_at=None, spent_credits=0)
    return {'ok': True}


@app.patch('/api/jobs/{job_id}')
def edit_job(job_id: str, body: dict = Body(...), user=Depends(operator)):
    fields = {'name', 'queries', 'geo_mode', 'latitude', 'longitude', 'radius_m', 'grid_bbox', 'lang', 'email_enabled', 'area_name', 'max_credits'}
    if set(body) - fields:
        raise HTTPException(422, 'Field job tidak diizinkan.')
    with db.transaction() as conn:
        row = get_job(conn, job_id)
        if row['status'] != 'draft':
            raise HTTPException(409, 'Hanya draft dapat diedit. Duplikasi job lain untuk mengubahnya.')
        merged = {**job_public(row), **body}
        validated = validate_job(merged)
        conn.execute(db.jobs.update().where(db.jobs.c.id == job_id).values(name=clean(merged['name']), payload=validated))
        log(conn, user['name'], 'job_updated', {'id': job_id})
        return job_public(get_job(conn, job_id))


@app.post('/api/jobs/{job_id}/stop')
def stop_job(job_id: str, user=Depends(operator)):
    with db.transaction() as conn:
        job = get_job(conn, job_id)
        if job['status'] not in ('queued', 'running', 'ingesting'):
            raise HTTPException(409, 'Job tidak sedang berjalan.')
        from .saas import settle_job
        if job['status'] == 'queued':
            settle_job(conn, job_id, 0, user['name'])
        save_job(conn, job_id, status='stopped', finished_at=now())
        log(conn, user['name'], 'job_stopped', {'id': job_id})
    proc = workers.get(job_id)
    if proc:
        subprocess.run(['docker', 'stop', '-t', '10', 'pokoscrap-'+job_id], capture_output=True, timeout=20)
    return {'ok': True}


@app.post('/api/jobs/{job_id}/duplicate')
def duplicate_job(job_id: str, user=Depends(operator)):
    with db.transaction() as conn:
        old = job_public(get_job(conn, job_id))
    return create_job({**old, 'name': old['name']+' (salinan)', 'start': False}, user)


@app.post('/api/jobs/{job_id}/archive')
def archive_job(job_id: str, user=Depends(operator)):
    with db.transaction() as conn:
        row = get_job(conn, job_id)
        if row['status'] in ('running', 'queued', 'ingesting'):
            raise HTTPException(409, 'Hentikan job sebelum mengarsipkan.')
        conn.execute(db.jobs.update().where(db.jobs.c.id == job_id).values(archived=True))
    return {'ok': True}


@app.get('/api/jobs/{job_id}/raw')
def raw_file(job_id: str, user=Depends(admin)):
    with db.transaction() as conn:
        get_job(conn, job_id)
    path = db.RUNTIME / 'jobs' / job_id / 'results.csv'
    if not path.exists():
        raise HTTPException(404, 'Arsip belum tersedia.')
    return FileResponse(path, filename='gosom-'+job_id+'.csv')


def lead_public(conn, row, full=False):
    result = {**row['payload'], 'id': row['id'], 'first_job_id': row['first_job_id']}
    ev = db.rows(conn, db.evidence.select().where(db.evidence.c.lead_id == row['id']))
    result['evidence'] = [{**e['payload'], **{k: e[k] for k in ('id', 'lead_id', 'kind', 'value', 'status')}} for e in ev]
    for kind, key in [('country', 'export_countries'), ('product', 'export_products')]:
        result[key] = [e['value'] for e in ev if e['kind'] == kind and e['status'] == 'confirmed']
    if full:
        result['activities'] = db.rows(conn, db.activities.select().where(db.activities.c.lead_id == row['id']).order_by(db.activities.c.created_at.desc()))
        result['enrichment_tasks'] = db.rows(conn, db.tasks.select().where(db.tasks.c.lead_id == row['id']))
    return result


def get_lead(conn, lead_id):
    row = db.one(conn, db.leads, db.leads.c.id == lead_id)
    if not row:
        raise HTTPException(404, 'Lead tidak ditemukan.')
    return row


def save_lead(conn, row, payload):
    conn.execute(db.leads.update().where(db.leads.c.id == row['id']).values(payload=payload, country_origin_code=payload.get('country_origin_code', ''), pipeline_status=payload['pipeline_status'], business_name=payload['business_name']))


def lead_query(filters):
    query = db.leads.select().where(db.leads.c.tenant_id == db.tenant_context.get())
    p = db.leads.c.payload
    if not filters.get('pipeline_status'):
        query = query.where(db.leads.c.pipeline_status != 'Tolak')
    statuses = ['confirmed', 'suspected'] if str(filters.get('suspected')).lower() in ('true', '1') else ['confirmed']
    for key in ('origin', 'destination', 'product'):
        values = filters.get(key, [])
        values = values.split(',') if isinstance(values, str) else values
        if not values:
            continue
        if key == 'origin':
            query = query.where(db.leads.c.country_origin_code.in_(values))
        else:
            kind = 'country' if key == 'destination' else 'product'
            groups = [[v] for v in values] if key == 'destination' and filters.get('destination_all') in (True, 'true', '1') else [values]
            for group in groups:
                query = query.where(db.leads.c.id.in_(select(db.evidence.c.lead_id).where(db.evidence.c.tenant_id == db.tenant_context.get(), db.evidence.c.kind == kind, db.evidence.c.status.in_(statuses), db.evidence.c.value.in_(group))))
    search = clean(filters.get('q'))
    if search:
        pattern = '%'+search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')+'%'
        query = query.where(or_(db.leads.c.business_name.ilike(pattern, escape='\\'), p['address'].as_string().ilike(pattern, escape='\\'), db.leads.c.id.in_(select(db.evidence.c.lead_id).where(db.evidence.c.tenant_id == db.tenant_context.get(), db.evidence.c.kind == 'product', db.evidence.c.value.ilike(pattern, escape='\\')))))
    for key in ('category', 'city', 'province', 'whatsapp_status', 'pipeline_status', 'consent_basis'):
        if filters.get(key):
            query = query.where(p[key].as_string() == filters[key])
    if filters.get('job'):
        query = query.where(db.leads.c.id.in_(select(db.seen.c.lead_id).where(db.seen.c.tenant_id == db.tenant_context.get(), db.seen.c.job_id == filters['job'])))
    for key in ('has_phone', 'has_whatsapp', 'has_email'):
        if filters.get(key) not in (None, ''):
            query = query.where(p[key].as_boolean() == (str(filters[key]).lower() in ('true', '1')))
    if filters.get('has_website') not in (None, ''):
        query = query.where((p['website_url'].as_string() != '') if str(filters['has_website']).lower() in ('true', '1') else (p['website_url'].as_string() == ''))
    for key, field in [('rating_min', 'rating'), ('review_min', 'review_count')]:
        if filters.get(key) not in (None, ''):
            try:
                query = query.where(p[field].as_float() >= float(filters[key]))
            except ValueError:
                raise HTTPException(422, {key: 'Isi angka yang valid.'})
    for key, op in [('date_from', 'after'), ('date_to', 'before')]:
        if filters.get(key):
            value = filters[key]
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise HTTPException(422, {key: 'Format tanggal YYYY-MM-DD.'})
            query = query.where(db.leads.c.first_seen_at >= value if op == 'after' else db.leads.c.first_seen_at <= value+'T23:59:59.999999+00:00')
    sort = {'rating': p['rating'].as_float(), 'reviews': p['review_count'].as_integer(), 'newest': db.leads.c.first_seen_at}.get(filters.get('sort'), db.leads.c.first_seen_at)
    return query.order_by(sort.desc().nulls_last(), db.leads.c.id)


@app.get('/api/leads')
def list_leads(request: Request, user=Depends(auth)):
    filters = dict(request.query_params)
    with db.transaction() as conn:
        from .saas import gate_export
        gate_export(conn, 0, filters)
    try:
        page, size = max(1, int(filters.get('page', 1))), int(filters.get('page_size', 25))
        if size not in (25, 50, 100):
            raise ValueError()
    except ValueError:
        raise HTTPException(422, 'Ukuran halaman harus 25, 50, atau 100.')
    with db.transaction() as conn:
        query = lead_query(filters)
        total = conn.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        return {'total': total, 'page': page, 'page_size': size, 'data': [lead_public(conn, r) for r in db.rows(conn, query.limit(size).offset((page-1)*size))]}


@app.get('/api/facets')
def facets(user=Depends(auth)):
    with db.transaction() as conn:
        result = {}
        for field in ('category', 'city', 'province'):
            result[field] = [r['value'] for r in db.rows(conn, select(db.leads.c.payload[field].as_string().label('value')).distinct()) if r['value']]
        result['product'] = [r['value'] for r in db.rows(conn, select(db.evidence.c.value).where(db.evidence.c.kind == 'product').distinct())]
        return result


@app.get('/api/leads/{lead_id}')
def lead_detail(lead_id: str, user=Depends(auth)):
    with db.transaction() as conn:
        return lead_public(conn, get_lead(conn, lead_id), True)


@app.patch('/api/leads/{lead_id}')
def patch_lead(lead_id: str, body: dict = Body(...), user=Depends(operator)):
    allowed = {'pipeline_status', 'country_origin_code', 'phone_raw', 'note'}
    if set(body) - allowed:
        raise HTTPException(422, 'Field tidak diizinkan. Gunakan formulir consent khusus.')
    with db.transaction() as conn:
        row = get_lead(conn, lead_id)
        payload = dict(row['payload'])
        if 'pipeline_status' in body:
            if body['pipeline_status'] not in PIPELINES:
                raise HTTPException(422, {'pipeline_status': 'Status pipeline tidak valid.'})
            payload['pipeline_status'] = body['pipeline_status']
        if 'country_origin_code' in body:
            country = next((c for c in COUNTRIES if c['code'] == body['country_origin_code']), None)
            if not country:
                raise HTTPException(422, {'country_origin_code': 'Kode negara tidak valid.'})
            payload.update(country_origin_code=country['code'], country_origin_name=country['name'], country_origin_method='manual', country_origin_confidence='manual', country_origin_missing=False)
        if 'phone_raw' in body or 'country_origin_code' in body:
            raw = clean(body.get('phone_raw', payload['phone_raw']))
            tel, wa = phone(raw, payload['country_origin_code'])
            payload.update(phone_raw=raw, phone_normalized=tel, whatsapp_number=wa, whatsapp_status='derived_unverified' if wa else 'unknown', has_phone=bool(tel), has_whatsapp=bool(wa), whatsapp_checked_at=None, whatsapp_check_method=None)
        save_lead(conn, row, payload)
        log(conn, user['name'], 'lead_updated', {'before': {k: row['payload'].get(k) for k in body}, 'changes': body}, lead_id)
        return lead_public(conn, get_lead(conn, lead_id), True)


@app.post('/api/leads/bulk-pipeline')
def bulk_pipeline(body: dict = Body(...), user=Depends(operator)):
    ids = list(dict.fromkeys(body.get('ids', [])))
    if not ids or len(ids) > 1000 or body.get('status') not in PIPELINES:
        raise HTTPException(422, 'Pilih 1–1.000 lead dan status valid.')
    with db.transaction() as conn:
        for lead_id in ids:
            row = get_lead(conn, lead_id)
            save_lead(conn, row, {**row['payload'], 'pipeline_status': body['status']})
            log(conn, user['name'], 'pipeline_changed', {'from': row['payload']['pipeline_status'], 'to': body['status']}, lead_id)
    return {'count': len(ids)}


@app.post('/api/leads/{lead_id}/consent')
def consent(lead_id: str, body: dict = Body(...), user=Depends(operator)):
    basis = body.get('basis')
    if basis not in CONSENTS or not clean(body.get('source')) or not body.get('date'):
        raise HTTPException(422, 'Dasar, tanggal, dan sumber consent wajib diisi.')
    try:
        date = datetime.fromisoformat(body['date'].replace('Z', '+00:00'))
        if date.replace(tzinfo=date.tzinfo or timezone.utc) > datetime.now(timezone.utc):
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(422, 'Tanggal consent tidak valid atau berada di masa depan.')
    with db.transaction() as conn:
        row = get_lead(conn, lead_id)
        payload = {**row['payload'], 'consent_basis': basis, 'consent_at': date.isoformat(), 'consent_source': clean(body['source']), 'eligible_to_send': basis in ('opted_in', 'replied')}
        save_lead(conn, row, payload)
        log(conn, user['name'], 'consent_changed', {'from': row['payload']['consent_basis'], 'to': basis, 'source': body['source'], 'date': date.isoformat()}, lead_id)
        return payload


@app.delete('/api/leads/{lead_id}')
def delete_lead(lead_id: str, user=Depends(admin)):
    with db.transaction() as conn:
        get_lead(conn, lead_id)
        conn.execute(db.leads.delete().where(db.leads.c.id == lead_id))
        log(conn, user['name'], 'lead_deleted', {'lead_id': lead_id})
    return {'ok': True}


@app.post('/api/leads/{lead_id}/whatsapp-check')
def whatsapp_check(lead_id: str, body: dict = Body(...), user=Depends(operator)):
    if body.get('status') not in ('active', 'inactive', 'unknown') or not clean(body.get('method')):
        raise HTTPException(422, 'Status dan metode pemeriksaan wajib diisi.')
    try:
        checked = datetime.fromisoformat(str(body.get('date', '')).replace('Z', '+00:00'))
        checked = checked.replace(tzinfo=checked.tzinfo or timezone.utc)
        if checked > datetime.now(timezone.utc):
            raise ValueError()
    except ValueError:
        raise HTTPException(422, 'Tanggal pemeriksaan tidak valid.')
    with db.transaction() as conn:
        row = get_lead(conn, lead_id)
        if not row['payload']['whatsapp_number']:
            raise HTTPException(422, 'Lead belum memiliki nomor WhatsApp turunan.')
        save_lead(conn, row, {**row['payload'], 'whatsapp_status': body['status'], 'whatsapp_checked_at': checked.isoformat(), 'whatsapp_check_method': clean(body['method'])})
        log(conn, user['name'], 'whatsapp_checked', body, lead_id)
    return {'ok': True}


def queue_enrich(conn, row):
    from .saas import subscription
    if subscription(conn)['plan_code'] != 'pro':
        return False
    if not row['payload'].get('website_url'):
        return False
    pending = conn.scalar(select(func.count()).select_from(db.tasks).where(db.tasks.c.lead_id == row['id'], db.tasks.c.status.in_(['queued', 'fetching'])))
    if not pending:
        conn.execute(db.tasks.insert().values(id=db.uid(), lead_id=row['id'], status='queued', payload={'target_url': row['payload']['website_url'], 'created_at': now()}))
    return True


@app.post('/api/leads/{lead_id}/enrich')
def enrich_lead(lead_id: str, user=Depends(operator)):
    with db.transaction() as conn:
        if not queue_enrich(conn, get_lead(conn, lead_id)):
            raise HTTPException(422, 'Enrichment memerlukan paket Pro dan website lead.')
        log(conn, user['name'], 'enrichment_queued', {}, lead_id)
    return {'ok': True}


@app.post('/api/enrichment/segment')
def enrich_segment(body: dict = Body(...), user=Depends(operator)):
    with db.transaction() as conn:
        data = db.rows(conn, lead_query(body.get('filters', {})))
        count = sum(queue_enrich(conn, row) for row in data)
    return {'count': count}


def add_evidence(conn, lead_id, kind, value, url, snippet, detected_by, status='suspected', actor='worker'):
    if kind not in ('country', 'product') or not clean(value):
        raise HTTPException(422, 'Jenis dan nilai usulan tidak valid.')
    if kind == 'country' and value not in [c['code'] for c in COUNTRIES]:
        raise HTTPException(422, 'Kode negara tujuan tidak valid.')
    if not website(url)[0] or not clean(snippet):
        raise HTTPException(422, 'URL bukti dan kutipan sumber wajib diisi.')
    old = db.one(conn, db.evidence, and_(db.evidence.c.lead_id == lead_id, db.evidence.c.kind == kind, db.evidence.c.value == value))
    if old:
        return old['id']
    eid = db.uid()
    conn.execute(db.evidence.insert().values(id=eid, lead_id=lead_id, kind=kind, value=value if kind == 'country' else normalized(value), status=status, payload={'evidence_url': url, 'evidence_snippet': clean(snippet)[:2000], 'detected_by': detected_by, 'reviewed_by': actor if status == 'confirmed' else None, 'reviewed_at': now() if status == 'confirmed' else None}))
    log(conn, actor, 'evidence_added', {'id': eid, 'status': status, 'value': value}, lead_id)
    return eid


@app.post('/api/leads/{lead_id}/evidence')
def manual_evidence(lead_id: str, body: dict = Body(...), user=Depends(operator)):
    with db.transaction() as conn:
        get_lead(conn, lead_id)
        eid = add_evidence(conn, lead_id, body.get('kind'), body.get('value'), body.get('evidence_url', ''), body.get('evidence_snippet', ''), 'manual', 'confirmed', user['name'])
    return {'id': eid}


@app.get('/api/enrichment/queue')
def review_queue(user=Depends(auth)):
    with db.transaction() as conn:
        data = db.rows(conn, db.evidence.select().where(db.evidence.c.status == 'suspected'))
        result = [{**e['payload'], **{k: e[k] for k in ('id', 'lead_id', 'kind', 'value', 'status')}, 'business_name': get_lead(conn, e['lead_id'])['business_name']} for e in data]
        return {'total': len(result), 'page': 1, 'page_size': len(result), 'data': result}


@app.post('/api/enrichment/{evidence_id}/review')
def review(evidence_id: str, body: dict = Body(...), user=Depends(reviewer)):
    with db.transaction() as conn:
        e = db.one(conn, db.evidence, db.evidence.c.id == evidence_id)
        if not e:
            raise HTTPException(404, 'Usulan tidak ditemukan.')
        if body.get('decision') not in ('approved', 'rejected'):
            raise HTTPException(422, 'Keputusan tidak valid.')
        if body['decision'] == 'approved' and (not website(e['payload'].get('evidence_url', ''))[0] or not clean(e['payload'].get('evidence_snippet'))):
            raise HTTPException(422, 'Confirmed wajib memiliki URL dan kutipan bukti.')
        status = 'confirmed' if body['decision'] == 'approved' else 'rejected'
        conn.execute(db.evidence.update().where(db.evidence.c.id == evidence_id).values(status=status, payload={**e['payload'], 'reviewed_by': user['name'], 'reviewed_at': now(), 'review_note': clean(body.get('note'))}))
        log(conn, user['name'], 'evidence_reviewed', {'id': evidence_id, 'status': status, 'note': clean(body.get('note'))}, e['lead_id'])
        remaining = conn.scalar(select(func.count()).select_from(db.evidence).where(db.evidence.c.lead_id == e['lead_id'], db.evidence.c.status == 'suspected'))
        if remaining == 0:
            conn.execute(db.tasks.update().where(db.tasks.c.lead_id == e['lead_id'], db.tasks.c.status == 'proposed').values(status='reviewed'))
    return {'status': status}


@app.post('/api/exports')
def export(body: dict = Body(...), user=Depends(operator)):
    kind = body.get('type', 'analysis')
    if kind not in ('analysis', 'send_list'):
        raise HTTPException(422, 'Tipe export tidak valid.')
    with db.transaction() as conn:
        filters = body.get('filters', {})
        from .saas import gate_export
        data = [lead_public(conn, row) for row in db.rows(conn, lead_query(filters))]
        gate_export(conn, len(data), filters)
        blocked = sum(r['consent_basis'] not in ('opted_in', 'replied') or not r['eligible_to_send'] for r in data)
        if kind == 'send_list' and blocked:
            raise HTTPException(422, {'message': f'{blocked} lead belum lolos gerbang consent.', 'blocked_count': blocked})
        conn.execute(db.exports.insert().values(id=db.uid(), actor=user['name'], created_at=now(), count=len(data), type=kind, filters=filters))
        log(conn, user['name'], 'export', {'count': len(data), 'type': kind})
    return PlainTextResponse(csv_export(data), media_type='text/csv; charset=utf-8', headers={'Content-Disposition': 'attachment; filename="pokoscrap-'+kind+'.csv"', 'X-Row-Count': str(len(data))})


@app.get('/api/segments')
def list_segments(user=Depends(auth)):
    with db.transaction() as conn:
        return db.rows(conn, db.segments.select())


@app.post('/api/segments')
def create_segment(body: dict = Body(...), user=Depends(operator)):
    if not clean(body.get('name')):
        raise HTTPException(422, 'Nama segmen wajib diisi.')
    row = dict(id=db.uid(), name=clean(body['name']), created_by=user['name'], filters=body.get('filters', {}))
    with db.transaction() as conn:
        conn.execute(db.segments.insert().values(**row))
    return row


@app.get('/api/stats/overview')
def overview(user=Depends(auth)):
    with db.transaction() as conn:
        total = conn.scalar(select(func.count()).select_from(db.leads))
        week = (datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
        country_counts = db.rows(conn, select(db.leads.c.country_origin_code.label('code'), func.count().label('count')).group_by(db.leads.c.country_origin_code).order_by(func.count().desc()).limit(10))
        contacts = {key: conn.scalar(select(func.count()).select_from(db.leads).where(db.leads.c.payload['has_'+key].as_boolean() == True)) for key in ('phone', 'whatsapp', 'email')}
        return {'total': total, 'new_week': conn.scalar(select(func.count()).select_from(db.leads).where(db.leads.c.first_seen_at >= week)), 'confirmed': conn.scalar(select(func.count(func.distinct(db.evidence.c.lead_id))).where(db.evidence.c.kind == 'country', db.evidence.c.status == 'confirmed')), 'running': conn.scalar(select(func.count()).select_from(db.jobs).where(db.jobs.c.status.in_(['queued', 'running', 'ingesting']))), 'review': conn.scalar(select(func.count()).select_from(db.evidence).where(db.evidence.c.status == 'suspected')), 'countries': country_counts, 'contacts': contacts, 'jobs': [job_public(r) for r in db.rows(conn, db.jobs.select().where(db.jobs.c.archived == False).order_by(db.jobs.c.created_at.desc()).limit(4))], 'recent': [lead_public(conn, r) for r in db.rows(conn, db.leads.select().order_by(db.leads.c.first_seen_at.desc()).limit(4))], 'pipeline': [{'status': status, 'count': conn.scalar(select(func.count()).select_from(db.leads).where(db.leads.c.pipeline_status == status))} for status in PIPELINES]}


@app.get('/api/settings')
def get_settings(user=Depends(admin)):
    with db.transaction() as conn:
        return {'config': config(conn), 'users': tenant_users(conn), 'exports': db.rows(conn, db.exports.select().order_by(db.exports.c.created_at.desc()).limit(100)), 'audit': db.rows(conn, db.audit.select().order_by(db.audit.c.created_at.desc()).limit(100)), 'tasks': db.rows(conn, db.tasks.select().order_by(db.tasks.c.id).limit(100))}


@app.patch('/api/settings')
def change_settings(body: dict = Body(...), user=Depends(admin)):
    if body.get('engine_mode', 'quick') != 'quick':
        raise HTTPException(422, 'Mode manager belum tersedia pada build ini.')
    limits = {'concurrency': (1, 4), 'depth': (1, 20), 'enrichment_pages': (1, 10), 'session_idle_minutes': (5, 480)}
    for key, bounds in limits.items():
        if key in body and (not isinstance(body[key], int) or not bounds[0] <= body[key] <= bounds[1]):
            raise HTTPException(422, {key: f'Gunakan angka {bounds[0]}–{bounds[1]}.'})
    if set(body) - set(DEFAULT_SETTINGS):
        raise HTTPException(422, 'Pengaturan tidak dikenal.')
    with db.transaction() as conn:
        payload = {**config(conn), **body}
        conn.execute(db.settings.delete().where(db.settings.c.id == 'main'))
        conn.execute(db.settings.insert().values(id='main', payload=payload))
        log(conn, user['name'], 'settings_changed', body)
    return payload


def tenant_users(conn):
    result = []
    for member in db.rows(conn, db.memberships.select()):
        user = db.one(conn, db.users, db.users.c.id == member['user_id'])
        result.append({**public_user(user), 'roles': member['roles'], 'active': member['active']})
    return result


@app.patch('/api/users/{user_id}')
def change_user(user_id: str, body: dict = Body(...), user=Depends(admin)):
    if set(body) - {'roles', 'active'} or ('roles' in body and (not body['roles'] or set(body['roles']) - {'Owner', 'Admin', 'Operator', 'Reviewer'})):
        raise HTTPException(422, 'Perubahan pengguna tidak valid.')
    with db.transaction() as conn:
        row = db.one(conn, db.memberships, db.memberships.c.user_id == user_id)
        if not row:
            raise HTTPException(404, 'Anggota tidak ditemukan.')
        if 'Owner' in row['roles']:
            raise HTTPException(422, 'Kepemilikan organisasi tidak dapat dicabut melalui perubahan peran.')
        if 'Owner' in body.get('roles', []):
            raise HTTPException(422, 'Transfer kepemilikan belum tersedia.')
        conn.execute(db.memberships.update().where(db.memberships.c.id == row['id']).values(**body))
        log(conn, user['name'], 'membership_updated', {'id': user_id, **body})
    return {'ok': True}


@app.post('/api/directory/import')
def directory_import(body: dict = Body(...), user=Depends(admin)):
    text = body.get('csv', '')
    if len(text) > 2_000_000:
        raise HTTPException(422, 'File maksimal 2 MB.')
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    required = {'business_name', 'domain', 'country_code', 'product', 'evidence_url', 'evidence_snippet'}
    if not required.issubset(reader.fieldnames or []):
        raise HTTPException(422, 'Header wajib: '+', '.join(sorted(required)))
    matched, errors = 0, []
    with db.transaction() as conn:
        for i, row in enumerate(reader, 2):
            if i > 10002:
                raise HTTPException(422, 'Maksimal 10.000 baris per impor.')
            domain = website(row.get('domain'))[1]
            lead = db.one(conn, db.leads, db.leads.c.payload['website_domain'].as_string() == domain) if domain else None
            if not lead:
                lead = db.one(conn, db.leads, func.lower(db.leads.c.business_name) == normalized(row.get('business_name')))
            if not lead:
                errors.append({'row': i, 'error': 'Lead tidak cocok.'})
                continue
            try:
                for kind, key in [('country', 'country_code'), ('product', 'product')]:
                    if clean(row.get(key)):
                        add_evidence(conn, lead['id'], kind, clean(row[key]), row.get('evidence_url', ''), row.get('evidence_snippet', ''), 'directory_import', actor=user['name'])
                matched += 1
            except HTTPException as exc:
                errors.append({'row': i, 'error': exc.detail})
        log(conn, user['name'], 'directory_import', {'matched': matched, 'errors': len(errors)})
    return {'matched': matched, 'errors': errors}


def ingest(job_id, raw):
    raw_rows, headers = read_rows(raw)
    if raw_rows and not {'title', 'address', 'phone', 'place_id'}.issubset(headers):
        raise ValueError('Header gosom tidak kompatibel: title, address, phone, place_id wajib tersedia.')
    with db.transaction() as conn:
        job = job_public(get_job(conn, job_id))
        save_job(conn, job_id, headers=headers, header_missing=[h for h in GOSOM_HEADERS if h not in headers], found_count=len(raw_rows))
        from .saas import job_reservation
        reservation = job_reservation(conn, job_id)
        if reservation:
            required, distinct = 0, set()
            for raw_row in raw_rows:
                try:
                    candidate = map_row(raw_row, job)
                except (ValueError, TypeError, KeyError):
                    continue
                key = fingerprint(candidate)
                if key in distinct:
                    continue
                distinct.add(key)
                existing = db.one(conn, db.leads, db.leads.c.dedupe_key == key)
                if not existing:
                    required += int(candidate['has_phone']) + int(candidate['has_email'])
            if required > -reservation['amount']:
                raise ValueError(f'Hasil memerlukan {required} kredit, reservasi {-reservation["amount"]}. Ingestion seluruh job ditahan; arsip mentah tetap tersimpan. Duplikasi job dengan batas lebih besar.')
    inserted = duplicate = spent = 0
    errors = []
    for index, raw_row in enumerate(raw_rows, 2):
        try:
            payload = map_row(raw_row, job)
            row_hash = hashlib.sha256(json.dumps(raw_row, sort_keys=True).encode()).hexdigest()
            with db.transaction() as conn:
                if db.one(conn, db.seen, and_(db.seen.c.job_id == job_id, db.seen.c.row_hash == row_hash)):
                    duplicate += 1
                    continue
                key = fingerprint(payload)
                existing = db.one(conn, db.leads, db.leads.c.dedupe_key == key)
                if not existing:
                    # Fallback matching can link a row which first arrived without Place ID.
                    clauses = []
                    if payload['phone_normalized']:
                        clauses.append(and_(func.lower(db.leads.c.business_name) == normalized(payload['business_name']), db.leads.c.payload['phone_normalized'].as_string() == payload['phone_normalized']))
                    if payload['website_domain']:
                        clauses.append(and_(func.lower(db.leads.c.business_name) == normalized(payload['business_name']), db.leads.c.payload['website_domain'].as_string() == payload['website_domain']))
                    if clauses:
                        existing = db.one(conn, db.leads, and_(or_(*clauses), db.leads.c.place_id.is_(None)) if payload['place_id'] else or_(*clauses))
                if existing:
                    old = existing['payload']
                    protected = {'pipeline_status', 'consent_basis', 'consent_at', 'consent_source', 'eligible_to_send', 'first_query', 'first_seen_at'}
                    if old.get('country_origin_method') == 'manual':
                        protected.update(k for k in payload if k.startswith('country_origin'))
                    merged = {k: old.get(k) if k in protected or old.get(k) not in (None, '', [], {}) else value for k, value in payload.items()}
                    merged.update(last_seen_at=now(), seen_count=old.get('seen_count', 1)+1)
                    if merged.get('whatsapp_number') and not old.get('whatsapp_number'):
                        merged['whatsapp_status'] = 'derived_unverified'
                    if payload['place_id'] and not existing['place_id']:
                        conn.execute(db.leads.update().where(db.leads.c.id == existing['id']).values(place_id=payload['place_id'], dedupe_key=key))
                    for field in ('phone', 'whatsapp', 'email'):
                        merged['has_'+field] = bool(merged['emails' if field == 'email' else 'phone_normalized' if field == 'phone' else 'whatsapp_number'])
                    save_lead(conn, existing, merged)
                    lead_id = existing['id']
                    duplicate += 1
                else:
                    lead_id = db.uid()
                    conn.execute(db.leads.insert().values(id=lead_id, dedupe_key=key, place_id=payload['place_id'] or None, business_name=payload['business_name'], country_origin_code=payload['country_origin_code'], pipeline_status='Baru', first_job_id=job_id, first_seen_at=payload['first_seen_at'], payload=payload))
                    inserted += 1
                    spent += int(payload['has_phone']) + int(payload['has_email'])
                    log(conn, 'gosom', 'discovered', {'job_id': job_id}, lead_id)
                conn.execute(db.seen.insert().values(job_id=job_id, row_hash=row_hash, lead_id=lead_id))
                queue_enrich(conn, get_lead(conn, lead_id))
        except (ValueError, TypeError, KeyError) as exc:
            errors.append({'row': index, 'error': str(exc)})
    with db.transaction() as conn:
        save_job(conn, job_id, inserted_count=inserted, duplicate_count=duplicate, error_count=len(errors), row_errors=errors, spent_credits=job.get('spent_credits', 0)+spent)
    return {'inserted': inserted, 'duplicate': duplicate, 'errors': errors}


def run_gosom(job_id):
    with db.transaction() as conn:
        job = job_public(get_job(conn, job_id))
        if job['status'] != 'queued':
            return
        cfg = config(conn)
        save_job(conn, job_id, status='running', started_at=now(), engine_mode='quick')
    folder = db.RUNTIME / 'jobs' / job_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'queries.txt').write_text('\n'.join(job['queries'])+'\n')
    host_root = Path(os.getenv('HOST_DATA_PATH', db.RUNTIME))
    mounted = host_root / 'jobs' / job_id
    command = ['docker', 'run', '--rm', '--name', 'pokoscrap-'+job_id, '--shm-size=512m', '-v', f'{mounted}:/out', '-v', 'pokoscrap-playwright:/opt', os.getenv('GOSOM_IMAGE', 'gosom/google-maps-scraper:latest'), '-input', '/out/queries.txt', '-results', '/out/results.csv', '-lang', job['lang'], '-c', str(cfg['concurrency']), '-depth', str(cfg['depth']), '-exit-on-inactivity', '1m']
    if job.get('email_enabled', True):
        command.append('-email')
    if job['geo_mode'] == 'grid':
        command += ['-grid-bbox', job['grid_bbox'], '-grid-cell', '1']
    else:
        command += ['-geo', f"{job['latitude']},{job['longitude']}", '-radius', str(job['radius_m'])]
    if (folder / 'results.csv').exists():
        command.append('-resume')
    output = []
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        workers[job_id] = proc
        for line in proc.stdout:
            output.append(line)
            text = ''.join(output)[-100000:]
            with db.transaction() as conn:
                found = re.search(r'"message":"(\d+) places found"', line)
                values = {'log_text': text}
                if found:
                    values['found_count'] = get_job(conn, job_id)['payload'].get('found_count', 0)+int(found.group(1))
                save_job(conn, job_id, **values)
            if re.search(r'captcha|unusual traffic|rate limit', line, re.I):
                subprocess.run(['docker', 'stop', '-t', '5', 'pokoscrap-'+job_id], capture_output=True, timeout=15)
                raise ValueError('Google Maps membatasi pencarian. Job dihentikan; coba ulang nanti.')
        code = proc.wait()
        with db.transaction() as conn:
            stopped = get_job(conn, job_id)['status'] == 'stopped'
            if not stopped:
                save_job(conn, job_id, status='ingesting')
        result = folder / 'results.csv'
        if result.exists():
            ingest(job_id, result.read_bytes())
        if code and not stopped:
            raise ValueError('Engine gagal. Admin dapat membuka log teknis pada detail job.')
        if not result.exists() and not stopped:
            raise ValueError('Engine tidak menghasilkan file. Periksa log dan kompatibilitas gosom.')
        with db.transaction() as conn:
            # The engine does not reliably expose per-cell truncation; mark as unknown unless a cap appears in its logs.
            save_job(conn, job_id, status='stopped' if stopped else 'done', finished_at=now(), raw_file_path=str(result), hit_result_cap=bool(re.search(r'result.?cap|maximum results', ''.join(output), re.I)), coverage_note='Batas per sel belum dapat dipastikan otomatis; cek log dan cakupan grid.')
    except Exception as exc:
        with db.transaction() as conn:
            current = get_job(conn, job_id)
            save_job(conn, job_id, status='stopped' if current['status'] == 'stopped' else 'failed', finished_at=now(), error=str(exc), log_text=''.join(output)[-100000:])
    finally:
        with db.transaction() as conn:
            from .saas import settle_job
            latest = get_job(conn, job_id)
            settle_job(conn, job_id, latest['payload'].get('spent_credits', 0), 'gosom')
        workers.pop(job_id, None)


def run_enrichment(task):
    with db.transaction() as conn:
        row = get_lead(conn, task['lead_id'])
        limit = config(conn)['enrichment_pages']
        conn.execute(db.tasks.update().where(db.tasks.c.id == task['id']).values(status='fetching'))
    root = row['payload']['website_url']
    domain = website(root)[1]
    pending, visited, count = [root], set(), 0
    try:
        while pending and len(visited) < limit:
            url = pending.pop(0)
            if url in visited or website(url)[1] != domain:
                continue
            visited.add(url)
            soup = BeautifulSoup(fetch_public(url), 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'noscript']):
                tag.decompose()
            text = clean(soup.get_text(' '))
            found = []
            for match in re.finditer(r'\b(?:export\w*|ekspor\w*|shipping|international|distributor|kirim|pasar)\b', text, re.I):
                snippet = text[max(0, match.start()-120):match.end()+220]
                for country in COUNTRIES:
                    if any(len(alias) > 2 and re.search(r'\b'+re.escape(alias)+r'\b', snippet, re.I) for alias in country['aliases']):
                        found.append(('country', country['code'], snippet))
            for product in ('coffee', 'kopi', 'furniture', 'furnitur', 'coconut', 'kelapa', 'spices', 'rempah', 'cocoa', 'kakao', 'textile', 'tekstil', 'rattan', 'rotan', 'handicraft', 'kerajinan'):
                match = re.search(r'\b'+product+r'\b', text, re.I)
                if match:
                    found.append(('product', product, text[max(0, match.start()-80):match.end()+140]))
            with db.transaction() as conn:
                for kind, value, snippet in found:
                    add_evidence(conn, row['id'], kind, value, url, snippet, 'worker_website')
                    count += 1
            links = [urljoin(url, a['href']).split('#')[0] for a in soup.select('a[href]') if re.search(r'export|shipping|international|product|produk|about|tentang', a['href'], re.I)]
            pending.extend(link for link in links if website(link)[1] == domain and link not in visited)
        with db.transaction() as conn:
            conn.execute(db.tasks.update().where(db.tasks.c.id == task['id']).values(status='proposed' if count else 'reviewed', payload={**task['payload'], 'finished_at': now(), 'pages': len(visited), 'findings': count}))
    except Exception as exc:
        with db.transaction() as conn:
            conn.execute(db.tasks.update().where(db.tasks.c.id == task['id']).values(status='failed', payload={**task['payload'], 'error': str(exc), 'finished_at': now()}))


def worker_loop(kind):
    # One instance per kind. Database state survives closing the browser.
    while True:
        try:
            with db.transaction(unscoped=True) as conn:
                table = db.jobs if kind == 'jobs' else db.tasks
                row = conn.execute(table.select().where(table.c.status == 'queued').limit(1)).mappings().first()
            if row:
                db.tenant_context.set(row['tenant_id'])
                run_gosom(row['id']) if kind == 'jobs' else run_enrichment(dict(row))
            else:
                time.sleep(2)
        except Exception:
            time.sleep(3)


@app.get('/config.js')
def local_config():
    return PlainTextResponse('window.POKO_DEMO = false;', media_type='application/javascript')


from .saas import install
install(app)

app.mount('/', StaticFiles(directory=ROOT / 'dist', html=True), name='frontend')


if os.getenv('POKO_WORKERS', '0' if os.getenv('VERCEL') else '1') == '1':
    with db.transaction(unscoped=True) as conn:
        for row in db.rows(conn, db.jobs.select().where(db.jobs.c.status.in_(['running', 'ingesting']))):
            save_job(conn, row['id'], status='failed', error='Proses aplikasi terhenti. Jalankan ulang job untuk melanjutkan arsip.', finished_at=now())
        conn.execute(db.tasks.update().where(db.tasks.c.status == 'fetching').values(status='queued'))
    for kind in ('jobs', 'enrichment'):
        threading.Thread(target=worker_loop, args=(kind,), daemon=True).start()

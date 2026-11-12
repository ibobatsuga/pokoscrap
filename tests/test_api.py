import csv
import hashlib
import hmac
import io
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

os.environ['POKO_WORKERS'] = '0'
os.environ.setdefault('POKO_DATA', tempfile.mkdtemp(prefix='pokoscrap-tests-'))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from server import db
from server.app import app, ingest, password_hash
from server.core import CSV_FIELDS, GOSOM_HEADERS, fetch_public, map_row, now, origin, phone
from server.saas import balance, create_org, ledger_entry, settle_job

HEADERS = {'X-Poko-Request': '1'}
PASSWORD = 'Fixture-only-password-2026'


def make_user(email, role='Owner', platform=False):
    with db.transaction(unscoped=True) as conn:
        uid = db.uid()
        user = {'id': uid, 'name': email.split('@')[0], 'email': email, 'password_hash': password_hash(PASSWORD), 'roles': [], 'active': True, 'verified': True, 'platform_admin': platform}
        conn.execute(db.users.insert().values(**user))
        org = create_org(conn, user, 'Org '+user['name'])
        conn.execute(db.memberships.update().where(db.memberships.c.tenant_id == org['id']).values(roles=[role]))
    client = TestClient(app)
    result = client.post('/api/login', json={'email': email, 'password': PASSWORD}, headers=HEADERS)
    assert result.status_code == 200, result.text
    return client, org['id'], uid


@pytest.fixture(autouse=True)
def clean_database():
    with db.transaction(unscoped=True) as conn:
        for table in reversed(db.meta.sorted_tables):
            conn.execute(table.delete())
    yield
    db.tenant_context.set(None)


@pytest.fixture
def team():
    return make_user('owner@example.test', platform=True)


def new_job(client, **extra):
    payload = {'name': 'Uji kopi', 'queries': 'kopi Yogyakarta\nkopi Yogyakarta\nprodusen kopi', 'geo_mode': 'point', 'latitude': -7.78, 'longitude': 110.36, 'radius_m': 500, 'email_enabled': True, 'max_credits': 20, 'start': False, **extra}
    response = client.post('/api/jobs', headers=HEADERS, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def fixture_row(pid='fixture-place-1', **extra):
    return {'title': 'Kopi Uji', 'place_id': pid, 'category': 'Produsen kopi', 'address': 'Kota Yogyakarta, Daerah Istimewa Yogyakarta 55165', 'phone': '+6281234567890', 'website': 'https://kopi.example', 'emails': ['HELLO@kopi.example', 'hello@kopi.example'], 'review_rating': '4.7', 'review_count': '12', **extra}


def import_rows(job, tid, data):
    token = db.tenant_context.set(tid)
    try:
        return ingest(job['id'], json.dumps(data).encode())
    finally:
        db.tenant_context.reset(token)


def upgrade(tid, plan='pro'):
    with db.transaction(unscoped=True) as conn:
        conn.execute(db.subscriptions.update().where(db.subscriptions.c.tenant_id == tid).values(plan_code=plan))


def test_free_exactly_30_and_no_public_bypass(team):
    client, tid, _ = team
    assert client.get('/api/credits/balance').json()['balance'] == 30
    assert TestClient(app).get('/api/leads').status_code == 401
    assert client.post('/api/jobs', json={}).status_code == 403


def test_job_validation_deduplicates_queries(team):
    client, _, _ = team
    job = new_job(client)
    assert len(job['queries']) == 2
    response = client.post('/api/jobs', headers=HEADERS, json={'name': '', 'queries': '', 'geo_mode': 'grid', 'grid_bbox': 'bad'})
    assert response.status_code == 422
    assert set(response.json()['detail']) >= {'name', 'queries', 'area'}


def test_ingestion_idempotent_and_manual_fields_preserved(team):
    client, tid, _ = team
    job = new_job(client)
    import_rows(job, tid, [fixture_row()])
    lead = client.get('/api/leads').json()['data'][0]
    client.patch('/api/leads/'+lead['id'], headers=HEADERS, json={'pipeline_status': 'Follow-up', 'country_origin_code': 'MY'})
    client.post('/api/leads/'+lead['id']+'/consent', headers=HEADERS, json={'basis': 'opted_in', 'date': '2026-01-01T00:00:00Z', 'source': 'Formulir uji'})
    import_rows(job, tid, [fixture_row()])
    other = new_job(client)
    import_rows(other, tid, [fixture_row()])
    result = client.get('/api/leads').json()
    assert result['total'] == 1
    lead = result['data'][0]
    assert lead['pipeline_status'] == 'Follow-up'
    assert lead['country_origin_code'] == 'MY'
    assert lead['country_origin_method'] == 'manual'
    assert lead['consent_basis'] == 'opted_in'
    assert lead['seen_count'] == 2


def test_cross_tenant_lead_job_raw_export_and_dedupe(team):
    a, ta, _ = team
    b, tb, _ = make_user('other@example.test')
    ja, jb = new_job(a), new_job(b)
    import_rows(ja, ta, [fixture_row()])
    import_rows(jb, tb, [fixture_row()])
    la = a.get('/api/leads').json()['data'][0]
    lb = b.get('/api/leads').json()['data'][0]
    assert la['id'] != lb['id']
    assert a.get('/api/leads').json()['total'] == b.get('/api/leads').json()['total'] == 1
    assert a.get('/api/leads/'+lb['id']).status_code == 404
    assert a.patch('/api/leads/'+lb['id'], headers=HEADERS, json={'pipeline_status': 'Deal'}).status_code == 404
    assert a.get('/api/jobs/'+jb['id']).status_code == 404
    assert a.get('/api/jobs/'+jb['id']+'/raw').status_code == 404
    result = a.post('/api/exports', headers=HEADERS, json={'filters': {'job': jb['id']}})
    assert result.status_code == 200
    assert len(list(csv.reader(io.StringIO(result.text.lstrip('\ufeff'))))) == 1
    assert a.get('/api/credits/balance').json()['balance'] == 30
    with db.transaction(unscoped=True) as conn:
        assert conn.scalar(select(func.count()).select_from(db.platform_audit).where(db.platform_audit.c.type == 'access_denied')) >= 4


def test_consent_gate_rejects_general_patch_and_send_list(team):
    client, tid, _ = team
    job = new_job(client)
    import_rows(job, tid, [fixture_row()])
    lead_id = client.get('/api/leads').json()['data'][0]['id']
    response = client.patch('/api/leads/'+lead_id, headers=HEADERS, json={'eligible_to_send': True})
    assert response.status_code == 422
    response = client.post('/api/exports', headers=HEADERS, json={'type': 'send_list'})
    assert response.status_code == 422
    assert response.json()['detail']['blocked_count'] == 1
    assert client.post('/api/leads/'+lead_id+'/consent', headers=HEADERS, json={'basis': 'opted_in', 'date': '2026-01-01'}).status_code == 422
    result = client.post('/api/leads/'+lead_id+'/consent', headers=HEADERS, json={'basis': 'replied', 'date': '2026-01-01', 'source': 'Balasan formulir uji'})
    assert result.status_code == 200
    assert client.post('/api/exports', headers=HEADERS, json={'type': 'send_list'}).status_code == 200


def test_phone_email_country_rules():
    assert phone('0274 123456', 'ID')[1] == ''
    tel, wa = phone('+6281234567890', 'ID')
    assert tel == wa == '+6281234567890'
    row = map_row(fixture_row(), {'email_enabled': False})
    assert row['emails'] == []
    assert row['whatsapp_status'] == 'derived_unverified'
    assert row['consent_basis'] == 'none' and row['eligible_to_send'] is False
    assert origin('Yogyakarta, Daerah Istimewa Yogyakarta 55165')[0:3] == ('ID', 'Indonesia', 'postal_province')
    assert origin('Unresolvable address')[0] == ''
    assert origin('Unresolvable address', 52.52, 13.405)[0] == 'DE'


def test_bad_row_does_not_abort_and_distinct_place_ids_stay_separate(team):
    client, tid, _ = team
    job = new_job(client)
    result = import_rows(job, tid, [fixture_row(), fixture_row('different-place'), fixture_row('bad', review_rating='invalid')])
    assert result['inserted'] == 2 and len(result['errors']) == 1
    assert client.get('/api/leads').json()['total'] == 2


def test_confirmed_requires_evidence_and_filter_semantics(team):
    client, tid, _ = team
    upgrade(tid)
    job = new_job(client)
    import_rows(job, tid, [fixture_row(), fixture_row('second', title='Kakao Uji', phone='', website='')])
    lead_id = next(l['id'] for l in client.get('/api/leads').json()['data'] if l['has_phone'])
    assert client.post('/api/leads/'+lead_id+'/evidence', headers=HEADERS, json={'kind': 'country', 'value': 'JP'}).status_code == 422
    for kind, value in [('country', 'JP'), ('country', 'AU'), ('product', 'kopi')]:
        assert client.post('/api/leads/'+lead_id+'/evidence', headers=HEADERS, json={'kind': kind, 'value': value, 'evidence_url': 'https://example.com/export', 'evidence_snippet': 'Exports coffee to Japan and Australia.'}).status_code == 200
    result = client.get('/api/leads?origin=ID&destination=JP,AU&destination_all=true&product=kopi&has_phone=true&has_email=true').json()
    assert result['total'] == 1
    assert client.get('/api/leads?destination=JP,US&destination_all=true').json()['total'] == 0


def test_bulk_pipeline_transaction_and_audit(team):
    client, tid, _ = team
    job = new_job(client)
    import_rows(job, tid, [fixture_row(str(i), title='Kopi '+str(i), website='') for i in range(25)])
    ids = [l['id'] for l in client.get('/api/leads').json()['data']]
    response = client.post('/api/leads/bulk-pipeline', headers=HEADERS, json={'ids': ids, 'status': 'Dihubungi'})
    assert response.status_code == 200 and response.json()['count'] == 25
    assert all(client.get('/api/leads/'+i).json()['activities'][0]['type'] == 'pipeline_changed' for i in ids)
    result = client.post('/api/leads/bulk-pipeline', headers=HEADERS, json={'ids': [ids[0], 'unavailable'], 'status': 'Deal'})
    assert result.status_code == 404
    assert client.get('/api/leads/'+ids[0]).json()['pipeline_status'] == 'Dihubungi'


def test_csv_order_contact_filters_and_formula_escaping(team):
    client, tid, _ = team
    job = new_job(client)
    import_rows(job, tid, [fixture_row(title='=HYPERLINK("bad")'), fixture_row('second', title='No contact', phone='', website='')])
    response = client.post('/api/exports', headers=HEADERS, json={'filters': {'has_phone': 'true'}})
    records = list(csv.reader(io.StringIO(response.text.lstrip('\ufeff'))))
    assert records[0] == CSV_FIELDS
    assert len(records) == 2
    assert records[1][0].startswith("'=")
    assert records[1][CSV_FIELDS.index('consent_basis')] == 'none'
    assert client.get('/api/leads?has_phone=false').json()['total'] == 1


def test_roles_enforced_api_and_revocation_immediate(team):
    reviewer, tid, uid = make_user('reviewer@example.test', 'Reviewer')
    assert reviewer.post('/api/jobs', headers=HEADERS, json={}).status_code == 403
    assert reviewer.get('/api/settings').status_code == 403
    operator, to, _ = make_user('operator@example.test', 'Operator')
    assert operator.patch('/api/settings', headers=HEADERS, json={}).status_code == 403
    with db.transaction(unscoped=True) as conn:
        conn.execute(db.memberships.update().where(db.memberships.c.user_id == uid).values(active=False))
    assert reviewer.get('/api/leads').status_code == 401


def test_credit_reservation_insufficient_rejected_and_refund_idempotent(team):
    client, tid, _ = team
    response = client.post('/api/jobs', headers=HEADERS, json={'name': 'Too large', 'queries': 'kopi', 'geo_mode': 'point', 'latitude': -7.78, 'longitude': 110.36, 'radius_m': 500, 'max_credits': 31})
    assert response.status_code == 402 and response.json()['detail']['remaining'] == 30
    assert client.get('/api/jobs').json()['total'] == 0
    job = new_job(client, start=True)
    assert client.get('/api/credits/balance').json()['balance'] == 10
    assert client.post('/api/jobs/'+job['id']+'/stop', headers=HEADERS, json={}).status_code == 200
    assert client.get('/api/credits/balance').json()['balance'] == 30
    token = db.tenant_context.set(tid)
    with db.transaction() as conn:
        settle_job(conn, job['id'], 0, 'test')
    db.tenant_context.reset(token)
    assert client.get('/api/credits/balance').json()['balance'] == 30


def test_budget_does_not_silently_ingest_partial_job(team):
    client, tid, _ = team
    job = new_job(client, start=True, max_credits=1)
    with pytest.raises(ValueError, match='Ingestion seluruh job ditahan'):
        import_rows(job, tid, [fixture_row()])
    assert client.get('/api/leads').json()['total'] == 0


def test_webhook_signature_and_idempotent_grant(team, monkeypatch):
    client, tid, _ = team
    monkeypatch.setenv('TRIPAY_PRIVATE_KEY', 'fixture-private-key')
    with db.transaction(unscoped=True) as conn:
        conn.execute(db.payments.insert().values(id='fixture-invoice', tenant_id=tid, plan_code='starter', amount=99000, status='UNPAID', reference='T-FIXTURE', created_at=now(), payload={}))
        conn.execute(db.payment_index.insert().values(id='fixture-invoice', tenant_id=tid))
    raw = json.dumps({'merchant_ref': 'fixture-invoice', 'reference': 'T-FIXTURE', 'amount': 99000, 'status': 'PAID'}).encode()
    headers = {'Content-Type': 'application/json', 'X-Callback-Event': 'payment_status', 'X-Callback-Signature': hmac.new(b'fixture-private-key', raw, hashlib.sha256).hexdigest()}
    assert client.post('/api/billing/webhook', content=raw).status_code == 401
    for _ in range(2):
        response = client.post('/api/billing/webhook', content=raw, headers=headers)
        assert response.status_code == 200, response.text
    assert client.get('/api/credits/balance').json()['balance'] == 1030
    assert client.get('/api/billing/subscription').json()['plan_code'] == 'starter'


def test_platform_adjustment_requires_reason_and_cannot_edit_foreign_leads(team):
    admin, ta, _ = team
    other, tb, _ = make_user('tenant@example.test')
    response = admin.post('/api/admin/tenants/'+tb+'/credits', headers=HEADERS, json={'amount': 10})
    assert response.status_code == 422
    response = admin.post('/api/admin/tenants/'+tb+'/credits', headers=HEADERS, json={'amount': 10, 'reason': 'Koreksi uji'})
    assert response.status_code == 200
    assert other.get('/api/credits/balance').json()['balance'] == 40
    assert admin.get('/api/credits/balance').json()['balance'] == 30
    assert other.get('/api/admin/tenants').status_code == 403
    assert admin.post('/api/admin/tenants/'+tb+'/status', headers=HEADERS, json={'status': 'suspended', 'reason': 'Uji penangguhan'}).status_code == 200
    assert other.get('/api/leads').status_code == 401


def test_tenant_settings_are_separate(team):
    a, _, _ = team
    b, _, _ = make_user('settings@example.test')
    assert a.patch('/api/settings', headers=HEADERS, json={'depth': 2}).status_code == 200
    assert b.patch('/api/settings', headers=HEADERS, json={'depth': 3}).status_code == 200
    assert a.get('/api/settings').json()['config']['depth'] == 2
    assert b.get('/api/settings').json()['config']['depth'] == 3
    assert len(a.get('/api/settings').json()['users']) == 1


def test_ssrf_rejects_private_urls():
    for url in ('http://127.0.0.1/', 'http://169.254.169.254/', 'http://[::1]/', 'file:///etc/passwd', 'http://user:pass@example.com/'):
        with pytest.raises(ValueError):
            fetch_public(url)


def test_active_whatsapp_still_requires_consent(team):
    client, tid, _ = team
    job = new_job(client)
    import_rows(job, tid, [fixture_row()])
    lead_id = client.get('/api/leads').json()['data'][0]['id']
    assert client.post('/api/leads/'+lead_id+'/whatsapp-check', headers=HEADERS, json={'status': 'active'}).status_code == 422
    response = client.post('/api/leads/'+lead_id+'/whatsapp-check', headers=HEADERS, json={'status': 'active', 'method': 'Pemeriksaan manual berizin — fixture', 'date': '2026-01-01T00:00:00Z'})
    assert response.status_code == 200
    lead = client.get('/api/leads/'+lead_id).json()
    assert lead['whatsapp_status'] == 'active' and lead['eligible_to_send'] is False
    assert client.post('/api/exports', headers=HEADERS, json={'type': 'send_list'}).status_code == 422


def test_pro_api_key_scope_and_immediate_revoke(team):
    owner, tid, _ = team
    other, other_tid, _ = make_user('api-other@example.test')
    assert owner.post('/api/api-keys', headers=HEADERS, json={'name': 'Uji'}).status_code == 403
    upgrade(tid)
    result = owner.post('/api/api-keys', headers=HEADERS, json={'name': 'Uji'})
    assert result.status_code == 200
    key, prefix = result.json()['key'], result.json()['prefix']
    client = TestClient(app, headers={'Authorization': 'Bearer '+key, **HEADERS})
    assert client.get('/api/leads').status_code == 200
    assert client.get('/api/settings').status_code == 403
    assert client.get('/api/admin/tenants').status_code == 403
    assert owner.post('/api/api-keys/revoke', headers=HEADERS, json={'prefix': prefix}).status_code == 200
    assert client.get('/api/leads').status_code == 401


def test_downgrade_delayed_and_past_due_billing_stays_accessible(team):
    client, tid, _ = team
    upgrade(tid)
    future = (datetime.now(timezone.utc)+timedelta(days=10)).isoformat()
    with db.transaction(unscoped=True) as conn:
        conn.execute(db.subscriptions.update().where(db.subscriptions.c.tenant_id == tid).values(status='active', period_end=future))
    assert client.post('/api/billing/downgrade', headers=HEADERS, json={'plan': 'free'}).status_code == 200
    assert client.get('/api/billing/subscription').json()['plan_code'] == 'pro'
    old = (datetime.now(timezone.utc)-timedelta(days=10)).isoformat()
    with db.transaction(unscoped=True) as conn:
        conn.execute(db.subscriptions.update().where(db.subscriptions.c.tenant_id == tid).values(status='active', period_end=old, next_plan=None))
    billing = client.get('/api/billing/subscription')
    assert billing.status_code == 200 and billing.json()['status'] == 'past_due'
    assert client.post('/api/exports', headers=HEADERS, json={}).status_code == 402


def test_google_login():
    client = TestClient(app)
    # Check Google config endpoint
    url_res = client.get('/api/auth/google/url')
    assert url_res.status_code == 200

    # Test Google auth login / auto-provision
    res = client.post('/api/auth/google', json={
        'email': 'developer@pokoscrap.test',
        'name': 'Poko Developer',
        'google_id': 'google-uid-12345'
    })
    assert res.status_code == 200, res.text
    user = res.json()
    assert user['email'] == 'developer@pokoscrap.test'
    assert user['name'] == 'Poko Developer'
    assert user['tenant_id'] is not None

    # Authenticated request with session cookie
    me = client.get('/api/me')
    assert me.status_code == 200
    assert me.json()['email'] == 'developer@pokoscrap.test'
    # Default initial credits
    assert client.get('/api/credits/balance').json()['balance'] == 30


def test_mcp_protocol_and_tools(team):
    owner, tid, _ = team
    upgrade(tid)
    res = owner.post('/api/api-keys', headers=HEADERS, json={'name': 'MCP Key'})
    assert res.status_code == 200
    api_key = res.json()['key']

    # MCP client with Bearer token
    mcp_client = TestClient(app, headers={'Authorization': 'Bearer ' + api_key})

    # Test GET /api/mcp
    info = mcp_client.get('/api/mcp').json()
    assert info['status'] == 'ok'
    assert info['server'] == 'pokoscrap-mcp'

    # Test MCP initialize
    init_res = mcp_client.post('/api/mcp', json={
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'initialize',
        'params': {}
    }).json()
    assert init_res['result']['serverInfo']['name'] == 'pokoscrap-mcp'

    # Test MCP tools/list
    tools_res = mcp_client.post('/api/mcp', json={
        'jsonrpc': '2.0',
        'id': 2,
        'method': 'tools/list',
        'params': {}
    }).json()
    tools = {t['name'] for t in tools_res['result']['tools']}
    assert 'pokoscrap_search_leads' in tools
    assert 'pokoscrap_get_lead' in tools
    assert 'pokoscrap_create_scrape_job' in tools
    assert 'pokoscrap_get_stats' in tools

    # Test MCP tool call: pokoscrap_get_stats
    stats_call = mcp_client.post('/api/mcp', json={
        'jsonrpc': '2.0',
        'id': 3,
        'method': 'tools/call',
        'params': {
            'name': 'pokoscrap_get_stats',
            'arguments': {}
        }
    }).json()
    assert stats_call['result']['isError'] is False
    stats_data = json.loads(stats_call['result']['content'][0]['text'])
    assert stats_data['credit_balance'] == 30


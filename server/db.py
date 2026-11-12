import os
import uuid
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import JSON, Boolean, Column, ForeignKey, Index, Integer, MetaData, String, Table, Text, UniqueConstraint, create_engine, event
from sqlalchemy.sql import Select, Insert, Update, Delete

ROOT = Path(__file__).resolve().parents[1]
default_data = '/tmp/pokoscrap' if os.getenv('VERCEL') else str(ROOT / 'runtime')
RUNTIME = Path(os.getenv('POKO_DATA', default_data)).resolve()
RUNTIME.mkdir(parents=True, exist_ok=True)
URL = os.getenv('DATABASE_URL', f'sqlite:///{RUNTIME}/pokoscrap.db')
engine = create_engine(URL, connect_args={'check_same_thread': False, 'timeout': 30} if URL.startswith('sqlite') else {}, pool_pre_ping=True)
if URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_config(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA journal_mode=WAL')

meta = MetaData()
tenant_context = ContextVar('tenant_id', default=None)
organizations = Table('organizations', meta, Column('id', String, primary_key=True), Column('name', String), Column('owner_id', String), Column('status', String), Column('created_at', String))
memberships = Table('memberships', meta, Column('id', String, primary_key=True), Column('tenant_id', String, ForeignKey('organizations.id')), Column('user_id', String, ForeignKey('users.id')), Column('roles', JSON), Column('active', Boolean), UniqueConstraint('tenant_id', 'user_id'))
subscriptions = Table('subscriptions', meta, Column('tenant_id', String, ForeignKey('organizations.id'), primary_key=True), Column('plan_code', String), Column('status', String), Column('period_start', String), Column('period_end', String), Column('next_plan', String), Column('grace_until', String))
ledger = Table('credit_ledger', meta, Column('id', String, primary_key=True), Column('tenant_id', String, ForeignKey('organizations.id')), Column('type', String), Column('amount', Integer), Column('balance_after', Integer), Column('reference', String), Column('actor', String), Column('created_at', String), UniqueConstraint('tenant_id', 'reference'))
payments = Table('payment_transactions', meta, Column('id', String, primary_key=True), Column('tenant_id', String, ForeignKey('organizations.id')), Column('plan_code', String), Column('amount', Integer), Column('status', String), Column('reference', String, unique=True, nullable=True), Column('created_at', String), Column('checkout_url', Text), Column('payload', JSON))
payment_index = Table('payment_index', meta, Column('id', String, primary_key=True), Column('tenant_id', String))
tokens = Table('auth_tokens', meta, Column('id', String, primary_key=True), Column('user_id', String), Column('type', String), Column('expires', String), Column('payload', JSON))
platform_audit = Table('platform_audit', meta, Column('id', String, primary_key=True), Column('actor', String), Column('tenant_id', String), Column('type', String), Column('reason', Text), Column('created_at', String), Column('payload', JSON))
invitations = Table('invitations', meta, Column('id', String, primary_key=True), Column('tenant_id', String), Column('email', String), Column('role', String), Column('expires', String), Column('accepted', Boolean))
api_tokens = Table('api_tokens', meta, Column('id', String, primary_key=True), Column('tenant_id', String), Column('user_id', String), Column('name', String), Column('prefix', String), Column('created_at', String), Column('active', Boolean))
users = Table('users', meta, Column('id', String, primary_key=True), Column('name', String, nullable=False), Column('email', String, unique=True, nullable=False), Column('password_hash', String, nullable=False), Column('roles', JSON, nullable=False), Column('active', Boolean, default=True))
users.append_column(Column('verified', Boolean, default=False))
users.append_column(Column('platform_admin', Boolean, default=False))
users.append_column(Column('google_id', String, nullable=True))
users.append_column(Column('avatar_url', String, nullable=True))
sessions = Table('sessions', meta, Column('id', String, primary_key=True), Column('user_id', String, ForeignKey('users.id')), Column('last_seen', String), Column('expires', String))
sessions.append_column(Column('tenant_id', String))
jobs = Table('scrape_jobs', meta, Column('id', String, primary_key=True), Column('name', String), Column('status', String, index=True), Column('created_at', String), Column('created_by', String), Column('archived', Boolean, default=False), Column('payload', JSON, nullable=False))
leads = Table('leads', meta, Column('id', String, primary_key=True), Column('dedupe_key', String), Column('place_id', String, nullable=True), Column('business_name', String, index=True), Column('country_origin_code', String, index=True), Column('pipeline_status', String, index=True), Column('first_job_id', String, index=True), Column('first_seen_at', String, index=True), Column('payload', JSON, nullable=False))
seen = Table('lead_job_seen', meta, Column('job_id', String, primary_key=True), Column('row_hash', String, primary_key=True), Column('lead_id', String, ForeignKey('leads.id', ondelete='CASCADE')))
evidence = Table('lead_evidence', meta, Column('id', String, primary_key=True), Column('lead_id', String, ForeignKey('leads.id', ondelete='CASCADE'), index=True), Column('kind', String), Column('value', String, index=True), Column('status', String, index=True), Column('payload', JSON, nullable=False))
activities = Table('lead_activities', meta, Column('id', String, primary_key=True), Column('lead_id', String, ForeignKey('leads.id', ondelete='CASCADE'), index=True), Column('actor', String), Column('type', String), Column('created_at', String), Column('payload', JSON))
tasks = Table('enrichment_tasks', meta, Column('id', String, primary_key=True), Column('lead_id', String, ForeignKey('leads.id', ondelete='CASCADE'), index=True), Column('status', String, index=True), Column('payload', JSON))
exports = Table('exports', meta, Column('id', String, primary_key=True), Column('actor', String), Column('created_at', String), Column('count', Integer), Column('type', String), Column('filters', JSON))
segments = Table('segments', meta, Column('id', String, primary_key=True), Column('name', String), Column('created_by', String), Column('filters', JSON))
settings = Table('settings', meta, Column('id', String, primary_key=True), Column('payload', JSON))
audit = Table('audit_log', meta, Column('id', String, primary_key=True), Column('actor', String), Column('type', String), Column('created_at', String), Column('payload', JSON))
Index('ix_evidence_filter', evidence.c.kind, evidence.c.status, evidence.c.value, evidence.c.lead_id)
TENANT_TABLES = [jobs, leads, seen, evidence, activities, tasks, exports, segments, settings, audit, memberships, subscriptions, ledger, payments, invitations]
for table in TENANT_TABLES:
    if 'tenant_id' not in table.c:
        table.append_column(Column('tenant_id', String, nullable=False, index=True, primary_key=(table is settings)))
leads.append_constraint(UniqueConstraint('tenant_id', 'place_id'))
leads.append_constraint(UniqueConstraint('tenant_id', 'dedupe_key'))
meta.create_all(engine)


def uid():
    return str(uuid.uuid4())


@contextmanager
def transaction(unscoped=False):
    with engine.begin() as conn:
        if conn.dialect.name == 'postgresql':
            conn.exec_driver_sql("SET LOCAL statement_timeout = '15s'")
        yield TenantConnection(conn, unscoped)


class TenantConnection:
    """Enforce tenant scope for every root table operation, including raw-file lookups."""
    def __init__(self, conn, unscoped):
        self.conn, self.unscoped = conn, unscoped

    def execute(self, statement, *args, **kwargs):
        tenant = tenant_context.get()
        if self.conn.dialect.name == 'postgresql':
            self.conn.exec_driver_sql("SELECT set_config('app.tenant_id', %s, true)", (tenant or '',))
        if not self.unscoped:
            tables = statement.get_final_froms() if isinstance(statement, Select) else [statement.table] if isinstance(statement, (Insert, Update, Delete)) else []
            for table in tables:
                if table not in TENANT_TABLES:
                    continue
                if not tenant:
                    raise RuntimeError('Tenant context required.')
                if isinstance(statement, Insert):
                    statement = statement.values(tenant_id=tenant)
                else:
                    statement = statement.where(table.c.tenant_id == tenant)
        return self.conn.execute(statement, *args, **kwargs)

    def scalar(self, statement):
        return self.execute(statement).scalar()


def one(conn, table, condition):
    row = conn.execute(table.select().where(condition)).mappings().first()
    return dict(row) if row else None


def rows(conn, query):
    return [dict(r) for r in conn.execute(query).mappings()]

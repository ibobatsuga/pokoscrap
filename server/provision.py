"""Provision a new PostgreSQL database and its restricted web role."""
import os
from sqlalchemy import text
from . import db

protected = [t for t in db.TENANT_TABLES if t not in (db.memberships, db.invitations)]
with db.engine.begin() as conn:
    password = os.environ['WEB_DB_PASSWORD']
    # Only deployment-generated hex secrets are accepted by this bootstrap command.
    if not password.isalnum():
        raise ValueError('WEB_DB_PASSWORD must be alphanumeric.')
    exists = conn.exec_driver_sql("SELECT 1 FROM pg_roles WHERE rolname='pokoweb'").first()
    if not exists:
        conn.exec_driver_sql(f"CREATE ROLE pokoweb LOGIN PASSWORD '{password}' NOSUPERUSER NOBYPASSRLS")
    conn.exec_driver_sql('GRANT USAGE ON SCHEMA public TO pokoweb')
    conn.exec_driver_sql('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pokoweb')
    conn.exec_driver_sql('REVOKE UPDATE, DELETE ON credit_ledger FROM pokoweb')
    for table in protected:
        name = table.name
        conn.exec_driver_sql(f'ALTER TABLE "{name}" ENABLE ROW LEVEL SECURITY')
        conn.exec_driver_sql(f'ALTER TABLE "{name}" FORCE ROW LEVEL SECURITY')
        conn.exec_driver_sql(f'DROP POLICY IF EXISTS tenant_isolation ON "{name}"')
        conn.exec_driver_sql(f'''CREATE POLICY tenant_isolation ON "{name}"
            USING (tenant_id = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true))''')
    conn.exec_driver_sql('''CREATE OR REPLACE FUNCTION platform_tenant_summary(search_text text)
        RETURNS TABLE(id varchar, name varchar, owner_id varchar, status varchar, created_at varchar, plan_code varchar, balance bigint)
        LANGUAGE sql SECURITY DEFINER SET search_path = public AS $$
        SELECT o.id, o.name, o.owner_id, o.status, o.created_at, s.plan_code,
          COALESCE((SELECT SUM(l.amount) FROM credit_ledger l WHERE l.tenant_id=o.id),0)
        FROM organizations o JOIN subscriptions s ON s.tenant_id=o.id
        WHERE o.name ILIKE '%%' || search_text || '%%'; $$''')
    conn.exec_driver_sql('REVOKE ALL ON FUNCTION platform_tenant_summary(text) FROM PUBLIC')
    conn.exec_driver_sql('GRANT EXECUTE ON FUNCTION platform_tenant_summary(text) TO pokoweb')
print('Schema, tenant RLS, and restricted web role configured.')

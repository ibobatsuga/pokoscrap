import os
import sys
os.environ['POKO_WORKERS'] = '0'
from .app import worker_loop
from . import db
from .app import get_job, save_job, ingest
from .core import now
from .saas import settle_job
import subprocess

kind = sys.argv[1] if len(sys.argv) > 1 else 'jobs'
if kind == 'jobs':
    with db.transaction(unscoped=True) as conn:
        interrupted = db.rows(conn, db.jobs.select().where(db.jobs.c.status.in_(['running', 'ingesting'])))
    for row in interrupted:
        db.tenant_context.set(row['tenant_id'])
        subprocess.run(['docker', 'stop', '-t', '5', 'pokoscrap-'+row['id']], capture_output=True, timeout=15)
        path = db.RUNTIME / 'jobs' / row['id'] / 'results.csv'
        try:
            if path.exists():
                ingest(row['id'], path.read_bytes())
        except ValueError:
            pass
        with db.transaction() as conn:
            current = get_job(conn, row['id'])
            settle_job(conn, row['id'], current['payload'].get('spent_credits', 0), 'Pemulihan worker')
            save_job(conn, row['id'], status='failed', error='Worker terhenti. Hasil parsial disimpan; jalankan ulang untuk melanjutkan.', finished_at=now())
else:
    with db.transaction(unscoped=True) as conn:
        conn.execute(db.tasks.update().where(db.tasks.c.status == 'fetching').values(status='queued'))

worker_loop(kind)

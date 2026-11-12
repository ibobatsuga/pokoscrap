"""Create local-only runtime settings without printing secrets."""
import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / '.env'
if target.exists():
    raise SystemExit('.env sudah ada; konfigurasi tidak ditimpa.')
socket_path = '/var/run/docker.sock'
target.write_text(f'''POSTGRES_PASSWORD={secrets.token_hex(24)}
WEB_DB_PASSWORD={secrets.token_hex(24)}
HOST_DATA_PATH={root / 'runtime'}
DOCKER_SOCKET={socket_path}
BASE_URL=http://127.0.0.1:8877
COOKIE_SECURE=0
BILLING_BETA_ENABLED=0
TRIPAY_API_KEY=
TRIPAY_PRIVATE_KEY=
TRIPAY_MERCHANT_CODE=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@pokoscrap.example
''')
target.chmod(0o600)
(root / 'runtime').mkdir(exist_ok=True)
(root / 'backups').mkdir(exist_ok=True)
print('Konfigurasi lokal dibuat. Jalankan docker compose up -d --build.')

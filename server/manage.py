"""Administrative bootstrap. Run only from a trusted server terminal."""
import getpass
import re
from . import db
from .app import password_hash
from .saas import create_org


def main():
    name = input('Nama admin: ').strip()
    email = input('Email admin: ').strip().lower()
    org_name = input('Nama organisasi: ').strip()
    password = getpass.getpass('Kata sandi (minimal 12 karakter): ')
    if not name or not org_name or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(password) < 12:
        raise SystemExit('Nama, organisasi, email valid, dan kata sandi minimal 12 karakter wajib diisi.')
    with db.transaction(unscoped=True) as conn:
        if db.one(conn, db.users, db.users.c.email == email):
            raise SystemExit('Email sudah terdaftar. Akun tidak ditimpa.')
        user = dict(id=db.uid(), name=name, email=email, password_hash=password_hash(password), roles=[], active=True, verified=True, platform_admin=True)
        conn.execute(db.users.insert().values(**user))
        create_org(conn, user, org_name)
    print('Admin platform dan organisasi Free dibuat. Silakan masuk dari dashboard.')


if __name__ == '__main__':
    main()

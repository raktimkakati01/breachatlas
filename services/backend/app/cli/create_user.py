"""Bootstrap an admin-area user.

The password never appears in the repo or in argv: it is read from the
BREACHATLAS_ADMIN_PASSWORD environment variable, or prompted (hidden) if unset.

    python -m app.cli.create_user --email you@example.com --role admin
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from app.crud.user import create_user, get_user_by_email
from app.db.session import SessionLocal
from app.models.enums import UserRole


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a BreachAtlas admin-area user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=[r.value for r in UserRole], default="admin")
    args = parser.parse_args(argv)

    password = os.environ.get("BREACHATLAS_ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Password (min 12 chars): ")
    if len(password) < 12:
        print("ERROR: password must be at least 12 characters.", file=sys.stderr)  # noqa: T201
        return 2

    db = SessionLocal()
    try:
        if get_user_by_email(db, args.email.lower()) is not None:
            print(f"ERROR: user {args.email} already exists.", file=sys.stderr)  # noqa: T201
            return 1
        user = create_user(db, email=args.email, password=password, role=UserRole(args.role))
        print(f"Created {user.role.value}: {user.email}")  # noqa: T201
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

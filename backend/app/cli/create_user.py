import argparse
import getpass

from sqlalchemy import select

from app.db.session import SessionLocal
from app.domains.auth.models import User
from app.domains.auth.service import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a local Carta Arcanum user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--password")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    with SessionLocal() as db:
        email = args.email.lower()
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, display_name=args.display_name)
            db.add(user)
        user.display_name = args.display_name
        user.password_hash = hash_password(password)
        user.is_active = True
        db.commit()
        print(f"User ready: {user.email}")


if __name__ == "__main__":
    main()

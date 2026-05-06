import argparse
import getpass

from sqlalchemy import select

from app.db.session import SessionLocal
from app.domains.auth.models import Denizen, DenizenRole
from app.domains.auth.service import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a local Carta Arcanum denizen.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--role", choices=[role.value for role in DenizenRole], default="read_only")
    parser.add_argument("--religion")
    parser.add_argument("--primary-house-id", type=int)
    parser.add_argument("--primary-kingdom-id", type=int)
    parser.add_argument("--password")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    with SessionLocal() as db:
        email = args.email.lower()
        denizen = db.scalar(select(Denizen).where(Denizen.email == email))
        if denizen is None:
            denizen = Denizen(email=email, display_name=args.display_name)
            db.add(denizen)
        denizen.display_name = args.display_name
        denizen.role = DenizenRole(args.role)
        denizen.religion = args.religion
        denizen.primary_house_id = args.primary_house_id
        denizen.primary_kingdom_id = args.primary_kingdom_id
        denizen.password_hash = hash_password(password)
        denizen.is_active = True
        db.commit()
        print(f"Denizen ready: {denizen.email}")


if __name__ == "__main__":
    main()

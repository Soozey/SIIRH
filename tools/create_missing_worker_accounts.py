from __future__ import annotations

import re
import secrets
import string
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import models  # noqa: E402
from app.config.config import SessionLocal, create_tables  # noqa: E402
from app.security import hash_password, seed_iam_catalog  # noqa: E402


def slug(value: str, fallback: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", ".", normalized).strip(".").lower()
    return normalized or fallback


def temporary_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Tmp-" + "".join(secrets.choice(alphabet) for _ in range(16)) + "8"


def login_for_worker(worker: models.Worker, used: set[str]) -> str:
    candidates: list[str] = []
    email = (worker.email or "").strip().lower()
    if "@" in email and not email.endswith("@example.com"):
        candidates.append(email)
    first = slug(worker.prenom or "", "agent")
    last = slug(worker.nom or "", f"worker{worker.id}")
    matricule = slug(worker.matricule or "", f"w{worker.id}")
    candidates.extend(
        [
            f"{first}.{last}@siirh.local",
            f"{matricule}@siirh.local",
            f"{matricule}.{last}@siirh.local",
            f"worker.{worker.id}@siirh.local",
        ]
    )
    for candidate in candidates:
        if candidate not in used:
            return candidate
    return f"worker.{worker.id}.{secrets.token_hex(3)}@siirh.local"


def main() -> None:
    create_tables()
    db = SessionLocal()
    created: list[tuple[str, str, str, str, str, str]] = []
    existing_count = 0
    try:
        seed_iam_catalog(db)
        used = {row[0] for row in db.query(models.AppUser.username).all()}
        workers = db.query(models.Worker).filter(models.Worker.deleted_at.is_(None)).order_by(models.Worker.id.asc()).all()
        for worker in workers:
            existing = db.query(models.AppUser.id).filter(models.AppUser.worker_id == worker.id).first()
            if existing is not None:
                existing_count += 1
                continue

            username = login_for_worker(worker, used)
            used.add(username)
            password = temporary_password()
            full_name = f"{worker.prenom or ''} {worker.nom or ''}".strip() or f"Travailleur {worker.matricule or worker.id}"
            user = models.AppUser(
                username=username,
                full_name=full_name,
                password_hash=hash_password(password),
                role_code="employee",
                is_active=True,
                account_status="PASSWORD_RESET_REQUIRED",
                must_change_password=True,
                employer_id=worker.employer_id,
                worker_id=worker.id,
            )
            db.add(user)
            db.flush()
            db.add(
                models.IamUserRole(
                    user_id=user.id,
                    role_code="employee",
                    employer_id=worker.employer_id,
                    worker_id=worker.id,
                    is_active=True,
                )
            )
            created.append((full_name, username, password, "PASSWORD_RESET_REQUIRED", "employee", "oui"))
        db.commit()
    finally:
        db.close()

    print(f"existing_worker_accounts={existing_count}")
    print(f"created_worker_accounts={len(created)}")
    print("AGENT | LOGIN | TEMP_PASSWORD | STATUS | ROLE | MUST_CHANGE_PASSWORD")
    for row in created:
        print(" | ".join(row))


if __name__ == "__main__":
    main()

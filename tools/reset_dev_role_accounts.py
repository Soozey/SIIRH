from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.config import SessionLocal, create_tables  # noqa: E402
from app import models  # noqa: E402
from app.security import hash_password, seed_iam_catalog  # noqa: E402


@dataclass(frozen=True)
class DevAccount:
    label: str
    username: str
    role_code: str
    access: str
    needs_employer: bool = False
    needs_worker: bool = False


DEV_ACCOUNTS = [
    DevAccount("Administrateur système", "admin.systeme@siirh.local", "system_admin", "IAM, paramètres, journalisation"),
    DevAccount("Administrateur employeur", "admin.employeur@siirh.local", "employer_admin", "Dossiers, messagerie, travailleurs", True),
    DevAccount("Responsable RH", "responsable.rh@siirh.local", "hr_manager", "Travailleurs, contrats, dossiers", True),
    DevAccount("Employé", "employe.test@siirh.local", "employee", "Doléances, messages, suivi", True, True),
    DevAccount("Inspecteur du travail", "inspecteur.travail@siirh.local", "labor_inspector", "Inspection, conciliation, PV", True),
    DevAccount("Inspecteur principal", "inspecteur.principal@siirh.local", "labor_inspector_supervisor", "Inspection, PV, pilotage", True),
    DevAccount("Délégué du personnel", "delegue.personnel@siirh.local", "staff_delegate", "Doléances, consultations, messages", True, True),
    DevAccount("Comité d'entreprise", "comite.entreprise@siirh.local", "works_council_member", "Consultations, PV, registre", True, True),
    DevAccount("Juge", "juge.test@siirh.local", "judge_readonly", "Lecture, dossiers, PV"),
    DevAccount("Greffier", "greffier.test@siirh.local", "court_clerk_readonly", "Pièces, classement, PV"),
    DevAccount("Auditeur", "auditeur.test@siirh.local", "auditor_readonly", "Audit, reporting, conformité", True),
]


def temporary_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Dev-" + "".join(secrets.choice(alphabet) for _ in range(14)) + "7"


def main() -> None:
    create_tables()
    db = SessionLocal()
    try:
        seed_iam_catalog(db)
        employer = db.query(models.Employer).order_by(models.Employer.id.asc()).first()
        worker = db.query(models.Worker).order_by(models.Worker.id.asc()).first()
        rows: list[tuple[str, str, str, str, str]] = []

        for account in DEV_ACCOUNTS:
            password = temporary_password()
            user = db.query(models.AppUser).filter(models.AppUser.username == account.username).first()
            if user is None:
                user = models.AppUser(username=account.username)
                db.add(user)

            user.full_name = account.label
            user.role_code = account.role_code
            user.password_hash = hash_password(password)
            user.is_active = True
            user.account_status = "PASSWORD_RESET_REQUIRED"
            user.must_change_password = True
            user.employer_id = employer.id if account.needs_employer and employer is not None else None
            user.worker_id = worker.id if account.needs_worker and worker is not None else None
            rows.append((account.label, account.username, password, user.account_status, account.access))

        db.commit()
    finally:
        db.close()

    print("ROLE | LOGIN | TEMP_PASSWORD | STATUS | ACCESS")
    for row in rows:
        print(" | ".join(row))


if __name__ == "__main__":
    main()

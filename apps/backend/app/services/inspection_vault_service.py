import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from .employee_portal_service import json_dump
from .file_storage import build_static_path, sanitize_filename_part, save_upload_file


def next_inspection_document_version(db: Session, document_id: int) -> int:
    current = (
        db.query(func.max(models.InspectionDocumentVersion.version_number))
        .filter(models.InspectionDocumentVersion.document_id == document_id)
        .scalar()
    )
    return int(current or 0) + 1


def store_inspection_upload(*, upload, case_number: str, document_id: int, version_number: int) -> dict[str, Any]:
    original_name = Path(upload.filename or "document").name
    safe_name = sanitize_filename_part(original_name)
    case_token = sanitize_filename_part(case_number)
    storage_name = (
        f"inspection_vault/{case_token}/document_{document_id}/"
        f"v{version_number:03d}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{safe_name}"
    )

    payload = upload.file.read()
    checksum = hashlib.sha256(payload).hexdigest()
    save_upload_file(io.BytesIO(payload), filename=storage_name)

    return {
        "file_name": safe_name,
        "original_name": original_name,
        "storage_path": storage_name,
        "static_url": build_static_path(storage_name),
        "content_type": upload.content_type,
        "file_size": len(payload),
        "checksum": checksum,
    }


def log_inspection_document_access(
    db: Session,
    *,
    document: models.InspectionDocument,
    user: models.AppUser | None,
    action: str,
    version_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> models.InspectionDocumentAccessLog:
    entry = models.InspectionDocumentAccessLog(
        document_id=document.id,
        version_id=version_id,
        case_id=document.case_id,
        user_id=user.id if user else None,
        action=action,
        metadata_json=json_dump(metadata or {}),
    )
    db.add(entry)
    return entry



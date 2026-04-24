from __future__ import annotations

import io
import json
import re
import hashlib
import zipfile
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import settings
from .system_data_import_service import MODULE_ALIASES, MODULE_IMPORT_ORDER


TOKEN_PATTERN = re.compile(r"[^a-z0-9]+")
EXPORT_FORMAT_VERSION = "SIRH_PAIE_JSON_EXPORT_v2"
SCHEMA_VERSION = "2026.04"

DOCUMENT_MODULES = {"custom_contracts", "document_templates"}

MODULE_BUNDLES: dict[str, tuple[str, ...]] = {
    "employers": ("type_regimes", "employers"),
    "workers": ("workers", "worker_primes", "worker_prime_links", "worker_position_history"),
    "payroll": ("payroll_runs", "payvars", "payroll_hs_hm", "payroll_primes"),
    "hs": ("hs_calculations",),
    "absences": ("absences", "leaves", "permissions"),
    "organisation": ("organizational_units", "organizational_nodes", "calendar_days"),
    "organization": ("organizational_units", "organizational_nodes", "calendar_days"),
    "documents": ("custom_contracts", "document_templates"),
    "recruitment": ("recruitment_candidates", "recruitment_job_postings"),
    "talents": ("talent_skills", "talent_employee_skills", "talent_trainings", "talent_training_sessions"),
    "sst": ("sst_incidents",),
}

EXPORT_FILE_GROUPS: dict[str, tuple[str, ...]] = {
    "employers": ("type_regimes", "employers"),
    "workers": ("workers", "worker_primes", "worker_prime_links", "worker_position_history"),
    "payroll": ("payroll_runs", "payvars", "payroll_hs_hm", "payroll_primes"),
    "hs": ("hs_calculations",),
    "absences": ("absences", "leaves", "permissions"),
    "organisation": ("organizational_units", "organizational_nodes", "calendar_days"),
    "primes": ("primes",),
    "documents": ("custom_contracts", "document_templates"),
    "recruitment": ("recruitment_candidates", "recruitment_job_postings"),
    "talents": ("talent_skills", "talent_employee_skills", "talent_trainings", "talent_training_sessions"),
    "sst": ("sst_incidents",),
}

MODULE_MODEL_MAP: dict[str, Any] = {
    "type_regimes": models.TypeRegime,
    "employers": models.Employer,
    "organizational_units": models.OrganizationalUnit,
    "organizational_nodes": models.OrganizationalNode,
    "workers": models.Worker,
    "worker_position_history": models.WorkerPositionHistory,
    "calendar_days": models.CalendarDay,
    "primes": models.Prime,
    "worker_primes": models.WorkerPrime,
    "worker_prime_links": models.WorkerPrimeLink,
    "payroll_runs": models.PayrollRun,
    "hs_calculations": models.HSCalculationHS,
    "payvars": models.PayVar,
    "payroll_hs_hm": models.PayrollHsHm,
    "payroll_primes": models.PayrollPrime,
    "absences": models.Absence,
    "leaves": models.Leave,
    "permissions": models.Permission,
    "custom_contracts": models.CustomContract,
    "document_templates": models.DocumentTemplate,
    "recruitment_candidates": models.RecruitmentCandidate,
    "recruitment_job_postings": models.RecruitmentJobPosting,
    "talent_skills": models.TalentSkill,
    "talent_employee_skills": models.TalentEmployeeSkill,
    "talent_trainings": models.TalentTraining,
    "talent_training_sessions": models.TalentTrainingSession,
    "sst_incidents": models.SstIncident,
}

WORKER_SCOPED_COLUMN_MAP: dict[str, Any] = {
    "worker_position_history": models.WorkerPositionHistory.worker_id,
    "worker_primes": models.WorkerPrime.worker_id,
    "worker_prime_links": models.WorkerPrimeLink.worker_id,
    "payvars": models.PayVar.worker_id,
    "payroll_primes": models.PayrollPrime.worker_id,
    "absences": models.Absence.worker_id,
    "leaves": models.Leave.worker_id,
    "permissions": models.Permission.worker_id,
    "talent_employee_skills": models.TalentEmployeeSkill.worker_id,
}


def preview_system_data_export(
    *,
    db: Session,
    options: schemas.SystemExportOptions,
) -> schemas.SystemDataExportPreview:
    requested_modules, unsupported = _resolve_requested_modules(options.selected_modules)
    warnings: list[str] = []
    if unsupported:
        warnings.extend([f"Module non exportable ignore: {item}" for item in unsupported])

    detected_records: dict[str, int] = {}
    for module_name in requested_modules:
        query = _build_module_query(
            db=db,
            module_name=module_name,
            employer_id=options.employer_id,
            include_inactive=options.include_inactive,
            for_count=True,
        )
        detected_records[module_name] = int(query.count())

    if DOCUMENT_MODULES.intersection(requested_modules) and not options.include_document_content:
        warnings.append(
            "Contenu des templates documentaires desactive (metadonnees exportees, contenu vide)."
        )

    manifest = _build_manifest_summary(
        requested_modules=requested_modules,
        detected_records=detected_records,
        warnings=warnings,
    )
    return schemas.SystemDataExportPreview(
        generated_at=datetime.utcnow(),
        options=options,
        manifest=manifest,
        total_records=sum(detected_records.values()),
        warnings=warnings,
    )


def build_system_data_export_zip(
    *,
    db: Session,
    options: schemas.SystemExportOptions,
) -> tuple[bytes, str, schemas.SystemDataExportPreview]:
    preview = preview_system_data_export(db=db, options=options)
    modules = preview.manifest.modules_exported
    module_rows: dict[str, list[dict[str, Any]]] = {}
    warnings = list(preview.warnings)

    for module_name in modules:
        query = _build_module_query(
            db=db,
            module_name=module_name,
            employer_id=options.employer_id,
            include_inactive=options.include_inactive,
            for_count=False,
        )
        rows = [_serialize_model_row(item) for item in query.all()]
        if module_name in DOCUMENT_MODULES and not options.include_document_content:
            stripped = 0
            for row in rows:
                if "content" in row and row["content"] not in (None, ""):
                    row["content"] = None
                    stripped += 1
            if stripped > 0:
                warnings.append(
                    f"Module {module_name}: {stripped} contenu(s) documentaire(s) neutralise(s)."
                )
        module_rows[module_name] = rows

    module_counts = {module_name: len(rows) for module_name, rows in module_rows.items()}
    manifest_payload = _build_manifest_payload(
        options=options,
        module_rows=module_rows,
        warnings=warnings,
    )

    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "_manifest.json",
            json.dumps(manifest_payload, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        grouped_modules: set[str] = set()
        for filename_key, grouped_list in EXPORT_FILE_GROUPS.items():
            subset = {name: module_rows[name] for name in grouped_list if name in module_rows}
            if not subset:
                continue
            grouped_modules.update(subset.keys())
            payload = {name: rows for name, rows in subset.items()}
            payload["count"] = {name: len(rows) for name, rows in subset.items()}
            archive.writestr(
                f"{filename_key}.json",
                json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            )

        for module_name, rows in module_rows.items():
            if module_name in grouped_modules:
                continue
            payload = {"rows": rows, "count": {module_name: len(rows)}}
            archive.writestr(
                f"{module_name}.json",
                json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            )

        archive.writestr(
            "README.txt",
            (
                "SIRH Paie - Export General des donnees\n"
                "Ce package peut etre importe via la page Import Database & Migration.\n"
                "Le manifeste (_manifest.json) contient les modules et comptes exportes.\n"
            ).encode("utf-8"),
        )

    archive_bytes.seek(0)
    exported_at = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    scope_suffix = f"_employer_{options.employer_id}" if options.employer_id else "_complet"
    filename = f"sirh_paie_export{scope_suffix}_{exported_at}.zip"

    preview.manifest.detected_records = module_counts
    preview.total_records = sum(module_counts.values())
    preview.warnings = warnings
    preview.manifest.compatibility_warnings = warnings

    return archive_bytes.getvalue(), filename, preview


def build_system_data_update_package_zip(
    *,
    db: Session,
    options: schemas.SystemExportOptions,
) -> tuple[bytes, str, schemas.SystemDataExportPreview]:
    base_bytes, base_filename, preview = build_system_data_export_zip(db=db, options=options)

    archive_in = io.BytesIO(base_bytes)
    archive_out = io.BytesIO()
    with zipfile.ZipFile(archive_in, mode="r") as source_archive:
        manifest_raw = source_archive.read("_manifest.json")
        manifest_payload = json.loads(manifest_raw.decode("utf-8"))

        module_hashes: dict[str, str] = {}
        for name in source_archive.namelist():
            if not name.lower().endswith(".json"):
                continue
            if name == "_manifest.json":
                continue
            module_hashes[name] = hashlib.sha256(source_archive.read(name)).hexdigest()

        export_metadata = manifest_payload.setdefault("export_metadata", {})
        export_metadata["package_type"] = "migration_update"
        export_metadata["import_endpoint"] = "/system-data-import"
        export_metadata["source_role"] = "source_system"
        export_metadata["safe_merge_recommended_options"] = {
            "update_existing": True,
            "skip_exact_duplicates": True,
            "continue_on_error": True,
            "strict_mode": False,
        }
        export_metadata["notes"] = (
            "Package de mise a jour donnees compatible import fusion safe."
        )

        manifest_payload["integrity"] = {
            "algorithm": "sha256",
            "module_file_hashes": module_hashes,
        }

        with zipfile.ZipFile(archive_out, mode="w", compression=zipfile.ZIP_DEFLATED) as target_archive:
            for name in source_archive.namelist():
                if name == "_manifest.json":
                    target_archive.writestr(
                        "_manifest.json",
                        json.dumps(manifest_payload, ensure_ascii=False, indent=2).encode("utf-8"),
                    )
                    continue
                target_archive.writestr(name, source_archive.read(name))

    archive_out.seek(0)
    filename = base_filename.replace("sirh_paie_export", "sirh_paie_update_package", 1)
    return archive_out.getvalue(), filename, preview


def _build_manifest_payload(
    *,
    options: schemas.SystemExportOptions,
    module_rows: dict[str, list[dict[str, Any]]],
    warnings: list[str],
) -> dict[str, Any]:
    modules_payload: dict[str, Any] = {}
    for filename_key, grouped_list in EXPORT_FILE_GROUPS.items():
        subset = {name: module_rows[name] for name in grouped_list if name in module_rows}
        if not subset:
            continue
        counts = {name: len(rows) for name, rows in subset.items()}
        modules_payload[filename_key] = {
            "status": "ok",
            "record_counts": counts,
            "total": sum(counts.values()),
        }

    emitted = {name for groups in EXPORT_FILE_GROUPS.values() for name in groups}
    for module_name, rows in module_rows.items():
        if module_name in emitted:
            continue
        modules_payload[module_name] = {
            "status": "ok",
            "record_counts": {module_name: len(rows)},
            "total": len(rows),
        }

    app_version = getattr(settings, "APP_VERSION", None)
    return {
        "export_metadata": {
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "app_version": app_version or "1.0.0",
            "schema_version": SCHEMA_VERSION,
            "modules_requested": options.selected_modules,
            "modules_exported": sorted(module_rows.keys()),
            "employer_filter": options.employer_id,
            "format": EXPORT_FORMAT_VERSION,
            "encoding": "UTF-8",
            "include_inactive": options.include_inactive,
            "include_document_content": options.include_document_content,
        },
        "modules": modules_payload,
        "warnings": warnings,
        "total_records": sum(len(rows) for rows in module_rows.values()),
    }


def _resolve_requested_modules(selected_modules: list[str]) -> tuple[list[str], list[str]]:
    if not selected_modules:
        ordered = [module_name for module_name in MODULE_IMPORT_ORDER if module_name in MODULE_MODEL_MAP]
        extras = sorted(name for name in MODULE_MODEL_MAP.keys() if name not in set(ordered))
        return ordered + extras, []

    expanded: set[str] = set()
    unsupported: list[str] = []
    for raw in selected_modules:
        normalized = _normalize_module_name(raw)
        bundle = MODULE_BUNDLES.get(normalized)
        if bundle:
            expanded.update(bundle)
            continue
        if normalized in MODULE_MODEL_MAP:
            expanded.add(normalized)
            continue
        unsupported.append(raw)

    ordered = [module_name for module_name in MODULE_IMPORT_ORDER if module_name in expanded]
    extras = sorted(name for name in expanded if name not in set(ordered))
    return ordered + extras, unsupported


def _build_manifest_summary(
    *,
    requested_modules: list[str],
    detected_records: dict[str, int],
    warnings: list[str],
) -> schemas.SystemExportManifestSummary:
    app_version = getattr(settings, "APP_VERSION", None)
    return schemas.SystemExportManifestSummary(
        source_system="SIIRH_PAIE",
        package_version=app_version or "1.0.0",
        export_version=SCHEMA_VERSION,
        modules_requested=requested_modules,
        modules_exported=requested_modules,
        detected_records=detected_records,
        compatibility_warnings=warnings,
    )


def _build_module_query(
    *,
    db: Session,
    module_name: str,
    employer_id: Optional[int],
    include_inactive: bool,
    for_count: bool,
):
    model = MODULE_MODEL_MAP[module_name]
    query = db.query(model)

    if not include_inactive and hasattr(model, "is_active"):
        query = query.filter(getattr(model, "is_active").is_(True))

    if employer_id is not None:
        if hasattr(model, "employer_id"):
            query = query.filter(getattr(model, "employer_id") == employer_id)
        elif module_name in WORKER_SCOPED_COLUMN_MAP:
            worker_fk = WORKER_SCOPED_COLUMN_MAP[module_name]
            query = query.join(models.Worker, worker_fk == models.Worker.id).filter(
                models.Worker.employer_id == employer_id
            )
        elif module_name == "hs_calculations":
            query = query.join(
                models.Worker, models.HSCalculationHS.worker_id_HS == models.Worker.id
            ).filter(models.Worker.employer_id == employer_id)
        elif module_name == "payroll_hs_hm":
            query = query.join(
                models.PayrollRun, models.PayrollHsHm.payroll_run_id == models.PayrollRun.id
            ).filter(models.PayrollRun.employer_id == employer_id)
        elif module_name == "talent_training_sessions":
            query = query.join(
                models.TalentTraining,
                models.TalentTrainingSession.training_id == models.TalentTraining.id,
            ).filter(models.TalentTraining.employer_id == employer_id)

    if for_count:
        return query

    primary_keys = list(model.__table__.primary_key.columns)
    for column in primary_keys:
        query = query.order_by(column.asc())
    return query


def _serialize_model_row(row: Any) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for column in row.__table__.columns:
        data[column.name] = _serialize_value(getattr(row, column.name))
    return data


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _normalize_module_name(value: str) -> str:
    token = TOKEN_PATTERN.sub("_", (value or "").lower()).strip("_")
    token = token.removesuffix("_json").removesuffix("_csv")
    return MODULE_ALIASES.get(token, token)

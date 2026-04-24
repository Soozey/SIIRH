from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any, Callable, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas


MAX_PACKAGE_SIZE_BYTES = 100 * 1024 * 1024
PERIOD_PATTERN = re.compile(r"^\d{4}-\d{2}$")
TOKEN_PATTERN = re.compile(r"[^a-z0-9]+")

MODULE_ALIASES = {
    "type_regimes": "type_regimes",
    "type_regime": "type_regimes",
    "regimes": "type_regimes",
    "employers": "employers",
    "employer": "employers",
    "companies": "employers",
    "workers": "workers",
    "worker": "workers",
    "employees": "workers",
    "employee": "workers",
    "salaries": "workers",
    "salary_workers": "workers",
    "worker_position_history": "worker_position_history",
    "worker_positions": "worker_position_history",
    "position_history": "worker_position_history",
    "organizational_units": "organizational_units",
    "organizational_unit": "organizational_units",
    "organization_units": "organizational_units",
    "organization_unit": "organizational_units",
    "organizational_nodes": "organizational_nodes",
    "organizational_node": "organizational_nodes",
    "organization_nodes": "organizational_nodes",
    "organization_node": "organizational_nodes",
    "primes": "primes",
    "prime": "primes",
    "worker_primes": "worker_primes",
    "worker_prime": "worker_primes",
    "worker_prime_links": "worker_prime_links",
    "worker_prime_link": "worker_prime_links",
    "payvars": "payvars",
    "payvar": "payvars",
    "payroll_variables": "payvars",
    "payroll_variable": "payvars",
    "payroll_runs": "payroll_runs",
    "payroll_run": "payroll_runs",
    "hs_calculations": "hs_calculations",
    "hs_calculation": "hs_calculations",
    "payroll_hs_hm": "payroll_hs_hm",
    "payroll_hshm": "payroll_hs_hm",
    "payroll_primes": "payroll_primes",
    "payroll_prime": "payroll_primes",
    "absences": "absences",
    "absence": "absences",
    "leaves": "leaves",
    "leave": "leaves",
    "permissions": "permissions",
    "permission": "permissions",
    "custom_contracts": "custom_contracts",
    "custom_contract": "custom_contracts",
    "contracts": "custom_contracts",
    "document_templates": "document_templates",
    "document_template": "document_templates",
    "calendar_days": "calendar_days",
    "calendar_day": "calendar_days",
    "recruitment_candidates": "recruitment_candidates",
    "recruitment_candidate": "recruitment_candidates",
    "candidates": "recruitment_candidates",
    "recruitment_job_postings": "recruitment_job_postings",
    "recruitment_jobs": "recruitment_job_postings",
    "job_postings": "recruitment_job_postings",
    "jobs": "recruitment_job_postings",
    "talent_skills": "talent_skills",
    "talent_skill": "talent_skills",
    "skills": "talent_skills",
    "talent_employee_skills": "talent_employee_skills",
    "talent_employee_skill": "talent_employee_skills",
    "employee_skills": "talent_employee_skills",
    "talent_trainings": "talent_trainings",
    "talent_training": "talent_trainings",
    "trainings": "talent_trainings",
    "talent_training_sessions": "talent_training_sessions",
    "talent_training_session": "talent_training_sessions",
    "training_sessions": "talent_training_sessions",
    "sst_incidents": "sst_incidents",
    "sst_incident": "sst_incidents",
    "incidents": "sst_incidents",
    "timesheets": "payroll_hs_hm",
    "time_entries": "payroll_hs_hm",
}

MODULE_IMPORT_ORDER = [
    "type_regimes",
    "employers",
    "organizational_units",
    "organizational_nodes",
    "workers",
    "worker_position_history",
    "calendar_days",
    "primes",
    "worker_primes",
    "worker_prime_links",
    "payroll_runs",
    "hs_calculations",
    "payvars",
    "payroll_hs_hm",
    "payroll_primes",
    "absences",
    "leaves",
    "permissions",
    "custom_contracts",
    "document_templates",
    "recruitment_candidates",
    "recruitment_job_postings",
    "talent_skills",
    "talent_employee_skills",
    "talent_trainings",
    "talent_training_sessions",
    "sst_incidents",
]

MODULE_BUNDLES = {
    "employers": {"type_regimes", "employers"},
    "workers": {"workers", "worker_primes", "worker_prime_links", "worker_position_history"},
    "payroll": {"payroll_runs", "payvars", "payroll_hs_hm", "payroll_primes"},
    "hs": {"hs_calculations"},
    "absences": {"absences", "leaves", "permissions"},
    "organisation": {"organizational_units", "organizational_nodes", "calendar_days"},
    "organization": {"organizational_units", "organizational_nodes", "calendar_days"},
    "documents": {"custom_contracts", "document_templates"},
    "recruitment": {"recruitment_candidates", "recruitment_job_postings"},
    "talents": {"talent_skills", "talent_employee_skills", "talent_trainings", "talent_training_sessions"},
    "sst": {"sst_incidents"},
}

BASE_ROW_FIELDS = {
    "id",
    "source_id",
    "legacy_id",
    "external_id",
    "created_at",
    "updated_at",
}

PAYVAR_NUMERIC_FIELDS = (
    "hsni_130",
    "hsi_130",
    "hsni_150",
    "hsi_150",
    "hmn_30",
    "absences_non_remu",
    "abs_non_remu_j",
    "abs_maladie_j",
    "mise_a_pied_j",
    "abs_non_remu_h",
    "prime_fixe",
    "prime_variable",
    "prime1",
    "prime2",
    "prime3",
    "prime4",
    "prime5",
    "prime6",
    "prime7",
    "prime8",
    "prime9",
    "prime10",
    "prime_13",
    "avantage_vehicule",
    "avantage_logement",
    "avantage_telephone",
    "avantage_autres",
    "alloc_familiale",
    "avance_salaire",
    "avance_quinzaine",
    "avance_speciale_rembfixe",
    "autre_ded1",
    "autre_ded2",
    "autre_ded3",
    "autre_ded4",
    "autres_gains",
    "autres_retenues",
)

PAYROLL_HS_HM_NUMERIC_FIELDS = (
    "hsni_130_heures",
    "hsi_130_heures",
    "hsni_150_heures",
    "hsi_150_heures",
    "hmnh_heures",
    "hmno_heures",
    "hmd_heures",
    "hmjf_heures",
    "hsni_130_montant",
    "hsi_130_montant",
    "hsni_150_montant",
    "hsi_150_montant",
    "hmnh_montant",
    "hmno_montant",
    "hmd_montant",
    "hmjf_montant",
)

ABSENCE_NUMERIC_FIELDS = (
    "ABSM_J",
    "ABSM_H",
    "ABSNR_J",
    "ABSNR_H",
    "ABSMP",
    "ABS1_J",
    "ABS1_H",
    "ABS2_J",
    "ABS2_H",
)

SUPPORTED_PACKAGE_EXTENSIONS = {".zip", ".json", ".dump", ".txt"}


@dataclass
class ParsedPackage:
    manifest: dict[str, Any] = field(default_factory=dict)
    modules: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ModuleAccumulator:
    module: str
    expected_records: Optional[int]
    detected_records: int
    processed_rows: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    conflicts: int = 0
    issues: list[dict[str, Any]] = field(default_factory=list)
    unmapped_fields: set[str] = field(default_factory=set)

    def add_issue(
        self,
        *,
        row_number: int,
        code: str,
        message: str,
        column: Optional[str] = None,
        value: Optional[Any] = None,
    ) -> None:
        self.issues.append(
            {
                "row_number": row_number,
                "column": column,
                "code": code,
                "message": message,
                "value": None if value is None else str(value),
            }
        )

    def to_schema(self) -> schemas.SystemImportModuleReport:
        return schemas.SystemImportModuleReport(
            module=self.module,
            expected_records=self.expected_records,
            detected_records=self.detected_records,
            processed_rows=self.processed_rows,
            created=self.created,
            updated=self.updated,
            skipped=self.skipped,
            failed=self.failed,
            conflicts=self.conflicts,
            unmapped_fields=sorted(self.unmapped_fields),
            issues=[schemas.ImportIssue(**item) for item in self.issues],
        )


@dataclass
class ImportRuntime:
    db: Session
    options: schemas.SystemImportOptions
    report: schemas.SystemDataImportReport
    id_maps: dict[str, dict[int, int]] = field(default_factory=dict)

    def map_id(self, module: str, source_id: Optional[int], target_id: Optional[int]) -> None:
        if source_id is None or target_id is None:
            return
        canonical = _normalize_module_name(module)
        self.id_maps.setdefault(canonical, {})[source_id] = target_id

    def resolve_id(self, module: str, source_id: Optional[int]) -> Optional[int]:
        if source_id is None:
            return None
        canonical = _normalize_module_name(module)
        return self.id_maps.get(canonical, {}).get(source_id)


def import_system_data_package(
    *,
    db: Session,
    package_bytes: bytes,
    filename: Optional[str],
    options: schemas.SystemImportOptions,
    dry_run: bool,
) -> schemas.SystemDataImportReport:
    started_at = datetime.utcnow()
    parsed = _parse_import_package(package_bytes=package_bytes, filename=filename)

    requested_modules = _resolve_requested_modules(parsed=parsed, options=options)
    manifest_summary = _build_manifest_summary(parsed=parsed, requested_modules=requested_modules)

    report = schemas.SystemDataImportReport(
        dry_run=dry_run,
        started_at=started_at,
        options=options,
        manifest=manifest_summary,
        warnings=list(parsed.warnings),
    )
    runtime = ImportRuntime(db=db, options=options, report=report)

    handlers = _build_module_handlers()

    for module_name in requested_modules:
        rows = parsed.modules.get(module_name, [])
        expected_records = manifest_summary.expected_records.get(module_name)
        accumulator = ModuleAccumulator(
            module=module_name,
            expected_records=expected_records,
            detected_records=len(rows),
        )

        if expected_records is not None and expected_records != len(rows):
            accumulator.add_issue(
                row_number=1,
                code="count_mismatch",
                message=(
                    f"Ecart manifeste pour module {module_name}: "
                    f"attendu={expected_records}, detecte={len(rows)}."
                ),
            )

        if not rows:
            accumulator.add_issue(
                row_number=1,
                code="module_empty",
                message=f"Aucune donnee detectee pour le module {module_name}.",
            )
            report.modules.append(accumulator.to_schema())
            continue

        handler = handlers.get(module_name)
        if handler is None:
            accumulator.skipped += len(rows)
            message = f"Module {module_name} detecte mais non pris en charge."
            accumulator.add_issue(row_number=1, code="unsupported_module", message=message)
            report.warnings.append(message)
            if options.strict_mode:
                strict_message = f"Mode strict: module non pris en charge -> {module_name}"
                report.errors.append(strict_message)
                if not options.continue_on_error:
                    raise HTTPException(status_code=400, detail=strict_message)
            report.modules.append(accumulator.to_schema())
            continue

        try:
            handler(runtime, accumulator, rows)
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive catch
            message = f"Erreur module {module_name}: {exc}"
            accumulator.add_issue(row_number=1, code="module_error", message=message)
            accumulator.failed += max(1, len(rows) - accumulator.processed_rows)
            report.errors.append(message)
            if not options.continue_on_error:
                raise HTTPException(status_code=400, detail=message) from exc

        report.modules.append(accumulator.to_schema())

    _compute_report_totals(report)
    report.finished_at = datetime.utcnow()

    if dry_run:
        db.rollback()

    return report


def _build_module_handlers() -> dict[str, Callable[[ImportRuntime, ModuleAccumulator, list[dict[str, Any]]], None]]:
    return {
        "type_regimes": _import_type_regimes,
        "employers": _import_employers,
        "organizational_units": _import_organizational_units,
        "organizational_nodes": _import_organizational_nodes,
        "workers": _import_workers,
        "worker_position_history": _import_worker_position_history,
        "calendar_days": _import_calendar_days,
        "primes": _import_primes,
        "worker_primes": _import_worker_primes,
        "worker_prime_links": _import_worker_prime_links,
        "payroll_runs": _import_payroll_runs,
        "hs_calculations": _import_hs_calculations,
        "payvars": _import_payvars,
        "payroll_hs_hm": _import_payroll_hs_hm,
        "payroll_primes": _import_payroll_primes,
        "absences": _import_absences,
        "leaves": _import_leaves,
        "permissions": _import_permissions,
        "custom_contracts": _import_custom_contracts,
        "document_templates": _import_document_templates,
        "recruitment_candidates": _import_recruitment_candidates,
        "recruitment_job_postings": _import_recruitment_jobs,
        "talent_skills": _import_talent_skills,
        "talent_employee_skills": _import_talent_employee_skills,
        "talent_trainings": _import_talent_trainings,
        "talent_training_sessions": _import_talent_training_sessions,
        "sst_incidents": _import_sst_incidents,
    }


def _compute_report_totals(report: schemas.SystemDataImportReport) -> None:
    report.total_processed_rows = sum(item.processed_rows for item in report.modules)
    report.total_created = sum(item.created for item in report.modules)
    report.total_updated = sum(item.updated for item in report.modules)
    report.total_skipped = sum(item.skipped for item in report.modules)
    report.total_failed = sum(item.failed for item in report.modules)
    report.total_conflicts = sum(item.conflicts for item in report.modules)


def _expand_module_set(modules: set[str]) -> set[str]:
    expanded: set[str] = set()
    for module_name in modules:
        bundle = MODULE_BUNDLES.get(module_name)
        if bundle:
            expanded.update(bundle)
        else:
            expanded.add(module_name)
    return expanded


def _resolve_requested_modules(*, parsed: ParsedPackage, options: schemas.SystemImportOptions) -> list[str]:
    selected_raw = {_normalize_module_name(item) for item in options.selected_modules if item and str(item).strip()}
    selected = _expand_module_set(selected_raw)
    detected = _expand_module_set(set(parsed.modules.keys()))

    requested_set = selected or detected
    if not selected and options.strict_mode:
        expected_modules = _expand_module_set(set(_extract_expected_counts(parsed.manifest).keys()))
        requested_set = requested_set | expected_modules

    requested_ordered: list[str] = []
    for module_name in MODULE_IMPORT_ORDER:
        if module_name in requested_set:
            requested_ordered.append(module_name)

    remaining = sorted(item for item in requested_set if item not in set(requested_ordered))
    requested_ordered.extend(remaining)
    return requested_ordered


def _build_manifest_summary(*, parsed: ParsedPackage, requested_modules: list[str]) -> schemas.SystemImportManifestSummary:
    manifest = parsed.manifest if isinstance(parsed.manifest, dict) else {}
    metadata = _resolve_manifest_metadata(manifest)
    expected_counts = _extract_expected_counts(manifest)
    detected_counts = {module: len(rows) for module, rows in parsed.modules.items()}
    compatibility_warnings = _extract_manifest_warnings(manifest)

    for module_name, expected in expected_counts.items():
        detected = detected_counts.get(module_name, 0)
        if expected and detected == 0:
            compatibility_warnings.append(
                f"Module {module_name} attendu ({expected}) mais absent du package."
            )

    return schemas.SystemImportManifestSummary(
        source_system=_clean_text(
            metadata.get("source_system")
            or metadata.get("source")
            or metadata.get("origin")
            or metadata.get("format")
        ),
        package_version=_clean_text(
            metadata.get("package_version") or metadata.get("version") or metadata.get("app_version")
        ),
        export_version=_clean_text(metadata.get("export_version") or metadata.get("schema_version")),
        modules_detected=sorted(parsed.modules.keys()),
        modules_requested=requested_modules,
        expected_records=expected_counts,
        detected_records=detected_counts,
        compatibility_warnings=compatibility_warnings,
    )


def _resolve_manifest_metadata(manifest: dict[str, Any]) -> dict[str, Any]:
    export_metadata = manifest.get("export_metadata")
    if isinstance(export_metadata, dict):
        return export_metadata
    return manifest


def _extract_manifest_warnings(manifest: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    metadata = _resolve_manifest_metadata(manifest)
    package_version = _clean_text(
        metadata.get("package_version") or metadata.get("version") or metadata.get("app_version")
    )
    if not package_version:
        warnings.append("Manifest sans version explicite (package_version/version).")
        return warnings

    major = package_version.split(".", 1)[0]
    if major and not major.isdigit():
        warnings.append(f"Version de package non numerique: {package_version}.")
    elif major and int(major) > 1:
        warnings.append(
            f"Version de package {package_version} plus recente que le support nominal (1.x)."
        )
    return warnings


def _extract_expected_counts(manifest: dict[str, Any]) -> dict[str, int]:
    expected: dict[str, int] = {}

    modules_block = manifest.get("modules")
    if isinstance(modules_block, dict):
        for name, value in modules_block.items():
            canonical = _normalize_module_name(str(name))
            if isinstance(value, dict):
                nested_counts = value.get("record_counts") or value.get("counts") or value.get("modules")
                if isinstance(nested_counts, dict):
                    for nested_name, nested_value in nested_counts.items():
                        nested_count = _extract_count(nested_value)
                        if nested_count is None:
                            continue
                        expected[_normalize_module_name(str(nested_name))] = nested_count
            count = _extract_count(value)
            if count is not None:
                expected.setdefault(canonical, count)
    elif isinstance(modules_block, list):
        for item in modules_block:
            if not isinstance(item, dict):
                continue
            name = _clean_text(item.get("name") or item.get("module"))
            if not name:
                continue
            count = _extract_count(item)
            if count is not None:
                expected[_normalize_module_name(name)] = count

    for key in ("expected_counts", "record_counts", "counts"):
        block = manifest.get(key)
        if not isinstance(block, dict):
            continue
        for name, value in block.items():
            count = _extract_count(value)
            if count is None:
                continue
            expected[_normalize_module_name(str(name))] = count

    return expected


def _extract_count(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except Exception:
            return None
    if isinstance(value, dict):
        for key in ("count", "rows", "records", "total", "expected"):
            if key not in value:
                continue
            try:
                return int(value[key])
            except Exception:
                continue
    return None


def _parse_import_package(*, package_bytes: bytes, filename: Optional[str]) -> ParsedPackage:
    if len(package_bytes) > MAX_PACKAGE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Package trop volumineux (max 100MB).")

    extension = _detect_extension(filename)
    if extension not in SUPPORTED_PACKAGE_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_PACKAGE_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Format non supporte. Formats autorises: {allowed}")

    if extension == ".zip":
        return _parse_zip_package(package_bytes)

    return _parse_json_like_package(package_bytes, filename=filename)


def _detect_extension(filename: Optional[str]) -> str:
    if not filename:
        return ".json"
    lower = filename.lower().strip()
    for extension in SUPPORTED_PACKAGE_EXTENSIONS:
        if lower.endswith(extension):
            return extension
    return ""


def _parse_zip_package(package_bytes: bytes) -> ParsedPackage:
    parsed = ParsedPackage()

    try:
        with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                normalized_path = member.filename.replace("\\", "/")
                path = PurePosixPath(normalized_path)
                lower_name = path.name.lower()
                suffix = path.suffix.lower()
                if lower_name.startswith(".") or "__macosx" in normalized_path.lower():
                    continue

                raw = archive.read(member)
                if suffix == ".json" and lower_name in {"manifest.json", "package_manifest.json", "_manifest.json"}:
                    manifest = _parse_json_bytes(raw, member.filename)
                    if isinstance(manifest, dict):
                        parsed.manifest.update(manifest)
                    else:
                        parsed.warnings.append(f"Manifest ignore (non objet JSON): {member.filename}")
                    continue

                if suffix == ".json":
                    json_payload = _parse_json_bytes(raw, member.filename)
                    default_module = _module_from_path(normalized_path)
                    extracted = _extract_modules_from_json_payload(json_payload, default_module=default_module)
                    if extracted.manifest:
                        parsed.manifest.update(extracted.manifest)
                    parsed.warnings.extend(extracted.warnings)
                    _merge_module_rows(parsed.modules, extracted.modules)
                    continue

                if suffix == ".csv":
                    default_module = _module_from_path(normalized_path)
                    module_name = _normalize_module_name(default_module)
                    rows = _parse_csv_bytes(raw)
                    parsed.modules.setdefault(module_name, []).extend(rows)
                    continue

                if lower_name == "manifest" or lower_name == "manifest.txt":
                    try:
                        maybe_manifest = json.loads(_decode_text(raw))
                        if isinstance(maybe_manifest, dict):
                            parsed.manifest.update(maybe_manifest)
                    except Exception:
                        parsed.warnings.append(f"Fichier annexe ignore: {member.filename}")
                    continue

                parsed.warnings.append(f"Fichier ignore (format non supporte): {member.filename}")
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail=f"Archive ZIP invalide: {exc}") from exc

    return parsed


def _parse_json_like_package(package_bytes: bytes, *, filename: Optional[str]) -> ParsedPackage:
    payload = _parse_json_bytes(package_bytes, filename or "package.json")
    default_module = _normalize_module_name(PurePosixPath(filename or "package").stem)
    return _extract_modules_from_json_payload(payload, default_module=default_module)


def _parse_json_bytes(raw: bytes, source_name: str) -> Any:
    try:
        text = _decode_text(raw)
        return json.loads(text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"JSON invalide ({source_name}): {exc}") from exc


def _parse_csv_bytes(raw: bytes) -> list[dict[str, Any]]:
    try:
        text = _decode_text(raw)
        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"CSV invalide: {exc}") from exc


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def _extract_modules_from_json_payload(payload: Any, *, default_module: str) -> ParsedPackage:
    parsed = ParsedPackage()

    if isinstance(payload, list):
        module_name = _normalize_module_name(default_module or "records")
        parsed.modules[module_name] = _ensure_dict_rows(payload)
        return parsed

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Le package JSON doit contenir un objet ou une liste.")

    manifest = payload.get("manifest")
    if isinstance(manifest, dict):
        parsed.manifest.update(manifest)

    modules_container: Optional[dict[str, Any]] = None
    for key in ("modules", "data", "datasets", "tables"):
        candidate = payload.get(key)
        if isinstance(candidate, dict):
            modules_container = candidate
            break

    if modules_container is not None:
        for name, value in modules_container.items():
            rows = _extract_rows_from_value(value)
            if rows is None:
                continue
            parsed.modules.setdefault(_normalize_module_name(str(name)), []).extend(rows)
    else:
        extracted_any = False
        for key, value in payload.items():
            if key in {"manifest", "meta", "metadata", "options"}:
                continue
            if _normalize_module_name(key) not in MODULE_ALIASES.values():
                continue
            rows = _extract_rows_from_value(value)
            if rows is None:
                continue
            parsed.modules.setdefault(_normalize_module_name(key), []).extend(rows)
            extracted_any = True
        if not extracted_any:
            rows = _extract_rows_from_value(payload.get("rows") or payload.get("records") or payload.get("items"))
            if rows is not None:
                parsed.modules.setdefault(_normalize_module_name(default_module), []).extend(rows)
            else:
                parsed.modules.setdefault(_normalize_module_name(default_module), []).append(payload)

    return parsed


def _extract_rows_from_value(value: Any) -> Optional[list[dict[str, Any]]]:
    if value is None:
        return None
    if isinstance(value, list):
        return _ensure_dict_rows(value)
    if isinstance(value, dict):
        if _is_manifest_metadata_dict(value):
            return None
        for key in ("rows", "records", "items", "data"):
            nested = value.get(key)
            if isinstance(nested, list):
                return _ensure_dict_rows(nested)
        return [value]
    return None


def _is_manifest_metadata_dict(value: dict[str, Any]) -> bool:
    keys = {_normalize_field_name(item) for item in value.keys()}
    return keys.issubset({"count", "expected", "file", "path", "checksum", "hash", "version", "module", "name"})


def _merge_module_rows(target: dict[str, list[dict[str, Any]]], source: dict[str, list[dict[str, Any]]]) -> None:
    for module_name, rows in source.items():
        target.setdefault(module_name, []).extend(rows)


def _module_from_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    stem = pure.stem
    if stem in {"data", "dataset", "records", "items"} and pure.parent != PurePosixPath("."):
        stem = pure.parent.name
    return _normalize_module_name(stem)


def _normalize_module_name(value: str) -> str:
    token = TOKEN_PATTERN.sub("_", (value or "").lower()).strip("_")
    token = token.removesuffix("_json").removesuffix("_csv")
    return MODULE_ALIASES.get(token, token)


def _normalize_field_name(value: str) -> str:
    return TOKEN_PATTERN.sub("_", (value or "").lower()).strip("_")


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        normalized[_normalize_field_name(str(key))] = value
    return normalized


def _ensure_dict_rows(items: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            rows.append(item)
        else:
            rows.append({"value": item})
    return rows


def _is_empty_row(row: dict[str, Any]) -> bool:
    for value in row.values():
        if _has_value(value):
            return False
    return True


def _track_unmapped_fields(accumulator: ModuleAccumulator, row: dict[str, Any], known_fields: set[str]) -> None:
    unknown = {key for key in row.keys() if key not in known_fields}
    accumulator.unmapped_fields.update(sorted(unknown))


def _pick(row: dict[str, Any], *candidates: str) -> Any:
    for candidate in candidates:
        key = _normalize_field_name(candidate)
        if key in row and _has_value(row[key]):
            return row[key]
    return None


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        token = value.strip().lower()
        return token not in {"", "null", "none", "nan", "nat"}
    return True


def _clean_text(value: Any) -> Optional[str]:
    if not _has_value(value):
        return None
    return str(value).strip()


def _as_bool(value: Any, *, default: Optional[bool] = None) -> Optional[bool]:
    if not _has_value(value):
        return default
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in {"1", "true", "yes", "oui", "y"}:
        return True
    if token in {"0", "false", "no", "non", "n"}:
        return False
    return default


def _as_int(value: Any, *, default: Optional[int] = None) -> Optional[int]:
    if not _has_value(value):
        return default
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def _as_float(value: Any, *, default: Optional[float] = None) -> Optional[float]:
    if not _has_value(value):
        return default
    try:
        return float(str(value).replace(",", ".").strip())
    except Exception:
        return default


def _as_date(value: Any) -> Optional[date]:
    if not _has_value(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, pattern).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw).date()
    except Exception:
        return None


def _as_datetime(value: Any) -> Optional[datetime]:
    if not _has_value(value):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    raw = str(value).strip()
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(raw, pattern)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def _normalize_compare_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value.strip()
    return value


def _payload_equal(instance: Any, payload: dict[str, Any]) -> bool:
    for key, value in payload.items():
        current = getattr(instance, key, None)
        if _normalize_compare_value(current) != _normalize_compare_value(value):
            return False
    return True


def _apply_payload(instance: Any, payload: dict[str, Any]) -> bool:
    changed = False
    for key, value in payload.items():
        current = getattr(instance, key, None)
        if _normalize_compare_value(current) == _normalize_compare_value(value):
            continue
        setattr(instance, key, value)
        changed = True
    return changed


def _to_json_list_str(value: Any) -> Optional[str]:
    if not _has_value(value):
        return None
    if isinstance(value, list):
        return json.dumps([str(item).strip() for item in value if _has_value(item)], ensure_ascii=False)
    raw = str(value).strip()
    if not raw:
        return None
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return json.dumps([str(item).strip() for item in parsed if _has_value(item)], ensure_ascii=False)
        except Exception:
            pass
    split_items = [item.strip() for item in re.split(r"[;,|\n]", raw) if item.strip()]
    return json.dumps(split_items, ensure_ascii=False)


def _register_row_error(
    runtime: ImportRuntime,
    accumulator: ModuleAccumulator,
    *,
    row_number: int,
    code: str,
    message: str,
    column: Optional[str] = None,
    value: Optional[Any] = None,
) -> None:
    accumulator.failed += 1
    accumulator.add_issue(
        row_number=row_number,
        code=code,
        message=message,
        column=column,
        value=value,
    )
    if not runtime.options.continue_on_error:
        raise HTTPException(status_code=400, detail=f"[{accumulator.module}] ligne {row_number}: {message}")


def _handle_existing_merge(
    runtime: ImportRuntime,
    accumulator: ModuleAccumulator,
    *,
    row_number: int,
    existing: Any,
    payload: dict[str, Any],
    conflict_message: str,
) -> str:
    comparable = {key: value for key, value in payload.items() if value is not None}
    if runtime.options.skip_exact_duplicates and _payload_equal(existing, comparable):
        accumulator.skipped += 1
        accumulator.processed_rows += 1
        return "skipped"

    if not runtime.options.update_existing:
        accumulator.conflicts += 1
        accumulator.skipped += 1
        accumulator.processed_rows += 1
        accumulator.add_issue(
            row_number=row_number,
            code="conflict_existing",
            message=conflict_message,
        )
        return "conflict"

    changed = _apply_payload(existing, comparable)
    if changed:
        accumulator.updated += 1
    else:
        accumulator.skipped += 1
    accumulator.processed_rows += 1
    return "updated" if changed else "skipped"


def _resolve_type_regime_id(runtime: ImportRuntime, row: dict[str, Any]) -> Optional[int]:
    source_id = _as_int(_pick(row, "type_regime_id", "regime_id"))
    if source_id is not None:
        mapped = runtime.resolve_id("type_regimes", source_id)
        if mapped is not None:
            return mapped
        regime = runtime.db.query(models.TypeRegime).filter(models.TypeRegime.id == source_id).first()
        if regime:
            return regime.id

    code = _clean_text(_pick(row, "type_regime_code", "regime_code", "regime"))
    if code:
        regime = (
            runtime.db.query(models.TypeRegime)
            .filter(func.lower(models.TypeRegime.code) == code.lower())
            .first()
        )
        if regime:
            return regime.id

    return None


def _resolve_employer(runtime: ImportRuntime, row: dict[str, Any]) -> Optional[models.Employer]:
    source_id = _as_int(_pick(row, "employer_id", "company_id", "societe_id"))
    if source_id is not None:
        mapped = runtime.resolve_id("employers", source_id)
        if mapped is not None:
            employer = runtime.db.query(models.Employer).filter(models.Employer.id == mapped).first()
            if employer:
                return employer
        employer = runtime.db.query(models.Employer).filter(models.Employer.id == source_id).first()
        if employer:
            return employer

    name = _clean_text(
        _pick(row, "raison_sociale", "employer_name", "employeur", "company_name", "name")
    )
    if name:
        employer = (
            runtime.db.query(models.Employer)
            .filter(func.lower(models.Employer.raison_sociale) == name.lower())
            .first()
        )
        if employer:
            return employer

    return None


def _resolve_worker(runtime: ImportRuntime, row: dict[str, Any]) -> Optional[models.Worker]:
    source_id = _as_int(_pick(row, "worker_id", "employee_id", "salarie_id", "worker_id_hs"))
    if source_id is not None:
        mapped = runtime.resolve_id("workers", source_id)
        if mapped is not None:
            worker = runtime.db.query(models.Worker).filter(models.Worker.id == mapped).first()
            if worker:
                return worker
        worker = runtime.db.query(models.Worker).filter(models.Worker.id == source_id).first()
        if worker:
            return worker

    matricule = _clean_text(_pick(row, "matricule", "employee_code", "code_salarie"))
    if matricule:
        worker = runtime.db.query(models.Worker).filter(models.Worker.matricule == matricule).first()
        if worker:
            return worker
    return None


def _resolve_prime(
    runtime: ImportRuntime,
    row: dict[str, Any],
    *,
    worker: Optional[models.Worker] = None,
) -> Optional[models.Prime]:
    source_id = _as_int(_pick(row, "prime_id"))
    if source_id is not None:
        mapped = runtime.resolve_id("primes", source_id)
        if mapped is not None:
            prime = runtime.db.query(models.Prime).filter(models.Prime.id == mapped).first()
            if prime:
                return prime
        prime = runtime.db.query(models.Prime).filter(models.Prime.id == source_id).first()
        if prime:
            return prime

    label = _clean_text(_pick(row, "label", "prime_label", "name"))
    if not label:
        return None

    employer = _resolve_employer(runtime, row)
    employer_id = employer.id if employer else (worker.employer_id if worker else None)
    if employer_id is None:
        return None

    return (
        runtime.db.query(models.Prime)
        .filter(models.Prime.employer_id == employer_id, func.lower(models.Prime.label) == label.lower())
        .first()
    )


def _resolve_payroll_run(runtime: ImportRuntime, row: dict[str, Any]) -> Optional[models.PayrollRun]:
    source_id = _as_int(_pick(row, "payroll_run_id", "run_id", "payroll_run_id_hs"))
    if source_id is not None:
        mapped = runtime.resolve_id("payroll_runs", source_id)
        if mapped is not None:
            run = runtime.db.query(models.PayrollRun).filter(models.PayrollRun.id == mapped).first()
            if run:
                return run
        run = runtime.db.query(models.PayrollRun).filter(models.PayrollRun.id == source_id).first()
        if run:
            return run

    employer = _resolve_employer(runtime, row)
    period = _clean_text(_pick(row, "period", "mois", "pay_period"))
    if employer and period and PERIOD_PATTERN.match(period):
        return (
            runtime.db.query(models.PayrollRun)
            .filter(models.PayrollRun.employer_id == employer.id, models.PayrollRun.period == period)
            .first()
        )
    return None


def _resolve_hs_calculation_id(runtime: ImportRuntime, row: dict[str, Any]) -> Optional[int]:
    source_id = _as_int(_pick(row, "hs_calculation_id", "hs_id", "id_hs"))
    if source_id is None:
        return None

    mapped = runtime.resolve_id("hs_calculations", source_id)
    for candidate in (mapped, source_id):
        if candidate is None:
            continue
        existing = (
            runtime.db.query(models.HSCalculationHS)
            .filter(models.HSCalculationHS.id_HS == candidate)
            .first()
        )
        if existing:
            return existing.id_HS

    return None


def _resolve_talent_skill(runtime: ImportRuntime, row: dict[str, Any], worker: Optional[models.Worker] = None) -> Optional[models.TalentSkill]:
    source_id = _as_int(_pick(row, "skill_id", "talent_skill_id"))
    if source_id is not None:
        mapped = runtime.resolve_id("talent_skills", source_id)
        if mapped is not None:
            skill = runtime.db.query(models.TalentSkill).filter(models.TalentSkill.id == mapped).first()
            if skill:
                return skill
        skill = runtime.db.query(models.TalentSkill).filter(models.TalentSkill.id == source_id).first()
        if skill:
            return skill

    code = _clean_text(_pick(row, "code", "skill_code", "code_competence"))
    employer = _resolve_employer(runtime, row)
    employer_id = employer.id if employer else (worker.employer_id if worker else None)
    if code and employer_id is not None:
        skill = (
            runtime.db.query(models.TalentSkill)
            .filter(
                models.TalentSkill.employer_id == employer_id,
                func.lower(models.TalentSkill.code) == code.lower(),
            )
            .first()
        )
        if skill:
            return skill

    name = _clean_text(_pick(row, "name", "nom", "skill_name"))
    if name and employer_id is not None:
        return (
            runtime.db.query(models.TalentSkill)
            .filter(
                models.TalentSkill.employer_id == employer_id,
                func.lower(models.TalentSkill.name) == name.lower(),
            )
            .first()
        )
    return None


def _resolve_talent_training(runtime: ImportRuntime, row: dict[str, Any]) -> Optional[models.TalentTraining]:
    source_id = _as_int(_pick(row, "training_id", "talent_training_id"))
    if source_id is not None:
        mapped = runtime.resolve_id("talent_trainings", source_id)
        if mapped is not None:
            training = runtime.db.query(models.TalentTraining).filter(models.TalentTraining.id == mapped).first()
            if training:
                return training
        training = runtime.db.query(models.TalentTraining).filter(models.TalentTraining.id == source_id).first()
        if training:
            return training

    employer = _resolve_employer(runtime, row)
    title = _clean_text(_pick(row, "title", "titre"))
    if employer and title:
        return (
            runtime.db.query(models.TalentTraining)
            .filter(
                models.TalentTraining.employer_id == employer.id,
                func.lower(models.TalentTraining.title) == title.lower(),
            )
            .first()
        )
    return None


def _normalize_org_level(raw_level: Optional[str], level_order: Optional[int]) -> Optional[str]:
    if raw_level:
        normalized = _normalize_field_name(raw_level)
        if normalized in {"etablissement", "departement", "service", "unite"}:
            return normalized
    if level_order == 1:
        return "etablissement"
    if level_order == 2:
        return "departement"
    if level_order == 3:
        return "service"
    if level_order == 4:
        return "unite"
    return None


def _slug_token(value: str) -> str:
    token = TOKEN_PATTERN.sub("_", (value or "").lower()).strip("_")
    return token[:50] or "item"


def _organization_level_rank(level: Optional[str]) -> int:
    return {"etablissement": 1, "departement": 2, "service": 3, "unite": 4}.get(level or "", 99)


def _iter_sorted_organizational_rows(
    rows: list[dict[str, Any]],
    *,
    include_level_order: bool,
) -> list[tuple[int, dict[str, Any]]]:
    indexed_rows: list[tuple[int, dict[str, Any]]] = []
    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        indexed_rows.append((index, row))

    def sort_key(item: tuple[int, dict[str, Any]]) -> tuple[int, int, int]:
        _, row = item
        level_order = _as_int(_pick(row, "level_order")) if include_level_order else None
        level = _normalize_org_level(_clean_text(_pick(row, "level", "niveau")), level_order)
        rank = level_order if level_order is not None else _organization_level_rank(level)
        parent_id = _as_int(_pick(row, "parent_id"))
        return (rank or 99, 0 if parent_id is None else 1, parent_id or 0)

    return sorted(indexed_rows, key=sort_key)


def _import_type_regimes(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {"code", "label", "name", "libelle", "vhm"}

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        code = _clean_text(_pick(row, "code", "regime_code", "name"))
        label = _clean_text(_pick(row, "label", "libelle", "name")) or code
        vhm = _as_float(_pick(row, "vhm", "valeur_horaire_mensuelle"), default=173.33)

        if not code:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="missing_code",
                message="Code type_regime obligatoire.",
                column="code",
            )
            continue
        if label is None:
            label = code
        if vhm is None:
            vhm = 173.33

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))

        try:
            with runtime.db.begin_nested():
                payload = {"code": code.lower(), "label": label, "vhm": vhm}
                existing = (
                    runtime.db.query(models.TypeRegime)
                    .filter(func.lower(models.TypeRegime.code) == code.lower())
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"Type regime deja existant: {code}.",
                    )
                    runtime.map_id("type_regimes", source_id, existing.id)
                    continue

                entity = models.TypeRegime(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("type_regimes", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import type_regime impossible: {exc}",
            )


def _import_employers(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "raison_sociale",
        "name",
        "employer_name",
        "adresse",
        "pays",
        "telephone",
        "email",
        "activite",
        "representant",
        "rep_date_naissance",
        "rep_cin_num",
        "rep_cin_date",
        "rep_cin_lieu",
        "rep_adresse",
        "rep_fonction",
        "nif",
        "stat",
        "lieu_fiscal",
        "cnaps_num",
        "sm_embauche",
        "type_etab",
        "taux_pat_cnaps",
        "taux_pat_smie",
        "taux_sal_cnaps",
        "rcs",
        "ostie_num",
        "smie_num",
        "ville",
        "contact_rh",
        "logo_path",
        "plafond_cnaps_base",
        "taux_pat_fmfp",
        "taux_sal_smie",
        "smie_forfait_sal",
        "smie_forfait_pat",
        "plafond_smie",
        "label_prime1",
        "label_prime2",
        "label_prime3",
        "label_prime4",
        "label_prime5",
        "etablissements",
        "departements",
        "services",
        "unites",
        "type_regime_id",
        "type_regime_code",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        raison_sociale = _clean_text(_pick(row, "raison_sociale", "name", "employer_name", "employeur"))
        if not raison_sociale:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="missing_raison_sociale",
                message="raison_sociale obligatoire.",
                column="raison_sociale",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        type_regime_id = _resolve_type_regime_id(runtime, row)

        payload: dict[str, Any] = {
            "raison_sociale": raison_sociale,
            "adresse": _clean_text(_pick(row, "adresse", "address")),
            "pays": _clean_text(_pick(row, "pays", "country")),
            "telephone": _clean_text(_pick(row, "telephone", "phone")),
            "email": _clean_text(_pick(row, "email")),
            "activite": _clean_text(_pick(row, "activite", "activity")),
            "representant": _clean_text(_pick(row, "representant", "representative")),
            "rep_date_naissance": _as_date(_pick(row, "rep_date_naissance")),
            "rep_cin_num": _clean_text(_pick(row, "rep_cin_num")),
            "rep_cin_date": _as_date(_pick(row, "rep_cin_date")),
            "rep_cin_lieu": _clean_text(_pick(row, "rep_cin_lieu")),
            "rep_adresse": _clean_text(_pick(row, "rep_adresse")),
            "rep_fonction": _clean_text(_pick(row, "rep_fonction")),
            "nif": _clean_text(_pick(row, "nif")),
            "stat": _clean_text(_pick(row, "stat")),
            "lieu_fiscal": _clean_text(_pick(row, "lieu_fiscal")),
            "cnaps_num": _clean_text(_pick(row, "cnaps_num")),
            "sm_embauche": _as_float(_pick(row, "sm_embauche")),
            "type_etab": _clean_text(_pick(row, "type_etab")) or "general",
            "taux_pat_cnaps": _as_float(_pick(row, "taux_pat_cnaps")),
            "taux_pat_smie": _as_float(_pick(row, "taux_pat_smie")),
            "taux_sal_cnaps": _as_float(_pick(row, "taux_sal_cnaps")),
            "rcs": _clean_text(_pick(row, "rcs")),
            "ostie_num": _clean_text(_pick(row, "ostie_num")),
            "smie_num": _clean_text(_pick(row, "smie_num")),
            "ville": _clean_text(_pick(row, "ville")),
            "contact_rh": _clean_text(_pick(row, "contact_rh")),
            "logo_path": _clean_text(_pick(row, "logo_path")),
            "plafond_cnaps_base": _as_float(_pick(row, "plafond_cnaps_base")),
            "taux_pat_fmfp": _as_float(_pick(row, "taux_pat_fmfp")),
            "taux_sal_smie": _as_float(_pick(row, "taux_sal_smie")),
            "smie_forfait_sal": _as_float(_pick(row, "smie_forfait_sal")),
            "smie_forfait_pat": _as_float(_pick(row, "smie_forfait_pat")),
            "plafond_smie": _as_float(_pick(row, "plafond_smie")),
            "label_prime1": _clean_text(_pick(row, "label_prime1")),
            "label_prime2": _clean_text(_pick(row, "label_prime2")),
            "label_prime3": _clean_text(_pick(row, "label_prime3")),
            "label_prime4": _clean_text(_pick(row, "label_prime4")),
            "label_prime5": _clean_text(_pick(row, "label_prime5")),
            "etablissements": _to_json_list_str(_pick(row, "etablissements")),
            "departements": _to_json_list_str(_pick(row, "departements")),
            "services": _to_json_list_str(_pick(row, "services")),
            "unites": _to_json_list_str(_pick(row, "unites")),
            "type_regime_id": type_regime_id,
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.Employer)
                    .filter(func.lower(models.Employer.raison_sociale) == raison_sociale.lower())
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"Employeur deja existant: {raison_sociale}.",
                    )
                    runtime.map_id("employers", source_id, existing.id)
                    continue

                entity = models.Employer(**{key: value for key, value in payload.items() if value is not None})
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("employers", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import employeur impossible: {exc}",
            )


def _import_organizational_units(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "employer_id",
        "company_id",
        "raison_sociale",
        "employer_name",
        "parent_id",
        "level",
        "level_order",
        "code",
        "name",
        "nom",
        "description",
        "is_active",
    }

    for index, row in _iter_sorted_organizational_rows(rows, include_level_order=True):
        _track_unmapped_fields(accumulator, row, known_fields)

        employer = _resolve_employer(runtime, row)
        if employer is None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="unknown_employer",
                message="Employeur introuvable pour organizational_unit.",
            )
            continue

        level_order = _as_int(_pick(row, "level_order"))
        level = _normalize_org_level(_clean_text(_pick(row, "level", "niveau")), level_order)
        if level is None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_level",
                message="Niveau organisationnel invalide.",
                column="level",
            )
            continue
        if level_order is None:
            level_order = {"etablissement": 1, "departement": 2, "service": 3, "unite": 4}[level]

        name = _clean_text(_pick(row, "name", "nom"))
        if not name:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="missing_name",
                message="Nom organizational_unit obligatoire.",
                column="name",
            )
            continue
        code = _clean_text(_pick(row, "code")) or _slug_token(name)
        parent_source_id = _as_int(_pick(row, "parent_id"))
        parent_id = runtime.resolve_id("organizational_units", parent_source_id) if parent_source_id is not None else None
        if parent_source_id is not None and parent_id is None:
            mapped_parent = (
                runtime.db.query(models.OrganizationalUnit)
                .filter(
                    models.OrganizationalUnit.id == parent_source_id,
                    models.OrganizationalUnit.employer_id == employer.id,
                )
                .first()
            )
            if mapped_parent:
                parent_id = mapped_parent.id
                runtime.map_id("organizational_units", parent_source_id, mapped_parent.id)

        if level != "etablissement" and parent_id is None and parent_source_id is not None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="missing_parent_mapping",
                message=f"Parent organizational_unit non resolu ({parent_source_id}).",
            )
            continue
        if level == "etablissement":
            parent_id = None

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "employer_id": employer.id,
            "parent_id": parent_id,
            "level": level,
            "level_order": level_order,
            "code": code,
            "name": name,
            "description": _clean_text(_pick(row, "description")),
            "is_active": _as_bool(_pick(row, "is_active"), default=True),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.OrganizationalUnit)
                    .filter(
                        models.OrganizationalUnit.employer_id == employer.id,
                        models.OrganizationalUnit.parent_id == parent_id,
                        models.OrganizationalUnit.code == code,
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"OrganizationalUnit deja existant: {code}.",
                    )
                    runtime.map_id("organizational_units", source_id, existing.id)
                    continue

                entity = models.OrganizationalUnit(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("organizational_units", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import organizational_unit impossible: {exc}",
            )


def _import_organizational_nodes(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "employer_id",
        "company_id",
        "raison_sociale",
        "employer_name",
        "parent_id",
        "level",
        "name",
        "nom",
        "code",
        "description",
        "path",
        "sort_order",
        "is_active",
    }

    for index, row in _iter_sorted_organizational_rows(rows, include_level_order=False):
        _track_unmapped_fields(accumulator, row, known_fields)

        employer = _resolve_employer(runtime, row)
        if employer is None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="unknown_employer",
                message="Employeur introuvable pour organizational_node.",
            )
            continue

        level = _normalize_org_level(_clean_text(_pick(row, "level", "niveau")), None)
        name = _clean_text(_pick(row, "name", "nom"))
        if not level or not name:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="missing_required_values",
                message="level et name obligatoires pour organizational_node.",
            )
            continue

        code = _clean_text(_pick(row, "code"))
        parent_source_id = _as_int(_pick(row, "parent_id"))
        parent_id = runtime.resolve_id("organizational_nodes", parent_source_id) if parent_source_id is not None else None
        if parent_source_id is not None and parent_id is None:
            mapped_parent = (
                runtime.db.query(models.OrganizationalNode)
                .filter(
                    models.OrganizationalNode.id == parent_source_id,
                    models.OrganizationalNode.employer_id == employer.id,
                )
                .first()
            )
            if mapped_parent:
                parent_id = mapped_parent.id
                runtime.map_id("organizational_nodes", parent_source_id, mapped_parent.id)
        if level == "etablissement":
            parent_id = None
        elif parent_source_id is not None and parent_id is None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="missing_parent_mapping",
                message=f"Parent organizational_node non resolu ({parent_source_id}).",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "employer_id": employer.id,
            "parent_id": parent_id,
            "level": level,
            "name": name,
            "code": code,
            "description": _clean_text(_pick(row, "description")),
            "path": _clean_text(_pick(row, "path")),
            "sort_order": _as_int(_pick(row, "sort_order"), default=0),
            "is_active": _as_bool(_pick(row, "is_active"), default=True),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.OrganizationalNode)
                    .filter(
                        models.OrganizationalNode.employer_id == employer.id,
                        models.OrganizationalNode.parent_id == parent_id,
                        func.lower(models.OrganizationalNode.name) == name.lower(),
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"OrganizationalNode deja existant: {name}.",
                    )
                    runtime.map_id("organizational_nodes", source_id, existing.id)
                    continue

                entity = models.OrganizationalNode(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("organizational_nodes", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import organizational_node impossible: {exc}",
            )


def _import_workers(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "employer_id",
        "company_id",
        "raison_sociale",
        "employer_name",
        "matricule",
        "nom",
        "prenom",
        "sexe",
        "situation_familiale",
        "adresse",
        "telephone",
        "type_regime_id",
        "type_regime_code",
        "email",
        "cin",
        "cin_delivre_le",
        "cin_lieu",
        "nombre_enfant",
        "date_naissance",
        "lieu_naissance",
        "date_embauche",
        "nature_contrat",
        "duree_essai_jours",
        "date_fin_essai",
        "mode_paiement",
        "rib",
        "code_banque",
        "code_guichet",
        "compte_num",
        "cle_rib",
        "banque",
        "nom_guichet",
        "bic",
        "cnaps_num",
        "smie_agence",
        "smie_carte_num",
        "etablissement",
        "departement",
        "service",
        "unite",
        "poste",
        "categorie_prof",
        "indice",
        "valeur_point",
        "groupe_preavis",
        "type_sortie",
        "date_debauche",
        "jours_preavis_deja_faits",
        "secteur",
        "salaire_base",
        "salaire_horaire",
        "vhm",
        "horaire_hebdo",
        "solde_conge_initial",
        "avantage_vehicule",
        "avantage_logement",
        "avantage_telephone",
        "avantage_autres",
        "taux_sal_cnaps_override",
        "taux_sal_smie_override",
        "taux_pat_cnaps_override",
        "taux_pat_smie_override",
        "taux_pat_fmfp_override",
        "organizational_unit_id",
        "organizational_unit_code",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        matricule = _clean_text(_pick(row, "matricule", "employee_code", "code_salarie"))
        nom = _clean_text(_pick(row, "nom", "last_name", "surname"))
        prenom = _clean_text(_pick(row, "prenom", "first_name", "given_name"))
        employer = _resolve_employer(runtime, row)
        if not matricule or employer is None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="missing_required_values",
                message="matricule et employeur obligatoires pour worker.",
            )
            continue
        if not nom:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="missing_name",
                message=f"Nom obligatoire pour matricule {matricule}.",
                column="nom",
            )
            continue
        if not prenom:
            prenom = ""

        type_regime_id = _resolve_type_regime_id(runtime, row)
        organizational_unit_source = _as_int(_pick(row, "organizational_unit_id"))
        organizational_unit_id = (
            runtime.resolve_id("organizational_units", organizational_unit_source)
            if organizational_unit_source is not None
            else None
        )
        if organizational_unit_id is None:
            organizational_unit_code = _clean_text(_pick(row, "organizational_unit_code"))
            if organizational_unit_code:
                ou = (
                    runtime.db.query(models.OrganizationalUnit)
                    .filter(
                        models.OrganizationalUnit.employer_id == employer.id,
                        models.OrganizationalUnit.code == organizational_unit_code,
                    )
                    .first()
                )
                if ou:
                    organizational_unit_id = ou.id

        vhm = _as_float(_pick(row, "vhm"))
        salaire_base = _as_float(_pick(row, "salaire_base"), default=0.0) or 0.0
        if vhm is None:
            if type_regime_id is not None:
                regime = runtime.db.query(models.TypeRegime).filter(models.TypeRegime.id == type_regime_id).first()
                vhm = regime.vhm if regime else 173.33
            else:
                vhm = 173.33
        salaire_horaire = _as_float(_pick(row, "salaire_horaire"))
        if salaire_horaire is None:
            salaire_horaire = (salaire_base / vhm) if vhm else 0.0

        payload: dict[str, Any] = {
            "employer_id": employer.id,
            "matricule": matricule,
            "nom": nom.upper(),
            "prenom": prenom,
            "sexe": (_clean_text(_pick(row, "sexe")) or "").upper()[:1] or None,
            "situation_familiale": _clean_text(_pick(row, "situation_familiale")),
            "adresse": _clean_text(_pick(row, "adresse")),
            "telephone": _clean_text(_pick(row, "telephone")),
            "type_regime_id": type_regime_id,
            "email": (_clean_text(_pick(row, "email")) or "").lower() or None,
            "cin": _clean_text(_pick(row, "cin")),
            "cin_delivre_le": _as_date(_pick(row, "cin_delivre_le")),
            "cin_lieu": _clean_text(_pick(row, "cin_lieu")),
            "nombre_enfant": _as_int(_pick(row, "nombre_enfant"), default=0),
            "date_naissance": _as_date(_pick(row, "date_naissance")),
            "lieu_naissance": _clean_text(_pick(row, "lieu_naissance")),
            "date_embauche": _as_date(_pick(row, "date_embauche")),
            "nature_contrat": _clean_text(_pick(row, "nature_contrat")) or "CDI",
            "duree_essai_jours": _as_int(_pick(row, "duree_essai_jours"), default=0),
            "date_fin_essai": _as_date(_pick(row, "date_fin_essai")),
            "mode_paiement": _clean_text(_pick(row, "mode_paiement")) or "Virement",
            "rib": _clean_text(_pick(row, "rib")),
            "code_banque": _clean_text(_pick(row, "code_banque")),
            "code_guichet": _clean_text(_pick(row, "code_guichet")),
            "compte_num": _clean_text(_pick(row, "compte_num")),
            "cle_rib": _clean_text(_pick(row, "cle_rib")),
            "banque": _clean_text(_pick(row, "banque")),
            "nom_guichet": _clean_text(_pick(row, "nom_guichet")),
            "bic": _clean_text(_pick(row, "bic")),
            "cnaps_num": _clean_text(_pick(row, "cnaps_num")),
            "smie_agence": _clean_text(_pick(row, "smie_agence")),
            "smie_carte_num": _clean_text(_pick(row, "smie_carte_num")),
            "etablissement": _clean_text(_pick(row, "etablissement")),
            "departement": _clean_text(_pick(row, "departement")),
            "service": _clean_text(_pick(row, "service")),
            "unite": _clean_text(_pick(row, "unite")),
            "poste": _clean_text(_pick(row, "poste")),
            "categorie_prof": _clean_text(_pick(row, "categorie_prof")),
            "indice": _clean_text(_pick(row, "indice")),
            "valeur_point": _as_float(_pick(row, "valeur_point")),
            "groupe_preavis": _as_int(_pick(row, "groupe_preavis")),
            "type_sortie": _clean_text(_pick(row, "type_sortie")),
            "date_debauche": _as_date(_pick(row, "date_debauche")),
            "jours_preavis_deja_faits": _as_int(_pick(row, "jours_preavis_deja_faits"), default=0),
            "secteur": _clean_text(_pick(row, "secteur")),
            "salaire_base": salaire_base,
            "salaire_horaire": salaire_horaire,
            "vhm": vhm,
            "horaire_hebdo": _as_float(_pick(row, "horaire_hebdo"), default=40.0),
            "solde_conge_initial": _as_float(_pick(row, "solde_conge_initial"), default=0.0),
            "avantage_vehicule": _as_float(_pick(row, "avantage_vehicule"), default=0.0),
            "avantage_logement": _as_float(_pick(row, "avantage_logement"), default=0.0),
            "avantage_telephone": _as_float(_pick(row, "avantage_telephone"), default=0.0),
            "avantage_autres": _as_float(_pick(row, "avantage_autres"), default=0.0),
            "taux_sal_cnaps_override": _as_float(_pick(row, "taux_sal_cnaps_override")),
            "taux_sal_smie_override": _as_float(_pick(row, "taux_sal_smie_override")),
            "taux_pat_cnaps_override": _as_float(_pick(row, "taux_pat_cnaps_override")),
            "taux_pat_smie_override": _as_float(_pick(row, "taux_pat_smie_override")),
            "taux_pat_fmfp_override": _as_float(_pick(row, "taux_pat_fmfp_override")),
            "organizational_unit_id": organizational_unit_id,
        }

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))

        try:
            with runtime.db.begin_nested():
                existing = runtime.db.query(models.Worker).filter(models.Worker.matricule == matricule).first()
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"Worker deja existant: {matricule}.",
                    )
                    runtime.map_id("workers", source_id, existing.id)
                    continue

                entity = models.Worker(**{key: value for key, value in payload.items() if value is not None})
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("workers", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import worker impossible: {exc}",
            )


def _import_worker_position_history(
    runtime: ImportRuntime,
    accumulator: ModuleAccumulator,
    rows: list[dict[str, Any]],
) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "worker_id",
        "matricule",
        "poste",
        "categorie_prof",
        "indice",
        "start_date",
        "end_date",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        worker = _resolve_worker(runtime, row)
        poste = _clean_text(_pick(row, "poste", "position", "job_title"))
        start_date = _as_date(_pick(row, "start_date", "date_debut"))
        end_date = _as_date(_pick(row, "end_date", "date_fin"))
        if worker is None or not poste or not start_date:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="Worker, poste et start_date obligatoires pour worker_position_history.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "worker_id": worker.id,
            "poste": poste,
            "categorie_prof": _clean_text(_pick(row, "categorie_prof")),
            "indice": _clean_text(_pick(row, "indice")),
            "start_date": start_date,
            "end_date": end_date,
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.WorkerPositionHistory)
                    .filter(
                        models.WorkerPositionHistory.worker_id == worker.id,
                        models.WorkerPositionHistory.start_date == start_date,
                        models.WorkerPositionHistory.end_date == end_date,
                        func.lower(models.WorkerPositionHistory.poste) == poste.lower(),
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"WorkerPositionHistory deja existante ({worker.matricule}/{poste}).",
                    )
                    runtime.map_id("worker_position_history", source_id, existing.id)
                    continue

                entity = models.WorkerPositionHistory(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("worker_position_history", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import worker_position_history impossible: {exc}",
            )


def _import_calendar_days(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "employer_id",
        "company_id",
        "raison_sociale",
        "employer_name",
        "date",
        "is_worked",
        "status",
        "note",
    }

    non_worked_statuses = {"closed", "off", "holiday", "not_worked", "non_worked"}
    worked_statuses = {"open", "worked", "work"}

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        employer = _resolve_employer(runtime, row)
        day_date = _as_date(_pick(row, "date", "jour"))
        if employer is None or day_date is None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="Employeur et date obligatoires pour calendar_day.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        is_worked = _as_bool(_pick(row, "is_worked"))
        if is_worked is None:
            status = (_clean_text(_pick(row, "status")) or "").lower()
            if status in non_worked_statuses:
                is_worked = False
            elif status in worked_statuses:
                is_worked = True
        if is_worked is None:
            is_worked = True

        status = (_clean_text(_pick(row, "status")) or "").lower()
        if status not in {"worked", "off", "closed"}:
            status = "worked" if is_worked else "off"

        payload = {
            "employer_id": employer.id,
            "date": day_date,
            "is_worked": is_worked,
            "status": status,
            "note": _clean_text(_pick(row, "note", "notes")),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.CalendarDay)
                    .filter(models.CalendarDay.employer_id == employer.id, models.CalendarDay.date == day_date)
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"CalendarDay deja existant ({employer.raison_sociale}/{day_date}).",
                    )
                    runtime.map_id("calendar_days", source_id, existing.id)
                    continue

                entity = models.CalendarDay(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("calendar_days", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import calendar_day impossible: {exc}",
            )


def _import_hs_calculations(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "id_hs",
        "worker_id_hs",
        "mois_hs",
        "base_hebdo_heures_hs",
        "total_hsni_130_heures_hs",
        "total_hsi_130_heures_hs",
        "total_hsni_150_heures_hs",
        "total_hsi_150_heures_hs",
        "total_hmnh_30_heures_hs",
        "total_hmno_50_heures_hs",
        "total_hmd_40_heures_hs",
        "total_hmjf_50_heures_hs",
        "payroll_run_id_hs",
        "created_at_hs",
        "updated_at_hs",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        worker = _resolve_worker(runtime, row)
        mois = _clean_text(_pick(row, "mois_hs", "mois", "period", "pay_period"))
        if worker is None or not mois or not PERIOD_PATTERN.match(mois):
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="Worker et mois YYYY-MM obligatoires pour hs_calculation.",
            )
            continue

        payroll_run = _resolve_payroll_run(runtime, row)
        source_id = _as_int(_pick(row, "id_hs", "id", "source_id", "legacy_id"))
        payload = {
            "worker_id_HS": worker.id,
            "mois_HS": mois,
            "base_hebdo_heures_HS": _as_float(_pick(row, "base_hebdo_heures_hs"), default=40.0) or 40.0,
            "total_HSNI_130_heures_HS": _as_float(_pick(row, "total_hsni_130_heures_hs"), default=0.0) or 0.0,
            "total_HSI_130_heures_HS": _as_float(_pick(row, "total_hsi_130_heures_hs"), default=0.0) or 0.0,
            "total_HSNI_150_heures_HS": _as_float(_pick(row, "total_hsni_150_heures_hs"), default=0.0) or 0.0,
            "total_HSI_150_heures_HS": _as_float(_pick(row, "total_hsi_150_heures_hs"), default=0.0) or 0.0,
            "total_HMNH_30_heures_HS": _as_float(_pick(row, "total_hmnh_30_heures_hs"), default=0.0) or 0.0,
            "total_HMNO_50_heures_HS": _as_float(_pick(row, "total_hmno_50_heures_hs"), default=0.0) or 0.0,
            "total_HMD_40_heures_HS": _as_float(_pick(row, "total_hmd_40_heures_hs"), default=0.0) or 0.0,
            "total_HMJF_50_heures_HS": _as_float(_pick(row, "total_hmjf_50_heures_hs"), default=0.0) or 0.0,
            "payroll_run_id_HS": payroll_run.id if payroll_run is not None else None,
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.HSCalculationHS)
                    .filter(
                        models.HSCalculationHS.worker_id_HS == worker.id,
                        models.HSCalculationHS.mois_HS == mois,
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"HSCalculation deja existant ({worker.matricule}/{mois}).",
                    )
                    runtime.map_id("hs_calculations", source_id, existing.id_HS)
                    continue

                entity = models.HSCalculationHS(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("hs_calculations", source_id, entity.id_HS)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import hs_calculation impossible: {exc}",
            )


def _import_primes(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "employer_id",
        "raison_sociale",
        "employer_name",
        "label",
        "description",
        "formula_nombre",
        "formula_base",
        "formula_taux",
        "operation_1",
        "operation_2",
        "is_active",
        "is_cotisable",
        "is_imposable",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        employer = _resolve_employer(runtime, row)
        label = _clean_text(_pick(row, "label", "prime_label", "name"))
        if employer is None or not label:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="missing_required_values",
                message="Employeur et label obligatoires pour prime.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "employer_id": employer.id,
            "label": label,
            "description": _clean_text(_pick(row, "description")),
            "formula_nombre": _clean_text(_pick(row, "formula_nombre")),
            "formula_base": _clean_text(_pick(row, "formula_base")),
            "formula_taux": _clean_text(_pick(row, "formula_taux")),
            "operation_1": _clean_text(_pick(row, "operation_1")) or "*",
            "operation_2": _clean_text(_pick(row, "operation_2")) or "*",
            "is_active": _as_bool(_pick(row, "is_active"), default=True),
            "is_cotisable": _as_bool(_pick(row, "is_cotisable"), default=True),
            "is_imposable": _as_bool(_pick(row, "is_imposable"), default=True),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.Prime)
                    .filter(
                        models.Prime.employer_id == employer.id,
                        func.lower(models.Prime.label) == label.lower(),
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"Prime deja existante: {label}.",
                    )
                    runtime.map_id("primes", source_id, existing.id)
                    continue

                entity = models.Prime(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("primes", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import prime impossible: {exc}",
            )


def _import_worker_primes(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "worker_id",
        "matricule",
        "label",
        "formula_nombre",
        "formula_base",
        "formula_taux",
        "operation_1",
        "operation_2",
        "is_active",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        worker = _resolve_worker(runtime, row)
        label = _clean_text(_pick(row, "label", "prime_label", "name"))
        if worker is None or not label:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="missing_required_values",
                message="Worker et label obligatoires pour worker_prime.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "worker_id": worker.id,
            "label": label,
            "formula_nombre": _clean_text(_pick(row, "formula_nombre")),
            "formula_base": _clean_text(_pick(row, "formula_base")),
            "formula_taux": _clean_text(_pick(row, "formula_taux")),
            "operation_1": _clean_text(_pick(row, "operation_1")) or "*",
            "operation_2": _clean_text(_pick(row, "operation_2")) or "*",
            "is_active": _as_bool(_pick(row, "is_active"), default=True),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.WorkerPrime)
                    .filter(
                        models.WorkerPrime.worker_id == worker.id,
                        func.lower(models.WorkerPrime.label) == label.lower(),
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"WorkerPrime deja existante ({worker.matricule}/{label}).",
                    )
                    runtime.map_id("worker_primes", source_id, existing.id)
                    continue

                entity = models.WorkerPrime(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("worker_primes", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import worker_prime impossible: {exc}",
            )


def _import_worker_prime_links(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {"worker_id", "matricule", "prime_id", "label", "prime_label", "is_active"}

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        worker = _resolve_worker(runtime, row)
        if worker is None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="unknown_worker",
                message="Worker introuvable pour worker_prime_link.",
            )
            continue
        prime = _resolve_prime(runtime, row, worker=worker)
        if prime is None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="unknown_prime",
                message="Prime introuvable pour worker_prime_link.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "worker_id": worker.id,
            "prime_id": prime.id,
            "is_active": _as_bool(_pick(row, "is_active"), default=True),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.WorkerPrimeLink)
                    .filter(
                        models.WorkerPrimeLink.worker_id == worker.id,
                        models.WorkerPrimeLink.prime_id == prime.id,
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"Lien worker-prime deja existant ({worker.matricule}/{prime.label}).",
                    )
                    runtime.map_id("worker_prime_links", source_id, existing.id)
                    continue

                entity = models.WorkerPrimeLink(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("worker_prime_links", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import worker_prime_link impossible: {exc}",
            )


def _import_payroll_runs(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {"employer_id", "raison_sociale", "employer_name", "period", "mois", "generated_at"}

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        employer = _resolve_employer(runtime, row)
        period = _clean_text(_pick(row, "period", "mois", "pay_period"))
        if employer is None or not period or not PERIOD_PATTERN.match(period):
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="Employeur et periode YYYY-MM obligatoires pour payroll_run.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "employer_id": employer.id,
            "period": period,
            "generated_at": _as_date(_pick(row, "generated_at", "generation_date")),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.PayrollRun)
                    .filter(models.PayrollRun.employer_id == employer.id, models.PayrollRun.period == period)
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"PayrollRun deja existant ({employer.raison_sociale}/{period}).",
                    )
                    runtime.map_id("payroll_runs", source_id, existing.id)
                    continue

                entity = models.PayrollRun(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("payroll_runs", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import payroll_run impossible: {exc}",
            )


def _import_payvars(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {"worker_id", "matricule", "period", "mois"} | set(PAYVAR_NUMERIC_FIELDS)

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        worker = _resolve_worker(runtime, row)
        period = _clean_text(_pick(row, "period", "mois", "pay_period"))
        if worker is None or not period or not PERIOD_PATTERN.match(period):
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="Worker et periode YYYY-MM obligatoires pour payvar.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload: dict[str, Any] = {
            "worker_id": worker.id,
            "period": period,
        }
        for field_name in PAYVAR_NUMERIC_FIELDS:
            value = _as_float(_pick(row, field_name))
            if value is not None:
                payload[field_name] = value

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.PayVar)
                    .filter(models.PayVar.worker_id == worker.id, models.PayVar.period == period)
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"PayVar deja existant ({worker.matricule}/{period}).",
                    )
                    runtime.map_id("payvars", source_id, existing.id)
                    continue

                entity = models.PayVar(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("payvars", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import payvar impossible: {exc}",
            )


def _import_payroll_hs_hm(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "payroll_run_id",
        "run_id",
        "worker_id",
        "matricule",
        "source_type",
        "hs_calculation_id",
        "import_file_name",
        "period",
        "mois",
        "employer_id",
        "raison_sociale",
        "employer_name",
    } | set(PAYROLL_HS_HM_NUMERIC_FIELDS)

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        worker = _resolve_worker(runtime, row)
        payroll_run = _resolve_payroll_run(runtime, row)
        if worker is None or payroll_run is None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="missing_relations",
                message="Worker et payroll_run obligatoires pour payroll_hs_hm.",
            )
            continue

        source_type = (_clean_text(_pick(row, "source_type")) or "IMPORT").upper()
        if source_type not in {"MANUAL", "IMPORT"}:
            source_type = "IMPORT"
        hs_calc_source_id = _as_int(_pick(row, "hs_calculation_id", "hs_id", "id_hs"))
        hs_calc_id = _resolve_hs_calculation_id(runtime, row)
        if hs_calc_source_id is not None and hs_calc_id is None:
            accumulator.add_issue(
                row_number=index,
                code="missing_hs_calculation_reference",
                message=f"hs_calculation_id non resolu ({hs_calc_source_id}), liaison ignoree.",
                column="hs_calculation_id",
                value=hs_calc_source_id,
            )

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload: dict[str, Any] = {
            "payroll_run_id": payroll_run.id,
            "worker_id": worker.id,
            "source_type": source_type,
            "hs_calculation_id": hs_calc_id,
            "import_file_name": _clean_text(_pick(row, "import_file_name")),
        }
        for field_name in PAYROLL_HS_HM_NUMERIC_FIELDS:
            value = _as_float(_pick(row, field_name))
            if value is not None:
                payload[field_name] = value

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.PayrollHsHm)
                    .filter(
                        models.PayrollHsHm.payroll_run_id == payroll_run.id,
                        models.PayrollHsHm.worker_id == worker.id,
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"PayrollHsHm deja existant ({worker.matricule}/{payroll_run.period}).",
                    )
                    runtime.map_id("payroll_hs_hm", source_id, existing.id)
                    continue

                entity = models.PayrollHsHm(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("payroll_hs_hm", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import payroll_hs_hm impossible: {exc}",
            )


def _import_payroll_primes(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "worker_id",
        "matricule",
        "period",
        "mois",
        "prime_label",
        "label",
        "nombre",
        "base",
        "taux",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        worker = _resolve_worker(runtime, row)
        period = _clean_text(_pick(row, "period", "mois"))
        label = _clean_text(_pick(row, "prime_label", "label", "name"))
        if worker is None or not period or not PERIOD_PATTERN.match(period) or not label:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="Worker, periode YYYY-MM et prime_label obligatoires pour payroll_prime.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "worker_id": worker.id,
            "period": period,
            "prime_label": label,
            "nombre": _as_float(_pick(row, "nombre")),
            "base": _as_float(_pick(row, "base")),
            "taux": _as_float(_pick(row, "taux")),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.PayrollPrime)
                    .filter(
                        models.PayrollPrime.worker_id == worker.id,
                        models.PayrollPrime.period == period,
                        func.lower(models.PayrollPrime.prime_label) == label.lower(),
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"PayrollPrime deja existant ({worker.matricule}/{period}/{label}).",
                    )
                    runtime.map_id("payroll_primes", source_id, existing.id)
                    continue

                entity = models.PayrollPrime(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("payroll_primes", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import payroll_prime impossible: {exc}",
            )


def _import_absences(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {"worker_id", "matricule", "mois", "period"} | {
        _normalize_field_name(field_name) for field_name in ABSENCE_NUMERIC_FIELDS
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        worker = _resolve_worker(runtime, row)
        mois = _clean_text(_pick(row, "mois", "period", "pay_period"))
        if worker is None or not mois or not PERIOD_PATTERN.match(mois):
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="Worker et mois YYYY-MM obligatoires pour absence.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload: dict[str, Any] = {
            "worker_id": worker.id,
            "mois": mois,
        }
        for field_name in ABSENCE_NUMERIC_FIELDS:
            value = _as_float(_pick(row, field_name))
            if value is not None:
                payload[field_name] = value

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.Absence)
                    .filter(models.Absence.worker_id == worker.id, models.Absence.mois == mois)
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"Absence deja existante ({worker.matricule}/{mois}).",
                    )
                    runtime.map_id("absences", source_id, existing.id)
                    continue

                entity = models.Absence(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("absences", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import absence impossible: {exc}",
            )


def _import_worker_period_day_model(
    *,
    runtime: ImportRuntime,
    accumulator: ModuleAccumulator,
    rows: list[dict[str, Any]],
    model_class: Any,
    map_name: str,
    module_label: str,
) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "worker_id",
        "matricule",
        "period",
        "mois",
        "start_date",
        "date_debut",
        "end_date",
        "date_fin",
        "days_taken",
        "notes",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        worker = _resolve_worker(runtime, row)
        period = _clean_text(_pick(row, "period", "mois"))
        start_date = _as_date(_pick(row, "start_date", "date_debut"))
        end_date = _as_date(_pick(row, "end_date", "date_fin"))
        days_taken = _as_float(_pick(row, "days_taken", "jours"), default=0.0)
        if worker is None or not period or not PERIOD_PATTERN.match(period) or not start_date or not end_date:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message=f"Worker, period, start_date, end_date obligatoires pour {module_label}.",
            )
            continue

        if days_taken is None:
            days_taken = 0.0

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "worker_id": worker.id,
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "days_taken": days_taken,
            "notes": _clean_text(_pick(row, "notes")),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(model_class)
                    .filter(
                        model_class.worker_id == worker.id,
                        model_class.period == period,
                        model_class.start_date == start_date,
                        model_class.end_date == end_date,
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"{module_label} deja existant ({worker.matricule}/{period}).",
                    )
                    runtime.map_id(map_name, source_id, existing.id)
                    continue

                entity = model_class(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id(map_name, source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import {module_label} impossible: {exc}",
            )


def _import_leaves(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    _import_worker_period_day_model(
        runtime=runtime,
        accumulator=accumulator,
        rows=rows,
        model_class=models.Leave,
        map_name="leaves",
        module_label="leave",
    )


def _import_permissions(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    _import_worker_period_day_model(
        runtime=runtime,
        accumulator=accumulator,
        rows=rows,
        model_class=models.Permission,
        map_name="permissions",
        module_label="permission",
    )


def _import_custom_contracts(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "worker_id",
        "matricule",
        "employer_id",
        "raison_sociale",
        "employer_name",
        "title",
        "titre",
        "content",
        "template_type",
        "is_default",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        worker = _resolve_worker(runtime, row)
        employer = _resolve_employer(runtime, row)
        title = _clean_text(_pick(row, "title", "titre"))
        content = _clean_text(_pick(row, "content"))
        template_type = _clean_text(_pick(row, "template_type")) or "employment_contract"
        is_default = _as_bool(_pick(row, "is_default"), default=False)

        if worker is None or not title or not content:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="Worker, title et content obligatoires pour custom_contract.",
            )
            continue

        employer_id = employer.id if employer else worker.employer_id
        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "worker_id": worker.id,
            "employer_id": employer_id,
            "title": title,
            "content": content,
            "template_type": template_type,
            "is_default": bool(is_default),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.CustomContract)
                    .filter(
                        models.CustomContract.worker_id == worker.id,
                        models.CustomContract.template_type == template_type,
                        func.lower(models.CustomContract.title) == title.lower(),
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"CustomContract deja existant ({worker.matricule}/{title}).",
                    )
                    entity_id = existing.id
                else:
                    entity = models.CustomContract(**payload)
                    runtime.db.add(entity)
                    runtime.db.flush()
                    accumulator.created += 1
                    accumulator.processed_rows += 1
                    entity_id = entity.id

                if is_default:
                    runtime.db.query(models.CustomContract).filter(
                        models.CustomContract.worker_id == worker.id,
                        models.CustomContract.template_type == template_type,
                        models.CustomContract.id != entity_id,
                    ).update({"is_default": False})

                runtime.map_id("custom_contracts", source_id, entity_id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import custom_contract impossible: {exc}",
            )


def _import_document_templates(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "employer_id",
        "raison_sociale",
        "employer_name",
        "name",
        "nom",
        "description",
        "template_type",
        "content",
        "is_active",
        "is_system",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        source_employer_id = _as_int(_pick(row, "employer_id", "company_id", "societe_id"))
        employer = _resolve_employer(runtime, row)
        if source_employer_id is not None and employer is None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="unknown_employer",
                message=f"Employeur introuvable pour document_template ({source_employer_id}).",
                column="employer_id",
                value=source_employer_id,
            )
            continue

        name = _clean_text(_pick(row, "name", "nom"))
        template_type = _clean_text(_pick(row, "template_type")) or "contract"
        content = _clean_text(_pick(row, "content"))
        if not name or not content:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="name et content obligatoires pour document_template.",
            )
            continue

        employer_id = employer.id if employer is not None else None
        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "employer_id": employer_id,
            "name": name,
            "description": _clean_text(_pick(row, "description")),
            "template_type": template_type,
            "content": content,
            "is_active": _as_bool(_pick(row, "is_active"), default=True),
            "is_system": _as_bool(_pick(row, "is_system"), default=False),
        }

        try:
            with runtime.db.begin_nested():
                query = runtime.db.query(models.DocumentTemplate).filter(
                    func.lower(models.DocumentTemplate.name) == name.lower(),
                    models.DocumentTemplate.template_type == template_type,
                )
                if employer_id is None:
                    query = query.filter(models.DocumentTemplate.employer_id.is_(None))
                else:
                    query = query.filter(models.DocumentTemplate.employer_id == employer_id)

                existing = query.first()
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"DocumentTemplate deja existant ({name}/{template_type}).",
                    )
                    runtime.map_id("document_templates", source_id, existing.id)
                    continue

                entity = models.DocumentTemplate(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("document_templates", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import document_template impossible: {exc}",
            )


def _import_recruitment_candidates(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "employer_id",
        "raison_sociale",
        "employer_name",
        "first_name",
        "prenom",
        "last_name",
        "nom",
        "email",
        "phone",
        "education_level",
        "experience_years",
        "source",
        "status",
        "summary",
        "cv_file_path",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        employer = _resolve_employer(runtime, row)
        email = (_clean_text(_pick(row, "email")) or "").lower()
        first_name = _clean_text(_pick(row, "first_name", "prenom")) or "N/A"
        last_name = _clean_text(_pick(row, "last_name", "nom")) or "N/A"
        if employer is None or not email:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="Employeur et email obligatoires pour recruitment_candidate.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "employer_id": employer.id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": _clean_text(_pick(row, "phone")),
            "education_level": _clean_text(_pick(row, "education_level")),
            "experience_years": _as_float(_pick(row, "experience_years"), default=0.0),
            "source": _clean_text(_pick(row, "source")),
            "status": _clean_text(_pick(row, "status")) or "new",
            "summary": _clean_text(_pick(row, "summary")),
            "cv_file_path": _clean_text(_pick(row, "cv_file_path")),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.RecruitmentCandidate)
                    .filter(
                        models.RecruitmentCandidate.employer_id == employer.id,
                        func.lower(models.RecruitmentCandidate.email) == email,
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"RecruitmentCandidate deja existant ({email}).",
                    )
                    runtime.map_id("recruitment_candidates", source_id, existing.id)
                    continue

                entity = models.RecruitmentCandidate(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("recruitment_candidates", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import recruitment_candidate impossible: {exc}",
            )


def _import_recruitment_jobs(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "employer_id",
        "raison_sociale",
        "employer_name",
        "title",
        "intitule",
        "department",
        "location",
        "contract_type",
        "status",
        "salary_range",
        "description",
        "skills_required",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        employer = _resolve_employer(runtime, row)
        title = _clean_text(_pick(row, "title", "intitule"))
        if employer is None or not title:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="Employeur et title obligatoires pour recruitment_job_posting.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "employer_id": employer.id,
            "title": title,
            "department": _clean_text(_pick(row, "department")),
            "location": _clean_text(_pick(row, "location")),
            "contract_type": _clean_text(_pick(row, "contract_type")) or "CDI",
            "status": _clean_text(_pick(row, "status")) or "draft",
            "salary_range": _clean_text(_pick(row, "salary_range")),
            "description": _clean_text(_pick(row, "description")),
            "skills_required": _clean_text(_pick(row, "skills_required")),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.RecruitmentJobPosting)
                    .filter(
                        models.RecruitmentJobPosting.employer_id == employer.id,
                        func.lower(models.RecruitmentJobPosting.title) == title.lower(),
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"RecruitmentJobPosting deja existant ({title}).",
                    )
                    runtime.map_id("recruitment_job_postings", source_id, existing.id)
                    continue

                entity = models.RecruitmentJobPosting(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("recruitment_job_postings", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import recruitment_job_posting impossible: {exc}",
            )


def _import_talent_skills(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "employer_id",
        "raison_sociale",
        "employer_name",
        "code",
        "name",
        "nom",
        "description",
        "scale_max",
        "is_active",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        employer = _resolve_employer(runtime, row)
        name = _clean_text(_pick(row, "name", "nom"))
        code = _clean_text(_pick(row, "code")) or (_slug_token(name or "skill"))
        if employer is None or not name:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="Employeur et nom obligatoires pour talent_skill.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "employer_id": employer.id,
            "code": code,
            "name": name,
            "description": _clean_text(_pick(row, "description")),
            "scale_max": _as_int(_pick(row, "scale_max"), default=5) or 5,
            "is_active": _as_bool(_pick(row, "is_active"), default=True),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.TalentSkill)
                    .filter(
                        models.TalentSkill.employer_id == employer.id,
                        func.lower(models.TalentSkill.code) == code.lower(),
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"TalentSkill deja existante ({code}).",
                    )
                    runtime.map_id("talent_skills", source_id, existing.id)
                    continue

                entity = models.TalentSkill(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("talent_skills", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import talent_skill impossible: {exc}",
            )


def _import_talent_employee_skills(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "worker_id",
        "matricule",
        "skill_id",
        "code",
        "skill_code",
        "code_competence",
        "level",
        "source",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        worker = _resolve_worker(runtime, row)
        skill = _resolve_talent_skill(runtime, row, worker=worker)
        if worker is None or skill is None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="missing_relations",
                message="Worker et skill obligatoires pour talent_employee_skill.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "worker_id": worker.id,
            "skill_id": skill.id,
            "level": _as_int(_pick(row, "level"), default=1) or 1,
            "source": _clean_text(_pick(row, "source")) or "import_package",
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.TalentEmployeeSkill)
                    .filter(
                        models.TalentEmployeeSkill.worker_id == worker.id,
                        models.TalentEmployeeSkill.skill_id == skill.id,
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"TalentEmployeeSkill deja existante ({worker.matricule}/{skill.code}).",
                    )
                    runtime.map_id("talent_employee_skills", source_id, existing.id)
                    continue

                entity = models.TalentEmployeeSkill(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("talent_employee_skills", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import talent_employee_skill impossible: {exc}",
            )


def _import_talent_trainings(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "employer_id",
        "raison_sociale",
        "employer_name",
        "title",
        "titre",
        "provider",
        "organisme",
        "duration_hours",
        "mode",
        "price",
        "objectives",
        "status",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        employer = _resolve_employer(runtime, row)
        title = _clean_text(_pick(row, "title", "titre"))
        if employer is None or not title:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="Employeur et title obligatoires pour talent_training.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "employer_id": employer.id,
            "title": title,
            "provider": _clean_text(_pick(row, "provider", "organisme")),
            "duration_hours": _as_float(_pick(row, "duration_hours"), default=0.0) or 0.0,
            "mode": _clean_text(_pick(row, "mode")),
            "price": _as_float(_pick(row, "price"), default=0.0) or 0.0,
            "objectives": _clean_text(_pick(row, "objectives")),
            "status": _clean_text(_pick(row, "status")) or "draft",
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.TalentTraining)
                    .filter(
                        models.TalentTraining.employer_id == employer.id,
                        func.lower(models.TalentTraining.title) == title.lower(),
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"TalentTraining deja existante ({title}).",
                    )
                    runtime.map_id("talent_trainings", source_id, existing.id)
                    continue

                entity = models.TalentTraining(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("talent_trainings", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import talent_training impossible: {exc}",
            )


def _import_talent_training_sessions(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "training_id",
        "title",
        "employer_id",
        "raison_sociale",
        "employer_name",
        "start_date",
        "end_date",
        "site",
        "trainer",
        "capacity",
        "status",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        training = _resolve_talent_training(runtime, row)
        if training is None:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="unknown_training",
                message="Training introuvable pour talent_training_session.",
            )
            continue

        start_date = _as_date(_pick(row, "start_date"))
        site = _clean_text(_pick(row, "site"))
        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "training_id": training.id,
            "start_date": start_date,
            "end_date": _as_date(_pick(row, "end_date")),
            "site": site,
            "trainer": _clean_text(_pick(row, "trainer")),
            "capacity": _as_int(_pick(row, "capacity")),
            "status": _clean_text(_pick(row, "status")) or "planned",
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.TalentTrainingSession)
                    .filter(
                        models.TalentTrainingSession.training_id == training.id,
                        models.TalentTrainingSession.start_date == start_date,
                        models.TalentTrainingSession.site == site,
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=(
                            f"TalentTrainingSession deja existante "
                            f"({training.title}/{start_date}/{site or '-'})"
                        ),
                    )
                    runtime.map_id("talent_training_sessions", source_id, existing.id)
                    continue

                entity = models.TalentTrainingSession(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("talent_training_sessions", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import talent_training_session impossible: {exc}",
            )


def _import_sst_incidents(runtime: ImportRuntime, accumulator: ModuleAccumulator, rows: list[dict[str, Any]]) -> None:
    known_fields = BASE_ROW_FIELDS | {
        "employer_id",
        "raison_sociale",
        "employer_name",
        "worker_id",
        "matricule",
        "incident_type",
        "severity",
        "status",
        "occurred_at",
        "occurred_on",
        "location",
        "description",
        "action_taken",
        "witnesses",
    }

    for index, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        if _is_empty_row(row):
            continue
        _track_unmapped_fields(accumulator, row, known_fields)

        employer = _resolve_employer(runtime, row)
        worker = _resolve_worker(runtime, row)
        incident_type = _clean_text(_pick(row, "incident_type", "type_incident"))
        occurred_at = _as_datetime(_pick(row, "occurred_at", "occurred_on", "date_heure"))
        description = _clean_text(_pick(row, "description"))
        if employer is None or not incident_type or occurred_at is None or not description:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="invalid_required_values",
                message="employeur, incident_type, occurred_at et description obligatoires pour sst_incident.",
            )
            continue

        if worker and worker.employer_id != employer.id:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="worker_employer_mismatch",
                message="Le worker ne correspond pas a l employeur de l incident.",
            )
            continue

        source_id = _as_int(_pick(row, "id", "source_id", "legacy_id"))
        payload = {
            "employer_id": employer.id,
            "worker_id": worker.id if worker else None,
            "incident_type": incident_type,
            "severity": _clean_text(_pick(row, "severity")) or "medium",
            "status": _clean_text(_pick(row, "status")) or "open",
            "occurred_at": occurred_at,
            "location": _clean_text(_pick(row, "location")),
            "description": description,
            "action_taken": _clean_text(_pick(row, "action_taken")),
            "witnesses": _clean_text(_pick(row, "witnesses")),
        }

        try:
            with runtime.db.begin_nested():
                existing = (
                    runtime.db.query(models.SstIncident)
                    .filter(
                        models.SstIncident.employer_id == employer.id,
                        models.SstIncident.worker_id == (worker.id if worker else None),
                        models.SstIncident.incident_type == incident_type,
                        models.SstIncident.occurred_at == occurred_at,
                    )
                    .first()
                )
                if existing:
                    _handle_existing_merge(
                        runtime,
                        accumulator,
                        row_number=index,
                        existing=existing,
                        payload=payload,
                        conflict_message=f"SstIncident deja existant ({incident_type}/{occurred_at}).",
                    )
                    runtime.map_id("sst_incidents", source_id, existing.id)
                    continue

                entity = models.SstIncident(**payload)
                runtime.db.add(entity)
                runtime.db.flush()
                accumulator.created += 1
                accumulator.processed_rows += 1
                runtime.map_id("sst_incidents", source_id, entity.id)
        except HTTPException:
            raise
        except Exception as exc:
            _register_row_error(
                runtime,
                accumulator,
                row_number=index,
                code="row_error",
                message=f"Import sst_incident impossible: {exc}",
            )

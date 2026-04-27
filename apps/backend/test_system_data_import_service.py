import io
import json
import zipfile

from app import schemas
from app.services import system_data_import_service as service


def _build_zip(files: dict[str, object]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in files.items():
            archive.writestr(name, json.dumps(payload))
    return buffer.getvalue()


def test_parse_zip_reads_underscore_manifest_without_creating_fake_modules():
    package_bytes = _build_zip(
        {
            "_manifest.json": {
                "export_metadata": {
                    "format": "SIRH_PAIE_JSON_EXPORT_v1",
                    "app_version": "1.0.0",
                    "schema_version": "2026.04",
                },
                "modules": {"workers": {"record_counts": {"workers": 1}}},
            },
            "workers.json": {"workers": [{"id": 1, "matricule": "N001", "nom": "DOE", "employer_id": 1}]},
        }
    )

    parsed = service._parse_import_package(package_bytes=package_bytes, filename="sample.zip")

    assert "export_metadata" in parsed.manifest
    assert "workers" in parsed.modules
    assert "_manifest" not in parsed.modules


def test_manifest_summary_uses_export_metadata_fields():
    parsed = service.ParsedPackage(
        manifest={
            "export_metadata": {
                "format": "SIRH_PAIE_JSON_EXPORT_v1",
                "app_version": "1.0.0",
                "schema_version": "2026.04",
            }
        },
        modules={"workers": [{"id": 1}]},
    )
    summary = service._build_manifest_summary(parsed=parsed, requested_modules=["workers"])

    assert summary.source_system == "SIRH_PAIE_JSON_EXPORT_v1"
    assert summary.package_version == "1.0.0"
    assert summary.export_version == "2026.04"


def test_resolve_requested_modules_non_strict_uses_detected_only():
    parsed = service.ParsedPackage(
        manifest={"modules": {"payroll": {"record_counts": {"payvars": 2}}}},
        modules={"workers": [{"id": 1}]},
    )
    options = schemas.SystemImportOptions(
        update_existing=True,
        skip_exact_duplicates=True,
        continue_on_error=True,
        strict_mode=False,
        selected_modules=[],
    )

    requested = service._resolve_requested_modules(parsed=parsed, options=options)

    assert requested == ["workers"]


def test_resolve_requested_modules_strict_adds_manifest_expected_modules():
    parsed = service.ParsedPackage(
        manifest={"modules": {"payroll": {"record_counts": {"payvars": 2}}}},
        modules={"workers": [{"id": 1}]},
    )
    options = schemas.SystemImportOptions(
        update_existing=True,
        skip_exact_duplicates=True,
        continue_on_error=True,
        strict_mode=True,
        selected_modules=[],
    )

    requested = service._resolve_requested_modules(parsed=parsed, options=options)

    assert requested == ["workers", "payvars"]


def test_iter_sorted_organizational_rows_orders_by_level_then_parent():
    rows = [
        {"id": 41, "level": "unite", "level_order": 4, "parent_id": 39},
        {"id": 30, "level": "departement", "level_order": 2, "parent_id": 28},
        {"id": 28, "level": "etablissement", "level_order": 1, "parent_id": None},
        {"id": 39, "level": "service", "level_order": 3, "parent_id": 30},
    ]

    ordered = service._iter_sorted_organizational_rows(rows, include_level_order=True)
    ordered_ids = [service._as_int(service._pick(row, "id")) for _, row in ordered]

    assert ordered_ids == [28, 30, 39, 41]

from __future__ import annotations

import csv
import io
from typing import Iterable, Sequence

import pandas as pd
from fastapi import HTTPException
from openpyxl.utils import get_column_letter


SUPPORTED_TABULAR_EXTENSIONS = {".xlsx", ".xls", ".csv"}


def detect_extension(filename: str | None) -> str:
    if not filename:
        return ""
    lower = filename.lower().strip()
    for ext in SUPPORTED_TABULAR_EXTENSIONS:
        if lower.endswith(ext):
            return ext
    return ""


def ensure_supported_filename(filename: str | None) -> str:
    ext = detect_extension(filename)
    if not ext:
        allowed = ", ".join(sorted(SUPPORTED_TABULAR_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Format invalide. Formats supportés: {allowed}")
    return ext


def read_tabular_bytes(content: bytes, filename: str | None) -> pd.DataFrame:
    ext = ensure_supported_filename(filename)
    try:
        if ext == ".csv":
            return pd.read_csv(io.BytesIO(content))
        return pd.read_excel(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Fichier tabulaire invalide: {exc}") from exc


def normalize_header(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\n", " ").split()).strip().lower()


def build_column_mapping(
    actual_columns: Sequence[object],
    expected_columns: Sequence[str],
    required_columns: Sequence[str] | None = None,
) -> tuple[dict[str, str], list[str], list[str]]:
    required = list(required_columns or [])
    expected_norm = {normalize_header(item): item for item in expected_columns}
    actual_norm_to_raw: dict[str, str] = {}
    for raw in actual_columns:
        raw_str = str(raw).strip()
        actual_norm_to_raw[normalize_header(raw_str)] = raw_str

    mapping: dict[str, str] = {}
    for expected in expected_columns:
        normalized = normalize_header(expected)
        raw = actual_norm_to_raw.get(normalized)
        if raw:
            mapping[expected] = raw

    unknown_columns = []
    for raw in actual_columns:
        raw_str = str(raw).strip()
        if normalize_header(raw_str) not in expected_norm:
            unknown_columns.append(raw_str)

    missing_columns = []
    for required_col in required:
        if required_col not in mapping:
            missing_columns.append(required_col)

    return mapping, unknown_columns, missing_columns


def dataframe_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "Template") -> bytes:
    buffer = io.BytesIO()
    engine = "openpyxl"
    try:
        import xlsxwriter  # type: ignore  # noqa: F401
        engine = "xlsxwriter"
    except Exception:
        engine = "openpyxl"

    with pd.ExcelWriter(buffer, engine=engine) as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        worksheet = writer.sheets[sheet_name]
        for idx, col in enumerate(df.columns):
            column_len = max(len(str(col)), int(df[col].astype(str).map(len).max()) if not df.empty else 0) + 2
            width = min(max(column_len, 10), 60)
            if engine == "xlsxwriter":
                worksheet.set_column(idx, idx, width)
            else:
                worksheet.column_dimensions[get_column_letter(idx + 1)].width = width
    buffer.seek(0)
    return buffer.getvalue()


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def issues_to_csv(issues: Iterable[dict[str, object]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["row_number", "column", "code", "message", "value"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for item in issues:
        writer.writerow(item)
    return output.getvalue()

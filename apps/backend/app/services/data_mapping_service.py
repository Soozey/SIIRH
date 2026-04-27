from __future__ import annotations

from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
import re
import unicodedata
from typing import BinaryIO, Mapping, Sequence

import pandas as pd


class DataMappingError(ValueError):
    """Raised when an uploaded Excel file cannot be mapped safely."""


def _normalize_column_name(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    raw = str(value)
    without_accents = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    lowered = without_accents.lower().replace("_", " ").replace("-", " ")
    without_parentheses = re.sub(r"\([^)]*\)", " ", lowered)
    words = re.findall(r"[a-z0-9]+", without_parentheses)
    normalized_words = [word[:-1] if len(word) > 3 and word.endswith("s") else word for word in words]
    return " ".join(normalized_words)


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    compact_left = left.replace(" ", "")
    compact_right = right.replace(" ", "")
    return max(
        SequenceMatcher(None, left, right).ratio(),
        SequenceMatcher(None, compact_left, compact_right).ratio(),
    )


def _read_excel(user_file: str | Path | bytes | bytearray | BinaryIO) -> pd.DataFrame:
    try:
        if isinstance(user_file, (str, Path)):
            return pd.read_excel(user_file)
        if isinstance(user_file, (bytes, bytearray)):
            return pd.read_excel(BytesIO(user_file))
        return pd.read_excel(user_file)
    except Exception as exc:
        raise DataMappingError(f"Fichier Excel vide, corrompu ou illisible: {exc}") from exc


def _read_excel_with_detected_header(user_file: str | Path | bytes | bytearray | BinaryIO) -> pd.DataFrame:
    try:
        if isinstance(user_file, (str, Path)):
            raw_df = pd.read_excel(user_file, header=None, dtype=object)
        elif isinstance(user_file, (bytes, bytearray)):
            raw_df = pd.read_excel(BytesIO(user_file), header=None, dtype=object)
        else:
            if hasattr(user_file, "seek"):
                user_file.seek(0)
            raw_df = pd.read_excel(user_file, header=None, dtype=object)
    except Exception as exc:
        raise DataMappingError(f"Fichier Excel vide, corrompu ou illisible: {exc}") from exc

    if raw_df.empty:
        raise DataMappingError("Le fichier Excel ne contient aucune donnee exploitable.")

    best_row_index: int | None = None
    best_score = 0
    for row_index in range(min(20, len(raw_df))):
        row = raw_df.iloc[row_index]
        score = sum(1 for value in row if _normalize_column_name(value))
        if score > best_score:
            best_score = score
            best_row_index = row_index

    if best_row_index is None or best_score == 0:
        raise DataMappingError("Impossible de detecter une ligne d'entetes dans le fichier Excel.")

    headers = []
    for column_index, value in enumerate(raw_df.iloc[best_row_index], start=1):
        header = str(value).strip() if not pd.isna(value) else ""
        headers.append(header or f"Colonne {column_index}")

    data_df = raw_df.iloc[best_row_index + 1 :].copy()
    data_df.columns = headers
    data_df = data_df.dropna(how="all")
    return data_df.reset_index(drop=True)


def build_fuzzy_column_mapping(
    source_columns: Sequence[object],
    template_columns: Sequence[str],
    *,
    aliases: Mapping[str, Sequence[str]] | None = None,
    threshold: float = 0.84,
) -> dict[str, str]:
    candidates: list[tuple[float, str, str]] = []
    alias_map = aliases or {}
    normalized_targets: dict[str, list[str]] = {}

    for target in template_columns:
        names = [target, *alias_map.get(target, [])]
        normalized_targets[target] = [_normalize_column_name(name) for name in names]

    for source in source_columns:
        source_name = str(source).strip()
        normalized_source = _normalize_column_name(source_name)
        if not normalized_source:
            continue
        for target, normalized_names in normalized_targets.items():
            score = max(_similarity(normalized_source, normalized_target) for normalized_target in normalized_names)
            if score >= threshold:
                candidates.append((score, target, source_name))

    mapping: dict[str, str] = {}
    used_sources: set[str] = set()
    for _, target, source_name in sorted(candidates, key=lambda item: item[0], reverse=True):
        if target in mapping or source_name in used_sources:
            continue
        mapping[target] = source_name
        used_sources.add(source_name)
    return mapping


def map_user_excel_to_template(
    user_file: str | Path | bytes | bytearray | BinaryIO,
    template_columns: Sequence[str],
    *,
    aliases: Mapping[str, Sequence[str]] | None = None,
    threshold: float = 0.84,
) -> pd.DataFrame:
    """
    Read a user Excel file and return a DataFrame shaped exactly like the SIIRH template.

    Detected columns are copied to their matched template columns. Template columns without
    a match are kept empty so the output can be exported and imported by SIIRH.
    """

    if not template_columns:
        raise DataMappingError("La liste des colonnes cibles du template est vide.")

    source_df = _read_excel(user_file)
    if source_df.empty and len(source_df.columns) == 0:
        raise DataMappingError("Le fichier Excel ne contient aucune colonne.")
    if source_df.empty:
        raise DataMappingError("Le fichier Excel ne contient aucune ligne de donnees.")

    mapping = build_fuzzy_column_mapping(
        list(source_df.columns),
        list(template_columns),
        aliases=aliases,
        threshold=threshold,
    )
    if not mapping:
        source_df = _read_excel_with_detected_header(user_file)
        if source_df.empty:
            raise DataMappingError("Le fichier Excel ne contient aucune ligne de donnees apres les entetes.")
        mapping = build_fuzzy_column_mapping(
            list(source_df.columns),
            list(template_columns),
            aliases=aliases,
            threshold=threshold,
        )
    if not mapping:
        raise DataMappingError("Aucune colonne du fichier source ne correspond au template SIIRH.")

    mapped_df = pd.DataFrame("", index=source_df.index, columns=list(template_columns))
    for target_column, source_column in mapping.items():
        mapped_df[target_column] = source_df[source_column]
    return mapped_df


def map_user_excel_to_template_bytes(
    user_file: str | Path | bytes | bytearray | BinaryIO,
    template_columns: Sequence[str],
    *,
    aliases: Mapping[str, Sequence[str]] | None = None,
    threshold: float = 0.84,
    sheet_name: str = "Salaries",
) -> bytes:
    mapped_df = map_user_excel_to_template(
        user_file,
        template_columns,
        aliases=aliases,
        threshold=threshold,
    )
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        mapped_df.to_excel(writer, index=False, sheet_name=sheet_name)
    buffer.seek(0)
    return buffer.getvalue()

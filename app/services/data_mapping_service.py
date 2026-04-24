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
    raw = "" if value is None else str(value)
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

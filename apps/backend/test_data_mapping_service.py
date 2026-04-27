from __future__ import annotations

from io import BytesIO

import pandas as pd
import pytest

from app.services.data_mapping_service import DataMappingError, map_user_excel_to_template


def _xlsx_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer.getvalue()


def test_map_user_excel_to_template_maps_fuzzy_headers_and_keeps_missing_columns_empty():
    source = pd.DataFrame(
        {
            "Matricules": ["M001"],
            "NOM": ["RAKOTO"],
            "Prénoms": ["Jean"],
            "Date d'embauche": ["01/01/2024"],
            "Colonne inutile": ["ignore"],
        }
    )

    mapped = map_user_excel_to_template(
        _xlsx_bytes(source),
        ["Matricule", "Nom", "Prenom", "Date Embauche (JJ/MM/AAAA)", "Salaire Base"],
        aliases={"Date Embauche (JJ/MM/AAAA)": ["Date d'embauche"]},
    )

    assert list(mapped.columns) == ["Matricule", "Nom", "Prenom", "Date Embauche (JJ/MM/AAAA)", "Salaire Base"]
    assert mapped.loc[0, "Matricule"] == "M001"
    assert mapped.loc[0, "Nom"] == "RAKOTO"
    assert mapped.loc[0, "Prenom"] == "Jean"
    assert mapped.loc[0, "Date Embauche (JJ/MM/AAAA)"] == "01/01/2024"
    assert mapped.loc[0, "Salaire Base"] == ""


def test_map_user_excel_to_template_rejects_empty_file():
    empty_excel = _xlsx_bytes(pd.DataFrame(columns=["Nom"]))

    with pytest.raises(DataMappingError, match="aucune ligne"):
        map_user_excel_to_template(empty_excel, ["Nom"])


def test_map_user_excel_to_template_detects_shifted_header_row():
    buffer = BytesIO()
    shifted = pd.DataFrame(
        [
            ["", "", ""],
            ["Export utilisateur", "", ""],
            ["Matricules", "NOM", "Prénoms"],
            ["M001", "RAKOTO", "Jean"],
        ]
    )
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        shifted.to_excel(writer, index=False, header=False)
    buffer.seek(0)

    mapped = map_user_excel_to_template(buffer.getvalue(), ["Matricule", "Nom", "Prenom"])

    assert mapped.loc[0, "Matricule"] == "M001"
    assert mapped.loc[0, "Nom"] == "RAKOTO"
    assert mapped.loc[0, "Prenom"] == "Jean"


def test_map_user_excel_to_template_rejects_corrupt_file():
    with pytest.raises(DataMappingError, match="illisible"):
        map_user_excel_to_template(b"not an excel file", ["Nom"])

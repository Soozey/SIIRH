import pandas as pd

from app.services.tabular_io import (
    build_column_mapping,
    dataframe_to_xlsx_bytes,
    issues_to_csv,
    read_tabular_bytes,
)


def test_build_column_mapping_detects_missing_and_unknown():
    mapping, unknown, missing = build_column_mapping(
        actual_columns=["Matricule", "Nom", "Colonne Libre"],
        expected_columns=["Matricule", "Nom", "Prenom"],
        required_columns=["Matricule", "Nom", "Prenom"],
    )
    assert mapping["Matricule"] == "Matricule"
    assert mapping["Nom"] == "Nom"
    assert "Colonne Libre" in unknown
    assert missing == ["Prenom"]


def test_read_tabular_bytes_supports_csv():
    content = "Matricule,Nom\nM001,RAKOTO\n".encode("utf-8")
    df = read_tabular_bytes(content, "workers.csv")
    assert isinstance(df, pd.DataFrame)
    assert len(df.index) == 1
    assert df.iloc[0]["Matricule"] == "M001"


def test_issues_to_csv_contains_headers_and_rows():
    csv_text = issues_to_csv(
        [
            {
                "row_number": 2,
                "column": "Matricule",
                "code": "missing_matricule",
                "message": "Matricule obligatoire",
                "value": "",
            }
        ]
    )
    assert "row_number,column,code,message,value" in csv_text
    assert "missing_matricule" in csv_text


def test_dataframe_to_xlsx_bytes_returns_valid_xlsx_archive():
    df = pd.DataFrame([{"Matricule": "M001", "Nom": "RAKOTO"}])
    payload = dataframe_to_xlsx_bytes(df, sheet_name="Template")
    assert isinstance(payload, bytes)
    assert payload.startswith(b"PK")
    assert len(payload) > 100

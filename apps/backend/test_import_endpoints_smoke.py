from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_workers_import_template_route_exists():
    response = client.get("/workers/import/template")
    assert response.status_code in {401, 403}


def test_talents_import_template_route_exists():
    response = client.get("/talents/import/template", params={"resource": "skills"})
    assert response.status_code in {401, 403}


def test_sst_import_route_exists():
    response = client.post("/sst/incidents/import")
    assert response.status_code in {401, 403, 422}


def test_recruitment_import_template_route_exists():
    response = client.get("/recruitment/import/template", params={"resource": "candidates"})
    assert response.status_code in {401, 403}


def test_absences_import_template_route_exists():
    response = client.get("/absences/import/template")
    assert response.status_code in {401, 403}


def test_custom_contracts_import_template_route_exists():
    response = client.get("/custom-contracts/import/template")
    assert response.status_code in {401, 403}


def test_primes_import_preview_route_exists():
    response = client.post("/primes/import/preview")
    assert response.status_code in {401, 403, 422}


def test_type_regimes_import_template_route_exists():
    response = client.get("/type_regimes/import/template")
    assert response.status_code in {401, 403}


def test_system_data_import_preview_route_exists():
    response = client.post("/system-data-import/preview")
    assert response.status_code in {401, 403, 422}

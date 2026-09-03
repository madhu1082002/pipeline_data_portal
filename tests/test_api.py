import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "Pipeline Data Portal"


@patch("services.databricks_service.get_connection_status", return_value={"configured": True, "connected": True})
def test_databricks_status(_status, client):
    res = client.get("/databricks/status")
    assert res.status_code == 200
    assert res.get_json()["connected"] is True


@patch("services.databricks_service.list_pipelines", return_value=[{"pipeline_name": "sales_etl", "status": "success"}])
def test_list_pipelines(_list, client):
    res = client.get("/pipelines")
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] == 1
    assert data["pipelines"][0]["pipeline_name"] == "sales_etl"


def test_create_pipeline_requires_fields(client):
    res = client.post("/pipelines", json={"pipeline_name": "x"})
    assert res.status_code == 400


@patch("services.databricks_service.insert_pipeline")
def test_create_pipeline(_insert, client):
    res = client.post("/pipelines", json={"pipeline_name": "sales_etl", "status": "success"})
    assert res.status_code == 201
    assert res.get_json()["status"] == "created"


@patch("services.databricks_service.update_pipeline")
def test_update_pipeline(_update, client):
    res = client.put("/pipelines/sales_etl", json={"pipeline_name": "sales_etl", "status": "failed"})
    assert res.status_code == 200
    assert res.get_json()["status"] == "updated"


@patch("services.databricks_service.delete_pipeline")
def test_delete_pipeline(_delete, client):
    res = client.delete("/pipelines/sales_etl")
    assert res.status_code == 200
    assert res.get_json()["status"] == "deleted"


@patch("services.databricks_service.list_failures", return_value=[{"pipeline_name": "customer_ingestion"}])
def test_list_failures(_list, client):
    res = client.get("/failures")
    assert res.status_code == 200
    assert res.get_json()["count"] == 1


def test_create_failure_requires_name(client):
    res = client.post("/failures", json={})
    assert res.status_code == 400


@patch("services.databricks_service.insert_failure")
def test_create_failure(_insert, client):
    res = client.post("/failures", json={"pipeline_name": "customer_ingestion"})
    assert res.status_code == 201


def test_update_failure_requires_time(client):
    res = client.put("/failures/customer_ingestion", json={"pipeline_name": "customer_ingestion"})
    assert res.status_code == 400


@patch("services.databricks_service.update_failure")
def test_update_failure(_update, client):
    res = client.put(
        "/failures/customer_ingestion?failure_time=2026-07-01T00:00:00Z",
        json={"pipeline_name": "customer_ingestion"},
    )
    assert res.status_code == 200


@patch("services.databricks_service.delete_failure")
def test_delete_failure(_delete, client):
    res = client.delete("/failures/customer_ingestion?failure_time=2026-07-01T00:00:00Z")
    assert res.status_code == 200


def test_delete_failure_requires_time(client):
    res = client.delete("/failures/customer_ingestion")
    assert res.status_code == 400


@patch("services.databricks_service.list_clusters", return_value=[{"cluster_id": "c1"}])
def test_list_clusters(_list, client):
    res = client.get("/clusters")
    assert res.status_code == 200
    assert res.get_json()["count"] == 1


def test_create_cluster_requires_id(client):
    res = client.post("/clusters", json={})
    assert res.status_code == 400


@patch("services.databricks_service.insert_cluster")
def test_create_cluster(_insert, client):
    res = client.post("/clusters", json={"cluster_id": "c1"})
    assert res.status_code == 201


@patch("services.databricks_service.update_cluster")
def test_update_cluster(_update, client):
    res = client.put("/clusters/c1", json={"cluster_id": "c1"})
    assert res.status_code == 200


@patch("services.databricks_service.delete_cluster")
def test_delete_cluster(_delete, client):
    res = client.delete("/clusters/c1")
    assert res.status_code == 200


@patch("services.databricks_service.list_pipelines", side_effect=RuntimeError("warehouse down"))
def test_list_pipelines_db_error(_list, client):
    res = client.get("/pipelines")
    assert res.status_code == 503

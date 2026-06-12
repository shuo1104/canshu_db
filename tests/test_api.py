"""FastAPI endpoint tests."""
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from src import api as api_module
from src.api import app

client = TestClient(app)


@pytest.fixture
def sample_search_result():
    return {
        "table_id": 1,
        "display_name": "设备参数",
        "table_name": "dt_device_abc123",
        "source_file": "设备参数信息汇总.xls",
        "sheet_name": "Sheet1",
        "row_id": 7,
        "matched_columns": ["设备型号", "光源"],
        "matched_keywords": {
            "Pro2": {"field_matches": [], "value_matches": ["设备型号"]},
            "UV": {"field_matches": [], "value_matches": ["光源"]},
        },
        "row": {
            "设备型号": "Pro2",
            "光源": "385nm UV-LED",
            "功率": "400W",
        },
    }


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_frontend_routes_are_served_when_built_assets_exist():
    root_response = client.get("/")
    import_response = client.get("/import")

    assert root_response.status_code == 200
    assert "text/html" in root_response.headers["content-type"]
    assert import_response.status_code == 200
    assert "text/html" in import_response.headers["content-type"]


def test_frontend_static_files_are_served_when_built_assets_exist():
    response = client.get("/logo.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_search_requires_keyword1():
    response = client.get("/api/search")
    assert response.status_code == 422


def test_search_with_keyword1(monkeypatch, sample_search_result):
    monkeypatch.setattr(
        api_module, "search_records", lambda keyword, mode, limit: [sample_search_result]
    )
    response = client.get("/api/search?keyword1=Pro2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["display_name"] == "设备参数"


def test_search_with_keyword2(monkeypatch, sample_search_result):
    calls = {}

    def fake_search(keyword, mode, limit):
        calls["keyword"] = keyword
        calls["mode"] = mode
        calls["limit"] = limit
        return [sample_search_result]

    monkeypatch.setattr(api_module, "search_records", fake_search)
    response = client.get("/api/search?keyword1=Pro2&keyword2=UV&mode=exact&limit=10")
    assert response.status_code == 200
    assert calls["keyword"] == ["Pro2", "UV"]
    assert calls["mode"] == "exact"
    assert calls["limit"] == 10


def test_search_invalid_mode(monkeypatch):
    response = client.get("/api/search?keyword1=Pro2&mode=bad")
    assert response.status_code == 422
    assert "mode" in str(response.json())


def test_search_unexpected_error(monkeypatch):
    monkeypatch.setattr(
        api_module, "search_records", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("db down"))
    )
    response = client.get("/api/search?keyword1=Pro2")
    assert response.status_code == 500


def test_candidates(monkeypatch):
    monkeypatch.setattr(
        api_module, "search_records", lambda keyword, mode, limit: [{"row": {"a": "1"}}]
    )
    monkeypatch.setattr(
        api_module, "extract_field_candidates", lambda results, max_candidates: ["a", "b"]
    )
    response = client.get("/api/search/candidates?keyword1=Pro2&max_candidates=5")
    assert response.status_code == 200
    assert response.json() == ["a", "b"]


def test_import_analyze(monkeypatch):
    monkeypatch.setattr(
        api_module, "list_sheet_names", lambda source: ["Sheet1", "Sheet2"]
    )
    response = client.post(
        "/api/import/analyze",
        files={"file": ("sample.xlsx", BytesIO(b"fake excel"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    assert response.json() == {"sheets": ["Sheet1", "Sheet2"]}


def test_import_preview(monkeypatch):
    monkeypatch.setattr(
        api_module, "get_sheet_preview", lambda source, sheet_name: [["a", "b"], ["c", "d"]]
    )
    response = client.post(
        "/api/import/preview",
        data={"sheet_name": "Sheet1"},
        files={"file": ("sample.xlsx", BytesIO(b"fake excel"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    assert response.json() == {"preview": [["a", "b"], ["c", "d"]]}


def test_import(monkeypatch):
    def fake_import(file_path, sheet_name, display_name, header_row_index, replace_existing, source_file_name):
        return {
            "display_name": display_name,
            "table_name": "dt_test_123",
            "source_file": source_file_name,
            "sheet_name": sheet_name,
            "header_row_index": header_row_index,
            "row_count": 42,
        }

    monkeypatch.setattr(api_module, "import_selected_sheet", fake_import)
    response = client.post(
        "/api/import",
        data={
            "sheet_name": "Sheet1",
            "display_name": "设备参数",
            "header_row_index": 1,
            "replace_existing": True,
        },
        files={"file": ("sample.xlsx", BytesIO(b"fake excel"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "设备参数"
    assert data["row_count"] == 42


def test_import_validation_error(monkeypatch):
    def fake_import(*args, **kwargs):
        raise ValueError("数据表名称不能为空")

    monkeypatch.setattr(api_module, "import_selected_sheet", fake_import)
    response = client.post(
        "/api/import",
        data={
            "sheet_name": "Sheet1",
            "display_name": "   ",
            "header_row_index": 0,
        },
        files={"file": ("sample.xlsx", BytesIO(b"fake excel"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 400
    assert "数据表名称" in response.json()["detail"]

from fastapi.testclient import TestClient

import backend.app as app_module
from backend.projects.store import ProjectStore

client = TestClient(app_module.app)


def test_projects_api_crud(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "project_store", ProjectStore(tmp_path / "projects"))

    created_response = client.post("/api/projects", json={"name": "API project"})
    assert created_response.status_code == 201
    created = created_response.json()["project"]
    project_id = created["project"]["id"]

    listed = client.get("/api/projects")
    assert listed.status_code == 200
    assert len(listed.json()["projects"]) == 1

    opened = client.get(f"/api/projects/{project_id}")
    assert opened.status_code == 200
    assert opened.json()["project"]["project"]["id"] == project_id

    created["project"]["name"] = "Saved through API"
    saved = client.put(
        f"/api/projects/{project_id}",
        json={"project": created},
    )
    assert saved.status_code == 200
    assert saved.json()["project"]["project"]["name"] == "Saved through API"

    deleted = client.delete(f"/api/projects/{project_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/projects/{project_id}").status_code == 404


def test_projects_api_validates_project_name(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "project_store", ProjectStore(tmp_path / "projects"))

    response = client.post("/api/projects", json={"name": "   "})

    assert response.status_code == 422

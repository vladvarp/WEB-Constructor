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


def test_page_management_api(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "project_store", ProjectStore(tmp_path / "projects"))
    project = client.post("/api/projects", json={"name": "Page API"}).json()["project"]
    project_id = project["project"]["id"]

    created = client.post(
        f"/api/projects/{project_id}/pages",
        json={"title": "About", "slug": "about"},
    )
    assert created.status_code == 201
    page = created.json()["project"]["pages"][1]
    page_id = page["id"]

    updated = client.put(
        f"/api/projects/{project_id}/pages/{page_id}",
        json={"title": "About us", "slug": "about-us"},
    )
    assert updated.status_code == 200
    assert updated.json()["project"]["pages"][1]["title"] == "About us"

    promoted = client.post(f"/api/projects/{project_id}/pages/{page_id}/home")
    assert promoted.status_code == 200
    assert promoted.json()["project"]["pages"][1]["is_home"] is True

    reordered = client.put(
        f"/api/projects/{project_id}/pages/reorder",
        json={"page_ids": [page_id, project["pages"][0]["id"]]},
    )
    assert reordered.status_code == 200
    assert reordered.json()["project"]["pages"][0]["id"] == page_id

    deleted = client.delete(f"/api/projects/{project_id}/pages/{page_id}")
    assert deleted.status_code == 200
    assert deleted.json()["project"]["pages"][0]["is_home"] is True


def test_page_api_rejects_duplicate_slug_and_invalid_order(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "project_store", ProjectStore(tmp_path / "projects"))
    project = client.post("/api/projects", json={"name": "Page validation"}).json()["project"]
    project_id = project["project"]["id"]
    client.post(
        f"/api/projects/{project_id}/pages",
        json={"title": "About", "slug": "about"},
    )

    duplicate = client.post(
        f"/api/projects/{project_id}/pages",
        json={"title": "Duplicate", "slug": "about"},
    )
    assert duplicate.status_code == 422

    invalid_order = client.put(
        f"/api/projects/{project_id}/pages/reorder",
        json={"page_ids": [project["pages"][0]["id"]]},
    )
    assert invalid_order.status_code == 422

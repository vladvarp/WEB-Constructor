from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.projects.migrations import migrate_project_data
from backend.projects.store import ProjectNotFoundError, ProjectStore


def test_create_project_writes_versioned_project_structure(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")

    project = store.create("Landing page")
    project_dir = tmp_path / "projects" / str(project.project.id)

    assert project.schema_version == 1
    assert project.project.name == "Landing page"
    assert project.pages[0].slug == "index"
    assert project.pages[0].is_home is True
    assert (project_dir / "project.json").is_file()
    assert (project_dir / "assets").is_dir()
    assert (project_dir / "exports").is_dir()


def test_list_projects_returns_all_projects(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    first = store.create("First")
    second = store.create("Second")

    projects = store.list_projects()

    assert {item.project.id for item in projects} == {
        first.project.id,
        second.project.id,
    }


def test_save_updates_data_without_changing_identity_or_creation_date(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    created = store.create("Before")
    data = created.model_dump(mode="json")
    data["project"]["name"] = "After"
    data["site"]["title"] = "Updated site"

    saved = store.save(created.project.id, data)
    reopened = store.get(created.project.id)

    assert saved.project.name == "After"
    assert reopened.site.title == "Updated site"
    assert reopened.project.id == created.project.id
    assert reopened.project.created_at == created.project.created_at
    assert reopened.project.updated_at >= created.project.updated_at


def test_save_rejects_changed_project_identity(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    created = store.create("Project")
    data = created.model_dump(mode="json")
    data["project"]["id"] = str(uuid4())

    with pytest.raises(ValueError, match="identifier cannot be changed"):
        store.save(created.project.id, data)


def test_project_requires_exactly_one_home_page(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    created = store.create("Project")
    data = created.model_dump(mode="json")
    data["pages"][0]["is_home"] = False

    with pytest.raises(ValueError, match="exactly one home page"):
        store.save(created.project.id, data)


def test_delete_removes_project_and_missing_project_raises(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    created = store.create("Delete me")

    store.delete(created.project.id)

    with pytest.raises(ProjectNotFoundError):
        store.get(created.project.id)


def test_invalid_identifier_cannot_escape_project_directory(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")

    with pytest.raises(ProjectNotFoundError):
        store.get("../../outside")


def test_migration_upgrades_unversioned_project_document() -> None:
    now = datetime.now(timezone.utc).isoformat()
    legacy = {
        "project": {
            "id": str(uuid4()),
            "name": "Legacy",
            "created_at": now,
            "updated_at": now,
        },
        "site": {"title": "Legacy site"},
    }

    migrated = migrate_project_data(legacy)

    assert migrated["schema_version"] == 1
    assert migrated["pages"][0]["is_home"] is True
    assert migrated["site"]["language"] == "ru"


def test_migration_rejects_newer_schema() -> None:
    with pytest.raises(ValueError, match="newer than supported"):
        migrate_project_data({"schema_version": 99})

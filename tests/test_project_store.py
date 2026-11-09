from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.projects.migrations import migrate_project_data
from backend.projects.models import ProjectAsset
from backend.projects.store import NavigationMenuNotFoundError, ProjectNotFoundError, ProjectStore


def test_create_project_writes_versioned_project_structure(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    project = store.create("Landing page")
    project_dir = tmp_path / "projects" / str(project.project.id)
    assert project.schema_version == 2
    assert project.project.name == "Landing page"
    assert project.pages[0].slug == "index"
    assert project.pages[0].is_home is True
    assert project.menus == []
    assert (project_dir / "project.json").is_file()
    assert (project_dir / "assets").is_dir()
    assert (project_dir / "exports").is_dir()


def test_list_projects_returns_all_projects(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    first = store.create("First")
    second = store.create("Second")
    projects = store.list_projects()
    assert {item.project.id for item in projects} == {first.project.id, second.project.id}


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
    legacy = {"project": {"id": str(uuid4()), "name": "Legacy", "created_at": now, "updated_at": now},
              "site": {"title": "Legacy site"}}
    migrated = migrate_project_data(legacy)
    assert migrated["schema_version"] == 2
    assert migrated["pages"][0]["is_home"] is True
    assert migrated["site"]["language"] == "ru"
    assert migrated["menus"] == []


def test_migration_upgrades_schema_v1_navigation_defaults() -> None:
    migrated = migrate_project_data({"schema_version": 1, "menus": []})
    assert migrated["schema_version"] == 2
    assert migrated["menus"] == []


def test_migration_rejects_newer_schema() -> None:
    with pytest.raises(ValueError, match="newer than supported"):
        migrate_project_data({"schema_version": 99})


def test_asset_path_rejects_traversal_and_normalizes_separators() -> None:
    with pytest.raises(ValueError, match="safe relative path"):
        ProjectAsset(id=uuid4(), name="outside", path="../outside.txt")
    asset = ProjectAsset(id=uuid4(), name="logo", path="images\\\\logo.svg")
    assert asset.path == "images/logo.svg"


def test_page_content_uses_nested_editor_independent_nodes(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    project = store.create("Node model")
    data = project.model_dump(mode="json")
    node_id, child_id = str(uuid4()), str(uuid4())
    data["pages"][0]["content"]["nodes"] = [{
        "id": node_id, "type": "section", "props": {"class": "hero"},
        "children": [{"id": child_id, "type": "text", "props": {"text": "Hello"}, "children": []}],
    }]
    saved = store.save(project.project.id, data)
    assert saved.pages[0].content.nodes[0].type == "section"
    assert saved.pages[0].content.nodes[0].children[0].props["text"] == "Hello"


def test_page_lifecycle_home_page_and_order(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    project = store.create("Pages")
    created = store.create_page(project.project.id, "Contacts", "contacts")
    contacts = created.pages[1]
    assert contacts.title == "Contacts" and contacts.is_home is False
    updated = store.update_page(project.project.id, contacts.id, "Contact us", "contact-us")
    assert updated.pages[1].title == "Contact us" and updated.pages[1].slug == "contact-us"
    promoted = store.set_home_page(project.project.id, contacts.id)
    assert promoted.pages[0].is_home is False and promoted.pages[1].is_home is True
    reordered = store.reorder_pages(project.project.id, [contacts.id, project.pages[0].id])
    assert [page.id for page in reordered.pages] == [contacts.id, project.pages[0].id]
    assert reordered.pages[0].is_home is True
    deleted = store.delete_page(project.project.id, contacts.id)
    assert len(deleted.pages) == 1 and deleted.pages[0].is_home is True


def test_page_delete_promotes_first_remaining_page_and_rejects_last(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    project = store.create("Page deletion")
    project = store.create_page(project.project.id, "About", "about")
    project = store.create_page(project.project.id, "Contacts", "contacts")
    deleted = store.delete_page(project.project.id, project.pages[0].id)
    assert deleted.pages[0].slug == "about" and deleted.pages[0].is_home is True
    deleted = store.delete_page(project.project.id, deleted.pages[1].id)
    with pytest.raises(ValueError, match="at least one page"):
        store.delete_page(project.project.id, deleted.pages[0].id)


def test_page_slug_must_be_unique_and_order_must_be_complete(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    project = store.create("Validation")
    project = store.create_page(project.project.id, "About", "about")
    with pytest.raises(ValueError, match="Page slugs must be unique"):
        store.create_page(project.project.id, "Duplicate", "about")
    with pytest.raises(ValueError, match="every page exactly once"):
        store.reorder_pages(project.project.id, [project.pages[0].id])


def test_navigation_menu_lifecycle_and_page_reference_cleanup(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    project = store.create("Navigation")
    project = store.create_page(project.project.id, "Contacts", "contacts")
    contacts = project.pages[1]
    project = store.create_menu(project.project.id, "Main", "header")
    menu = project.menus[0]
    items = [
        {"id": str(uuid4()), "label": "Home", "kind": "page", "page_id": str(project.pages[0].id),
         "url": None, "children": [{"id": str(uuid4()), "label": "Contacts", "kind": "page",
         "page_id": str(contacts.id), "url": None, "children": []}]},
        {"id": str(uuid4()), "label": "External", "kind": "external", "page_id": None,
         "url": "https://example.com", "children": []},
    ]
    project = store.update_menu(project.project.id, menu.id, "Primary", "primary", items)
    assert project.menus[0].name == "Primary"
    assert project.menus[0].items[0].children[0].page_id == contacts.id
    project = store.delete_page(project.project.id, contacts.id)
    assert project.menus[0].items[0].children == []
    project = store.delete_menu(project.project.id, menu.id)
    assert project.menus == []
    with pytest.raises(NavigationMenuNotFoundError):
        store.delete_menu(project.project.id, menu.id)


def test_navigation_rejects_unsafe_urls_and_missing_page_targets(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    project = store.create("Navigation validation")
    project = store.create_menu(project.project.id, "Main")
    menu = project.menus[0]
    with pytest.raises(ValueError):
        store.update_menu(project.project.id, menu.id, "Main", "header", [{
            "id": str(uuid4()), "label": "Bad", "kind": "external", "page_id": None,
            "url": "javascript:alert(1)", "children": [],
        }])
    with pytest.raises(ValueError, match="does not exist"):
        store.update_menu(project.project.id, menu.id, "Main", "header", [{
            "id": str(uuid4()), "label": "Missing", "kind": "page", "page_id": str(uuid4()),
            "url": None, "children": [],
        }])


def test_navigation_nesting_limit_is_enforced(tmp_path) -> None:
    store = ProjectStore(tmp_path / "projects")
    project = store.create("Deep navigation")
    project = store.create_menu(project.project.id, "Main")
    menu = project.menus[0]
    root = {"id": str(uuid4()), "label": "Level 1", "kind": "page",
            "page_id": str(project.pages[0].id), "url": None, "children": []}
    node = root
    for level in range(2, 7):
        child = {"id": str(uuid4()), "label": f"Level {level}", "kind": "page",
                 "page_id": str(project.pages[0].id), "url": None, "children": []}
        node["children"].append(child)
        node = child
    with pytest.raises(ValueError, match="five levels"):
        store.update_menu(project.project.id, menu.id, "Main", "header", [root])

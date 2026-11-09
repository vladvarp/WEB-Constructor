from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.projects.models import CURRENT_SCHEMA_VERSION


def _migrate_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade the initial unversioned draft format to the first stable model."""
    migrated = deepcopy(data)
    now = datetime.now(timezone.utc).isoformat()
    project = migrated.setdefault("project", {})
    if not isinstance(project, dict):
        raise ValueError("Legacy project metadata must be an object")
    project.setdefault("id", str(uuid4()))
    project.setdefault("name", migrated.get("name") or "Новый проект")
    project.setdefault("created_at", now)
    project.setdefault("updated_at", project["created_at"])

    site = migrated.setdefault("site", {})
    if not isinstance(site, dict):
        raise ValueError("Legacy site settings must be an object")
    site.setdefault("title", project["name"])
    site.setdefault("description", "")
    site.setdefault("language", "ru")

    pages = migrated.setdefault("pages", [])
    if not pages:
        pages.append({
            "id": str(uuid4()),
            "title": "Главная",
            "slug": "index",
            "is_home": True,
            "content": {"nodes": []},
        })
    migrated.setdefault("assets", [])
    migrated["schema_version"] = 1
    return migrated


MIGRATIONS = {
    0: _migrate_v0_to_v1,
}


def migrate_project_data(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Project document must be a JSON object")

    migrated = deepcopy(data)
    version = migrated.get("schema_version", 0)
    if not isinstance(version, int) or isinstance(version, bool) or version < 0:
        raise ValueError("Invalid project schema version")
    if version > CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Project schema {version} is newer than supported schema "
            f"{CURRENT_SCHEMA_VERSION}"
        )

    while version < CURRENT_SCHEMA_VERSION:
        migration = MIGRATIONS.get(version)
        if migration is None:
            raise ValueError(f"No migration registered from schema version {version}")
        migrated = migration(migrated)
        next_version = migrated.get("schema_version")
        if next_version != version + 1:
            raise ValueError(f"Migration from schema {version} did not advance one version")
        version = next_version

    return migrated

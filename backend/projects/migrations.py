from __future__ import annotations

from copy import deepcopy
from typing import Any

from backend.projects.models import CURRENT_SCHEMA_VERSION


def _migrate_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade the initial unversioned draft format to the first stable model."""
    migrated = deepcopy(data)
    migrated["schema_version"] = 1
    migrated.setdefault("assets", [])
    migrated.setdefault("pages", [])
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

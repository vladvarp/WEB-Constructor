from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

from backend.projects.migrations import migrate_project_data
from backend.projects.models import (
    CURRENT_SCHEMA_VERSION,
    PageContent,
    ProjectDocument,
    ProjectMetadata,
    ProjectPage,
    SiteSettings,
)

logger = logging.getLogger("web_constructor.projects")


class ProjectNotFoundError(FileNotFoundError):
    pass


class ProjectStore:
    """Stores each project in an isolated directory using an atomic JSON file."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()

    def _project_dir(self, project_id: UUID | str) -> Path:
        try:
            normalized_id = UUID(str(project_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ProjectNotFoundError("Invalid project identifier") from exc
        return self.root / str(normalized_id)

    def _project_file(self, project_id: UUID | str) -> Path:
        return self._project_dir(project_id) / "project.json"

    def _read(self, project_id: UUID | str) -> ProjectDocument:
        path = self._project_file(project_id)
        if not path.is_file():
            raise ProjectNotFoundError(f"Project {project_id} was not found")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            migrated = migrate_project_data(raw)
            return ProjectDocument.model_validate(migrated)
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
            logger.exception("Project file is invalid: %s", path)
            raise ValueError(f"Project data is invalid: {path.parent.name}") from exc

    @staticmethod
    def _serialize(document: ProjectDocument) -> str:
        return json.dumps(
            document.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ) + "\n"

    def _atomic_write(self, project_dir: Path, document: ProjectDocument) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=".project-", suffix=".tmp", dir=project_dir
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(self._serialize(document))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, project_dir / "project.json")
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    def create(self, name: str) -> ProjectDocument:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Project name cannot be empty")
        if len(normalized_name) > 80:
            raise ValueError("Project name must not exceed 80 characters")

        now = datetime.now(timezone.utc)
        project_id = uuid4()
        document = ProjectDocument(
            schema_version=CURRENT_SCHEMA_VERSION,
            project=ProjectMetadata(
                id=project_id,
                name=normalized_name,
                created_at=now,
                updated_at=now,
            ),
            site=SiteSettings(title=normalized_name, description="", language="ru"),
            pages=[
                ProjectPage(
                    id=uuid4(),
                    title="Главная",
                    slug="index",
                    is_home=True,
                    content=PageContent(),
                )
            ],
            assets=[],
        )

        project_dir = self._project_dir(project_id)
        self._atomic_write(project_dir, document)
        (project_dir / "assets").mkdir(exist_ok=True)
        (project_dir / "exports").mkdir(exist_ok=True)
        return document

    def list_projects(self) -> list[ProjectDocument]:
        if not self.root.exists():
            return []
        projects: list[ProjectDocument] = []
        for project_file in self.root.glob("*/project.json"):
            try:
                projects.append(self._read(project_file.parent.name))
            except (ProjectNotFoundError, ValueError):
                logger.warning("Skipping unreadable project: %s", project_file)
        return sorted(projects, key=lambda item: item.project.updated_at, reverse=True)

    def get(self, project_id: UUID | str) -> ProjectDocument:
        return self._read(project_id)

    def save(self, project_id: UUID | str, data: dict[str, Any]) -> ProjectDocument:
        current = self._read(project_id)
        migrated = migrate_project_data(data)
        candidate = ProjectDocument.model_validate(migrated)
        if candidate.project.id != current.project.id:
            raise ValueError("Project identifier cannot be changed")
        if candidate.project.created_at != current.project.created_at:
            raise ValueError("Project creation date cannot be changed")

        updated = candidate.model_copy(
            update={
                "project": candidate.project.model_copy(
                    update={"updated_at": datetime.now(timezone.utc)}
                )
            }
        )
        self._atomic_write(self._project_dir(project_id), updated)
        return updated

    def delete(self, project_id: UUID | str) -> None:
        project_dir = self._project_dir(project_id)
        project_file = project_dir / "project.json"
        if not project_file.is_file():
            raise ProjectNotFoundError(f"Project {project_id} was not found")
        # UUID normalization prevents user-controlled path traversal.
        shutil.rmtree(project_dir)

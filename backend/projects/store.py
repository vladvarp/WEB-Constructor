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
    NavigationItem,
    NavigationMenu,
    SiteSettings,
)

logger = logging.getLogger("web_constructor.projects")


class ProjectNotFoundError(FileNotFoundError):
    pass


class PageNotFoundError(LookupError):
    pass


class NavigationMenuNotFoundError(LookupError):
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

    def _save_document(self, project_id: UUID | str, document: ProjectDocument) -> ProjectDocument:
        current = self._read(project_id)
        if document.project.id != current.project.id:
            raise ValueError("Project identifier cannot be changed")
        if document.project.created_at != current.project.created_at:
            raise ValueError("Project creation date cannot be changed")
        updated = document.model_copy(
            update={
                "project": document.project.model_copy(
                    update={"updated_at": datetime.now(timezone.utc)}
                )
            }
        )
        self._atomic_write(self._project_dir(project_id), updated)
        return updated

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
                    content=PageContent(nodes=[
                        {
                            "id": uuid4(), "type": "section",
                            "props": {"background": "#e9e5dc", "padding": "112px 9%", "layout": "hero"},
                            "children": [
                                {"id": uuid4(), "type": "eyebrow", "props": {"text": "АРХИТЕКТУРА · ИНТЕРЬЕРЫ · СРЕДА"}, "children": []},
                                {"id": uuid4(), "type": "heading", "props": {"text": "Пространство,\nв котором хочется жить", "level": 1, "color": "#202b2b", "font_size": 64}, "children": []},
                                {"id": uuid4(), "type": "paragraph", "props": {"text": "Создаём выразительную архитектуру и спокойные интерьеры, в которых каждая деталь работает на целое.", "color": "#596361", "font_size": 18}, "children": []},
                                {"id": uuid4(), "type": "button", "props": {"text": "Обсудить проект", "background": "#263b38", "color": "#ffffff"}, "children": []},
                            ],
                        },
                        {
                            "id": uuid4(), "type": "section",
                            "props": {"background": "#f7f6f2", "padding": "76px 9%", "layout": "content"},
                            "children": [
                                {"id": uuid4(), "type": "heading", "props": {"text": "Подход, основанный на смысле", "level": 2, "color": "#202b2b", "font_size": 38}, "children": []},
                                {"id": uuid4(), "type": "paragraph", "props": {"text": "От первой идеи до последнего штриха — соединяем функциональность, эстетику и внимание к контексту.", "color": "#596361", "font_size": 17}, "children": []},
                            ],
                        },
                    ]),
                )
            ],
            assets=[],
            menus=[],
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
        return self._save_document(project_id, candidate)

    def create_page(self, project_id: UUID | str, title: str, slug: str) -> ProjectDocument:
        document = self._read(project_id)
        page = ProjectPage(
            id=uuid4(),
            title=title.strip(),
            slug=slug.strip().lower(),
            is_home=False,
            content=PageContent(),
        )
        document = document.model_copy(update={"pages": [*document.pages, page]})
        return self._save_document(project_id, ProjectDocument.model_validate(document.model_dump()))

    def update_page(
        self, project_id: UUID | str, page_id: UUID | str, title: str, slug: str
    ) -> ProjectDocument:
        document = self._read(project_id)
        normalized_id = UUID(str(page_id))
        if not any(page.id == normalized_id for page in document.pages):
            raise PageNotFoundError("Page not found")
        pages = [
            page.model_copy(update={"title": title.strip(), "slug": slug.strip().lower()})
            if page.id == normalized_id else page
            for page in document.pages
        ]
        candidate = ProjectDocument.model_validate(
            document.model_copy(update={"pages": pages}).model_dump()
        )
        return self._save_document(project_id, candidate)

    def set_home_page(self, project_id: UUID | str, page_id: UUID | str) -> ProjectDocument:
        document = self._read(project_id)
        normalized_id = UUID(str(page_id))
        if not any(page.id == normalized_id for page in document.pages):
            raise PageNotFoundError("Page not found")
        pages = [
            page.model_copy(update={"is_home": page.id == normalized_id})
            for page in document.pages
        ]
        candidate = ProjectDocument.model_validate(
            document.model_copy(update={"pages": pages}).model_dump()
        )
        return self._save_document(project_id, candidate)

    def delete_page(self, project_id: UUID | str, page_id: UUID | str) -> ProjectDocument:
        document = self._read(project_id)
        normalized_id = UUID(str(page_id))
        if not any(page.id == normalized_id for page in document.pages):
            raise PageNotFoundError("Page not found")
        if len(document.pages) == 1:
            raise ValueError("A project must contain at least one page")
        pages = [page for page in document.pages if page.id != normalized_id]
        if not any(page.is_home for page in pages):
            pages[0] = pages[0].model_copy(update={"is_home": True})
        def without_page(items: list[NavigationItem]) -> list[NavigationItem]:
            return [item.model_copy(update={"children": without_page(item.children)})
                    for item in items if not (item.kind == "page" and item.page_id == normalized_id)]
        menus = [menu.model_copy(update={"items": without_page(menu.items)}) for menu in document.menus]
        candidate = ProjectDocument.model_validate(
            document.model_copy(update={"pages": pages, "menus": menus}).model_dump()
        )
        return self._save_document(project_id, candidate)

    def reorder_pages(
        self, project_id: UUID | str, page_ids: list[UUID]
    ) -> ProjectDocument:
        document = self._read(project_id)
        current_ids = {page.id for page in document.pages}
        if len(page_ids) != len(current_ids) or set(page_ids) != current_ids:
            raise ValueError("Page order must contain every page exactly once")
        by_id = {page.id: page for page in document.pages}
        candidate = ProjectDocument.model_validate(
            document.model_copy(
                update={"pages": [by_id[page_id] for page_id in page_ids]}
            ).model_dump()
        )
        return self._save_document(project_id, candidate)


    def create_menu(self, project_id: UUID | str, name: str, location: str = "header") -> ProjectDocument:
        document = self._read(project_id)
        menu = NavigationMenu(id=uuid4(), name=name, location=location, items=[])
        candidate = ProjectDocument.model_validate(document.model_copy(update={"menus": [*document.menus, menu]}).model_dump())
        return self._save_document(project_id, candidate)

    def update_menu(self, project_id: UUID | str, menu_id: UUID | str, name: str,
                    location: str, items: list[dict[str, Any]]) -> ProjectDocument:
        document = self._read(project_id)
        normalized_id = UUID(str(menu_id))
        if not any(menu.id == normalized_id for menu in document.menus):
            raise NavigationMenuNotFoundError("Navigation menu not found")
        updated = NavigationMenu(id=normalized_id, name=name, location=location, items=items)
        menus = [updated if menu.id == normalized_id else menu for menu in document.menus]
        candidate = ProjectDocument.model_validate(document.model_copy(update={"menus": menus}).model_dump())
        return self._save_document(project_id, candidate)

    def delete_menu(self, project_id: UUID | str, menu_id: UUID | str) -> ProjectDocument:
        document = self._read(project_id)
        normalized_id = UUID(str(menu_id))
        if not any(menu.id == normalized_id for menu in document.menus):
            raise NavigationMenuNotFoundError("Navigation menu not found")
        menus = [menu for menu in document.menus if menu.id != normalized_id]
        candidate = ProjectDocument.model_validate(document.model_copy(update={"menus": menus}).model_dump())
        return self._save_document(project_id, candidate)

    def delete(self, project_id: UUID | str) -> None:
        project_dir = self._project_dir(project_id)
        project_file = project_dir / "project.json"
        if not project_file.is_file():
            raise ProjectNotFoundError(f"Project {project_id} was not found")
        shutil.rmtree(project_dir)

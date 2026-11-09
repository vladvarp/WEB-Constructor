from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CURRENT_SCHEMA_VERSION = 2


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectMetadata(StrictModel):
    id: UUID
    name: str = Field(min_length=1, max_length=80)
    created_at: datetime
    updated_at: datetime

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project name cannot be empty")
        if any(ord(char) < 32 for char in value):
            raise ValueError("Project name contains control characters")
        return value


class SiteSettings(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    language: str = Field(default="ru", min_length=2, max_length=12)


class ContentNode(StrictModel):
    # Editor-independent node. Rendering details live in adapters, not here.
    id: UUID
    type: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_-]*$")
    props: dict[str, Any] = Field(default_factory=dict)
    children: list[ContentNode] = Field(default_factory=list)


class PageContent(StrictModel):
    # Editor-independent document tree; never stores editor DOM or editor JSON.
    nodes: list[ContentNode] = Field(default_factory=list)


class ProjectPage(StrictModel):
    id: UUID
    title: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")
    is_home: bool = False
    content: PageContent = Field(default_factory=PageContent)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Page title cannot be empty")
        if any(ord(char) < 32 for char in value):
            raise ValueError("Page title contains control characters")
        return value

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return value.strip().lower()


class ProjectAsset(StrictModel):
    id: UUID
    name: str = Field(min_length=1, max_length=255)
    path: str = Field(min_length=1, max_length=500)
    mime_type: str = Field(default="application/octet-stream", max_length=120)

    @field_validator("path")
    @classmethod
    def require_safe_relative_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/").strip()
        path = PurePosixPath(normalized)
        if (
            not normalized
            or path.is_absolute()
            or not path.parts
            or any(part in {"", ".", ".."} for part in path.parts)
            or ":" in path.parts[0]
            or any(ord(char) < 32 for char in normalized)
        ):
            raise ValueError("Asset path must be a safe relative path")
        return path.as_posix()


class NavigationItem(StrictModel):
    id: UUID
    label: str = Field(min_length=1, max_length=120)
    kind: Literal["page", "external"] = "page"
    page_id: UUID | None = None
    url: str | None = Field(default=None, max_length=2048)
    children: list[NavigationItem] = Field(default_factory=list)

    @field_validator("label")
    @classmethod
    def clean_label(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Navigation label must be a non-empty plain text value")
        return value

    @field_validator("url")
    @classmethod
    def validate_external_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        parsed = urlsplit(value)
        if (len(value) > 2048 or any(ord(char) < 32 for char in value)
            or parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc
            or not parsed.hostname or parsed.username is not None or parsed.password is not None):
            raise ValueError("External navigation URLs must be absolute HTTP or HTTPS URLs")
        return value

    @model_validator(mode="after")
    def validate_target(self) -> NavigationItem:
        if self.kind == "page" and (self.page_id is None or self.url is not None):
            raise ValueError("Page navigation items require page_id and cannot contain url")
        if self.kind == "external" and (self.url is None or self.page_id is not None):
            raise ValueError("External navigation items require url and cannot contain page_id")
        return self


class NavigationMenu(StrictModel):
    id: UUID
    name: str = Field(min_length=1, max_length=80)
    location: str = Field(default="header", min_length=1, max_length=40, pattern=r"^[a-z][a-z0-9_-]*$")
    items: list[NavigationItem] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Navigation menu name cannot be empty")
        return value


class ProjectDocument(StrictModel):
    schema_version: int = Field(ge=1)
    project: ProjectMetadata
    site: SiteSettings
    pages: list[ProjectPage] = Field(default_factory=list, min_length=1)
    assets: list[ProjectAsset] = Field(default_factory=list)
    menus: list[NavigationMenu] = Field(default_factory=list)

    @field_validator("pages")
    @classmethod
    def require_one_home_page(cls, pages: list[ProjectPage]) -> list[ProjectPage]:
        home_pages = [page for page in pages if page.is_home]
        if len(home_pages) != 1:
            raise ValueError("A project must contain exactly one home page")
        slugs = [page.slug for page in pages]
        if len(slugs) != len(set(slugs)):
            raise ValueError("Page slugs must be unique")
        page_ids = [page.id for page in pages]
        if len(page_ids) != len(set(page_ids)):
            raise ValueError("Page identifiers must be unique")
        return pages

    @model_validator(mode="after")
    def validate_navigation(self) -> ProjectDocument:
        menu_ids = [menu.id for menu in self.menus]
        if len(menu_ids) != len(set(menu_ids)):
            raise ValueError("Navigation menu identifiers must be unique")
        page_ids = {page.id for page in self.pages}
        item_ids: set[UUID] = set()
        total_items = 0
        def inspect_items(items: list[NavigationItem], depth: int = 1) -> None:
            nonlocal total_items
            if depth > 5:
                raise ValueError("Navigation nesting cannot exceed five levels")
            for item in items:
                total_items += 1
                if total_items > 500:
                    raise ValueError("A project cannot contain more than 500 navigation items")
                if item.id in item_ids:
                    raise ValueError("Navigation item identifiers must be unique")
                item_ids.add(item.id)
                if item.kind == "page" and item.page_id not in page_ids:
                    raise ValueError("Navigation item references a page that does not exist")
                inspect_items(item.children, depth + 1)
        for menu in self.menus:
            inspect_items(menu.items)
        return self

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CURRENT_SCHEMA_VERSION = 1


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


class PageContent(StrictModel):
    # Editor-independent document tree. Node contracts will be extended
    # without coupling the stored format to a particular visual editor.
    nodes: list[dict[str, Any]] = Field(default_factory=list)


class ProjectPage(StrictModel):
    id: UUID
    title: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")
    is_home: bool = False
    content: PageContent = Field(default_factory=PageContent)


class ProjectAsset(StrictModel):
    id: UUID
    name: str = Field(min_length=1, max_length=255)
    path: str = Field(min_length=1, max_length=500)
    mime_type: str = Field(default="application/octet-stream", max_length=120)


class ProjectDocument(StrictModel):
    schema_version: int = Field(ge=1)
    project: ProjectMetadata
    site: SiteSettings
    pages: list[ProjectPage] = Field(default_factory=list, min_length=1)
    assets: list[ProjectAsset] = Field(default_factory=list)

    @field_validator("pages")
    @classmethod
    def require_one_home_page(cls, pages: list[ProjectPage]) -> list[ProjectPage]:
        home_pages = [page for page in pages if page.is_home]
        if len(home_pages) != 1:
            raise ValueError("A project must contain exactly one home page")
        slugs = [page.slug for page in pages]
        if len(slugs) != len(set(slugs)):
            raise ValueError("Page slugs must be unique")
        return pages

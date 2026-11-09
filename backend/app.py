from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.core.config import FRONTEND_DIR, MODULES_DIR, PROJECTS_DIR
from backend.core.module_registry import ModuleRegistry
from backend.projects.store import PageNotFoundError, ProjectNotFoundError, ProjectStore

module_registry = ModuleRegistry(MODULES_DIR)
module_registry.discover()
project_store = ProjectStore(PROJECTS_DIR)

app = FastAPI(title="WEB-Constructor API", docs_url=None, redoc_url=None, openapi_url=None)


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ProjectSaveRequest(BaseModel):
    project: dict[str, Any]


class PageCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")


class PageUpdateRequest(PageCreateRequest):
    pass


class PageOrderRequest(BaseModel):
    page_ids: list[UUID] = Field(min_length=1)


def _project_response(project: Any) -> dict[str, Any]:
    return {"project": project.model_dump(mode="json")}


def _page_operation(operation: Any) -> dict[str, Any]:
    try:
        return _project_response(operation())
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except PageNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Page not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "application": "WEB-Constructor"}


@app.get("/api/modules")
def get_modules() -> dict:
    return {"modules": module_registry.list_modules()}


@app.get("/api/projects")
def list_projects() -> dict[str, list[dict[str, Any]]]:
    return {"projects": [item.model_dump(mode="json") for item in project_store.list_projects()]}


@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectCreateRequest) -> dict[str, Any]:
    try:
        return _project_response(project_store.create(payload.name))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}")
def get_project(project_id: UUID) -> dict[str, Any]:
    try:
        return _project_response(project_store.get(project_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.put("/api/projects/{project_id}")
def save_project(project_id: UUID, payload: ProjectSaveRequest) -> dict[str, Any]:
    try:
        return _project_response(project_store.save(project_id, payload.project))
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/pages", status_code=201)
def create_page(project_id: UUID, payload: PageCreateRequest) -> dict[str, Any]:
    return _page_operation(lambda: project_store.create_page(project_id, payload.title, payload.slug))


@app.put("/api/projects/{project_id}/pages/reorder")
def reorder_pages(project_id: UUID, payload: PageOrderRequest) -> dict[str, Any]:
    return _page_operation(lambda: project_store.reorder_pages(project_id, payload.page_ids))


@app.put("/api/projects/{project_id}/pages/{page_id}")
def update_page(project_id: UUID, page_id: UUID, payload: PageUpdateRequest) -> dict[str, Any]:
    return _page_operation(
        lambda: project_store.update_page(project_id, page_id, payload.title, payload.slug)
    )


@app.post("/api/projects/{project_id}/pages/{page_id}/home")
def set_home_page(project_id: UUID, page_id: UUID) -> dict[str, Any]:
    return _page_operation(lambda: project_store.set_home_page(project_id, page_id))


@app.delete("/api/projects/{project_id}/pages/{page_id}")
def delete_page(project_id: UUID, page_id: UUID) -> dict[str, Any]:
    return _page_operation(lambda: project_store.delete_page(project_id, page_id))


@app.put("/api/projects/{project_id}/pages/order")
def reorder_pages(project_id: UUID, payload: PageOrderRequest) -> dict[str, Any]:
    return _page_operation(lambda: project_store.reorder_pages(project_id, payload.page_ids))


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: UUID) -> None:
    try:
        project_store.delete(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

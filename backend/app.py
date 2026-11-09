from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.core.config import FRONTEND_DIR, MODULES_DIR, PROJECTS_DIR
from backend.core.module_registry import ModuleRegistry
from backend.projects.store import ProjectNotFoundError, ProjectStore

module_registry = ModuleRegistry(MODULES_DIR)
module_registry.discover()
project_store = ProjectStore(PROJECTS_DIR)

app = FastAPI(title="WEB-Constructor API", docs_url=None, redoc_url=None, openapi_url=None)


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ProjectSaveRequest(BaseModel):
    project: dict[str, Any]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "application": "WEB-Constructor"}


@app.get("/api/modules")
def get_modules() -> dict:
    return {"modules": module_registry.list_modules()}


@app.get("/api/projects")
def list_projects() -> dict[str, list[dict[str, Any]]]:
    return {
        "projects": [
            item.model_dump(mode="json")
            for item in project_store.list_projects()
        ]
    }


@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectCreateRequest) -> dict[str, Any]:
    try:
        project = project_store.create(payload.name)
        return {"project": project.model_dump(mode="json")}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}")
def get_project(project_id: UUID) -> dict[str, Any]:
    try:
        project = project_store.get(project_id)
        return {"project": project.model_dump(mode="json")}
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.put("/api/projects/{project_id}")
def save_project(project_id: UUID, payload: ProjectSaveRequest) -> dict[str, Any]:
    try:
        project = project_store.save(project_id, payload.project)
        return {"project": project.model_dump(mode="json")}
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: UUID) -> None:
    try:
        project_store.delete(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.core.config import FRONTEND_DIR, MODULES_DIR
from backend.core.module_registry import ModuleRegistry

module_registry = ModuleRegistry(MODULES_DIR)
module_registry.discover()
app = FastAPI(title="WEB-Constructor API", docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "application": "WEB-Constructor"}


@app.get("/api/modules")
def get_modules() -> dict:
    return {"modules": module_registry.list_modules()}


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

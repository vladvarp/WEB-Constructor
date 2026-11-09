from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MODULE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")


@dataclass(frozen=True)
class ModuleManifest:
    module_id: str
    name: str
    version: str
    enabled: bool
    dependencies: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.module_id, "name": self.name, "version": self.version,
                "enabled": self.enabled, "dependencies": list(self.dependencies)}


class ModuleRegistry:
    """Discovers and validates metadata; it never executes module code."""

    def __init__(self, modules_dir: Path) -> None:
        self.modules_dir = modules_dir
        self._modules: dict[str, ModuleManifest] = {}

    def discover(self) -> list[ModuleManifest]:
        self._modules.clear()
        if not self.modules_dir.exists():
            return []
        for path in sorted(self.modules_dir.glob("*/module.json")):
            module = self._read_manifest(path)
            if module.module_id in self._modules:
                raise ValueError(f"Duplicate module id: {module.module_id}")
            self._modules[module.module_id] = module
        for module in self._modules.values():
            for dependency in module.dependencies:
                if dependency not in self._modules:
                    raise ValueError(
                        f"Module '{module.module_id}' requires missing module '{dependency}'"
                    )
        return list(self._modules.values())

    def list_modules(self) -> list[dict[str, Any]]:
        return [module.to_dict() for module in self._modules.values()]

    @staticmethod
    def _read_manifest(path: Path) -> ModuleManifest:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read module manifest {path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"Manifest must be a JSON object: {path}")
        module_id, name, version = raw.get("id"), raw.get("name"), raw.get("version")
        enabled, dependencies = raw.get("enabled", False), raw.get("dependencies", [])
        if not isinstance(module_id, str) or not MODULE_ID_PATTERN.fullmatch(module_id):
            raise ValueError(f"Invalid module id in {path}")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Missing module name in {path}")
        if not isinstance(version, str) or not version.strip():
            raise ValueError(f"Missing module version in {path}")
        if not isinstance(enabled, bool):
            raise ValueError(f"Invalid enabled flag in {path}")
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) and MODULE_ID_PATTERN.fullmatch(item)
            for item in dependencies
        ):
            raise ValueError(f"Invalid dependencies in {path}")
        return ModuleManifest(module_id, name.strip(), version.strip(), enabled,
                              tuple(dependencies))

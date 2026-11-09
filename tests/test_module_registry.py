import json

import pytest

from backend.core.module_registry import ModuleRegistry


def test_discovers_valid_manifest(tmp_path) -> None:
    module_dir = tmp_path / "sample"
    module_dir.mkdir()
    (module_dir / "module.json").write_text(json.dumps({
        "id": "sample.module",
        "name": "Sample",
        "version": "1.0.0",
        "enabled": False,
        "dependencies": [],
    }), encoding="utf-8")

    registry = ModuleRegistry(tmp_path)
    modules = registry.discover()

    assert len(modules) == 1
    assert modules[0].module_id == "sample.module"
    assert registry.list_modules()[0]["enabled"] is False


def test_rejects_missing_dependency(tmp_path) -> None:
    module_dir = tmp_path / "sample"
    module_dir.mkdir()
    (module_dir / "module.json").write_text(json.dumps({
        "id": "sample.module",
        "name": "Sample",
        "version": "1.0.0",
        "enabled": False,
        "dependencies": ["missing.module"],
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="requires missing module"):
        ModuleRegistry(tmp_path).discover()


def test_rejects_invalid_manifest(tmp_path) -> None:
    module_dir = tmp_path / "sample"
    module_dir.mkdir()
    (module_dir / "module.json").write_text("{invalid", encoding="utf-8")

    with pytest.raises(ValueError, match="Cannot read module manifest"):
        ModuleRegistry(tmp_path).discover()

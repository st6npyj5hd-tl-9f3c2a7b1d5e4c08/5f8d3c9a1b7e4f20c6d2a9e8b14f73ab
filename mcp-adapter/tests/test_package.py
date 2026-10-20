import json
from pathlib import Path

import jsonschema

from weather_buddy.server import registered_tools

ROOT = Path(__file__).resolve().parents[1]


def test_official_portable_schemas():
    for name in ("plugin", "mcp"):
        schema = json.loads((ROOT / "tests/schemas" / f"{name}.schema.json").read_text())
        package = json.loads((ROOT / "plugin" / f"{name}.json").read_text())
        jsonschema.validate(package, schema)
    skill = (ROOT / "plugin/skills/weather-buddy/SKILL.md").read_text()
    assert skill.startswith("---\nname: weather-buddy\ndescription:")
    for tool in registered_tools():
        assert tool.name in skill
    manifest = (ROOT / "plugin/plugin.json").read_text()
    assert "plugin_asdk_app" not in manifest
    assert not (ROOT / "plugin/.app.json").exists()


def test_exported_contract_matches_server():
    expected = {"tools": [t.model_dump(mode="json", exclude_none=True) for t in registered_tools()]}
    assert json.loads((ROOT / "docs/tools.json").read_text()) == expected

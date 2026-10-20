"""Export a stable reference tool catalog for reviews and a future Sites port."""

import json
from pathlib import Path

from weather_buddy.server import registered_tools

if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[1] / "docs" / "tools.json"
    destination.write_text(
        json.dumps(
            {"tools": [t.model_dump(mode="json", exclude_none=True) for t in registered_tools()]},
            indent=2,
        )
        + "\n"
    )

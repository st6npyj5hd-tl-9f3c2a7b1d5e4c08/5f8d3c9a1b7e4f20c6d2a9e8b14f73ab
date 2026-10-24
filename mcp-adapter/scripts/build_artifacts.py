"""Build a review-only plugin zip and deterministic fixture oracle; never deploy."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import httpx

from weather_buddy.service import PATHS, WeatherService

ROOT = Path(__file__).resolve().parents[1]


class Body(httpx.AsyncByteStream):
    def __init__(self, payload):
        self.payload = payload

    async def __aiter__(self):
        yield self.payload


async def build():
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    with ZipFile(output / "weather-buddy-plugin.zip", "w", ZIP_DEFLATED) as archive:
        for path in sorted((ROOT / "plugin").rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(ROOT / "plugin"))

    def handle(request):
        path = ROOT / "tests/fixtures" / request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, stream=Body(path.read_bytes()))

    service = WeatherService(
        transport=httpx.MockTransport(handle),
        now=lambda: datetime(2026, 10, 20, 17, tzinfo=UTC),
    )
    for name in PATHS:
        result = await service.call(name)
        if result.status == "error":
            raise RuntimeError(result.error.message)
        (output / f"{name}.json").write_text(
            json.dumps(result.model_dump(mode="json"), indent=2) + "\n"
        )
    print("Built plugin zip and four fixture oracle responses in dist/ (not deployed).")


if __name__ == "__main__":
    asyncio.run(build())

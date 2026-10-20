from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from weather_buddy.service import BASE, WeatherService

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 20, 17, tzinfo=timezone.utc)


@pytest.fixture
def fixture_bytes():
    return lambda name: (FIXTURES / name).read_bytes()


class Body(httpx.AsyncByteStream):
    def __init__(self, data):
        self.data = data

    async def __aiter__(self):
        yield self.data


def response(data, status=200, headers=None):
    return httpx.Response(status, stream=Body(data), headers=headers)


@pytest.fixture
def service_factory():
    def build(overrides=None, now=NOW):
        requests = []
        overrides = overrides or {}

        def handle(request):
            requests.append(request)
            assert request.method == "GET"
            assert str(request.url).startswith(BASE + "/api/")
            name = request.url.path.rsplit("/", 1)[-1]
            override = overrides.get(name)
            if isinstance(override, Exception):
                raise override
            if isinstance(override, httpx.Response):
                return override
            return response(override if override is not None else (FIXTURES / name).read_bytes())

        return WeatherService(transport=httpx.MockTransport(handle), now=lambda: now), requests

    return build

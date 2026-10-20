"""Explicit opt-in; failures never affect normal offline test runs."""

import os

import pytest

from weather_buddy.service import PATHS, WeatherService


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("WEATHER_LIVE_TESTS") != "1", reason="opt-in live network test")
@pytest.mark.parametrize("tool", PATHS)
async def test_pages_contract(tool):
    result = await WeatherService().call(tool)
    if result.error and (result.error.retryable or result.error.code == "network_error"):
        pytest.skip(f"Network/source unavailable: {result.error.code}: {result.error.message}")
    assert result.status != "error", result.model_dump_json()
    assert result.provenance.cache_headers.get("content-type")
    assert result.data is not None

import json
from datetime import timedelta

import httpx
import pytest
from conftest import NOW, response

from weather_buddy.parsers import DataError
from weather_buddy.service import MAX_BYTES, PATHS, WeatherService


def codes(result):
    return {w.code for w in result.warnings}


@pytest.mark.parametrize("tool", list(PATHS))
async def test_success(tool, service_factory):
    service, requests = service_factory()
    result = await service.call(tool)
    assert result.status != "error"
    assert result.provenance.last_success_at is None
    assert result.provenance.snapshot_not_live
    assert result.provenance.hash_status == (
        "not_applicable" if tool == "getSnapshotStatus" else "match"
    )
    assert len(requests) == (1 if tool == "getSnapshotStatus" else 2)


async def test_stale_despite_success(service_factory):
    service, _ = service_factory(now=NOW + timedelta(days=10))
    result = await service.call("getDwmlForecast")
    assert result.provenance.latest_attempt_success
    assert {"forecast_stale", "collection_stale", "forecast_expired"} <= codes(result)
    assert result.status == "degraded" and result.data


async def test_failed_hash_matches_is_not_fresh(service_factory, fixture_bytes):
    status = json.loads(fixture_bytes("status.json"))
    status["sources"][2]["success"] = False
    service, _ = service_factory({"status.json": json.dumps(status).encode()})
    r = await service.call("getDwmlForecast")
    assert r.provenance.hash_status == "match"
    assert "source_failed" in codes(r)
    r = await service.call("getSnapshotStatus")
    assert "source_failed" in codes(r)


async def test_generation_mismatch(service_factory, fixture_bytes):
    raw = fixture_bytes("forecast.dwml").replace(b"<value>81</value>", b"<value>80</value>", 1)
    service, _ = service_factory({"forecast.dwml": raw})
    r = await service.call("getDwmlForecast")
    assert r.provenance.hash_status == "mismatch"
    assert "publication_inconsistent" in codes(r)
    assert r.data is not None


@pytest.mark.parametrize("override", [response(b"", 404), b"{}", b"not json"])
async def test_missing_status(service_factory, override):
    service, _ = service_factory({"status.json": override})
    r = await service.call("getDwmlForecast")
    assert "status_unavailable" in codes(r) and r.data is not None


@pytest.mark.parametrize(
    "override,code",
    [
        (httpx.ReadTimeout("private info"), "timeout"),
        (httpx.ConnectError("private info"), "network_error"),
        (response(b"", 429), "http_error"),
        (response(b"", 503), "http_error"),
        (response(b"", 404), "http_error"),
        (response(b"", 302, {"Location": "http://evil.invalid"}), "http_error"),
        (b"<html/>", "not_dwml"),
        (b"not XML", "invalid_xml"),
        (b"x" * (MAX_BYTES + 1), "response_too_large"),
        (response(b"x", headers={"Content-Encoding": "gzip"}), "encoded_response"),
    ],
)
async def test_failures(service_factory, override, code):
    service, requests = service_factory({"forecast.dwml": override})
    r = await service.call("getDwmlForecast")
    assert r.status == "error" and r.data is None and r.error.code == code
    assert len(requests) == 1 and "private info" not in r.error.message


async def test_no_arbitrary_targets(service_factory):
    service, requests = service_factory()
    for target in ("https://evil.invalid", "/api/school-calendar.pdf", "/api/../status.json"):
        with pytest.raises(DataError):
            await service.fetch(target)
    assert not requests


@pytest.mark.parametrize("val", ["nan", "inf", "0", "1000"])
def test_bad_threshold(monkeypatch, val):
    monkeypatch.setenv("WEATHER_DWML_MAX_AGE_HOURS", val)
    with pytest.raises(ValueError):
        WeatherService()


async def test_unknown_and_future_times(service_factory, fixture_bytes):
    raw = fixture_bytes("forecast.dwml")
    for replacement, code in [
        (b"unknown", "forecast_unknown"),
        (b"2027-01-01T03:13:28-07:00", "forecast_future"),
    ]:
        service, _ = service_factory(
            {"forecast.dwml": raw.replace(b"2026-10-20T03:13:28-07:00", replacement)}
        )
        assert code in codes(await service.call("getDwmlForecast"))


async def test_total_deadline(monkeypatch):
    import anyio

    from weather_buddy import service as module

    async def slow(request):
        await anyio.sleep(0.2)
        return response(b"never reached")

    monkeypatch.setattr(module, "FETCH_DEADLINE_SECONDS", 0.01)
    service = WeatherService(transport=httpx.MockTransport(slow))
    result = await service.call("getDwmlForecast")
    assert result.error.code == "timeout" and result.error.retryable


async def test_unknown_afd_issuance(service_factory, fixture_bytes):
    raw = fixture_bytes("area-forecast-discussion.txt").replace(
        b"450 AM PDT Tue Oct 20 2026", b"Issuance unavailable"
    )
    service, _ = service_factory({"area-forecast-discussion.txt": raw})
    result = await service.call("getAreaForecastDiscussion")
    assert result.provenance.freshness_basis is None
    assert "forecast_unknown" in codes(result)


async def test_absent_source_and_hash(service_factory, fixture_bytes):
    status = json.loads(fixture_bytes("status.json"))
    status["sources"] = []
    service, _ = service_factory({"status.json": json.dumps(status).encode()})
    result = await service.call("getDwmlForecast")
    assert {"source_status_missing", "hash_unavailable"} <= codes(result)


async def test_threshold_config_and_fixed_requests(monkeypatch, service_factory):
    monkeypatch.setenv("WEATHER_DWML_MAX_AGE_HOURS", "1")
    service, requests = service_factory()
    result = await service.call("getDwmlForecast")
    assert "forecast_stale" in codes(result)
    assert result.provenance.threshold_hours == 1
    assert all(r.headers["Cache-Control"] == "no-cache" for r in requests)
    assert all(r.headers["Accept-Encoding"] == "identity" for r in requests)


async def test_normalized_output_limit(monkeypatch, service_factory):
    from weather_buddy import service as module

    monkeypatch.setattr(module, "MAX_OUTPUT_BYTES", 100)
    service, _ = service_factory()
    result = await service.call("getHourlyDwmlForecast")
    assert result.status == "error" and result.data is None
    assert result.error.code == "output_too_large"

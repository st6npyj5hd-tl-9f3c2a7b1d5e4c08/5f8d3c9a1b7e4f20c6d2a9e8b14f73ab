"""Bounded GET-only access to fixed Pages snapshots; no persistent cache or writes."""

import hashlib
import math
import os
from datetime import datetime, timezone

import anyio
import httpx

from .models import Failure, Provenance, Result, Warning
from .parsers import DataError, parse_afd, parse_dwml, parse_status, timestamp

BASE = "https://st6npyj5hd-tl-9f3c2a7b1d5e4c08.github.io/5f8d3c9a1b7e4f20c6d2a9e8b14f73ab"
PATHS = {
    "getDwmlForecast": "/api/forecast.dwml",
    "getHourlyDwmlForecast": "/api/hourly-forecast.dwml",
    "getAreaForecastDiscussion": "/api/area-forecast-discussion.txt",
    "getSnapshotStatus": "/api/status.json",
}
MAX_BYTES = 512 * 1024
MAX_OUTPUT_BYTES = 1024 * 1024
FETCH_DEADLINE_SECONDS = 12


def threshold(name, default):
    val = float(os.environ.get(name, default))
    if not math.isfinite(val) or not 1 <= val <= 168:
        raise ValueError(f"{name} must be finite and between 1 and 168 hours")
    return val


class WeatherService:
    def __init__(self, transport=None, now=None):
        self.transport = transport
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.limiter = anyio.CapacityLimiter(8)
        self.thresholds = {
            "getDwmlForecast": threshold("WEATHER_DWML_MAX_AGE_HOURS", 18),
            "getHourlyDwmlForecast": threshold("WEATHER_DWML_MAX_AGE_HOURS", 18),
            "getAreaForecastDiscussion": threshold("WEATHER_AFD_MAX_AGE_HOURS", 12),
            "getSnapshotStatus": threshold("WEATHER_STATUS_MAX_AGE_HOURS", 12),
        }

    async def fetch(self, path):
        if path not in PATHS.values():
            raise DataError("unsupported_source", "Only the four fixed Pages paths are supported.")
        try:
            with anyio.fail_after(FETCH_DEADLINE_SECONDS):
                async with httpx.AsyncClient(
                    transport=self.transport,
                    follow_redirects=False,
                    trust_env=False,
                    timeout=httpx.Timeout(8, connect=3, pool=3),
                ) as client:
                    async with client.stream(
                        "GET",
                        BASE + path,
                        headers={
                            "User-Agent": "weather-buddy-mcp/0.1",
                            "Accept-Encoding": "identity",
                            "Cache-Control": "no-cache",
                        },
                    ) as response:
                        if response.status_code != 200:
                            code = response.status_code
                            raise DataError(
                                "http_error",
                                f"Pages returned HTTP {code}; retry later or inspect the published source.",
                                code in (408, 429) or code >= 500,
                            )
                        if response.headers.get("content-encoding", "identity") != "identity":
                            raise DataError(
                                "encoded_response",
                                "Unexpected compressed response; cannot safely bound decoded size.",
                            )
                        body = bytearray()
                        async for chunk in response.aiter_raw(8192):
                            if len(body) + len(chunk) > MAX_BYTES:
                                raise DataError(
                                    "response_too_large",
                                    "Snapshot exceeds the 512 KiB safety limit.",
                                )
                            body.extend(chunk)
                        headers = {
                            k: response.headers[k][:200]
                            for k in ("date", "age", "etag", "last-modified", "content-type")
                            if k in response.headers
                        }
                        return bytes(body), headers
        except (httpx.TimeoutException, TimeoutError) as exc:
            raise DataError(
                "timeout",
                "Pages retrieval timed out. Retry later; no substitute forecast was used.",
                True,
            ) from exc
        except httpx.HTTPError as exc:
            raise DataError(
                "network_error",
                "Could not retrieve the Pages snapshot. Check network access and retry.",
                True,
            ) from exc

    async def call(self, name):
        if name not in PATHS:
            raise DataError("unknown_tool", "Unsupported weather tool.")
        async with self.limiter:
            result = await self._call(name)
            if len(result.model_dump_json().encode("utf-8")) > MAX_OUTPUT_BYTES:
                return Result(
                    status="error",
                    provenance=result.provenance,
                    error=Failure(
                        code="output_too_large",
                        message="Normalized snapshot exceeds the 1 MiB output limit; review the source structure.",
                    ),
                )
            return result

    async def _call(self, name):
        now = self.now()
        provenance = Provenance(
            source_url=BASE + PATHS[name],
            retrieved_at=now.isoformat(),
            threshold_hours=self.thresholds[name],
        )
        warnings = []

        def warn(code, message):
            warnings.append(Warning(code=code, message=message))

        def age(value, limit, prefix):
            dt = timestamp(value)
            if dt is None:
                warn(
                    prefix + "_unknown",
                    "Embedded time is missing or lacks a reliable timezone; freshness is uncertain.",
                )
                return None
            hours = (now - dt).total_seconds() / 3600
            if hours < -0.25:
                warn(
                    prefix + "_future",
                    "Source time is in the future; check source time and adapter clock.",
                )
            elif hours > limit:
                warn(
                    prefix + "_stale",
                    f"Source age exceeds the configured {limit:g}-hour threshold. Disclose staleness before using it.",
                )
            return round(hours, 3)

        try:
            payload, headers = await self.fetch(PATHS[name])
            provenance.cache_headers = headers
            provenance.sha256 = hashlib.sha256(payload).hexdigest()
            if name == "getSnapshotStatus":
                data = parse_status(payload)
                provenance.collection_attempt_at = data.collection_attempt_at
                provenance.hash_status = "not_applicable"
                provenance.freshness_basis = "collection_attempt_only"
                provenance.age_hours = age(
                    data.collection_attempt_at, self.thresholds[name], "collection"
                )
                warn(
                    "metadata_only",
                    "Collection status does not establish forecast freshness. Call each needed weather tool for embedded times and hash checks.",
                )
                for row in data.sources:
                    if row.success is not True:
                        warn(
                            "source_failed" if row.success is False else "source_status_missing",
                            f"{row.output_path}: latest collection failed or metadata is missing; retained files may be outdated.",
                        )
            else:
                data = (
                    parse_afd(payload)
                    if name == "getAreaForecastDiscussion"
                    else parse_dwml(payload)
                )
                provenance.issued_at = data.issued_at
                provenance.generated_at = getattr(data, "generated_at", None)
                basis = data.issued_at or provenance.generated_at
                provenance.freshness_basis = (
                    "issuance"
                    if data.issued_at
                    else "document_generation"
                    if provenance.generated_at
                    else None
                )
                provenance.age_hours = age(basis, self.thresholds[name], "forecast")
                if name != "getAreaForecastDiscussion":
                    warn(
                        "issuance_unproven",
                        "DWML creation-date is document generation, not independently proven model issuance or last successful download.",
                    )
                    if any(
                        i.start_local is None or (i.end and i.end_local is None)
                        for layout in data.layouts.values()
                        for i in layout.intervals
                    ):
                        warn(
                            "forecast_time_uncertain",
                            "Some validity timestamps cannot be converted reliably; retain source times and do not infer offsets.",
                        )
                    times = [
                        timestamp(i.end or i.start)
                        for layout in data.layouts.values()
                        for i in layout.intervals
                    ]
                    valid = [t for t in times if t]
                    if valid and max(valid) < now:
                        warn(
                            "forecast_expired", "All supplied forecast validity times have passed."
                        )
                    if any(v is None for p in data.parameters for v in p.values):
                        warn(
                            "missing_values",
                            "Some source values are missing; null does not mean zero or no hazard.",
                        )
                try:
                    status_payload, _ = await self.fetch(PATHS["getSnapshotStatus"])
                    status = parse_status(status_payload)
                    provenance.collection_attempt_at = status.collection_attempt_at
                    age(
                        status.collection_attempt_at,
                        self.thresholds["getSnapshotStatus"],
                        "collection",
                    )
                    row = next(r for r in status.sources if r.output_path == PATHS[name])
                    provenance.latest_attempt_success = row.success
                    if row.success is not True:
                        warn(
                            "source_failed" if row.success is False else "source_status_missing",
                            "Latest source collection failed or is unknown. This may be a retained older snapshot.",
                        )
                    if row.sha256:
                        provenance.hash_status = (
                            "match" if row.sha256.lower() == provenance.sha256 else "mismatch"
                        )
                        if provenance.hash_status == "mismatch":
                            warn(
                                "publication_inconsistent",
                                "Content hash differs from status. Pages caches or different publication generations may explain this; corruption is not established. Retry later.",
                            )
                    else:
                        warn(
                            "hash_unavailable",
                            "Status provides no content hash; publication consistency is uncertain.",
                        )
                except DataError as exc:
                    warn("status_unavailable", f"Freshness metadata unavailable: {exc.message}")
            return Result(
                status="degraded" if warnings else "ok",
                provenance=provenance,
                warnings=warnings,
                data=data,
            )
        except DataError as exc:
            return Result(
                status="error",
                provenance=provenance,
                warnings=warnings,
                error=Failure(code=exc.code, message=exc.message, retryable=exc.retryable),
            )

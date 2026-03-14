#!/usr/bin/env python3
"""Fetch upstream weather/school resources and publish static snapshots for GitHub Pages."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib import error, request

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
API_DIR = DOCS_DIR / "api"
STATUS_PATH = API_DIR / "status.json"
OPENAPI_PATH = DOCS_DIR / "openapi.yaml"

REQUEST_TIMEOUT_SECONDS = 30
USER_AGENT = "sd-snapshot-service/1.0"

OPENAPI_SERVER_URL = "https://st6npyj5hd-tl-9f3c2a7b1d5e4c08.github.io/5f8d3c9a1b7e4f20c6d2a9e8b14f73ab"


@dataclass(frozen=True)
class Source:
    logical_name: str
    source_url: str
    output_path: Path


SOURCES = [
    Source(
        logical_name="school-calendar",
        source_url=(
            "https://cdnsm5-ss18.sharpschool.com/UserFiles/Servers/Server_27732394/File/"
            "Academics/Academic%20Calendars/Traditional/Final%202025-26%20Academic%20Calendar%202025-26.pdf"
        ),
        output_path=API_DIR / "school-calendar.pdf",
    ),
    Source(
        logical_name="area-forecast-discussion",
        source_url=(
            "https://forecast.weather.gov/product.php?site=SGX&issuedby=SGX&product=AFD"
            "&format=TXT&version=1&glossary=0"
        ),
        output_path=API_DIR / "area-forecast-discussion.txt",
    ),
    Source(
        logical_name="forecast-dwml",
        source_url=(
            "https://forecast.weather.gov/MapClick.php?lat=32.8007&lon=-117.0497&unit=0"
            "&lg=english&FcstType=dwml"
        ),
        output_path=API_DIR / "forecast.dwml",
    ),
]


def sha256_file(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    hasher = hashlib.sha256()
    with path.open("rb") as infile:
        for chunk in iter(lambda: infile.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_openapi() -> None:
    content = f"""openapi: 3.1.0
info:
  title: San Diego Weather and School Snapshot API
  version: 1.0.0
  description: >-
    Static snapshot endpoints hosted on GitHub Pages. This API publishes periodic
    copies of upstream resources and is not a live proxy.
servers:
  - url: {OPENAPI_SERVER_URL}
    description: Replace with your GitHub Pages base URL
paths:
  /api/school-calendar.pdf:
    get:
      operationId: getSchoolCalendarPdf
      summary: Download the school district academic calendar PDF snapshot
      description: >-
        Returns the latest fetched copy of the district academic calendar PDF
        published by this repository.
      responses:
        '200':
          description: PDF snapshot of the school calendar.
          content:
            application/pdf:
              schema:
                type: string
                format: binary
  /api/area-forecast-discussion.txt:
    get:
      operationId: getAreaForecastDiscussion
      summary: Get the San Diego area forecast discussion text snapshot
      description: >-
        Returns the latest fetched text version of the NWS San Diego Area
        Forecast Discussion.
      responses:
        '200':
          description: Plain text area forecast discussion snapshot.
          content:
            text/plain:
              schema:
                type: string
  /api/forecast.dwml:
    get:
      operationId: getDwmlForecast
      summary: Get the NWS DWML XML forecast snapshot for San Diego
      description: >-
        Returns the latest fetched DWML forecast XML for the configured
        San Diego latitude/longitude point.
      responses:
        '200':
          description: DWML XML forecast snapshot.
          content:
            application/xml:
              schema:
                type: string
  /api/status.json:
    get:
      operationId: getSnapshotStatus
      summary: Get snapshot refresh status metadata
      description: >-
        Returns generation timestamp and per-source fetch metadata, including
        success/failure details and published file hashes.
      responses:
        '200':
          description: Status and fetch metadata for the latest snapshot run.
          content:
            application/json:
              schema:
                type: object
                additionalProperties: true
"""
    OPENAPI_PATH.write_text(content, encoding="utf-8")


def fetch_source(source: Source) -> tuple[dict, bool]:
    result = {
        "logical_name": source.logical_name,
        "source_url": source.source_url,
        "output_path": f"/{source.output_path.relative_to(DOCS_DIR).as_posix()}",
        "success": False,
        "http_status": None,
        "content_type": None,
        "bytes_written": None,
        "sha256": sha256_file(source.output_path),
        "error": None,
    }

    req = request.Request(
        source.source_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        },
        method="GET",
    )

    try:
        with request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = response.read()
            result["http_status"] = response.status
            result["content_type"] = response.headers.get("Content-Type")

        source.output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = source.output_path.with_suffix(source.output_path.suffix + ".tmp")
        tmp_path.write_bytes(payload)
        os.replace(tmp_path, source.output_path)

        result["success"] = True
        result["bytes_written"] = len(payload)
        result["sha256"] = sha256_file(source.output_path)
        return result, True
    except error.HTTPError as exc:
        result["http_status"] = exc.code
        result["content_type"] = exc.headers.get("Content-Type") if exc.headers else None
        result["error"] = f"HTTP error: {exc.code}"
    except error.URLError as exc:
        result["error"] = f"URL error: {exc.reason}"
    except TimeoutError:
        result["error"] = "Request timed out"
    except OSError as exc:
        result["error"] = f"File write error: {exc}"

    result["sha256"] = sha256_file(source.output_path)
    return result, False


def main() -> int:
    API_DIR.mkdir(parents=True, exist_ok=True)

    source_results: list[dict] = []
    successes = 0

    for source in SOURCES:
        source_result, ok = fetch_source(source)
        source_results.append(source_result)
        if ok:
            successes += 1

    status = {
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "sources": source_results,
    }
    STATUS_PATH.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    write_openapi()

    if successes == 0:
        print("All source fetches failed.")
        return 1

    print(f"Fetch completed with {successes}/{len(SOURCES)} successful source updates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

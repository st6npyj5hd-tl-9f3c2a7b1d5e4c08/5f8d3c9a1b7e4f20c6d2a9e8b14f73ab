"""Parse source data without inventing values, intervals, or issuance times."""

import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

from .models import (
    Discussion,
    Forecast,
    Interval,
    Layout,
    Node,
    Parameter,
    SnapshotStatus,
    SourceAttempt,
)

LOCAL = ZoneInfo("America/Los_Angeles")
WEATHER_PATHS = (
    "/api/forecast.dwml",
    "/api/hourly-forecast.dwml",
    "/api/area-forecast-discussion.txt",
)


class DataError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        self.code, self.message, self.retryable = code, message, retryable
        super().__init__(message)


def timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo is not None else None
    except ValueError:
        return None


def local_time(value: str | None) -> str | None:
    dt = timestamp(value)
    return dt.astimezone(LOCAL).isoformat() if dt else None


def node(element) -> Node:
    return Node(
        tag=element.tag,
        attributes=dict(element.attrib),
        text=(element.text or "").strip() or None,
        children=[node(c) for c in element],
    )


def value(element):
    if element.get("nil") in ("true", "1"):
        return None
    if len(element) or element.attrib:
        return node(element)
    text = (element.text or "").strip()
    return None if text in ("", "NA", "N/A", "NULL") else text


def parse_dwml(payload: bytes) -> Forecast:
    try:
        root = ET.fromstring(payload, forbid_dtd=True)
    except (ET.ParseError, DefusedXmlException, ValueError) as exc:
        raise DataError(
            "invalid_xml", "DWML is invalid XML or contains forbidden entities/DTD."
        ) from exc
    # Namespace-tolerant including the source's http and https xsi variants.
    for element in root.iter():
        element.tag = element.tag.split("}")[-1]
        element.attrib = {k.split("}")[-1]: v for k, v in element.attrib.items()}
    if root.tag != "dwml":
        raise DataError("not_dwml", "Expected DWML; Pages may contain an upstream HTML error page.")
    # Bound structure/depth before recursive normalization.
    stack = [(root, 0)]
    count = 0
    while stack:
        element, depth = stack.pop()
        count += 1
        if (
            depth > 20
            or count > 30000
            or sum(len(k) + len(v) for k, v in element.attrib.items()) > 8192
        ):
            raise DataError("structure_limit", "DWML exceeds safe structure limits.")
        stack.extend((c, depth + 1) for c in element)
    blocks = [b for b in root.findall("data") if b.get("type") in (None, "forecast")]
    if sum(len(b.findall("parameters/*")) for b in blocks) > 64:
        raise DataError("structure_limit", "Too many forecast parameter series.")
    layouts, locations, parameters = {}, [], []
    for block in blocks:
        locations.extend(node(e) for e in block.findall("location"))
        block_layouts = {}
        for layout in block.findall("time-layout"):
            key = layout.findtext("layout-key")
            starts = layout.findall("start-valid-time")
            ends = layout.findall("end-valid-time")
            if not key or not starts or (ends and len(ends) != len(starts)):
                raise DataError(
                    "time_alignment", "Missing or inconsistent DWML time-layout entries."
                )
            intervals = []
            for i, start in enumerate(starts):
                s = (start.text or "").strip() or None
                e = ((ends[i].text or "").strip() or None) if ends else None
                intervals.append(
                    Interval(
                        start=s,
                        end=e,
                        start_local=local_time(s),
                        end_local=local_time(e),
                        period_name=start.get("period-name"),
                    )
                )
            normalized = Layout(attributes=dict(layout.attrib), intervals=intervals)
            if key in layouts and layouts[key] != normalized:
                raise DataError("time_alignment", "Conflicting DWML layout keys.")
            layouts[key] = block_layouts[key] = normalized
        for group in block.findall("parameters"):
            for param in group:
                key = param.get("time-layout")
                if key not in block_layouts:
                    raise DataError(
                        "time_alignment", "A forecast parameter references a missing time-layout."
                    )
                values = [value(c) for c in param if c.tag != "name"]
                if len(values) != len(layouts[key].intervals):
                    raise DataError(
                        "time_alignment",
                        "Forecast values do not match their time-layout; alignment is uncertain.",
                    )
                parameters.append(
                    Parameter(
                        element=param.tag,
                        attributes={**group.attrib, **param.attrib},
                        name=param.findtext("name"),
                        time_layout=key,
                        values=values,
                    )
                )
    if not parameters or not locations:
        raise DataError("missing_parameters", "No usable forecast parameters or location in DWML.")
    for block in blocks:
        if not block.findall("location/point"):
            raise DataError("location_mismatch", "Forecast location has no grid coordinates.")
        for point in block.findall("location/point"):
            try:
                lat, lon = float(point.get("latitude", "nan")), float(point.get("longitude", "nan"))
            except ValueError as exc:
                raise DataError("location_mismatch", "Invalid source location.") from exc
            # NWS grid point differs slightly from requested coordinates; do not relabel it.
            if not (abs(lat - 32.8007) < 0.05 and abs(lon + 117.0497) < 0.05):
                raise DataError(
                    "location_mismatch", "DWML does not describe the configured local grid area."
                )
    source = root.find("head/source")
    return Forecast(
        generated_at=root.findtext("head/product/creation-date"),
        source=node(source) if source is not None else None,
        locations=locations,
        layouts=layouts,
        parameters=parameters,
        excluded_observation_blocks=len(root.findall("data")) - len(blocks),
    )


def parse_afd(payload: bytes) -> Discussion:
    try:
        raw = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DataError("invalid_afd", "Discussion is not valid UTF-8 text.") from exc
    if re.search(r"<(?:!doctype|html|pre|body)\b", raw, re.I):
        soup = BeautifulSoup(raw, "html.parser")
        for unwanted in soup(["script", "style", "nav", "noscript"]):
            unwanted.decompose()
        candidates = [p.get_text().strip() for p in soup.find_all("pre")]
    else:
        candidates = [raw.strip()]
    candidates = [
        t
        for t in candidates
        if re.search(r"\bAFDSGX\b", t)
        and "Area Forecast Discussion" in t
        and "National Weather Service San Diego" in t
        and re.search(r"^\.[A-Z][A-Z /]+\.\.\.", t, re.M)
    ]
    if len(candidates) != 1:
        raise DataError(
            "afd_extraction",
            "Could not uniquely identify the NWS San Diego AFD product. Review the source page structure.",
        )
    text = candidates[0]
    match = re.search(
        r"^(\d{1,4}) (AM|PM) (PDT|PST) (\w{3}) (\w{3}) (\d{1,2}) (\d{4})\s*$", text, re.M
    )
    issued = None
    if match:
        clock, ampm, zone, weekday, month, day, year = match.groups()
        try:
            dt = datetime.strptime(
                f"{clock.zfill(4)} {ampm} {month} {day} {year}", "%I%M %p %b %d %Y"
            )
            dt = dt.replace(tzinfo=timezone(timedelta(hours=-7 if zone == "PDT" else -8)))
            # Validate the stated offset against LA's DST rules, including repeated hours.
            if dt.astimezone(LOCAL).tzname() == zone and dt.strftime("%a") == weekday:
                issued = dt.isoformat()
        except ValueError:
            pass
    return Discussion(
        text=text, issued_at=issued, issuance_text=match.group(0).strip() if match else None
    )


def parse_status(payload: bytes) -> SnapshotStatus:
    try:
        raw = json.loads(payload)
        if not isinstance(raw, dict) or not timestamp(raw.get("generated_at_utc")):
            raise ValueError
        rows = raw["sources"]
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise ValueError
        sources = []
        for path in WEATHER_PATHS:
            matches = [r for r in rows if r.get("output_path") == path]
            if len(matches) > 1:
                raise ValueError
            row = matches[0] if matches else {}
            success = row.get("success")
            digest = row.get("sha256")
            if success is not None and not isinstance(success, bool):
                raise ValueError
            if digest is not None and not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
                raise ValueError
            sources.append(
                SourceAttempt(
                    output_path=path,
                    success=success,
                    http_status=row.get("http_status"),
                    sha256=digest,
                )
            )
        return SnapshotStatus(collection_attempt_at=raw["generated_at_utc"], sources=sources)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise DataError(
            "invalid_status",
            "Status metadata is malformed or lacks a valid collection attempt time.",
        ) from exc

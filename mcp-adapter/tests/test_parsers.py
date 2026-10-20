import json
from xml.etree import ElementTree as ET

import pytest

from weather_buddy.parsers import DataError, local_time, parse_afd, parse_dwml, parse_status


def test_general_source_fidelity(fixture_bytes):
    raw = fixture_bytes("forecast.dwml")
    d = parse_dwml(raw)
    assert d.generated_at == "2026-10-20T03:13:28-07:00"
    assert d.issued_at is None
    assert d.excluded_observation_blocks == 1
    assert len(d.parameters) == 6
    assert d.parameters[0].values == ["81", "79", "70", "72", "80", "81", "82"]
    assert d.parameters[0].attributes["units"] == "Fahrenheit"
    assert d.parameters[2].values[:4] == [None, None, None, "90"]
    assert d.layouts[d.parameters[1].time_layout].intervals[0].period_name == "Tonight"
    assert d.layouts[d.parameters[0].time_layout].intervals[0].end is None
    # All scalar samples and layout positions compared against the original XML.
    root = ET.fromstring(raw)
    source = root.find("data/parameters")
    for param, original in zip(d.parameters, source, strict=True):
        samples = [x for x in original if x.tag != "name"]
        assert len(param.values) == len(samples) == len(d.layouts[param.time_layout].intervals)
        for actual, expected in zip(param.values, samples, strict=True):
            if not expected.attrib and not len(expected):
                assert actual == expected.text.strip()


def test_hourly_all_parameters(fixture_bytes):
    raw = fixture_bytes("hourly-forecast.dwml")
    d = parse_dwml(raw)
    assert len(d.parameters) == 11
    assert all(len(p.values) == 168 for p in d.parameters)
    qpf = next(p for p in d.parameters if p.element == "hourly-qpf")
    assert qpf.attributes["units"] == "inches"
    assert qpf.values[0] == "0"
    assert "0.0150" in qpf.values
    assert {p.attributes.get("type") for p in d.parameters if p.element == "wind-speed"} == {
        "gust",
        "sustained",
    }
    rain = next(p for p in d.parameters if p.element == "weather")
    assert rain.values[0] is None
    assert rain.values[32].children[0].attributes["weather-type"] == "rain"
    root = ET.fromstring(raw)
    for p, original in zip(d.parameters, root.find("data/parameters"), strict=True):
        for actual, expected in zip(p.values, original, strict=True):
            if expected.tag == "value" and not expected.attrib:
                assert actual == (expected.text.strip() if expected.text else None)
    layout = next(iter(d.layouts.values()))
    assert [i.start for i in layout.intervals] == [
        x.text for x in root.findall("data/time-layout/start-valid-time")
    ]
    assert [i.end for i in layout.intervals] == [
        x.text for x in root.findall("data/time-layout/end-valid-time")
    ]
    assert len(d.model_dump_json()) < len(raw)


def test_namespace_and_hazards(fixture_bytes):
    raw = fixture_bytes("forecast.dwml").replace(
        b"<dwml version=", b'<dwml xmlns="urn:dwml" version='
    )
    d = parse_dwml(raw)
    assert d.parameters[2].values[0] is None
    raw = raw.replace(b"<weather time-layout=", b"<hazards time-layout=", 1).replace(
        b"</weather>", b"</hazards>", 1
    )
    assert parse_dwml(raw).parameters[3].element == "hazards"


@pytest.mark.parametrize(
    "source,expected",
    [
        ("2026-11-01T08:30:00Z", "2026-11-01T01:30:00-07:00"),
        ("2026-11-01T09:30:00Z", "2026-11-01T01:30:00-08:00"),
        ("2026-03-08T09:30:00Z", "2026-03-08T01:30:00-08:00"),
        ("2026-03-08T10:30:00Z", "2026-03-08T03:30:00-07:00"),
        ("2026-10-20T09:00:00", None),
        ("broken", None),
    ],
)
def test_local_dst(source, expected):
    assert local_time(source) == expected


@pytest.mark.parametrize(
    "raw,code",
    [
        (b"<html>error</html>", "not_dwml"),
        (b"<dwml>", "invalid_xml"),
        (
            b'<!DOCTYPE dwml [<!ENTITY e SYSTEM "file:///etc/passwd">]><dwml>&e;</dwml>',
            "invalid_xml",
        ),
        (b"<dwml/>", "missing_parameters"),
    ],
)
def test_invalid_dwml(raw, code):
    with pytest.raises(DataError) as exc:
        parse_dwml(raw)
    assert exc.value.code == code


def test_misalignment_and_location(fixture_bytes):
    raw = fixture_bytes("forecast.dwml")
    for changed in (
        raw.replace(b"<value>81</value>", b"", 1),
        raw.replace(b'time-layout="k-p24h-n7-1"', b'time-layout="absent"', 1),
    ):
        with pytest.raises(DataError, match="layout"):
            parse_dwml(changed)
    with pytest.raises(DataError, match="configured"):
        parse_dwml(raw.replace(b'latitude="32.8"', b'latitude="40.0"'))


def test_afd_actual_html(fixture_bytes):
    d = parse_afd(fixture_bytes("area-forecast-discussion.txt"))
    assert d.issued_at == "2026-10-20T04:50:00-07:00"
    assert ".SYNOPSIS..." in d.text and ".AVIATION..." in d.text
    assert "<" not in d.text and "javascript" not in d.text and "Previous Version" not in d.text
    assert parse_afd(d.text.encode()) == d
    no_time = parse_afd(d.text.replace(d.issuance_text, "Time unknown").encode())
    assert no_time.issued_at is None


@pytest.mark.parametrize(
    "raw",
    [
        b"<html>No product</html>",
        b"<pre>Area Forecast Discussion</pre>",
        b"<script>AFDSGX</script>",
        b"\xff",
    ],
)
def test_afd_failure(raw):
    with pytest.raises(DataError):
        parse_afd(raw)


def test_status_interpretation(fixture_bytes):
    raw = fixture_bytes("status.json")
    d = parse_status(raw)
    assert len(d.sources) == 3
    assert all(r.last_success_at is None for r in d.sources)
    assert "school" not in d.model_dump_json()
    changed = json.loads(raw)
    changed["sources"][2]["success"] = False
    assert parse_status(json.dumps(changed).encode()).sources[0].success is False


@pytest.mark.parametrize(
    "raw",
    [
        b"{}",
        b"[]",
        b"{",
        b'{"generated_at_utc": 3}',
        b'{"generated_at_utc":"2026-10-20T00:00:00Z","sources":{}}',
    ],
)
def test_status_invalid(raw):
    with pytest.raises(DataError):
        parse_status(raw)


def test_nested_hazards_and_missing_temperature(fixture_bytes):
    raw = fixture_bytes("forecast.dwml")
    original = b'<weather time-layout="k-p12h-n13-1">'
    hazards = (
        b'<hazards time-layout="k-p12h-n13-1"><name>Hazards</name>'
        + b'<hazard-conditions><hazard phenomena="FL" significance="A"><hazardTextURL>https://weather.gov/sgx</hazardTextURL></hazard></hazard-conditions>'
        * 13
        + b"</hazards>"
    )
    d = parse_dwml(raw.replace(original, hazards + original))
    hazard = next(p for p in d.parameters if p.element == "hazards")
    assert hazard.values[0].children[0].attributes == {"phenomena": "FL", "significance": "A"}
    assert hazard.values[0].children[0].children[0].text == "https://weather.gov/sgx"
    root = ET.fromstring(raw)
    group = root.find("data/parameters")
    for p in list(group):
        if p.tag == "temperature":
            group.remove(p)
    assert not any(p.element == "temperature" for p in parse_dwml(ET.tostring(root)).parameters)


def test_dst_slots_do_not_merge(fixture_bytes):
    raw = fixture_bytes("hourly-forecast.dwml")
    raw = raw.replace(b"2026-10-20T09:00:00-07:00", b"2026-11-01T01:00:00-07:00")
    raw = raw.replace(b"2026-10-20T10:00:00-07:00", b"2026-11-01T01:00:00-08:00")
    d = parse_dwml(raw)
    intervals = next(iter(d.layouts.values())).intervals
    assert intervals[0].start_local == "2026-11-01T01:00:00-07:00"
    assert intervals[1].start_local == "2026-11-01T01:00:00-08:00"
    assert len(d.parameters[0].values) == len(intervals) == 168

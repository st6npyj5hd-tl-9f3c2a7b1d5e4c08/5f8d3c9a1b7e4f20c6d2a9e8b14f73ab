"""Explicit wire models. Numeric source values stay strings to retain precision."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Node(Model):
    tag: str
    attributes: dict[str, str] = Field(default_factory=dict)
    text: str | None = None
    children: list["Node"] = Field(default_factory=list)


class Interval(Model):
    start: str | None
    end: str | None
    start_local: str | None
    end_local: str | None
    period_name: str | None = None


class Layout(Model):
    attributes: dict[str, str]
    intervals: list[Interval]


class Parameter(Model):
    element: str
    attributes: dict[str, str]
    name: str | None
    time_layout: str
    # Index i refers to interval i, never joined by list position across layouts.
    values: list[str | Node | None]


class Forecast(Model):
    kind: Literal["forecast"] = "forecast"
    generated_at: str | None
    issued_at: str | None = None
    source: Node | None
    locations: list[Node]
    layouts: dict[str, Layout]
    parameters: list[Parameter]
    excluded_observation_blocks: int


class Discussion(Model):
    kind: Literal["discussion"] = "discussion"
    issued_at: str | None
    issuance_text: str | None
    text: str


class SourceAttempt(Model):
    output_path: str
    success: bool | None = None
    http_status: int | None = None
    sha256: str | None = None
    last_success_at: str | None = None


class SnapshotStatus(Model):
    kind: Literal["status"] = "status"
    collection_attempt_at: str
    sources: list[SourceAttempt]


class Provenance(Model):
    provider: str = "NWS San Diego"
    source_url: str
    retrieved_at: str
    configured_latitude: float = 32.8007
    configured_longitude: float = -117.0497
    timezone: str = "America/Los_Angeles"
    snapshot_not_live: bool = True
    collection_attempt_at: str | None = None
    generated_at: str | None = None
    issued_at: str | None = None
    last_success_at: str | None = None
    latest_attempt_success: bool | None = None
    sha256: str | None = None
    hash_status: Literal["match", "mismatch", "unavailable", "not_applicable"] = "unavailable"
    freshness_basis: str | None = None
    age_hours: float | None = None
    threshold_hours: float
    cache_headers: dict[str, str] = Field(default_factory=dict)


class Warning(Model):
    code: str
    message: str


class Failure(Model):
    code: str
    message: str
    retryable: bool = False


class Result(Model):
    schema_version: Literal["1.0"] = "1.0"
    status: Literal["ok", "degraded", "error"]
    provenance: Provenance
    warnings: list[Warning] = Field(default_factory=list)
    data: Forecast | Discussion | SnapshotStatus | None = None
    error: Failure | None = None

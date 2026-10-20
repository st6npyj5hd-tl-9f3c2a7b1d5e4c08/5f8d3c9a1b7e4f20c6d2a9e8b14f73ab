# Implementation review and test report

Validation date: 2026-10-20. Review branch: `feat/weather-buddy-mcp`.
Baseline: remote `main` at `f4b70f2d901cc15b4b186c8b6342ad3c6a323040`.
Development used a separate checkout to preserve unrelated uncommitted work in
the original workspace. No original files were restored, edited or committed.

## Results

Environment: Python 3.12.15, official MCP SDK 1.30.0, uv 0.13.4; full transitive
versions and hashes are in `uv.lock`.

Commands below are relative to `mcp-adapter/`. The validation environment used
its temporary absolute uv executable and `.venv/bin/` equivalents of `uv run`.

| Command | Result |
| --- | --- |
| `uv sync --locked` | Passed; lock and editable package build verified |
| `.venv/bin/pytest -q` | **63 passed, 4 skipped** (opt-in live cases intentionally skipped) |
| `WEATHER_LIVE_TESTS=1 .venv/bin/pytest -q -m live -rs` | **4 passed, 63 deselected**; all four real Pages contracts passed |
| `.venv/bin/ruff check src tests scripts` | Passed |
| `.venv/bin/ruff format --check src tests scripts` | Passed; 15 Python files |
| `.venv/bin/python scripts/build_artifacts.py` | Plugin zip and four frozen fixture oracle JSON responses built |
| `git diff --cached --check -- . ':!mcp-adapter/tests/fixtures/**'` (repository root) | Passed; exact source fixtures intentionally retain upstream whitespace |
| `git diff --exit-code -- ../README.md ../docs ../scripts ../requirements.txt ../.github/workflows/fetch-and-deploy.yml` | Passed; no tracked production changes |

No outstanding test failures. During setup, an offline sync against a deliberately
empty temporary cache could not resolve the hatchling build dependency; the final
normal locked sync passed. Dependency installation needs registry access or a
populated cache; **the test suite does not need live weather/network access**.

The integration tests use the official MCP ClientSession and Streamable HTTP
client against the real ASGI transport implementation with controlled upstream
HTTP responses. They exercise initialization, discovery, every tool's schemas,
representative calls, `isError`, read-only hints, unknown tools, input rejection,
and host protection. This is a standards-compliant client equivalent to Inspector;
no Inspector GUI or ChatGPT deployment is claimed.

Parser coverage includes original general/hourly XML scalar and validity-array
comparisons; namespaces/nils/zeros; lexical units/precision; wind/QPF/humidity;
nested conditions/hazards; missing series; DST offsets; malformed XML/DTD/HTML;
source location; actual AFD HTML and failed extraction. Service tests cover
status semantics, partial collection failure, missing metadata/hash, stale and
expired forecasts, future/unknown times, publication mismatch, timeouts including
a total deadline, HTTP/rate limits, redirect refusal, response/output caps and
compressed-response refusal. Portable manifests validate against vendored official
schemas. `tools.json` is checked against actual registration.

The optional live pass verifies retrieval/parsing, not correctness of NWS forecasts,
new issuance, Plus account access or Sites deployment. CI runs only the deterministic
suite and build; it never fetches production weather or deploys/commits anything.

## Added file inventory

All paths below are under `mcp-adapter/` except the new workflow.

| File | Purpose |
| --- | --- |
| `README.md` | Architecture, isolated setup, commands and artifact index |
| `.gitignore` | Excludes local venv, caches and generated review artifacts |
| `pyproject.toml` | Isolated runtime/dev dependencies, entry point and checks |
| `uv.lock` | Reproducible dependency versions and integrity hashes |
| `src/weather_buddy/__init__.py` | Package marker |
| `src/weather_buddy/models.py` | Explicit response models and JSON Schemas |
| `src/weather_buddy/parsers.py` | DWML normalization, safe AFD extraction and status interpretation |
| `src/weather_buddy/service.py` | Fixed read-only HTTP access, bounds, freshness and consistency |
| `src/weather_buddy/server.py` | Four-tool official SDK Streamable HTTP server |
| `plugin/plugin.json` | Current portable plugin manifest; no invented IDs |
| `plugin/mcp.json` | Local authoring Streamable HTTP configuration |
| `plugin/skills/weather-buddy/SKILL.md` | Technical usage/freshness/limitation instructions |
| `scripts/export_contract.py` | Regenerates discovery schemas for review/Sites adaptation |
| `scripts/build_artifacts.py` | Produces plugin zip and deterministic fixture oracles without deploying |
| `docs/contract.md` | Human-readable tools, response shapes, bounds and policies |
| `docs/tools.json` | Exact machine-readable tool discovery catalog and output schemas |
| `docs/deployment.md` | Sites procedure, runtime gap, portable alternative and rollback |
| `docs/site-building-prompt.md` | Owner-authorized future Site draft prompt with publication stop |
| `docs/migration-regression.md` | Original-instruction reconciliation and six end-user scenarios |
| `docs/review.md` | This test report, file inventory and limitations |
| `tests/conftest.py` | Controlled HTTP responses, frozen clock and fixture loading |
| `tests/test_parsers.py` | Source fidelity, time alignment, DST, AFD and malformed data tests |
| `tests/test_service.py` | Freshness, failures, fixed-target and bounds tests |
| `tests/test_mcp.py` | Official client HTTP protocol/schema and tool registration tests |
| `tests/test_package.py` | Manifest schema validation, skill linkage and contract drift checks |
| `tests/test_live.py` | Separately opted-in, read-only Pages contract checks |
| `tests/fixtures/README.md` | Fixture commit/provenance and refresh guidance |
| `tests/fixtures/forecast.dwml` | Unmodified production general snapshot copy |
| `tests/fixtures/hourly-forecast.dwml` | Unmodified production hourly snapshot copy |
| `tests/fixtures/area-forecast-discussion.txt` | Unmodified production AFD HTML copy |
| `tests/fixtures/status.json` | Unmodified production attempt metadata copy, including calendar filtering case |
| `tests/schemas/README.md` | Official schema source URLs and retrieval date |
| `tests/schemas/plugin.schema.json` | Vendored portable manifest schema for offline validation |
| `tests/schemas/mcp.schema.json` | Vendored MCP package schema for offline validation |
| `../.github/workflows/validate-weather-mcp.yml` | PR-only read-permission lint/tests/package build; no schedule/deployment |

Generated `dist/` outputs are reproducible review materials and ignored by Git.
The zip is a prepared local package, not an installed ChatGPT plugin.

## Remaining gates and risks

- **Prepared, not deployed:** Site creation procedure and portable package.
  There is no tested Site-runtime port yet; the owner must authorize a build and
  validate runtime parity before publishing.
- **Pending owner/ChatGPT validation:** Plus controls, hosting usage terms,
  private Site auth/egress, real plugin connection, tool payload limits and all
  six conversation scenarios.
- **Pending owner input:** original GPT instructions/style/reference materials.
  No exact behavioral equivalence can be claimed without them.
- **Pending review:** PR approval, any merge, later private deployment/install,
  real migration and any alternative host/auth/cost decision.
- **Data limitations:** snapshots can be stale despite successful downloads;
  no independently proven per-source last-success time; no atomic Pages reads;
  AFD structure can change. These conditions produce explicit warnings/errors.
- **Protocol maintenance:** supported SDK 1.x is the portable baseline;
  current Sites protocol adaptation is separate. Review updates before hosting.
- **Out of scope:** producer improvements, calendar migration, live observations,
  alert monitoring, long-range data and new locations.

The original scheduled workflow, collector, all published files, OpenAPI schema,
Pages settings and original GPT/Actions remain unchanged by this work. No secrets,
paid resources, DNS settings, plugin installations or production deployments were
created. Actual GPT migration remains separate because it can make the original
GPT read-only; future platform retirement is not controlled by this PR.

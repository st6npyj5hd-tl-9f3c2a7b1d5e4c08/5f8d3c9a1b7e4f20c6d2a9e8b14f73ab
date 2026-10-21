# Implementation review and test report

Validation date: 2026-10-21 (private-review fixes). Review branch: `feat/weather-buddy-mcp`.
Baseline: remote `main` at `f4b70f2d901cc15b4b186c8b6342ad3c6a323040`.
Reviewed implementation baseline: `f4098266d27c9d0c1a944b2a5b5f55c447b68eee`.
Development used a separate checkout to preserve unrelated uncommitted work in
the original workspace. No original files were restored, edited or committed.

## Results

Environment: Python 3.12.15, official MCP SDK 1.30.0, uv 0.13.4; full transitive
versions and hashes are in `uv.lock`.

Commands below are relative to `mcp-adapter/`. The validation environment used
its temporary absolute uv executable and `.venv/bin/` equivalents of `uv run`.

| Command | Result |
| --- | --- |
| `uv sync --locked` | Initial baseline check passed; dependencies and lock unchanged by this review fix |
| `.venv/bin/pytest -q` | **88 passed, 4 skipped** (opt-in live cases intentionally skipped) |
| `WEATHER_LIVE_TESTS=1 .venv/bin/pytest -q -m live -rs` | **4 passed, 88 deselected**; all four real Pages contracts passed |
| `.venv/bin/ruff check src tests scripts` | Passed |
| `.venv/bin/ruff format --check src tests scripts` | Passed; 15 Python files |
| `.venv/bin/python scripts/build_artifacts.py` | Plugin zip and four frozen fixture oracle JSON responses rebuilt; ZIP integrity, exact packaged-file bytes and Result schema validation of all four oracles passed |
| `git diff --check` | Passed for the review changes; original fixture whitespace is unchanged |
| `git diff --exit-code f4b70f2d901cc15b4b186c8b6342ad3c6a323040 -- . ':!mcp-adapter/**' ':!.github/workflows/validate-weather-mcp.yml'` (repository root) | Passed; additionally compared all 18 original file blob hashes byte for byte |

No outstanding local test failures. Dependency installation needs registry access
or a populated cache; **the deterministic test suite does not need live weather or
network access**. No dependency or SDK change was needed for the review fix.

The integration tests use the official MCP ClientSession and Streamable HTTP
client against the real ASGI transport implementation with controlled upstream
HTTP responses. They exercise initialization, discovery, every tool's schemas,
representative calls, `isError`, read-only hints, unknown tools, input rejection,
Host/Origin protection and declared, streamed and understated request-body limits. This is a standards-compliant client equivalent to Inspector;
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

## Expiration review fix and reproduction

The previous code substituted an interval's start for a missing end, then declared
the whole forecast expired after the latest such timestamp. Before changing the
implementation, the new regression reproduced `forecast_expired` at
`2026-10-26T14:00:00Z` even though the final Monday period starts at
`2026-10-26T06:00:00-07:00`, has `end=null`, and retains its `"82"` Fahrenheit high.

The revised rule requires a reliable explicit end for **every** forecast interval
before asserting whole-forecast expiration. All such ends must be at or before
the check time. Any missing, invalid or offset-free end instead produces
`forecast_expiration_uncertain`. A start never supplies an end. This warning does
not establish indefinite applicability or freshness.

The fixture replay now returns Monday's unchanged period and high with
`forecast_expiration_uncertain`, `forecast_stale`, `collection_stale`,
`issuance_unproven` and `missing_values`; it does **not** return `forecast_expired`.
Thus source age, collection age and uncertain expiration remain distinct. The
technical skill and human-readable contract explain this distinction.

New committed regressions verify the exact Monday case; mixed valid/missing,
malformed or offset-free ends; fully established ends at the expiration boundary
and one hour later; and an explicit end still in the future. The old stale-general
fixture assertion was corrected: stale source data does not establish expiration.
No source fixture was edited to achieve these results.

## Requirements coverage matrix

“Pass locally” below applies to the Python adapter, controlled HTTP fixtures and
local ASGI transport. It does not validate the eventual hosted integration.

| Requirement | Evidence | Coverage / remaining gate |
| --- | --- | --- |
| Production isolation | Pinned comparison and blob hashes for all 18 original files, including original workflow, collector, OpenAPI, snapshots and calendar | Pass; only adapter review files changed |
| Four read-only tools; strict arguments; calendar excluded | `test_streamable_http_contract`, `test_no_arbitrary_targets`, `test_exported_contract_matches_server` | Pass locally; exact tool catalog unchanged |
| Original DWML content, units and precision | `test_general_source_fidelity`, `test_hourly_all_parameters`, missing-temperature and nested-hazard tests | Pass for committed fixtures and negative cases |
| Final period with unknown end | `test_started_final_period_without_end_is_not_expired`, exact Monday/82 F fixture replay at 2026-10-26T14:00:00Z | Pass; uncertain expiration, separate age warnings |
| Mixed known/unknown ends | `test_mixed_known_and_unknown_ends_preserve_uncertainty` (missing, invalid and offset-free end variants) | Pass; no whole-forecast expiration inferred |
| Established expiration | `test_explicitly_ended_forecast_is_expired` (exact end and one hour later), `test_future_explicit_end_is_not_expired` | Pass; explicit past ends still expire; future ends do not |
| Time alignment, timezone and DST | Layout comparisons, namespace/nil tests, `test_local_dst`, `test_dst_slots_do_not_merge` | Pass locally; offsets and repeated hours preserved |
| AFD HTML/plain-text extraction and ambiguity | `test_afd_actual_html`, `test_afd_failure`, new `test_afd_ambiguous_products` | Pass; multiple plausible products fail explicitly |
| AFD issuance validation | New `test_invalid_afd_issuance_is_preserved_as_unknown` (weekday, wrong seasonal offset, nonexistent spring hour, premature standard time, invalid date); valid repeated-hour control | Pass; original issuance text retained, unreliable parsed time unknown |
| XML structural bounds | New `test_xml_structural_limits` for depth >20, >30,000 elements, >8 KiB attributes and >64 series; existing DTD/entity rejection | Pass locally; bounded explicit errors |
| Fixed HTTP targets, redirects, timeouts and source/output limits | `test_failures`, total-deadline, fixed-target and normalized-output tests | Pass locally |
| Host and Origin rejection | `test_transport_host_protection`, new `test_transport_rejects_untrusted_origin` (foreign, null and lookalike origin) | Pass locally; no source requests on rejection |
| Request-body bounds | New `test_transport_rejects_oversized_request_body` with declared length, chunked data without Content-Length, and understated length | Pass locally; HTTP 413, no source requests |
| Source age, collection age, partial failures and cache inconsistency | Stale/success, failed-fetch/hash-match, missing status and generation-mismatch tests | Pass; independent warnings preserved |
| MCP protocol and schemas | Official SDK/client initialization, discovery, tool calls, schema checks, failure and input rejection | Pass locally; exactly four read-only tools |
| Plugin packaging and artifact build | Vendored official manifest schemas; skill/contract checks; rebuilt ZIP and four schema-valid fixture oracles | Prepared and checked locally; no installation validated |
| Read-only live Pages contracts | Four explicit opt-in contract checks passed on 2026-10-21 | Pass for observed responses; does not prove new issuance or hosted egress |
| Sites runtime implementation and fixture/schema parity | Version-controlled build procedure and Python oracle only | **Pending**; runtime adaptation is not implemented or validated |
| Hosted authentication and connectivity | Local Host/Origin tests are not hosted authentication or egress tests | **Pending** owner-authorized hosted implementation and verification |
| Real private plugin installation and connection | Local package exists; no real connection installed by this work | **Pending** in the owner's ChatGPT account |
| Original GPT instruction reconciliation | Technical skill explicitly requires owner-provided instructions | **Pending** original instructions, references and style comparison |
| End-to-end ChatGPT acceptance | Six scenarios in `migration-regression.md` | **Pending** actual ChatGPT tool/skill selection and behavior testing |

**The migration is not deployment-ready.** Passing local tests does not validate
Sites implementation, hosted authentication/connectivity, private plugin
installation, original-instruction reconciliation or ChatGPT acceptance. These
gates require separate owner authorization and recorded validation before use.
No merge, deployment, publication or production integration change was performed.

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

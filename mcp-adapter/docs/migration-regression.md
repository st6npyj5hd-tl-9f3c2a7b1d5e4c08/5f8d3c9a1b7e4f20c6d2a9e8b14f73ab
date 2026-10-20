# Original instruction reconciliation and regression plan

**Pending owner validation:** exact original GPT instructions, style, reference
files, account plugin access, Site runtime, end-to-end behavior. Nothing here is
claimed to be an exact migration of the original instructions.

The official migration guide says the latest published instructions become a
skill, custom Actions do not transfer, and migration makes the original GPT
read-only. Check the account's notice and timing; do not trigger migration during
this adapter trial. [Official migration FAQ](https://help.openai.com/en/articles/20001519-custom-gpt-retirement-and-migration-faq).

## Owner checklist

- [ ] Preserve an owner-controlled copy of the latest published GPT instructions,
  references, preferred output examples and existing conversation starters.
  Do not commit private instructions/reference files to this public repository.
- [ ] Supply those materials privately for reconciliation, or authorize the actual
  account migration later. Do not publish/edit the original GPT as part of this PR.
- [ ] Keep the supplied/migrated behavior skill and this technical integration skill
  in distinct folders. Review their triggers so a weather request uses both.
- [ ] Replace old weather-Action invocation references in the replacement only,
  using the four identical operation names and their new normalized contracts.
- [ ] Preserve original style, units/preferences and presentation rules wherever
  compatible. Explicitly resolve conflicts about live observations, freshness,
  calendar access or capabilities; do not silently claim they transferred.
- [ ] Retain or privately map necessary original references separately. The new
  plugin intentionally lacks calendar access; the original pipeline still has it.
- [ ] Keep the Site's real MCP connection while adding the instruction skill.
  If the migration creates a separate plugin, have the current plugin-creator
  reconcile the real registered connection as described in deployment.md.
- [ ] Review both final skills and tool registration together; no duplicate weather
  tools, missing skill, overwritten manifest or invented `plugin_asdk_app` ID.
- [ ] Run the comparison below with the original GPT unchanged and the replacement
  explicitly selected. Record failures and approve only the completed replacement.

## Comparison method

Use the same question, configured location, local date and published source
hashes. Save tool outputs/source files for the comparison: outputs collected hours
apart may reasonably differ. Compare factual claims against the captured data,
not just one model's prose. Record selected tools, timestamps, cited URLs, warning
disclosures, units, time alignment, missing values, and original style compliance.

Offline reference snapshot commit:
`f4b70f2d901cc15b4b186c8b6342ad3c6a323040`, collection attempt
`2026-10-20T16:29:03.198307Z`. Freeze the test clock at `2026-10-20T17:00:00Z`.
The Python fixture oracle exports these exact normalized responses for a Site port.

| Scenario / sample prompt | Required behavior and evidence |
| --- | --- |
| “Give me today's detailed local weather briefing.” | Status + general/hourly; Oct 20 fixture high 81 F, low 62 F, distinguish daytime/nighttime layouts, attribute NWS and generation time. Use owner's briefing style once provided. |
| “What does this week's local forecast look like?” | General forecast, highs/lows and worded periods through supplied horizon; no unsupported extension beyond the source. |
| “When could rain arrive Wednesday afternoon, October 21?” | Hourly valid intervals, PoP and QPF kept separate; source QPF retains 0.0150 precision. Explain forecast uncertainty, avoid promising an exact arrival minute or converting missing PoP to zero. |
| “Explain the latest NWS Area Forecast Discussion.” | Extract AFDSGX product, 450 AM PDT Tue Oct 20 2026 fixture issuance, preserve SYNOPSIS/AVIATION and other meaningful sections; no menus, script or HTML prose. Distinguish regional context from point forecast. |
| “Is this forecast current enough to rely on?” | Compare embedded times, validity, attempt result and hash. Repeat at clock +10 days: disclose stale/expired. Repeat failed-fetch and hash-mismatch fixtures: no false freshness/corruption assertion. |
| “Is there an active warning right now, and what is the current measured temperature?” | State snapshots cannot verify current alerts/observations. Cached DWML observations are excluded. AFD watches/warnings are dated context only. Direct user to current official NWS information; no invented all-clear or measured value. |

Additional negatives: “Forecast for New York,” arbitrary URL arguments, malformed
HTML, timeout, missing metadata and absent parameters. All must explain the
specific limitation without generic substitute weather or another provider.

## Acceptance record

- [x] Dedicated feature branch and isolated implementation/dependencies.
- [x] Four read-only tools; no school-calendar tool or arbitrary network target.
- [x] Snapshot-derived general/hourly/AFD fixtures and offline tests.
- [x] Freshness, failures, cache/hash inconsistency, DST and MCP contracts tested.
- [x] Portable package and skill prepared; Site procedure prepared.
- [x] Existing production files/workflow/OpenAPI/Pages settings untouched.
- [ ] PR reviewed and approved by owner (merge is a separate explicit approval).
- [ ] Site built and runtime parity verified under separate authorization.
- [ ] Private Site publication/plugin connection/install explicitly authorized.
- [ ] Original instructions supplied/imported and style regression approved.
- [ ] End-to-end ChatGPT tests recorded and approved.

Out of scope: upstream collector improvements, calendar migration, live observation
feeds, alert monitoring, other locations, paid hosting, production deployment and
actual GPT migration. Possible follow-up only: a reliably plain-text AFD source,
per-source last-success timestamps, and atomic publication-generation identifiers.
These would require a separate producer change and are not implemented here.

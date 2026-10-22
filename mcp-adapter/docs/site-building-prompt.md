# Copy into an owner-authorized future Sites build session

Build a NEW owner-private Weather Buddy Site from the reviewed `mcp-adapter/`
materials. This request authorizes a local draft/saved version only. **Do not
publish, deploy, install, activate, migrate a GPT, change secrets/DNS, create paid
resources, or modify the existing weather-data repository pipeline.** Stop with
reviewable source and test results before asking for deployment approval.

Use the current Sites skill and starter. Inspect `docs/deployment.md`,
`docs/contract.md`, `docs/tools.json`, Python source, tests and fixtures. Determine
the actual supported runtime before implementing. Do not assume a Python repo
can be directly imported. Port to the supported runtime if needed and report
that as a separate implementation requiring fixture parity tests.

Expose only `getDwmlForecast`, `getHourlyDwmlForecast`,
`getAreaForecastDiscussion`, `getSnapshotStatus`, with strict `{}` inputs and
read-only annotations. Use a stateless MCP route at `/mcp`, the current Site
protocol, and `"mcp"` hosting capability. Reuse real returned Site IDs; never
invent a project ID, plugin ID or connection mapping.

Fetch only these fixed public Pages URLs, by server-side GET with no redirects:
- https://st6npyj5hd-tl-9f3c2a7b1d5e4c08.github.io/5f8d3c9a1b7e4f20c6d2a9e8b14f73ab/api/forecast.dwml
- https://st6npyj5hd-tl-9f3c2a7b1d5e4c08.github.io/5f8d3c9a1b7e4f20c6d2a9e8b14f73ab/api/hourly-forecast.dwml
- https://st6npyj5hd-tl-9f3c2a7b1d5e4c08.github.io/5f8d3c9a1b7e4f20c6d2a9e8b14f73ab/api/area-forecast-discussion.txt
- https://st6npyj5hd-tl-9f3c2a7b1d5e4c08.github.io/5f8d3c9a1b7e4f20c6d2a9e8b14f73ab/api/status.json

Preserve the configured point 32.8007,-117.0497 and America/Los_Angeles. Follow the
contract for units, lexical precision, nil values, layouts, DST, AFD extraction,
issuance, collection attempts, unknown last-success times, stale warnings,
hashes/publication overlap, network errors and response/depth/timeout limits.
Do not expose the school calendar or cached observations. No storage, scheduled
jobs, write tools, model API calls or credentials for Pages are needed.

Generate the Python fixture oracle with `scripts/build_artifacts.py`; replay
fixtures in the Site implementation and compare complete outputs at the same
clock time. Port all failure/DST/network-boundary tests. Verify tool discovery
and output schemas against `tools.json`. Report any runtime validation that
requires a separate approved private deployment as pending, not passed.

Provide a minimal owner-facing page explaining the fixed location, snapshot
limitations and source status. Do not include secrets or fabricate current weather.
Keep the audience private. Prepare the technical skill, but state that the exact
original GPT instructions must come from the owner. Leave the original GPT
untouched. On a later authorized publication, reuse the Site-generated plugin;
do not create duplicate external MCP connections.

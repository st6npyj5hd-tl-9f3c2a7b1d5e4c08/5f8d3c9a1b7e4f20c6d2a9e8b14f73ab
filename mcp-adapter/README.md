# Weather Buddy MCP adapter

**Implemented and tested locally; prepared, not deployed.** This isolated adapter
replaces the four weather Actions with MCP tools while leaving the scheduled
publisher, Pages files, OpenAPI schema, calendar and original GPT untouched.
Original GPT instructions are not included and must be supplied by the owner.

The migration is **not deployment-ready**: Sites runtime implementation and parity,
hosted authentication/connectivity, real plugin installation, original-instruction
reconciliation and end-to-end ChatGPT acceptance remain unvalidated. Local test
and package checks do not satisfy these gates.

```text
ChatGPT → private Weather Buddy plugin + skill → MCP adapter
                                                    ↓ GET only
                                              GitHub Pages
                                                    ↑
                                    existing scheduled GitHub Actions
```

The Python implementation uses the official `mcp` SDK, stateless Streamable HTTP
and a fixed Pages origin. It requires no OpenAI API account, API key, NWS key,
GitHub token, database, scheduler or write access. Sites is the preferred future
host; Python is **not** asserted to run directly in Sites. See the runtime gap and
owner steps in [deployment.md](docs/deployment.md).

## Local setup and checks

Install Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/),
then from this directory:

```sh
uv sync --locked
uv run --frozen pytest -q
uv run --frozen ruff check src tests scripts
uv run --frozen ruff format --check src tests scripts
uv run --frozen weather-buddy-mcp
```

The last command listens only at `http://127.0.0.1:8000/mcp/`. The plugin's
`mcp.json` is a **local authoring configuration**. ChatGPT cloud cannot call your
loopback address. No installation or hosting is performed by these commands.

Optional public Pages reads (never run by normal CI):

```sh
WEATHER_LIVE_TESTS=1 uv run --frozen pytest -q -m live -rs
```

Network errors/timeouts/temporary 429 or 5xx responses are reported as skipped
live checks, not as a successful source contract validation. Parse errors and
permanent HTTP failures fail. Stale but valid data is returned with warnings.

## Review materials

- [Tool contract](docs/contract.md), [machine-readable schemas](docs/tools.json).
- [Deployment and rollback](docs/deployment.md), [Site-building prompt](docs/site-building-prompt.md).
- [Migration and regression checklist](docs/migration-regression.md).
- [Test report and file inventory](docs/review.md).
- [Portable plugin](plugin/plugin.json), [MCP configuration](plugin/mcp.json),
  [technical skill](plugin/skills/weather-buddy/SKILL.md).

Dependencies are isolated in `pyproject.toml`/`uv.lock`; the repository's original
requirements are unchanged. The locked official SDK is 1.30.0 on the supported
1.x maintenance line, with Streamable HTTP and the 2025-11-25 handshake. This is a
deliberate portable compatibility baseline; Sites' newer discovery protocol is
separately addressed in the runbook. Review new SDK maintenance releases before
any deployment. [SDK support policy](https://github.com/modelcontextprotocol/python-sdk/security).

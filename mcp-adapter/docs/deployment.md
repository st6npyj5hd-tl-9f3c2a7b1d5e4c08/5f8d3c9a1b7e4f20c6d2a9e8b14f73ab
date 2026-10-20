# Deployment preparation — owner approval required

Nothing in this PR creates a Site, publishes an endpoint, registers/installs a
plugin, edits a GPT, changes DNS/secrets, or deploys a cloud resource. Stop after
review until the owner separately authorizes the next action.

## Verified architecture and account limits (2026-10-20)

Sites is documented as available on Plus and Pro, through Work on web or Work/
Codex on supported desktop surfaces. Build usage and hosting usage are separate;
confirm the account's displayed limits/cost terms rather than assuming unlimited
free hosting. The adapter makes no OpenAI model API calls and needs no separately
billed API key. [Sites availability and usage](https://help.openai.com/en/articles/20001339-creating-and-using-chatgpt-sites).

A Site can expose MCP tools and produce an associated plugin when its owner
publishes it. Review/install/connect that plugin through its card or Personal
plugins. This is the preferred path for this personal-account use case.
[Official hosting guide](https://help.openai.com/en/articles/20001547-hosting-a-plugin-with-chatgpt-sites).

The reviewed public docs do **not** establish direct import/execution of this
Python repository in Sites. The installed OpenAI Sites integration guidance
(1.0.1, `references/site-mcp-server.md`) describes a Worker runtime and a stateless
JSON-RPC `POST /mcp`, with `capabilities: ["mcp"]` in `.openai/hosting.json`.
It prefers `2026-07-28` discovery (`server/discover`, `tools/list`, `tools/call`).
This is runtime guidance, not a Python compatibility guarantee. Re-read the
current Sites skill when implementing. Public entry point:
[Sites developer guide](https://learn.chatgpt.com/docs/sites).

**Chosen deliverable:** a tested portable Python adapter plus a version-controlled
Sites creation/adaptation procedure. No untested JavaScript port is presented as
a working implementation. Native Site implementation and parity checks remain
**pending owner-authorized build/runtime validation**. Do not create an external
proxy just to hide the Python/runtime difference.

## Sites procedure

1. **Owner:** confirm Plus account access to Sites and personal plugins. Use the
   account that owns Weather Buddy. Confirm usage/cost terms. If controls are
   absent, stop and use account support; do not create paid resources as a workaround.
2. **Owner:** open Work on ChatGPT web, or Work/Codex in the supported desktop app.
   Provide the reviewed PR/repository plus this adapter directory. Use
   [site-building-prompt.md](site-building-prompt.md). It explicitly requests a
   local draft/saved version with **no publishing or plugin activation**.
3. **Codex, after authorization to build:** create a separate Site project using
   the current Sites starter. Keep the audience owner-private. Read and reuse any
   existing `.openai/hosting.json`; otherwise obtain a real project ID only through
   Site creation, never invent one. Do not modify this repository's production paths.
4. **Codex:** implement exactly the four tools from `tools.json` in the runtime
   Sites actually supports. If Python execution is supported then, verify it
   explicitly; otherwise port `models.py`, `parsers.py`, `service.py` to TypeScript.
   Use the runtime's supported official MCP SDK where compatible, or the documented
   Site MCP route. Preserve every contract and warning, not just the happy path.
5. **Codex:** configure the fixed `service.BASE` and four paths. There are no source
   secrets. Use server-side HTTPS fetch with redirects disabled, bounded streams,
   timeouts, entity-safe XML parsing, HTML extraction and SHA-256. Do not load weather
   in browser code or expose arbitrary fetch URLs. Do not add storage or schedules.
6. **Codex:** add `"mcp"` to hosting capabilities only in that new Site project.
   Implement `server/discover` as required by the current runtime, plus tool list
   and calls. Retain strict empty input schemas, structured output and read-only
   annotations. For the documented 2026 protocol, discovery advertises
   `supportedVersions: ["2026-07-28"]`, `capabilities: {"tools": {}}`.
   Verify the current SDK/runtime requirements before using that example.
7. **Codex:** replay the committed fixtures and the generated oracle from
   `python scripts/build_artifacts.py`. Compare every parameter/value/layout,
   AFD product text, null, timestamp, hash and warning. Reproduce failure, DST,
   size-limit, redirect and invalid-argument cases from the tests. Do not ship if
   parsing, precision or freshness behavior diverges.
8. **Codex + owner:** verify actual Site-runtime outbound retrieval, content types,
   byte hashes, response limits, tool discovery/schemas, and authentication. A local
   Python pass does not satisfy this. If hosted runtime cannot be tested before
   publication, mark this gate pending and request a separately approved private
   validation deployment. Never claim an unpublished local preview proves hosting.
9. **Owner:** review the Site audience (owner-private), endpoint access, four tools,
   dependency changes, usage limits and results. No anonymous/public access should
   be enabled. Sites' access checks are separate from the public Pages origin.
10. **Only after explicit approval:** owner publishes the private Site. Publication
    creates/updates its associated plugin; a deployment URL is production even when
    private. Codex can carry out authorized publishing via Sites tools, but must not
    do so under the authorization for this PR.
11. **Owner:** review the plugin card, tools and permissions, then install/connect.
    If auto-connected by the surface, verify its actual state rather than creating
    a duplicate connection. Locate it under Plugins → Personal → Created by you.
12. **Owner + Codex:** supply original instructions and follow
    [migration-regression.md](migration-regression.md). Reuse the actual Site-created
    connection. Test in a fresh Work conversation using `@Weather Buddy` and all
    six scenarios before switching everyday use.

If runtime egress, XML libraries, payload limits or protocol support prevent
parity, document the specific failing gate. Keep the original GPT in use while
seeking approval for further adaptation or the portable alternative. There is no
automatic third-party hosting fallback.

## Local package and connection reconciliation

`plugin/plugin.json` and `plugin/mcp.json` use the current portable Agent Plugins
schemas; fixed `skills/` and `mcp.json` paths identify their components. No fabricated
registration ID or auth secret is included. [Official packaging format](https://developers.openai.com/plugins/build/plugins).

Build review artifacts with `uv run python scripts/build_artifacts.py`. The zip
contains the plugin files only; the Python adapter is installed separately. Its
loopback URL is suitable for a local-capable MCP client, not ChatGPT web. Review
package upload/local-marketplace availability on the actual surface before use.

For Sites, reuse its generated private plugin connection, not the loopback
`mcp.json`. Attach the technical skill to that plugin through the available editor/
plugin-creator workflow. If merging it into a separate owner-migrated plugin,
use only the actual registered connection ID returned by Sites. The official
packaging guide describes `extensions.com.openai.apps` pointing to `./.app.json`
for existing registered mappings. Ask the current plugin-creator to generate the
mapping from that real ID; inspect it before installation. Do not overwrite the
migrated skill with this technical skill or discard the MCP connection.

## Portable Python alternative

The official Python SDK is supported for MCP tool servers. This implementation
uses Streamable HTTP rather than legacy SSE transport.
[OpenAI MCP build guide](https://developers.openai.com/plugins/build/mcp-server).

1. Run the README's locked setup, offline tests and local server. Use an MCP
   client supporting Streamable HTTP against `http://127.0.0.1:8000/mcp/`.
2. For an approved owner-managed host, install Python 3.12+, copy only the adapter,
   run `uv sync --locked --no-dev`, then supervise `.venv/bin/weather-buddy-mcp`.
   Keep it bound to loopback. No backend credentials are needed.
3. **Before external hosting approval**, select and review a TLS/authentication
   reverse proxy with bounded body size, concurrency and timeouts. Forward only
   the MCP route to loopback; normalize its upstream Host to `127.0.0.1:8000` so
   the SDK host guard remains enabled. Configure an exact allowed browser Origin
   if required; do not disable host/origin protections or use wildcard CORS.
   Authentication must be compatible with the eventual ChatGPT connection.
   The Python server deliberately does not implement OAuth or public access itself.
4. After separate approval and host-specific testing, point a **copy** of the
   portable `mcp.json` at the verified HTTPS endpoint and configure its actual auth.
   Do not expose an unauthenticated public port. No tunnel, DNS, secret, cloud
   resource or deployment is created by this PR.
5. Confirm the account can connect this external server before paying for hosting.
   Official custom-server account guidance currently focuses on Business and
   Enterprise/Edu; do not assume that it applies to personal Plus. The Sites path
   has separate availability. [Custom-server connection requirements](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt).

This fallback needs an approved host and auth configuration; it is not a claim of
one-click Plus compatibility. The default remains Sites without a separate OpenAI
API billing relationship. Owner-specific hosting cost is an outstanding decision.

## Tested Python versus eventual Sites runtime

| Concern | Tested implementation | Required Sites validation |
| --- | --- | --- |
| Language | Python 3.12, locked SDK 1.30.0 | Current Worker-compatible stack; Python execution unproven |
| Protocol | Stateless Streamable HTTP; initialize handshake | Current Site discovery/version semantics, plugin refresh |
| XML/HTML | defusedxml, BeautifulSoup | Equivalent safe parsers, same fixtures and lexical precision |
| HTTP | httpx, fixed GET allowlist, timeouts/caps | Server-side fetch, abort deadlines, bounded decoding |
| Access | Localhost + SDK host/origin guard | Owner-private Site access checks and actual plugin auth |
| Packaging | Valid portable manifests, local URL | Site-created plugin and real connection mapping |
| Cost | No model API calls | Account usage/hosting terms verified by owner |

## Rollback

Before deployment: close or leave the PR unmerged; the original system is unchanged.
After an approved private trial: disable/uninstall only the new plugin, disconnect
its Site connection and return to the original GPT. Do not edit the producer,
calendar, Actions schedule, Pages configuration, snapshots or old Action schema.
Where Sites offers earlier saved versions, restore the selected known-good code
version and republish only with owner approval, then verify refreshed tools. Version
rollback does not restore databases/files; this design requires neither. If no
rollback control is available, leave the plugin disabled and ask for support.
Do not run actual GPT migration as a reversible trial: it can make the original
GPT read-only. Its future availability is also subject to OpenAI's retirement
policy, not controlled by this adapter.

import json

import httpx
import jsonschema
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from weather_buddy.server import create_app
from weather_buddy.service import PATHS


@pytest.mark.parametrize("bad_source", [False, True])
async def test_streamable_http_contract(service_factory, bad_source):
    service, requests = service_factory(
        {"forecast.dwml": b"<html>bad</html>"} if bad_source else {}
    )
    app = create_app(service)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), follow_redirects=True
        ) as http:
            async with streamable_http_client("http://localhost/mcp/", http_client=http) as (
                read,
                write,
                _,
            ):
                async with ClientSession(read, write) as client:
                    initialized = await client.initialize()
                    assert initialized.serverInfo.name == "weather-buddy"
                    tools = (await client.list_tools()).tools
                    assert {t.name for t in tools} == set(PATHS)
                    for tool in tools:
                        assert tool.inputSchema == {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False,
                        }
                        assert tool.annotations.readOnlyHint is True
                        assert tool.annotations.destructiveHint is False
                        assert tool.annotations.idempotentHint is True
                        jsonschema.Draft202012Validator.check_schema(tool.outputSchema)
                        result = await client.call_tool(tool.name, {})
                        body = result.structuredContent
                        assert body is not None
                        jsonschema.validate(body, tool.outputSchema)
                        assert json.loads(result.content[0].text) == body
                        assert result.isError == (bad_source and tool.name == "getDwmlForecast")
                    count = len(requests)
                    for arguments in (
                        {"url": "https://evil.invalid"},
                        {"latitude": 40},
                        {"location": "NYC"},
                    ):
                        result = await client.call_tool("getDwmlForecast", arguments)
                        assert result.isError
                    assert (await client.call_tool("getSchoolCalendarPdf", {})).isError
                    assert len(requests) == count
                    assert all(r.method == "GET" for r in requests)


async def test_transport_host_protection(service_factory):
    service, requests = service_factory()
    app = create_app(service)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app)) as http:
            r = await http.post(
                "http://evil.invalid/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            )
            assert r.status_code == 421
    assert not requests

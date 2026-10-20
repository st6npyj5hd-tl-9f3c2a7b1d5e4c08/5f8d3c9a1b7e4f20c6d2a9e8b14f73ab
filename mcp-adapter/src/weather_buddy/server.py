"""Official MCP SDK with stateless Streamable HTTP; loopback only by default."""

from contextlib import asynccontextmanager

import uvicorn
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.routing import Mount

from .models import Result
from .service import PATHS, WeatherService

DESCRIPTIONS = {
    "getDwmlForecast": "Read the NWS San Diego general forecast snapshot for 32.8007,-117.0497, with validity layouts, units and freshness warnings. Not live observations.",
    "getHourlyDwmlForecast": "Read the local NWS hourly forecast snapshot for precise timing. Preserve time-layout alignment, missing values and freshness warnings. Not live observations.",
    "getAreaForecastDiscussion": "Read the NWS San Diego Area Forecast Discussion extracted from the published HTML snapshot, with issuance and freshness warnings.",
    "getSnapshotStatus": "Read latest collection attempt metadata for the three weather sources. Success does not prove forecast freshness; no school calendar is exposed.",
}
INPUT_SCHEMA = {"type": "object", "properties": {}, "additionalProperties": False}


def registered_tools():
    return [
        types.Tool(
            name=name,
            description=DESCRIPTIONS[name],
            inputSchema=INPUT_SCHEMA,
            outputSchema=Result.model_json_schema(),
            annotations=types.ToolAnnotations(
                readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
            ),
        )
        for name in PATHS
    ]


def create_app(service=None):
    service = service or WeatherService()
    server = Server("weather-buddy", version="0.1.0")

    @server.list_tools()
    async def list_tools():
        return registered_tools()

    @server.call_tool()
    async def call_tool(name, arguments):
        # SDK schema validation rejects extra keys before any network I/O.
        result = await service.call(name)
        # Compact JSON avoids sending XML or duplicate expanded time rows.
        content = result.model_dump(mode="json")
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=result.model_dump_json())],
            structuredContent=content,
            isError=result.status == "error",
        )

    manager = StreamableHTTPSessionManager(
        app=server,
        stateless=True,
        json_response=True,
        max_request_body_size=16384,
        security_settings=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1", "localhost", "127.0.0.1:*", "localhost:*"],
            allowed_origins=["http://127.0.0.1:*", "http://localhost:*"],
        ),
    )

    @asynccontextmanager
    async def lifespan(app):
        async with manager.run():
            yield

    async def handle(scope, receive, send):
        await manager.handle_request(scope, receive, send)

    return Starlette(routes=[Mount("/mcp", app=handle)], lifespan=lifespan)


def main():
    uvicorn.run(create_app(), host="127.0.0.1", port=8000, limit_concurrency=16)


if __name__ == "__main__":
    main()

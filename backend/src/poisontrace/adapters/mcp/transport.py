from contextlib import asynccontextmanager, AsyncExitStack
from dataclasses import asdict
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
from importlib.metadata import version
from tempfile import TemporaryDirectory

import anyio
from jsonschema import validate
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from poisontrace.domain import EvidenceObservation, EvidenceTool
from poisontrace.application.errors import EvidenceToolError, InvestigationOutputLimit
from poisontrace.domain import investigation_attack


class LocalSocTransport:
    def __init__(self, timeout_seconds: float = 10, max_output_bytes: int = 16384):
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes

    @asynccontextmanager
    async def open(self, case, *, attack_family=None):
        attack = investigation_attack(attack_family) if attack_family else None
        async with AsyncExitStack() as stack:
            sessions = []
            for server_id in ("trusted-soc", "controlled-malicious"):
                sessions.append(await stack.enter_async_context(self._open_server(case, server_id,
                    attack.description if attack and server_id == "controlled-malicious" else None)))
            yield CombinedSession(sessions)

    @asynccontextmanager
    async def _open_server(self, case, server_id, description):
        payload = json.dumps({key: value for key, value in asdict(case).items() if key not in {"expected_decision", "dataset_category", "attack_targets", "supported_attack_families"}})
        if len(payload.encode("utf-8")) > self.max_output_bytes:
            raise InvestigationOutputLimit()
        with TemporaryDirectory(prefix="poisontrace-soc-") as directory, open(os.devnull, "w") as errors:
            parameters = StdioServerParameters(command=sys.executable,
                args=["-I", "-B", str(Path(__file__).with_name("server.py").resolve())],
                env={"POISONTRACE_CASE_JSON": payload, "POISONTRACE_SERVER_ID": server_id,
                     **({"POISONTRACE_DESCRIPTION": description} if description else {})}, cwd=directory)
            async with stdio_client(parameters, errlog=errors) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=self.timeout_seconds)) as session:
                    with anyio.fail_after(self.timeout_seconds):
                        initialized = await session.initialize()
                    yield SocSession(session, self.timeout_seconds, self.max_output_bytes,
                        {"server_id": server_id, "transport": "stdio", "sdk_version": version("mcp"),
                         "protocol_version": initialized.protocolVersion,
                         "server_info": initialized.serverInfo.model_dump(mode="json")})


class SocSession:
    def __init__(self, session, timeout_seconds, max_output_bytes, identity):
        self.identity = identity
        self.session = session
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.tools = ()

    async def discover(self):
        with anyio.fail_after(self.timeout_seconds):
            definitions = await self.session.list_tools()
        self.tools = tuple(EvidenceTool(self.identity["server_id"], tool.name, tool.description or "", tool.inputSchema,
                          bool(tool.annotations and tool.annotations.readOnlyHint),
                          tool.model_dump(mode="json", by_alias=True, exclude_none=True)) for tool in definitions.tools)
        return self.tools

    async def invoke(self, call):
        tool = next((tool for tool in self.tools if (tool.server_id, tool.name) == (call.server_id, call.name)), None)
        if tool is None:
            raise ValueError("unknown qualified tool")
        validate(call.arguments, tool.input_schema)
        with anyio.fail_after(self.timeout_seconds):
            result = await self.session.call_tool(call.name, call.arguments)
        if result.isError:
            raise EvidenceToolError()
        if len(result.model_dump_json().encode("utf-8")) > self.max_output_bytes:
            raise InvestigationOutputLimit()
        value = result.structuredContent
        if not isinstance(value, dict):
            raise ValueError("invalid synthetic result")
        return EvidenceObservation(call.server_id, call.name, call.arguments, value)


class CombinedSession:
    def __init__(self, sessions):
        self.sessions = {session.identity["server_id"]: session for session in sessions}
        self.identity = {"transport": "stdio", "servers": [session.identity for session in sessions]}

    async def discover(self):
        tools = []
        for session in self.sessions.values():
            tools.extend(await session.discover())
        return tuple(tools)

    async def invoke(self, call):
        if call.server_id not in self.sessions:
            raise ValueError("unknown configured server")
        return await self.sessions[call.server_id].invoke(call)

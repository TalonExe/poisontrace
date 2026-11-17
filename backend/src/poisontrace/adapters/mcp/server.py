"""Fixed stdio-only read tools. No caller-selected paths, endpoints or commands."""
import asyncio
import json
import os
from pathlib import Path
import sys

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations


def restrict_runtime():
    """Defense in depth for our bundled Python process, not an OS sandbox."""
    runtime_roots = (Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve())

    def audit(event, args):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.exec", "os.spawn", "ctypes.dlopen"}:
            raise PermissionError("operation outside synthetic testbed")
        if event == "open" and not isinstance(args[0], int):
            path = Path(args[0]).resolve()
            mode, flags = args[1], args[2]
            if (mode and any(char in mode for char in "wax+")) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
                raise PermissionError("testbed is read only")
            if not any(path.is_relative_to(root) for root in runtime_roots):
                raise PermissionError("file outside Python runtime")
        if event in {"os.remove", "os.rename", "os.mkdir", "os.rmdir", "os.link", "os.symlink", "os.truncate"}:
            raise PermissionError("testbed is read only")

    sys.addaudithook(audit)


def build_server(case: dict, server_id="trusted-soc", description=None) -> FastMCP:
    server = FastMCP("poisontrace-synthetic-soc" if server_id == "trusted-soc" else "poisontrace-controlled-malicious", log_level="ERROR")
    annotations = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)

    if server_id == "controlled-malicious":
        @server.tool(annotations=annotations, structured_output=True,
                     description=description or "Read synthetic advisory context.")
        def get_advisory(case_id: str) -> dict[str, object]:
            if case_id != case["case_id"]:
                raise ValueError("unknown synthetic case")
            return {"case_id": case_id, "case_version": case["case_version"],
                    "records": [{"evidence_id": "advisory-001", "note": "Synthetic advisory only."}],
                    "server_pid": os.getpid()}
        return server

    def read(name, case_id):
        if case_id != case["case_id"]:
            raise ValueError("unknown synthetic case")
        return {"case_id": case_id, "case_version": case["case_version"],
                "records": case["reads"][name], "server_pid": os.getpid()}

    @server.tool(annotations=annotations, structured_output=True)
    def get_alert(case_id: str) -> dict[str, object]:
        """Read the synthetic case's alert."""
        return read("get_alert", case_id)

    @server.tool(annotations=annotations, structured_output=True)
    def get_evidence(case_id: str) -> dict[str, object]:
        """Read the synthetic case's event, endpoint, process and network evidence."""
        return read("get_evidence", case_id)

    @server.tool(annotations=annotations, structured_output=True)
    def get_context(case_id: str) -> dict[str, object]:
        """Read synthetic asset/user context and prior-case references."""
        return read("get_context", case_id)

    return server


async def main():
    case = json.loads(os.environ.pop("POISONTRACE_CASE_JSON"))
    server = build_server(case, os.environ.pop("POISONTRACE_SERVER_ID", "trusted-soc"),
                          os.environ.pop("POISONTRACE_DESCRIPTION", None))
    # Install restrictions after the event loop and runtime have initialized.
    restrict_runtime()
    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())

"""Real stdio transport against the bundled read-only SOC server."""
import asyncio
import os
import sys


def test_separate_mcp_process_discovers_schemas_and_returns_synthetic_evidence():
    from poisontrace.adapters.mcp.cases import BundledCases
    from poisontrace.adapters.mcp.transport import LocalSocTransport
    from poisontrace.domain import InvestigationCall

    async def exercise():
        case = BundledCases().get("soc-auth-001")
        async with LocalSocTransport().open(case) as session:
            tools = await session.discover()
            assert {tool.name for tool in tools} == {"get_alert", "get_evidence", "get_context", "get_advisory"}
            assert {tool.server_id for tool in tools} == {"trusted-soc", "controlled-malicious"}
            assert all(tool.read_only for tool in tools)
            assert all(tool.input_schema["properties"]["case_id"]["type"] == "string" for tool in tools)
            observation = await session.invoke(InvestigationCall("trusted-soc", "get_evidence", {"case_id": case.case_id}))
            assert observation.result["records"][0]["evidence_id"] == "auth-001"
            assert observation.result["records"][0]["unauthorized_access"] is True
            assert observation.result["server_pid"] != os.getpid()
            assert "expected" not in str(observation.result)
            return observation.result["server_pid"]

    first = asyncio.run(exercise())
    second = asyncio.run(exercise())
    assert first != second, "Each investigation must start a fresh process"
    if sys.platform == "win32":
        import ctypes
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        for pid in (first, second):
            handle = kernel.OpenProcess(0x1000, False, pid)
            if handle:
                code = ctypes.c_ulong()
                assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
                kernel.CloseHandle(handle)
                assert code.value != 259, "Server process must have exited"


def test_bundled_runtime_denies_network_external_files_and_writes(tmp_path):
    import subprocess
    from pathlib import Path

    server = Path("backend/src/poisontrace/adapters/mcp/server.py").resolve()
    synthetic_file = tmp_path / "outside-runtime.txt"
    synthetic_file.write_text("synthetic-only")
    script = '''
import importlib.util, pathlib, socket, subprocess, sys
spec = importlib.util.spec_from_file_location("synthetic_server", sys.argv[1])
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
server.restrict_runtime()
blocked = 0
for operation in (lambda: socket.socket(), lambda: pathlib.Path(sys.argv[2]).read_text(),
                  lambda: pathlib.Path(sys.argv[2]).write_text("changed"),
                  lambda: subprocess.run([sys.executable, "-c", "pass"])):
    try:
        operation()
    except PermissionError:
        blocked += 1
assert blocked == 4, blocked
'''
    result = subprocess.run([sys.executable, "-I", "-B", "-c", script, str(server), str(synthetic_file)],
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert synthetic_file.read_text() == "synthetic-only"

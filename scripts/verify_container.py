"""Offline Linux container acceptance check using disposable named state only.

Requires a running Linux Docker or Podman engine. Builds with network access, then runs
without a network, host mounts, Docker socket or provider credentials.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
from tempfile import TemporaryDirectory
import textwrap
import time
from uuid import uuid4


def stage_build_context(project, destination):
    """Copy explicit build inputs without enumerating local state or tool folders."""
    destination = Path(destination).resolve()
    project = Path(project).resolve()
    if destination.is_relative_to(project):
        raise ValueError("build context must be outside the project")
    destination.mkdir(parents=True, exist_ok=True)
    required = ("Dockerfile", ".dockerignore", "pyproject.toml", "requirements-runtime.lock",
                "frontend/package.json", "frontend/package-lock.json", "frontend/index.html", "frontend/vite.config.js")
    for relative in required:
        source, target = project / relative, destination / relative
        if source.is_symlink():
            raise ValueError("build inputs must not be symbolic links")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for relative in ("backend/src/poisontrace", "frontend/src"):
        source, target = project / relative, destination / relative
        if source.is_symlink():
            raise ValueError("build inputs must not be symbolic links")
        shutil.copytree(source, target, symlinks=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".env", ".env.*", "*.db", "*.log"))
    if any(path.is_symlink() for path in destination.rglob("*")):
        raise ValueError("build inputs must not be symbolic links")


def main(argv=None, *, run=subprocess.run):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("docker", "podman"), default="docker")
    engine = parser.parse_args(argv).engine
    project = Path(__file__).resolve().parents[1]
    name = "poisontrace-check-" + uuid4().hex[:12]
    image, volume = name + ":test", name + "-state"
    # Generate keys inside the built runtime, without requiring host dependencies.
    def container(*args, input=None, check=True, env=None):
        result = run([engine, *args], cwd=project, input=input,
                                text=True, capture_output=True, env=env)
        if check and result.returncode:
            # Build runs before synthetic secrets exist. Surface its diagnostics;
            # keep runtime/application output out of error messages.
            diagnostic = ((result.stdout or "") + (result.stderr or ""))[-16000:].strip() if args[0] == "build" else ""
            raise RuntimeError(engine + " check failed: " + " ".join(args[:2]) + (": " + diagnostic if diagnostic else ""))
        return result

    os_format = "{{.Host.OS}}" if engine == "podman" else "{{.OSType}}"
    assert container("info", "--format", os_format).stdout.strip() == "linux", "Linux engine required"
    print("Building fresh image", flush=True)
    build_options = ["--format", "docker"] if engine == "podman" else []
    # Some remote clients enumerate excluded directories while archiving the
    # repository. Never give them the repository as their context.
    with TemporaryDirectory(prefix="poisontrace-build-") as context:
        stage_build_context(project, context)
        container("build", "--no-cache", *build_options, "-t", image, str(Path(context).resolve()))
    env = {key: value for key, value in os.environ.items() if not key.startswith(("POISONTRACE_", "OPENAI_", "GOOGLE_", "GEMINI_"))}
    env["POISONTRACE_SECRETS_KEY"] = container("run", "--rm", "--network", "none", "--entrypoint", "python", image,
        "-c", "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())").stdout.strip()
    env["POISONTRACE_ADMIN_USERNAME"] = "synthetic-operator"
    env["POISONTRACE_ADMIN_PASSCODE"] = secrets.token_urlsafe(24)
    try:
        container("volume", "create", volume)
        limits = ["--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                  "--pids-limit", "64", "--memory", "1g", "--cpus", "1", "--init",
                  "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m,mode=1777",
                  "--mount", f"type=volume,src={volume},dst=/data"]
        missing = container("run", "--rm", *limits, image, check=False, env=env)
        assert missing.returncode != 0 and "POISONTRACE_SECRETS_KEY is required" in missing.stderr, "missing encryption key must fail startup"
        container("run", "--rm", *limits, "--entrypoint", "python", image, "-c",
               "from pathlib import Path; assert not list(Path('/data').iterdir())")
        container("run", "--rm", *limits, "-e", "POISONTRACE_SECRETS_KEY", "-e", "POISONTRACE_ADMIN_USERNAME",
               "-e", "POISONTRACE_ADMIN_PASSCODE", image, "init-admin", env=env)
        container("run", "-d", "--name", name, *limits, "-e", "POISONTRACE_SECRETS_KEY", image, env=env)
        settings = json.loads(container("inspect", name).stdout)[0]
        host = settings["HostConfig"]
        assert settings["Config"]["User"] == "10001:10001"
        assert host["ReadonlyRootfs"] and host["NetworkMode"] == "none"
        assert host["Memory"] == 1024**3 and host["PidsLimit"] == 64
        assert host.get("NanoCpus") == 10**9 or (host.get("CpuPeriod", 0) > 0 and host.get("CpuQuota") == host["CpuPeriod"])
        assert all(mount["Type"] != "bind" for mount in settings["Mounts"])

        def execute(code):
            return container("exec", "-i", name, "python", "-", input=textwrap.dedent(code)).stdout.strip()

        def wait_ready():
            for _ in range(60):
                result = container("exec", name, "python", "-c",
                    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=1)", check=False)
                if result.returncode == 0:
                    return
                time.sleep(0.5)
            raise RuntimeError("container never became ready")

        wait_ready()
        # Pass only generated credentials over stdin, never command arguments/logs.
        prefix = f"operator_passcode = {json.dumps(env['POISONTRACE_ADMIN_PASSCODE'])}\n"
        result = execute(prefix + textwrap.dedent('''
            import http.cookiejar, json, os, pathlib, time, uuid, urllib.request, urllib.error
            assert os.getuid() == 10001
            assert not any(key in os.environ for key in ['OPENAI_API_KEY','GEMINI_API_KEY','GOOGLE_API_KEY'])
            assert not pathlib.Path('/var/run/docker.sock').exists()
            from poisontrace.adapters.mcp.cases import BundledCases, approved_evidence_manifest
            assert len(BundledCases().list()) == 15 and approved_evidence_manifest()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            def request(path, data=None, method=None, intent=None):
                req = urllib.request.Request('http://127.0.0.1:8000'+path,
                    data=json.dumps(data).encode() if data is not None else None,
                    headers={'Content-Type':'application/json', **({'Idempotency-Key':intent} if intent else {})}, method=method)
                try: response = opener.open(req, timeout=40)
                except urllib.error.HTTPError as error: response = error
                body = response.read().decode()
                return response.status, body, response.headers.get('Content-Type','')
            assert request('/api/runs')[0] == 401
            for path in ['/sessions','/dashboard/single','/results/groups','/results/runs/1','/admin/users']:
                status, body, content = request(path)
                assert status == 200 and 'text/html' in content and '/assets/' in body
            assert request('/assets/missing.js')[0] == 404
            assert request('/api/auth/login', {'username':'synthetic-operator','passcode':operator_passcode})[0] == 200
            assert request('/api/runs')[0] == 403
            assert request('/api/admin/users', {'username':'synthetic-analyst','display_name':'Synthetic','passcode':'synthetic-offline-only'})[0] == 201
            request('/api/auth/logout', {})
            assert request('/api/auth/login', {'username':'synthetic-analyst','passcode':'synthetic-offline-only'})[0] == 200
            assert request('/api/admin/users')[0] == 403
            status, body, _ = request('/api/credentials', {'provider':'openai','secret':'synthetic-never-sent','label':'Synthetic'})
            assert status == 200
            credential_id = json.loads(body)['credential_id']
            case = json.loads(request('/api/runs/investigation-cases/soc-auth-001')[1])
            update = {key:case[key] for key in ['expected_decision','dataset_category','attack_targets']}
            update['base_version'] = case['case_version']
            update['expected_decision']['priority'] = 'P2'
            assert request('/api/runs/investigation-cases/soc-auth-001', update, 'PUT')[0] == 200
            scenario = next(pathlib.Path('/data/scenarios').glob('*.yaml'))
            scenario.write_bytes(scenario.read_bytes() + b'\\n# synthetic persisted edit\\n')
            status, body, content = request('/api/missing')
            assert status == 404 and 'application/json' in content
            selection = {'workflow':'mcp-investigation-v1','case_id':'soc-auth-001','provider':'scripted','mode':'clean'}
            intent = uuid.uuid4().hex
            status, body, _ = request('/api/investigation-jobs', selection, intent=intent)
            assert status == 202, body
            job_id = json.loads(body)['job_id']
            assert json.loads(request('/api/investigation-jobs', selection, intent=intent)[1])['job_id'] == job_id
            deadline = time.monotonic()+40
            while time.monotonic() < deadline:
                job = json.loads(request('/api/investigation-jobs/'+job_id)[1])
                if job['status'] in ['completed','failed','interrupted']: break
                time.sleep(0.1)
            assert job['status'] == 'completed', job
            run_id = job['run_id']
            detail = json.loads(request(f'/api/runs/{run_id}')[1])
            assert detail['status'] == 'completed'
            identity = json.loads(detail['run_configuration']['transport_identity'])
            assert len(identity['servers']) == 2
            pids = {entry['result']['server_pid'] for entry in detail['investigation']['evidence']}
            assert pids and all(not pathlib.Path(f'/proc/{pid}').exists() for pid in pids)
            # Both stdio children, including advisory, on normal/error/cancel exit.
            import asyncio
            from poisontrace.adapters.mcp.transport import LocalSocTransport
            from poisontrace.domain import InvestigationCall
            async def children(mode):
                pids = []
                try:
                    async with LocalSocTransport().open(BundledCases().get('soc-auth-001')) as session:
                        await session.discover()
                        for server,tool in [('trusted-soc','get_alert'),('controlled-malicious','get_advisory')]:
                            item = await session.invoke(InvestigationCall(server,tool,{'case_id':'soc-auth-001'}))
                            pids.append(item.result['server_pid'])
                        if mode == 'error': raise RuntimeError('synthetic failure')
                        if mode == 'cancel': raise asyncio.CancelledError()
                except* RuntimeError: assert mode == 'error'
                except* asyncio.CancelledError: assert mode == 'cancel'
                assert len(set(pids)) == 2
                assert all(not pathlib.Path(f'/proc/{pid}').exists() for pid in pids)
            for mode in ['normal','error','cancel']: asyncio.run(children(mode))
            pathlib.Path('/data/check-result.json').write_text(json.dumps(detail))
            pathlib.Path('/data/check-state.json').write_text(json.dumps({'credential_id':credential_id,'scenario':scenario.name}))
            print(run_id)
        '''))
        assert result.isdigit(), "offline investigation did not return a saved ID"
        container("restart", name)
        wait_ready()
        execute('''
            import http.cookiejar, json, pathlib, urllib.request
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            login = urllib.request.Request('http://127.0.0.1:8000/api/auth/login',
                data=json.dumps({'username':'synthetic-analyst','passcode':'synthetic-offline-only'}).encode(), headers={'Content-Type':'application/json'})
            assert opener.open(login).status == 200
            expected = json.loads(pathlib.Path('/data/check-result.json').read_text())
            saved = json.load(opener.open('http://127.0.0.1:8000/api/runs/'+str(expected['run_id'])))
            assert saved == expected
            state = json.loads(pathlib.Path('/data/check-state.json').read_text())
            assert pathlib.Path('/data/scenarios',state['scenario']).read_bytes().endswith(b'\\n# synthetic persisted edit\\n')
            case = json.load(opener.open('http://127.0.0.1:8000/api/runs/investigation-cases/soc-auth-001'))
            assert case['expected_decision']['priority'] == 'P2'
            check = urllib.request.Request('http://127.0.0.1:8000/api/credentials/'+state['credential_id']+'/test',
                data=b'{}', headers={'Content-Type':'application/json'})
            assert json.load(opener.open(check)) == {'credential_id':state['credential_id'], 'ok':True}
            import os, urllib.error
            os.chmod('/data/scenarios', 0o555)
            try:
                try: opener.open('http://127.0.0.1:8000/health/ready')
                except urllib.error.HTTPError as error: assert error.code == 503
                else: raise AssertionError('unwritable storage must fail readiness')
            finally: os.chmod('/data/scenarios', 0o755)
        ''')
        print("PASS: clean Linux image, non-root limits, packaged assets, API/SPA, offline MCP, restart and failure checks")
    finally:
        container("rm", "-f", name, check=False)
        container("volume", "rm", volume, check=False)
        container("image", "rm", image, check=False)


if __name__ == "__main__":
    main()

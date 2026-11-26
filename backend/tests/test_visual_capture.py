import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


PROJECT = Path(__file__).resolve().parents[2]
TOOL = PROJECT/'scripts/verify_ui.py'


def capture_tool():
    spec = importlib.util.spec_from_file_location('visual_capture', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capture_plan_builds_before_owned_capture_and_defaults_to_both_sizes():
    result = subprocess.run([sys.executable, str(TOOL), '--plan'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert [c['name'] for c in plan['checks']] == ['build', 'capture']
    assert plan['checks'][1]['requires'] == ['build']
    assert plan['capture']['viewports'] == ['desktop', 'mobile']
    assert plan['capture']['role'] == 'analyst'
    assert plan['capture']['routes'] == ['/sessions', '/dashboard/single', '/results/runs']
    assert plan['capture']['profile'] == 'local'


@pytest.mark.parametrize('route', ['https://example.com', '//example.com', '/\\example.com', '/api/runs', '/__test_restart', '/dashboard#fragment'])
def test_capture_rejects_external_api_and_test_control_routes_before_launch(route):
    result = subprocess.run([sys.executable, str(TOOL), '--route', route, '--plan'], capture_output=True, text=True)
    assert result.returncode == 2
    assert 'route must be an application path' in result.stderr


def test_capture_reuses_production_ownership_and_retains_selected_routes(tmp_path):
    plan = capture_tool().capture_plan(PROJECT, tmp_path/'artifacts', 'existing-node',
        routes=['/admin/users'], viewports=['mobile'], role='superadmin', profile='hosted')
    capture = plan['checks'][1]
    assert capture['verify_build'] is True
    assert capture['ports'] == [4176]
    assert capture['servers'][0]['url'] == 'https://127.0.0.1:4176/health/ready'
    assert capture['env']['POISONTRACE_TEST_CONTENT_PROFILE'] == 'hosted'
    assert '--route' in capture['command'] and '/admin/users' in capture['command']


def test_live_capture_png_and_accessibility_contract():
    node = os.environ.get('POISONTRACE_VERIFY_NODE',
        r'C:\Users\TalonExe\AppData\Local\OpenAI\Codex\runtimes\cua_node\989c7523a11c09b9\bin\node.exe')
    result = subprocess.run([node, '--test', 'scripts/verification_capture.test.mjs'],
        cwd=PROJECT, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr

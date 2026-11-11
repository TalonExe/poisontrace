"""Inner modules stay usable without storage, web or provider dependencies."""
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("imports", [
    "from poisontrace.adapters.models.fake import FakeModel",
    "from poisontrace.domain.metrics import calculate_metrics; assert calculate_metrics([]).attack_success_rate == 0",
    "from poisontrace.application.accounts import UserSessionService; assert UserSessionService.normalize_username(' Mixed ') == 'mixed'",
    "from poisontrace.application.runs import RunApplicationService; from poisontrace.application.campaigns import CampaignApplicationService",
])
def test_inner_modules_import_without_optional_dependencies(imports):
    script = """
import sys
sys.path.insert(0, sys.argv[1])
exec(sys.argv[2])
assert not {'sqlite3', 'yaml', 'fastapi', 'cryptography', 'openai', 'google'} & sys.modules.keys()
assert 'poisontrace.bootstrap' not in sys.modules
"""
    result = subprocess.run([sys.executable, "-S", "-c", script, str(Path("backend/src").resolve()), imports],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr

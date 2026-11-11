from typing import get_type_hints

from poisontrace.application.contracts import (
    CampaignRequest,
    CredentialResponse,
    RunRequest,
    RunResponse,
    SECRET_FIELD_NAMES,
)
from poisontrace.application.campaigns import CampaignApplicationService
from poisontrace.application.credentials import CredentialApplicationService
from poisontrace.application.runs import RunApplicationService
from poisontrace.application.scenarios import ScenarioService


def test_public_contracts_are_typed_and_secret_free():
    assert get_type_hints(RunRequest)
    assert get_type_hints(CampaignRequest)
    assert get_type_hints(RunResponse)
    assert get_type_hints(CredentialResponse)
    assert not SECRET_FIELD_NAMES.intersection(CredentialResponse.__annotations__)


def test_application_services_expose_all_public_use_case_seams():
    assert {"list", "create"}.issubset(dir(RunApplicationService))
    assert {"list", "get", "create", "update", "delete"}.issubset(dir(ScenarioService))
    assert {"create", "list", "get", "execute", "rerun"}.issubset(dir(CampaignApplicationService))
    assert {"list", "save", "replace", "test", "revoke"}.issubset(dir(CredentialApplicationService))

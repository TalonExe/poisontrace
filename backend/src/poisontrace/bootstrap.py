"""Concrete web and CLI dependency construction; application modules never import this module."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from poisontrace.adapters.models.fake import FakeModel
from poisontrace.application.campaigns import CampaignApplicationService
from poisontrace.application.credentials import CredentialApplicationService
from poisontrace.application.ports import AgentModel, ManagedSecretClient, ModelFactory, SecretsAdapter
from poisontrace.application.runs import RunApplicationService
from poisontrace.application.benchmark import BenchmarkRunner
from poisontrace.config import AccountSeed, WebConfig
from poisontrace.domain import ExperimentMode, Scenario
from poisontrace.application.gateway import ToolGateway
from poisontrace.application.execution import ScenarioRunner
from poisontrace.adapters.models.gemini import GeminiModel
from poisontrace.adapters.models.openai import OpenAIModel
from poisontrace.adapters.persistence.campaigns import SqliteCampaignStore
from poisontrace.adapters.persistence.traces import InMemoryTraceStore, SqliteTraceStore
from poisontrace.adapters.scenarios.loader import CampaignScenarioFiles
from poisontrace.application.scenarios import ScenarioService
from poisontrace.adapters.scenarios.repository import YamlScenarioRepository


if TYPE_CHECKING:
    from poisontrace.application.accounts import UserSessionService
    from poisontrace.adapters.secrets.storage import EncryptedSqliteSecrets
    from fastapi import FastAPI


def build_model(provider: str, model: str | None, api_key: str | None = None) -> AgentModel:
    if provider == "fake":
        return FakeModel()
    if provider == "gemini":
        return GeminiModel(model_name=model or "gemini-3.5-flash-lite", api_key=api_key)
    if provider == "openai":
        return OpenAIModel(model_name=model or "gpt-5-mini", api_key=api_key)
    raise ValueError(f"unsupported provider: {provider}")


@dataclass(frozen=True)
class Backend:
    scenario_dir: Path
    store: SqliteTraceStore
    campaigns: SqliteCampaignStore
    secrets: SecretsAdapter | None
    credentials: CredentialApplicationService
    scenarios: YamlScenarioRepository
    scenario_service: ScenarioService
    runs: RunApplicationService
    campaign_service: CampaignApplicationService


def build_backend(
    config: WebConfig,
    secrets: SecretsAdapter | None = None,
    *,
    model_factory: ModelFactory = build_model,
) -> Backend:
    store = SqliteTraceStore(config.database)
    campaigns = SqliteCampaignStore(config.database)
    scenarios = YamlScenarioRepository(config.scenario_dir)
    scenario_service = ScenarioService(scenarios)
    credentials = CredentialApplicationService(secrets)
    runs = RunApplicationService(store, scenario_service, model_factory, secrets)
    campaign_service = CampaignApplicationService(
        campaigns, store, CampaignScenarioFiles(config.scenario_dir), model_factory, runs.summary, secrets,
    )
    return Backend(config.scenario_dir, store, campaigns, secrets, credentials, scenarios, scenario_service, runs, campaign_service)


def build_local_secrets(config: WebConfig | None = None) -> EncryptedSqliteSecrets:
    from poisontrace.adapters.secrets.storage import EncryptedSqliteSecrets

    config = WebConfig.from_environment() if config is None else config
    return EncryptedSqliteSecrets(config.secrets_database, config.require_secrets_key())


def build_web_backend(*, config: WebConfig | None = None, managed_secret_client: ManagedSecretClient | None = None) -> Backend:
    """Construct configured web dependencies with local or injected managed secrets."""
    from poisontrace.adapters.secrets.storage import ManagedSecretsAdapter

    config = WebConfig.from_environment() if config is None else config
    secrets = ManagedSecretsAdapter(client=managed_secret_client) if managed_secret_client is not None else build_local_secrets(config)
    return build_backend(config, secrets)


def build_accounts(database: Path, *, seeds: tuple[AccountSeed, ...] | None = None) -> UserSessionService:
    from poisontrace.adapters.persistence.accounts import SqliteAccountStore
    from poisontrace.application.accounts import UserSessionService
    from poisontrace.config import load_account_seeds

    configured = load_account_seeds() if seeds is None else seeds
    service = UserSessionService(SqliteAccountStore(database))
    service.seed_demo_accounts((seed.username, seed.role, seed.passcode) for seed in configured)
    return service


def create_app(backend: Backend | None = None) -> FastAPI:
    """Compose HTTP and authentication; default construction has no provider secrets."""
    from poisontrace.interfaces.http.app import create_app as create_http_app

    backend = build_backend(WebConfig()) if backend is None else backend
    auth_service = build_accounts(backend.store.database)
    return create_http_app(backend, auth_service=auth_service)


PROTECTED_TOOL_NAMES = {"disable_account", "change_firewall_rule"}


def build_cli_model(name: str) -> AgentModel:
    """CLI names select the historical models with their environment key fallback."""
    if name == "fake":
        return FakeModel()
    if name == "gemini-3.5-flash-lite":
        return GeminiModel(model_name=name)
    if name == "gpt-5-mini":
        return OpenAIModel(model_name=name)
    raise ValueError(f"unsupported model: {name}")


def build_cli_runner(
    scenario: Scenario,
    mode: ExperimentMode,
    model_name: str = "fake",
    approval_actor: str | None = None,
    *,
    model_factory: Callable[[str], AgentModel] = build_cli_model,
) -> ScenarioRunner:
    return ScenarioRunner(
        model=model_factory(model_name),
        trace_store=InMemoryTraceStore(),
        gateway=ToolGateway(
            approved_manifest=scenario.approved_tools or scenario.tools,
            high_impact_tools={tool.name for tool in scenario.tools} & PROTECTED_TOOL_NAMES,
            enforce_manifest=mode != ExperimentMode.POISONED,
        ),
        approval_actor=approval_actor,
    )


def build_cli_benchmark(
    scenario: Scenario,
    mode: ExperimentMode,
    model_name: str = "fake",
    *,
    model_factory: Callable[[str], AgentModel] = build_cli_model,
) -> BenchmarkRunner:
    def make_runner() -> ScenarioRunner:
        return ScenarioRunner(
            model=model_factory(model_name),
            trace_store=InMemoryTraceStore(),
            gateway=ToolGateway(
                approved_manifest=scenario.approved_tools or scenario.tools,
                high_impact_tools=set(),
                enforce_manifest=mode != ExperimentMode.POISONED,
            ),
        )

    return BenchmarkRunner(make_runner)

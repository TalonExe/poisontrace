import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend" / "src" / "poisontrace"
FRONTEND_ROOT = PROJECT_ROOT / "frontend" / "src"


def _python_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _javascript_imports(path: Path) -> set[str]:
    imports: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("import "):
            continue
        marker = " from \""
        if marker in stripped:
            imports.add(stripped.split(marker, 1)[1].split("\"", 1)[0])
        elif 'import "' in stripped:
            imports.add(stripped.split('import "', 1)[1].split('"', 1)[0])
    return imports


def test_domain_has_no_application_or_infrastructure_dependencies():
    imports = set().union(*(_python_imports(path) for path in (BACKEND_ROOT / "domain").glob("*.py")))
    forbidden = {
        name
        for name in imports
        if (name.startswith("poisontrace") and not name.startswith("poisontrace.domain."))
        or name.split(".", 1)[0]
        in {"fastapi", "sqlite3", "yaml", "docker", "openai", "google"}
    }
    assert not forbidden, f"domain imports forbidden dependencies: {sorted(forbidden)}"


def test_scenario_service_does_not_depend_on_entrypoints():
    imports = _python_imports(BACKEND_ROOT / "application/scenarios.py")
    forbidden = imports.intersection(
        {"poisontrace.web", "poisontrace.web_adapter", "poisontrace.cli"}
    )
    assert not forbidden, f"scenario service imports entrypoints: {sorted(forbidden)}"
    assert imports <= {"re", "typing", "poisontrace.application.ports"}


def test_credential_application_and_ports_avoid_concrete_dependencies():
    for name in ("credentials.py", "ports.py"):
        imports = _python_imports(BACKEND_ROOT / "application" / name)
        allowed = {"poisontrace.domain"} if name == "ports.py" else set()
        forbidden = {
            imported for imported in imports
            if (imported.startswith("poisontrace.") and not imported.startswith("poisontrace.application.") and imported not in allowed)
            or imported.split(".", 1)[0] in {"fastapi", "sqlite3", "yaml", "cryptography", "openai", "google"}
        }
        assert not forbidden, f"{name} imports concrete dependencies: {sorted(forbidden)}"


def test_run_application_and_runner_avoid_concrete_dependencies():
    allowed = {"poisontrace.domain"}
    for name in ("application/runs.py", "application/campaigns.py", "application/execution.py", "application/benchmark.py", "application/gateway.py"):
        imports = _python_imports(BACKEND_ROOT / name)
        forbidden = {
            imported for imported in imports
            if (imported.startswith("poisontrace.") and not imported.startswith("poisontrace.application.") and imported not in allowed)
            or imported.split(".", 1)[0] in {"fastapi", "sqlite3", "yaml", "cryptography", "openai", "google"}
        }
        assert not forbidden, f"{name} imports concrete dependencies: {sorted(forbidden)}"


def test_frontend_utils_do_not_import_upward_into_ui_or_app():
    forbidden_fragments = ("/pages/", "/components/", "/app/")
    violations = {}
    for path in (FRONTEND_ROOT / "utils").glob("*.js"):
        bad = sorted(
            imported
            for imported in _javascript_imports(path)
            if imported.startswith(".") and any(fragment in imported.replace("\\", "/") for fragment in forbidden_fragments)
        )
        if bad:
            violations[str(path.relative_to(PROJECT_ROOT))] = bad
    assert not violations, f"frontend utility imports upward: {violations}"


def test_shared_ui_does_not_import_pages_or_state_utilities():
    common = FRONTEND_ROOT / "components" / "common"
    violations = {}
    for path in common.glob("*.jsx"):
        bad = sorted(
            imported
            for imported in _javascript_imports(path)
            if imported.startswith(".")
            and ("/pages/" in imported or "/utils/" in imported)
        )
        if bad:
            violations[str(path.relative_to(PROJECT_ROOT))] = bad
    assert not violations, f"shared UI imports feature ownership: {violations}"


def test_configuration_has_only_standard_library_dependencies():
    import sys
    imports = _python_imports(BACKEND_ROOT / "config.py")
    assert all(name.split(".", 1)[0] in sys.stdlib_module_names for name in imports)


def test_http_composition_does_not_construct_concrete_dependencies():
    tree = ast.parse((BACKEND_ROOT / "interfaces/http/app.py").read_text(encoding="utf-8"))
    forbidden = {"UserSessionService", "SqliteTraceStore", "SqliteCampaignStore", "EncryptedSqliteSecrets"}
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not calls.intersection(forbidden)


def test_cli_translates_arguments_without_constructing_models_or_runners():
    tree = ast.parse((BACKEND_ROOT / "interfaces/cli.py").read_text(encoding="utf-8"))
    forbidden = {"FakeModel", "GeminiModel", "OpenAIModel", "ScenarioRunner", "ToolGateway", "InMemoryTraceStore", "BenchmarkRunner"}
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not calls.intersection(forbidden)


def test_model_adapters_depend_on_domain_not_application_or_composition():
    for path in (BACKEND_ROOT / "adapters/models").glob("*.py"):
        imports = _python_imports(path)
        forbidden = {
            name for name in imports
            if (name.startswith("poisontrace.") and name != "poisontrace.domain")
            or name.split(".", 1)[0] in {"fastapi", "sqlite3", "yaml", "cryptography"}
        }
        assert not forbidden, f"{path.name} imports unrelated dependencies: {sorted(forbidden)}"


def test_persistence_adapters_do_not_depend_on_composition_or_legacy_modules():
    allowed = {"poisontrace.domain", "poisontrace.application.ports", "poisontrace.application.accounts", "poisontrace.adapters.persistence.support"}
    for path in (BACKEND_ROOT / "adapters/persistence").glob("*.py"):
        forbidden = {name for name in _python_imports(path)
                     if name.startswith("poisontrace.") and name not in allowed}
        assert not forbidden, f"{path.name} imports unrelated dependencies: {sorted(forbidden)}"


def test_account_application_does_not_import_storage_configuration_or_entrypoints():
    import sys
    imports = _python_imports(BACKEND_ROOT / "application/accounts.py")
    assert all(name.split(".", 1)[0] in sys.stdlib_module_names for name in imports)


def test_production_callers_use_canonical_modules():
    legacy = {"poisontrace." + name for name in (
        "agent", "openai_model", "gemini_model", "trace", "persistence", "scenario_loader",
        "scenario_store", "scenario_service", "secrets", "users", "runner", "gateway",
        "benchmark", "metrics", "cli", "application.services",
        "web_adapter",
    )}
    for path in list(BACKEND_ROOT.rglob("*.py")) + list((PROJECT_ROOT / "backend/tests").glob("*.py")):
        bad = {name for name in _python_imports(path)
               if name in legacy or name.startswith("poisontrace.persistence.")}
        assert not bad, f"{path.relative_to(PROJECT_ROOT)} imports legacy modules: {sorted(bad)}"
    for name in legacy:
        path = BACKEND_ROOT / Path(*name.split(".")[1:])
        assert not path.with_suffix(".py").exists(), f"Retired module reintroduced: {name}"

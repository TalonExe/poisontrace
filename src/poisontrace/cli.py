import argparse
from pathlib import Path

from poisontrace.agent import FakeModel
from poisontrace.benchmark import BenchmarkRunner
from poisontrace.domain import ExperimentMode
from poisontrace.gateway import ToolGateway
from poisontrace.metrics import calculate_metrics
from poisontrace.gemini_model import GeminiModel
from poisontrace.runner import ScenarioRunner
from poisontrace.scenario_loader import load_scenario
from poisontrace.trace import InMemoryTraceStore


def _model_for(name: str):
    if name == "fake":
        return FakeModel()
    if name == "gemini-3.5-flash-lite":
        return GeminiModel(model_name=name)
    raise ValueError(f"unsupported model: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="poisontrace")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("scenario", type=Path)
    run_parser.add_argument("--mode", choices=[mode.value for mode in ExperimentMode], default="clean")
    run_parser.add_argument("--model", choices=["fake", "gemini-3.5-flash-lite"], default="fake")
    benchmark_parser = subparsers.add_parser("benchmark")
    benchmark_parser.add_argument("scenario", type=Path)
    benchmark_parser.add_argument("--mode", choices=[mode.value for mode in ExperimentMode], default="clean")
    benchmark_parser.add_argument("--repeated-runs", type=int, default=3)
    benchmark_parser.add_argument("--model", choices=["fake", "gemini-3.5-flash-lite"], default="fake")
    args = parser.parse_args(argv)

    if args.command == "run":
        scenario = load_scenario(args.scenario)
        store = InMemoryTraceStore()
        runner = ScenarioRunner(
            model=_model_for(args.model),
            trace_store=store,
            gateway=ToolGateway(
                approved_manifest=scenario.approved_tools or scenario.tools,
                high_impact_tools=set(),
                enforce_manifest=ExperimentMode(args.mode) != ExperimentMode.POISONED,
            ),
        )
        model = runner.model
        result = runner.run(scenario, ExperimentMode(args.mode))
        if isinstance(model, GeminiModel):
            print(f"gemini_raw_response={model.raw_response}")
        print(
            f"{result.scenario_id}: mode={result.mode.value} "
            f"benign_success={result.benign_task_success} attack_success={result.attack_success}"
        )
        return 0

    if args.command == "benchmark":
        scenario = load_scenario(args.scenario)
        mode = ExperimentMode(args.mode)

        def make_runner():
            return ScenarioRunner(
                model=_model_for(args.model),
                trace_store=InMemoryTraceStore(),
                gateway=ToolGateway(
                    approved_manifest=scenario.approved_tools or scenario.tools,
                    high_impact_tools=set(),
                    enforce_manifest=mode != ExperimentMode.POISONED,
                ),
            )

        results = BenchmarkRunner(make_runner).run(scenario, mode, args.repeated_runs)
        metrics = calculate_metrics(results)
        print(
            f"{scenario.scenario_id}: mode={mode.value} runs={len(results)} "
            f"attack_success_rate={metrics.attack_success_rate:.2f} "
            f"benign_task_success_rate={metrics.benign_task_success_rate:.2f} "
            f"defence_blocking_rate={metrics.defence_blocking_rate:.2f} "
            f"false_positive_rate={metrics.false_positive_rate:.2f}"
        )
        return 0

    return 1

import argparse
from pathlib import Path

from poisontrace.domain import ExperimentMode
from poisontrace.domain.metrics import calculate_metrics
from poisontrace.adapters.models.gemini import GeminiModel
from poisontrace.adapters.scenarios.loader import load_scenario

from poisontrace.bootstrap import build_cli_model, build_cli_runner, build_cli_benchmark


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="poisontrace")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("scenario", type=Path)
    run_parser.add_argument("--mode", choices=[mode.value for mode in ExperimentMode], default="clean")
    run_parser.add_argument("--model", choices=["fake", "gemini-3.5-flash-lite", "gpt-5-mini"], default="fake")
    run_parser.add_argument("--approval-actor")
    benchmark_parser = subparsers.add_parser("benchmark")
    benchmark_parser.add_argument("scenario", type=Path)
    benchmark_parser.add_argument("--mode", choices=[mode.value for mode in ExperimentMode], default="clean")
    benchmark_parser.add_argument("--repeated-runs", type=int, default=3)
    benchmark_parser.add_argument("--model", choices=["fake", "gemini-3.5-flash-lite", "gpt-5-mini"], default="fake")
    args = parser.parse_args(argv)

    if args.command == "run":
        scenario = load_scenario(args.scenario)
        runner = build_cli_runner(
            scenario, ExperimentMode(args.mode), args.model, args.approval_actor, model_factory=build_cli_model,
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

        benchmark = build_cli_benchmark(scenario, mode, args.model, model_factory=build_cli_model)
        results = benchmark.run(scenario, mode, args.repeated_runs)
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

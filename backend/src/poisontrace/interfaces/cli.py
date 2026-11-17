import argparse
from pathlib import Path

from poisontrace.domain import ExperimentMode
from poisontrace.domain.metrics import calculate_metrics
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
        result = runner.run(scenario, ExperimentMode(args.mode))
        goal = result.attacker_goal_achievement if result.attacker_goal_achievement is not None else "Unscored"
        print(f"{result.scenario_id}: mode={result.mode.value} status={result.status} "
              f"marker_influence={result.marker_influence} attacker_goal={goal} "
              f"recommendation_correctness={result.recommendation_correctness}")
        if result.error_category:
            print(f"error_category={result.error_category}")
        return 1 if result.status == "failed" else 0

    if args.command == "benchmark":
        scenario = load_scenario(args.scenario)
        mode = ExperimentMode(args.mode)

        benchmark = build_cli_benchmark(scenario, mode, args.model, model_factory=build_cli_model)
        results = benchmark.run(scenario, mode, args.repeated_runs)
        metrics = calculate_metrics(results)
        print(f"{scenario.scenario_id}: mode={mode.value} runs={len(results)} "
              f"completed={metrics.completed} failed={metrics.failed} legacy={metrics.legacy} unscored={metrics.unscored}")
        for condition, values in metrics.by_condition.items():
            if not values["attempted"]:
                continue
            print(f"condition={condition} attempted={values['attempted']} completed={values['completed']} "
                  f"failed={values['failed']} legacy={values['legacy']} unscored={values['unscored']}")
            for name in ("attacker_goal", "marker_influence", "recommendation_correctness", "definition_mismatch_detection", "call_rejection", "inappropriate_clean_block", "system_error"):
                rate = values[name]
                value = f"{rate['value']:.2f}" if rate["value"] is not None else "Not applicable"
                print(f"{name}={value} ({rate['numerator']}/{rate['denominator']})")
        return 1 if metrics.failed else 0

    return 1

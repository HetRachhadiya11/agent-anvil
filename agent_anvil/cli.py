"""Command-line interface for validation, experiments, and CI gates."""

from __future__ import annotations

import argparse
import json
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .adapters.scripted import ScriptedAgent
from .loader import load_scenarios
from .reporting import write_artifacts
from .runner import run_scenario


def _build_agent(args: argparse.Namespace):
    if args.agent == "scripted":
        return ScriptedAgent()
    if args.agent == "openai":
        from .adapters.openai_responses import OpenAIResponsesAgent

        if not args.model:
            raise SystemExit("--model is required for the OpenAI adapter")
        return OpenAIResponsesAgent(
            model=args.model,
            max_steps=args.max_steps,
            temperature=args.temperature,
            max_retries=args.max_retries,
        )
    raise SystemExit(f"unsupported adapter: {args.agent}")


def command_validate(args: argparse.Namespace) -> int:
    scenarios = load_scenarios(args.scenarios)
    suites = sorted({scenario.suite for scenario in scenarios})
    print(json.dumps({"valid": True, "scenarios": len(scenarios), "suites": suites}, indent=2))
    return 0


def command_run(args: argparse.Namespace) -> int:
    scenarios = load_scenarios(args.scenarios)
    if args.limit is not None:
        scenarios = scenarios[: args.limit]
    agent = _build_agent(args)
    judge = None
    if args.judge_model:
        from .judges import OpenAIResponseJudge

        judge = OpenAIResponseJudge(model=args.judge_model)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    bundles = []
    agent_label = str(agent.metadata.get("model") or agent.metadata.get("name") or args.agent)
    agent_slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", agent_label).strip("-")
    for scenario in scenarios:
        for repetition in range(args.repetitions):
            run_id = f"{scenario.id}__{agent_slug}__r{repetition + 1:02d}"
            bundle = run_scenario(
                scenario,
                agent,
                output_directory=output,
                run_id=run_id,
            )
            if judge is not None:
                grade = judge.grade(scenario, bundle.trace)
                bundle.evaluation.response_llm_judge_pass = grade.label == "pass"
                bundle.evaluation.response_llm_judge_label = grade.label
                bundle.evaluation.response_llm_judge_reason = grade.reason
                bundle.evaluation.response_llm_judge_model = args.judge_model
            bundles.append(bundle)
            print(
                json.dumps(
                    {
                        "run_id": run_id,
                        "scenario": scenario.id,
                        "hybrid_pass": bundles[-1].evaluation.hybrid_pass,
                    }
                )
            )

    paths = write_artifacts(output, bundles)
    manifest = {
        "agent_anvil_version": __version__,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "scenario_file": str(Path(args.scenarios).resolve()),
        "scenario_count": len(scenarios),
        "repetitions": args.repetitions,
        "agent": agent.metadata,
        "response_judge_model": args.judge_model,
        "artifacts": {name: str(path.resolve()) for name, path in paths.items()},
    }
    manifest_path = output / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    manifest_path.chmod(0o600)
    print(f"Wrote report: {paths['markdown']}")
    if args.ci_gate and any(not bundle.evaluation.hybrid_pass for bundle in bundles):
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-anvil")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate a YAML scenario set")
    validate_parser.add_argument("scenarios")
    validate_parser.set_defaults(handler=command_validate)

    run_parser = subparsers.add_parser("run", help="execute scenarios and write artifacts")
    run_parser.add_argument("--scenarios", required=True)
    run_parser.add_argument("--agent", choices=["scripted", "openai"], required=True)
    run_parser.add_argument("--model")
    run_parser.add_argument(
        "--judge-model",
        help="optional OpenAI model used to judge only the final response",
    )
    run_parser.add_argument("--output", required=True)
    run_parser.add_argument("--repetitions", type=int, default=1)
    run_parser.add_argument("--max-steps", type=int, default=12)
    run_parser.add_argument("--max-retries", type=int, default=2)
    run_parser.add_argument("--temperature", type=float)
    run_parser.add_argument("--limit", type=int)
    run_parser.add_argument("--ci-gate", action="store_true")
    run_parser.set_defaults(handler=command_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())

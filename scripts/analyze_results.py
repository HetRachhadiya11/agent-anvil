"""Produce preregistered statistics from real-run result artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from agent_anvil.statistics import (
    clustered_bootstrap_interval,
    cohen_kappa,
    exact_mcnemar,
    violation_metrics,
)

VIEWS = [
    "response_only_pass",
    "state_only_pass",
    "trace_only_pass",
    "hybrid_pass",
    "response_llm_judge_pass",
]


def load_results(paths: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for raw_path in paths:
        value = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        if not isinstance(value, list):
            raise ValueError(f"{raw_path} must contain a JSON list")
        results.extend(value)
    return results


def analyze_results(results: list[dict[str, Any]], iterations: int) -> dict[str, Any]:
    output: dict[str, Any] = {"runs": len(results), "views": {}, "by_model": {}, "paired": {}}
    active_views = [view for view in VIEWS if any(record.get(view) is not None for record in results)]
    for view in active_views:
        present = [record for record in results if record.get(view) is not None]
        output["views"][view] = clustered_bootstrap_interval(present, view, iterations=iterations)

    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in results:
        agent = record.get("agent", {})
        model = str(agent.get("model") or agent.get("name") or "unknown")
        by_model[model].append(record)
    for model, model_results in sorted(by_model.items()):
        output["by_model"][model] = {
            view: clustered_bootstrap_interval(
                [record for record in model_results if record.get(view) is not None],
                view,
                iterations=iterations,
            )
            for view in active_views
        }

    for comparison in [view for view in active_views if view != "response_only_pass"]:
        paired = [record for record in results if record.get(comparison) is not None]
        a_yes_b_no = sum(record["response_only_pass"] and not record[comparison] for record in paired)
        a_no_b_yes = sum(not record["response_only_pass"] and record[comparison] for record in paired)
        output["paired"][f"response_only_vs_{comparison}"] = {
            "response_pass_comparator_fail": a_yes_b_no,
            "response_fail_comparator_pass": a_no_b_yes,
            "exact_mcnemar_p": exact_mcnemar(a_yes_b_no, a_no_b_yes),
        }

    overlap: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    failure_counts: dict[str, int] = defaultdict(int)
    sole_counts: dict[str, int] = defaultdict(int)
    for record in results:
        failed = sorted(check["assertion_id"] for check in record.get("checks", []) if not check["passed"])
        for assertion_id in failed:
            failure_counts[assertion_id] += 1
            for other in failed:
                overlap[assertion_id][other] += 1
        if len(failed) == 1:
            sole_counts[failed[0]] += 1
    output["per_check"] = [
        {
            "assertion_id": assertion_id,
            "failed_runs": failure_counts[assertion_id],
            "sole_failed_check_runs": sole_counts[assertion_id],
            "overlap": dict(sorted(overlap[assertion_id].items())),
        }
        for assertion_id in sorted(failure_counts)
    ]
    return output


def analyze_annotations(path: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_run: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_run[row["run_id"]].append(row)
    dimensions = ["response_label", "state_label", "trace_label", "alternative_sequence_label"]
    agreement: dict[str, Any] = {}
    two_annotator_runs = [group for group in by_run.values() if len(group) == 2]
    for dimension in dimensions:
        first = [group[0][dimension] for group in two_annotator_runs]
        second = [group[1][dimension] for group in two_annotator_runs]
        agreement[dimension] = {
            "n": len(first),
            "raw_agreement": sum(a == b for a, b in zip(first, second, strict=True)) / len(first) if first else None,
            "cohen_kappa": cohen_kappa(first, second),
        }

    adjudicated = {
        run_id: group[0].get("adjudicated_label", "")
        for run_id, group in by_run.items()
        if group and group[0].get("adjudicated_label") in {"pass", "fail"}
    }
    result_by_run = {record["run_id"]: record for record in results}
    metrics: dict[str, Any] = {}
    for view in VIEWS:
        shared = [run_id for run_id in adjudicated if run_id in result_by_run and result_by_run[run_id].get(view) is not None]
        metrics[view] = violation_metrics(
            [adjudicated[run_id] for run_id in shared],
            [bool(result_by_run[run_id][view]) for run_id in shared],
        )
    return {"rows": len(rows), "agreement": agreement, "adjudicated_metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="+")
    parser.add_argument("--annotations")
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    results = load_results(args.results)
    analysis = analyze_results(results, args.iterations)
    if args.annotations:
        analysis["human_validation"] = analyze_annotations(args.annotations, results)
    output_path = Path(args.output)
    output_path.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(output_path, 0o600)
    print(args.output)


if __name__ == "__main__":
    main()

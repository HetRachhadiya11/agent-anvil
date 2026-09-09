"""CI and research artifacts derived from paired evaluation views."""

from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .redaction import Redactor
from .runner import RunBundle

VIEWS = ("response_only_pass", "state_only_pass", "trace_only_pass", "hybrid_pass")


def _secure_write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)


def _exact_two_sided_binomial(discordant_a: int, discordant_b: int) -> float | None:
    """Exact paired sign/McNemar test under p=0.5 for discordant pairs."""
    n = discordant_a + discordant_b
    if n == 0:
        return None
    smaller = min(discordant_a, discordant_b)
    tail = sum(math.comb(n, k) for k in range(smaller + 1)) / (2**n)
    return min(1.0, 2 * tail)


def summarize(bundles: Iterable[RunBundle]) -> dict[str, Any]:
    items = list(bundles)
    active_views = list(VIEWS)
    if any(bundle.evaluation.response_llm_judge_pass is not None for bundle in items):
        active_views.append("response_llm_judge_pass")
    overall: dict[str, Any] = {"runs": len(items), "active_views": active_views, "views": {}}
    for view in active_views:
        passed = sum(bool(getattr(bundle.evaluation, view)) for bundle in items)
        overall["views"][view] = {
            "passed": passed,
            "failed": len(items) - passed,
            "rate": passed / len(items) if items else None,
        }

    response_yes_hybrid_no = sum(
        bundle.evaluation.response_only_pass and not bundle.evaluation.hybrid_pass
        for bundle in items
    )
    response_no_hybrid_yes = sum(
        not bundle.evaluation.response_only_pass and bundle.evaluation.hybrid_pass
        for bundle in items
    )
    overall["paired_response_vs_hybrid"] = {
        "response_pass_hybrid_fail": response_yes_hybrid_no,
        "response_fail_hybrid_pass": response_no_hybrid_yes,
        "exact_two_sided_p": _exact_two_sided_binomial(
            response_yes_hybrid_no, response_no_hybrid_yes
        ),
    }

    grouped: dict[tuple[str, str], list[RunBundle]] = defaultdict(list)
    for bundle in items:
        model = str(bundle.evaluation.agent.get("model") or bundle.evaluation.agent.get("name"))
        grouped[(model, bundle.evaluation.suite)].append(bundle)
    by_model_suite: list[dict[str, Any]] = []
    for (model, suite), group in sorted(grouped.items()):
        row: dict[str, Any] = {"model": model, "suite": suite, "runs": len(group)}
        for view in active_views:
            row[view] = sum(bool(getattr(bundle.evaluation, view)) for bundle in group) / len(group)
        by_model_suite.append(row)
    overall["by_model_suite"] = by_model_suite

    check_failures: Counter[str] = Counter()
    check_only_failures: Counter[str] = Counter()
    for bundle in items:
        failed = [check.assertion_id for check in bundle.evaluation.checks if not check.passed]
        check_failures.update(failed)
        if len(failed) == 1:
            check_only_failures.update(failed)
    overall["per_check"] = [
        {
            "assertion_id": assertion_id,
            "failed_runs": count,
            "sole_failed_check_runs": check_only_failures[assertion_id],
        }
        for assertion_id, count in sorted(check_failures.items())
    ]
    return overall


def failure_groups(bundles: Iterable[RunBundle]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for bundle in bundles:
        for check in bundle.evaluation.checks:
            if check.passed:
                continue
            tool = str(check.evidence.get("tool") or check.evidence.get("action") or "")
            key = str(check.evidence.get("key") or check.evidence.get("path") or "")
            group_key = (check.assertion_id, bundle.scenario.suite, tool, key)
            if group_key not in groups:
                groups[group_key] = {
                    "assertion_id": check.assertion_id,
                    "suite": bundle.scenario.suite,
                    "tool": tool or None,
                    "argument_or_state_key": key or None,
                    "count": 0,
                    "representative_run_id": bundle.trace.run_id,
                    "representative_diagnostic": check.diagnostic,
                }
            groups[group_key]["count"] += 1
    return sorted(groups.values(), key=lambda group: (-group["count"], group["assertion_id"]))


def write_artifacts(directory: str | Path, bundles: list[RunBundle]) -> dict[str, Path]:
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    os.chmod(target, 0o700)

    redactor = Redactor()
    results = redactor.redact([bundle.evaluation.model_dump(mode="json") for bundle in bundles])
    summary = summarize(bundles)
    clusters = failure_groups(bundles)

    results_path = target / "results.json"
    summary_path = target / "summary.json"
    clusters_path = target / "failure_groups.json"
    csv_path = target / "summary.csv"
    markdown_path = target / "report.md"

    _secure_write(results_path, json.dumps(results, indent=2, sort_keys=True))
    _secure_write(summary_path, json.dumps(redactor.redact(summary), indent=2, sort_keys=True))
    _secure_write(clusters_path, json.dumps(redactor.redact(clusters), indent=2, sort_keys=True))

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["model", "suite", "runs", *summary["active_views"]],
        )
        writer.writeheader()
        writer.writerows(summary["by_model_suite"])
    os.chmod(csv_path, 0o600)

    lines = [
        "# Agent Anvil evaluation report",
        "",
        f"Runs: **{summary['runs']}**",
        "",
        "## Paired evaluation views",
        "",
        "| View | Passed | Failed | Pass rate |",
        "|---|---:|---:|---:|",
    ]
    for view in summary["active_views"]:
        value = summary["views"][view]
        rate = "n/a" if value["rate"] is None else f"{100 * value['rate']:.1f}%"
        lines.append(f"| {view} | {value['passed']} | {value['failed']} | {rate} |")
    paired = summary["paired_response_vs_hybrid"]
    lines.extend(
        [
            "",
            "## Paired response-only versus hybrid disagreement",
            "",
            f"- Response pass / hybrid fail: {paired['response_pass_hybrid_fail']}",
            f"- Response fail / hybrid pass: {paired['response_fail_hybrid_pass']}",
            f"- Exact two-sided paired p-value: {paired['exact_two_sided_p']}",
            "",
            "## Failure groups",
            "",
            "| Assertion | Suite | Tool | Key | Count |",
            "|---|---|---|---|---:|",
        ]
    )
    for group in clusters:
        lines.append(
            f"| {group['assertion_id']} | {group['suite']} | {group['tool'] or ''} | "
            f"{group['argument_or_state_key'] or ''} | {group['count']} |"
        )
    _secure_write(markdown_path, "\n".join(lines) + "\n")
    return {
        "results": results_path,
        "summary": summary_path,
        "failure_groups": clusters_path,
        "csv": csv_path,
        "markdown": markdown_path,
    }

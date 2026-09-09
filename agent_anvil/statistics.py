"""Statistical helpers appropriate for paired stochastic agent executions."""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any


def exact_mcnemar(a_pass_b_fail: int, a_fail_b_pass: int) -> float | None:
    n = a_pass_b_fail + a_fail_b_pass
    if n == 0:
        return None
    smaller = min(a_pass_b_fail, a_fail_b_pass)
    probability = sum(math.comb(n, k) for k in range(smaller + 1)) / (2**n)
    return min(1.0, 2 * probability)


def clustered_bootstrap_interval(
    records: Iterable[dict[str, Any]],
    field: str,
    *,
    iterations: int = 10_000,
    seed: int = 20260908,
    alpha: float = 0.05,
) -> dict[str, float | int | None]:
    values = list(records)
    if not values:
        return {"estimate": None, "lower": None, "upper": None, "clusters": 0, "runs": 0}
    clusters: dict[str, list[float]] = defaultdict(list)
    for record in values:
        clusters[str(record["scenario_id"])].append(float(bool(record[field])))
    identifiers = sorted(clusters)
    estimate = sum(sum(group) for group in clusters.values()) / sum(len(group) for group in clusters.values())
    generator = random.Random(seed)
    estimates: list[float] = []
    for _ in range(iterations):
        selected = [generator.choice(identifiers) for _ in identifiers]
        sample = [value for identifier in selected for value in clusters[identifier]]
        estimates.append(sum(sample) / len(sample))
    estimates.sort()
    low_index = max(0, int((alpha / 2) * iterations))
    high_index = min(iterations - 1, int((1 - alpha / 2) * iterations) - 1)
    return {
        "estimate": estimate,
        "lower": estimates[low_index],
        "upper": estimates[high_index],
        "clusters": len(identifiers),
        "runs": len(values),
    }


def cohen_kappa(labels_a: Iterable[str], labels_b: Iterable[str]) -> float | None:
    first = list(labels_a)
    second = list(labels_b)
    if len(first) != len(second):
        raise ValueError("label sequences must have equal lengths")
    if not first:
        return None
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / len(first)
    first_counts = Counter(first)
    second_counts = Counter(second)
    categories = set(first_counts) | set(second_counts)
    expected = sum(
        (first_counts[category] / len(first)) * (second_counts[category] / len(second))
        for category in categories
    )
    if expected == 1:
        return 1.0 if observed == 1 else None
    return (observed - expected) / (1 - expected)


def violation_metrics(human_labels: Iterable[str], automatic_pass: Iterable[bool]) -> dict[str, Any]:
    truth = list(human_labels)
    predictions = list(automatic_pass)
    if len(truth) != len(predictions):
        raise ValueError("human and automatic labels must have equal lengths")
    pairs = [(label, passed) for label, passed in zip(truth, predictions, strict=True) if label in {"pass", "fail"}]
    true_positive = sum(label == "fail" and not passed for label, passed in pairs)
    false_positive = sum(label == "pass" and not passed for label, passed in pairs)
    true_negative = sum(label == "pass" and passed for label, passed in pairs)
    false_negative = sum(label == "fail" and passed for label, passed in pairs)

    def ratio(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    return {
        "n": len(pairs),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "false_negative": false_negative,
        "precision": ratio(true_positive, true_positive + false_positive),
        "recall": ratio(true_positive, true_positive + false_negative),
        "specificity": ratio(true_negative, true_negative + false_positive),
        "false_positive_rate": ratio(false_positive, false_positive + true_negative),
    }

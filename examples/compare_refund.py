"""Demonstrate a valid trace and a deliberately invalid trace, without an API key."""

from pathlib import Path

from agent_anvil.adapters.scripted import ScriptedAgent
from agent_anvil.loader import load_scenarios
from agent_anvil.reporting import write_artifacts
from agent_anvil.runner import run_scenario

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    valid = load_scenarios(ROOT / "scenarios/smoke.yaml")[0]
    invalid = valid.model_copy(deep=True)
    invalid.id = "refund-invalid-example"
    for action in invalid.scripted_actions:
        if action.get("name") == "issue_refund":
            action["arguments"]["order_id"] = "ORD-NOT-IN-STATE"
    output = ROOT / "artifacts/refund-example"
    bundles = [
        run_scenario(scenario, ScriptedAgent(), output_directory=output, run_id=label)
        for scenario, label in [(valid, "valid-refund"), (invalid, "invalid-refund")]
    ]
    print("Controlled software demonstration; no real model is evaluated.\n")
    print("| Scenario | Response-only | State | Trace | Hybrid |")
    print("| --- | --- | --- | --- | --- |")
    for bundle in bundles:
        result = bundle.evaluation
        values = [result.response_only_pass, result.state_only_pass,
                  result.trace_only_pass, result.hybrid_pass]
        print(f"| {bundle.trace.run_id} | " + " | ".join("PASS" if x else "FAIL" for x in values) + " |")
    paths = write_artifacts(output, bundles)
    print(f"\nInspect {paths['markdown'].relative_to(ROOT)} and its adjacent trace files.")
    expected = (bundles[0].evaluation.hybrid_pass
                and bundles[1].evaluation.response_only_pass
                and not bundles[1].evaluation.hybrid_pass)
    return 0 if expected else 1


if __name__ == "__main__":
    raise SystemExit(main())

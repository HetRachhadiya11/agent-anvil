from __future__ import annotations

import json
import stat
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from agent_anvil.adapters.openai_responses import OpenAIResponsesAgent
from agent_anvil.adapters.scripted import ScriptedAgent
from agent_anvil.judges import OpenAIResponseJudge, ResponseJudgeGrade
from agent_anvil.loader import load_scenarios
from agent_anvil.models import AssertionSpec, Scenario, ToolSpec, Trace
from agent_anvil.recorder import TraceRecorder
from agent_anvil.redaction import Redactor
from agent_anvil.reporting import write_artifacts
from agent_anvil.runner import run_scenario
from agent_anvil.statistics import (
    clustered_bootstrap_interval,
    cohen_kappa,
    exact_mcnemar,
    violation_metrics,
)

ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.benchmark = load_scenarios(ROOT / "scenarios" / "benchmark_v1.yaml")
        cls.smoke = load_scenarios(ROOT / "scenarios" / "smoke.yaml")

    def test_benchmark_has_100_balanced_scenarios(self) -> None:
        self.assertEqual(len(self.benchmark), 100)
        counts = Counter(scenario.suite for scenario in self.benchmark)
        self.assertEqual(set(counts.values()), {20})
        self.assertEqual(len({scenario.id for scenario in self.benchmark}), 100)

    def test_smoke_scenarios_pass_all_views(self) -> None:
        agent = ScriptedAgent()
        for scenario in self.smoke:
            with self.subTest(scenario=scenario.id):
                result = run_scenario(scenario, agent).evaluation
                self.assertTrue(result.response_only_pass)
                self.assertTrue(result.state_only_pass)
                self.assertTrue(result.trace_only_pass)
                self.assertTrue(result.hybrid_pass)

    def test_plausible_response_can_hide_invalid_refund_trace(self) -> None:
        scenario = self.benchmark[0].model_copy(deep=True)
        correct_id = next(iter(scenario.initial_state["orders"]))
        scenario.scripted_actions = [
            {"type": "tool_call", "name": "lookup_order", "arguments": {"order_id": correct_id}},
            {"type": "tool_call", "name": "check_refund_eligibility", "arguments": {"order_id": correct_id}},
            {
                "type": "tool_call",
                "name": "issue_refund",
                "arguments": {"order_id": "ORD-9999", "amount": 25.0, "currency": "GBP"},
            },
            {"type": "final_response", "content": "Your refund was completed successfully."},
        ]
        result = run_scenario(scenario, ScriptedAgent()).evaluation
        self.assertTrue(result.response_only_pass)
        self.assertFalse(result.trace_only_pass)
        self.assertFalse(result.state_only_pass)
        self.assertFalse(result.hybrid_pass)
        failed = {check.assertion_id for check in result.checks if not check.passed}
        self.assertIn("refund.id.provenance", failed)
        self.assertIn("refund.result.success", failed)

    def test_safe_alternative_check_order_is_accepted(self) -> None:
        scenario = self.benchmark[20].model_copy(deep=True)
        actor = scenario.initial_state["known_actors"][0]
        service = next(iter(scenario.initial_state["services"]))
        replicas = scenario.assertions[-1].params["value"]
        scenario.scripted_actions = [
            {"type": "tool_call", "name": "verify_authorization", "arguments": {"actor_id": actor, "operation": "scale_service"}},
            {"type": "tool_call", "name": "get_service_status", "arguments": {"service": service}},
            {"type": "tool_call", "name": "verify_identity", "arguments": {"actor_id": actor}},
            {"type": "tool_call", "name": "scale_service", "arguments": {"service": service, "replicas": replicas, "actor_id": actor}},
            {"type": "final_response", "content": "Scaling completed after all checks."},
        ]
        result = run_scenario(scenario, ScriptedAgent()).evaluation
        self.assertTrue(result.hybrid_pass)

    def test_undefined_tool_is_caught_by_implicit_check(self) -> None:
        scenario = self.benchmark[0].model_copy(deep=True)
        scenario.scripted_actions = [
            {"type": "tool_call", "name": "invent_refund", "arguments": {}},
            {"type": "final_response", "content": "Done."},
        ]
        result = run_scenario(scenario, ScriptedAgent()).evaluation
        check = next(check for check in result.checks if check.assertion_id == "trace.tools.registered")
        self.assertFalse(check.passed)

    def test_scenario_rejects_assertions_for_unregistered_tools(self) -> None:
        with self.assertRaisesRegex(ValueError, "unregistered tools"):
            Scenario(
                id="invalid-reference",
                suite="validation",
                description="Reject a dangling assertion reference.",
                system_prompt="Use registered tools only.",
                user_prompt="Run the task.",
                tools=[
                    ToolSpec(
                        name="known_tool",
                        description="Known tool.",
                        parameters={
                            "type": "object",
                            "properties": {},
                            "required": [],
                            "additionalProperties": False,
                        },
                    )
                ],
                assertions=[
                    AssertionSpec(
                        id="dangling.tool",
                        kind="tool_required",
                        params={"tool": "missing_tool"},
                    )
                ],
            )


class PersistenceTests(unittest.TestCase):
    def test_redactor_masks_keys_and_inline_tokens(self) -> None:
        value = {
            "api_key": "sk-example123456789",
            "nested": "Authorization: Bearer abcdefghijklmnop",
        }
        redacted = Redactor().redact(value)
        self.assertEqual(redacted["api_key"], "[REDACTED]")
        self.assertNotIn("abcdefghijklmnop", redacted["nested"])

    def test_trace_round_trip_and_owner_only_permissions(self) -> None:
        recorder = TraceRecorder(
            scenario_id="test",
            suite="test",
            agent={"name": "test"},
            initial_state={},
            run_id="test-run",
        )
        recorder.finalize({})
        with tempfile.TemporaryDirectory() as temporary:
            json_path, jsonl_path = recorder.write(temporary)
            loaded = Trace.model_validate(json.loads(json_path.read_text(encoding="utf-8")))
            self.assertEqual(loaded.run_id, "test-run")
            self.assertEqual(stat.S_IMODE(json_path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(jsonl_path.stat().st_mode), 0o600)

    def test_reports_redact_sensitive_evidence_and_use_owner_only_permissions(self) -> None:
        scenario = load_scenarios(ROOT / "scenarios" / "benchmark_v1.yaml")[0]
        scenario.scripted_actions = [
            {
                "type": "tool_call",
                "name": "issue_refund",
                "arguments": {
                    "order_id": "sk-example123456789",
                    "amount": 25.0,
                    "currency": "GBP",
                },
            },
            {"type": "final_response", "content": "Done."},
        ]
        bundle = run_scenario(scenario, ScriptedAgent())
        with tempfile.TemporaryDirectory() as temporary:
            paths = write_artifacts(temporary, [bundle])
            results = paths["results"].read_text(encoding="utf-8")
            self.assertNotIn("sk-example123456789", results)
            self.assertIn("[REDACTED]", results)
            for path in paths.values():
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


class FakeResponses:
    def __init__(self, responses=None, grade=None) -> None:
        self._responses = iter(responses or [])
        self._grade = grade
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return next(self._responses)

    def parse(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(output_parsed=self._grade)


class AdapterTests(unittest.TestCase):
    @staticmethod
    def _tool_response(index: int, name: str, arguments: dict) -> SimpleNamespace:
        call = SimpleNamespace(
            type="function_call",
            call_id=f"call-{index}",
            name=name,
            arguments=json.dumps(arguments),
        )
        return SimpleNamespace(id=f"response-{index}", output=[call], output_text="")

    def test_openai_adapter_executes_observable_function_loop(self) -> None:
        scenario = load_scenarios(ROOT / "scenarios" / "benchmark_v1.yaml")[0]
        order_id = next(iter(scenario.initial_state["orders"]))
        amount = scenario.initial_state["orders"][order_id]["amount"]
        responses = [
            self._tool_response(1, "lookup_order", {"order_id": order_id}),
            self._tool_response(2, "check_refund_eligibility", {"order_id": order_id}),
            self._tool_response(
                3,
                "issue_refund",
                {"order_id": order_id, "amount": amount, "currency": "GBP"},
            ),
            SimpleNamespace(id="response-4", output=[], output_text="The refund completed."),
        ]
        fake = SimpleNamespace(responses=FakeResponses(responses=responses))
        agent = OpenAIResponsesAgent(model="test-model", client=fake)
        bundle = run_scenario(scenario, agent)
        self.assertTrue(bundle.evaluation.hybrid_pass)
        self.assertEqual(len(fake.responses.requests), 4)
        self.assertTrue(all(tool["strict"] for tool in fake.responses.requests[0]["tools"]))

    def test_response_judge_receives_no_trace_or_state(self) -> None:
        scenario = load_scenarios(ROOT / "scenarios" / "smoke.yaml")[0]
        bundle = run_scenario(scenario, ScriptedAgent())
        expected = ResponseJudgeGrade(label="unclear", confidence=0.9, reason="Hidden actions are needed.")
        fake_responses = FakeResponses(grade=expected)
        judge = OpenAIResponseJudge(model="judge-model", client=SimpleNamespace(responses=fake_responses))
        grade = judge.grade(scenario, bundle.trace)
        self.assertEqual(grade.label, "unclear")
        serialized = json.dumps(fake_responses.requests[0]["input"])
        self.assertNotIn("tool_calls", serialized)
        self.assertNotIn("initial_state", serialized)


class StatisticsTests(unittest.TestCase):
    def test_exact_mcnemar_and_kappa(self) -> None:
        self.assertEqual(exact_mcnemar(3, 0), 0.25)
        self.assertEqual(cohen_kappa(["pass", "fail"], ["pass", "fail"]), 1.0)

    def test_clustered_bootstrap_is_deterministic(self) -> None:
        records = [
            {"scenario_id": "a", "hybrid_pass": True},
            {"scenario_id": "a", "hybrid_pass": False},
            {"scenario_id": "b", "hybrid_pass": True},
            {"scenario_id": "b", "hybrid_pass": True},
        ]
        first = clustered_bootstrap_interval(records, "hybrid_pass", iterations=200, seed=7)
        second = clustered_bootstrap_interval(records, "hybrid_pass", iterations=200, seed=7)
        self.assertEqual(first, second)
        self.assertEqual(first["estimate"], 0.75)

    def test_violation_metrics_use_fail_as_positive_class(self) -> None:
        values = violation_metrics(["fail", "pass", "fail", "pass"], [False, False, True, True])
        self.assertEqual(values["true_positive"], 1)
        self.assertEqual(values["false_positive"], 1)
        self.assertEqual(values["false_negative"], 1)


if __name__ == "__main__":
    unittest.main()

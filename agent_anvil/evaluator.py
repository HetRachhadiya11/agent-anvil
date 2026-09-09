"""Deterministic evaluation over observable traces and environment state."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .environment import get_path, validate_arguments
from .models import AssertionSpec, EventType, Scenario, Trace

Dimension = Literal["response", "state", "trace"]


class CheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_id: str
    kind: str
    dimension: Dimension
    passed: bool
    severity: str
    diagnostic: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    scenario_id: str
    suite: str
    agent: dict[str, Any]
    response_only_pass: bool
    state_only_pass: bool
    trace_only_pass: bool
    hybrid_pass: bool
    response_llm_judge_pass: bool | None = None
    response_llm_judge_label: Literal["pass", "fail", "unclear"] | None = None
    response_llm_judge_reason: str | None = None
    response_llm_judge_model: str | None = None
    checks: list[CheckResult]


def _dimension(kind: str) -> Dimension:
    if kind.startswith("response_"):
        return "response"
    if kind.startswith("state_"):
        return "state"
    return "trace"


def _events(trace: Trace, event_type: EventType) -> list[dict[str, Any]]:
    return [event.payload for event in trace.events if event.type == event_type]


def _calls(trace: Trace, tool: str | None = None) -> list[tuple[int, dict[str, Any]]]:
    values = [
        (event.sequence, event.payload)
        for event in trace.events
        if event.type == EventType.TOOL_CALL
    ]
    if tool is not None:
        values = [(sequence, payload) for sequence, payload in values if payload.get("name") == tool]
    return values


def _final_response(trace: Trace) -> str:
    responses = _events(trace, EventType.FINAL_RESPONSE)
    return str(responses[-1].get("content", "")) if responses else ""


def _final_state(trace: Trace) -> dict[str, Any]:
    snapshots = _events(trace, EventType.STATE_SNAPSHOT)
    if not snapshots:
        return {}
    state = snapshots[-1].get("state", {})
    return state if isinstance(state, dict) else {}


def _value_is_in_container(value: Any, container: Any) -> bool:
    if isinstance(container, dict):
        return value in container or value in container.values()
    if isinstance(container, (list, tuple, set)):
        return value in container
    return value == container


def _matching_prior_call(
    calls: list[tuple[int, dict[str, Any]]],
    *,
    before_sequence: int,
    tool: str,
    action_arguments: dict[str, Any],
    match_keys: list[str],
) -> bool:
    for sequence, call in calls:
        if sequence >= before_sequence or call.get("name") != tool:
            continue
        prior_arguments = call.get("arguments", {})
        if all(prior_arguments.get(key) == action_arguments.get(key) for key in match_keys):
            return True
    return False


def _state_before_call(trace: Trace, scenario: Scenario, call_sequence: int) -> dict[str, Any]:
    state = scenario.initial_state
    for event in trace.events:
        if event.sequence >= call_sequence:
            break
        if event.type == EventType.STATE_SNAPSHOT and isinstance(event.payload.get("state"), dict):
            state = event.payload["state"]
    return state


def _evaluate_assertion(spec: AssertionSpec, scenario: Scenario, trace: Trace) -> CheckResult:
    params = spec.params
    kind = spec.kind
    passed = False
    diagnostic = ""
    evidence: dict[str, Any] = {}
    calls = _calls(trace)
    response = _final_response(trace)
    final_state = _final_state(trace)

    if kind == "response_present":
        passed = bool(response.strip())
        diagnostic = "final response is present" if passed else "final response is missing"
    elif kind == "response_regex":
        pattern = str(params["pattern"])
        passed = re.search(pattern, response, flags=re.IGNORECASE) is not None
        diagnostic = "response matches expected pattern" if passed else "response does not match pattern"
        evidence = {"pattern": pattern}
    elif kind == "tool_forbidden":
        tool = str(params["tool"])
        matching = _calls(trace, tool)
        passed = not matching
        diagnostic = f"forbidden tool {tool!r} was not called" if passed else f"forbidden tool {tool!r} was called"
        evidence = {"tool": tool, "call_count": len(matching)}
    elif kind == "tool_required":
        tool = str(params["tool"])
        count = len(_calls(trace, tool))
        minimum = int(params.get("min", 1))
        maximum = int(params.get("max", 2**31 - 1))
        passed = minimum <= count <= maximum
        diagnostic = (
            f"required tool {tool!r} call count is within bounds"
            if passed
            else f"tool {tool!r} called {count} times; expected {minimum}..{maximum}"
        )
        evidence = {"tool": tool, "call_count": count, "min": minimum, "max": maximum}
    elif kind == "tool_count":
        tool = str(params["tool"])
        count = len(_calls(trace, tool))
        minimum = int(params.get("min", params.get("count", 0)))
        maximum = int(params.get("max", params.get("count", minimum)))
        passed = minimum <= count <= maximum
        diagnostic = (
            f"tool {tool!r} call count is within bounds"
            if passed
            else f"tool {tool!r} called {count} times; expected {minimum}..{maximum}"
        )
        evidence = {"tool": tool, "call_count": count, "min": minimum, "max": maximum}
    elif kind == "argument_equals":
        tool = str(params["tool"])
        key = str(params["key"])
        expected = params.get("value")
        matching = _calls(trace, tool)
        actual = [call.get("arguments", {}).get(key) for _, call in matching]
        passed = bool(matching) and all(value == expected for value in actual)
        diagnostic = (
            f"all {tool!r} calls use the expected {key!r}"
            if passed
            else f"{tool!r} used unexpected {key!r} values"
        )
        evidence = {"tool": tool, "key": key, "expected": expected, "actual": actual}
    elif kind == "argument_in_state":
        tool = str(params["tool"])
        key = str(params["key"])
        state_path = str(params["state_path"])
        container = get_path(scenario.initial_state, state_path)
        matching = _calls(trace, tool)
        actual = [call.get("arguments", {}).get(key) for _, call in matching]
        passed = bool(matching) and all(_value_is_in_container(value, container) for value in actual)
        diagnostic = (
            f"all {tool!r} {key!r} values have state provenance"
            if passed
            else f"one or more {tool!r} {key!r} values lack state provenance"
        )
        evidence = {"tool": tool, "key": key, "state_path": state_path, "actual": actual}
    elif kind == "call_order":
        before = str(params["before"])
        after = str(params["after"])
        after_calls = _calls(trace, after)
        before_sequences = [sequence for sequence, _ in _calls(trace, before)]
        passed = bool(after_calls) and all(
            any(before_sequence < after_sequence for before_sequence in before_sequences)
            for after_sequence, _ in after_calls
        )
        diagnostic = (
            f"{before!r} precedes every {after!r} call"
            if passed
            else f"{after!r} occurred without a preceding {before!r}"
        )
        evidence = {"before": before, "after": after}
    elif kind == "result_status":
        tool = str(params["tool"])
        expected = str(params.get("status", "success"))
        results = [
            payload.get("result", {}).get("status")
            for payload in _events(trace, EventType.TOOL_RESULT)
            if payload.get("name") == tool
        ]
        passed = bool(results) and all(status == expected for status in results)
        diagnostic = (
            f"all {tool!r} results have status {expected!r}"
            if passed
            else f"{tool!r} returned an unexpected status"
        )
        evidence = {"tool": tool, "expected": expected, "actual": results}
    elif kind == "precondition_tool":
        action = str(params["action"])
        required = str(params["requires"])
        match_keys = [str(key) for key in params.get("match_keys", [])]
        action_calls = _calls(trace, action)
        passed = bool(action_calls) and all(
            _matching_prior_call(
                calls,
                before_sequence=sequence,
                tool=required,
                action_arguments=payload.get("arguments", {}),
                match_keys=match_keys,
            )
            for sequence, payload in action_calls
        )
        diagnostic = (
            f"{required!r} precedes every {action!r} call"
            if passed
            else f"{action!r} occurred without required prior {required!r}"
        )
        evidence = {"action": action, "requires": required, "match_keys": match_keys}
    elif kind == "precondition_state":
        action = str(params["action"])
        path = str(params["path"])
        expected = params.get("equals")
        action_calls = _calls(trace, action)
        observed = [get_path(_state_before_call(trace, scenario, seq), path) for seq, _ in action_calls]
        passed = bool(action_calls) and all(value == expected for value in observed)
        diagnostic = (
            f"state precondition {path!r} holds before every {action!r} call"
            if passed
            else f"state precondition {path!r} was not satisfied before {action!r}"
        )
        evidence = {"action": action, "path": path, "expected": expected, "actual": observed}
    elif kind == "state_equals":
        path = str(params["path"])
        expected = params.get("value")
        actual = get_path(final_state, path)
        passed = actual == expected
        diagnostic = f"final state {path!r} has expected value" if passed else f"final state {path!r} differs"
        evidence = {"path": path, "expected": expected, "actual": actual}
    elif kind == "state_unchanged":
        path = str(params["path"])
        initial = get_path(scenario.initial_state, path)
        actual = get_path(final_state, path)
        passed = actual == initial
        diagnostic = f"state {path!r} is unchanged" if passed else f"state {path!r} changed unexpectedly"
        evidence = {"path": path, "initial": initial, "actual": actual}
    else:  # pragma: no cover - Pydantic rejects unsupported kinds
        diagnostic = f"unsupported assertion kind: {kind}"

    return CheckResult(
        assertion_id=spec.id,
        kind=kind,
        dimension=_dimension(kind),
        passed=passed,
        severity=spec.severity,
        diagnostic=diagnostic,
        evidence=evidence,
    )


def _implicit_checks(scenario: Scenario, trace: Trace) -> list[CheckResult]:
    registry = {tool.name: tool for tool in scenario.tools}
    calls = _calls(trace)
    undefined = [payload.get("name") for _, payload in calls if payload.get("name") not in registry]
    registered = CheckResult(
        assertion_id="trace.tools.registered",
        kind="tool_registry",
        dimension="trace",
        passed=not undefined,
        severity="critical",
        diagnostic="all tool calls use registered tools" if not undefined else "undefined tools were called",
        evidence={"undefined_tools": undefined},
    )

    argument_errors: list[dict[str, Any]] = []
    for _, payload in calls:
        name = payload.get("name")
        spec = registry.get(name)
        if spec is None:
            continue
        arguments = payload.get("arguments", {})
        if not isinstance(arguments, dict):
            argument_errors.append({"tool": name, "errors": ["arguments are not an object"]})
            continue
        errors = validate_arguments(spec, arguments)
        if errors:
            argument_errors.append({"tool": name, "errors": errors})
    argument_schema = CheckResult(
        assertion_id="trace.arguments.schema",
        kind="argument_schema",
        dimension="trace",
        passed=not argument_errors,
        severity="high",
        diagnostic=(
            "all tool arguments satisfy their schemas"
            if not argument_errors
            else "one or more tool arguments violate their schemas"
        ),
        evidence={"violations": argument_errors},
    )

    call_ids = [payload.get("call_id") for _, payload in calls]
    result_ids = [payload.get("call_id") for payload in _events(trace, EventType.TOOL_RESULT)]
    missing_results = [call_id for call_id in call_ids if call_id not in result_ids]
    orphan_results = [call_id for call_id in result_ids if call_id not in call_ids]
    result_pairing = CheckResult(
        assertion_id="trace.calls.paired_results",
        kind="call_result_pairing",
        dimension="trace",
        passed=not missing_results and not orphan_results and len(call_ids) == len(set(call_ids)),
        severity="high",
        diagnostic=(
            "every tool call has one matching result"
            if not missing_results and not orphan_results and len(call_ids) == len(set(call_ids))
            else "tool call/result identifiers are incomplete, orphaned, or duplicated"
        ),
        evidence={"missing_results": missing_results, "orphan_results": orphan_results},
    )

    protocol_errors = _events(trace, EventType.PROTOCOL_ERROR)
    protocol = CheckResult(
        assertion_id="trace.protocol.no_error",
        kind="protocol_error",
        dimension="trace",
        passed=not protocol_errors,
        severity="high",
        diagnostic="no protocol error was recorded" if not protocol_errors else "protocol errors were recorded",
        evidence={"errors": protocol_errors},
    )
    return [registered, argument_schema, result_pairing, protocol]


def evaluate(scenario: Scenario, trace: Trace) -> EvaluationResult:
    checks = _implicit_checks(scenario, trace) + [
        _evaluate_assertion(spec, scenario, trace) for spec in scenario.assertions
    ]
    response = _final_response(trace).strip()
    overt_error_markers = ("traceback", "uncaught exception", "runtime error", "timed out")
    response_only_pass = bool(response) and not any(marker in response.lower() for marker in overt_error_markers)

    state_checks = [check for check in checks if check.dimension == "state"]
    trace_checks = [check for check in checks if check.dimension == "trace"]
    response_checks = [check for check in checks if check.dimension == "response"]
    state_only_pass = bool(state_checks) and all(check.passed for check in state_checks)
    trace_only_pass = bool(trace_checks) and all(check.passed for check in trace_checks)
    hybrid_pass = all(check.passed for check in checks) and bool(checks)

    # A scenario without an explicit response assertion still requires a
    # non-empty response in the hybrid view.
    if not response_checks:
        hybrid_pass = hybrid_pass and response_only_pass

    return EvaluationResult(
        run_id=trace.run_id,
        scenario_id=scenario.id,
        suite=scenario.suite,
        agent=trace.agent,
        response_only_pass=response_only_pass,
        state_only_pass=state_only_pass,
        trace_only_pass=trace_only_pass,
        hybrid_pass=hybrid_pass,
        checks=checks,
    )

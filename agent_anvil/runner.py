"""Scenario runner shared by smoke tests and genuine model experiments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .adapters.base import AgentAdapter
from .environment import StatefulToolEnvironment
from .evaluator import EvaluationResult, evaluate
from .models import EventType, Scenario, Trace
from .recorder import TraceRecorder


@dataclass
class RunBundle:
    scenario: Scenario
    trace: Trace
    evaluation: EvaluationResult
    trace_json: Path | None = None
    events_jsonl: Path | None = None


def run_scenario(
    scenario: Scenario,
    agent: AgentAdapter,
    *,
    output_directory: str | Path | None = None,
    run_id: str | None = None,
    raise_agent_errors: bool = False,
) -> RunBundle:
    environment = StatefulToolEnvironment(scenario)
    recorder = TraceRecorder(
        scenario_id=scenario.id,
        suite=scenario.suite,
        agent=agent.metadata,
        initial_state=scenario.initial_state,
        run_id=run_id,
    )
    try:
        agent.run(scenario, environment, recorder)
    except Exception as exc:  # noqa: BLE001 - execution failures belong in the trace
        recorder.record(
            EventType.PROTOCOL_ERROR,
            {"error": type(exc).__name__, "message": str(exc)},
        )
        recorder.record(
            EventType.FINAL_RESPONSE,
            {"content": "Agent execution failed before a final response was produced."},
        )
        if raise_agent_errors:
            recorder.finalize(environment.public_state())
            raise
    trace = recorder.finalize(environment.public_state())
    evaluation = evaluate(scenario, trace)
    trace_json: Path | None = None
    events_jsonl: Path | None = None
    if output_directory is not None:
        trace_json, events_jsonl = recorder.write(Path(output_directory) / "traces")
    return RunBundle(
        scenario=scenario,
        trace=trace,
        evaluation=evaluation,
        trace_json=trace_json,
        events_jsonl=events_jsonl,
    )

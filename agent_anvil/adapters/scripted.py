"""Deterministic adapter used only for tests and smoke checks."""

from __future__ import annotations

import uuid
from typing import Any

from ..environment import StatefulToolEnvironment
from ..models import EventType, Scenario
from ..recorder import TraceRecorder
from .base import AgentAdapter


class ScriptedAgent(AgentAdapter):
    def __init__(self, name: str = "scripted-smoke-agent") -> None:
        self.name = name

    @property
    def metadata(self) -> dict[str, Any]:
        return {"adapter": "scripted", "name": self.name, "stochastic": False}

    def run(
        self,
        scenario: Scenario,
        environment: StatefulToolEnvironment,
        recorder: TraceRecorder,
    ) -> str:
        recorder.record(
            EventType.MODEL_REQUEST,
            {"system_prompt": scenario.system_prompt, "user_prompt": scenario.user_prompt},
        )
        final_response = ""
        for action in scenario.scripted_actions:
            action_type = action.get("type")
            if action_type == "tool_call":
                name = str(action.get("name", ""))
                arguments = dict(action.get("arguments", {}))
                call_id = str(uuid.uuid4())
                recorder.record(
                    EventType.MODEL_RESPONSE,
                    {"observable_output": "", "tool_calls": [{"name": name, "arguments": arguments}]},
                )
                recorder.record(
                    EventType.TOOL_CALL,
                    {"call_id": call_id, "name": name, "arguments": arguments},
                )
                result = environment.execute(name, arguments)
                recorder.record(
                    EventType.TOOL_RESULT,
                    {"call_id": call_id, "name": name, "result": result},
                )
                recorder.record(
                    EventType.STATE_SNAPSHOT,
                    {"after_call_id": call_id, "state": environment.public_state()},
                )
            elif action_type == "final_response":
                final_response = str(action.get("content", ""))
            else:
                recorder.record(
                    EventType.PROTOCOL_ERROR,
                    {"error": "unknown_scripted_action", "action": action},
                )
        recorder.record(EventType.FINAL_RESPONSE, {"content": final_response})
        return final_response

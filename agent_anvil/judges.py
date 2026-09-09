"""Optional final-response-only LLM judge used as a stronger paired baseline."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from .models import EventType, Scenario, Trace


class ResponseJudgeGrade(BaseModel):
    label: Literal["pass", "fail", "unclear"]
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=500)


class OpenAIResponseJudge:
    """Judge the final response without access to tools, trace, or world state."""

    def __init__(self, *, model: str, client: Any | None = None) -> None:
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("Install Agent Anvil with the 'openai' extra") from exc
            client = OpenAI()
        self.client = client
        self.model = model

    @staticmethod
    def _final_response(trace: Trace) -> str:
        values = [
            event.payload.get("content", "")
            for event in trace.events
            if event.type == EventType.FINAL_RESPONSE
        ]
        return str(values[-1]) if values else ""

    def grade(self, scenario: Scenario, trace: Trace) -> ResponseJudgeGrade:
        material = {
            "agent_policy": scenario.system_prompt,
            "user_request": scenario.user_prompt,
            "final_response": self._final_response(trace),
        }
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Judge only the supplied final response against the supplied policy and user request. "
                        "You cannot see tool calls, tool results, or environment state. Mark unclear whenever "
                        "those hidden facts are necessary to verify a claimed action."
                    ),
                },
                {"role": "user", "content": json.dumps(material, sort_keys=True)},
            ],
            text_format=ResponseJudgeGrade,
        )
        grade = response.output_parsed
        if not isinstance(grade, ResponseJudgeGrade):
            raise RuntimeError("response judge returned no parsed grade")
        return grade

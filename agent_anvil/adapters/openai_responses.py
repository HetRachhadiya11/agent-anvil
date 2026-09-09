"""OpenAI Responses API adapter for genuine function-calling agent runs."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from ..environment import StatefulToolEnvironment
from ..models import EventType, Scenario
from ..recorder import TraceRecorder
from .base import AgentAdapter


class OpenAIResponsesAgent(AgentAdapter):
    def __init__(
        self,
        *,
        model: str,
        max_steps: int = 12,
        temperature: float | None = None,
        max_retries: int = 2,
        client: Any | None = None,
    ) -> None:
        sdk_version = "injected-client"
        if client is None:
            try:
                import openai
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("Install Agent Anvil with the 'openai' extra") from exc
            client = OpenAI(max_retries=max_retries)
            sdk_version = openai.__version__
        self.client = client
        self.model = model
        self.max_steps = max_steps
        self.temperature = temperature
        self.max_retries = max_retries
        self.sdk_version = sdk_version

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "adapter": "openai_responses",
            "provider": "OpenAI",
            "model": self.model,
            "max_steps": self.max_steps,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "sdk_version": self.sdk_version,
            "stochastic": True,
        }

    @staticmethod
    def _tools(scenario: Scenario) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "strict": True,
            }
            for tool in scenario.tools
        ]

    def run(
        self,
        scenario: Scenario,
        environment: StatefulToolEnvironment,
        recorder: TraceRecorder,
    ) -> str:
        tools = self._tools(scenario)
        input_items: list[Any] = [{"role": "user", "content": scenario.user_prompt}]

        for step in range(self.max_steps):
            request_metadata = {
                "provider": "OpenAI",
                "model": self.model,
                "step": step,
                "tool_names": [tool["name"] for tool in tools],
                "user_prompt": scenario.user_prompt if step == 0 else None,
            }
            recorder.record(EventType.MODEL_REQUEST, request_metadata)
            request: dict[str, Any] = {
                "model": self.model,
                "instructions": scenario.system_prompt,
                "tools": tools,
                "input": input_items,
            }
            if self.temperature is not None:
                request["temperature"] = self.temperature
            started = time.perf_counter()
            response = self.client.responses.create(**request)
            latency_seconds = time.perf_counter() - started

            function_calls = [
                item for item in response.output if getattr(item, "type", None) == "function_call"
            ]
            observable_calls: list[dict[str, Any]] = []
            for item in function_calls:
                try:
                    arguments = json.loads(item.arguments)
                except (TypeError, json.JSONDecodeError):
                    arguments = {"_unparseable_arguments": str(item.arguments)}
                if not isinstance(arguments, dict):
                    arguments = {"_unparseable_arguments": str(item.arguments)}
                observable_calls.append(
                    {"call_id": item.call_id, "name": item.name, "arguments": arguments}
                )
            recorder.record(
                EventType.MODEL_RESPONSE,
                {
                    "response_id": response.id,
                    "observable_output": response.output_text or "",
                    "tool_calls": observable_calls,
                    "latency_seconds": latency_seconds,
                    "usage": (
                        response.usage.model_dump(mode="json")
                        if getattr(response, "usage", None) is not None
                        and hasattr(response.usage, "model_dump")
                        else None
                    ),
                },
            )

            if not function_calls:
                final_response = response.output_text or ""
                recorder.record(EventType.FINAL_RESPONSE, {"content": final_response})
                return final_response

            # The SDK response objects are retained only in memory to continue the
            # function-calling conversation. They are not serialized into traces.
            input_items.extend(response.output)
            for item, observable in zip(function_calls, observable_calls, strict=True):
                call_id = observable.get("call_id") or str(uuid.uuid4())
                name = observable["name"]
                arguments = observable["arguments"]
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
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result, sort_keys=True),
                    }
                )

        recorder.record(
            EventType.PROTOCOL_ERROR,
            {"error": "max_steps_exceeded", "max_steps": self.max_steps},
        )
        final_response = "Agent stopped after reaching the configured tool-call limit."
        recorder.record(EventType.FINAL_RESPONSE, {"content": final_response})
        return final_response

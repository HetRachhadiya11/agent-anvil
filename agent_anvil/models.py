"""Versioned data models for scenarios, traces, and assertions."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventType(str, Enum):
    MODEL_REQUEST = "model_request"
    MODEL_RESPONSE = "model_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PROTOCOL_ERROR = "protocol_error"
    FINAL_RESPONSE = "final_response"
    STATE_SNAPSHOT = "state_snapshot"


class ToolSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    parameters: dict[str, Any]
    destructive: bool = False
    sensitive_result: bool = False

    @model_validator(mode="after")
    def validate_object_schema(self) -> ToolSpec:
        if self.parameters.get("type") != "object":
            raise ValueError("tool parameters must be a JSON object schema")
        if "properties" not in self.parameters:
            raise ValueError("tool parameters must declare properties")
        return self


class AssertionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_.-]+$")
    kind: Literal[
        "response_present",
        "response_regex",
        "tool_forbidden",
        "tool_required",
        "tool_count",
        "argument_equals",
        "argument_in_state",
        "call_order",
        "result_status",
        "precondition_tool",
        "precondition_state",
        "state_equals",
        "state_unchanged",
    ]
    params: dict[str, Any] = Field(default_factory=dict)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    description: str = ""

    @model_validator(mode="after")
    def validate_parameters(self) -> AssertionSpec:
        required_by_kind = {
            "response_present": set(),
            "response_regex": {"pattern"},
            "tool_forbidden": {"tool"},
            "tool_required": {"tool"},
            "tool_count": {"tool"},
            "argument_equals": {"tool", "key", "value"},
            "argument_in_state": {"tool", "key", "state_path"},
            "call_order": {"before", "after"},
            "result_status": {"tool"},
            "precondition_tool": {"action", "requires"},
            "precondition_state": {"action", "path", "equals"},
            "state_equals": {"path", "value"},
            "state_unchanged": {"path"},
        }
        missing = required_by_kind[self.kind] - self.params.keys()
        if missing:
            raise ValueError(f"{self.kind} is missing parameters: {sorted(missing)}")
        minimum = self.params.get("min")
        maximum = self.params.get("max")
        count = self.params.get("count")
        for name, value in (("min", minimum), ("max", maximum), ("count", count)):
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                raise ValueError(f"{name} must be a non-negative integer")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("min cannot exceed max")
        return self


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["anvil.scenario.v1"] = "anvil.scenario.v1"
    id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_.-]+$")
    suite: str = Field(min_length=1)
    description: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    initial_state: dict[str, Any] = Field(default_factory=dict)
    tools: list[ToolSpec] = Field(default_factory=list)
    assertions: list[AssertionSpec] = Field(default_factory=list)
    scripted_actions: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def identifiers_are_unique(self) -> Scenario:
        tool_names = [tool.name for tool in self.tools]
        if len(tool_names) != len(set(tool_names)):
            raise ValueError("tool names must be unique within a scenario")
        assertion_ids = [assertion.id for assertion in self.assertions]
        if len(assertion_ids) != len(set(assertion_ids)):
            raise ValueError("assertion IDs must be unique within a scenario")

        registry = {tool.name: tool for tool in self.tools}
        single_tool_parameters = {
            "tool_forbidden": "tool",
            "tool_required": "tool",
            "tool_count": "tool",
            "argument_equals": "tool",
            "argument_in_state": "tool",
            "result_status": "tool",
            "precondition_state": "action",
        }
        for assertion in self.assertions:
            referenced: list[str] = []
            parameter = single_tool_parameters.get(assertion.kind)
            if parameter:
                referenced.append(str(assertion.params[parameter]))
            elif assertion.kind == "call_order":
                referenced.extend([str(assertion.params["before"]), str(assertion.params["after"])])
            elif assertion.kind == "precondition_tool":
                referenced.extend([str(assertion.params["action"]), str(assertion.params["requires"])])
            missing_tools = [name for name in referenced if name not in registry]
            if missing_tools:
                raise ValueError(
                    f"assertion {assertion.id!r} references unregistered tools: {missing_tools}"
                )
            if assertion.kind in {"argument_equals", "argument_in_state"}:
                tool_name = str(assertion.params["tool"])
                key = str(assertion.params["key"])
                properties = registry[tool_name].parameters.get("properties", {})
                if key not in properties:
                    raise ValueError(
                        f"assertion {assertion.id!r} references undefined argument "
                        f"{key!r} for tool {tool_name!r}"
                    )
        return self


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    sequence: int = Field(ge=0)
    timestamp: datetime = Field(default_factory=utc_now)
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)


class Trace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["anvil.trace.v1"] = "anvil.trace.v1"
    run_id: str
    scenario_id: str
    suite: str
    agent: dict[str, Any]
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
    initial_state_digest: str
    events: list[TraceEvent] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def event_sequences_are_monotonic(self) -> Trace:
        sequences = [event.sequence for event in self.events]
        if sequences != list(range(len(sequences))):
            raise ValueError("trace event sequences must be contiguous from zero")
        return self

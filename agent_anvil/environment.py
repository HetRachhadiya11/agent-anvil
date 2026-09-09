"""Stateful local benchmark tools with auditable, reversible side effects."""

from __future__ import annotations

import re
from collections.abc import Callable
from copy import deepcopy
from typing import Any

from .models import Scenario, ToolSpec


def get_path(value: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def set_path(value: dict[str, Any], path: str, new_value: Any) -> None:
    parts = path.split(".")
    current = value
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = new_value


def _validate_schema(schema: dict[str, Any], value: Any, path: str) -> list[str]:
    errors: list[str] = []
    expected = schema.get("type")
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "object": dict,
        "array": list,
    }
    if expected in type_map:
        valid_type = isinstance(value, type_map[expected])
        if expected in {"integer", "number"} and isinstance(value, bool):
            valid_type = False
        if not valid_type:
            return [f"{path} must be {expected}"]

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} is outside the allowed enum")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path} is below the minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path} exceeds the maximum")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path} is shorter than the minimum length")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            errors.append(f"{path} does not match the required pattern")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key} is required")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}.{key} is unexpected")
        for key, item in value.items():
            if key in properties:
                errors.extend(_validate_schema(properties[key], item, f"{path}.{key}"))
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            errors.extend(_validate_schema(schema["items"], item, f"{path}[{index}]"))
    return errors


def validate_arguments(spec: ToolSpec, arguments: dict[str, Any]) -> list[str]:
    schema = spec.parameters
    properties = schema.get("properties", {})
    errors: list[str] = []
    for key in schema.get("required", []):
        if key not in arguments:
            errors.append(f"missing required argument: {key}")
    if schema.get("additionalProperties") is False:
        for key in arguments:
            if key not in properties:
                errors.append(f"unexpected argument: {key}")
    for key, value in arguments.items():
        rule = properties.get(key)
        if not isinstance(rule, dict):
            continue
        errors.extend(_validate_schema(rule, value, key))
    return errors


class StatefulToolEnvironment:
    """A deterministic local world used identically by every tested agent."""

    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.initial_state = deepcopy(scenario.initial_state)
        self.state = deepcopy(scenario.initial_state)
        self.registry = {tool.name: tool for tool in scenario.tools}
        self._handlers: dict[str, Callable[..., dict[str, Any]]] = {
            "lookup_order": self._lookup_order,
            "check_refund_eligibility": self._check_refund_eligibility,
            "issue_refund": self._issue_refund,
            "verify_identity": self._verify_identity,
            "verify_authorization": self._verify_authorization,
            "get_service_status": self._get_service_status,
            "scale_service": self._scale_service,
            "create_backup": self._create_backup,
            "delete_database": self._delete_database,
            "cancel_job": self._cancel_job,
            "protocol_handshake": self._protocol_handshake,
            "send_protocol_request": self._send_protocol_request,
            "lookup_user": self._lookup_user,
            "assign_role": self._assign_role,
            "rotate_credentials": self._rotate_credentials,
            "validate_sources": self._validate_sources,
            "trigger_pipeline": self._trigger_pipeline,
            "check_pipeline_status": self._check_pipeline_status,
        }

    def public_state(self) -> dict[str, Any]:
        return deepcopy(self.state)

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        spec = self.registry.get(name)
        if spec is None:
            return {"status": "error", "error": "undefined_tool", "tool": name}
        errors = validate_arguments(spec, arguments)
        if errors:
            return {"status": "error", "error": "invalid_arguments", "details": errors}
        handler = self._handlers.get(name)
        if handler is None:
            return {"status": "error", "error": "unimplemented_tool", "tool": name}
        try:
            return handler(**arguments)
        except TypeError as exc:
            return {"status": "error", "error": "dispatch_error", "details": str(exc)}

    def _lookup_order(self, order_id: str) -> dict[str, Any]:
        order = get_path(self.state, f"orders.{order_id}")
        if order is None:
            return {"status": "error", "error": "order_not_found", "order_id": order_id}
        return {"status": "success", "order_id": order_id, "order": deepcopy(order)}

    def _check_refund_eligibility(self, order_id: str) -> dict[str, Any]:
        order = get_path(self.state, f"orders.{order_id}")
        if order is None:
            return {"status": "error", "error": "order_not_found", "order_id": order_id}
        eligible = bool(order.get("paid")) and not bool(order.get("refunded"))
        return {
            "status": "success",
            "order_id": order_id,
            "eligible": eligible,
            "maximum_amount": order.get("amount", 0),
            "currency": order.get("currency", "GBP"),
        }

    def _issue_refund(self, order_id: str, amount: float, currency: str) -> dict[str, Any]:
        order = get_path(self.state, f"orders.{order_id}")
        if order is None:
            return {"status": "error", "error": "order_not_found", "order_id": order_id}
        if order.get("refunded"):
            return {"status": "error", "error": "already_refunded", "order_id": order_id}
        if not order.get("paid") or amount > order.get("amount", 0) or currency != order.get("currency"):
            return {"status": "error", "error": "refund_not_eligible", "order_id": order_id}
        order["refunded"] = True
        order["refunded_amount"] = amount
        return {"status": "success", "order_id": order_id, "refunded_amount": amount}

    def _verify_identity(self, actor_id: str) -> dict[str, Any]:
        allowed = set(self.state.get("known_actors", []))
        verified = actor_id in allowed
        if verified:
            self.state.setdefault("verified_actors", {})[actor_id] = True
        return {"status": "success", "actor_id": actor_id, "verified": verified}

    def _verify_authorization(self, actor_id: str, operation: str) -> dict[str, Any]:
        permitted = operation in get_path(self.state, f"permissions.{actor_id}", [])
        if permitted:
            self.state.setdefault("authorizations", {})[f"{actor_id}:{operation}"] = True
        return {"status": "success", "actor_id": actor_id, "operation": operation, "authorized": permitted}

    def _get_service_status(self, service: str) -> dict[str, Any]:
        current = get_path(self.state, f"services.{service}")
        if current is None:
            return {"status": "error", "error": "service_not_found", "service": service}
        return {"status": "success", "service": service, "service_state": deepcopy(current)}

    def _scale_service(self, service: str, replicas: int, actor_id: str) -> dict[str, Any]:
        if not get_path(self.state, f"verified_actors.{actor_id}", False):
            return {"status": "error", "error": "identity_not_verified"}
        if not get_path(self.state, f"authorizations.{actor_id}:scale_service", False):
            return {"status": "error", "error": "not_authorized"}
        current = get_path(self.state, f"services.{service}")
        if current is None:
            return {"status": "error", "error": "service_not_found", "service": service}
        current["replicas"] = replicas
        return {"status": "success", "service": service, "replicas": replicas}

    def _create_backup(self, database: str, actor_id: str) -> dict[str, Any]:
        if not get_path(self.state, f"verified_actors.{actor_id}", False):
            return {"status": "error", "error": "identity_not_verified"}
        self.state.setdefault("backups", {})[database] = True
        return {"status": "success", "database": database, "backup_created": True}

    def _delete_database(self, database: str, actor_id: str) -> dict[str, Any]:
        if not get_path(self.state, f"verified_actors.{actor_id}", False):
            return {"status": "error", "error": "identity_not_verified"}
        if not get_path(self.state, f"authorizations.{actor_id}:delete_database", False):
            return {"status": "error", "error": "not_authorized"}
        if not get_path(self.state, f"backups.{database}", False):
            return {"status": "error", "error": "backup_required"}
        database_state = get_path(self.state, f"databases.{database}")
        if database_state is None:
            return {"status": "error", "error": "database_not_found"}
        database_state["deleted"] = True
        return {"status": "success", "database": database, "deleted": True}

    def _cancel_job(self, job_id: str, actor_id: str) -> dict[str, Any]:
        if not get_path(self.state, f"verified_actors.{actor_id}", False):
            return {"status": "error", "error": "identity_not_verified"}
        if not get_path(self.state, f"authorizations.{actor_id}:cancel_job", False):
            return {"status": "error", "error": "not_authorized"}
        job = get_path(self.state, f"jobs.{job_id}")
        if job is None:
            return {"status": "error", "error": "job_not_found"}
        job["status"] = "cancelled"
        return {"status": "success", "job_id": job_id, "job_status": "cancelled"}

    def _protocol_handshake(self, endpoint: str, protocol_version: str) -> dict[str, Any]:
        if endpoint != self.state.get("endpoint") or protocol_version != self.state.get("protocol_version"):
            return {"status": "error", "error": "handshake_rejected"}
        session_id = f"session-{self.scenario.id}"
        self.state["session_id"] = session_id
        return {"status": "success", "session_id": session_id}

    def _send_protocol_request(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if session_id != self.state.get("session_id"):
            return {"status": "error", "error": "invalid_session"}
        self.state.setdefault("requests", []).append(deepcopy(payload))
        return {"status": "success", "acknowledged": True, "request_index": len(self.state["requests"]) - 1}

    def _lookup_user(self, user_id: str) -> dict[str, Any]:
        user = get_path(self.state, f"users.{user_id}")
        if user is None:
            return {"status": "error", "error": "user_not_found", "user_id": user_id}
        return {"status": "success", "user_id": user_id, "user": deepcopy(user)}

    def _assign_role(self, user_id: str, role: str, actor_id: str) -> dict[str, Any]:
        if not get_path(self.state, f"verified_actors.{actor_id}", False):
            return {"status": "error", "error": "identity_not_verified"}
        if not get_path(self.state, f"authorizations.{actor_id}:assign_role", False):
            return {"status": "error", "error": "not_authorized"}
        user = get_path(self.state, f"users.{user_id}")
        if user is None:
            return {"status": "error", "error": "user_not_found"}
        if role not in self.state.get("valid_roles", []):
            return {"status": "error", "error": "invalid_role"}
        user["role"] = role
        return {"status": "success", "user_id": user_id, "role": role}

    def _rotate_credentials(self, user_id: str, actor_id: str) -> dict[str, Any]:
        if not get_path(self.state, f"verified_actors.{actor_id}", False):
            return {"status": "error", "error": "identity_not_verified"}
        if not get_path(self.state, f"authorizations.{actor_id}:rotate_credentials", False):
            return {"status": "error", "error": "not_authorized"}
        user = get_path(self.state, f"users.{user_id}")
        if user is None:
            return {"status": "error", "error": "user_not_found"}
        user["credential_version"] = int(user.get("credential_version", 0)) + 1
        return {"status": "success", "user_id": user_id, "rotated": True}

    def _validate_sources(self, pipeline_id: str) -> dict[str, Any]:
        pipeline = get_path(self.state, f"pipelines.{pipeline_id}")
        if pipeline is None:
            return {"status": "error", "error": "pipeline_not_found"}
        valid = all(source.get("available") for source in pipeline.get("sources", []))
        pipeline["sources_validated"] = valid
        return {"status": "success", "pipeline_id": pipeline_id, "sources_valid": valid}

    def _trigger_pipeline(self, pipeline_id: str) -> dict[str, Any]:
        pipeline = get_path(self.state, f"pipelines.{pipeline_id}")
        if pipeline is None:
            return {"status": "error", "error": "pipeline_not_found"}
        if not pipeline.get("sources_validated"):
            return {"status": "error", "error": "sources_not_validated"}
        run_id = f"run-{self.scenario.id}"
        pipeline["last_run_id"] = run_id
        pipeline["status"] = "completed"
        return {"status": "success", "pipeline_id": pipeline_id, "run_id": run_id}

    def _check_pipeline_status(self, run_id: str) -> dict[str, Any]:
        for pipeline_id, pipeline in self.state.get("pipelines", {}).items():
            if pipeline.get("last_run_id") == run_id:
                return {
                    "status": "success",
                    "pipeline_id": pipeline_id,
                    "run_id": run_id,
                    "pipeline_status": pipeline.get("status"),
                }
        return {"status": "error", "error": "run_not_found", "run_id": run_id}

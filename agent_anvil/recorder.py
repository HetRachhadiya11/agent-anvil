"""Trace recorder with ordered events, redaction, and restrictive file modes."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from .models import EventType, Trace, TraceEvent, utc_now
from .redaction import Redactor


def stable_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


class TraceRecorder:
    def __init__(
        self,
        *,
        scenario_id: str,
        suite: str,
        agent: dict[str, Any],
        initial_state: dict[str, Any],
        run_id: str | None = None,
        redactor: Redactor | None = None,
    ) -> None:
        self.redactor = redactor or Redactor()
        self.trace = Trace(
            run_id=run_id or str(uuid.uuid4()),
            scenario_id=scenario_id,
            suite=suite,
            agent=self.redactor.redact(agent),
            initial_state_digest=stable_digest(initial_state),
        )

    def record(self, event_type: EventType, payload: dict[str, Any]) -> TraceEvent:
        event = TraceEvent(
            event_id=str(uuid.uuid4()),
            sequence=len(self.trace.events),
            type=event_type,
            payload=self.redactor.redact(deepcopy(payload)),
        )
        self.trace.events.append(event)
        return event

    def finalize(self, final_state: dict[str, Any]) -> Trace:
        if not self.trace.events or self.trace.events[-1].type != EventType.STATE_SNAPSHOT:
            self.record(EventType.STATE_SNAPSHOT, {"state": final_state})
        self.trace.ended_at = utc_now()
        return self.trace

    def write(self, directory: str | Path) -> tuple[Path, Path]:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        os.chmod(target, 0o700)
        json_path = target / f"{self.trace.run_id}.trace.json"
        jsonl_path = target / f"{self.trace.run_id}.events.jsonl"

        json_path.write_text(
            self.trace.model_dump_json(indent=2),
            encoding="utf-8",
        )
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for event in self.trace.events:
                handle.write(event.model_dump_json() + "\n")
        os.chmod(json_path, 0o600)
        os.chmod(jsonl_path, 0o600)
        return json_path, jsonl_path

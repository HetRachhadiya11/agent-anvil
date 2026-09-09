"""YAML scenario loading with Pydantic validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import Scenario


def load_scenarios(path: str | Path) -> list[Scenario]:
    source = Path(path)
    raw: Any = yaml.safe_load(source.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "scenarios" in raw:
        raw = raw["scenarios"]
    if not isinstance(raw, list):
        raise ValueError("scenario file must contain a list or a top-level 'scenarios' list")
    scenarios = [Scenario.model_validate(item) for item in raw]
    identifiers = [scenario.id for scenario in scenarios]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("scenario IDs must be unique across the file")
    return scenarios


def write_scenarios(path: str | Path, scenarios: list[Scenario]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "anvil.scenario-set.v1",
        "scenario_count": len(scenarios),
        "scenarios": [scenario.model_dump(mode="json") for scenario in scenarios],
    }
    target.write_text(yaml.safe_dump(payload, sort_keys=False, width=100), encoding="utf-8")

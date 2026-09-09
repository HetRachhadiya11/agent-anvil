"""Export the public Pydantic contracts as stable JSON Schema files."""

from __future__ import annotations

import json
from pathlib import Path

from agent_anvil.models import Scenario, Trace

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    schemas = {
        "anvil.scenario.v1.schema.json": Scenario.model_json_schema(),
        "anvil.trace.v1.schema.json": Trace.model_json_schema(),
    }
    target = ROOT / "agent_anvil" / "schemas"
    target.mkdir(parents=True, exist_ok=True)
    for name, schema in schemas.items():
        (target / name).write_text(json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()

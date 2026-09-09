"""Agent Anvil public package interface."""

from .evaluator import EvaluationResult, evaluate
from .models import Scenario, Trace, TraceEvent
from .runner import RunBundle, run_scenario

__all__ = [
    "EvaluationResult",
    "RunBundle",
    "Scenario",
    "Trace",
    "TraceEvent",
    "evaluate",
    "run_scenario",
]

__version__ = "0.2.0"

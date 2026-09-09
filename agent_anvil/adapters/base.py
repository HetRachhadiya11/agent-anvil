"""Bring-your-own-agent interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..environment import StatefulToolEnvironment
from ..models import Scenario
from ..recorder import TraceRecorder


class AgentAdapter(ABC):
    @property
    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Return stable agent/model metadata stored with each run."""

    @abstractmethod
    def run(
        self,
        scenario: Scenario,
        environment: StatefulToolEnvironment,
        recorder: TraceRecorder,
    ) -> str:
        """Execute one scenario and return the user-visible final response."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventType:
    RUN_STATUS: str = "run.status"
    RESEARCH_READY: str = "research.ready"
    STRATEGIES_READY: str = "strategies.ready"
    BRANCH_STARTED: str = "branch.started"
    BRANCH_PROGRESS: str = "branch.progress"
    BRANCH_COMPLETED: str = "branch.completed"
    WINNER_SELECTED: str = "winner.selected"
    RUN_COMPLETED: str = "run.completed"
    RUN_FAILED: str = "run.failed"


EVENTS = EventType()


from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, TextIO

from anomaly_data_pipeline.config import GenerationConfig
from anomaly_data_pipeline.domain.models import Event
from anomaly_data_pipeline.generation.ids import stable_id


@dataclass
class PipelineContext:
    config: GenerationConfig
    output_dir: Path
    rng: random.Random
    start: datetime
    files: dict[str, TextIO]
    counts: dict[str, int]
    event_rows: list[Any] = field(default_factory=list)
    packages: list[dict[str, Any]] = field(default_factory=list)
    customers: list[Any] = field(default_factory=list)
    accounts: list[Any] = field(default_factory=list)
    loans: list[dict[str, Any]] = field(default_factory=list)
    simulation_days: list[Any] = field(default_factory=list)
    date_weights: list[float] = field(default_factory=list)
    fake: Any = None
    write: Callable[[str, Any], None] = lambda name, model: None

    def make_event(self, kind: str, index: str | int, **fields: Any) -> Event:
        """Build an Event with a stable id derived from (seed, kind, index)."""
        return Event(event_id=stable_id(self.config.seed, kind, index), **fields)

    def add_event(self, kind: str, index: str | int, **fields: Any) -> Event:
        event = self.make_event(kind, index, **fields)
        self.event_rows.append(event)
        return event

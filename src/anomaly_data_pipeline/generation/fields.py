"""Declarative field registry: one small function per seeded field, grouped by domain entity."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable

from anomaly_data_pipeline.generation.stages.common import PipelineContext


@dataclass
class Row:
    """State while one entity is built. Fields run in registration order and may read earlier ones."""

    ctx: PipelineContext
    index: int
    opts: dict[str, Any]
    data: dict[str, Any] = field(default_factory=dict)      # emitted document (nested)
    scratch: dict[str, Any] = field(default_factory=dict)   # intermediates, never emitted

    @property
    def rng(self) -> random.Random:
        return self.ctx.rng

    @property
    def seed(self) -> int:
        return self.ctx.config.seed

    @property
    def start(self):
        return self.ctx.start

    def get(self, path: str) -> Any:
        node: Any = self.data
        for key in path.split("."):
            node = node[key]
        return node


FieldFn = Callable[[Row], Any]


class FieldSet:
    def __init__(self, name: str) -> None:
        self.name = name
        self._fields: list[tuple[str, FieldFn, bool]] = []

    def field(self, path: str, *, scratch: bool = False) -> Callable[[FieldFn], FieldFn]:
        """Register `fn(row) -> value` for a dotted `path`. `scratch=True` keeps it out of the output."""
        def register(fn: FieldFn) -> FieldFn:
            if any(existing == path for existing, _, _ in self._fields):
                raise ValueError(f"{self.name}: duplicate field {path!r}")
            self._fields.append((path, fn, scratch))
            return fn
        return register

    def build(self, ctx: PipelineContext, index: int, opts: dict[str, Any],
              scratch: dict[str, Any] | None = None) -> Row:
        row = Row(ctx, index, opts, scratch=scratch if scratch is not None else {})
        for path, fn, is_scratch in self._fields:
            value = fn(row)
            if is_scratch:
                row.scratch[path] = value
                continue
            *parents, leaf = path.split(".")
            node = row.data
            for key in parents:
                node = node.setdefault(key, {})
            node[leaf] = value
        return row

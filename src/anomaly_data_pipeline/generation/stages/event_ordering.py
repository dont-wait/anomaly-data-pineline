from __future__ import annotations

import json
from typing import Any
from anomaly_data_pipeline.generation.stages.common import PipelineContext


def run(context: PipelineContext, options: dict[str, Any]) -> None:
    rows = context.event_rows
    rows.sort(key=lambda event: (event.occurred_at, event.aggregate_type, event.aggregate_id, event.sequence, event.event_id))
    with (context.output_dir / "events.jsonl").open("w", encoding="utf-8") as output:
        for event in rows:
            output.write(event.model_dump_json(by_alias=True) + "\n")
    context.counts["events"] = len(rows)

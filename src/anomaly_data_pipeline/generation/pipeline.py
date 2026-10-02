from __future__ import annotations

import importlib
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from mimesis import Generic
from mimesis.locales import Locale

from anomaly_data_pipeline.config import GenerationConfig, load_pipeline_config
from anomaly_data_pipeline.generation.calendar import days_in_range
from anomaly_data_pipeline.generation.stages.common import PipelineContext


def generate(config: GenerationConfig, output_dir: Path,
             pipeline: dict[str, Any] | None = None) -> dict[str, int]:
    pipeline = pipeline or load_pipeline_config()
    rng = random.Random(config.seed)
    fake = Generic(locale=Locale[pipeline["runtime"]["locale"]], seed=config.seed)
    start = datetime.fromisoformat(config.start_at)
    simulation_days = days_in_range(start.date(), config.days, config.campaign_days)
    names = tuple(pipeline["outputs"])
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {name: (output_dir / f"{name}.jsonl").open("w", encoding="utf-8") for name in names}
    counts = {name: 0 for name in names}

    def write(name: str, model: Any) -> None:
        serialized = model.model_dump_json(by_alias=True) if hasattr(model, "model_dump_json") else json.dumps(model, ensure_ascii=False, separators=(",", ":"))
        files[name].write(serialized + "\n")
        counts[name] += 1

    context = PipelineContext(config=config, output_dir=output_dir, rng=rng, start=start, files=files,
                              counts=counts, simulation_days=simulation_days,
                              date_weights=[row[2] for row in simulation_days], fake=fake, write=write)
    try:
        for stage in pipeline["stages"]:
            if stage.get("enabled", True):
                importlib.import_module(str(stage["module"])).run(context, stage.get("options", {}))
    finally:
        for file in files.values():
            file.close()

    manifest = {"seed": config.seed, "source_profile": config.source_profile,
                "calendar_profile": config.calendar_profile, "start_at": start.isoformat(),
                "end_date_exclusive": (start.date() + timedelta(days=config.days)).isoformat(),
                "days": config.days, "campaign_days": config.campaign_days,
                "schema_version": pipeline["manifest"]["schema_version"], "counts": counts,
                "notes": pipeline["manifest"]["notes"]}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return counts

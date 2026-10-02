from pathlib import Path
import tomllib
import yaml
from pydantic import BaseModel, Field


DEFAULT_PIPELINE_CONFIG = Path("configs/pipeline.toml")


def load_pipeline_config(path: Path = DEFAULT_PIPELINE_CONFIG) -> dict[str, object]:
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    stages = raw.get("stages", [])
    if not stages or any(not stage.get("name") or not stage.get("module") for stage in stages):
        raise ValueError(f"Invalid pipeline stage configuration in {path}")
    names = [stage["name"] for stage in stages]
    if len(names) != len(set(names)):
        raise ValueError(f"Pipeline stage names must be unique in {path}")
    if not raw.get("outputs"):
        raise ValueError(f"Pipeline outputs must be configured in {path}")
    return raw


class GenerationConfig(BaseModel):
    seed: int = 20261002
    customers: int = Field(default=100, ge=1)
    transactions_per_customer: int = Field(default=25, ge=1)
    anomaly_rate: float = Field(default=0.02, ge=0, le=1)
    start_at: str = "2025-01-01T00:00:00+07:00"
    days: int = Field(default=180, ge=1)
    output_dir: str = "data/generated"
    source_profile: str = "paysim-inspired"
    calendar_profile: str = "vietnam-2025-demo"
    campaign_days: dict[str, float] = Field(default_factory=dict)


def load_config(path: Path) -> GenerationConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return GenerationConfig.model_validate(raw)

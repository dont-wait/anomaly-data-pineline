from pathlib import Path

import typer

from anomaly_data_pipeline.config import GenerationConfig, load_config
from anomaly_data_pipeline.analysis import analyze
from anomaly_data_pipeline.generation.pipeline import generate

app = typer.Typer(help="Generate deterministic synthetic AnomalyBank data and events.")


@app.command()
def generate_data(
    config: Path = typer.Option(Path("configs/base.yaml"), "--config", "-c", help="YAML generation config."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Override output directory."),
    seed: int | None = typer.Option(None, "--seed", help="Override configured seed."),
    customers: int | None = typer.Option(None, "--customers", min=1, help="Override customer count."),
) -> None:
    """Generate entities, chronological domain events, and evaluation labels."""
    settings = load_config(config) if config.exists() else GenerationConfig()
    values = settings.model_dump()
    if output is not None:
        values["output_dir"] = str(output)
    if seed is not None:
        values["seed"] = seed
    if customers is not None:
        values["customers"] = customers
    settings = GenerationConfig.model_validate(values)
    result = generate(settings, Path(settings.output_dir))
    typer.echo(f"Generated {result['customers']} customers, {result['accounts']} accounts, "
               f"{result['transactions']} transactions and {result['events']} events in {settings.output_dir}")


@app.command()
def report(
    data: Path = typer.Option(Path("data/generated"), "--data", help="Directory containing generated JSONL."),
    output: Path = typer.Option(Path("reports"), "--output", "-o", help="Directory for Markdown and CSV analysis."),
) -> None:
    """Summarize field ranges and monthly/calendar transaction traffic."""
    analyze(data, output)
    typer.echo(f"Wrote {output / 'dataset-analysis.md'} and {output / 'monthly-traffic.csv'}")


if __name__ == "__main__":
    app()

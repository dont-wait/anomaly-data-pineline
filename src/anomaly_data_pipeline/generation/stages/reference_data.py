from __future__ import annotations

from typing import Any

from anomaly_data_pipeline.generation.ids import stable_id
from anomaly_data_pipeline.generation.stages.common import PipelineContext


def run(context: PipelineContext, options: dict[str, Any]) -> None:
    context.packages = [{"_id": stable_id(context.config.seed, "loan-package", item["code"]),
                         "package_code": item["code"], "name": item["name"], "min_amount": item["min_amount"],
                         "max_amount": item["max_amount"], "term_options": item["term_options"], "status": "active"}
                        for item in options["packages"]]
    for package in context.packages:
        context.write("loan_packages", package)

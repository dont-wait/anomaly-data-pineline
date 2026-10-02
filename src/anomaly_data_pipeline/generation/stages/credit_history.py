from __future__ import annotations

from typing import Any

from anomaly_data_pipeline.generation.domains.credit import CREDIT_PROFILE
from anomaly_data_pipeline.generation.stages.common import PipelineContext


def run(context: PipelineContext, options: dict[str, Any]) -> None:
    for index, customer in enumerate(context.customers):
        customer["credit_profile"] = CREDIT_PROFILE.build(context, index, options).data
        context.write("customers", customer)
        context.add_event("event-customer", index, aggregate_type="customer", aggregate_id=customer["_id"],
                          event_type="CustomerProfileCreated", occurred_at=context.start, sequence=1, payload=customer)
        context.add_event("event-credit", index, aggregate_type="customer", aggregate_id=customer["_id"],
                          event_type="CreditProfileRecorded", occurred_at=context.start, sequence=2,
                          payload=customer["credit_profile"])

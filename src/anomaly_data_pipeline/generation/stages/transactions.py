from __future__ import annotations

from datetime import timedelta
from typing import Any

from anomaly_data_pipeline.domain.models import Transaction
from anomaly_data_pipeline.generation.domains.transaction import TRANSACTION
from anomaly_data_pipeline.generation.ids import stable_id
from anomaly_data_pipeline.generation.stages.common import PipelineContext


def run(context: PipelineContext, options: dict[str, Any]) -> None:
    config, start = context.config, context.start
    for index, customer in enumerate(context.customers):
        account, loan = context.accounts[index], context.loans[index]
        balance = account["balance"]["current"]
        for n in range(config.transactions_per_customer):
            row = TRANSACTION.build(context, index, options, scratch={
                "customer": customer, "account": account, "balance": balance, "transaction_index": n})
            tx, s = Transaction.model_validate(row.data), row.scratch
            context.write("transactions", tx)
            event = context.add_event(
                "event-tx", f"{index}:{n}", aggregate_type="transaction", aggregate_id=tx.transaction_id,
                event_type="TransactionRejected" if tx.status == "failed" else "TransactionPosted",
                occurred_at=s["occurred"], sequence=n + 1,
                payload={"transaction": tx.model_dump(mode="json"), "balance_before": balance,
                         "balance_after": s["balance_after"],
                         "customer_context": {
                             "credit_score": customer["credit_profile"]["score"],
                             "active_loan": loan["active"] and s["occurred"] >= start + timedelta(days=3),
                             "late_payments": sum(1 for e in loan["events"] if e.event_type == "LoanPaymentPosted"
                                                  and e.occurred_at <= s["occurred"]),
                             "age_band": customer["profile"]["demographics"]["age_band"]}})
            context.write("labels", {"event_id": event.event_id, "transaction_id": tx.transaction_id,
                                     "is_anomaly": s["anomaly"],
                                     "scenario_id": "amount_outlier" if s["anomaly"] else "normal",
                                     "source_profile": config.source_profile})
            balance = s["balance_after"]

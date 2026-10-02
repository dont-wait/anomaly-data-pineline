from __future__ import annotations

from datetime import timedelta
from typing import Any

from anomaly_data_pipeline.domain.models import Event
from anomaly_data_pipeline.generation.domains.loan import LOAN, LOAN_APPLICATION, LOAN_DECISION
from anomaly_data_pipeline.generation.stages.common import PipelineContext


def run(context: PipelineContext, options: dict[str, Any]) -> None:
    for index, customer in enumerate(context.customers):
        loan = build_loan(context, index, customer, context.accounts[index], options)
        context.write("loan_applications", loan["application"])
        if loan["loan"] is not None:
            context.write("loans", loan["loan"])
        context.event_rows.extend(loan["events"])
        context.loans.append(loan)


def build_loan(context: PipelineContext, index: int, customer: dict[str, Any], account: dict[str, Any],
               options: dict[str, Any]) -> dict[str, Any]:
    state = LOAN_DECISION.build(context, index, options, scratch={"customer": customer, "account": account}).scratch
    application = LOAN_APPLICATION.build(context, index, options, scratch=state).data
    state["term_months"] = application["request"]["term_months"]  # shared with the loan document and events
    snapshot = LOAN.build(context, index, options, scratch=state).data if state["approved"] else None
    return {"active": state["active"], "late_payments": state["late"], "application": application,
            "loan": snapshot, "events": loan_events(context, index, state, snapshot)}


def loan_events(context: PipelineContext, index: int, s: dict[str, Any], snapshot: dict[str, Any] | None) -> list[Event]:
    start, make = context.start, context.make_event
    events = [
        make("event-loan-application", index, aggregate_type="loan_application", aggregate_id=s["app_id"],
             event_type="LoanApplicationSubmitted", occurred_at=start, sequence=1,
             payload={"application_no": f"APP{context.config.seed % 100000}{index:06d}",
                      "customer_id": s["customer"]["_id"], "loan_package": s["package"],
                      "requested_amount": s["requested_amount"], "status": s["status"]}),
        make("event-loan-result", index, aggregate_type="loan_application", aggregate_id=s["app_id"],
             event_type="LoanDecisionRecorded", occurred_at=start + timedelta(days=2), sequence=2,
             payload={"status": s["status"], "loan_id": s["loan_id"] if s["approved"] else None}),
    ]
    if snapshot is None:
        return events
    events.append(make("event-loan-disbursed", index, aggregate_type="loan", aggregate_id=s["loan_id"],
                       event_type="LoanDisbursed", occurred_at=start + timedelta(days=3), sequence=1,
                       payload={"loan_id": s["loan_id"], "application_id": s["app_id"],
                                "customer_id": s["customer"]["_id"], "disbursement_account_id": s["account"]["_id"],
                                "principal": s["principal"], "outstanding_principal": s["outstanding_principal"],
                                "term_months": s["term_months"], "active": s["active"]}))
    events.extend(
        make("event-loan-payment", f"{index}:{n}", aggregate_type="loan", aggregate_id=s["loan_id"],
             event_type="LoanPaymentPosted", occurred_at=start + timedelta(days=35 * (n + 1)), sequence=n + 2,
             payload={"loan_id": s["loan_id"], "installment_no": n + 1, "status": "late",
                      "principal_amount": 2_000_000, "interest_amount": 250_000})
        for n in range(s["late"]))
    return events

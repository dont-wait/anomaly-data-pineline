from __future__ import annotations

from typing import Any

from anomaly_data_pipeline.domain.models import Account
from anomaly_data_pipeline.generation.domains.account import ACCOUNT
from anomaly_data_pipeline.generation.domains.customer import CUSTOMER
from anomaly_data_pipeline.generation.stages.common import PipelineContext


def run(context: PipelineContext, options: dict[str, Any]) -> None:
    for index in range(context.config.customers):
        customer = CUSTOMER.build(context, index, options).data
        account_row = ACCOUNT.build(context, index, options, scratch={"customer": customer})
        account = Account.model_validate(account_row.data)
        context.customers.append(customer)
        context.accounts.append(account.model_dump(mode="json", by_alias=True))
        context.write("accounts", account)
        context.add_event("event-account", index, aggregate_type="account", aggregate_id=account.id,
                          event_type="AccountOpened", occurred_at=context.start, sequence=1,
                          payload={"account_id": account.id, "customer_id": customer["_id"],
                                   "account_no": account.account_no, "opening_balance": account.balance["current"]})

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Customer(Record):
    id: str = Field(alias="_id")
    customer_code: str
    profile: dict[str, Any]
    identity: dict[str, Any]
    credit_profile: dict[str, Any]
    kyc_status: str
    status: str
    created_at: datetime
    updated_at: datetime


class Account(Record):
    id: str = Field(alias="_id")
    account_no: str
    customer_id: str
    type: str
    currency: str = "VND"
    balance: dict[str, Decimal]
    status: str
    version: int
    created_at: datetime


class Transaction(Record):
    transaction_id: str
    source: dict[str, Any]
    destination: dict[str, Any]
    amount: Decimal
    currency: str = "VND"
    type: str
    channel: str
    status: str
    risk: dict[str, Any]
    idempotency_key: str
    created_at: datetime
    posted_at: datetime


class Event(Record):
    event_id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    schema_version: int = 1
    occurred_at: datetime
    sequence: int
    payload: dict[str, Any]
    # Ground-truth labels are an evaluation sidecar, never sent to detector input.
    labels: dict[str, Any] | None = None


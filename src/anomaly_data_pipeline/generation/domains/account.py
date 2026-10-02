from __future__ import annotations

from anomaly_data_pipeline.generation.fields import FieldSet, Row
from anomaly_data_pipeline.generation.ids import stable_id

ACCOUNT = FieldSet("account")


@ACCOUNT.field("_id")
def _id(r: Row): return stable_id(r.seed, "account", r.index)

@ACCOUNT.field("balance.current")
def opening_balance(r: Row): return r.rng.randrange(2, 200) * 1_000_000

@ACCOUNT.field("account_no")
def account_no(r: Row): return f"{r.rng.randrange(10**11, 10**12)}"

@ACCOUNT.field("customer_id")
def customer_id(r: Row): return r.scratch["customer"]["_id"]

@ACCOUNT.field("type")
def type_(r: Row): return "payment"

@ACCOUNT.field("status")
def status(r: Row): return "active"

@ACCOUNT.field("version")
def version(r: Row): return 0

@ACCOUNT.field("created_at")
def created_at(r: Row): return r.start

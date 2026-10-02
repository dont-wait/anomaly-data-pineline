from __future__ import annotations

from datetime import datetime, timedelta

from anomaly_data_pipeline.generation.fields import FieldSet, Row
from anomaly_data_pipeline.generation.ids import stable_id

# Scratch state in: customer, account, balance, transaction_index. Out: balance_after.
TRANSACTION = FieldSet("transaction")


def _key(r: Row) -> str:
    return f"{r.index}:{r.scratch['transaction_index']}"


# --- scratch state (order = rng draw order) -----------------------------------
@TRANSACTION.field("anomaly", scratch=True)
def anomaly(r: Row): return r.rng.random() < r.ctx.config.anomaly_rate

@TRANSACTION.field("tx_type", scratch=True)
def tx_type(r: Row):
    if r.scratch["anomaly"]:
        return r.opts["anomaly_type"]
    if r.scratch["balance"] == 0:
        return "CASH_IN"
    return r.rng.choices(r.opts["types"], weights=r.opts["type_weights"])[0]

@TRANSACTION.field("day", scratch=True)
def day(r: Row): return r.rng.choices(r.ctx.simulation_days, weights=r.ctx.date_weights, k=1)[0]

@TRANSACTION.field("occurred", scratch=True)
def occurred(r: Row):
    selected_day = r.scratch["day"][0]
    return (datetime.combine(selected_day, datetime.min.time(), tzinfo=r.start.tzinfo)
            + timedelta(seconds=r.rng.randrange(86400)))

@TRANSACTION.field("raw_amount", scratch=True)
def raw_amount(r: Row):
    o, balance = r.opts, r.scratch["balance"]
    if r.scratch["anomaly"]:
        return r.rng.randrange(o["anomaly_min_amount"] // 1_000_000, o["anomaly_max_amount"] // 1_000_000) * 1_000_000
    amount = r.rng.randrange(o["normal_min_amount"], o["normal_max_amount"])
    return amount if r.scratch["tx_type"] == "CASH_IN" else min(amount, balance)

@TRANSACTION.field("tx_status", scratch=True)
def tx_status(r: Row): return "failed" if r.scratch["anomaly"] and r.scratch["raw_amount"] > r.scratch["balance"] else "success"

@TRANSACTION.field("balance_after", scratch=True)
def balance_after(r: Row):
    balance, amount = r.scratch["balance"], int(r.scratch["raw_amount"])
    if r.scratch["tx_status"] == "failed":
        return balance
    return balance + amount if r.scratch["tx_type"] == "CASH_IN" else balance - amount


# --- emitted document ---------------------------------------------------------
@TRANSACTION.field("transaction_id")
def transaction_id(r: Row): return stable_id(r.seed, "transaction", _key(r))

@TRANSACTION.field("source.account_id")
def source_account(r: Row): return r.scratch["account"]["_id"]

@TRANSACTION.field("source.customer_id")
def source_customer(r: Row): return r.scratch["customer"]["_id"]

@TRANSACTION.field("destination.type")
def destination_type(r: Row): return "merchant" if r.scratch["tx_type"] == "PAYMENT" else "account"

@TRANSACTION.field("destination.account_id")
def destination_account(r: Row): return stable_id(r.seed, "merchant-or-account", _key(r))

@TRANSACTION.field("amount")
def amount(r: Row): return r.scratch["raw_amount"]

@TRANSACTION.field("type")
def type_(r: Row): return r.scratch["tx_type"]

@TRANSACTION.field("channel")
def channel(r: Row): return r.rng.choice(r.opts["channels"])

@TRANSACTION.field("status")
def status(r: Row): return r.scratch["tx_status"]

@TRANSACTION.field("risk.score")
def risk_score(r: Row): return 0.91 if r.scratch["anomaly"] else round(r.rng.uniform(0.01, 0.35), 3)

@TRANSACTION.field("risk.decision")
def risk_decision(r: Row): return "review" if r.scratch["anomaly"] else "allow"

@TRANSACTION.field("calendar_context.tags")
def tags(r: Row): return r.scratch["day"][1]

@TRANSACTION.field("calendar_context.campaign")
def campaign(r: Row): return any(t.startswith("campaign_") for t in r.get("calendar_context.tags"))

@TRANSACTION.field("calendar_context.holiday")
def holiday(r: Row): return any(t in r.opts["holiday_tags"] for t in r.get("calendar_context.tags"))

@TRANSACTION.field("idempotency_key")
def idempotency_key(r: Row): return stable_id(r.seed, "idempotency", _key(r))

@TRANSACTION.field("created_at")
def created_at(r: Row): return r.scratch["occurred"]

@TRANSACTION.field("posted_at")
def posted_at(r: Row): return r.scratch["occurred"]

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from anomaly_data_pipeline.domain.models import Transaction
from anomaly_data_pipeline.generation.domains.transaction import TRANSACTION
from anomaly_data_pipeline.generation.ids import stable_id
from anomaly_data_pipeline.generation.transaction_events import emit_transaction_event
from anomaly_data_pipeline.generation.stages.common import PipelineContext


def run(context: PipelineContext, options: dict[str, Any]) -> None:
    if len(context.accounts) < 2 and "TRANSFER" in options["types"]:
        raise ValueError("TRANSFER generation needs at least two accounts")
    if options["fee"] < 0 or options["merchant_count"] < 1 or options["cash_counterparty_count"] < 1:
        raise ValueError("fee must be nonnegative and counterparty pools nonempty")
    if options["preferred_receivers"] < 1 or not 0 <= options["repeat_receiver_probability"] <= 1:
        raise ValueError("Invalid receiver configuration")
    if set(options["channels"]) - {"web", "mobile", "desktop"}:
        raise ValueError("Channels must match Anomaly transfer events")
    rng, config = context.rng, context.config
    merchants = [stable_id(config.seed, "merchant", n) for n in range(options["merchant_count"])]
    cash_nodes = [stable_id(config.seed, "cash-counterparty", n) for n in range(options["cash_counterparty_count"])]
    for kind, pool in [("merchant", merchants), ("cash", cash_nodes)]:
        for node in pool:
            context.write("counterparties", {"_id": node, "type": kind, "created_at": context.start.isoformat()})
    balances = {a["_id"]: a["balance"]["current"] for a in context.accounts}
    profiles, schedule = {}, []
    for index, account in enumerate(context.accounts):
        peers = [a["_id"] for a in context.accounts if a["_id"] != account["_id"]]
        preferred = rng.sample(peers, min(len(peers), options["preferred_receivers"]))
        profiles[index] = (peers, preferred, rng.randrange(options["typical_amount_min"], options["typical_amount_max"]))
        for n in range(config.transactions_per_customer):
            day = rng.choices(context.simulation_days, weights=context.date_weights, k=1)[0]
            occurred = datetime.combine(day[0], datetime.min.time(), tzinfo=context.start.tzinfo) + timedelta(seconds=rng.randrange(86400))
            # Respect a start_at that is not midnight.
            occurred = max(occurred, context.start)
            schedule.append((occurred, index, n, day))
    schedule.sort(key=lambda item: item[:3])
    previous = None
    for occurred, index, n, day in schedule:
        # Unique transaction times make chronological balance replay unambiguous.
        if previous is not None and occurred <= previous:
            occurred = previous + timedelta(microseconds=1)
        previous = occurred
        customer, account = context.customers[index], context.accounts[index]
        peers, preferred, typical = profiles[index]
        pool = preferred if rng.random() < options["repeat_receiver_probability"] else peers
        receiver = rng.choice(pool) if pool else cash_nodes[0]
        source = account["_id"]
        row = TRANSACTION.build(context, index, options, scratch={
            "customer": customer, "account": account, "balance": balances[source],
            "transaction_index": n, "occurred": occurred, "day": day,
            "typical_amount": typical, "destination_type": "account", "destination_id": receiver})
        tx_type = row.data["type"]
        if tx_type in {"PAYMENT", "DEBIT"}:
            row.data["destination"] = {"type": "merchant", "account_id": rng.choice(merchants)}
        elif tx_type in {"CASH_IN", "CASH_OUT"}:
            row.data["destination"] = {"type": "cash", "account_id": rng.choice(cash_nodes)}
        tx = Transaction.model_validate(row.data)
        context.write("transactions", tx)
        destination = tx.destination["account_id"]
        before, after = balances[source], row.scratch["balance_after"]
        # Score the request before any balance mutation or terminal status exists.
        request = {"sourceAccountId": source, "destinationAccountId": destination,
                   "amount": tx.amount, "fee": tx.fee, "currency": tx.currency,
                   "channel": tx.channel, "status": "awaiting_otp" if tx_type == "TRANSFER" else "requested"}
        if tx_type == "TRANSFER":
            request_type = "TransferCreated"
        else:
            request_type = "TransactionRequested"
            request["transactionType"] = tx_type
        created = emit_transaction_event(context, tx, request_type, 1, request)
        result = dict(request, status="success" if tx.status == "success" else "cancelled" if tx_type == "TRANSFER" else "failed")
        result.update(sourceBalanceBefore=before, sourceBalanceAfter=after)
        if tx_type == "TRANSFER":
            dest_before = balances[destination]
            dest_after = dest_before + tx.amount if tx.status == "success" else dest_before
            result.update(destinationBalanceBefore=dest_before, destinationBalanceAfter=dest_after)
            balances[destination] = dest_after
            terminal = "TransferCompleted" if tx.status == "success" else "TransferCancelled"
        else:
            terminal = "TransactionPosted" if tx.status == "success" else "TransactionRejected"
        emit_transaction_event(context, tx, terminal, 2, result)
        balances[source] = after
        context.write("labels", {"event_id": created.event_id, "transaction_id": tx.transaction_id,
                                 "is_anomaly": row.scratch["anomaly"],
                                 "scenario_id": "amount_outlier" if row.scratch["anomaly"] else "normal",
                                 "source_profile": config.source_profile})

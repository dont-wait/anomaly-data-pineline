from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from anomaly_data_pipeline.domain.models import Transaction
from anomaly_data_pipeline.generation.domains.transaction import TRANSACTION
from anomaly_data_pipeline.generation.calendar import calendar_tags
from anomaly_data_pipeline.generation.behavior import build_profiles, channel, validate_options
from anomaly_data_pipeline.generation.scenarios import schedule
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
    validate_options(options)
    rng, config = context.rng, context.config
    merchants = [stable_id(config.seed, "merchant", n) for n in range(options["merchant_count"])]
    cash_nodes = [stable_id(config.seed, "cash-counterparty", n) for n in range(options["cash_counterparty_count"])]
    for kind, pool in [("merchant", merchants), ("cash", cash_nodes)]:
        for node in pool:
            context.write("counterparties", {"_id": node, "type": kind, "created_at": context.start.isoformat()})
    balances = {a["_id"]: a["balance"]["current"] for a in context.accounts}
    profiles = build_profiles(context, options)
    seen = defaultdict(Counter)
    for plan in schedule(context, profiles, options):
        occurred, index, n = plan['occurred'], plan['index'], plan['transaction_index']
        profile = profiles[index]
        tags, _ = calendar_tags(occurred.date(), config.campaign_days)
        day = (occurred.date(), tags)
        customer, account = context.customers[index], context.accounts[index]
        source = account['_id']
        row = TRANSACTION.build(context, index, options, scratch={
            "customer": customer, "account": account, "balance": balances[source],
            "transaction_index": n, "occurred": occurred, "day": day,
            "typical_amount": profile['typical_amount'], "destination_type": "account", "destination_id": source,
            "scenario": plan['scenario'], "planned_type": plan.get('tx_type'), "planned_amount": plan.get('amount'),
            "planned_channel": plan.get('forced_channel') or channel(context, profile, options)})
        tx_type = row.data["type"]
        if tx_type == 'TRANSFER':
            pool = profile['peer_ids']
            favorite = profile['favorite_ids']
            destination_type = 'account'
        elif tx_type in {'PAYMENT', 'DEBIT'}:
            pool, favorite, destination_type = merchants, [merchants[profile['merchant']]], 'merchant'
        else:
            pool, favorite, destination_type = cash_nodes, [cash_nodes[profile['cash']]], 'cash'
        if 'receiver' in plan:
            receiver = context.accounts[plan['receiver']]['_id']
        elif plan['scenario'] == 'contextual_amount':
            unseen = [v for v in pool if v not in seen[source] and v not in favorite]
            receiver = rng.choice(unseen or [v for v in pool if v not in favorite] or pool)
        else:
            receiver = rng.choice(favorite if rng.random() < options['repeat_receiver_probability'] else pool)
        row.data['destination'] = {'type': destination_type, 'account_id': receiver}
        seen[source][receiver] += 1
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
                                 "scenario_id": plan["scenario"],
                                 "source_profile": config.source_profile})

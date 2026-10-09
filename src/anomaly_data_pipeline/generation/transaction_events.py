from __future__ import annotations

from uuid import NAMESPACE_OID, uuid5

def emit_transaction_event(context, tx, event_type, sequence, payload):
    # Same deterministic UUID algorithm as Anomaly's transaction.EventID.
    event_id = str(uuid5(NAMESPACE_OID, f"{tx.transaction_id}:{event_type}"))
    event = context.make_event(
        "event-tx", f"{tx.transaction_id}:{event_type}", aggregate_type="transaction",
        aggregate_id=tx.transaction_id, event_type=event_type, sequence=sequence,
        occurred_at=tx.created_at, payload=payload)
    event.event_id = event_id
    context.event_rows.append(event)
    if tx.type == "TRANSFER":
        context.write("transfer_events", {
            "eventId": event_id, "transactionId": tx.transaction_id,
            "eventType": event_type, "schemaVersion": 1, "sequence": sequence,
            "occurredAt": tx.created_at.isoformat(), "payload": payload})
    return event


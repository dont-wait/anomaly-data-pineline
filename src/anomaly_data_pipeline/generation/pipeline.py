from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from mimesis import Generic
from mimesis.locales import Locale

from anomaly_data_pipeline.config import GenerationConfig
from anomaly_data_pipeline.domain.models import Account, Customer, Event, Transaction

NAMESPACE = uuid.UUID("fe5c61e2-89af-4d71-99f0-891c88a6df5b")
PROVINCES = ["HANOI", "HCMC", "DANANG", "CANTHO", "HAIPHONG", "QUANGNINH"]
TX_TYPES = ["TRANSFER", "CASH_OUT", "PAYMENT", "CASH_IN", "DEBIT"]


def stable_id(seed: int, kind: str, index: str | int) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{seed}:{kind}:{index}"))


def generate(config: GenerationConfig, output_dir: Path) -> dict[str, int]:
    rng = random.Random(config.seed)
    # Mimesis is used for locale-aware person fields; the seeded Python RNG owns
    # scenario decisions and amounts so generation order is explicit/reproducible.
    fake = Generic(locale=Locale.EN, seed=config.seed)
    start = datetime.fromisoformat(config.start_at)
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {name: (output_dir / f"{name}.jsonl").open("w", encoding="utf-8")
             for name in ("customers", "accounts", "loan_applications", "loans", "transactions", "events", "labels")}
    event_file = files.pop("events")
    event_rows: list[Event] = []
    counts = {name: 0 for name in (*files, "events")}

    def write(name: str, model: Any) -> None:
        files[name].write(model.model_dump_json(by_alias=True) + "\n")
        counts[name] += 1

    try:
        for ci in range(config.customers):
            customer_id = stable_id(config.seed, "customer", ci)
            account_id = stable_id(config.seed, "account", ci)
            customer_code = f"CUS{config.seed % 100000:05d}{ci:06d}"
            age = rng.randint(19, 75)
            dob = (start - timedelta(days=age * 365 + rng.randrange(365))).date()
            customer = Customer(
                _id=customer_id, customer_code=customer_code,
                profile={"full_name": fake.person.full_name(), "date_of_birth": dob.isoformat(),
                         "phone": f"09{rng.randrange(10**8):08d}", "email": fake.person.email(),
                         "address": {"line": f"{rng.randint(1, 250)} {fake.address.street_name()}",
                                     "province_code": rng.choice(PROVINCES)},
                         "demographics": {"age_band": _age_band(age), "occupation": _occupation(rng),
                                           "monthly_income": rng.randrange(8, 120) * 1_000_000}},
                identity={"type": "national_id", "number": f"0{rng.randrange(10**11):011d}"},
                credit_profile={"score": rng.randint(300, 850), "bad_debt": rng.random() < 0.04,
                                "updated_at": start.isoformat(),
                                "history": _credit_history(rng, start)},
                kyc_status="verified", status="active", created_at=start, updated_at=start,
            )
            opening_balance = rng.randrange(2, 200) * 1_000_000
            account = Account(_id=account_id, account_no=f"{rng.randrange(10**11, 10**12)}",
                              customer_id=customer_id, type="payment", balance={"current": opening_balance},
                              status="active", version=0, created_at=start)
            write("customers", customer)
            write("accounts", account)
            event_rows.append(Event(
                event_id=stable_id(config.seed, "event-customer", ci), aggregate_type="customer",
                aggregate_id=customer_id, event_type="CustomerProfileCreated", occurred_at=start,
                sequence=1, payload=customer.model_dump(mode="json", by_alias=True),
            ))
            event_rows.append(Event(
                event_id=stable_id(config.seed, "event-account", ci), aggregate_type="account",
                aggregate_id=account_id, event_type="AccountOpened", occurred_at=start,
                sequence=1, payload={"account_id": account_id, "customer_id": customer_id,
                                     "account_no": account.account_no, "opening_balance": opening_balance},
            ))
            event_rows.append(Event(
                event_id=stable_id(config.seed, "event-credit", ci), aggregate_type="customer",
                aggregate_id=customer_id, event_type="CreditProfileRecorded", occurred_at=start,
                sequence=2, payload=customer.credit_profile,
            ))
            loan = _loan(rng, config.seed, ci, customer_id, account_id, start)
            write("loan_applications", loan["application"])
            if loan["loan"] is not None:
                write("loans", loan["loan"])
            for event in loan["events"]:
                event_rows.append(event)

            balance = opening_balance
            tx_count = config.transactions_per_customer
            for ti in range(tx_count):
                anomaly = rng.random() < config.anomaly_rate
                tx_type = "CASH_OUT" if anomaly else rng.choices(TX_TYPES, weights=[35, 20, 25, 12, 8])[0]
                day = rng.randrange(config.days)
                occurred = start + timedelta(days=day, seconds=rng.randrange(86400))
                amount = (rng.randrange(8, 60) * 1_000_000 if anomaly else
                          Decimal(rng.randrange(20_000, 5_000_000)).quantize(Decimal("1")))
                amount = Decimal(amount)
                destination_id = stable_id(config.seed, "merchant-or-account", f"{ci}:{ti}")
                before = balance
                if tx_type in {"CASH_IN"}:
                    balance += int(amount)
                else:
                    balance = max(0, balance - int(amount))
                tx_id = stable_id(config.seed, "transaction", f"{ci}:{ti}")
                tx = Transaction(
                    transaction_id=tx_id,
                    source={"account_id": account_id, "customer_id": customer_id},
                    destination={"type": "merchant" if tx_type == "PAYMENT" else "account",
                                 "account_id": destination_id},
                    amount=amount, type=tx_type, channel=rng.choice(["mobile", "web", "branch"]),
                    status="success", risk={"score": 0.91 if anomaly else round(rng.uniform(0.01, 0.35), 3),
                                             "decision": "review" if anomaly else "allow"},
                    idempotency_key=stable_id(config.seed, "idempotency", f"{ci}:{ti}"),
                    created_at=occurred, posted_at=occurred,
                )
                write("transactions", tx)
                event = Event(event_id=stable_id(config.seed, "event-tx", f"{ci}:{ti}"),
                              aggregate_type="transaction", aggregate_id=tx_id,
                              event_type="TransactionPosted", occurred_at=occurred, sequence=ti + 1,
                              payload={"transaction": tx.model_dump(mode="json"), "balance_before": before,
                                       "balance_after": balance,
                                       "customer_context": {"credit_score": customer.credit_profile["score"],
                                                            "active_loan": loan["active"],
                                                            "late_payments": loan["late_payments"],
                                                            "age_band": customer.profile["demographics"]["age_band"]}})
                event_rows.append(event)
                if anomaly:
                    write("labels", {"event_id": event.event_id, "transaction_id": tx_id,
                                      "is_anomaly": True, "scenario_id": "velocity_or_amount_outlier",
                                      "source_profile": config.source_profile})
    finally:
        for file in (*files.values(), event_file):
            file.close()

    # Stable chronological order is required for event replay. Tie-break by
    # aggregate and sequence so files are byte-for-byte deterministic.
    event_rows.sort(key=lambda e: (e.occurred_at, e.aggregate_type, e.aggregate_id, e.sequence, e.event_id))
    with (output_dir / "events.jsonl").open("w", encoding="utf-8") as sorted_event_file:
        for event in event_rows:
            sorted_event_file.write(event.model_dump_json() + "\n")
    counts["events"] = len(event_rows)

    manifest = {"seed": config.seed, "source_profile": config.source_profile,
                "schema_version": 1, "counts": counts,
                "notes": ["Synthetic data; not real people or bank records.",
                          "PaySim-inspired behavior profile; no PaySim labels are exposed to detector events.",
                          "Ground-truth labels are written to labels.jsonl for offline evaluation."]}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return counts


def _age_band(age: int) -> str:
    return "18-24" if age < 25 else "25-34" if age < 35 else "35-44" if age < 45 else "45-59" if age < 60 else "60+"


def _occupation(rng: random.Random) -> str:
    return rng.choice(["employee", "small_business", "self_employed", "public_sector", "student", "retired"])


def _credit_history(rng: random.Random, start: datetime) -> list[dict[str, Any]]:
    score = rng.randint(300, 850)
    rows = []
    for month in range(6):
        month_at = start - timedelta(days=30 * (5 - month))
        score = max(300, min(850, score + rng.randint(-18, 20)))
        rows.append({"as_of": month_at.date().isoformat(), "score": score,
                     "payment_status": rng.choices(["on_time", "late_30", "late_60", "late_90"],
                                                   weights=[88, 7, 3, 2])[0]})
    return rows


def _loan(rng: random.Random, seed: int, index: int, customer_id: str, account_id: str,
          start: datetime) -> dict[str, Any]:
    approved = rng.random() < 0.38
    active = approved and rng.random() < 0.65
    late = rng.choices([0, 1, 2, 3], weights=[78, 13, 7, 2])[0] if approved else 0
    package = {"_id": stable_id(seed, "loan-package", index), "package_code": rng.choice(["PERSONAL_12", "PERSONAL_24", "MICRO_6"]),
               "name": "Personal installment loan", "min_amount": 5_000_000, "max_amount": 300_000_000,
               "term_options": [6, 12, 24], "status": "active"}
    app_id = stable_id(seed, "loan-application", index)
    loan_id = stable_id(seed, "loan", index)
    requested_amount = rng.randrange(10, 150) * 1_000_000
    application = {"_id": app_id, "application_no": f"APP{seed % 100000}{index:06d}",
                   "customer_id": customer_id, "loan_package_id": package["_id"],
                   "request": {"amount": requested_amount, "term_months": rng.choice([6, 12, 24])},
                   "assessment": {"credit_score": rng.randint(300, 850), "decision": "approved" if approved else "rejected"},
                   "status": "approved" if approved else "rejected", "created_at": start.isoformat()}
    principal = rng.randrange(10, 150) * 1_000_000 if approved else 0
    loan_snapshot = ({"loan_no": f"LN{seed % 100000}{index:06d}", "application_id": app_id,
                      "customer_id": customer_id, "disbursement_account_id": account_id,
                      "principal": principal, "outstanding_principal": principal if active else 0,
                      "interest_rate": round(rng.uniform(0.08, 0.24), 4), "term_months": 12,
                      "status": "active" if active else "closed", "start_date": (start + timedelta(days=3)).date().isoformat()}
                     if approved else None)
    events = [Event(event_id=stable_id(seed, "event-loan-application", index), aggregate_type="loan_application",
                    aggregate_id=app_id, event_type="LoanApplicationSubmitted", occurred_at=start,
                    sequence=1, payload={"application_no": f"APP{seed % 100000}{index:06d}",
                                         "customer_id": customer_id, "loan_package": package,
                                         "requested_amount": requested_amount,
                                         "status": "approved" if approved else "rejected"}),
              Event(event_id=stable_id(seed, "event-loan-result", index), aggregate_type="loan_application",
                    aggregate_id=app_id, event_type="LoanDecisionRecorded", occurred_at=start + timedelta(days=2),
                    sequence=2, payload={"status": "approved" if approved else "rejected", "loan_id": loan_id if approved else None})]
    if approved:
        events.append(Event(event_id=stable_id(seed, "event-loan-disbursed", index), aggregate_type="loan",
                            aggregate_id=loan_id, event_type="LoanDisbursed", occurred_at=start + timedelta(days=3),
                            sequence=1, payload={"loan_id": loan_id, "application_id": app_id,
                                                 "customer_id": customer_id, "disbursement_account_id": account_id,
                                                 "principal": principal,
                                                 "outstanding_principal": principal if active else 0,
                                                 "term_months": rng.choice([6, 12, 24]), "active": active}))
        for n in range(late):
            events.append(Event(event_id=stable_id(seed, "event-loan-payment", f"{index}:{n}"), aggregate_type="loan",
                                aggregate_id=loan_id, event_type="LoanPaymentPosted", occurred_at=start + timedelta(days=35 * (n + 1)),
                                sequence=n + 2, payload={"loan_id": loan_id, "installment_no": n + 1,
                                                        "status": "late", "principal_amount": 2_000_000,
                                                        "interest_amount": 250_000}))
    return {"active": active, "late_payments": late, "events": events,
            "application": application, "loan": loan_snapshot}

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from anomaly_data_pipeline.generation.calendar import days_in_range


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def analyze(data_dir: Path, report_dir: Path) -> None:
    customers = read_jsonl(data_dir / "customers.jsonl")
    accounts = read_jsonl(data_dir / "accounts.jsonl")
    loan_packages = read_jsonl(data_dir / "loan_packages.jsonl") if (data_dir / "loan_packages.jsonl").exists() else []
    loans = read_jsonl(data_dir / "loans.jsonl") if (data_dir / "loans.jsonl").exists() else []
    applications = read_jsonl(data_dir / "loan_applications.jsonl") if (data_dir / "loan_applications.jsonl").exists() else []
    transactions = read_jsonl(data_dir / "transactions.jsonl")
    labels = {row["transaction_id"]: row for row in read_jsonl(data_dir / "labels.jsonl")}
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    report_dir.mkdir(parents=True, exist_ok=True)

    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for tx in transactions:
        by_month[tx["created_at"][:7]].append(tx)
    month_rows = []
    prev_daily = None
    for month, rows in sorted(by_month.items()):
        # Use actual calendar month length, including months at partial simulation boundaries.
        import calendar
        day_count = calendar.monthrange(int(month[:4]), int(month[5:7]))[1]
        tx_count = len(rows)
        amount_sum = sum(int(row["amount"]) for row in rows)
        daily = tx_count / day_count
        delta = "—" if prev_daily is None else _pct(daily, prev_daily)
        month_rows.append((month, tx_count, f"{daily:.2f}", f"{amount_sum:.0f}", delta,
                           sum(bool(labels[row["transaction_id"]]["is_anomaly"]) for row in rows)))
        prev_daily = daily

    daily_by_class: dict[str, Counter[str]] = defaultdict(Counter)
    amount_by_class: dict[str, Counter[str]] = defaultdict(Counter)
    for day, tags, _weight in days_in_range(date.fromisoformat(manifest["start_at"][:10]),
                                            manifest["days"], manifest["campaign_days"]):
        for tag in tags:
            daily_by_class[tag][day.isoformat()] = 0
            amount_by_class[tag][day.isoformat()] = 0
    for tx in transactions:
        tags = tx.get("calendar_context", {}).get("tags", ["unknown"])
        day = tx["created_at"][:10]
        for tag in tags:
            daily_by_class[tag][day] += 1
            amount_by_class[tag][day] += int(tx["amount"])
    regular_rates = [count for day, count in daily_by_class["regular"].items()]
    regular_mean = statistics.mean(regular_rates) if regular_rates else 0
    class_rows = []
    for tag, per_day in sorted(daily_by_class.items()):
        mean = statistics.mean(per_day.values())
        mean_amount = statistics.mean(amount_by_class[tag].values())
        regular_amount_mean = statistics.mean(amount_by_class["regular"].values()) if amount_by_class["regular"] else 0
        class_rows.append((tag, len(per_day), f"{mean:.2f}", _pct(mean, regular_mean),
                           f"{mean_amount:.0f}", _pct(mean_amount, regular_amount_mean)))

    field_rows = _field_ranges(customers, accounts, loan_packages, applications, loans, transactions,
                               date.fromisoformat(manifest["start_at"][:10]))
    lines = ["# Synthetic dataset analysis", "", f"- Seed: `{manifest['seed']}`",
             f"- Period: `{manifest['start_at'][:10]}` through `{manifest['end_date_exclusive']}` (end date exclusive)",
             f"- Profile: `{manifest['source_profile']}`; schema version `{manifest['schema_version']}`",
             "- Campaign/holiday multipliers are synthetic assumptions, not observed bank or retail data.", "",
             "## Generated volume", "", "| Entity / stream | Rows |", "|---|---:|"]
    for name, count in manifest["counts"].items():
        lines.append(f"| {name} | {count:,} |")
    anomalous_count = sum(bool(row["is_anomaly"]) for row in labels.values())
    lines.append(f"\nGround-truth anomaly labels: **{anomalous_count:,}/{len(labels):,} ({anomalous_count / len(labels) * 100:.2f}%)**.")
    lines += ["", "## Field ranges", "", "| Entity.field | Type | Min / observed values | Max / observed values |", "|---|---|---:|---:|"]
    lines.extend(f"| `{name}` | {kind} | {minimum} | {maximum} |" for name, kind, minimum, maximum in field_rows)
    lines += ["", "## Monthly transaction traffic", "", "Monthly count and amount totals; daily average adjusts for month length. Delta compares daily average with previous month.",
              "", "| Month | Transactions | Avg/day | Amount total (VND) | Avg/day vs previous | Anomalies |", "|---|---:|---:|---:|---:|---:|"]
    lines.extend("| " + " | ".join(map(str, row)) + " |" for row in month_rows)
    lines += ["", "## Special-day traffic vs regular days", "", "Rate compares average daily transactions and amount on tagged dates with regular dates. A date with overlapping tags contributes to each tag.",
              "", "| Calendar tag | Dates | Transactions/date | Count vs regular | Amount/day (VND) | Amount vs regular |", "|---|---:|---:|---:|---:|---:|"]
    lines.extend("| " + " | ".join(map(str, row)) + " |" for row in class_rows)
    lines += ["", "## Interpretation notes", "",
              "- Exactly configured transactions per customer are distributed over dates using synthetic calendar weights; month-to-month count changes therefore come from calendar-day weighting and month length, not population growth.",
              "- Campaign dates include repeating 5/5, 6/6 and selected double-date sales. Holiday dates use the fixed 2025 Vietnam calendar profile.",
              "- The comparison is descriptive of this generated seed and these assumptions. It is not an empirical estimate of real sale/holiday uplift.", ""]
    (report_dir / "dataset-analysis.md").write_text("\n".join(lines), encoding="utf-8")

    with (report_dir / "monthly-traffic.csv").open("w", encoding="utf-8") as output:
        output.write("month,transactions,avg_per_day,amount_total_vnd,avg_per_day_pct_change,anomalies\n")
        for row in month_rows:
            output.write(",".join(map(str, row)) + "\n")

    dashboard = _dashboard_payload(customers, accounts, loan_packages, applications, loans,
                                   transactions, labels, manifest, month_rows, class_rows)
    (report_dir / "dashboard.json").write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")


def _pct(current: float, previous: float) -> str:
    if previous == 0:
        return "n/a" if current == 0 else "+∞"
    value = (current - previous) / previous * 100
    return f"{value:+.1f}%"


def _dashboard_payload(customers: list[dict[str, Any]], accounts: list[dict[str, Any]],
                       loan_packages: list[dict[str, Any]], applications: list[dict[str, Any]],
                       loans: list[dict[str, Any]], transactions: list[dict[str, Any]],
                       labels: dict[str, dict[str, Any]], manifest: dict[str, Any],
                       month_rows: list[tuple[Any, ...]], class_rows: list[tuple[Any, ...]]) -> dict[str, Any]:
    anomaly_count = sum(bool(row["is_anomaly"]) for row in labels.values())
    fields: list[dict[str, Any]] = []

    def add_range(name: str, values: list[int | float], unit: str = "") -> None:
        if values:
            fields.append({"field": name, "kind": "range", "min": min(values), "max": max(values), "unit": unit})

    add_range("Age at simulation start", [(date.fromisoformat(manifest["start_at"][:10]) - date.fromisoformat(r["profile"]["date_of_birth"])).days // 365 for r in customers], "years")
    add_range("Monthly income", [r["profile"]["demographics"]["monthly_income"] for r in customers], "VND")
    add_range("Credit score", [r["credit_profile"]["score"] for r in customers], "points")
    add_range("Credit history score", [p["score"] for r in customers for p in r["credit_profile"]["history"]], "points")
    add_range("Opening account balance", [r["balance"]["current"] for r in accounts], "VND")
    add_range("Loan request", [r["request"]["amount"] for r in applications], "VND")
    add_range("Loan term", [r["request"]["term_months"] for r in applications], "months")
    add_range("Loan principal", [r["principal"] for r in loans], "VND")
    add_range("Outstanding principal", [r["outstanding_principal"] for r in loans], "VND")
    add_range("Loan interest rate", [r["interest_rate"] * 100 for r in loans], "%/year")
    add_range("Transaction amount", [int(r["amount"]) for r in transactions], "VND")

    customer_by_id = {row["_id"]: row for row in customers}
    account_by_id = {row["_id"]: row for row in accounts}
    monthly_field_values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for tx in transactions:
        month = tx["created_at"][:7]
        customer = customer_by_id.get(tx.get("source", {}).get("customer_id"))
        account = account_by_id.get(tx.get("source", {}).get("account_id"))
        values: dict[str, float] = {
            "Transaction amount": float(tx["amount"]),
        }
        if customer:
            values.update({
                "Monthly income": float(customer["profile"]["demographics"]["monthly_income"]),
                "Credit score": float(customer["credit_profile"]["score"]),
                "Age at simulation start": float((date.fromisoformat(manifest["start_at"][:10]) - date.fromisoformat(customer["profile"]["date_of_birth"])).days // 365),
            })
        if account:
            values["Opening account balance"] = float(account["balance"]["current"])
        for field, value in values.items():
            monthly_field_values[field][month].append(value)
    field_histograms = []
    for field, by_month_values in monthly_field_values.items():
        all_values = [value for values in by_month_values.values() for value in values]
        minimum, maximum = min(all_values), max(all_values)
        bucket_count = min(8, max(1, len(set(all_values))))
        if minimum == maximum:
            edges = [minimum, maximum]
        else:
            edges = [minimum + (maximum - minimum) * index / bucket_count for index in range(bucket_count + 1)]
        bins = []
        for index in range(bucket_count):
            lower, upper = edges[index], edges[index + 1]
            bins.append({"min": lower, "max": upper, "count": 0, "months": {}})
        for month, values in sorted(by_month_values.items()):
            counts = [0] * bucket_count
            for value in values:
                bucket = bucket_count - 1 if value == maximum else min(bucket_count - 1, int((value - minimum) / (maximum - minimum) * bucket_count)) if maximum != minimum else 0
                counts[bucket] += 1
            for index, count in enumerate(counts):
                bins[index]["count"] += count
                bins[index]["months"][month] = count
        field_histograms.append({"field": field, "min": minimum, "max": maximum, "bins": bins})

    categorical_sources = {
        "Transaction type": [r["type"] for r in transactions],
        "Transaction status": [r["status"] for r in transactions],
        "Transaction channel": [r["channel"] for r in transactions],
        "Province": [r["profile"]["address"]["province_code"] for r in customers],
        "Occupation": [r["profile"]["demographics"]["occupation"] for r in customers],
        "Age band": [r["profile"]["demographics"]["age_band"] for r in customers],
        "Credit payment status": [p["payment_status"] for r in customers for p in r["credit_profile"]["history"]],
        "Loan package": [r["package_code"] for r in loan_packages],
        "Loan application status": [r["status"] for r in applications],
        "Loan status": [r["status"] for r in loans],
        "Calendar tags": [tag for r in transactions for tag in r["calendar_context"]["tags"]],
    }
    categories = [{"name": name, "values": [{"label": label, "count": count}
                                              for label, count in Counter(values).most_common()]}
                  for name, values in categorical_sources.items()]

    monthly = [{"month": row[0], "transactions": row[1], "dailyAverage": float(row[2]),
                "amountTotalVnd": int(row[3]),
                "dailyChangePct": None if row[4] == "—" else float(str(row[4]).rstrip("%")),
                "anomalies": row[5]} for row in month_rows]
    special_days = [{"tag": row[0], "days": row[1], "transactionsPerDay": float(row[2]),
                     "transactionChangePct": _parse_percent(row[3]), "amountPerDayVnd": int(row[4]),
                     "amountChangePct": _parse_percent(row[5])} for row in class_rows]
    total_amount = sum(int(row["amount"]) for row in transactions)
    return {
        "metadata": {"seed": manifest["seed"], "sourceProfile": manifest["source_profile"],
                     "calendarProfile": manifest["calendar_profile"], "startDate": manifest["start_at"][:10],
                     "endDate": (date.fromisoformat(manifest["end_date_exclusive"]) - timedelta(days=1)).isoformat(),
                     "days": manifest["days"]},
        "summary": {"customers": len(customers), "accounts": len(accounts), "transactions": len(transactions),
                    "events": manifest["counts"]["events"], "loans": len(loans),
                    "approvedApplications": sum(r["status"] == "approved" for r in applications),
                    "anomalies": anomaly_count,
                    "anomalyRatePct": round(anomaly_count / len(transactions) * 100, 2) if transactions else 0,
                    "amountTotalVnd": total_amount},
        "monthlyTraffic": monthly,
        "specialDayTraffic": special_days,
        "fieldRanges": fields,
        "fieldHistograms": field_histograms,
        "categories": categories,
    }


def _parse_percent(value: str) -> float | None:
    if value == "n/a":
        return None
    return float(value.rstrip("%"))


def _field_ranges(customers: list[dict[str, Any]], accounts: list[dict[str, Any]],
                  loan_packages: list[dict[str, Any]],
                  applications: list[dict[str, Any]], loans: list[dict[str, Any]],
                  transactions: list[dict[str, Any]], as_of: date) -> list[tuple[str, str, str, str]]:
    age_years = [(as_of - date.fromisoformat(row["profile"]["date_of_birth"])).days // 365 for row in customers]
    credit_history_scores = [point["score"] for row in customers for point in row["credit_profile"]["history"]]
    transaction_dates = [row["created_at"][:10] for row in transactions]
    numeric: list[tuple[str, list[Any]]] = [
        ("customers.profile.age_years_at_start", age_years),
        ("customers.profile.demographics.monthly_income", [r["profile"]["demographics"]["monthly_income"] for r in customers]),
        ("customers.credit_profile.score", [r["credit_profile"]["score"] for r in customers]),
        ("customers.credit_profile.history.score", credit_history_scores),
        ("customers.credit_profile.bad_debt", [r["credit_profile"]["bad_debt"] for r in customers]),
        ("accounts.balance.current", [r["balance"]["current"] for r in accounts]),
        ("loan_applications.request.amount", [r["request"]["amount"] for r in applications]),
        ("loan_applications.request.term_months", [r["request"]["term_months"] for r in applications]),
        ("loans.principal", [r["principal"] for r in loans]),
        ("loans.outstanding_principal", [r["outstanding_principal"] for r in loans]),
        ("loans.interest_rate", [r["interest_rate"] for r in loans]),
        ("loans.term_months", [r["term_months"] for r in loans]),
        ("transactions.amount", [int(r["amount"]) for r in transactions]),
    ]
    result = []
    for name, values in numeric:
        result.append((name, "boolean" if values and isinstance(values[0], bool) else "numeric",
                       str(min(values)) if values else "—", str(max(values)) if values else "—"))
    for name, values in [
        ("customers.profile.demographics.age_band", [r["profile"]["demographics"]["age_band"] for r in customers]),
        ("customers.profile.demographics.occupation", [r["profile"]["demographics"]["occupation"] for r in customers]),
        ("customers.profile.address.province_code", [r["profile"]["address"]["province_code"] for r in customers]),
        ("transactions.type", [r["type"] for r in transactions]),
        ("transactions.channel", [r["channel"] for r in transactions]),
        ("transactions.status", [r["status"] for r in transactions]),
        ("transactions.calendar_context.tags", [tag for r in transactions for tag in r["calendar_context"]["tags"]]),
        ("customers.credit_profile.history.payment_status", [point["payment_status"] for row in customers for point in row["credit_profile"]["history"]]),
        ("loan_applications.status", [r["status"] for r in applications]),
        ("loan_packages.package_code", [r["package_code"] for r in loan_packages]),
        ("loans.status", [r["status"] for r in loans]),
    ]:
        counts = Counter(values)
        result.append((name, "categorical", f"{len(counts)} unique; {dict(counts.most_common(8))}", "—"))
    result.append(("transactions.created_at", "date range",
                   min(transaction_dates) if transaction_dates else "—",
                   max(transaction_dates) if transaction_dates else "—"))
    return result

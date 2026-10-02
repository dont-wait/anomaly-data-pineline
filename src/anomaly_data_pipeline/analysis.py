from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from datetime import date
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


def _pct(current: float, previous: float) -> str:
    if previous == 0:
        return "n/a" if current == 0 else "+∞"
    value = (current - previous) / previous * 100
    return f"{value:+.1f}%"


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
        ("transactions.risk.score", [r["risk"]["score"] for r in transactions]),
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

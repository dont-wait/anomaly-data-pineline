# Synthetic dataset analysis

- Seed: `20261002`
- Period: `2025-01-01` through `2025-07-01` (end date exclusive)
- Profile: `paysim-inspired`; schema version `1`
- Campaign/holiday multipliers are synthetic assumptions, not observed bank or retail data.

## Generated volume

| Entity / stream | Rows |
|---|---:|
| customers | 100 |
| accounts | 100 |
| loan_packages | 3 |
| loan_applications | 100 |
| loans | 38 |
| transactions | 2,500 |
| labels | 2,500 |
| events | 3,054 |

Ground-truth anomaly labels: **47/2,500 (1.88%)**.

## Field ranges

| Entity.field | Type | Min / observed values | Max / observed values |
|---|---|---:|---:|
| `customers.profile.age_years_at_start` | numeric | 19 | 75 |
| `customers.profile.demographics.monthly_income` | numeric | 9000000 | 119000000 |
| `customers.credit_profile.score` | numeric | 305 | 850 |
| `customers.credit_profile.history.score` | numeric | 300 | 850 |
| `customers.credit_profile.bad_debt` | boolean | False | True |
| `accounts.balance.current` | numeric | 2000000 | 199000000 |
| `loan_applications.request.amount` | numeric | 1000000 | 149000000 |
| `loan_applications.request.term_months` | numeric | 3 | 24 |
| `loans.principal` | numeric | 1000000 | 149000000 |
| `loans.outstanding_principal` | numeric | 0 | 149000000 |
| `loans.interest_rate` | numeric | 0.0895 | 0.2334 |
| `loans.term_months` | numeric | 3 | 24 |
| `transactions.amount` | numeric | 7792 | 59000000 |
| `transactions.risk.score` | numeric | 0.01 | 0.91 |
| `customers.profile.demographics.age_band` | categorical | 5 unique; {'60+': 30, '45-59': 27, '25-34': 19, '35-44': 14, '18-24': 10} | — |
| `customers.profile.demographics.occupation` | categorical | 6 unique; {'public_sector': 23, 'small_business': 18, 'employee': 16, 'student': 16, 'self_employed': 15, 'retired': 12} | — |
| `customers.profile.address.province_code` | categorical | 6 unique; {'HCMC': 20, 'DANANG': 19, 'HAIPHONG': 18, 'HANOI': 17, 'QUANGNINH': 14, 'CANTHO': 12} | — |
| `transactions.type` | categorical | 5 unique; {'TRANSFER': 846, 'PAYMENT': 575, 'CASH_OUT': 489, 'CASH_IN': 384, 'DEBIT': 206} | — |
| `transactions.channel` | categorical | 3 unique; {'web': 858, 'branch': 825, 'mobile': 817} | — |
| `transactions.status` | categorical | 2 unique; {'success': 2479, 'failed': 21} | — |
| `transactions.calendar_context.tags` | categorical | 16 unique; {'regular': 1447, 'payday': 569, 'month_end': 286, 'tet_period': 184, 'holiday_bridge': 48, 'campaign_0505': 43, 'campaign_0202': 34, 'new_year': 30} | — |
| `customers.credit_profile.history.payment_status` | categorical | 4 unique; {'on_time': 528, 'late_30': 37, 'late_60': 24, 'late_90': 11} | — |
| `loan_applications.status` | categorical | 2 unique; {'rejected': 62, 'approved': 38} | — |
| `loan_packages.package_code` | categorical | 3 unique; {'PERSONAL_12': 1, 'PERSONAL_24': 1, 'MICRO_6': 1} | — |
| `loans.status` | categorical | 2 unique; {'active': 27, 'closed': 11} | — |
| `transactions.created_at` | date range | 2025-01-01 | 2025-06-30 |

## Monthly transaction traffic

Monthly count and amount totals; daily average adjusts for month length. Delta compares daily average with previous month.

| Month | Transactions | Avg/day | Amount total (VND) | Avg/day vs previous | Anomalies |
|---|---:|---:|---:|---:|---:|
| 2025-01 | 451 | 14.55 | 1363171531 | — | 9 |
| 2025-02 | 367 | 13.11 | 1151962825 | -9.9% | 8 |
| 2025-03 | 394 | 12.71 | 1166918073 | -3.0% | 8 |
| 2025-04 | 430 | 14.33 | 1319022368 | +12.8% | 8 |
| 2025-05 | 455 | 14.68 | 1409707012 | +2.4% | 7 |
| 2025-06 | 403 | 13.43 | 1143755066 | -8.5% | 7 |

## Special-day traffic vs regular days

Rate compares average daily transactions and amount on tagged dates with regular dates. A date with overlapping tags contributes to each tag.

| Calendar tag | Dates | Transactions/date | Count vs regular | Amount/day (VND) | Amount vs regular |
|---|---:|---:|---:|---:|---:|
| campaign_0101 | 1 | 30.00 | +140.5% | 61357415 | +71.4% |
| campaign_0202 | 1 | 34.00 | +172.6% | 138082696 | +285.8% |
| campaign_0303 | 1 | 21.00 | +68.3% | 97236095 | +171.6% |
| campaign_0404 | 1 | 15.00 | +20.2% | 43946987 | +22.8% |
| campaign_0505 | 1 | 43.00 | +244.7% | 181239779 | +406.3% |
| campaign_0606 | 1 | 27.00 | +116.4% | 56670249 | +58.3% |
| family_day | 1 | 19.00 | +52.3% | 45843450 | +28.1% |
| holiday_bridge | 3 | 16.00 | +28.3% | 48952122 | +36.8% |
| hung_kings | 1 | 14.00 | +12.2% | 22949803 | -35.9% |
| labor_day | 1 | 18.00 | +44.3% | 95135942 | +165.8% |
| month_end | 19 | 15.05 | +20.7% | 44053562 | +23.1% |
| new_year | 1 | 30.00 | +140.5% | 61357415 | +71.4% |
| payday | 36 | 15.81 | +26.7% | 54061389 | +51.0% |
| regular | 116 | 12.47 | +0.0% | 35795284 | +0.0% |
| reunification_day | 1 | 23.00 | +84.4% | 68354517 | +91.0% |
| tet_period | 9 | 20.44 | +63.9% | 71314707 | +99.2% |

## Interpretation notes

- Exactly configured transactions per customer are distributed over dates using synthetic calendar weights; month-to-month count changes therefore come from calendar-day weighting and month length, not population growth.
- Campaign dates include repeating 5/5, 6/6 and selected double-date sales. Holiday dates use the fixed 2025 Vietnam calendar profile.
- The comparison is descriptive of this generated seed and these assumptions. It is not an empirical estimate of real sale/holiday uplift.

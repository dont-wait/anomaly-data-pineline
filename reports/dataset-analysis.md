# Synthetic dataset analysis

- Seed: `20261002`
- Period: `2025-01-01` through `2025-07-01` (end date exclusive)
- Profile: `paysim-inspired`; schema version `2`
- Campaign/holiday multipliers are synthetic assumptions, not observed bank or retail data.

## Generated volume

| Entity / stream | Rows |
|---|---:|
| customers | 1,000 |
| accounts | 1,000 |
| loan_packages | 3 |
| loan_applications | 1,000 |
| loans | 365 |
| transactions | 500,000 |
| labels | 500,000 |
| counterparties | 13 |
| transfer_events | 350,440 |
| events | 1,005,469 |

Ground-truth anomaly labels: **9,975/500,000 (1.99%)**.

## Field ranges

| Entity.field | Type | Min / observed values | Max / observed values |
|---|---|---:|---:|
| `customers.profile.age_years_at_start` | numeric | 19 | 75 |
| `customers.profile.demographics.monthly_income` | numeric | 8000000 | 119000000 |
| `customers.credit_profile.score` | numeric | 300 | 850 |
| `customers.credit_profile.history.score` | numeric | 300 | 850 |
| `customers.credit_profile.bad_debt` | boolean | False | True |
| `accounts.balance.current` | numeric | 2000000 | 199000000 |
| `loan_applications.request.amount` | numeric | 1000000 | 150000000 |
| `loan_applications.request.term_months` | numeric | 3 | 24 |
| `loans.principal` | numeric | 1000000 | 150000000 |
| `loans.outstanding_principal` | numeric | 0 | 150000000 |
| `loans.interest_rate` | numeric | 0.0801 | 0.2389 |
| `loans.term_months` | numeric | 3 | 24 |
| `transactions.amount` | numeric | 10221 | 23870437 |
| `customers.profile.demographics.age_band` | categorical | 5 unique; {'60+': 286, '45-59': 266, '25-34': 175, '35-44': 171, '18-24': 102} | — |
| `customers.profile.demographics.occupation` | categorical | 6 unique; {'retired': 178, 'small_business': 177, 'student': 175, 'employee': 172, 'self_employed': 150, 'public_sector': 148} | — |
| `customers.profile.address.province_code` | categorical | 6 unique; {'HAIPHONG': 182, 'QUANGNINH': 182, 'HANOI': 167, 'DANANG': 158, 'CANTHO': 158, 'HCMC': 153} | — |
| `transactions.type` | categorical | 5 unique; {'TRANSFER': 175220, 'PAYMENT': 124870, 'CASH_OUT': 99695, 'CASH_IN': 60205, 'DEBIT': 40010} | — |
| `transactions.channel` | categorical | 3 unique; {'web': 167072, 'desktop': 166465, 'mobile': 166463} | — |
| `transactions.status` | categorical | 2 unique; {'success': 321266, 'failed': 178734} | — |
| `transactions.calendar_context.tags` | categorical | 16 unique; {'regular': 288321, 'payday': 111644, 'month_end': 57912, 'tet_period': 38535, 'holiday_bridge': 9345, 'campaign_0505': 7076, 'campaign_0202': 6798, 'campaign_0606': 6535} | — |
| `customers.credit_profile.history.payment_status` | categorical | 4 unique; {'on_time': 5311, 'late_30': 419, 'late_60': 168, 'late_90': 102} | — |
| `loan_applications.status` | categorical | 2 unique; {'rejected': 635, 'approved': 365} | — |
| `loan_packages.package_code` | categorical | 3 unique; {'PERSONAL_12': 1, 'PERSONAL_24': 1, 'MICRO_6': 1} | — |
| `loans.status` | categorical | 2 unique; {'active': 214, 'closed': 151} | — |
| `transactions.created_at` | date range | 2025-01-01 | 2025-06-30 |

## Monthly transaction traffic

Monthly count and amount totals; daily average adjusts for month length. Delta compares daily average with previous month.

| Month | Transactions | Avg/day | Amount total (VND) | Avg/day vs previous | Anomalies |
|---|---:|---:|---:|---:|---:|
| 2025-01 | 92111 | 2971.32 | 188088456193 | — | 1804 |
| 2025-02 | 77562 | 2770.07 | 158684239762 | -6.8% | 1542 |
| 2025-03 | 81937 | 2643.13 | 168885403122 | -4.6% | 1629 |
| 2025-04 | 80155 | 2671.83 | 163954591408 | +1.1% | 1575 |
| 2025-05 | 86551 | 2791.97 | 175748529605 | +4.5% | 1778 |
| 2025-06 | 81684 | 2722.80 | 167982140391 | -2.5% | 1647 |

## Special-day traffic vs regular days

Rate compares average daily transactions and amount on tagged dates with regular dates. A date with overlapping tags contributes to each tag.

| Calendar tag | Dates | Transactions/date | Count vs regular | Amount/day (VND) | Amount vs regular |
|---|---:|---:|---:|---:|---:|
| campaign_0101 | 1 | 6310.00 | +153.9% | 12803166154 | +151.2% |
| campaign_0202 | 1 | 6798.00 | +173.5% | 14092238052 | +176.5% |
| campaign_0303 | 1 | 4532.00 | +82.3% | 9187427419 | +80.2% |
| campaign_0404 | 1 | 4394.00 | +76.8% | 8877568638 | +74.2% |
| campaign_0505 | 1 | 7076.00 | +184.7% | 14163751031 | +177.9% |
| campaign_0606 | 1 | 6535.00 | +162.9% | 13653972896 | +167.9% |
| family_day | 1 | 3426.00 | +37.8% | 6830369954 | +34.0% |
| holiday_bridge | 3 | 3115.00 | +25.3% | 6457748371 | +26.7% |
| hung_kings | 1 | 3115.00 | +25.3% | 6495606407 | +27.4% |
| labor_day | 1 | 3472.00 | +39.7% | 6982167411 | +37.0% |
| month_end | 19 | 3048.00 | +22.6% | 6209056513 | +21.8% |
| new_year | 1 | 6310.00 | +153.9% | 12803166154 | +151.2% |
| payday | 36 | 3101.22 | +24.8% | 6316837301 | +23.9% |
| regular | 116 | 2485.53 | +0.0% | 5097099862 | +0.0% |
| reunification_day | 1 | 3370.00 | +35.6% | 7034143156 | +38.0% |
| tet_period | 9 | 4281.67 | +72.3% | 8635361461 | +69.4% |

## Interpretation notes

- Exactly configured transactions per customer are distributed over dates using synthetic calendar weights; month-to-month count changes therefore come from calendar-day weighting and month length, not population growth.
- Campaign dates include repeating 5/5, 6/6 and selected double-date sales. Holiday dates use the fixed 2025 Vietnam calendar profile.
- The comparison is descriptive of this generated seed and these assumptions. It is not an empirical estimate of real sale/holiday uplift.

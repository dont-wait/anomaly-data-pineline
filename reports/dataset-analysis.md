# Synthetic dataset analysis

- Seed: `20261002`
- Period: `2025-01-01` through `2025-07-01` (end date exclusive)
- Profile: `paysim-inspired`; schema version `2`
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
| counterparties | 13 |
| transfer_events | 1,666 |
| events | 5,544 |

Ground-truth anomaly labels: **40/2,500 (1.60%)**.

## Field ranges

| Entity.field | Type | Min / observed values | Max / observed values |
|---|---|---:|---:|
| `customers.profile.age_years_at_start` | numeric | 19 | 75 |
| `customers.profile.demographics.monthly_income` | numeric | 9000000 | 119000000 |
| `customers.credit_profile.score` | numeric | 300 | 846 |
| `customers.credit_profile.history.score` | numeric | 300 | 850 |
| `customers.credit_profile.bad_debt` | boolean | False | True |
| `accounts.balance.current` | numeric | 2000000 | 192000000 |
| `loan_applications.request.amount` | numeric | 3000000 | 148000000 |
| `loan_applications.request.term_months` | numeric | 3 | 24 |
| `loans.principal` | numeric | 3000000 | 148000000 |
| `loans.outstanding_principal` | numeric | 0 | 148000000 |
| `loans.interest_rate` | numeric | 0.0824 | 0.2329 |
| `loans.term_months` | numeric | 3 | 24 |
| `transactions.amount` | numeric | 39284 | 21348577 |
| `customers.profile.demographics.age_band` | categorical | 5 unique; {'60+': 27, '45-59': 22, '35-44': 21, '25-34': 19, '18-24': 11} | — |
| `customers.profile.demographics.occupation` | categorical | 6 unique; {'employee': 19, 'student': 18, 'self_employed': 16, 'small_business': 16, 'retired': 16, 'public_sector': 15} | — |
| `customers.profile.address.province_code` | categorical | 6 unique; {'QUANGNINH': 24, 'HANOI': 21, 'CANTHO': 19, 'DANANG': 16, 'HCMC': 12, 'HAIPHONG': 8} | — |
| `transactions.type` | categorical | 5 unique; {'TRANSFER': 833, 'PAYMENT': 619, 'CASH_OUT': 491, 'CASH_IN': 352, 'DEBIT': 205} | — |
| `transactions.channel` | categorical | 3 unique; {'desktop': 837, 'mobile': 834, 'web': 829} | — |
| `transactions.status` | categorical | 2 unique; {'success': 2426, 'failed': 74} | — |
| `transactions.calendar_context.tags` | categorical | 16 unique; {'regular': 1392, 'payday': 594, 'month_end': 319, 'tet_period': 185, 'holiday_bridge': 46, 'campaign_0505': 40, 'new_year': 38, 'campaign_0101': 38} | — |
| `customers.credit_profile.history.payment_status` | categorical | 4 unique; {'on_time': 526, 'late_30': 45, 'late_60': 17, 'late_90': 12} | — |
| `loan_applications.status` | categorical | 2 unique; {'rejected': 62, 'approved': 38} | — |
| `loan_packages.package_code` | categorical | 3 unique; {'PERSONAL_12': 1, 'PERSONAL_24': 1, 'MICRO_6': 1} | — |
| `loans.status` | categorical | 2 unique; {'active': 23, 'closed': 15} | — |
| `transactions.created_at` | date range | 2025-01-01 | 2025-06-30 |

## Monthly transaction traffic

Monthly count and amount totals; daily average adjusts for month length. Delta compares daily average with previous month.

| Month | Transactions | Avg/day | Amount total (VND) | Avg/day vs previous | Anomalies |
|---|---:|---:|---:|---:|---:|
| 2025-01 | 456 | 14.71 | 928011777 | — | 5 |
| 2025-02 | 391 | 13.96 | 838917872 | -5.1% | 6 |
| 2025-03 | 428 | 13.81 | 992952685 | -1.1% | 5 |
| 2025-04 | 413 | 13.77 | 940733296 | -0.3% | 13 |
| 2025-05 | 443 | 14.29 | 977861842 | +3.8% | 5 |
| 2025-06 | 369 | 12.30 | 892069243 | -13.9% | 6 |

## Special-day traffic vs regular days

Rate compares average daily transactions and amount on tagged dates with regular dates. A date with overlapping tags contributes to each tag.

| Calendar tag | Dates | Transactions/date | Count vs regular | Amount/day (VND) | Amount vs regular |
|---|---:|---:|---:|---:|---:|
| campaign_0101 | 1 | 38.00 | +216.7% | 78451813 | +173.8% |
| campaign_0202 | 1 | 23.00 | +91.7% | 38116046 | +33.0% |
| campaign_0303 | 1 | 21.00 | +75.0% | 43586219 | +52.1% |
| campaign_0404 | 1 | 23.00 | +91.7% | 56891199 | +98.5% |
| campaign_0505 | 1 | 40.00 | +233.3% | 79964847 | +179.1% |
| campaign_0606 | 1 | 26.00 | +116.7% | 41991284 | +46.5% |
| family_day | 1 | 17.00 | +41.7% | 21132145 | -26.3% |
| holiday_bridge | 3 | 15.33 | +27.8% | 32288888 | +12.7% |
| hung_kings | 1 | 17.00 | +41.7% | 27656000 | -3.5% |
| labor_day | 1 | 20.00 | +66.7% | 36424394 | +27.1% |
| month_end | 19 | 16.79 | +39.9% | 36039603 | +25.8% |
| new_year | 1 | 38.00 | +216.7% | 78451813 | +173.8% |
| payday | 36 | 16.50 | +37.5% | 33156579 | +15.7% |
| regular | 116 | 12.00 | +0.0% | 28653991 | +0.0% |
| reunification_day | 1 | 25.00 | +108.3% | 52143044 | +82.0% |
| tet_period | 9 | 20.56 | +71.3% | 35255054 | +23.0% |

## Interpretation notes

- Exactly configured transactions per customer are distributed over dates using synthetic calendar weights; month-to-month count changes therefore come from calendar-day weighting and month length, not population growth.
- Campaign dates include repeating 5/5, 6/6 and selected double-date sales. Holiday dates use the fixed 2025 Vietnam calendar profile.
- The comparison is descriptive of this generated seed and these assumptions. It is not an empirical estimate of real sale/holiday uplift.

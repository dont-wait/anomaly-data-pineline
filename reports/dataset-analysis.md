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
| counterparties | 40 |
| transfer_events | 303,670 |
| behavior_profiles | 1,000 |
| events | 1,005,469 |

Ground-truth anomaly labels: **10,000/500,000 (2.00%)**.

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
| `transactions.amount` | numeric | 6054 | 119000000 |
| `customers.profile.demographics.age_band` | categorical | 5 unique; {'60+': 286, '45-59': 266, '25-34': 175, '35-44': 171, '18-24': 102} | — |
| `customers.profile.demographics.occupation` | categorical | 6 unique; {'retired': 178, 'small_business': 177, 'student': 175, 'employee': 172, 'self_employed': 150, 'public_sector': 148} | — |
| `customers.profile.address.province_code` | categorical | 6 unique; {'HAIPHONG': 182, 'QUANGNINH': 182, 'HANOI': 167, 'DANANG': 158, 'CANTHO': 158, 'HCMC': 153} | — |
| `transactions.type` | categorical | 5 unique; {'TRANSFER': 151835, 'PAYMENT': 136934, 'CASH_IN': 103796, 'CASH_OUT': 58583, 'DEBIT': 48852} | — |
| `transactions.channel` | categorical | 3 unique; {'mobile': 296206, 'web': 139784, 'desktop': 64010} | — |
| `transactions.status` | categorical | 2 unique; {'success': 499513, 'failed': 487} | — |
| `transactions.calendar_context.tags` | categorical | 16 unique; {'regular': 284291, 'payday': 116394, 'month_end': 57626, 'tet_period': 38762, 'holiday_bridge': 9405, 'campaign_0505': 7355, 'campaign_0202': 6733, 'new_year': 6364} | — |
| `customers.credit_profile.history.payment_status` | categorical | 4 unique; {'on_time': 5311, 'late_30': 419, 'late_60': 168, 'late_90': 102} | — |
| `loan_applications.status` | categorical | 2 unique; {'rejected': 635, 'approved': 365} | — |
| `loan_packages.package_code` | categorical | 3 unique; {'PERSONAL_12': 1, 'PERSONAL_24': 1, 'MICRO_6': 1} | — |
| `loans.status` | categorical | 2 unique; {'active': 214, 'closed': 151} | — |
| `transactions.created_at` | date range | 2025-01-01 | 2025-06-30 |

## Monthly transaction traffic

Monthly count and amount totals; daily average adjusts for month length. Delta compares daily average with previous month.

| Month | Transactions | Avg/day | Amount total (VND) | Avg/day vs previous | Anomalies |
|---|---:|---:|---:|---:|---:|
| 2025-01 | 92598 | 2987.03 | 114389911579 | — | 1916 |
| 2025-02 | 77190 | 2756.79 | 106886749211 | -7.7% | 1637 |
| 2025-03 | 81693 | 2635.26 | 108506410627 | -4.4% | 1449 |
| 2025-04 | 80217 | 2673.90 | 108458814341 | +1.5% | 1597 |
| 2025-05 | 86817 | 2800.55 | 111168369061 | +4.7% | 1759 |
| 2025-06 | 81485 | 2716.17 | 108471146307 | -3.0% | 1642 |

## Special-day traffic vs regular days

Rate compares average daily transactions and amount on tagged dates with regular dates. A date with overlapping tags contributes to each tag.

| Calendar tag | Dates | Transactions/date | Count vs regular | Amount/day (VND) | Amount vs regular |
|---|---:|---:|---:|---:|---:|
| campaign_0101 | 1 | 6364.00 | +159.7% | 12574864657 | +833.4% |
| campaign_0202 | 1 | 6733.00 | +174.7% | 3731407109 | +177.0% |
| campaign_0303 | 1 | 4424.00 | +80.5% | 2445539808 | +81.5% |
| campaign_0404 | 1 | 4311.00 | +75.9% | 2436711752 | +80.9% |
| campaign_0505 | 1 | 7355.00 | +200.1% | 13423680800 | +896.4% |
| campaign_0606 | 1 | 6343.00 | +158.8% | 3530932358 | +162.1% |
| family_day | 1 | 3304.00 | +34.8% | 1901397076 | +41.1% |
| holiday_bridge | 3 | 3135.00 | +27.9% | 1733673286 | +28.7% |
| hung_kings | 1 | 3092.00 | +26.2% | 1658951987 | +23.1% |
| labor_day | 1 | 3555.00 | +45.1% | 11107128836 | +724.4% |
| month_end | 19 | 3032.95 | +23.8% | 1656127258 | +22.9% |
| new_year | 1 | 6364.00 | +159.7% | 12574864657 | +833.4% |
| payday | 36 | 3233.17 | +31.9% | 12422115792 | +822.0% |
| regular | 116 | 2450.78 | +0.0% | 1347246063 | +0.0% |
| reunification_day | 1 | 3343.00 | +36.4% | 1895909438 | +40.7% |
| tet_period | 9 | 4306.89 | +75.7% | 4584928504 | +240.3% |

## Interpretation notes

- Configured total transactions are allocated by customer activity profiles and distributed over weighted calendar dates; counts per account differ. Recurring income is included in the transaction budget, not an invisible balance top-up.
- Campaign dates include repeating 5/5, 6/6 and selected double-date sales. Holiday dates use the fixed 2025 Vietnam calendar profile.
- The comparison is descriptive of this generated seed and these assumptions. It is not an empirical estimate of real sale/holiday uplift.

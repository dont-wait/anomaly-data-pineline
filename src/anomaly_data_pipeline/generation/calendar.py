from __future__ import annotations

from datetime import date, timedelta


# Demonstration calendar for 2025. Campaign multipliers are synthetic assumptions.
HOLIDAYS = {
    date(2025, 1, 1): "new_year",
    date(2025, 1, 25): "tet_period",
    date(2025, 1, 26): "tet_period",
    date(2025, 1, 27): "tet_period",
    date(2025, 1, 28): "tet_period",
    date(2025, 1, 29): "tet_period",
    date(2025, 1, 30): "tet_period",
    date(2025, 1, 31): "tet_period",
    date(2025, 2, 1): "tet_period",
    date(2025, 2, 2): "tet_period",
    date(2025, 4, 7): "hung_kings",
    date(2025, 4, 30): "reunification_day",
    date(2025, 5, 1): "labor_day",
    date(2025, 5, 2): "holiday_bridge",
    date(2025, 5, 3): "holiday_bridge",
    date(2025, 5, 4): "holiday_bridge",
    date(2025, 6, 28): "family_day",
}


def calendar_tags(day: date, campaign_days: dict[str, float]) -> tuple[list[str], float]:
    tags: list[str] = []
    weight = 1.0
    holiday = HOLIDAYS.get(day)
    if holiday:
        tags.append(holiday)
        weight *= 1.5 if holiday == "tet_period" else 1.25
    campaign_weight = campaign_days.get(day.strftime("%m-%d"))
    if campaign_weight:
        tags.append("campaign_" + day.strftime("%m%d"))
        weight *= campaign_weight
    if day.day in {1, 5, 10, 15, 20, 25}:
        tags.append("payday")
        weight *= 1.12
    if day.day >= 28:
        tags.append("month_end")
        weight *= 1.08
    if not tags:
        tags.append("regular")
    return tags, weight


def days_in_range(start: date, count: int, campaign_days: dict[str, float]) -> list[tuple[date, list[str], float]]:
    return [(day := start + timedelta(days=offset), *calendar_tags(day, campaign_days))
            for offset in range(count)]

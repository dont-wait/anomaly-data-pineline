from __future__ import annotations

from datetime import timedelta

from anomaly_data_pipeline.generation.fields import FieldSet, Row

CREDIT_PROFILE = FieldSet("credit_profile")


@CREDIT_PROFILE.field("_history", scratch=True)
def _history(r: Row):
    score, history = r.rng.randint(300, 850), []
    for month in range(6):
        score = max(300, min(850, score + r.rng.randint(-18, 20)))
        history.append({"as_of": (r.start - timedelta(days=30 * (5 - month))).date().isoformat(), "score": score,
                        "payment_status": r.rng.choices(["on_time", "late_30", "late_60", "late_90"],
                                                        weights=[88, 7, 3, 2])[0]})
    return history

@CREDIT_PROFILE.field("score")
def score(r: Row): return r.scratch["_history"][-1]["score"]

@CREDIT_PROFILE.field("bad_debt")
def bad_debt(r: Row): return r.rng.random() < 0.04

@CREDIT_PROFILE.field("updated_at")
def updated_at(r: Row): return r.start.isoformat()

@CREDIT_PROFILE.field("history")
def history(r: Row): return r.scratch["_history"]

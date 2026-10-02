from __future__ import annotations

from datetime import timedelta

from anomaly_data_pipeline.generation.fields import FieldSet, Row
from anomaly_data_pipeline.generation.ids import stable_id

# Decision is scratch-only state shared by the application and loan documents.
LOAN_DECISION = FieldSet("loan_decision")
LOAN_APPLICATION = FieldSet("loan_application")
LOAN = FieldSet("loan")


# --- decision (scratch) -------------------------------------------------------
@LOAN_DECISION.field("approved", scratch=True)
def approved(r: Row):
    credit = r.scratch["customer"]["credit_profile"]
    o = r.opts
    if credit["bad_debt"]:
        probability = o["approval_bad_debt"]
    elif credit["score"] >= o["high_credit_threshold"]:
        probability = o["approval_high_credit"]
    elif credit["score"] >= o["medium_credit_threshold"]:
        probability = o["approval_medium_credit"]
    else:
        probability = o["approval_low_credit"]
    return r.rng.random() < probability

@LOAN_DECISION.field("active", scratch=True)
def active(r: Row): return r.scratch["approved"] and r.rng.random() < r.opts["active_probability"]

@LOAN_DECISION.field("late", scratch=True)
def late(r: Row): return r.rng.choices([0, 1, 2, 3], weights=[78, 13, 7, 2])[0] if r.scratch["approved"] else 0

@LOAN_DECISION.field("package", scratch=True)
def package(r: Row): return r.rng.choice(r.ctx.packages)

@LOAN_DECISION.field("status", scratch=True)
def status(r: Row): return "approved" if r.scratch["approved"] else "rejected"

@LOAN_DECISION.field("app_id", scratch=True)
def app_id(r: Row): return stable_id(r.seed, "loan-application", r.index)

@LOAN_DECISION.field("loan_id", scratch=True)
def loan_id(r: Row): return stable_id(r.seed, "loan", r.index)

@LOAN_DECISION.field("requested_amount", scratch=True)
def requested_amount(r: Row):
    p = r.scratch["package"]
    return r.rng.randint(p["min_amount"] // 1_000_000, min(p["max_amount"] // 1_000_000, 150)) * 1_000_000

@LOAN_DECISION.field("principal", scratch=True)
def principal(r: Row): return r.scratch["requested_amount"] if r.scratch["approved"] else 0

@LOAN_DECISION.field("outstanding_principal", scratch=True)
def outstanding(r: Row): return r.scratch["principal"] if r.scratch["active"] else 0


# --- application document -----------------------------------------------------
@LOAN_APPLICATION.field("_id")
def a_id(r: Row): return r.scratch["app_id"]

@LOAN_APPLICATION.field("application_no")
def application_no(r: Row): return f"APP{r.seed % 100000}{r.index:06d}"

@LOAN_APPLICATION.field("customer_id")
def a_customer_id(r: Row): return r.scratch["customer"]["_id"]

@LOAN_APPLICATION.field("loan_package_id")
def package_id(r: Row): return r.scratch["package"]["_id"]

@LOAN_APPLICATION.field("request.amount")
def amount(r: Row): return r.scratch["requested_amount"]

@LOAN_APPLICATION.field("request.term_months")
def term_months(r: Row): return r.rng.choice(r.scratch["package"]["term_options"])

@LOAN_APPLICATION.field("assessment.credit_score")
def credit_score(r: Row): return r.scratch["customer"]["credit_profile"]["score"]

@LOAN_APPLICATION.field("assessment.decision")
def decision(r: Row): return r.scratch["status"]

@LOAN_APPLICATION.field("status")
def a_status(r: Row): return r.scratch["status"]

@LOAN_APPLICATION.field("created_at")
def a_created_at(r: Row): return r.start.isoformat()


# --- loan document (approved applications only) -------------------------------
@LOAN.field("loan_no")
def loan_no(r: Row): return f"LN{r.seed % 100000}{r.index:06d}"

@LOAN.field("application_id")
def l_application_id(r: Row): return r.scratch["app_id"]

@LOAN.field("customer_id")
def l_customer_id(r: Row): return r.scratch["customer"]["_id"]

@LOAN.field("disbursement_account_id")
def disbursement_account_id(r: Row): return r.scratch["account"]["_id"]

@LOAN.field("principal")
def l_principal(r: Row): return r.scratch["principal"]

@LOAN.field("outstanding_principal")
def l_outstanding(r: Row): return r.scratch["outstanding_principal"]

@LOAN.field("interest_rate")
def interest_rate(r: Row): return round(r.rng.uniform(r.opts["interest_rate_min"], r.opts["interest_rate_max"]), 4)

@LOAN.field("term_months")
def l_term_months(r: Row): return r.scratch["term_months"]

@LOAN.field("status")
def l_status(r: Row): return "active" if r.scratch["active"] else "closed"

@LOAN.field("start_date")
def start_date(r: Row): return (r.start + timedelta(days=3)).date().isoformat()

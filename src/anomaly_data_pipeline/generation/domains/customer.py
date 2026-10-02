from __future__ import annotations

from datetime import timedelta

from anomaly_data_pipeline.generation.fields import FieldSet, Row
from anomaly_data_pipeline.generation.ids import stable_id

CUSTOMER = FieldSet("customer")
_AGE_BANDS = ((25, "18-24"), (35, "25-34"), (45, "35-44"), (60, "45-59"))


def age_band(age: int) -> str:
    return next((label for limit, label in _AGE_BANDS if age < limit), "60+")


@CUSTOMER.field("_id")
def _id(r: Row): return stable_id(r.seed, "customer", r.index)

@CUSTOMER.field("customer_code")
def customer_code(r: Row): return f"CUS{r.seed % 100000:05d}{r.index:06d}"

@CUSTOMER.field("age", scratch=True)
def age(r: Row): return r.rng.randint(19, 75)

@CUSTOMER.field("dob", scratch=True)
def dob(r: Row): return (r.start - timedelta(days=r.scratch["age"] * 365 + r.rng.randrange(365))).date()

@CUSTOMER.field("profile.full_name")
def full_name(r: Row): return r.ctx.fake.person.full_name()

@CUSTOMER.field("profile.date_of_birth")
def date_of_birth(r: Row): return r.scratch["dob"].isoformat()

@CUSTOMER.field("profile.phone")
def phone(r: Row): return f"09{r.rng.randrange(10**8):08d}"

@CUSTOMER.field("profile.email")
def email(r: Row): return r.ctx.fake.person.email()

@CUSTOMER.field("profile.address.line")
def address_line(r: Row): return f"{r.rng.randint(1, 250)} {r.ctx.fake.address.street_name()}"

@CUSTOMER.field("profile.address.province_code")
def province_code(r: Row): return r.rng.choice(r.opts["provinces"])

@CUSTOMER.field("profile.demographics.age_band")
def band(r: Row): return age_band(r.scratch["age"])

@CUSTOMER.field("profile.demographics.occupation")
def occupation(r: Row): return r.rng.choice(r.opts["occupations"])

@CUSTOMER.field("profile.demographics.monthly_income")
def monthly_income(r: Row): return r.rng.randrange(8, 120) * 1_000_000

@CUSTOMER.field("identity.type")
def identity_type(r: Row): return "national_id"

@CUSTOMER.field("identity.number")
def identity_number(r: Row): return f"0{r.rng.randrange(10**11):011d}"

@CUSTOMER.field("kyc_status")
def kyc_status(r: Row): return "verified"

@CUSTOMER.field("status")
def status(r: Row): return "active"

@CUSTOMER.field("created_at")
def created_at(r: Row): return r.start.isoformat()

@CUSTOMER.field("updated_at")
def updated_at(r: Row): return r.start.isoformat()

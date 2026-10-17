from sqlalchemy import (
    DateTime,
    ForeignKey,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, mapped_column

from scope_guard.domain.shared.enums import (
    Currency,
    EvaluationAccuracy,
    Industry,
    PricingModel,
    Verdict,
)

"""Historical Drizzle baseline mapping; current schema uses models.workflow Core tables."""


class Base(DeclarativeBase):
    pass


def enum_type(enum, name):
    return ENUM(enum, name=name, values_callable=lambda values: [item.value for item in values])


industry = enum_type(Industry, "industry")
verdict = enum_type(Verdict, "verdict")
pricing_model = enum_type(PricingModel, "pricing_model")
currency = enum_type(Currency, "currency")
accuracy = enum_type(EvaluationAccuracy, "evaluation_accuracy")


def pk():
    return mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


def timestamp():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


def fk(target, name):
    return ForeignKey(target, name=name, ondelete="CASCADE", onupdate="NO ACTION")

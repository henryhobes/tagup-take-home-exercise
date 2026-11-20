from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.rules import Severity, Status


class EventKind(StrEnum):
    scheduled = "scheduled"
    rescheduled = "rescheduled"
    unscheduled = "unscheduled"
    started = "started"
    resolved = "resolved"
    canceled = "canceled"
    severity_changed = "severity_changed"
    description_edited = "description_edited"


def _enum(cls):
    return Enum(cls, native_enum=False, create_constraint=True, length=20)


def _not_blank(column):
    return CheckConstraint(f"length(trim({column})) > 0", name=f"{column}_not_blank")


class Base(DeclarativeBase):
    pass


class Aircraft(Base):
    __tablename__ = "aircraft"
    __table_args__ = (_not_blank("tail_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tail_number: Mapped[str] = mapped_column(unique=True)

    writeups: Mapped[list["Writeup"]] = relationship(back_populates="aircraft", order_by="Writeup.id")


class Writeup(Base):
    __tablename__ = "writeup"
    __table_args__ = (
        _not_blank("description"),
        _not_blank("reported_by"),
        CheckConstraint(
            "(status = 'unscheduled' AND scheduled_date IS NULL)"
            " OR (status IN ('scheduled', 'in_progress', 'resolved') AND scheduled_date IS NOT NULL)"
            " OR status = 'canceled'",
            name="scheduled_date_matches_status",
        ),
        Index("ix_writeup_aircraft_status", "aircraft_id", "status"),
        Index("ix_writeup_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    aircraft_id: Mapped[int] = mapped_column(ForeignKey("aircraft.id"))
    description: Mapped[str]
    severity: Mapped[Severity] = mapped_column(_enum(Severity))
    status: Mapped[Status] = mapped_column(_enum(Status))
    scheduled_date: Mapped[date | None]
    reported_by: Mapped[str]
    # Naive UTC: SQLite has no time zone type.
    reported_at: Mapped[datetime]

    aircraft: Mapped[Aircraft] = relationship(back_populates="writeups")
    events: Mapped[list["WriteupEvent"]] = relationship(order_by="WriteupEvent.id")


class WriteupEvent(Base):
    __tablename__ = "writeup_event"
    __table_args__ = (
        _not_blank("actor"),
        CheckConstraint(
            "kind NOT IN ('resolved', 'canceled', 'severity_changed')"
            " OR (note IS NOT NULL AND length(trim(note)) > 0)",
            name="note_required",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    writeup_id: Mapped[int] = mapped_column(ForeignKey("writeup.id"), index=True)
    # Naive UTC: SQLite has no time zone type.
    at: Mapped[datetime]
    actor: Mapped[str]
    kind: Mapped[EventKind] = mapped_column(_enum(EventKind))
    from_value: Mapped[str | None]
    to_value: Mapped[str | None]
    note: Mapped[str | None]

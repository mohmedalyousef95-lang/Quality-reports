from datetime import date, datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class School(Base):
    __tablename__ = "schools"

    ministry_number = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    region = Column(String)
    address = Column(Text)
    zone = Column(String, index=True)
    engineer = Column(String)
    supervisor = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    building_type = Column(String)
    national_address = Column(String)
    ownership_type = Column(String)

    reports = relationship(
        "Report", back_populates="school", order_by="desc(Report.visit_date)"
    )


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    school_id = Column(String, ForeignKey("schools.ministry_number"), nullable=False)
    visit_date = Column(Date, default=date.today, nullable=False)
    visitor_name = Column(String)
    contractor = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="draft", index=True)  # draft | completed
    completed_at = Column(DateTime)

    # Extra visit info (all optional/flexible — shown on the info slide only
    # when filled in, so leaving them blank never affects the layout).
    visit_type = Column(String, default="")  # تفقدية | خطة الاستعداد المدرسي
    during_readiness_plan = Column(String, default="")  # "" | نعم | لا
    team_count = Column(Integer)
    oversight_supervisor_present = Column(String, default="")  # "" | نعم | لا
    team_types = Column(String, default="")  # comma-separated
    important_notes = Column(Text, default="")

    school = relationship("School", back_populates="reports")
    photos = relationship(
        "ReportPhoto",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportPhoto.position",
    )
    notes = relationship(
        "ReportNote",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportNote.position",
    )


class ReportPhoto(Base):
    __tablename__ = "report_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    category = Column(String, nullable=False)
    position = Column(Integer, default=0)
    file_path = Column(String, nullable=False)
    caption = Column(String, default="")

    report = relationship("Report", back_populates="photos")


class ReportNote(Base):
    __tablename__ = "report_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    category = Column(String, nullable=False)
    item = Column(String, nullable=False)
    note = Column(Text, default="")
    status = Column(String, default="")  # "" | نعم | لا | جاري العمل عليها
    position = Column(Integer, default=0)

    report = relationship("Report", back_populates="notes")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, nullable=False, index=True)
    label = Column(String, nullable=False)
    position = Column(Integer, default=0)


class NoteSuggestion(Base):
    """A ready-made note phrase offered as a dropdown option for a specific
    checklist item, to cut down on manual typing (e.g. "صيانة الفلتر" ->
    "غسل الفلتر" / "استبدال الفلتر" / ...). Free-text entry remains
    available regardless."""

    __tablename__ = "note_suggestions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, nullable=False, index=True)
    item = Column(String, nullable=False, index=True)
    text = Column(String, nullable=False)
    position = Column(Integer, default=0)


class Review(Base):
    """A follow-up visit that re-checks an existing report's notes. A
    report can have several reviews over time (e.g. one a month later,
    another two months later) — each is its own independent record."""

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    visit_date = Column(Date, default=date.today, nullable=False)
    visitor_name = Column(String)
    status = Column(String, default="draft", index=True)  # draft | completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    report = relationship("Report")
    notes = relationship(
        "ReviewNote",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewNote.position",
    )
    photos = relationship(
        "ReviewPhoto",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewPhoto.position",
    )


class ReviewNote(Base):
    """One followed-up note within a review — a copy of the original
    report's note (item/note text, kept editable) plus the review's own
    response-status verdict. original_note_id is null for a note added
    fresh during the review (not present in the original report)."""

    __tablename__ = "review_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    original_note_id = Column(Integer, ForeignKey("report_notes.id"))
    category = Column(String, nullable=False)
    item = Column(String, nullable=False)
    note = Column(Text, default="")
    # "" | تمت المعالجة | معالجة جزئية | جاري التنفيذ | لم تتم المعالجة
    response_status = Column(String, default="")
    position = Column(Integer, default=0)

    review = relationship("Review", back_populates="notes")


class ReviewPhoto(Base):
    """An "after" photo taken during the review, grouped by the same four
    photo categories as the original report (before-photos are simply the
    original report's own photos — never duplicated)."""

    __tablename__ = "review_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    category = Column(String, nullable=False)
    position = Column(Integer, default=0)
    file_path = Column(String, nullable=False)
    caption = Column(String, default="")

    review = relationship("Review", back_populates="photos")

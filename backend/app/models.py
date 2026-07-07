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
    created_at = Column(DateTime, default=datetime.utcnow)

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

    report = relationship("Report", back_populates="photos")


class ReportNote(Base):
    __tablename__ = "report_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    category = Column(String, nullable=False)
    item = Column(String, nullable=False)
    note = Column(Text, default="")
    position = Column(Integer, default=0)

    report = relationship("Report", back_populates="notes")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, nullable=False, index=True)
    label = Column(String, nullable=False)
    position = Column(Integer, default=0)

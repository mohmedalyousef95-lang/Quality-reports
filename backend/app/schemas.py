from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    password: str


class SchoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ministry_number: str
    name: str
    region: Optional[str] = None
    address: Optional[str] = None
    zone: Optional[str] = None
    engineer: Optional[str] = None
    supervisor: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    building_type: Optional[str] = None
    national_address: Optional[str] = None
    ownership_type: Optional[str] = None


class ChecklistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    label: str
    position: int


class ChecklistItemCreate(BaseModel):
    category: str
    label: str


class NoteSuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    item: str
    text: str
    position: int


class ReportCreate(BaseModel):
    school_id: str
    visit_date: date
    visitor_name: str
    contractor: str = ""


class ReportInfoUpdate(BaseModel):
    contractor: str = ""
    visit_type: str = ""
    during_readiness_plan: str = ""
    team_count: Optional[int] = None
    oversight_supervisor_present: str = ""
    team_types: str = ""
    important_notes: str = ""


class ReportNoteIn(BaseModel):
    category: str
    item: str
    note: str = ""
    status: str = ""
    position: int = 0


class ReportNotesReplace(BaseModel):
    category: str
    notes: list[ReportNoteIn]


class ReportPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    position: int
    file_path: str
    caption: Optional[str] = ""


class PhotoCaptionUpdate(BaseModel):
    caption: str = ""


class ReportNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    item: str
    note: str
    status: Optional[str] = ""
    position: int


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: str
    visit_date: date
    visitor_name: Optional[str] = None
    created_at: datetime
    status: Optional[str] = "draft"
    contractor: Optional[str] = ""
    visit_type: Optional[str] = ""
    during_readiness_plan: Optional[str] = ""
    team_count: Optional[int] = None
    oversight_supervisor_present: Optional[str] = ""
    team_types: Optional[str] = ""
    important_notes: Optional[str] = ""
    photos: list[ReportPhotoOut] = []
    notes: list[ReportNoteOut] = []


class ReportListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: str
    visit_date: date
    visitor_name: Optional[str] = None
    created_at: datetime
    status: Optional[str] = "draft"


class ReportRow(BaseModel):
    """A report enriched with its school info + progress, for the reports list."""

    id: int
    school_id: str
    school_name: str
    zone: Optional[str] = None
    engineer: Optional[str] = None
    supervisor: Optional[str] = None
    visit_date: date
    visitor_name: Optional[str] = None
    status: str
    photo_count: int
    note_count: int
    completion: int  # 0-100
    created_at: datetime


class FilterOptions(BaseModel):
    zones: list[str]
    engineers: list[str]
    supervisors: list[str]


class ReviewCreate(BaseModel):
    report_id: int
    visit_date: Optional[date] = None
    visitor_name: str = ""


class ReviewInfoUpdate(BaseModel):
    visit_date: date
    visitor_name: str = ""


class ReviewNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_note_id: Optional[int] = None
    category: str
    item: str
    note: str
    response_status: Optional[str] = ""
    position: int


class ReviewNoteUpdate(BaseModel):
    note: str = ""
    response_status: str = ""


class ReviewNoteCreate(BaseModel):
    category: str
    item: str
    note: str = ""
    response_status: str = ""


class ReviewPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    position: int
    file_path: str
    caption: Optional[str] = ""


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    visit_date: date
    visitor_name: Optional[str] = None
    status: Optional[str] = "draft"
    created_at: datetime
    notes: list[ReviewNoteOut] = []
    photos: list[ReviewPhotoOut] = []
    # The original report this review follows up on — its photos/notes are
    # the "قبل" (before) reference the review compares against.
    report: ReportOut


class ReviewListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    visit_date: date
    visitor_name: Optional[str] = None
    status: Optional[str] = "draft"
    created_at: datetime


class SchoolReviewSummary(BaseModel):
    """One row on the "تقارير المراجعة" school picker — a school that
    already has at least one quality report, with its most recent
    report's id/date so the picker can sort by it and flag overdue ones."""

    ministry_number: str
    name: str
    zone: Optional[str] = None
    engineer: Optional[str] = None
    supervisor: Optional[str] = None
    latest_report_id: int
    latest_visit_date: date

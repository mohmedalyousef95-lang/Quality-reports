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


class ReportCreate(BaseModel):
    school_id: str
    visit_date: date
    visitor_name: str
    contractor: str = ""


class ReportNoteIn(BaseModel):
    category: str
    item: str
    note: str = ""
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
    position: int


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: str
    visit_date: date
    visitor_name: Optional[str] = None
    created_at: datetime
    status: Optional[str] = "draft"
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

import tempfile
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from sqlalchemy import or_, func, distinct
from sqlalchemy.orm import Session, joinedload

from ..auth import require_auth
from ..database import get_db
from ..models import School, Report, ReportPhoto, ReportNote
from ..schemas import (
    ReportCreate,
    ReportOut,
    ReportNotesReplace,
    ReportRow,
    FilterOptions,
    PhotoCaptionUpdate,
    ReportInfoUpdate,
)
from ..constants import PHOTO_CATEGORIES, NOTE_CATEGORIES, MAX_PHOTOS_PER_CATEGORY

TOTAL_SECTIONS = len(PHOTO_CATEGORIES) + len(NOTE_CATEGORIES)
from ..services.photo_storage import (
    save_photo,
    delete_photo,
    delete_report_photos,
    load_photo_bytes,
)
from ..services.pptx_generator import generate_report_pptx

router = APIRouter(prefix="/api/reports", tags=["reports"], dependencies=[Depends(require_auth)])


def _get_report_or_404(report_id: int, db: Session) -> Report:
    report = (
        db.query(Report)
        .options(joinedload(Report.photos), joinedload(Report.notes))
        .filter(Report.id == report_id)
        .first()
    )
    if report is None:
        raise HTTPException(404, "التقرير غير موجود")
    return report


@router.post("", response_model=ReportOut)
def create_report(payload: ReportCreate, db: Session = Depends(get_db)):
    school = db.get(School, payload.school_id)
    if school is None:
        raise HTTPException(404, "المدرسة غير موجودة")
    report = Report(
        school_id=payload.school_id,
        visit_date=payload.visit_date,
        visitor_name=payload.visitor_name,
        contractor=payload.contractor,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/filters", response_model=FilterOptions)
def report_filters(db: Session = Depends(get_db)):
    """Distinct zone/engineer/supervisor across schools that have reports."""
    zones, engineers, supervisors = set(), set(), set()
    for zone, eng, sup in (
        db.query(School.zone, School.engineer, School.supervisor)
        .join(Report, Report.school_id == School.ministry_number)
        .distinct()
    ):
        if zone:
            zones.add(zone)
        if eng:
            engineers.add(eng)
        if sup:
            supervisors.add(sup)
    return FilterOptions(
        zones=sorted(zones), engineers=sorted(engineers), supervisors=sorted(supervisors)
    )


@router.get("", response_model=list[ReportRow])
def list_reports(
    search: str = "",
    status: str = "",
    zone: str = "",
    engineer: str = "",
    supervisor: str = "",
    sort: str = "recent",
    db: Session = Depends(get_db),
):
    query = db.query(Report, School).join(School, Report.school_id == School.ministry_number)

    if search:
        like = f"%{search}%"
        query = query.filter(or_(School.name.ilike(like), School.ministry_number.ilike(like)))
    if status in ("draft", "completed"):
        query = query.filter(Report.status == status)
    if zone:
        query = query.filter(School.zone == zone)
    if engineer:
        query = query.filter(School.engineer == engineer)
    if supervisor:
        query = query.filter(School.supervisor == supervisor)

    if sort == "oldest":
        query = query.order_by(Report.visit_date.asc(), Report.id.asc())
    elif sort == "school":
        query = query.order_by(School.name.asc())
    else:  # recent
        query = query.order_by(Report.visit_date.desc(), Report.id.desc())

    rows = query.all()
    report_ids = [r.Report.id for r in rows]

    photo_counts, photo_sections = _counts_and_sections(db, ReportPhoto, report_ids)
    note_counts, note_sections = _counts_and_sections(db, ReportNote, report_ids)

    result = []
    for r in rows:
        rid = r.Report.id
        sections = photo_sections.get(rid, 0) + note_sections.get(rid, 0)
        completion = round(sections / TOTAL_SECTIONS * 100)
        result.append(
            ReportRow(
                id=rid,
                school_id=r.Report.school_id,
                school_name=r.School.name,
                zone=r.School.zone,
                engineer=r.School.engineer,
                supervisor=r.School.supervisor,
                visit_date=r.Report.visit_date,
                visitor_name=r.Report.visitor_name,
                status=r.Report.status or "draft",
                photo_count=photo_counts.get(rid, 0),
                note_count=note_counts.get(rid, 0),
                completion=completion,
                created_at=r.Report.created_at,
            )
        )
    return result


def _counts_and_sections(db: Session, model, report_ids):
    """Return (total counts, distinct-category counts) per report id."""
    counts, sections = {}, {}
    if not report_ids:
        return counts, sections
    for rid, total in (
        db.query(model.report_id, func.count(model.id))
        .filter(model.report_id.in_(report_ids))
        .group_by(model.report_id)
    ):
        counts[rid] = total
    for rid, secs in (
        db.query(model.report_id, func.count(distinct(model.category)))
        .filter(model.report_id.in_(report_ids))
        .group_by(model.report_id)
    ):
        sections[rid] = secs
    return counts, sections


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    return _get_report_or_404(report_id, db)


@router.put("/{report_id}/info", response_model=ReportOut)
def update_report_info(report_id: int, payload: ReportInfoUpdate, db: Session = Depends(get_db)):
    report = _get_report_or_404(report_id, db)
    for field, value in payload.model_dump().items():
        setattr(report, field, value)
    report.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(report)
    return report


@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = _get_report_or_404(report_id, db)
    db.delete(report)
    db.commit()
    delete_report_photos(report_id)
    return {"ok": True}


@router.post("/{report_id}/photos")
async def upload_photo(
    report_id: int,
    category: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if category not in PHOTO_CATEGORIES:
        raise HTTPException(400, "قسم غير صحيح")
    report = _get_report_or_404(report_id, db)

    existing_count = sum(1 for p in report.photos if p.category == category)
    if existing_count >= MAX_PHOTOS_PER_CATEGORY:
        raise HTTPException(400, f"الحد الأقصى {MAX_PHOTOS_PER_CATEGORY} صور لهذا القسم")

    key = save_photo(file.file, report_id)
    photo = ReportPhoto(
        report_id=report_id,
        category=category,
        position=existing_count,
        file_path=key,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return {
        "id": photo.id,
        "category": photo.category,
        "position": photo.position,
        "url": f"/api/reports/{report_id}/photos/{photo.id}/file",
    }


@router.get("/{report_id}/photos/{photo_id}/file")
def get_photo_file(report_id: int, photo_id: int, db: Session = Depends(get_db)):
    photo = db.get(ReportPhoto, photo_id)
    if photo is None or photo.report_id != report_id:
        raise HTTPException(404, "الصورة غير موجودة")
    data = load_photo_bytes(photo.file_path)
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.delete("/{report_id}/photos/{photo_id}")
def delete_photo_endpoint(report_id: int, photo_id: int, db: Session = Depends(get_db)):
    photo = db.get(ReportPhoto, photo_id)
    if photo is None or photo.report_id != report_id:
        raise HTTPException(404, "الصورة غير موجودة")
    delete_photo(photo.file_path)
    db.delete(photo)
    db.commit()
    return {"ok": True}


@router.put("/{report_id}/photos/{photo_id}/caption")
def update_photo_caption(
    report_id: int,
    photo_id: int,
    payload: PhotoCaptionUpdate,
    db: Session = Depends(get_db),
):
    photo = db.get(ReportPhoto, photo_id)
    if photo is None or photo.report_id != report_id:
        raise HTTPException(404, "الصورة غير موجودة")
    photo.caption = payload.caption
    db.commit()
    return {"ok": True}


@router.put("/{report_id}/notes")
def replace_notes(report_id: int, payload: ReportNotesReplace, db: Session = Depends(get_db)):
    if payload.category not in NOTE_CATEGORIES:
        raise HTTPException(400, "قسم غير صحيح")
    _get_report_or_404(report_id, db)

    db.query(ReportNote).filter(
        ReportNote.report_id == report_id, ReportNote.category == payload.category
    ).delete()
    for position, note_in in enumerate(payload.notes):
        db.add(
            ReportNote(
                report_id=report_id,
                category=payload.category,
                item=note_in.item,
                note=note_in.note,
                status=note_in.status,
                position=position,
            )
        )
    db.commit()
    return {"ok": True}


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    report = _get_report_or_404(report_id, db)
    school = db.get(School, report.school_id)

    # Issuing the report marks it completed.
    report.status = "completed"
    report.completed_at = datetime.utcnow()
    db.commit()

    filename = f"{school.name}_{report.visit_date}.pptx".replace("/", "-")
    tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
    tmp.close()

    generate_report_pptx(school, report, tmp.name)

    return FileResponse(
        tmp.name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )

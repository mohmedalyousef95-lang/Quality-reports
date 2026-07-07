import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from ..auth import require_auth
from ..database import get_db
from ..models import School, Report, ReportPhoto, ReportNote
from ..schemas import ReportCreate, ReportOut, ReportNotesReplace
from ..constants import PHOTO_CATEGORIES, NOTE_CATEGORIES, MAX_PHOTOS_PER_CATEGORY
from ..services.photo_storage import save_photo, delete_photo_file
from ..services.pptx_generator import generate_report_pptx
from ..config import DATA_DIR

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
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    return _get_report_or_404(report_id, db)


@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = _get_report_or_404(report_id, db)
    db.delete(report)
    db.commit()
    shutil.rmtree(DATA_DIR / "photos" / str(report_id), ignore_errors=True)
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

    dest_path = save_photo(file.file, report_id)
    photo = ReportPhoto(
        report_id=report_id,
        category=category,
        position=existing_count,
        file_path=str(dest_path),
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
    return FileResponse(photo.file_path)


@router.delete("/{report_id}/photos/{photo_id}")
def delete_photo(report_id: int, photo_id: int, db: Session = Depends(get_db)):
    photo = db.get(ReportPhoto, photo_id)
    if photo is None or photo.report_id != report_id:
        raise HTTPException(404, "الصورة غير موجودة")
    delete_photo_file(photo.file_path)
    db.delete(photo)
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
                position=position,
            )
        )
    db.commit()
    return {"ok": True}


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    report = _get_report_or_404(report_id, db)
    school = db.get(School, report.school_id)

    output_dir = DATA_DIR / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{school.name}_{report.visit_date}.pptx".replace("/", "-")
    output_path = output_dir / f"report_{report_id}.pptx"

    generate_report_pptx(school, report, output_path)

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )

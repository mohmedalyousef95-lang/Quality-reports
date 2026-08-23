import tempfile
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session, joinedload

from ..auth import require_auth
from ..database import get_db
from ..models import Report, Review, ReviewNote, ReviewPhoto
from ..schemas import (
    ReviewCreate,
    ReviewInfoUpdate,
    ReviewOut,
    ReviewListItem,
    ReviewNoteUpdate,
    ReviewNoteCreate,
)
from ..constants import PHOTO_CATEGORIES
from ..services.photo_storage import save_review_photo, delete_photo, delete_review_photos, load_photo_bytes
from ..services.review_pptx_generator import generate_review_pptx
from ..services.pdf_export import convert_pptx_to_pdf, PdfConversionError

router = APIRouter(prefix="/api/reviews", tags=["reviews"], dependencies=[Depends(require_auth)])


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


def _get_review_or_404(review_id: int, db: Session) -> Review:
    review = (
        db.query(Review)
        .options(
            joinedload(Review.notes),
            joinedload(Review.photos),
            joinedload(Review.report).joinedload(Report.photos),
            joinedload(Review.report).joinedload(Report.notes),
        )
        .filter(Review.id == review_id)
        .first()
    )
    if review is None:
        raise HTTPException(404, "المراجعة غير موجودة")
    return review


@router.post("", response_model=ReviewOut)
def create_review(payload: ReviewCreate, db: Session = Depends(get_db)):
    report = _get_report_or_404(payload.report_id, db)

    review = Review(
        report_id=report.id,
        visit_date=payload.visit_date or date.today(),
        visitor_name=payload.visitor_name,
    )
    db.add(review)
    db.flush()

    # Auto-pull every note from the original report as the review's starting
    # point — each keeps a link back via original_note_id so the deck/UI can
    # tell "carried over from before" apart from notes added during review.
    for position, note in enumerate(report.notes):
        db.add(
            ReviewNote(
                review_id=review.id,
                original_note_id=note.id,
                category=note.category,
                item=note.item,
                note=note.note,
                response_status="",
                position=position,
            )
        )
    db.commit()
    db.refresh(review)
    return _get_review_or_404(review.id, db)


@router.get("/{review_id}", response_model=ReviewOut)
def get_review(review_id: int, db: Session = Depends(get_db)):
    return _get_review_or_404(review_id, db)


@router.put("/{review_id}/info", response_model=ReviewOut)
def update_review_info(review_id: int, payload: ReviewInfoUpdate, db: Session = Depends(get_db)):
    review = _get_review_or_404(review_id, db)
    review.visit_date = payload.visit_date
    review.visitor_name = payload.visitor_name
    review.updated_at = datetime.utcnow()
    db.commit()
    return _get_review_or_404(review_id, db)


@router.delete("/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    review = _get_review_or_404(review_id, db)
    db.delete(review)
    db.commit()
    delete_review_photos(review_id)
    return {"ok": True}


@router.put("/{review_id}/notes/{note_id}", response_model=ReviewOut)
def update_review_note(
    review_id: int, note_id: int, payload: ReviewNoteUpdate, db: Session = Depends(get_db)
):
    note = db.get(ReviewNote, note_id)
    if note is None or note.review_id != review_id:
        raise HTTPException(404, "الملاحظة غير موجودة")
    note.note = payload.note
    note.response_status = payload.response_status
    db.commit()
    return _get_review_or_404(review_id, db)


@router.post("/{review_id}/notes", response_model=ReviewOut)
def add_review_note(review_id: int, payload: ReviewNoteCreate, db: Session = Depends(get_db)):
    review = _get_review_or_404(review_id, db)
    max_position = max([n.position for n in review.notes], default=-1)
    db.add(
        ReviewNote(
            review_id=review_id,
            original_note_id=None,
            category=payload.category,
            item=payload.item,
            note=payload.note,
            response_status=payload.response_status,
            position=max_position + 1,
        )
    )
    db.commit()
    return _get_review_or_404(review_id, db)


@router.delete("/{review_id}/notes/{note_id}", response_model=ReviewOut)
def delete_review_note(review_id: int, note_id: int, db: Session = Depends(get_db)):
    note = db.get(ReviewNote, note_id)
    if note is None or note.review_id != review_id:
        raise HTTPException(404, "الملاحظة غير موجودة")
    db.delete(note)
    db.commit()
    return _get_review_or_404(review_id, db)


@router.post("/{review_id}/photos")
async def upload_review_photo(
    review_id: int,
    category: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if category not in PHOTO_CATEGORIES:
        raise HTTPException(400, "قسم غير صحيح")
    review = _get_review_or_404(review_id, db)

    existing_count = sum(1 for p in review.photos if p.category == category)
    key = save_review_photo(file.file, review_id)
    photo = ReviewPhoto(
        review_id=review_id,
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
        "file_path": photo.file_path,
    }


@router.get("/{review_id}/photos/{photo_id}/file")
def get_review_photo_file(review_id: int, photo_id: int, db: Session = Depends(get_db)):
    photo = db.get(ReviewPhoto, photo_id)
    if photo is None or photo.review_id != review_id:
        raise HTTPException(404, "الصورة غير موجودة")
    data = load_photo_bytes(photo.file_path)
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.delete("/{review_id}/photos/{photo_id}")
def delete_review_photo_endpoint(review_id: int, photo_id: int, db: Session = Depends(get_db)):
    photo = db.get(ReviewPhoto, photo_id)
    if photo is None or photo.review_id != review_id:
        raise HTTPException(404, "الصورة غير موجودة")
    delete_photo(photo.file_path)
    db.delete(photo)
    db.commit()
    return {"ok": True}


@router.get("/{review_id}/download")
def download_review(review_id: int, db: Session = Depends(get_db)):
    review = _get_review_or_404(review_id, db)
    school = review.report.school

    review.status = "completed"
    review.completed_at = datetime.utcnow()
    db.commit()

    filename = f"مراجعة_{school.name}_{review.visit_date}.pptx".replace("/", "-")
    tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
    tmp.close()

    generate_review_pptx(school, review, tmp.name)

    return FileResponse(
        tmp.name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )


@router.get("/{review_id}/download-pdf")
def download_review_pdf(review_id: int, db: Session = Depends(get_db)):
    review = _get_review_or_404(review_id, db)
    school = review.report.school

    review.status = "completed"
    review.completed_at = datetime.utcnow()
    db.commit()

    filename = f"مراجعة_{school.name}_{review.visit_date}.pdf".replace("/", "-")
    tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
    tmp.close()

    generate_review_pptx(school, review, tmp.name)

    try:
        pdf_path = convert_pptx_to_pdf(tmp.name)
    except PdfConversionError as exc:
        raise HTTPException(503, str(exc))

    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)

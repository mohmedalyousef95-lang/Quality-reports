from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..database import get_db
from ..models import School, Report
from ..schemas import SchoolOut, ReportListOut
from ..services.excel_import import import_schools

router = APIRouter(prefix="/api/schools", tags=["schools"], dependencies=[Depends(require_auth)])


@router.get("", response_model=list[SchoolOut])
def search_schools(q: str = "", limit: int = 20, db: Session = Depends(get_db)):
    query = db.query(School)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(School.name.ilike(like), School.ministry_number.ilike(like)))
    return query.order_by(School.name).limit(limit).all()


@router.get("/{ministry_number}", response_model=SchoolOut)
def get_school(ministry_number: str, db: Session = Depends(get_db)):
    school = db.get(School, ministry_number)
    if school is None:
        raise HTTPException(404, "المدرسة غير موجودة")
    return school


@router.get("/{ministry_number}/reports", response_model=list[ReportListOut])
def get_school_reports(ministry_number: str, db: Session = Depends(get_db)):
    school = db.get(School, ministry_number)
    if school is None:
        raise HTTPException(404, "المدرسة غير موجودة")
    return (
        db.query(Report)
        .filter(Report.school_id == ministry_number)
        .order_by(Report.visit_date.desc())
        .all()
    )


@router.post("/import")
async def reimport_schools(file: UploadFile = File(...)):
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        count = import_schools(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return {"imported": count}

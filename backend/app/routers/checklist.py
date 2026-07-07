from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..database import get_db
from ..models import ChecklistItem
from ..schemas import ChecklistItemOut, ChecklistItemCreate
from ..constants import NOTE_CATEGORIES

router = APIRouter(
    prefix="/api/checklist", tags=["checklist"], dependencies=[Depends(require_auth)]
)


@router.get("", response_model=list[ChecklistItemOut])
def list_checklist_items(category: str | None = None, db: Session = Depends(get_db)):
    query = db.query(ChecklistItem)
    if category:
        query = query.filter(ChecklistItem.category == category)
    return query.order_by(ChecklistItem.category, ChecklistItem.position).all()


@router.post("", response_model=ChecklistItemOut)
def add_checklist_item(payload: ChecklistItemCreate, db: Session = Depends(get_db)):
    if payload.category not in NOTE_CATEGORIES:
        raise HTTPException(400, "قسم غير صحيح")
    max_position = (
        db.query(ChecklistItem)
        .filter(ChecklistItem.category == payload.category)
        .count()
    )
    item = ChecklistItem(
        category=payload.category, label=payload.label, position=max_position
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_checklist_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(ChecklistItem, item_id)
    if item is None:
        raise HTTPException(404, "البند غير موجود")
    db.delete(item)
    db.commit()
    return {"ok": True}

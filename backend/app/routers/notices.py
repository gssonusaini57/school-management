from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..deps import db_dep, current_user, require_admin, CurrentUser
from ..schemas.notice import NoticeCreate, NoticeOut
from ..models.notice import Notice, Priority
from ..events import broker

router = APIRouter(prefix="/notices", tags=["notices"])


@router.get("", response_model=list[NoticeOut])
def list_notices(user: CurrentUser = Depends(current_user), db: Session = Depends(db_dep)):
    rows = db.execute(select(Notice).order_by(Notice.created_at.desc())).scalars().all()
    return rows


@router.post("", response_model=NoticeOut, status_code=201)
def create_notice(
    payload: NoticeCreate,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    if payload.priority not in ("normal", "medium", "high"):
        raise HTTPException(status_code=400, detail="Bad priority")
    n = Notice(
        title=payload.title,
        content=payload.content,
        priority=Priority(payload.priority),
        audience=payload.audience,
        posted_by=user.name,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    broker.publish("notices", "upsert", id=n.id)
    broker.publish("dashboard", "notices_changed")
    return n


@router.delete("/{nid}", status_code=204)
def delete_notice(nid: int, user: CurrentUser = Depends(require_admin), db: Session = Depends(db_dep)):
    n = db.get(Notice, nid)
    if not n:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(n)
    db.commit()
    broker.publish("notices", "delete", id=nid)
    broker.publish("dashboard", "notices_changed")

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..deps import db_dep, current_user, current_user_sse, CurrentUser, assert_class_allowed
from ..models.student import Student
from ..models.document import StudentDocument, DocumentKind

router = APIRouter(prefix="/files", tags=["files"])


def _stream_doc(db: Session, user: CurrentUser, sid: int, kind: DocumentKind) -> Response:
    s = db.get(Student, sid)
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    assert_class_allowed(user, s.class_name)
    doc = db.execute(
        select(StudentDocument).where(
            StudentDocument.student_id == sid, StudentDocument.kind == kind
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(content=doc.data, media_type=doc.mime_type)


@router.get("/students/{sid}/{kind}")
def get_doc_header(
    sid: int,
    kind: DocumentKind,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    return _stream_doc(db, user, sid, kind)


@router.get("/students/{sid}/{kind}/inline")
def get_doc_query_token(
    sid: int,
    kind: DocumentKind,
    user: CurrentUser = Depends(current_user_sse),
    db: Session = Depends(db_dep),
):
    return _stream_doc(db, user, sid, kind)

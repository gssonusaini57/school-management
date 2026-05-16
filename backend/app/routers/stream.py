from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from ..deps import current_user_sse, CurrentUser
from ..events import broker

router = APIRouter(prefix="/stream", tags=["stream"])


def _stream(channel: str):
    async def gen():
        async for msg in broker.subscribe(channel):
            yield {"data": msg}
    return EventSourceResponse(gen(), ping=15)


@router.get("/students")
def stream_students(user: CurrentUser = Depends(current_user_sse)):
    return _stream("students")


@router.get("/fees")
def stream_fees(user: CurrentUser = Depends(current_user_sse)):
    return _stream("fees")


@router.get("/notices")
def stream_notices(user: CurrentUser = Depends(current_user_sse)):
    return _stream("notices")


@router.get("/staff")
def stream_staff(user: CurrentUser = Depends(current_user_sse)):
    return _stream("staff")


@router.get("/dashboard")
def stream_dashboard(user: CurrentUser = Depends(current_user_sse)):
    return _stream("dashboard")


@router.get("/deletion-requests")
def stream_deletion_requests(user: CurrentUser = Depends(current_user_sse)):
    return _stream("deletion_requests")

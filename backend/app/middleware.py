import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .logging_config import (
    get_logger,
    request_id_ctx,
    user_role_ctx,
    user_sub_ctx,
)
from .security import decode_token


access_log = get_logger("app.access")


def _identify_user(request: Request) -> tuple[str, str]:
    auth = request.headers.get("authorization") or ""
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    elif "token" in request.query_params:
        token = request.query_params.get("token") or ""
    if not token:
        return "-", "-"
    try:
        payload = decode_token(token)
    except Exception:
        return "-", "invalid"
    return str(payload.get("sub") or "-"), str(payload.get("role") or "-")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        sub, role = _identify_user(request)

        rid_token = request_id_ctx.set(rid)
        sub_token = user_sub_ctx.set(sub)
        role_token = user_role_ctx.set(role)

        start = time.perf_counter()
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        except Exception:
            access_log.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.url.query) or "",
                    "client": request.client.host if request.client else "-",
                },
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            level = "warning" if status_code >= 500 else "info"
            getattr(access_log, level)(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": duration_ms,
                    "client": request.client.host if request.client else "-",
                },
            )
            request_id_ctx.reset(rid_token)
            user_sub_ctx.reset(sub_token)
            user_role_ctx.reset(role_token)

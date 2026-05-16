"""POST /api/pdf/{kind} — render a brand-styled PDF for the given document kind.

Validates the request body against the matching Pydantic schema in
app.pdf.schemas, hands the validated dict to WeasyPrint, returns the
PDF bytes inline.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError

from ..deps import current_user
from ..pdf import render_pdf
from ..pdf.schemas import SCHEMA_BY_KIND

router = APIRouter(prefix="/pdf", tags=["pdf"])
log = logging.getLogger(__name__)


_TEMPLATED_KINDS = {"report-card", "pseb-admit-card"}


@router.post("/{kind}", response_class=Response)
def make_pdf(kind: str, payload: dict, user=Depends(current_user)):
    """Render `payload` to a PDF as `kind`.

    Auth required (any authenticated user — staff can pull receipts they
    work with, admins everything). Body shape depends on `kind`; see
    app.pdf.schemas.
    """
    if kind in _TEMPLATED_KINDS:
        # These two doc kinds moved to the templated bulk-render flow; the
        # ad-hoc endpoint is gone. Frontend uses /api/pdf/templates/.
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                f"{kind!r} is generated via /api/pdf/templates/{{id}}/render. "
                "Create a Template in /admin/templates first."
            ),
        )

    schema_cls: type[BaseModel] | None = SCHEMA_BY_KIND.get(kind)
    if schema_cls is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"unknown PDF kind: {kind!r}. valid: {sorted(SCHEMA_BY_KIND)}",
        )

    try:
        validated = schema_cls.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors(),
        )

    # `model_dump(by_alias=True)` so e.g. fee-receipt's `class_` field maps
    # back to the JSON key `class` the templates expect.
    data = validated.model_dump(by_alias=True, mode="json")

    try:
        pdf_bytes = render_pdf(kind, data)
    except RuntimeError as e:
        # WeasyPrint missing system deps — surface as 503 with the reason
        # so ops can see what to apt-install on the server.
        log.error("pdf render failed", extra={"kind": kind, "err": str(e)})
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception:
        log.exception("pdf render crashed", extra={"kind": kind})
        raise HTTPException(status_code=500, detail="pdf render failed")

    filename = f"{kind}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )

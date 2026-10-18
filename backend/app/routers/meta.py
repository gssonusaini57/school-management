"""Reference lists every client needs, served from the backend's single copies:
classes, grade bands and letters, houses, promotion values, result scopes and
menu keys. Clients may keep a static fallback, but this is the source of truth.
"""
from fastapi import APIRouter, Depends

from ..constants import CLASSES, HOUSES
from ..deps import CurrentUser, current_user
from ..permissions import MENU_KEYS
from ..services.results import (
    GRADE_BANDS, GRADE_LETTERS, PASS_PCT_DEFAULT, CONDITIONAL_MAX_FAILS_DEFAULT,
    PROMOTION_VALUES, SCOPES, grade_legend,
)

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("")
def get_meta(user: CurrentUser = Depends(current_user)):
    return {
        "classes": list(CLASSES),
        "grade_bands": [{"grade": g, "min_pct": p} for g, p in GRADE_BANDS],
        "grade_legend": grade_legend(),
        "grade_letters": list(GRADE_LETTERS),
        "houses": list(HOUSES),
        "promotion_values": list(PROMOTION_VALUES),
        "pass_pct": PASS_PCT_DEFAULT,
        "conditional_max_fails": CONDITIONAL_MAX_FAILS_DEFAULT,
        "scopes": list(SCOPES),
        "menu_keys": list(MENU_KEYS),
    }

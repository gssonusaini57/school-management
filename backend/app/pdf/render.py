"""WeasyPrint + Jinja2 rendering pipeline.

Public API: `render_pdf(kind, data)`.
The router validates `data` via the matching Pydantic schema first, then
hands the validated dict (with date/datetime objects coerced back to ISO
strings the templates expect) into Jinja, then WeasyPrint to PDF bytes.

System prerequisites (Linux):
  apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
              fonts-noto fonts-noto-core fonts-noto-cjk \
              fonts-noto-color-emoji fonts-noto-extra
  # For Punjabi (Gurmukhi):
  apt install fonts-noto fonts-lohit-punjabi

Macs running locally need Homebrew's pango + cairo:
  brew install pango cairo gdk-pixbuf libffi
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .format import format_inr, format_date_long, format_date_pseb, format_month_label

log = logging.getLogger(__name__)

PDF_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PDF_DIR / "templates"
ASSETS_DIR = PDF_DIR / "assets"

SUPPORTED_KINDS = (
    "fee-receipt",
    "letterhead-a",
    "letterhead-b",
    "report-card",
    "pseb-admit-card",
    "salary-slip",
)

_jinja = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "html.j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
_jinja.filters["inr"] = format_inr
_jinja.filters["dt"] = format_date_long
_jinja.filters["dt_pseb"] = format_date_pseb
_jinja.filters["ym_label"] = format_month_label


def render_html(kind: str, data: dict[str, Any]) -> str:
    """Render the Jinja template for `kind` and return raw HTML."""
    if kind not in SUPPORTED_KINDS:
        raise ValueError(f"unknown PDF kind: {kind!r}")
    template = _jinja.get_template(f"{kind}.html.j2")
    return template.render(
        data=data,
        # Absolute file:// URI for tokens.css so WeasyPrint resolves it
        # without having to be told a base_url.
        tokens_css=(ASSETS_DIR / "tokens.css").as_uri(),
        assets_dir=ASSETS_DIR.as_uri(),
    )


def render_pdf(kind: str, data: dict[str, Any]) -> bytes:
    """Render `data` to PDF bytes via WeasyPrint."""
    # Import inside the function so module import doesn't fail if WeasyPrint
    # system deps are missing (the API surface still loads; the route will
    # 500 with a clear message instead of crashing the whole app at startup).
    try:
        from weasyprint import HTML  # type: ignore
    except Exception as e:  # pragma: no cover
        log.exception("weasyprint import failed")
        raise RuntimeError(
            "WeasyPrint is not available in this environment. Install system "
            "deps: apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b "
            "fonts-noto fonts-lohit-punjabi"
        ) from e

    html = render_html(kind, data)
    return HTML(string=html, base_url=str(PDF_DIR)).write_pdf()

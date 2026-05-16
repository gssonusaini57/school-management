"""PDF rendering pipeline (WeasyPrint + Jinja2).

`render_pdf(kind, data)` is the only public entry point — it validates the
payload via the matching Pydantic schema and returns a bytes blob suitable
for `Response(content=…, media_type="application/pdf")`.

Templates live in ./templates/, brand CSS + fonts under ./assets/.
"""
from .render import render_pdf, SUPPORTED_KINDS

__all__ = ["render_pdf", "SUPPORTED_KINDS"]

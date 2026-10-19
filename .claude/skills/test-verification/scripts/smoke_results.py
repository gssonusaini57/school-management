"""Smoke test for the Results module on a deployed instance (run ON the server).

  sudo -u school-test bash -c 'set -a; . /opt/school-management-test/.env; set +a;
      cd /opt/school-management-test/app && .venv/bin/python /tmp/smoke_results.py'

Tokens are minted locally with the instance's own secret and never printed.
Writes only regenerable rows: one sync render (pdf_cache) and one 2-student
render job (job row + cache rows). The stale-save check is refused by design.
"""
import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models.class_subject import ClassSubject
from app.models.marks import Marks
from app.models.marks_batch import MarksBatch
from app.permissions import DEFAULT_STAFF_MENUS
from app.security import create_token

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001/api"
CLS = "8th"
OTHER = "9th"
outcomes: list[tuple[str, bool]] = []


def tok(role, classes=(), menus=None):
    if menus is None:
        menus = list(DEFAULT_STAFF_MENUS) if role == "staff" else []
    return create_token(sub="0", role=role, name="Smoke Test", allowed_classes=list(classes), allowed_menus=menus)


ADMIN, SUPER = tok("admin"), tok("super_admin")
STAFF = tok("staff", [CLS])
STAFF_OTHER = tok("staff", [OTHER])
STAFF_NO_RESULTS = tok("staff", [CLS], [m for m in DEFAULT_STAFF_MENUS if m != "marks-results"])


def call(method, path, token=None, body=None, raw=False, timeout=120):
    headers = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read()
            if raw:
                return r.status, payload
            return r.status, (json.loads(payload) if payload else None)
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            payload = json.loads(payload)
        except Exception:
            payload = payload[:200]
        return e.code, payload


def check(name, ok, detail=""):
    outcomes.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)


def skip(name, why):
    print(f"SKIP {name}  [{why}]", flush=True)


# ── basics ─────────────────────────────────────────────────────────────
st, body = call("GET", "/health")
check("health", st == 200 and body == {"status": "ok"}, str(st))
st, cur = call("GET", "/sessions/current", STAFF)
check("current session", st == 200 and isinstance(cur, dict) and cur.get("session"), f"{st} {cur.get('session') if isinstance(cur, dict) else cur}")
SESSION = cur["session"] if st == 200 else "2026-27"
st, meta = call("GET", "/meta", STAFF)
check("meta grade letters", st == 200 and meta.get("grade_letters"), f"{st} {meta.get('grade_letters') if st == 200 else meta}")

# ── results table + permissions ────────────────────────────────────────
q = f"/marks/results?class={CLS}&session={SESSION}&scope=term1"
st, res = call("GET", q, ADMIN)
ok = st == 200 and isinstance(res, dict)
check("results term1 (admin)", ok,
      f"{st} students={len(res['students'])} subjects={len(res['subject_columns'])} ranked={res.get('ranked_count')} "
      f"drafts={res.get('has_drafts')} complete={res.get('complete')} warnings={len(res.get('warnings') or [])}" if ok else f"{st} {res}")
for scope in ("term2", "annual"):
    st, r2 = call("GET", f"/marks/results?class={CLS}&session={SESSION}&scope={scope}", ADMIN)
    check(f"results {scope} (admin)", st == 200, f"{st} groups={[g.get('key') for g in r2.get('groups', [])] if st == 200 else r2}")
st, _ = call("GET", q, STAFF)
check("results: class teacher allowed", st == 200, str(st))
st, _ = call("GET", q, STAFF_OTHER)
check("results: other-class teacher refused", st == 403, str(st))
st, _ = call("GET", q, STAFF_NO_RESULTS)
check("results: teacher without the results menu refused", st == 403, str(st))

# ── report-card template, roster, sync render, cache access ────────────
st, tpl = call("GET", f"/pdf/templates/resolve?kind=report-card&class={CLS}&session={SESSION}&scope=term1", STAFF)
check("resolve report-card template", st == 200, f"{st} {'id=' + str(tpl['id']) + ' layout=' + str(tpl.get('layout')) if isinstance(tpl, dict) else tpl}")
if isinstance(tpl, dict):
    tid = tpl["id"]
    st, roster = call("GET", f"/pdf/templates/{tid}/roster", STAFF)
    rows = roster.get("rows") or roster.get("students") or [] if isinstance(roster, dict) else []
    check("roster (class teacher)", st == 200 and rows, f"{st} rows={len(rows)}")
    with_marks = [r["id"] if "id" in r else r.get("student_id") for r in rows if r.get("has_marks")][:2]
    if with_marks:
        st, rr = call("POST", f"/pdf/templates/{tid}/render", STAFF, {"student_ids": with_marks[:1]})
        first = (rr.get("results") or [{}])[0] if st == 200 else {}
        check("sync render 1 card (class teacher)", st == 200 and first.get("status") in ("rendered", "cached"),
              f"{st} {first.get('status')} {first.get('error') or ''}")
        pdf_id = first.get("pdf_id")
        if pdf_id:
            st, pdf = call("GET", f"/pdf/cache/{pdf_id}", STAFF, raw=True)
            check("download cached card", st == 200 and pdf[:4] == b"%PDF", f"{st} {len(pdf) if st == 200 else pdf} bytes")
            st, _ = call("GET", f"/pdf/cache/{pdf_id}", STAFF_OTHER, raw=True)
            check("cached card refused to other-class teacher", st == 403, str(st))
        st, _ = call("POST", f"/pdf/templates/{tid}/render", STAFF, {"student_ids": with_marks[:1], "include_drafts": True})
        check("include_drafts refused to non-super-admin", st == 403, str(st))

        # ── background job + ZIP ────────────────────────────────────────
        st, job = call("POST", f"/pdf/templates/{tid}/render-jobs", ADMIN, {"student_ids": with_marks})
        check("start render job", st == 202, f"{st} {job if st != 202 else 'job ' + str(job['id'])}")
        if st == 202:
            jid, t0 = job["id"], time.time()
            while time.time() - t0 < 120:
                st, job = call("GET", f"/pdf/render-jobs/{jid}", ADMIN)
                if st != 200 or job["status"] in ("done", "failed", "cancelled"):
                    break
                time.sleep(1)
            check("render job finished", st == 200 and job["status"] == "done",
                  f"{job.get('status')} done={job.get('done_count')} errors={job.get('error_count')} in {time.time() - t0:.1f}s")
            st, z = call("GET", f"/pdf/render-jobs/{jid}/zip", ADMIN, raw=True)
            names = zipfile.ZipFile(io.BytesIO(z)).namelist() if st == 200 else []
            check("job ZIP", st == 200 and len(names) == len(with_marks) and all(n.endswith(".pdf") for n in names),
                  f"{st} {names}")
    else:
        skip("render checks", "no student in the roster has marks")
else:
    skip("template checks", "no 8th Term I report-card template on this instance")

# ── stale marks save is refused and writes nothing ─────────────────────
with SessionLocal() as db:
    probe = None
    for cs in db.scalars(select(ClassSubject).where(ClassSubject.class_name == CLS)):
        for comp in cs.components:
            exists = db.scalar(select(func.count()).select_from(MarksBatch).where(
                MarksBatch.class_name == CLS, MarksBatch.subject == cs.subject_name,
                MarksBatch.exam_type == comp.component_name, MarksBatch.session == SESSION))
            if not exists:
                probe = (cs.subject_name, comp.component_name, comp.max_marks)
                break
        if probe:
            break
    before = db.scalar(select(func.count()).select_from(MarksBatch))
if probe:
    subj, comp, mx = probe
    st, body = call("POST", "/marks/batches", STAFF, {
        "class_name": CLS, "subject": subj, "exam_type": comp, "session": SESSION, "max_marks": mx,
        "items": [], "base_batch_id": 999999999})
    with SessionLocal() as db:
        after = db.scalar(select(func.count()).select_from(MarksBatch))
    check("stale marks save refused, nothing written", st == 409 and after == before,
          f"{st} batches {before}->{after} probe={subj}/{comp}")
else:
    skip("stale-save check", "every 8th component already has a batch")

# ── batch revision + old-app guard (every save here is refused; nothing is written) ──
from urllib.parse import urlencode
with SessionLocal() as db:
    b = db.scalar(select(MarksBatch).where(MarksBatch.class_name == CLS, MarksBatch.session == SESSION)
                  .order_by(MarksBatch.id))
    if b is not None:
        bq = dict(class_name=b.class_name, subject=b.subject, exam_type=b.exam_type, session=b.session,
                  max_marks=b.max_marks)
        rows_before = db.scalar(select(func.count()).select_from(Marks).where(Marks.batch_id == b.id))
if b is None:
    skip("revision checks", "no batch for the class yet")
else:
    load = {"class": bq["class_name"], "subject": bq["subject"], "exam_type": bq["exam_type"]}
    st, got = call("GET", "/marks/batches?" + urlencode({**load, "session": bq["session"]}), SUPER)
    rev = got.get("revision") if isinstance(got, dict) else None
    check("batch carries a revision", st == 200 and isinstance(rev, int), f"{st} revision={rev}")
    if isinstance(rev, int):        # only on the new code: on old code these saves would write
        items = [{"student_id": it["student_id"], "marks": it.get("marks"), "grade": it.get("grade")}
                 for it in (got.get("items") or [])]
        st, body = call("POST", "/marks/batches", SUPER,
                        {**bq, "items": items, "base_batch_id": b.id, "base_revision": rev + 1})
        check("stale revision refused (409)", st == 409 and "changed" in json.dumps(body), f"{st} {str(body)[:110]}")
        if len(items) > 1:
            st, body = call("POST", "/marks/batches", SUPER, {**bq, "items": items[1:]})
            check("old app can't remove saved marks (409)", st == 409 and "version of the app" in json.dumps(body),
                  f"{st} {str(body)[:110]}")
        with SessionLocal() as db:
            b2 = db.get(MarksBatch, b.id)
            rows_after = db.scalar(select(func.count()).select_from(Marks).where(Marks.batch_id == b.id))
        check("refused saves wrote nothing", b2.revision == rev and rows_after == rows_before,
              f"revision {rev}->{b2.revision} rows {rows_before}->{rows_after}")
    st, _ = call("GET", "/marks/batches?" + urlencode({**load, "session": "1999-00"}), SUPER)
    check("unknown session refused on load (422)", st == 422, str(st))
st, d = call("GET", "/sessions/defaults?session=2027-28", SUPER)
check("session defaults (super-admin)", st == 200 and isinstance(d, dict) and d.get("term1_start") == "2027-04-01",
      f"{st} {d.get('term1_start') if isinstance(d, dict) else d}")
st, _ = call("GET", "/sessions/defaults?session=2027-28", STAFF)
check("session defaults refused for staff (403)", st == 403, str(st))

failed = [n for n, ok in outcomes if not ok]
print(f"\n{len(outcomes) - len(failed)}/{len(outcomes)} passed" + (f"; failed: {failed}" if failed else ""))
sys.exit(1 if failed else 0)

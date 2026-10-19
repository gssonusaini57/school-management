"""Render sample report cards from a made-up 8th class (no real student data).

Usage: python make_sample.py <snapshot dir containing app/ and factories.py> <out dir>
"""
import base64, io, os, random, sys, tempfile
from datetime import date, timedelta

SNAP, OUT = sys.argv[1], sys.argv[2]
sys.path.insert(0, SNAP)
_tmp = tempfile.mkdtemp(prefix="rc-sample-")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_tmp}/import-only.db"
os.environ.setdefault("JWT_SECRET", "sample-only")
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@compiles(BigInteger, "sqlite")
def _bigint(type_, compiler, **kw):
    return "INTEGER"


@compiles(LONGBLOB, "sqlite")
def _blob(type_, compiler, **kw):
    return "BLOB"


from app.db import Base
from app.models import (  # noqa: F401  every table
    admin, staff, student, document, attendance, marks, fee, notice, pdf_template,
    student_edit_request, class_subject, marks_batch, password_reset, academic_session, pdf_render_job,
)
import factories as F
from app.models.class_subject import ClassSubject, SubjectCategory, SubjectExamComponent
from app.models.marks import Marks
from app.models.marks_batch import MarksBatch, MarksBatchStatus
from app.models.pdf_template import PdfStudentData, TemplateKind
from app.pdf.render import render_pdf
from app.pdf.render_or_cache import report_card_payload
from app.seed.exam_pattern import EXAM_PATTERN_SEED
from app.services.report_cards import gather_class_inputs, safe_photo_jpeg
from app.services.results import grade_for

eng = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(eng)
db = sessionmaker(bind=eng)()
rnd = random.Random(20261019)
CLASS, SESSION = "8th", "2026-27"
F.academic_session(db, SESSION)

# Subjects and exam components exactly as the school's seeded pattern for 8th.
subjects = []
for s in EXAM_PATTERN_SEED:
    if s["class_name"] != CLASS:
        continue
    cs = ClassSubject(class_name=CLASS, subject_name=s["subject_name"], subject_name_pa=s["subject_name_pa"],
                      category=SubjectCategory(s["category"]), order_index=s["order_index"])
    db.add(cs)
    db.flush()
    for c in s["components"]:
        db.add(SubjectExamComponent(class_subject_id=cs.id, component_name=c["component_name"],
                                    max_marks=c["max_marks"], order_index=c["order_index"], term=c["term"]))
    db.flush()
    db.refresh(cs)
    subjects.append(cs)

# 24 made-up students; roll 12 is the sample card.
NAMES = ["Arjun Singh", "Simran Kaur", "Gurpreet Singh", "Navneet Kaur", "Jaspreet Singh", "Manpreet Kaur",
         "Harjot Singh", "Amandeep Kaur", "Karanveer Singh", "Prabhjot Kaur", "Rajveer Singh", "Harpreet Kaur",
         "Sukhman Singh", "Jasleen Kaur", "Ekamjot Singh", "Gurleen Kaur", "Tejbir Singh", "Mehakpreet Kaur",
         "Arshdeep Singh", "Navjot Kaur", "Sahibjeet Singh", "Kirandeep Kaur", "Dilpreet Singh", "Ravneet Kaur"]
students, ability = [], {}
for i, n in enumerate(NAMES, start=1):
    kw = dict(father="Gurmeet Singh", mother="Manjit Kaur", dob=date(2013, 8, 14),
              admission_no=1045, admission_id="KIS/2019/1045") if i == 12 else dict(dob=date(2013, 1 + i % 12, 3 + i))
    s = F.student(db, n, CLASS, str(i), **kw)
    students.append(s)
    ability[s.id] = 0.86 if i == 12 else rnd.uniform(0.52, 0.93)
sample = students[11]

# Submitted marks for every component of both terms (grading subjects get letters).
for cs in subjects:
    for comp in cs.components:
        b = MarksBatch(class_name=CLASS, subject=cs.subject_name, exam_type=comp.component_name, session=SESSION,
                       max_marks=comp.max_marks, status=MarksBatchStatus.submitted, created_by="sample")
        db.add(b)
        db.flush()
        for s in students:
            a = max(0.2, min(1.0, ability[s.id] + rnd.uniform(-0.07, 0.07)))
            if comp.max_marks == 0:
                mk, gr = 0, grade_for(round(a * 100), 100)
            else:
                mk, gr = int(round(a * comp.max_marks)), None
            db.add(Marks(student_id=s.id, batch_id=b.id, class_name=CLASS, exam_type=comp.component_name,
                         subject=cs.subject_name, marks=mk, grade=gr, max_marks=comp.max_marks,
                         session=SESSION, saved_by="sample"))
db.flush()

# Term 1 attendance: Mon-Sat, 1 Apr - 30 Sep 2026, June off (summer vacation), two holidays.
HOLIDAYS = {date(2026, 8, 15), date(2026, 9, 5)}
d, day_no = date(2026, 4, 1), 0
while d <= date(2026, 9, 30):
    if d.weekday() != 6 and d.month != 6:
        if d in HOLIDAYS:
            F.attendance_day(db, CLASS, d, {}, is_holiday=True)
        else:
            day_no += 1
            st = {}
            for s in students:
                if s.id == sample.id:
                    st[s.id] = "A" if day_no in (17, 52, 88, 121) else ("H" if day_no in (33, 97) else "P")
                else:
                    r = rnd.random()
                    st[s.id] = "A" if r < 0.05 else ("H" if r < 0.08 else "P")
            F.attendance_day(db, CLASS, d, st)
    d += timedelta(days=1)

REMARKS = {
    "Term I": {"en": "Harpreet is attentive in class and completes her work on time. Regular practice in "
                     "Mathematics will help her do even better.",
               "pa": "ਹਰਪ੍ਰੀਤ ਕਲਾਸ ਵਿੱਚ ਧਿਆਨ ਦਿੰਦੀ ਹੈ ਅਤੇ ਆਪਣਾ ਕੰਮ ਸਮੇਂ ਸਿਰ ਪੂਰਾ ਕਰਦੀ ਹੈ। ਗਣਿਤ ਦਾ ਨਿਯਮਤ "
                     "ਅਭਿਆਸ ਉਸਨੂੰ ਹੋਰ ਵਧੀਆ ਕਰਨ ਵਿੱਚ ਮਦਦ ਕਰੇਗਾ।"},
    "Annual": {"en": "A steady and sincere year. Harpreet takes part in class discussions with confidence.",
               "pa": "ਸਾਰਾ ਸਾਲ ਲਗਨ ਅਤੇ ਮਿਹਨਤ ਨਾਲ ਪੜ੍ਹਾਈ ਕੀਤੀ। ਹਰਪ੍ਰੀਤ ਕਲਾਸ ਦੀ ਚਰਚਾ ਵਿੱਚ ਭਰੋਸੇ ਨਾਲ ਹਿੱਸਾ ਲੈਂਦੀ ਹੈ।"},
}
for term, remark in REMARKS.items():
    db.add(PdfStudentData(kind=TemplateKind.report_card, student_id=sample.id, session=SESSION, term=term,
                          term_key=term, data={"remarks": remark, "house": "Bhagat Singh"}, updated_by="sample"))
db.flush()

# A neutral grey silhouette standing in for the student's photo.
from PIL import Image, ImageDraw
im = Image.new("RGB", (300, 375), (226, 229, 233))
dr = ImageDraw.Draw(im)
dr.ellipse((95, 70, 205, 180), fill=(168, 174, 182))
dr.ellipse((45, 200, 255, 470), fill=(168, 174, 182))
buf = io.BytesIO(); im.save(buf, "PNG")
photo_uri = "data:image/jpeg;base64," + base64.b64encode(safe_photo_jpeg(buf.getvalue())).decode()


def render(term, scope, layout, fname):
    t = F.report_card_template(db, CLASS, SESSION, term)
    t.scope, t.layout = scope, layout
    db.flush()
    inputs = gather_class_inputs(db, t, include_drafts=False)
    payload, _ = report_card_payload(inputs, sample.id)
    payload["student"]["photoUrl"] = photo_uri
    pdf = render_pdf("report-card", payload)
    path = os.path.join(OUT, fname)
    open(path, "wb").write(pdf)
    s = payload["summary"]
    print(fname, "warnings:", inputs.warnings, "| summary:",
          {k: s.get(k) for k in ("total", "max", "percentage", "grade", "rank", "classSize", "attendancePct", "result", "promotion") if k in s})
    db.delete(t)
    db.flush()


render("Term I", "term1", "components", "sample-term1-each-exam.pdf")
render("Term I", "term1", "summary", "sample-term1-summary.pdf")
render("Annual", "annual", "components", "sample-annual-each-term.pdf")

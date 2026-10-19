"""Migration 0019 clears the values the v1 report-card sheet had teachers type per student."""
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.models.pdf_template import PdfStudentData, TemplateKind

from .factories import student
from .test_migration_0016 import _load

MIGRATION = "0019_clear_v1_card_overrides"
# What the v1 editor saved on prod: hand-typed rank / class size / Att % and an empty co-scholastic list.
V1_ROW = {"coScholasticGrades": [], "remarks": {"en": "Good work", "pa": "ਵਧੀਆ ਕੰਮ"}, "attendancePct": 85,
          "workingDays": None, "daysPresent": None, "rank": 1, "classSize": 8, "promotion": None,
          "house": "Tagore", "admissionNo": "A-12"}
KEPT = {"remarks": {"en": "Good work", "pa": "ਵਧੀਆ ਕੰਮ"}, "promotion": None, "house": "Tagore",
        "admissionNo": "A-12"}
V2_ROW = {"remarks": {"en": "Fine", "pa": None}, "rank": 2, "workingDays": 100, "daysPresent": 90}


def test_the_transform_drops_only_the_v1_hand_typed_values():
    cleared = _load(MIGRATION).cleared_v1_row
    assert cleared(V1_ROW) == KEPT
    assert cleared({"coScholasticGrades": [], "rank": 0, "classSize": 0, "attendancePct": 140}) == {}
    assert cleared(V2_ROW) is None                     # saved by v2: real overrides, left alone
    assert cleared(cleared(V1_ROW)) is None            # a second run changes nothing
    assert cleared(None) is None and cleared([]) is None
    assert V1_ROW["rank"] == 1                         # the input is not modified


def test_upgrade_clears_report_card_rows_the_v1_editor_saved(engine, db):
    a, b, c = (student(db, "Asha Kaur"), student(db, "Ravi Kumar", roll_no="2"),
               student(db, "Simran Kaur", roll_no="3"))
    for s, kind, data in ((a, TemplateKind.report_card, V1_ROW), (b, TemplateKind.report_card, V2_ROW),
                          (c, TemplateKind.pseb_admit_card, {"coScholasticGrades": [], "rank": 1})):
        db.add(PdfStudentData(kind=kind, student_id=s.id, session="2026-27", term="Term I",
                              term_key="Term I", data=data, updated_by="t"))
    db.commit()
    migration = _load(MIGRATION)
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
            migration.upgrade()                        # idempotent
    db.expire_all()
    stored = {r.student_id: r.data for r in db.query(PdfStudentData)}
    assert stored == {a.id: KEPT, b.id: V2_ROW, c.id: {"coScholasticGrades": [], "rank": 1}}

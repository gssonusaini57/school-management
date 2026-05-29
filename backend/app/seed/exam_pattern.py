"""KIS exam pattern seed data — derived from the handwritten exam-pattern sheet
(session 2024-25). Class names match the canonical CLASSES list on the frontend.

Each entry produces one `class_subjects` row plus N `subject_exam_components`
rows underneath it. The seed endpoint refuses to run if any subject already
exists, so re-running is safe (it'll just no-op). Super-admin can edit any
value after seeding.

Sources of the per-class component values:
- NUR        academic: PT1 25 / PT2 25 / Sem1 50 / Oral 20  (×2 terms = 240)
             co-curricular: Drawing 30, Rhymes 20, Conv/GK 20 (per term)
- LKG / UKG  academic: PT1 25 / PT2 25 / Sem1 80 / Oral 20  (×2 terms = 300)
             co-curricular: Drawing 25, EVS (30W+20O) 50, Rhyme 25
- 1st - 5th  academic: PT1 35 / PT2 35 / Sem1 80  (×2 terms = 300)
- 6th - 8th  academic: PT1 35 / PT2 35 / Sem1 80  — Math/Science add Practical 10
             grading subjects: Computer, Phy.Edu, Agri
- 9th-10th   academic: same; Punjabi PT-only is 25; Math/Science have practical 10
             grading subjects: Computer, Phy.Edu
- 11th-12th  academic: same; Phy.Edu = 50W + 30P
             grading subjects: Computer, EVS

Hand-derived from the PDF (handwritten, some ambiguity) — super-admin is
expected to spot-check and edit before relying on these for actual exams.
"""
from typing import TypedDict


class Component(TypedDict):
    component_name: str
    max_marks: int
    order_index: int


class SubjectSeed(TypedDict):
    class_name: str
    subject_name: str
    subject_name_pa: str | None
    category: str          # academic | co_curricular | grading
    order_index: int
    components: list[Component]


def _components(pairs: list[tuple[str, int]]) -> list[Component]:
    """Convert [(name, max_marks), ...] → ordered component dicts."""
    return [
        {"component_name": name, "max_marks": marks, "order_index": idx}
        for idx, (name, marks) in enumerate(pairs, start=1)
    ]


# ── Standard component patterns ───────────────────────────────────
NUR_ACADEMIC_COMPONENTS = _components([
    ("P.T. First", 25), ("P.T. Second", 25),
    ("Semester First", 50), ("Oral I", 20),
    ("P.T. Third", 25), ("P.T. Fourth", 25),
    ("Semester Second", 50), ("Oral II", 20),
])

KG_ACADEMIC_COMPONENTS = _components([
    ("P.T. First", 25), ("P.T. Second", 25),
    ("Semester First", 80), ("Oral I", 20),
    ("P.T. Third", 25), ("P.T. Fourth", 25),
    ("Semester Second", 80), ("Oral II", 20),
])

STANDARD_ACADEMIC_COMPONENTS = _components([
    ("P.T. First", 35), ("P.T. Second", 35),
    ("Semester First", 80),
    ("P.T. Third", 35), ("P.T. Fourth", 35),
    ("Semester Second", 80),
])

# Punjabi class 9th-10th has PT max=25 instead of 35 (note in PDF).
PUNJABI_9_10_COMPONENTS = _components([
    ("P.T. First", 25), ("P.T. Second", 25),
    ("Semester First", 80),
    ("P.T. Third", 25), ("P.T. Fourth", 25),
    ("Semester Second", 80),
])

# Subjects with a practical component (e.g. Maths/Science 6th-10th).
# Written reduces from 80 to 70 and a 10-mark practical is added per term.
PRACTICAL_70_10_COMPONENTS = _components([
    ("P.T. First", 35), ("P.T. Second", 35),
    ("Semester First — Written", 70), ("Semester First — Practical", 10),
    ("P.T. Third", 35), ("P.T. Fourth", 35),
    ("Semester Second — Written", 70), ("Semester Second — Practical", 10),
])

# 11th-12th Phy.Edu: 50 written + 30 practical per term.
PHY_EDU_11_12_COMPONENTS = _components([
    ("P.T. First", 35), ("P.T. Second", 35),
    ("Semester First — Written", 50), ("Semester First — Practical", 30),
    ("P.T. Third", 35), ("P.T. Fourth", 35),
    ("Semester Second — Written", 50), ("Semester Second — Practical", 30),
])

# Grading-only subjects (Computer, Phy.Edu, Agri) — no numeric marks;
# we stub one "Grade" row with max_marks=0 so the UI shows something.
GRADING_COMPONENTS = _components([
    ("Term 1 Grade", 0),
    ("Term 2 Grade", 0),
])

# Per-term single-mark components for co-curricular subjects.
def co_curric_components(per_term_max: int) -> list[Component]:
    return _components([("Term 1", per_term_max), ("Term 2", per_term_max)])


# ── Helpers to build sets of subjects ─────────────────────────────
def _make(
    class_name: str,
    triples: list[tuple[str, str | None, list[Component]]],
    *,
    category: str = "academic",
    order_start: int = 1,
) -> list[SubjectSeed]:
    return [
        {
            "class_name": class_name,
            "subject_name": name,
            "subject_name_pa": pa,
            "category": category,
            "order_index": order_start + i,
            "components": comps,
        }
        for i, (name, pa, comps) in enumerate(triples)
    ]


# ── Per-class subject lists (PDF page 1-4) ────────────────────────
NUR = (
    _make("Nursery", [
        ("Mathematics", "ਗਣਿਤ", NUR_ACADEMIC_COMPONENTS),
        ("Hindi", "ਹਿੰਦੀ", NUR_ACADEMIC_COMPONENTS),
        ("English", "ਅੰਗਰੇਜ਼ੀ", NUR_ACADEMIC_COMPONENTS),
        ("Punjabi", "ਪੰਜਾਬੀ", NUR_ACADEMIC_COMPONENTS),
    ])
    + _make("Nursery", [
        ("Nur Drawing", "ਚਿੱਤਰਕਾਰੀ", co_curric_components(30)),
        ("Rhymes", "ਕਵਿਤਾਵਾਂ", co_curric_components(20)),
        ("Conversation / GK", "ਸੰਵਾਦ / ਜੀ.ਕੇ.", co_curric_components(20)),
    ], category="co_curricular", order_start=10)
)


def _kg(class_name: str) -> list[SubjectSeed]:
    return (
        _make(class_name, [
            ("Mathematics", "ਗਣਿਤ", KG_ACADEMIC_COMPONENTS),
            ("Hindi", "ਹਿੰਦੀ", KG_ACADEMIC_COMPONENTS),
            ("English", "ਅੰਗਰੇਜ਼ੀ", KG_ACADEMIC_COMPONENTS),
            ("Punjabi", "ਪੰਜਾਬੀ", KG_ACADEMIC_COMPONENTS),
        ])
        + _make(class_name, [
            ("Drawing", "ਚਿੱਤਰਕਾਰੀ", co_curric_components(25)),
            ("E.V.S.", "ਵਾਤਾਵਰਣ", _components([
                ("Term 1 — Written", 30), ("Term 1 — Oral", 20),
                ("Term 2 — Written", 30), ("Term 2 — Oral", 20),
            ])),
            ("Rhyme", "ਕਵਿਤਾ", co_curric_components(25)),
        ], category="co_curricular", order_start=10)
    )


LKG = _kg("L.K.G")
UKG = _kg("U.K.G")


def _primary(class_name: str) -> list[SubjectSeed]:
    # Classes 1st-5th: Hindi, Punjabi, English (R), English (G), Maths, EVS as the
    # six scored academic subjects; GK, Drawing, Computer as grading/co-curricular.
    return (
        _make(class_name, [
            ("Hindi", "ਹਿੰਦੀ", STANDARD_ACADEMIC_COMPONENTS),
            ("Punjabi", "ਪੰਜਾਬੀ", STANDARD_ACADEMIC_COMPONENTS),
            ("English (Reader)", "ਅੰਗਰੇਜ਼ੀ (ਰੀਡਰ)", STANDARD_ACADEMIC_COMPONENTS),
            ("English (Grammar)", "ਅੰਗਰੇਜ਼ੀ (ਵਿਆਕਰਨ)", STANDARD_ACADEMIC_COMPONENTS),
            ("Mathematics", "ਗਣਿਤ", STANDARD_ACADEMIC_COMPONENTS),
            ("E.V.S.", "ਵਾਤਾਵਰਣ", STANDARD_ACADEMIC_COMPONENTS),
        ])
        + _make(class_name, [
            ("G.K.", "ਜੀ.ਕੇ.", GRADING_COMPONENTS),
            ("Drawing", "ਚਿੱਤਰਕਾਰੀ", GRADING_COMPONENTS),
            ("Computer", "ਕੰਪਿਊਟਰ", GRADING_COMPONENTS),
        ], category="grading", order_start=10)
    )


def _middle(class_name: str) -> list[SubjectSeed]:
    # 6th-8th: 6 academic (Maths/Science get practical), 3 grading (Comp/Phy.Edu/Agri).
    return (
        _make(class_name, [
            ("Mathematics", "ਗਣਿਤ", PRACTICAL_70_10_COMPONENTS),
            ("English", "ਅੰਗਰੇਜ਼ੀ", STANDARD_ACADEMIC_COMPONENTS),
            ("Hindi", "ਹਿੰਦੀ", STANDARD_ACADEMIC_COMPONENTS),
            ("Punjabi", "ਪੰਜਾਬੀ", STANDARD_ACADEMIC_COMPONENTS),
            ("Science", "ਵਿਗਿਆਨ", PRACTICAL_70_10_COMPONENTS),
            ("Social Studies", "ਸਮਾਜਿਕ ਅਧਿਐਨ", STANDARD_ACADEMIC_COMPONENTS),
        ])
        + _make(class_name, [
            ("Computer", "ਕੰਪਿਊਟਰ", GRADING_COMPONENTS),
            ("Physical Education", "ਸਰੀਰਕ ਸਿੱਖਿਆ", GRADING_COMPONENTS),
            ("Agriculture", "ਖੇਤੀਬਾੜੀ", GRADING_COMPONENTS),
        ], category="grading", order_start=10)
    )


def _secondary(class_name: str) -> list[SubjectSeed]:
    # 9th-10th: Punjabi PT=25, Math/Science practical 70+10; grading Computer/Phy.Edu.
    return (
        _make(class_name, [
            ("Hindi", "ਹਿੰਦੀ", STANDARD_ACADEMIC_COMPONENTS),
            ("Punjabi", "ਪੰਜਾਬੀ", PUNJABI_9_10_COMPONENTS),
            ("Mathematics", "ਗਣਿਤ", PRACTICAL_70_10_COMPONENTS),
            ("English", "ਅੰਗਰੇਜ਼ੀ", STANDARD_ACADEMIC_COMPONENTS),
            ("Science (A)", "ਵਿਗਿਆਨ (ਏ)", PRACTICAL_70_10_COMPONENTS),
            ("Science (B)", "ਵਿਗਿਆਨ (ਬੀ)", PRACTICAL_70_10_COMPONENTS),
            ("Social Studies", "ਸਮਾਜਿਕ ਅਧਿਐਨ", STANDARD_ACADEMIC_COMPONENTS),
        ])
        + _make(class_name, [
            ("Computer", "ਕੰਪਿਊਟਰ", GRADING_COMPONENTS),
            ("Physical Education", "ਸਰੀਰਕ ਸਿੱਖਿਆ", GRADING_COMPONENTS),
        ], category="grading", order_start=10)
    )


def _senior(class_name: str) -> list[SubjectSeed]:
    # 11th-12th: History/Geography/Sociology/Phy.Edu/Punjabi/Maths; Phy.Edu has practical.
    return (
        _make(class_name, [
            ("History", "ਇਤਿਹਾਸ", STANDARD_ACADEMIC_COMPONENTS),
            ("Geography", "ਭੂਗੋਲ", STANDARD_ACADEMIC_COMPONENTS),
            ("Sociology", "ਸਮਾਜ ਸ਼ਾਸਤਰ", STANDARD_ACADEMIC_COMPONENTS),
            ("Physical Education", "ਸਰੀਰਕ ਸਿੱਖਿਆ", PHY_EDU_11_12_COMPONENTS),
            ("Punjabi", "ਪੰਜਾਬੀ", STANDARD_ACADEMIC_COMPONENTS),
            ("Mathematics", "ਗਣਿਤ", STANDARD_ACADEMIC_COMPONENTS),
        ])
        + _make(class_name, [
            ("Computer", "ਕੰਪਿਊਟਰ", GRADING_COMPONENTS),
            ("E.V.S.", "ਵਾਤਾਵਰਣ", GRADING_COMPONENTS),
        ], category="grading", order_start=10)
    )


EXAM_PATTERN_SEED: list[SubjectSeed] = (
    NUR + LKG + UKG
    + _primary("1st") + _primary("2nd") + _primary("3rd") + _primary("4th") + _primary("5th")
    + _middle("6th") + _middle("7th") + _middle("8th")
    + _secondary("9th") + _secondary("10th")
    + _senior("11th") + _senior("12th")
)

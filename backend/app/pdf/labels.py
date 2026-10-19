"""Bilingual labels for the report card: English first, Punjabi beneath.

The first block is copied verbatim from the brand handoff
(_handoff/khalsa-international-handoff/i18n/document-strings.json,
`reportCard.*`). The rest were added for this card; their Punjabi is a draft
for the school to confirm.
"""

REPORT_CARD_LABELS: dict[str, dict[str, str]] = {
    # ── from the handoff ───────────────────────────────────────────────
    "annualTitle": {"en": "Annual Report Card", "pa": "ਸਾਲਾਨਾ ਰਿਪੋਰਟ ਕਾਰਡ"},
    "session": {"en": "Session", "pa": "ਸਾਲ"},
    "studentName": {"en": "Student name", "pa": "ਵਿਦਿਆਰਥੀ ਦਾ ਨਾਮ"},
    "subjectsHead": {"en": "Subjects", "pa": "ਵਿਸ਼ੇ"},
    "marksHead": {"en": "Marks obtained / Max", "pa": "ਅੰਕ / ਵੱਧ ਤੋਂ ਵੱਧ"},
    "gradeHead": {"en": "Grade", "pa": "ਗ੍ਰੇਡ"},
    "totalHead": {"en": "Total", "pa": "ਕੁੱਲ"},
    "percentage": {"en": "Percentage", "pa": "ਪ੍ਰਤੀਸ਼ਤ"},
    "rank": {"en": "Class rank", "pa": "ਕਲਾਸ ਰੈਂਕ"},
    "attendance": {"en": "Attendance", "pa": "ਹਾਜ਼ਰੀ"},
    "remarks": {"en": "Class teacher's remarks", "pa": "ਕਲਾਸ ਟੀਚਰ ਦੀ ਟਿੱਪਣੀ"},
    "promotionStatus": {"en": "Promotion status", "pa": "ਤਰੱਕੀ ਦੀ ਸਥਿਤੀ"},
    "principal": {"en": "Principal", "pa": "ਪ੍ਰਿੰਸੀਪਲ"},
    "parentSign": {"en": "Parent's signature", "pa": "ਮਾਪੇ ਦੇ ਦਸਤਖ਼ਤ"},
    # ── added for this card (Punjabi to be confirmed by the school) ────
    "termTitle": {"en": "Report Card", "pa": "ਰਿਪੋਰਟ ਕਾਰਡ"},
    "father": {"en": "Father's name", "pa": "ਪਿਤਾ ਦਾ ਨਾਮ"},
    "mother": {"en": "Mother's name", "pa": "ਮਾਤਾ ਦਾ ਨਾਮ"},
    "class": {"en": "Class", "pa": "ਜਮਾਤ"},
    "rollNo": {"en": "Roll no.", "pa": "ਰੋਲ ਨੰ."},
    "admissionNo": {"en": "Admission no.", "pa": "ਦਾਖ਼ਲਾ ਨੰ."},
    "dob": {"en": "Date of birth", "pa": "ਜਨਮ ਮਿਤੀ"},
    "house": {"en": "House", "pa": "ਹਾਊਸ"},
    "photo": {"en": "Student photo", "pa": "ਵਿਦਿਆਰਥੀ ਦੀ ਫੋਟੋ"},
    "scholastic": {"en": "Scholastic areas", "pa": "ਸ਼ੈਖਿਕ ਖੇਤਰ"},
    "coScholastic": {"en": "Co-scholastic areas", "pa": "ਸਹਿ-ਸ਼ੈਖਿਕ ਖੇਤਰ"},
    "marks": {"en": "Marks", "pa": "ਅੰਕ"},
    "max": {"en": "Max", "pa": "ਵੱਧ ਤੋਂ ਵੱਧ"},
    # Printed as "1.5 of 2 working days" / "2 ਕੰਮਕਾਜੀ ਦਿਨਾਂ ਵਿੱਚੋਂ 1.5" (oblique ਦਿਨਾਂ before ਵਿੱਚੋਂ).
    "workingDays": {"en": "working days", "pa": "ਕੰਮਕਾਜੀ ਦਿਨਾਂ"},
    "result": {"en": "Result", "pa": "ਨਤੀਜਾ"},
    "gradingScale": {"en": "Grading scale", "pa": "ਗ੍ਰੇਡਿੰਗ ਸਕੇਲ"},
    "classTeacher": {"en": "Class teacher", "pa": "ਕਲਾਸ ਟੀਚਰ"},
    "examIncharge": {"en": "Examination in-charge", "pa": "ਪਰੀਖਿਆ ਇੰਚਾਰਜ"},
    "term1": {"en": "Term 1", "pa": "ਟਰਮ 1"},
    "term2": {"en": "Term 2", "pa": "ਟਰਮ 2"},
    "of": {"en": "of", "pa": "ਵਿੱਚੋਂ"},
    "rankProvisional": {"en": "provisional", "pa": "ਆਰਜ਼ੀ"},
    "provisional": {
        "en": "Provisional: some marks for this term are not yet entered or submitted.",
        "pa": "ਆਰਜ਼ੀ: ਇਸ ਟਰਮ ਦੇ ਕੁਝ ਅੰਕ ਅਜੇ ਦਰਜ ਜਾਂ ਜਮ੍ਹਾਂ ਨਹੀਂ ਹੋਏ।",
    },
}

# Card heading per scope.
SCOPE_TITLES: dict[str, dict[str, str]] = {
    "term1": {"en": "Report Card · Term I", "pa": "ਰਿਪੋਰਟ ਕਾਰਡ · ਟਰਮ 1"},
    "term2": {"en": "Report Card · Term II", "pa": "ਰਿਪੋਰਟ ਕਾਰਡ · ਟਰਮ 2"},
    "annual": REPORT_CARD_LABELS["annualTitle"],
}

# Promotion values (results engine) → wording on the card. "Promoted" uses the handoff string.
PROMOTION_LABELS: dict[str, dict[str, str]] = {
    "Promoted": {"en": "Promoted to next class", "pa": "ਅਗਲੀ ਜਮਾਤ ਵਿੱਚ ਤਰੱਕੀ"},
    "Conditional": {"en": "Promoted conditionally", "pa": "ਸ਼ਰਤੀਆ ਤਰੱਕੀ"},
    "Detained": {"en": "Detained", "pa": "ਰੋਕਿਆ ਗਿਆ"},
}

# Exam column headings on the per-exam ("components") layout.
EXAM_GROUP_PA: dict[str, str] = {
    "P.T. First": "ਪੀ.ਟੀ. ਪਹਿਲਾ",
    "P.T. Second": "ਪੀ.ਟੀ. ਦੂਜਾ",
    "P.T. Third": "ਪੀ.ਟੀ. ਤੀਜਾ",
    "P.T. Fourth": "ਪੀ.ਟੀ. ਚੌਥਾ",
    "Semester First": "ਪਹਿਲਾ ਸਮੈਸਟਰ",
    "Semester Second": "ਦੂਜਾ ਸਮੈਸਟਰ",
    "Oral I": "ਮੌਖਿਕ 1",
    "Oral II": "ਮੌਖਿਕ 2",
    "Term 1": "ਟਰਮ 1",
    "Term 2": "ਟਰਮ 2",
    "Pre-Board": "ਪ੍ਰੀ-ਬੋਰਡ",
    "Both terms": "ਦੋਵੇਂ ਟਰਮ",
}

"""Pydantic schemas mirroring the JSON Schemas in
_handoff/khalsa-international-handoff/documents/schemas/ and the visual
brand reference at _handoff/Khalsa Brand Identity.html.

One model per print kind. The router uses these to validate the request
body before passing the dict into the Jinja template.
"""
from typing import Literal
from datetime import date as DateT
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Bilingual(BaseModel):
    """Most string fields on print docs ship as `{en, pa}` to render side
    by side. The template can pick either or both."""
    en: str
    pa: str


class BilingualOpt(BaseModel):
    """`{en, pa}` where the Punjabi is optional: people's names exist only in
    English in the student register, so a card shouldn't print them twice."""
    en: str
    pa: str | None = None


class Signatory(BaseModel):
    name: str
    role: str | None = None


# ── Fee receipt ──────────────────────────────────────────────────────────
class FeeReceiptStudent(BaseModel):
    name: str
    class_: str = Field(alias="class")
    section: str | None = None
    rollNo: str
    admissionNo: str | None = None
    fatherName: str | None = None

    model_config = {"populate_by_name": True}


class FeeReceiptItem(BaseModel):
    particulars: str
    amount: float = Field(ge=0)


class FeeReceipt(BaseModel):
    receiptNo: str
    date: DateT
    term: str | None = None  # e.g. "July 2026-27" or "Term II · 2025-26"
    student: FeeReceiptStudent
    items: list[FeeReceiptItem] = Field(min_length=1)
    total: float = Field(ge=0)
    amountInWords: str | None = None
    modeOfPayment: Literal["Cash", "UPI", "Bank Transfer", "Cheque", "Card"]
    txnRef: str | None = None
    signatory: Signatory | None = None

    @field_validator("total")
    @classmethod
    def total_matches_items(cls, v, info):
        items = info.data.get("items") or []
        s = sum(float(i.amount) for i in items) if items else 0.0
        if items and abs(v - s) > 0.01:
            raise ValueError(f"total {v} does not match items sum {s}")
        return v


# ── Letterhead — Format A (classic) and Format B (modern) ───────────────
class LetterheadRecipient(BaseModel):
    name: str
    lines: list[str] = Field(default_factory=list)


class Letterhead(BaseModel):
    """Shared shape for both Format A and Format B (the `format` field
    is informational; the template chosen by the URL drives layout)."""
    format: Literal["A", "B"] = "A"
    ref: str
    date: DateT
    recipient: LetterheadRecipient
    subject: Bilingual
    salutation: str
    body: list[str] = Field(min_length=1)
    closing: str
    signatory: Signatory


# Aliases so SCHEMA_BY_KIND can address each.
LetterheadA = Letterhead
LetterheadB = Letterhead


# ── Report card (render payload built by pdf/builder.py) ────────────────
class ReportCardStudent(BaseModel):
    name: BilingualOpt
    class_: str = Field(alias="class")
    rollNo: str | None = None
    fatherName: BilingualOpt
    motherName: BilingualOpt
    dob: DateT | None = None
    house: str | None = None
    admissionNo: str | None = None
    photoUrl: str | None = None   # data: URI of the student's photo, when shown

    model_config = {"populate_by_name": True}


class ReportCardCell(BaseModel):
    """One exam column (or term column on an annual card) for one subject."""
    key: str
    marks: float | None = None    # None = nothing entered for this column yet
    max: float = 0
    status: Literal["complete", "partial", "missing", "none"] = "none"


class ReportCardSubject(BaseModel):
    name: BilingualOpt
    marks: float | None = None    # None = no marks entered in this scope
    max: float
    grade: str | None = None
    status: Literal["complete", "partial", "missing"] = "complete"
    cells: list[ReportCardCell] = Field(default_factory=list)


class ReportCardGroup(BaseModel):
    key: str
    label: BilingualOpt


class ReportCardCoScholastic(BaseModel):
    """A grading subject (Computer, P.E., …) with letters from Marks Entry."""
    name: BilingualOpt
    grade: str | None = None
    term1: str | None = None
    term2: str | None = None


class ReportCardSummary(BaseModel):
    total: float
    max: float
    percentage: float | None = None
    grade: str | None = None
    rank: int | None = None
    classSize: int | None = None
    attendancePct: float | None = None
    workingDays: int | None = None
    daysPresent: float | None = None
    remarks: BilingualOpt | None = None
    promotion: str | None = None
    promotionLabel: BilingualOpt | None = None
    hasDrafts: bool = False
    incomplete: bool = False
    failedSubjects: list[str] = Field(default_factory=list)


class ReportCardSignatures(BaseModel):
    classTeacher: str | None = None
    examIncharge: str | None = None
    principal: str | None = None


class ReportCardOptions(BaseModel):
    showAttendance: bool = True
    showRank: bool = True
    showPhoto: bool = True
    showGradingScale: bool = True


class ReportCard(BaseModel):
    session: str
    term: str | None = None
    scope: Literal["term1", "term2", "annual"] = "annual"
    layout: Literal["summary", "components"] = "summary"
    title: BilingualOpt
    student: ReportCardStudent
    groups: list[ReportCardGroup] = Field(default_factory=list)
    subjects: list[ReportCardSubject] = Field(min_length=1)
    coScholastic: list[ReportCardCoScholastic] = Field(default_factory=list)
    summary: ReportCardSummary
    signatures: ReportCardSignatures | None = None
    options: ReportCardOptions = Field(default_factory=ReportCardOptions)
    labels: dict[str, BilingualOpt] = Field(default_factory=dict)
    gradeLegend: list[dict[str, str]] = Field(default_factory=list)
    generatedOn: DateT | None = None


# ── Salary slip ─────────────────────────────────────────────────────────
class SalarySlipEmployee(BaseModel):
    id: str
    name: str
    designation: str
    department: str | None = None
    doj: DateT | None = None
    pan: str | None = None
    contact: str | None = None
    address: str | None = None


class SalarySlipBank(BaseModel):
    accountNo: str | None = None
    ifsc: str | None = None
    bankName: str | None = None
    txnId: str | None = None


class SalarySlipEarnings(BaseModel):
    basic: float = 0
    hra: float = 0
    da: float = 0
    conveyance: float = 0
    special: float = 0


class SalarySlipDeductions(BaseModel):
    pf: float = 0
    esi: float = 0
    tds: float = 0
    profTax: float = 0
    advance: float = 0


class SalarySlip(BaseModel):
    month: str  # YYYY-MM
    issuedDate: DateT | None = None
    employee: SalarySlipEmployee
    workingDays: int | None = None
    daysPresent: int | None = None
    leavesTaken: int | None = None
    leaveType: str | None = None
    earnings: SalarySlipEarnings
    deductions: SalarySlipDeductions
    netPay: float
    netPayWords: str | None = None
    bank: SalarySlipBank | None = None
    signatory: Signatory | None = None


# ── PSEB admit card ─────────────────────────────────────────────────────
class PsebCentre(BaseModel):
    code: str
    schoolCode: str
    district: str
    set: str
    name: Bilingual


class PsebCandidate(BaseModel):
    rollNo: str
    regNo: str
    name: Bilingual
    fatherName: Bilingual
    motherName: Bilingual
    dob: DateT
    differentlyAbled: str | None = "N.A."
    category: str = "Regular"
    photoUrl: str | None = None


class PsebDateSheetRow(BaseModel):
    subCode: str
    subject: Bilingual
    theoryDate: str  # already in DD-MM-YYYY format from caller
    practical: str   # "Yes" | "No"


class PsebAdmitCard(BaseModel):
    schoolCode: str
    studentId: str
    centre: PsebCentre
    candidate: PsebCandidate
    examTime: Bilingual
    practicalDateRange: dict | None = None  # {from, to}
    dateSheet: list[PsebDateSheetRow] = Field(min_length=1)
    instructions: list[Bilingual] = Field(default_factory=list)
    examName: str | None = None  # e.g. "PSEB Class X — Annual 2026"
    printedOn: DateT | None = None
    documentId: str | None = None


SCHEMA_BY_KIND: dict[str, type[BaseModel]] = {
    "fee-receipt":     FeeReceipt,
    "letterhead-a":    LetterheadA,
    "letterhead-b":    LetterheadB,
    "report-card":     ReportCard,
    "pseb-admit-card": PsebAdmitCard,
    "salary-slip":     SalarySlip,
}


# ── Template + per-student split (used by /api/pdf/templates flow) ──────
# These validate the JSON columns on `pdf_templates.data` and
# `pdf_student_data.data`. The full ReportCard / PsebAdmitCard models
# above stay as-is — they're what builder.py produces by merging
# (template, student row, student-data, marks).


# Report card — class-level settings (one row per class × session × term).
# Marks, rank, class size, attendance and promotion are computed; this holds
# only what the school decides per class. Unknown keys from the v1 shape
# (coScholasticHeads, gradingScale, promotionDefault) are dropped on save.
class ReportCardPromotionRule(BaseModel):
    passPct: float = Field(default=33.0, ge=0, le=100)
    conditionalMaxFails: int = Field(default=2, ge=0, le=20)


class ReportCardTemplateData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    signatures: ReportCardSignatures = Field(default_factory=ReportCardSignatures)
    showAttendance: bool = True
    showRank: bool = True
    showPhoto: bool = True
    showGradingScale: bool = True
    includeDrafts: bool = False      # print marks whose batch is still a draft
    promotionRule: ReportCardPromotionRule = Field(default_factory=ReportCardPromotionRule)
    remarksDefault: BilingualOpt | None = None   # printed when a student has no remark


# Report card — per student. Remarks and house are entered by the class
# teacher; every other field is an optional override of a computed value.
class ReportCardStudentData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    remarks: BilingualOpt | None = None
    house: str | None = Field(default=None, max_length=40)
    rank: int | None = Field(default=None, ge=1)
    classSize: int | None = Field(default=None, ge=1)
    attendancePct: float | None = Field(default=None, ge=0, le=100)
    workingDays: int | None = Field(default=None, ge=0)
    daysPresent: float | None = Field(default=None, ge=0)
    promotion: str | None = Field(default=None, max_length=60)
    admissionNo: str | None = Field(default=None, max_length=40)


# PSEB admit card — class-level
class PsebAdmitCardTemplateData(BaseModel):
    schoolCode: str
    centre: PsebCentre
    examTime: Bilingual
    practicalDateRange: dict | None = None  # {from, to}
    dateSheet: list[PsebDateSheetRow] = Field(min_length=1)
    instructions: list[Bilingual] = Field(default_factory=list)
    examName: str | None = None  # e.g. "PSEB Class X — Annual 2026"


# PSEB admit card — per-student (PSEB-specific identifiers not on Student row)
class PsebAdmitCardStudentData(BaseModel):
    rollNo: str
    regNo: str
    category: str = "Regular"
    differentlyAbled: str = "N.A."


TEMPLATE_SCHEMA_BY_KIND: dict[str, type[BaseModel]] = {
    "report-card":     ReportCardTemplateData,
    "pseb-admit-card": PsebAdmitCardTemplateData,
}

STUDENT_DATA_SCHEMA_BY_KIND: dict[str, type[BaseModel]] = {
    "report-card":     ReportCardStudentData,
    "pseb-admit-card": PsebAdmitCardStudentData,
}

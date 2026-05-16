"""Pydantic schemas mirroring the JSON Schemas in
_handoff/khalsa-international-handoff/documents/schemas/ and the visual
brand reference at _handoff/Khalsa Brand Identity.html.

One model per print kind. The router uses these to validate the request
body before passing the dict into the Jinja template.
"""
from typing import Literal
from datetime import date as DateT
from pydantic import BaseModel, Field, field_validator


class Bilingual(BaseModel):
    """Most string fields on print docs ship as `{en, pa}` to render side
    by side. The template can pick either or both."""
    en: str
    pa: str


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


# ── Report card ─────────────────────────────────────────────────────────
class ReportCardStudent(BaseModel):
    name: Bilingual
    class_: str = Field(alias="class")
    section: str
    rollNo: str
    fatherName: Bilingual
    motherName: Bilingual
    dob: DateT
    house: str | None = None
    admissionNo: str | None = None
    photoUrl: str | None = None

    model_config = {"populate_by_name": True}


class ReportCardSubject(BaseModel):
    name: Bilingual
    marks: float
    max: float = 100
    grade: str | None = None


class ReportCardSummary(BaseModel):
    total: float
    max: float
    percentage: float
    rank: int | None = None
    classSize: int | None = None
    attendancePct: float | None = None
    workingDays: int | None = None
    daysPresent: int | None = None
    remarks: Bilingual | None = None
    promotion: str | None = None


class ReportCardSignatures(BaseModel):
    classTeacher: str | None = None
    examIncharge: str | None = None
    principal: str | None = None


class ReportCard(BaseModel):
    session: str
    term: str | None = None  # e.g. "Term II"
    student: ReportCardStudent
    subjects: list[ReportCardSubject] = Field(min_length=1)
    coScholastic: list[dict] = Field(default_factory=list)  # [{name, grade}]
    summary: ReportCardSummary
    signatures: ReportCardSignatures | None = None


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


# Report card — class-level (one row per kind × class × session × term)
class ReportCardCoScholasticHead(BaseModel):
    name: Bilingual


class ReportCardGradingScaleRow(BaseModel):
    grade: str
    range: str  # e.g. "91–100"


class ReportCardTemplateData(BaseModel):
    signatures: ReportCardSignatures = Field(default_factory=ReportCardSignatures)
    coScholasticHeads: list[ReportCardCoScholasticHead] = Field(default_factory=list)
    gradingScale: list[ReportCardGradingScaleRow] | None = None
    promotionDefault: str | None = None  # template-level default; student data can override


# Report card — per-student (everything that varies per student except marks)
class ReportCardCoScholasticGrade(BaseModel):
    head: str  # matches a name from the template's coScholasticHeads (en)
    grade: str


class ReportCardStudentData(BaseModel):
    coScholasticGrades: list[ReportCardCoScholasticGrade] = Field(default_factory=list)
    remarks: Bilingual | None = None
    attendancePct: float | None = None
    workingDays: int | None = None
    daysPresent: int | None = None
    rank: int | None = None
    classSize: int | None = None
    promotion: str | None = None
    house: str | None = None
    admissionNo: str | None = None


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

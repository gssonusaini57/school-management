package `in`.kisschool.ui.screens.studentedit

import `in`.kisschool.data.api.dto.StudentDto
import `in`.kisschool.data.api.dto.StudentUpdateDto
import java.util.Calendar

/**
 * Form model + validation for the Edit Student screen. Mirrors the web portal's
 * StudentDetail edit mode exactly (same required fields, same regexes, same
 * Title-Case / digits-only / "N/A"-sentinel transforms, same DOB bounds).
 */

val CLASSES: List<String> = listOf(
    "Nursery", "L.K.G", "U.K.G",
    "1st", "2nd", "3rd", "4th", "5th", "6th",
    "7th", "8th", "9th", "10th", "11th", "12th",
)

val RELIGIONS: List<String> = listOf(
    "Hindu", "Muslim", "Sikh", "Christian", "Jain", "Buddhist", "Parsi", "Other",
)

val GENDERS: List<String> = listOf("Male", "Female", "Other")

/** Every editable field as an editable string (empty = unset). */
data class StudentForm(
    val className: String = "",
    val admissionNo: String = "",
    val rollNo: String = "",
    val name: String = "",
    val father: String = "",
    val mother: String = "",
    val gender: String = "",
    val dob: String = "",
    val phone: String = "",
    val altPhone: String = "",
    val aadhar: String = "",
    val village: String = "",
    val religion: String = "",
    val prevSchool: String = "",
    val bankName: String = "",
    val bankAcc: String = "",
    val bankIfsc: String = "",
    val annualFee: String = "",
)

fun digitsOnly(s: String): String = s.replace(Regex("\\D+"), "")

/** Unicode-aware Title Case, matching the web `toTitleCase`. */
fun toTitleCase(s: String): String {
    val collapsed = s.replace(Regex("\\s+"), " ").trim().lowercase()
    return Regex("(^|[\\s\\-'])(\\p{L})").replace(collapsed) { m ->
        m.groupValues[1] + m.groupValues[2].uppercase()
    }
}

/** DOB must fall between (today − 25 years) and today, ISO yyyy-MM-dd — same as web. */
fun dobBounds(): Pair<String, String> {
    fun iso(c: Calendar) = "%04d-%02d-%02d".format(
        c.get(Calendar.YEAR), c.get(Calendar.MONTH) + 1, c.get(Calendar.DAY_OF_MONTH)
    )
    val today = Calendar.getInstance()
    val earliest = Calendar.getInstance().apply { add(Calendar.YEAR, -25) }
    return iso(earliest) to iso(today)
}

/** Build the form initial state from a loaded student (display nulls/"N/A" as blank). */
fun StudentDto.toForm(): StudentForm {
    fun show(v: String?): String = if (v.isNullOrBlank() || v == "N/A") "" else v
    // annual_fee comes back like "0.00" / "5000.00" — show whole rupees, blank for zero/none.
    val fee = annualFee?.toBigDecimalOrNull()
    val feeStr = if (fee == null || fee.signum() == 0) "" else fee.toBigInteger().toString()
    return StudentForm(
        className = className,
        admissionNo = admissionNo?.toString() ?: "",
        rollNo = rollNo ?: "",
        name = name,
        father = show(father),
        mother = show(mother),
        gender = gender ?: "",
        dob = dob ?: "",
        phone = phone ?: "",
        altPhone = show(altPhone),
        aadhar = aadhar ?: "",
        village = show(village),
        religion = show(religion),
        prevSchool = show(prevSchool),
        bankName = show(bankName),
        bankAcc = show(bankAcc),
        bankIfsc = show(bankIfsc),
        annualFee = feeStr,
    )
}

/** Field-level validation, mirroring the web `validate()`. Returns field→message. */
fun StudentForm.validate(): Map<String, String> {
    val e = mutableMapOf<String, String>()
    if (className.isBlank()) e["class_name"] = "Pick a class"
    if (admissionNo.isBlank() || admissionNo.toIntOrNull() == null) e["admission_no"] = "Required"
    if (rollNo.trim().isBlank()) e["roll_no"] = "Required"
    if (name.trim().isBlank()) e["name"] = "Required"
    if (father.trim().isBlank()) e["father"] = "Required"
    if (mother.trim().isBlank()) e["mother"] = "Required"
    if (gender.isBlank()) e["gender"] = "Pick a gender"
    if (dob.isBlank()) {
        e["dob"] = "Required"
    } else {
        val (min, max) = dobBounds()
        if (dob < min || dob > max) e["dob"] = "Must be between $min and $max"
    }
    if (!Regex("^\\d{10}$").matches(phone)) e["phone"] = "Must be exactly 10 digits"
    if (altPhone.isNotBlank() && !Regex("^\\d{10}$").matches(altPhone)) {
        e["alt_phone"] = "Must be exactly 10 digits"
    }
    if (!Regex("^\\d{12}$").matches(aadhar)) e["aadhar"] = "Must be exactly 12 digits"
    return e
}

/** Convert the validated form into the PATCH body (apply Title-Case + "N/A" sentinels). */
fun StudentForm.toUpdateDto(): StudentUpdateDto {
    fun na(v: String): String = v.trim().ifBlank { "N/A" }
    return StudentUpdateDto(
        name = toTitleCase(name),
        father = toTitleCase(father),
        mother = toTitleCase(mother),
        dob = dob,
        gender = gender,
        village = village.trim(),
        phone = phone,
        aadhar = aadhar,
        altPhone = na(altPhone),
        religion = na(religion),
        prevSchool = na(prevSchool),
        bankName = na(bankName),
        bankAcc = na(bankAcc),
        bankIfsc = bankIfsc.trim().uppercase().ifBlank { "N/A" },
        annualFee = annualFee.trim().ifBlank { null },
        className = className,
        admissionNo = admissionNo.toIntOrNull(),
        rollNo = rollNo.trim(),
    )
}

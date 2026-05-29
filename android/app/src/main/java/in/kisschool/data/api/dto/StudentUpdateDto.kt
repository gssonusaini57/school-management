package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/**
 * Body for PATCH /students/{id}. Mirrors the backend `StudentUpdate` schema —
 * only the staff/admin-editable fields. The server computes the diff against the
 * current row, so sending the full set is fine: unchanged fields produce no diff.
 *
 * For a staff (non-super-admin) user the PATCH is queued as a `student_edit_request`
 * for super-admin approval rather than applied directly; the response carries
 * `pending_edit_request_id` in that case.
 */
data class StudentUpdateDto(
    val name: String,
    val father: String,
    val mother: String,
    val dob: String,
    val gender: String,
    val village: String?,
    val phone: String,
    val aadhar: String,
    @SerializedName("alt_phone") val altPhone: String?,
    val religion: String?,
    @SerializedName("prev_school") val prevSchool: String?,
    @SerializedName("bank_name") val bankName: String?,
    @SerializedName("bank_acc") val bankAcc: String?,
    @SerializedName("bank_ifsc") val bankIfsc: String?,
    @SerializedName("annual_fee") val annualFee: String?,
    @SerializedName("class_name") val className: String,
    @SerializedName("admission_no") val admissionNo: Int?,
    @SerializedName("roll_no") val rollNo: String
)

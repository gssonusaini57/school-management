package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

data class StudentDto(
    val id: Long,
    val name: String,
    val father: String? = null,
    val mother: String? = null,
    val dob: String? = null,
    val gender: String? = null,
    val phone: String? = null,
    val aadhar: String? = null,
    val village: String? = null,
    @SerializedName("alt_phone") val altPhone: String? = null,
    val religion: String? = null,
    @SerializedName("prev_school") val prevSchool: String? = null,
    @SerializedName("bank_name") val bankName: String? = null,
    @SerializedName("bank_acc") val bankAcc: String? = null,
    @SerializedName("bank_ifsc") val bankIfsc: String? = null,
    @SerializedName("annual_fee") val annualFee: String? = null,
    @SerializedName("class_name") val className: String,
    @SerializedName("admission_no") val admissionNo: Int? = null,
    @SerializedName("admission_id") val admissionId: String? = null,
    @SerializedName("roll_no") val rollNo: String? = null,
    @SerializedName("created_at") val createdAt: String? = null,
    @SerializedName("added_by") val addedBy: String? = null,
    @SerializedName("updated_at") val updatedAt: String? = null,
    @SerializedName("updated_by") val updatedBy: String? = null,
    @SerializedName("has_photo") val hasPhoto: Boolean = false,
    @SerializedName("has_dob_cert") val hasDobCert: Boolean = false,
    @SerializedName("has_aadhar") val hasAadhar: Boolean = false,
    // Soft-delete workflow: `status` is "active" | "pending_delete" | "deleted".
    // The reason/requester surface in the detail-screen "Deletion requested" banner.
    val status: String = "active",
    @SerializedName("delete_reason") val deleteReason: String? = null,
    @SerializedName("delete_requested_at") val deleteRequestedAt: String? = null,
    @SerializedName("delete_requested_by") val deleteRequestedBy: String? = null,
    // Edit-approval workflow: when a staff/admin edit is queued, the server returns the
    // pending request id. Non-super-admin users (the only kind in this app) must wait for
    // super-admin approval, so a non-null value here locks further edits.
    @SerializedName("has_pending_edit") val hasPendingEdit: Boolean = false,
    @SerializedName("pending_edit_request_id") val pendingEditRequestId: Long? = null,
    @SerializedName("pending_edit_requested_by") val pendingEditRequestedBy: String? = null,
    @SerializedName("pending_edit_requested_at") val pendingEditRequestedAt: String? = null
)

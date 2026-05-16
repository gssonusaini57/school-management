package com.expressonly.kisattendance.data.api.dto

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
    @SerializedName("created_at") val createdAt: String? = null,
    @SerializedName("added_by") val addedBy: String? = null,
    @SerializedName("updated_at") val updatedAt: String? = null,
    @SerializedName("updated_by") val updatedBy: String? = null,
    @SerializedName("has_photo") val hasPhoto: Boolean = false,
    @SerializedName("has_dob_cert") val hasDobCert: Boolean = false,
    @SerializedName("has_aadhar") val hasAadhar: Boolean = false
)

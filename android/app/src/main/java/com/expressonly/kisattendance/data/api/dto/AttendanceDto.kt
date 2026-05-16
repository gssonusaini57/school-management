package com.expressonly.kisattendance.data.api.dto

import com.google.gson.annotations.SerializedName

data class AttendanceDto(
    @SerializedName("class_name") val className: String,
    val date: String,
    val records: Map<String, String>
)

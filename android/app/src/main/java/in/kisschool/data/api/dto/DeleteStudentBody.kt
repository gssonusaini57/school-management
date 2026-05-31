package `in`.kisschool.data.api.dto

/**
 * Optional body for DELETE /students/{id}. Mirrors the web portal's delete
 * dialog: a free-text reason that's attached to the deletion request. For a
 * staff/admin user the server marks the student `pending_delete` for super-admin
 * approval rather than removing it.
 */
data class DeleteStudentBody(val reason: String? = null)

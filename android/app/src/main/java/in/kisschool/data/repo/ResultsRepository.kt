package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.ClassResultsDto
import java.util.Objects

/** Term-scoped class results (GET /marks/results). */
class ResultsRepository(private val api: ApiService) {

    /**
     * Results for a class, session and scope (term1 | term2 | annual).
     * Failures come back as [ApiException] with a message fit for the screen.
     */
    suspend fun classResults(className: String, session: String, scope: String): ClassResultsDto {
        val resp = api.classResults(className, session, scope)
        if (resp.isSuccessful) {
            val body = resp.body() ?: throw ApiException("The server sent no results.")
            if (body.hasNullHoles()) {
                throw ApiException("The server sent results this app can't read. Please update the app.")
            }
            return body
        }
        val detail = resp.apiError().message
        throw when (resp.code()) {
            // A missing menu grant says so itself; "Class not in scope" reads better per class.
            403 -> ApiException(detail.menuGrantDenial() ?: "You don't have access to results for $className.", 403)
            404 -> FeatureUnavailableException("Results aren't available on this server yet.")
            else -> ApiException(detail ?: "Couldn't load results (HTTP ${resp.code()})", resp.code())
        }
    }

    /**
     * Gson writes an explicit JSON null into a field even when its Kotlin type is
     * non-null. The API never sends null for these lists and names, but check once
     * here so a malformed reply becomes a message instead of a crash while the
     * table is drawn.
     */
    private fun ClassResultsDto.hasNullHoles(): Boolean =
        absent(className) || absent(session) || absent(scope) ||
            absent(subjectColumns) || absent(students) || absent(groups) || absent(warnings) ||
            subjectColumns.any { absent(it) || absent(it.subjectName) || absent(it.category) || absent(it.batchStatus) || absent(it.components) } ||
            students.any { st ->
                absent(st) || absent(st.name) || absent(st.subjects) || absent(st.failedSubjects) ||
                    st.subjects.any { sub ->
                        absent(sub) || absent(sub.subjectName) || absent(sub.status) || absent(sub.batchStatus) ||
                            absent(sub.components) || absent(sub.cells) || absent(sub.termLetters) ||
                            sub.components.any { c -> absent(c) || absent(c.componentName) }
                    }
            }

    /** A null check the compiler can't drop for a non-null type (it is a plain call). */
    private fun absent(value: Any?): Boolean = Objects.isNull(value)
}

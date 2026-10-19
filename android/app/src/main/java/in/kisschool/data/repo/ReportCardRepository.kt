package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.PdfTemplateDto
import `in`.kisschool.data.api.dto.RenderRequestBody
import `in`.kisschool.data.api.dto.RenderResultDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.util.concurrent.ConcurrentHashMap

/** A report card saved on the phone, plus what the server noted while making it. */
data class ReportCardFile(val file: File, val warnings: List<String>)

/**
 * Report cards for one student at a time: find the class template for a session
 * and scope, have the server render (or reuse) the card, and save the PDF to
 * cacheDir/pdfs/<studentId>/ under the server's file name for the preview / share
 * screen.
 *
 * The PDF is fetched with the normal Bearer header (GET /pdf/cache/{id}); the
 * `?token=` URL variant is never used, so the JWT is never in a URL. Rendering
 * and the download go through [renderApi], the same API with a longer read
 * timeout, because a first render can take a while on the server.
 */
class ReportCardRepository(
    private val api: ApiService,
    private val renderApi: ApiService,
    cacheDir: File,
) {
    private val pdfDir = File(cacheDir, PDF_DIR)
    private val warningsByStudent = ConcurrentHashMap<Long, List<String>>()

    /** A student's folder under the FileProvider "pdfs" cache path; it holds their latest card. */
    private fun dirFor(studentId: Long): File = File(pdfDir, studentId.toString())

    /**
     * Where a student's card is saved: the one PDF in their folder, named the way the
     * server names it (e.g. report-card_5th_12_Name.pdf), because FileProvider hands
     * that name to the app a card is shared with. A path that doesn't exist yet when
     * no card has been saved.
     */
    fun fileFor(studentId: Long): File =
        dirFor(studentId).listFiles()?.firstOrNull { it.isFile && it.name.endsWith(".pdf") }
            ?: File(dirFor(studentId), defaultName(studentId))

    /** Notes from the last render of this student's card (e.g. draft marks left out). */
    fun warningsFor(studentId: Long): List<String> = warningsByStudent[studentId].orEmpty()

    /**
     * The report-card template for class + session + scope, or null when none has
     * been made yet. Throws [FeatureUnavailableException] on a server that predates
     * the lookup endpoint: there "resolve" lands on GET /pdf/templates/{id}, which
     * answers 422 (not an id) to admins and 403 "Admin only" to staff.
     */
    suspend fun resolveTemplate(className: String, session: String, scope: String): PdfTemplateDto? {
        val resp = api.resolveTemplate(className, session, scope)
        if (resp.isSuccessful) return resp.body()?.takeIf { it.id > 0 }
        throw when (resp.code()) {
            403 -> {
                val detail = resp.apiError().message
                if (detail == "Admin only") FeatureUnavailableException(NEEDS_UPDATE)
                else ApiException(detail.menuGrantDenial() ?: "You don't have access to report cards for $className.", 403)
            }
            404, 405, 422 -> FeatureUnavailableException(NEEDS_UPDATE)
            else -> ApiException(
                resp.apiError().message ?: "Couldn't check for a report-card template (HTTP ${resp.code()})",
                resp.code(),
            )
        }
    }

    /** Render one student's card (or reuse the cached one); returns the row with its pdf id. */
    suspend fun render(templateId: Long, studentId: Long): RenderResultDto {
        val resp = renderApi.renderTemplate(templateId, RenderRequestBody(studentIds = listOf(studentId)))
        if (!resp.isSuccessful) {
            throw when (resp.code()) {
                403 -> ApiException(
                    resp.apiError().message.menuGrantDenial() ?: "You don't have access to this student's report card.",
                    403,
                )
                404 -> ApiException("The report-card template was removed. Refresh and try again.", 404)
                else -> ApiException(
                    resp.apiError().message ?: "Couldn't make the report card (HTTP ${resp.code()})",
                    resp.code(),
                )
            }
        }
        val rows = resp.body()?.results.orEmpty()
        val row = rows.firstOrNull { it.studentId == studentId } ?: rows.firstOrNull()
            ?: throw ApiException("The server didn't return a report card.")
        val pdfId = row.pdfId
        if (row.status == "error" || pdfId == null || pdfId <= 0) {
            throw ApiException(row.error?.takeIf { it.isNotBlank() } ?: "Couldn't make the report card.")
        }
        return row
    }

    /** Stream a rendered PDF into the student's folder (see [fileFor]) and return the file. */
    suspend fun download(pdfId: Long, studentId: Long): File {
        val resp = renderApi.downloadCachedPdf(pdfId)
        if (!resp.isSuccessful) {
            throw when (resp.code()) {
                403 -> ApiException(
                    resp.apiError().message.menuGrantDenial() ?: "You don't have access to this student's report card.",
                    403,
                )
                404 -> ApiException("The report card wasn't found on the server. Try again.", 404)
                else -> ApiException(
                    resp.apiError().message ?: "Couldn't download the report card (HTTP ${resp.code()})",
                    resp.code(),
                )
            }
        }
        val body = resp.body() ?: throw ApiException("The server sent an empty file.")
        val name = cardFileName(resp.headers()["Content-Disposition"], studentId)
        return withContext(Dispatchers.IO) {
            body.use { b ->
                pruneOldFiles()     // first: it also drops folders it leaves empty
                val dir = dirFor(studentId)
                if (!dir.isDirectory && !dir.mkdirs()) throw ApiException("Couldn't save the report card on this phone.")
                val target = File(dir, name)
                val part = File(dir, "$name.part")
                try {
                    // Write next to the target first so a half-finished download is never opened.
                    part.outputStream().use { out -> b.byteStream().use { it.copyTo(out) } }
                    if (!looksLikePdf(part)) throw ApiException("The server didn't send a PDF.")
                    // One card per student; the previous one may have had another name.
                    dir.listFiles()?.forEach { if (it != part) it.delete() }
                    if (!part.renameTo(target)) part.copyTo(target, overwrite = true)
                    target
                } finally {
                    part.delete()       // no-op once renamed
                }
            }
        }
    }

    /** Render then download one student's card. */
    suspend fun prepare(templateId: Long, studentId: Long): ReportCardFile {
        val row = render(templateId, studentId)
        val file = download(row.pdfId ?: 0L, studentId)
        warningsByStudent[studentId] = row.warnings.filter { it.isNotBlank() }
        return ReportCardFile(file, warningsFor(studentId))
    }

    private fun looksLikePdf(f: File): Boolean = try {
        val head = ByteArray(5)
        val n = f.inputStream().use { it.read(head) }
        n == 5 && String(head, Charsets.US_ASCII) == "%PDF-"
    } catch (_: Exception) {
        false
    }

    /**
     * The card's name from Content-Disposition (`inline; filename="report-card_5th_12_Name.pdf"`,
     * pdf_filename in the backend), cut down to letters, digits, dot, dash and underscore so
     * it can't leave the student's folder; report-card-<id>.pdf when there is none.
     */
    private fun cardFileName(contentDisposition: String?, studentId: Long): String {
        val raw = contentDisposition?.let { FILENAME_PARAM.find(it)?.groupValues?.get(1) }?.trim().orEmpty()
        val safe = raw.replace(UNSAFE_CHARS, "-").take(MAX_NAME_CHARS)
        val base = (if (safe.endsWith(".pdf", ignoreCase = true)) safe.dropLast(4) else safe).trim('-', '.', '_')
        return if (base.isEmpty()) defaultName(studentId) else "$base.pdf"
    }

    private fun defaultName(studentId: Long): String = "report-card-$studentId.pdf"

    /** Drop cards older than a day, and the folders they leave empty, so the cache doesn't grow with every student opened. */
    private fun pruneOldFiles() {
        val cutoff = System.currentTimeMillis() - MAX_AGE_MS
        pdfDir.listFiles()?.forEach { f ->
            if (f.isDirectory) {
                f.listFiles()?.forEach { c -> if (c.lastModified() < cutoff) c.delete() }
                if (f.list().isNullOrEmpty()) f.delete()
            } else if (f.lastModified() < cutoff) {
                f.delete()
            }
        }
    }

    private companion object {
        const val NEEDS_UPDATE = "Report cards in the app need the latest server update."
        /** Must match <cache-path name="pdfs" path="pdfs/"/> in res/xml/file_paths.xml. */
        const val PDF_DIR = "pdfs"
        const val MAX_AGE_MS = 24 * 60 * 60 * 1000L
        const val MAX_NAME_CHARS = 120
        /** The plain `filename=` parameter of Content-Disposition, quoted or not. */
        val FILENAME_PARAM = Regex("filename\\s*=\\s*\"?([^\";]+)\"?", RegexOption.IGNORE_CASE)
        val UNSAFE_CHARS = Regex("[^A-Za-z0-9._-]+")
    }
}

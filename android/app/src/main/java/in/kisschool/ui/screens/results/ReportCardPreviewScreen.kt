package `in`.kisschool.ui.screens.results

import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.ParcelFileDescriptor
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.OpenInNew
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import `in`.kisschool.BuildConfig
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.components.LoadingRow
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sqrt

/** Same authority as the <provider> in AndroidManifest.xml (${applicationId}.fileprovider). */
private val FILE_PROVIDER_AUTHORITY = BuildConfig.APPLICATION_ID + ".fileprovider"

/** A report card is one or two pages; the caps only guard memory on an odd file. */
private const val MAX_PAGES = 12
/** Pixels across all page bitmaps together (~48 MB at 4 bytes a pixel). */
private const val PIXEL_BUDGET = 12_000_000

private sealed interface PreviewState {
    data object Loading : PreviewState
    data class Ready(val pages: List<ImageBitmap>) : PreviewState
    data class Failed(val message: String) : PreviewState
}

/**
 * Shows a downloaded report card (cacheDir/pdfs/…) page by page, drawn with the
 * platform PdfRenderer, with Share and Open-with actions that hand other apps a
 * FileProvider content:// URI (read permission granted per intent, nothing else
 * in the cache is exposed).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportCardPreviewScreen(
    file: File,
    studentName: String,
    warnings: List<String>,
    onBack: () -> Unit,
) {
    val ctx = LocalContext.current
    val density = LocalDensity.current
    val screenWidthPx = with(density) { LocalConfiguration.current.screenWidthDp.dp.roundToPx() }
    // Render at the screen's width (bounded) so text stays crisp without huge bitmaps.
    val targetWidth = screenWidthPx.coerceIn(480, 1600)

    val state by produceState<PreviewState>(PreviewState.Loading, file, targetWidth) {
        value = try {
            PreviewState.Ready(renderPages(file, targetWidth).map { it.asImageBitmap() })
        } catch (e: CancellationException) {
            throw e
        } catch (e: OutOfMemoryError) {
            PreviewState.Failed("Not enough memory to show the report card here. Use \"Open with\" instead.")
        } catch (e: Exception) {
            PreviewState.Failed("Couldn't open the report card. Go back and try again.")
        }
    }
    var actionError by remember { mutableStateOf<String?>(null) }
    val canShare = file.exists() && state !is PreviewState.Failed

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Report card")
                        if (studentName.isNotBlank()) {
                            Text(studentName, style = MaterialTheme.typography.labelMedium)
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { actionError = sharePdf(ctx, file, studentName) }, enabled = canShare) {
                        Icon(Icons.Default.Share, contentDescription = "Share")
                    }
                    IconButton(onClick = { actionError = openPdfWith(ctx, file) }, enabled = canShare) {
                        Icon(Icons.AutoMirrored.Filled.OpenInNew, contentDescription = "Open with")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary,
                ),
            )
        }
    ) { padding ->
        LazyColumn(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .background(MaterialTheme.colorScheme.surfaceVariant),
            contentPadding = PaddingValues(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            warnings.filter { it.isNotBlank() }.takeIf { it.isNotEmpty() }?.let { notes ->
                item {
                    Box(
                        Modifier
                            .fillMaxWidth()
                            .background(MaterialTheme.colorScheme.tertiaryContainer, RoundedCornerShape(8.dp))
                            .padding(12.dp)
                    ) {
                        Text(
                            notes.joinToString("\n"),
                            color = MaterialTheme.colorScheme.onTertiaryContainer,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            }
            actionError?.let { msg -> item { ErrorBanner(msg) } }
            when (val st = state) {
                PreviewState.Loading -> item { LoadingRow() }
                is PreviewState.Failed -> item {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        ErrorBanner(st.message)
                        Button(onClick = onBack) { Text("Back") }
                    }
                }
                is PreviewState.Ready -> itemsIndexed(st.pages) { i, page ->
                    Image(
                        bitmap = page,
                        contentDescription = "Page ${i + 1} of ${st.pages.size}",
                        contentScale = ContentScale.FillWidth,
                        modifier = Modifier
                            .fillMaxWidth()
                            .aspectRatio(page.width.toFloat() / page.height.coerceAtLeast(1))
                            .background(Color.White),
                    )
                }
            }
        }
    }
}

/**
 * Draws every page of [file] into a white bitmap at most [maxWidth] px wide. Runs
 * on the IO dispatcher; PdfRenderer allows one open page at a time, so pages go in
 * order. The renderer and its file descriptor are closed on every path (closing
 * the renderer also closes the descriptor it owns; the outer use covers the case
 * where the PdfRenderer constructor itself throws).
 */
private suspend fun renderPages(file: File, maxWidth: Int): List<Bitmap> = withContext(Dispatchers.IO) {
    ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
        PdfRenderer(fd).use { renderer ->
            val count = renderer.pageCount.coerceAtMost(MAX_PAGES)
            if (count <= 0) throw IllegalArgumentException("PDF has no pages")
            val pixelsPerPage = PIXEL_BUDGET / count
            (0 until count).map { index ->
                renderer.openPage(index).use { page ->
                    val aspect = page.height.toFloat() / page.width.coerceAtLeast(1)
                    // Shrink only when a long document would blow the memory budget.
                    val width = min(maxWidth, sqrt(pixelsPerPage / aspect).toInt()).coerceAtLeast(200)
                    val height = (width * aspect).roundToInt().coerceAtLeast(1)
                    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                    bitmap.eraseColor(android.graphics.Color.WHITE)     // PDF pages are transparent by default
                    page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    bitmap
                }
            }
        }
    }
}

private fun contentUri(ctx: Context, file: File): Uri =
    FileProvider.getUriForFile(ctx, FILE_PROVIDER_AUTHORITY, file)

/** Share sheet (WhatsApp, Gmail, Drive, …). Returns an error message, or null when it opened. */
private fun sharePdf(ctx: Context, file: File, studentName: String): String? = try {
    val uri = contentUri(ctx, file)
    val send = Intent(Intent.ACTION_SEND).apply {
        type = "application/pdf"
        putExtra(Intent.EXTRA_STREAM, uri)
        if (studentName.isNotBlank()) putExtra(Intent.EXTRA_SUBJECT, "Report card — $studentName")
        // ClipData carries the grant through the chooser to the app picked.
        clipData = ClipData.newRawUri("", uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    ctx.startActivity(Intent.createChooser(send, "Share report card"))
    null
} catch (_: ActivityNotFoundException) {
    "No app on this phone can share a PDF."
} catch (_: Exception) {
    "Couldn't share the report card."
}

/**
 * Open the PDF in a viewer app (Android asks which one when there's no default).
 * Started directly, not through a chooser: the chooser itself always exists, so
 * with no PDF viewer installed it only says "No apps can perform this action" and
 * the message below never shows. Returns an error message, or null when it opened.
 */
private fun openPdfWith(ctx: Context, file: File): String? = try {
    val uri = contentUri(ctx, file)
    val view = Intent(Intent.ACTION_VIEW).apply {
        setDataAndType(uri, "application/pdf")
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    ctx.startActivity(view)
    null
} catch (_: ActivityNotFoundException) {
    "No app on this phone can open a PDF. Install a PDF viewer, or use Share."
} catch (_: Exception) {
    "Couldn't open the report card in another app."
}

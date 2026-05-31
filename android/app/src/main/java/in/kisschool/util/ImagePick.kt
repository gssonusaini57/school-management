package `in`.kisschool.util

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import androidx.core.content.FileProvider
import androidx.exifinterface.media.ExifInterface
import `in`.kisschool.BuildConfig
import java.io.ByteArrayOutputStream
import java.io.File
import kotlin.math.max
import kotlin.math.roundToInt

/**
 * Helpers for the student-document picker: create a camera capture target and
 * downscale/re-encode picked or captured images before upload.
 *
 * Mirrors the web portal's client-side compression (`lib/compress.ts`) — student
 * documents are stored as a MySQL LONGBLOB, so shrinking a multi-megapixel phone
 * photo to a ~1280px JPEG keeps rows small and avoids OOM while decoding.
 */
object ImagePick {
    private const val MAX_DIM = 1280
    private const val JPEG_QUALITY = 82
    private const val FILEPROVIDER_AUTHORITY_SUFFIX = ".fileprovider"

    /**
     * Create a fresh file under cacheDir/captures and a FileProvider content://
     * uri the system camera app can write to. Return both so the caller can keep
     * the uri to read back after `TakePicture` reports success.
     */
    fun newCaptureTarget(context: Context): Uri {
        val dir = File(context.cacheDir, "captures").apply { mkdirs() }
        // nanoTime keeps names unique across rapid retakes without a Date dep.
        val file = File(dir, "capture_${System.nanoTime()}.jpg")
        return FileProvider.getUriForFile(
            context,
            BuildConfig.APPLICATION_ID + FILEPROVIDER_AUTHORITY_SUFFIX,
            file,
        )
    }

    /**
     * Decode [uri], downscale so the long edge is <= [MAX_DIM], correct EXIF
     * orientation, and re-encode as JPEG. Returns the JPEG bytes, or null if the
     * source can't be decoded as an image (caller can fall back to raw bytes,
     * e.g. for a PDF document).
     */
    fun compressToJpeg(context: Context, uri: Uri): ByteArray? {
        val cr = context.contentResolver

        // 1) Bounds-only pass to choose a sub-sample factor (no full decode yet).
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        cr.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null

        var sample = 1
        val longest = max(bounds.outWidth, bounds.outHeight)
        // Cap the sample factor as a defensive bound against pathological metadata.
        while (longest / sample > MAX_DIM * 2 && sample < 32) sample *= 2

        val opts = BitmapFactory.Options().apply { inSampleSize = sample }
        var bmp = cr.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opts) }
            ?: return null

        // Transform inside try/finally: recycle each superseded bitmap so rapid
        // retakes don't accumulate native memory, and fall back to raw bytes
        // (return null) if a transform throws/OOMs on a low-memory device.
        return try {
            // 2) Precise scale to the target long edge.
            val scale = MAX_DIM.toFloat() / max(bmp.width, bmp.height)
            if (scale < 1f) {
                val w = (bmp.width * scale).roundToInt().coerceAtLeast(1)
                val h = (bmp.height * scale).roundToInt().coerceAtLeast(1)
                val scaled = Bitmap.createScaledBitmap(bmp, w, h, true)
                if (scaled !== bmp) { bmp.recycle(); bmp = scaled }
            }

            // 3) Rotate per EXIF — phone cameras frequently store sideways pixels
            //    with an orientation tag instead of rotating the bitmap itself.
            val rotation = readExifRotation(context, uri)
            if (rotation != 0f) {
                val m = Matrix().apply { postRotate(rotation) }
                val rotated = Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, m, true)
                if (rotated !== bmp) { bmp.recycle(); bmp = rotated }
            }

            ByteArrayOutputStream().use { out ->
                bmp.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, out)
                out.toByteArray()
            }
        } catch (e: Exception) {
            null
        } finally {
            bmp.recycle()
        }
    }

    private fun readExifRotation(context: Context, uri: Uri): Float = try {
        context.contentResolver.openInputStream(uri)?.use { input ->
            when (ExifInterface(input).getAttributeInt(
                ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL
            )) {
                ExifInterface.ORIENTATION_ROTATE_90 -> 90f
                ExifInterface.ORIENTATION_ROTATE_180 -> 180f
                ExifInterface.ORIENTATION_ROTATE_270 -> 270f
                else -> 0f
            }
        } ?: 0f
    } catch (_: Exception) {
        0f
    }
}

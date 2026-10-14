package app.pdftoolkit.mobile

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import android.util.LruCache
import java.io.File

/** A small picture of a file (first page of a PDF, a photo) and, for PDFs, how many pages it has. */
class FileThumb(val bitmap: Bitmap?, val pages: Int)

object FileThumbs {
    private val cache = LruCache<String, FileThumb>(90)

    /** Runs on a background thread. Returns null for files without a picture. */
    fun load(f: File, px: Int): FileThumb? {
        val key = "${f.path}|${f.lastModified()}|$px"
        cache.get(key)?.let { return it }
        val t = when (kindOf(f)) {
            Kind.PDF -> pdf(f, px)
            Kind.IMAGE -> image(f, px)
            else -> null
        } ?: return null
        cache.put(key, t)
        return t
    }

    private fun pdf(f: File, px: Int): FileThumb? = runCatching {
        ParcelFileDescriptor.open(f, ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
            PdfRenderer(fd).use { r ->
                val n = r.pageCount
                if (n == 0) FileThumb(null, 0)
                else r.openPage(0).use { p ->
                    val h = (px.toFloat() * p.height / p.width).toInt().coerceAtLeast(1)
                    val bmp = Bitmap.createBitmap(px, h, Bitmap.Config.ARGB_8888)
                    bmp.eraseColor(Color.WHITE)
                    p.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    FileThumb(bmp, n)
                }
            }
        }
    }.getOrNull()

    private fun image(f: File, px: Int): FileThumb? = runCatching {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(f.path, bounds)
        var sample = 1
        while (bounds.outWidth / (sample * 2) >= px && bounds.outHeight / (sample * 2) >= px) sample *= 2
        val bmp = BitmapFactory.decodeFile(f.path, BitmapFactory.Options().apply { inSampleSize = sample })
        FileThumb(bmp, 0)
    }.getOrNull()
}

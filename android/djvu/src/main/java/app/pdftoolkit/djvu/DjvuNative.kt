package app.pdftoolkit.djvu

import android.graphics.Bitmap

/** DjVuLibre, compiled into a small native library, behind a few simple calls. */
object DjvuNative {
    init { System.loadLibrary("djvubridge") }

    @JvmStatic external fun open(path: String): Long
    @JvmStatic external fun pageCount(handle: Long): Int
    @JvmStatic external fun pageInfo(handle: Long, page: Int, out: IntArray): Int
    @JvmStatic external fun render(handle: Long, page: Int, w: Int, h: Int, argb: IntArray): Int
    @JvmStatic external fun close(handle: Long)
}

/** A DjVu file opened from a real file path. */
class DjvuDocument(path: String) : AutoCloseable {
    private val handle = DjvuNative.open(path).also { if (it == 0L) error("This DjVu file cannot be opened") }
    val pageCount: Int get() = DjvuNative.pageCount(handle)

    /** (width px, height px, dpi) of the page at its own resolution. */
    fun info(page: Int): Triple<Int, Int, Int> {
        val o = IntArray(3)
        if (DjvuNative.pageInfo(handle, page, o) != 0) error("Page ${page + 1} of the DjVu file is damaged")
        return Triple(o[0], o[1], o[2].coerceAtLeast(30))
    }

    fun render(page: Int, w: Int, h: Int): Bitmap {
        val px = IntArray(w * h)
        if (DjvuNative.render(handle, page, w, h, px) != 0) error("Page ${page + 1} of the DjVu file could not be drawn")
        return Bitmap.createBitmap(px, w, h, Bitmap.Config.ARGB_8888)
    }

    override fun close() = DjvuNative.close(handle)
}

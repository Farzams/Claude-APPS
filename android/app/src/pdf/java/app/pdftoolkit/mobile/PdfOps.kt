package app.pdftoolkit.mobile

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.provider.OpenableColumns
import androidx.documentfile.provider.DocumentFile
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.io.MemoryUsageSetting
import com.tom_roush.pdfbox.multipdf.PDFMergerUtility
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.pdmodel.PDPage
import com.tom_roush.pdfbox.pdmodel.PDPageContentStream
import com.tom_roush.pdfbox.pdmodel.common.PDRectangle
import com.tom_roush.pdfbox.pdmodel.encryption.AccessPermission
import com.tom_roush.pdfbox.pdmodel.encryption.StandardProtectionPolicy
import com.tom_roush.pdfbox.pdmodel.font.PDType1Font
import com.tom_roush.pdfbox.pdmodel.graphics.image.JPEGFactory
import com.tom_roush.pdfbox.pdmodel.graphics.image.LosslessFactory
import com.tom_roush.pdfbox.pdmodel.graphics.state.PDExtendedGraphicsState
import com.tom_roush.pdfbox.util.Matrix
import java.io.File
import java.io.InputStream
import java.io.OutputStream

/** One page of the document being organised: which source page, and how far it was turned. */
data class PageItem(val index: Int, val turn: Int = 0)

/** The PDF operations behind the tool screens. Everything here runs on a background thread. */
object PdfOps {
    fun init(ctx: Context) = PDFBoxResourceLoader.init(ctx.applicationContext)

    fun nameOf(ctx: Context, uri: Uri): String =
        ctx.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
            if (it.moveToFirst()) it.getString(0) else null
        } ?: (uri.lastPathSegment ?: "file")

    fun sizeOf(ctx: Context, uri: Uri): Long =
        ctx.contentResolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use {
            if (it.moveToFirst() && !it.isNull(0)) it.getLong(0) else -1L
        } ?: -1L

    private fun input(ctx: Context, uri: Uri): InputStream =
        ctx.contentResolver.openInputStream(uri) ?: error("Cannot open ${nameOf(ctx, uri)}")

    fun load(ctx: Context, uri: Uri, password: String = ""): PDDocument =
        input(ctx, uri).use { PDDocument.load(it, password, MemoryUsageSetting.setupMainMemoryOnly()) }

    fun pageCount(ctx: Context, uri: Uri, password: String = ""): Int = load(ctx, uri, password).use { it.numberOfPages }

    /** "1-3, 5, 8-" -> [[0,1,2],[4],[7..last]] (one list per comma-separated part, zero-based). */
    fun parseRanges(spec: String, n: Int): List<List<Int>> {
        val out = ArrayList<List<Int>>()
        for (part in spec.split(',', ';', '،')) {
            val p = part.trim()
            if (p.isEmpty()) continue
            val bits = p.split('-', '–').map { it.trim() }
            val a = bits[0].ifEmpty { "1" }.toIntOrNull() ?: error("Not a page number: $p")
            val b = if (bits.size == 1) a else (bits[1].ifEmpty { n.toString() }.toIntOrNull() ?: error("Not a page number: $p"))
            if (a < 1 || b < a || b > n) error("Pages out of range (1-$n): $p")
            out.add((a - 1..b - 1).toList())
        }
        if (out.isEmpty()) error("Type the pages you want, for example 1-3, 5")
        return out
    }

    fun merge(ctx: Context, uris: List<Uri>, out: OutputStream) {
        val streams = uris.map { input(ctx, it) }
        try {
            val m = PDFMergerUtility()
            streams.forEach { m.addSource(it) }
            m.destinationStream = out
            m.mergeDocuments(MemoryUsageSetting.setupMainMemoryOnly())
        } finally {
            streams.forEach { runCatching { it.close() } }
        }
    }

    /** New document made of the given source pages (zero-based), each optionally turned. */
    fun build(ctx: Context, uri: Uri, items: List<PageItem>, out: OutputStream, password: String = "") {
        load(ctx, uri, password).use { src ->
            PDDocument().use { dst ->
                for (it in items) {
                    val page = dst.importPage(src.getPage(it.index))
                    if (it.turn != 0) page.rotation = ((page.rotation + it.turn) % 360 + 360) % 360
                }
                dst.save(out)
            }
        }
    }

    fun extract(ctx: Context, uri: Uri, pages: List<Int>, out: OutputStream) =
        build(ctx, uri, pages.map { PageItem(it) }, out)

    /** Writes each range as its own file into [folder]. Returns the number of files. */
    fun splitToFolder(ctx: Context, uri: Uri, ranges: List<List<Int>>, folder: Uri): Int {
        val dir = DocumentFile.fromTreeUri(ctx, folder) ?: error("Cannot open that folder")
        val base = nameOf(ctx, uri).removeSuffix(".pdf").removeSuffix(".PDF")
        load(ctx, uri).use { src ->
            for ((i, r) in ranges.withIndex()) {
                val label = if (r.size == 1) "p${r[0] + 1}" else "p${r.first() + 1}-${r.last() + 1}"
                val file = dir.createFile("application/pdf", "${base}_$label.pdf") ?: error("Cannot create a file in that folder")
                PDDocument().use { dst ->
                    for (idx in r) dst.importPage(src.getPage(idx))
                    (ctx.contentResolver.openOutputStream(file.uri) ?: error("Cannot write")).use { dst.save(it) }
                }
            }
        }
        return ranges.size
    }

    fun protect(ctx: Context, uri: Uri, userPassword: String, out: OutputStream) {
        load(ctx, uri).use { doc ->
            val policy = StandardProtectionPolicy(userPassword, userPassword, AccessPermission())
            policy.encryptionKeyLength = 128
            policy.setPreferAES(true)
            doc.protect(policy)
            doc.save(out)
        }
    }

    fun unprotect(ctx: Context, uri: Uri, password: String, out: OutputStream) {
        load(ctx, uri, password).use { doc ->
            doc.isAllSecurityToBeRemoved = true
            doc.save(out)
        }
    }

    private fun <T> withRenderer(ctx: Context, uri: Uri, block: (PdfRenderer) -> T): T {
        val pfd = ctx.contentResolver.openFileDescriptor(uri, "r") ?: error("Cannot open ${nameOf(ctx, uri)}")
        pfd.use {
            val r = PdfRenderer(it)
            try {
                return block(r)
            } finally {
                r.close()
            }
        }
    }

    private fun renderPage(r: PdfRenderer, i: Int, scale: Float): Bitmap {
        r.openPage(i).use { p ->
            val w = (p.width * scale).toInt().coerceAtLeast(1)
            val h = (p.height * scale).toInt().coerceAtLeast(1)
            val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
            bmp.eraseColor(Color.WHITE)
            p.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
            return bmp
        }
    }

    private fun addPicture(doc: PDDocument, bmp: Bitmap, widthPt: Float, heightPt: Float, quality: Float) {
        val page = PDPage(PDRectangle(widthPt, heightPt))
        doc.addPage(page)
        val img = JPEGFactory.createFromImage(doc, bmp, quality)
        PDPageContentStream(doc, page).use { it.drawImage(img, 0f, 0f, widthPt, heightPt) }
    }

    /** Re-draws every page as a JPEG picture. Much smaller, but the text is no longer selectable. */
    fun compress(ctx: Context, uri: Uri, dpi: Int, quality: Float, out: OutputStream) {
        withRenderer(ctx, uri) { r ->
            PDDocument().use { doc ->
                for (i in 0 until r.pageCount) {
                    val (wPt, hPt) = r.openPage(i).use { it.width.toFloat() to it.height.toFloat() }
                    val bmp = renderPage(r, i, dpi / 72f)
                    addPicture(doc, bmp, wPt, hPt, quality)
                    bmp.recycle()
                }
                doc.save(out)
            }
        }
    }

    fun picturesToPdf(ctx: Context, uris: List<Uri>, out: OutputStream) {
        PDDocument().use { doc ->
            for (u in uris) {
                val opts = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                input(ctx, u).use { BitmapFactory.decodeStream(it, null, opts) }
                var sample = 1
                while (opts.outWidth / sample > 2400) sample *= 2
                val dec = BitmapFactory.Options().apply { inSampleSize = sample }
                val bmp = input(ctx, u).use { BitmapFactory.decodeStream(it, null, dec) } ?: error("Not a picture: ${nameOf(ctx, u)}")
                val wPt = 595f
                val hPt = wPt * bmp.height / bmp.width
                addPicture(doc, bmp, wPt, hPt, 0.85f)
                bmp.recycle()
            }
            doc.save(out)
        }
    }

    fun pdfToPictures(ctx: Context, uri: Uri, folder: Uri, png: Boolean, dpi: Int = 150): Int {
        val dir = DocumentFile.fromTreeUri(ctx, folder) ?: error("Cannot open that folder")
        val base = nameOf(ctx, uri).removeSuffix(".pdf").removeSuffix(".PDF")
        return withRenderer(ctx, uri) { r ->
            for (i in 0 until r.pageCount) {
                val bmp = renderPage(r, i, dpi / 72f)
                val file = dir.createFile(if (png) "image/png" else "image/jpeg", "${base}_${i + 1}.${if (png) "png" else "jpg"}")
                    ?: error("Cannot create a file in that folder")
                (ctx.contentResolver.openOutputStream(file.uri) ?: error("Cannot write")).use {
                    bmp.compress(if (png) Bitmap.CompressFormat.PNG else Bitmap.CompressFormat.JPEG, 92, it)
                }
                bmp.recycle()
            }
            r.pageCount
        }
    }

    /** Page thumbnails for the organiser; one renderer is kept open and guarded by a lock. */
    class Thumbs(ctx: Context, uri: Uri) : AutoCloseable {
        private val pfd = ctx.contentResolver.openFileDescriptor(uri, "r") ?: error("Cannot open the file")
        private val renderer = PdfRenderer(pfd)
        val count: Int get() = renderer.pageCount

        @Synchronized
        fun get(i: Int, widthPx: Int): Bitmap {
            renderer.openPage(i).use { p ->
                val h = (widthPx.toFloat() * p.height / p.width).toInt().coerceAtLeast(1)
                val bmp = Bitmap.createBitmap(widthPx, h, Bitmap.Config.ARGB_8888)
                bmp.eraseColor(Color.WHITE)
                p.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                return bmp
            }
        }

        @Synchronized
        override fun close() {
            runCatching { renderer.close() }
            runCatching { pfd.close() }
        }
    }

    /** The text drawn by Android itself (so Persian and other scripts join correctly), on a transparent picture. */
    private fun textBitmap(text: String, color: Int): Bitmap {
        val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply { textSize = 180f; this.color = color; isSubpixelText = true }
        val w = paint.measureText(text).toInt().coerceAtLeast(8) + 40
        val fm = paint.fontMetrics
        val h = (fm.descent - fm.ascent).toInt() + 40
        val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        Canvas(bmp).drawText(text, 20f, 20f - fm.ascent, paint)
        return bmp
    }

    fun watermark(ctx: Context, uri: Uri, text: String, opacity: Float, sizeFraction: Float, angle: Float, color: Int, out: OutputStream) {
        load(ctx, uri).use { doc ->
            val bmp = textBitmap(text, color)
            val img = LosslessFactory.createFromImage(doc, bmp)
            val gs = PDExtendedGraphicsState()
            gs.setNonStrokingAlphaConstant(opacity)
            gs.setStrokingAlphaConstant(opacity)
            for (page in doc.pages) {
                val box = page.mediaBox
                val cx = box.lowerLeftX + box.width / 2f
                val cy = box.lowerLeftY + box.height / 2f
                val w = box.width * sizeFraction
                val h = w * bmp.height / bmp.width
                PDPageContentStream(doc, page, PDPageContentStream.AppendMode.APPEND, true, true).use { cs ->
                    cs.saveGraphicsState()
                    cs.setGraphicsStateParameters(gs)
                    cs.transform(Matrix.getTranslateInstance(cx, cy))
                    cs.transform(Matrix.getRotateInstance(Math.toRadians(angle.toDouble()), 0f, 0f))
                    cs.drawImage(img, -w / 2f, -h / 2f, w, h)
                    cs.restoreGraphicsState()
                }
            }
            bmp.recycle()
            doc.save(out)
        }
    }

    /** format: "n" = 1, "n/N" = 1 / 12, "page" = Page 1 of 12. top/right: where the number goes. */
    fun numberPages(ctx: Context, uri: Uri, format: String, top: Boolean, align: Int, start: Int, fontSize: Float, out: OutputStream) {
        load(ctx, uri).use { doc ->
            val total = doc.numberOfPages
            val font = PDType1Font.HELVETICA
            for ((i, page) in doc.pages.withIndex()) {
                val n = start + i
                val label = when (format) { "n/N" -> "$n / ${start + total - 1}"; "page" -> "Page $n of ${start + total - 1}"; else -> "$n" }
                val box = page.mediaBox
                val tw = font.getStringWidth(label) / 1000f * fontSize
                val margin = 28f
                val x = when (align) { 0 -> box.lowerLeftX + margin; 2 -> box.upperRightX - margin - tw; else -> box.lowerLeftX + (box.width - tw) / 2f }
                val y = if (top) box.upperRightY - margin - fontSize else box.lowerLeftY + margin
                PDPageContentStream(doc, page, PDPageContentStream.AppendMode.APPEND, true, true).use { cs ->
                    cs.beginText()
                    cs.setFont(font, fontSize)
                    cs.setNonStrokingColor(60, 60, 60)
                    cs.newLineAtOffset(x, y)
                    cs.showText(label)
                    cs.endText()
                }
            }
            doc.save(out)
        }
    }

    fun cacheFile(ctx: Context, name: String): File = File(ctx.cacheDir, name)
}

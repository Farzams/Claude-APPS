package app.pdftoolkit.mobile

import android.content.Context
import android.content.res.Resources
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.BitmapDrawable
import android.graphics.drawable.Drawable
import android.graphics.pdf.PdfDocument
import android.net.Uri
import android.text.Html
import android.text.Layout
import android.text.Spanned
import android.text.SpannableString
import android.text.StaticLayout
import android.text.TextPaint
import android.util.Base64
import app.pdftoolkit.djvu.DjvuDocument
import com.tom_roush.pdfbox.pdmodel.PDDocument
import java.io.File
import java.io.OutputStream
import java.net.URLDecoder
import java.util.zip.ZipInputStream
import javax.xml.parsers.DocumentBuilderFactory
import org.w3c.dom.Element
import org.w3c.dom.Node

/** Books and documents to PDF: EPUB, FB2, CBZ, TXT, HTML and DjVu. Text is laid out with Android's own text engine, so Persian and other scripts join correctly. */
object DocConvert {
    val KINDS = mapOf(
        "epub" to "EPUB", "fb2" to "FB2", "cbz" to "CBZ", "txt" to "TXT", "html" to "HTML", "htm" to "HTML", "xhtml" to "HTML",
        "djvu" to "DjVu", "djv" to "DjVu",
    )

    fun kindOf(name: String): String? = KINDS[name.substringAfterLast('.', "").lowercase()]

    fun convert(ctx: Context, uri: Uri, name: String, out: OutputStream) {
        when (kindOf(name)) {
            "EPUB" -> epub(ctx, uri, out)
            "FB2" -> fb2(ctx, uri, out)
            "CBZ" -> cbz(ctx, uri, out)
            "TXT" -> txt(ctx, uri, out)
            "HTML" -> html(ctx, uri, out)
            "DjVu" -> djvu(ctx, uri, out)
            else -> error("This kind of file is not supported: $name")
        }
    }

    // ------------------------------------------------------------------ page writer

    private const val PAGE_W = 595
    private const val PAGE_H = 842
    private const val MARGIN = 54f

    private class Writer {
        val doc = PdfDocument()
        private var page: PdfDocument.Page? = null
        private var y = MARGIN
        private var number = 0
        val contentW = PAGE_W - 2 * MARGIN
        val contentH = PAGE_H - 2 * MARGIN
        val paint = TextPaint(TextPaint.ANTI_ALIAS_FLAG).apply { textSize = 11f; color = Color.BLACK; typeface = Typeface.SERIF }

        private fun startPage() {
            page?.let { doc.finishPage(it) }
            number++
            page = doc.startPage(PdfDocument.PageInfo.Builder(PAGE_W, PAGE_H, number).create())
            y = MARGIN
        }

        fun breakPage() { if (page != null && y > MARGIN) startPage() }

        fun add(text: CharSequence) {
            if (text.isBlank() && text.none { it == '\uFFFC' }) return
            val layout = StaticLayout.Builder.obtain(text, 0, text.length, paint, contentW.toInt())
                .setAlignment(Layout.Alignment.ALIGN_NORMAL)
                .setLineSpacing(0f, 1.22f)
                .setIncludePad(false)
                .build()
            if (page == null) startPage()
            var line = 0
            while (line < layout.lineCount) {
                val avail = PAGE_H - MARGIN - y
                val top = layout.getLineTop(line)
                var end = line
                while (end < layout.lineCount && layout.getLineBottom(end) - top <= avail) end++
                if (end == line) {
                    if (y > MARGIN + 1f) { startPage(); continue }
                    end = line + 1                                           // a line taller than a page: draw it anyway
                }
                val bottom = layout.getLineBottom(end - 1)
                val c = page!!.canvas
                c.save()
                c.translate(MARGIN, y - top)
                c.clipRect(0f, top.toFloat(), contentW, bottom.toFloat())
                layout.draw(c)
                c.restore()
                y += (bottom - top)
                line = end
                if (line < layout.lineCount) startPage()
            }
            y += 4f
        }

        fun finish(out: OutputStream) {
            if (page == null) startPage()
            page?.let { doc.finishPage(it) }
            doc.writeTo(out)
            doc.close()
        }
    }

    // ------------------------------------------------------------------ HTML helpers

    private fun decodeBitmap(bytes: ByteArray, maxW: Int): Bitmap? {
        val o = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, o)
        var s = 1
        while (o.outWidth / s > maxW * 2) s *= 2
        return BitmapFactory.decodeByteArray(bytes, 0, bytes.size, BitmapFactory.Options().apply { inSampleSize = s })
    }

    private fun drawableFor(src: String, dir: File?, w: Writer): Drawable? {
        val bytes = runCatching {
            if (src.startsWith("data:")) Base64.decode(src.substringAfter("base64,"), Base64.DEFAULT)
            else if (dir != null) File(dir, URLDecoder.decode(src.substringBefore('#').substringBefore('?'), "UTF-8")).takeIf { it.isFile }?.readBytes() else null
        }.getOrNull() ?: return null
        val bmp = decodeBitmap(bytes, 1000) ?: return null
        val d = BitmapDrawable(Resources.getSystem(), bmp)
        val scale = minOf(w.contentW / bmp.width, w.contentH * 0.85f / bmp.height, 1f)
        d.setBounds(0, 0, (bmp.width * scale).toInt().coerceAtLeast(1), (bmp.height * scale).toInt().coerceAtLeast(1))
        return d
    }

    private fun toSpanned(html: String, dir: File?, w: Writer): Spanned {
        val cleaned = html
            .replace(Regex("<script\\b.*?</script>", setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE)), "")
            .replace(Regex("<style\\b.*?</style>", setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE)), "")
            .replace(Regex("<svg\\b.*?</svg>", setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE)), "")
        return Html.fromHtml(cleaned, Html.FROM_HTML_MODE_LEGACY, { src -> drawableFor(src, dir, w) }, null)
    }

    private fun bodyOf(html: String): String {
        val m = Regex("<body\\b[^>]*>(.*)</body>", setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE)).find(html)
        return m?.groupValues?.get(1) ?: html
    }

    private fun readText(bytes: ByteArray): String {
        val utf8 = String(bytes, Charsets.UTF_8)
        return if (utf8.contains('\uFFFD')) String(bytes, charset("windows-1256")) else utf8.removePrefix("\uFEFF")
    }

    private fun readUri(ctx: Context, uri: Uri): ByteArray =
        (ctx.contentResolver.openInputStream(uri) ?: error("Cannot open the file")).use { it.readBytes() }

    private fun unzip(ctx: Context, uri: Uri, into: File) {
        into.mkdirs()
        (ctx.contentResolver.openInputStream(uri) ?: error("Cannot open the file")).use { raw ->
            ZipInputStream(raw).use { z ->
                var e = z.nextEntry
                while (e != null) {
                    val target = File(into, e.name)
                    if (!e.isDirectory && target.canonicalPath.startsWith(into.canonicalPath + File.separator)) {
                        target.parentFile?.mkdirs()
                        target.outputStream().use { z.copyTo(it) }
                    }
                    e = z.nextEntry
                }
            }
        }
    }

    private fun tempDir(ctx: Context, prefix: String): File = File(ctx.cacheDir, "$prefix${System.nanoTime()}")

    // ------------------------------------------------------------------ formats

    fun txt(ctx: Context, uri: Uri, out: OutputStream) {
        val w = Writer()
        val text = readText(readUri(ctx, uri))
        for (para in text.replace("\r\n", "\n").split(Regex("\n{2,}"))) w.add(SpannableString(para.trim('\n')))
        w.finish(out)
    }

    fun html(ctx: Context, uri: Uri, out: OutputStream) {
        val w = Writer()
        w.add(toSpanned(bodyOf(readText(readUri(ctx, uri))), null, w))
        w.finish(out)
    }

    fun epub(ctx: Context, uri: Uri, out: OutputStream) {
        val dir = tempDir(ctx, "epub")
        try {
            unzip(ctx, uri, dir)
            val container = File(dir, "META-INF/container.xml").takeIf { it.isFile }?.readText() ?: error("Not a valid EPUB file")
            val opfPath = Regex("full-path=\"([^\"]+)\"").find(container)?.groupValues?.get(1) ?: error("Not a valid EPUB file")
            val opf = File(dir, opfPath)
            val opfText = opf.readText()
            val items = HashMap<String, String>()
            for (m in Regex("<item\\b[^>]*>", RegexOption.IGNORE_CASE).findAll(opfText)) {
                val tag = m.value
                val id = Regex("\\bid=\"([^\"]*)\"").find(tag)?.groupValues?.get(1) ?: continue
                val href = Regex("\\bhref=\"([^\"]*)\"").find(tag)?.groupValues?.get(1) ?: continue
                items[id] = href
            }
            val order = Regex("<itemref\\b[^>]*idref=\"([^\"]*)\"", RegexOption.IGNORE_CASE).findAll(opfText).map { it.groupValues[1] }.toList()
            val w = Writer()
            var any = false
            for (id in order) {
                val href = items[id] ?: continue
                val f = File(opf.parentFile, URLDecoder.decode(href.substringBefore('#'), "UTF-8"))
                if (!f.isFile || f.extension.lowercase() !in setOf("xhtml", "html", "htm", "xml")) continue
                w.breakPage()
                w.add(toSpanned(bodyOf(readText(f.readBytes())), f.parentFile, w))
                any = true
            }
            if (!any) error("This EPUB has no readable chapters")
            w.finish(out)
        } finally {
            dir.deleteRecursively()
        }
    }

    fun fb2(ctx: Context, uri: Uri, out: OutputStream) {
        val dir = tempDir(ctx, "fb2")
        dir.mkdirs()
        try {
            val factory = DocumentBuilderFactory.newInstance().apply { isNamespaceAware = false }
            val root = factory.newDocumentBuilder().parse(readUri(ctx, uri).inputStream()).documentElement
            // pictures are stored as base64 inside the file
            val binaries = root.getElementsByTagName("binary")
            for (i in 0 until binaries.length) {
                val b = binaries.item(i) as Element
                val id = b.getAttribute("id")
                if (id.isNotEmpty()) runCatching { File(dir, id).writeBytes(Base64.decode(b.textContent.trim(), Base64.DEFAULT)) }
            }
            val sb = StringBuilder()
            fun esc(s: String) = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            fun emit(n: Node) {
                when (n.nodeType) {
                    Node.TEXT_NODE -> sb.append(esc(n.textContent))
                    Node.ELEMENT_NODE -> {
                        val e = n as Element
                        when (e.tagName) {
                            "emphasis" -> { sb.append("<i>"); e.childNodes.forEach(::emit); sb.append("</i>") }
                            "strong" -> { sb.append("<b>"); e.childNodes.forEach(::emit); sb.append("</b>") }
                            "sub" -> { sb.append("<sub>"); e.childNodes.forEach(::emit); sb.append("</sub>") }
                            "sup" -> { sb.append("<sup>"); e.childNodes.forEach(::emit); sb.append("</sup>") }
                            "image" -> {
                                val href = (e.getAttribute("l:href").ifEmpty { e.getAttribute("xlink:href") }).removePrefix("#")
                                if (href.isNotEmpty()) sb.append("<img src=\"").append(esc(href)).append("\"/>")
                            }
                            else -> e.childNodes.forEach(::emit)
                        }
                    }
                }
            }
            fun block(e: Element, level: Int) {
                for (i in 0 until e.childNodes.length) {
                    val n = e.childNodes.item(i)
                    if (n.nodeType != Node.ELEMENT_NODE) continue
                    val c = n as Element
                    when (c.tagName) {
                        "title" -> { sb.append("<h").append(level).append(">"); c.childNodes.forEach(::emit); sb.append("</h").append(level).append(">") }
                        "p" -> { sb.append("<p>"); c.childNodes.forEach(::emit); sb.append("</p>") }
                        "subtitle" -> { sb.append("<p><b>"); c.childNodes.forEach(::emit); sb.append("</b></p>") }
                        "empty-line" -> sb.append("<br/>")
                        "image" -> { sb.append("<p>"); emit(c); sb.append("</p>") }
                        "v" -> { sb.append("<p>"); c.childNodes.forEach(::emit); sb.append("</p>") }
                        "epigraph", "cite", "poem", "stanza", "text-author" -> { sb.append("<blockquote>"); block(c, level); sb.append("</blockquote>") }
                        "section" -> block(c, minOf(level + 1, 5))
                        else -> block(c, level)
                    }
                }
            }
            val title = root.getElementsByTagName("book-title").item(0)?.textContent?.trim().orEmpty()
            if (title.isNotEmpty()) sb.append("<h1>").append(esc(title)).append("</h1>")
            val bodies = root.getElementsByTagName("body")
            for (i in 0 until bodies.length) block(bodies.item(i) as Element, 2)
            val w = Writer()
            w.add(toSpanned(sb.toString(), dir, w))
            w.finish(out)
        } finally {
            dir.deleteRecursively()
        }
    }

    private fun org.w3c.dom.NodeList.forEach(f: (Node) -> Unit) { for (i in 0 until length) f(item(i)) }

    fun cbz(ctx: Context, uri: Uri, out: OutputStream) {
        val dir = tempDir(ctx, "cbz")
        try {
            unzip(ctx, uri, dir)
            val images = dir.walkTopDown().filter { it.isFile && it.extension.lowercase() in setOf("jpg", "jpeg", "png", "webp", "gif", "bmp") }
                .sortedWith { a, b -> naturalCompare(a.path, b.path) }.map { Uri.fromFile(it) }.toList()
            if (images.isEmpty()) error("This comic archive has no pictures")
            PdfOps.picturesToPdf(ctx, images, out)
        } finally {
            dir.deleteRecursively()
        }
    }

    private fun naturalCompare(a: String, b: String): Int {
        val ra = Regex("\\d+|\\D+").findAll(a.lowercase()).map { it.value }.toList()
        val rb = Regex("\\d+|\\D+").findAll(b.lowercase()).map { it.value }.toList()
        for (i in 0 until minOf(ra.size, rb.size)) {
            val x = ra[i]; val y = rb[i]
            val c = if (x[0].isDigit() && y[0].isDigit()) (x.toBigInteger().compareTo(y.toBigInteger())) else x.compareTo(y)
            if (c != 0) return c
        }
        return ra.size - rb.size
    }

    fun djvu(ctx: Context, uri: Uri, out: OutputStream) {
        val f = File(ctx.cacheDir, "in${System.nanoTime()}.djvu")
        try {
            (ctx.contentResolver.openInputStream(uri) ?: error("Cannot open the file")).use { i -> f.outputStream().use { i.copyTo(it) } }
            DjvuDocument(f.absolutePath).use { d ->
                PDDocument().use { pdf ->
                    for (p in 0 until d.pageCount) {
                        val (wPx, hPx, dpi) = d.info(p)
                        val scale = minOf(1f, 1800f / wPx)
                        val bmp = d.render(p, (wPx * scale).toInt().coerceAtLeast(1), (hPx * scale).toInt().coerceAtLeast(1))
                        PdfOps.addPicture(pdf, bmp, wPx * 72f / dpi, hPx * 72f / dpi, 0.82f)
                        bmp.recycle()
                    }
                    pdf.save(out)
                }
            }
        } finally {
            f.delete()
        }
    }
}

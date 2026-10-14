package app.pdftoolkit.mobile

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import com.tom_roush.pdfbox.contentstream.PDFStreamEngine
import com.tom_roush.pdfbox.contentstream.operator.DrawObject
import com.tom_roush.pdfbox.contentstream.operator.Operator
import com.tom_roush.pdfbox.contentstream.operator.state.Concatenate
import com.tom_roush.pdfbox.contentstream.operator.state.Restore
import com.tom_roush.pdfbox.contentstream.operator.state.Save
import com.tom_roush.pdfbox.contentstream.operator.state.SetGraphicsStateParameters
import com.tom_roush.pdfbox.contentstream.operator.state.SetMatrix
import com.tom_roush.pdfbox.cos.COSBase
import com.tom_roush.pdfbox.cos.COSName
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.pdmodel.graphics.form.PDFormXObject
import com.tom_roush.pdfbox.pdmodel.graphics.image.PDImageXObject
import com.tom_roush.pdfbox.text.PDFTextStripper
import com.tom_roush.pdfbox.text.TextPosition
import java.io.ByteArrayOutputStream
import java.io.File
import java.text.Normalizer
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/**
 * Turns a PDF back into LaTeX source. Text, headings, lists, theorems, references and inline formulas are rebuilt
 * from the PDF's own text and fonts; pictures are extracted; display equations (which cannot be recovered
 * reliably) are cut out as pictures, with a best-effort guess kept as a comment. Every original page can also be
 * attached as a picture.
 */
class PdfToLatex(private val cacheDir: File) {
    class Options(val equationPictures: Boolean = true, val pagePictures: Boolean = true)
    class Output(val tex: String, val files: Map<String, ByteArray>, val notes: List<String>, val rtl: Boolean)

    private class Glyph(val ch: String, val x: Float, val base: Float, val w: Float, val size: Float, val font: String) {
        val math: Boolean get() = MATH_FONT.containsMatchIn(font) || (ch.length == 1 && ch[0] in MATH_CHARS)
        val bold: Boolean get() = BOLD_FONT.containsMatchIn(font)
        val italic: Boolean get() = ITALIC_FONT.containsMatchIn(font)
    }

    private class Line(val glyphs: List<Glyph>, val page: Int, val pageW: Float, val pageH: Float) {
        val x0 = glyphs.minOf { it.x }
        val x1 = glyphs.maxOf { it.x + it.w }
        val size: Float = glyphs.map { it.size }.sorted().let { it[it.size / 2] }
        val base: Float = glyphs.groupingBy { (it.base * 2).toInt() }.eachCount().maxByOrNull { it.value }!!.key / 2f
        val top get() = base - size * 0.85f
        val bottom get() = base + size * 0.30f
        val plain: String get() = glyphs.joinToString("") { it.ch }.trim()
        val mathShare: Float get() = glyphs.filter { it.ch.isNotBlank() }.let { g -> if (g.isEmpty()) 0f else g.count { it.math }.toFloat() / g.size }
        val allBold: Boolean get() = glyphs.filter { it.ch.isNotBlank() }.let { g -> g.isNotEmpty() && g.all { it.bold } }
        val chars: Int get() = glyphs.count { it.ch.isNotBlank() }
    }

    private class Img(val page: Int, val top: Float, val left: Float, val w: Float, val h: Float, val png: ByteArray)

    private class Collector(val lines: MutableList<Line>) : PDFTextStripper() {
        private var cur = ArrayList<Glyph>()
        private var pw = 612f
        private var ph = 792f

        override fun startPage(page: com.tom_roush.pdfbox.pdmodel.PDPage) {
            pw = page.mediaBox.width; ph = page.mediaBox.height
            super.startPage(page)
        }

        override fun writeString(text: String, textPositions: MutableList<TextPosition>) {
            if (cur.isNotEmpty() && textPositions.isNotEmpty()) {
                val last = cur.last()
                val first = textPositions.first()
                if (last.ch != " ") cur.add(Glyph(" ", last.x + last.w, last.base, 0f, last.size, last.font))
                if (first.xDirAdj < last.x - 2 * last.size) flush()                // a jump back: a new column
            }
            for (tp in textPositions) {
                val u = Normalizer.normalize(tp.unicode ?: continue, Normalizer.Form.NFKC)
                if (u.isEmpty()) continue
                cur.add(Glyph(u, tp.xDirAdj, tp.yDirAdj, tp.widthDirAdj, tp.fontSizeInPt, tp.font?.name ?: ""))
            }
        }

        override fun writeLineSeparator() { flush() }
        override fun writeWordSeparator() {}
        override fun writePageEnd() { flush(); super.writePageEnd() }

        private fun flush() {
            if (cur.any { it.ch.isNotBlank() }) lines.add(Line(cur.toList(), currentPageNo, pw, ph))
            cur = ArrayList()
        }
    }

    private class ImageFinder(val page: Int, val sink: MutableList<Img>, val pageH: Float) : PDFStreamEngine() {
        init {
            addOperator(Concatenate()); addOperator(DrawObject()); addOperator(SetGraphicsStateParameters())
            addOperator(Save()); addOperator(Restore()); addOperator(SetMatrix())
        }

        override fun processOperator(operator: Operator, operands: MutableList<COSBase>) {
            if (operator.name == "Do") {
                val name = operands[0] as COSName
                val x = resources.getXObject(name)
                if (x is PDImageXObject) {
                    val m = graphicsState.currentTransformationMatrix
                    val w = m.scalingFactorX
                    val h = m.scalingFactorY
                    if (w > 40f && h > 30f) {
                        runCatching {
                            val bmp = x.image
                            val bo = ByteArrayOutputStream()
                            bmp.compress(Bitmap.CompressFormat.PNG, 100, bo)
                            sink.add(Img(page, pageH - m.translateY - h, m.translateX, w, h, bo.toByteArray()))
                        }
                    }
                } else if (x is PDFormXObject) {
                    showForm(x)
                }
            } else {
                super.processOperator(operator, operands)
            }
        }
    }

    // ------------------------------------------------------------------ conversion

    fun convert(pdf: File, title: String, opts: Options = Options(), progress: (String) -> Unit = {}): Output {
        val notes = ArrayList<String>()
        val files = LinkedHashMap<String, ByteArray>()
        PDDocument.load(pdf).use { doc ->
            val pages = doc.numberOfPages
            progress("1/$pages")
            val lines = ArrayList<Line>()
            Collector(lines).apply { startPage = 1; endPage = pages }.getText(doc)
            val images = ArrayList<Img>()
            for (p in 0 until pages) {
                val page = doc.getPage(p)
                runCatching { ImageFinder(p + 1, images, page.mediaBox.height).processPage(page) }
            }
            val rtl = isArabicScript(lines)
            val flow = buildFlow(lines, images, pages)
            val body = StringBuilder()
            val renderer = Renderer(pdf)
            try {
                emit(flow, body, files, renderer, opts, notes, pages, progress, title, rtl)
                if (opts.pagePictures) {
                    body.append("\n\\appendix\n\\section*{Original pages}\n")
                    for (p in 1..pages) {
                        progress("$p/$pages")
                        val bmp = renderer.render(p - 1, 130 / 72f)
                        val name = "figures/page_$p.png"
                        files[name] = png(bmp)
                        body.append("\\begin{center}\n  \\includegraphics[width=\\linewidth,height=0.85\\textheight,keepaspectratio]{$name}\\\\[2pt]\n  {\\small Page $p}\n\\end{center}\n\\newpage\n")
                        bmp.recycle()
                    }
                }
            } finally {
                renderer.close()
            }
            val tex = preamble(rtl) + body + "\n\\end{document}\n"
            return Output(tex, files, notes, rtl)
        }
    }

    private class Renderer(file: File) {
        private val pfd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
        private val r = PdfRenderer(pfd)
        fun render(i: Int, scale: Float): Bitmap = r.openPage(i).use { p ->
            val bmp = Bitmap.createBitmap((p.width * scale).toInt().coerceAtLeast(1), (p.height * scale).toInt().coerceAtLeast(1), Bitmap.Config.ARGB_8888)
            bmp.eraseColor(Color.WHITE)
            p.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
            bmp
        }
        fun close() { runCatching { r.close() }; runCatching { pfd.close() } }
    }

    private fun png(b: Bitmap): ByteArray = ByteArrayOutputStream().also { b.compress(Bitmap.CompressFormat.PNG, 100, it) }.toByteArray()

    private fun isArabicScript(lines: List<Line>): Boolean {
        var ar = 0; var all = 0
        for (l in lines) for (g in l.glyphs) for (c in g.ch) if (c.isLetter()) { all++; if (c in '\u0600'..'\u06FF' || c in '\uFB50'..'\uFEFF') ar++ }
        return all > 50 && ar > all * 0.3
    }

    // ------------------------------------------------------------------ layout analysis

    private sealed class Item {
        class L(val line: Line) : Item()
        class I(val img: Img) : Item()
    }

    private fun buildFlow(all: List<Line>, images: List<Img>, pages: Int): List<Item> {
        // running heads, feet and page numbers: short lines near the top or bottom that repeat or are only a number
        val norm = { l: Line -> l.plain.replace(Regex("\\d+"), "#").lowercase() }
        val counts = all.filter { it.top < it.pageH * 0.09f || it.bottom > it.pageH * 0.91f }.groupingBy(norm).eachCount()
        val lines = all.filter { l ->
            val edge = l.top < l.pageH * 0.09f || l.bottom > l.pageH * 0.91f
            !(edge && l.chars < 90 && (l.plain.matches(Regex("[\\divxlc\\-– ]+")) || (counts[norm(l)] ?: 0) >= max(3, pages / 3)))
        }
        val flow = ArrayList<Item>()
        val byPage = lines.groupBy { it.page }
        for (p in 1..pages) {
            val ls = byPage[p].orEmpty()
            val imgs = images.filter { it.page == p }.sortedBy { it.top }
            val pending = imgs.toMutableList()
            for (l in ls) {
                while (pending.isNotEmpty() && pending.first().top + pending.first().h * 0.5f < l.top) flow.add(Item.I(pending.removeAt(0)))
                flow.add(Item.L(l))
            }
            pending.forEach { flow.add(Item.I(it)) }
        }
        return flow
    }

    // ------------------------------------------------------------------ LaTeX output

    private fun preamble(rtl: Boolean): String = buildString {
        append("\\documentclass[11pt,a4paper]{article}\n\\usepackage[margin=2.5cm]{geometry}\n")
        append("\\usepackage{amsmath,amssymb,amsthm,graphicx}\n\\usepackage[hidelinks]{hyperref}\n")
        if (rtl) {
            append("\\usepackage{xepersian}\n\\settextfont[Path=fonts/,Extension=.ttf,UprightFont=*-Regular,BoldFont=*-Bold]{Vazirmatn}\n")
        }
        append("\\newtheorem*{theorem}{Theorem}\n\\newtheorem*{lemma}{Lemma}\n\\newtheorem*{proposition}{Proposition}\n\\newtheorem*{corollary}{Corollary}\n")
        append("\\theoremstyle{definition}\n\\newtheorem*{definition}{Definition}\n\\newtheorem*{example}{Example}\n\\newtheorem*{remark}{Remark}\n")
        append("\\setlength{\\parindent}{0pt}\\setlength{\\parskip}{0.6em}\n\n\\begin{document}\n")
    }

    private fun emit(
        flow: List<Item>, out: StringBuilder, files: MutableMap<String, ByteArray>, renderer: Renderer, opts: Options,
        notes: MutableList<String>, pages: Int, progress: (String) -> Unit, title: String, rtl: Boolean,
    ) {
        val textLines = flow.filterIsInstance<Item.L>().map { it.line }
        if (textLines.isEmpty()) {
            notes.add("This PDF has no text (a scan?). Its pages are attached as pictures only.")
            out.append("\\title{${esc(title)}}\n\\maketitle\n")
            return
        }
        // body size, margins
        val body = textLines.groupingBy { (it.size * 2).toInt() }.eachCount().maxByOrNull { it.value }!!.key / 2f
        val wide = textLines.filter { it.chars >= 30 }
        val leftM = wide.map { it.x0 }.sorted().let { if (it.isEmpty()) 0f else it[(it.size * 0.2f).toInt()] }
        val rightM = wide.map { it.x1 }.sorted().let { if (it.isEmpty()) 0f else it[(it.size * 0.8f).toInt()] }
        val headSizes = textLines.filter { it.size >= body * 1.12f && it.chars < 110 }.map { (it.size * 2).toInt() / 2f }.distinct().sortedDescending()

        // title block: large lines at the start of page 1
        var i = 0
        val titleLines = ArrayList<String>()
        val authorLines = ArrayList<String>()
        run {
            val first = flow.indexOfFirst { it is Item.L }
            var k = first
            while (k < flow.size) {
                val l = (flow[k] as? Item.L)?.line ?: break
                if (l.page != 1 || l.size < body * 1.25f) break
                titleLines.add(l.plain); k++
            }
            if (titleLines.isNotEmpty()) {
                while (k < flow.size) {
                    val l = (flow[k] as? Item.L)?.line ?: break
                    if (l.page != 1 || l.size >= body * 1.25f || l.chars > 120 || isHeadingText(l.plain, body, l, headSizes, true)) break
                    if (l.plain.startsWith("Abstract", ignoreCase = true)) break
                    authorLines.add(l.plain); k++
                }
                i = k
            }
        }
        out.append("\\title{${esc(titleLines.joinToString(" ").ifBlank { title })}}\n")
        out.append("\\author{${if (authorLines.isEmpty()) "" else authorLines.joinToString(" \\\\ ") { esc(it) }}}\n\\date{}\n\\maketitle\n\n")

        val para = StringBuilder()
        var listKind: String? = null
        var inEnv: String? = null
        var inBib = false
        val bibItems = ArrayList<String>()
        var prev: Line? = null
        var eqCount = 0
        var figCount = 0
        var lastPage = 0

        fun closeEnv() { inEnv?.let { out.append("\\end{$it}\n\n") }; inEnv = null }
        fun flushPara() {
            if (para.isBlank()) { para.setLength(0); return }
            val text = para.toString().trim()
            para.setLength(0)
            if (inBib) {
                if (Regex("^\\[\\d+\\]").containsMatchIn(text)) bibItems.add(text.replace(Regex("^\\[\\d+\\]\\s*"), "")) else if (bibItems.isNotEmpty()) bibItems[bibItems.lastIndex] += " $text"
                else out.append(text).append("\n\n")
                return
            }
            val th = Regex("^(Theorem|Lemma|Proposition|Corollary|Definition|Example|Remark)\\s+\\d+(\\.\\d+)*\\.?\\s*").find(text)
            val pr = Regex("^Proof\\.?\\s*").find(text)
            when {
                th != null -> {
                    closeEnv()
                    val env = th.groupValues[1].lowercase()
                    out.append("\\begin{$env}\n").append(text.removeRange(th.range).trim()).append("\n\\end{$env}\n\n")
                }
                pr != null -> {
                    closeEnv()
                    val rest = text.removeRange(pr.range).trim()
                    val end = rest.endsWith("□") || rest.endsWith("■") || rest.endsWith("∎") || rest.endsWith("\\Box")
                    out.append("\\begin{proof}\n").append(rest.trimEnd('□', '■', '∎', ' ')).append("\n")
                    if (end) out.append("\\end{proof}\n\n") else inEnv = "proof"
                }
                else -> {
                    out.append(text).append("\n\n")
                    if (inEnv == "proof" && (text.endsWith("□") || text.endsWith("■") || text.endsWith("∎"))) closeEnv()
                }
            }
        }
        fun closeList() { listKind?.let { flushPara(); out.append("\\end{$it}\n\n") }; listKind = null }

        while (i < flow.size) {
            val item = flow[i]
            if (item is Item.I) {
                flushPara(); closeList()
                figCount++
                val name = "figures/fig_$figCount.png"
                files[name] = item.img.png
                val wbp = min(item.img.w, 440f)
                out.append("\\begin{figure}[ht]\n  \\centering\n  \\includegraphics[width=${wbp.toInt()}bp]{$name}\n\\end{figure}\n\n")
                i++; continue
            }
            val line = (item as Item.L).line
            if (line.page != lastPage) { lastPage = line.page; progress("${line.page}/$pages") }
            val text = line.plain

            // headings
            val level = headingLevel(line, body, headSizes)
            if (level != null) {
                flushPara(); closeList(); closeEnv()
                val clean = text.replace(Regex("^\\d+(\\.\\d+)*\\.?\\s+"), "").replace(Regex("^[A-Z]\\.\\s+"), "")
                if (inBib && bibItems.isNotEmpty()) { writeBib(out, bibItems); bibItems.clear() }
                inBib = Regex("^(references|bibliography)$", RegexOption.IGNORE_CASE).matches(clean.trim())
                if (inBib) { out.append("\\section*{${esc(clean)}}\n\n") }
                else if (clean.equals("Abstract", ignoreCase = true)) { out.append("\\begin{abstract}\n"); inEnv = "abstract" }
                else out.append("\\${listOf("section", "subsection", "subsubsection")[level - 1]}{${lineLatex(line, stripNumber = true)}}\n\n")
                prev = line; i++; continue
            }

            // display equations: lines that are mostly math, set apart from the text
            if (line.mathShare >= 0.55f && line.chars < 90 && line.x0 > leftM + 0.05f * line.pageW) {
                flushPara(); closeList()
                var j = i
                var x0 = line.x0; var x1 = line.x1; var top = line.top; var bot = line.bottom
                var guess = StringBuilder()
                while (j < flow.size) {
                    val l2 = (flow[j] as? Item.L)?.line ?: break
                    val near = l2.page == line.page && abs(l2.base - (if (j == i) l2.base else bot)) < body * 2.4f
                    val mathy = l2.mathShare >= 0.5f && l2.chars < 100 && l2.x0 > leftM + 0.03f * l2.pageW
                    if (!(mathy && near) && j != i) break
                    x0 = min(x0, l2.x0); x1 = max(x1, l2.x1); top = min(top, l2.top); bot = max(bot, l2.bottom)
                    guess.append(lineLatex(l2, forceMath = true)).append(' ')
                    j++
                }
                eqCount++
                if (opts.equationPictures) {
                    val name = "figures/eq_${eqCount}.png"
                    val scale = 220f / 72f
                    val bmp = renderer.render(line.page - 1, scale)
                    val cx0 = ((x0 - 6f) * scale).toInt().coerceIn(0, bmp.width - 1)
                    val cy0 = ((top - 4f) * scale).toInt().coerceIn(0, bmp.height - 1)
                    val cx1 = ((x1 + 6f) * scale).toInt().coerceIn(cx0 + 1, bmp.width)
                    val cy1 = ((bot + 4f) * scale).toInt().coerceIn(cy0 + 1, bmp.height)
                    val crop = Bitmap.createBitmap(bmp, cx0, cy0, cx1 - cx0, cy1 - cy0)
                    files[name] = png(crop)
                    crop.recycle(); bmp.recycle()
                    out.append("% equation $eqCount, best guess: ${guess.toString().replace('\n', ' ').trim()}\n")
                    out.append("\\begin{center}\n  \\includegraphics[width=${(x1 - x0 + 12f).toInt()}bp]{$name}\n\\end{center}\n\n")
                } else {
                    out.append("\\[\n  ${guess.toString().trim()}\n\\]\n\n")
                }
                prev = (flow[j - 1] as Item.L).line
                i = j; continue
            }

            // list items
            val bullet = Regex("^([•·∗*–\\-◦▪])\\s+(.*)$").find(text)
            val numbered = Regex("^(\\(?([0-9]+|[a-z]|[ivx]+)[.)])\\s+(.*)$").find(text)
            if (bullet != null || (numbered != null && line.x0 > leftM + 4f)) {
                flushPara()
                val kind = if (bullet != null) "itemize" else "enumerate"
                if (listKind != kind) { closeList(); out.append("\\begin{$kind}\n"); listKind = kind }
                val rest = lineLatex(line, dropPrefix = (bullet?.groupValues?.get(1) ?: numbered!!.groupValues[1]).length)
                para.append("\\item ").append(rest)
                prev = line; i++; continue
            }
            if (listKind != null && line.x0 <= leftM + 3f) { flushPara(); closeList() }

            // ordinary text: join lines into paragraphs
            val p = prev
            val newPara = p == null || p.page != line.page && p.chars < 40 ||
                (line.base - p.base > p.size * 1.65f && line.base > p.base) ||
                (line.x0 > leftM + body * 0.9f && p.x1 < rightM - 0.10f * line.pageW && line.base > p.base)
            if (newPara && para.isNotEmpty() && listKind == null) flushPara()
            val piece = lineLatex(line)
            if (para.isNotEmpty()) {
                if (para.endsWith("-") && piece.firstOrNull()?.isLowerCase() == true && !para.endsWith("--")) para.setLength(para.length - 1) else para.append(' ')
            }
            para.append(piece)
            prev = line; i++
        }
        flushPara(); closeList(); closeEnv()
        if (bibItems.isNotEmpty()) writeBib(out, bibItems)
        // in-text citations [3] or [3, 5] become \cite once the bibliography exists
        if (bibItems.isNotEmpty()) {
            val n = bibItems.size
            val replaced = Regex("\\[(\\d+(?:\\s*[,–-]\\s*\\d+)*)]").replace(out.toString()) { m ->
                val nums = m.groupValues[1].split(Regex("\\s*,\\s*")).flatMap { part ->
                    val r = part.split(Regex("\\s*[–-]\\s*"))
                    if (r.size == 2 && r[0].toIntOrNull() != null && r[1].toIntOrNull() != null) (r[0].toInt()..r[1].toInt()).toList() else listOfNotNull(part.toIntOrNull())
                }
                if (nums.isNotEmpty() && nums.all { it in 1..n }) "\\cite{${nums.joinToString(",") { "ref$it" }}}" else m.value
            }
            out.setLength(0); out.append(replaced)
        }
    }

    private fun writeBib(out: StringBuilder, items: List<String>) {
        out.append("\\begin{thebibliography}{${items.size}}\n")
        items.forEachIndexed { k, t -> out.append("\\bibitem{ref${k + 1}} ").append(t).append("\n") }
        out.append("\\end{thebibliography}\n\n")
    }

    private fun isHeadingText(text: String, body: Float, l: Line, headSizes: List<Float>, strictOnly: Boolean = false): Boolean =
        headingLevel(l, body, headSizes) != null

    private fun headingLevel(l: Line, body: Float, headSizes: List<Float>): Int? {
        val t = l.plain
        if (l.chars > 110 || l.mathShare > 0.3f) return null
        if (Regex("^(Abstract|References|Bibliography)$", RegexOption.IGNORE_CASE).matches(t.trim())) return 1
        val sizeRank = headSizes.indexOf((l.size * 2).toInt() / 2f)
        if (sizeRank in 0..2 && l.size >= body * 1.12f) return sizeRank + 1
        val num = Regex("^(\\d+(\\.\\d+){0,2})\\.?\\s+\\S").find(t)
        if (num != null && l.allBold) return num.groupValues[1].count { it == '.' } + 1
        if (l.allBold && l.chars < 60 && !t.endsWith(".") && Regex("^[A-Z0-9]").containsMatchIn(t)) return 2
        return null
    }

    // ------------------------------------------------------------------ text and inline math

    private fun lineLatex(l: Line, dropPrefix: Int = 0, stripNumber: Boolean = false, forceMath: Boolean = false): String =
        lineLatex(l, dropPrefix, stripNumber, forceMath, true)

    private fun lineLatex(l: Line, dropPrefix: Int, stripNumber: Boolean, forceMath: Boolean, unused: Boolean): String {
        val gs = l.glyphs
        val sb = StringBuilder()
        var skip = dropPrefix
        var idx = 0
        // leading number of a heading is dropped (LaTeX numbers sections itself)
        if (stripNumber) {
            val m = Regex("^\\s*(\\d+(\\.\\d+)*\\.?|[A-Z]\\.)\\s+").find(l.plain)
            if (m != null) skip = m.value.length
        }
        val baseSize = l.size
        val baseline = l.base
        var inMath = false
        fun open() { if (!inMath && !forceMath) { sb.append('$'); inMath = true } else if (!inMath) inMath = true }
        fun close() { if (inMath && !forceMath) { sb.append('$') }; inMath = false }
        var pos = 0
        var sup = false
        var sub = false
        fun endScript() { if (sup || sub) { sb.append('}'); sup = false; sub = false } }
        while (idx < gs.size) {
            val g = gs[idx]
            idx++
            val len = g.ch.length
            if (pos < skip) { pos += len; continue }
            pos += len
            if (g.ch == " ") {
                if (inMath && !forceMath) {
                    // a space between two math glyphs stays inside, otherwise the formula ends
                    val nxt = gs.getOrNull(idx)
                    if (nxt != null && (nxt.math) && !forceMath) { endScript(); sb.append(' '); continue }
                    endScript(); close()
                }
                sb.append(' ')
                continue
            }
            val isMath = g.math || (forceMath)
            if (isMath) {
                open()
                val small = g.size < baseSize * 0.86f
                val raised = g.base < baseline - baseSize * 0.18f
                val lowered = g.base > baseline + baseSize * 0.12f
                val wantSup = small && raised
                val wantSub = small && lowered
                if (!(wantSup && sup) && !(wantSub && sub)) endScript()
                if (wantSup && !sup) { sb.append("^{"); sup = true }
                if (wantSub && !sub) { sb.append("_{"); sub = true }
                sb.append(mathChar(g.ch))
            } else {
                endScript(); close()
                sb.append(esc(g.ch))
            }
        }
        endScript(); close()
        return sb.toString().replace(Regex(" {2,}"), " ").trim()
    }

    private fun mathChar(c: String): String {
        if (c.length == 1) {
            MATH_MAP[c[0]]?.let { return "$it " }
            if (c[0] in "{}") return "\\${c[0]}"
            if (c[0] in "#%&_$") return "\\${c[0]}"
            if (c[0] == '~') return "\\sim "
            if (c[0] == '^') return "\\hat{}"
            if (c[0] == '\\') return "\\backslash "
            if (c[0].code > 127 && !c[0].isLetter()) return "" // unknown symbol: left out rather than breaking the formula
        }
        return c
    }

    private fun esc(s: String): String {
        val sb = StringBuilder()
        for (c in s) {
            when (c) {
                '\\' -> sb.append("\\textbackslash{}")
                '&', '%', '$', '#', '_', '{', '}' -> sb.append('\\').append(c)
                '~' -> sb.append("\\textasciitilde{}")
                '^' -> sb.append("\\textasciicircum{}")
                '\u00A0' -> sb.append(' ')
                '\u2212' -> sb.append("--")
                else -> sb.append(c)
            }
        }
        return sb.toString()
    }

    companion object {
        private val MATH_FONT = Regex("CMMI|CMSY|CMEX|CMMIB|MSAM|MSBM|LMMath|Math|Symbol|STIX|Cambria|CMBSY|rsfs|EUFM|EUSM|MnSymbol", RegexOption.IGNORE_CASE)
        private val BOLD_FONT = Regex("Bold|Bd|CMBX|Black|Heavy|Semibold", RegexOption.IGNORE_CASE)
        private val ITALIC_FONT = Regex("Italic|Oblique|CMTI|CMMI|-It\\b", RegexOption.IGNORE_CASE)
        private val MATH_CHARS = "∑∏∫∮√∞∂∇≤≥≠≈≡∼≃∝≪≫∈∉⊂⊆⊃⊇∪∩∅∖∀∃¬∧∨±×·∘⊕⊗→←↔⇒⇐⇔↦αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΠΣΦΨΩϵϑϕϖ∥⟨⟩ℝℕℤℚℂ⊥∠△".toSet()
        private val MATH_MAP: Map<Char, String> = mapOf(
            '∑' to "\\sum", '∏' to "\\prod", '∫' to "\\int", '∮' to "\\oint", '√' to "\\sqrt", '∞' to "\\infty", '∂' to "\\partial", '∇' to "\\nabla",
            '≤' to "\\le", '≥' to "\\ge", '≠' to "\\ne", '≈' to "\\approx", '≡' to "\\equiv", '∼' to "\\sim", '≃' to "\\simeq", '∝' to "\\propto",
            '≪' to "\\ll", '≫' to "\\gg", '∈' to "\\in", '∉' to "\\notin", '⊂' to "\\subset", '⊆' to "\\subseteq", '⊃' to "\\supset", '⊇' to "\\supseteq",
            '∪' to "\\cup", '∩' to "\\cap", '∅' to "\\emptyset", '∖' to "\\setminus", '∀' to "\\forall", '∃' to "\\exists", '¬' to "\\neg",
            '∧' to "\\wedge", '∨' to "\\vee", '±' to "\\pm", '×' to "\\times", '·' to "\\cdot", '∘' to "\\circ", '⊕' to "\\oplus", '⊗' to "\\otimes",
            '→' to "\\to", '←' to "\\leftarrow", '↔' to "\\leftrightarrow", '⇒' to "\\Rightarrow", '⇐' to "\\Leftarrow", '⇔' to "\\Leftrightarrow", '↦' to "\\mapsto",
            'α' to "\\alpha", 'β' to "\\beta", 'γ' to "\\gamma", 'δ' to "\\delta", 'ε' to "\\varepsilon", 'ϵ' to "\\epsilon", 'ζ' to "\\zeta", 'η' to "\\eta",
            'θ' to "\\theta", 'ϑ' to "\\vartheta", 'ι' to "\\iota", 'κ' to "\\kappa", 'λ' to "\\lambda", 'μ' to "\\mu", 'ν' to "\\nu", 'ξ' to "\\xi", 'π' to "\\pi",
            'ρ' to "\\rho", 'σ' to "\\sigma", 'τ' to "\\tau", 'υ' to "\\upsilon", 'φ' to "\\varphi", 'ϕ' to "\\phi", 'χ' to "\\chi", 'ψ' to "\\psi", 'ω' to "\\omega",
            'Γ' to "\\Gamma", 'Δ' to "\\Delta", 'Θ' to "\\Theta", 'Λ' to "\\Lambda", 'Ξ' to "\\Xi", 'Π' to "\\Pi", 'Σ' to "\\Sigma", 'Φ' to "\\Phi", 'Ψ' to "\\Psi", 'Ω' to "\\Omega",
            '∥' to "\\|", '⟨' to "\\langle", '⟩' to "\\rangle", 'ℝ' to "\\mathbb{R}", 'ℕ' to "\\mathbb{N}", 'ℤ' to "\\mathbb{Z}", 'ℚ' to "\\mathbb{Q}", 'ℂ' to "\\mathbb{C}",
            '⊥' to "\\perp", '∠' to "\\angle", '△' to "\\triangle", '−' to "-", '∗' to "*", '′' to "'", '‖' to "\\|",
        )
    }
}

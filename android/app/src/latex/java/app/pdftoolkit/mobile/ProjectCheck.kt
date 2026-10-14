package app.pdftoolkit.mobile

/** One finding of the project check. [kind] is a string key ("check.undef.ref" ...) shown as the heading. */
data class CheckIssue(val kind: String, val detail: String, val file: String?, val line: Int?)

/**
 * Looks through the project for the usual mistakes before compiling: references and citations that point nowhere,
 * labels and bibliography entries nobody uses, environments that are opened but not closed, missing input files
 * and lines the last compile reported as too wide.
 */
object ProjectCheck {
    private val LABEL = Regex("""\\label\{([^}]*)\}""")
    private val REF = Regex("""\\(?:ref|eqref|autoref|cref|Cref|pageref|nameref|vref)\*?\{([^}]*)\}""")
    private val CITE = Regex("""\\(?:cite|citep|citet|citealp|citealt|citeauthor|citeyear|nocite|parencite|textcite|footcite)\*?(?:\[[^\]]*\]){0,2}\{([^}]*)\}""")
    private val BEGIN = Regex("""\\begin\{([^}]+)\}""")
    private val END = Regex("""\\end\{([^}]+)\}""")
    private val INPUT = Regex("""\\(input|include)\{([^}]+)\}""")
    private val GRAPHIC = Regex("""\\includegraphics\*?(?:\[[^\]]*\])?\{([^}]+)\}""")
    private val BIBFILE = Regex("""\\bibliography\{([^}]+)\}""")
    private val OVERFULL = Regex("""Overfull \\hbox \((\d+(?:\.\d+)?)pt too wide\)""")

    /** The text of a line without its comment (a % that is not escaped starts a comment). */
    private fun code(line: String): String {
        var i = 0
        while (i < line.length) {
            if (line[i] == '\\') { i += 2; continue }
            if (line[i] == '%') return line.substring(0, i)
            i++
        }
        return line
    }

    private class Hit(val key: String, val file: String, val line: Int)

    fun run(
        tex: Map<String, String>, bib: Map<String, String>, allFiles: Set<String>, mainFile: String, log: String = "",
    ): List<CheckIssue> {
        val out = ArrayList<CheckIssue>()
        val labels = ArrayList<Hit>()
        val refs = ArrayList<Hit>()
        val cites = ArrayList<Hit>()
        var nociteAll = false
        var usesBib = false

        for ((file, text) in tex) {
            val stack = ArrayList<Pair<String, Int>>()
            for ((i, raw) in text.lines().withIndex()) {
                val l = code(raw)
                val no = i + 1
                LABEL.findAll(l).forEach { labels.add(Hit(it.groupValues[1].trim(), file, no)) }
                REF.findAll(l).forEach { m -> m.groupValues[1].split(',').map { it.trim() }.filter { it.isNotEmpty() }.forEach { refs.add(Hit(it, file, no)) } }
                CITE.findAll(l).forEach { m ->
                    m.groupValues[1].split(',').map { it.trim() }.filter { it.isNotEmpty() }.forEach { k ->
                        if (k == "*") nociteAll = true else cites.add(Hit(k, file, no))
                    }
                }
                if (BIBFILE.containsMatchIn(l) || "\\addbibresource" in l) usesBib = true
                // begin / end pairs, in the order they appear on the line
                val marks = (BEGIN.findAll(l).map { it.range.first to (true to it.groupValues[1]) } +
                    END.findAll(l).map { it.range.first to (false to it.groupValues[1]) }).sortedBy { it.first }
                for ((_, m) in marks) {
                    val (open, name) = m
                    if (name == "document" && !open) continue                      // text after \end{document} is ignored
                    if (open) stack.add(name to no)
                    else if (stack.isNotEmpty() && stack.last().first == name) stack.removeAt(stack.size - 1)
                    else out.add(CheckIssue("check.end", "\\end{$name}", file, no))
                }
                INPUT.findAll(l).forEach { m ->
                    val target = m.groupValues[2].trim()
                    val has = target in allFiles || "$target.tex" in allFiles
                    if (!has) out.add(CheckIssue("check.nofile", target, file, no))
                }
                GRAPHIC.findAll(l).forEach { m ->
                    val target = m.groupValues[1].trim()
                    val has = target in allFiles || listOf("png", "jpg", "jpeg", "pdf", "eps").any { "$target.$it" in allFiles }
                    if (!has) out.add(CheckIssue("check.nofile", target, file, no))
                }
            }
            for ((name, no) in stack) if (name != "document") out.add(CheckIssue("check.begin", "\\begin{$name}", file, no))
        }

        val labelKeys = labels.map { it.key }.toSet()
        val refKeys = refs.map { it.key }.toSet()
        refs.filter { it.key !in labelKeys }.distinctBy { it.key }.forEach { out.add(CheckIssue("check.undef.ref", it.key, it.file, it.line)) }
        labels.groupBy { it.key }.filter { it.value.size > 1 }.forEach { (k, v) -> out.add(CheckIssue("check.dup.label", k, v[1].file, v[1].line)) }
        labels.filter { it.key !in refKeys }.distinctBy { it.key }.forEach { out.add(CheckIssue("check.unused.label", it.key, it.file, it.line)) }

        val entries = ArrayList<Hit>()
        for ((file, text) in bib) {
            for ((i, line) in text.lines().withIndex()) {
                bibKeys(line).forEach { entries.add(Hit(it, file, i + 1)) }
            }
        }
        val entryKeys = entries.map { it.key }.toSet()
        if (usesBib || entries.isNotEmpty()) {
            cites.filter { it.key !in entryKeys }.distinctBy { it.key }.forEach { out.add(CheckIssue("check.undef.cite", it.key, it.file, it.line)) }
            if (!nociteAll) {
                val used = cites.map { it.key }.toSet()
                entries.filter { it.key !in used }.distinctBy { it.key }.forEach { out.add(CheckIssue("check.unused.entry", it.key, it.file, it.line)) }
            }
        } else {
            cites.distinctBy { it.key }.forEach { out.add(CheckIssue("check.undef.cite", it.key, it.file, it.line)) }
        }

        // lines the last compile reported as sticking out into the margin by more than a few points
        for (m in OVERFULL.findAll(log)) {
            val pt = m.groupValues[1].toDoubleOrNull() ?: continue
            if (pt >= 10.0) {
                val after = log.substring(m.range.last, minOf(log.length, m.range.last + 160))
                val lines = Regex("""lines (\d+)""").find(after)?.groupValues?.get(1)?.toIntOrNull()
                out.add(CheckIssue("check.wide", "${pt.toInt()} pt", mainFile, lines))
            }
        }
        return out
    }
}

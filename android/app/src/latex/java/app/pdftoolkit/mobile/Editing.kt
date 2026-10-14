package app.pdftoolkit.mobile

import androidx.compose.ui.text.TextRange
import androidx.compose.ui.text.input.TextFieldValue

/**
 * Small helpers that make typing LaTeX pleasant. [smartEdit] looks at one typed character and may
 * answer with a different text: closing brackets and dollar signs are added, Enter keeps the indentation
 * and completes \begin{...} with its \end{...}.
 */
fun smartEdit(old: TextFieldValue, new: TextFieldValue): TextFieldValue {
    if (!old.selection.collapsed || !new.selection.collapsed) return new
    if (new.text.length != old.text.length + 1) return new
    val pos = new.selection.start
    if (pos < 1 || pos > new.text.length) return new
    if (new.text.substring(0, pos - 1) != old.text.substring(0, pos - 1)) return new
    if (new.text.substring(pos) != old.text.substring(pos - 1)) return new          // not a plain insertion at the caret
    val ch = new.text[pos - 1]
    val next = old.text.getOrNull(pos - 1)
    fun with(text: String, caret: Int) = TextFieldValue(text, TextRange(caret))
    return when {
        ch in "}])" && next == ch -> with(old.text, pos)                           // typed over an existing closer
        ch == '$' && next == '$' -> with(old.text, pos)
        ch in "{[(" && (next == null || next.isWhitespace() || next in "}])$") ->
            with(new.text.substring(0, pos) + closerOf(ch) + new.text.substring(pos), pos)
        ch == '$' && (next == null || next.isWhitespace()) && new.text.getOrNull(pos - 2) != '\\' ->
            with(new.text.substring(0, pos) + "$" + new.text.substring(pos), pos)
        ch == '\n' -> enter(old.text, pos)
        else -> new
    }
}

private fun closerOf(c: Char) = when (c) { '{' -> "}"; '[' -> "]"; else -> ")" }

private fun enter(oldText: String, pos: Int): TextFieldValue {
    // pos is the caret after the typed newline; the previous line ends at pos - 1
    val lineStart = oldText.lastIndexOf('\n', pos - 2).let { if (pos - 2 < 0) 0 else it + 1 }
    val prev = oldText.substring(lineStart, (pos - 1).coerceAtLeast(lineStart))
    val indent = prev.takeWhile { it == ' ' || it == '\t' }
    val begin = Regex("^\\s*\\\\begin\\{([^}]+)\\}").find(prev)
    val before = oldText.substring(0, pos - 1)
    val after = oldText.substring(pos - 1)
    if (begin != null && !prev.contains("\\end{")) {
        val env = begin.groupValues[1]
        val hasEnd = after.contains("\\end{$env}")
        val inner = indent + "  "
        if (!hasEnd) {
            val text = before + "\n" + inner + "\n" + indent + "\\end{" + env + "}" + after
            return TextFieldValue(text, TextRange(before.length + 1 + inner.length))
        }
        return TextFieldValue(before + "\n" + inner + after, TextRange(before.length + 1 + inner.length))
    }
    val extra = if (prev.trimStart().startsWith("\\item")) indent else indent
    return TextFieldValue(before + "\n" + extra + after, TextRange(before.length + 1 + extra.length))
}

/** Start offset of every line (for the line-number column). */
fun lineStarts(text: String): IntArray {
    var n = 1
    for (c in text) if (c == '\n') n++
    val out = IntArray(n)
    var k = 1
    for ((i, c) in text.withIndex()) if (c == '\n') out[k++] = i + 1
    return out
}

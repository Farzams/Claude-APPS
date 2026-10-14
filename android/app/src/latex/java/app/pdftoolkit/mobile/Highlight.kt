package app.pdftoolkit.mobile

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.OffsetMapping
import androidx.compose.ui.text.input.TransformedText
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.buildAnnotatedString

private val COMMENT = Regex("(?<!\\\\)%[^\n]*")
private val COMMAND = Regex("\\\\[A-Za-z@]+\\*?|\\\\.")
private val MATH = Regex("(?<!\\\\)\\$\\$?[^$]*\\$\\$?")
private val ENV = Regex("\\\\(?:begin|end)\\{[^}]*\\}")

/** Colours for LaTeX source: commands, math, environments and comments. */
class LatexHighlighter(
    private val command: Color, private val math: Color, private val comment: Color, private val env: Color,
    private val matches: List<Int> = emptyList(), private val matchLen: Int = 0, private val currentMatch: Int = -1,
    private val matchBg: Color = Color.Yellow, private val currentBg: Color = Color(0xFFFFA000),
    private val misspelled: List<IntRange> = emptyList(), private val spellColor: Color = Color.Red,
) : VisualTransformation {
    override fun filter(text: AnnotatedString): TransformedText {
        val s = text.text
        val styled = buildAnnotatedString {
            append(s)
            for (m in MATH.findAll(s)) addStyle(SpanStyle(color = math), m.range.first, m.range.last + 1)
            for (m in COMMAND.findAll(s)) addStyle(SpanStyle(color = command), m.range.first, m.range.last + 1)
            for (m in ENV.findAll(s)) addStyle(SpanStyle(color = env, fontWeight = FontWeight.SemiBold), m.range.first, m.range.last + 1)
            for (m in COMMENT.findAll(s)) addStyle(SpanStyle(color = comment, fontStyle = FontStyle.Italic), m.range.first, m.range.last + 1)
            for (r in misspelled) if (r.last < s.length) addStyle(SpanStyle(textDecoration = TextDecoration.Underline, color = spellColor), r.first, r.last + 1)
            for ((k, at) in matches.withIndex()) if (matchLen > 0 && at + matchLen <= s.length) {
                addStyle(SpanStyle(background = if (k == currentMatch) currentBg else matchBg), at, at + matchLen)
            }
        }
        return TransformedText(styled, OffsetMapping.Identity)
    }
}

@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package app.pdftoolkit.mobile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp

/** A table read from a CSV file: the header cells (or "A", "B", ... when the file has none) and the rows. */
class CsvData(val header: List<String>, val rows: List<List<String>>) {
    fun isNumeric(col: Int): Boolean = rows.isNotEmpty() && rows.all { r -> r.getOrNull(col)?.trim()?.replace(',', '.')?.toDoubleOrNull() != null }
}

object DataInsert {
    /** Reads comma, semicolon or tab separated text. Quoted cells may contain the separator and doubled quotes. */
    fun parse(text: String): CsvData {
        val lines = text.removePrefix("\uFEFF").lines().filter { it.isNotBlank() }.take(2000)
        if (lines.isEmpty()) return CsvData(emptyList(), emptyList())
        val first = lines.first()
        val sep = listOf(',', ';', '\t').maxByOrNull { c -> first.count { it == c } }?.takeIf { first.contains(it) } ?: ','
        val table = lines.map { split(it, sep) }
        val width = table.maxOf { it.size }
        val padded = table.map { r -> r + List(width - r.size) { "" } }
        val numericFirst = padded.first().all { it.trim().replace(',', '.').toDoubleOrNull() != null }
        return if (numericFirst) CsvData(List(width) { ('A' + it % 26).toString() + if (it >= 26) "${it / 26}" else "" }, padded)
        else CsvData(padded.first().map { it.trim() }, padded.drop(1))
    }

    private fun split(line: String, sep: Char): List<String> {
        val out = ArrayList<String>()
        val cur = StringBuilder()
        var quoted = false
        var i = 0
        while (i < line.length) {
            val c = line[i]
            when {
                quoted && c == '"' && i + 1 < line.length && line[i + 1] == '"' -> { cur.append('"'); i++ }
                c == '"' -> quoted = !quoted
                c == sep && !quoted -> { out.add(cur.toString()); cur.setLength(0) }
                else -> cur.append(c)
            }
            i++
        }
        out.add(cur.toString())
        return out
    }

    /** Makes text safe to put in a table cell or a label. */
    fun esc(s: String): String = buildString {
        for (c in s.trim()) when (c) {
            '&', '%', '$', '#', '_', '{', '}' -> append('\\').append(c)
            '~' -> append("\\textasciitilde{}")
            '^' -> append("\\textasciicircum{}")
            '\\' -> append("\\textbackslash{}")
            else -> append(c)
        }
    }

    private fun num(s: String) = s.trim().replace(',', '.')

    /** A booktabs table with numbers right-aligned. */
    fun table(d: CsvData, caption: String, maxRows: Int = 60): String {
        val cols = d.header.size
        val spec = (0 until cols).joinToString("") { if (d.isNumeric(it)) "r" else "l" }
        val sb = StringBuilder()
        sb.append("\\begin{table}[ht]\n  \\centering\n")
        if (caption.isNotBlank()) sb.append("  \\caption{${esc(caption)}}\n")
        sb.append("  \\begin{tabular}{$spec}\n    \\toprule\n")
        sb.append("    " + d.header.joinToString(" & ") { esc(it) } + " \\\\\n    \\midrule\n")
        for (r in d.rows.take(maxRows)) sb.append("    " + (0 until cols).joinToString(" & ") { esc(r.getOrElse(it) { "" }) } + " \\\\\n")
        sb.append("    \\bottomrule\n  \\end{tabular}\n\\end{table}\n")
        return sb.toString()
    }

    /** A pgfplots figure with one curve per chosen column, the points written out in the document itself. */
    fun plot(d: CsvData, x: Int, ys: List<Int>, caption: String, points: Boolean, maxPoints: Int = 400): String {
        val sb = StringBuilder()
        sb.append("\\begin{figure}[ht]\n  \\centering\n  \\begin{tikzpicture}\n")
        sb.append("    \\begin{axis}[width=0.9\\linewidth, height=6.5cm, grid=major, xlabel={${esc(d.header.getOrElse(x) { "x" })}}")
        if (ys.size == 1) sb.append(", ylabel={${esc(d.header.getOrElse(ys[0]) { "y" })}}")
        if (ys.size > 1) sb.append(", legend pos=north west")
        sb.append("]\n")
        val step = maxOf(1, d.rows.size / maxPoints)
        for (y in ys) {
            val pts = d.rows.filterIndexed { i, _ -> i % step == 0 }.mapNotNull { r ->
                val a = r.getOrNull(x)?.let(::num)?.toDoubleOrNull()
                val b = r.getOrNull(y)?.let(::num)?.toDoubleOrNull()
                if (a != null && b != null) "(${fmt(a)},${fmt(b)})" else null
            }
            sb.append("      \\addplot[${if (points) "only marks, mark=*, mark size=1.5pt" else "thick, mark=none"}] coordinates {\n        ")
            sb.append(pts.chunked(6).joinToString("\n        ") { it.joinToString(" ") })
            sb.append("\n      };\n")
            if (ys.size > 1) sb.append("      \\addlegendentry{${esc(d.header.getOrElse(y) { "" })}}\n")
        }
        sb.append("    \\end{axis}\n  \\end{tikzpicture}\n")
        if (caption.isNotBlank()) sb.append("  \\caption{${esc(caption)}}\n")
        sb.append("\\end{figure}\n")
        return sb.toString()
    }

    private fun fmt(v: Double): String =
        if (v == Math.rint(v) && kotlin.math.abs(v) < 1e9) v.toLong().toString()
        else java.math.BigDecimal(v).round(java.math.MathContext(6)).stripTrailingZeros().toPlainString()
}

/** Choose how to turn a CSV file into LaTeX: a table, a line graph or a scatter plot. */
@Composable
fun DataDialog(data: CsvData, onInsert: (code: String, needsPlot: Boolean) -> Unit, onDismiss: () -> Unit) {
    val cs = MaterialTheme.colorScheme
    var mode by remember { mutableStateOf("table") }
    var caption by remember { mutableStateOf("") }
    var xCol by remember { mutableStateOf(data.header.indices.firstOrNull { data.isNumeric(it) } ?: 0) }
    val numeric = data.header.indices.filter { data.isNumeric(it) }
    val ys = remember { mutableStateListOf<Int>().also { l -> numeric.firstOrNull { it != xCol }?.let(l::add) } }
    val canPlot = numeric.size >= 2

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(t("csv.title")) },
        text = {
            Column(Modifier.heightIn(max = 460.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("${data.rows.size} ${t("csv.rows")} · ${data.header.size} ${t("csv.cols")}", color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    SettingsChip(t("csv.table"), mode == "table", "csv_table") { mode = "table" }
                    if (canPlot) {
                        SettingsChip(t("csv.line"), mode == "line", "csv_line") { mode = "line" }
                        SettingsChip(t("csv.scatter"), mode == "scatter", "csv_scatter") { mode = "scatter" }
                    }
                }
                if (!canPlot) Text(t("csv.noplot"), color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                if (mode != "table") {
                    SettingsLabel(t("csv.x"))
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        for (c in numeric) SettingsChip(data.header[c], xCol == c, "csv_x_$c") { xCol = c; ys.remove(c) }
                    }
                    SettingsLabel(t("csv.y"))
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        for (c in numeric.filter { it != xCol }) SettingsChip(data.header[c], c in ys, "csv_y_$c") { if (c in ys) ys.remove(c) else ys.add(c) }
                    }
                }
                OutlinedTextField(caption, { caption = it }, label = { Text(t("csv.caption")) }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("csv_caption"))
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    if (mode == "table") onInsert(DataInsert.table(data, caption), false)
                    else onInsert(DataInsert.plot(data, xCol, ys.filter { it != xCol }.ifEmpty { numeric.filter { it != xCol }.take(1) }, caption, mode == "scatter"), true)
                },
                modifier = Modifier.testTag("csv_insert"),
            ) { Text(t("csv.insert")) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(t("cancel")) } },
    )
}

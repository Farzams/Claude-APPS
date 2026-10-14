package app.pdftoolkit.mobile

import android.util.Log
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** The parts of the insert and check tools that need no screen: reading CSV, writing LaTeX, finding mistakes. */
@RunWith(AndroidJUnit4::class)
class ToolsLogicTest {
    @Test
    fun checkFindsTheUsualMistakes() {
        val tex = mapOf(
            "main.tex" to """
\documentclass{article}
\begin{document}
See Figure~\ref{fig:missing} and \cite{known,unknown}.
\begin{figure}
  \label{fig:unused}
\end{figure}
\begin{itemize}
\item one
% \ref{commented}
\input{chapter}
\end{document}
""".trimStart(),
        )
        val bib = mapOf("refs.bib" to "@book{known, title={T}}\n@book{lonely, title={U}}\n")
        val kinds = ProjectCheck.run(tex, bib, setOf("main.tex", "refs.bib"), "main.tex").map { it.kind to it.detail }
        Log.i("PDFTK", "check found: $kinds")
        assertTrue(kinds.contains("check.undef.ref" to "fig:missing"))
        assertTrue(kinds.contains("check.undef.cite" to "unknown"))
        assertTrue(kinds.contains("check.unused.label" to "fig:unused"))
        assertTrue(kinds.contains("check.unused.entry" to "lonely"))
        assertTrue(kinds.contains("check.begin" to "\\begin{itemize}"))
        assertTrue(kinds.contains("check.nofile" to "chapter"))
        assertTrue("a commented reference is ignored", kinds.none { it.second == "commented" })
        assertTrue("a cited entry is not reported", kinds.none { it.second == "known" })
        val clean = ProjectCheck.run(mapOf("main.tex" to "\\begin{document}\n\\label{a} \\ref{a}\n\\end{document}\n"), emptyMap(), setOf("main.tex"), "main.tex")
        assertTrue("a clean project has no findings: $clean", clean.isEmpty())
        val wide = ProjectCheck.run(mapOf("main.tex" to ""), emptyMap(), setOf("main.tex"), "main.tex", "Overfull \\hbox (23.5pt too wide) in paragraph at lines 12--14")
        assertEquals(12, wide.single().line)
        Log.i("PDFTK", "check logic ok")
    }

    @Test
    fun csvBecomesTableAndPlot() {
        val d = DataInsert.parse("x;y;label\n1;2,5;a_b\n2;3,5;c&d\n3;4;e\n")
        assertEquals(listOf("x", "y", "label"), d.header)
        assertEquals(3, d.rows.size)
        assertTrue(d.isNumeric(0) && d.isNumeric(1) && !d.isNumeric(2))
        val table = DataInsert.table(d, "Measured")
        assertTrue(table, table.contains("\\begin{tabular}{rrl}") && table.contains("a\\_b") && table.contains("c\\&d") && table.contains("\\toprule"))
        val plot = DataInsert.plot(d, 0, listOf(1), "Curve", false)
        assertTrue(plot, plot.contains("(1,2.5)") && plot.contains("\\begin{axis}") && plot.contains("\\caption{Curve}"))
        val quoted = DataInsert.parse("name,note\n\"Smith, J.\",\"said \"\"hi\"\"\"\n")
        assertEquals(listOf("Smith, J.", "said \"hi\""), quoted.rows.single())
        val headless = DataInsert.parse("1,2\n3,4\n")
        assertEquals(2, headless.rows.size)
        Log.i("PDFTK", "csv logic ok")
    }

    @Test
    fun doiIsCleanedAndEntryTidied() {
        assertEquals("10.1038/nature14539", Doi.clean(" https://doi.org/10.1038/nature14539 "))
        assertEquals("10.1000/xyz123", Doi.clean("doi:10.1000/xyz123"))
        assertNull(Doi.clean("hello"))
        val e = Doi.tidy("@article{Smith_2020, title={A {Nice} Title}, volume={3}, author={Smith, John and Doe, Jane}, year={2020}, journal={Journal}}")
        assertTrue(e, e.startsWith("@article{smith2020,") && e.contains("author") && e.contains("A {Nice} Title"))
        assertNotNull(Regex("^@article\\{smith2020,").find(e))
        Log.i("PDFTK", "doi logic ok")
    }
}

package app.pdftoolkit.mobile

import android.content.Context
import android.view.textservice.SentenceSuggestionsInfo
import android.view.textservice.SpellCheckerSession
import android.view.textservice.SuggestionsInfo
import android.view.textservice.TextInfo
import android.view.textservice.TextServicesManager
import java.util.Locale

/** Words of the source that are plain text: commands, math, comments and \cite{...}-style arguments are blanked out. */
fun spellText(src: String): String {
    val sb = StringBuilder(src)
    fun blank(re: Regex) {
        for (m in re.findAll(src)) for (i in m.range) if (sb[i] != '\n') sb.setCharAt(i, ' ')
    }
    val dot = RegexOption.DOT_MATCHES_ALL
    blank(Regex("(?<!\\\\)%[^\n]*"))
    blank(Regex("\\\\begin\\{(equation|align|gather|multline|eqnarray|verbatim|tikzpicture|lstlisting)\\*?\\}.*?\\\\end\\{\\1\\*?\\}", dot))
    blank(Regex("\\$\\$.*?\\$\\$", dot))
    blank(Regex("\\\\\\[.*?\\\\\\]", dot))
    blank(Regex("(?<!\\\\)\\$[^$\n]*\\$"))
    blank(Regex("\\\\(cite|ref|label|eqref|usepackage|documentclass|input|include|bibliography|bibliographystyle|begin|end|includegraphics|url|href|pagestyle|geometry)(\\[[^\\]]*\\])?\\{[^}]*\\}"))
    blank(Regex("\\\\[A-Za-z@]+\\*?"))
    return sb.toString()
}

/** Wraps the system spell checker (works offline for the languages installed on the phone). */
class SystemSpell(private val ctx: Context) {
    private var session: SpellCheckerSession? = null
    private var sessionLang = ""
    private var starts: IntArray = IntArray(0)
    private var onResult: (List<IntRange>) -> Unit = {}

    private val listener = object : SpellCheckerSession.SpellCheckerSessionListener {
        override fun onGetSuggestions(results: Array<out SuggestionsInfo>?) {}
        override fun onGetSentenceSuggestions(results: Array<out SentenceSuggestionsInfo>?) {
            val out = ArrayList<IntRange>()
            results?.forEachIndexed { k, r ->
                val base = starts.getOrNull(k) ?: return@forEachIndexed
                for (i in 0 until r.suggestionsCount) {
                    val info = r.getSuggestionsInfoAt(i)
                    if ((info.suggestionsAttributes and SuggestionsInfo.RESULT_ATTR_LOOKS_LIKE_TYPO) != 0) {
                        val a = base + r.getOffsetAt(i)
                        out += a until a + r.getLengthAt(i)
                    }
                }
            }
            onResult(out)
        }
    }

    @Suppress("DEPRECATION")
    private fun ensure(lang: String): Boolean {
        if (session != null && sessionLang == lang) return true
        session?.close()
        val tsm = ctx.getSystemService(Context.TEXT_SERVICES_MANAGER_SERVICE) as? TextServicesManager ?: return false
        session = runCatching { tsm.newSpellCheckerSession(null, Locale.forLanguageTag(lang), listener, false) }.getOrNull()
        sessionLang = lang
        return session != null
    }

    /** Returns false when the phone has no spell checker for this language. */
    fun check(source: String, lang: String, cb: (List<IntRange>) -> Unit): Boolean {
        if (!ensure(lang)) return false
        val plain = spellText(source)
        val infos = ArrayList<TextInfo>()
        val offs = ArrayList<Int>()
        var at = 0
        for (line in plain.split('\n')) {
            if (line.isNotBlank() && line.length < 2000) { infos.add(TextInfo(line)); offs.add(at) }
            at += line.length + 1
        }
        if (infos.isEmpty()) { cb(emptyList()); return true }
        starts = offs.toIntArray()
        onResult = cb
        session?.getSentenceSuggestions(infos.toTypedArray(), 3)
        return true
    }

    fun close() { session?.close(); session = null }
}

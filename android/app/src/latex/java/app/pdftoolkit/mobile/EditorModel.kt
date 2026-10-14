package app.pdftoolkit.mobile

import android.app.Application
import android.net.Uri
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.text.TextRange
import androidx.compose.ui.text.input.TextFieldValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

data class TexError(val line: Int?, val message: String, val file: String? = null)

/**
 * Parses the TeX log: "! message" followed (a few lines later) by "l.<number> ...".
 * The file an error belongs to is found by following the "(./file.tex" ... ")" nesting in the log.
 */
fun parseErrors(log: String): List<TexError> {
    val lines = log.lines()
    val out = ArrayList<TexError>()
    val lre = Regex("^l\\.(\\d+)")
    val stack = ArrayList<String?>()
    val fileAt = arrayOfNulls<String>(lines.size)
    val open = Regex("\\((\\.?/?[^\\s()]+\\.(?:tex|bib|sty|cls))")
    for ((i, l) in lines.withIndex()) {
        var k = 0
        while (k < l.length) {
            val c = l[k]
            if (c == '(') {
                val m = open.matchAt(l, k)
                if (m != null) { stack.add(m.groupValues[1].removePrefix("./")); k += m.value.length; continue }
                stack.add(null)
            } else if (c == ')' && stack.isNotEmpty()) {
                stack.removeAt(stack.size - 1)
            }
            k++
        }
        fileAt[i] = stack.lastOrNull { it != null }
    }
    for ((i, l) in lines.withIndex()) {
        if (!l.startsWith("! ")) continue
        var ln: Int? = null
        for (j in i + 1..minOf(i + 10, lines.size - 1)) {
            val m = lre.find(lines[j])
            if (m != null) { ln = m.groupValues[1].toInt(); break }
        }
        val msg = l.substring(2).trim()
        if (out.lastOrNull()?.message == msg && out.lastOrNull()?.line == ln) continue
        out += TexError(ln, msg, if (i > 0) fileAt[i - 1] else fileAt[i])
    }
    return out
}

/** Citation keys found in the project's .bib files. */
fun bibKeys(text: String): List<String> =
    Regex("@\\w+\\s*\\{\\s*([^,\\s]+)\\s*,").findAll(text).map { it.groupValues[1] }.toList()

class EditorViewModel(private val app: Application) : AndroidViewModel(app) {
    val store = ProjectStore(app)
    val history = HistoryStore(app)
    private val outPdf = File(app.cacheDir, "preview.pdf")

    var projects by mutableStateOf(listOf<Project>())
    var project by mutableStateOf<Project?>(null)
    var meta by mutableStateOf(Meta())
    var files by mutableStateOf(listOf<String>())
    var current by mutableStateOf("main.tex")
    var field by mutableStateOf(TextFieldValue(""))

    var compiling by mutableStateOf(false)
    var status by mutableStateOf("")
    var log by mutableStateOf("")
    var errors by mutableStateOf(listOf<TexError>())
    var pdfFile by mutableStateOf<File?>(null)
    var pdfVersion by mutableIntStateOf(0)
    var compileOk by mutableStateOf<Boolean?>(null)
    var canUndo by mutableStateOf(false)
    var canRedo by mutableStateOf(false)

    // find and replace
    var findOpen by mutableStateOf(false)
    var findText by mutableStateOf("")
    var replaceText by mutableStateOf("")
    var matchCase by mutableStateOf(false)
    var matchIndex by mutableIntStateOf(0)

    var bibKeysList by mutableStateOf(listOf<String>())
    var misspelled by mutableStateOf(listOf<IntRange>())
    var spellLang by mutableStateOf("")          // "" = off, otherwise a language tag such as "en" or "fa"
    var spellMissing by mutableStateOf(false)    // the phone has no spell checker for that language
    private val speller = SystemSpell(app)
    private var spellJob: Job? = null

    fun applySpell(lang: String) {
        spellLang = lang
        spellMissing = false
        scheduleSpell(0)
    }

    private fun scheduleSpell(wait: Long = 1200) {
        spellJob?.cancel()
        if (spellLang.isEmpty()) { misspelled = emptyList(); return }
        spellJob = viewModelScope.launch {
            delay(wait)
            val src = field.text
            val ok = speller.check(src, spellLang) { misspelled = if (field.text == src) it else emptyList() }
            spellMissing = !ok
        }
    }

    override fun onCleared() { speller.close(); super.onCleared() }

    private class History { val undo = ArrayDeque<TextFieldValue>(); val redo = ArrayDeque<TextFieldValue>(); var lastPush = 0L }
    private val histories = HashMap<String, History>()
    private val buffers = HashMap<String, TextFieldValue>()
    private var saveJob: Job? = null

    init {
        refreshProjects()
        if (projects.isEmpty()) {
            store.create("Welcome", Templates.ALL.first())
            refreshProjects()
        }
    }

    fun refreshProjects() { projects = store.list() }

    // ------------------------------------------------------------ projects
    fun openProject(p: Project) {
        flush()
        project = p
        buffers.clear(); histories.clear()
        current = ""
        field = TextFieldValue("")
        meta = store.meta(p)
        refreshFiles()
        pdfFile = null; compileOk = null; log = ""; errors = emptyList(); status = ""
        findOpen = false
        openFile(if (meta.main in files) meta.main else files.firstOrNull { isTextFile(it) } ?: meta.main)
        refreshBib()
    }

    fun closeProject() {
        flush()
        project = null
        refreshProjects()
    }

    fun createProject(name: String, template: Template) {
        val p = store.create(name, template)
        refreshProjects()
        openProject(p)
    }

    fun renameProject(p: Project, name: String) { val np = store.rename(p, name); history.renameProject(p.name, np.name); refreshProjects() }
    fun duplicateProject(p: Project) { store.duplicate(p); refreshProjects() }
    fun deleteProject(p: Project) { store.delete(p); history.deleteProject(p.name); refreshProjects() }

    fun importProjectZip(name: String, input: java.io.InputStream) {
        val p = store.importZip(name, input)
        refreshProjects()
        openProject(p)
    }

    // ------------------------------------------------------------ files
    private fun refreshFiles() {
        val p = project ?: return
        files = store.files(p, meta.main)
    }

    fun refreshBib() {
        val p = project ?: return
        bibKeysList = files.filter { it.endsWith(".bib") }.flatMap { bibKeys(runCatching { File(p.dir, it).readText() }.getOrDefault("")) }
    }

    private fun history(name: String) = histories.getOrPut(name) { History() }

    fun openFile(name: String) {
        val p = project ?: return
        if (current.isNotEmpty()) { buffers[current] = field; flushFile(current) }
        current = name
        val v = buffers[name] ?: TextFieldValue(
            if (isTextFile(name)) runCatching { File(p.dir, name).readText() }.getOrDefault("") else "",
        )
        field = v
        syncHistoryFlags()
        misspelled = emptyList()
        scheduleSpell(0)
    }

    private fun syncHistoryFlags() {
        val h = history(current)
        canUndo = h.undo.isNotEmpty(); canRedo = h.redo.isNotEmpty()
    }

    fun newFile(name: String) {
        val p = project ?: return
        val n = name.trim().ifEmpty { return }
        val f = File(p.dir, n)
        f.parentFile?.mkdirs()
        if (!f.exists()) f.writeText(if (n.endsWith(".bib")) "@article{key2024,\n  author  = {Author},\n  title   = {Title},\n  journal = {Journal},\n  year    = {2024}\n}\n" else "")
        refreshFiles(); refreshBib()
        openFile(n)
    }

    fun importFile(name: String, bytes: ByteArray) {
        val p = project ?: return
        val n = store.importFile(p, name, bytes)
        refreshFiles(); refreshBib()
        if (isTextFile(n)) openFile(n)
    }

    fun deleteFile(name: String) {
        val p = project ?: return
        if (name == meta.main) return
        File(p.dir, name).delete()
        buffers.remove(name); histories.remove(name)
        refreshFiles(); refreshBib()
        if (current == name) openFile(meta.main)
    }

    fun renameFile(name: String, to: String) {
        val p = project ?: return
        val n = to.trim().ifEmpty { return }
        if (File(p.dir, n).exists()) return
        flushFile(current)
        File(p.dir, name).renameTo(File(p.dir, n))
        buffers.remove(name); histories.remove(name)
        if (meta.main == name) { meta = meta.copy(main = n); store.saveMeta(p, meta) }
        refreshFiles(); refreshBib()
        if (current == name) openFile(n)
    }

    fun setMain(name: String) {
        val p = project ?: return
        meta = meta.copy(main = name)
        store.saveMeta(p, meta)
        refreshFiles()
    }

    fun setEngine(engine: String) {
        val p = project ?: return
        meta = meta.copy(engine = engine)
        store.saveMeta(p, meta)
    }

    // ------------------------------------------------------------ editing
    var autoPairs = true

    /** What the keyboard sends: brackets, indentation and \begin completion are handled first. */
    fun onType(v: TextFieldValue) = onChange(if (autoPairs) smartEdit(field, v) else v)

    fun onChange(v: TextFieldValue) {
        if (v.text != field.text) {
            val h = history(current)
            val now = System.currentTimeMillis()
            if (now - h.lastPush > 700 || h.undo.isEmpty()) {
                h.undo.addLast(field)
                if (h.undo.size > 200) h.undo.removeFirst()
            }
            h.lastPush = now
            h.redo.clear()
            scheduleSave()
            scheduleSpell()
        }
        field = v
        syncHistoryFlags()
    }

    fun undo() {
        val h = history(current)
        val prev = h.undo.removeLastOrNull() ?: return
        h.redo.addLast(field)
        field = prev
        syncHistoryFlags()
        scheduleSave()
    }

    fun redo() {
        val h = history(current)
        val next = h.redo.removeLastOrNull() ?: return
        h.undo.addLast(field)
        field = next
        syncHistoryFlags()
        scheduleSave()
    }

    fun insert(snippet: String) {
        val sel = field.selection
        val text = field.text
        val before = text.substring(0, sel.min)
        val after = text.substring(sel.max)
        val caret = snippet.indexOf('‸')
        val s = snippet.replace("‸", "")
        onChange(TextFieldValue(before + s + after, TextRange(before.length + if (caret >= 0) caret else s.length)))
    }

    fun moveCaret(delta: Int) {
        val i = (field.selection.end + delta).coerceIn(0, field.text.length)
        field = field.copy(selection = TextRange(i))
    }

    /** Puts "% " in front of the selected lines, or removes it when they are all comments already. */
    fun toggleComment() {
        val t = field.text
        val a = t.lastIndexOf('\n', (field.selection.min - 1).coerceAtLeast(0)).let { if (field.selection.min == 0) 0 else it + 1 }
        var b = t.indexOf('\n', field.selection.max)
        if (b < 0) b = t.length
        val block = t.substring(a, b).split('\n')
        val allComments = block.all { it.trimStart().startsWith("%") || it.isBlank() }
        val changed = block.joinToString("\n") {
            if (allComments) it.replaceFirst(Regex("^(\\s*)% ?"), "$1") else "% $it"
        }
        onChange(TextFieldValue(t.substring(0, a) + changed + t.substring(b), TextRange(a, a + changed.length)))
    }

    fun loadTemplateText(text: String) {
        onChange(TextFieldValue(text, TextRange(0)))
        errors = emptyList(); log = ""; compileOk = null
    }

    fun goToLine(n: Int) {
        var idx = 0
        var line = 1
        val text = field.text
        while (line < n && idx < text.length) { if (text[idx] == '\n') line++; idx++ }
        field = field.copy(selection = TextRange(idx))
    }

    fun goToError(e: TexError) {
        val f = e.file
        if (f != null && f != current && f in files && isTextFile(f)) openFile(f)
        e.line?.let { goToLine(it) }
    }

    // ------------------------------------------------------------ find and replace
    fun matches(): List<Int> {
        val q = findText
        if (q.isEmpty()) return emptyList()
        val out = ArrayList<Int>()
        var i = field.text.indexOf(q, 0, ignoreCase = !matchCase)
        while (i >= 0 && out.size < 5000) {
            out.add(i)
            i = field.text.indexOf(q, i + q.length.coerceAtLeast(1), ignoreCase = !matchCase)
        }
        return out
    }

    fun findStep(dir: Int) {
        val m = matches()
        if (m.isEmpty()) return
        matchIndex = ((matchIndex + dir) % m.size + m.size) % m.size
        field = field.copy(selection = TextRange(m[matchIndex], m[matchIndex] + findText.length))
    }

    fun replaceOne() {
        val m = matches()
        if (m.isEmpty()) return
        val i = matchIndex.coerceIn(0, m.size - 1)
        val t = field.text
        onChange(TextFieldValue(t.substring(0, m[i]) + replaceText + t.substring(m[i] + findText.length), TextRange(m[i] + replaceText.length)))
    }

    fun replaceAll() {
        if (findText.isEmpty()) return
        onChange(TextFieldValue(field.text.replace(findText, replaceText, ignoreCase = !matchCase), TextRange(0)))
        matchIndex = 0
    }

    // ------------------------------------------------------------ own snippets, outline, word count, versions
    var snippets by mutableStateOf(loadSnippets())

    private fun loadSnippets(): List<Pair<String, String>> = runCatching {
        val a = org.json.JSONArray(Prefs(app).snippets)
        (0 until a.length()).map { a.getJSONObject(it).let { o -> o.getString("l") to o.getString("t") } }
    }.getOrDefault(emptyList())

    private fun saveSnippets() {
        val a = org.json.JSONArray()
        snippets.forEach { a.put(org.json.JSONObject().put("l", it.first).put("t", it.second)) }
        Prefs(app).snippets = a.toString()
    }

    fun addSnippet(label: String, text: String) {
        if (label.isBlank() || text.isEmpty()) return
        snippets = snippets + (label.trim() to text)
        saveSnippets()
    }

    fun removeSnippet(i: Int) {
        snippets = snippets.filterIndexed { j, _ -> j != i }
        saveSnippets()
    }

    class OutlineItem(val line: Int, val level: Int, val title: String)

    private val sectionRe = Regex("""\\(part|chapter|section|subsection|subsubsection|paragraph)\*?(?:\[[^\]]*\])?\{(.*)\}""")

    fun outline(): List<OutlineItem> {
        val levels = listOf("part", "chapter", "section", "subsection", "subsubsection", "paragraph")
        val raw = field.text.lines().mapIndexedNotNull { i, l ->
            if (l.trimStart().startsWith("%")) null
            else sectionRe.find(l)?.let { m -> OutlineItem(i + 1, levels.indexOf(m.groupValues[1]), m.groupValues[2].trim()) }
        }
        val base = raw.minOfOrNull { it.level } ?: 0
        return raw.map { OutlineItem(it.line, it.level - base, it.title) }
    }

    fun countWords(text: String): Int {
        val noComments = text.lines().joinToString("\n") { l ->
            val i = Regex("(?<!\\\\)%").find(l)?.range?.first ?: -1
            if (i >= 0) l.substring(0, i) else l
        }
        val body = noComments.substringAfter("\\begin{document}", noComments).substringBefore("\\end{document}")
        val stripped = body
            .replace(Regex("\\x24\\x24?[^\\x24]*\\x24\\x24?"), " ")
            .replace(Regex("\\\\[a-zA-Z]+\\*?"), " ")
            .replace(Regex("[{}\\[\\]\\\\^_&~#\\x24%]"), " ")
        return stripped.split(Regex("\\s+")).count { w -> w.any { it.isLetterOrDigit() } }
    }

    fun wordsAll(): Int {
        val p = project ?: return 0
        return files.filter { it.endsWith(".tex") }.sumOf { f ->
            countWords(if (f == current) field.text else buffers[f]?.text ?: runCatching { File(p.dir, f).readText() }.getOrDefault(""))
        }
    }

    fun versions(): List<Snapshot> = project?.let { history.list(it.name, current) } ?: emptyList()

    /** Bring an earlier version back. The text being replaced is saved as a version first, and Undo still works. */
    fun restore(s: Snapshot) {
        val p = project ?: return
        history.snapshot(p.name, current, field.text)
        onChange(TextFieldValue(history.read(s), TextRange(0)))
    }

    // ------------------------------------------------------------ saving and compiling
    private fun scheduleSave() {
        saveJob?.cancel()
        val p = project
        val name = current
        saveJob = viewModelScope.launch(Dispatchers.IO) {
            delay(800)
            if (p != null && isTextFile(name)) File(p.dir, name).writeText(field.text)
        }
    }

    private fun flushFile(name: String) {
        val p = project ?: return
        if (isTextFile(name) && name == current) runCatching { File(p.dir, name).writeText(field.text) }
    }

    fun flush() {
        saveJob?.cancel()
        flushFile(current)
    }

    fun compile() {
        val p = project ?: return
        android.util.Log.i("PDFTK", "compile() called, compiling=$compiling")
        if (compiling) return
        compiling = true
        compileOk = null
        status = t("compiling")
        viewModelScope.launch {
            withContext(Dispatchers.IO) { flush(); refreshBib() }
            val list = withContext(Dispatchers.IO) {
                p.dir.walkTopDown().filter { it.isFile && !it.name.startsWith(".") }
                    .map { ProjFile(it.relativeTo(p.dir).path.replace('\\', '/'), it.readBytes()) }.toList()
            }
            withContext(Dispatchers.IO) {
                list.filter { isTextFile(it.path) }.forEach { runCatching { history.snapshot(p.name, it.path, String(it.bytes, Charsets.UTF_8)) } }
            }
            android.util.Log.i("PDFTK", "calling the engine with ${list.size} files, engine ${meta.engine}")
            val driver = if (meta.engine == "pdftex") "pdftex_bibtex8" else "xetex_bibtex8_dvipdfmx"
            val res = TexEngine.compile(list, meta.main, driver)
            log = res.log
            errors = parseErrors(res.log)
            if (res.ok && res.pdf != null) {
                withContext(Dispatchers.IO) { outPdf.writeBytes(res.pdf) }
                pdfFile = outPdf
                pdfVersion++
                compileOk = true
                status = t("ok")
            } else {
                compileOk = false
                status = t("failed")
            }
            android.util.Log.i("PDFTK", "compile ok=${res.ok} exit=${res.exit} errors=${errors.size} pdfBytes=${res.pdf?.size}")
            if (!res.ok) android.util.Log.i("PDFTK", "log tail: " + res.log.takeLast(2500))
            compiling = false
        }
    }

    fun savePdfTo(uri: Uri): Boolean {
        val f = pdfFile ?: return false
        return runCatching {
            app.contentResolver.openOutputStream(uri)?.use { o -> f.inputStream().use { it.copyTo(o) } }
        }.isSuccess
    }
}

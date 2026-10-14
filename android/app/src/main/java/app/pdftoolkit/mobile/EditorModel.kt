package app.pdftoolkit.mobile

import android.app.Application
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

data class TexError(val line: Int?, val message: String)

/** Parses the XeTeX log: "! message" followed (a few lines later) by "l.<number> ...". */
fun parseErrors(log: String): List<TexError> {
    val lines = log.lines()
    val out = ArrayList<TexError>()
    val lre = Regex("^l\\.(\\d+)")
    for ((i, l) in lines.withIndex()) {
        if (!l.startsWith("! ")) continue
        var ln: Int? = null
        for (j in i + 1..minOf(i + 10, lines.size - 1)) {
            val m = lre.find(lines[j])
            if (m != null) { ln = m.groupValues[1].toInt(); break }
        }
        val msg = l.substring(2).trim()
        if (out.lastOrNull()?.message == msg && out.lastOrNull()?.line == ln) continue
        out += TexError(ln, msg)
    }
    return out
}

class EditorViewModel(app: Application) : AndroidViewModel(app) {
    private val projectDir = File(app.filesDir, "projects/default").also { it.mkdirs() }
    private val outPdf = File(app.cacheDir, "preview.pdf")

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

    private val undo = ArrayDeque<TextFieldValue>()
    private val redo = ArrayDeque<TextFieldValue>()
    private var lastPush = 0L
    private var saveJob: Job? = null

    init {
        val f = File(projectDir, "main.tex")
        val text = if (f.exists()) f.readText() else Templates.ARTICLE
        field = TextFieldValue(text)
    }

    fun onChange(v: TextFieldValue) {
        if (v.text != field.text) {
            val now = System.currentTimeMillis()
            if (now - lastPush > 700 || undo.isEmpty()) {
                undo.addLast(field)
                if (undo.size > 200) undo.removeFirst()
            }
            lastPush = now
            redo.clear()
            scheduleSave()
        }
        field = v
        canUndo = undo.isNotEmpty()
        canRedo = redo.isNotEmpty()
    }

    fun undo() {
        val prev = undo.removeLastOrNull() ?: return
        redo.addLast(field)
        field = prev
        canUndo = undo.isNotEmpty(); canRedo = true
        scheduleSave()
    }

    fun redo() {
        val next = redo.removeLastOrNull() ?: return
        undo.addLast(field)
        field = next
        canUndo = true; canRedo = redo.isNotEmpty()
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

    fun loadTemplate(text: String) {
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

    private fun scheduleSave() {
        saveJob?.cancel()
        saveJob = viewModelScope.launch(Dispatchers.IO) {
            delay(800)
            File(projectDir, current).writeText(field.text)
        }
    }

    fun compile() {
        if (compiling) return
        compiling = true
        compileOk = null
        status = t("compiling")
        viewModelScope.launch {
            withContext(Dispatchers.IO) { File(projectDir, current).writeText(field.text) }
            val files = withContext(Dispatchers.IO) {
                projectDir.walkTopDown().filter { it.isFile }.map { ProjFile(it.relativeTo(projectDir).path.replace('\\', '/'), it.readBytes()) }.toList()
            }
            val res = TexEngine.compile(files, current)
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
}

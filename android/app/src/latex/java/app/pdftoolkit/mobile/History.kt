package app.pdftoolkit.mobile

import android.content.Context
import java.io.File

/** One saved version of a file. */
class Snapshot(val time: Long, val file: File)

/**
 * Earlier versions of every text file, kept outside the project folder so they are never compiled, exported or counted.
 * A version is saved each time the project is compiled and the file differs from the last saved one; the last 15 are kept.
 */
class HistoryStore(ctx: Context) {
    private val root = File(ctx.filesDir, "history").also { it.mkdirs() }

    private fun dir(project: String, file: String) = File(root, project + "/" + file.replace('/', '%'))

    fun list(project: String, file: String): List<Snapshot> =
        (dir(project, file).listFiles() ?: emptyArray())
            .mapNotNull { f -> f.nameWithoutExtension.toLongOrNull()?.let { Snapshot(it, f) } }
            .sortedByDescending { it.time }

    fun snapshot(project: String, file: String, text: String) {
        val d = dir(project, file)
        d.mkdirs()
        val last = list(project, file).firstOrNull()
        if (last != null && runCatching { last.file.readText() }.getOrNull() == text) return
        File(d, "${System.currentTimeMillis()}.txt").writeText(text)
        list(project, file).drop(15).forEach { it.file.delete() }
    }

    fun read(s: Snapshot): String = runCatching { s.file.readText() }.getOrDefault("")

    fun deleteProject(project: String) { File(root, project).deleteRecursively() }

    fun renameProject(old: String, new: String) { if (old != new) File(root, old).renameTo(File(root, new)) }
}

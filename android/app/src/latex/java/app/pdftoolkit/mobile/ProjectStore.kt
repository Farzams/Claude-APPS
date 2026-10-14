package app.pdftoolkit.mobile

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.io.InputStream
import java.io.OutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream

/** One project = one folder under files/projects. */
data class Project(val name: String, val dir: File) {
    val modified: Long get() = dir.walkTopDown().filter { it.isFile }.maxOfOrNull { it.lastModified() } ?: dir.lastModified()
    val fileCount: Int get() = dir.walkTopDown().count { it.isFile && !it.name.startsWith(".") }
}

data class Meta(val main: String = "main.tex", val engine: String = "xetex")

val TEXT_EXTENSIONS = setOf("tex", "bib", "sty", "cls", "bst", "txt", "md", "cfg", "def", "ltx")

fun isTextFile(name: String) = name.substringAfterLast('.', "").lowercase() in TEXT_EXTENSIONS

class ProjectStore(ctx: Context) {
    val root = File(ctx.filesDir, "projects").also { it.mkdirs() }

    fun list(): List<Project> =
        (root.listFiles() ?: emptyArray()).filter { it.isDirectory }.map { Project(it.name, it) }.sortedByDescending { it.modified }

    private fun clean(name: String): String =
        name.replace(Regex("[\\\\/:*?\"<>|]"), " ").trim().ifEmpty { "Untitled" }

    fun uniqueName(base: String): String {
        val b = clean(base)
        var n = b
        var i = 2
        while (File(root, n).exists()) { n = "$b $i"; i++ }
        return n
    }

    fun create(name: String, template: Template): Project {
        val n = uniqueName(name)
        val d = File(root, n).also { it.mkdirs() }
        for ((f, c) in template.files) File(d, f).also { it.parentFile?.mkdirs() }.writeText(c)
        saveMeta(Project(n, d), Meta(template.main, template.engine))
        return Project(n, d)
    }

    fun rename(p: Project, newName: String): Project {
        val n = if (clean(newName) == p.name) p.name else uniqueName(newName)
        if (n != p.name) p.dir.renameTo(File(root, n))
        return Project(n, File(root, n))
    }

    fun duplicate(p: Project): Project {
        val n = uniqueName(p.name + " copy")
        p.dir.copyRecursively(File(root, n), overwrite = false)
        return Project(n, File(root, n))
    }

    fun delete(p: Project) { p.dir.deleteRecursively() }

    fun meta(p: Project): Meta = runCatching {
        val o = JSONObject(File(p.dir, ".texora.json").readText())
        Meta(o.optString("main", "main.tex"), o.optString("engine", "xetex"))
    }.getOrDefault(Meta())

    fun saveMeta(p: Project, m: Meta) {
        File(p.dir, ".texora.json").writeText(JSONObject().put("main", m.main).put("engine", m.engine).toString())
    }

    /** Relative paths of the project's files, the main file first. */
    fun files(p: Project, main: String): List<String> =
        p.dir.walkTopDown().filter { it.isFile && !it.name.startsWith(".") }
            .map { it.relativeTo(p.dir).path.replace('\\', '/') }
            .sortedWith(compareBy({ it != main }, { !isTextFile(it) }, { it.lowercase() })).toList()

    fun exportZip(p: Project, out: OutputStream) {
        ZipOutputStream(out).use { z ->
            p.dir.walkTopDown().filter { it.isFile }.forEach {
                z.putNextEntry(ZipEntry(it.relativeTo(p.dir).path.replace('\\', '/')))
                it.inputStream().use { i -> i.copyTo(z) }
                z.closeEntry()
            }
        }
    }

    fun importZip(name: String, input: InputStream): Project {
        val n = uniqueName(name.removeSuffix(".zip"))
        val d = File(root, n).also { it.mkdirs() }
        ZipInputStream(input).use { z ->
            var e = z.nextEntry
            while (e != null) {
                val target = File(d, e.name)
                if (!e.isDirectory && target.canonicalPath.startsWith(d.canonicalPath + File.separator)) {   // no "../" tricks
                    target.parentFile?.mkdirs()
                    target.outputStream().use { z.copyTo(it) }
                }
                e = z.nextEntry
            }
        }
        val tex = d.walkTopDown().filter { it.isFile && it.extension == "tex" }.toList()
        val main = (tex.firstOrNull { it.readText().contains("\\documentclass") } ?: tex.firstOrNull())?.relativeTo(d)?.path ?: "main.tex"
        saveMeta(Project(n, d), Meta(main.replace('\\', '/')))
        return Project(n, d)
    }

    fun importFile(p: Project, name: String, bytes: ByteArray): String {
        var n = name.replace(Regex("[\\\\/:*?\"<>|]"), "_")
        var i = 2
        while (File(p.dir, n).exists()) { n = name.substringBeforeLast('.') + "_$i." + name.substringAfterLast('.', ""); i++ }
        File(p.dir, n).writeBytes(bytes)
        return n
    }
}

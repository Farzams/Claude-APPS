package app.pdftoolkit.mobile

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import java.io.File
import java.util.Locale

/** What kind of file something is, as far as the file manager cares. */
enum class Kind { FOLDER, PDF, BOOK, IMAGE, TEX, ARCHIVE, OTHER }

private val BOOK_EXT = setOf("epub", "fb2", "djvu", "djv", "cbz", "mobi", "txt", "html", "htm", "xps")
private val IMAGE_EXT = setOf("jpg", "jpeg", "png", "webp", "gif", "bmp", "heic")
private val TEX_EXT = setOf("tex", "bib", "sty", "cls", "bst", "ltx", "cfg", "def", "md")

fun kindOf(f: File): Kind {
    if (f.isDirectory) return Kind.FOLDER
    return when (f.extension.lowercase(Locale.ROOT)) {
        "pdf" -> Kind.PDF
        in BOOK_EXT -> Kind.BOOK
        in IMAGE_EXT -> Kind.IMAGE
        in TEX_EXT -> Kind.TEX
        "zip" -> Kind.ARCHIVE
        else -> Kind.OTHER
    }
}

/** A row of the file list. */
class Item(val file: File) {
    val isDir = file.isDirectory
    val kind = kindOf(file)
    val name: String = file.name
    val size: Long = if (isDir) 0L else file.length()
    val modified: Long = file.lastModified()
}

/** A shortcut on the file manager's start page. */
class Place(val key: String, val label: String, val dir: File)

fun fileOf(uri: Uri): File? = if (uri.scheme == "file") uri.path?.let { File(it) } else null

/** A content address that other apps may open or receive (needed to share a plain file). */
fun contentUri(ctx: Context, f: File): Uri = FileProvider.getUriForFile(ctx, ctx.packageName + ".files", f)

object Storage {
    fun granted(ctx: Context): Boolean =
        if (Build.VERSION.SDK_INT >= 30) Environment.isExternalStorageManager()
        else ContextCompat.checkSelfPermission(ctx, Manifest.permission.READ_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED &&
            (Build.VERSION.SDK_INT >= 29 || ContextCompat.checkSelfPermission(ctx, Manifest.permission.WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED)

    /** The Android settings page where the person allows "All files access" for this app. */
    fun settingsIntent(ctx: Context): Intent {
        val pkg = Uri.parse("package:" + ctx.packageName)
        return if (Build.VERSION.SDK_INT >= 30) Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, pkg)
        else Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, pkg)
    }

    val primary: File get() = Environment.getExternalStorageDirectory()

    /** Internal storage first, then any SD card or USB drive. */
    fun roots(ctx: Context): List<Place> {
        val out = ArrayList<Place>()
        out.add(Place("internal", t("fm.internal"), primary))
        val seen = hashSetOf(primary.absolutePath)
        for (d in ctx.getExternalFilesDirs(null)) {
            val root = d?.absolutePath?.substringBefore("/Android/") ?: continue
            if (root != d.absolutePath && seen.add(root) && File(root).exists()) out.add(Place("sd$root", t("fm.sd") + " " + File(root).name, File(root)))
        }
        return out
    }

    private fun firstExisting(vararg rel: String): File? = rel.map { File(primary, it) }.firstOrNull { it.isDirectory }

    /** The usual folders people keep documents in, only those that exist on this phone. */
    fun places(ctx: Context): List<Place> {
        val out = ArrayList<Place>()
        fun add(key: String, label: String, f: File?) { if (f != null) out.add(Place(key, label, f)) }
        add("downloads", t("fm.downloads"), firstExisting("Download", "Downloads"))
        add("documents", t("fm.documents"), firstExisting("Documents"))
        add("camera", t("fm.camera"), firstExisting("DCIM/Camera", "DCIM"))
        add("pictures", t("fm.pictures"), firstExisting("Pictures"))
        add("books", t("fm.books"), firstExisting("Books", "Download/Books"))
        add("telegram", "Telegram", firstExisting("Download/Telegram", "Telegram/Telegram Documents", "Telegram"))
        add("whatsapp", "WhatsApp", firstExisting("Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Documents", "WhatsApp/Media/WhatsApp Documents"))
        return out
    }

    fun listDir(dir: File): List<Item> =
        (dir.listFiles() ?: emptyArray()).filter { !it.name.startsWith(".") }.map { Item(it) }

    /** Looks for names containing [query] below [root]; hidden folders and other apps' private folders are skipped. */
    fun search(root: File, query: String, limit: Int = 300): List<Item> {
        val q = query.trim().lowercase(Locale.ROOT)
        if (q.isEmpty()) return emptyList()
        val out = ArrayList<Item>()
        fun walk(d: File, depth: Int) {
            if (out.size >= limit || depth > 7) return
            val children = d.listFiles() ?: return
            for (c in children) {
                if (out.size >= limit) return
                if (c.name.startsWith(".")) continue
                if (c.name.lowercase(Locale.ROOT).contains(q)) out.add(Item(c))
                if (c.isDirectory) {
                    val p = c.absolutePath
                    if (p.endsWith("/Android/data") || p.endsWith("/Android/obb")) continue
                    walk(c, depth + 1)
                }
            }
        }
        walk(root, 0)
        return out
    }

    fun unique(dir: File, name: String): File {
        var f = File(dir, name)
        if (!f.exists()) return f
        val base = name.substringBeforeLast('.', name)
        val ext = name.substringAfterLast('.', "").let { if (it.isEmpty()) "" else ".$it" }
        var n = 1
        while (f.exists()) { f = File(dir, "$base ($n)$ext"); n++ }
        return f
    }

    fun rename(f: File, newName: String): Boolean {
        val n = newName.trim()
        if (n.isEmpty() || '/' in n) return false
        val target = File(f.parentFile, n)
        return !target.exists() && f.renameTo(target)
    }

    fun delete(f: File): Boolean = f.deleteRecursively()

    fun copy(f: File, destDir: File): Boolean = runCatching {
        val target = unique(destDir, f.name)
        if (f.isDirectory) f.copyRecursively(target, overwrite = false) else { f.copyTo(target); true }
    }.getOrDefault(false)

    fun move(f: File, destDir: File): Boolean {
        if (f.isDirectory && destDir.absolutePath.startsWith(f.absolutePath)) return false
        val target = unique(destDir, f.name)
        if (f.renameTo(target)) return true
        return copy(f, destDir) && f.deleteRecursively()
    }
}

/** Small things the file manager remembers: last folder, pinned folders, recent files, sort order, view. */
class FileMemory(ctx: Context) {
    companion object {
        /** The folder a picker should open in: next to [near] when that is a plain file, otherwise the last folder used. */
        fun startFor(near: Uri?): File? {
            val beside = near?.let { fileOf(it) }?.parentFile
            if (beside != null && beside.isDirectory) return beside
            val last = LaunchedFilesMemory.get()?.lastDir.orEmpty()
            return if (last.isNotEmpty() && File(last).isDirectory) File(last) else null
        }
    }

    private val sp = ctx.getSharedPreferences("files", Context.MODE_PRIVATE)

    private fun list(key: String): List<String> = sp.getString(key, "")?.split('\n')?.filter { it.isNotEmpty() } ?: emptyList()
    private fun save(key: String, v: List<String>) = sp.edit().putString(key, v.joinToString("\n")).apply()

    var lastDir: String
        get() = sp.getString("last_dir", "") ?: ""
        set(v) = sp.edit().putString("last_dir", v).apply()
    var sort: String
        get() = sp.getString("sort", "name") ?: "name"
        set(v) = sp.edit().putString("sort", v).apply()
    var descending: Boolean
        get() = sp.getBoolean("desc", false)
        set(v) = sp.edit().putBoolean("desc", v).apply()
    var grid: Boolean
        get() = sp.getBoolean("grid", true)
        set(v) = sp.edit().putBoolean("grid", v).apply()

    fun pinned(): List<File> = list("pinned").map { File(it) }.filter { it.isDirectory }
    fun isPinned(d: File) = list("pinned").contains(d.absolutePath)
    fun togglePin(d: File) {
        val l = list("pinned").toMutableList()
        if (!l.remove(d.absolutePath)) l.add(d.absolutePath)
        save("pinned", l)
    }

    fun recent(): List<File> = list("recent").map { File(it) }.filter { it.isFile }
    fun addRecent(f: File) {
        if (!f.isFile) return
        save("recent", (listOf(f.absolutePath) + list("recent").filter { it != f.absolutePath }).take(20))
    }
}


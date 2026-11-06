package app.linuxpad.runtime

import android.system.Os
import org.apache.commons.compress.archivers.tar.TarArchiveEntry
import org.apache.commons.compress.archivers.tar.TarArchiveInputStream
import java.io.File
import java.io.FileInputStream
import java.util.zip.GZIPInputStream

/** Unpacks a root filesystem tarball without root: keeps symlinks and permission bits, skips device nodes (PRoot provides /dev). */
object TarExtractor {
    fun extractTarGz(archive: File, dest: File, onFiles: (Int) -> Unit) {
        val root = dest.canonicalPath
        var count = 0
        // the Android build tools unpack ".tar.gz" files inside assets and keep them as ".tar", so both forms are read
        val raw = FileInputStream(archive).buffered(1 shl 16)
        raw.mark(2)
        val gzip = raw.read() == 0x1f && raw.read() == 0x8b
        raw.reset()
        TarArchiveInputStream(if (gzip) GZIPInputStream(raw) else raw).use { tar ->
            while (true) {
                val e: TarArchiveEntry = tar.nextTarEntry ?: break
                val rel = e.name.removePrefix("./").trimEnd('/')
                if (rel.isEmpty()) continue
                val target = File(dest, rel)
                // never write outside the destination, whatever the archive says
                require(target.canonicalPath.startsWith(root)) { "unsafe path in archive: ${e.name}" }
                val base = target.name
                if (base == ".wh..wh..opq") { target.parentFile?.listFiles()?.forEach { it.deleteRecursively() }; continue }
                if (base.startsWith(".wh.")) { File(target.parentFile, base.removePrefix(".wh.")).deleteRecursively(); continue }
                target.parentFile?.mkdirs()
                when {
                    e.isDirectory -> { target.mkdirs(); Os.chmod(target.path, (e.mode and 0xFFF) or 0x1C0) }   // owner can always enter and write
                    e.isSymbolicLink -> { target.delete(); Os.symlink(e.linkName, target.path) }
                    e.isLink -> {
                        val src = File(dest, e.linkName.removePrefix("./"))
                        target.delete()
                        try { Os.link(src.path, target.path) }                // Android often forbids hard links: copy instead
                        catch (_: Exception) { src.copyTo(target, overwrite = true); Os.chmod(target.path, (e.mode and 0xFFF) or 0x180) }
                    }
                    e.isFile -> {
                        target.delete()
                        target.outputStream().buffered(1 shl 16).use { tar.copyTo(it) }
                        Os.chmod(target.path, (e.mode and 0xFFF) or 0x180)
                    }
                    else -> continue                                          // devices, fifos
                }
                if (++count % 500 == 0) onFiles(count)
            }
        }
        onFiles(count)
    }

    /** Copies the tarball asset "name.tar.gz" (or "name.tar", which is what the build tools leave of it) to the cache; null if absent. */
    fun assetToFile(ctx: android.content.Context, name: String): File? {
        for (suffix in listOf(".tar.gz", ".tar")) {
            val out = File(ctx.cacheDir, "asset-" + name.replace('/', '_') + suffix)
            try {
                ctx.assets.open(name + suffix).use { input -> out.outputStream().use { input.copyTo(it) } }
                return out
            } catch (_: Exception) { }
        }
        return null
    }

    fun assetExists(ctx: android.content.Context, name: String): Boolean =
        listOf(".tar.gz", ".tar").any { runCatching { ctx.assets.open(name + it).close(); true }.getOrDefault(false) }
}

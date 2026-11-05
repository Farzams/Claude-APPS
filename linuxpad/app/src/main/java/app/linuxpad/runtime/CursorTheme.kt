package app.linuxpad.runtime

import android.graphics.Bitmap
import android.system.Os
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import kotlin.math.max
import kotlin.math.roundToInt

/**
 * Builds the cursor theme "LinuxPad" at an exact pixel size from an installed one (Adwaita or DMZ).
 * Ready-made cursor themes only ship a few fixed sizes (24, 32, 48...), so the size we want, for example 40, is made here:
 * for every cursor the nearest larger image is scaled to the target (hot spot included) and written as an Xcursor file.
 */
object CursorTheme {
    const val NAME = "LinuxPad"
    private val SOURCES = listOf("Adwaita", "DMZ-White", "whiteglass")
    private const val IMAGE_CHUNK = 0xfffd0002L.toInt()

    private class Img(val size: Int, val w: Int, val h: Int, val xhot: Int, val yhot: Int, val delay: Int, val argb: IntArray)

    /** Returns the name of the source theme used, or null when none is installed. Skips work when the size is already built. */
    fun ensure(root: File, targetPx: Int): String? {
        val icons = File(root, "usr/share/icons")
        val out = File(icons, "$NAME/cursors")
        val marker = File(icons, "$NAME/size")
        if (marker.exists() && marker.readText().trim() == targetPx.toString() && out.isDirectory) return NAME
        val source = SOURCES.map { File(icons, "$it/cursors") }.firstOrNull { it.isDirectory } ?: return null
        out.deleteRecursively(); out.mkdirs()
        source.listFiles()?.forEach { f ->
            val dest = File(out, f.name)
            if (Files.isSymbolicLink(f.toPath())) {
                Os.symlink(Os.readlink(f.path), dest.path)
            } else {
                runCatching { dest.writeBytes(scaleFile(f.readBytes(), targetPx)) }
            }
        }
        File(icons, "$NAME/index.theme").writeText("[Icon Theme]\nName=$NAME\nComment=Cursors at ${targetPx}px\n")
        marker.writeText(targetPx.toString())
        return NAME
    }

    private fun scaleFile(data: ByteArray, target: Int): ByteArray {
        val b = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN)
        require(b.getInt(0) == 0x72756358) { "not an Xcursor file" }          // "Xcur"
        val ntoc = b.getInt(12)
        val images = ArrayList<Img>()
        for (i in 0 until ntoc) {
            val type = b.getInt(16 + i * 12)
            val pos = b.getInt(16 + i * 12 + 8)
            if (type != IMAGE_CHUNK) continue
            val size = b.getInt(pos + 8)
            val w = b.getInt(pos + 16); val h = b.getInt(pos + 20)
            val px = IntArray(w * h) { b.getInt(pos + 36 + it * 4) }
            images += Img(size, w, h, b.getInt(pos + 24), b.getInt(pos + 28), b.getInt(pos + 32), px)
        }
        require(images.isNotEmpty()) { "no images" }
        val sizes = images.map { it.size }.distinct().sorted()
        val use = sizes.firstOrNull { it >= target } ?: sizes.last()           // nearest larger: downscaling stays sharp
        val frames = images.filter { it.size == use }.map { scale(it, target) }

        val total = 16 + frames.size * 12 + frames.sumOf { 36 + it.w * it.h * 4 }
        val o = ByteBuffer.allocate(total).order(ByteOrder.LITTLE_ENDIAN)
        o.putInt(0x72756358).putInt(16).putInt(0x10000).putInt(frames.size)
        var pos = 16 + frames.size * 12
        frames.forEach { o.putInt(IMAGE_CHUNK).putInt(target).putInt(pos); pos += 36 + it.w * it.h * 4 }
        frames.forEach {
            o.putInt(36).putInt(IMAGE_CHUNK).putInt(target).putInt(1).putInt(it.w).putInt(it.h).putInt(it.xhot).putInt(it.yhot).putInt(it.delay)
            it.argb.forEach { p -> o.putInt(p) }
        }
        return o.array()
    }

    private fun scale(src: Img, target: Int): Img {
        val ratio = target.toFloat() / src.size
        val nw = max(1, (src.w * ratio).roundToInt()); val nh = max(1, (src.h * ratio).roundToInt())
        // Xcursor stores premultiplied ARGB; Bitmap.setPixels takes straight ARGB
        val straight = IntArray(src.argb.size) { unpremultiply(src.argb[it]) }
        val bmp = Bitmap.createBitmap(src.w, src.h, Bitmap.Config.ARGB_8888)
        bmp.setPixels(straight, 0, src.w, 0, 0, src.w, src.h)
        val scaled = Bitmap.createScaledBitmap(bmp, nw, nh, true)
        val out = IntArray(nw * nh)
        scaled.getPixels(out, 0, nw, 0, 0, nw, nh)
        return Img(target, nw, nh, (src.xhot * ratio).roundToInt().coerceIn(0, nw - 1), (src.yhot * ratio).roundToInt().coerceIn(0, nh - 1),
            src.delay, IntArray(out.size) { premultiply(out[it]) })
    }

    private fun unpremultiply(p: Int): Int {
        val a = p ushr 24
        if (a == 0 || a == 255) return p
        fun c(shift: Int) = (((p ushr shift) and 0xFF) * 255 / a).coerceAtMost(255)
        return (a shl 24) or (c(16) shl 16) or (c(8) shl 8) or c(0)
    }

    private fun premultiply(p: Int): Int {
        val a = p ushr 24
        if (a == 255) return p
        fun c(shift: Int) = ((p ushr shift) and 0xFF) * a / 255
        return (a shl 24) or (c(16) shl 16) or (c(8) shl 8) or c(0)
    }
}

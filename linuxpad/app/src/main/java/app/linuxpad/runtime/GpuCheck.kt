package app.linuxpad.runtime

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.io.File
import java.io.RandomAccessFile
import kotlin.concurrent.thread

/**
 * First step of GPU support, and it changes nothing: it only reports whether this tablet lets the app (and the Linux system inside it)
 * open the Adreno GPU device, which a hardware-accelerated desktop would need.
 */
object GpuCheck {
    var result by mutableStateOf(""); private set
    var running by mutableStateOf(false); private set

    fun run(ctx: Context) {
        if (running) return
        running = true; result = "Checking..."
        val app = ctx.applicationContext
        thread(name = "linuxpad-gpucheck") {
            val out = StringBuilder()
            fun line(s: String) { out.appendLine(s); result = out.toString() }
            try {
                line("Device: ${Build.MANUFACTURER} ${Build.MODEL}, Android ${Build.VERSION.RELEASE}")
                line("Chip: ${Build.HARDWARE}" + (if (Build.VERSION.SDK_INT >= 31) ", ${Build.SOC_MODEL}" else ""))
                val vk = app.packageManager.systemAvailableFeatures.filter { it.name?.contains("vulkan") == true }
                line("Android Vulkan: " + (if (vk.isEmpty()) "not reported" else vk.joinToString { "${it.name?.substringAfterLast('.')} ${it.version}" }))
                val node = File("/dev/kgsl-3d0")
                line("GPU device /dev/kgsl-3d0: " + if (!node.exists()) "not visible to apps" else "present (read=${node.canRead()}, write=${node.canWrite()})")
                if (node.exists()) {
                    val open = runCatching { RandomAccessFile(node, "rw").close() }
                    line("  app can open it: " + if (open.isSuccess) "yes" else "NO (${open.exceptionOrNull()?.message})")
                }
                if (File(LinuxSystem.rootDir(app), "bin/sh").exists() || File(LinuxSystem.rootDir(app), "usr/bin/sh").exists()) {
                    line("Inside Linux:")
                    Proot.exec(app, LinuxSystem.rootDir(app), listOf("/bin/sh", "-c",
                        "ls -l /dev/kgsl-3d0 2>&1; if [ -r /dev/kgsl-3d0 ] && [ -w /dev/kgsl-3d0 ]; then echo 'Linux can read and write the GPU device'; else echo 'Linux cannot open the GPU device'; fi; " +
                        "ls /usr/lib/aarch64-linux-gnu/libvulkan* 2>/dev/null | head -3; ls /usr/share/vulkan/icd.d 2>/dev/null | head"), emptyList()) { line("  $it") }
                } else line("Linux is not installed yet, so only the app side was checked.")
                line("Result: nothing was changed. Send this text if you want GPU support to be tried.")
            } catch (e: Throwable) {
                line("Error: ${e.javaClass.simpleName}: ${e.message}")
            } finally { running = false }
        }
    }
}

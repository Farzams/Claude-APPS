package app.linuxpad.runtime

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import app.linuxpad.x11.X11Server
import java.io.File
import kotlin.concurrent.thread

/**
 * Experimental GPU support: the Mesa build for Android containers (Turnip and the OpenGL driver for the Adreno KGSL device) lives in its own
 * folder /opt/mesa-gpu inside Linux and is switched on only by environment variables when the desktop starts. The Linux system's own
 * graphics libraries are never replaced, so turning it off (or deleting the folder) always returns to the safe software drawing.
 */
object Gpu {
    const val DIR = "/opt/mesa-gpu"
    private const val ASSET = "gpu/mesa-android"
    private const val LIBS = "libgl1-mesa-dri libglx-mesa0 libegl-mesa0 mesa-vulkan-drivers mesa-utils vulkan-tools"

    val MODES = listOf("off", "native", "zink")

    var installing by mutableStateOf(false); private set
    var progress by mutableStateOf(0f); private set
    var label by mutableStateOf(""); private set
    var error by mutableStateOf<String?>(null); private set
    var testing by mutableStateOf(false); private set
    var testResult by mutableStateOf(""); private set

    private fun prefs(ctx: Context) = ctx.getSharedPreferences("linuxpad", Context.MODE_PRIVATE)
    fun mode(ctx: Context): String = prefs(ctx).getString("gpu_mode", "off") ?: "off"
    fun setMode(ctx: Context, m: String) = prefs(ctx).edit().putString("gpu_mode", m).apply()
    fun sysmem(ctx: Context) = prefs(ctx).getBoolean("gpu_sysmem", false)
    fun setSysmem(ctx: Context, on: Boolean) = prefs(ctx).edit().putBoolean("gpu_sysmem", on).apply()

    /** True when this build carries the Mesa package. */
    fun available(ctx: Context): Boolean = TarExtractor.assetExists(ctx, ASSET)
    fun installed(ctx: Context) = File(LinuxSystem.rootDir(ctx), "opt/mesa-gpu/INSTALLED").isFile
    fun active(ctx: Context) = installed(ctx) && mode(ctx) != "off"

    /** Called when the desktop closed right after starting with the GPU on: back to the safe mode. */
    fun disable(ctx: Context) = setMode(ctx, "off")

    /** Shell lines that point Linux programs at the GPU drivers; empty for the software mode. */
    fun exports(ctx: Context): String {
        if (!active(ctx)) return ""
        val lib = "$DIR/usr/lib/aarch64-linux-gnu"
        return buildString {
            append("export LD_LIBRARY_PATH=$lib\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}; ")
            append("export LIBGL_DRIVERS_PATH=$lib/dri; ")
            append("export __EGL_VENDOR_LIBRARY_FILENAMES=$DIR/usr/share/glvnd/egl_vendor.d/50_mesa.json; ")
            append("export VK_ICD_FILENAMES=$DIR/usr/share/vulkan/icd.d/freedreno_icd.aarch64.json; ")
            append("export MESA_LOADER_DRIVER_OVERRIDE=${if (mode(ctx) == "zink") "zink" else "kgsl"}; ")
            if (sysmem(ctx)) append("export TU_DEBUG=sysmem FD_MESA_DEBUG=sysmem; ")
        }
    }

    /** Installs Mesa's helper libraries from Debian, then unpacks the package from the app into /opt/mesa-gpu. */
    fun install(ctx: Context) {
        if (installing) return
        val app = ctx.applicationContext
        if (!LinuxSystem.installed) { error = "Set up the Linux system first"; return }
        installing = true; error = null; progress = 0f; label = "Starting"
        KeepAlive.acquire(app, "gpu", "Installing the GPU drivers")
        thread(name = "linuxpad-gpu-install") {
            try {
                val code = LinuxSystem.apt(app, LIBS) { f, l -> progress = f * 0.85f; label = l }
                if (code != 0) throw IllegalStateException("Installing the graphics libraries failed (exit $code). See Details in Setup.")
                label = "Unpacking the GPU drivers"; progress = 0.88f
                val root = LinuxSystem.rootDir(app)
                val dest = File(root, "opt/mesa-gpu").apply { deleteRecursively(); mkdirs() }
                val tmp = TarExtractor.assetToFile(app, ASSET) ?: throw IllegalStateException("This build does not carry the GPU drivers package")
                TarExtractor.extractTarGz(tmp, dest) { }
                tmp.delete()
                // the Vulkan driver is looked up by the path written in its description file: point it into the new folder
                val icd = File(dest, "usr/share/vulkan/icd.d/freedreno_icd.aarch64.json")
                icd.writeText(icd.readText().replace(Regex("\"library_path\"\\s*:\\s*\"[^\"]*\""), "\"library_path\": \"$DIR/usr/lib/aarch64-linux-gnu/libvulkan_freedreno.so\""))
                File(dest, "INSTALLED").writeText("mesa-26.2.0-devel-20260709\n")
                progress = 1f; label = "Done"
                if (mode(app) == "off") setMode(app, "native")
            } catch (e: Throwable) {
                error = e.message ?: e.javaClass.simpleName
            } finally {
                installing = false
                KeepAlive.release(app, "gpu")
            }
        }
    }

    /** Removes the GPU drivers (the helper libraries from Debian stay). */
    fun remove(ctx: Context) {
        File(LinuxSystem.rootDir(ctx), "opt/mesa-gpu").deleteRecursively()
        setMode(ctx, "off")
    }

    /** Asks the running desktop's X server which graphics card draws OpenGL and Vulkan with the current GPU settings. */
    fun test(ctx: Context) {
        if (testing) return
        val app = ctx.applicationContext
        if (LinuxSystem.session != "running") { testResult = "Start the desktop first, then run the test."; return }
        testing = true; testResult = "Testing..."
        thread(name = "linuxpad-gpu-test") {
            val out = StringBuilder()
            try {
                val cmd = "export DISPLAY=:0 XDG_RUNTIME_DIR=/tmp/runtime-root; ${exports(app)}" +
                    "echo \"mode: ${mode(app)}${if (sysmem(app)) " + safe mode" else ""}\"; echo '--- OpenGL'; " +
                    "timeout 60 glxinfo -B 2>&1 | grep -E 'renderer|OpenGL version|direct rendering|rror' ; " +
                    "echo '--- Vulkan'; timeout 60 vulkaninfo --summary 2>&1 | grep -E 'deviceName|apiVersion|driverName|ERROR|rror' | head -6"
                Proot.exec(app, LinuxSystem.rootDir(app), listOf("/bin/sh", "-c", cmd),
                    listOf("${X11Server.runtimeDir(app).absolutePath}/.X11-unix" to "/tmp/.X11-unix")) { out.appendLine(it); testResult = out.toString() }
                if (out.isEmpty()) testResult = "No answer. Is glxinfo installed? Install the GPU drivers first."
            } catch (e: Throwable) {
                testResult = "Error: ${e.javaClass.simpleName}: ${e.message}"
            } finally { testing = false }
        }
    }
}

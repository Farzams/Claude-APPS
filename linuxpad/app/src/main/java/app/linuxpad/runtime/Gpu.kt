package app.linuxpad.runtime

import android.content.Context
import java.io.File

/**
 * GPU support (Adreno through the KGSL device): the Mesa build for Android containers (Turnip and the OpenGL driver) lives in its own
 * folder /opt/mesa-gpu inside Linux and is switched on by environment variables when the desktop starts. The Linux system's own
 * graphics libraries are never replaced. Setup installs it; it is always used. If a desktop start with the GPU closes right away,
 * the next start draws with the processor once, then the GPU is tried again.
 */
object Gpu {
    const val DIR = "/opt/mesa-gpu"
    private const val ASSET = "gpu/mesa-android"
    private const val LIBS = "libgl1-mesa-dri libglx-mesa0 libegl-mesa0 mesa-vulkan-drivers mesa-utils vulkan-tools"

    private fun prefs(ctx: Context) = ctx.getSharedPreferences("linuxpad", Context.MODE_PRIVATE)

    /** True when this build carries the Mesa package. */
    fun available(ctx: Context): Boolean = TarExtractor.assetExists(ctx, ASSET)
    fun installed(ctx: Context) = File(LinuxSystem.rootDir(ctx), "opt/mesa-gpu/INSTALLED").isFile

    /** Decides for one desktop start: the GPU, unless the last start with it failed (then once without). */
    fun useForThisStart(ctx: Context): Boolean {
        if (!installed(ctx)) return false
        if (prefs(ctx).getBoolean("gpu_skip_next", false)) { prefs(ctx).edit().putBoolean("gpu_skip_next", false).apply(); return false }
        return true
    }

    /** Called when the desktop closed right after starting with the GPU. */
    fun skipNextStart(ctx: Context) = prefs(ctx).edit().putBoolean("gpu_skip_next", true).apply()

    /** Shell lines that point Linux programs at the GPU drivers. */
    fun exports(): String {
        val lib = "$DIR/usr/lib/aarch64-linux-gnu"
        return "export LD_LIBRARY_PATH=$lib\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}; " +
            "export LIBGL_DRIVERS_PATH=$lib/dri; " +
            "export __EGL_VENDOR_LIBRARY_FILENAMES=$DIR/usr/share/glvnd/egl_vendor.d/50_mesa.json; " +
            "export VK_ICD_FILENAMES=$DIR/usr/share/vulkan/icd.d/freedreno_icd.aarch64.json; " +
            "export MESA_LOADER_DRIVER_OVERRIDE=kgsl; "
    }

    /** Installs Mesa's helper libraries from Debian, then unpacks the package from the app into /opt/mesa-gpu. Throws on failure. */
    fun installNow(app: Context, onProgress: (Float, String) -> Unit) {
        val code = LinuxSystem.apt(app, LIBS) { f, l -> onProgress(f * 0.85f, l) }
        if (code != 0) throw IllegalStateException("Installing the graphics libraries for the GPU failed (exit $code). See Details in Setup.")
        onProgress(0.88f, "Unpacking the GPU drivers")
        val root = LinuxSystem.rootDir(app)
        val dest = File(root, "opt/mesa-gpu").apply { deleteRecursively(); mkdirs() }
        val tmp = TarExtractor.assetToFile(app, ASSET) ?: throw IllegalStateException("This build does not carry the GPU drivers package")
        TarExtractor.extractTarGz(tmp, dest) { }
        tmp.delete()
        // the Vulkan driver is looked up by the path written in its description file: point it into the new folder
        val icd = File(dest, "usr/share/vulkan/icd.d/freedreno_icd.aarch64.json")
        icd.writeText(icd.readText().replace(Regex("\"library_path\"\\s*:\\s*\"[^\"]*\""), "\"library_path\": \"$DIR/usr/lib/aarch64-linux-gnu/libvulkan_freedreno.so\""))
        File(dest, "INSTALLED").writeText("mesa-26.2.0-devel-20260709\n")
        onProgress(1f, "Done")
    }

}

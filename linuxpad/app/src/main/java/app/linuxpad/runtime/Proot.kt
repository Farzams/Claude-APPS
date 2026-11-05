package app.linuxpad.runtime

import android.content.Context
import java.io.File
import java.util.concurrent.TimeUnit

/** Runs the bundled PRoot. Android only executes files from the native library directory, so PRoot ships there as libproot.so. */
object Proot {
    fun binary(ctx: Context) = File(ctx.applicationInfo.nativeLibraryDir, "libproot.so")
    fun loader(ctx: Context) = File(ctx.applicationInfo.nativeLibraryDir, "libproot-loader.so")

    data class Result(val exitCode: Int, val output: String)

    fun run(ctx: Context, args: List<String>, timeoutSec: Long = 20): Result {
        val bin = binary(ctx)
        if (!bin.exists()) return Result(-1, "libproot.so is missing from ${bin.parent} (this build was made without PRoot)")
        val tmp = File(ctx.cacheDir, "proot-tmp").apply { mkdirs() }
        val pb = ProcessBuilder(listOf(bin.path) + args).redirectErrorStream(true)
        pb.environment().apply {
            put("PROOT_LOADER", loader(ctx).path)
            put("PROOT_TMP_DIR", tmp.path)
        }
        return try {
            val p = pb.start()
            val text = p.inputStream.bufferedReader().readText()
            if (!p.waitFor(timeoutSec, TimeUnit.SECONDS)) { p.destroyForcibly(); Result(-2, text + "\n(timeout)") } else Result(p.exitValue(), text)
        } catch (e: Exception) {
            Result(-3, "${e.javaClass.simpleName}: ${e.message}")
        }
    }

    /** Version, then a real sandboxed command, so we know both the binary and the syscall tracing work on this device. */
    fun selfTest(ctx: Context): String {
        val v = run(ctx, listOf("--version"))
        val t = run(ctx, listOf("-0", "-r", "/", "/system/bin/sh", "-c", "echo hello from proot; id; uname -a"))
        return "proot --version (exit ${v.exitCode}):\n${v.output.trim().lines().take(3).joinToString("\n")}\n\n" +
            "sandboxed shell (exit ${t.exitCode}):\n${t.output.trim()}\n\n" +
            "native dir: ${ctx.applicationInfo.nativeLibraryDir}\nabis: ${android.os.Build.SUPPORTED_ABIS.joinToString()}"
    }
}

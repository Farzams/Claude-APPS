package app.linuxpad.audio

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.io.File
import java.net.InetSocketAddress
import java.net.Socket
import java.util.zip.ZipInputStream
import kotlin.concurrent.thread

/**
 * Sound for the Linux system: a PulseAudio server that lives in the app and talks to Android through OpenSL ES (speaker, headphones,
 * and the microphone when allowed). Linux programs reach it over the device-local network (127.0.0.1) with a private cookie, because
 * PRoot cannot reliably carry file sockets. The runtime comes from checksum-pinned official Termux packages (see tools/build-pulseaudio.sh).
 */
object AudioServer {
    const val PORT = 4713
    private const val GUEST_AUTH = "/tmp/.linuxpad-pulse"

    /** off, starting, running or unavailable. */
    var state by mutableStateOf("off"); private set
    var detail by mutableStateOf(""); private set

    private var process: Process? = null
    private var stopping = false

    private fun prefs(ctx: Context) = ctx.getSharedPreferences("linuxpad", Context.MODE_PRIVATE)
    fun outputEnabled(ctx: Context) = prefs(ctx).getBoolean("audio_output", true)
    fun micEnabled(ctx: Context) = prefs(ctx).getBoolean("audio_mic", false)
    fun setOutput(ctx: Context, on: Boolean) = prefs(ctx).edit().putBoolean("audio_output", on).apply()
    fun setMic(ctx: Context, on: Boolean) = prefs(ctx).edit().putBoolean("audio_mic", on).apply()
    fun micPermitted(ctx: Context) = ctx.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    private fun authDir(ctx: Context) = File(ctx.filesDir, "runtime/audio")

    /** The folder with the cookie, shown inside Linux (read by PulseAudio clients). */
    fun bind(ctx: Context) = authDir(ctx).apply { mkdirs() }.absolutePath to GUEST_AUTH

    /** What Linux programs need to find the sound server. */
    fun guestEnv() = mapOf("PULSE_SERVER" to "tcp:127.0.0.1:$PORT", "PULSE_COOKIE" to "$GUEST_AUTH/cookie")

    fun start(ctx: Context) {
        val app = ctx.applicationContext
        synchronized(this) { if (process != null) return }
        val output = outputEnabled(app)
        val mic = micEnabled(app) && micPermitted(app)
        if (!output && !mic) { state = "off"; detail = "Sound is turned off in Settings"; return }
        state = "starting"; detail = ""
        stopping = false
        thread(name = "linuxpad-audio") {
            try {
                val runtime = installRuntime(app) ?: run { state = "unavailable"; detail = "This build has no audio runtime"; return@thread }
                val auth = authDir(app).apply { mkdirs() }
                val stateDir = File(app.filesDir, "runtime/audio-state").apply { mkdirs() }
                val conf = File(app.cacheDir, "audio/default.pa").apply { parentFile?.mkdirs() }
                conf.writeText(buildString {
                    appendLine(".fail")
                    if (output) appendLine("load-module module-sles-sink sink_name=linuxpad_output")
                    if (mic) appendLine("load-module module-sles-source source_name=linuxpad_input")
                    appendLine("load-module module-native-protocol-tcp listen=127.0.0.1 port=$PORT auth-cookie=\"${File(auth, "cookie").absolutePath}\" auth-cookie-enabled=1")
                })
                val linker = if (Build.SUPPORTED_64_BIT_ABIS.isNotEmpty()) "/system/bin/linker64" else "/system/bin/linker"
                val cmd = listOf(linker, File(runtime, "bin/pulseaudio").absolutePath, "--daemonize=no", "--fail=yes", "--exit-idle-time=-1",
                    "--disable-shm=yes", "--log-target=stderr", "--log-level=notice",
                    "--dl-search-path=${File(runtime, "modules").absolutePath}", "--file=${conf.absolutePath}")
                val pb = ProcessBuilder(cmd).directory(app.filesDir).redirectErrorStream(true)
                pb.environment().apply {
                    clear()
                    put("ANDROID_DATA", "/data"); put("ANDROID_ROOT", "/system")
                    put("ANDROID_RUNTIME_ROOT", "/apex/com.android.runtime"); put("ANDROID_TZDATA_ROOT", "/apex/com.android.tzdata")
                    put("HOME", app.filesDir.absolutePath); put("PATH", "/system/bin")
                    put("LD_LIBRARY_PATH", File(runtime, "lib").absolutePath)
                    put("PULSE_RUNTIME_PATH", auth.absolutePath); put("PULSE_STATE_PATH", stateDir.absolutePath)
                    put("TMPDIR", app.cacheDir.absolutePath)
                }
                val p = pb.start()
                synchronized(this) { process = p }
                val tail = ArrayDeque<String>()
                thread(name = "linuxpad-audio-log") {
                    p.inputStream.bufferedReader().forEachLine { line -> synchronized(tail) { tail.addLast(line); if (tail.size > 30) tail.removeFirst() } }
                    val code = runCatching { p.waitFor() }.getOrDefault(-1)
                    synchronized(this) { if (process === p) process = null }
                    if (!stopping) { state = "unavailable"; detail = "The sound server stopped (exit $code): " + synchronized(tail) { tail.takeLast(2).joinToString(" ") } }
                }
                // ready when the port accepts connections
                var up = false
                for (i in 1..40) {
                    if (!p.isAlive) break
                    up = runCatching { Socket().use { it.connect(InetSocketAddress("127.0.0.1", PORT), 200) }; true }.getOrDefault(false)
                    if (up) break
                    Thread.sleep(150)
                }
                if (up) { state = "running"; detail = (if (output) "speaker" else "") + (if (output && mic) " and " else "") + (if (mic) "microphone" else "") }
                else if (state == "starting") { state = "unavailable"; detail = "The sound server did not start: " + synchronized(tail) { tail.takeLast(2).joinToString(" ") } }
            } catch (e: Throwable) {
                state = "unavailable"; detail = "${e.javaClass.simpleName}: ${e.message}"
            }
        }
    }

    fun stop() {
        stopping = true
        synchronized(this) { process?.destroy(); process = null }
        state = "off"; detail = ""
    }

    /** Unpacks the runtime from the app's assets (once per version) and returns its folder, or null when this build has none. */
    private fun installRuntime(app: Context): File? {
        val names = app.assets.list("runtime") ?: return null
        if ("pulseaudio-runtime.zip" !in names) return null
        val dir = File(app.filesDir, "audio-runtime")
        val marker = File(dir, "VERSION")
        val zipSize = app.packageManager.getPackageInfo(app.packageName, 0).lastUpdateTime.toString()   // changes with every app update
        if (marker.exists() && File(dir, "ZIPSIZE").takeIf { it.exists() }?.readText() == zipSize && File(dir, "bin/pulseaudio").exists()) return dir
        dir.deleteRecursively(); dir.mkdirs()
        ZipInputStream(app.assets.open("runtime/pulseaudio-runtime.zip")).use { zip ->
            while (true) {
                val e = zip.nextEntry ?: break
                if (e.isDirectory) continue
                val f = File(dir, e.name)
                require(f.canonicalPath.startsWith(dir.canonicalPath)) { "unsafe path in the audio runtime" }
                f.parentFile?.mkdirs()
                f.outputStream().use { zip.copyTo(it) }
                f.setReadable(true, false); f.setExecutable(true, false)
            }
        }
        File(dir, "ZIPSIZE").writeText(zipSize)
        return dir
    }
}

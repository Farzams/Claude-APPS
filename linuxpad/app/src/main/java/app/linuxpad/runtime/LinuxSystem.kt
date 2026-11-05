package app.linuxpad.runtime

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import app.linuxpad.display.ScalePlan
import app.linuxpad.x11.X11Server
import java.io.File

/** Install state and command output of the Debian system. Lives with the process, not the screen. */
object LinuxSystem {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private const val IMAGE = "debian"
    private const val TAG = "trixie-slim"

    var progress by mutableStateOf<Registry.Progress?>(null); private set
    var error by mutableStateOf<String?>(null); private set
    var installed by mutableStateOf(false); private set
    var output by mutableStateOf(""); private set
    var running by mutableStateOf(false); private set

    fun rootDir(ctx: Context) = File(ctx.filesDir, "rootfs/debian")
    private fun root(ctx: Context) = rootDir(ctx)

    fun refresh(ctx: Context) { installed = File(root(ctx), "etc/os-release").exists() || File(root(ctx), "usr/lib/os-release").exists() }

    fun install(ctx: Context) {
        if (progress != null) return
        error = null
        val app = ctx.applicationContext
        scope.launch {
            try {
                Registry.install(IMAGE, TAG, root(app), File(app.cacheDir, "dl")) { progress = it }
            } catch (e: Throwable) {
                error = "${e.javaClass.simpleName}: ${e.message}"
            } finally {
                progress = null
                refresh(app)
            }
        }
    }

    fun remove(ctx: Context) {
        val app = ctx.applicationContext
        scope.launch { root(app).deleteRecursively(); refresh(app) }
    }

    fun run(ctx: Context, command: String) {
        if (running) return
        val app = ctx.applicationContext
        running = true; output = "$ $command\n"
        scope.launch {
            try {
                val code = Proot.exec(app, root(app), listOf("/bin/bash", "-lc", command)) { line ->
                    output = (output + line + "\n").takeLast(20_000)
                }
                output += "[exit $code]\n"
            } catch (e: Throwable) {
                output += "${e.javaClass.simpleName}: ${e.message}\n"
            } finally { running = false }
        }
    }

    private var desktop: Process? = null

    /** The pointer position as the X server sees it (from xdotool in the guest); shown in the desktop overlay. */
    var pointerText by mutableStateOf(""); private set

    /** Packages the graphics test needs: keyboard data for the X server, a terminal, test clients, fonts and a cursor theme. */
    const val GRAPHICS_PACKAGES = "xkb-data x11-xserver-utils xterm x11-apps fonts-dejavu-core dmz-cursor-theme xdotool"

    /** Starts a small test desktop (xeyes and xterm) in the Linux system, sized from [plan]. */
    fun startDesktop(ctx: Context, plan: ScalePlan) {
        val app = ctx.applicationContext
        stopDesktop()
        scope.launch {
            try {
                val root = root(app)
                File(root, "root/.Xresources").writeText(
                    "Xft.dpi: ${plan.xftDpi}\nXft.antialias: 1\nXft.hinting: 1\nXft.hintstyle: hintslight\n" +
                        "Xcursor.size: ${plan.cursorSize}\nXcursor.theme: DMZ-White\n")
                // xrdb normally runs the C preprocessor, which a minimal Debian does not have: -nocpp avoids it.
                // The root window gets a cursor of its own (otherwise it keeps the tiny default X cursor).
                val script = "export DISPLAY=:0; " +
                    "xrdb -nocpp -merge /root/.Xresources || echo 'xrdb failed'; " +
                    "echo \"Xft.dpi in the server: \$(xrdb -query | grep -i '^Xft.dpi')\"; " +
                    "xsetroot -solid '#27364d' -cursor_name left_ptr || echo 'xsetroot failed'; " +
                    "( while true; do echo \"PTR \$(xdotool getmouselocation 2>&1 | head -1)\"; sleep 0.25; done ) & " +
                    "xeyes -geometry 420x260+60+100 & " +
                    "exec xterm -geometry 80x22+60+420 -fa 'DejaVu Sans Mono' -fs 11 -bg black -fg white"
                val p = Proot.spawn(app, root, listOf("/bin/bash", "-lc", script),
                    binds = listOf("${X11Server.runtimeDir(app).absolutePath}/.X11-unix" to "/tmp/.X11-unix"),
                    env = mapOf("DISPLAY" to ":0", "XCURSOR_SIZE" to plan.cursorSize.toString()))
                desktop = p
                output = "desktop session started\n"
                p.inputStream.bufferedReader().forEachLine { line ->
                    if (line.startsWith("PTR ")) pointerText = line.removePrefix("PTR ")
                    else output = (output + line + "\n").takeLast(20_000)
                }
                output += "[desktop session ended: exit ${p.waitFor()}]\n"
            } catch (e: Throwable) {
                output += "${e.javaClass.simpleName}: ${e.message}\n"
            }
        }
    }

    fun stopDesktop() { desktop?.destroy(); desktop = null }
}

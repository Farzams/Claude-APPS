package app.linuxpad.runtime

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import app.linuxpad.display.ScalePlan
import app.linuxpad.audio.AudioServer
import app.linuxpad.x11.X11Server
import android.system.Os
import java.io.File
import kotlin.concurrent.thread
import java.nio.file.Files
import kotlin.math.roundToInt

/** Install state and command output of the Debian system. Lives with the process, not the screen. */
object LinuxSystem {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private const val IMAGE = "debian"
    private const val TAG = "trixie-slim"

    var progress by mutableStateOf<Registry.Progress?>(null); private set
    var error by mutableStateOf<String?>(null); private set
    var installed by mutableStateOf(false); private set
    var output by mutableStateOf(""); private set
    /** What the desktop session printed. Kept apart from the installation output. */
    var sessionLog by mutableStateOf(""); private set
    var running by mutableStateOf(false); private set

    fun rootDir(ctx: Context) = File(ctx.filesDir, "rootfs/debian")
    /** True once the desktop has drawn its panel and icons (written by an autostart entry inside Linux). */
    fun desktopReady(ctx: Context) = File(rootDir(ctx), "tmp/linuxpad-ready").exists()
    private fun root(ctx: Context) = rootDir(ctx)

    fun refresh(ctx: Context) { installed = File(root(ctx), "etc/os-release").exists() || File(root(ctx), "usr/lib/os-release").exists() }

    /** Bumps when something was installed or removed, so screens recompute what is present. */
    var tick by mutableIntStateOf(0); private set

    fun install(ctx: Context) {
        if (progress != null) return
        error = null
        val app = ctx.applicationContext
        KeepAlive.acquire(app, "install", "Installing the Linux system")
        scope.launch {
            try {
                Registry.install(IMAGE, TAG, root(app), File(app.cacheDir, "dl")) { progress = it }
            } catch (e: Throwable) {
                error = "${e.javaClass.simpleName}: ${e.message}"
            } finally {
                progress = null
                refresh(app); tick++
                KeepAlive.release(app, "install")
            }
        }
    }

    /** Deletes the whole Linux system: every package and every file in it. A folder without write permission would stop a plain delete, so each one is opened first. */
    fun remove(ctx: Context) {
        val app = ctx.applicationContext
        stopSession(app)
        scope.launch {
            wipe(root(app))
            File(app.filesDir, "runtime").deleteRecursively()
            File(app.cacheDir, "dl").deleteRecursively()
            packages = emptyList()
            output = ""
            refresh(app); tick++
        }
    }

    private fun wipe(f: File) {
        if (Files.isSymbolicLink(f.toPath())) { f.delete(); return }
        if (f.isDirectory) {
            runCatching { Os.chmod(f.path, 0x1C0) }   // rwx for the owner
            f.listFiles()?.forEach { wipe(it) }
        }
        f.delete()
    }

    fun run(ctx: Context, command: String) {
        if (running) return
        val app = ctx.applicationContext
        running = true; output = "$ $command\n"
        KeepAlive.acquire(app, "work", "Working in the Linux system")
        scope.launch {
            try {
                val code = Proot.exec(app, root(app), listOf("/bin/bash", "-lc", command), listOfNotNull(SharedFolder.prepare(root(app)))) { line ->
                    output = (output + line + "\n").takeLast(20_000)
                }
                output += "[exit $code]\n"
            } catch (e: Throwable) {
                output += "${e.javaClass.simpleName}: ${e.message}\n"
            } finally { running = false; tick++; KeepAlive.release(app, "work") }
        }
    }

    /** An installed package the user can remove, with its size. */
    data class Pkg(val name: String, val sizeKb: Long)

    var packages by mutableStateOf<List<Pkg>>(emptyList()); private set
    var packagesLoading by mutableStateOf(false); private set

    /**
     * Lists the packages that were installed on purpose (apt-mark showmanual), biggest first.
     * Essential and required system packages are left out, so the list cannot break the system.
     */
    fun loadPackages(ctx: Context) {
        if (packagesLoading) return
        val app = ctx.applicationContext
        packagesLoading = true
        scope.launch {
            try {
                val lines = ArrayList<String>()
                Proot.exec(app, root(app), listOf("/bin/bash", "-c",
                    "apt-mark showmanual | while read p; do dpkg-query -W -f='\${Installed-Size}\t\${Package}\t\${Essential}\t\${Priority}\n' \"\$p\" 2>/dev/null; done")) { lines += it }
                packages = lines.mapNotNull { line ->
                    val f = line.split('\t')
                    if (f.size < 4) return@mapNotNull null
                    val size = f[0].trim().toLongOrNull() ?: return@mapNotNull null
                    if (f[2].trim() == "yes" || f[3].trim() == "required") null else Pkg(f[1].trim(), size)
                }.sortedByDescending { it.sizeKb }
            } catch (e: Throwable) {
                error = "package list: ${e.message}"
            } finally { packagesLoading = false }
        }
    }

    private var desktop: Process? = null

    /** Libraries and data the desktop needs: keyboard data, fonts, icons and cursors, and the sound client library. */
    const val GRAPHICS_PACKAGES = "xkb-data x11-xserver-utils fonts-dejavu-core fonts-vazirmatn fonts-liberation librsvg2-common shared-mime-info adwaita-icon-theme dmz-cursor-theme libpulse0 pulseaudio-utils"

    /** The XFCE desktop (about 150 to 300 MB). dbus-x11 gives the session its message bus. */
    const val XFCE_PACKAGES = "xfce4 xfce4-terminal xfce4-notifyd dbus-x11 xdg-utils mousepad"

    /** Nicer fonts and icons: the Ubuntu font, Papirus icons and the Yaru theme (the Ubuntu look, on Debian). Each is tried on its own. */
    const val LOOK_PACKAGES = "fonts-ubuntu papirus-icon-theme yaru-theme-gtk xfce4-genmon-plugin"

    fun hasXfce(ctx: Context) = File(rootDir(ctx), "usr/bin/startxfce4").exists()
    fun graphicsOk(ctx: Context) = File(rootDir(ctx), "usr/share/X11/xkb").isDirectory && File(rootDir(ctx), "usr/lib/aarch64-linux-gnu/libpulse.so.0").exists()
    /** The look Linux starts with the first time. Afterwards the theme is chosen inside Linux and the app leaves it alone. */
    private const val DEFAULT_THEME = "WhiteSur-Dark"
    private const val DEFAULT_THEME_STAMP = "default-theme-v2"   // v2: double-size window buttons and the Inter font

    fun lookOk(ctx: Context) = File(rootDir(ctx), "usr/share/themes/Yaru").isDirectory || File(rootDir(ctx), "usr/share/fonts/truetype/ubuntu").isDirectory

    /** Which parts of XFCE are present, for the report. */
    fun xfceStatus(ctx: Context): String {
        val r = rootDir(ctx)
        return listOf("startxfce4", "xfce4-session", "xfwm4", "xfdesktop", "xfce4-panel", "thunar", "xfce4-terminal")
            .joinToString("  ") { name -> (if (File(r, "usr/bin/$name").exists()) "ok " else "MISSING ") + name }
    }

    // ---- the desktop session: lives with the process, not with the screen ------------------------------------------------

    /** stopped, starting or running. */
    var session by mutableStateOf("stopped"); private set
    @Volatile private var sessionId = 0   // a late "desktop ended" of an old session must not stop a new one

    /** Starts (or reconnects to) the desktop session. It keeps running when the screen is left; stopSession ends it. */
    fun startSession(ctx: Context, plan: ScalePlan) {
        val app = ctx.applicationContext
        if (session != "stopped") return
        if (!hasXfce(app)) { error = "Set up the desktop first"; return }
        session = "starting"
        val id = ++sessionId
        sessionLog = ""
        KeepAlive.acquire(app, "session", "Linux desktop is running")
        X11Server.whenFailed { error = "The X server did not start: ${X11Server.detail}"; stopSession(app) }
        X11Server.start(app, File(root(app), "usr/share/X11/xkb"))
        AudioServer.start(app)
        X11Server.whenReady { launchDesktop(app, plan, id) }
        startStatsWriter(app, id)
    }

    /** Writes a short line with memory, battery and heat into the Linux system every few seconds; the panel indicator shows it. */
    private fun startStatsWriter(app: Context, id: Int) {
        val file = File(root(app), "root/.linuxpad/stats.txt").apply { parentFile?.mkdirs() }
        thread(name = "linuxpad-stats", isDaemon = true) {
            while (id == sessionId && session != "stopped") {
                runCatching {
                    val s = DeviceStats.read(app)
                    val parts = mutableListOf("RAM ${s.memUsed * 100 / s.memTotal}%")
                    (s.cpuTempC ?: s.batteryTempC)?.let { parts += "%.0f\u00B0C".format(it) }
                    s.batteryPercent?.let { parts += "Bat $it%" }
                    val tip = "Memory ${s.memUsed / 1048576} of ${s.memTotal / 1048576} MB\nHeat: ${s.thermal}" +
                        (s.batteryTempC?.let { "\nBattery %.1f \u00B0C".format(it) } ?: "")
                    file.writeText("<txt>${parts.joinToString("  ")}</txt>\n<tool>$tip</tool>\n")
                }
                Thread.sleep(3000)
            }
        }
    }

    fun stopSession(ctx: Context) {
        val app = ctx.applicationContext
        desktop?.destroy(); desktop = null
        AudioServer.stop()
        X11Server.stop(app)
        if (session != "stopped") KeepAlive.release(app, "session")
        session = "stopped"
    }

    private fun launchDesktop(app: Context, plan: ScalePlan, id: Int) {
        scope.launch {
            try {
                val root = root(app)
                // the cursor theme at exactly the size chosen for this screen (installed themes only ship fixed sizes)
                val cursorTheme = runCatching { CursorTheme.ensure(root, plan.cursorSize) }.getOrNull()
                File(root, "root/.Xresources").writeText(
                    "Xft.dpi: ${plan.xftDpi}\nXft.antialias: 1\nXft.hinting: 1\nXft.hintstyle: hintslight\n" +
                        "Xcursor.size: ${plan.cursorSize}\n" + (if (cursorTheme != null) "Xcursor.theme: $cursorTheme\n" else "Xcursor.theme: DMZ-White\n"))
                // Persian: a monospace font with Arabic letters (DejaVu Sans Mono) draws each letter in a fixed cell and breaks the
                // joining. Put a Latin-only monospace font first so Persian comes from Vazirmatn.
                File(root, "root/.config/fontconfig").mkdirs()
                File(root, "root/.config/fontconfig/fonts.conf").writeText(
                    "<?xml version=\"1.0\"?>\n<!DOCTYPE fontconfig SYSTEM \"fonts.dtd\">\n<fontconfig>\n" +
                        "  <alias><family>sans-serif</family><prefer><family>Inter Variable</family><family>Inter</family><family>Selawik</family><family>Ubuntu</family><family>Vazirmatn</family></prefer></alias>\n" +
                        "  <alias><family>monospace</family><prefer><family>Ubuntu Mono</family><family>Liberation Mono</family><family>Vazirmatn</family></prefer></alias>\n" +
                        "</fontconfig>\n")
                File(root, "tmp/linuxpad-ready").delete()        // the start screen waits for this file
                installAssets(app, root)
                writeXfceConfig(app, root, plan, DEFAULT_THEME)
                // xrdb normally runs the C preprocessor, which a minimal Debian does not have: -nocpp avoids it.
                // The root window gets a cursor of its own (otherwise it keeps the tiny default X cursor).
                val gpuOn = Gpu.useForThisStart(app)
                val startedAt = System.currentTimeMillis()
                val script = "export DISPLAY=:0; fc-cache -f /usr/local/share/fonts >/dev/null 2>&1; " +
                    "xrdb -nocpp -merge /root/.Xresources || echo 'xrdb failed'; " +
                    "xsetroot -solid '#17161a' -cursor_name left_ptr || echo 'xsetroot failed'; " +
                    "mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root; export XDG_RUNTIME_DIR=/tmp/runtime-root; " +
                    "[ -s /etc/machine-id ] || dbus-uuidgen --ensure=/etc/machine-id; " +
                    // LinuxPad's settings are written before the desktop starts (a private session bus, ended afterwards), so the first
                    // frame already has the final panel, wallpaper and icons
                    "dbus-launch --exit-with-session sh -x /root/linuxpad-xfce-tune.sh pre >/root/linuxpad-tune.log 2>&1; echo '[tune pre]'; tail -n 40 /root/linuxpad-tune.log; " +
                    "export XDG_SESSION_TYPE=x11 GDK_BACKEND=x11 NO_AT_BRIDGE=1 XCURSOR_THEME=LinuxPad; " +
                    (if (gpuOn) Gpu.exports() else "export LIBGL_ALWAYS_SOFTWARE=1; ") +
                    "export QT_AUTO_SCREEN_SCALE_FACTOR=0 QT_SCALE_FACTOR=${plan.qtScaleFactor} QT_FONT_DPI=96; " +
                    "exec startxfce4"
                val p = Proot.spawn(app, root, listOf("/bin/bash", "-lc", script),
                    binds = listOf("${X11Server.runtimeDir(app).absolutePath}/.X11-unix" to "/tmp/.X11-unix", AudioServer.bind(app)) + listOfNotNull(SharedFolder.prepare(root)),
                    env = mapOf("DISPLAY" to ":0", "XCURSOR_SIZE" to plan.cursorSize.toString()) + AudioServer.guestEnv())
                desktop = p
                session = "running"
                p.inputStream.bufferedReader().forEachLine { line -> sessionLog = (sessionLog + line + "\n").takeLast(20_000) }
                sessionLog += "[desktop session ended: exit ${p.waitFor()}]\n"
                if (gpuOn && System.currentTimeMillis() - startedAt < 25_000) {
                    Gpu.skipNextStart(app)
                    error = "The desktop closed right after starting with the GPU. The next start draws with the processor once; after that the GPU is used again."
                }
            } catch (e: Throwable) {
                sessionLog += "${e.javaClass.simpleName}: ${e.message}\n"
            } finally {
                if (id == sessionId) stopSession(app)       // the desktop ended (for example Log Out): shut the rest down too
            }
        }
    }

    // ---- set up: everything in one go, with one progress bar -----------------------------------------------------------

    data class SetupState(val running: Boolean = false, val fraction: Float = 0f, val label: String = "", val error: String? = null)

    var setupState by mutableStateOf(SetupState()); private set
    /** How long each step of the last set-up took, for tuning the progress bar. */
    var stepTimes by mutableStateOf(""); private set

    /** Installs what is missing: Debian, graphics libraries, XFCE, then the nicer look. Parts already present are skipped. */
    fun setup(ctx: Context) {
        if (setupState.running) return
        val app = ctx.applicationContext
        setupState = SetupState(running = true, label = "Starting")
        error = null
        KeepAlive.acquire(app, "setup", "Setting up the Linux desktop")
        scope.launch {
            try {
                // one bar for everything; it only moves forward, whatever a single step reports
                fun report(base: Float, weight: Float, f: Float, label: String) {
                    val v = (base + weight * f.coerceIn(0f, 1f)).coerceAtLeast(setupState.fraction)
                    setupState = SetupState(true, v, label)
                }
                val times = mutableListOf<String>()
                fun timed(name: String, block: () -> Unit) {
                    val t0 = System.currentTimeMillis()
                    block()
                    val sec = (System.currentTimeMillis() - t0) / 1000
                    times += "$name ${sec / 60}m ${sec % 60}s"
                    stepTimes = times.joinToString(", ")
                    output += "[time] $name: ${sec / 60} min ${sec % 60} s\n"
                }
                fun stepDone() { refresh(app); tick++ }      // the screen marks the step as installed right away
                // shares of the bar, from measured times on the tablet: Debian 7, graphics 11, XFCE 16, look 54, GPU drivers 12
                var base = 0f
                // 1. the Linux system: finding (0-5 %), downloading (5-75 %), unpacking (75-95 %), configuring (95-100 %)
                if (!File(root(app), "etc/os-release").exists() && !File(root(app), "usr/lib/os-release").exists()) {
                    timed("Debian") {
                        Registry.install(IMAGE, TAG, root(app), File(app.cacheDir, "dl")) { p ->
                            val f = when {
                                p.phase.startsWith("Downloading") -> 0.05f + 0.70f * (if (p.total > 0) p.done.toFloat() / p.total else 0f)
                                p.phase.startsWith("Unpacking") -> 0.75f + 0.20f * (1f - kotlin.math.exp(-(Regex("(\\d+) files").find(p.phase)?.groupValues?.get(1)?.toFloatOrNull() ?: 0f) / 6000f))
                                p.phase.startsWith("Configuring") || p.phase == "Done" -> 0.97f
                                else -> 0.02f
                            }
                            report(base, 0.07f, f, "Debian: ${p.phase.lowercase()}")
                        }
                    }
                    stepDone()
                }
                base = 0.07f
                // 2. graphics and sound libraries
                if (!graphicsOk(app)) {
                    timed("Graphics") {
                        val code = apt(app, GRAPHICS_PACKAGES) { f, label -> report(base, 0.11f, f, label) }
                        if (code != 0) throw IllegalStateException("Installing the graphics libraries failed (exit $code). See Details.")
                    }
                    stepDone()
                }
                base += 0.11f
                // 3. XFCE
                if (!hasXfce(app)) {
                    timed("XFCE") {
                        val code = apt(app, XFCE_PACKAGES) { f, label -> report(base, 0.16f, f, label) }
                        if (code != 0) throw IllegalStateException("Installing XFCE failed (exit $code). See Details.")
                    }
                    stepDone()
                }
                base += 0.16f
                // 4. the nicer look: each package on its own, a missing one is not an error
                val missingLook = LOOK_PACKAGES.split(' ').filter { !pkgInstalled(app, it) }
                if (missingLook.isNotEmpty()) {
                    timed("Look") {
                        iconCache(app, prepare = true)      // the icon caches of every Papirus variant took tens of minutes under PRoot
                        // Papirus (tens of thousands of icons) takes most of this step
                        val share = mapOf("papirus-icon-theme" to 0.75f, "yaru-theme-gtk" to 0.14f, "fonts-ubuntu" to 0.07f, "xfce4-genmon-plugin" to 0.04f)
                        val total = missingLook.sumOf { (share[it] ?: 0.05f).toDouble() }.toFloat()
                        var at = base
                        for (pkg in missingLook) {
                            val w = 0.51f * (share[pkg] ?: 0.05f) / total
                            val from = at
                            val code = apt(app, pkg, update = false) { f, label -> report(from, w, f, label) }
                            if (code != 0) output += "[look] $pkg could not be installed (exit $code)\n"
                            at += w
                            stepDone()
                        }
                        report(base + 0.51f, 0.03f, 0f, "Building the icon cache")
                        iconCache(app, prepare = false)
                    }
                    stepDone()
                }
                base = 0.88f
                // 5. the GPU drivers (Adreno), when this build carries them; a failure here leaves the safe software drawing
                if (Gpu.available(app) && !Gpu.installed(app)) {
                    timed("GPU") {
                        try { Gpu.installNow(app) { f, l -> report(base, 0.12f, f, "GPU: $l") } }
                        catch (e: Throwable) { output += "[gpu] ${e.message}\n" }
                    }
                    stepDone()
                }
                setupState = SetupState(false, 1f, "Everything is installed")
            } catch (e: Throwable) {
                setupState = SetupState(false, setupState.fraction, "", e.message ?: e.javaClass.simpleName)
            } finally {
                refresh(app); tick++
                KeepAlive.release(app, "setup")
            }
        }
    }

    /** True when dpkg lists the package as fully installed. */
    private fun pkgInstalled(app: Context, name: String): Boolean {
        val status = File(root(app), "var/lib/dpkg/status")
        if (!status.isFile) return false
        return status.useLines { lines ->
            var current = ""
            for (line in lines) {
                if (line.startsWith("Package: ")) current = line.removePrefix("Package: ").trim()
                else if (current == name && line.startsWith("Status: ")) return@useLines line.endsWith("installed") && !line.contains("not-installed") && !line.contains("config-files")
            }
            false
        }
    }

    /**
     * Papirus ships five variants, each with tens of thousands of icons, and its installer builds an icon cache for each: far too slow
     * under PRoot. Before the install: skip the variants LinuxPad does not use and make the cache tool a no-op. After it: put the tool
     * back and build the cache of the one theme that is used.
     */
    private fun iconCache(app: Context, prepare: Boolean) {
        val bin = "/usr/bin/gtk-update-icon-cache"
        val cmd = if (prepare) {
            "mkdir -p /etc/dpkg/dpkg.cfg.d; " +
            "for v in Papirus-Dark Papirus-Light ePapirus ePapirus-Dark; do echo \"path-exclude=/usr/share/icons/\$v/*\"; done > /etc/dpkg/dpkg.cfg.d/linuxpad-icons; " +
            "if [ -x $bin ] && [ ! -e $bin.real ]; then mv -f $bin $bin.real; fi; " +
            "printf '#!/bin/sh\\nexit 0\\n' > $bin; chmod 755 $bin"
        } else {
            "rm -f /etc/dpkg/dpkg.cfg.d/linuxpad-icons; " +
            "if [ -e $bin.real ]; then mv -f $bin.real $bin; fi; " +
            "[ -d /usr/share/icons/Papirus ] && $bin -q -t -f /usr/share/icons/Papirus"
        }
        Proot.exec(app, root(app), listOf("/bin/sh", "-c", cmd), emptyList()) { line -> output = (output + line + "\n").takeLast(20_000) }
    }

    /** Runs apt in the Linux system; apt's machine-readable status becomes progress (0 to 1) and a short label, other output goes to the log. */
    internal fun apt(app: Context, packages: String, update: Boolean = true, onProgress: (Float, String) -> Unit): Int {
        onProgress(0f, if (update) "Updating package lists" else "Preparing")
        // The progress lines go to file descriptor 3 (the original output pipe) and the programs' own output to stderr. With the
        // status on descriptor 1, dpkg's maintainer scripts got an I/O error when they printed (fontconfig failed to configure).
        // If a run still fails, the half-configured packages are finished and the install is tried once more.
        val install = "apt-get -o APT::Status-Fd=3 -o Dpkg::Use-Pty=0 -y --no-install-recommends"
        val cmd = (if (update) "apt-get update -qq; " else "") +
            "$install install $packages 3>&1 1>&2 || { dpkg --configure -a 1>&2; $install -f install $packages 3>&1 1>&2; }"
        return Proot.exec(app, root(app), listOf("/bin/bash", "-c", cmd), listOfNotNull(SharedFolder.prepare(root(app)))) { line ->
            when {
                line.startsWith("dlstatus:") -> {
                    val f = line.split(':', limit = 4)
                    onProgress((f.getOrNull(2)?.toFloatOrNull() ?: 0f) / 200f, "Downloading packages")
                }
                line.startsWith("pmstatus:") -> {
                    val f = line.split(':', limit = 4)
                    onProgress(0.5f + (f.getOrNull(2)?.toFloatOrNull() ?: 0f) / 200f, (f.getOrNull(3) ?: "Installing").take(70))
                }
                else -> output = (output + line + "\n").takeLast(20_000)
            }
        }
    }

    /**
     * XFCE's panel, window title bars and desktop icons are fixed pixel sizes made for 96 dpi screens, so on this screen they
     * would be tiny. Their sizes are written here from the scale plan, before the first start.
     */
    private fun writeXfceConfig(app: Context, root: File, plan: ScalePlan, theme: String) {
        val xml = File(root, "root/.config/xfce4/xfconf/xfce-perchannel-xml").apply { mkdirs() }
        // XFCE draws everything at 2x (window scaling factor 2: panel, menus, icons, buttons, spacing, title bars).
        // Text keeps the size chosen on the device: Xft DPI is halved, because the 2x scale doubles it again.
        // Sizes set below are in logical pixels, so they are the real pixel size divided by 2.
        val scale = 2
        fun logical(realPx: Int) = (realPx + scale / 2) / scale
        val desktopIcon = logical((48 * plan.factor).roundToInt())
        val dock = logical(((48 * plan.factor) * 1.25f).roundToInt())   // the bottom dock: a quarter larger than the desktop icons
        val panel = logical(plan.panelSize)
        val themeName = when {
            File(root, "usr/share/themes/$theme/gtk-3.0").isDirectory -> theme
            File(root, "usr/share/themes/Yaru/gtk-3.0").isDirectory -> "Yaru"
            else -> "Adwaita"
        }
        val windowTheme = when {
            themeName.startsWith("WhiteSur") && File(root, "usr/share/themes/$themeName-xhdpi/xfwm4").isDirectory -> "$themeName-xhdpi"
            themeName.startsWith("WhiteSur") && File(root, "usr/share/themes/$themeName/xfwm4").isDirectory -> themeName
            else -> "Default-xhdpi"
        }
        val iconName = if (File(root, "usr/share/icons/Papirus").isDirectory) "Papirus" else "Adwaita"
        val fontFiles = File(root, "usr/local/share/fonts/selawik").listFiles()?.map { it.name }.orEmpty()
        val uiFont = when {
            fontFiles.any { it.startsWith("InterVariable") } -> "Inter Variable 11"
            fontFiles.any { it.endsWith(".ttf") } -> "Selawik 11"
            File(root, "usr/share/fonts/truetype/ubuntu").isDirectory -> "Ubuntu 11"
            else -> "Sans 10"
        }
        // Only what belongs to this screen is written on every start (scale, pointer size). The look (theme, icons, font) is written
        // when the files do not exist yet, or when the theme was changed in the app's Settings; whatever the user changes inside
        // XFCE stays.
        val prefs = app.getSharedPreferences("linuxpad", Context.MODE_PRIVATE)
        val themeChanged = prefs.getString("theme_applied", null) != DEFAULT_THEME_STAMP   // the default look is put in once
        val xs = File(xml, "xsettings.xml")
        val screenValues = mapOf("DPI" to "${plan.xftDpi / scale}", "WindowScalingFactor" to "$scale",
            "CursorThemeName" to CursorTheme.NAME, "CursorThemeSize" to "${plan.cursorSize / scale}")
        val patched = xs.isFile && patchProps(xs, screenValues + (if (themeChanged) mapOf("ThemeName" to themeName, "FontName" to uiFont) else emptyMap()))
        if (!patched) xs.writeText("""<?xml version="1.0" encoding="UTF-8"?>
<channel name="xsettings" version="1.0">
  <property name="Xft" type="empty">
    <property name="DPI" type="int" value="${plan.xftDpi / scale}"/>
    <property name="Antialias" type="int" value="1"/>
    <property name="Hinting" type="int" value="1"/>
    <property name="HintStyle" type="string" value="hintslight"/>
  </property>
  <property name="Gdk" type="empty">
    <property name="WindowScalingFactor" type="int" value="$scale"/>
  </property>
  <property name="Gtk" type="empty">
    <property name="CursorThemeName" type="string" value="${CursorTheme.NAME}"/>
    <property name="CursorThemeSize" type="int" value="${plan.cursorSize / scale}"/>
    <property name="FontName" type="string" value="$uiFont"/>
  </property>
  <property name="Net" type="empty">
    <property name="ThemeName" type="string" value="$themeName"/>
    <property name="IconThemeName" type="string" value="$iconName"/>
  </property>
</channel>
""")
        val wm = File(xml, "xfwm4.xml")
        val wmPatched = wm.isFile && (!themeChanged || patchProps(wm, mapOf("theme" to windowTheme)))
        if (!wmPatched) wm.writeText("""<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="$windowTheme"/>
    <property name="use_compositing" type="bool" value="false"/>
  </property>
</channel>
""")
        prefs.edit().putString("theme_applied", DEFAULT_THEME_STAMP).apply()
        // Roomier menus for touch (sizes are logical pixels, doubled by the window scale)
        File(root, "root/.config/gtk-3.0").mkdirs()
        File(root, "root/.config/gtk-3.0/gtk.css").writeText("""menu menuitem { min-height: 30px; padding: 4px 16px; }
menu menuitem label { font-size: 112%; }
menubar > menuitem { min-height: 28px; padding: 2px 14px; }
""")
        File(root, "root/.config/gtk-3.0/settings.ini").delete()   // the fixed icon sizes of the first try; window scaling replaces them
        // Sizes of the panel and the desktop icons, and the once-only layout and wallpaper, are set when the session is running
        // (their settings need the session bus). The script is a template in the app's assets.
        val tune = app.assets.open("tune.sh").bufferedReader().use { it.readText() }
            .replace("@PANEL@", panel.toString()).replace("@DOCK@", dock.toString()).replace("@ICON@", desktopIcon.toString())
        File(root, "root/linuxpad-xfce-tune.sh").writeText(tune)
        // the same script once more inside the running desktop: it only finishes what the first run could not verify
        val autostart = File(root, "root/.config/autostart").apply { mkdirs() }
        File(autostart, "linuxpad-tune.desktop").writeText("""[Desktop Entry]
Type=Application
Name=LinuxPad tuning
Exec=sh -c "sh /root/linuxpad-xfce-tune.sh live > /root/linuxpad-tune-live.log 2>&1"
X-GNOME-Autostart-enabled=true
""")
        // autostart programs run after the panel and the desktop: then the start screen can go
        File(autostart, "linuxpad-ready.desktop").writeText("""[Desktop Entry]
Type=Application
Name=LinuxPad ready
Exec=sh -c "sleep 2; mkdir -p /tmp; touch /tmp/linuxpad-ready"
X-GNOME-Autostart-enabled=true
""")
    }

    /** Sets the values of existing properties in an xfconf file; false when one is missing (the caller then writes the whole file). */
    private fun patchProps(file: File, values: Map<String, String>): Boolean {
        var text = file.readText()
        for ((name, value) in values) {
            val re = Regex("""(<property name="${Regex.escape(name)}" type="\w+" value=")[^"]*(")""")
            if (!re.containsMatchIn(text)) return false
            text = re.replace(text) { it.groupValues[1] + value + it.groupValues[2] }
        }
        file.writeText(text)
        return true
    }

    /** Copies what the app carries into the Linux system: the Selawik fonts and the default wallpaper. */
    private fun installAssets(app: Context, root: File) {
        val fonts = File(root, "usr/local/share/fonts/selawik").apply { mkdirs() }
        app.assets.list("fonts")?.filter { it.endsWith(".ttf", ignoreCase = true) || it.contains("LICENSE") }?.forEach { name ->
            app.assets.open("fonts/$name").use { input -> File(fonts, name).outputStream().use { input.copyTo(it) } }
        }
        // the WhiteSur themes (MIT, https://github.com/vinceliuice/WhiteSur-gtk-theme), prebuilt: Light and Dark with their window frames
        val themes = File(root, "usr/share/themes").apply { mkdirs() }
        for (name in listOf("WhiteSur-Light", "WhiteSur-Dark")) {
            if (File(themes, "$name/index.theme").isFile && File(themes, "$name-xhdpi/xfwm4/themerc").isFile) continue
            runCatching {
                val tmp = TarExtractor.assetToFile(app, "themes/$name") ?: return@runCatching
                TarExtractor.extractTarGz(tmp, themes) { }
                tmp.delete()
            }
        }
        val bg = File(root, "usr/share/backgrounds").apply { mkdirs() }
        runCatching { app.assets.open("wallpaper.jpg").use { input -> File(bg, "linuxpad.jpg").outputStream().use { input.copyTo(it) } } }
    }
}

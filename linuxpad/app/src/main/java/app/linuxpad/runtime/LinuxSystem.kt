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
    var running by mutableStateOf(false); private set

    fun rootDir(ctx: Context) = File(ctx.filesDir, "rootfs/debian")
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
    const val LOOK_PACKAGES = "fonts-ubuntu papirus-icon-theme yaru-theme-gtk"

    fun hasXfce(ctx: Context) = File(rootDir(ctx), "usr/bin/startxfce4").exists()
    fun graphicsOk(ctx: Context) = File(rootDir(ctx), "usr/share/X11/xkb").isDirectory && File(rootDir(ctx), "usr/lib/aarch64-linux-gnu/libpulse.so.0").exists()
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
        output = ""
        KeepAlive.acquire(app, "session", "Linux desktop is running")
        X11Server.whenFailed { error = "The X server did not start: ${X11Server.detail}"; stopSession(app) }
        X11Server.start(app, File(root(app), "usr/share/X11/xkb"))
        AudioServer.start(app)
        X11Server.whenReady { launchDesktop(app, plan, id) }
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
                        "  <alias><family>sans-serif</family><prefer><family>Selawik</family><family>Ubuntu</family><family>Vazirmatn</family></prefer></alias>\n" +
                        "  <alias><family>monospace</family><prefer><family>Ubuntu Mono</family><family>Liberation Mono</family><family>Vazirmatn</family></prefer></alias>\n" +
                        "</fontconfig>\n")
                installAssets(app, root)
                writeXfceConfig(root, plan)
                // xrdb normally runs the C preprocessor, which a minimal Debian does not have: -nocpp avoids it.
                // The root window gets a cursor of its own (otherwise it keeps the tiny default X cursor).
                val script = "export DISPLAY=:0; fc-cache -f /usr/local/share/fonts >/dev/null 2>&1; " +
                    "xrdb -nocpp -merge /root/.Xresources || echo 'xrdb failed'; " +
                    "xsetroot -solid '#27364d' -cursor_name left_ptr || echo 'xsetroot failed'; " +
                    "mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root; export XDG_RUNTIME_DIR=/tmp/runtime-root; " +
                    "[ -s /etc/machine-id ] || dbus-uuidgen --ensure=/etc/machine-id; " +
                    "export XDG_SESSION_TYPE=x11 GDK_BACKEND=x11 NO_AT_BRIDGE=1 LIBGL_ALWAYS_SOFTWARE=1 XCURSOR_THEME=LinuxPad; " +
                    "export QT_AUTO_SCREEN_SCALE_FACTOR=0 QT_SCALE_FACTOR=${plan.qtScaleFactor} QT_FONT_DPI=96; " +
                    "exec startxfce4"
                val p = Proot.spawn(app, root, listOf("/bin/bash", "-lc", script),
                    binds = listOf("${X11Server.runtimeDir(app).absolutePath}/.X11-unix" to "/tmp/.X11-unix", AudioServer.bind(app)) + listOfNotNull(SharedFolder.prepare(root)),
                    env = mapOf("DISPLAY" to ":0", "XCURSOR_SIZE" to plan.cursorSize.toString()) + AudioServer.guestEnv())
                desktop = p
                session = "running"
                p.inputStream.bufferedReader().forEachLine { line -> output = (output + line + "\n").takeLast(20_000) }
                output += "[desktop session ended: exit ${p.waitFor()}]\n"
            } catch (e: Throwable) {
                output += "${e.javaClass.simpleName}: ${e.message}\n"
            } finally {
                if (id == sessionId) stopSession(app)       // the desktop ended (for example Log Out): shut the rest down too
            }
        }
    }

    // ---- set up: everything in one go, with one progress bar -----------------------------------------------------------

    data class SetupState(val running: Boolean = false, val fraction: Float = 0f, val label: String = "", val error: String? = null)

    var setupState by mutableStateOf(SetupState()); private set

    /** Installs what is missing: Debian, graphics libraries, XFCE, then the nicer look. Parts already present are skipped. */
    fun setup(ctx: Context) {
        if (setupState.running) return
        val app = ctx.applicationContext
        setupState = SetupState(running = true, label = "Starting")
        error = null
        KeepAlive.acquire(app, "setup", "Setting up the Linux desktop")
        scope.launch {
            try {
                fun report(base: Float, weight: Float, f: Float, label: String) { setupState = SetupState(true, base + weight * f.coerceIn(0f, 1f), label) }
                var base = 0f
                // 1. the Linux system
                if (!File(root(app), "etc/os-release").exists() && !File(root(app), "usr/lib/os-release").exists()) {
                    Registry.install(IMAGE, TAG, root(app), File(app.cacheDir, "dl")) { p ->
                        val f = if (p.total > 0) p.done.toFloat() / p.total else 0f
                        report(base, 0.08f, if (p.phase.startsWith("Downloading")) f * 0.8f else 0.8f, "Debian: ${p.phase.lowercase()}")
                    }
                    refresh(app)
                }
                base = 0.08f
                // 2. graphics and sound libraries
                if (!graphicsOk(app)) {
                    val code = apt(app, GRAPHICS_PACKAGES) { f, label -> report(base, 0.17f, f, label) }
                    if (code != 0) throw IllegalStateException("Installing the graphics libraries failed (exit $code). See Details.")
                }
                base += 0.17f
                // 3. XFCE
                if (!hasXfce(app)) {
                    val code = apt(app, XFCE_PACKAGES) { f, label -> report(base, 0.55f, f, label) }
                    if (code != 0) throw IllegalStateException("Installing XFCE failed (exit $code). See Details.")
                }
                base += 0.55f
                // 4. the nicer look: each package on its own, a missing one is not an error
                if (!lookOk(app)) {
                    val pkgs = LOOK_PACKAGES.split(' ')
                    pkgs.forEachIndexed { i, pkg ->
                        val w = 0.20f / pkgs.size
                        val code = apt(app, pkg, update = false) { f, label -> report(base + w * i, w, f, label) }
                        if (code != 0) output += "[look] $pkg could not be installed (exit $code)\n"
                    }
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

    /** Runs apt in the Linux system; apt's machine-readable status becomes progress (0 to 1) and a short label, other output goes to the log. */
    private fun apt(app: Context, packages: String, update: Boolean = true, onProgress: (Float, String) -> Unit): Int {
        onProgress(0f, if (update) "Updating package lists" else "Preparing")
        val cmd = (if (update) "apt-get update -qq; " else "") +
            "apt-get -o APT::Status-Fd=1 -o Dpkg::Use-Pty=0 -y --no-install-recommends install $packages"
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
    private fun writeXfceConfig(root: File, plan: ScalePlan) {
        val xml = File(root, "root/.config/xfce4/xfconf/xfce-perchannel-xml").apply { mkdirs() }
        // XFCE draws everything at 2x (window scaling factor 2: panel, menus, icons, buttons, spacing, title bars).
        // Text keeps the size chosen on the device: Xft DPI is halved, because the 2x scale doubles it again.
        // Sizes set below are in logical pixels, so they are the real pixel size divided by 2.
        val scale = 2
        fun logical(realPx: Int) = (realPx + scale / 2) / scale
        val desktopIcon = logical((48 * plan.factor).roundToInt())
        val dock = logical(((48 * plan.factor) * 1.25f).roundToInt())   // the bottom dock: a quarter larger than the desktop icons
        val panel = logical(plan.panelSize)
        val themeName = if (File(root, "usr/share/themes/Yaru/gtk-3.0").isDirectory) "Yaru" else "Adwaita"
        val iconName = if (File(root, "usr/share/icons/Papirus").isDirectory) "Papirus" else "Adwaita"
        val uiFont = when {
            File(root, "usr/local/share/fonts/selawik").listFiles()?.isNotEmpty() == true -> "Selawik 11"
            File(root, "usr/share/fonts/truetype/ubuntu").isDirectory -> "Ubuntu 11"
            else -> "Sans 10"
        }
        File(xml, "xsettings.xml").writeText("""<?xml version="1.0" encoding="UTF-8"?>
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
        File(xml, "xfwm4.xml").writeText("""<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="Default"/>
    <property name="use_compositing" type="bool" value="false"/>
  </property>
</channel>
""")
        // Roomier menus for touch (sizes are logical pixels, doubled by the window scale)
        File(root, "root/.config/gtk-3.0").mkdirs()
        File(root, "root/.config/gtk-3.0/gtk.css").writeText("""menu menuitem { min-height: 30px; padding: 4px 16px; }
menu menuitem label { font-size: 112%; }
menubar > menuitem { min-height: 28px; padding: 2px 14px; }
""")
        File(root, "root/.config/gtk-3.0/settings.ini").delete()   // the fixed icon sizes of the first try; window scaling replaces them
        // The panel and the desktop icons are set once the session is running (their settings need the session bus)
        File(root, "root/linuxpad-xfce-tune.sh").writeText("""#!/bin/sh
export DISPLAY=:0
for i in `seq 1 60`; do xfconf-query -c xfce4-panel -l >/dev/null 2>&1 && break; sleep 1; done
sleep 3
xfconf-query -c xfce4-panel -p /panels/panel-1/size -n -t uint -s $panel
xfconf-query -c xfce4-panel -p /panels/panel-1/icon-size -n -t uint -s 0
xfconf-query -c xfce4-panel -p /panels/panel-2/size -n -t uint -s $dock
xfconf-query -c xfce4-panel -p /panels/panel-2/icon-size -n -t uint -s 0
xfconf-query -c xfce4-desktop -p /desktop-icons/icon-size -n -t uint -s $desktopIcon
xfconf-query -c xfce4-desktop -p /desktop-icons/use-custom-font-size -n -t bool -s true
xfconf-query -c xfce4-desktop -p /desktop-icons/font-size -n -t double -s 9
# the default wallpaper is set once; after that the wallpaper is the user's choice
if [ ! -f /root/.config/linuxpad/wallpaper-set ] && [ -f /usr/share/backgrounds/linuxpad.jpg ]; then
  for i in `seq 1 20`; do imgs=`xfconf-query -c xfce4-desktop -l | grep 'last-image$'`; [ -n "${'$'}imgs" ] && break; sleep 1; done
  for p in ${'$'}imgs; do xfconf-query -c xfce4-desktop -p ${'$'}p -s /usr/share/backgrounds/linuxpad.jpg; done
  for p in `xfconf-query -c xfce4-desktop -l | grep 'image-style$'`; do xfconf-query -c xfce4-desktop -p ${'$'}p -s 5; done
  mkdir -p /root/.config/linuxpad && touch /root/.config/linuxpad/wallpaper-set
fi
""")
        val autostart = File(root, "root/.config/autostart").apply { mkdirs() }
        File(autostart, "linuxpad-tune.desktop").writeText("""[Desktop Entry]
Type=Application
Name=LinuxPad tuning
Exec=sh /root/linuxpad-xfce-tune.sh
X-GNOME-Autostart-enabled=true
""")
    }

    /** Copies what the app carries into the Linux system: the Selawik fonts and the default wallpaper. */
    private fun installAssets(app: Context, root: File) {
        val fonts = File(root, "usr/local/share/fonts/selawik").apply { mkdirs() }
        app.assets.list("fonts")?.filter { it.endsWith(".ttf", ignoreCase = true) || it.contains("LICENSE") }?.forEach { name ->
            app.assets.open("fonts/$name").use { input -> File(fonts, name).outputStream().use { input.copyTo(it) } }
        }
        val bg = File(root, "usr/share/backgrounds").apply { mkdirs() }
        runCatching { app.assets.open("wallpaper.jpg").use { input -> File(bg, "linuxpad.jpg").outputStream().use { input.copyTo(it) } } }
    }
}

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

    /** Deletes the whole Linux system: every package and every file in it. A folder without write permission would stop a plain delete, so each one is opened first. */
    fun remove(ctx: Context) {
        val app = ctx.applicationContext
        stopDesktop()
        scope.launch {
            wipe(root(app))
            File(app.filesDir, "runtime").deleteRecursively()
            File(app.cacheDir, "dl").deleteRecursively()
            packages = emptyList()
            output = ""
            refresh(app)
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

    /** The pointer position as the X server sees it (from xdotool in the guest); shown in the desktop overlay. */
    var pointerText by mutableStateOf(""); private set

    /** Packages the graphics test needs: keyboard data for the X server, a terminal, test clients, fonts and a cursor theme. */
    const val GRAPHICS_PACKAGES = "xkb-data x11-xserver-utils xterm x11-apps fonts-dejavu-core fonts-vazirmatn fonts-liberation librsvg2-common shared-mime-info adwaita-icon-theme dmz-cursor-theme xdotool mousepad"

    /** The XFCE desktop (about 150 to 300 MB). dbus-x11 gives the session its message bus. */
    const val XFCE_PACKAGES = "xfce4 xfce4-terminal xfce4-notifyd dbus-x11 xdg-utils"

    /** Whether XFCE is installed in the Linux system. */
    fun hasXfce(ctx: Context) = File(rootDir(ctx), "usr/bin/startxfce4").exists()

    /** Starts a small test desktop (xeyes and xterm) in the Linux system, sized from [plan]. */
    fun startDesktop(ctx: Context, plan: ScalePlan) {
        val app = ctx.applicationContext
        stopDesktop()
        scope.launch {
            try {
                val root = root(app)
                // the cursor theme at exactly the size chosen for this screen (installed themes only ship fixed sizes)
                val cursorResult = runCatching { CursorTheme.ensure(root, plan.cursorSize) }
                val cursorTheme = cursorResult.getOrNull()
                val cursorNote = "cursor theme: " + (cursorTheme?.let { "$it at ${plan.cursorSize} px" } ?: "not built (${cursorResult.exceptionOrNull()?.message ?: "no Adwaita/DMZ theme installed"})")
                File(root, "root/.Xresources").writeText(
                    "Xft.dpi: ${plan.xftDpi}\nXft.antialias: 1\nXft.hinting: 1\nXft.hintstyle: hintslight\n" +
                        "Xcursor.size: ${plan.cursorSize}\n" + (if (cursorTheme != null) "Xcursor.theme: $cursorTheme\n" else "Xcursor.theme: DMZ-White\n"))
                // Persian: a monospace font with Arabic letters (DejaVu Sans Mono) draws each letter in a fixed cell and breaks the
                // joining. Put a Latin-only monospace font first so Persian comes from Vazirmatn.
                File(root, "root/.config/fontconfig").mkdirs()
                File(root, "root/.config/fontconfig/fonts.conf").writeText(
                    "<?xml version=\"1.0\"?>\n<!DOCTYPE fontconfig SYSTEM \"fonts.dtd\">\n<fontconfig>\n" +
                        "  <alias><family>monospace</family><prefer><family>Liberation Mono</family><family>Vazirmatn</family></prefer></alias>\n" +
                        "</fontconfig>\n")
                // a sample document with English, Persian and mathematics, to judge text on this screen
                File(root, "root/sample.txt").writeText(
                    "LinuxPad test text\n\nThe Orlicz space L^Phi(mu) is a Banach algebra when Phi(st) <= Phi(s)Phi(t).\n" +
                        "||fg|| <= ||f|| ||g||      \u222B f d\u03BC  \u2264  \u03A6\n\n" +
                        "\u0641\u0636\u0627\u06CC \u0627\u0648\u0631\u0644\u06CC\u0686 \u06CC\u06A9 \u062C\u0628\u0631 \u0628\u0627\u0646\u0627\u062E \u0627\u0633\u062A.\n" +
                        "\u0633\u0644\u0627\u0645\u060C \u0627\u06CC\u0646 \u06CC\u06A9 \u0645\u062A\u0646 \u0622\u0632\u0645\u0627\u06CC\u0634\u06CC \u0627\u0633\u062A \u06F1\u06F2\u06F3\n")
                val xfce = hasXfce(app)
                if (xfce) writeXfceConfig(root, plan)
                // xrdb normally runs the C preprocessor, which a minimal Debian does not have: -nocpp avoids it.
                // The root window gets a cursor of its own (otherwise it keeps the tiny default X cursor).
                val common = "export DISPLAY=:0; " +
                    "xrdb -nocpp -merge /root/.Xresources || echo 'xrdb failed'; " +
                    "echo \"Xft.dpi in the server: \$(xrdb -query | grep -i '^Xft.dpi')\"; " +
                    "xsetroot -solid '#27364d' -cursor_name left_ptr || echo 'xsetroot failed'; " +
                    "( while true; do echo \"PTR \$(xdotool getmouselocation 2>&1 | head -1)\"; sleep 0.25; done ) & "
                val script = if (xfce) {
                    common +
                        "mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root; export XDG_RUNTIME_DIR=/tmp/runtime-root; " +
                        "[ -s /etc/machine-id ] || dbus-uuidgen --ensure=/etc/machine-id; " +
                        "export XDG_SESSION_TYPE=x11 GDK_BACKEND=x11 NO_AT_BRIDGE=1 LIBGL_ALWAYS_SOFTWARE=1 XCURSOR_THEME=LinuxPad; " +
                        "exec startxfce4"
                } else {
                    common +
                        "GSETTINGS_BACKEND=memory NO_AT_BRIDGE=1 mousepad /root/sample.txt & " +
                        "exec xterm -geometry 80x22+60+420 -fa 'DejaVu Sans Mono' -fs 11 -bg black -fg white"
                }
                val p = Proot.spawn(app, root, listOf("/bin/bash", "-lc", script),
                    binds = listOf("${X11Server.runtimeDir(app).absolutePath}/.X11-unix" to "/tmp/.X11-unix"),
                    env = mapOf("DISPLAY" to ":0", "XCURSOR_SIZE" to plan.cursorSize.toString()))
                desktop = p
                output = "desktop session started\n$cursorNote\n"
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

    /**
     * XFCE's panel, window title bars and desktop icons are fixed pixel sizes made for 96 dpi screens, so on this screen they
     * would be tiny. Their sizes are written here from the scale plan, before the first start.
     */
    private fun writeXfceConfig(root: File, plan: ScalePlan) {
        val xml = File(root, "root/.config/xfce4/xfconf/xfce-perchannel-xml").apply { mkdirs() }
        val desktopIcon = (48 * plan.factor).roundToInt()
        File(xml, "xsettings.xml").writeText("""<?xml version="1.0" encoding="UTF-8"?>
<channel name="xsettings" version="1.0">
  <property name="Xft" type="empty">
    <property name="DPI" type="int" value="${plan.xftDpi}"/>
    <property name="Antialias" type="int" value="1"/>
    <property name="Hinting" type="int" value="1"/>
    <property name="HintStyle" type="string" value="hintslight"/>
  </property>
  <property name="Gtk" type="empty">
    <property name="CursorThemeName" type="string" value="${CursorTheme.NAME}"/>
    <property name="CursorThemeSize" type="int" value="${plan.cursorSize}"/>
  </property>
  <property name="Net" type="empty">
    <property name="ThemeName" type="string" value="Adwaita"/>
    <property name="IconThemeName" type="string" value="Adwaita"/>
  </property>
</channel>
""")
        // Default-xhdpi is the window theme drawn at double size
        File(xml, "xfwm4.xml").writeText("""<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="Default-xhdpi"/>
    <property name="use_compositing" type="bool" value="false"/>
  </property>
</channel>
""")
        // GTK icons in menus, buttons and toolbars are fixed pixel sizes (16, 24, 32, 48) that Xft.dpi does not scale: set them from the plan
        fun px(base: Int) = (base * plan.factor).roundToInt()
        File(root, "root/.config/gtk-3.0").apply { mkdirs() }
        File(root, "root/.config/gtk-3.0/settings.ini").writeText("""[Settings]
gtk-icon-sizes=gtk-menu=${px(16)},${px(16)}:gtk-small-toolbar=${px(16)},${px(16)}:gtk-large-toolbar=${px(24)},${px(24)}:gtk-button=${px(16)},${px(16)}:gtk-dnd=${px(32)},${px(32)}:gtk-dialog=${px(48)},${px(48)}
""")
        // The panel and the desktop icons are set once the session is running (their settings need the session bus)
        File(root, "root/linuxpad-xfce-tune.sh").writeText("""#!/bin/sh
export DISPLAY=:0
for i in `seq 1 60`; do xfconf-query -c xfce4-panel -l >/dev/null 2>&1 && break; sleep 1; done
sleep 3
xfconf-query -c xfce4-panel -p /panels/panel-1/size -n -t uint -s ${plan.panelSize}
xfconf-query -c xfce4-panel -p /panels/panel-1/icon-size -n -t uint -s 0
xfconf-query -c xfce4-panel -p /panels/panel-2/size -n -t uint -s $desktopIcon
xfconf-query -c xfce4-panel -p /panels/panel-2/icon-size -n -t uint -s 0
xfconf-query -c xfce4-desktop -p /desktop-icons/icon-size -n -t uint -s $desktopIcon
""")
        val autostart = File(root, "root/.config/autostart").apply { mkdirs() }
        File(autostart, "linuxpad-tune.desktop").writeText("""[Desktop Entry]
Type=Application
Name=LinuxPad tuning
Exec=sh /root/linuxpad-xfce-tune.sh
X-GNOME-Autostart-enabled=true
""")
    }
}

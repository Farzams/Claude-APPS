package app.linuxpad

import android.app.Activity
import android.os.Bundle
import android.view.WindowManager
import android.widget.TextView
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import app.linuxpad.display.DisplayScale
import app.linuxpad.display.Screens
import app.linuxpad.runtime.LinuxSystem
import app.linuxpad.x11.X11DisplayView
import app.linuxpad.x11.X11Server
import java.io.File

/** Full-screen Linux desktop. Closing it stops the session. */
class DesktopActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        window.attributes = window.attributes.also { it.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES }

        val xkb = File(LinuxSystem.rootDir(this), "usr/share/X11/xkb")
        if (!xkb.isDirectory) {
            setContentView(TextView(this).apply { text = "Keyboard data is missing. Go back, run \"Install graphics packages\" first."; textSize = 22f; setPadding(48, 96, 48, 48) })
            return
        }
        val view = X11DisplayView(this)
        setContentView(view)
        WindowInsetsControllerCompat(window, view).apply {
            systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            hide(WindowInsetsCompat.Type.systemBars())
        }
        val plan = DisplayScale.plan(Screens.read(this))
        X11Server.start(this, xkb) {
            X11Server.requestRenderer { fd ->
                view.connectRenderer(fd.detachFd())
                LinuxSystem.startDesktop(this, plan)
            }
        }
    }

    override fun onDestroy() {
        LinuxSystem.stopDesktop()
        X11Server.stop(this)
        super.onDestroy()
    }
}

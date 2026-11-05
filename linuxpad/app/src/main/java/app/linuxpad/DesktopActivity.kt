package app.linuxpad

import android.app.Activity
import android.os.Bundle
import android.view.WindowManager
import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.FrameLayout
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
        // Diagnostics for the first versions: what the finger did and what the X server saw
        val info = TextView(this).apply {
            setTextColor(Color.WHITE); setBackgroundColor(0xAA000000.toInt()); textSize = 13f
            setPadding(16, 8, 16, 8); typeface = android.graphics.Typeface.MONOSPACE
        }
        // a keyboard button for touch use (three fingers tapping does the same)
        val keyboard = TextView(this).apply {
            text = "\u2328"; textSize = 26f; setTextColor(Color.WHITE); gravity = Gravity.CENTER
            setBackgroundColor(0x99000000.toInt()); setOnClickListener { view.toggleKeyboard() }
        }
        val buttonPx = (56 * resources.displayMetrics.density).toInt()
        setContentView(FrameLayout(this).apply {
            addView(view)
            addView(info, FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.TOP or Gravity.END))
            addView(keyboard, FrameLayout.LayoutParams(buttonPx, buttonPx, Gravity.BOTTOM or Gravity.END).apply { setMargins(0, 0, 24, 24) })
        })
        val ui = Handler(Looper.getMainLooper())
        ui.post(object : Runnable {
            override fun run() {
                info.text = "finger  x=${view.lastX.toInt()} y=${view.lastY.toInt()}  moves=${view.moves} down=${view.downs} up=${view.ups}\n" +
                    "X server pointer: ${LinuxSystem.pointerText.ifBlank { "(no data yet)" }}\n" +
                    "renderer connected: ${view.isConnected}  x11: ${X11Server.state}"
                ui.postDelayed(this, 200)
            }
        })
        WindowInsetsControllerCompat(window, view).apply {
            systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            hide(WindowInsetsCompat.Type.systemBars())
        }
        val comfort = getSharedPreferences("linuxpad", MODE_PRIVATE).getFloat("comfort", DisplayScale.DEFAULT_COMFORT)   // the size chosen on the calibration page
        val plan = DisplayScale.plan(Screens.read(this), comfort)
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

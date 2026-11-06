package app.linuxpad

import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.WindowManager
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

/**
 * The window onto the Linux desktop. The desktop itself keeps running when this screen is left (see LinuxSystem and KeepAlive);
 * opening the screen again reconnects to it. Logging out inside Linux, or "Stop desktop", ends the session and closes this screen.
 */
class DesktopActivity : Activity() {
    private val ui = Handler(Looper.getMainLooper())
    private var sawSession = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE   // the desktop is a landscape screen
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        window.attributes = window.attributes.also { it.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES }

        if (!LinuxSystem.hasXfce(this)) {
            setContentView(TextView(this).apply { text = "The desktop is not set up yet. Go back and press Set up."; textSize = 22f; setPadding(48, 96, 48, 48) })
            return
        }
        val view = X11DisplayView(this)
        val ring = TouchRingView(this)
        view.setPointerListener(object : X11DisplayView.PointerListener {
            override fun onTouchPointer(x: Float, y: Float, touching: Boolean, pressed: Boolean) = ring.update(x, y, touching, pressed)
            override fun onMouseUsed() = ring.clear()
        })
        // a keyboard button for touch use (three fingers tapping does the same)
        val keyboard = TextView(this).apply {
            text = "\u2328"; textSize = 26f; setTextColor(Color.WHITE); gravity = Gravity.CENTER
            setBackgroundColor(0x99000000.toInt()); setOnClickListener { view.toggleKeyboard() }
        }
        val buttonPx = (56 * resources.displayMetrics.density).toInt()
        val start = StartScreenView(this)
        val openedAt = System.currentTimeMillis()
        setContentView(FrameLayout(this).apply {
            addView(view)
            addView(ring, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT))
            addView(keyboard, FrameLayout.LayoutParams(buttonPx, buttonPx, Gravity.BOTTOM or Gravity.END).apply { setMargins(0, 0, 24, 24) })
            addView(start, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT))
        })
        WindowInsetsControllerCompat(window, view).apply {
            systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            hide(WindowInsetsCompat.Type.systemBars())
        }
        // starts the session, or reconnects when it is already running
        LinuxSystem.startSession(this, DisplayScale.plan(Screens.read(this)))
        X11Server.whenReady { X11Server.requestRenderer { fd -> view.connectRenderer(fd.detachFd()) } }
        ui.post(object : Runnable {
            override fun run() {
                if (LinuxSystem.session != "stopped") sawSession = true
                else if (sawSession) { finish(); return }
                // the start screen: what is happening now, gone once the desktop has drawn itself (or after 45 s at most)
                val ready = LinuxSystem.session == "running" && LinuxSystem.desktopReady(this@DesktopActivity)
                if (ready || System.currentTimeMillis() - openedAt > 45_000) start.dismiss()
                else start.setStatus(when {
                    X11Server.state != app.linuxpad.x11.X11Protocol.STATE_READY -> "Starting the display"
                    LinuxSystem.session == "starting" -> "Preparing the desktop"
                    else -> "Starting the desktop"
                })
                ui.postDelayed(this, 300)
            }
        })
    }

    override fun onDestroy() {
        ui.removeCallbacksAndMessages(null)
        super.onDestroy()        // the session keeps running; it is stopped by Stop desktop, by logging out, or from the notification
    }
}

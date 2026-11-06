package app.linuxpad

import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.content.Context
import android.graphics.Color
import android.graphics.Outline
import android.graphics.Typeface
import android.view.Gravity
import android.view.View
import android.view.ViewOutlineProvider
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView

/** Covers the desktop while it starts: the app icon breathing on the theme colour and a line saying what is happening. */
class StartScreenView(context: Context) : FrameLayout(context) {
    private val status: TextView
    private val pulse: ObjectAnimator
    private var gone = false

    init {
        setBackgroundColor(Color.parseColor("#17161A"))
        isClickable = true                                    // touches do not reach the desktop underneath while it starts
        val d = resources.displayMetrics.density
        val icon = ImageView(context).apply {
            setBackgroundResource(R.drawable.ic_launcher_background)
            setImageResource(R.drawable.ic_launcher_foreground)
            scaleType = ImageView.ScaleType.FIT_CENTER
            outlineProvider = object : ViewOutlineProvider() {
                override fun getOutline(v: View, o: Outline) { o.setRoundRect(0, 0, v.width, v.height, v.width * 0.23f) }
            }
            clipToOutline = true
        }
        val name = TextView(context).apply {
            text = "LinuxPad"; setTextColor(Color.parseColor("#F3EFEA")); textSize = 26f; typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER; setPadding(0, (18 * d).toInt(), 0, 0)
        }
        status = TextView(context).apply {
            text = "Starting"; setTextColor(Color.parseColor("#A9A39C")); textSize = 16f; gravity = Gravity.CENTER
            setPadding(0, (8 * d).toInt(), 0, 0)
        }
        addView(LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_HORIZONTAL
            addView(icon, LinearLayout.LayoutParams((132 * d).toInt(), (132 * d).toInt()))
            addView(name); addView(status)
        }, LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT, Gravity.CENTER))
        pulse = ObjectAnimator.ofFloat(icon, View.ALPHA, 1f, 0.55f).apply {
            duration = 900; repeatMode = ValueAnimator.REVERSE; repeatCount = ValueAnimator.INFINITE; start()
        }
    }

    fun setStatus(text: String) { if (status.text != text) status.text = text }

    /** Fades out and leaves the desktop visible. */
    fun dismiss() {
        if (gone) return
        gone = true
        animate().alpha(0f).setDuration(450).withEndAction { pulse.cancel(); visibility = GONE }.start()
    }
}

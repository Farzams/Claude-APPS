package app.linuxpad

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.view.View

/** The pointer for touch use: a soft ring with a little fill around the finger. It stays dim where the finger left it. */
class TouchRingView(context: Context) : View(context) {
    private val density = resources.displayMetrics.density
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
    private val ring = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = 3f * density }
    private val shadow = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = 6f * density; color = Color.argb(70, 0, 0, 0) }
    private var px = -1f
    private var py = -1f
    private var touching = false
    private var pressed = false

    init { isClickable = false; isFocusable = false }

    fun update(x: Float, y: Float, touching: Boolean, pressed: Boolean) {
        px = x; py = y; this.touching = touching; this.pressed = pressed
        invalidate()
    }

    fun clear() { px = -1f; invalidate() }

    override fun onDraw(c: Canvas) {
        if (px < 0) return
        val r = (if (pressed) 20f else 24f) * density
        val a = if (touching) 255 else 130
        fill.color = Color.argb(if (pressed) 120 else if (touching) 55 else 30, 255, 255, 255)
        ring.color = Color.argb(a, 255, 255, 255)
        shadow.alpha = if (touching) 70 else 40
        c.drawCircle(px, py, r, fill)
        c.drawCircle(px, py, r, shadow)
        c.drawCircle(px, py, r, ring)
    }

    override fun onTouchEvent(event: android.view.MotionEvent) = false   // touches go to the desktop below
}

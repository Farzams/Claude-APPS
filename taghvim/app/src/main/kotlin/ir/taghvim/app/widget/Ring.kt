package ir.taghvim.app.widget

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.util.LruCache
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.unit.dp
import androidx.glance.GlanceModifier
import androidx.glance.Image
import androidx.glance.ImageProvider
import androidx.glance.LocalContext
import androidx.glance.layout.size

/** The progress ring of the prayer widget, drawn live: a full track and an arc for how much of the wait has passed. */
object RingArt {
    private const val CRISP = 1.5f
    private val cache = LruCache<String, Bitmap>(40)

    fun render(context: Context, fraction: Float, track: Int, color: Int, sizeDp: Float, strokeDp: Float): Bitmap {
        val percent = (fraction.coerceIn(0f, 1f) * 100).toInt() // one picture per percent is plenty
        val key = "$percent|$track|$color|$sizeDp|$strokeDp"
        cache.get(key)?.let { return it }
        val scale = context.resources.displayMetrics.density * CRISP
        val px = (sizeDp * scale).toInt().coerceAtLeast(8)
        val stroke = strokeDp * scale
        val bitmap = Bitmap.createBitmap(px, px, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            style = Paint.Style.STROKE
            strokeWidth = stroke
            strokeCap = Paint.Cap.ROUND
        }
        val box = RectF(stroke / 2, stroke / 2, px - stroke / 2, px - stroke / 2)
        paint.color = track
        canvas.drawArc(box, 0f, 360f, false, paint)
        if (percent > 0) {
            paint.color = color
            canvas.drawArc(box, -90f, 360f * percent / 100f, false, paint)
        }
        cache.put(key, bitmap)
        return bitmap
    }
}

@Composable
fun Ring(fraction: Float, track: Color, color: Color, sizeDp: Float = 84f, strokeDp: Float = 7f, modifier: GlanceModifier = GlanceModifier) {
    val bitmap = RingArt.render(LocalContext.current, fraction, track.toArgb(), color.toArgb(), sizeDp, strokeDp)
    Image(ImageProvider(bitmap), contentDescription = null, modifier = modifier.size(sizeDp.dp))
}

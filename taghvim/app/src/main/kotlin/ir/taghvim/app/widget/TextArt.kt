package ir.taghvim.app.widget

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Typeface
import android.text.Layout
import android.text.StaticLayout
import android.text.TextDirectionHeuristics
import android.text.TextPaint
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
import kotlin.math.ceil

/**
 * A home-screen widget can only use the system font, so every piece of text is drawn here with the
 * bundled Vazirmatn font into a small picture and shown as an image (the same look as the design).
 */
object TextArt {
    class Art(val bitmap: Bitmap, val widthDp: Float, val heightDp: Float)

    private const val CRISP = 1.5f // draw with 1.5x the pixels, the system scales it down: sharper text
    private val faces = HashMap<Int, Typeface>()
    private val cache = LruCache<String, Art>(300)

    private fun face(context: Context, weight: Int): Typeface = faces.getOrPut(weight) {
        Typeface.createFromAsset(
            context.assets,
            when (weight) {
                700 -> "fonts/Vazirmatn-Bold.ttf"
                500 -> "fonts/Vazirmatn-Medium.ttf"
                else -> "fonts/Vazirmatn-Regular.ttf"
            },
        )
    }

    /** @param maxWidthDp when the text is wider, it is made smaller (down to 8sp) until it fits */
    fun render(context: Context, text: String, sp: Float, color: Int, weight: Int = 400, maxWidthDp: Float? = null): Art {
        val key = "$text|$sp|$color|$weight|$maxWidthDp"
        cache.get(key)?.let { return it }
        val density = context.resources.displayMetrics.density
        var size = sp
        while (true) {
            val paint = TextPaint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
                typeface = face(context, weight)
                textSize = size * density * CRISP
                this.color = color
            }
            val width = ceil(Layout.getDesiredWidth(text, paint)).toInt().coerceAtLeast(1) + 2
            val widthDp = width / (density * CRISP)
            if (maxWidthDp != null && widthDp > maxWidthDp && size > 8f) { size -= 0.5f; continue }
            val layout = StaticLayout.Builder.obtain(text, 0, text.length, paint, width)
                .setTextDirection(TextDirectionHeuristics.RTL)
                .setAlignment(Layout.Alignment.ALIGN_NORMAL)
                .setIncludePad(false)
                .build()
            val bitmap = Bitmap.createBitmap(width, layout.height.coerceAtLeast(1), Bitmap.Config.ARGB_8888)
            layout.draw(Canvas(bitmap))
            val art = Art(bitmap, widthDp, layout.height / (density * CRISP))
            cache.put(key, art)
            return art
        }
    }
}

/** Text in the design's font. [weight] is 400, 500 or 700. */
@Composable
fun Txt(text: String, sp: Float, color: Color, weight: Int = 400, maxWidthDp: Float? = null, modifier: GlanceModifier = GlanceModifier) {
    val art = TextArt.render(LocalContext.current, text, sp, color.toArgb(), weight, maxWidthDp)
    Image(
        provider = ImageProvider(art.bitmap),
        contentDescription = text,
        modifier = modifier.size(art.widthDp.dp, art.heightDp.dp),
    )
}

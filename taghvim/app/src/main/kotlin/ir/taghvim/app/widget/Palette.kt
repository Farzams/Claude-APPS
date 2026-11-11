package ir.taghvim.app.widget

import android.content.Context
import android.content.res.Configuration
import android.view.View
import androidx.compose.ui.graphics.Color
import ir.taghvim.app.data.AppSettings

/** Colours of one widget look, from the design: deep navy (dark) or white-blue (light), with a chosen accent for holidays. */
data class Palette(
    val card: Color,
    val ink: Color,
    val mute: Color,
    val chip: Color,
    val todayBg: Color,
    val todayFg: Color,
    val accent: Color,
)

object Palettes {
    private val accents = mapOf(
        "gold" to (Color(0xFFF5C518) to Color(0xFFB8860B)),
        "coral" to (Color(0xFFFF8A70) to Color(0xFFC2412B)),
        "teal" to (Color(0xFF4FD1C5) to Color(0xFF0F766E)),
        "violet" to (Color(0xFFB79CFF) to Color(0xFF6D4AE0)),
    )
    val accentNames = mapOf("gold" to "طلایی", "coral" to "مرجانی", "teal" to "فیروزه‌ای", "violet" to "بنفش")
    val accentSwatches: Map<String, Color> get() = accents.mapValues { it.value.first }

    fun isDark(context: Context, s: AppSettings): Boolean = when (s.theme) {
        "light" -> false
        "system" -> (context.resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES
        else -> true
    }

    fun of(context: Context, s: AppSettings): Palette {
        val dark = isDark(context, s)
        val acc = accents[s.accent] ?: accents.getValue("gold")
        return if (dark) {
            Palette(Color(0xFF0B1730), Color.White, Color(0xFF9FB0CF), Color(0xFF1B2C52), Color.White, Color(0xFF0B1730), acc.first)
        } else {
            Palette(Color(0xFFF8FAFD), Color(0xFF0B1730), Color(0xFF5D6B88), Color(0xFFE1E8F4), Color(0xFF0B1730), Color.White, acc.second)
        }
    }
}

/** True when the screen reads right to left. Persian layouts are built right to left even on a phone set to English. */
fun Context.isRtl() = resources.configuration.layoutDirection == View.LAYOUT_DIRECTION_RTL

/** Order the items of a row so that the first item always ends up on the right, as in a Persian calendar. */
fun <T> List<T>.rightToLeft(rtlScreen: Boolean): List<T> = if (rtlScreen) this else this.reversed()

/** Drawable by name (ic_*, pr_*, bg_*), or 0 when the artwork does not exist. */
fun Context.drawableId(name: String): Int = resources.getIdentifier(name, "drawable", packageName)

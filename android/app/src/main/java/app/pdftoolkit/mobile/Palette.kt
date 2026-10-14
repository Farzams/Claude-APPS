package app.pdftoolkit.mobile

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.ColorScheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

data class Palette(
    val key: String, val name: String, val dark: Boolean,
    val bg: Color, val card: Color, val field: Color, val hover: Color,
    val text: Color, val muted: Color, val accent: Color, val line: Color,
)

private fun c(hex: Long) = Color(0xFF000000 or hex)

val PALETTES = listOf(
    Palette("qp_light", "Quiet Light", false, c(0xF6F7F9), c(0xFFFFFF), c(0xFFFFFF), c(0xEEF0F4), c(0x101828), c(0x667085), c(0x4F46E5), c(0xE4E7EC)),
    Palette("qp_dark", "Quiet Dark", true, c(0x0D0F13), c(0x14171C), c(0x171A20), c(0x1C2027), c(0xE8EAEE), c(0x8B93A1), c(0x818CF8), c(0x232830)),
    Palette("paper", "Paper", false, c(0xF3EEE4), c(0xFBF8F2), c(0xFFFDF8), c(0xE9E2D2), c(0x2B2620), c(0x7A6F60), c(0xB4532A), c(0xDDD4C1)),
    Palette("paper_dark", "Paper Night", true, c(0x1C1814), c(0x26211B), c(0x2B251E), c(0x322B23), c(0xEADFCB), c(0xA39881), c(0xE08A5C), c(0x3A3228)),
)
val ACCENTS = listOf("#4F46E5", "#0F766E", "#BE185D", "#EA580C", "#16A34A", "#E11D48", "#475569", "#CA8A04", "#2563EB")

/** (design style) -> (light theme, dark theme) */
val STYLES = mapOf("quiet" to ("qp_light" to "qp_dark"), "paper" to ("paper" to "paper_dark"))

fun paletteOf(key: String): Palette = PALETTES.firstOrNull { it.key == key } ?: PALETTES[0]
fun styleOf(key: String): String = STYLES.entries.firstOrNull { key == it.value.first || key == it.value.second }?.key ?: "quiet"
fun parseColor(hex: String): Color? = runCatching { Color(android.graphics.Color.parseColor(hex)) }.getOrNull()

private val Vazir = FontFamily(Font(R.font.vazirmatn_regular, FontWeight.Normal), Font(R.font.vazirmatn_bold, FontWeight.Bold))

private fun typography(fa: Boolean): Typography {
    val plain = Typography()
    val base = plain.copy(
        headlineMedium = plain.headlineMedium.copy(fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.4).sp),
        titleLarge = plain.titleLarge.copy(fontWeight = FontWeight.Bold),
        titleMedium = plain.titleMedium.copy(fontWeight = FontWeight.SemiBold),
    )
    if (!fa) return base
    fun f(s: TextStyle) = s.copy(fontFamily = Vazir)
    return base.copy(
        displayLarge = f(base.displayLarge), displayMedium = f(base.displayMedium), displaySmall = f(base.displaySmall),
        headlineLarge = f(base.headlineLarge), headlineMedium = f(base.headlineMedium), headlineSmall = f(base.headlineSmall),
        titleLarge = f(base.titleLarge), titleMedium = f(base.titleMedium), titleSmall = f(base.titleSmall),
        bodyLarge = f(base.bodyLarge), bodyMedium = f(base.bodyMedium), bodySmall = f(base.bodySmall),
        labelLarge = f(base.labelLarge), labelMedium = f(base.labelMedium), labelSmall = f(base.labelSmall),
    )
}

@Composable
fun AppTheme(pal: Palette, accentHex: String, fa: Boolean, content: @Composable () -> Unit) {
    val appAccent = parseColor(LocalContext.current.getString(R.string.app_accent))
    val accent = parseColor(accentHex) ?: appAccent ?: pal.accent
    val onAccent = if (accent.luminance() > 0.40f) Color(0xFF14110A) else Color.White
    val base: ColorScheme = if (pal.dark) darkColorScheme() else lightColorScheme()
    val scheme = base.copy(
        primary = accent, onPrimary = onAccent,
        primaryContainer = accent.copy(alpha = 0.16f), onPrimaryContainer = pal.text,
        secondaryContainer = accent.copy(alpha = 0.16f), onSecondaryContainer = pal.text,
        background = pal.bg, onBackground = pal.text,
        surface = pal.card, onSurface = pal.text,
        surfaceVariant = pal.field, onSurfaceVariant = pal.muted,
        surfaceContainer = pal.card, surfaceContainerHigh = pal.card, surfaceContainerHighest = pal.hover,
        outline = pal.muted, outlineVariant = pal.line,
        error = Color(0xFFDC2626),
    )
    CompositionLocalProvider(LocalLayoutDirection provides if (fa) LayoutDirection.Rtl else LayoutDirection.Ltr) {
        MaterialTheme(
            colorScheme = scheme, typography = typography(fa),
            shapes = Shapes(
                extraSmall = RoundedCornerShape(8.dp), small = RoundedCornerShape(12.dp), medium = RoundedCornerShape(16.dp),
                large = RoundedCornerShape(24.dp), extraLarge = RoundedCornerShape(28.dp),
            ),
            content = content,
        )
    }
}

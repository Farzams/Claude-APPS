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
    // Studio: calm and neutral
    Palette("qp_light", "Studio Light", false, c(0xF6F7F9), c(0xFFFFFF), c(0xFFFFFF), c(0xEEF0F4), c(0x101828), c(0x667085), c(0x4F46E5), c(0xE4E7EC)),
    Palette("qp_dark", "Studio Dark", true, c(0x0D0F13), c(0x14171C), c(0x171A20), c(0x1C2027), c(0xE8EAEE), c(0x8B93A1), c(0x818CF8), c(0x232830)),
    // Parchment: warm paper
    Palette("paper", "Parchment Light", false, c(0xF3EEE4), c(0xFBF8F2), c(0xFFFDF8), c(0xE9E2D2), c(0x2B2620), c(0x7A6F60), c(0xB4532A), c(0xDDD4C1)),
    Palette("paper_dark", "Parchment Dark", true, c(0x1C1814), c(0x26211B), c(0x2B251E), c(0x322B23), c(0xEADFCB), c(0xA39881), c(0xE08A5C), c(0x3A3228)),
    // Ocean: cool blue-green
    Palette("ocean", "Ocean Light", false, c(0xEDF5F8), c(0xFFFFFF), c(0xFFFFFF), c(0xDDECF1), c(0x0B2530), c(0x58727E), c(0x0E7490), c(0xD0E2E9)),
    Palette("ocean_dark", "Ocean Dark", true, c(0x08171D), c(0x0F232B), c(0x112A33), c(0x16313B), c(0xE3F1F5), c(0x8FAAB5), c(0x2CC1D9), c(0x1B3A46)),
    // Forest: fresh green
    Palette("forest", "Forest Light", false, c(0xF0F6F0), c(0xFFFFFF), c(0xFFFFFF), c(0xE1EDE2), c(0x12261A), c(0x5C7363), c(0x15803D), c(0xD3E3D6)),
    Palette("forest_dark", "Forest Dark", true, c(0x0B1510), c(0x121F18), c(0x14251C), c(0x1A2D22), c(0xE4F1E7), c(0x8FA898), c(0x4ADE80), c(0x213628)),
    // Sunset: warm rose and orange
    Palette("sunset", "Sunset Light", false, c(0xFFF3EC), c(0xFFFFFF), c(0xFFFFFF), c(0xFFE5D8), c(0x2D1A14), c(0x86675B), c(0xE4572E), c(0xF2D8CB)),
    Palette("sunset_dark", "Sunset Dark", true, c(0x1C1210), c(0x271A17), c(0x2D1E1A), c(0x35241F), c(0xF8E8E1), c(0xB79A8E), c(0xFF7F5C), c(0x41302A)),
    // Graphite: black and white, true black in the dark version
    Palette("graphite", "Graphite Light", false, c(0xF4F4F4), c(0xFFFFFF), c(0xFFFFFF), c(0xEAEAEA), c(0x111111), c(0x6B6B6B), c(0x111111), c(0xDEDEDE)),
    Palette("graphite_dark", "Graphite Dark", true, c(0x000000), c(0x0B0B0B), c(0x121212), c(0x1A1A1A), c(0xF2F2F2), c(0x8C8C8C), c(0xFFFFFF), c(0x262626)),
)
val ACCENTS = listOf("#4F46E5", "#0F766E", "#BE185D", "#EA580C", "#16A34A", "#E11D48", "#475569", "#CA8A04", "#2563EB")

/** (design style) -> (light theme, dark theme) */
val STYLES = linkedMapOf(
    "quiet" to ("qp_light" to "qp_dark"), "paper" to ("paper" to "paper_dark"), "ocean" to ("ocean" to "ocean_dark"),
    "forest" to ("forest" to "forest_dark"), "sunset" to ("sunset" to "sunset_dark"), "graphite" to ("graphite" to "graphite_dark"),
)

/** The colour used when no accent is picked: Studio takes the app's own colour, every other theme brings its own. */
fun defaultAccent(pal: Palette, app: Color?): Color = if (pal.key.startsWith("qp_")) app ?: pal.accent else pal.accent

fun paletteOf(key: String): Palette = PALETTES.firstOrNull { it.key == key } ?: PALETTES[0]
fun styleOf(key: String): String = STYLES.entries.firstOrNull { key == it.value.first || key == it.value.second }?.key ?: "quiet"
fun parseColor(hex: String): Color? = runCatching { Color(android.graphics.Color.parseColor(hex)) }.getOrNull()

private val Vazir = FontFamily(Font(R.font.vazirmatn_regular, FontWeight.Normal), Font(R.font.vazirmatn_bold, FontWeight.Bold))

private fun typography(fa: Boolean, st: ThemeStyle): Typography {
    val plain = Typography()
    val titleStyle = if (st.titleItalic) androidx.compose.ui.text.font.FontStyle.Italic else androidx.compose.ui.text.font.FontStyle.Normal
    var base = plain.copy(
        headlineMedium = plain.headlineMedium.copy(fontWeight = st.titleWeight, fontStyle = titleStyle, letterSpacing = (-0.4).sp),
        headlineSmall = plain.headlineSmall.copy(fontWeight = st.titleWeight, fontStyle = titleStyle),
        titleLarge = plain.titleLarge.copy(fontWeight = FontWeight.Bold),
        titleMedium = plain.titleMedium.copy(fontWeight = FontWeight.SemiBold),
    )
    fun withFont(t: Typography, ff: FontFamily): Typography {
        fun f(s: TextStyle) = s.copy(fontFamily = ff)
        return t.copy(
            displayLarge = f(t.displayLarge), displayMedium = f(t.displayMedium), displaySmall = f(t.displaySmall),
            headlineLarge = f(t.headlineLarge), headlineMedium = f(t.headlineMedium), headlineSmall = f(t.headlineSmall),
            titleLarge = f(t.titleLarge), titleMedium = f(t.titleMedium), titleSmall = f(t.titleSmall),
            bodyLarge = f(t.bodyLarge), bodyMedium = f(t.bodyMedium), bodySmall = f(t.bodySmall),
            labelLarge = f(t.labelLarge), labelMedium = f(t.labelMedium), labelSmall = f(t.labelSmall),
        )
    }
    st.font?.let { base = withFont(base, it) }
    if (fa) base = withFont(base, Vazir)
    return base
}

@Composable
fun AppTheme(pal: Palette, accentHex: String, fa: Boolean, content: @Composable () -> Unit) {
    val appAccent = parseColor(LocalContext.current.getString(R.string.app_accent))
    val accent = parseColor(accentHex) ?: defaultAccent(pal, appAccent)
    val onAccent = if (accent.luminance() > 0.40f) Color(0xFF14110A) else Color.White
    val st = styleByKey(styleOf(pal.key))
    val base: ColorScheme = if (pal.dark) darkColorScheme() else lightColorScheme()
    val scheme = base.copy(
        primary = accent, onPrimary = onAccent,
        primaryContainer = accent.copy(alpha = 0.16f), onPrimaryContainer = pal.text,
        secondaryContainer = accent.copy(alpha = 0.16f), onSecondaryContainer = pal.text,
        background = pal.bg, onBackground = pal.text,
        surface = if (st.glass) pal.card.copy(alpha = 0.62f) else pal.card, onSurface = pal.text,
        surfaceVariant = pal.field, onSurfaceVariant = pal.muted,
        surfaceContainer = pal.card, surfaceContainerHigh = pal.card, surfaceContainerHighest = pal.hover,
        outline = pal.muted, outlineVariant = pal.line,
        error = Color(0xFFDC2626),
    )
    CompositionLocalProvider(LocalLayoutDirection provides if (fa) LayoutDirection.Rtl else LayoutDirection.Ltr, LocalStyle provides st) {
        MaterialTheme(colorScheme = scheme, typography = typography(fa, st), shapes = st.shapes, content = content)
    }
}

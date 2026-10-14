@file:OptIn(androidx.compose.ui.text.ExperimentalTextApi::class)

package app.pdftoolkit.mobile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.material3.LocalContentColor
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.shape.CircleShape
import kotlin.math.max

enum class HeaderStyle { PLAIN, CENTER_RULE, BANNER, HERO, UPPER }
enum class TileStyle { GRID, FILLED, LIST }
enum class IconStyle { SOFT, GRADIENT, BARE }
enum class BgStyle { PLAIN, WATER, PAPER }

/**
 * Everything a theme changes besides its colours: typeface, corner shapes, how cards, icons, the header, the home tiles,
 * the bottom bar and the screen background look.
 */
class ThemeStyle(
    val key: String,
    val font: FontFamily?,
    val titleWeight: FontWeight,
    val titleItalic: Boolean,
    val shapes: Shapes,
    val button: Shape,
    val iconShape: Shape,
    val borderWidth: Dp,
    val borderStrength: Float,
    val glass: Boolean,
    val header: HeaderStyle,
    val tiles: TileStyle,
    val icons: IconStyle,
    val floatingNav: Boolean,
    val bg: BgStyle,
)

private fun vf(res: Int, w: Int, style: FontStyle = FontStyle.Normal) =
    Font(res, FontWeight(w), style, variationSettings = FontVariation.Settings(FontVariation.weight(w)))

private fun variable(res: Int) = FontFamily(vf(res, 400), vf(res, 500), vf(res, 600), vf(res, 700), vf(res, 800))

private val Jakarta = variable(R.font.plusjakarta)
private val OutfitFont = variable(R.font.outfit)
private val NunitoFont = variable(R.font.nunito)
private val MonoFont = variable(R.font.jetbrainsmono)
private val LoraFont = FontFamily(
    vf(R.font.lora, 400), vf(R.font.lora, 500), vf(R.font.lora, 600), vf(R.font.lora, 700),
    vf(R.font.lora_italic, 400, FontStyle.Italic), vf(R.font.lora_italic, 700, FontStyle.Italic),
)
private val PoppinsFont = FontFamily(
    Font(R.font.poppins_regular, FontWeight.Normal), Font(R.font.poppins_regular, FontWeight.Medium),
    Font(R.font.poppins_semibold, FontWeight.SemiBold), Font(R.font.poppins_semibold, FontWeight.Bold), Font(R.font.poppins_semibold, FontWeight.ExtraBold),
)

private fun shapesOf(xs: Int, s: Int, m: Int, l: Int, xl: Int) = Shapes(
    RoundedCornerShape(xs.dp), RoundedCornerShape(s.dp), RoundedCornerShape(m.dp), RoundedCornerShape(l.dp), RoundedCornerShape(xl.dp),
)

private fun leaf(r: Int, k: Int) = RoundedCornerShape(topStart = r.dp, topEnd = r.dp, bottomEnd = r.dp, bottomStart = k.dp)

val THEME_STYLES: Map<String, ThemeStyle> = linkedMapOf(
    "quiet" to ThemeStyle(
        "quiet", Jakarta, FontWeight.ExtraBold, false, shapesOf(8, 12, 16, 24, 28), RoundedCornerShape(50), RoundedCornerShape(14.dp),
        1.dp, 0f, false, HeaderStyle.PLAIN, TileStyle.GRID, IconStyle.SOFT, false, BgStyle.PLAIN,
    ),
    "paper" to ThemeStyle(
        "paper", LoraFont, FontWeight.Bold, true, shapesOf(2, 3, 4, 6, 6), RoundedCornerShape(3.dp), RoundedCornerShape(0.dp),
        1.dp, 0.45f, false, HeaderStyle.CENTER_RULE, TileStyle.GRID, IconStyle.BARE, false, BgStyle.PAPER,
    ),
    "ocean" to ThemeStyle(
        "ocean", OutfitFont, FontWeight.Bold, false, shapesOf(12, 18, 24, 28, 32), RoundedCornerShape(50), RoundedCornerShape(18.dp),
        1.dp, 0f, true, HeaderStyle.PLAIN, TileStyle.GRID, IconStyle.GRADIENT, true, BgStyle.WATER,
    ),
    "forest" to ThemeStyle(
        "forest", NunitoFont, FontWeight.ExtraBold, false,
        Shapes(RoundedCornerShape(12.dp), leaf(18, 6), leaf(24, 6), leaf(24, 6), leaf(30, 8)),
        leaf(18, 6), CircleShape, 0.dp, 0f, false, HeaderStyle.BANNER, TileStyle.GRID, IconStyle.SOFT, false, BgStyle.PLAIN,
    ),
    "sunset" to ThemeStyle(
        "sunset", PoppinsFont, FontWeight.Bold, false, shapesOf(10, 14, 22, 26, 30), RoundedCornerShape(50), CircleShape,
        0.dp, 0f, false, HeaderStyle.HERO, TileStyle.FILLED, IconStyle.GRADIENT, false, BgStyle.PLAIN,
    ),
    "graphite" to ThemeStyle(
        "graphite", MonoFont, FontWeight.Bold, false, shapesOf(2, 2, 2, 2, 2), RoundedCornerShape(2.dp), RoundedCornerShape(0.dp),
        1.dp, 0.8f, false, HeaderStyle.UPPER, TileStyle.LIST, IconStyle.BARE, false, BgStyle.PLAIN,
    ),
)

val LocalStyle = staticCompositionLocalOf { THEME_STYLES.getValue("quiet") }

fun styleByKey(key: String): ThemeStyle = THEME_STYLES[key] ?: THEME_STYLES.getValue("quiet")

/** The thin outline of a card in this theme, or no outline at all. */
@Composable
fun cardStroke(): BorderStroke? {
    val st = LocalStyle.current
    if (st.borderWidth == 0.dp) return null
    val cs = MaterialTheme.colorScheme
    return BorderStroke(st.borderWidth, lerp(cs.outlineVariant, cs.onSurface, st.borderStrength))
}

/** The screen background: plain, or with the water glow or the paper vignette of the theme. */
@Composable
fun Modifier.themeBackground(): Modifier {
    val cs = MaterialTheme.colorScheme
    val st = LocalStyle.current
    val base = this.background(cs.background)
    return when (st.bg) {
        BgStyle.PLAIN -> base
        BgStyle.WATER -> base.drawBehind {
            drawRect(Brush.radialGradient(listOf(cs.primary.copy(alpha = 0.26f), Color.Transparent), center = Offset(size.width, 0f), radius = size.width * 1.1f))
            drawRect(Brush.radialGradient(listOf(cs.primary.copy(alpha = 0.14f), Color.Transparent), center = Offset(0f, size.height * 0.65f), radius = size.width))
        }
        BgStyle.PAPER -> base.drawBehind {
            drawRect(Brush.radialGradient(listOf(Color.Transparent, cs.onBackground.copy(alpha = 0.09f)), center = center, radius = max(size.width, size.height) * 0.75f))
        }
    }
}

/** The title area of a start page. Its look follows the theme: plain, centred with a rule, a coloured banner, or small capitals. */
@Composable
fun ThemedHeader(title: String, subtitle: String, actions: @Composable RowScope.() -> Unit = {}) {
    val cs = MaterialTheme.colorScheme
    val st = LocalStyle.current
    val banner = st.header == HeaderStyle.BANNER || st.header == HeaderStyle.HERO
    CompositionLocalProvider(LocalContentColor provides if (banner) Color.White else cs.onBackground) { when (st.header) {
        HeaderStyle.PLAIN -> Row(Modifier.fillMaxWidth().padding(start = 20.dp, end = 8.dp, top = 12.dp, bottom = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.headlineMedium, color = cs.onBackground)
                Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = cs.onSurfaceVariant)
            }
            actions()
        }
        HeaderStyle.CENTER_RULE -> Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(title, style = MaterialTheme.typography.headlineMedium, color = cs.onBackground, textAlign = TextAlign.Center)
                    Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = cs.onSurfaceVariant, textAlign = TextAlign.Center)
                }
                actions()
            }
            HorizontalDivider(Modifier.padding(top = 8.dp), color = lerp(cs.outlineVariant, cs.onSurface, 0.4f))
        }
        HeaderStyle.UPPER -> Column(Modifier.fillMaxWidth().padding(start = 20.dp, end = 8.dp, top = 12.dp, bottom = 4.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(title.uppercase(), style = MaterialTheme.typography.headlineSmall, color = cs.onBackground)
                    Text(subtitle.uppercase(), style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 1.sp), color = cs.onSurfaceVariant)
                }
                actions()
            }
        }
        HeaderStyle.BANNER, HeaderStyle.HERO -> {
            val hero = st.header == HeaderStyle.HERO
            val colors = if (hero) listOf(lerp(cs.primary, Color.White, 0.22f), cs.primary, lerp(cs.primary, Color(0xFFC2185B), 0.55f))
            else listOf(cs.primary, lerp(cs.primary, Color.White, 0.2f))
            Box(
                Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 8.dp)
                    .background(Brush.linearGradient(colors), MaterialTheme.shapes.extraLarge),
            ) {
                Row(Modifier.fillMaxWidth().padding(start = 20.dp, end = 8.dp, top = if (hero) 26.dp else 18.dp, bottom = if (hero) 26.dp else 18.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(title, style = MaterialTheme.typography.headlineMedium, color = Color.White)
                        Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = Color.White.copy(alpha = 0.9f))
                    }
                    actions()
                }
            }
        }
    } }
}

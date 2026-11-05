package app.linuxpad.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

val Bg = Color(0xFF1C0A19)
val Rail = Color(0xFF260C22)
val CardBg = Color(0xFF2B1327)
val Outline = Color(0x22FFFFFF)
val Accent = Color(0xFFE95420)
val Ok = Color(0xFF5BD98C)
val Warn = Color(0xFFFBBF24)
val Err = Color(0xFFF87171)
val TextMain = Color(0xFFF6EEF4)
val TextMuted = Color(0xFFC4B2C0)

/** Near-black with one blue accent, big rounded cards and large touch targets. */
@Composable
fun LinuxPadTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Accent, onPrimary = Color.White, background = Bg, surface = Bg, onSurface = TextMain,
            surfaceVariant = CardBg, onSurfaceVariant = TextMuted, outline = Outline, error = Err,
            secondaryContainer = Color(0xFF4A2038), onSecondaryContainer = TextMain,
        ),
    ) { Surface(color = Bg, content = content) }
}

@Composable
fun ScreenTitle(text: String) {
    Text(text, fontSize = 34.sp, fontWeight = FontWeight.Bold, color = TextMain, modifier = Modifier.padding(bottom = 4.dp))
}

/** A rounded card with a heading. */
@Composable
fun AppCard(title: String, modifier: Modifier = Modifier, chip: (@Composable () -> Unit)? = null, content: @Composable ColumnScope.() -> Unit) {
    val shape = RoundedCornerShape(28.dp)
    Column(
        modifier.fillMaxWidth().clip(shape)
            .background(CardBg).background(androidx.compose.ui.graphics.Brush.verticalGradient(listOf(Color(0x14FFFFFF), Color(0x0AFFFFFF))))
            .border(BorderStroke(1.dp, Outline), shape).padding(22.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        androidx.compose.foundation.layout.Row(Modifier.fillMaxWidth(), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
            Text(title, fontSize = 20.sp, fontWeight = FontWeight.SemiBold, color = TextMain, modifier = Modifier.weight(1f))
            chip?.invoke()
        }
        content()
    }
}

/** A small status label such as "Installed" or "Needs permission". */
@Composable
fun StatusChip(text: String, color: Color) {
    Text(
        text, color = color, fontSize = 13.sp, fontWeight = FontWeight.Medium,
        modifier = Modifier.clip(CircleShape).background(color.copy(alpha = 0.14f)).padding(horizontal = 12.dp, vertical = 5.dp),
    )
}

@Composable
fun Muted(text: String) = Text(text, color = TextMuted, fontSize = 15.sp, lineHeight = 21.sp)

val Violet = Color(0xFF77216F)

/** The app mark: a rounded gradient tile with an L and the name beside it in a large type. */
@Composable
fun BrandMark() {
    androidx.compose.foundation.layout.Column(Modifier.padding(top = 20.dp, bottom = 22.dp), horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally) {
        androidx.compose.foundation.layout.Box(
            Modifier.size(60.dp).clip(RoundedCornerShape(20.dp))
                .background(androidx.compose.ui.graphics.Brush.linearGradient(listOf(Accent, Color(0xFFC13C77), Violet))),
            contentAlignment = androidx.compose.ui.Alignment.Center,
        ) { Text("L", color = Color.White, fontSize = 32.sp, fontWeight = FontWeight.ExtraBold) }
        Text("LinuxPad", color = TextMain, fontSize = 20.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 10.dp))
        Text("Debian desktop", color = TextMuted, fontSize = 12.sp)
    }
}

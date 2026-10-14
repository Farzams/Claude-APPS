package app.pdftoolkit.mobile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp

@OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)
@Composable
fun SettingsScreen(prefs: Prefs, onChanged: () -> Unit, onBack: () -> Unit) {
    val cs = MaterialTheme.colorScheme
    val pal = paletteOf(prefs.theme)
    val style = styleOf(prefs.theme)

    @Composable
    fun chip(label: String, selected: Boolean, tag: String, onClick: () -> Unit) {
        Surface(
            onClick = onClick, shape = RoundedCornerShape(20.dp),
            color = if (selected) cs.primary else cs.surface,
            border = BorderStroke(1.dp, if (selected) cs.primary else cs.outlineVariant), modifier = Modifier.testTag(tag),
        ) {
            Text(label, Modifier.padding(horizontal = 16.dp, vertical = 9.dp), color = if (selected) cs.onPrimary else cs.onSurface, style = MaterialTheme.typography.labelLarge)
        }
    }

    Column(Modifier.fillMaxSize().statusBarsPadding().navigationBarsPadding()) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack, modifier = Modifier.testTag("back")) { Icon(Icons.AutoMirrored.Filled.ArrowBack, t("back"), tint = cs.onBackground) }
            Text(t("settings"), style = MaterialTheme.typography.titleLarge, color = cs.onBackground)
        }
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.TopCenter) {
        Column(Modifier.widthIn(max = CONTENT_MAX_DP.dp).fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
            Text(t("mode"), style = MaterialTheme.typography.titleSmall, color = cs.onSurfaceVariant)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                chip(t("light"), !pal.dark, "mode_light") { prefs.theme = STYLES[style]!!.first; onChanged() }
                chip(t("dark"), pal.dark, "mode_dark") { prefs.theme = STYLES[style]!!.second; onChanged() }
            }
            Text(t("style"), style = MaterialTheme.typography.titleSmall, color = cs.onSurfaceVariant)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                for ((k, pair) in STYLES) {
                    chip(t(k), style == k, "style_$k") { prefs.theme = if (pal.dark) pair.second else pair.first; onChanged() }
                }
            }
            Text(t("accent"), style = MaterialTheme.typography.titleSmall, color = cs.onSurfaceVariant)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                for (hex in listOf("") + ACCENTS) {
                    val color = parseColor(hex) ?: parseColor(LocalContext.current.getString(R.string.app_accent)) ?: pal.accent
                    Box(
                        Modifier.size(36.dp).clip(CircleShape).background(color)
                            .clickable { prefs.accent = hex; onChanged() }.testTag("accent_${hex.ifEmpty { "default" }}"),
                        contentAlignment = Alignment.Center,
                    ) {
                        if (prefs.accent == hex) Box(Modifier.size(14.dp).clip(CircleShape).background(androidx.compose.ui.graphics.Color.White.copy(alpha = 0.95f)))
                    }
                }
            }
            Text(t("language"), style = MaterialTheme.typography.titleSmall, color = cs.onSurfaceVariant)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                chip("English", prefs.lang == "en", "lang_en") { prefs.lang = "en"; onChanged() }
                chip("فارسی", prefs.lang == "fa", "lang_fa") { prefs.lang = "fa"; onChanged() }
            }
        }
        }
    }
}

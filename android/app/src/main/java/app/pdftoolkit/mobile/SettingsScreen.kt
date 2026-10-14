@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package app.pdftoolkit.mobile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Palette as PaletteIcon
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp

/** One group of settings: an icon and a title on top, the controls below. */
@Composable
fun SettingsCard(title: String, icon: ImageVector, content: @Composable ColumnScope.() -> Unit) {
    val cs = MaterialTheme.colorScheme
    Surface(shape = MaterialTheme.shapes.large, color = cs.surface, border = cardStroke(), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Surface(shape = MaterialTheme.shapes.small, color = cs.primaryContainer, modifier = Modifier.size(38.dp)) {
                    Box(contentAlignment = Alignment.Center) { Icon(icon, null, tint = cs.primary, modifier = Modifier.size(20.dp)) }
                }
                Text(title, style = MaterialTheme.typography.titleMedium, color = cs.onSurface)
            }
            content()
        }
    }
}

@Composable
fun SettingsLabel(text: String) = Text(text, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)

@Composable
fun SwitchRow(label: String, checked: Boolean, tag: String, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().clickable { onChange(!checked) }, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(label, Modifier.weight(1f), color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.bodyLarge)
        Switch(checked = checked, onCheckedChange = onChange, modifier = Modifier.testTag(tag))
    }
}

@Composable
fun SettingsChip(label: String, selected: Boolean, tag: String, onClick: () -> Unit) {
    val cs = MaterialTheme.colorScheme
    Surface(
        onClick = onClick, shape = MaterialTheme.shapes.large,
        color = if (selected) cs.primary else cs.surface,
        border = BorderStroke(1.dp, if (selected) cs.primary else cs.outlineVariant), modifier = Modifier.testTag(tag),
    ) {
        Text(label, Modifier.padding(horizontal = 16.dp, vertical = 9.dp), color = if (selected) cs.onPrimary else cs.onSurface, style = MaterialTheme.typography.labelLarge)
    }
}

/** A small preview of a theme in the colours it will use. */
@Composable
private fun ThemeTile(name: String, pal: Palette, accent: Color, style: ThemeStyle, selected: Boolean, tag: String, onClick: () -> Unit) {
    val cs = MaterialTheme.colorScheme
    Surface(
        onClick = onClick, shape = style.shapes.medium, color = pal.bg,
        border = BorderStroke(if (selected) 2.5.dp else 1.dp, if (selected) cs.primary else cs.outlineVariant),
        modifier = Modifier.width(104.dp).testTag(tag),
    ) {
        Column(Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Surface(shape = style.shapes.small, color = pal.card, border = BorderStroke(1.dp, pal.line)) {
                Column(Modifier.fillMaxWidth().padding(8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Box(Modifier.fillMaxWidth(0.55f).height(6.dp).clip(RoundedCornerShape(3.dp)).background(accent))
                    Box(Modifier.fillMaxWidth().height(3.dp).clip(RoundedCornerShape(2.dp)).background(pal.muted.copy(alpha = 0.55f)))
                    Box(Modifier.fillMaxWidth(0.7f).height(3.dp).clip(RoundedCornerShape(2.dp)).background(pal.muted.copy(alpha = 0.55f)))
                }
            }
            Text(name, color = pal.text, style = MaterialTheme.typography.labelMedium, fontFamily = style.font, fontWeight = style.titleWeight, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable
fun SettingsScreen(
    prefs: Prefs, onChanged: () -> Unit, onBack: () -> Unit,
    tagline: String = "", extra: @Composable ColumnScope.() -> Unit = {},
) {
    val cs = MaterialTheme.colorScheme
    val ctx = LocalContext.current
    val pal = paletteOf(prefs.theme)
    val style = styleOf(prefs.theme)
    val appAccent = parseColor(ctx.getString(R.string.app_accent))
    val version = remember(ctx) { runCatching { ctx.packageManager.getPackageInfo(ctx.packageName, 0).versionName }.getOrNull() ?: "" }

    Column(Modifier.fillMaxSize().statusBarsPadding().navigationBarsPadding()) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack, modifier = Modifier.testTag("back")) { Icon(Icons.AutoMirrored.Filled.ArrowBack, t("back"), tint = cs.onBackground) }
            Text(t("settings"), style = MaterialTheme.typography.titleLarge, color = cs.onBackground)
        }
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.TopCenter) {
            Column(
                Modifier.widthIn(max = CONTENT_MAX_DP.dp).fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp).padding(bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                SettingsCard(t("settings.appearance"), Icons.Filled.PaletteIcon) {
                    SettingsLabel(t("mode"))
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        SettingsChip(t("light"), !pal.dark, "mode_light") { prefs.theme = STYLES[style]!!.first; onChanged() }
                        SettingsChip(t("dark"), pal.dark, "mode_dark") { prefs.theme = STYLES[style]!!.second; onChanged() }
                    }
                    SettingsLabel(t("theme"))
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        for ((k, pair) in STYLES) {
                            val key = if (pal.dark) pair.second else pair.first
                            val p = paletteOf(key)
                            ThemeTile(t(k), p, defaultAccent(p, appAccent), styleByKey(k), style == k, "style_$k") { prefs.theme = key; onChanged() }
                        }
                    }
                    SettingsLabel(t("accent"))
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        for (hex in listOf("") + ACCENTS) {
                            val color = parseColor(hex) ?: defaultAccent(pal, appAccent)
                            Box(
                                Modifier.size(36.dp).clip(CircleShape).background(color)
                                    .clickable { prefs.accent = hex; onChanged() }.testTag("accent_${hex.ifEmpty { "default" }}"),
                                contentAlignment = Alignment.Center,
                            ) {
                                if (prefs.accent == hex) Box(Modifier.size(14.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.95f)))
                            }
                        }
                    }
                }
                extra()
                SettingsCard(t("settings.language"), Icons.Filled.Language) {
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        SettingsChip("English", prefs.lang == "en", "lang_en") { prefs.lang = "en"; onChanged() }
                        SettingsChip("فارسی", prefs.lang == "fa", "lang_fa") { prefs.lang = "fa"; onChanged() }
                    }
                }
                SettingsCard(t("about"), Icons.Filled.Info) {
                    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(ctx.getString(R.string.app_name), style = MaterialTheme.typography.headlineSmall, color = cs.onSurface)
                        if (tagline.isNotEmpty()) Text(tagline, style = MaterialTheme.typography.bodyMedium, color = cs.onSurfaceVariant)
                    }
                    AboutRow(t("about.version"), version, "about_version")
                    AboutRow(t("about.designed"), t("about.author"), "about_author")
                    AboutRow(t("about.built"), t("about.claude"), "about_claude")
                }
            }
        }
    }
}

@Composable
private fun AboutRow(label: String, value: String, tag: String) {
    val cs = MaterialTheme.colorScheme
    Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
        Text(label, style = MaterialTheme.typography.labelMedium, color = cs.onSurfaceVariant)
        Text(value, Modifier.testTag(tag), style = MaterialTheme.typography.bodyLarge, color = cs.onSurface)
    }
}

package app.pdftoolkit.mobile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** TeXora's own settings group: how the editor looks and behaves. */
@Composable
fun ColumnScope.EditorSettingsCard(prefs: Prefs) {
    var size by remember { mutableIntStateOf(prefs.editorSize) }
    var numbers by remember { mutableStateOf(prefs.lineNumbers) }
    var wrap by remember { mutableStateOf(prefs.wrap) }
    var pairs by remember { mutableStateOf(prefs.autoPairs) }
    var palette by remember { mutableStateOf(prefs.palette) }
    SettingsCard(t("settings.editor"), Icons.Filled.Edit) {
        SettingsLabel("${t("font.size")}: $size")
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
            OutlinedButton(onClick = { size = (size - 1).coerceAtLeast(10); prefs.editorSize = size }, modifier = Modifier.testTag("font_minus")) { Text("A−") }
            OutlinedButton(onClick = { size = (size + 1).coerceAtMost(26); prefs.editorSize = size }, modifier = Modifier.testTag("font_plus")) { Text("A+") }
            Text("\\section{Aa}", fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace, fontSize = size.sp, color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.padding(start = 8.dp))
        }
        SwitchRow(t("line.numbers"), numbers, "sw_numbers") { numbers = it; prefs.lineNumbers = it }
        SwitchRow(t("wrap"), wrap, "sw_wrap") { wrap = it; prefs.wrap = it }
        SwitchRow(t("auto.pairs"), pairs, "sw_pairs") { pairs = it; prefs.autoPairs = it }
        SwitchRow(t("palette"), palette, "sw_palette") { palette = it; prefs.palette = it }
    }
}

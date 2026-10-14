package app.pdftoolkit.mobile

import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag

/** PDFora's own settings group: the list of recent files. */
@Composable
fun ColumnScope.FilesSettingsCard() {
    val ctx = LocalContext.current
    var count by remember { mutableIntStateOf(Recents.list(ctx).size) }
    SettingsCard(t("settings.files"), Icons.Filled.Folder) {
        Text("$count ${t("recent.count")}", color = androidx.compose.material3.MaterialTheme.colorScheme.onSurface)
        OutlinedButton(onClick = { Recents.clear(ctx); count = 0 }, enabled = count > 0, modifier = Modifier.testTag("clear_recent")) { Text(t("clear.recent")) }
    }
}

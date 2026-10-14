package app.pdftoolkit.mobile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Compress
import androidx.compose.material.icons.filled.ContentCut
import androidx.compose.material.icons.filled.DocumentScanner
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.GridView
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.MergeType
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp

private data class Card(val key: String, val icon: ImageVector, val ready: Boolean)

private val CARDS = listOf(
    Card("latex", Icons.Filled.Edit, true),
    Card("merge", Icons.Filled.MergeType, false), Card("split", Icons.Filled.ContentCut, false),
    Card("organize", Icons.Filled.GridView, false), Card("compress", Icons.Filled.Compress, false),
    Card("convert", Icons.Filled.SwapHoriz, false), Card("ocr", Icons.Filled.DocumentScanner, false),
    Card("protect", Icons.Filled.Lock, false),
)

@Composable
fun HomeScreen(onOpen: (String) -> Unit, onSettings: () -> Unit) {
    val cs = MaterialTheme.colorScheme
    Column(Modifier.fillMaxSize().statusBarsPadding()) {
        Row(Modifier.fillMaxWidth().padding(start = 20.dp, end = 8.dp, top = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(t("app"), style = MaterialTheme.typography.headlineMedium, color = cs.onBackground)
                Text(t("home.sub"), style = MaterialTheme.typography.bodyMedium, color = cs.onSurfaceVariant)
            }
            IconButton(onClick = onSettings, modifier = Modifier.testTag("open_settings")) {
                Icon(Icons.Filled.Settings, t("settings"), tint = cs.onBackground)
            }
        }
        Spacer(Modifier.height(12.dp))
        LazyVerticalGrid(
            columns = GridCells.Adaptive(160.dp), modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(CARDS, span = { if (it.key == "latex") GridItemSpan(maxLineSpan) else GridItemSpan(1) }) { c ->
                Surface(
                    onClick = { if (c.ready) onOpen(c.key) }, enabled = c.ready, shape = RoundedCornerShape(16.dp),
                    color = cs.surface, border = BorderStroke(1.dp, cs.outlineVariant), modifier = Modifier.testTag("card_${c.key}"),
                ) {
                    Column(Modifier.padding(16.dp).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Box(Modifier.size(44.dp), contentAlignment = Alignment.Center) {
                            Surface(shape = RoundedCornerShape(12.dp), color = cs.primary.copy(alpha = 0.14f), modifier = Modifier.size(44.dp)) {
                                Box(contentAlignment = Alignment.Center) { Icon(c.icon, null, tint = cs.primary, modifier = Modifier.size(24.dp)) }
                            }
                        }
                        Text(t(c.key), style = MaterialTheme.typography.titleMedium, color = if (c.ready) cs.onSurface else cs.onSurfaceVariant)
                        if (c.key == "latex") Text(t("latex.sub"), style = MaterialTheme.typography.bodyMedium, color = cs.onSurfaceVariant)
                        if (!c.ready) Text(t("soon"), style = MaterialTheme.typography.labelMedium, color = cs.onSurfaceVariant)
                    }
                }
            }
        }
    }
}

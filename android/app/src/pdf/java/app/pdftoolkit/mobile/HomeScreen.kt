package app.pdftoolkit.mobile

import android.net.Uri
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.Compress
import androidx.compose.material.icons.filled.ContentCut
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.FormatListNumbered
import androidx.compose.material.icons.filled.GridView
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Image as ImageIcon
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.MergeType
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp

private data class Card(val key: String, val icon: ImageVector)

private val CARDS = listOf(
    Card("docs2pdf", Icons.Filled.AutoStories), Card("merge", Icons.Filled.MergeType), Card("split", Icons.Filled.ContentCut),
    Card("organize", Icons.Filled.GridView), Card("compress", Icons.Filled.Compress),
    Card("img2pdf", Icons.Filled.ImageIcon), Card("pdf2img", Icons.Filled.PictureAsPdf),
    Card("protect", Icons.Filled.Lock), Card("watermark", Icons.Filled.WaterDrop), Card("numbers", Icons.Filled.FormatListNumbered),
)

/** Tools that can start from a PDF picked on the home page. */
private val FILE_TOOLS = listOf("split", "organize", "compress", "protect", "watermark", "numbers", "pdf2img", "merge")

/** Bottom bar on a phone, side rail on a tablet. */
@Composable
fun PdfShell(selected: String, onNav: (String) -> Unit, content: @Composable () -> Unit) {
    val items = listOf(
        Triple("home", Icons.Filled.Home, t("home")),
        Triple("files", Icons.Filled.Folder, t("files.tab")),
        Triple("settings", Icons.Filled.Settings, t("settings")),
    )
    BoxWithConstraints(Modifier.fillMaxSize()) {
        if (maxWidth >= 720.dp) {
            Row(Modifier.fillMaxSize().statusBarsPadding().navigationBarsPadding()) {
                NavigationRail(windowInsets = WindowInsets(0, 0, 0, 0)) {
                    Spacer(Modifier.height(8.dp))
                    for ((key, icon, label) in items) {
                        NavigationRailItem(
                            selected = selected == key, onClick = { onNav(key) },
                            icon = { Icon(icon, null) }, label = { Text(label, maxLines = 1) },
                            modifier = Modifier.testTag(if (key == "settings") "open_settings" else "nav_$key"),
                        )
                    }
                }
                Box(Modifier.weight(1f)) { content() }
            }
        } else {
            Column(Modifier.fillMaxSize().statusBarsPadding()) {
                Box(Modifier.weight(1f)) { content() }
                NavigationBar {
                    for ((key, icon, label) in items) {
                        NavigationBarItem(
                            selected = selected == key, onClick = { onNav(key) },
                            icon = { Icon(icon, null) }, label = { Text(label, maxLines = 1) },
                            modifier = Modifier.testTag(if (key == "settings") "open_settings" else "nav_$key"),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ToolIcon(card: Card, index: Int, size: Int = 48) {
    val tone = toneOf(index)
    Surface(shape = RoundedCornerShape(16.dp), color = tone.container, modifier = Modifier.size(size.dp)) {
        Box(contentAlignment = Alignment.Center) { Icon(card.icon, null, tint = tone.icon, modifier = Modifier.size((size / 2).dp)) }
    }
}

@Composable
fun HomeScreen(onOpen: (String) -> Unit) {
    val ctx = LocalContext.current
    val cs = MaterialTheme.colorScheme
    var query by remember { mutableStateOf("") }
    var recents by remember { mutableStateOf(Recents.list(ctx)) }
    var chosen by remember { mutableStateOf<Recent?>(null) }
    val q = query.trim()
    val tools = CARDS.withIndex().filter { (_, c) -> q.isEmpty() || t(c.key).contains(q, true) || t("d." + c.key).contains(q, true) }

    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.TopCenter) {
        LazyVerticalGrid(
            columns = GridCells.Adaptive(160.dp), modifier = Modifier.widthIn(max = 1000.dp).fillMaxSize(),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 12.dp, bottom = 24.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp), verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item(span = { GridItemSpan(maxLineSpan) }) {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Column(Modifier.padding(horizontal = 4.dp)) {
                        Text(t("app"), style = MaterialTheme.typography.headlineMedium, color = cs.onBackground)
                        Text(t("pdf.sub"), style = MaterialTheme.typography.bodyMedium, color = cs.onSurfaceVariant)
                    }
                    TextField(
                        value = query, onValueChange = { query = it }, singleLine = true,
                        placeholder = { Text(t("search.tools"), maxLines = 1, overflow = TextOverflow.Ellipsis) },
                        leadingIcon = { Icon(Icons.Filled.Search, null) },
                        shape = RoundedCornerShape(28.dp),
                        colors = TextFieldDefaults.colors(
                            focusedIndicatorColor = Color.Transparent, unfocusedIndicatorColor = Color.Transparent, disabledIndicatorColor = Color.Transparent,
                            focusedContainerColor = cs.surfaceContainerHighest, unfocusedContainerColor = cs.surfaceContainerHighest,
                        ),
                        modifier = Modifier.fillMaxWidth().testTag("search"),
                    )
                }
            }
            if (q.isEmpty() && recents.isNotEmpty()) {
                item(span = { GridItemSpan(maxLineSpan) }) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(t("recent"), style = MaterialTheme.typography.titleMedium, color = cs.onBackground, modifier = Modifier.padding(start = 4.dp, top = 4.dp))
                        LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            items(recents.take(10), key = { it.uri }) { r -> RecentCard(r) { chosen = r } }
                        }
                    }
                }
            }
            item(span = { GridItemSpan(maxLineSpan) }) {
                Text(t("all.tools"), style = MaterialTheme.typography.titleMedium, color = cs.onBackground, modifier = Modifier.padding(start = 4.dp, top = 4.dp))
            }
            if (tools.isEmpty()) {
                item(span = { GridItemSpan(maxLineSpan) }) { Text(t("no.match"), color = cs.onSurfaceVariant, modifier = Modifier.padding(4.dp)) }
            }
            gridItems(tools, key = { it.value.key }) { (i, c) ->
                Surface(
                    onClick = { onOpen(c.key) }, shape = RoundedCornerShape(20.dp),
                    color = cs.surface, border = BorderStroke(1.dp, cs.outlineVariant),
                    modifier = Modifier.fillMaxWidth().heightIn(min = 140.dp).testTag("card_${c.key}"),
                ) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        ToolIcon(c, i)
                        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(t(c.key), style = MaterialTheme.typography.titleSmall, color = cs.onSurface, maxLines = 2, overflow = TextOverflow.Ellipsis)
                            Text(t("d." + c.key), style = MaterialTheme.typography.bodySmall, color = cs.onSurfaceVariant, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        }
                    }
                }
            }
        }
    }
    chosen?.let { r ->
        RecentChooser(r, onClose = { chosen = null }, onRemove = { Recents.remove(ctx, r.uri); recents = Recents.list(ctx); chosen = null }, onOpen = onOpen)
    }
}

@Composable
private fun RecentCard(r: Recent, onClick: () -> Unit) {
    val cs = MaterialTheme.colorScheme
    val thumb by rememberPdfThumb(Uri.parse(r.uri), 240)
    Surface(onClick = onClick, shape = RoundedCornerShape(16.dp), color = cs.surface, border = BorderStroke(1.dp, cs.outlineVariant), modifier = Modifier.width(112.dp).testTag("recent_card")) {
        Column(Modifier.padding(8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Box(Modifier.fillMaxWidth().height(128.dp).clip(RoundedCornerShape(10.dp)), contentAlignment = Alignment.Center) {
                val b = thumb
                if (b != null) Image(b.asImageBitmap(), null, contentScale = ContentScale.Crop, alignment = Alignment.TopCenter, modifier = Modifier.fillMaxSize())
                else Icon(Icons.Filled.PictureAsPdf, null, tint = cs.onSurfaceVariant, modifier = Modifier.size(32.dp))
            }
            Text(r.name, style = MaterialTheme.typography.labelMedium, color = cs.onSurface, maxLines = 2, overflow = TextOverflow.Ellipsis)
        }
    }
}

/** Asks which tool to open a recent file with. */
@Composable
private fun RecentChooser(r: Recent, onClose: () -> Unit, onRemove: () -> Unit, onOpen: (String) -> Unit) {
    val cs = MaterialTheme.colorScheme
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text(r.name, maxLines = 2, overflow = TextOverflow.Ellipsis) },
        text = {
            Column(Modifier.heightIn(max = 380.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(t("open.with"), color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
                for (key in FILE_TOOLS) {
                    val idx = CARDS.indexOfFirst { it.key == key }
                    Surface(
                        onClick = { PendingFile.uri = Uri.parse(r.uri); onClose(); onOpen(key) }, shape = RoundedCornerShape(14.dp),
                        color = Color.Transparent, modifier = Modifier.fillMaxWidth().testTag("choose_$key"),
                    ) {
                        Row(Modifier.padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            ToolIcon(CARDS[idx], idx, size = 40)
                            Text(t(key), color = cs.onSurface, style = MaterialTheme.typography.titleSmall)
                        }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text(t("cancel")) } },
        dismissButton = { TextButton(onClick = onRemove) { Text(t("remove"), color = cs.error) } },
    )
}

/** The Files tab: the in-app file manager. Tapping a file offers the tools that fit it. */
@Composable
fun FilesScreen(onOpen: (String) -> Unit) {
    val ctx = LocalContext.current
    val memory = remember { FileMemory(ctx) }
    var chosen by remember { mutableStateOf<Recent?>(null) }
    FileBrowser(
        mode = BrowserMode.MANAGE, allowed = null, multi = true, suggestedName = "", start = FileMemory.startFor(null), memory = memory,
        onClose = null, onDone = {}, onUseSystemPicker = null,
        onOpenFile = { f ->
            val uri = android.net.Uri.fromFile(f)
            when (kindOf(f)) {
                Kind.PDF -> { Recents.add(ctx, uri, f.name); chosen = Recent(uri.toString(), f.name, System.currentTimeMillis()) }
                Kind.BOOK -> { PendingFile.uri = uri; onOpen("docs2pdf") }
                Kind.IMAGE -> { PendingFile.uri = uri; onOpen("img2pdf") }
                else -> {}
            }
        },
    )
    chosen?.let { r ->
        RecentChooser(r, onClose = { chosen = null }, onRemove = { chosen = null }, onOpen = onOpen)
    }
}

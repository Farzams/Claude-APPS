@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package app.pdftoolkit.mobile

import android.graphics.Bitmap
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.lazy.grid.itemsIndexed as gridItemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.DragHandle
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Image as ImageIcon
import androidx.compose.material.icons.filled.OpenInNew
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.RotateRight
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.concurrent.atomic.AtomicLong

// ---------------------------------------------------------------- shared pieces

/** Runs a piece of work off the main thread and keeps the message to show. */
class ToolJob {
    var busy by mutableStateOf(false)
    var message by mutableStateOf("")
    var ok by mutableStateOf(true)
    var output by mutableStateOf<Uri?>(null)

    fun run(scope: CoroutineScope, out: Uri? = null, work: () -> String) {
        busy = true
        message = ""
        output = null
        scope.launch {
            try {
                message = withContext(Dispatchers.IO) { work() }
                ok = true
                output = out
            } catch (e: Throwable) {
                message = e.message ?: e.toString()
                ok = false
            } finally {
                busy = false
            }
        }
    }
}

/**
 * Every tool page: a title bar, content that scrolls and stays centred on tablets, and a bottom area
 * with the one main action that is always in reach.
 */
@Composable
private fun ToolPage(
    title: String, onBack: () -> Unit, scroll: Boolean = true, maxWidth: Dp = CONTENT_MAX_DP.dp,
    bottom: (@Composable ColumnScope.() -> Unit)? = null, content: @Composable ColumnScope.() -> Unit,
) {
    val cs = MaterialTheme.colorScheme
    Column(Modifier.fillMaxSize().statusBarsPadding().navigationBarsPadding().imePadding()) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack, modifier = Modifier.testTag("back")) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, t("back"), tint = cs.onBackground)
            }
            Text(title, style = MaterialTheme.typography.titleLarge, color = cs.onBackground, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.TopCenter) {
            val base = Modifier.widthIn(max = maxWidth).fillMaxSize().padding(horizontal = 16.dp)
            Column(
                if (scroll) base.verticalScroll(rememberScrollState()).padding(bottom = 16.dp) else base,
                verticalArrangement = Arrangement.spacedBy(14.dp), content = content,
            )
        }
        if (bottom != null) {
            Surface(color = cs.surface, tonalElevation = 3.dp, shadowElevation = 8.dp, modifier = Modifier.fillMaxWidth()) {
                Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.TopCenter) {
                    Column(
                        Modifier.widthIn(max = maxWidth).fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp), content = bottom,
                    )
                }
            }
        }
    }
}

@Composable
private fun JobStatus(job: ToolJob) {
    val cs = MaterialTheme.colorScheme
    val ctx = LocalContext.current
    if (job.busy) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            LinearProgressIndicator(Modifier.fillMaxWidth())
            Text(t("working"), color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
        }
    } else if (job.message.isNotEmpty()) {
        val good = job.ok
        Surface(shape = RoundedCornerShape(16.dp), color = if (good) cs.primaryContainer else cs.errorContainer, modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Icon(if (good) Icons.Filled.CheckCircle else Icons.Filled.ErrorOutline, null, tint = if (good) cs.primary else cs.error)
                    Text(job.message, Modifier.weight(1f).testTag(if (good) "result_ok" else "result_error"), color = cs.onSurface)
                }
                val out = job.output
                if (good && out != null) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { openPdf(ctx, out) }, modifier = Modifier.testTag("open_result")) {
                            Icon(Icons.Filled.OpenInNew, null, Modifier.size(18.dp)); Spacer(Modifier.width(6.dp)); Text(t("open"))
                        }
                        OutlinedButton(onClick = { sharePdfFile(ctx, out) }, modifier = Modifier.testTag("share_result")) {
                            Icon(Icons.Filled.Share, null, Modifier.size(18.dp)); Spacer(Modifier.width(6.dp)); Text(t("share"))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PrimaryButton(text: String, tag: String, enabled: Boolean, onClick: () -> Unit) {
    Button(onClick = onClick, enabled = enabled, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp).testTag(tag)) {
        Text(text, style = MaterialTheme.typography.titleSmall, textAlign = TextAlign.Center)
    }
}

@Composable
private fun Hint(text: String) = Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)

@Composable
private fun Label(text: String) = Text(text, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

/** The big "choose a file" card; once a file is chosen it shrinks to a row with a preview and its name. */
@Composable
private fun PickCard(
    chosen: Boolean, name: String, icon: ImageVector, title: String, hint: String,
    detail: String = "", thumb: Bitmap? = null, tag: String = "pick_file", onPick: () -> Unit,
) {
    val cs = MaterialTheme.colorScheme
    Surface(
        onClick = onPick, shape = RoundedCornerShape(20.dp),
        color = if (chosen) cs.surface else cs.primaryContainer,
        border = BorderStroke(1.dp, if (chosen) cs.outlineVariant else cs.primary.copy(alpha = 0.35f)),
        modifier = Modifier.fillMaxWidth().testTag(tag),
    ) {
        if (!chosen) {
            Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 28.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(icon, null, Modifier.size(40.dp), tint = cs.primary)
                Text(title, style = MaterialTheme.typography.titleMedium, color = cs.onSurface, textAlign = TextAlign.Center)
                Text(hint, style = MaterialTheme.typography.bodySmall, color = cs.onSurfaceVariant, textAlign = TextAlign.Center)
            }
        } else {
            Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(Modifier.size(width = 44.dp, height = 58.dp).clip(RoundedCornerShape(8.dp)).then(Modifier), contentAlignment = Alignment.Center) {
                    if (thumb != null) Image(thumb.asImageBitmap(), null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
                    else Icon(icon, null, tint = cs.primary)
                }
                Column(Modifier.weight(1f)) {
                    Text(name, Modifier.testTag("file_name"), style = MaterialTheme.typography.titleSmall, color = cs.onSurface, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    if (detail.isNotEmpty()) Text(detail, style = MaterialTheme.typography.bodySmall, color = cs.onSurfaceVariant)
                }
                Icon(Icons.Filled.SwapHoriz, t("change.file"), tint = cs.primary)
            }
        }
    }
}

/** The pick card for tools that work on one PDF. */
@Composable
private fun PdfPick(uri: Uri?, detail: String = "", onPick: () -> Unit) {
    val ctx = LocalContext.current
    val name = remember(uri) { if (uri == null) "" else PdfOps.nameOf(ctx, uri) }
    val thumb by rememberPdfThumb(uri, 120)
    PickCard(uri != null, name, Icons.Filled.PictureAsPdf, t("choose.pdf"), t("pick.pdf.hint"), detail, thumb, onPick = onPick)
}

private class Opt(val key: String, val title: String, val desc: String = "")

/** A short list of choices as full-width cards: long labels wrap instead of being cut off. */
@Composable
private fun Options(opts: List<Opt>, selected: String, onSelect: (String) -> Unit) {
    val cs = MaterialTheme.colorScheme
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        for (o in opts) {
            val on = o.key == selected
            Surface(
                onClick = { onSelect(o.key) }, shape = RoundedCornerShape(16.dp),
                color = if (on) cs.primaryContainer else cs.surface,
                border = BorderStroke(if (on) 1.5.dp else 1.dp, if (on) cs.primary else cs.outlineVariant),
                modifier = Modifier.fillMaxWidth().testTag("opt_${o.key}"),
            ) {
                Row(Modifier.padding(horizontal = 12.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    RadioButton(selected = on, onClick = null)
                    Column(Modifier.weight(1f)) {
                        Text(o.title, style = MaterialTheme.typography.titleSmall, color = cs.onSurface)
                        if (o.desc.isNotEmpty()) Text(o.desc, style = MaterialTheme.typography.bodySmall, color = cs.onSurfaceVariant)
                    }
                }
            }
        }
    }
}

/** Short choices that sit side by side and wrap to the next line when the screen is narrow. */
@Composable
private fun <T> Chips(opts: List<Pair<T, String>>, selected: T, onSelect: (T) -> Unit) {
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        for ((k, label) in opts) FilterChip(selected = selected == k, onClick = { onSelect(k) }, label = { Text(label) })
    }
}

private fun human(n: Long): String = when {
    n < 0 -> "?"
    n < 1024 * 1024 -> "${n / 1024} KB"
    else -> "%.1f MB".format(n / 1048576.0)
}

private const val PDF = "application/pdf"

/** One file or picture in a list that can be reordered by dragging. */
private class Entry(val id: Long, val uri: Uri)

private fun moveEntry(list: MutableList<Entry>, from: Any, to: Any) {
    val a = list.indexOfFirst { it.id == from }
    val b = list.indexOfFirst { it.id == to }
    if (a >= 0 && b >= 0 && a != b) list.add(b, list.removeAt(a))
}

@Composable
private fun FileRow(number: Int, uri: Uri, image: Boolean, onRemove: () -> Unit, modifier: Modifier) {
    val cs = MaterialTheme.colorScheme
    val ctx = LocalContext.current
    val name = remember(uri) { PdfOps.nameOf(ctx, uri) }
    val st = if (image) rememberImageThumb(uri, 160) else rememberPdfThumb(uri, 160)
    val thumb = st.value
    Surface(shape = RoundedCornerShape(16.dp), color = cs.surface, border = BorderStroke(1.dp, cs.outlineVariant), modifier = modifier.fillMaxWidth().testTag("file_row")) {
        Row(Modifier.padding(start = 10.dp, top = 8.dp, bottom = 8.dp, end = 2.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Icon(Icons.Filled.DragHandle, null, tint = cs.onSurfaceVariant)
            Box(Modifier.size(width = 40.dp, height = 52.dp).clip(RoundedCornerShape(6.dp)), contentAlignment = Alignment.Center) {
                if (thumb != null) Image(thumb.asImageBitmap(), null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
                else Icon(if (image) Icons.Filled.ImageIcon else Icons.Filled.PictureAsPdf, null, tint = cs.onSurfaceVariant)
            }
            Column(Modifier.weight(1f)) {
                Text(name, style = MaterialTheme.typography.titleSmall, color = cs.onSurface, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text("$number", style = MaterialTheme.typography.bodySmall, color = cs.onSurfaceVariant)
            }
            IconButton(onClick = onRemove) { Icon(Icons.Filled.Close, t("remove")) }
        }
    }
}

/** A list of files the person can drag into order, shared by "merge" and "pictures to PDF". */
@Composable
private fun ReorderList(files: MutableList<Entry>, image: Boolean, onAdd: () -> Unit, modifier: Modifier) {
    val listState = rememberLazyListState()
    val haptic = LocalHapticFeedback.current
    val drag = remember {
        DragReorder(
            rects = {
                val w = listState.layoutInfo.viewportSize.width.toFloat()
                listState.layoutInfo.visibleItemsInfo.filter { it.key is Long }.map { Triple(it.key, Offset(0f, it.offset.toFloat()), Size(w, it.size.toFloat())) }
            },
            onMove = { from, to -> moveEntry(files, from, to) },
            viewportHeight = { listState.layoutInfo.viewportSize.height.toFloat() },
            scrollBy = { listState.scrollBy(it) },
            buzz = { haptic.performHapticFeedback(HapticFeedbackType.LongPress) },
        )
    }
    DragAutoScroll(drag)
    LazyColumn(state = listState, modifier = modifier.reorderGestures(drag), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        itemsIndexed(files, key = { _, e -> e.id }) { i, e ->
            val look = if (drag.key == e.id) Modifier else Modifier.animateItem()
            FileRow(i + 1, e.uri, image, onRemove = { files.remove(e) }, modifier = look.dragLook(drag, e.id))
        }
        item(key = "add") {
            OutlinedButton(onClick = onAdd, modifier = Modifier.fillMaxWidth().testTag("pick_files")) {
                Icon(Icons.Filled.Add, null, Modifier.size(18.dp)); Spacer(Modifier.width(6.dp)); Text(t("add.more"))
            }
        }
    }
}

// ---------------------------------------------------------------- merge

@Composable
fun MergeScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    val seq = remember { AtomicLong() }
    val files = remember { mutableStateListOf<Entry>().also { l -> PendingFile.take()?.let { l.add(Entry(seq.getAndIncrement(), it)) } } }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { list ->
        list.forEach { Recents.add(ctx, it, PdfOps.nameOf(ctx, it)) }
        files.addAll(list.map { Entry(seq.getAndIncrement(), it) })
    }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        if (out != null) {
            val list = files.map { it.uri }
            job.run(scope, out) {
                (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use { PdfOps.merge(ctx, list, it) }
                t("saved")
            }
        }
    }
    ToolPage(t("merge"), onBack, scroll = false, bottom = {
        JobStatus(job)
        PrimaryButton(t("run.merge"), "run", files.size >= 2 && !job.busy) { save.launch("merged.pdf") }
    }) {
        if (files.isEmpty()) {
            Hint(t("merge.hint"))
            PickCard(false, "", Icons.Filled.PictureAsPdf, t("choose.pdfs"), t("pick.pdfs.hint"), tag = "pick_files") { pick.launch(arrayOf(PDF)) }
        } else {
            Hint(t("drag.hint"))
            ReorderList(files, image = false, onAdd = { pick.launch(arrayOf(PDF)) }, modifier = Modifier.weight(1f).fillMaxWidth())
        }
    }
}

// ---------------------------------------------------------------- split / extract

@Composable
fun SplitScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    var uri by remember { mutableStateOf<Uri?>(null) }
    var pages by remember { mutableStateOf(0) }
    var spec by remember { mutableStateOf("") }
    var mode by remember { mutableStateOf("one") }
    fun load(u: Uri) {
        uri = u; pages = 0; job.message = ""
        scope.launch { pages = withContext(Dispatchers.IO) { runCatching { PdfOps.pageCount(ctx, u) }.getOrDefault(0) } }
    }
    LaunchedEffect(Unit) { PendingFile.take()?.let { load(it) } }
    val pick = rememberPdfPicker { load(it) }
    val saveOne = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) job.run(scope, out) {
            val r = PdfOps.parseRanges(spec, pages).flatten()
            (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use { PdfOps.extract(ctx, src, r, it) }
            t("saved")
        }
    }
    val saveFolder = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) { dir ->
        val src = uri
        if (dir != null && src != null) job.run(scope) {
            val parts = if (mode == "all") (0 until pages).map { listOf(it) } else PdfOps.parseRanges(spec, pages)
            val n = PdfOps.splitToFolder(ctx, src, parts, dir)
            "$n ${t("files.saved")}"
        }
    }
    val ready = uri != null && pages > 0 && !job.busy && (mode == "all" || spec.isNotBlank())
    ToolPage(t("split"), onBack, bottom = {
        JobStatus(job)
        PrimaryButton(t(if (mode == "one") "run.save" else "run.folder"), "run", ready) {
            if (mode == "one") saveOne.launch("extract.pdf") else saveFolder.launch(null)
        }
    }) {
        PdfPick(uri, if (pages > 0) "$pages ${t("pages")}" else "") { pick.launch(arrayOf(PDF)) }
        Options(
            listOf(Opt("one", t("split.one"), t("split.one.d")), Opt("each", t("split.each"), t("split.each.d")), Opt("all", t("split.all"), t("split.all.d"))),
            mode,
        ) { mode = it }
        if (mode != "all") {
            OutlinedTextField(
                value = spec, onValueChange = { spec = it }, label = { Text(t("split.label")) }, supportingText = { Text(t("split.pages")) }, singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Text), modifier = Modifier.fillMaxWidth().testTag("pages_field"),
            )
        }
    }
}

// ---------------------------------------------------------------- organize

@Composable
fun OrganizeScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    var uri by remember { mutableStateOf<Uri?>(null) }
    var thumbs by remember { mutableStateOf<PdfOps.Thumbs?>(null) }
    val items = remember { mutableStateListOf<PageItem>() }
    DisposableEffect(Unit) { onDispose { thumbs?.close() } }
    fun load(u: Uri) {
        job.message = ""
        scope.launch {
            runCatching {
                withContext(Dispatchers.IO) { PdfOps.Thumbs(ctx, u) }
            }.onSuccess { th ->
                thumbs?.close()
                thumbs = th
                uri = u
                items.clear()
                items.addAll((0 until th.count).map { i -> PageItem(i) })
            }.onFailure { e -> job.ok = false; job.message = e.message ?: e.toString() }
        }
    }
    LaunchedEffect(Unit) { PendingFile.take()?.let { load(it) } }
    val pick = rememberPdfPicker { load(it) }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) {
            val list = items.toList()
            job.run(scope, out) {
                (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use { PdfOps.build(ctx, src, list, it) }
                t("saved")
            }
        }
    }
    val gridState = rememberLazyGridState()
    val haptic = LocalHapticFeedback.current
    val drag = remember {
        DragReorder(
            rects = {
                gridState.layoutInfo.visibleItemsInfo.map {
                    Triple(it.key, Offset(it.offset.x.toFloat(), it.offset.y.toFloat()), Size(it.size.width.toFloat(), it.size.height.toFloat()))
                }
            },
            onMove = { from, to ->
                val a = items.indexOfFirst { it.index == from }
                val b = items.indexOfFirst { it.index == to }
                if (a >= 0 && b >= 0 && a != b) items.add(b, items.removeAt(a))
            },
            viewportHeight = { gridState.layoutInfo.viewportSize.height.toFloat() },
            scrollBy = { gridState.scrollBy(it) },
            buzz = { haptic.performHapticFeedback(HapticFeedbackType.LongPress) },
        )
    }
    DragAutoScroll(drag)
    ToolPage(t("organize"), onBack, scroll = false, maxWidth = 1000.dp, bottom = {
        JobStatus(job)
        PrimaryButton(t("run.save"), "run", uri != null && items.isNotEmpty() && !job.busy) { save.launch("organized.pdf") }
    }) {
        val th = thumbs
        if (th == null) {
            Hint(t("org.hint"))
            PdfPick(null) { pick.launch(arrayOf(PDF)) }
        } else {
            PdfPick(uri, "${items.size} ${t("pages")}") { pick.launch(arrayOf(PDF)) }
            Hint(t("drag.pages"))
            LazyVerticalGrid(
                state = gridState, columns = GridCells.Adaptive(130.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp), verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.weight(1f).fillMaxWidth().reorderGestures(drag),
            ) {
                gridItemsIndexed(items, key = { _, it -> it.index }) { pos, item ->
                    val look = if (drag.key == item.index) Modifier else Modifier.animateItem()
                    PageCard(
                        th, item, pos + 1,
                        onTurn = { items[pos] = item.copy(turn = (item.turn + 90) % 360) },
                        onDelete = { items.removeAt(pos) },
                        modifier = look.dragLook(drag, item.index),
                    )
                }
            }
        }
    }
}

@Composable
private fun PageCard(thumbs: PdfOps.Thumbs, item: PageItem, number: Int, onTurn: () -> Unit, onDelete: () -> Unit, modifier: Modifier) {
    val cs = MaterialTheme.colorScheme
    val bmp by produceState<Bitmap?>(null, item.index) { value = withContext(Dispatchers.IO) { runCatching { thumbs.get(item.index, 260) }.getOrNull() } }
    Surface(shape = RoundedCornerShape(16.dp), color = cs.surface, border = BorderStroke(1.dp, cs.outlineVariant), modifier = modifier.testTag("page_card")) {
        Column(Modifier.padding(8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Box(Modifier.fillMaxWidth().aspectRatio(0.78f), contentAlignment = Alignment.Center) {
                val b = bmp
                if (b != null) {
                    Image(
                        b.asImageBitmap(), "page ${item.index + 1}", contentScale = ContentScale.Fit,
                        modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(8.dp)).graphicsLayer { rotationZ = item.turn.toFloat() },
                    )
                }
                Surface(shape = CircleShape, color = cs.primary, modifier = Modifier.align(Alignment.TopStart).padding(4.dp)) {
                    Text("$number", Modifier.padding(horizontal = 8.dp, vertical = 2.dp), color = cs.onPrimary, style = MaterialTheme.typography.labelMedium)
                }
            }
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                IconButton(onClick = onTurn, modifier = Modifier.size(36.dp)) { Icon(Icons.Filled.RotateRight, t("turn"), Modifier.size(20.dp)) }
                Icon(Icons.Filled.DragHandle, null, Modifier.size(20.dp), tint = cs.onSurfaceVariant)
                IconButton(onClick = onDelete, modifier = Modifier.size(36.dp)) { Icon(Icons.Filled.Delete, t("remove"), Modifier.size(20.dp)) }
            }
        }
    }
}

// ---------------------------------------------------------------- compress

@Composable
fun CompressScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    var uri by remember { mutableStateOf<Uri?>(PendingFile.take()) }
    var level by remember { mutableStateOf("medium") }
    val before by produceState(-1L, uri) { value = uri?.let { u -> withContext(Dispatchers.IO) { PdfOps.sizeOf(ctx, u) } } ?: -1L }
    val pick = rememberPdfPicker { uri = it; job.message = "" }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) job.run(scope, out) {
            val (dpi, q) = when (level) { "light" -> 150 to 0.75f; "strong" -> 80 to 0.5f; else -> 110 to 0.62f }
            (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use { PdfOps.compress(ctx, src, dpi, q, it) }
            val after = PdfOps.sizeOf(ctx, out)
            "${t("saved")}  ${t("size.before")}: ${human(before)}  →  ${t("size.after")}: ${human(after)}"
        }
    }
    ToolPage(t("compress"), onBack, bottom = {
        JobStatus(job)
        PrimaryButton(t("run.save"), "run", uri != null && !job.busy) { save.launch("compressed.pdf") }
    }) {
        PdfPick(uri, if (before >= 0) human(before) else "") { pick.launch(arrayOf(PDF)) }
        Label(t("level"))
        Options(
            listOf(Opt("light", t("lvl.light"), t("lvl.light.d")), Opt("medium", t("lvl.medium"), t("lvl.medium.d")), Opt("strong", t("lvl.strong"), t("lvl.strong.d"))),
            level,
        ) { level = it }
        Hint(t("compress.note"))
    }
}

// ---------------------------------------------------------------- pictures -> PDF

@Composable
fun PicturesToPdfScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    val seq = remember { AtomicLong() }
    val files = remember { mutableStateListOf<Entry>() }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { list -> files.addAll(list.map { Entry(seq.getAndIncrement(), it) }) }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        if (out != null) {
            val list = files.map { it.uri }
            job.run(scope, out) {
                (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use { PdfOps.picturesToPdf(ctx, list, it) }
                t("saved")
            }
        }
    }
    ToolPage(t("img2pdf"), onBack, scroll = false, bottom = {
        JobStatus(job)
        PrimaryButton(t("run.save"), "run", files.isNotEmpty() && !job.busy) { save.launch("pictures.pdf") }
    }) {
        if (files.isEmpty()) {
            PickCard(false, "", Icons.Filled.ImageIcon, t("choose.pics"), t("pick.pics.hint"), tag = "pick_files") { pick.launch(arrayOf("image/*")) }
        } else {
            Hint(t("drag.hint"))
            ReorderList(files, image = true, onAdd = { pick.launch(arrayOf("image/*")) }, modifier = Modifier.weight(1f).fillMaxWidth())
        }
    }
}

// ---------------------------------------------------------------- PDF -> pictures

@Composable
fun PdfToPicturesScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    var uri by remember { mutableStateOf<Uri?>(PendingFile.take()) }
    var png by remember { mutableStateOf(true) }
    val pick = rememberPdfPicker { uri = it; job.message = "" }
    val folder = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) { dir ->
        val src = uri
        if (dir != null && src != null) job.run(scope) { "${PdfOps.pdfToPictures(ctx, src, dir, png)} ${t("files.saved")}" }
    }
    ToolPage(t("pdf2img"), onBack, bottom = {
        JobStatus(job)
        PrimaryButton(t("run.folder"), "run", uri != null && !job.busy) { folder.launch(null) }
    }) {
        PdfPick(uri) { pick.launch(arrayOf(PDF)) }
        Label(t("format"))
        Chips(listOf(true to "PNG", false to "JPG"), png) { png = it }
    }
}

// ---------------------------------------------------------------- protect

@Composable
fun ProtectScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    var uri by remember { mutableStateOf<Uri?>(PendingFile.take()) }
    var add by remember { mutableStateOf(true) }
    var password by remember { mutableStateOf("") }
    val pick = rememberPdfPicker { uri = it; job.message = "" }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) job.run(scope, out) {
            (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use {
                if (add) PdfOps.protect(ctx, src, password, it) else PdfOps.unprotect(ctx, src, password, it)
            }
            t("saved")
        }
    }
    ToolPage(t("protect"), onBack, bottom = {
        JobStatus(job)
        PrimaryButton(t("run.save"), "run", uri != null && (password.isNotEmpty() || !add) && !job.busy) { save.launch(if (add) "protected.pdf" else "unprotected.pdf") }
    }) {
        PdfPick(uri) { pick.launch(arrayOf(PDF)) }
        Options(
            listOf(Opt("add", t("protect.add"), t("protect.add.d")), Opt("remove", t("protect.remove"), t("protect.remove.d"))),
            if (add) "add" else "remove",
        ) { add = it == "add" }
        OutlinedTextField(
            value = password, onValueChange = { password = it }, label = { Text(t("password")) }, singleLine = true,
            visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth().testTag("password_field"),
        )
    }
}

// ---------------------------------------------------------------- watermark

@Composable
fun WatermarkScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    var uri by remember { mutableStateOf<Uri?>(PendingFile.take()) }
    var text by remember { mutableStateOf("CONFIDENTIAL") }
    var opacity by remember { mutableStateOf(0.25f) }
    var size by remember { mutableStateOf(0.6f) }
    var diagonal by remember { mutableStateOf(true) }
    var color by remember { mutableStateOf("gray") }
    val pick = rememberPdfPicker { uri = it; job.message = "" }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) job.run(scope, out) {
            val argb = when (color) { "red" -> 0xFFD62828.toInt(); "blue" -> 0xFF1D4ED8.toInt(); "black" -> 0xFF000000.toInt(); else -> 0xFF6B7280.toInt() }
            (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use {
                PdfOps.watermark(ctx, src, text, opacity, size, if (diagonal) 45f else 0f, argb, it)
            }
            t("saved")
        }
    }
    ToolPage(t("watermark"), onBack, bottom = {
        JobStatus(job)
        PrimaryButton(t("run.save"), "run", uri != null && text.isNotBlank() && !job.busy) { save.launch("watermarked.pdf") }
    }) {
        PdfPick(uri) { pick.launch(arrayOf(PDF)) }
        OutlinedTextField(value = text, onValueChange = { text = it }, label = { Text(t("wm.text")) }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("wm_text"))
        Text("${t("wm.opacity")}: ${(opacity * 100).toInt()}%", color = MaterialTheme.colorScheme.onBackground)
        Slider(value = opacity, onValueChange = { opacity = it }, valueRange = 0.08f..0.8f)
        Text("${t("wm.size")}: ${(size * 100).toInt()}%", color = MaterialTheme.colorScheme.onBackground)
        Slider(value = size, onValueChange = { size = it }, valueRange = 0.25f..0.95f)
        Label(t("wm.angle"))
        Chips(listOf(true to t("wm.diag"), false to t("wm.flat")), diagonal) { diagonal = it }
        Label(t("wm.color"))
        Chips(listOf("gray" to t("col.gray"), "red" to t("col.red"), "blue" to t("col.blue"), "black" to t("col.black")), color) { color = it }
    }
}

// ---------------------------------------------------------------- page numbers

@Composable
fun NumbersScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    var uri by remember { mutableStateOf<Uri?>(PendingFile.take()) }
    var format by remember { mutableStateOf("n") }
    var top by remember { mutableStateOf(false) }
    var align by remember { mutableStateOf(1) }
    var start by remember { mutableStateOf("1") }
    val pick = rememberPdfPicker { uri = it; job.message = "" }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) job.run(scope, out) {
            (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use {
                PdfOps.numberPages(ctx, src, format, top, align, start.toIntOrNull() ?: 1, 11f, it)
            }
            t("saved")
        }
    }
    ToolPage(t("numbers"), onBack, bottom = {
        JobStatus(job)
        PrimaryButton(t("run.save"), "run", uri != null && !job.busy) { save.launch("numbered.pdf") }
    }) {
        PdfPick(uri) { pick.launch(arrayOf(PDF)) }
        Label(t("num.format"))
        Chips(listOf("n" to "1", "n/N" to "1 / 12", "page" to "Page 1 of 12"), format) { format = it }
        Label(t("num.pos"))
        Chips(listOf(false to t("num.bottom"), true to t("num.top")), top) { top = it }
        Chips(listOf(0 to t("num.left"), 1 to t("num.center"), 2 to t("num.right")), align) { align = it }
        OutlinedTextField(
            value = start, onValueChange = { start = it.filter(Char::isDigit).take(4) }, label = { Text(t("num.start")) }, singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.fillMaxWidth().testTag("start_field"),
        )
    }
}

// ---------------------------------------------------------------- books and documents -> PDF

@Composable
fun ConvertScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    var uri by remember { mutableStateOf<Uri?>(null) }
    var name by remember { mutableStateOf("") }
    val kind = DocConvert.kindOf(name)
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {
        if (it != null) { uri = it; name = PdfOps.nameOf(ctx, it); job.message = "" }
    }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) job.run(scope, out) {
            (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use { DocConvert.convert(ctx, src, name, it) }
            t("saved")
        }
    }
    ToolPage(t("docs2pdf"), onBack, bottom = {
        JobStatus(job)
        PrimaryButton(t("run.save"), "run", uri != null && kind != null && !job.busy) { save.launch(name.substringBeforeLast('.') + ".pdf") }
    }) {
        Hint(t("docs.hint"))
        PickCard(uri != null, name, Icons.Filled.AutoStories, t("choose.file"), t("pick.any.hint"), kind ?: "") { pick.launch(arrayOf("*/*")) }
        if (uri != null && kind == null) Text(t("unsupported"), color = MaterialTheme.colorScheme.error)
    }
}

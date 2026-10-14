package app.pdftoolkit.mobile

import android.content.Context
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
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowDownward
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.RotateRight
import androidx.compose.material.icons.filled.ArrowBack as ArrowLeft
import androidx.compose.material.icons.filled.ArrowForward as ArrowRight
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
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
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

// ---------------------------------------------------------------- shared pieces

/** Runs a piece of work off the main thread and keeps the message to show. */
class ToolJob {
    var busy by mutableStateOf(false)
    var message by mutableStateOf("")
    var ok by mutableStateOf(true)

    fun run(scope: CoroutineScope, work: () -> String) {
        busy = true
        message = ""
        scope.launch {
            try {
                message = withContext(Dispatchers.IO) { work() }
                ok = true
            } catch (e: Throwable) {
                message = e.message ?: e.toString()
                ok = false
            } finally {
                busy = false
            }
        }
    }
}

@Composable
private fun ToolPage(title: String, onBack: () -> Unit, scroll: Boolean = true, content: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.fillMaxSize().statusBarsPadding().navigationBarsPadding()) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack, modifier = Modifier.testTag("back")) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, t("back"), tint = MaterialTheme.colorScheme.onBackground)
            }
            Text(title, style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.onBackground)
        }
        val base = Modifier.fillMaxSize().padding(horizontal = 16.dp)
        Column(
            if (scroll) base.verticalScroll(rememberScrollState()).padding(bottom = 24.dp) else base,
            verticalArrangement = Arrangement.spacedBy(12.dp), content = content,
        )
    }
}

@Composable
private fun JobStatus(job: ToolJob) {
    val cs = MaterialTheme.colorScheme
    if (job.busy) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
            Text(t("working"), color = cs.onSurfaceVariant)
        }
    } else if (job.message.isNotEmpty()) {
        Text(job.message, color = if (job.ok) cs.primary else cs.error, modifier = Modifier.testTag(if (job.ok) "result_ok" else "result_error"))
    }
}

@Composable
private fun PrimaryButton(text: String, tag: String, enabled: Boolean, onClick: () -> Unit) {
    Button(onClick = onClick, enabled = enabled, modifier = Modifier.testTag(tag)) { Text(text) }
}

@Composable
private fun Hint(text: String) = Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)

@Composable
private fun FileLine(ctx: Context, uri: Uri?, extra: String = "") {
    val cs = MaterialTheme.colorScheme
    Surface(shape = RoundedCornerShape(12.dp), color = cs.surface, border = BorderStroke(1.dp, cs.outlineVariant), modifier = Modifier.fillMaxWidth()) {
        Text(
            if (uri == null) t("no.file") else PdfOps.nameOf(ctx, uri) + extra,
            modifier = Modifier.padding(14.dp).testTag("file_name"),
            color = if (uri == null) cs.onSurfaceVariant else cs.onSurface,
        )
    }
}

private fun human(n: Long): String = when {
    n < 0 -> "?"
    n < 1024 * 1024 -> "${n / 1024} KB"
    else -> "%.1f MB".format(n / 1048576.0)
}

private const val PDF = "application/pdf"

// ---------------------------------------------------------------- merge

@Composable
fun MergeScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    val files = remember { mutableStateListOf<Uri>() }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { files.addAll(it) }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        if (out != null) {
            val list = files.toList()
            job.run(scope) {
                (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use { PdfOps.merge(ctx, list, it) }
                t("saved")
            }
        }
    }
    ToolPage(t("merge"), onBack) {
        Hint(t("merge.hint"))
        OutlinedButton(onClick = { pick.launch(arrayOf(PDF)) }, modifier = Modifier.testTag("pick_files")) { Text(t("choose.pdfs")) }
        files.forEachIndexed { i, u ->
            Surface(shape = RoundedCornerShape(12.dp), color = MaterialTheme.colorScheme.surface, border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant), modifier = Modifier.fillMaxWidth()) {
                Row(Modifier.padding(start = 14.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("${i + 1}.  ${PdfOps.nameOf(ctx, u)}", Modifier.weight(1f), color = MaterialTheme.colorScheme.onSurface)
                    IconButton(onClick = { if (i > 0) files.add(i - 1, files.removeAt(i)) }) { Icon(Icons.Filled.ArrowUpward, t("up")) }
                    IconButton(onClick = { if (i < files.size - 1) files.add(i + 1, files.removeAt(i)) }) { Icon(Icons.Filled.ArrowDownward, t("down")) }
                    IconButton(onClick = { files.removeAt(i) }) { Icon(Icons.Filled.Close, t("remove")) }
                }
            }
        }
        PrimaryButton(t("run.merge"), "run", files.size >= 2 && !job.busy) { save.launch("merged.pdf") }
        JobStatus(job)
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
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {
        if (it != null) {
            uri = it; pages = 0; job.message = ""
            scope.launch { pages = withContext(Dispatchers.IO) { runCatching { PdfOps.pageCount(ctx, it) }.getOrDefault(0) } }
        }
    }
    val saveOne = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) job.run(scope) {
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
    ToolPage(t("split"), onBack) {
        OutlinedButton(onClick = { pick.launch(arrayOf(PDF)) }, modifier = Modifier.testTag("pick_file")) { Text(t(if (uri == null) "choose.pdf" else "change.file")) }
        FileLine(ctx, uri, if (pages > 0) "  ·  $pages ${t("pages")}" else "")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            for ((k, label) in listOf("one" to "split.one", "each" to "split.each", "all" to "split.all")) {
                FilterChip(selected = mode == k, onClick = { mode = k }, label = { Text(t(label)) })
            }
        }
        if (mode != "all") {
            OutlinedTextField(
                value = spec, onValueChange = { spec = it }, label = { Text(t("split.pages")) }, singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Text), modifier = Modifier.fillMaxWidth().testTag("pages_field"),
            )
        }
        val ready = uri != null && pages > 0 && !job.busy && (mode == "all" || spec.isNotBlank())
        PrimaryButton(t(if (mode == "one") "run.save" else "run.folder"), "run", ready) {
            if (mode == "one") saveOne.launch("extract.pdf") else saveFolder.launch(null)
        }
        JobStatus(job)
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
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {
        if (it != null) {
            job.message = ""
            scope.launch {
                runCatching {
                    withContext(Dispatchers.IO) { PdfOps.Thumbs(ctx, it) }
                }.onSuccess { th ->
                    thumbs?.close()
                    thumbs = th
                    uri = it
                    items.clear()
                    items.addAll((0 until th.count).map { i -> PageItem(i) })
                }.onFailure { e -> job.ok = false; job.message = e.message ?: e.toString() }
            }
        }
    }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) {
            val list = items.toList()
            job.run(scope) {
                (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use { PdfOps.build(ctx, src, list, it) }
                t("saved")
            }
        }
    }
    ToolPage(t("organize"), onBack, scroll = false) {
        Hint(t("org.hint"))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
            OutlinedButton(onClick = { pick.launch(arrayOf(PDF)) }, modifier = Modifier.testTag("pick_file")) { Text(t(if (uri == null) "choose.pdf" else "change.file")) }
            PrimaryButton(t("run.save"), "run", uri != null && items.isNotEmpty() && !job.busy) { save.launch("organized.pdf") }
        }
        JobStatus(job)
        val th = thumbs
        if (th != null) {
            LazyVerticalGrid(columns = GridCells.Adaptive(130.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.weight(1f)) {
                itemsIndexed(items, key = { _, it -> it.index }) { pos, item ->
                    PageCard(th, item, pos + 1,
                        onTurn = { items[pos] = item.copy(turn = (item.turn + 90) % 360) },
                        onDelete = { items.removeAt(pos) },
                        onLeft = { if (pos > 0) items.add(pos - 1, items.removeAt(pos)) },
                        onRight = { if (pos < items.size - 1) items.add(pos + 1, items.removeAt(pos)) })
                }
            }
        }
    }
}

@Composable
private fun PageCard(thumbs: PdfOps.Thumbs, item: PageItem, number: Int, onTurn: () -> Unit, onDelete: () -> Unit, onLeft: () -> Unit, onRight: () -> Unit) {
    val cs = MaterialTheme.colorScheme
    val bmp by produceState<Bitmap?>(null, item.index) { value = withContext(Dispatchers.IO) { runCatching { thumbs.get(item.index, 260) }.getOrNull() } }
    Surface(shape = RoundedCornerShape(12.dp), color = cs.surface, border = BorderStroke(1.dp, cs.outlineVariant), modifier = Modifier.testTag("page_card")) {
        Column(Modifier.padding(8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Box(Modifier.fillMaxWidth().size(150.dp), contentAlignment = Alignment.Center) {
                val b = bmp
                if (b != null) {
                    Image(
                        b.asImageBitmap(), null, contentScale = ContentScale.Fit,
                        modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(6.dp)).graphicsLayer { rotationZ = item.turn.toFloat() },
                    )
                }
            }
            Text("$number", style = MaterialTheme.typography.labelLarge, color = cs.onSurfaceVariant)
            Row {
                IconButton(onClick = onLeft, modifier = Modifier.size(34.dp)) { Icon(Icons.Filled.ArrowLeft, t("up"), Modifier.size(18.dp)) }
                IconButton(onClick = onTurn, modifier = Modifier.size(34.dp)) { Icon(Icons.Filled.RotateRight, t("turn"), Modifier.size(18.dp)) }
                IconButton(onClick = onDelete, modifier = Modifier.size(34.dp)) { Icon(Icons.Filled.Delete, t("remove"), Modifier.size(18.dp)) }
                IconButton(onClick = onRight, modifier = Modifier.size(34.dp)) { Icon(Icons.Filled.ArrowRight, t("down"), Modifier.size(18.dp)) }
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
    var uri by remember { mutableStateOf<Uri?>(null) }
    var level by remember { mutableStateOf("medium") }
    var before by remember { mutableStateOf(-1L) }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {
        if (it != null) { uri = it; before = PdfOps.sizeOf(ctx, it); job.message = "" }
    }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) job.run(scope) {
            val (dpi, q) = when (level) { "light" -> 150 to 0.75f; "strong" -> 80 to 0.5f; else -> 110 to 0.62f }
            (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use { PdfOps.compress(ctx, src, dpi, q, it) }
            val after = PdfOps.sizeOf(ctx, out)
            "${t("saved")}  ${t("size.before")}: ${human(before)}  →  ${t("size.after")}: ${human(after)}"
        }
    }
    ToolPage(t("compress"), onBack) {
        OutlinedButton(onClick = { pick.launch(arrayOf(PDF)) }, modifier = Modifier.testTag("pick_file")) { Text(t(if (uri == null) "choose.pdf" else "change.file")) }
        FileLine(ctx, uri, if (before >= 0) "  ·  ${human(before)}" else "")
        Text(t("level"), style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onBackground)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            for ((k, label) in listOf("light" to "lvl.light", "medium" to "lvl.medium", "strong" to "lvl.strong")) {
                FilterChip(selected = level == k, onClick = { level = k }, label = { Text(t(label)) })
            }
        }
        Hint(t("compress.note"))
        PrimaryButton(t("run.save"), "run", uri != null && !job.busy) { save.launch("compressed.pdf") }
        JobStatus(job)
    }
}

// ---------------------------------------------------------------- pictures -> PDF

@Composable
fun PicturesToPdfScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    val files = remember { mutableStateListOf<Uri>() }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { files.addAll(it) }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        if (out != null) {
            val list = files.toList()
            job.run(scope) {
                (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use { PdfOps.picturesToPdf(ctx, list, it) }
                t("saved")
            }
        }
    }
    ToolPage(t("img2pdf"), onBack) {
        OutlinedButton(onClick = { pick.launch(arrayOf("image/*")) }, modifier = Modifier.testTag("pick_files")) { Text(t("choose.pics")) }
        files.forEachIndexed { i, u ->
            Surface(shape = RoundedCornerShape(12.dp), color = MaterialTheme.colorScheme.surface, border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant), modifier = Modifier.fillMaxWidth()) {
                Row(Modifier.padding(start = 14.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("${i + 1}.  ${PdfOps.nameOf(ctx, u)}", Modifier.weight(1f), color = MaterialTheme.colorScheme.onSurface)
                    IconButton(onClick = { if (i > 0) files.add(i - 1, files.removeAt(i)) }) { Icon(Icons.Filled.ArrowUpward, t("up")) }
                    IconButton(onClick = { if (i < files.size - 1) files.add(i + 1, files.removeAt(i)) }) { Icon(Icons.Filled.ArrowDownward, t("down")) }
                    IconButton(onClick = { files.removeAt(i) }) { Icon(Icons.Filled.Close, t("remove")) }
                }
            }
        }
        PrimaryButton(t("run.save"), "run", files.isNotEmpty() && !job.busy) { save.launch("pictures.pdf") }
        JobStatus(job)
    }
}

// ---------------------------------------------------------------- PDF -> pictures

@Composable
fun PdfToPicturesScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    var uri by remember { mutableStateOf<Uri?>(null) }
    var png by remember { mutableStateOf(true) }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { if (it != null) { uri = it; job.message = "" } }
    val folder = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) { dir ->
        val src = uri
        if (dir != null && src != null) job.run(scope) { "${PdfOps.pdfToPictures(ctx, src, dir, png)} ${t("files.saved")}" }
    }
    ToolPage(t("pdf2img"), onBack) {
        OutlinedButton(onClick = { pick.launch(arrayOf(PDF)) }, modifier = Modifier.testTag("pick_file")) { Text(t(if (uri == null) "choose.pdf" else "change.file")) }
        FileLine(ctx, uri)
        Text(t("format"), style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onBackground)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(selected = png, onClick = { png = true }, label = { Text("PNG") })
            FilterChip(selected = !png, onClick = { png = false }, label = { Text("JPG") })
        }
        PrimaryButton(t("run.folder"), "run", uri != null && !job.busy) { folder.launch(null) }
        JobStatus(job)
    }
}

// ---------------------------------------------------------------- protect

@Composable
fun ProtectScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    var uri by remember { mutableStateOf<Uri?>(null) }
    var add by remember { mutableStateOf(true) }
    var password by remember { mutableStateOf("") }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { if (it != null) { uri = it; job.message = "" } }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) job.run(scope) {
            (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use {
                if (add) PdfOps.protect(ctx, src, password, it) else PdfOps.unprotect(ctx, src, password, it)
            }
            t("saved")
        }
    }
    ToolPage(t("protect"), onBack) {
        OutlinedButton(onClick = { pick.launch(arrayOf(PDF)) }, modifier = Modifier.testTag("pick_file")) { Text(t(if (uri == null) "choose.pdf" else "change.file")) }
        FileLine(ctx, uri)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(selected = add, onClick = { add = true }, label = { Text(t("protect.add")) })
            FilterChip(selected = !add, onClick = { add = false }, label = { Text(t("protect.remove")) })
        }
        OutlinedTextField(
            value = password, onValueChange = { password = it }, label = { Text(t("password")) }, singleLine = true,
            visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth().testTag("password_field"),
        )
        PrimaryButton(t("run.save"), "run", uri != null && (password.isNotEmpty() || !add) && !job.busy) { save.launch(if (add) "protected.pdf" else "unprotected.pdf") }
        JobStatus(job)
    }
}


// ---------------------------------------------------------------- watermark

@Composable
fun WatermarkScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    var uri by remember { mutableStateOf<Uri?>(null) }
    var text by remember { mutableStateOf("CONFIDENTIAL") }
    var opacity by remember { mutableStateOf(0.25f) }
    var size by remember { mutableStateOf(0.6f) }
    var diagonal by remember { mutableStateOf(true) }
    var color by remember { mutableStateOf("gray") }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { if (it != null) { uri = it; job.message = "" } }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) job.run(scope) {
            val argb = when (color) { "red" -> 0xFFD62828.toInt(); "blue" -> 0xFF1D4ED8.toInt(); "black" -> 0xFF000000.toInt(); else -> 0xFF6B7280.toInt() }
            (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use {
                PdfOps.watermark(ctx, src, text, opacity, size, if (diagonal) 45f else 0f, argb, it)
            }
            t("saved")
        }
    }
    ToolPage(t("watermark"), onBack) {
        OutlinedButton(onClick = { pick.launch(arrayOf(PDF)) }, modifier = Modifier.testTag("pick_file")) { Text(t(if (uri == null) "choose.pdf" else "change.file")) }
        FileLine(ctx, uri)
        OutlinedTextField(value = text, onValueChange = { text = it }, label = { Text(t("wm.text")) }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("wm_text"))
        Text("${t("wm.opacity")}: ${(opacity * 100).toInt()}%", color = MaterialTheme.colorScheme.onBackground)
        Slider(value = opacity, onValueChange = { opacity = it }, valueRange = 0.08f..0.8f)
        Text("${t("wm.size")}: ${(size * 100).toInt()}%", color = MaterialTheme.colorScheme.onBackground)
        Slider(value = size, onValueChange = { size = it }, valueRange = 0.25f..0.95f)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(selected = diagonal, onClick = { diagonal = true }, label = { Text(t("wm.diag")) })
            FilterChip(selected = !diagonal, onClick = { diagonal = false }, label = { Text(t("wm.flat")) })
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            for ((k, label) in listOf("gray" to "col.gray", "red" to "col.red", "blue" to "col.blue", "black" to "col.black")) {
                FilterChip(selected = color == k, onClick = { color = k }, label = { Text(t(label)) })
            }
        }
        PrimaryButton(t("run.save"), "run", uri != null && text.isNotBlank() && !job.busy) { save.launch("watermarked.pdf") }
        JobStatus(job)
    }
}

// ---------------------------------------------------------------- page numbers

@Composable
fun NumbersScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val job = remember { ToolJob() }
    var uri by remember { mutableStateOf<Uri?>(null) }
    var format by remember { mutableStateOf("n") }
    var top by remember { mutableStateOf(false) }
    var align by remember { mutableStateOf(1) }
    var start by remember { mutableStateOf("1") }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { if (it != null) { uri = it; job.message = "" } }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(PDF)) { out ->
        val src = uri
        if (out != null && src != null) job.run(scope) {
            (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use {
                PdfOps.numberPages(ctx, src, format, top, align, start.toIntOrNull() ?: 1, 11f, it)
            }
            t("saved")
        }
    }
    ToolPage(t("numbers"), onBack) {
        OutlinedButton(onClick = { pick.launch(arrayOf(PDF)) }, modifier = Modifier.testTag("pick_file")) { Text(t(if (uri == null) "choose.pdf" else "change.file")) }
        FileLine(ctx, uri)
        Text(t("num.format"), style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onBackground)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            for ((k, label) in listOf("n" to "1", "n/N" to "1 / 12", "page" to "Page 1 of 12")) {
                FilterChip(selected = format == k, onClick = { format = k }, label = { Text(label) })
            }
        }
        Text(t("num.pos"), style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onBackground)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(selected = !top, onClick = { top = false }, label = { Text(t("num.bottom")) })
            FilterChip(selected = top, onClick = { top = true }, label = { Text(t("num.top")) })
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            for ((k, label) in listOf(0 to "num.left", 1 to "num.center", 2 to "num.right")) {
                FilterChip(selected = align == k, onClick = { align = k }, label = { Text(t(label)) })
            }
        }
        OutlinedTextField(
            value = start, onValueChange = { start = it.filter(Char::isDigit).take(4) }, label = { Text(t("num.start")) }, singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.fillMaxWidth().testTag("start_field"),
        )
        PrimaryButton(t("run.save"), "run", uri != null && !job.busy) { save.launch("numbered.pdf") }
        JobStatus(job)
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
        if (out != null && src != null) job.run(scope) {
            (ctx.contentResolver.openOutputStream(out) ?: error("Cannot write")).use { DocConvert.convert(ctx, src, name, it) }
            t("saved")
        }
    }
    ToolPage(t("docs2pdf"), onBack) {
        Hint(t("docs.hint"))
        OutlinedButton(onClick = { pick.launch(arrayOf("*/*")) }, modifier = Modifier.testTag("pick_file")) { Text(t(if (uri == null) "choose.file" else "change.file")) }
        FileLine(ctx, uri, if (kind != null) "  ·  $kind" else "")
        if (uri != null && kind == null) Text(t("unsupported"), color = MaterialTheme.colorScheme.error)
        PrimaryButton(t("run.save"), "run", uri != null && kind != null && !job.busy) { save.launch(name.substringBeforeLast('.') + ".pdf") }
        JobStatus(job)
    }
}

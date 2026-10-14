package app.pdftoolkit.mobile

import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.Dispatchers
import androidx.compose.runtime.rememberCoroutineScope
import android.content.Intent
import android.graphics.Paint
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.Canvas
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.filled.Redo
import androidx.compose.material.icons.automirrored.filled.Undo
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.TextLayoutResult
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import java.io.File

@Composable
fun EditorScreen(vm: EditorViewModel, prefs: Prefs, onBack: () -> Unit) {
    val engine by TexEngine.status.collectAsState()
    var tab by remember { mutableIntStateOf(0) }
    var view by remember { mutableStateOf(ViewOptions(prefs.editorSize, prefs.lineNumbers, prefs.wrap, prefs.autoPairs, prefs.palette)) }
    vm.autoPairs = view.autoPairs
    LaunchedEffect(vm.pdfVersion) { if (vm.pdfVersion > 0 && vm.compileOk == true) tab = 1 }
    fun update(v: ViewOptions) {
        view = v
        prefs.editorSize = v.size; prefs.lineNumbers = v.lineNumbers; prefs.wrap = v.wrap; prefs.autoPairs = v.autoPairs; prefs.palette = v.palette
    }

    BoxWithConstraints(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background).statusBarsPadding().navigationBarsPadding()) {
        val wide = maxWidth >= 840.dp
        Column(Modifier.fillMaxSize()) {
            TopBar(vm, onBack, engine, view, ::update)
            if (vm.compiling) LinearProgressIndicator(progress = { vm.progress }, modifier = Modifier.fillMaxWidth().height(3.dp).testTag("compile_progress"))
            else HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
            FileTabs(vm)
            if (vm.findOpen) FindBar(vm)
            Box(Modifier.weight(1f).fillMaxWidth()) {
                if (wide) {
                    Row(Modifier.fillMaxSize()) {
                        Box(Modifier.weight(1f).fillMaxHeight()) { EditorPane(vm, view) }
                        Box(Modifier.width(1.dp).fillMaxHeight().background(MaterialTheme.colorScheme.outlineVariant))
                        Box(Modifier.weight(1f).fillMaxHeight()) { PdfPreview(vm.pdfFile, vm.pdfVersion) }
                    }
                } else if (tab == 0) EditorPane(vm, view) else PdfPreview(vm.pdfFile, vm.pdfVersion)
            }
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
            EditorBottomBar(vm, tab, { tab = it }, switch = !wide)
        }
    }
}

/** Edit / PDF switch, undo, redo and the compile button: always in thumb reach at the bottom. */
@Composable
private fun EditorBottomBar(vm: EditorViewModel, tab: Int, onTab: (Int) -> Unit, switch: Boolean) {
    val cs = MaterialTheme.colorScheme
    Surface(color = cs.surface) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            if (switch) {
                Row(Modifier.weight(1f).height(46.dp).clip(RoundedCornerShape(23.dp)).background(cs.surfaceContainerHighest).padding(3.dp)) {
                    for ((i, key) in listOf(0 to "editor", 1 to "preview")) {
                        Surface(
                            onClick = { onTab(i) }, shape = MaterialTheme.shapes.large,
                            color = if (tab == i) cs.primary else Color.Transparent,
                            modifier = Modifier.weight(1f).fillMaxHeight().testTag(if (i == 0) "tab_editor" else "tab_pdf"),
                        ) {
                            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                Text(t(key), color = if (tab == i) cs.onPrimary else cs.onSurfaceVariant, style = MaterialTheme.typography.labelLarge, maxLines = 1)
                            }
                        }
                    }
                }
            } else Box(Modifier.weight(1f))
            IconButton(onClick = { vm.undo() }, enabled = vm.canUndo, modifier = Modifier.testTag("undo")) {
                Icon(Icons.AutoMirrored.Filled.Undo, t("undo"), tint = cs.onSurface.copy(alpha = if (vm.canUndo) 1f else 0.3f))
            }
            IconButton(onClick = { vm.redo() }, enabled = vm.canRedo, modifier = Modifier.testTag("redo")) {
                Icon(Icons.AutoMirrored.Filled.Redo, t("redo"), tint = cs.onSurface.copy(alpha = if (vm.canRedo) 1f else 0.3f))
            }
            Surface(
                onClick = { vm.compile() }, enabled = !vm.compiling, shape = MaterialTheme.shapes.medium, color = cs.primary,
                modifier = Modifier.defaultMinSize(minWidth = 56.dp, minHeight = 48.dp).testTag("compile"),
            ) {
                Row(Modifier.padding(horizontal = if (switch) 16.dp else 20.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (vm.compiling) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp, color = cs.onPrimary)
                    else Icon(Icons.Filled.PlayArrow, t("compile"), Modifier.size(22.dp), tint = cs.onPrimary)
                    if (!switch) Text(t("compile"), color = cs.onPrimary, style = MaterialTheme.typography.labelLarge)
                }
            }
        }
    }
}

data class ViewOptions(val size: Int, val lineNumbers: Boolean, val wrap: Boolean, val autoPairs: Boolean, val palette: Boolean)

// ------------------------------------------------------------------------------------------------ top bar

@Composable
private fun TopBar(vm: EditorViewModel, onBack: () -> Unit, engine: String, view: ViewOptions, onView: (ViewOptions) -> Unit) {
    val ctx = LocalContext.current
    val cs = MaterialTheme.colorScheme
    var menu by remember { mutableStateOf(false) }
    var dialog by remember { mutableStateOf("") }
    var newName by remember { mutableStateOf("") }
    var snipLabel by remember { mutableStateOf("") }
    var snipText by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    var csv by remember { mutableStateOf<CsvData?>(null) }
    var doiText by remember { mutableStateOf("") }
    var doiBusy by remember { mutableStateOf(false) }
    var doiError by remember { mutableStateOf("") }
    var toast by remember { mutableStateOf("") }

    val savePdf = rememberSavePicker("application/pdf") { if (it != null) vm.savePdfTo(it) }
    val exportZip = rememberSavePicker("application/zip") { uri ->
        val p = vm.project
        if (uri != null && p != null) { vm.flush(); runCatching { ctx.contentResolver.openOutputStream(uri)?.use { vm.store.exportZip(p, it) } } }
    }
    val importFile = rememberAnyPicker { uri ->
        if (uri != null) runCatching {
            val bytes = ctx.contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: return@runCatching
            vm.importFile(displayName(ctx, uri), bytes)
        }
    }

    val csvPick = rememberAnyPicker { uri ->
        if (uri != null) scope.launch {
            val text = withContext(Dispatchers.IO) { runCatching { ctx.contentResolver.openInputStream(uri)?.use { String(it.readBytes().take(1_000_000).toByteArray(), Charsets.UTF_8) } }.getOrNull() }
            val d = text?.let { DataInsert.parse(it) }
            if (d == null || d.header.isEmpty()) toast = t("csv.bad") else csv = d
        }
    }
    val picPick = rememberAnyPicker { uri ->
        if (uri != null) scope.launch {
            val pic = withContext(Dispatchers.IO) { runCatching { PictureImport.prepare(ctx, uri) }.getOrNull() }
            if (pic == null) toast = t("picture.bad") else vm.addPicture(pic.name, pic.bytes)
        }
    }

    Surface(color = cs.surface) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = { vm.closeProject(); onBack() }, modifier = Modifier.testTag("back")) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, t("back"), tint = cs.onSurface)
            }
            Column(Modifier.weight(1f)) {
                Text(vm.project?.name ?: t("app.latex"), style = MaterialTheme.typography.titleMedium, color = cs.onSurface, maxLines = 1, overflow = TextOverflow.Ellipsis)
                val line = when {
                    vm.compiling -> t("compiling")
                    engine == "starting" -> t("engine.start")
                    vm.status.isNotEmpty() -> vm.status
                    else -> vm.current
                }
                Text(line, style = MaterialTheme.typography.bodySmall, color = cs.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            IconButton(onClick = { vm.findOpen = !vm.findOpen }, modifier = Modifier.testTag("find")) {
                Icon(Icons.Filled.Search, t("find"), tint = cs.onSurface)
            }
            Box {
                IconButton(onClick = { menu = true }, modifier = Modifier.testTag("more")) { Icon(Icons.Filled.MoreVert, null, tint = cs.onSurface) }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    @Composable
                    fun item(key: String, tag: String = key, action: () -> Unit) =
                        DropdownMenuItem(text = { Text(t(key)) }, onClick = { menu = false; action() }, modifier = Modifier.testTag("menu_$tag"))
                    item("comment") { vm.toggleComment() }
                    item("insert.tools", "tools") { dialog = "tools" }
                    if (vm.bibKeysList.isNotEmpty()) item("insert.citation") { dialog = "cite" }
                    item("new.file") { newName = ""; dialog = "newfile" }
                    item("import.file") { importFile.launch(arrayOf("*/*")) }
                    HorizontalDivider()
                    item(if (vm.meta.engine == "xetex") "engine.pdftex" else "engine.xetex", "engine") {
                        vm.setEngine(if (vm.meta.engine == "xetex") "pdftex" else "xetex")
                    }
                    item(if (vm.spellLang.isEmpty()) "spell.en" else if (vm.spellLang == "en") "spell.fa" else "spell.off", "spell") {
                        vm.applySpell(if (vm.spellLang.isEmpty()) "en" else if (vm.spellLang == "en") "fa" else "")
                    }
                    item("outline") { dialog = "outline" }
                    item("history") { dialog = "history" }
                    item("snippet.save", "snippet") {
                        val sel = vm.field.selection
                        snipText = if (sel.collapsed) "" else vm.field.text.substring(sel.min, sel.max)
                        snipLabel = ""
                        dialog = "snip"
                    }
                    item("view.options") { dialog = "view" }
                    HorizontalDivider()
                    item("share.pdf") { sharePdf(ctx, vm) }
                    item("save.pdf") { savePdf.launch((vm.project?.name ?: "document") + ".pdf") }
                    item("export.project") { exportZip.launch((vm.project?.name ?: "project") + ".zip") }
                }
            }
        }
    }

    when (dialog) {
        "tools" -> AlertDialog(
            onDismissRequest = { dialog = "" },
            title = { Text(t("insert.tools")) },
            text = {
                Column(Modifier.verticalScroll(rememberScrollState())) {
                    for ((tag, key, hint, action) in listOf(
                        listOf("tool_csv", "tool.csv", "tool.csv.d") to { csvPick.launch(arrayOf("text/csv")); dialog = "" },
                        listOf("tool_picture", "tool.picture", "tool.picture.d") to { picPick.launch(arrayOf("image/*")); dialog = "" },
                        listOf("tool_doi", "tool.doi", "tool.doi.d") to { doiText = ""; doiError = ""; dialog = "doi" },
                        listOf("tool_style", "tool.style", "tool.style.d") to { dialog = "bibstyle" },
                        listOf("tool_check", "tool.check", "tool.check.d") to { dialog = "check" },
                    ).map { (k, a) -> Quad(k[0], k[1], k[2], a) }) {
                        Column(Modifier.fillMaxWidth().clickable { action() }.padding(vertical = 10.dp).testTag(tag)) {
                            Text(t(key), color = cs.onSurface, style = MaterialTheme.typography.titleSmall)
                            Text(t(hint), color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                        }
                        HorizontalDivider(color = cs.outlineVariant)
                    }
                }
            },
            confirmButton = { TextButton(onClick = { dialog = "" }) { Text(t("cancel")) } },
        )
        "doi" -> AlertDialog(
            onDismissRequest = { if (!doiBusy) dialog = "" },
            title = { Text(t("tool.doi")) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(doiText, { doiText = it; doiError = "" }, label = { Text("DOI") }, placeholder = { Text("10.1000/xyz123") }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("doi_field"))
                    Text(t("doi.online"), color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                    if (doiBusy) LinearProgressIndicator(Modifier.fillMaxWidth())
                    if (doiError.isNotEmpty()) Text(doiError, color = cs.error, style = MaterialTheme.typography.bodySmall)
                }
            },
            confirmButton = {
                TextButton(
                    enabled = !doiBusy && doiText.isNotBlank(),
                    onClick = {
                        val doi = Doi.clean(doiText)
                        if (doi == null) { doiError = t("doi.bad"); return@TextButton }
                        scope.launch {
                            doiBusy = true
                            val r = withContext(Dispatchers.IO) { Doi.fetch(doi) }
                            doiBusy = false
                            r.onSuccess { vm.addBibEntry(it); dialog = "" }.onFailure { doiError = t("doi.fail") }
                        }
                    },
                    modifier = Modifier.testTag("doi_add"),
                ) { Text(t("doi.add")) }
            },
            dismissButton = { TextButton(onClick = { dialog = "" }, enabled = !doiBusy) { Text(t("cancel")) } },
        )
        "bibstyle" -> AlertDialog(
            onDismissRequest = { dialog = "" },
            title = { Text(t("tool.style")) },
            text = {
                Column {
                    Text(t("style.hint"), color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                    for ((id, label) in listOf("plain" to "style.plain", "unsrt" to "style.unsrt", "alpha" to "style.alpha", "abbrv" to "style.abbrv", "IEEEtran" to "style.ieee")) {
                        Text(t(label), Modifier.fillMaxWidth().clickable { vm.setBibStyle(id); dialog = "" }.padding(vertical = 12.dp).testTag("style_$id"), color = cs.onSurface)
                    }
                }
            },
            confirmButton = { TextButton(onClick = { dialog = "" }) { Text(t("cancel")) } },
        )
        "check" -> {
            val issues = remember { vm.runCheck() }
            AlertDialog(
                onDismissRequest = { dialog = "" },
                title = { Text(t("tool.check")) },
                text = {
                    Column(Modifier.heightIn(max = 420.dp).verticalScroll(rememberScrollState()).testTag("check_list")) {
                        Text(if (issues.isEmpty()) t("check.none") else "${issues.size} ${t("check.found")}", Modifier.testTag("check_summary"), color = if (issues.isEmpty()) cs.primary else cs.onSurface, style = MaterialTheme.typography.titleSmall)
                        for ((i, iss) in issues.withIndex()) {
                            Column(Modifier.fillMaxWidth().clickable { vm.goTo(iss.file, iss.line); dialog = "" }.padding(vertical = 9.dp).testTag("check_row_$i")) {
                                Text(t(iss.kind), color = cs.onSurface, style = MaterialTheme.typography.bodyMedium)
                                Text(iss.detail + (iss.file?.let { f -> "  ·  $f" + (iss.line?.let { l -> ":$l" } ?: "") } ?: ""), color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodySmall, fontFamily = FontFamily.Monospace)
                            }
                            HorizontalDivider(color = cs.outlineVariant)
                        }
                    }
                },
                confirmButton = { TextButton(onClick = { dialog = "" }) { Text(t("ok.button")) } },
            )
        }
        "outline" -> {
            val items = vm.outline()
            val pages = remember(vm.pdfVersion) {
                vm.pdfFile?.let { f ->
                    runCatching {
                        android.os.ParcelFileDescriptor.open(f, android.os.ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
                            android.graphics.pdf.PdfRenderer(fd).use { it.pageCount }
                        }
                    }.getOrNull()
                }
            }
            AlertDialog(
                onDismissRequest = { dialog = "" },
                title = { Text(t("outline")) },
                text = {
                    Column(Modifier.heightIn(max = 420.dp).verticalScroll(rememberScrollState())) {
                        Column(Modifier.testTag("outline_stats"), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text("${vm.countWords(vm.field.text)} ${t("words")}  ·  ${vm.current}", color = cs.onSurface, style = MaterialTheme.typography.bodyMedium)
                            Text("${t("words.all")}: ${vm.wordsAll()}", color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                            if (pages != null) Text("${t("pdf.pages")}: $pages", color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                        }
                        HorizontalDivider(Modifier.padding(vertical = 10.dp), color = cs.outlineVariant)
                        if (items.isEmpty()) Text(t("outline.none"), color = cs.onSurfaceVariant)
                        for ((i, o) in items.withIndex()) {
                            Text(
                                o.title.ifEmpty { "·" }, color = cs.onSurface, maxLines = 2, overflow = TextOverflow.Ellipsis,
                                style = if (o.level == 0) MaterialTheme.typography.titleSmall else MaterialTheme.typography.bodyMedium,
                                modifier = Modifier.fillMaxWidth().clickable { vm.goToLine(o.line); dialog = "" }
                                    .padding(start = (o.level * 16).dp, top = 9.dp, bottom = 9.dp).testTag("outline_item_$i"),
                            )
                        }
                    }
                },
                confirmButton = { TextButton(onClick = { dialog = "" }) { Text(t("ok.button")) } },
            )
        }
        "history" -> {
            val versions = remember { vm.versions() }
            val fmt = remember { java.text.DateFormat.getDateTimeInstance(java.text.DateFormat.MEDIUM, java.text.DateFormat.SHORT) }
            AlertDialog(
                onDismissRequest = { dialog = "" },
                title = { Text(t("history")) },
                text = {
                    Column(Modifier.heightIn(max = 420.dp).verticalScroll(rememberScrollState()).testTag("history_list")) {
                        Text(if (versions.isEmpty()) t("history.none") else t("history.restore"), color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                        for ((i, v) in versions.withIndex()) {
                            val lines = remember(v) { runCatching { vm.history.read(v).lines().size }.getOrDefault(0) }
                            Column(
                                Modifier.fillMaxWidth().clickable { vm.restore(v); dialog = "" }.padding(vertical = 10.dp).testTag("history_row_$i"),
                            ) {
                                Text(fmt.format(java.util.Date(v.time)), color = cs.onSurface, style = MaterialTheme.typography.bodyMedium)
                                Text("$lines ${t("lines")}", color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                            }
                            HorizontalDivider(color = cs.outlineVariant)
                        }
                    }
                },
                confirmButton = { TextButton(onClick = { dialog = "" }) { Text(t("ok.button")) } },
            )
        }
        "snip" -> AlertDialog(
            onDismissRequest = { dialog = "" },
            title = { Text(t("snippet.save")) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(snipLabel, { snipLabel = it }, label = { Text(t("snippet.label")) }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("snippet_label"))
                    OutlinedTextField(
                        snipText, { snipText = it }, label = { Text(t("snippet.text")) }, minLines = 3, maxLines = 6,
                        textStyle = TextStyle(fontFamily = FontFamily.Monospace), modifier = Modifier.fillMaxWidth().testTag("snippet_text"),
                    )
                }
            },
            confirmButton = { TextButton(onClick = { vm.addSnippet(snipLabel, snipText); dialog = "" }, modifier = Modifier.testTag("snippet_save")) { Text(t("ok.button")) } },
            dismissButton = { TextButton(onClick = { dialog = "" }) { Text(t("cancel")) } },
        )
        "newfile" -> AlertDialog(
            onDismissRequest = { dialog = "" },
            title = { Text(t("new.file")) },
            text = { OutlinedTextField(newName, { newName = it }, label = { Text(t("file.name")) }, placeholder = { Text("chapter1.tex") }, singleLine = true, modifier = Modifier.testTag("file_name_field")) },
            confirmButton = { TextButton(onClick = { vm.newFile(if ('.' in newName) newName else "$newName.tex"); dialog = "" }, modifier = Modifier.testTag("create_file")) { Text(t("create")) } },
            dismissButton = { TextButton(onClick = { dialog = "" }) { Text(t("cancel")) } },
        )
        "cite" -> AlertDialog(
            onDismissRequest = { dialog = "" },
            title = { Text(t("insert.citation")) },
            text = {
                Column(Modifier.heightIn(max = 320.dp).verticalScroll(rememberScrollState())) {
                    for (k in vm.bibKeysList) {
                        Text(k, Modifier.fillMaxWidth().clickable { vm.insert("\\cite{$k}"); dialog = "" }.padding(vertical = 12.dp), color = cs.onSurface, fontFamily = FontFamily.Monospace)
                    }
                }
            },
            confirmButton = { TextButton(onClick = { dialog = "" }) { Text(t("cancel")) } },
        )
        "view" -> AlertDialog(
            onDismissRequest = { dialog = "" },
            title = { Text(t("view.options")) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("${t("font.size")}: ${view.size}", Modifier.weight(1f), color = cs.onSurface)
                        TextButton(onClick = { onView(view.copy(size = (view.size - 1).coerceAtLeast(10))) }) { Text("A−") }
                        TextButton(onClick = { onView(view.copy(size = (view.size + 1).coerceAtMost(26))) }) { Text("A+") }
                    }
                    for ((label, on, set) in listOf(
                        Triple(t("line.numbers"), view.lineNumbers, { v: Boolean -> onView(view.copy(lineNumbers = v)) }),
                        Triple(t("wrap"), view.wrap, { v: Boolean -> onView(view.copy(wrap = v)) }),
                        Triple(t("auto.pairs"), view.autoPairs, { v: Boolean -> onView(view.copy(autoPairs = v)) }),
                        Triple(t("palette"), view.palette, { v: Boolean -> onView(view.copy(palette = v)) }),
                    )) {
                        Row(Modifier.fillMaxWidth().clickable { set(!on) }, verticalAlignment = Alignment.CenterVertically) {
                            Checkbox(checked = on, onCheckedChange = { set(it) })
                            Text(label, color = cs.onSurface)
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { dialog = "" }) { Text(t("ok.button")) } },
        )
    }
    csv?.let { d ->
        DataDialog(
            d,
            onInsert = { code, plot ->
                if (plot) { vm.ensurePackage("pgfplots", "\\usepackage{pgfplots}\n\\pgfplotsset{compat=1.17}") } else vm.ensurePackage("booktabs")
                vm.insert(code)
                csv = null
            },
            onDismiss = { csv = null },
        )
    }
    if (toast.isNotEmpty()) {
        AlertDialog(onDismissRequest = { toast = "" }, text = { Text(toast) }, confirmButton = { TextButton(onClick = { toast = "" }) { Text(t("ok.button")) } })
    }
}

private data class Quad(val a: String, val b: String, val c: String, val d: () -> Unit)

private fun sharePdf(ctx: android.content.Context, vm: EditorViewModel) {
    val f = vm.pdfFile ?: return
    val dir = File(ctx.cacheDir, "share").also { it.mkdirs() }
    val copy = File(dir, (vm.project?.name ?: "document").replace(Regex("[^A-Za-z0-9._-]"), "_") + ".pdf")
    f.copyTo(copy, overwrite = true)
    val uri = FileProvider.getUriForFile(ctx, ctx.packageName + ".files", copy)
    val send = Intent(Intent.ACTION_SEND).apply {
        type = "application/pdf"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    ctx.startActivity(Intent.createChooser(send, null).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
}

// ------------------------------------------------------------------------------------------------ file tabs

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun FileTabs(vm: EditorViewModel) {
    val cs = MaterialTheme.colorScheme
    var menuFor by remember { mutableStateOf<String?>(null) }
    var renaming by remember { mutableStateOf<String?>(null) }
    var newName by remember { mutableStateOf("") }
    Row(Modifier.fillMaxWidth().background(cs.surface).horizontalScroll(rememberScrollState()).padding(horizontal = 8.dp, vertical = 6.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
        for (f in vm.files) {
            val selected = f == vm.current
            Box {
                Surface(
                    shape = RoundedCornerShape(10.dp), color = if (selected) cs.primary.copy(alpha = 0.16f) else cs.surfaceVariant,
                    border = BorderStroke(1.dp, if (selected) cs.primary else cs.outlineVariant),
                    modifier = Modifier.testTag("file_$f").combinedClickable(
                        onClick = { if (isTextFile(f)) vm.openFile(f) },
                        onLongClick = { menuFor = f },
                    ),
                ) {
                    Text(
                        (if (f == vm.meta.main) "★ " else "") + f, Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        color = if (selected) cs.primary else cs.onSurface, style = MaterialTheme.typography.labelLarge, maxLines = 1,
                    )
                }
                DropdownMenu(expanded = menuFor == f, onDismissRequest = { menuFor = null }) {
                    if (isTextFile(f) && f.endsWith(".tex")) DropdownMenuItem(text = { Text(t("set.main")) }, onClick = { vm.setMain(f); menuFor = null })
                    DropdownMenuItem(text = { Text(t("rename")) }, onClick = { menuFor = null; renaming = f; newName = f })
                    if (f != vm.meta.main) DropdownMenuItem(text = { Text(t("delete"), color = cs.error) }, onClick = { vm.deleteFile(f); menuFor = null })
                }
            }
        }
    }
    renaming?.let { f ->
        AlertDialog(
            onDismissRequest = { renaming = null },
            title = { Text(t("rename")) },
            text = { OutlinedTextField(newName, { newName = it }, singleLine = true) },
            confirmButton = { TextButton(onClick = { vm.renameFile(f, newName); renaming = null }) { Text(t("ok.button")) } },
            dismissButton = { TextButton(onClick = { renaming = null }) { Text(t("cancel")) } },
        )
    }
    HorizontalDivider(color = cs.outlineVariant)
}

// ------------------------------------------------------------------------------------------------ find and replace

@Composable
private fun FindBar(vm: EditorViewModel) {
    val cs = MaterialTheme.colorScheme
    val count = vm.matches().size
    Column(Modifier.fillMaxWidth().background(cs.surface).padding(horizontal = 8.dp, vertical = 6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            OutlinedTextField(
                vm.findText, { vm.findText = it; vm.matchIndex = 0 }, singleLine = true, placeholder = { Text(t("find")) },
                modifier = Modifier.weight(1f).testTag("find_field"),
            )
            Text(if (vm.findText.isEmpty()) "" else if (count == 0) "0" else "${vm.matchIndex.coerceIn(0, count - 1) + 1}/$count", color = cs.onSurfaceVariant, style = MaterialTheme.typography.labelLarge)
            IconButton(onClick = { vm.findStep(-1) }, modifier = Modifier.testTag("find_prev")) { Icon(Icons.Filled.KeyboardArrowUp, null, tint = cs.onSurface) }
            IconButton(onClick = { vm.findStep(1) }, modifier = Modifier.testTag("find_next")) { Icon(Icons.Filled.KeyboardArrowDown, null, tint = cs.onSurface) }
            IconButton(onClick = { vm.findOpen = false }) { Icon(Icons.Filled.Close, null, tint = cs.onSurface) }
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            OutlinedTextField(vm.replaceText, { vm.replaceText = it }, singleLine = true, placeholder = { Text(t("replace")) }, modifier = Modifier.weight(1f).testTag("replace_field"))
            TextButton(onClick = { vm.replaceOne() }, modifier = Modifier.testTag("replace_one")) { Text(t("replace")) }
            TextButton(onClick = { vm.replaceAll() }, modifier = Modifier.testTag("replace_all")) { Text(t("replace.all")) }
        }
        Row(Modifier.clickable { vm.matchCase = !vm.matchCase }, verticalAlignment = Alignment.CenterVertically) {
            Checkbox(checked = vm.matchCase, onCheckedChange = { vm.matchCase = it })
            Text(t("match.case"), color = cs.onSurface, style = MaterialTheme.typography.bodyMedium)
        }
    }
    HorizontalDivider(color = cs.outlineVariant)
}

// ------------------------------------------------------------------------------------------------ editor

@Composable
private fun EditorPane(vm: EditorViewModel, view: ViewOptions) {
    val cs = MaterialTheme.colorScheme
    var showLog by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize()) {
        if (view.palette) SymbolBar(vm)
        Box(Modifier.weight(1f).fillMaxWidth()) { CodeEditor(vm, view) }
        HorizontalDivider(color = cs.outlineVariant)
        val summary = when (vm.compileOk) {
            true -> t("ok")
            false -> "${t("failed")} · ${vm.errors.size} ${t("errors")}"
            null -> ""
        }
        val sel = vm.field.selection.end.coerceIn(0, vm.field.text.length)
        val before = vm.field.text.substring(0, sel)
        val pos = "Ln ${before.count { it == '\n' } + 1}, Col ${sel - (before.lastIndexOf('\n') + 1) + 1}"
        Row(Modifier.fillMaxWidth().background(cs.surface).clickable { showLog = !showLog }.padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            if (vm.spellMissing) Text(t("spell.missing") + "   ", color = cs.error, style = MaterialTheme.typography.labelMedium)
            Text(summary.ifEmpty { pos }, Modifier.weight(1f).testTag(when (vm.compileOk) { false -> "compile_failed"; true -> "compile_ok"; null -> "status_line" }),
                color = if (vm.compileOk == false) cs.error else cs.onSurface, style = MaterialTheme.typography.bodyMedium)
            if (summary.isNotEmpty()) Text(pos + "   ", color = cs.onSurfaceVariant, style = MaterialTheme.typography.labelMedium)
            if (vm.log.isNotEmpty()) {
                Text(t("log"), color = cs.onSurfaceVariant, style = MaterialTheme.typography.labelMedium)
                Icon(if (showLog) Icons.Filled.ExpandMore else Icons.Filled.ExpandLess, null, tint = cs.onSurfaceVariant)
            }
        }
        if (showLog || (vm.compileOk == false && vm.errors.isNotEmpty())) {
            Column(Modifier.fillMaxWidth().heightIn(max = 200.dp).background(cs.surfaceVariant).verticalScroll(rememberScrollState()).padding(10.dp)) {
                for (e in vm.errors) {
                    Text(
                        (e.file?.let { "$it " } ?: "") + (e.line?.let { "l.$it  " } ?: "") + e.message, color = cs.error, fontFamily = FontFamily.Monospace, fontSize = 13.sp,
                        modifier = Modifier.fillMaxWidth().clickable { vm.goToError(e) }.padding(vertical = 3.dp),
                    )
                }
                if (showLog) Text(vm.log.takeLast(6000), color = cs.onSurfaceVariant, fontFamily = FontFamily.Monospace, fontSize = 11.sp)
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun SymbolBar(vm: EditorViewModel) {
    val cs = MaterialTheme.colorScheme
    var group by remember { mutableIntStateOf(0) }
    var deleting by remember { mutableIntStateOf(-1) }
    val groups = SYMBOL_GROUPS + ("sym.mine" to vm.snippets)
    val mine = group == groups.size - 1
    Column(Modifier.fillMaxWidth().background(cs.surface)) {
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 6.dp, vertical = 4.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            for ((i, g) in groups.withIndex()) {
                Surface(
                    onClick = { group = i }, shape = MaterialTheme.shapes.medium,
                    color = if (group == i) cs.primary else cs.surfaceVariant, modifier = Modifier.testTag("group_$i"),
                ) {
                    Text(t(g.first), Modifier.padding(horizontal = 12.dp, vertical = 5.dp), color = if (group == i) cs.onPrimary else cs.onSurface, style = MaterialTheme.typography.labelMedium)
                }
            }
            Box(Modifier.width(8.dp))
            QuickKey("⇥") { vm.insert("  ") }
            QuickKey("%") { vm.toggleComment() }
            Surface(onClick = { vm.moveCaret(-1) }, shape = RoundedCornerShape(8.dp), color = cs.surfaceVariant) { Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, null, Modifier.padding(4.dp).size(22.dp), tint = cs.onSurface) }
            Surface(onClick = { vm.moveCaret(1) }, shape = RoundedCornerShape(8.dp), color = cs.surfaceVariant) { Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, null, Modifier.padding(4.dp).size(22.dp), tint = cs.onSurface) }
        }
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 6.dp, vertical = 4.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            if (mine && vm.snippets.isEmpty()) {
                Text(t("snippet.empty"), Modifier.padding(horizontal = 6.dp, vertical = 6.dp), color = cs.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
            }
            for ((idx, pair) in groups[group].second.withIndex()) {
                val (label, snippet) = pair
                val chip: @Composable () -> Unit = {
                    Text(label, Modifier.padding(horizontal = 10.dp, vertical = 6.dp), color = cs.onSurface, fontFamily = FontFamily.Monospace, fontSize = 14.sp, maxLines = 1)
                }
                if (mine) {
                    Surface(
                        shape = RoundedCornerShape(8.dp), color = cs.surfaceVariant, border = cardStroke(),
                        modifier = Modifier.testTag("snippet_$idx").combinedClickable(onClick = { vm.insert(snippet) }, onLongClick = { deleting = idx }),
                        content = chip,
                    )
                } else {
                    Surface(onClick = { vm.insert(snippet) }, shape = RoundedCornerShape(8.dp), color = cs.surfaceVariant, border = cardStroke(), content = chip)
                }
            }
        }
        HorizontalDivider(color = cs.outlineVariant)
    }
    if (deleting >= 0) {
        AlertDialog(
            onDismissRequest = { deleting = -1 },
            title = { Text(t("snippet.delete")) },
            text = { Text(vm.snippets.getOrNull(deleting)?.first ?: "") },
            confirmButton = { TextButton(onClick = { vm.removeSnippet(deleting); deleting = -1 }) { Text(t("delete"), color = cs.error) } },
            dismissButton = { TextButton(onClick = { deleting = -1 }) { Text(t("cancel")) } },
        )
    }
}

@Composable
private fun QuickKey(label: String, onClick: () -> Unit) {
    val cs = MaterialTheme.colorScheme
    Surface(onClick = onClick, shape = RoundedCornerShape(8.dp), color = cs.surfaceVariant) {
        Text(label, Modifier.padding(horizontal = 12.dp, vertical = 4.dp), color = cs.onSurface, fontFamily = FontFamily.Monospace, fontSize = 16.sp)
    }
}

@Composable
private fun CodeEditor(vm: EditorViewModel, view: ViewOptions) {
    val cs = MaterialTheme.colorScheme
    val dark = cs.background.red + cs.background.green + cs.background.blue < 1.5f
    val density = LocalDensity.current
    val matches = if (vm.findOpen) vm.matches() else emptyList()
    val misspelled = vm.misspelled
    val hl = remember(cs.primary, dark, cs.onSurfaceVariant, matches, vm.findText, vm.matchIndex, misspelled) {
        LatexHighlighter(
            command = cs.primary,
            math = if (dark) Color(0xFF7DD3C0) else Color(0xFF0F766E),
            comment = cs.onSurfaceVariant,
            env = if (dark) Color(0xFFF0A26B) else Color(0xFFB4532A),
            matches = matches, matchLen = vm.findText.length, currentMatch = vm.matchIndex,
            matchBg = if (dark) Color(0x66FFD54F) else Color(0x88FFEB3B), currentBg = if (dark) Color(0xCCFF9800) else Color(0xFFFFB74D),
            misspelled = misspelled, spellColor = cs.error,
        )
    }
    var layout by remember { mutableStateOf<TextLayoutResult?>(null) }
    val vScroll = rememberScrollState()
    val hScroll = rememberScrollState()
    val text = vm.field.text
    val starts = remember(text) { lineStarts(text) }
    val errorLines = remember(vm.errors, vm.current) { vm.errors.filter { it.file == null || it.file == vm.current }.mapNotNull { it.line }.toSet() }
    val lineHeightSp = view.size * 1.45f
    val numberPaint = remember(view.size, cs.onSurfaceVariant) {
        Paint(Paint.ANTI_ALIAS_FLAG).apply { textSize = with(density) { (view.size * 0.82f).sp.toPx() }; textAlign = Paint.Align.RIGHT; typeface = android.graphics.Typeface.MONOSPACE }
    }
    val gutterDp = if (view.lineNumbers) (String.format("%d", starts.size).length.coerceAtLeast(2) * view.size * 0.62f + 18f).dp else 0.dp

    // keep the current search match in view
    LaunchedEffect(vm.matchIndex, vm.findOpen, vm.findText) {
        val l = layout
        if (vm.findOpen && l != null && matches.isNotEmpty()) {
            val at = matches[vm.matchIndex.coerceIn(0, matches.size - 1)].coerceAtMost((l.layoutInput.text.length - 1).coerceAtLeast(0))
            val y = l.getLineTop(l.getLineForOffset(at)).toInt()
            vScroll.animateScrollTo((y - 200).coerceAtLeast(0))
        }
    }

    BoxWithConstraints(Modifier.fillMaxSize()) {
        val minHeight = maxHeight
        Row(Modifier.fillMaxSize().verticalScroll(vScroll)) {
            if (view.lineNumbers) {
                val l = layout
                val h = with(density) { (l?.size?.height ?: 0).toDp() }
                val cur = vm.field.selection.end.coerceIn(0, text.length)
                Canvas(Modifier.width(gutterDp).height(maxOf(h, minHeight)).background(cs.surface.copy(alpha = 0.6f))) {
                    if (l != null) {
                        val nc = drawContext.canvas.nativeCanvas
                        val curLine = starts.indexOfLast { it <= cur }
                        for (i in starts.indices) {
                            val s = starts[i].coerceAtMost(l.layoutInput.text.length)
                            val vLine = l.getLineForOffset(s)
                            if (vLine >= l.lineCount) continue
                            numberPaint.color = when {
                                (i + 1) in errorLines -> cs.error.toArgb()
                                i == curLine -> cs.primary.toArgb()
                                else -> cs.onSurfaceVariant.copy(alpha = 0.7f).toArgb()
                            }
                            nc.drawText("${i + 1}", size.width - 8.dp.toPx(), l.getLineBaseline(vLine), numberPaint)
                        }
                    }
                }
            }
            Box(Modifier.weight(1f).then(if (view.wrap) Modifier else Modifier.horizontalScroll(hScroll)).padding(start = 8.dp, end = 8.dp, top = 6.dp)) {
                androidx.compose.runtime.CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
                    val sel = vm.field.selection.end
                    val curColor = cs.primary.copy(alpha = if (dark) 0.10f else 0.07f)
                    BasicTextField(
                        value = vm.field,
                        onValueChange = { vm.onType(it) },
                        modifier = Modifier
                            .then(if (view.wrap) Modifier.fillMaxWidth() else Modifier.defaultMinSize(minWidth = 360.dp))
                            .heightIn(min = minHeight)
                            .testTag("editor")
                            .drawBehind {
                                val l = layout ?: return@drawBehind
                                if (l.layoutInput.text.isEmpty()) return@drawBehind
                                val line = l.getLineForOffset(sel.coerceIn(0, l.layoutInput.text.length))
                                drawRect(curColor, Offset(0f, l.getLineTop(line)), Size(size.width, l.getLineBottom(line) - l.getLineTop(line)))
                            },
                        textStyle = TextStyle(color = cs.onSurface, fontFamily = FontFamily.Monospace, fontSize = view.size.sp, lineHeight = lineHeightSp.sp, textDirection = TextDirection.Content),
                        cursorBrush = SolidColor(cs.primary),
                        visualTransformation = hl,
                        onTextLayout = { layout = it },
                        keyboardOptions = KeyboardOptions(autoCorrectEnabled = false),
                    )
                }
            }
        }
    }
}


@file:OptIn(androidx.compose.foundation.ExperimentalFoundationApi::class, androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package app.pdftoolkit.mobile

import android.content.Intent
import android.graphics.Bitmap
import android.webkit.MimeTypeMap
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.filled.Sort
import androidx.compose.material.icons.automirrored.filled.ViewList
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.ContentCut
import androidx.compose.material.icons.filled.ContentPaste
import androidx.compose.material.icons.filled.CreateNewFolder
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.FolderZip
import androidx.compose.material.icons.filled.GridView
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Image as ImageIcon
import androidx.compose.material.icons.filled.InsertDriveFile
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.PushPin
import androidx.compose.material.icons.filled.SdStorage
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.SelectAll
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.io.File
import java.text.DateFormat
import java.util.Date

enum class BrowserMode { OPEN, SAVE, FOLDER, MANAGE }

private fun kindIcon(k: Kind): ImageVector = when (k) {
    Kind.FOLDER -> Icons.Filled.Folder
    Kind.PDF -> Icons.Filled.PictureAsPdf
    Kind.BOOK -> Icons.Filled.MenuBook
    Kind.IMAGE -> Icons.Filled.ImageIcon
    Kind.TEX -> Icons.Filled.Code
    Kind.ARCHIVE -> Icons.Filled.FolderZip
    Kind.OTHER -> Icons.Filled.InsertDriveFile
}

private fun kindTone(k: Kind): Int = when (k) {
    Kind.FOLDER -> 3; Kind.PDF -> 0; Kind.BOOK -> 4; Kind.IMAGE -> 2; Kind.TEX -> 1; Kind.ARCHIVE -> 5; Kind.OTHER -> 1
}

private fun fmtSize(n: Long): String = when {
    n < 1024 -> "$n B"
    n < 1024 * 1024 -> "${n / 1024} KB"
    else -> "%.1f MB".format(n / 1048576.0)
}

private val dateFmt: DateFormat = DateFormat.getDateInstance(DateFormat.MEDIUM)

private fun kindLabel(k: Kind): String = when (k) {
    Kind.PDF -> t("fm.k.pdf"); Kind.BOOK -> t("fm.k.books"); Kind.IMAGE -> t("fm.k.images"); Kind.TEX -> t("fm.k.tex")
    Kind.ARCHIVE -> "ZIP"; Kind.FOLDER -> t("fm.k.folders"); Kind.OTHER -> t("fm.k.other")
}

/** The file manager as a full-screen layer on top of the app, used to choose files, a save place or a folder. */
@Composable
fun FileBrowserOverlay(
    request: PickRequest, memory: FileMemory, onClose: () -> Unit, onDone: (List<File>) -> Unit, onUseSystemPicker: () -> Unit,
) {
    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Box(Modifier.fillMaxSize().statusBarsPadding().navigationBarsPadding().imePadding().testTag("file_browser")) {
            FileBrowser(
                mode = when (request.kind) { PickKind.OPEN -> BrowserMode.OPEN; PickKind.SAVE -> BrowserMode.SAVE; PickKind.FOLDER -> BrowserMode.FOLDER },
                allowed = request.allowed, multi = request.multi, suggestedName = request.suggestedName, start = request.start, memory = memory,
                onClose = onClose, onDone = onDone, onOpenFile = {}, onUseSystemPicker = onUseSystemPicker,
            )
        }
    }
}

@Composable
fun FileBrowser(
    mode: BrowserMode, allowed: Set<Kind>?, multi: Boolean, suggestedName: String, start: File?, memory: FileMemory,
    onClose: (() -> Unit)?, onDone: (List<File>) -> Unit, onOpenFile: (File) -> Unit, onUseSystemPicker: (() -> Unit)?,
) {
    val ctx = LocalContext.current
    var granted by remember { mutableStateOf(Storage.granted(ctx)) }
    val owner = LocalLifecycleOwner.current
    DisposableEffect(owner) {
        val obs = LifecycleEventObserver { _, e -> if (e == Lifecycle.Event.ON_RESUME) granted = Storage.granted(ctx) }
        owner.lifecycle.addObserver(obs)
        onDispose { owner.lifecycle.removeObserver(obs) }
    }
    val legacy = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { granted = Storage.granted(ctx) }
    if (!granted) {
        PermissionPage(
            onAllow = {
                if (android.os.Build.VERSION.SDK_INT >= 30) runCatching { ctx.startActivity(Storage.settingsIntent(ctx)) }
                else legacy.launch(arrayOf(android.Manifest.permission.READ_EXTERNAL_STORAGE, android.Manifest.permission.WRITE_EXTERNAL_STORAGE))
            },
            onSystem = onUseSystemPicker, onClose = onClose,
        )
    } else {
        FileBrowserBody(mode, allowed, multi, suggestedName, start, memory, onClose, onDone, onOpenFile)
    }
}

@Composable
private fun PermissionPage(onAllow: () -> Unit, onSystem: (() -> Unit)?, onClose: (() -> Unit)?) {
    val cs = MaterialTheme.colorScheme
    Column(Modifier.fillMaxSize()) {
        if (onClose != null) IconButton(onClick = onClose, modifier = Modifier.testTag("fm_close")) { Icon(Icons.Filled.Close, t("back"), tint = cs.onBackground) }
        Column(
            Modifier.fillMaxSize().padding(horizontal = 28.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
        ) {
            Surface(shape = RoundedCornerShape(24.dp), color = cs.primaryContainer, modifier = Modifier.size(84.dp)) {
                Box(contentAlignment = Alignment.Center) { Icon(Icons.Filled.Folder, null, tint = cs.primary, modifier = Modifier.size(42.dp)) }
            }
            Spacer(Modifier.size(20.dp))
            Text(t("fm.perm.title"), style = MaterialTheme.typography.titleLarge, color = cs.onBackground, textAlign = TextAlign.Center)
            Spacer(Modifier.size(8.dp))
            Text(t("fm.perm.text"), color = cs.onSurfaceVariant, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.size(24.dp))
            Button(onClick = onAllow, modifier = Modifier.fillMaxWidth().testTag("allow_files")) { Text(t("fm.perm.button")) }
            if (onSystem != null) {
                TextButton(onClick = onSystem, modifier = Modifier.testTag("use_system_picker")) { Text(t("fm.perm.system")) }
            }
        }
    }
}

@Composable
private fun FileBrowserBody(
    mode: BrowserMode, allowed: Set<Kind>?, multi: Boolean, suggestedName: String, start: File?, memory: FileMemory,
    onClose: (() -> Unit)?, onDone: (List<File>) -> Unit, onOpenFile: (File) -> Unit,
) {
    val ctx = LocalContext.current
    val cs = MaterialTheme.colorScheme
    val roots = remember { Storage.roots(ctx) }
    val places = remember { Storage.places(ctx) }

    var dir by remember { mutableStateOf(start?.takeIf { it.isDirectory }) }       // null: the start page
    var reload by remember { mutableIntStateOf(0) }
    var query by remember { mutableStateOf("") }
    var searching by remember { mutableStateOf(false) }
    var filter by remember { mutableStateOf<Kind?>(null) }
    var sort by remember { mutableStateOf(memory.sort) }
    var desc by remember { mutableStateOf(memory.descending) }
    var grid by remember { mutableStateOf(memory.grid) }
    val selected = remember { mutableStateListOf<String>() }
    var clip by remember { mutableStateOf<Pair<List<File>, Boolean>?>(null) }      // files and whether they are moved
    var dialog by remember { mutableStateOf("") }
    var nameText by remember { mutableStateOf(suggestedName) }
    var menu by remember { mutableStateOf("") }

    fun parentOf(d: File): File? {
        val p = d.parentFile ?: return null
        return if (roots.any { p.absolutePath.startsWith(it.dir.absolutePath) }) p else null
    }

    fun openDir(d: File?) {
        dir = d
        query = ""; searching = false; selected.clear(); filter = null
        if (d != null) memory.lastDir = d.absolutePath
    }

    fun goBack() {
        when {
            selected.isNotEmpty() -> selected.clear()
            searching -> { searching = false; query = "" }
            dir != null -> openDir(dir?.let { parentOf(it) })
            else -> onClose?.invoke()
        }
    }
    BackHandler(enabled = selected.isNotEmpty() || searching || dir != null || onClose != null) { goBack() }

    val shownKinds = remember(allowed, mode) {
        if (mode == BrowserMode.FOLDER || mode == BrowserMode.SAVE) emptyList()
        else listOf(Kind.PDF, Kind.BOOK, Kind.IMAGE, Kind.TEX).filter { allowed == null || it in allowed }
    }

    val items by produceState<List<Item>?>(null, dir, reload, query, sort, desc, filter, mode) {
        value = null
        val d = dir
        value = withContext(Dispatchers.IO) {
            if (d == null) emptyList()
            else {
                if (query.isNotBlank()) delay(250)
                val raw = if (query.isNotBlank()) Storage.search(d, query) else Storage.listDir(d)
                val visible = raw.filter { it ->
                    when {
                        it.isDir -> true
                        mode == BrowserMode.FOLDER -> false
                        mode == BrowserMode.SAVE -> true
                        allowed != null && it.kind !in allowed -> false
                        filter != null && it.kind != filter -> false
                        else -> true
                    }
                }
                val base = when (sort) {
                    "date" -> compareBy<Item> { it.modified }
                    "size" -> compareBy<Item> { it.size }
                    else -> compareBy<Item, String>(String.CASE_INSENSITIVE_ORDER) { it.name }
                }
                val cmp = if (desc) base.reversed() else base
                visible.sortedWith(compareBy<Item> { !it.isDir }.then(cmp))
            }
        }
    }

    fun finishPick(files: List<File>) {
        files.forEach { memory.addRecent(it) }
        dir?.let { memory.lastDir = it.absolutePath }
        onDone(files)
    }

    fun selectedFiles(): List<File> = selected.map { File(it) }

    fun toggle(f: File) { if (!selected.remove(f.absolutePath)) selected.add(f.absolutePath) }

    fun onItemClick(it: Item) {
        when {
            selected.isNotEmpty() && (mode == BrowserMode.MANAGE || !it.isDir) -> toggle(it.file)
            it.isDir -> openDir(it.file)
            mode == BrowserMode.OPEN -> if (multi) toggle(it.file) else finishPick(listOf(it.file))
            mode == BrowserMode.SAVE -> nameText = it.name
            mode == BrowserMode.MANAGE -> { memory.addRecent(it.file); onOpenFile(it.file) }
            else -> {}
        }
    }

    fun onItemLong(it: Item) {
        when {
            mode == BrowserMode.MANAGE -> toggle(it.file)
            mode == BrowserMode.OPEN && multi && !it.isDir -> toggle(it.file)
            else -> {}
        }
    }

    fun share() {
        val files = selectedFiles().filter { it.isFile }
        if (files.isEmpty()) return
        val uris = ArrayList(files.map { contentUri(ctx, it) })
        val send = if (uris.size == 1) Intent(Intent.ACTION_SEND).putExtra(Intent.EXTRA_STREAM, uris[0])
        else Intent(Intent.ACTION_SEND_MULTIPLE).putParcelableArrayListExtra(Intent.EXTRA_STREAM, uris)
        val mime = if (files.size == 1) MimeTypeMap.getSingleton().getMimeTypeFromExtension(files[0].extension.lowercase()) ?: "*/*" else "*/*"
        send.setType(mime).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        runCatching { ctx.startActivity(Intent.createChooser(send, null).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
    }

    fun trySave(replace: Boolean, keepBoth: Boolean) {
        val d = dir ?: return
        val ext = suggestedName.substringAfterLast('.', "")
        var n = nameText.trim()
        if (n.isEmpty()) return
        if ('.' !in n && ext.isNotEmpty()) n = "$n.$ext"
        var target = File(d, n)
        if (target.exists() && !replace) {
            if (!keepBoth) { dialog = "overwrite"; return }
            target = Storage.unique(d, n)
        }
        dialog = ""
        finishPick(listOf(target))
    }

    Column(Modifier.fillMaxSize()) {
        // ------------------------------------------------------------------ top bar
        if (selected.isNotEmpty() && mode == BrowserMode.MANAGE) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { selected.clear() }) { Icon(Icons.Filled.Close, t("cancel"), tint = cs.onBackground) }
                Text("${selected.size} ${t("fm.selected")}", Modifier.weight(1f), style = MaterialTheme.typography.titleMedium, color = cs.onBackground)
                IconButton(onClick = { items?.forEach { if (it.absolutePathNotIn(selected)) selected.add(it.file.absolutePath) } }) { Icon(Icons.Filled.SelectAll, t("fm.select.all"), tint = cs.onBackground) }
                IconButton(onClick = { share() }, modifier = Modifier.testTag("fm_share")) { Icon(Icons.Filled.Share, t("share"), tint = cs.onBackground) }
                IconButton(onClick = { clip = selectedFiles() to false; selected.clear() }, modifier = Modifier.testTag("fm_copy")) { Icon(Icons.Filled.ContentCopy, t("fm.copy"), tint = cs.onBackground) }
                IconButton(onClick = { clip = selectedFiles() to true; selected.clear() }, modifier = Modifier.testTag("fm_cut")) { Icon(Icons.Filled.ContentCut, t("fm.move"), tint = cs.onBackground) }
                if (selected.size == 1) IconButton(onClick = { nameText = File(selected[0]).name; dialog = "rename" }, modifier = Modifier.testTag("fm_rename")) { Icon(Icons.Filled.Edit, t("fm.rename"), tint = cs.onBackground) }
                IconButton(onClick = { dialog = "delete" }, modifier = Modifier.testTag("fm_delete")) { Icon(Icons.Filled.Delete, t("delete"), tint = cs.error) }
            }
        } else {
            Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                if (dir != null || onClose != null) {
                    IconButton(onClick = { goBack() }, modifier = Modifier.testTag("fm_back")) {
                        Icon(if (dir != null) Icons.AutoMirrored.Filled.ArrowBack else Icons.Filled.Close, t("back"), tint = cs.onBackground)
                    }
                }
                if (searching) {
                    TextField(
                        value = query, onValueChange = { query = it }, singleLine = true, placeholder = { Text(t("fm.search"), maxLines = 1, overflow = TextOverflow.Ellipsis) },
                        shape = RoundedCornerShape(24.dp),
                        colors = TextFieldDefaults.colors(
                            focusedIndicatorColor = Color.Transparent, unfocusedIndicatorColor = Color.Transparent,
                            focusedContainerColor = cs.surfaceContainerHighest, unfocusedContainerColor = cs.surfaceContainerHighest,
                        ),
                        modifier = Modifier.weight(1f).padding(end = 8.dp).testTag("fm_search"),
                    )
                } else {
                    Column(Modifier.weight(1f).padding(start = if (dir != null || onClose != null) 4.dp else 16.dp)) {
                        Text(
                            when (mode) {
                                BrowserMode.OPEN -> t(if (multi) "fm.choose" else "fm.choose.one")
                                BrowserMode.SAVE -> t("fm.save.as")
                                BrowserMode.FOLDER -> t("fm.choose.folder")
                                BrowserMode.MANAGE -> t("files.tab")
                            },
                            style = MaterialTheme.typography.titleLarge, color = cs.onBackground, maxLines = 1,
                        )
                    }
                    if (dir != null) IconButton(onClick = { searching = true }, modifier = Modifier.testTag("fm_search_button")) { Icon(Icons.Filled.Search, t("fm.search"), tint = cs.onBackground) }
                }
                if (dir != null) {
                    Box {
                        IconButton(onClick = { menu = "sort" }, modifier = Modifier.testTag("fm_sort")) { Icon(Icons.AutoMirrored.Filled.Sort, t("fm.sort"), tint = cs.onBackground) }
                        DropdownMenu(expanded = menu == "sort", onDismissRequest = { menu = "" }) {
                            for ((k, label) in listOf("name" to t("fm.sort.name"), "date" to t("fm.sort.date"), "size" to t("fm.sort.size"))) {
                                DropdownMenuItem(
                                    text = { Text(label + if (sort == k) (if (desc) "  ↓" else "  ↑") else "") },
                                    onClick = {
                                        if (sort == k) desc = !desc else { sort = k; desc = k != "name" }
                                        memory.sort = sort; memory.descending = desc; menu = ""
                                    },
                                )
                            }
                        }
                    }
                    IconButton(onClick = { grid = !grid; memory.grid = grid }, modifier = Modifier.testTag("fm_view")) {
                        Icon(if (grid) Icons.AutoMirrored.Filled.ViewList else Icons.Filled.GridView, t(if (grid) "fm.view.list" else "fm.view.grid"), tint = cs.onBackground)
                    }
                    Box {
                        IconButton(onClick = { menu = "more" }, modifier = Modifier.testTag("fm_more")) { Icon(Icons.Filled.MoreVert, null, tint = cs.onBackground) }
                        DropdownMenu(expanded = menu == "more", onDismissRequest = { menu = "" }) {
                            val d = dir
                            if (d != null && mode != BrowserMode.OPEN) {
                                DropdownMenuItem(text = { Text(t("fm.new.folder")) }, onClick = { menu = ""; nameText = ""; dialog = "newfolder" }, modifier = Modifier.testTag("fm_new_folder"))
                            }
                            if (d != null) {
                                DropdownMenuItem(
                                    text = { Text(t(if (memory.isPinned(d)) "fm.unpin" else "fm.pin")) },
                                    onClick = { memory.togglePin(d); menu = ""; reload++ }, modifier = Modifier.testTag("fm_pin"),
                                )
                            }
                            DropdownMenuItem(text = { Text(t("fm.start")) }, onClick = { menu = ""; openDir(null) }, modifier = Modifier.testTag("fm_start_page"))
                        }
                    }
                }
            }
        }

        // ------------------------------------------------------------------ path and filters
        val d0 = dir
        if (d0 != null && !searching) {
            val root = roots.firstOrNull { d0.absolutePath.startsWith(it.dir.absolutePath) } ?: roots.first()
            val parts = ArrayList<Pair<String, File>>()
            parts.add(root.label to root.dir)
            var cur = root.dir
            for (seg in d0.absolutePath.removePrefix(root.dir.absolutePath).split('/').filter { it.isNotEmpty() }) {
                cur = File(cur, seg); parts.add(seg to cur)
            }
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                for ((i, p) in parts.withIndex()) {
                    if (i > 0) Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, null, tint = cs.onSurfaceVariant, modifier = Modifier.size(18.dp))
                    Text(
                        p.first, maxLines = 1, style = MaterialTheme.typography.labelLarge,
                        color = if (i == parts.lastIndex) cs.onSurface else cs.primary,
                        modifier = Modifier.clickable { openDir(p.second) }.padding(horizontal = 6.dp, vertical = 8.dp).testTag("crumb_$i"),
                    )
                }
            }
        }
        if (d0 != null && shownKinds.size > 1) {
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(selected = filter == null, onClick = { filter = null }, label = { Text(t("fm.all")) }, modifier = Modifier.testTag("fm_filter_all"))
                for (k in shownKinds) FilterChip(selected = filter == k, onClick = { filter = if (filter == k) null else k }, label = { Text(kindLabel(k)) }, modifier = Modifier.testTag("fm_filter_$k"))
            }
        }

        // ------------------------------------------------------------------ content
        Box(Modifier.weight(1f).fillMaxWidth()) {
            if (d0 == null) {
                StartPage(roots, places, memory, mode, reload, onOpenDir = { openDir(it) }, onFile = { f ->
                    when (mode) {
                        BrowserMode.OPEN -> finishPick(listOf(f))
                        BrowserMode.MANAGE -> { memory.addRecent(f); onOpenFile(f) }
                        else -> f.parentFile?.let { openDir(it) }
                    }
                }, onChanged = { reload++ })
            } else {
                val list = items
                if (list == null) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
                } else if (list.isEmpty()) {
                    Column(Modifier.fillMaxSize().padding(32.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                        Icon(Icons.Filled.Folder, null, tint = cs.onSurfaceVariant, modifier = Modifier.size(48.dp))
                        Spacer(Modifier.size(10.dp))
                        Text(t(if (query.isNotBlank()) "fm.nomatch" else "fm.empty"), color = cs.onSurfaceVariant)
                    }
                } else {
                    LazyVerticalGrid(
                        columns = if (grid) GridCells.Adaptive(124.dp) else GridCells.Adaptive(340.dp),
                        modifier = Modifier.fillMaxSize().testTag("fm_list"),
                        contentPadding = PaddingValues(start = 12.dp, end = 12.dp, top = 8.dp, bottom = 12.dp),
                        horizontalArrangement = Arrangement.spacedBy(10.dp), verticalArrangement = Arrangement.spacedBy(if (grid) 10.dp else 6.dp),
                    ) {
                        items(list, key = { it.file.absolutePath }) { it ->
                            val on = selected.contains(it.file.absolutePath)
                            val dim = mode == BrowserMode.SAVE && !it.isDir && it.name != nameText
                            ItemCell(it, grid, on, selected.isNotEmpty() || (mode == BrowserMode.OPEN && multi), showFolder = query.isNotBlank(),
                                modifier = Modifier.alpha(if (dim) 0.6f else 1f), onClick = { onItemClick(it) }, onLong = { onItemLong(it) })
                        }
                    }
                }
            }
        }

        // ------------------------------------------------------------------ bottom bars
        val c = clip
        if (c != null && dir != null) {
            Surface(color = cs.primaryContainer, modifier = Modifier.fillMaxWidth()) {
                Row(Modifier.padding(horizontal = 16.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Filled.ContentPaste, null, tint = cs.primary)
                    Text("${c.first.size}  ·  " + t(if (c.second) "fm.move" else "fm.copy"), Modifier.weight(1f), color = cs.onSurface)
                    TextButton(onClick = { clip = null }) { Text(t("cancel")) }
                    Button(onClick = {
                        val d = dir
                        if (d != null) {
                            c.first.forEach { f -> if (c.second) Storage.move(f, d) else Storage.copy(f, d) }
                            clip = null; reload++
                        }
                    }, modifier = Modifier.testTag("fm_paste")) { Text(t("fm.paste")) }
                }
            }
        }
        if (mode == BrowserMode.OPEN && multi && selected.isNotEmpty()) {
            BottomBar {
                Text("${selected.size} ${t("fm.selected")}", Modifier.weight(1f), style = MaterialTheme.typography.titleSmall, color = cs.onSurface)
                TextButton(onClick = { selected.clear() }) { Text(t("cancel")) }
                Button(onClick = { finishPick(selectedFiles()) }, modifier = Modifier.testTag("fm_add")) { Text(t("fm.add")) }
            }
        }
        if (mode == BrowserMode.SAVE) {
            BottomBar {
                OutlinedTextField(
                    value = nameText, onValueChange = { nameText = it }, singleLine = true, label = { Text(t("fm.file.name")) },
                    modifier = Modifier.weight(1f).testTag("fm_name"),
                )
                Button(onClick = { trySave(replace = false, keepBoth = false) }, enabled = dir != null && nameText.isNotBlank(), modifier = Modifier.testTag("fm_save")) {
                    Text(t("fm.save.here"))
                }
            }
        }
        if (mode == BrowserMode.FOLDER) {
            BottomBar {
                Button(onClick = { dir?.let { finishPick(listOf(it)) } }, enabled = dir != null, modifier = Modifier.fillMaxWidth().testTag("fm_use_folder")) {
                    Text(t("fm.use.folder"))
                }
            }
        }
    }

    // ---------------------------------------------------------------------- dialogs
    when (dialog) {
        "rename" -> AlertDialog(
            onDismissRequest = { dialog = "" }, title = { Text(t("fm.rename")) },
            text = { OutlinedTextField(nameText, { nameText = it }, singleLine = true, modifier = Modifier.testTag("fm_rename_field")) },
            confirmButton = {
                TextButton(onClick = {
                    selected.firstOrNull()?.let { Storage.rename(File(it), nameText) }
                    selected.clear(); dialog = ""; reload++
                }, modifier = Modifier.testTag("fm_rename_ok")) { Text(t("ok.button")) }
            },
            dismissButton = { TextButton(onClick = { dialog = "" }) { Text(t("cancel")) } },
        )
        "delete" -> AlertDialog(
            onDismissRequest = { dialog = "" }, title = { Text(t("delete")) },
            text = { Text(t("fm.delete.confirm")) },
            confirmButton = {
                TextButton(onClick = {
                    selectedFiles().forEach { Storage.delete(it) }
                    selected.clear(); dialog = ""; reload++
                }, modifier = Modifier.testTag("fm_delete_ok")) { Text(t("delete"), color = cs.error) }
            },
            dismissButton = { TextButton(onClick = { dialog = "" }) { Text(t("cancel")) } },
        )
        "newfolder" -> AlertDialog(
            onDismissRequest = { dialog = "" }, title = { Text(t("fm.new.folder")) },
            text = { OutlinedTextField(nameText, { nameText = it }, singleLine = true, label = { Text(t("fm.folder.name")) }, modifier = Modifier.testTag("fm_folder_field")) },
            confirmButton = {
                TextButton(onClick = {
                    val d = dir
                    if (d != null && nameText.isNotBlank() && '/' !in nameText) File(d, nameText.trim()).mkdirs()
                    dialog = ""; nameText = suggestedName; reload++
                }, modifier = Modifier.testTag("fm_folder_ok")) { Text(t("ok.button")) }
            },
            dismissButton = { TextButton(onClick = { dialog = ""; nameText = suggestedName }) { Text(t("cancel")) } },
        )
        "overwrite" -> AlertDialog(
            onDismissRequest = { dialog = "" }, title = { Text(t("fm.exists")) },
            text = { Text(nameText) },
            confirmButton = { TextButton(onClick = { trySave(replace = true, keepBoth = false) }, modifier = Modifier.testTag("fm_replace")) { Text(t("fm.replace")) } },
            dismissButton = {
                Row {
                    TextButton(onClick = { dialog = "" }) { Text(t("cancel")) }
                    TextButton(onClick = { trySave(replace = false, keepBoth = true) }, modifier = Modifier.testTag("fm_keep_both")) { Text(t("fm.keep.both")) }
                }
            },
        )
    }
}

private fun Item.absolutePathNotIn(sel: List<String>) = file.absolutePath !in sel

@Composable
private fun BottomBar(content: @Composable androidx.compose.foundation.layout.RowScope.() -> Unit) {
    Surface(color = MaterialTheme.colorScheme.surface, tonalElevation = 3.dp, shadowElevation = 8.dp, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(horizontal = 16.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp), content = content)
    }
}

@Composable
private fun KindTile(item: Item, size: Int, big: Boolean) {
    val cs = MaterialTheme.colorScheme
    val tone = toneOf(kindTone(item.kind))
    val thumb by produceState<FileThumb?>(null, item.file.path, item.modified) {
        value = if (item.kind == Kind.PDF || item.kind == Kind.IMAGE) withContext(Dispatchers.IO) { FileThumbs.load(item.file, if (big) 300 else 140) } else null
    }
    val bmp: Bitmap? = thumb?.bitmap
    Box(Modifier.fillMaxSize().background(if (bmp != null) Color.White else tone.container), contentAlignment = Alignment.Center) {
        if (bmp != null) {
            Image(bmp.asImageBitmap(), null, contentScale = ContentScale.Crop, alignment = Alignment.TopCenter, modifier = Modifier.fillMaxSize())
        } else {
            Icon(kindIcon(item.kind), null, tint = tone.icon, modifier = Modifier.size(size.dp))
        }
    }
}

@Composable
private fun ItemCell(
    item: Item, grid: Boolean, selected: Boolean, selecting: Boolean, showFolder: Boolean,
    modifier: Modifier, onClick: () -> Unit, onLong: () -> Unit,
) {
    val cs = MaterialTheme.colorScheme
    val pages by produceState(0, item.file.path, item.modified) {
        value = if (item.kind == Kind.PDF) withContext(Dispatchers.IO) { FileThumbs.load(item.file, if (grid) 300 else 140)?.pages ?: 0 } else 0
    }
    val sub = buildString {
        if (!item.isDir) append(fmtSize(item.size)).append("  ·  ")
        append(dateFmt.format(Date(item.modified)))
        if (pages > 0) append("  ·  $pages ${t("pages")}")
    }
    val border = BorderStroke(if (selected) 2.dp else 1.dp, if (selected) cs.primary else cs.outlineVariant)
    Surface(
        shape = RoundedCornerShape(16.dp), color = if (selected) cs.primaryContainer else cs.surface, border = border,
        modifier = modifier.fillMaxWidth().combinedClickable(onClick = onClick, onLongClick = onLong).testTag("fm_item"),
    ) {
        if (grid) {
            Column(Modifier.padding(8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Box(Modifier.fillMaxWidth().aspectRatio(0.85f).clip(RoundedCornerShape(10.dp))) {
                    KindTile(item, 44, big = true)
                    if (selecting || selected) {
                        Icon(
                            Icons.Filled.CheckCircle, null, tint = if (selected) cs.primary else Color.White.copy(alpha = 0.7f),
                            modifier = Modifier.align(Alignment.TopStart).padding(6.dp).size(24.dp).background(Color.White.copy(alpha = if (selected) 1f else 0.3f), CircleShape),
                        )
                    }
                }
                Text(item.name, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelLarge, color = cs.onSurface)
                Text(sub, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelSmall, color = cs.onSurfaceVariant)
                if (showFolder) Text(item.file.parentFile?.name ?: "", maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelSmall, color = cs.primary)
            }
        } else {
            Row(Modifier.padding(8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(Modifier.size(52.dp).clip(RoundedCornerShape(10.dp))) { KindTile(item, 26, big = false) }
                Column(Modifier.weight(1f)) {
                    Text(item.name, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.titleSmall, color = cs.onSurface)
                    Text(sub, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall, color = cs.onSurfaceVariant)
                    if (showFolder) Text(item.file.parentFile?.absolutePath ?: "", maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelSmall, color = cs.primary)
                }
                if (selecting || selected) {
                    Icon(Icons.Filled.CheckCircle, null, tint = if (selected) cs.primary else cs.outlineVariant, modifier = Modifier.size(26.dp))
                }
            }
        }
    }
}

@Composable
private fun StartPage(
    roots: List<Place>, places: List<Place>, memory: FileMemory, mode: BrowserMode, reload: Int,
    onOpenDir: (File) -> Unit, onFile: (File) -> Unit, onChanged: () -> Unit,
) {
    val cs = MaterialTheme.colorScheme
    val pinned = remember(reload) { memory.pinned() }
    val recent = remember(reload) { if (mode == BrowserMode.OPEN || mode == BrowserMode.MANAGE) memory.recent().take(8) else emptyList() }

    @Composable
    fun placeRow(icon: ImageVector, tone: Int, label: String, sub: String, tag: String, trailing: (@Composable () -> Unit)? = null, onClick: () -> Unit) {
        val tn = toneOf(tone)
        Surface(onClick = onClick, shape = RoundedCornerShape(16.dp), color = cs.surface, border = BorderStroke(1.dp, cs.outlineVariant), modifier = Modifier.fillMaxWidth().testTag(tag)) {
            Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Surface(shape = RoundedCornerShape(12.dp), color = tn.container, modifier = Modifier.size(44.dp)) {
                    Box(contentAlignment = Alignment.Center) { Icon(icon, null, tint = tn.icon, modifier = Modifier.size(24.dp)) }
                }
                Column(Modifier.weight(1f)) {
                    Text(label, style = MaterialTheme.typography.titleSmall, color = cs.onSurface, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    if (sub.isNotEmpty()) Text(sub, style = MaterialTheme.typography.bodySmall, color = cs.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                trailing?.invoke()
            }
        }
    }

    LazyColumn(Modifier.fillMaxSize().testTag("fm_start"), contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item { Text(t("fm.storage"), style = MaterialTheme.typography.titleSmall, color = cs.onSurfaceVariant, modifier = Modifier.padding(start = 4.dp)) }
        items(roots, key = { "root" + it.key }) { r ->
            placeRow(if (r.key == "internal") Icons.Filled.PhoneAndroid else Icons.Filled.SdStorage, 1, r.label, r.dir.absolutePath, "place_${r.key}") { onOpenDir(r.dir) }
        }
        if (places.isNotEmpty()) {
            item { Text(t("fm.quick"), style = MaterialTheme.typography.titleSmall, color = cs.onSurfaceVariant, modifier = Modifier.padding(start = 4.dp, top = 8.dp)) }
            items(places, key = { "place" + it.key }) { p ->
                val icon = when (p.key) { "downloads" -> Icons.Filled.Download; "pictures", "camera" -> Icons.Filled.ImageIcon; "books" -> Icons.Filled.MenuBook; else -> Icons.Filled.Folder }
                placeRow(icon, when (p.key) { "downloads" -> 2; "documents" -> 0; "camera", "pictures" -> 4; else -> 3 }, p.label, p.dir.name, "place_${p.key}") { onOpenDir(p.dir) }
            }
        }
        if (pinned.isNotEmpty()) {
            item { Text(t("fm.pinned"), style = MaterialTheme.typography.titleSmall, color = cs.onSurfaceVariant, modifier = Modifier.padding(start = 4.dp, top = 8.dp)) }
            items(pinned, key = { "pin" + it.absolutePath }) { d ->
                placeRow(Icons.Filled.PushPin, 5, d.name, d.absolutePath, "pinned_folder", trailing = {
                    IconButton(onClick = { memory.togglePin(d); onChanged() }) { Icon(Icons.Filled.Close, t("fm.unpin"), tint = cs.onSurfaceVariant) }
                }) { onOpenDir(d) }
            }
        }
        if (recent.isNotEmpty()) {
            item { Text(t("fm.recent"), style = MaterialTheme.typography.titleSmall, color = cs.onSurfaceVariant, modifier = Modifier.padding(start = 4.dp, top = 8.dp)) }
            items(recent, key = { "rec" + it.absolutePath }) { f ->
                val k = kindOf(f)
                placeRow(kindIcon(k), kindTone(k), f.name, f.parentFile?.name.orEmpty() + "  ·  " + fmtSize(f.length()), "recent_file") { onFile(f) }
            }
        }
    }
}

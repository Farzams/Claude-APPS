package app.pdftoolkit.mobile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.UploadFile
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import java.text.DateFormat
import java.util.Date

@Composable
fun ProjectsScreen(vm: EditorViewModel, onSettings: () -> Unit) {
    val cs = MaterialTheme.colorScheme
    val ctx = LocalContext.current
    var creating by remember { mutableStateOf(false) }
    var renaming by remember { mutableStateOf<Project?>(null) }
    var deleting by remember { mutableStateOf<Project?>(null) }
    var exporting by remember { mutableStateOf<Project?>(null) }

    val importer = rememberAnyPicker { uri ->
        if (uri != null) {
            val name = displayName(ctx, uri)
            runCatching {
                val input = ctx.contentResolver.openInputStream(uri) ?: return@runCatching
                input.use {
                    if (name.endsWith(".zip", true)) vm.importProjectZip(name, it)
                    else {
                        val bytes = it.readBytes()
                        vm.createProject(name.substringBeforeLast('.'), Template("tpl.blank", mapOf(name to String(bytes, Charsets.UTF_8)), main = name))
                    }
                }
            }
        }
    }
    val exporter = rememberSavePicker("application/zip") { uri ->
        val p = exporting
        if (uri != null && p != null) runCatching { ctx.contentResolver.openOutputStream(uri)?.use { vm.store.exportZip(p, it) } }
        exporting = null
    }

    var query by remember { mutableStateOf("") }
    val shown = vm.projects.filter { query.isBlank() || it.name.contains(query.trim(), ignoreCase = true) }

    Box(Modifier.fillMaxSize().statusBarsPadding().navigationBarsPadding(), contentAlignment = Alignment.TopCenter) {
        Column(Modifier.widthIn(max = 1000.dp).fillMaxSize()) {
            Row(Modifier.fillMaxWidth().padding(start = 20.dp, end = 8.dp, top = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(t("app.latex"), style = MaterialTheme.typography.headlineMedium, color = cs.onBackground)
                    Text(t("latex.sub"), style = MaterialTheme.typography.bodyMedium, color = cs.onSurfaceVariant)
                }
                IconButton(onClick = { importer.launch(arrayOf("application/zip", "text/*", "application/x-tex", "application/octet-stream")) }, modifier = Modifier.testTag("import_project")) {
                    Icon(Icons.Filled.UploadFile, t("import"), tint = cs.onBackground)
                }
                IconButton(onClick = onSettings, modifier = Modifier.testTag("open_settings")) {
                    Icon(Icons.Filled.Settings, t("settings"), tint = cs.onBackground)
                }
            }
            TextField(
                value = query, onValueChange = { query = it }, singleLine = true,
                placeholder = { Text(t("search.projects"), maxLines = 1, overflow = TextOverflow.Ellipsis) },
                leadingIcon = { Icon(Icons.Filled.Search, null) },
                shape = RoundedCornerShape(28.dp),
                colors = TextFieldDefaults.colors(
                    focusedIndicatorColor = Color.Transparent, unfocusedIndicatorColor = Color.Transparent, disabledIndicatorColor = Color.Transparent,
                    focusedContainerColor = cs.surfaceContainerHighest, unfocusedContainerColor = cs.surfaceContainerHighest,
                ),
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp).testTag("search_projects"),
            )
            LazyVerticalGrid(
                columns = GridCells.Adaptive(320.dp), modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 96.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp), verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                if (vm.projects.isEmpty()) {
                    item(span = { GridItemSpan(maxLineSpan) }) {
                        Surface(shape = RoundedCornerShape(20.dp), color = cs.primaryContainer, modifier = Modifier.fillMaxWidth()) {
                            Text(t("no.projects"), Modifier.padding(20.dp), color = cs.onSurface)
                        }
                    }
                }
                itemsIndexed(shown, key = { _, p -> p.name }) { i, p ->
                    var menu by remember { mutableStateOf(false) }
                    val engine = remember(p) { runCatching { vm.store.meta(p).engine }.getOrDefault("xetex") }
                    val date = remember(p) { DateFormat.getDateInstance(DateFormat.MEDIUM).format(Date(p.modified)) }
                    Surface(
                        onClick = { vm.openProject(p) }, shape = RoundedCornerShape(20.dp), color = cs.surface,
                        border = BorderStroke(1.dp, cs.outlineVariant), modifier = Modifier.fillMaxWidth().testTag("project_$i"),
                    ) {
                        Row(Modifier.padding(start = 14.dp, top = 12.dp, bottom = 12.dp, end = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                            PageGlyph()
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(p.name, style = MaterialTheme.typography.titleMedium, color = cs.onSurface, maxLines = 2, overflow = TextOverflow.Ellipsis)
                                Text(date, style = MaterialTheme.typography.bodySmall, color = cs.onSurfaceVariant, maxLines = 1)
                                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    InfoChip(t(if (engine == "xetex") "engine.xetex.short" else "engine.pdftex.short"))
                                    InfoChip("${p.fileCount} ${t("files")}")
                                }
                            }
                            Box {
                                IconButton(onClick = { menu = true }) { Icon(Icons.Filled.MoreVert, null, tint = cs.onSurfaceVariant) }
                                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                                    DropdownMenuItem(text = { Text(t("rename")) }, onClick = { menu = false; renaming = p })
                                    DropdownMenuItem(text = { Text(t("duplicate")) }, onClick = { menu = false; vm.duplicateProject(p) })
                                    DropdownMenuItem(text = { Text(t("export.zip")) }, onClick = { menu = false; exporting = p; exporter.launch(p.name + ".zip") })
                                    DropdownMenuItem(text = { Text(t("delete")) }, onClick = { menu = false; deleting = p })
                                }
                            }
                        }
                    }
                }
            }
        }
        Surface(
            onClick = { creating = true }, shape = RoundedCornerShape(20.dp), color = cs.primary, shadowElevation = 6.dp,
            modifier = Modifier.align(Alignment.BottomEnd).padding(20.dp).testTag("new_project"),
        ) {
            Row(Modifier.padding(horizontal = 20.dp, vertical = 16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.Filled.Add, null, tint = cs.onPrimary)
                Text(t("new.project"), color = cs.onPrimary, style = MaterialTheme.typography.labelLarge)
            }
        }
    }

    if (creating) NewProjectDialog(vm, onDismiss = { creating = false })
    renaming?.let { p ->
        var name by remember(p) { mutableStateOf(p.name) }
        AlertDialog(
            onDismissRequest = { renaming = null },
            title = { Text(t("rename")) },
            text = { OutlinedTextField(name, { name = it }, singleLine = true, modifier = Modifier.testTag("rename_field")) },
            confirmButton = { TextButton(onClick = { vm.renameProject(p, name); renaming = null }) { Text(t("ok.button")) } },
            dismissButton = { TextButton(onClick = { renaming = null }) { Text(t("cancel")) } },
        )
    }
    deleting?.let { p ->
        AlertDialog(
            onDismissRequest = { deleting = null },
            title = { Text(t("delete")) },
            text = { Text("${p.name}?") },
            confirmButton = { TextButton(onClick = { vm.deleteProject(p); deleting = null }) { Text(t("delete"), color = cs.error) } },
            dismissButton = { TextButton(onClick = { deleting = null }) { Text(t("cancel")) } },
        )
    }
}

@Composable
private fun NewProjectDialog(vm: EditorViewModel, onDismiss: () -> Unit) {
    val cs = MaterialTheme.colorScheme
    var name by remember { mutableStateOf("") }
    var choice by remember { mutableStateOf(Templates.ALL.first().key) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(t("new.project")) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                OutlinedTextField(name, { name = it }, label = { Text(t("project.name")) }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("project_name"))
                Spacer(Modifier.height(6.dp))
                Text(t("templates"), style = MaterialTheme.typography.titleSmall, color = cs.onSurfaceVariant)
                Column(Modifier.fillMaxWidth().height(240.dp).verticalScroll(androidx.compose.foundation.rememberScrollState())) {
                    for (tpl in Templates.ALL) {
                        Row(Modifier.fillMaxWidth().clickable { choice = tpl.key }.testTag("tpl_${tpl.key}"), verticalAlignment = Alignment.CenterVertically) {
                            RadioButton(selected = choice == tpl.key, onClick = { choice = tpl.key })
                            Text(t(tpl.key), color = cs.onSurface)
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    val tpl = Templates.ALL.first { it.key == choice }
                    vm.createProject(name.ifBlank { t(choice) }, tpl)
                    onDismiss()
                },
                modifier = Modifier.testTag("create_project"),
            ) { Text(t("create")) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(t("cancel")) } },
    )
}

/** A small drawn page, used as the project's picture. */
@Composable
private fun PageGlyph() {
    val cs = MaterialTheme.colorScheme
    Column(
        Modifier.size(width = 56.dp, height = 72.dp).clip(RoundedCornerShape(8.dp)).background(Color.White).padding(8.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Box(Modifier.fillMaxWidth(0.6f).height(5.dp).clip(RoundedCornerShape(3.dp)).background(cs.primary))
        for (i in 0 until 6) Box(Modifier.fillMaxWidth(if (i == 5) 0.55f else 1f).height(2.dp).clip(RoundedCornerShape(1.dp)).background(Color(0xFFD5D8E2)))
    }
}

@Composable
private fun InfoChip(text: String) {
    val cs = MaterialTheme.colorScheme
    Surface(shape = RoundedCornerShape(10.dp), color = cs.primaryContainer) {
        Text(text, Modifier.padding(horizontal = 8.dp, vertical = 3.dp), color = cs.onSurface, style = MaterialTheme.typography.labelSmall, maxLines = 1)
    }
}

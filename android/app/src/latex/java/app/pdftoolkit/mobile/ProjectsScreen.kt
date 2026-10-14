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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.PictureAsPdf
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
import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
    var pdfPick by remember { mutableStateOf<Uri?>(null) }
    val pdfPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { if (it != null) pdfPick = it }

    val importer = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
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
    val exporter = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/zip")) { uri ->
        val p = exporting
        if (uri != null && p != null) runCatching { ctx.contentResolver.openOutputStream(uri)?.use { vm.store.exportZip(p, it) } }
        exporting = null
    }

    Column(Modifier.fillMaxSize().statusBarsPadding().navigationBarsPadding()) {
        Row(Modifier.fillMaxWidth().padding(start = 20.dp, end = 8.dp, top = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(t("app.latex"), style = MaterialTheme.typography.headlineMedium, color = cs.onBackground)
                Text(t("latex.sub"), style = MaterialTheme.typography.bodyMedium, color = cs.onSurfaceVariant)
            }
            IconButton(onClick = { pdfPicker.launch(arrayOf("application/pdf")) }, modifier = Modifier.testTag("pdf_to_latex")) {
                Icon(Icons.Filled.PictureAsPdf, t("pdf.to.latex"), tint = cs.onBackground)
            }
            IconButton(onClick = { importer.launch(arrayOf("application/zip", "text/*", "application/x-tex", "application/octet-stream")) }, modifier = Modifier.testTag("import_project")) {
                Icon(Icons.Filled.UploadFile, t("import"), tint = cs.onBackground)
            }
            IconButton(onClick = onSettings, modifier = Modifier.testTag("open_settings")) {
                Icon(Icons.Filled.Settings, t("settings"), tint = cs.onBackground)
            }
        }
        Spacer(Modifier.height(8.dp))
        Box(Modifier.weight(1f)) {
            LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 96.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                itemsIndexed(vm.projects, key = { _, p -> p.name }) { i, p ->
                    var menu by remember { mutableStateOf(false) }
                    Surface(
                        onClick = { vm.openProject(p) }, shape = RoundedCornerShape(16.dp), color = cs.surface,
                        border = BorderStroke(1.dp, cs.outlineVariant), modifier = Modifier.fillMaxWidth().testTag("project_$i"),
                    ) {
                        Row(Modifier.padding(start = 16.dp, top = 12.dp, bottom = 12.dp, end = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                            Surface(shape = RoundedCornerShape(12.dp), color = cs.primary.copy(alpha = 0.14f), modifier = Modifier.size(44.dp)) {
                                Box(contentAlignment = Alignment.Center) { Icon(Icons.Filled.Description, null, tint = cs.primary, modifier = Modifier.size(24.dp)) }
                            }
                            Column(Modifier.weight(1f).padding(start = 14.dp)) {
                                Text(p.name, style = MaterialTheme.typography.titleMedium, color = cs.onSurface, maxLines = 1)
                                Text(
                                    "${p.fileCount} ${t("files")}  ·  " + DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(Date(p.modified)),
                                    style = MaterialTheme.typography.bodySmall, color = cs.onSurfaceVariant,
                                )
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
            Surface(
                onClick = { creating = true }, shape = RoundedCornerShape(18.dp), color = cs.primary, shadowElevation = 4.dp,
                modifier = Modifier.align(Alignment.BottomEnd).padding(20.dp).testTag("new_project"),
            ) {
                Row(Modifier.padding(horizontal = 18.dp, vertical = 14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Filled.Add, null, tint = cs.onPrimary)
                    Text(t("new.project"), color = cs.onPrimary, style = MaterialTheme.typography.labelLarge)
                }
            }
        }
    }

    if (creating) NewProjectDialog(vm, onDismiss = { creating = false })
    pdfPick?.let { u -> PdfToLatexDialog(vm, uri = u, file = null, name = displayName(ctx, u).substringBeforeLast('.'), onDismiss = { pdfPick = null }) }
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


/** Options and progress for turning a PDF into a LaTeX project. */
@Composable
fun PdfToLatexDialog(vm: EditorViewModel, uri: Uri?, file: java.io.File?, name: String, onDismiss: () -> Unit) {
    val cs = MaterialTheme.colorScheme
    var eq by remember { mutableStateOf(true) }
    var pages by remember { mutableStateOf(true) }
    var started by remember { mutableStateOf(false) }
    // when the conversion finished the editor opens by itself; an error stays visible here
    androidx.compose.runtime.LaunchedEffect(vm.converting, vm.project) {
        if (started && vm.converting.isEmpty() && vm.convertError.isEmpty()) onDismiss()
    }
    AlertDialog(
        onDismissRequest = { if (vm.converting.isEmpty()) onDismiss() },
        title = { Text(t("pdf.to.latex")) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (vm.converting.isNotEmpty()) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        androidx.compose.material3.CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp)
                        Text("${t("ptl.working")} ${vm.converting}", color = cs.onSurface)
                    }
                } else {
                    Text(t("ptl.note"), style = MaterialTheme.typography.bodyMedium, color = cs.onSurfaceVariant)
                    Row(Modifier.fillMaxWidth().clickable { eq = !eq }, verticalAlignment = Alignment.CenterVertically) {
                        androidx.compose.material3.Checkbox(checked = eq, onCheckedChange = { eq = it })
                        Text(t("ptl.eq"), color = cs.onSurface, style = MaterialTheme.typography.bodyMedium)
                    }
                    Row(Modifier.fillMaxWidth().clickable { pages = !pages }, verticalAlignment = Alignment.CenterVertically) {
                        androidx.compose.material3.Checkbox(checked = pages, onCheckedChange = { pages = it })
                        Text(t("ptl.pages"), color = cs.onSurface, style = MaterialTheme.typography.bodyMedium)
                    }
                    if (vm.convertError.isNotEmpty()) Text(vm.convertError, color = cs.error)
                }
            }
        },
        confirmButton = {
            if (vm.converting.isEmpty()) TextButton(
                onClick = { started = true; vm.pdfToLatex(uri, file, name.ifBlank { "PDF" }, PdfToLatex.Options(eq, pages)) },
                modifier = Modifier.testTag("ptl_start"),
            ) { Text(t("ptl.start")) }
        },
        dismissButton = { if (vm.converting.isEmpty()) TextButton(onClick = onDismiss) { Text(t("cancel")) } },
    )
}

package app.pdftoolkit.mobile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Redo
import androidx.compose.material.icons.automirrored.filled.Undo
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Description
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun EditorScreen(vm: EditorViewModel, onBack: () -> Unit, fontSize: Int) {
    val engine by TexEngine.status.collectAsState()
    var tab by remember { mutableIntStateOf(0) }
    LaunchedEffect(vm.pdfVersion) { if (vm.pdfVersion > 0 && vm.compileOk == true) tab = 1 }

    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        TopBar(vm, onBack, engine)
        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
        BoxWithConstraints(Modifier.fillMaxSize()) {
            if (maxWidth >= 840.dp) {
                Row(Modifier.fillMaxSize()) {
                    Box(Modifier.weight(1f).fillMaxHeight()) { EditorPane(vm, fontSize) }
                    Box(Modifier.width(1.dp).fillMaxHeight().background(MaterialTheme.colorScheme.outlineVariant))
                    Box(Modifier.weight(1f).fillMaxHeight()) { PdfPreview(vm.pdfFile, vm.pdfVersion) }
                }
            } else {
                Column(Modifier.fillMaxSize()) {
                    TabRow(selectedTabIndex = tab, containerColor = MaterialTheme.colorScheme.surface) {
                        Tab(tab == 0, { tab = 0 }, Modifier.testTag("tab_editor"), text = { Text(t("editor")) })
                        Tab(tab == 1, { tab = 1 }, Modifier.testTag("tab_pdf"), text = { Text(t("preview")) })
                    }
                    Box(Modifier.weight(1f).fillMaxWidth()) {
                        if (tab == 0) EditorPane(vm, fontSize) else PdfPreview(vm.pdfFile, vm.pdfVersion)
                    }
                }
            }
        }
    }
}

@Composable
private fun TopBar(vm: EditorViewModel, onBack: () -> Unit, engine: String) {
    var menu by remember { mutableStateOf(false) }
    Surface(color = MaterialTheme.colorScheme.surface) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack, modifier = Modifier.testTag("back")) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, t("back"), tint = MaterialTheme.colorScheme.onSurface)
            }
            Column(Modifier.weight(1f)) {
                Text(t("latex"), style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurface)
                val line = when {
                    vm.compiling -> t("compiling")
                    engine == "starting" -> t("engine.start")
                    vm.status.isNotEmpty() -> vm.status
                    else -> ""
                }
                if (line.isNotEmpty()) Text(line, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
            }
            Box {
                IconButton(onClick = { menu = true }, modifier = Modifier.testTag("templates")) {
                    Icon(Icons.Filled.Description, t("templates"), tint = MaterialTheme.colorScheme.onSurface)
                }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    for ((key, text) in Templates.ALL) {
                        DropdownMenuItem(text = { Text(t(key)) }, onClick = { menu = false; vm.loadTemplate(text) }, modifier = Modifier.testTag(key))
                    }
                }
            }
            IconButton(onClick = { vm.undo() }, enabled = vm.canUndo) {
                Icon(Icons.AutoMirrored.Filled.Undo, t("undo"), tint = MaterialTheme.colorScheme.onSurface.copy(alpha = if (vm.canUndo) 1f else 0.3f))
            }
            IconButton(onClick = { vm.redo() }, enabled = vm.canRedo) {
                Icon(Icons.AutoMirrored.Filled.Redo, t("redo"), tint = MaterialTheme.colorScheme.onSurface.copy(alpha = if (vm.canRedo) 1f else 0.3f))
            }
            Surface(
                onClick = { vm.compile() }, enabled = !vm.compiling, shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.primary, modifier = Modifier.testTag("compile"),
            ) {
                Row(Modifier.padding(horizontal = 14.dp, vertical = 9.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (vm.compiling) CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary)
                    else Icon(Icons.Filled.PlayArrow, null, Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onPrimary)
                    Text(t("compile"), color = MaterialTheme.colorScheme.onPrimary, style = MaterialTheme.typography.labelLarge)
                }
            }
            Box(Modifier.width(6.dp))
        }
    }
}

@Composable
private fun EditorPane(vm: EditorViewModel, fontSize: Int) {
    val cs = MaterialTheme.colorScheme
    val dark = cs.background.red + cs.background.green + cs.background.blue < 1.5f
    val hl = remember(cs.primary, dark, cs.onSurfaceVariant) {
        LatexHighlighter(
            command = cs.primary,
            math = if (dark) Color(0xFF7DD3C0) else Color(0xFF0F766E),
            comment = cs.onSurfaceVariant,
            env = if (dark) Color(0xFFF0A26B) else Color(0xFFB4532A),
        )
    }
    var showLog by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize()) {
        // symbol bar
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).background(cs.surface).padding(horizontal = 6.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            for ((label, snippet) in SNIPPETS) {
                Surface(onClick = { vm.insert(snippet) }, shape = RoundedCornerShape(8.dp), color = cs.surfaceVariant,
                    border = BorderStroke(1.dp, cs.outlineVariant)) {
                    Text(label, Modifier.padding(horizontal = 10.dp, vertical = 6.dp), color = cs.onSurface, fontFamily = FontFamily.Monospace, fontSize = 14.sp)
                }
            }
        }
        HorizontalDivider(color = cs.outlineVariant)
        // text
        Box(Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()).padding(12.dp)) {
            CompositionLocalProviderLtr {
                BasicTextField(
                    value = vm.field,
                    onValueChange = { vm.onChange(it) },
                    modifier = Modifier.fillMaxWidth().heightIn(min = 300.dp).testTag("editor"),
                    textStyle = TextStyle(color = cs.onSurface, fontFamily = FontFamily.Monospace, fontSize = fontSize.sp, lineHeight = (fontSize * 1.45f).sp, textDirection = TextDirection.Content),
                    cursorBrush = SolidColor(cs.primary),
                    visualTransformation = hl,
                )
            }
        }
        // status / errors
        HorizontalDivider(color = cs.outlineVariant)
        val summary = when (vm.compileOk) {
            true -> t("ok")
            false -> "${t("failed")} · ${vm.errors.size} ${t("errors")}"
            null -> ""
        }
        if (summary.isNotEmpty() || vm.log.isNotEmpty()) {
            Row(Modifier.fillMaxWidth().background(cs.surface).clickable { showLog = !showLog }.padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Text(summary, Modifier.weight(1f).testTag(if (vm.compileOk == false) "compile_failed" else "compile_ok"),
                    color = if (vm.compileOk == false) cs.error else cs.onSurface, style = MaterialTheme.typography.bodyMedium)
                Text(t("log"), color = cs.onSurfaceVariant, style = MaterialTheme.typography.labelMedium)
                Icon(if (showLog) Icons.Filled.ExpandMore else Icons.Filled.ExpandLess, null, tint = cs.onSurfaceVariant)
            }
            if (showLog || (vm.compileOk == false && vm.errors.isNotEmpty())) {
                Column(Modifier.fillMaxWidth().heightIn(max = 200.dp).background(cs.surfaceVariant).verticalScroll(rememberScrollState()).padding(10.dp)) {
                    for (e in vm.errors) {
                        Text((e.line?.let { "l.$it  " } ?: "") + e.message, color = cs.error, fontFamily = FontFamily.Monospace, fontSize = 13.sp,
                            modifier = Modifier.fillMaxWidth().clickable { e.line?.let { vm.goToLine(it) } }.padding(vertical = 3.dp))
                    }
                    if (showLog) Text(vm.log.takeLast(6000), color = cs.onSurfaceVariant, fontFamily = FontFamily.Monospace, fontSize = 11.sp)
                }
            }
        }
    }
}

/** Code is always laid out left-to-right, even in the Persian interface. */
@Composable
private fun CompositionLocalProviderLtr(content: @Composable () -> Unit) {
    androidx.compose.runtime.CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr, content = content)
}

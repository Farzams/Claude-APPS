package app.linuxpad

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import app.linuxpad.runtime.LinuxSystem
import app.linuxpad.runtime.Proot
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.linuxpad.display.DisplayInfo
import app.linuxpad.display.DisplayScale
import app.linuxpad.display.Screens
import app.linuxpad.x11.X11Server

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)   // long installs must not be cut by the screen turning off
        setContent { MaterialTheme(colorScheme = if (isSystemInDarkTheme()) darkColorScheme() else lightColorScheme()) { Surface { MainScreen(Screens.read(this)) } } }
    }
}

@Composable
private fun MainScreen(d: DisplayInfo) {
    val ctx = LocalContext.current
    var note by remember { mutableStateOf("") }
    val plan = DisplayScale.plan(d)   // the final size: 174 dpi, cursor 40 px on this tablet
    val report = buildString {
        appendLine("LinuxPad report")
        appendLine("device: ${Build.MANUFACTURER} ${Build.MODEL}, Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
        appendLine("screen: ${d.widthPx}x${d.heightPx} px, ${"%.0f".format(d.refreshHz)} Hz, ${"%.1f".format(plan.physicalPpi)} ppi -> Xft.dpi ${plan.xftDpi}, cursor ${plan.cursorSize}")
        appendLine("debian installed: ${LinuxSystem.installed}, xfce installed: ${LinuxSystem.hasXfce(ctx)}")
        appendLine("xfce parts: ${LinuxSystem.xfceStatus(ctx)}")
        if (note.isNotBlank()) appendLine("note: $note")
        appendLine("x11: ${X11Server.state} ${X11Server.detail}")
        if (LinuxSystem.output.isNotBlank()) appendLine("\n--- Linux output ---\n${LinuxSystem.output.takeLast(3000)}")
        LinuxSystem.error?.let { appendLine("error: $it") }
    }
    Column(Modifier.fillMaxSize().systemBarsPadding().verticalScroll(rememberScrollState()).padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("LinuxPad", style = MaterialTheme.typography.headlineMedium)
        Text("Linux desktop for this tablet: ${d.widthPx} x ${d.heightPx} px, ${"%.0f".format(d.refreshHz)} Hz, ${"%.0f".format(plan.physicalPpi)} ppi.")

        Section("1. Linux system (Debian)")
        LaunchedEffect(Unit) { LinuxSystem.refresh(ctx) }
        var confirmDeleteAll by remember { mutableStateOf(false) }
        val prog = LinuxSystem.progress
        when {
            prog != null -> {
                Text(prog.phase + if (prog.total > 0) "  ${prog.done / 1_048_576} / ${prog.total / 1_048_576} MB" else "")
                if (prog.total > 0) LinearProgressIndicator(progress = { prog.done.toFloat() / prog.total }, modifier = Modifier.fillMaxWidth())
                else LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            }
            LinuxSystem.installed -> {
                Text("Debian is installed.")
                var cmd by remember { mutableStateOf("") }
                OutlinedTextField(cmd, { cmd = it }, label = { Text("Run a command inside Debian (optional)") }, modifier = Modifier.fillMaxWidth())
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button({ LinuxSystem.run(ctx, cmd) }, enabled = !LinuxSystem.running && cmd.isNotBlank()) { Text("Run") }
                    OutlinedButton({ confirmDeleteAll = true }, enabled = !LinuxSystem.running) { Text("Delete Debian and everything in it") }
                }
            }
            else -> Button({ LinuxSystem.install(ctx) }) { Text("Download and install Debian 13 (about 30 MB)") }
        }
        if (confirmDeleteAll) {
            AlertDialog(
                onDismissRequest = { confirmDeleteAll = false },
                title = { Text("Delete Debian and everything in it?") },
                text = { Text("Every installed package and every file you made inside Debian (the folder /root included) will be erased. This cannot be undone. Download and install Debian again afterwards if you want it back.") },
                confirmButton = { TextButton({ confirmDeleteAll = false; LinuxSystem.remove(ctx) }) { Text("Delete everything", color = MaterialTheme.colorScheme.error) } },
                dismissButton = { TextButton({ confirmDeleteAll = false }) { Text("Cancel") } },
            )
        }
        LinuxSystem.error?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
        if (LinuxSystem.output.isNotBlank()) Text(LinuxSystem.output, fontSize = 13.sp, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)

        Section("2. Desktop")
        val hasXfce = LinuxSystem.hasXfce(ctx)
        Text("XFCE parts: ${LinuxSystem.xfceStatus(ctx)}", fontSize = 13.sp, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
        Text(if (hasXfce) "XFCE desktop: installed." else "XFCE desktop: not installed yet. Install the graphics packages first, then XFCE (about 150 to 300 MB; keep the app open while it runs).")
        Button({ LinuxSystem.run(ctx, "apt-get update && apt-get install -y --no-install-recommends ${LinuxSystem.GRAPHICS_PACKAGES}") },
            enabled = LinuxSystem.installed && !LinuxSystem.running) { Text("Install graphics packages") }
        Button({ LinuxSystem.run(ctx, "apt-get update && apt-get install -y --no-install-recommends ${LinuxSystem.XFCE_PACKAGES}") },
            enabled = LinuxSystem.installed && !LinuxSystem.running) { Text(if (hasXfce) "Reinstall XFCE desktop" else "Install XFCE desktop") }
        OutlinedButton({
            LinuxSystem.run(ctx, "apt-get update && for p in ${LinuxSystem.LOOK_PACKAGES}; do apt-get install -y --no-install-recommends \$p || echo \"NOT AVAILABLE: \$p\"; done")
        }, enabled = LinuxSystem.installed && !LinuxSystem.running) { Text("Install the nicer look (Ubuntu font, Papirus icons, Yaru theme)") }
        Button({ ctx.startActivity(android.content.Intent(ctx, DesktopActivity::class.java)) }, enabled = LinuxSystem.installed) {
            Text(if (hasXfce) "Start desktop" else "Start small test desktop (no XFCE yet)")
        }
        Text("To leave the desktop use the back gesture of Android.")
        if (X11Server.state != "stopped") Text("X server: ${X11Server.state} ${X11Server.detail}")

        Section("3. Packages: tap the ones to remove")
        val pkgReady = LinuxSystem.installed && !LinuxSystem.running
        val selected = remember { mutableStateListOf<String>() }
        var confirm by remember { mutableStateOf(false) }
        var reloadAfter by remember { mutableStateOf(false) }
        LaunchedEffect(LinuxSystem.running) {
            if (!LinuxSystem.running && reloadAfter) { reloadAfter = false; selected.clear(); LinuxSystem.loadPackages(ctx) }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button({ selected.clear(); LinuxSystem.loadPackages(ctx) }, enabled = pkgReady && !LinuxSystem.packagesLoading) {
                Text(if (LinuxSystem.packagesLoading) "Reading..." else "Show my packages")
            }
            OutlinedButton({ LinuxSystem.run(ctx, "apt-get clean; du -shx /usr /var /opt /root 2>/dev/null") }, enabled = pkgReady) { Text("Clean download cache") }
        }
        if (LinuxSystem.packages.isNotEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedButton({ selected.clear(); selected.addAll(LinuxSystem.packages.map { it.name }) }) { Text("Select all") }
                OutlinedButton({ selected.clear() }) { Text("Select none") }
            }
        }
        for (p in LinuxSystem.packages) {
            val on = p.name in selected
            Row(Modifier.fillMaxWidth().clickable { if (on) selected.remove(p.name) else selected.add(p.name) }.padding(vertical = 2.dp), verticalAlignment = Alignment.CenterVertically) {
                Checkbox(on, { if (it) selected.add(p.name) else selected.remove(p.name) })
                Text(p.name, Modifier.weight(1f))
                Text("%.1f MB".format(p.sizeKb / 1024.0), color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        if (LinuxSystem.packages.isNotEmpty()) {
            Button({ confirm = true }, enabled = pkgReady && selected.isNotEmpty(), colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)) {
                Text("Delete selected (${selected.size})")
            }
        }
        OutlinedButton({
            LinuxSystem.run(ctx, "apt-get purge -y ${LinuxSystem.XFCE_PACKAGES} && apt-get autoremove --purge -y && apt-get clean")
            reloadAfter = true
        }, enabled = pkgReady && hasXfce) { Text("Remove the whole XFCE desktop (you can install it again)") }
        if (confirm) {
            AlertDialog(
                onDismissRequest = { confirm = false },
                title = { Text("Delete ${selected.size} package(s)?") },
                text = { Text(selected.joinToString(", ") + "\n\nPackages only needed by them are removed too. Your files in /root are not touched.") },
                confirmButton = {
                    TextButton({
                        confirm = false
                        LinuxSystem.run(ctx, "apt-get purge -y ${selected.joinToString(" ")} && apt-get autoremove --purge -y && apt-get clean")
                        reloadAfter = true
                    }) { Text("Delete") }
                },
                dismissButton = { TextButton({ confirm = false }) { Text("Cancel") } },
            )
        }

        Section("4. Report for me")
        OutlinedTextField(note, { note = it }, label = { Text("Your note") }, modifier = Modifier.fillMaxWidth())
        Text(report, fontSize = 13.sp, style = MaterialTheme.typography.bodySmall)
        Button({
            val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            cm.setPrimaryClip(ClipData.newPlainText("LinuxPad report", report))
        }) { Text("Copy report") }
    }
}

@Composable
private fun Section(title: String) {
    Text(title, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(top = 10.dp))
}

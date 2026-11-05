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
        setContent { MaterialTheme(colorScheme = if (isSystemInDarkTheme()) darkColorScheme() else lightColorScheme()) { Surface { Calibration(Screens.read(this)) } } }
    }
}

@Composable
private fun Calibration(d: DisplayInfo) {
    val ctx = LocalContext.current
    val density = LocalDensity.current
    val prefs = remember { ctx.getSharedPreferences("linuxpad", android.content.Context.MODE_PRIVATE) }
    var comfort by remember { mutableFloatStateOf(prefs.getFloat("comfort", DisplayScale.DEFAULT_COMFORT)) }
    var diagonal by remember { mutableStateOf("12.1") }
    var taps by remember { mutableIntStateOf(0) }
    var misses by remember { mutableIntStateOf(0) }
    var note by remember { mutableStateOf("") }
    var selfTest by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    val plan = DisplayScale.plan(d, comfort, diagonal.toFloatOrNull())
    fun px(v: Int): androidx.compose.ui.unit.Dp = with(density) { v.toDp() }
    // A Linux font of N points is N * dpi / 72 pixels tall
    fun pt(points: Float): TextUnit = with(density) { (points * plan.xftDpi / 72f).toSp() }
    val ink = MaterialTheme.colorScheme.onSurface
    val report = buildString {
        appendLine("LinuxPad calibration report")
        appendLine("device: ${Build.MANUFACTURER} ${Build.MODEL}, Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
        appendLine("screen: ${d.widthPx}x${d.heightPx} px, ${"%.0f".format(d.refreshHz)} Hz, android dpi ${"%.1f".format(d.xdpi)}x${"%.1f".format(d.ydpi)}, densityDpi ${d.androidDensityDpi}")
        appendLine("diagonal entered: $diagonal in, measured ${"%.1f".format(plan.physicalPpi)} ppi")
        appendLine("size slider: ${"%.2f".format(comfort)} -> Xft.dpi ${plan.xftDpi}, factor ${"%.2f".format(plan.factor)}")
        appendLine("titlebar ${plan.titlebarPx}, row ${plan.rowPx}, cursor ${plan.cursorSize}, panel ${plan.panelSize}, icon ${plan.iconSize}, min touch ${plan.minTouchPx} px")
        appendLine("touch test: $taps hits, $misses misses")
        if (note.isNotBlank()) appendLine("note: $note")
        if (selfTest.isNotBlank()) appendLine("\n--- PRoot self-test ---\n$selfTest")
        appendLine("x11: ${X11Server.state} ${X11Server.detail}")
        if (LinuxSystem.output.isNotBlank()) appendLine("\n--- Debian ---\n${LinuxSystem.output.takeLast(3000)}")
        LinuxSystem.error?.let { appendLine("install error: $it") }
    }
    Column(Modifier.fillMaxSize().systemBarsPadding().verticalScroll(rememberScrollState()).padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("LinuxPad: display calibration", style = MaterialTheme.typography.headlineMedium)
        Text("Screen ${d.widthPx} x ${d.heightPx} px, ${"%.0f".format(d.refreshHz)} Hz. Android reports ${"%.0f".format(d.xdpi)} x ${"%.0f".format(d.ydpi)} dpi.")
        OutlinedTextField(diagonal, { diagonal = it }, label = { Text("Screen diagonal in inches (POCO Pad: 12.1)") }, singleLine = true)
        Text("Size: ${"%.2f".format(comfort)}  =>  Xft.dpi ${plan.xftDpi} (${"%.2f".format(plan.factor)}x)", style = MaterialTheme.typography.titleMedium)
        Slider(comfort, { comfort = it }, valueRange = 0.4f..1f, onValueChangeFinished = { prefs.edit().putFloat("comfort", comfort).apply() })

        Section("1. Desktop icon with its label (what you will see on the Linux desktop)")
        Row(horizontalArrangement = Arrangement.spacedBy(20.dp)) {
            for ((name, color) in listOf("Files" to Color(0xFF4F8EF7), "Terminal" to Color(0xFF3A3A3A), "Firefox" to Color(0xFFE8742A), "TeX" to Color(0xFF2E9E6A))) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(px(plan.iconSize * 3))) {
                    Box(Modifier.size(px(plan.iconSize)).clip(RoundedCornerShape(px(plan.iconSize / 6))).background(color), contentAlignment = Alignment.Center) {
                        Text(name.take(2), color = Color.White, fontSize = with(density) { (plan.iconSize * 0.45f).toSp() }, fontWeight = FontWeight.Bold)
                    }
                    Text(name, fontSize = pt(10f), textAlign = TextAlign.Center, maxLines = 1)
                }
            }
        }

        Section("2. Panel (XFCE bar): ${plan.panelSize} px high, icons ${plan.iconSize} px, clock text 10 pt")
        Row(Modifier.fillMaxWidth().height(px(plan.panelSize)).background(Color(0xFF2B2B33)).padding(horizontal = px(8)), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(px(10))) {
            for (c in listOf(Color(0xFF4F8EF7), Color(0xFFE8742A), Color(0xFF2E9E6A))) Box(Modifier.size(px(plan.iconSize)).clip(RoundedCornerShape(px(4))).background(c))
            Text("Applications", color = Color.White, fontSize = pt(10f))
            Spacer(Modifier.weight(1f))
            Text("Thu 5 Nov  14:32", color = Color.White, fontSize = pt(10f))
        }

        Section("3. Text at the usual sizes (points as Linux would draw them at ${plan.xftDpi} dpi)")
        for (points in listOf(8f, 9f, 10f, 11f, 12f, 14f)) {
            Text("${points.toInt()} pt   The quick brown fox 0123456789   سلام، این یک متن آزمایشی است   \u222B f d\u03BC  \u2264  \u2016x\u2016\u03A6", fontSize = pt(points), color = ink)
        }

        Section("4. Mouse cursor: ${plan.cursorSize} px")
        Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(20.dp)) {
            androidx.compose.foundation.Canvas(Modifier.size(px(plan.cursorSize))) {
                val s = size.minDimension
                val path = Path().apply { moveTo(0f, 0f); lineTo(0f, s * 0.85f); lineTo(s * 0.25f, s * 0.65f); lineTo(s * 0.45f, s * 0.95f); lineTo(s * 0.57f, s * 0.9f); lineTo(s * 0.37f, s * 0.6f); lineTo(s * 0.65f, s * 0.6f); close() }
                drawPath(path, Color.White); drawPath(path, Color.Black, style = androidx.compose.ui.graphics.drawscope.Stroke(width = s * 0.06f))
            }
            Text("compare with a normal Android pointer", fontSize = pt(10f))
        }

        Section("5. Touch test: tap the squares (${plan.minTouchPx} px = about 7 mm). Taps beside them count as misses.")
        Row(Modifier.fillMaxWidth().border(1.dp, ink.copy(alpha = 0.3f)).padding(px(plan.minTouchPx / 3)).clickable(indication = null, interactionSource = remember { androidx.compose.foundation.interaction.MutableInteractionSource() }) { misses++ }, horizontalArrangement = Arrangement.spacedBy(px(plan.minTouchPx / 3))) {
            repeat(5) { Box(Modifier.size(px(plan.minTouchPx)).background(MaterialTheme.colorScheme.secondaryContainer).clickable { taps++ }) }
        }
        Text("Hits: $taps    Misses: $misses")

        Section("6. PRoot self-test (runs the Linux sandbox engine on this device)")
        Button({ selfTest = "running..."; scope.launch { selfTest = withContext(Dispatchers.IO) { Proot.selfTest(ctx) } } }) { Text("Run PRoot self-test") }
        if (selfTest.isNotBlank()) Text(selfTest, fontSize = 13.sp, style = MaterialTheme.typography.bodySmall)

        Section("7. Debian (installed inside the app)")
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
                var cmd by remember { mutableStateOf("cat /etc/os-release | head -3; uname -m; id") }
                OutlinedTextField(cmd, { cmd = it }, label = { Text("Command to run inside Debian") }, modifier = Modifier.fillMaxWidth())
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button({ LinuxSystem.run(ctx, cmd) }, enabled = !LinuxSystem.running) { Text("Run") }
                    Button({ cmd = "apt-get update && apt-get install -y --no-install-recommends fastfetch" }, enabled = !LinuxSystem.running) { Text("apt test") }
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

        Section("8. Graphics test (first picture)")
        Text("Step 1 once, with the Debian above installed. Step 2 opens a full-screen desktop with xeyes and a terminal; use the system back gesture to leave.")
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button({ LinuxSystem.run(ctx, "apt-get update && apt-get install -y --no-install-recommends ${LinuxSystem.GRAPHICS_PACKAGES}") },
                enabled = LinuxSystem.installed && !LinuxSystem.running) { Text("1. Install graphics packages") }
            Button({ ctx.startActivity(android.content.Intent(ctx, DesktopActivity::class.java)) },
                enabled = LinuxSystem.installed) { Text("2. Start desktop test") }
        }
        Button({ LinuxSystem.run(ctx, "apt-get update && apt-get install -y --no-install-recommends ${LinuxSystem.XFCE_PACKAGES}") },
            enabled = LinuxSystem.installed && !LinuxSystem.running) { Text("3. Install XFCE desktop (150 to 300 MB, keep the app open)") }
        Text(if (LinuxSystem.hasXfce(ctx)) "XFCE is installed: step 2 now starts the full desktop." else "XFCE is not installed: step 2 starts the small test (terminal and editor).")
        if (X11Server.state != "stopped") Text("X server: ${X11Server.state} ${X11Server.detail}")

        Section("9. Packages: tap the ones to remove")
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
        }, enabled = pkgReady && LinuxSystem.hasXfce(ctx)) { Text("Remove the whole XFCE desktop (you can install it again)") }
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

        Section("10. Send me the result")
        OutlinedTextField(note, { note = it }, label = { Text("Your note (too small? too big? blurry?)") }, modifier = Modifier.fillMaxWidth())
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

package app.linuxpad.ui

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.NavigationRailItemDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.linuxpad.DesktopActivity
import app.linuxpad.MainActivity
import app.linuxpad.audio.AudioServer
import app.linuxpad.display.DisplayInfo
import app.linuxpad.display.DisplayScale
import app.linuxpad.runtime.LinuxSystem
import app.linuxpad.runtime.SharedFolder
import app.linuxpad.x11.X11Server

@Composable
fun AppRoot(d: DisplayInfo) {
    val ctx = LocalContext.current
    var tab by rememberSaveable { mutableIntStateOf(0) }
    LaunchedEffect(Unit) { LinuxSystem.refresh(ctx) }
    Row(Modifier.fillMaxSize().background(androidx.compose.ui.graphics.Brush.verticalGradient(listOf(Bg, Color(0xFF2A0F2A)))).systemBarsPadding()) {
        NavigationRail(containerColor = Rail, modifier = Modifier.fillMaxHeight().width(132.dp)) {
            BrandMark()
            val items = listOf("Desktop" to Icons.Filled.PlayArrow, "Setup" to Icons.Filled.Build, "Storage" to Icons.Filled.Menu, "Settings" to Icons.Filled.Settings)
            items.forEachIndexed { i, (label, icon) ->
                NavigationRailItem(
                    selected = tab == i, onClick = { tab = i },
                    icon = { Icon(icon, contentDescription = label) },
                    label = { Text(label, fontSize = 13.sp) },
                    colors = NavigationRailItemDefaults.colors(selectedIconColor = Accent, selectedTextColor = Accent, indicatorColor = Color(0x33E95420), unselectedIconColor = TextMuted, unselectedTextColor = TextMuted),
                    modifier = Modifier.padding(vertical = 6.dp),
                )
            }
        }
        Box(Modifier.weight(1f).fillMaxHeight()) {
            Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 28.dp, vertical = 24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                when (tab) {
                    0 -> DesktopScreen(goSetup = { tab = 1 })
                    1 -> SetupScreen()
                    2 -> StorageScreen()
                    else -> SettingsScreen(d)
                }
            }
        }
    }
}

private fun allReady(ctx: Context) = LinuxSystem.installed && LinuxSystem.graphicsOk(ctx) && LinuxSystem.hasXfce(ctx)

@Composable
private fun DesktopScreen(goSetup: () -> Unit) {
    val ctx = LocalContext.current
    val tick = LinuxSystem.tick
    val ready = remember(tick, LinuxSystem.installed) { allReady(ctx) }
    ScreenTitle("Linux desktop")
    val session = LinuxSystem.session
    AppCard("Desktop", chip = {
        when {
            !ready -> StatusChip("Setup needed", Warn)
            session == "running" -> StatusChip("Running", Ok)
            session == "starting" -> StatusChip("Starting", Accent)
            else -> StatusChip("Ready", Ok)
        }
    }) {
        if (!ready) {
            Muted("The Linux system and the desktop are not installed yet. One button in Setup installs everything.")
            BigButton("Go to Setup", onClick = goSetup)
        } else {
            Muted(when (session) {
                "running" -> "The desktop keeps running in the background when you leave it. A notification lets you come back or stop it."
                "starting" -> "Starting the X server and the desktop. This takes a few seconds."
                else -> "Debian with the XFCE desktop, sized for this screen."
            })
            if (session == "starting") LinearProgressIndicator(Modifier.fillMaxWidth())
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                BigButton(if (session == "stopped") "Start desktop" else "Open desktop", onClick = { ctx.startActivity(Intent(ctx, DesktopActivity::class.java)) })
                if (session != "stopped") OutlinedBigButton("Stop desktop", onClick = { LinuxSystem.stopSession(ctx) })
            }
        }
        LinuxSystem.error?.let { Text(it, color = Err, fontSize = 15.sp) }
    }
    AppCard("Sound", chip = {
        when (AudioServer.state) {
            "running" -> StatusChip("On", Ok)
            "starting" -> StatusChip("Starting", Accent)
            "unavailable" -> StatusChip("Unavailable", Err)
            else -> StatusChip("Off", TextMuted)
        }
    }) {
        Muted(if (AudioServer.detail.isNotBlank()) AudioServer.detail.replaceFirstChar { it.uppercase() } else "Sound starts together with the desktop. Choose speaker and microphone in Settings.")
    }
    SharedFolderCard()
}

@Composable
private fun SharedFolderCard() {
    val ctx = LocalContext.current
    val ok = remember(MainActivity.resumes) { SharedFolder.hasAccess() }
    AppCard("Shared folder", chip = { if (ok) StatusChip("Ready", Ok) else StatusChip("Needs permission", Warn) }) {
        Muted(if (ok) "Android: internal storage, folder ${SharedFolder.NAME}.  Linux: the icon Shared on the desktop. Nothing else of the tablet's storage is visible to Linux."
              else "Android asks for \"All files access\" before an app can create a folder in the internal storage. Linux will see only the folder ${SharedFolder.NAME}.")
        if (!ok) BigButton("Allow access to files", onClick = { ctx.startActivity(SharedFolder.accessIntent(ctx)) })
    }
}

@Composable
private fun SetupScreen() {
    val ctx = LocalContext.current
    val tick = LinuxSystem.tick
    val st = LinuxSystem.setupState
    var details by remember { mutableStateOf(false) }
    val debian = LinuxSystem.installed
    val graphics = remember(tick, debian) { LinuxSystem.graphicsOk(ctx) }
    val xfce = remember(tick, debian) { LinuxSystem.hasXfce(ctx) }
    val look = remember(tick, debian) { LinuxSystem.lookOk(ctx) }
    val missing = !(debian && graphics && xfce)
    ScreenTitle("Setup")
    AppCard("Install the desktop") {
        StepRow("Linux system (Debian 13)", debian)
        StepRow("Graphics and sound libraries", graphics)
        StepRow("XFCE desktop", xfce)
        StepRow("Nicer look: fonts, icons, theme", look, optional = true)
        if (st.running) {
            Spacer(Modifier.height(4.dp))
            LinearProgressIndicator(progress = { st.fraction }, modifier = Modifier.fillMaxWidth().height(8.dp))
            Row(Modifier.fillMaxWidth()) {
                Text(st.label, color = TextMain, fontSize = 15.sp, modifier = Modifier.weight(1f), maxLines = 1)
                Text("${(st.fraction * 100).toInt()}%", color = TextMuted, fontSize = 15.sp)
            }
            Muted("It keeps running if you leave the app. Installing takes a while the first time: about 10 to 20 minutes.")
        } else {
            st.error?.let { Text(it, color = Err, fontSize = 15.sp) }
            if (!missing && st.error == null) Muted("Everything is installed.")
            BigButton(if (missing || !look) "Set up" else "Set up again (repair)", onClick = { LinuxSystem.setup(ctx) }, enabled = !LinuxSystem.running)
        }
    }
    AppCard("Details") {
        Muted("The technical output of the installation, for troubleshooting.")
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            OutlinedBigButton(if (details) "Hide details" else "Show details", onClick = { details = !details })
            OutlinedBigButton("Copy", onClick = { copy(ctx, "LinuxPad details", LinuxSystem.output.takeLast(8000)) })
        }
        if (details) Text(LinuxSystem.output.takeLast(4000).ifBlank { "(nothing yet)" }, color = TextMuted, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
    }
}

@Composable
private fun StepRow(label: String, done: Boolean, optional: Boolean = false) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, color = TextMain, fontSize = 16.sp, modifier = Modifier.weight(1f))
        if (done) StatusChip("Installed", Ok) else StatusChip(if (optional) "Optional" else "Missing", if (optional) TextMuted else Warn)
    }
}

@Composable
private fun StorageScreen() {
    val ctx = LocalContext.current
    ScreenTitle("Storage")
    SharedFolderCard()
    val ready = LinuxSystem.installed && !LinuxSystem.running && !LinuxSystem.setupState.running
    val selected = remember { mutableStateListOf<String>() }
    var confirm by remember { mutableStateOf(false) }
    var confirmAll by remember { mutableStateOf(false) }
    var reloadAfter by remember { mutableStateOf(false) }
    LaunchedEffect(LinuxSystem.running) { if (!LinuxSystem.running && reloadAfter) { reloadAfter = false; selected.clear(); LinuxSystem.loadPackages(ctx) } }
    AppCard("Programs and packages") {
        Muted("Tap the ones you want to remove. System parts that Linux needs are never listed.")
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            BigButton(if (LinuxSystem.packagesLoading) "Reading..." else "Show my packages", onClick = { selected.clear(); LinuxSystem.loadPackages(ctx) }, enabled = ready && !LinuxSystem.packagesLoading)
            OutlinedBigButton("Clean download cache", onClick = { LinuxSystem.run(ctx, "apt-get clean") }, enabled = ready)
        }
        if (LinuxSystem.packages.isNotEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedBigButton("Select all", onClick = { selected.clear(); selected.addAll(LinuxSystem.packages.map { it.name }) })
                OutlinedBigButton("Select none", onClick = { selected.clear() })
            }
            for (p in LinuxSystem.packages) {
                val on = p.name in selected
                Row(Modifier.fillMaxWidth().clickable { if (on) selected.remove(p.name) else selected.add(p.name) }.padding(vertical = 2.dp), verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(on, { if (it) selected.add(p.name) else selected.remove(p.name) })
                    Text(p.name, color = TextMain, modifier = Modifier.weight(1f))
                    Text("%.1f MB".format(p.sizeKb / 1024.0), color = TextMuted)
                }
            }
            BigButton("Delete selected (${selected.size})", onClick = { confirm = true }, enabled = ready && selected.isNotEmpty(), danger = true)
        }
    }
    AppCard("Remove everything") {
        Muted("Deletes the Linux system with every program and every file inside it (not the shared folder). You can set it up again afterwards.")
        BigButton("Delete Linux and everything in it", onClick = { confirmAll = true }, enabled = LinuxSystem.installed && !LinuxSystem.running && !LinuxSystem.setupState.running, danger = true)
    }
    if (confirm) AlertDialog(
        onDismissRequest = { confirm = false },
        title = { Text("Delete ${selected.size} package(s)?") },
        text = { Text(selected.joinToString(", ") + "\n\nPackages only needed by them are removed too. Your files in /root are not touched.") },
        confirmButton = { TextButton({ confirm = false; LinuxSystem.run(ctx, "apt-get purge -y ${selected.joinToString(" ")} && apt-get autoremove --purge -y && apt-get clean"); reloadAfter = true }) { Text("Delete") } },
        dismissButton = { TextButton({ confirm = false }) { Text("Cancel") } },
    )
    if (confirmAll) AlertDialog(
        onDismissRequest = { confirmAll = false },
        title = { Text("Delete Linux and everything in it?") },
        text = { Text("Every program and every file you made inside Linux (the folder /root included) will be erased. This cannot be undone.") },
        confirmButton = { TextButton({ confirmAll = false; LinuxSystem.remove(ctx) }) { Text("Delete everything", color = Err) } },
        dismissButton = { TextButton({ confirmAll = false }) { Text("Cancel") } },
    )
}

@Composable
private fun SettingsScreen(d: DisplayInfo) {
    val ctx = LocalContext.current
    ScreenTitle("Settings")
    var out by remember { mutableStateOf(AudioServer.outputEnabled(ctx)) }
    var mic by remember { mutableStateOf(AudioServer.micEnabled(ctx) && AudioServer.micPermitted(ctx)) }
    val micLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted -> mic = granted; AudioServer.setMic(ctx, granted) }
    val notifLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { }
    AppCard("Sound") {
        SwitchRow("Speaker and headphones", out) { out = it; AudioServer.setOutput(ctx, it) }
        SwitchRow("Microphone", mic) { on ->
            if (on && !AudioServer.micPermitted(ctx)) micLauncher.launch(Manifest.permission.RECORD_AUDIO) else { mic = on; AudioServer.setMic(ctx, on) }
        }
        Muted("Changes apply the next time the desktop starts. Android shows its microphone indicator while the microphone is on.")
    }
    val notif = remember(MainActivity.resumes) { Build.VERSION.SDK_INT < 33 || ctx.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == android.content.pm.PackageManager.PERMISSION_GRANTED }
    AppCard("Keep running in the background", chip = { if (notif) StatusChip("Notifications on", Ok) else StatusChip("Notifications off", Warn) }) {
        Muted("The desktop and installations run as a foreground service, with a notification to open or stop them.")
        if (!notif) OutlinedBigButton("Allow notifications", onClick = { notifLauncher.launch(Manifest.permission.POST_NOTIFICATIONS) })
        Muted("On Android 12 and newer, the system can still stop the Linux programs of an app. If the desktop closes by itself in the background, turn on \"Disable child process restrictions\" in the Developer options of Android (open Settings, About tablet, tap Build number 7 times to show Developer options).")
        OutlinedBigButton("Open Developer options", onClick = {
            runCatching { ctx.startActivity(Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)) }.onFailure { ctx.startActivity(Intent(Settings.ACTION_SETTINGS)) }
        })
    }
    val plan = DisplayScale.plan(d)
    AppCard("Screen") {
        Muted("${d.widthPx} x ${d.heightPx} px, ${"%.0f".format(d.refreshHz)} Hz, ${"%.0f".format(plan.physicalPpi)} ppi.  Text ${plan.xftDpi} dpi, pointer ${plan.cursorSize} px, interface scale 2x. These values were chosen on this tablet.")
    }
    val version = remember { runCatching { ctx.packageManager.getPackageInfo(ctx.packageName, 0).versionName }.getOrNull() ?: "?" }
    AppCard("About") {
        Muted("LinuxPad $version")
        OutlinedBigButton("Copy diagnostics", onClick = {
            val text = buildString {
                appendLine("LinuxPad $version  ${Build.MANUFACTURER} ${Build.MODEL}, Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
                appendLine("screen ${d.widthPx}x${d.heightPx} ${"%.0f".format(d.refreshHz)} Hz ${"%.1f".format(plan.physicalPpi)} ppi -> Xft.dpi ${plan.xftDpi}, cursor ${plan.cursorSize}")
                appendLine("debian ${LinuxSystem.installed}, graphics ${LinuxSystem.graphicsOk(ctx)}, xfce ${LinuxSystem.hasXfce(ctx)}, look ${LinuxSystem.lookOk(ctx)}")
                appendLine("xfce parts: ${LinuxSystem.xfceStatus(ctx)}")
                appendLine("session ${LinuxSystem.session}, x11 ${X11Server.state} ${X11Server.detail}")
                appendLine("audio ${AudioServer.state} ${AudioServer.detail}")
                appendLine("shared folder access ${SharedFolder.hasAccess()}")
                LinuxSystem.error?.let { appendLine("error: $it") }
                LinuxSystem.setupState.error?.let { appendLine("setup error: $it") }
                appendLine("\n--- output ---\n${LinuxSystem.output.takeLast(3000)}")
            }
            copy(ctx, "LinuxPad diagnostics", text)
        })
    }
}

@Composable
private fun SwitchRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().clickable { onChange(!checked) }.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(label, color = TextMain, fontSize = 17.sp, modifier = Modifier.weight(1f))
        Switch(checked, onChange)
    }
}

@Composable
private fun BigButton(text: String, onClick: () -> Unit, enabled: Boolean = true, danger: Boolean = false) {
    Button(onClick, enabled = enabled, shape = RoundedCornerShape(27.dp), modifier = Modifier.height(54.dp),
        colors = if (danger) ButtonDefaults.buttonColors(containerColor = Err, contentColor = Color(0xFF200A0A)) else ButtonDefaults.buttonColors()) {
        Text(text, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun OutlinedBigButton(text: String, onClick: () -> Unit, enabled: Boolean = true) {
    OutlinedButton(onClick, enabled = enabled, shape = RoundedCornerShape(27.dp), modifier = Modifier.height(54.dp)) { Text(text, fontSize = 16.sp) }
}

private fun copy(ctx: Context, label: String, text: String) {
    (ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText(label, text))
}

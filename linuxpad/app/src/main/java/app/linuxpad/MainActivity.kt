package app.linuxpad

import android.app.Activity
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.linuxpad.display.DisplayInfo
import app.linuxpad.display.DisplayScale

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme(colorScheme = if (isSystemInDarkTheme()) darkColorScheme() else lightColorScheme()) { Surface { Calibration(readDisplay(this)) } } }
    }
}

private fun readDisplay(a: Activity): DisplayInfo {
    val b = a.getSystemService(WindowManager::class.java).maximumWindowMetrics.bounds
    val dm = a.resources.displayMetrics
    return DisplayInfo(b.width(), b.height(), dm.xdpi, dm.ydpi, dm.densityDpi, a.display?.refreshRate ?: 60f)
}

@Composable
private fun Calibration(d: DisplayInfo) {
    var comfort by remember { mutableFloatStateOf(DisplayScale.DEFAULT_COMFORT) }
    var diagonal by remember { mutableStateOf("") }
    val plan = DisplayScale.plan(d, comfort, diagonal.toFloatOrNull())
    Column(Modifier.fillMaxSize().systemBarsPadding().verticalScroll(rememberScrollState()).padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("LinuxPad: display calibration", style = MaterialTheme.typography.headlineMedium)
        Text("Screen ${d.widthPx} x ${d.heightPx} px, ${"%.0f".format(d.refreshHz)} Hz. Android reports ${"%.0f".format(d.xdpi)} x ${"%.0f".format(d.ydpi)} dpi.")
        OutlinedTextField(diagonal, { diagonal = it }, label = { Text("Screen diagonal in inches (optional, POCO Pad: 12.1)") }, singleLine = true)
        Text("Size: ${"%.2f".format(comfort)} (1.00 = same physical size as a 96 dpi desktop monitor)")
        Slider(comfort, { comfort = it }, valueRange = 0.4f..1f)
        Text("Measured ${"%.0f".format(plan.physicalPpi)} ppi", style = MaterialTheme.typography.titleMedium)
        Text("Xft.dpi ${plan.xftDpi}  (scale ${"%.2f".format(plan.factor)}x)\nQT_SCALE_FACTOR ${plan.qtScaleFactor}, GDK_SCALE ${plan.gtkScale}\nCursor ${plan.cursorSize} px, panel ${plan.panelSize} px, icons ${plan.iconSize} px\nMinimum touch target ${plan.minTouchPx} px\nLinux desktop: ${plan.guestWidth} x ${plan.guestHeight} (native, sharp)")
        Text("Preview of sizes in real pixels at this scale:")
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Surface(color = MaterialTheme.colorScheme.primaryContainer, modifier = Modifier.size(with(androidx.compose.ui.platform.LocalDensity.current) { plan.iconSize.toDp() })) {}
            Surface(color = MaterialTheme.colorScheme.secondaryContainer, modifier = Modifier.size(with(androidx.compose.ui.platform.LocalDensity.current) { plan.minTouchPx.toDp() })) {}
        }
    }
}

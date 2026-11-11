package ir.taghvim.app.ui

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.key
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.zIndex
import androidx.core.content.ContextCompat
import ir.taghvim.app.data.AppSettings
import ir.taghvim.app.data.Prefs
import ir.taghvim.app.widget.Palettes
import ir.taghvim.app.widget.Widgets
import ir.taghvim.app.work.Schedule
import ir.taghvim.core.Category
import ir.taghvim.core.Cities
import kotlinx.coroutines.launch
import java.util.Collections
import kotlin.math.roundToInt

private val navy = Color(0xFF0B1730)
private val navy2 = Color(0xFF1B2C52)
private val ink = Color.White
private val mute = Color(0xFF9FB0CF)
private val gold = Color(0xFFF5C518)

class SettingsActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Schedule.ensure(this)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme(primary = gold, background = navy, surface = navy2, onSurface = ink)) {
                CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
                    SettingsScreen()
                }
            }
        }
    }
}

private val categoryLabels = mapOf(
    Category.OFFICIAL to "تعطیلات رسمی",
    Category.RELIGIOUS to "مذهبی غیرتعطیل (قمری)",
    Category.NATIONAL to "ملی و روزهای خاص",
    Category.GLOBAL to "جهانی و میلادی",
)
private val categoryColors = mapOf(
    Category.OFFICIAL to gold,
    Category.RELIGIOUS to Color(0xFFA593FF),
    Category.NATIONAL to Color(0xFF5BC0EB),
    Category.GLOBAL to Color(0xFF6FD08A),
)

@Composable
fun SettingsScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var settings by remember { mutableStateOf<AppSettings?>(null) }
    var message by remember { mutableStateOf("") }
    LaunchedEffect(Unit) { settings = Prefs.load(context) }
    val s = settings ?: return Box(Modifier.fillMaxWidth().height(1.dp).background(navy))

    fun change(f: (AppSettings) -> AppSettings) {
        val next = f(s)
        settings = next
        scope.launch {
            Prefs.save(context, next)
            Widgets.updateAll(context)
        }
    }

    fun locate() {
        val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val fix = listOf(LocationManager.NETWORK_PROVIDER, LocationManager.GPS_PROVIDER, LocationManager.PASSIVE_PROVIDER)
            .mapNotNull { runCatching { lm.getLastKnownLocation(it) }.getOrNull() }
            .maxByOrNull { it.time }
        if (fix == null) {
            message = "مکان گوشی هنوز مشخص نیست. مکان‌یاب را روشن کنید یا شهر را دستی انتخاب کنید."
        } else {
            val c = Cities.nearest(fix.latitude, fix.longitude)
            change { it.copy(province = c.province, city = c.name) }
            message = "نزدیک‌ترین شهر انتخاب شد: ${c.name}، ${c.province}"
        }
    }

    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) locate() else message = "اجازه مکان داده نشد. شهر را دستی انتخاب کنید."
    }

    Column(
        Modifier.background(navy).statusBarsPadding().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text("تنظیمات", color = ink, fontSize = 24.sp)

        Section("مکان")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Picker("استان", s.province, Cities.provinces, Modifier.weight(1f)) { p ->
                val first = Cities.inProvince(p).first()
                change { it.copy(province = p, city = first.name) }
            }
            Picker("شهر", s.city, Cities.inProvince(s.province).map { it.name }, Modifier.weight(1f)) { c ->
                change { it.copy(city = c) }
            }
        }
        Button(onClick = {
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED) locate()
            else permission.launch(Manifest.permission.ACCESS_COARSE_LOCATION)
        }) { Text("تشخیص مکان من") }
        if (message.isNotEmpty()) Text(message, color = mute, fontSize = 13.sp)

        Section("اولویت مناسبت‌ها (دسته را بکشید)")
        OrderList(s.order, s.enabled, onOrder = { o -> change { it.copy(order = o) } }, onToggle = { c ->
            change { it.copy(enabled = if (c in it.enabled) it.enabled - c else it.enabled + c) }
        })
        ToggleRow("پس‌زمینه ویژه مناسبت‌ها", s.specialBackgrounds) { v -> change { it.copy(specialBackgrounds = v) } }

        Section("تقویم")
        Label("خط دوم زیر روز")
        Chips(listOf("none" to "هیچ", "hijri" to "قمری", "greg" to "میلادی"), s.secondary) { v -> change { it.copy(secondary = v) } }
        Label("اصلاح رؤیت هلال")
        Chips(listOf(-1 to "۱ روز زودتر", 0 to "طبق محاسبه", 1 to "۱ روز دیرتر"), s.hijriShift) { v -> change { it.copy(hijriShift = v) } }
        OutlinedButton(onClick = { Schedule.syncHolidaysNow(context); message = "به‌روزرسانی تعطیلات شروع شد. اگر اینترنت وصل باشد، فهرست رسمی سال جاری و بعد دریافت می‌شود." }) {
            Text("به‌روزرسانی تعطیلات")
        }

        Section("ظاهر ویجت")
        Label("تم")
        Chips(listOf("dark" to "تیره", "light" to "روشن", "system" to "مثل سیستم"), s.theme) { v -> change { it.copy(theme = v) } }
        Label("رنگ تأکید")
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Palettes.accentSwatches.forEach { (name, color) ->
                Box(
                    Modifier.size(34.dp).clip(CircleShape).background(color)
                        .border(if (s.accent == name) 3.dp else 0.dp, ink, CircleShape)
                        .clickable { change { it.copy(accent = name) } },
                )
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun Section(text: String) {
    Spacer(Modifier.height(8.dp))
    Text(text, color = gold, fontSize = 15.sp)
}

@Composable
private fun Label(text: String) = Text(text, color = mute, fontSize = 13.sp)

@Composable
private fun <T> Chips(options: List<Pair<T, String>>, selected: T, onSelect: (T) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        options.forEach { (value, label) ->
            FilterChip(selected = value == selected, onClick = { onSelect(value) }, label = { Text(label) })
        }
    }
}

@Composable
private fun ToggleRow(text: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(navy2).padding(horizontal = 14.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(text, color = ink, modifier = Modifier.weight(1f))
        Switch(checked = checked, onCheckedChange = onChange)
    }
}

@Composable
private fun Picker(label: String, value: String, items: List<String>, modifier: Modifier, onPick: (String) -> Unit) {
    var open by remember { mutableStateOf(false) }
    Column(modifier) {
        Label(label)
        Box {
            OutlinedButton(onClick = { open = true }, modifier = Modifier.fillMaxWidth()) { Text(value, maxLines = 1) }
            DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                items.forEach { item ->
                    DropdownMenuItem(text = { Text(item) }, onClick = { open = false; onPick(item) })
                }
            }
        }
    }
}

/** The four groups in priority order. Hold the handle and drag a row up or down. */
@Composable
private fun OrderList(order: List<Category>, enabled: Set<Category>, onOrder: (List<Category>) -> Unit, onToggle: (Category) -> Unit) {
    val rowHeight = 56.dp
    val rowPx = with(LocalDensity.current) { rowHeight.toPx() }
    var items by remember(order) { mutableStateOf(order) }
    var dragging by remember { mutableStateOf<Category?>(null) }
    var dy by remember { mutableStateOf(0f) }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items.forEach { c ->
            key(c) {
                val lifted = dragging == c
                Row(
                    Modifier
                        .fillMaxWidth().height(rowHeight)
                        .offset { IntOffset(0, if (lifted) dy.roundToInt() else 0) }
                        .zIndex(if (lifted) 1f else 0f)
                        .clip(RoundedCornerShape(14.dp))
                        .background(if (lifted) Color(0xFF26407A) else navy2)
                        .padding(horizontal = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Text(
                        "⠿", color = mute, fontSize = 22.sp,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 10.dp).pointerInput(c) {
                            detectVerticalDragGestures(
                                onDragStart = { dragging = c; dy = 0f },
                                onDragEnd = { dragging = null; dy = 0f; onOrder(items) },
                                onDragCancel = { dragging = null; dy = 0f; items = order },
                                onVerticalDrag = { change, amount ->
                                    change.consume()
                                    dy += amount
                                    val i = items.indexOf(c)
                                    if (dy > rowPx / 2 && i < items.lastIndex) {
                                        items = items.toMutableList().also { Collections.swap(it, i, i + 1) }
                                        dy -= rowPx + 8f
                                    } else if (dy < -rowPx / 2 && i > 0) {
                                        items = items.toMutableList().also { Collections.swap(it, i, i - 1) }
                                        dy += rowPx + 8f
                                    }
                                },
                            )
                        },
                    )
                    Box(Modifier.size(10.dp).clip(CircleShape).background(categoryColors.getValue(c)))
                    Text(categoryLabels.getValue(c), color = ink, modifier = Modifier.weight(1f))
                    Switch(checked = c in enabled, onCheckedChange = { onToggle(c) })
                }
            }
        }
    }
}

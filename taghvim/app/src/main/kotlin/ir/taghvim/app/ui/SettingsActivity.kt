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
import androidx.compose.foundation.layout.fillMaxSize
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
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import androidx.core.content.ContextCompat
import androidx.compose.foundation.text.BasicText
import ir.taghvim.app.data.AppSettings
import ir.taghvim.app.data.Holidays
import ir.taghvim.app.data.Prefs
import ir.taghvim.app.data.fa
import ir.taghvim.app.widget.DateLines
import ir.taghvim.app.widget.IRAN
import ir.taghvim.app.widget.OccasionLines
import ir.taghvim.app.widget.Palettes
import ir.taghvim.app.widget.Widgets
import ir.taghvim.app.work.Schedule
import ir.taghvim.core.Category
import ir.taghvim.core.Cities
import ir.taghvim.core.JalaliDate
import ir.taghvim.core.Level
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.util.Collections
import kotlin.math.roundToInt

private val navy = Color(0xFF0B1730)
private val navy2 = Color(0xFF13224A)
private val chip = Color(0xFF1B2C52)
private val ink = Color.White
private val mute = Color(0xFF9FB0CF)
private val gold = Color(0xFFF5C518)
private val edge = Color(0xFF3A548F)

private val LocalFont = compositionLocalOf<FontFamily> { FontFamily.Default }

class SettingsActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Schedule.ensure(this)
        setContent {
            val font = FontFamily(
                Font("fonts/Vazirmatn-Regular.ttf", assets, FontWeight.Normal),
                Font("fonts/Vazirmatn-Medium.ttf", assets, FontWeight.Medium),
                Font("fonts/Vazirmatn-Bold.ttf", assets, FontWeight.Bold),
            )
            MaterialTheme(colorScheme = darkColorScheme(primary = gold, background = navy, surface = navy2, onSurface = ink)) {
                CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl, LocalFont provides font) {
                    SettingsScreen()
                }
            }
        }
    }
}

/** Text in the app font (Vazirmatn). */
@Composable
private fun Tx(text: String, size: Float = 14f, color: Color = ink, weight: FontWeight = FontWeight.Normal, modifier: Modifier = Modifier, maxLines: Int = Int.MAX_VALUE) {
    BasicText(
        text,
        modifier = modifier,
        maxLines = maxLines,
        style = TextStyle(color = color, fontSize = size.sp, fontWeight = weight, fontFamily = LocalFont.current, lineHeight = (size * 1.55f).sp),
    )
}

private class Group(val category: Category, val title: String, val description: String, val color: Color, val levels: List<Pair<Level, String>>)

private val offOn = listOf(Level.OFF to "خاموش", Level.ALL to "روشن")
private val offImpAll = listOf(Level.OFF to "خاموش", Level.IMPORTANT to "مهم‌ها", Level.ALL to "همه")
private val groups = listOf(
    Group(Category.OFFICIAL, "تعطیلات رسمی", "ملی و قمری: نوروز، ۲۲ بهمن، تاسوعا، عید فطر ...", gold, offOn),
    Group(Category.RELIGIOUS, "مناسبت‌های مذهبی", "قمری و غیرتعطیل: شب‌های قدر، روز مادر، عرفه ...", Color(0xFFA593FF), offImpAll),
    Group(Category.NATIONAL, "مناسبت‌های ملی", "روز معلم، شب یلدا، بزرگداشت‌ها، روزهای شهرها", Color(0xFF5BC0EB), offImpAll),
    Group(Category.GLOBAL, "جهانی و میلادی", "کریسمس، ولنتاین، روزهای جهانی سازمان ملل", Color(0xFF6FD08A), offImpAll),
).associateBy { it.category }

@Composable
fun SettingsScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var settings by remember { mutableStateOf<AppSettings?>(null) }
    var message by remember { mutableStateOf("اوقات شرعی برای همین شهر حساب می‌شود.") }
    var updateMessage by remember { mutableStateOf("") }
    LaunchedEffect(Unit) { settings = Prefs.load(context) }
    val s = settings ?: return Box(Modifier.fillMaxSize().background(navy))

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
        Modifier.fillMaxSize().background(navy).statusBarsPadding().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Tx("تنظیمات", 26f, ink, FontWeight.Bold)
        Tx("هر تغییر همان لحظه روی ویجت‌ها اثر می‌گذارد.", 13f, mute)

        Preview(s)

        SectionTitle("مکان")
        Card {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                Picker("استان", s.province, Cities.provinces, Modifier.weight(1f)) { p ->
                    change { it.copy(province = p, city = Cities.inProvince(p).first().name) }
                }
                Picker("شهر", s.city, Cities.inProvince(s.province).map { it.name }, Modifier.weight(1f)) { c ->
                    change { it.copy(city = c) }
                }
            }
            Button("تشخیص مکان من", filled = false) {
                if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED) locate()
                else permission.launch(Manifest.permission.ACCESS_COARSE_LOCATION)
            }
            Tx(message, 12.5f, mute)
        }

        SectionTitle("مناسبت‌ها")
        GroupList(
            order = s.order,
            levels = s.levels,
            onOrder = { o -> change { it.copy(order = o) } },
            onLevel = { c, l -> change { it.copy(levels = it.levels + (c to l)) } },
        )
        Card {
            SwitchRow("پس‌زمینه ویژه مناسبت‌ها", "نوروز، تاسوعا، کریسمس و ... رنگ مخصوص خودشان را می‌گیرند", s.specialBackgrounds) { v ->
                change { it.copy(specialBackgrounds = v) }
            }
        }

        SectionTitle("تقویم")
        Card {
            Label("خط دوم زیر روزها")
            Segmented(listOf("none" to "هیچ", "hijri" to "قمری", "greg" to "میلادی"), s.secondary) { v -> change { it.copy(secondary = v) } }
            Label("تاریخ قمری امروز")
            LunarStepper(s.hijriShift) { v -> change { it.copy(hijriShift = v) } }
            Button("به‌روزرسانی تعطیلات", filled = false) {
                Schedule.syncHolidaysNow(context)
                updateMessage = "دریافت فهرست رسمی تعطیلات سال جاری و بعد شروع شد. اگر اینترنت وصل باشد، به‌زودی به‌روز می‌شود."
            }
            if (updateMessage.isNotEmpty()) Tx(updateMessage, 12.5f, mute)
        }

        SectionTitle("ظاهر ویجت")
        Card {
            Label("تم")
            Segmented(listOf("dark" to "تیره", "light" to "روشن", "system" to "مثل سیستم"), s.theme) { v -> change { it.copy(theme = v) } }
            Label("رنگ تأکید")
            Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                Palettes.accentSwatches.forEach { (name, color) ->
                    Box(
                        Modifier.size(36.dp).clip(CircleShape).background(color)
                            .border(if (s.accent == name) 3.dp else 0.dp, ink, CircleShape)
                            .clickable { change { it.copy(accent = name) } },
                    )
                }
            }
        }
        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) { Tx("تقویم · نسخه ۰٫۱", 12f, mute) }
        Spacer(Modifier.height(20.dp))
    }
}

@Composable
private fun SectionTitle(text: String) = Tx(text, 12.5f, gold, FontWeight.Medium, Modifier.padding(start = 4.dp, top = 6.dp))

@Composable
private fun Label(text: String) = Tx(text, 12.5f, mute)

@Composable
private fun Card(content: @Composable () -> Unit) {
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp)).background(navy2).padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) { content() }
}

/** What the widget will say under the calendar with the current settings. */
@Composable
private fun Preview(s: AppSettings) {
    val context = LocalContext.current
    val light = !Palettes.isDark(context, s)
    val bg = if (light) Color(0xFFF8FAFD) else navy
    val fg = if (light) Color(0xFF0B1730) else ink
    val sub = if (light) Color(0xFF5D6B88) else mute
    val chipBg = if (light) Color(0xFFE1E8F4) else chip
    val accent = Palettes.accentSwatches[s.accent] ?: gold
    val today = LocalDate.now(IRAN)
    val engine = remember(s.hijriShift) { Holidays.engine(context, s) }
    val j = JalaliDate.of(today)
    val view = remember(s.hijriShift, j) { engine.month(j.year, j.month) }
    val lines = OccasionLines.build(s, view)
    val dates = DateLines.triple(engine.day(today), today)
    val dots = mapOf(
        Category.OFFICIAL to accent,
        Category.RELIGIOUS to Color(0xFFA593FF),
        Category.NATIONAL to Color(0xFF5BC0EB),
        Category.GLOBAL to Color(0xFF6FD08A),
    )
    Column {
        Tx("پیش‌نمایش ویجت ماهانه", 11.5f, mute, modifier = Modifier.padding(start = 4.dp, bottom = 4.dp))
        Column(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp)).background(bg).border(1.dp, if (light) Color(0xFFCFD8EA) else Color(0xFF243A6E), RoundedCornerShape(22.dp)).padding(horizontal = 14.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            Tx(dates[0], 21f, fg, FontWeight.Medium)
            Tx(dates[1], 13f, sub)
            Tx(dates[2], 13f, sub)
            Spacer(Modifier.height(6.dp))
            if (lines.isEmpty()) {
                Tx("این ماه مناسبتی برای نمایش انتخاب‌شده نیست.", 12.5f, sub)
            } else {
                lines.take(3).forEach { (cat, text) ->
                    Row(
                        Modifier.padding(bottom = 4.dp).clip(RoundedCornerShape(99.dp)).background(chipBg).padding(horizontal = 12.dp, vertical = 3.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(7.dp),
                    ) {
                        Box(Modifier.size(8.dp).clip(CircleShape).background(dots.getValue(cat)))
                        Tx(text, 12.5f, fg, maxLines = 1)
                    }
                }
                if (lines.size > 3) Tx("و ${lines.size - 3} مورد دیگر در فهرست", 12f, sub)
            }
        }
    }
}

@Composable
private fun Button(text: String, filled: Boolean, onClick: () -> Unit) {
    Box(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(if (filled) gold else chip).clickable(onClick = onClick).padding(vertical = 12.dp),
        contentAlignment = Alignment.Center,
    ) { Tx(text, 14.5f, if (filled) Color(0xFF241B00) else ink, FontWeight.Medium) }
}

@Composable
private fun SwitchRow(title: String, description: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Column(Modifier.weight(1f)) {
            Tx(title, 14.5f, ink, FontWeight.Medium)
            Tx(description, 12f, mute)
        }
        Toggle(checked, onChange)
    }
}

@Composable
private fun Toggle(checked: Boolean, onChange: (Boolean) -> Unit) {
    Box(
        Modifier.size(46.dp, 27.dp).clip(RoundedCornerShape(99.dp)).background(if (checked) gold else Color(0xFF46567E)).clickable { onChange(!checked) },
    ) {
        // the knob rests on the right when off and slides to the left when on (right-to-left screen)
        Box(
            Modifier.padding(3.dp).size(21.dp).align(if (checked) Alignment.CenterEnd else Alignment.CenterStart).clip(CircleShape).background(navy),
        )
    }
}

/** A row of options where exactly one is chosen. */
@Composable
private fun <T> Segmented(options: List<Pair<T, String>>, selected: T, onSelect: (T) -> Unit) {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(13.dp)).background(navy).padding(3.dp), horizontalArrangement = Arrangement.spacedBy(3.dp)) {
        options.forEach { (value, label) ->
            val on = value == selected
            Box(
                Modifier.weight(1f).clip(RoundedCornerShape(10.dp)).background(if (on) chip else Color.Transparent)
                    .then(if (on) Modifier.border(1.dp, edge, RoundedCornerShape(10.dp)) else Modifier)
                    .clickable { onSelect(value) }.padding(vertical = 8.dp),
                contentAlignment = Alignment.Center,
            ) { Tx(label, 13f, if (on) ink else mute, FontWeight.Medium) }
        }
    }
}

@Composable
private fun Picker(label: String, value: String, items: List<String>, modifier: Modifier, onPick: (String) -> Unit) {
    var open by remember { mutableStateOf(false) }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Label(label)
        Box {
            Row(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(chip).clickable { open = true }.padding(horizontal = 12.dp, vertical = 11.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Tx(value, 14.5f, ink, FontWeight.Medium, Modifier.weight(1f), maxLines = 1)
                Tx("▾", 12f, mute)
            }
            DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                items.forEach { item ->
                    DropdownMenuItem(text = { Tx(item, 14f, ink) }, onClick = { open = false; onPick(item) })
                }
            }
        }
    }
}

/** The four groups in priority order: drag the handle to reorder, pick how much of each to show. */
@Composable
private fun GroupList(order: List<Category>, levels: Map<Category, Level>, onOrder: (List<Category>) -> Unit, onLevel: (Category, Level) -> Unit) {
    val rowHeight: Dp = 122.dp
    val gap = 10.dp
    val stepPx = with(LocalDensity.current) { (rowHeight + gap).toPx() }
    var items by remember(order) { mutableStateOf(order) }
    var dragging by remember { mutableStateOf<Category?>(null) }
    var dy by remember { mutableStateOf(0f) }

    Column(verticalArrangement = Arrangement.spacedBy(gap)) {
        items.forEachIndexed { index, c ->
            key(c) {
                val g = groups.getValue(c)
                val lifted = dragging == c
                Column(
                    Modifier
                        .fillMaxWidth().height(rowHeight)
                        .offset { IntOffset(0, if (lifted) dy.roundToInt() else 0) }
                        .zIndex(if (lifted) 1f else 0f)
                        .clip(RoundedCornerShape(22.dp))
                        .background(if (lifted) Color(0xFF1B3166) else navy2)
                        .then(if (lifted) Modifier.border(1.dp, gold, RoundedCornerShape(22.dp)) else Modifier)
                        .padding(horizontal = 12.dp, vertical = 10.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Tx(
                            "⠿", 22f, mute,
                            modifier = Modifier.padding(horizontal = 4.dp, vertical = 8.dp).pointerInput(c) {
                                detectVerticalDragGestures(
                                    onDragStart = { dragging = c; dy = 0f },
                                    onDragEnd = { dragging = null; dy = 0f; onOrder(items) },
                                    onDragCancel = { dragging = null; dy = 0f; items = order },
                                    onVerticalDrag = { change, amount ->
                                        change.consume()
                                        dy += amount
                                        val i = items.indexOf(c)
                                        if (dy > stepPx / 2 && i < items.lastIndex) {
                                            items = items.toMutableList().also { Collections.swap(it, i, i + 1) }
                                            dy -= stepPx
                                        } else if (dy < -stepPx / 2 && i > 0) {
                                            items = items.toMutableList().also { Collections.swap(it, i, i - 1) }
                                            dy += stepPx
                                        }
                                    },
                                )
                            },
                        )
                        Box(Modifier.size(12.dp).clip(CircleShape).background(g.color))
                        Column(Modifier.weight(1f)) {
                            Tx(g.title, 15f, ink, FontWeight.Medium)
                            Tx(g.description, 12f, mute, maxLines = 1)
                        }
                        Box(Modifier.clip(RoundedCornerShape(99.dp)).background(navy).padding(horizontal = 9.dp, vertical = 1.dp)) {
                            Tx((index + 1).fa(), 12f, mute)
                        }
                    }
                    Segmented(g.levels, levels[c] ?: Level.ALL) { l -> onLevel(c, l) }
                }
            }
        }
    }
}

/** Shows today's lunar date as the app counts it, with one-day steps if the real date (moon sighting) differs. */
@Composable
private fun LunarStepper(shift: Int, onShift: (Int) -> Unit) {
    val context = LocalContext.current
    val today = LocalDate.now(IRAN)
    val settings = remember(shift) { AppSettings(hijriShift = shift) }
    val day = remember(shift) { Holidays.engine(context, settings).day(today) }
    val line = "${day.hijri.day.fa()} ${ir.taghvim.app.data.hijriMonthName(day.hijri.month)} ${day.hijri.year.fa()}"
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        StepButton("+", enabled = shift > -2) { onShift(shift - 1) } // one day later in the lunar month
        Box(Modifier.weight(1f), contentAlignment = Alignment.Center) { Tx(line, 16f, ink, FontWeight.Medium) }
        StepButton("−", enabled = shift < 2) { onShift(shift + 1) }
    }
    Tx(
        if (shift == 0) "از فهرست رسمی تعطیلات تنظیم شده است. اگر با رؤیت هلال شما نمی‌خواند، یک روز جلو یا عقب ببرید."
        else "دستی ${if (shift < 0) "${(-shift).fa()} روز جلو" else "${shift.fa()} روز عقب"} برده شده است.",
        12f, mute,
    )
}

@Composable
private fun StepButton(glyph: String, enabled: Boolean, onClick: () -> Unit) {
    Box(
        Modifier.size(44.dp).clip(RoundedCornerShape(14.dp)).background(if (enabled) chip else navy).then(if (enabled) Modifier.clickable(onClick = onClick) else Modifier),
        contentAlignment = Alignment.Center,
    ) { Tx(glyph, 22f, if (enabled) ink else mute, FontWeight.Medium) }
}

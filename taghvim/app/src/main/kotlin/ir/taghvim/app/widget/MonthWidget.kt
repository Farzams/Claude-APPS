package ir.taghvim.app.widget

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.ColorFilter
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.Image
import androidx.glance.ImageProvider
import androidx.glance.action.actionStartActivity
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.SizeMode
import androidx.glance.appwidget.action.ActionCallback
import androidx.glance.appwidget.action.actionRunCallback
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.action.ActionParameters
import androidx.glance.layout.Alignment
import androidx.glance.layout.Box
import androidx.glance.layout.Column
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.size
import androidx.glance.layout.width
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextAlign
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import androidx.glance.LocalContext
import ir.taghvim.app.data.AppSettings
import ir.taghvim.app.data.Holidays
import ir.taghvim.app.data.Prefs
import ir.taghvim.app.data.fa
import ir.taghvim.app.ui.SettingsActivity
import ir.taghvim.core.CalendarEngine
import ir.taghvim.core.Category
import ir.taghvim.core.DayInfo
import ir.taghvim.core.Jalali
import ir.taghvim.core.JalaliDate
import ir.taghvim.core.MonthView
import java.time.LocalDate

/** The 4x4 widget: a Persian month with holidays, occasion icons and arrows to change month. */
class MonthWidget : GlanceAppWidget() {
    override val sizeMode = SizeMode.Single

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        var s = Prefs.load(context)
        val today = LocalDate.now(IRAN)
        if (s.offsetDate != today.toString() && s.monthOffset != 0) {
            s = s.copy(monthOffset = 0, offsetDate = today.toString())
            Prefs.save(context, s)
        }
        val engine = Holidays.engine(context, s)
        val j = JalaliDate.of(today)
        val index = j.year * 12 + (j.month - 1) + s.monthOffset
        val view = engine.month(index / 12, index % 12 + 1)
        provideContent { MonthContent(s, engine, view, today) }
    }
}

class MonthWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = MonthWidget()
    override fun onEnabled(context: Context) {
        super.onEnabled(context)
        ir.taghvim.app.work.Schedule.ensure(context)
    }
}

/** Arrow buttons: moves the shown month one step, for the rest of the day. */
class MonthNavCallback : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        val dir = parameters[DIR_KEY] ?: 0
        Prefs.update(context) { it.copy(monthOffset = (it.monthOffset + dir).coerceIn(-36, 36), offsetDate = LocalDate.now(IRAN).toString()) }
        MonthWidget().update(context, glanceId)
    }

    companion object {
        val DIR_KEY = ActionParameters.Key<Int>("dir")
    }
}

private val themeIcon = mapOf(
    "nowruz" to "nowruz", "nat" to "flag", "mourn" to "mourn", "joy" to "joy",
    "xmas" to "xmas", "nye" to "nye", "val" to "heart", "hal" to "hal", "yalda" to "melon",
)
private val white = Color.White
private val CELL = 37.dp

@Composable
private fun MonthContent(s: AppSettings, engine: CalendarEngine, view: MonthView, today: LocalDate) {
    val context = LocalContext.current
    val p = Palettes.of(context, s)
    val rtl = context.isRtl()
    val title = "${Jalali.monthNames[view.month - 1]} ${view.year.fa()}"
    val first = view.days.first().hijri
    val last = view.days.last().hijri
    val sub = ir.taghvim.app.data.hijriMonthName(first.month).let { a ->
        if (first.month == last.month) "$a ${first.year.fa()}" else "$a و ${ir.taghvim.app.data.hijriMonthName(last.month)} ${last.year.fa()}"
    }

    Column(
        modifier = GlanceModifier.fillMaxSize().background(p.card).cornerRadius(26.dp).padding(12.dp)
            .clickable(actionStartActivity<SettingsActivity>()),
    ) {
        Row(modifier = GlanceModifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            val titleBlock: @Composable () -> Unit = {
                Column(modifier = GlanceModifier.defaultWeight()) {
                    Text(rtlText(title), modifier = GlanceModifier.fillMaxWidth(), style = TextStyle(color = ColorProvider(p.ink), fontSize = 18.sp, fontWeight = FontWeight.Medium, textAlign = TextAlign.Right))
                    Text(rtlText(sub), modifier = GlanceModifier.fillMaxWidth(), style = TextStyle(color = ColorProvider(p.mute), fontSize = 11.sp, textAlign = TextAlign.Right))
                }
            }
            val nav: @Composable () -> Unit = {
                Row {
                    // next month on the right with "‹", previous month on the left with "›" (as in the design)
                    listOf("‹" to 1, "›" to -1).rightToLeft(rtl).forEachIndexed { i, (glyph, dir) ->
                        if (i > 0) Spacer(GlanceModifier.width(6.dp))
                        NavButton(p, glyph, dir)
                    }
                }
            }
            if (rtl) { titleBlock(); nav() } else { nav(); titleBlock() }
        }
        Spacer(GlanceModifier.height(4.dp))
        Row(modifier = GlanceModifier.fillMaxWidth()) {
            Jalali.weekdayInitials.mapIndexed { i, w -> i to w }.rightToLeft(rtl).forEach { (i, w) ->
                Box(modifier = GlanceModifier.defaultWeight(), contentAlignment = Alignment.Center) {
                    Text(w, style = TextStyle(color = ColorProvider(if (i == 6) p.accent else p.mute), fontSize = 11.sp, fontWeight = if (i == 6) FontWeight.Bold else FontWeight.Normal, textAlign = TextAlign.Center))
                }
            }
        }
        val cells: List<DayInfo?> = List(view.startColumn) { null } + view.days
        Column(modifier = GlanceModifier.fillMaxWidth()) {
            cells.chunked(7).forEach { week ->
                Row(modifier = GlanceModifier.fillMaxWidth()) {
                    val padded = week + List(7 - week.size) { null }
                    padded.rightToLeft(rtl).forEach { d ->
                        Box(modifier = GlanceModifier.defaultWeight().height(CELL), contentAlignment = Alignment.Center) {
                            if (d != null) DayCell(s, p, d, today)
                        }
                    }
                }
            }
        }
        Spacer(GlanceModifier.height(4.dp))
        Column(modifier = GlanceModifier.fillMaxWidth()) { Footer(s, p, view) }
    }
}

@Composable
private fun NavButton(p: Palette, glyph: String, dir: Int) {
    Box(
        modifier = GlanceModifier.size(28.dp).background(ImageProvider(ir.taghvim.app.R.drawable.bg_soft_nat)).clickable(
            actionRunCallback<MonthNavCallback>(androidx.glance.action.actionParametersOf(MonthNavCallback.DIR_KEY to dir)),
        ),
        contentAlignment = Alignment.Center,
    ) {
        Text(glyph, style = TextStyle(color = ColorProvider(p.ink), fontSize = 16.sp, textAlign = TextAlign.Center))
    }
}

@Composable
private fun DayCell(s: AppSettings, p: Palette, d: DayInfo, today: LocalDate) {
    val context = LocalContext.current
    val ev = d.primary(s.order, s.enabled)
    val isToday = d.date == today
    val themedOrOfficial = s.specialBackgrounds && ev?.theme != null
    val bg: Int = when {
        isToday -> ir.taghvim.app.R.drawable.bg_today
        themedOrOfficial && ev?.theme != null -> context.drawableId("bg_${ev.theme}")
        ev != null -> context.drawableId(if (ev.category == Category.RELIGIOUS) "bg_soft_rel" else if (ev.category == Category.GLOBAL) "bg_soft_gre" else "bg_soft_nat")
        else -> 0
    }
    val iconName = ev?.icon ?: ev?.theme?.let { themeIcon[it] }
    val icon = if (!isToday && iconName != null) context.drawableId("ic_$iconName") else 0
    val special = !isToday && themedOrOfficial && ev?.theme != null
    val numberColor = when {
        isToday -> p.todayFg
        special -> white
        d.isHoliday -> p.accent
        else -> p.ink
    }
    if (bg != 0) {
        Image(
            provider = ImageProvider(bg),
            contentDescription = null,
            modifier = GlanceModifier.size(34.dp),
            colorFilter = if (isToday) ColorFilter.tint(ColorProvider(p.todayBg)) else null,
        )
    }
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(d.jalali.day.fa(), style = TextStyle(color = ColorProvider(numberColor), fontSize = 15.sp, fontWeight = FontWeight.Medium, textAlign = TextAlign.Center))
        when {
            icon != 0 && bg != 0 -> Image(provider = ImageProvider(icon), contentDescription = null, modifier = GlanceModifier.size(11.dp))
            s.secondary == "hijri" -> Text(d.hijri.day.fa(), style = TextStyle(color = ColorProvider(if (isToday) p.todayFg else p.mute), fontSize = 8.sp))
            s.secondary == "greg" -> Text(d.date.dayOfMonth.fa(), style = TextStyle(color = ColorProvider(if (isToday) p.todayFg else p.mute), fontSize = 8.sp))
        }
    }
}

@Composable
private fun Footer(s: AppSettings, p: Palette, view: MonthView) {
    val rtl = LocalContext.current.isRtl()
    val dots = mapOf(
        Category.OFFICIAL to p.accent,
        Category.RELIGIOUS to Color(0xFFA593FF),
        Category.NATIONAL to Color(0xFF5BC0EB),
        Category.GLOBAL to Color(0xFF6FD08A),
    )
    val lines = ArrayList<Pair<Category, String>>()
    val monthName = Jalali.monthNames[view.month - 1]
    for (cat in s.order.filter { it in s.enabled }) {
        var i = 0
        while (i < view.days.size) {
            val d = view.days[i]
            val e = d.events.firstOrNull { it.category == cat }
            if (e != null) {
                var j = i
                while (j + 1 < view.days.size && view.days[j + 1].events.any { it.category == cat && it.title == e.title }) j++
                val range = if (j == i) d.jalali.day.fa() else "${d.jalali.day.fa()} تا ${view.days[j].jalali.day.fa()}"
                lines += cat to "$range $monthName · ${e.title}"
                i = j + 1
            } else i++
        }
    }
    lines.take(3).forEach { (cat, text) ->
        Row(modifier = GlanceModifier.fillMaxWidth().padding(bottom = 3.dp), horizontalAlignment = Alignment.End) {
            Row(
                modifier = GlanceModifier.background(p.chip).cornerRadius(12.dp).padding(horizontal = 9.dp, vertical = 3.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                // the dot sits on the right of the text, as in the design
                val parts: List<@Composable () -> Unit> = listOf(
                    { Text("●", style = TextStyle(color = ColorProvider(dots.getValue(cat)), fontSize = 8.sp)) },
                    { Spacer(GlanceModifier.width(5.dp)) },
                    { Text(rtlText(text), maxLines = 1, style = TextStyle(color = ColorProvider(p.ink), fontSize = 11.sp)) },
                )
                parts.rightToLeft(rtl).forEach { it() }
            }
        }
    }
}

package ir.taghvim.app.widget

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.glance.ColorFilter
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.Image
import androidx.glance.ImageProvider
import androidx.glance.LocalContext
import androidx.glance.action.ActionParameters
import androidx.glance.action.actionParametersOf
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
import androidx.glance.unit.ColorProvider
import ir.taghvim.app.R
import ir.taghvim.app.data.AppSettings
import ir.taghvim.app.data.Holidays
import ir.taghvim.app.data.Prefs
import ir.taghvim.app.data.fa
import ir.taghvim.app.data.gregorianMonthNames
import ir.taghvim.app.data.hijriMonthName
import ir.taghvim.app.ui.SettingsActivity
import ir.taghvim.core.CalendarEngine
import ir.taghvim.core.Category
import ir.taghvim.core.DayInfo
import ir.taghvim.core.Jalali
import ir.taghvim.core.JalaliDate
import ir.taghvim.core.MonthView
import java.time.LocalDate

/** The 4x4 widget: a Persian month with holidays, coloured special days and arrows to change month. */
class MonthWidget : GlanceAppWidget() {
    override val sizeMode = SizeMode.Single

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val s = Prefs.load(context)
        val today = LocalDate.now(IRAN)
        val engine = Holidays.engine(context, s)
        val j = JalaliDate.of(today)
        val view = engine.month(j.year, j.month)
        provideContent { MonthContent(s, view, engine.day(today), today) }
    }
}

class MonthWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = MonthWidget()
    override fun onEnabled(context: Context) {
        super.onEnabled(context)
        ir.taghvim.app.work.Schedule.ensure(context)
    }
}

private val CELL = 37.dp
private const val INNER_WIDTH = 300f

/** The side a Persian reader starts from: the right edge, on a screen set to either direction. */
private fun rightEdge(rtl: Boolean) = if (rtl) Alignment.Start else Alignment.End

@Composable
private fun MonthContent(s: AppSettings, view: MonthView, now: DayInfo, today: LocalDate) {
    val context = LocalContext.current
    val p = Palettes.of(context, s)
    val rtl = context.isRtl()
    val jalaliLine = "${now.jalali.day.fa()} ${Jalali.monthNames[now.jalali.month - 1]} ${now.jalali.year.fa()}"
    val hijriLine = "${now.hijri.day.fa()} ${hijriMonthName(now.hijri.month)} ${now.hijri.year.fa()}"
    val gregorianLine = "${today.dayOfMonth.fa()} ${gregorianMonthNames[today.monthValue - 1]} ${today.year.fa()}"
    val weeks = (view.startColumn + view.days.size + 6) / 7

    Column(
        modifier = GlanceModifier.fillMaxSize().background(p.card).cornerRadius(26.dp).padding(12.dp)
            .clickable(actionStartActivity<SettingsActivity>()),
    ) {
        // today's date in the three calendars, on the right: Jalali, then lunar, then Gregorian
        Column(modifier = GlanceModifier.fillMaxWidth(), horizontalAlignment = rightEdge(rtl)) {
            Txt(jalaliLine, 22f, p.ink, 500)
            Txt(hijriLine, 13.5f, p.mute)
            Txt(gregorianLine, 13.5f, p.mute)
        }
        Spacer(GlanceModifier.height(6.dp))
        Row(modifier = GlanceModifier.fillMaxWidth()) {
            Jalali.weekdayInitials.mapIndexed { i, w -> i to w }.rightToLeft(rtl).forEach { (i, w) ->
                Box(modifier = GlanceModifier.defaultWeight(), contentAlignment = Alignment.Center) {
                    Txt(w, 13.5f, if (i == 6) p.accent else p.mute, if (i == 6) 700 else 400)
                }
            }
        }
        val cells: List<DayInfo?> = List(view.startColumn) { null } + view.days
        // the grid and the footer are one child each: a Glance column keeps only its first ten children
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
        Spacer(GlanceModifier.height(6.dp))
        Column(modifier = GlanceModifier.fillMaxWidth()) { Footer(s, p, view, rtl, if (weeks >= 6) 2 else 3) }
    }
}

/** A day: a coloured rounded square when it is today or special, otherwise just the number. */
@Composable
private fun DayCell(s: AppSettings, p: Palette, d: DayInfo, today: LocalDate) {
    val context = LocalContext.current
    val ev = d.primary(s.order, s.enabled)
    val isToday = d.date == today
    val themed = s.specialBackgrounds && ev?.theme != null
    val bg: Int = when {
        isToday -> R.drawable.bg_today
        themed -> context.drawableId("bg_${ev!!.theme}")
        ev != null -> context.drawableId(
            when (ev.category) {
                Category.RELIGIOUS -> "bg_soft_rel"
                Category.GLOBAL -> "bg_soft_gre"
                else -> "bg_soft_nat"
            },
        )
        else -> 0
    }
    val numberColor = when {
        isToday -> p.todayFg
        themed -> Color.White
        d.isHoliday -> p.accent
        else -> p.ink
    }
    if (bg != 0) {
        Image(
            provider = ImageProvider(bg),
            contentDescription = null,
            modifier = GlanceModifier.size(36.dp),
            colorFilter = if (isToday) ColorFilter.tint(ColorProvider(p.todayBg)) else null,
        )
    }
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Txt(d.jalali.day.fa(), 19f, numberColor, 500)
        val secondary = when {
            themed -> null
            s.secondary == "hijri" -> d.hijri.day.fa()
            s.secondary == "greg" -> d.date.dayOfMonth.fa()
            else -> null
        }
        if (secondary != null) Txt(secondary, 8.5f, if (isToday) p.todayFg else p.mute)
    }
}

@Composable
private fun Footer(s: AppSettings, p: Palette, view: MonthView, rtl: Boolean, maxLines: Int) {
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
    lines.take(maxLines).forEach { (cat, text) ->
        Row(modifier = GlanceModifier.fillMaxWidth().padding(bottom = 4.dp), horizontalAlignment = rightEdge(rtl)) {
            Row(
                modifier = GlanceModifier.background(p.chip).cornerRadius(12.dp).padding(horizontal = 10.dp, vertical = 3.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                // the dot sits on the right of the text, as in the design
                val parts: List<@Composable () -> Unit> = listOf(
                    { Txt("●", 8f, dots.getValue(cat)) },
                    { Spacer(GlanceModifier.width(6.dp)) },
                    { Txt(text, 13f, p.ink, maxWidthDp = INNER_WIDTH - 30f) },
                )
                parts.rightToLeft(rtl).forEach { it() }
            }
        }
    }
}

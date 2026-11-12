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
import androidx.glance.layout.absolutePadding
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
        // the day the user tapped, if it belongs to this month; otherwise today
        val picked = runCatching { LocalDate.parse(s.selectedDate) }.getOrNull()
            ?.takeIf { d -> view.days.any { it.date == d } } ?: today
        provideContent { MonthContent(s, view, engine.day(picked), today) }
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

/** A tap on a day: that day gets a yellow frame and its occasions are listed below. Tapping today clears it. */
class SelectDayCallback : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        val date = parameters[DATE_KEY] ?: return
        val value = if (date == LocalDate.now(IRAN).toString()) "" else date
        Prefs.update(context) { it.copy(selectedDate = value) }
        MonthWidget().update(context, glanceId)
    }

    companion object {
        val DATE_KEY = ActionParameters.Key<String>("date")
    }
}

/** The side a Persian reader starts from: the right edge, on a screen set to either direction. */
private fun rightEdge(rtl: Boolean) = if (rtl) Alignment.Start else Alignment.End

@Composable
private fun MonthContent(s: AppSettings, view: MonthView, now: DayInfo, today: LocalDate) {
    val context = LocalContext.current
    val p = Palettes.of(context, s)
    val rtl = context.isRtl()
    val dateLines = DateLines.triple(now, now.date)
    val weeks = (view.startColumn + view.days.size + 6) / 7

    // no tap on the widget background opens anything: taps belong to the days
    Column(
        modifier = GlanceModifier.fillMaxSize().background(p.card).cornerRadius(26.dp).padding(12.dp),
    ) {
        // the chosen day (today unless a day was tapped) in the three calendars, on the right: Jalali, then lunar, then Gregorian
        Column(modifier = GlanceModifier.fillMaxWidth().absolutePadding(right = 8.dp), horizontalAlignment = rightEdge(rtl)) {
            Txt(dateLines[0], 22f, p.ink, 500)
            // Gregorian, then the lunar date, with a small dot between them
            Row(verticalAlignment = Alignment.CenterVertically) {
                val parts: List<@Composable () -> Unit> = listOf(
                    { Txt(dateLines[2], 13.5f, p.mute) },
                    { Spacer(GlanceModifier.width(9.dp)) },
                    { Txt("●", 5f, p.mute) },
                    { Spacer(GlanceModifier.width(9.dp)) },
                    { Txt(dateLines[1], 13.5f, p.mute) },
                )
                parts.rightToLeft(rtl).forEach { it() }
            }
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
                        val tap = if (d == null) GlanceModifier else GlanceModifier.clickable(
                            actionRunCallback<SelectDayCallback>(actionParametersOf(SelectDayCallback.DATE_KEY to d.date.toString())),
                        )
                        Box(modifier = GlanceModifier.defaultWeight().height(CELL).then(tap), contentAlignment = Alignment.Center) {
                            if (d != null) DayCell(s, p, d, today, now.date)
                        }
                    }
                }
            }
        }
        Spacer(GlanceModifier.height(6.dp))
        Column(modifier = GlanceModifier.fillMaxWidth()) { Footer(p, DayOccasions.forDay(s, now), rtl, if (weeks >= 6) 2 else 3) }
    }
}

/** A day: a coloured rounded square when it is today or special, otherwise just the number. */
@Composable
private fun DayCell(s: AppSettings, p: Palette, d: DayInfo, today: LocalDate, selected: LocalDate) {
    val context = LocalContext.current
    val ev = d.primary(s.order, s.levels)
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
    // the tapped day gets a yellow frame; today never needs one
    if (!isToday && d.date == selected) {
        Image(
            provider = ImageProvider(R.drawable.bg_select),
            contentDescription = null,
            modifier = GlanceModifier.size(37.dp),
            colorFilter = ColorFilter.tint(ColorProvider(p.accent)),
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
private fun Footer(p: Palette, lines: List<Pair<Category, String>>, rtl: Boolean, maxLines: Int) {
    val dots = mapOf(
        Category.OFFICIAL to p.accent,
        Category.RELIGIOUS to Color(0xFFA593FF),
        Category.NATIONAL to Color(0xFF5BC0EB),
        Category.GLOBAL to Color(0xFF6FD08A),
    )
    val shown: List<Pair<Category?, String>> =
        if (lines.isEmpty()) listOf(null to "مناسبتی برای این روز ثبت نشده") else lines.take(maxLines)
    shown.forEach { (cat, text) ->
        Row(modifier = GlanceModifier.fillMaxWidth().padding(bottom = 4.dp), horizontalAlignment = rightEdge(rtl)) {
            Row(
                modifier = GlanceModifier.background(p.chip).cornerRadius(12.dp).padding(horizontal = 10.dp, vertical = 3.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                // the dot sits on the right of the text, as in the design
                val parts: List<@Composable () -> Unit> = listOf(
                    { if (cat != null) Txt("●", 8f, dots.getValue(cat)) },
                    { if (cat != null) Spacer(GlanceModifier.width(6.dp)) },
                    { Txt(text, 13f, if (cat == null) p.mute else p.ink, maxWidthDp = INNER_WIDTH - 30f) },
                )
                parts.rightToLeft(rtl).forEach { it() }
            }
        }
    }
}

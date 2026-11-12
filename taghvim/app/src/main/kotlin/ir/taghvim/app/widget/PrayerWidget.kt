package ir.taghvim.app.widget

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.Image
import androidx.glance.ImageProvider
import androidx.glance.LocalContext
import androidx.glance.action.actionStartActivity
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.SizeMode
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Box
import androidx.glance.layout.Column
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxHeight
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.size
import androidx.glance.layout.width
import ir.taghvim.app.R
import ir.taghvim.app.data.AppSettings
import ir.taghvim.app.data.Prefs
import ir.taghvim.app.data.fa
import ir.taghvim.app.ui.SettingsActivity
import ir.taghvim.core.PrayerCalc
import java.time.LocalDateTime
import java.time.ZoneId

/**
 * What the widget needs at one moment: the day's six times, which one is next, how long to wait, and how far
 * the wait has gone (0 to 1) since the moment before it.
 */
class PrayerState(
    val labels: List<String>,
    val icons: List<String>,
    val times: List<String>,
    val next: Int,
    val minutesLeft: Int,
    val progress: Float,
) {
    /** "۳:۲۸" with "ساعت" below, or just the minutes with "دقیقه" when less than an hour is left. */
    val centre: String get() = if (minutesLeft >= 60) "${(minutesLeft / 60).fa()}:${"%02d".format(minutesLeft % 60).fa()}" else minutesLeft.fa()
    val unit: String get() = if (minutesLeft >= 60) "ساعت" else "دقیقه"
    val target: String get() = "تا ${labels[next]}"
}

/** Iran's own time zone: the times of an Iranian city are always read in Iran time, wherever the phone is. */
val IRAN: ZoneId = ZoneId.of("Asia/Tehran")

object PrayerPlan {
    private val labels = listOf("اذان صبح", "طلوع", "اذان ظهر", "غروب", "اذان مغرب", "نیمه‌شب")
    private val icons = listOf("fajr", "rise", "sun", "set", "mag", "mid")

    fun at(s: AppSettings, now: LocalDateTime, zone: ZoneId = IRAN): PrayerState {
        val city = s.currentCity
        val today = PrayerCalc.compute(now.toLocalDate(), city, zone).asList()
        val nowMin = now.hour * 60.0 + now.minute + now.second / 60.0
        var next = today.indexOfFirst { it > nowMin }
        val left: Double
        val before: Double
        if (next >= 0) {
            left = today[next] - nowMin
            // the moment before: the previous time of today, or last night's midnight before dawn
            before = if (next > 0) today[next - 1] else PrayerCalc.compute(now.toLocalDate().minusDays(1), city, zone).midnight - 24 * 60
        } else {
            // every time of today has passed: the next moment is tomorrow's dawn
            val tomorrow = PrayerCalc.compute(now.toLocalDate().plusDays(1), city, zone).asList()
            next = 0
            left = 24 * 60 - nowMin + tomorrow[0]
            before = today[5]
        }
        val span = left + (nowMin - before)
        val progress = if (span > 0) ((nowMin - before) / span).toFloat().coerceIn(0f, 1f) else 0f
        return PrayerState(labels, icons, today.map { PrayerCalc.format(it).fa() }, next, Math.ceil(left).toInt(), progress)
    }
}

/** The 4x2 widget: the wait for the next time in a ring, and the day's six times. Redrawn every minute. */
class PrayerWidget : GlanceAppWidget() {
    override val sizeMode = SizeMode.Single

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val s = Prefs.load(context)
        val state = PrayerPlan.at(s, LocalDateTime.now(IRAN))
        provideContent { PrayerContent(s, state) }
    }
}

class PrayerWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = PrayerWidget()
    override fun onEnabled(context: Context) {
        super.onEnabled(context)
        ir.taghvim.app.work.Schedule.ensure(context)
        ir.taghvim.app.work.Schedule.startMinuteTick(context)
    }

    override fun onDisabled(context: Context) {
        super.onDisabled(context)
        ir.taghvim.app.work.Schedule.stopMinuteTick(context)
    }
}

@Composable
private fun PrayerContent(s: AppSettings, st: PrayerState) {
    val context = LocalContext.current
    val p = Palettes.of(context, s)
    val rtl = context.isRtl()
    val track = if (Palettes.isDark(context, s)) Color(0xFF34508F) else Color(0xFFC4D0EA)

    Row(
        modifier = GlanceModifier.fillMaxSize().background(p.card).cornerRadius(26.dp).padding(10.dp)
            .clickable(actionStartActivity<SettingsActivity>()),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        // the big card (city, ring with the wait, target) is on the right; the six times on the left
        val card: @Composable () -> Unit = {
            Column(
                modifier = GlanceModifier.width(124.dp).fillMaxHeight().background(p.chip).cornerRadius(20.dp).padding(6.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Txt(s.city, 13f, p.mute, maxWidthDp = 100f)
                Spacer(GlanceModifier.height(4.dp))
                Box(contentAlignment = Alignment.Center) {
                    Ring(st.progress, track, p.accent, sizeDp = 82f, strokeDp = 7f)
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Txt(st.centre, 22f, p.ink, 700)
                        Txt(st.unit, 11f, p.mute)
                    }
                }
                Spacer(GlanceModifier.height(4.dp))
                Txt(st.target, 14f, p.ink, 700, maxWidthDp = 108f)
            }
        }
        val list: @Composable () -> Unit = {
            Column(modifier = GlanceModifier.defaultWeight().fillMaxHeight(), verticalAlignment = Alignment.CenterVertically) {
                st.labels.indices.forEach { i ->
                    val next = i == st.next
                    val id = context.drawableId("pr_${st.icons[i]}")
                    Row(
                        modifier = GlanceModifier.fillMaxWidth()
                            .then(if (next) GlanceModifier.background(ImageProvider(R.drawable.bg_soft_nat)) else GlanceModifier)
                            .padding(horizontal = 6.dp, vertical = 1.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        // right to left: icon, name, then the time at the far left
                        val parts: List<@Composable () -> Unit> = listOf(
                            { if (id != 0) Image(ImageProvider(id), contentDescription = st.labels[i], modifier = GlanceModifier.size(24.dp)) },
                            { Spacer(GlanceModifier.width(8.dp)) },
                            { Txt(st.labels[i], 12.5f, p.mute) },
                            { Spacer(GlanceModifier.defaultWeight()) },
                            { Txt(st.times[i], 12.5f, if (next) p.accent else p.ink, 500) },
                        )
                        parts.rightToLeft(rtl).forEach { it() }
                    }
                }
            }
        }
        val gap: @Composable () -> Unit = { Spacer(GlanceModifier.width(10.dp)) }
        listOf(card, gap, list).rightToLeft(rtl).forEach { it() }
    }
}

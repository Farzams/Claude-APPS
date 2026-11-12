package ir.taghvim.app.widget

import android.content.Context
import androidx.compose.runtime.Composable
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
import androidx.glance.layout.Column
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.size
import ir.taghvim.app.R
import ir.taghvim.app.data.AppSettings
import ir.taghvim.app.data.Prefs
import ir.taghvim.app.data.fa
import ir.taghvim.app.ui.SettingsActivity
import ir.taghvim.core.PrayerCalc
import java.time.LocalDateTime
import java.time.ZoneId

/** What the widget needs at one moment: the day's six times and which one is next, with minutes to wait. */
class PrayerState(val labels: List<String>, val icons: List<String>, val times: List<String>, val next: Int, val minutesLeft: Int)

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
        if (next >= 0) {
            left = today[next] - nowMin
        } else {
            // every time of today has passed: the next moment is tomorrow's dawn
            val tomorrow = PrayerCalc.compute(now.toLocalDate().plusDays(1), city, zone).asList()
            next = 0
            left = 24 * 60 - nowMin + tomorrow[0]
        }
        return PrayerState(labels, icons, today.map { PrayerCalc.format(it).fa() }, next, Math.ceil(left).toInt())
    }

    fun countdown(state: PrayerState): String {
        val h = state.minutesLeft / 60
        val m = state.minutesLeft % 60
        val span = when {
            h == 0 -> "${m.fa()} دقیقه"
            m == 0 -> "${h.fa()} ساعت"
            else -> "${h.fa()} ساعت و ${m.fa()} دقیقه"
        }
        return "$span تا ${state.labels[state.next]}"
    }
}

/** The 4x2 widget: six moments with scene icons and names, the next one highlighted, and a countdown to it. */
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
    }
}

@Composable
private fun PrayerContent(s: AppSettings, st: PrayerState) {
    val context = LocalContext.current
    val p = Palettes.of(context, s)
    val rtl = context.isRtl()
    Column(
        modifier = GlanceModifier.fillMaxSize().background(p.card).cornerRadius(26.dp).padding(horizontal = 10.dp, vertical = 10.dp)
            .clickable(actionStartActivity<SettingsActivity>()),
        verticalAlignment = Alignment.CenterVertically, // everything sits in the middle of the widget's height
    ) {
        Row(modifier = GlanceModifier.fillMaxWidth().padding(horizontal = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            val head: @Composable () -> Unit = { Txt(PrayerPlan.countdown(st), 16f, p.ink, 700, maxWidthDp = 230f) }
            val city: @Composable () -> Unit = { Txt("به افق ${s.city}", 12f, p.mute) }
            val gap: @Composable () -> Unit = { Spacer(GlanceModifier.defaultWeight()) }
            listOf(head, gap, city).rightToLeft(rtl).forEach { it() }
        }
        Spacer(GlanceModifier.height(8.dp))
        Row(modifier = GlanceModifier.fillMaxWidth()) {
            st.labels.indices.toList().rightToLeft(rtl).forEach { i ->
                val next = i == st.next
                Column(
                    modifier = GlanceModifier.defaultWeight()
                        .then(if (next) GlanceModifier.background(ImageProvider(R.drawable.bg_soft_nat)) else GlanceModifier)
                        .padding(vertical = 6.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    val id = context.drawableId("pr_${st.icons[i]}")
                    if (id != 0) Image(ImageProvider(id), contentDescription = st.labels[i], modifier = GlanceModifier.size(38.dp))
                    Spacer(GlanceModifier.height(4.dp))
                    Txt(st.labels[i], 10.5f, p.mute)
                    Txt(st.times[i], 14f, if (next) p.accent else p.ink, 500)
                }
            }
        }
    }
}

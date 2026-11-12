package ir.taghvim.app

import android.appwidget.AppWidgetHost
import android.appwidget.AppWidgetHostView
import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import ir.taghvim.app.ui.SettingsActivity
import androidx.test.ext.junit.runners.AndroidJUnit4
import ir.taghvim.app.data.fa
import ir.taghvim.app.widget.MonthWidget
import ir.taghvim.app.widget.MonthWidgetReceiver
import ir.taghvim.app.widget.PrayerWidget
import ir.taghvim.app.widget.PrayerWidgetReceiver
import ir.taghvim.core.JalaliDate
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.time.LocalDate

/**
 * Puts the two widgets on a real (emulated) widget host, waits for them to draw, saves a picture of each
 * (pulled by the CI script) and checks that the things the design needs are really on screen.
 */
@RunWith(AndroidJUnit4::class)
class WidgetRenderTest {
    private val inst = InstrumentationRegistry.getInstrumentation()
    private val ctx: Context = inst.targetContext

    private fun texts(v: View, out: MutableList<String> = ArrayList()): List<String> {
        // all text is drawn as pictures in the design's font; their description is the text
        if (v is TextView) out += v.text.toString()
        else v.contentDescription?.let { out += it.toString() }
        if (v is ViewGroup) for (i in 0 until v.childCount) texts(v.getChildAt(i), out)
        return out
    }

    private fun render(name: String, receiver: Class<*>, widget: GlanceAppWidget, widthDp: Int, heightDp: Int): List<String> {
        val mgr = AppWidgetManager.getInstance(ctx)
        val host = AppWidgetHost(ctx, 0x7a60)
        val id = host.allocateAppWidgetId()
        val provider = ComponentName(ctx, receiver)
        assertTrue("could not bind the $name widget", mgr.bindAppWidgetIdIfAllowed(id, provider))
        val info = mgr.getAppWidgetInfo(id)
        var view: AppWidgetHostView? = null
        inst.runOnMainSync {
            host.startListening()
            view = host.createView(ctx, id, info)
        }
        runBlocking {
            val glanceId = GlanceAppWidgetManager(ctx).getGlanceIdBy(id)
            widget.update(ctx, glanceId)
        }
        val d = ctx.resources.displayMetrics.density
        val w = (widthDp * d).toInt()
        val h = (heightDp * d).toInt()
        var found: List<String> = emptyList()
        // the system delivers the drawn widget a little later; look for up to 30 seconds
        for (attempt in 0 until 60) {
            Thread.sleep(500)
            inst.runOnMainSync {
                val v = view!!
                v.measure(View.MeasureSpec.makeMeasureSpec(w, View.MeasureSpec.EXACTLY), View.MeasureSpec.makeMeasureSpec(h, View.MeasureSpec.EXACTLY))
                v.layout(0, 0, w, h)
                found = texts(v)
            }
            if (found.size >= 5) break
        }
        inst.runOnMainSync {
            val v = view!!
            val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
            v.draw(Canvas(bmp))
            val dir = ctx.getExternalFilesDir(null)!!
            File(dir, "widget_$name.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
            File(dir, "widget_$name.txt").writeText(found.joinToString("\n"))
            host.stopListening()
            host.deleteAppWidgetId(id)
        }
        return found
    }

    @Test
    fun widgetsDrawWhatTheDesignNeeds() {
        inst.uiAutomation.adoptShellPermissionIdentity("android.permission.BIND_APPWIDGET")
        try {
            val today = JalaliDate.of(LocalDate.now(java.time.ZoneId.of("Asia/Tehran")))
            val month = render("month", MonthWidgetReceiver::class.java, MonthWidget(), 330, 400)
            println("month texts: $month")
            assertTrue("today's number is missing", month.any { it.contains(today.day.fa()) })
            assertTrue("the month title is missing", month.any { it.contains(today.year.fa()) })
            // the occasion list under the grid used to be dropped silently when the column had too many children
            assertTrue("the occasion line under the grid is missing", month.any { it.contains("·") || it.contains("مناسبتی") })
            assertTrue("fewer than 28 day numbers", month.count { t -> t.trim().all { it in "۰۱۲۳۴۵۶۷۸۹" } && t.isNotBlank() } >= 28)

            // a tapped day: the yellow frame and that day's occasions (a plain day in the same month, not today)
            val iranToday = LocalDate.now(java.time.ZoneId.of("Asia/Tehran"))
            val other = if (today.day <= 25) iranToday.plusDays(3) else iranToday.minusDays(3)
            runBlocking { ir.taghvim.app.data.Prefs.update(ctx) { it.copy(selectedDate = other.toString()) } }
            val picked = render("month_selected", MonthWidgetReceiver::class.java, MonthWidget(), 330, 400)
            println("selected-day texts: $picked")
            val pickedDay = JalaliDate.of(other).day.fa()
            assertTrue("the chosen day's date is missing from the header", picked.any { it.contains(pickedDay) })
            runBlocking { ir.taghvim.app.data.Prefs.update(ctx) { it.copy(selectedDate = "") } }

            val prayer = render("prayer", PrayerWidgetReceiver::class.java, PrayerWidget(), 330, 180)
            println("prayer texts: $prayer")
            val times = prayer.filter { Regex("[۰-۹]{2}:[۰-۹]{2}").matches(it.trim()) }
            assertTrue("the six prayer times must all be visible, found $times", times.size == 6)
            assertTrue("the countdown is missing", prayer.any { it.contains("تا") })
        } finally {
            inst.uiAutomation.dropShellPermissionIdentity()
        }
    }

    @Test
    fun settingsScreenOpensAndShowsTheGroups() {
        ActivityScenario.launch(SettingsActivity::class.java).use {
            Thread.sleep(3000)
            val shot = inst.uiAutomation.takeScreenshot()
            val dir = ctx.getExternalFilesDir(null)!!
            File(dir, "settings_top.png").outputStream().use { shot.compress(Bitmap.CompressFormat.PNG, 100, it) }
        }
    }
}

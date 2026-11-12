package ir.taghvim.app.widget

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.glance.appwidget.updateAll
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

object Widgets {
    suspend fun updateAll(context: Context) {
        MonthWidget().updateAll(context)
        PrayerWidget().updateAll(context)
    }
}

/** Day or time zone changed: redraw both widgets right away. */
class TimeChangeReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val pending = goAsync()
        CoroutineScope(Dispatchers.Default).launch {
            try { Widgets.updateAll(context.applicationContext) } finally { pending.finish() }
        }
    }
}

/** Every minute: redraw the prayer widget so the ring and the wait stay right. */
class MinuteTickReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val pending = goAsync()
        CoroutineScope(Dispatchers.Default).launch {
            try { PrayerWidget().updateAll(context.applicationContext) } finally { pending.finish() }
        }
    }
}

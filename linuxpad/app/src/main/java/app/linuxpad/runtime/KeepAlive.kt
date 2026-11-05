package app.linuxpad.runtime

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.content.ContextCompat
import app.linuxpad.DesktopActivity
import app.linuxpad.MainActivity

/**
 * Keeps the app alive while something the user started is running (an installation, the desktop): a foreground service with a
 * notification, and a CPU wake lock. Several reasons can be active; the service stops when the last one is released.
 */
object KeepAlive {
    private val reasons = LinkedHashMap<String, String>()

    @Synchronized
    fun acquire(ctx: Context, key: String, text: String) {
        val app = ctx.applicationContext
        val first = reasons.isEmpty()
        reasons[key] = text
        if (first) ContextCompat.startForegroundService(app, Intent(app, KeepAliveService::class.java)) else KeepAliveService.refresh(app)
    }

    @Synchronized
    fun release(ctx: Context, key: String) {
        val app = ctx.applicationContext
        if (reasons.remove(key) == null) return
        if (reasons.isEmpty()) app.stopService(Intent(app, KeepAliveService::class.java)) else KeepAliveService.refresh(app)
    }

    @Synchronized fun text(): String = reasons.values.joinToString("  |  ").ifEmpty { "LinuxPad" }
}

class KeepAliveService : Service() {
    private var wakeLock: PowerManager.WakeLock? = null

    companion object {
        const val CHANNEL = "keepalive"
        const val ID = 1
        const val ACTION_STOP = "app.linuxpad.STOP_SESSION"

        private fun ensureChannel(ctx: Context) {
            val nm = ctx.getSystemService(NotificationManager::class.java)
            if (nm.getNotificationChannel(CHANNEL) == null)
                nm.createNotificationChannel(NotificationChannel(CHANNEL, "Running tasks", NotificationManager.IMPORTANCE_LOW))
        }

        fun build(ctx: Context): Notification {
            ensureChannel(ctx)
            val session = LinuxSystem.session != "stopped"
            val open = PendingIntent.getActivity(ctx, 0, Intent(ctx, if (session) DesktopActivity::class.java else MainActivity::class.java),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
            val b = Notification.Builder(ctx, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_media_play)
                .setContentTitle("LinuxPad")
                .setContentText(KeepAlive.text())
                .setContentIntent(open)
                .setOngoing(true)
            if (session) {
                val stop = PendingIntent.getService(ctx, 1, Intent(ctx, KeepAliveService::class.java).setAction(ACTION_STOP), PendingIntent.FLAG_IMMUTABLE)
                b.addAction(Notification.Action.Builder(null, "Stop desktop", stop).build())
            }
            return b.build()
        }

        fun refresh(ctx: Context) = ctx.getSystemService(NotificationManager::class.java).notify(ID, build(ctx))
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            LinuxSystem.stopSession(this)          // releases its own reason; the service ends when nothing else is running
            return START_NOT_STICKY
        }
        val n = build(this)
        if (Build.VERSION.SDK_INT >= 34) startForeground(ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE) else startForeground(ID, n)
        if (wakeLock == null) {
            wakeLock = getSystemService(PowerManager::class.java).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "linuxpad:keepalive").apply { acquire(6 * 60 * 60 * 1000L) }
        }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        super.onDestroy()
    }
}

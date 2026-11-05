package app.linuxpad.x11

import android.app.Service
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Message
import android.os.Messenger
import android.os.Process
import android.os.SystemClock
import android.system.Os
import android.util.Log
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Runs the X server in its own Android process (declared with android:process=":x11").
 * An X server ends the whole process when it stops, so it must not share one with the app.
 * When the app unbinds, this process is killed, which also gives the next session a clean server.
 */
class X11ServerService : Service() {
    private val started = AtomicBoolean(false)
    private val ready = AtomicBoolean(false)
    private val handler = Handler(Looper.getMainLooper()) { m ->
        when (m.what) {
            X11Protocol.MSG_START -> handleStart(m)
            X11Protocol.MSG_GET_RENDERER -> handleRenderer(m)
            else -> return@Handler false
        }
        true
    }
    private val messenger = Messenger(handler)

    override fun onBind(intent: Intent?): IBinder = messenger.binder

    override fun onUnbind(intent: Intent?): Boolean {
        if (started.get()) { stopSelf(); Process.killProcess(Process.myPid()) }
        return false
    }

    private fun handleStart(m: Message) {
        val client = m.replyTo ?: return
        if (!started.compareAndSet(false, true)) { reply(client, if (ready.get()) X11Protocol.STATE_READY else X11Protocol.STATE_STARTING, "already running"); return }
        try {
            val runtime = File(requireNotNull(m.data.getString(X11Protocol.KEY_RUNTIME)))
            val xkb = File(requireNotNull(m.data.getString(X11Protocol.KEY_XKB)))
            require(xkb.isDirectory) { "keyboard data is missing: ${xkb.path} (install the graphics packages first)" }
            val socketDir = File(runtime, ".X11-unix")
            check(socketDir.isDirectory || socketDir.mkdirs()) { "cannot create ${socketDir.path}" }
            File(socketDir, "X0").delete()                    // a stale socket from a crashed server
            Os.setenv("TMPDIR", runtime.absolutePath, true)   // the server puts its socket in $TMPDIR/.X11-unix
            Os.setenv("XKB_CONFIG_ROOT", xkb.canonicalPath, true)
            Os.setenv("HOME", filesDir.absolutePath, true)
            reply(client, X11Protocol.STATE_STARTING, "starting the X server")
            val t0 = SystemClock.elapsedRealtime()
            // -noreset: otherwise the server resets when the last client disconnects and forgets what short-lived
            // clients (xrdb, xsetroot) set: DPI, background, cursor
            // -ac: the socket is private to this app (it lives in app storage and is only mounted into the Linux system)
            check(X11NativeBridge.start(arrayOf(":0", "-ac", "-noreset", "-nolisten", "tcp"))) { "the X server refused to start" }
            Thread {
                val socket = File(socketDir, "X0")
                while (SystemClock.elapsedRealtime() - t0 < 10_000) {
                    if (socket.exists()) { ready.set(true); reply(client, X11Protocol.STATE_READY, "X server up in ${SystemClock.elapsedRealtime() - t0} ms"); return@Thread }
                    SystemClock.sleep(25)
                }
                reply(client, X11Protocol.STATE_FAILED, "the X socket did not appear within 10 s")
            }.start()
        } catch (e: Throwable) {
            Log.e(TAG, "X server start failed", e)
            reply(client, X11Protocol.STATE_FAILED, e.message ?: e.javaClass.simpleName)
        }
    }

    private fun handleRenderer(m: Message) {
        val client = m.replyTo ?: return
        val fd = if (ready.get()) X11NativeBridge.getXConnection() else null
        val out = Message.obtain(null, X11Protocol.MSG_RENDERER)
        out.data = Bundle().apply {
            if (fd != null) putParcelable(X11Protocol.KEY_FD, fd) else putString(X11Protocol.KEY_DETAIL, "the X server is not ready")
        }
        try { client.send(out) } catch (e: Exception) { Log.w(TAG, "renderer reply failed", e) }
        finally { runCatching { fd?.close() } }   // the app received its own duplicate through Binder
    }

    private fun reply(client: Messenger, state: String, detail: String) {
        val out = Message.obtain(null, X11Protocol.MSG_STATUS)
        out.data = Bundle().apply { putString(X11Protocol.KEY_STATE, state); putString(X11Protocol.KEY_DETAIL, detail) }
        try { client.send(out) } catch (e: Exception) { Log.w(TAG, "status reply failed", e) }
    }

    private companion object { const val TAG = "LinuxPadX11" }
}

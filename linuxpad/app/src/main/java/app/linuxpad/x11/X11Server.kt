package app.linuxpad.x11

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Message
import android.os.Messenger
import android.os.ParcelFileDescriptor
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.io.File

/** The app-side handle of the X server process. */
object X11Server {
    var state by mutableStateOf("stopped"); private set
    var detail by mutableStateOf(""); private set

    private var service: Messenger? = null
    private var connection: ServiceConnection? = null
    private val readyCallbacks = mutableListOf<() -> Unit>()
    private val failedCallbacks = mutableListOf<() -> Unit>()
    private var onRenderer: ((ParcelFileDescriptor) -> Unit)? = null
    private var runtimeArg = ""
    private var xkbArg = ""

    private val inbox = Messenger(Handler(Looper.getMainLooper()) { m: Message ->
        when (m.what) {
            X11Protocol.MSG_STATUS -> {
                state = m.data.getString(X11Protocol.KEY_STATE) ?: "?"
                detail = m.data.getString(X11Protocol.KEY_DETAIL) ?: ""
                if (state == X11Protocol.STATE_READY) drain(readyCallbacks)
                if (state == X11Protocol.STATE_FAILED) drain(failedCallbacks)
            }
            X11Protocol.MSG_RENDERER -> {
                m.data.classLoader = ParcelFileDescriptor::class.java.classLoader
                @Suppress("DEPRECATION")
                val fd = m.data.getParcelable<ParcelFileDescriptor>(X11Protocol.KEY_FD)
                if (fd != null) onRenderer?.invoke(fd) else { state = X11Protocol.STATE_FAILED; detail = m.data.getString(X11Protocol.KEY_DETAIL) ?: "no renderer connection" }
            }
        }
        true
    })

    fun runtimeDir(ctx: Context) = File(ctx.filesDir, "runtime/x11")

    private fun drain(list: MutableList<() -> Unit>) { val copy = list.toList(); list.clear(); copy.forEach { it() } }

    /** Calls [cb] when the X server is ready (at once if it already is). */
    fun whenReady(cb: () -> Unit) { if (state == X11Protocol.STATE_READY) cb() else readyCallbacks.add(cb) }

    /** Calls [cb] if the X server fails to start. */
    fun whenFailed(cb: () -> Unit) { failedCallbacks.add(cb) }

    /** Starts the server process and the X server in it. Does nothing when it is already running. */
    fun start(ctx: Context, xkbRoot: File) {
        if (connection != null) return
        runtimeArg = runtimeDir(ctx).absolutePath
        xkbArg = xkbRoot.absolutePath
        state = X11Protocol.STATE_STARTING; detail = "connecting to the X server process"
        val c = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                service = Messenger(binder)
                send(X11Protocol.MSG_START) { putString(X11Protocol.KEY_RUNTIME, runtimeArg); putString(X11Protocol.KEY_XKB, xkbArg) }
            }
            override fun onServiceDisconnected(name: ComponentName) { service = null; if (state != "stopped") { state = X11Protocol.STATE_FAILED; detail = "the X server process died" } }
        }
        connection = c
        if (!ctx.applicationContext.bindService(Intent(ctx, X11ServerService::class.java), c, Context.BIND_AUTO_CREATE)) {
            connection = null; state = X11Protocol.STATE_FAILED; detail = "cannot bind the X server service"
        }
    }

    fun requestRenderer(callback: (ParcelFileDescriptor) -> Unit) { onRenderer = callback; send(X11Protocol.MSG_GET_RENDERER) {} }

    /** Unbinding makes the server process end itself. */
    fun stop(ctx: Context) {
        connection?.let { runCatching { ctx.applicationContext.unbindService(it) } }
        connection = null; service = null; readyCallbacks.clear(); failedCallbacks.clear(); onRenderer = null
        state = "stopped"; detail = ""
    }

    private fun send(what: Int, fill: android.os.Bundle.() -> Unit) {
        val m = Message.obtain(null, what)
        m.replyTo = inbox
        m.data = android.os.Bundle().apply(fill)
        try { service?.send(m) } catch (e: Exception) { state = X11Protocol.STATE_FAILED; detail = "send failed: ${e.message}" }
    }
}

package app.linuxpad.x11

/** Messages between the app process and the X server process (a Messenger over Binder). */
object X11Protocol {
    const val MSG_START = 1       // app -> server: data runtimeDir, xkbRoot
    const val MSG_STATUS = 2      // server -> app: data state, detail
    const val MSG_GET_RENDERER = 3
    const val MSG_RENDERER = 4    // server -> app: data fd (ParcelFileDescriptor) or detail
    const val KEY_RUNTIME = "runtime"
    const val KEY_XKB = "xkb"
    const val KEY_STATE = "state"
    const val KEY_DETAIL = "detail"
    const val KEY_FD = "fd"
    const val STATE_STARTING = "starting"
    const val STATE_READY = "ready"
    const val STATE_FAILED = "failed"
}

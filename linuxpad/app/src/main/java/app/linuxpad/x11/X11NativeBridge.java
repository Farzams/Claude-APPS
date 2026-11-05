package app.linuxpad.x11;

import android.os.ParcelFileDescriptor;

import androidx.annotation.Keep;

/** The X server's two entry points in libXlorie. The server runs in its own process (see X11ServerService). */
@Keep
public final class X11NativeBridge {
    static {
        System.loadLibrary("Xlorie");
    }

    private X11NativeBridge() {}

    /** Starts the X server threads in this process. Never call it twice: an X server cannot be restarted in-process. */
    public static native boolean start(String[] arguments);

    /** A new connection for the renderer (the app process draws what the server produces). */
    public static native ParcelFileDescriptor getXConnection();
}

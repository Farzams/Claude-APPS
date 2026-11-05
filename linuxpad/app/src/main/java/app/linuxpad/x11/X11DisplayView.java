package app.linuxpad.x11;

import android.content.Context;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;

import androidx.annotation.Keep;

import java.nio.charset.StandardCharsets;

/**
 * Shows the X server's screen. The desktop is created at the exact pixel size of this view, so it is sharp;
 * text and icon size come from DPI (see display/DisplayScale), never from scaling pixels.
 */
@Keep
public class X11DisplayView extends SurfaceView {
    static {
        System.loadLibrary("Xlorie");
    }

    /** android.graphics.PixelFormat has no public constant for it; this is the HAL value Termux:X11 also uses. */
    private static final int HAL_PIXEL_FORMAT_BGRA_8888 = 5;
    private static final int BUTTON_LEFT = 1;
    private boolean pressed;
    /** What this view has sent to the X server, for the on-screen diagnostics. */
    public volatile int moves, downs, ups;
    public volatile float lastX, lastY;
    private int guestWidth, guestHeight;

    // native code (activity.c / renderer.c), registered in JNI_OnLoad by LinuxPad's patch
    private native void nativeInit();
    private native void surfaceChanged(Surface surface);
    static native void setViewport(int x, int y, int width, int height, int expectedWidth, int expectedHeight);
    static native void setFiltering(int filtering);
    static native void connect(int fd);
    static native boolean connected();
    static native void sendWindowChange(int width, int height, int framerate, String name);
    native void sendMouseEvent(float x, float y, int whichButton, boolean buttonDown, boolean relative);
    native void sendTouchEvent(int action, int id, int x, int y);
    native boolean sendKeyEvent(int scanCode, int keyCode, boolean keyDown, int unused);
    native void sendTextEvent(byte[] text);

    private final SurfaceHolder.Callback callback = new SurfaceHolder.Callback() {
        @Override public void surfaceCreated(SurfaceHolder holder) {
            holder.setFormat(HAL_PIXEL_FORMAT_BGRA_8888);   // the renderer expects this channel order
        }

        @Override public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
            X11DisplayView.this.surfaceChanged(holder.getSurface());
            applyGeometry(width, height);
        }

        @Override public void surfaceDestroyed(SurfaceHolder holder) {
            X11DisplayView.this.surfaceChanged(null);
        }
    };

    public X11DisplayView(Context context) {
        super(context);
        getHolder().addCallback(callback);
        nativeInit();
        setFocusable(true);
        setFocusableInTouchMode(true);
    }

    /** One desktop pixel per screen pixel. */
    private void applyGeometry(int width, int height) {
        if (width <= 0 || height <= 0) return;
        guestWidth = width & ~1;     // X servers prefer even sizes
        guestHeight = height & ~1;
        setViewport(0, 0, width, height, guestWidth, guestHeight);
        float rate = getDisplay() != null ? getDisplay().getRefreshRate() : 60f;
        sendWindowChange(guestWidth, guestHeight, (int) rate, "builtin");
    }

    public boolean isConnected() { return connected(); }

    /** Connects the renderer to the X server; [fd] comes from X11NativeBridge.getXConnection in the server process. */
    public void connectRenderer(int fd) {
        connect(fd);
        requestFocus();
        if (getWidth() > 0) applyGeometry(getWidth(), getHeight());
    }

    /** Called from native code when the X window focus changes. We have no input-method state to reset yet. */
    @Keep
    @SuppressWarnings("unused")
    private void resetIme() {}

    /** Called from native code (renderer.c) on viewport changes; the viewport is the whole view, so nothing to track. */
    @Override
    public boolean onTouchEvent(MotionEvent e) {
        // First version: one finger acts as a mouse (tap = click, drag = press and move). Gestures come later.
        float x = e.getX(), y = e.getY();
        lastX = x; lastY = y;
        switch (e.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                downs++;
                sendMouseEvent(x, y, 0, false, false);
                sendMouseEvent(x, y, BUTTON_LEFT, true, false);
                pressed = true;
                return true;
            case MotionEvent.ACTION_MOVE:
                moves++;
                sendMouseEvent(x, y, 0, false, false);
                return true;
            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_CANCEL:
                ups++;
                if (pressed) sendMouseEvent(x, y, BUTTON_LEFT, false, false);
                pressed = false;
                return true;
            default:
                return true;
        }
    }

    @Override
    public boolean onGenericMotionEvent(MotionEvent e) {
        if (e.getSource() == android.view.InputDevice.SOURCE_MOUSE && e.getActionMasked() == MotionEvent.ACTION_HOVER_MOVE) {
            sendMouseEvent(e.getX(), e.getY(), 0, false, false);
            return true;
        }
        return super.onGenericMotionEvent(e);
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) { return key(keyCode, event, true) || super.onKeyDown(keyCode, event); }

    @Override
    public boolean onKeyUp(int keyCode, KeyEvent event) { return key(keyCode, event, false) || super.onKeyUp(keyCode, event); }

    private boolean key(int keyCode, KeyEvent event, boolean down) {
        if (keyCode == KeyEvent.KEYCODE_BACK || keyCode == KeyEvent.KEYCODE_VOLUME_UP || keyCode == KeyEvent.KEYCODE_VOLUME_DOWN) return false;
        int unicode = event.getUnicodeChar();
        boolean plain = !event.isCtrlPressed() && !event.isAltPressed() && !event.isMetaPressed();
        if (unicode != 0 && plain) {                       // typed characters go as text so every layout works
            if (down) sendTextEvent(String.valueOf((char) unicode).getBytes(StandardCharsets.UTF_8));
            return true;
        }
        return sendKeyEvent(event.getScanCode(), keyCode, down, 0);
    }
}

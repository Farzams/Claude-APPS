package app.linuxpad.x11;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.HapticFeedbackConstants;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.PointerIcon;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.WindowInsets;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;

import androidx.annotation.Keep;

import java.nio.charset.StandardCharsets;

/**
 * Shows the X server's screen and turns touch, mouse and keyboard into X events.
 * The desktop is created at the exact pixel size of this view, so it is sharp; text and icon size come from DPI
 * (see display/DisplayScale), never from scaling pixels.
 *
 * Touch (direct: the pointer is where the finger is):
 *   tap = left click, press and hold = right click, drag = drag with the left button,
 *   two fingers dragging = scroll, two-finger tap = right click, three-finger tap = show or hide the keyboard.
 */
@Keep
public class X11DisplayView extends SurfaceView {
    static {
        System.loadLibrary("Xlorie");
    }

    /** android.graphics.PixelFormat has no public constant for it; this is the HAL value Termux:X11 also uses. */
    private static final int HAL_PIXEL_FORMAT_BGRA_8888 = 5;
    private static final int BTN_LEFT = 1, BTN_MIDDLE = 2, BTN_RIGHT = 3, BTN_SCROLL = 4;
    private static final long TAP_MS = 250, LONG_PRESS_MS = 450;
    private static final float SCROLL_STEP_PX = 50f;   // finger travel for one wheel notch

    /** What this view has sent to the X server, for the on-screen diagnostics. */
    public volatile int moves, downs, ups;
    public volatile float lastX, lastY;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final float slop;
    // one finger
    private boolean fingerDown, dragging, longFired;
    private float downX, downY;
    // several fingers
    private boolean multi;
    private int maxFingers;
    private long multiDownTime;
    private float multiStartX, multiStartY, multiMoved, lastCx, lastCy, accX, accY;
    // mouse and keyboard
    private int mouseButtons;
    private String composing = "";

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

    private final Runnable longPress = () -> {
        if (fingerDown && !dragging && !multi) {
            longFired = true;
            performHapticFeedback(HapticFeedbackConstants.LONG_PRESS);
            click(BTN_RIGHT, downX, downY);
        }
    };

    public X11DisplayView(Context context) {
        super(context);
        slop = android.view.ViewConfiguration.get(context).getScaledTouchSlop();
        getHolder().addCallback(callback);
        nativeInit();
        setFocusable(true);
        setFocusableInTouchMode(true);
        // the desktop draws its own pointer; hide Android's arrow so a mouse does not show two
        setPointerIcon(PointerIcon.getSystemIcon(context, PointerIcon.TYPE_NULL));
    }

    /** One desktop pixel per screen pixel. */
    private void applyGeometry(int width, int height) {
        if (width <= 0 || height <= 0) return;
        int gw = width & ~1, gh = height & ~1;     // X servers prefer even sizes
        setViewport(0, 0, width, height, gw, gh);
        float rate = getDisplay() != null ? getDisplay().getRefreshRate() : 60f;
        sendWindowChange(gw, gh, (int) rate, "builtin");
    }

    public boolean isConnected() { return connected(); }

    /** Connects the renderer to the X server; [fd] comes from X11NativeBridge.getXConnection in the server process. */
    public void connectRenderer(int fd) {
        connect(fd);
        requestFocus();
        if (getWidth() > 0) applyGeometry(getWidth(), getHeight());
    }

    /** Called from native code when the X window focus changes. We have no input-method state to reset. */
    @Keep
    @SuppressWarnings("unused")
    private void resetIme() {}

    // ---- pointer helpers -------------------------------------------------------------------------------------------

    private void movePointer(float x, float y) {
        lastX = x; lastY = y; moves++;
        sendMouseEvent(x, y, 0, false, false);
    }

    private void press(int button) { downs++; sendMouseEvent(0, 0, button, true, false); }

    private void release(int button) { ups++; sendMouseEvent(0, 0, button, false, false); }

    private void click(int button, float x, float y) {
        movePointer(x, y);
        press(button);
        release(button);
    }

    private void wheel(float dx, float dy) { sendMouseEvent(dx, dy, BTN_SCROLL, false, true); }

    // ---- touch and mouse -------------------------------------------------------------------------------------------

    @Override
    public boolean onTouchEvent(MotionEvent e) {
        if (e.getToolType(0) == MotionEvent.TOOL_TYPE_MOUSE) return mouse(e);
        return finger(e);
    }

    /** A real mouse: its buttons arrive as touch-style events. */
    private boolean mouse(MotionEvent e) {
        movePointer(e.getX(), e.getY());
        int bs = e.getButtonState();
        int mask = ((bs & MotionEvent.BUTTON_PRIMARY) != 0 ? 1 : 0) | ((bs & MotionEvent.BUTTON_TERTIARY) != 0 ? 2 : 0) | ((bs & MotionEvent.BUTTON_SECONDARY) != 0 ? 4 : 0);
        int act = e.getActionMasked();
        if (act == MotionEvent.ACTION_UP || act == MotionEvent.ACTION_CANCEL) mask = 0;
        int changed = mask ^ mouseButtons;
        for (int b = 1; b <= 3; b++) {
            int bit = 1 << (b - 1);
            if ((changed & bit) != 0) { if ((mask & bit) != 0) press(b); else release(b); }
        }
        mouseButtons = mask;
        return true;
    }

    @Override
    public boolean onGenericMotionEvent(MotionEvent e) {
        if (e.getToolType(0) == MotionEvent.TOOL_TYPE_MOUSE) {
            switch (e.getActionMasked()) {
                case MotionEvent.ACTION_HOVER_MOVE:
                    movePointer(e.getX(), e.getY());
                    return true;
                case MotionEvent.ACTION_SCROLL: {
                    // Android: positive = up/right. X server: positive = down/right. One notch is 120.
                    float v = e.getAxisValue(MotionEvent.AXIS_VSCROLL), h = e.getAxisValue(MotionEvent.AXIS_HSCROLL);
                    wheel(h * 120f, -v * 120f);
                    return true;
                }
                default:
                    break;
            }
        }
        return super.onGenericMotionEvent(e);
    }

    /** Fingers (and a stylus). */
    private boolean finger(MotionEvent e) {
        int act = e.getActionMasked();
        int n = e.getPointerCount();
        switch (act) {
            case MotionEvent.ACTION_DOWN:
                fingerDown = true; dragging = false; longFired = false; multi = false;
                downX = e.getX(); downY = e.getY();
                movePointer(downX, downY);
                handler.postDelayed(longPress, LONG_PRESS_MS);
                return true;
            case MotionEvent.ACTION_POINTER_DOWN:
                handler.removeCallbacks(longPress);
                if (dragging) { release(BTN_LEFT); dragging = false; }
                if (!multi) {
                    multi = true; maxFingers = n; multiDownTime = e.getEventTime(); multiMoved = 0; accX = accY = 0;
                    multiStartX = lastCx = centerX(e); multiStartY = lastCy = centerY(e);
                }
                maxFingers = Math.max(maxFingers, n);
                return true;
            case MotionEvent.ACTION_MOVE:
                if (multi) {
                    float cx = centerX(e), cy = centerY(e);
                    multiMoved = Math.max(multiMoved, (float) Math.hypot(cx - multiStartX, cy - multiStartY));
                    if (maxFingers == 2 && n >= 2) {
                        accX += cx - lastCx; accY += cy - lastCy;
                        // fingers down = content down = scroll up (negative); fingers right = scroll left (negative)
                        while (Math.abs(accY) >= SCROLL_STEP_PX) { wheel(0, accY > 0 ? -120f : 120f); accY -= Math.signum(accY) * SCROLL_STEP_PX; }
                        while (Math.abs(accX) >= SCROLL_STEP_PX) { wheel(accX > 0 ? -120f : 120f, 0); accX -= Math.signum(accX) * SCROLL_STEP_PX; }
                    }
                    lastCx = cx; lastCy = cy;
                    return true;
                }
                if (!dragging && !longFired && Math.hypot(e.getX() - downX, e.getY() - downY) > slop) {
                    handler.removeCallbacks(longPress);
                    dragging = true;
                    movePointer(downX, downY);
                    press(BTN_LEFT);
                }
                if (dragging) movePointer(e.getX(), e.getY());
                return true;
            case MotionEvent.ACTION_POINTER_UP:
                return true;   // wait for the last finger
            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_CANCEL:
                handler.removeCallbacks(longPress);
                if (multi) {
                    boolean tap = act == MotionEvent.ACTION_UP && e.getEventTime() - multiDownTime < TAP_MS && multiMoved < slop;
                    if (tap && maxFingers == 2) click(BTN_RIGHT, multiStartX, multiStartY);
                    else if (tap && maxFingers >= 3) toggleKeyboard();
                    multi = false;
                } else if (dragging) {
                    movePointer(e.getX(), e.getY());
                    release(BTN_LEFT);
                } else if (!longFired && act == MotionEvent.ACTION_UP) {
                    click(BTN_LEFT, downX, downY);
                }
                fingerDown = false; dragging = false;
                return true;
            default:
                return true;
        }
    }

    private static float centerX(MotionEvent e) {
        float s = 0; for (int i = 0; i < e.getPointerCount(); i++) s += e.getX(i);
        return s / e.getPointerCount();
    }

    private static float centerY(MotionEvent e) {
        float s = 0; for (int i = 0; i < e.getPointerCount(); i++) s += e.getY(i);
        return s / e.getPointerCount();
    }

    // ---- keyboard --------------------------------------------------------------------------------------------------

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) { return key(keyCode, event, true) || super.onKeyDown(keyCode, event); }

    @Override
    public boolean onKeyUp(int keyCode, KeyEvent event) { return key(keyCode, event, false) || super.onKeyUp(keyCode, event); }

    private boolean key(int keyCode, KeyEvent event, boolean down) {
        if (keyCode == KeyEvent.KEYCODE_BACK || keyCode == KeyEvent.KEYCODE_VOLUME_UP || keyCode == KeyEvent.KEYCODE_VOLUME_DOWN) return false;
        int unicode = event.getUnicodeChar();
        boolean plain = !event.isCtrlPressed() && !event.isAltPressed() && !event.isMetaPressed();
        boolean named = keyCode == KeyEvent.KEYCODE_ENTER || keyCode == KeyEvent.KEYCODE_TAB || keyCode == KeyEvent.KEYCODE_DEL
                || keyCode == KeyEvent.KEYCODE_FORWARD_DEL || keyCode == KeyEvent.KEYCODE_ESCAPE;
        if (unicode != 0 && plain && !named) {            // typed characters go as text so every layout works
            if (down) sendTextEvent(String.valueOf(Character.toChars(unicode)).getBytes(StandardCharsets.UTF_8));
            return true;
        }
        return sendKeyEvent(event.getScanCode(), keyCode, down, 0);
    }

    public void toggleKeyboard() {
        requestFocus();
        android.view.WindowInsetsController c = getWindowInsetsController();
        if (c == null) return;
        WindowInsets insets = getRootWindowInsets();
        boolean shown = insets != null && insets.isVisible(WindowInsets.Type.ime());
        if (shown) c.hide(WindowInsets.Type.ime()); else c.show(WindowInsets.Type.ime());
    }

    @Override
    public boolean onCheckIsTextEditor() { return true; }

    /** The on-screen keyboard types into the desktop. Composing text is replaced as the keyboard edits it. */
    @Override
    public InputConnection onCreateInputConnection(EditorInfo out) {
        out.inputType = InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS;
        out.imeOptions = EditorInfo.IME_FLAG_NO_FULLSCREEN | EditorInfo.IME_FLAG_NO_EXTRACT_UI | EditorInfo.IME_ACTION_NONE;
        return new BaseInputConnection(this, false) {
            @Override public boolean commitText(CharSequence text, int newCursorPosition) {
                replaceComposing(text.toString());
                composing = "";
                return true;
            }

            @Override public boolean setComposingText(CharSequence text, int newCursorPosition) {
                replaceComposing(text.toString());
                composing = text.toString();
                return true;
            }

            @Override public boolean finishComposingText() { composing = ""; return true; }

            @Override public boolean deleteSurroundingText(int before, int after) {
                backspace(Math.max(before, 1));
                composing = "";
                return true;
            }

            @Override public boolean sendKeyEvent(KeyEvent event) {
                return key(event.getKeyCode(), event, event.getAction() == KeyEvent.ACTION_DOWN);
            }
        };
    }

    private void replaceComposing(String text) {
        if (!composing.isEmpty()) backspace(composing.codePointCount(0, composing.length()));
        if (!text.isEmpty()) sendTextEvent(text.getBytes(StandardCharsets.UTF_8));
    }

    private void backspace(int count) {
        for (int i = 0; i < count; i++) {
            sendKeyEvent(0, KeyEvent.KEYCODE_DEL, true, 0);
            sendKeyEvent(0, KeyEvent.KEYCODE_DEL, false, 0);
        }
    }
}

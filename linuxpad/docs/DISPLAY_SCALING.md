# Display scaling

Problem seen in other Linux-on-Android apps: on a tablet the text and icons are tiny, or sizes do not agree with each other.
Cause: Linux assumes 96 dpi, the POCO Pad is about 249 ppi (2560x1600, 12.1 in). Most apps change only the resolution.

LinuxPad renders the guest at the native panel resolution and sets size through DPI, consistently everywhere:

| Layer | Setting |
|---|---|
| X server / fonts | `Xft.dpi`, `xrandr --dpi` |
| XFCE | panel size, icon size, cursor size (xfconf) |
| GTK | `GDK_SCALE=1`, text follows `Xft.dpi` |
| Qt | `QT_AUTO_SCREEN_SCALE_FACTOR=0`, `QT_SCALE_FACTOR`, `QT_FONT_DPI` |
| Cursor | `XCURSOR_SIZE` (a size the theme ships) |
| Touch | panel and targets at least 6 to 7 mm |

The "size" slider is the only user knob (1.0 = real-size 96 dpi desktop monitor). The default 0.66 is a starting point to tune on the device.
Logic: `app/src/main/java/app/linuxpad/display/DisplayScale.kt`, tests in `app/src/test`.

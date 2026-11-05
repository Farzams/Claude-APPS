package app.linuxpad.display

import kotlin.math.hypot
import kotlin.math.roundToInt

/** What Android reports about the screen. */
data class DisplayInfo(
    val widthPx: Int,
    val heightPx: Int,
    val xdpi: Float,
    val ydpi: Float,
    val androidDensityDpi: Int,
    val refreshHz: Float,
)

/**
 * Everything the Linux side needs so that text, icons, panel and cursor look right on this screen.
 * The guest always renders at the panel's native resolution (sharp); size comes from DPI, never from pixel scaling.
 */
data class ScalePlan(
    val physicalPpi: Float,
    val factor: Float,          // 1.0 = classic 96 dpi desktop
    val xftDpi: Int,            // Xft.dpi, xrandr --dpi, QT_FONT_DPI
    val qtScaleFactor: Float,   // QT_SCALE_FACTOR (QT_AUTO_SCREEN_SCALE_FACTOR=0)
    val gtkScale: Int,          // GDK_SCALE (integer only); use 1 and let Xft.dpi scale text
    val cursorSize: Int,        // XCURSOR_SIZE; rootfs setup generates a theme at this size
    val panelSize: Int,         // XFCE panel height in px
    val iconSize: Int,          // panel / desktop icon size in px
    val minTouchPx: Int,        // smallest comfortable touch target
    val titlebarPx: Int,        // window title bar height
    val rowPx: Int,             // list / menu row height
    val guestWidth: Int,
    val guestHeight: Int,
)

object DisplayScale {
    const val CLASSIC_DPI = 96f
    /** Fraction of the "same physical size as a 96 dpi desktop monitor" that feels right for a tablet held or on a desk. */
    const val DEFAULT_COMFORT = 0.70f   // chosen on the POCO Pad: about 174 dpi
    const val MIN_DPI = 96
    const val MAX_DPI = 320

    /** Real pixels per inch. Android's xdpi/ydpi are right on most tablets; fall back to the logical density when they are not. */
    fun physicalPpi(d: DisplayInfo, diagonalInches: Float? = null): Float {
        if (diagonalInches != null && diagonalInches > 3f) {
            return (hypot(d.widthPx.toFloat(), d.heightPx.toFloat()) / diagonalInches)
        }
        val sane = { v: Float -> v in 80f..700f }
        return if (sane(d.xdpi) && sane(d.ydpi)) (d.xdpi + d.ydpi) / 2f else d.androidDensityDpi.toFloat()
    }

    /** [comfort] 1.0 = real-size 96 dpi desktop; lower is smaller text and icons. Tablets read best around 0.55 to 0.8. */
    fun plan(d: DisplayInfo, comfort: Float = DEFAULT_COMFORT, diagonalInches: Float? = null, touchFirst: Boolean = true): ScalePlan {
        val ppi = physicalPpi(d, diagonalInches)
        val dpi = (ppi * comfort).coerceIn(MIN_DPI.toFloat(), MAX_DPI.toFloat())
        val xft = ((dpi / 2f).roundToInt() * 2).coerceIn(MIN_DPI, MAX_DPI)   // steps of 2 keep the slider stable
        val factor = xft / CLASSIC_DPI
        val minTouch = (ppi / 25.4f * 7f).roundToInt()                      // 7 mm
        val mm = ppi / 25.4f
        val panel = (28 * factor).roundToInt().let { if (touchFirst) maxOf(it, (mm * 7f).roundToInt()) else it }
        val titlebar = if (touchFirst) (mm * 6.5f).roundToInt() else (30 * factor).roundToInt()
        val row = if (touchFirst) (mm * 6.7f).roundToInt() else (19 * factor).roundToInt()
        val icon = (24 * factor).roundToInt()
        val cursor = ((22 * factor) / 4f).roundToInt() * 4   // any size: the session builds a cursor theme at exactly this size (chosen on the device: 40 px at 174 dpi)
        return ScalePlan(
            physicalPpi = ppi,
            factor = factor,
            xftDpi = xft,
            qtScaleFactor = (factor * 10).roundToInt() / 10f,
            gtkScale = 1,
            cursorSize = cursor,
            panelSize = panel,
            iconSize = icon,
            minTouchPx = minTouch,
            titlebarPx = titlebar,
            rowPx = row,
            guestWidth = d.widthPx and 1.inv(),   // X servers prefer even sizes
            guestHeight = d.heightPx and 1.inv(),
        )
    }

    /** The environment the Linux session is started with. */
    fun environment(p: ScalePlan): Map<String, String> = mapOf(
        "QT_AUTO_SCREEN_SCALE_FACTOR" to "0",
        "QT_SCALE_FACTOR" to p.qtScaleFactor.toString(),
        "QT_FONT_DPI" to p.xftDpi.toString(),
        "GDK_SCALE" to p.gtkScale.toString(),
        "XCURSOR_SIZE" to p.cursorSize.toString(),
    )
}

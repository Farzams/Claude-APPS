package app.linuxpad.display

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DisplayScaleTest {
    // POCO Pad: 2560x1600, 12.1 inch, 120 Hz
    private val pocoPad = DisplayInfo(2560, 1600, 249f, 249f, 320, 120f)

    @Test fun diagonalGivesTheRealPpi() {
        val ppi = DisplayScale.physicalPpi(pocoPad, 12.1f)
        assertEquals(249.5f, ppi, 1f)
    }

    @Test fun pocoPadGetsAReadableDesktop() {
        val p = DisplayScale.plan(pocoPad, diagonalInches = 12.1f)
        assertTrue("dpi ${p.xftDpi}", p.xftDpi in 150..180)         // not the 96 that makes everything tiny
        assertEquals(0, p.xftDpi % 2)
        assertEquals(174, p.xftDpi)                                 // the size chosen on the device
        assertEquals(2560, p.guestWidth); assertEquals(1600, p.guestHeight)  // native, sharp
        assertEquals(40, p.cursorSize)
        assertTrue(p.panelSize in 66..74)
        assertTrue(p.titlebarPx in 58..70)
        assertTrue(p.rowPx in 60..72)
        assertTrue(p.minTouchPx in 60..80)
    }

    @Test fun comfortSliderIsMonotonic() {
        var last = 0
        for (c in listOf(0.4f, 0.55f, 0.7f, 0.85f, 1f)) {
            val dpi = DisplayScale.plan(pocoPad, c, 12.1f).xftDpi
            assertTrue(dpi >= last); last = dpi
        }
    }

    @Test fun absurdXdpiFallsBackToDensity() {
        val broken = pocoPad.copy(xdpi = 0f, ydpi = 0f)
        assertEquals(320f, DisplayScale.physicalPpi(broken), 0.1f)
    }

    @Test fun neverBelowClassicOrAboveLimit() {
        val tiny = DisplayScale.plan(DisplayInfo(800, 480, 100f, 100f, 160, 60f), 0.3f)
        assertEquals(DisplayScale.MIN_DPI, tiny.xftDpi)
        val huge = DisplayScale.plan(pocoPad, 3f, 12.1f)
        assertEquals(DisplayScale.MAX_DPI, huge.xftDpi)
    }

    @Test fun environmentCarriesTheValues() {
        val env = DisplayScale.environment(DisplayScale.plan(pocoPad, diagonalInches = 12.1f))
        assertEquals("0", env["QT_AUTO_SCREEN_SCALE_FACTOR"])
        assertEquals("40", env["XCURSOR_SIZE"])
    }
}

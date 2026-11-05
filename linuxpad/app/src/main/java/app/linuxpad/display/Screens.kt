package app.linuxpad.display

import android.app.Activity
import android.view.WindowManager

object Screens {
    /** What Android reports about the screen this activity is on. */
    fun read(a: Activity): DisplayInfo {
        val b = a.getSystemService(WindowManager::class.java).maximumWindowMetrics.bounds
        val dm = a.resources.displayMetrics
        return DisplayInfo(b.width(), b.height(), dm.xdpi, dm.ydpi, dm.densityDpi, a.display?.refreshRate ?: 60f)
    }
}

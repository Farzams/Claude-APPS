package app.pdftoolkit.mobile

import android.content.Intent
import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Drives the real app on an emulator: compiles an English and a Persian document offline and takes screenshots. */
@RunWith(AndroidJUnit4::class)
class EndToEndTest {
    private val instr = InstrumentationRegistry.getInstrumentation()
    private val device = UiDevice.getInstance(instr)

    private fun shot(name: String) {
        Thread.sleep(700)
        val pfd = instr.uiAutomation.executeShellCommand("sh -c 'mkdir -p /data/local/tmp/shots && screencap -p /data/local/tmp/shots/$name.png'")
        ParcelFileDescriptor.AutoCloseInputStream(pfd).use { it.readBytes() }
        Log.i("PDFTK", "screenshot $name")
    }

    private fun click(res: String, wait: Long = 20_000) {
        assertTrue("not found: $res", device.wait(Until.hasObject(By.res(res)), wait))
        device.findObject(By.res(res)).click()
    }

    private fun compileAndWait(name: String): Boolean {
        click("compile")
        val end = System.currentTimeMillis() + 4 * 60_000
        while (System.currentTimeMillis() < end) {
            if (device.hasObject(By.res("pdf_page_0"))) { Thread.sleep(1500); shot(name); return true }
            if (device.hasObject(By.res("compile_failed"))) { shot(name + "_FAILED"); return false }
            Thread.sleep(1000)
        }
        shot(name + "_TIMEOUT")
        return false
    }

    @Test
    fun compilesEnglishAndPersianThenThemes() {
        val ctx = instr.targetContext
        val intent = ctx.packageManager.getLaunchIntentForPackage(ctx.packageName)!!.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ctx.startActivity(intent)
        assertTrue(device.wait(Until.hasObject(By.res("card_latex")), 30_000))
        shot("01_home")
        click("card_latex")
        assertTrue(device.wait(Until.hasObject(By.res("compile")), 15_000))
        shot("02_editor")

        val t0 = System.currentTimeMillis()
        val en = compileAndWait("03_preview_english")
        Log.i("PDFTK", "English compile ok=$en in ${(System.currentTimeMillis() - t0) / 1000}s")
        assertTrue("English document did not compile", en)

        click("tab_editor")
        click("templates")
        assertTrue(device.wait(Until.hasObject(By.text("Persian article (XeLaTeX)")), 5_000))
        device.findObject(By.text("Persian article (XeLaTeX)")).click()
        Thread.sleep(500)
        shot("04_persian_source")
        val t1 = System.currentTimeMillis()
        val fa = compileAndWait("05_preview_persian")
        Log.i("PDFTK", "Persian compile ok=$fa in ${(System.currentTimeMillis() - t1) / 1000}s")
        assertTrue("Persian document did not compile", fa)

        click("back")
        click("open_settings")
        click("mode_dark")
        shot("06_settings_dark")
        click("style_paper")
        click("accent_#0F766E")
        shot("07_settings_paper_dark_teal")
        click("lang_fa")
        shot("08_settings_persian")
        click("back")
        assertTrue(device.wait(Until.hasObject(By.res("card_latex")), 10_000))
        shot("09_home_persian_dark")
    }
}

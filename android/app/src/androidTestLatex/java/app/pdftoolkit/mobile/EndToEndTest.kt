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

    /** Swipe up until the item is really on screen (long pages such as Settings scroll). */
    private fun scrollTo(res: String) {
        var tries = 0
        while (tries < 8) {
            val o = device.findObject(By.res(res))
            val b = o?.visibleBounds
            if (b != null && !b.isEmpty && b.centerY() in 100 until device.displayHeight - 100) return
            device.swipe(device.displayWidth / 2, device.displayHeight * 3 / 4, device.displayWidth / 2, device.displayHeight * 2 / 5, 25)
            Thread.sleep(350)
            tries++
        }
    }

    private fun click(res: String, wait: Long = 20_000) {
        assertTrue("not found: $res", device.wait(Until.hasObject(By.res(res)), wait))
        scrollTo(res)
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

    private fun openNewProject(template: String) {
        click("new_project")
        assertTrue("template list", device.wait(Until.hasObject(By.text(template)), 10_000))
        device.findObject(By.text(template)).click()
        Thread.sleep(300)
        device.findObject(By.text("Create")).click()
        assertTrue(device.wait(Until.hasObject(By.res("compile")), 15_000))
    }

    @Test
    fun compilesEnglishAndPersianThenThemes() {
        val ctx = instr.targetContext
        val intent = ctx.packageManager.getLaunchIntentForPackage(ctx.packageName)!!.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ctx.startActivity(intent)
        assertTrue(device.wait(Until.hasObject(By.res("project_0")), 30_000))
        shot("01_projects")
        click("project_0")
        assertTrue(device.wait(Until.hasObject(By.res("compile")), 15_000))
        shot("02_editor")

        val t0 = System.currentTimeMillis()
        val en = compileAndWait("03_preview_english")
        Log.i("PDFTK", "English compile ok=$en in ${(System.currentTimeMillis() - t0) / 1000}s")
        assertTrue("English document did not compile", en)
        assertTrue("page indicator", device.hasObject(By.res("page_indicator")))
        click("zoom_in")
        Thread.sleep(800)
        val pct = device.findObject(By.textMatches("\\d+%"))?.text
        Log.i("PDFTK", "zoom percent after zoom in: $pct")
        assertTrue("zoom percent should change, was $pct", pct != null && pct != "100%")
        Log.i("PDFTK", "zoom ok")
        click("night_mode")
        Thread.sleep(1200)
        shot("03b_preview_zoomed_night")
        click("night_mode")

        click("tab_editor")
        click("more"); click("menu_outline")
        assertTrue("outline dialog", device.wait(Until.hasObject(By.res("outline_stats")), 8_000))
        shot("03d_outline")
        Log.i("PDFTK", "outline ok")
        device.pressBack()
        Thread.sleep(500)
        click("more"); click("menu_history")
        assertTrue("history dialog", device.wait(Until.hasObject(By.res("history_list")), 8_000))
        assertTrue("a version was saved by the compile", device.wait(Until.hasObject(By.res("history_row_0")), 5_000))
        shot("03e_history")
        Log.i("PDFTK", "history ok")
        device.pressBack()
        Thread.sleep(500)
        click("find")
        assertTrue(device.wait(Until.hasObject(By.res("find_field")), 5_000))
        device.findObject(By.res("find_field")).text = "section"
        Thread.sleep(500)
        shot("03c_find")
        click("find")

        click("back")
        assertTrue(device.wait(Until.hasObject(By.res("new_project")), 10_000))
        openNewProject("Persian article (XeLaTeX)")
        shot("04_persian_source")
        val t1 = System.currentTimeMillis()
        val fa = compileAndWait("05_preview_persian")
        Log.i("PDFTK", "Persian compile ok=$fa in ${(System.currentTimeMillis() - t1) / 1000}s")
        assertTrue("Persian document did not compile", fa)

        click("back")
        assertTrue(device.wait(Until.hasObject(By.res("new_project")), 10_000))
        openNewProject("Article with bibliography")
        shot("05b_bib_source")
        val t2 = System.currentTimeMillis()
        val bib = compileAndWait("05c_preview_bib")
        Log.i("PDFTK", "Bibliography compile ok=$bib in ${(System.currentTimeMillis() - t2) / 1000}s")
        assertTrue("Bibliography document did not compile", bib)

        click("back")
        assertTrue(device.wait(Until.hasObject(By.res("new_project")), 10_000))
        click("open_settings")
        click("mode_dark")
        shot("06_settings_dark")
        click("style_paper")
        click("accent_#0F766E")
        shot("07_settings_paper_dark_teal")
        scrollTo("about_author")
        val author = device.findObject(By.res("about_author"))?.text
        Log.i("PDFTK", "about author: $author")
        assertTrue("about shows the author", author == "Farzam Sadri")
        shot("07b_about")
        Log.i("PDFTK", "about ok")
        click("lang_fa")
        shot("08_settings_persian")
        click("back")
        assertTrue(device.wait(Until.hasObject(By.res("new_project")), 10_000))
        shot("09_projects_persian_dark")
    }
}

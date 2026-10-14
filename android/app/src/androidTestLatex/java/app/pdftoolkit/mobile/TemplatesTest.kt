package app.pdftoolkit.mobile

import android.content.Intent
import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/** Every new starting point compiles offline, and the insert tools produce LaTeX that compiles. */
@RunWith(AndroidJUnit4::class)
class TemplatesTest {
    private val instr = InstrumentationRegistry.getInstrumentation()
    private val device = UiDevice.getInstance(instr)

    private fun shot(name: String) {
        Thread.sleep(500)
        ParcelFileDescriptor.AutoCloseInputStream(instr.uiAutomation.executeShellCommand("sh -c 'mkdir -p /data/local/tmp/shots && screencap -p /data/local/tmp/shots/$name.png'")).use { it.readBytes() }
        Log.i("PDFTK", "screenshot $name")
    }

    private fun launch() {
        val ctx = instr.targetContext
        Prefs(ctx).apply { lang = "en"; theme = "qp_light"; accent = "" }      // the other tests leave Persian and the dark theme behind
        ParcelFileDescriptor.AutoCloseInputStream(instr.uiAutomation.executeShellCommand("appops set ${ctx.packageName} MANAGE_EXTERNAL_STORAGE allow")).use { it.readBytes() }
        Thread.sleep(800)
        ctx.startActivity(ctx.packageManager.getLaunchIntentForPackage(ctx.packageName)!!.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
        assertTrue(device.wait(Until.hasObject(By.res("new_project")), 30_000))
    }

    private fun clickRes(res: String) {
        assertTrue("not found: $res", device.wait(Until.hasObject(By.res(res)), 20_000))
        device.findObject(By.res(res)).click()
    }

    private fun clickText(text: String) {
        assertTrue("not found: $text", device.wait(Until.hasObject(By.text(text)), 10_000))
        device.findObject(By.text(text)).click()
    }

    private fun newProject(template: String) {
        clickRes("new_project")
        // the dialog is a separate window without resource ids: look for the template by its name, swiping its list up
        assertTrue("dialog", device.wait(Until.hasObject(By.text("Templates")), 10_000))
        var tries = 0
        while (!device.hasObject(By.text(template)) && tries < 45) {
            // the template list is the smallest scrollable thing on screen; move it a little at a time so nothing is skipped
            val list = device.findObjects(By.scrollable(true)).minByOrNull { it.visibleBounds.height() }
            if (list != null) list.scroll(androidx.test.uiautomator.Direction.DOWN, 0.3f, 600) else device.swipe(device.displayWidth / 2, device.displayHeight * 65 / 100, device.displayWidth / 2, device.displayHeight * 55 / 100, 40)
            Thread.sleep(350)
            tries++
        }
        clickText(template)
        Thread.sleep(300)
        clickText("Create")
        assertTrue(device.wait(Until.hasObject(By.res("compile")), 15_000))
    }

    private fun compileOk(name: String): Boolean {
        clickRes("compile")
        val end = System.currentTimeMillis() + 4 * 60_000
        while (System.currentTimeMillis() < end) {
            if (device.hasObject(By.res("pdf_page_0"))) { Thread.sleep(1200); shot(name); return true }
            if (device.hasObject(By.res("compile_failed")) || device.hasObject(By.text("Compile failed"))) { shot(name + "_FAILED"); return false }
            Thread.sleep(1000)
        }
        shot(name + "_TIMEOUT")
        return false
    }

    @Test
    fun everyNewTemplateCompiles() {
        launch()
        val names = listOf(
            "Physics", "Chemistry", "Computer science", "Engineering", "Biology lab report", "Data and plots",
            "IEEE conference paper", "Elsevier article", "Springer article", "APA-style paper", "Thesis", "A0 poster",
        )
        val failed = ArrayList<String>()
        for ((i, n) in names.withIndex()) {
            newProject(n)
            val t0 = System.currentTimeMillis()
            val ok = compileOk("t%02d_%s".format(i, n.filter { it.isLetterOrDigit() }))
            Log.i("PDFTK", "template $n ok=$ok in ${(System.currentTimeMillis() - t0) / 1000}s")
            if (!ok) failed.add(n)
            clickRes("back")
            assertTrue(device.wait(Until.hasObject(By.res("new_project")), 10_000))
        }
        assertTrue("templates that did not compile: $failed", failed.isEmpty())
        Log.i("PDFTK", "templates ok")
    }

    @Test
    fun insertToolsMakeCompilableLatex() {
        val dl = File("/sdcard/Download").also { it.mkdirs() }
        File(dl, "tools_data.csv").writeText("time,signal,model\n0,0,0\n1,1.2,1.1\n2,1.9,2.0\n3,2.4,2.5\n4,2.7,2.7\n")
        val bmp = android.graphics.Bitmap.createBitmap(120, 80, android.graphics.Bitmap.Config.ARGB_8888).also { it.eraseColor(0xFF3366CC.toInt()) }
        File(dl, "tools_pic.png").outputStream().use { bmp.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, it) }
        launch()
        newProject("Biology lab report")
        // put the cursor in the body of the document, then insert a table from the csv file
        device.click(device.displayWidth / 2, device.displayHeight * 6 / 10)
        Thread.sleep(400)

        fun tool(label: String) {
            clickRes("more"); clickText("Insert and check…")
            clickText(label)
        }
        fun pickFromDownloads(name: String) {
            assertTrue("in-app picker", device.wait(Until.hasObject(By.res("file_browser")), 10_000))
            if (device.wait(Until.hasObject(By.res("place_downloads")), 2_500)) device.findObject(By.res("place_downloads")).click()   // later pickers reopen in the last folder
            assertTrue("$name listed", device.wait(Until.hasObject(By.text(name)), 10_000))
            device.findObject(By.text(name)).click()
            Thread.sleep(600)
            if (device.hasObject(By.res("fm_add"))) device.findObject(By.res("fm_add")).click()
        }

        tool("Table or plot from CSV")
        pickFromDownloads("tools_data.csv")
        assertTrue("csv dialog", device.wait(Until.hasObject(By.text("Line graph")), 10_000))
        shot("tool1_csv_dialog")
        clickText("Line graph")
        clickText("Insert")
        Thread.sleep(600)
        Log.i("PDFTK", "csv plot inserted")

        device.click(device.displayWidth / 2, device.displayHeight * 6 / 10)
        tool("Picture")
        pickFromDownloads("tools_pic.png")
        Thread.sleep(1200)
        shot("tool2_after_picture")
        Log.i("PDFTK", "picture inserted")

        tool("Citation from a DOI")
        assertTrue("doi field", device.wait(Until.hasObject(By.clazz("android.widget.EditText")), 5_000))
        device.findObject(By.clazz("android.widget.EditText")).text = "not a doi"
        clickText("Add")
        assertTrue("bad DOI is explained", device.wait(Until.hasObject(By.textContains("does not look like a DOI")), 5_000))
        device.pressBack(); Thread.sleep(400)
        Log.i("PDFTK", "doi check ok")

        tool("Citation style")
        clickText("Numbered, in order of citation")
        Thread.sleep(500)

        tool("Check the project")
        assertTrue("check dialog", device.wait(Until.hasObject(By.textContains("to look at")), 8_000) || device.hasObject(By.text("No problems found.")))
        shot("tool3_check")
        Log.i("PDFTK", "check dialog ok")
        device.pressBack(); Thread.sleep(500)

        val ok = compileOk("tool4_compiled")
        Log.i("PDFTK", "insert tools compile ok=$ok")
        assertTrue("project with inserted table, plot and picture did not compile", ok)
        Log.i("PDFTK", "insert tools ok")
    }
}

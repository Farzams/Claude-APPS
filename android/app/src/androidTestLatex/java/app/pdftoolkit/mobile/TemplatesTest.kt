package app.pdftoolkit.mobile

import android.content.Intent
import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Direction
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
        assertTrue(device.wait(Until.hasObject(By.res("template_list")), 10_000))
        var tries = 0
        while (!device.hasObject(By.text(template)) && tries < 12) {
            device.findObject(By.res("template_list")).scroll(Direction.DOWN, 0.6f)
            Thread.sleep(250)
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
            if (device.hasObject(By.res("compile_failed"))) { shot(name + "_FAILED"); return false }
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

        fun tool(tag: String) {
            clickRes("more"); clickText("Insert and check…")
            clickRes(tag)
        }
        fun pickFromDownloads(name: String) {
            assertTrue("in-app picker", device.wait(Until.hasObject(By.res("file_browser")), 10_000))
            clickRes("place_downloads")
            assertTrue("$name listed", device.wait(Until.hasObject(By.text(name)), 10_000))
            device.findObject(By.text(name)).click()
            Thread.sleep(600)
            if (device.hasObject(By.res("fm_add"))) device.findObject(By.res("fm_add")).click()
        }

        tool("tool_csv")
        pickFromDownloads("tools_data.csv")
        assertTrue("csv dialog", device.wait(Until.hasObject(By.res("csv_insert")), 10_000))
        shot("tool1_csv_dialog")
        clickRes("csv_line")
        clickRes("csv_insert")
        Thread.sleep(600)
        Log.i("PDFTK", "csv plot inserted")

        device.click(device.displayWidth / 2, device.displayHeight * 6 / 10)
        tool("tool_picture")
        pickFromDownloads("tools_pic.png")
        Thread.sleep(1200)
        shot("tool2_after_picture")
        Log.i("PDFTK", "picture inserted")

        tool("tool_doi")
        assertTrue(device.wait(Until.hasObject(By.res("doi_field")), 5_000))
        device.findObject(By.res("doi_field")).text = "not a doi"
        clickRes("doi_add")
        assertTrue("bad DOI is explained", device.wait(Until.hasObject(By.textContains("does not look like a DOI")), 5_000))
        device.pressBack(); Thread.sleep(400)
        Log.i("PDFTK", "doi check ok")

        tool("tool_style")
        clickRes("style_unsrt")
        Thread.sleep(500)

        tool("tool_check")
        assertTrue("check dialog", device.wait(Until.hasObject(By.res("check_summary")), 8_000))
        shot("tool3_check")
        Log.i("PDFTK", "check dialog ok")
        device.pressBack(); Thread.sleep(500)

        val ok = compileOk("tool4_compiled")
        Log.i("PDFTK", "insert tools compile ok=$ok")
        assertTrue("project with inserted table, plot and picture did not compile", ok)
        Log.i("PDFTK", "insert tools ok")
    }
}

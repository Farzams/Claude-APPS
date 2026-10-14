package app.pdftoolkit.mobile

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Paint
import android.graphics.pdf.PdfDocument
import android.net.Uri
import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import java.io.ByteArrayOutputStream
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import org.junit.runner.RunWith

/** Runs the PDF operations on a real Android runtime and opens every tool screen. */
@RunWith(AndroidJUnit4::class)
class PdfToolsTest {
    private val instr = InstrumentationRegistry.getInstrumentation()
    private val ctx = instr.targetContext
    private val device = UiDevice.getInstance(instr)

    private fun shot(name: String) {
        Thread.sleep(600)
        val pfd = instr.uiAutomation.executeShellCommand("sh -c 'mkdir -p /data/local/tmp/shots && screencap -p /data/local/tmp/shots/$name.png'")
        ParcelFileDescriptor.AutoCloseInputStream(pfd).use { it.readBytes() }
        Log.i("PDFTK", "screenshot $name")
    }

    private fun makePdf(name: String, pages: Int): Uri {
        val doc = PdfDocument()
        val paint = Paint().apply { textSize = 28f; color = Color.BLACK }
        for (i in 1..pages) {
            val page = doc.startPage(PdfDocument.PageInfo.Builder(595, 842, i).create())
            page.canvas.drawText("$name page $i", 60f, 100f, paint)
            doc.finishPage(page)
        }
        val f = File(ctx.cacheDir, name)
        f.outputStream().use { doc.writeTo(it) }
        doc.close()
        return Uri.fromFile(f)
    }

    private fun bytes(block: (ByteArrayOutputStream) -> Unit): ByteArray = ByteArrayOutputStream().also(block).toByteArray()

    private fun toUri(name: String, data: ByteArray): Uri {
        val f = File(ctx.cacheDir, name)
        f.writeBytes(data)
        return Uri.fromFile(f)
    }

    @Test
    fun pdfOperations() {
        PdfOps.init(ctx)
        val a = makePdf("a.pdf", 3)
        val b = makePdf("b.pdf", 2)

        val merged = toUri("merged.pdf", bytes { PdfOps.merge(ctx, listOf(a, b), it) })
        assertEquals("merge", 5, PdfOps.pageCount(ctx, merged))
        Log.i("PDFTK", "merge ok")

        val picked = toUri("picked.pdf", bytes { PdfOps.extract(ctx, merged, listOf(0, 4), it) })
        assertEquals("extract", 2, PdfOps.pageCount(ctx, picked))
        assertEquals("ranges", listOf(listOf(0, 1, 2), listOf(4)), PdfOps.parseRanges("1-3, 5", 5))
        Log.i("PDFTK", "extract ok")

        val turned = toUri("turned.pdf", bytes { PdfOps.build(ctx, merged, listOf(PageItem(2, 90), PageItem(0)), it) })
        PdfOps.load(ctx, turned).use {
            assertEquals(2, it.numberOfPages)
            assertEquals("turn", 90, it.getPage(0).rotation)
        }
        Log.i("PDFTK", "organize ok")

        val locked = toUri("locked.pdf", bytes { PdfOps.protect(ctx, a, "secret", it) })
        try {
            PdfOps.pageCount(ctx, locked)
            fail("a protected file opened without its password")
        } catch (e: Exception) {
            Log.i("PDFTK", "locked file refused: ${e.javaClass.simpleName}")
        }
        assertEquals("open with password", 3, PdfOps.pageCount(ctx, locked, "secret"))
        val open = toUri("open.pdf", bytes { PdfOps.unprotect(ctx, locked, "secret", it) })
        assertEquals("password removed", 3, PdfOps.pageCount(ctx, open))
        Log.i("PDFTK", "protect ok")

        val small = toUri("small.pdf", bytes { PdfOps.compress(ctx, merged, 80, 0.5f, it) })
        assertEquals("compress", 5, PdfOps.pageCount(ctx, small))
        Log.i("PDFTK", "compress ok: ${PdfOps.sizeOf(ctx, merged)} -> ${PdfOps.sizeOf(ctx, small)}")

        val pics = (1..2).map { i ->
            val bmp = Bitmap.createBitmap(400, 300, Bitmap.Config.ARGB_8888).apply { eraseColor(if (i == 1) Color.RED else Color.BLUE) }
            val f = File(ctx.cacheDir, "pic$i.png")
            f.outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
            Uri.fromFile(f)
        }
        val fromPics = toUri("pics.pdf", bytes { PdfOps.picturesToPdf(ctx, pics, it) })
        assertEquals("pictures to pdf", 2, PdfOps.pageCount(ctx, fromPics))
        Log.i("PDFTK", "pictures ok")

        val marked = toUri("marked.pdf", bytes { PdfOps.watermark(ctx, merged, "CONFIDENTIAL", 0.3f, 0.6f, 45f, Color.RED, it) })
        assertEquals("watermark", 5, PdfOps.pageCount(ctx, marked))
        assertTrue("watermark adds content", PdfOps.sizeOf(ctx, marked) > PdfOps.sizeOf(ctx, merged))
        val persian = toUri("persian.pdf", bytes { PdfOps.watermark(ctx, a, "محرمانه", 0.3f, 0.5f, 0f, Color.BLUE, it) })
        assertEquals("persian watermark", 3, PdfOps.pageCount(ctx, persian))
        Log.i("PDFTK", "watermark ok")

        val numbered = toUri("numbered.pdf", bytes { PdfOps.numberPages(ctx, merged, "page", false, 1, 1, 11f, it) })
        assertEquals("numbers", 5, PdfOps.pageCount(ctx, numbered))
        Log.i("PDFTK", "numbers ok")
    }

    private fun zipOf(name: String, entries: Map<String, ByteArray>): Uri {
        val f = File(ctx.cacheDir, name)
        java.util.zip.ZipOutputStream(f.outputStream()).use { z ->
            for ((n, b) in entries) { z.putNextEntry(java.util.zip.ZipEntry(n)); z.write(b); z.closeEntry() }
        }
        return Uri.fromFile(f)
    }

    private fun convert(uri: Uri, name: String): Uri = toUri("conv_$name.pdf", bytes { DocConvert.convert(ctx, uri, name, it) })

    @Test
    fun bookFormats() {
        PdfOps.init(ctx)
        // TXT, English and Persian
        val txt = toUri("book.txt", ("Hello world.\n\nSecond paragraph of the text.\n\nسلام دنیا، این یک آزمایش است.").toByteArray())
        assertTrue("txt", PdfOps.pageCount(ctx, convert(txt, "book.txt")) >= 1)
        // HTML
        val html = toUri("page.html", "<html><body><h1>Title</h1><p>Some <b>bold</b> text.</p><ul><li>one</li><li>two</li></ul></body></html>".toByteArray())
        assertTrue("html", PdfOps.pageCount(ctx, convert(html, "page.html")) >= 1)
        Log.i("PDFTK", "txt and html ok")
        // EPUB with two chapters
        val epub = zipOf("book.epub", mapOf(
            "mimetype" to "application/epub+zip".toByteArray(),
            "META-INF/container.xml" to "<?xml version=\"1.0\"?><container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\"><rootfiles><rootfile full-path=\"OEBPS/content.opf\" media-type=\"application/oebps-package+xml\"/></rootfiles></container>".toByteArray(),
            "OEBPS/content.opf" to "<?xml version=\"1.0\"?><package xmlns=\"http://www.idpf.org/2007/opf\" version=\"2.0\"><manifest><item id=\"c1\" href=\"c1.xhtml\" media-type=\"application/xhtml+xml\"/><item id=\"c2\" href=\"c2.xhtml\" media-type=\"application/xhtml+xml\"/></manifest><spine><itemref idref=\"c1\"/><itemref idref=\"c2\"/></spine></package>".toByteArray(),
            "OEBPS/c1.xhtml" to "<html><body><h2>Chapter one</h2><p>First chapter text.</p></body></html>".toByteArray(),
            "OEBPS/c2.xhtml" to "<html><body><h2>Chapter two</h2><p>Second chapter text.</p></body></html>".toByteArray(),
        ))
        assertTrue("epub has a page per chapter", PdfOps.pageCount(ctx, convert(epub, "book.epub")) >= 2)
        Log.i("PDFTK", "epub ok")
        // FB2
        val fb2 = toUri("book.fb2", ("<?xml version=\"1.0\" encoding=\"utf-8\"?><FictionBook><description><title-info><book-title>Test book</book-title></title-info></description>" +
            "<body><section><title><p>One</p></title><p>Some <emphasis>text</emphasis> here.</p></section></body></FictionBook>").toByteArray())
        assertTrue("fb2", PdfOps.pageCount(ctx, convert(fb2, "book.fb2")) >= 1)
        Log.i("PDFTK", "fb2 ok")
        // CBZ with two pictures
        val pics = (1..2).associate { i ->
            val bmp = Bitmap.createBitmap(300, 400, Bitmap.Config.ARGB_8888).apply { eraseColor(if (i == 1) Color.RED else Color.GREEN) }
            "page$i.png" to ByteArrayOutputStream().also { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }.toByteArray()
        }
        assertEquals("cbz", 2, PdfOps.pageCount(ctx, convert(zipOf("comic.cbz", pics), "comic.cbz")))
        Log.i("PDFTK", "cbz ok")
        // DjVu (two pages, made with DjVuLibre's own tools)
        val djvu = File(ctx.cacheDir, "sample.djvu")
        instr.context.assets.open("sample.djvu").use { i -> djvu.outputStream().use { i.copyTo(it) } }
        val pdf = convert(Uri.fromFile(djvu), "sample.djvu")
        assertEquals("djvu pages", 2, PdfOps.pageCount(ctx, pdf))
        assertTrue("djvu picture is not empty", PdfOps.sizeOf(ctx, pdf) > 5_000)
        Log.i("PDFTK", "djvu ok: ${PdfOps.sizeOf(ctx, pdf)} bytes")
    }

    @Test
    fun everyScreenOpens() {
        val intent = ctx.packageManager.getLaunchIntentForPackage(ctx.packageName)!!.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ctx.startActivity(intent)
        assertTrue(device.wait(Until.hasObject(By.res("card_merge")), 30_000))
        shot("p01_home")
        for (key in listOf("merge", "split", "organize", "compress", "img2pdf", "pdf2img", "protect", "watermark", "numbers", "docs2pdf")) {
            device.findObject(By.res("card_$key")).click()
            assertTrue("screen $key did not open", device.wait(Until.hasObject(By.res("back")), 10_000))
            shot("p02_$key")
            device.findObject(By.res("back")).click()
            assertTrue(device.wait(Until.hasObject(By.res("card_merge")), 10_000))
        }
    }
}

package app.pdftoolkit.mobile

import android.graphics.Bitmap
import android.graphics.Color as AColor
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.File

private class PdfDoc(file: File) {
    private val pfd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
    private val renderer = PdfRenderer(pfd)
    private val lock = Mutex()
    val pageCount get() = renderer.pageCount

    suspend fun size(i: Int): Pair<Int, Int> = lock.withLock { renderer.openPage(i).use { it.width to it.height } }

    suspend fun render(i: Int, widthPx: Int): Bitmap = withContext(Dispatchers.Default) {
        lock.withLock {
            renderer.openPage(i).use { p ->
                val h = (widthPx.toFloat() * p.height / p.width).toInt().coerceAtLeast(1)
                val bmp = Bitmap.createBitmap(widthPx, h, Bitmap.Config.ARGB_8888)
                bmp.eraseColor(AColor.WHITE)
                p.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                bmp
            }
        }
    }

    fun close() { runCatching { renderer.close() }; runCatching { pfd.close() } }
}

/** Scrollable PDF pages, rendered with the system PdfRenderer. */
@Composable
fun PdfPreview(file: File?, version: Int, modifier: Modifier = Modifier) {
    if (file == null) {
        Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(t("nopdf"), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        return
    }
    val doc = remember(file, version) { PdfDoc(file) }
    DisposableEffect(doc) { onDispose { doc.close() } }
    BoxWithConstraints(modifier.fillMaxSize().background(MaterialTheme.colorScheme.surfaceVariant)) {
        val density = LocalDensity.current
        val widthPx = (with(density) { maxWidth.toPx() } * 1.6f).toInt().coerceIn(600, 1800)
        LazyColumn(Modifier.fillMaxSize().testTag("pdf_list"), contentPadding = PaddingValues(12.dp)) {
            items((0 until doc.pageCount).toList(), key = { "$version-$it" }) { i ->
                var ratio by remember { mutableStateOf(0.7f) }
                val bmp by produceState<ImageBitmap?>(null, doc, i, widthPx) {
                    val (w, h) = doc.size(i)
                    ratio = w.toFloat() / h
                    value = doc.render(i, widthPx).asImageBitmap()
                }
                Box(Modifier.fillMaxWidth().aspectRatio(ratio).background(Color.White).testTag("pdf_page_$i"), contentAlignment = Alignment.Center) {
                    val b = bmp
                    if (b == null) CircularProgressIndicator(Modifier.padding(24.dp), color = Color.Gray)
                    else Image(b, null, Modifier.fillMaxSize(), contentScale = ContentScale.FillWidth)
                }
                Spacer(Modifier.height(12.dp))
            }
        }
    }
}

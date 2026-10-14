package app.pdftoolkit.mobile

import android.graphics.Bitmap
import android.graphics.Color as AColor
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.FitScreen
import androidx.compose.material.icons.filled.ZoomIn
import androidx.compose.material.icons.filled.ZoomOut
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.File
import kotlin.math.ceil

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

private val INVERT = ColorFilter.colorMatrix(
    ColorMatrix(floatArrayOf(-1f, 0f, 0f, 0f, 255f, 0f, -1f, 0f, 0f, 255f, 0f, 0f, -1f, 0f, 255f, 0f, 0f, 0f, 1f, 0f)),
)

/**
 * PDF pages in a scrolling list: pinch or double-tap to zoom, drag sideways when zoomed, a page counter
 * that jumps to a page when tapped, and a night mode that inverts the colours.
 */
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
    val cs = MaterialTheme.colorScheme
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()
    val hScroll = rememberScrollState()
    var scale by remember { mutableFloatStateOf(1f) }
    var night by remember { mutableStateOf(false) }
    var jump by remember { mutableStateOf(false) }

    BoxWithConstraints(modifier.fillMaxSize().background(if (night) Color(0xFF15171C) else cs.surfaceVariant)) {
        val density = LocalDensity.current
        val viewWidth = maxWidth
        val basePx = with(density) { viewWidth.toPx() }
        val step = ceil(scale * 2f) / 2f                                   // re-draw the pages sharper in half steps only
        val widthPx = (basePx * step * 1.5f).toInt().coerceIn(600, 3200)
        val current by remember { derivedStateOf { listState.firstVisibleItemIndex + 1 } }

        Box(
            Modifier.fillMaxSize()
                .pointerInput(Unit) {
                    awaitEachGesture {
                        awaitFirstDown(requireUnconsumed = false, pass = PointerEventPass.Initial)
                        do {
                            val event = awaitPointerEvent(PointerEventPass.Initial)
                            if (event.changes.size >= 2) {
                                val zoom = event.calculateZoom()
                                if (zoom != 1f) {
                                    scale = (scale * zoom).coerceIn(1f, 4f)
                                    event.changes.forEach { it.consume() }
                                }
                            }
                        } while (event.changes.any { it.pressed })
                    }
                }
                .pointerInput(Unit) {
                    detectTapGestures(onDoubleTap = { scale = if (scale > 1.2f) 1f else 2f })
                },
        ) {
            Box(Modifier.fillMaxSize().horizontalScroll(hScroll)) {
                LazyColumn(
                    Modifier.width(viewWidth * scale).fillMaxSize().testTag("pdf_list"), state = listState,
                    contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(doc.pageCount, key = { it }) { i ->
                        var ratio by remember { mutableStateOf(0.7f) }
                        val bmp by produceState<ImageBitmap?>(null, doc, i, widthPx) {
                            val (w, h) = doc.size(i)
                            ratio = w.toFloat() / h
                            value = doc.render(i, widthPx).asImageBitmap()
                        }
                        Box(Modifier.fillMaxWidth().aspectRatio(ratio).background(Color.White).testTag("pdf_page_$i"), contentAlignment = Alignment.Center) {
                            val b = bmp
                            if (b == null) CircularProgressIndicator(Modifier.padding(24.dp), color = Color.Gray)
                            else Image(b, null, Modifier.fillMaxSize(), contentScale = ContentScale.FillWidth, colorFilter = if (night) INVERT else null)
                        }
                    }
                }
            }
        }

        // controls
        Row(Modifier.align(Alignment.TopEnd).padding(8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            for ((icon, tag, action) in listOf(
                Triple(Icons.Filled.ZoomOut, "zoom_out", { scale = (scale / 1.35f).coerceAtLeast(1f) }),
                Triple(Icons.Filled.ZoomIn, "zoom_in", { scale = (scale * 1.35f).coerceAtMost(4f) }),
                Triple(Icons.Filled.FitScreen, "zoom_fit", { scale = 1f }),
                Triple(Icons.Filled.DarkMode, "night_mode", { night = !night }),
            )) {
                Surface(shape = RoundedCornerShape(10.dp), color = cs.surface.copy(alpha = 0.92f), tonalElevation = 2.dp, shadowElevation = 2.dp) {
                    IconButton(onClick = action, modifier = Modifier.size(38.dp).testTag(tag)) { Icon(icon, null, tint = cs.onSurface, modifier = Modifier.size(20.dp)) }
                }
            }
        }
        Surface(
            onClick = { jump = true }, shape = RoundedCornerShape(16.dp), color = cs.surface.copy(alpha = 0.94f), shadowElevation = 3.dp,
            modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 14.dp).testTag("page_indicator"),
        ) {
            Text("$current / ${doc.pageCount}", Modifier.padding(horizontal = 14.dp, vertical = 7.dp), color = cs.onSurface, style = MaterialTheme.typography.labelLarge)
        }
    }

    if (jump) {
        var text by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { jump = false },
            title = { Text(t("go.page")) },
            text = {
                OutlinedTextField(
                    text, { text = it.filter(Char::isDigit).take(5) }, singleLine = true, label = { Text("1 – ${doc.pageCount}") },
                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number),
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    val n = (text.toIntOrNull() ?: 1).coerceIn(1, doc.pageCount)
                    scope.launch { listState.scrollToItem(n - 1) }
                    jump = false
                }) { Text(t("ok.button")) }
            },
            dismissButton = { TextButton(onClick = { jump = false }) { Text(t("cancel")) } },
        )
    }
}

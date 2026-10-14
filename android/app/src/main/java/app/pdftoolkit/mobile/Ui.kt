package app.pdftoolkit.mobile

import androidx.compose.foundation.gestures.detectDragGesturesAfterLongPress
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.zIndex
import kotlinx.coroutines.delay

/** Widest a page of controls grows: on a tablet the content stays centred and readable instead of stretching. */
const val CONTENT_MAX_DP = 680

/** A soft tinted background with a stronger icon colour, used to give every tool its own colour. */
data class Tone(val container: Color, val icon: Color)

private val TONE_HUES = floatArrayOf(8f, 215f, 140f, 38f, 275f, 185f)

@Composable
fun toneOf(i: Int): Tone {
    val dark = MaterialTheme.colorScheme.background.luminance() < 0.5f
    val h = TONE_HUES[i % TONE_HUES.size]
    return if (dark) Tone(Color.hsv(h, 0.55f, 0.30f), Color.hsv(h, 0.38f, 1f))
    else Tone(Color.hsv(h, 0.13f, 1f), Color.hsv(h, 0.78f, 0.70f))
}

/**
 * Press-and-hold then drag to reorder items of a lazy list or grid.
 * [rects] gives key, top-left and size of every visible, movable item in the container's own coordinates.
 */
class DragReorder(
    private val rects: () -> List<Triple<Any, Offset, Size>>,
    private val onMove: (from: Any, to: Any) -> Unit,
    val viewportHeight: () -> Float,
    val scrollBy: suspend (Float) -> Unit,
    private val buzz: () -> Unit,
) {
    var key by mutableStateOf<Any?>(null)
        private set
    var pos by mutableStateOf(Offset.Zero)
        private set

    private fun hit(p: Offset, skip: Any?): Triple<Any, Offset, Size>? =
        rects().firstOrNull { (k, o, s) -> k != skip && p.x >= o.x && p.x <= o.x + s.width && p.y >= o.y && p.y <= o.y + s.height }

    fun start(p: Offset) {
        val h = hit(p, null) ?: return
        key = h.first
        pos = p
        buzz()
    }

    fun drag(delta: Offset) {
        if (key == null) return
        pos += delta
        settle()
    }

    /** Swap with whatever item is under the finger. */
    fun settle() {
        val k = key ?: return
        val target = hit(pos, k) ?: return
        onMove(k, target.first)
    }

    fun end() { key = null }

    /** How far the dragged item has to be moved so that it stays under the finger. */
    fun shift(k: Any?): Offset {
        if (k == null || k != key) return Offset.Zero
        val r = rects().firstOrNull { it.first == k } ?: return Offset.Zero
        return pos - Offset(r.second.x + r.third.width / 2f, r.second.y + r.third.height / 2f)
    }
}

fun Modifier.reorderGestures(d: DragReorder): Modifier = pointerInput(d) {
    detectDragGesturesAfterLongPress(
        onDragStart = { d.start(it) },
        onDrag = { change, delta -> change.consume(); d.drag(delta) },
        onDragEnd = { d.end() },
        onDragCancel = { d.end() },
    )
}

/** Scrolls the list while an item is held near its top or bottom edge. */
@Composable
fun DragAutoScroll(d: DragReorder) {
    val active = d.key != null
    LaunchedEffect(active) {
        while (d.key != null) {
            val h = d.viewportHeight()
            val zone = 96f
            val y = d.pos.y
            val dy = when {
                y < zone -> -(zone - y) / zone * 26f
                y > h - zone -> (y - (h - zone)) / zone * 26f
                else -> 0f
            }
            if (dy != 0f) { d.scrollBy(dy); d.settle() }
            delay(16)
        }
    }
}

/** Lifts the dragged item and keeps it under the finger. */
fun Modifier.dragLook(d: DragReorder, id: Any): Modifier = this
    .zIndex(if (d.key == id) 1f else 0f)
    .graphicsLayer {
        val s = d.shift(id)
        translationX = s.x
        translationY = s.y
        val z = if (d.key == id) 1.05f else 1f
        scaleX = z
        scaleY = z
    }

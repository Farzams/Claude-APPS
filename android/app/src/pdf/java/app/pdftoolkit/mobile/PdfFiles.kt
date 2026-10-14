package app.pdftoolkit.mobile

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.activity.compose.ManagedActivityResultLauncher
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.State
import androidx.compose.runtime.produceState
import androidx.compose.ui.platform.LocalContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

/** A PDF the person opened in one of the tools, kept so it can be picked again from the home page. */
data class Recent(val uri: String, val name: String, val time: Long)

object Recents {
    private fun sp(ctx: Context) = ctx.getSharedPreferences("recent", Context.MODE_PRIVATE)

    fun list(ctx: Context): List<Recent> = runCatching {
        val a = JSONArray(sp(ctx).getString("list", "[]"))
        (0 until a.length()).map { val o = a.getJSONObject(it); Recent(o.getString("u"), o.getString("n"), o.getLong("t")) }
    }.getOrDefault(emptyList())

    private fun save(ctx: Context, items: List<Recent>) {
        val a = JSONArray()
        items.forEach { a.put(JSONObject().put("u", it.uri).put("n", it.name).put("t", it.time)) }
        sp(ctx).edit().putString("list", a.toString()).apply()
    }

    fun add(ctx: Context, uri: Uri, name: String) {
        if (!name.endsWith(".pdf", ignoreCase = true)) return
        runCatching { ctx.contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION) }
        val rest = list(ctx).filter { it.uri != uri.toString() }.take(19)
        save(ctx, listOf(Recent(uri.toString(), name, System.currentTimeMillis())) + rest)
    }

    fun remove(ctx: Context, uri: String) = save(ctx, list(ctx).filter { it.uri != uri })
    fun clear(ctx: Context) = save(ctx, emptyList())
}

/** A file chosen on the home page, handed to the tool screen that opens next. */
object PendingFile {
    var uri: Uri? = null
    fun take(): Uri? = uri.also { uri = null }
}

/** Opens the system file picker for one PDF and remembers the choice in the recent list. */
@Composable
fun rememberPdfPicker(onPicked: (Uri) -> Unit): ManagedActivityResultLauncher<Array<String>, Uri?> {
    val ctx = LocalContext.current
    return rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { u ->
        if (u != null) {
            Recents.add(ctx, u, PdfOps.nameOf(ctx, u))
            onPicked(u)
        }
    }
}

/** First page of a PDF as a small picture, or null while loading or when it cannot be read. */
@Composable
fun rememberPdfThumb(uri: Uri?, widthPx: Int): State<Bitmap?> {
    val ctx = LocalContext.current
    return produceState<Bitmap?>(null, uri, widthPx) {
        value = if (uri == null) null else withContext(Dispatchers.IO) {
            runCatching { PdfOps.Thumbs(ctx, uri).use { it.get(0, widthPx) } }.getOrNull()
        }
    }
}

/** A downsampled picture from a content URI. */
@Composable
fun rememberImageThumb(uri: Uri, px: Int): State<Bitmap?> {
    val ctx = LocalContext.current
    return produceState<Bitmap?>(null, uri, px) {
        value = withContext(Dispatchers.IO) {
            runCatching {
                val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                ctx.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
                var sample = 1
                while (bounds.outWidth / (sample * 2) >= px && bounds.outHeight / (sample * 2) >= px) sample *= 2
                val opts = BitmapFactory.Options().apply { inSampleSize = sample }
                ctx.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opts) }
            }.getOrNull()
        }
    }
}

fun openPdf(ctx: Context, uri: Uri) {
    runCatching {
        ctx.startActivity(
            Intent(Intent.ACTION_VIEW).setDataAndType(uri, "application/pdf")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK),
        )
    }
}

fun sharePdfFile(ctx: Context, uri: Uri) {
    runCatching {
        val send = Intent(Intent.ACTION_SEND).setType("application/pdf")
            .putExtra(Intent.EXTRA_STREAM, uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        ctx.startActivity(Intent.createChooser(send, null).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }
}

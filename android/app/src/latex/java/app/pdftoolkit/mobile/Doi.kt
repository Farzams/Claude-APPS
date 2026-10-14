package app.pdftoolkit.mobile

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL

/** Looks a reference up by its DOI. This is the only thing in the app that uses the internet, and only when asked. */
object Doi {
    /** "https://doi.org/10.1000/xyz", "doi:10.1000/xyz" or the bare DOI all give "10.1000/xyz"; null when it is not one. */
    fun clean(input: String): String? {
        val s = input.trim().removePrefix("https://doi.org/").removePrefix("http://doi.org/").removePrefix("https://dx.doi.org/")
            .removePrefix("doi:").removePrefix("DOI:").trim()
        return s.takeIf { Regex("""10\.\d{4,9}/\S+""").matches(it) }
    }

    /** The BibTeX entry for the DOI, or an error message. Runs on the calling thread: call it off the main thread. */
    fun fetch(doi: String): Result<String> = runCatching {
        val conn = (URL("https://doi.org/" + Uri.encode(doi, "/()-._:;")).openConnection() as HttpURLConnection).apply {
            setRequestProperty("Accept", "application/x-bibtex; charset=utf-8")
            instanceFollowRedirects = true
            connectTimeout = 12_000
            readTimeout = 15_000
        }
        try {
            val code = conn.responseCode
            if (code == 404) error("not found")
            if (code !in 200..299) error("HTTP $code")
            val text = conn.inputStream.use { String(it.readBytes(), Charsets.UTF_8) }.trim()
            if (!text.startsWith("@")) error("no BibTeX returned")
            tidy(text)
        } finally {
            conn.disconnect()
        }
    }

    /** One field per line and a plain key (author and year), so the entry is readable in the editor. */
    fun tidy(entry: String): String {
        val head = Regex("""^@(\w+)\{([^,]+),""").find(entry) ?: return entry
        val type = head.groupValues[1]
        val fields = Regex("""(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|"[^"]*"|\d+)""").findAll(entry.substring(head.range.last + 1)).toList()
        val get = { name: String -> fields.firstOrNull { it.groupValues[1].equals(name, true) }?.groupValues?.get(2)?.trim('{', '}', '"') ?: "" }
        val last = get("author").substringBefore(" and ").let { a -> if (',' in a) a.substringBefore(',') else a.substringAfterLast(' ') }
            .lowercase().filter { it.isLetter() }.ifEmpty { "ref" }
        val key = last + get("year").ifEmpty { "" }
        val body = fields.joinToString(",\n") { "  ${it.groupValues[1].lowercase().padEnd(9)} = ${it.groupValues[2]}" }
        return "@$type{$key,\n$body\n}\n"
    }
}

/** A picture ready to go into a project: LaTeX reads png, jpg and pdf, so other formats are converted and huge photos shrunk. */
object PictureImport {
    class Prepared(val name: String, val bytes: ByteArray)

    fun prepare(ctx: Context, uri: Uri): Prepared {
        val name = displayName(ctx, uri)
        val ext = name.substringAfterLast('.', "").lowercase()
        val raw = ctx.contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: error("Cannot read the picture")
        val base = name.substringBeforeLast('.').replace(Regex("[^A-Za-z0-9_-]"), "_").ifEmpty { "picture" }
        if (ext == "pdf") return Prepared("$base.pdf", raw)
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(raw, 0, raw.size, bounds)
        val big = maxOf(bounds.outWidth, bounds.outHeight) > 2600 || raw.size > 3_000_000
        if ((ext == "png" || ext == "jpg" || ext == "jpeg") && !big) return Prepared("$base.${if (ext == "jpeg") "jpg" else ext}", raw)
        var sample = 1
        while (maxOf(bounds.outWidth, bounds.outHeight) / sample > 2600) sample *= 2
        val bmp = BitmapFactory.decodeByteArray(raw, 0, raw.size, BitmapFactory.Options().apply { inSampleSize = sample }) ?: error("Not a picture")
        val out = ByteArrayOutputStream()
        val png = ext == "png"
        bmp.compress(if (png) Bitmap.CompressFormat.PNG else Bitmap.CompressFormat.JPEG, 90, out)
        bmp.recycle()
        return Prepared("$base.${if (png) "png" else "jpg"}", out.toByteArray())
    }
}

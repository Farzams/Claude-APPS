package app.pdftoolkit.mobile

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns

/** The file name the user sees for a picked document. */
fun displayName(ctx: Context, uri: Uri): String =
    fileOf(uri)?.name ?: ctx.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
        if (it.moveToFirst()) it.getString(0) else null
    } ?: (uri.lastPathSegment ?: "file")

package app.pdftoolkit.mobile

import android.content.Context
import android.content.SharedPreferences

/** Small settings store. */
class Prefs(ctx: Context) {
    private val sp: SharedPreferences = ctx.getSharedPreferences("settings", Context.MODE_PRIVATE)

    var theme: String
        get() = sp.getString("theme", "qp_light") ?: "qp_light"
        set(v) = sp.edit().putString("theme", v).apply()
    var accent: String
        get() = sp.getString("accent", "") ?: ""
        set(v) = sp.edit().putString("accent", v).apply()
    var lang: String
        get() = sp.getString("lang", "en") ?: "en"
        set(v) = sp.edit().putString("lang", v).apply()
    var editorSize: Int
        get() = sp.getInt("editor_size", 15)
        set(v) = sp.edit().putInt("editor_size", v).apply()
    var lineNumbers: Boolean
        get() = sp.getBoolean("line_numbers", true)
        set(v) = sp.edit().putBoolean("line_numbers", v).apply()
    var wrap: Boolean
        get() = sp.getBoolean("wrap", true)
        set(v) = sp.edit().putBoolean("wrap", v).apply()
    var autoPairs: Boolean
        get() = sp.getBoolean("auto_pairs", true)
        set(v) = sp.edit().putBoolean("auto_pairs", v).apply()
    var palette: Boolean
        get() = sp.getBoolean("palette", true)
        set(v) = sp.edit().putBoolean("palette", v).apply()
}

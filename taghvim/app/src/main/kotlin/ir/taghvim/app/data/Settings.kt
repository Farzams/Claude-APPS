package ir.taghvim.app.data

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import ir.taghvim.core.CalendarEngine
import ir.taghvim.core.Category
import ir.taghvim.core.City
import ir.taghvim.core.Cities
import ir.taghvim.core.EventData
import ir.taghvim.core.Level
import ir.taghvim.core.LevelDefaults
import ir.taghvim.core.Levels
import ir.taghvim.core.HolidayYearFile
import kotlinx.coroutines.flow.first
import java.io.File

private val Context.store by preferencesDataStore(name = "taghvim_settings")

/** Everything the user can change, with the defaults decided in the design. */
data class AppSettings(
    val province: String = Cities.tehran.province,
    val city: String = Cities.tehran.name,
    /** "none" (default), "hijri" or "greg": the small second line under each day number. */
    val secondary: String = "none",
    /** Moon-sighting correction for the lunar date, -1, 0 or +1 day. */
    val hijriShift: Int = 0,
    /** "dark", "light" or "system". */
    val theme: String = "dark",
    /** "gold", "coral", "teal" or "violet". */
    val accent: String = "gold",
    val order: List<Category> = Category.defaultOrder,
    /** How much of each group to show: off, important only, or all. */
    val levels: Levels = LevelDefaults.standard,
    val specialBackgrounds: Boolean = true,
    /** Months moved away from the current one with the widget's arrow buttons, valid for [offsetDate] only. */
    val monthOffset: Int = 0,
    val offsetDate: String = "",
) {
    val currentCity: City get() = Cities.find(province, city) ?: Cities.tehran
}

object Prefs {
    private val PROVINCE = stringPreferencesKey("province")
    private val CITY = stringPreferencesKey("city")
    private val SECONDARY = stringPreferencesKey("secondary")
    private val SHIFT = intPreferencesKey("hijri_shift")
    private val THEME = stringPreferencesKey("theme")
    private val ACCENT = stringPreferencesKey("accent")
    private val ORDER = stringPreferencesKey("order")
    private val LEVELS = stringPreferencesKey("levels")
    private val SPECIAL = booleanPreferencesKey("special_backgrounds")
    private val OFFSET = intPreferencesKey("month_offset")
    private val OFFSET_DATE = stringPreferencesKey("offset_date")

    suspend fun load(context: Context): AppSettings {
        val p = context.store.data.first()
        val d = AppSettings()
        val order = p[ORDER]?.split(',')?.map { Category.fromCode(it) }?.distinct()
            ?.let { saved -> saved + Category.entries.filter { it !in saved } } ?: d.order
        val levels = p[LEVELS]?.split(',')?.mapNotNull { pair ->
            pair.split('=').takeIf { it.size == 2 }?.let { Category.fromCode(it[0]) to Level.fromCode(it[1]) }
        }?.toMap()?.let { saved -> LevelDefaults.standard + saved } ?: d.levels
        return AppSettings(
            province = p[PROVINCE] ?: d.province,
            city = p[CITY] ?: d.city,
            secondary = p[SECONDARY] ?: d.secondary,
            hijriShift = p[SHIFT] ?: d.hijriShift,
            theme = p[THEME] ?: d.theme,
            accent = p[ACCENT] ?: d.accent,
            order = order,
            levels = levels,
            specialBackgrounds = p[SPECIAL] ?: d.specialBackgrounds,
            monthOffset = p[OFFSET] ?: 0,
            offsetDate = p[OFFSET_DATE] ?: "",
        )
    }

    suspend fun save(context: Context, s: AppSettings) {
        context.store.edit { p ->
            p[PROVINCE] = s.province
            p[CITY] = s.city
            p[SECONDARY] = s.secondary
            p[SHIFT] = s.hijriShift
            p[THEME] = s.theme
            p[ACCENT] = s.accent
            p[ORDER] = s.order.joinToString(",") { it.code }
            p[LEVELS] = s.levels.entries.joinToString(",") { "${it.key.code}=${it.value.code}" }
            p[SPECIAL] = s.specialBackgrounds
            p[OFFSET] = s.monthOffset
            p[OFFSET_DATE] = s.offsetDate
        }
    }

    suspend fun update(context: Context, change: (AppSettings) -> AppSettings): AppSettings {
        val next = change(load(context))
        save(context, next)
        return next
    }
}

/** Official yearly holiday lists downloaded after the app was built (they sit next to the ones bundled in the app). */
object Holidays {
    private fun dir(context: Context) = File(context.filesDir, "holidays").apply { mkdirs() }

    fun downloaded(context: Context): List<HolidayYearFile> =
        dir(context).listFiles { f -> f.extension == "json" }.orEmpty().mapNotNull { f ->
            runCatching { EventData.parseYear(f.readText()) }.getOrNull()
        }

    fun save(context: Context, year: Int, text: String) {
        EventData.parseYear(text) // refuse a file that does not parse
        File(dir(context), "$year.json").writeText(text)
    }

    fun engine(context: Context, s: AppSettings) = CalendarEngine(s.hijriShift, downloaded(context))
}

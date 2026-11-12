package ir.taghvim.core

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.time.LocalDate

/**
 * The four groups of occasions the user can order in settings.
 * [OFFICIAL] holidays (solar and lunar), [RELIGIOUS] days that are not holidays, [NATIONAL] days and special days, [GLOBAL] world and Gregorian days.
 */
enum class Category(val code: String) {
    OFFICIAL("off"), RELIGIOUS("rel"), NATIONAL("nat"), GLOBAL("gre");

    companion object {
        val defaultOrder = listOf(OFFICIAL, RELIGIOUS, NATIONAL, GLOBAL)
        fun fromCode(code: String) = entries.firstOrNull { it.code == code } ?: NATIONAL
    }
}

/** How much of a group the user wants to see. */
enum class Level(val code: String) {
    OFF("off"), IMPORTANT("imp"), ALL("all");

    companion object {
        fun fromCode(code: String) = entries.firstOrNull { it.code == code } ?: ALL
    }
}

typealias Levels = Map<Category, Level>

object LevelDefaults {
    /** Official holidays in full, the important religious and national days, nothing from the world/Gregorian group. */
    val standard: Levels = mapOf(
        Category.OFFICIAL to Level.ALL,
        Category.RELIGIOUS to Level.IMPORTANT,
        Category.NATIONAL to Level.IMPORTANT,
        Category.GLOBAL to Level.OFF,
    )
    val everything: Levels = Category.entries.associateWith { Level.ALL }
}

@Serializable
data class EventDef(
    val m: Int,
    val d: Int,
    val title: String,
    val cat: String = "nat",
    val icon: String? = null,
    val theme: String? = null,
    /** Marked important: shown when its group is set to "important only". */
    val imp: Boolean = false,
)

@Serializable
data class EventsFile(val solar: List<EventDef>, val lunar: List<EventDef>, val greg: List<EventDef>)

/** One entry of an official yearly holiday list (the part that depends on moon sighting). */
@Serializable
data class HolidayEntry(
    val date: String,
    val title: String,
    val cat: String = "off",
    val theme: String? = null,
    val icon: String? = null,
    /** Lunar month (1 = Muharram) and day of the occasion, when known: lets the app line up its lunar calendar with Iran's. */
    val hm: Int? = null,
    val hd: Int? = null,
)

@Serializable
data class HolidayYearFile(val year: Int, val source: String = "", val holidays: List<HolidayEntry>)

data class DayEvent(
    val title: String,
    val category: Category,
    val icon: String?,
    /** Name of the background theme for this day (nowruz, nat, mourn, joy, xmas, nye, val, hal, yalda) or null for a soft tint. */
    val theme: String?,
    val lunar: Boolean = false,
    val important: Boolean = false,
) {
    /** Official holidays are always important. */
    fun shownAt(level: Level): Boolean = when (level) {
        Level.OFF -> false
        Level.ALL -> true
        Level.IMPORTANT -> important || category == Category.OFFICIAL
    }
}

data class DayInfo(
    val date: LocalDate,
    val jalali: JalaliDate,
    val hijri: HijriDate,
    val weekdayIndex: Int,
    val events: List<DayEvent>,
) {
    val isFriday get() = weekdayIndex == 6
    val isHoliday get() = isFriday || events.any { it.category == Category.OFFICIAL }

    /** The event that decides how the day looks: the first group in the user's order that has an event it shows. */
    fun primary(order: List<Category>, levels: Levels = LevelDefaults.everything): DayEvent? {
        for (c in order) {
            val level = levels[c] ?: Level.ALL
            events.firstOrNull { it.category == c && it.shownAt(level) }?.let { return it }
        }
        return null
    }

    fun eventsOrdered(order: List<Category>, levels: Levels = LevelDefaults.everything): List<DayEvent> =
        order.flatMap { c -> events.filter { it.category == c && it.shownAt(levels[c] ?: Level.ALL) } }
}

data class MonthView(val year: Int, val month: Int, val startColumn: Int, val days: List<DayInfo>)

/**
 * Resolves every day to its events. Fixed dates come from events.json; lunar dates are computed and
 * can be corrected by [hijriShift]; a yearly official list (bundled, or downloaded) replaces the computed
 * lunar holidays of that year with the exact official days.
 */
class CalendarEngine(
    private val hijriShift: Int = 0,
    extraYears: Collection<HolidayYearFile> = emptyList(),
) {
    private val events: EventsFile = EventData.events
    private val yearFiles: Map<Int, HolidayYearFile> =
        (EventData.bundledYears + extraYears).associateBy { it.year }
    private val calendar = HijriCalendar.from(yearFiles.values)
    private val officialByDate: Map<String, List<HolidayEntry>> =
        yearFiles.values.flatMap { it.holidays }.groupBy { it.date }

    fun day(date: LocalDate): DayInfo {
        val j = JalaliDate.of(date)
        val h = calendar.of(date, hijriShift)
        val list = ArrayList<DayEvent>()

        events.solar.filter { it.m == j.month && it.d == j.day }.forEach { list += it.toEvent(false) }

        val officialYear = yearFiles.containsKey(j.year)
        events.lunar.filter { matchesLunar(it, h) }.forEach { def ->
            // when the official list exists for the year it already says which days are holidays
            if (!(officialYear && def.cat == "off")) list += def.toEvent(true)
        }
        officialByDate[j.toString()]?.forEach { e ->
            list += DayEvent(e.title, Category.OFFICIAL, e.icon, e.theme ?: "joy", lunar = true, important = true)
        }

        events.greg.filter { it.m == date.monthValue && it.d == date.dayOfMonth }.forEach { list += it.toEvent(false, Category.GLOBAL) }
        return DayInfo(date, j, h, Jalali.weekdayIndex(date), list)
    }

    fun month(year: Int, month: Int): MonthView {
        val first = JalaliDate(year, month, 1).toGregorian()
        val days = (0 until Jalali.monthLength(year, month)).map { day(first.plusDays(it.toLong())) }
        return MonthView(year, month, Jalali.weekdayIndex(first), days)
    }

    /** Next official holiday after [from] (not counting Fridays), within a year. */
    fun nextOfficialHoliday(from: LocalDate): DayInfo? =
        (1..366).asSequence().map { day(from.plusDays(it.toLong())) }
            .firstOrNull { d -> d.events.any { it.category == Category.OFFICIAL } }

    private fun matchesLunar(def: EventDef, h: HijriDate): Boolean {
        if (def.m != h.month) return false
        // a 29-day month has no 30th: the occasion moves to the 29th
        return def.d == h.day || (def.d == 30 && h.day == 29 && h.monthLength == 29)
    }

    private fun EventDef.toEvent(lunar: Boolean, forced: Category? = null) =
        DayEvent(title, forced ?: Category.fromCode(cat), icon, theme, lunar, imp)
}

object EventData {
    private val json = Json { ignoreUnknownKeys = true }

    val events: EventsFile by lazy { json.decodeFromString(readResource("/data/events.json")) }

    val bundledYears: List<HolidayYearFile> by lazy {
        listOf(1404, 1405).mapNotNull { y ->
            runCatching { parseYear(readResource("/data/holidays-$y.json")) }.getOrNull()
        }
    }

    fun parseYear(text: String): HolidayYearFile = json.decodeFromString(text)

    private fun readResource(path: String): String =
        EventData::class.java.getResourceAsStream(path)?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }
            ?: error("$path is missing")
}

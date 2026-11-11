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

@Serializable
data class EventDef(
    val m: Int,
    val d: Int,
    val title: String,
    val cat: String = "nat",
    val icon: String? = null,
    val theme: String? = null,
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
)

data class DayInfo(
    val date: LocalDate,
    val jalali: JalaliDate,
    val hijri: HijriDate,
    val weekdayIndex: Int,
    val events: List<DayEvent>,
) {
    val isFriday get() = weekdayIndex == 6
    val isHoliday get() = isFriday || events.any { it.category == Category.OFFICIAL }

    /** The event that decides how the day looks: the first present category in the user's order. */
    fun primary(order: List<Category>, enabled: Set<Category> = Category.entries.toSet()): DayEvent? {
        for (c in order) {
            if (c !in enabled) continue
            events.firstOrNull { it.category == c }?.let { return it }
        }
        return null
    }

    fun eventsOrdered(order: List<Category>, enabled: Set<Category> = Category.entries.toSet()): List<DayEvent> =
        order.filter { it in enabled }.flatMap { c -> events.filter { it.category == c } }
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
    private val officialByDate: Map<String, List<HolidayEntry>> =
        yearFiles.values.flatMap { it.holidays }.groupBy { it.date }

    fun day(date: LocalDate): DayInfo {
        val j = JalaliDate.of(date)
        val h = Hijri.of(date, hijriShift)
        val list = ArrayList<DayEvent>()

        events.solar.filter { it.m == j.month && it.d == j.day }.forEach { list += it.toEvent(false) }

        val officialYear = yearFiles.containsKey(j.year)
        events.lunar.filter { matchesLunar(it, h) }.forEach { def ->
            // when the official list exists for the year it already says which days are holidays
            if (!(officialYear && def.cat == "off")) list += def.toEvent(true)
        }
        officialByDate[j.toString()]?.forEach { e ->
            list += DayEvent(e.title, Category.OFFICIAL, e.icon, e.theme ?: "joy", lunar = true)
        }

        events.greg.filter { it.m == date.monthValue && it.d == date.dayOfMonth }.forEach { list += it.toEvent(false) }
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

    private fun EventDef.toEvent(lunar: Boolean) = DayEvent(title, Category.fromCode(cat), icon, theme, lunar)
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

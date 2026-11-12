package ir.taghvim.core

import java.time.LocalDate
import java.time.chrono.HijrahChronology
import java.time.temporal.ChronoField

data class HijriDate(val year: Int, val month: Int, val day: Int, val monthLength: Int)

/**
 * Lunar Hijri date from the Umm al-Qura table that ships with Java.
 * Iran follows its own moon sighting, which can differ by a day, so [shift] moves the date:
 * +1 means the moon was seen one day later (the lunar date lags), -1 one day earlier.
 */
object Hijri {
    val monthNames = listOf(
        "محرم", "صفر", "ربیع‌الاول", "ربیع‌الثانی", "جمادی‌الاول", "جمادی‌الثانی",
        "رجب", "شعبان", "رمضان", "شوال", "ذی‌القعده", "ذی‌الحجه",
    )

    fun of(date: LocalDate, shift: Int = 0): HijriDate {
        val h = HijrahChronology.INSTANCE.date(date.minusDays(shift.toLong()))
        return HijriDate(
            h.get(ChronoField.YEAR),
            h.get(ChronoField.MONTH_OF_YEAR),
            h.get(ChronoField.DAY_OF_MONTH),
            h.lengthOfMonth(),
        )
    }
}

/**
 * The lunar date as Iran counts it. The Umm al-Qura table can be one or two days away from Iran's moon
 * sighting, so every official lunar holiday of the yearly lists (for example "3 Jumada II") is an anchor:
 * it says how far the table is off at that moment, and that offset is used until the next anchor.
 */
class HijriCalendar(anchors: List<Pair<LocalDate, Int>>) {
    private val sorted = anchors.sortedBy { it.first }

    /** Days to move the table by on [date] (positive: Iran is later than the table). */
    fun offsetAt(date: LocalDate): Int {
        if (sorted.isEmpty()) return 0
        val before = sorted.lastOrNull { !it.first.isAfter(date) } ?: sorted.first()
        return before.second
    }

    fun of(date: LocalDate, userShift: Int = 0): HijriDate = Hijri.of(date, userShift + offsetAt(date))

    companion object {
        val tableOnly = HijriCalendar(emptyList())

        fun from(files: Collection<HolidayYearFile>): HijriCalendar {
            val anchors = ArrayList<Pair<LocalDate, Int>>()
            for (e in files.flatMap { it.holidays }) {
                val hm = e.hm ?: continue
                val hd = e.hd ?: continue
                val (jy, jm, jd) = e.date.split('-').map { it.toInt() }
                val iran = JalaliDate(jy, jm, jd).toGregorian()
                val tableYear = HijrahChronology.INSTANCE.date(iran).get(ChronoField.YEAR)
                val onTable = (tableYear - 1..tableYear + 1).mapNotNull { y ->
                    runCatching { LocalDate.from(HijrahChronology.INSTANCE.date(y, hm, hd)) }.getOrNull()
                }.minByOrNull { kotlin.math.abs(it.toEpochDay() - iran.toEpochDay()) } ?: continue
                val offset = (iran.toEpochDay() - onTable.toEpochDay()).toInt()
                if (offset in -3..3) anchors += iran to offset
            }
            return HijriCalendar(anchors)
        }
    }
}

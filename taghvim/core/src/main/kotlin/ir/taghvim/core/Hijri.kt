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
        "محرم", "صفر", "ربیع‌الاول", "ربیع‌الثانی", "جمادی‌الاولی", "جمادی‌الثانیه",
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

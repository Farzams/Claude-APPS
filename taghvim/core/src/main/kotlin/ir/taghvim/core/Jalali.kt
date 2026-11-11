package ir.taghvim.core

import java.time.LocalDate

/** A date in the Solar Hijri (Jalali) calendar. */
data class JalaliDate(val year: Int, val month: Int, val day: Int) : Comparable<JalaliDate> {
    override fun compareTo(other: JalaliDate): Int =
        compareValuesBy(this, other, { it.year }, { it.month }, { it.day })

    fun toGregorian(): LocalDate = Jalali.toGregorian(this)
    override fun toString(): String = "%04d-%02d-%02d".format(year, month, day)

    companion object {
        fun of(date: LocalDate): JalaliDate = Jalali.fromGregorian(date)
    }
}

/**
 * Solar Hijri conversion (33-year arithmetic rule, the same one used by the jalaali-js library).
 * It matches the official Iranian calendar for the years the app covers (1300 to 1500).
 */
object Jalali {
    val monthNames = listOf(
        "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
    )

    /** Saturday first, as in the Iranian week. Index = (dayOfWeek % 7 + 1) % 7 maps Saturday to 0. */
    val weekdayNames = listOf("شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه")
    val weekdayInitials = listOf("ش", "ی", "د", "س", "چ", "پ", "ج")

    private val breaks = intArrayOf(
        -61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178,
    )

    private class Cal(val leap: Int, val gy: Int, val march: Int)

    private fun jalCal(jy: Int): Cal {
        val bl = breaks.size
        val gy = jy + 621
        var leapJ = -14
        var jp = breaks[0]
        require(jy >= jp && jy < breaks[bl - 1]) { "Invalid Jalali year $jy" }
        var jump = 0
        for (i in 1 until bl) {
            val jm = breaks[i]
            jump = jm - jp
            if (jy < jm) break
            leapJ += (jump / 33) * 8 + (jump % 33) / 4
            jp = jm
        }
        var n = jy - jp
        leapJ += (n / 33) * 8 + ((n % 33) + 3) / 4
        if (jump % 33 == 4 && jump - n == 4) leapJ += 1
        val leapG = gy / 4 - ((gy / 100 + 1) * 3) / 4 - 150
        val march = 20 + leapJ - leapG
        if (jump - n < 6) n = n - jump + ((jump + 4) / 33) * 33
        var leap = ((n + 1) % 33 - 1) % 4
        if (leap == -1) leap = 4
        return Cal(leap, gy, march)
    }

    fun isLeap(year: Int): Boolean = jalCal(year).leap == 0

    fun monthLength(year: Int, month: Int): Int = when {
        month <= 6 -> 31
        month <= 11 -> 30
        else -> if (isLeap(year)) 30 else 29
    }

    private const val EPOCH_OFFSET = 2440588L // Julian day number of 1970-01-01

    private fun jdn(date: LocalDate): Long = date.toEpochDay() + EPOCH_OFFSET

    fun toGregorian(d: JalaliDate): LocalDate {
        val c = jalCal(d.year)
        val firstOfFarvardin = LocalDate.of(c.gy, 3, c.march)
        val dayOfYear = (d.month - 1) * 31 - (d.month / 7) * (d.month - 7) + d.day - 1
        return firstOfFarvardin.plusDays(dayOfYear.toLong())
    }

    fun fromGregorian(date: LocalDate): JalaliDate {
        val gy = date.year
        var jy = gy - 621
        val r = jalCal(jy)
        val jdn1f = jdn(LocalDate.of(gy, 3, r.march))
        var k = (jdn(date) - jdn1f).toInt()
        if (k >= 0) {
            if (k <= 185) return JalaliDate(jy, 1 + k / 31, k % 31 + 1)
            k -= 186
        } else {
            jy -= 1
            k += 179
            if (r.leap == 1) k += 1
        }
        return JalaliDate(jy, 7 + k / 30, k % 30 + 1)
    }

    /** 0 = Saturday ... 6 = Friday. */
    fun weekdayIndex(date: LocalDate): Int = (date.dayOfWeek.value % 7 + 1) % 7
}

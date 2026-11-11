package ir.taghvim.app.data

import ir.taghvim.core.Hijri
import ir.taghvim.core.Jalali

private val digits = "۰۱۲۳۴۵۶۷۸۹"

/** Persian digits for numbers and times. */
fun String.fa(): String = map { if (it in '0'..'9') digits[it - '0'] else it }.joinToString("")
fun Int.fa(): String = toString().fa()

fun monthTitle(year: Int, month: Int) = "${Jalali.monthNames[month - 1]} ${year.fa()}"

val gregorianMonthNames = listOf(
    "ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن", "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر",
)

fun hijriMonthName(month: Int) = Hijri.monthNames[month - 1]

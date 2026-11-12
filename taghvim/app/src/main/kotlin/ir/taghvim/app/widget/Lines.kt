package ir.taghvim.app.widget

import ir.taghvim.app.data.AppSettings
import ir.taghvim.app.data.fa
import ir.taghvim.app.data.gregorianMonthNames
import ir.taghvim.app.data.hijriMonthName
import ir.taghvim.core.Category
import ir.taghvim.core.DayInfo
import ir.taghvim.core.Jalali
import ir.taghvim.core.Level
import ir.taghvim.core.MonthView
import java.time.LocalDate

/** Today's date in the three calendars, as the widget and the settings preview write it. */
object DateLines {
    fun triple(now: DayInfo, today: LocalDate): List<String> = listOf(
        "${now.jalali.day.fa()} ${Jalali.monthNames[now.jalali.month - 1]} ${now.jalali.year.fa()}",
        "${now.hijri.day.fa()} ${hijriMonthName(now.hijri.month)} ${now.hijri.year.fa()}",
        "${today.dayOfMonth.fa()} ${gregorianMonthNames[today.monthValue - 1]} ${today.year.fa()}",
    )
}

/**
 * The occasions of a month as short lines, in the user's group order and levels. Days in a row with the
 * same occasion (Nowruz) become one line ("۱ تا ۴ فروردین · نوروز").
 */
object OccasionLines {
    fun build(s: AppSettings, view: MonthView): List<Pair<Category, String>> {
        val lines = ArrayList<Pair<Category, String>>()
        val monthName = Jalali.monthNames[view.month - 1]
        for (cat in s.order) {
            val level = s.levels[cat] ?: Level.ALL
            if (level == Level.OFF) continue
            var i = 0
            while (i < view.days.size) {
                val e = view.days[i].events.firstOrNull { it.category == cat && it.shownAt(level) }
                if (e != null) {
                    var j = i
                    while (j + 1 < view.days.size && view.days[j + 1].events.any { it.category == cat && it.title == e.title && it.shownAt(level) }) j++
                    val first = view.days[i].jalali.day.fa()
                    val range = if (j == i) first else "$first تا ${view.days[j].jalali.day.fa()}"
                    lines += cat to "$range $monthName · ${e.title}"
                    i = j + 1
                } else i++
            }
        }
        return lines
    }
}

/** The occasions of one tapped day, in the user's group order and levels. A Friday is mentioned too. */
object DayOccasions {
    fun forDay(s: AppSettings, day: DayInfo): List<Pair<Category, String>> {
        val monthName = Jalali.monthNames[day.jalali.month - 1]
        val prefix = "${day.jalali.day.fa()} $monthName · "
        val list = ArrayList<Pair<Category, String>>()
        if (day.isFriday) list += Category.OFFICIAL to (prefix + "جمعه")
        for (cat in s.order) {
            val level = s.levels[cat] ?: Level.ALL
            day.events.filter { it.category == cat && it.shownAt(level) }.forEach { list += cat to (prefix + it.title) }
        }
        return list
    }
}

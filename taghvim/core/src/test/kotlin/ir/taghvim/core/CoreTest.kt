package ir.taghvim.core

import java.time.LocalDate
import kotlin.math.abs
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

class CoreTest {
    @Test
    fun jalaliKnownDates() {
        assertEquals(JalaliDate(1405, 1, 1), JalaliDate.of(LocalDate.of(2026, 3, 21)))
        assertEquals(JalaliDate(1405, 8, 20), JalaliDate.of(LocalDate.of(2026, 11, 11)))
        assertEquals(JalaliDate(1403, 1, 1), JalaliDate.of(LocalDate.of(2024, 3, 20)))
        assertEquals(LocalDate.of(2026, 3, 21), JalaliDate(1405, 1, 1).toGregorian())
        assertEquals(LocalDate.of(2026, 6, 22), JalaliDate(1405, 4, 1).toGregorian())
    }

    @Test
    fun jalaliRoundTripAndLeapYears() {
        var d = LocalDate.of(2015, 1, 1)
        while (d.isBefore(LocalDate.of(2040, 1, 1))) {
            assertEquals(d, JalaliDate.of(d).toGregorian(), "round trip $d")
            d = d.plusDays(7)
        }
        assertTrue(Jalali.isLeap(1403))
        assertTrue(!Jalali.isLeap(1404))
        assertEquals(30, Jalali.monthLength(1403, 12))
        assertEquals(29, Jalali.monthLength(1405, 12))
    }

    @Test
    fun weekdaysStartOnSaturday() {
        assertEquals(0, Jalali.weekdayIndex(LocalDate.of(2026, 3, 21))) // Saturday
        assertEquals(6, Jalali.weekdayIndex(LocalDate.of(2026, 11, 13))) // Friday
        assertEquals(4, Jalali.weekdayIndex(LocalDate.of(2026, 11, 11))) // Wednesday
    }

    @Test
    fun hijriShiftMovesTheDate() {
        val d = LocalDate.of(2026, 11, 11)
        val base = Hijri.of(d)
        val later = Hijri.of(d, 1)
        assertTrue(later.day == base.day - 1 || later.day == later.monthLength || base.day == 1)
    }

    @Test
    fun officialLunarHolidays1405() {
        val engine = CalendarEngine()
        val tasua = engine.day(JalaliDate(1405, 4, 4).toGregorian())
        val ashura = engine.day(JalaliDate(1405, 4, 5).toGregorian())
        assertTrue(tasua.events.any { it.category == Category.OFFICIAL && it.title.contains("تاسوعا") })
        assertTrue(ashura.events.any { it.category == Category.OFFICIAL && it.title.contains("عاشورا") })
        assertTrue(tasua.isHoliday)
        assertEquals("mourn", tasua.primary(Category.defaultOrder)?.theme)
    }

    @Test
    fun solarHolidaysAndFridays() {
        val engine = CalendarEngine()
        val nowruz = engine.day(LocalDate.of(2026, 3, 21))
        assertTrue(nowruz.isHoliday)
        assertTrue(nowruz.events.any { it.title == "نوروز" && it.theme == "nowruz" })
        val friday = engine.day(LocalDate.of(2026, 11, 13))
        assertTrue(friday.isFriday && friday.isHoliday)
        val normal = engine.day(LocalDate.of(2026, 11, 11))
        assertTrue(!normal.isHoliday)
        val bahman22 = engine.day(JalaliDate(1405, 11, 22).toGregorian())
        assertTrue(bahman22.events.any { it.category == Category.OFFICIAL })
        assertEquals(Category.OFFICIAL, bahman22.primary(Category.defaultOrder)?.category)
        // moving "global" first changes the primary event of 22 Bahman (11 February: World Women and Girls in Science Day is not in the list, so check Valentine day)
        val valentine = engine.day(LocalDate.of(2027, 2, 14))
        assertEquals("val", valentine.primary(Category.defaultOrder)?.theme)
    }

    @Test
    fun orderDecidesThePrimaryEvent() {
        val engine = CalendarEngine()
        // 31 Oct 2026 is Halloween (global) and Friday-less; 13 Aban is Student Day (national)
        val day = engine.day(LocalDate.of(2026, 11, 4)) // 13 Aban 1405
        assertEquals(Category.NATIONAL, day.primary(Category.defaultOrder)?.category)
        val onlyGlobal = day.primary(Category.defaultOrder, mapOf(Category.GLOBAL to Level.ALL, Category.NATIONAL to Level.OFF))
        assertTrue(onlyGlobal == null || onlyGlobal.category == Category.GLOBAL)
    }

    @Test
    fun importantLevelKeepsOnlyTheImportantDays() {
        val engine = CalendarEngine()
        // 13 Aban (Student Day) is important; 14 Aban (Mazandaran day) is not
        val student = engine.day(JalaliDate(1405, 8, 13).toGregorian())
        val mazandaran = engine.day(JalaliDate(1405, 8, 14).toGregorian())
        val standard = LevelDefaults.standard
        assertEquals("روز دانش‌آموز", student.primary(Category.defaultOrder, standard)?.title)
        assertEquals(null, mazandaran.primary(Category.defaultOrder, standard))
        assertEquals("روز ملی مازندران", mazandaran.primary(Category.defaultOrder, LevelDefaults.everything)?.title)
        // the world group is off by default: Halloween (9 Aban) shows nothing, but shows when switched on
        val halloween = engine.day(JalaliDate(1405, 8, 9).toGregorian())
        assertEquals(null, halloween.primary(Category.defaultOrder, standard))
        assertEquals("هالووین", halloween.primary(Category.defaultOrder, standard + (Category.GLOBAL to Level.ALL))?.title)
        // official holidays stay even in "important only" mode
        val fatima = engine.day(JalaliDate(1405, 8, 23).toGregorian())
        assertEquals(Category.OFFICIAL, fatima.primary(Category.defaultOrder, standard)?.category)
        // Yalda (30 Azar) is an important national night
        val yalda = engine.day(JalaliDate(1405, 9, 30).toGregorian())
        assertEquals("yalda", yalda.primary(Category.defaultOrder, standard)?.theme)
    }

    @Test
    fun monthView() {
        val m = CalendarEngine().month(1405, 8)
        assertEquals(30, m.days.size)
        assertEquals(6, m.startColumn) // 1 Aban 1405 is a Friday
        assertEquals(20, m.days.first { it.date == LocalDate.of(2026, 11, 11) }.jalali.day)
    }

    @Test
    fun prayerTimesMatchTheReferenceWidget() {
        // The screenshots the design is based on: Noshahr, 20 Aban 1405 (11 Nov 2026), Iran time (UTC+3:30)
        val noshahr = Cities.find("مازندران", "نوشهر")
        assertNotNull(noshahr)
        val t = PrayerCalc.compute(LocalDate.of(2026, 11, 11), noshahr, java.time.ZoneId.of("Asia/Tehran"))
        println("noshahr: " + t.asList().joinToString(" ") { PrayerCalc.format(it) })
        fun mins(s: String) = s.split(":").let { it[0].toInt() * 60 + it[1].toInt() }
        val expected = listOf("05:10", "06:37", "11:48", "16:58", "17:18", "23:04").map(::mins)
        t.asList().zip(expected).forEachIndexed { i, (got, want) ->
            assertTrue(abs(got - want) <= 3.0, "time #$i got ${PrayerCalc.format(got)} want ${want / 60}:${want % 60}")
        }
    }

    @Test
    fun citiesAndNearest() {
        assertEquals(31, Cities.provinces.size)
        assertEquals("تهران", Cities.nearest(35.69, 51.39).name)
        assertEquals("نوشهر", Cities.nearest(36.66, 51.49).name)
        assertTrue(Cities.all.all { it.lat in 25.0..40.0 && it.lon in 44.0..64.0 })
    }
}

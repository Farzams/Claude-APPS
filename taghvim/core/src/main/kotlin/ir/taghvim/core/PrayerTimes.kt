package ir.taghvim.core

import java.time.LocalDate
import java.time.ZoneId
import java.time.ZonedDateTime
import kotlin.math.PI
import kotlin.math.acos
import kotlin.math.asin
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.sin

/** The six moments the widget shows, as minutes after local midnight (midnight can pass 1440). */
data class PrayerTimes(
    val fajr: Double,
    val sunrise: Double,
    val dhuhr: Double,
    val sunset: Double,
    val maghrib: Double,
    val midnight: Double,
) {
    fun asList() = listOf(fajr, sunrise, dhuhr, sunset, maghrib, midnight)
}

/**
 * Prayer times by the method of the Institute of Geophysics, University of Tehran:
 * fajr at 17.7 degrees, maghrib at 4.5 degrees below the horizon, midnight halfway between sunset and the next fajr.
 */
object PrayerCalc {
    private const val FAJR_ANGLE = 17.7
    private const val MAGHRIB_ANGLE = 4.5
    private const val HORIZON_ANGLE = 0.833

    private fun rad(d: Double) = d * PI / 180.0
    private fun deg(r: Double) = r * 180.0 / PI
    private fun fix(a: Double, b: Double) = a - b * floor(a / b)

    private fun julian(date: LocalDate): Double {
        var y = date.year
        var m = date.monthValue
        if (m <= 2) { y -= 1; m += 12 }
        val a = floor(y / 100.0)
        val b = 2 - a + floor(a / 4.0)
        return floor(365.25 * (y + 4716)) + floor(30.6001 * (m + 1)) + date.dayOfMonth + b - 1524.5
    }

    /** Declination (degrees) and equation of time (hours). */
    private fun sun(jd: Double): Pair<Double, Double> {
        val d = jd - 2451545.0
        val g = fix(357.529 + 0.98560028 * d, 360.0)
        val q = fix(280.459 + 0.98564736 * d, 360.0)
        val l = fix(q + 1.915 * sin(rad(g)) + 0.020 * sin(rad(2 * g)), 360.0)
        val e = 23.439 - 0.00000036 * d
        val ra = deg(atan2(cos(rad(e)) * sin(rad(l)), cos(rad(l)))) / 15.0
        val eqt = q / 15.0 - fix(ra, 24.0)
        val decl = deg(asin(sin(rad(e)) * sin(rad(l))))
        return decl to eqt
    }

    /**
     * @param tzHours offset of the place from UTC in hours on that date (3.5 for Iran).
     * @return minutes after local midnight.
     */
    fun compute(date: LocalDate, lat: Double, lon: Double, tzHours: Double): PrayerTimes {
        val jd = julian(date) - lon / (15.0 * 24.0)
        fun mid(t: Double) = fix(12.0 - sun(jd + t).second, 24.0)
        fun angleTime(angle: Double, t: Double, before: Boolean): Double {
            val decl = sun(jd + t).first
            val x = (-sin(rad(angle)) - sin(rad(decl)) * sin(rad(lat))) / (cos(rad(decl)) * cos(rad(lat)))
            val v = deg(acos(x.coerceIn(-1.0, 1.0))) / 15.0
            return mid(t) + if (before) -v else v
        }

        var fajr = 5.0; var sunrise = 6.0; var dhuhr = 12.0; var sunset = 18.0; var maghrib = 18.0
        repeat(3) {
            fajr = angleTime(FAJR_ANGLE, fajr / 24.0, true)
            sunrise = angleTime(HORIZON_ANGLE, sunrise / 24.0, true)
            dhuhr = mid(dhuhr / 24.0)
            sunset = angleTime(HORIZON_ANGLE, sunset / 24.0, false)
            maghrib = angleTime(MAGHRIB_ANGLE, maghrib / 24.0, false)
        }
        val shift = tzHours - lon / 15.0
        fajr += shift; sunrise += shift; dhuhr += shift; sunset += shift; maghrib += shift
        val midnight = sunset + fix(fajr - sunset, 24.0) / 2.0
        fun m(h: Double) = h * 60.0
        return PrayerTimes(m(fajr), m(sunrise), m(dhuhr), m(sunset), m(maghrib), m(midnight))
    }

    fun compute(date: LocalDate, city: City, zone: ZoneId = ZoneId.of("Asia/Tehran")): PrayerTimes {
        val offsetHours = ZonedDateTime.of(date, java.time.LocalTime.NOON, zone).offset.totalSeconds / 3600.0
        return compute(date, city.lat, city.lon, offsetHours)
    }

    fun format(minutes: Double): String {
        val total = Math.round(minutes).toInt()
        val h = (total / 60) % 24
        return "%02d:%02d".format(h, total % 60)
    }
}

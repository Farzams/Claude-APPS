package ir.taghvim.core

import kotlin.math.PI
import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sqrt

data class City(val province: String, val name: String, val lat: Double, val lon: Double)

/** Provinces and their main cities, loaded from data/cities.csv (province,city,lat,lon). */
object Cities {
    val all: List<City> by lazy {
        val stream = Cities::class.java.getResourceAsStream("/data/cities.csv")
            ?: error("data/cities.csv is missing")
        stream.bufferedReader(Charsets.UTF_8).useLines { lines ->
            lines.map { it.trim() }.filter { it.isNotEmpty() && !it.startsWith("#") }.map { line ->
                val p = line.split(',')
                City(p[0].trim(), p[1].trim(), p[2].trim().toDouble(), p[3].trim().toDouble())
            }.toList()
        }
    }

    val provinces: List<String> by lazy { all.map { it.province }.distinct() }

    fun inProvince(province: String): List<City> = all.filter { it.province == province }

    fun find(province: String, name: String): City? = all.firstOrNull { it.province == province && it.name == name }

    val tehran: City by lazy { find("تهران", "تهران")!! }

    /** The listed city closest to a point, by great-circle distance. */
    fun nearest(lat: Double, lon: Double): City = all.minBy { distanceKm(lat, lon, it.lat, it.lon) }

    fun distanceKm(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        fun r(d: Double) = d * PI / 180.0
        val a = sin(r(lat2 - lat1) / 2).pow(2) + cos(r(lat1)) * cos(r(lat2)) * sin(r(lon2 - lon1) / 2).pow(2)
        return 2 * 6371.0 * asin(sqrt(a))
    }
}

package app.linuxpad.runtime

import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.PowerManager
import android.os.StatFs
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.io.File
import java.io.IOException
import java.nio.file.FileVisitResult
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.SimpleFileVisitor
import java.nio.file.attribute.BasicFileAttributes
import kotlin.concurrent.thread

/** What the tablet reports about itself: memory, battery temperature, heat state and storage. Only what Android allows an app to read. */
object DeviceStats {
    data class Snapshot(
        val memTotal: Long, val memUsed: Long,
        val batteryTempC: Float?, val batteryPercent: Int?, val charging: Boolean,
        val thermal: String, val thermalLevel: Int, val cpuTempC: Float?,
        val storageFree: Long, val storageTotal: Long,
    )

    /** Size of the Linux system on disk; measured in the background because it has very many small files. */
    var linuxBytes by mutableStateOf<Long?>(null); private set
    @Volatile private var measuring = false

    fun read(ctx: Context): Snapshot {
        val am = ctx.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val mi = ActivityManager.MemoryInfo().also { am.getMemoryInfo(it) }
        val b: Intent? = ctx.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val temp = b?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Int.MIN_VALUE)?.takeIf { it != Int.MIN_VALUE }?.let { it / 10f }
        val level = b?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale = b?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
        val status = b?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
        val pm = ctx.getSystemService(Context.POWER_SERVICE) as PowerManager
        val level2 = pm.currentThermalStatus
        val thermal = when (level2) {
            PowerManager.THERMAL_STATUS_NONE -> "Normal"
            PowerManager.THERMAL_STATUS_LIGHT -> "Slightly warm"
            PowerManager.THERMAL_STATUS_MODERATE -> "Warm, may slow down"
            PowerManager.THERMAL_STATUS_SEVERE -> "Hot, slowing down"
            else -> "Very hot"
        }
        val st = StatFs(ctx.filesDir.absolutePath)
        return Snapshot(mi.totalMem, mi.totalMem - mi.availMem, temp, if (level >= 0 && scale > 0) level * 100 / scale else null,
            status == BatteryManager.BATTERY_STATUS_CHARGING || status == BatteryManager.BATTERY_STATUS_FULL,
            thermal, level2, cpuTemp(), st.availableBytes, st.totalBytes)
    }

    /** The hottest readable thermal zone that looks like the processor. Many devices do not let apps read these: then null. */
    private fun cpuTemp(): Float? = runCatching {
        File("/sys/class/thermal").listFiles { f -> f.name.startsWith("thermal_zone") }.orEmpty().mapNotNull { z ->
            val type = runCatching { File(z, "type").readText().trim().lowercase() }.getOrNull() ?: return@mapNotNull null
            if (!(type.contains("cpu") || type.contains("soc") || type.contains("tsens") || type.contains("big") || type.contains("gold"))) return@mapNotNull null
            val raw = runCatching { File(z, "temp").readText().trim().toFloat() }.getOrNull() ?: return@mapNotNull null
            if (raw > 1000f) raw / 1000f else raw
        }.filter { it in 10f..120f }.maxOrNull()
    }.getOrNull()

    /** Adds up the size of every file of the Linux system (symbolic links are not followed). Runs once in the background. */
    fun measureLinux(ctx: Context) {
        if (measuring) return
        measuring = true
        val root = LinuxSystem.rootDir(ctx).toPath()
        thread(name = "linuxpad-size") {
            var total = 0L
            try {
                if (Files.isDirectory(root)) Files.walkFileTree(root, object : SimpleFileVisitor<Path>() {
                    override fun visitFile(file: Path, attrs: BasicFileAttributes): FileVisitResult { if (attrs.isRegularFile) total += attrs.size(); return FileVisitResult.CONTINUE }
                    override fun visitFileFailed(file: Path, exc: IOException): FileVisitResult = FileVisitResult.CONTINUE
                })
            } catch (_: Throwable) { }
            linuxBytes = total
            measuring = false
        }
    }
}

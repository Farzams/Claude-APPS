package ir.taghvim.app.work

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.Constraints
import ir.taghvim.app.data.Holidays
import ir.taghvim.app.widget.Widgets
import ir.taghvim.core.JalaliDate
import java.net.HttpURLConnection
import java.net.URL
import java.time.LocalDate
import java.util.concurrent.TimeUnit

/** Where the official holiday lists of each year are published (one file per Jalali year). */
const val HOLIDAY_BASE_URL = "https://raw.githubusercontent.com/Farzams/Claude-APPS/main/taghvim/data/holidays/"

/** Redraws the widgets so the countdown, the highlighted time and the day stay right. */
class RefreshWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        Widgets.updateAll(applicationContext)
        return Result.success()
    }
}

/** Downloads the official holiday list of this and the next Jalali year, so lunar holidays follow the real announcement. */
class HolidaySyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val year = JalaliDate.of(LocalDate.now()).year
        var failed = false
        for (y in listOf(year, year + 1)) {
            when (fetch(y)) {
                Fetch.FAILED -> failed = true
                else -> Unit
            }
        }
        Widgets.updateAll(applicationContext)
        return if (failed) Result.retry() else Result.success()
    }

    private enum class Fetch { OK, MISSING, FAILED }

    private fun fetch(year: Int): Fetch = try {
        val c = URL("$HOLIDAY_BASE_URL$year.json").openConnection() as HttpURLConnection
        c.connectTimeout = 15000
        c.readTimeout = 15000
        when (c.responseCode) {
            200 -> { Holidays.save(applicationContext, year, c.inputStream.bufferedReader(Charsets.UTF_8).readText()); Fetch.OK }
            404 -> Fetch.MISSING // the year has not been published yet
            else -> Fetch.FAILED
        }
    } catch (e: Exception) {
        Fetch.FAILED
    }
}

object Schedule {
    fun ensure(context: Context) {
        val wm = WorkManager.getInstance(context)
        wm.enqueueUniquePeriodicWork("refresh", ExistingPeriodicWorkPolicy.KEEP, PeriodicWorkRequestBuilder<RefreshWorker>(15, TimeUnit.MINUTES).build())
        wm.enqueueUniquePeriodicWork(
            "holidays",
            ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<HolidaySyncWorker>(1, TimeUnit.DAYS)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()).build(),
        )
    }

    fun syncHolidaysNow(context: Context) {
        WorkManager.getInstance(context).enqueue(
            OneTimeWorkRequestBuilder<HolidaySyncWorker>()
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()).build(),
        )
    }
}

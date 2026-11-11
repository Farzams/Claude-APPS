# Taghvim (تقویم)

Persian (Jalali) calendar for Android, built around two home-screen widgets:

* **Month widget, 4x4**: the Jalali month with Fridays and official holidays in the accent colour, a themed background and a small icon for the special days (Nowruz, 22 Bahman, Tasua and Ashura, births, Christmas and so on), arrows to move between months, and the month's occasions listed under the grid.
* **Prayer-times widget, 4x1**: dawn, sunrise, noon, sunset, maghrib and midnight with scene icons, the next one highlighted and a countdown to it ("۴۸ دقیقه تا نیمه‌شب").

The app itself is one settings screen: city (all 31 provinces) or "detect my location", the order and visibility of the four occasion groups (drag to reorder), moon-sighting correction (-1, 0, +1 day), the small second line under each day (none, lunar, Gregorian), dark/light theme and accent colour. The design lives in the Artifact page the project was designed on.

## Layout

| Path | What it is |
| --- | --- |
| `core/` | Pure Kotlin (JVM) calendar logic with tests: Jalali conversion, Hijri dates with a sighting shift, occasions, prayer times, cities |
| `core/src/main/resources/data/` | `events.json` (fixed occasions), `cities.csv`, bundled official holiday lists (1404, 1405) |
| `app/` | The Android app: Jetpack Glance widgets, settings screen (Compose), WorkManager jobs |
| `data/holidays/` | Official lunar holiday list per Jalali year, published here and downloaded by the app |
| `tools/` | `render_assets.js` draws the PNG artwork in `app/src/main/res/drawable-nodpi` from `icons.json` and `themes.css` |

## Decisions

* **Prayer times** follow the Institute of Geophysics, University of Tehran: fajr at 17.7 degrees, maghrib at 4.5 degrees, midnight halfway between sunset and the next fajr. The test compares Noshahr on 20 Aban 1405 with the reference widget (05:10, 06:37, 11:48, 16:58, 17:18, 23:04) and they match to the minute.
* **Lunar dates** come from the Umm al-Qura table in `java.time`; Iran's moon sighting can differ by a day, so the user can shift it. The exact official lunar holidays of a year come from `data/holidays/<year>.json` (made from the time.ir derived datasets), bundled for 1404 and 1405 and downloaded daily for the current and next year (`HOLIDAY_BASE_URL` in `work/Workers.kt`).
* **Occasion groups** (default order): official holidays, religious non-holidays, national and special days, global and Gregorian days. The group first in the user's order decides the look of a day.
* Nothing is written under the Jalali date by default; the second line is optional.

## Build

```
cd taghvim
./gradlew :core:test            # anywhere with a JDK
./gradlew :app:assembleDebug    # needs the Android SDK (ANDROID_HOME)
```

GitHub Actions (`.github/workflows/build-taghvim.yml`) runs both and publishes the APK in the release `taghvim-latest`.

## Adding a year

Make `data/holidays/<year>.json` with the official lunar holidays of that Jalali year (same shape as `1405.json`), commit it, and installed apps pick it up within a day.

(CI re-run)

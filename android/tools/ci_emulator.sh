#!/usr/bin/env bash
# Runs inside the Android emulator (started by reactivecircus/android-emulator-runner).
set -uo pipefail
cd "$(dirname "$0")/.."
adb shell settings put global window_animation_scale 0 || true
adb shell settings put global transition_animation_scale 0 || true
adb shell settings put global animator_duration_scale 0 || true
./gradlew --no-daemon connectedDebugAndroidTest
echo $? > ../test_exit.txt
mkdir -p ../shots
adb shell ls -l /data/local/tmp/shots > ../shots/_ls.txt 2>&1 || true
adb pull /data/local/tmp/shots ../_pulled > ../shots/_pull.txt 2>&1 || true
cp -r ../_pulled/. ../shots/ 2>/dev/null || true
adb exec-out screencap -p > ../shots/final.png || true
adb logcat -d -s PDFTK:I > ../pdftk.log || true
adb logcat -d -s chromium:I cr_ConsoleLog:I > ../chromium.log || true
adb logcat -d | grep -iE "lowmemorykiller|oom|out of memory|killed|FATAL|ANR|crash|render process" | tail -80 > ../system.log || true
exit 0

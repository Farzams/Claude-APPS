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
adb pull /data/local/tmp/shots/. ../shots/ || true
adb logcat -d -s PDFTK:I > ../pdftk.log || true
adb logcat -d -s chromium:I cr_ConsoleLog:I > ../chromium.log || true
exit 0

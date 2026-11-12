#!/usr/bin/env bash
# Runs inside the emulator job: installs the app, renders both widgets on a widget host, pulls the pictures.
cd "$(dirname "$0")/.."
mkdir -p ../shots
./gradlew --no-daemon :app:connectedDebugAndroidTest > ../gradle_test.log 2>&1
echo $? > ../test_exit.txt
adb logcat -d > ../logcat.txt 2>&1 || true
adb shell ls -R /sdcard/Android/data/ir.taghvim.calendar/files > ../files.txt 2>&1 || true
adb pull /sdcard/Android/data/ir.taghvim.calendar/files/. ../shots/ > ../pull.txt 2>&1 || true
adb exec-out screencap -p > ../shots/screen.png 2>/dev/null || true
exit 0

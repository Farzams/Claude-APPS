#!/usr/bin/env bash
# Runs inside the Android emulator (started by reactivecircus/android-emulator-runner).
set -uo pipefail
cd "$(dirname "$0")/.."
adb shell settings put global window_animation_scale 0 || true
adb shell settings put global transition_animation_scale 0 || true
adb shell settings put global animator_duration_scale 0 || true
pip install -q pillow 2>/dev/null || true
mkdir -p ../shots
( i=0; while true; do
    adb exec-out screencap -p > /tmp/frame.png 2>/dev/null
    python3 - "$i" <<'PY' || true
import sys
from PIL import Image
im = Image.open("/tmp/frame.png").convert("RGB")
im.thumbnail((420, 900))
im.save("../shots/frame_%03d.jpg" % int(sys.argv[1]), quality=70)
PY
    i=$((i+1)); sleep 15
  done ) &
REC=$!
./gradlew --no-daemon connectedDebugAndroidTest
echo $? > ../test_exit.txt
kill $REC 2>/dev/null || true
mkdir -p ../shots
adb shell ls -l /data/local/tmp/shots > ../shots/_ls.txt 2>&1 || true
adb pull /data/local/tmp/shots ../_pulled > ../shots/_pull.txt 2>&1 || true
cp -r ../_pulled/. ../shots/ 2>/dev/null || true
adb exec-out screencap -p > ../shots/final.png || true
adb logcat -d -s PDFTK:I > ../pdftk.log || true
adb logcat -d -s chromium:I cr_ConsoleLog:I > ../chromium.log || true
adb logcat -d | grep -iE "lowmemorykiller|oom|out of memory|killed|FATAL|ANR|crash|render process" | tail -80 > ../system.log || true
exit 0

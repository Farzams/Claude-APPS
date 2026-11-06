#!/bin/sh
# LinuxPad tuning. Runs twice per desktop start:
#   "pre"  before the desktop starts, inside a private session bus, so the first frame already has the final panel and wallpaper;
#   "live" after the desktop started, only to finish what "pre" could not (a step is remembered as done only when it is verified).
# Sizes for this screen are set every start; layout and wallpaper choices once, so that what the user changes inside XFCE stays.
# @PANEL@ @DOCK@ @ICON@ are filled in by the app.
MODE="${1:-pre}"
export DISPLAY=:0
M=/root/.config/linuxpad; mkdir -p "$M"
IMG=/usr/share/backgrounds/linuxpad.jpg
genmon_ok=1; dpkg -s xfce4-genmon-plugin >/dev/null 2>&1 || genmon_ok=0
need=0
[ -f "$M/layout-v2" ] || need=1
[ -f "$M/wallpaper-v3" ] || [ ! -f "$IMG" ] || need=1
[ -f "$M/genmon-v5" ] || [ $genmon_ok = 0 ] || need=1
[ "$MODE" = live ] && [ $need = 0 ] && exit 0

for i in `seq 1 30`; do xfconf-query -c xfce4-panel -l >/dev/null 2>&1 && break; sleep 1; done
xfconf-query -c xfce4-panel -p /panels/panel-1/size -n -t uint -s @PANEL@
xfconf-query -c xfce4-panel -p /panels/panel-1/icon-size -n -t uint -s 0
xfconf-query -c xfce4-panel -p /panels/panel-2/size -n -t uint -s @DOCK@
xfconf-query -c xfce4-panel -p /panels/panel-2/icon-size -n -t uint -s 0
xfconf-query -c xfce4-desktop -p /desktop-icons/icon-size -n -t uint -s @ICON@
xfconf-query -c xfce4-desktop -p /desktop-icons/use-custom-font-size -n -t bool -s true
xfconf-query -c xfce4-desktop -p /desktop-icons/font-size -n -t double -s 12

changed=0

# once: a simpler top panel (no workspace switcher, no user menu) and no drive icons on the desktop
if [ ! -f "$M/layout-v2" ]; then
  ids=`xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids 2>/dev/null | grep -E '^[0-9]+$'`
  drop=""; keep=""
  for id in $ids; do
    t=`xfconf-query -c xfce4-panel -p /plugins/plugin-$id 2>/dev/null`
    case "$t" in pager|actions) drop="$drop $id" ;; *) keep="$keep -t int -s $id" ;; esac
  done
  if [ -n "$drop" ] && [ -n "$keep" ]; then
    xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids --force-array $keep
    for id in $drop; do xfconf-query -c xfce4-panel -p /plugins/plugin-$id -r -R; done
    changed=1
  fi
  xfconf-query -c xfce4-desktop -p /desktop-icons/file-icons/show-filesystem -n -t bool -s false
  xfconf-query -c xfce4-desktop -p /desktop-icons/file-icons/show-removable -n -t bool -s false
  # done only when the dropped plugins are really gone from the list (or there was nothing to drop)
  now=`xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids 2>/dev/null | grep -E '^[0-9]+$'`
  left=0; for id in $drop; do echo "$now" | grep -qx "$id" && left=1; done
  [ -n "$now" ] && [ $left = 0 ] && touch "$M/layout-v2"
fi

# once: the default wallpaper, written for every real monitor name (the properties of a monitor exist only under its own name)
if [ ! -f "$M/wallpaper-v3" ] && [ -f "$IMG" ]; then
  mons=`xrandr 2>/dev/null | awk '/ connected/{print $1}'`
  [ -z "$mons" ] && mons="screen"
  for m in $mons monitor0; do
    for w in 0 1 2 3; do
      b=/backdrop/screen0/monitor$m/workspace$w
      xfconf-query -c xfce4-desktop -p $b/last-image -n -t string -s "$IMG"
      xfconf-query -c xfce4-desktop -p $b/image-style -n -t int -s 5
      xfconf-query -c xfce4-desktop -p $b/color-style -n -t int -s 0
    done
  done
  for p in `xfconf-query -c xfce4-desktop -l | grep -E 'last-image$'`; do xfconf-query -c xfce4-desktop -p $p -s "$IMG"; done
  first=`echo $mons | cut -d' ' -f1`
  if [ "`xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitor$first/workspace0/last-image 2>/dev/null`" = "$IMG" ]; then
    touch "$M/wallpaper-v3"
    [ "$MODE" = live ] && xfdesktop --reload >/dev/null 2>&1
  fi
fi

# once: a small indicator in the top panel with memory, heat and battery (the app writes /root/.linuxpad/stats.txt every few seconds)
if [ ! -f "$M/genmon-v5" ] && [ $genmon_ok = 1 ]; then
  # the plugin reads its settings only when it starts, so they are written before it is put on the panel
  xfconf-query -c xfce4-panel -p /plugins/plugin-90/command -n -t string -s "sh -c 'cat /root/.linuxpad/stats.txt 2>/dev/null || echo \"<txt>no data</txt>\"'"
  xfconf-query -c xfce4-panel -p /plugins/plugin-90/update-period -n -t int -s 3000
  xfconf-query -c xfce4-panel -p /plugins/plugin-90/use-label -n -t bool -s false
  xfconf-query -c xfce4-panel -p /plugins/plugin-90/enable-single-row -n -t bool -s true
  ids=`xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids 2>/dev/null | grep -E '^[0-9]+$'`
  if [ -n "$ids" ] && ! echo "$ids" | grep -qx 90; then
    args=""; put=0
    for id in $ids; do
      t=`xfconf-query -c xfce4-panel -p /plugins/plugin-$id 2>/dev/null`
      if [ "$t" = "clock" ] && [ $put = 0 ]; then args="$args -t int -s 90"; put=1; fi
      args="$args -t int -s $id"
    done
    [ $put = 0 ] && args="$args -t int -s 90"
    xfconf-query -c xfce4-panel -p /plugins/plugin-90 -n -t string -s genmon
    xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids --force-array $args
  fi
  changed=1          # the panel is started again so that the plugin reads its settings
  now=`xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids 2>/dev/null | grep -E '^[0-9]+$'`
  echo "$now" | grep -qx 90 && touch "$M/genmon-v5"
fi

# in the running desktop, a changed panel has to be started again to show it
if [ "$MODE" = live ] && [ $changed = 1 ]; then xfce4-panel -r >/dev/null 2>&1; fi
[ "$MODE" = pre ] && sleep 2   # let xfconfd write its files before this session bus ends
exit 0

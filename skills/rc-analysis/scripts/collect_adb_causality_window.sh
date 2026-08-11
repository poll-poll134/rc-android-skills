#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <adb-serial> <logcat-start-time> [output-dir]" >&2
  echo "example: $0 192.0.2.10:5555 '05-30 23:50:00.000' ./adb-causality-demo" >&2
  exit 2
fi

serial="$1"
start_time="$2"
out_dir="${3:-adb-causality-${serial//[:.]/_}}"

mkdir -p "$out_dir"

printf '%s\n' "$serial" > "$out_dir/serial.txt"
printf 'host=%s\nendpoint=%s\n' "${serial%%:*}" "${serial##*:}" > "$out_dir/topology_hint.txt"

adb devices > "$out_dir/adb_devices_before.txt" 2>&1 || true
device_state="$(
  awk -v serial="$serial" '$1 == serial { print $2; found=1; exit } END { if (!found) print "" }' \
    "$out_dir/adb_devices_before.txt"
)"

{
  echo "serial=$serial"
  echo "state_before=${device_state:-absent}"
  if [[ -z "$device_state" ]]; then
    echo "action=adb connect $serial"
    adb connect "$serial" 2>&1 || true
  else
    echo "action=skip adb connect"
    echo "already_listed_state=$device_state"
  fi
} > "$out_dir/adb_connect.txt"

adb devices > "$out_dir/adb_devices_after.txt" 2>&1 || true
adb -s "$serial" get-state > "$out_dir/adb_state.txt" 2>&1 || true
adb -s "$serial" shell date > "$out_dir/device_date.txt" 2>&1 || true
adb -s "$serial" shell ps -A > "$out_dir/ps_A.txt" 2>&1 || true
adb -s "$serial" shell dumpsys activity activities > "$out_dir/dumpsys_activity_activities.txt" 2>&1 || true
adb -s "$serial" shell dumpsys activity recents > "$out_dir/dumpsys_activity_recents.txt" 2>&1 || true

for buffer in system events main crash; do
  adb -s "$serial" logcat -b "$buffer" -d -v threadtime -T "$start_time" \
    > "$out_dir/logcat_${buffer}.txt" 2>&1 || true
done

{
  echo "# log buffer ranges"
  for buffer in system events main crash; do
    file="$out_dir/logcat_${buffer}.txt"
    first="$(grep -m 1 -E '^[0-9]{2}-[0-9]{2} ' "$file" || true)"
    last="$(grep -E '^[0-9]{2}-[0-9]{2} ' "$file" | tail -n 1 || true)"
    echo "$buffer first=${first:-NONE}"
    echo "$buffer last=${last:-NONE}"
  done
} > "$out_dir/log_buffer_ranges.txt"

{
  echo "# merged key events with buffer source"
  echo "# serial=$serial"
  echo "# start_time=$start_time"
  pattern="ActivityManager: Killing|am_kill|am_proc_died|am_crash|am_anr|lowmemory|lowmemorykiller|lmkd.*([Kk]ill|reclaim)|InputDispatcher: channel|Zygote  : Process|START u0|RecentsActivity|Launcher|am_(pause|stop|resume|destroy|finish|set_resumed)_activity"
  for buffer in system events main crash; do
    awk -v buffer="$buffer" -v pattern="$pattern" '$0 ~ pattern { print substr($0, 1, 18) " [" buffer "] " substr($0, 20) }' \
      "$out_dir/logcat_${buffer}.txt" 2>/dev/null || true
  done | sort
} > "$out_dir/merged_key_events.txt"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -x "$script_dir/analyze_adb_causality.py" ]]; then
  "$script_dir/analyze_adb_causality.py" "$out_dir" -o "$out_dir/rc_analysis_report.md" || true
fi

echo "$out_dir"

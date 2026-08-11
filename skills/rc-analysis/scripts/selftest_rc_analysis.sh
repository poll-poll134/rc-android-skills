#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

grep -Fq "adb devices" "$script_dir/collect_adb_causality_window.sh"
grep -Fq "adb connect" "$script_dir/collect_adb_causality_window.sh"
grep -Fq "already_listed_state" "$script_dir/collect_adb_causality_window.sh"

case_dir="$("$script_dir/init_rc_case_dir.sh" "android-container" "reader-demo" "20260530-2355" "CPUkill退桌面" "$tmp_dir")"
test -d "$case_dir/raw"
test -f "$case_dir/原始问题描述.md"
test -f "$case_dir/devices-adb.md"
test -f "$case_dir/aggregate-evidence.md"
test -f "$case_dir/最终分析报告.md"
grep -Fq "原始问题描述" "$case_dir/原始问题描述.md"
grep -Fq "聚合证据中间报告" "$case_dir/aggregate-evidence.md"
grep -Fq "## 日志证据" "$case_dir/最终分析报告.md"
! grep -Eq '^## (推断|需补证|下一次要抓)$' "$case_dir/最终分析报告.md"

default_root_tmp="$tmp_dir/default-root"
mkdir -p "$default_root_tmp"
(
  cd "$default_root_tmp"
  default_case_dir="$("$script_dir/init_rc_case_dir.sh" "android-arm64" "reader-demo" "20260531-1100" "CPUkill")"
  test -d "$default_case_dir/raw"
  test -f "$default_case_dir/原始问题描述.md"
  test -f "$default_case_dir/最终分析报告.md"
  case "$default_case_dir" in
    ./incident-analysis/RC-android-arm64-reader-demo-CPUkill-0531-1100) ;;
    *) echo "unexpected default case dir: $default_case_dir" >&2; exit 1 ;;
  esac
)

touch "$tmp_dir/logcat_crash.txt"

cat > "$tmp_dir/logcat_system.txt" <<'EOF'
05-30 23:55:51.430   405   447 I ActivityManager: Killing 18788:pluginhost.alpha:p0/u0a96 (adj 900): excessive cpu 64520 during 300001 dur=1003167 limit=2
05-30 23:55:51.431   405   447 I ActivityManager: Killing 13998:pluginhost.beta:p0/u0a97 (adj 700): excessive cpu 65860 during 300001 dur=1002797 limit=2
EOF

cat > "$tmp_dir/logcat_events.txt" <<'EOF'
05-30 23:55:51.430   405   447 I am_kill : [0,18788,pluginhost.alpha:p0,900,excessive cpu 64520 during 300001 dur=1003167 limit=2]
05-30 23:55:51.431   405   447 I am_kill : [0,13998,pluginhost.beta:p0,700,excessive cpu 65860 during 300001 dur=1002797 limit=2]
EOF

cat > "$tmp_dir/logcat_main.txt" <<'EOF'
05-30 23:55:51.434   405   514 W InputDispatcher: channel 'eac7608 com.example.reader/com.example.reader.ui.ReaderActivity (server)' ~ Consumer closed input channel or an error occurred.  events=0x9
05-30 23:55:51.436   193   193 I Zygote  : Process 18788 exited due to signal 9 (Killed)
05-30 23:55:51.437   405   514 W InputDispatcher: channel 'd562883 com.example.reader/com.example.reader.ui.ReaderActivity (server)' ~ Consumer closed input channel or an error occurred.  events=0x9
05-30 23:55:51.440   193   193 I Zygote  : Process 13998 exited due to signal 9 (Killed)
05-30 23:55:55.000   405   514 I ActivityTaskManager: START u0 {act=android.intent.action.MAIN cat=[android.intent.category.HOME] cmp=com.android.launcher3/.Launcher} from uid 10079
EOF

report="$("$script_dir/analyze_adb_causality.py" "$tmp_dir")"

grep -Fq "工具中间报告" <<<"$report"
grep -Fq "拓扑判断: 单端分析" <<<"$report"
grep -Fq "Chain 1: 时间窗关联（进程 kill/signal 实锤） kill -> channel_broken -> zygote_signal" <<<"$report"
grep -Fq "未取得 window-to-PID 映射时不能确认特定 Activity 因果" <<<"$report"
grep -Fq "pid=18788 proc=pluginhost.alpha:p0" <<<"$report"
grep -Fq "pid=13998 proc=pluginhost.beta:p0" <<<"$report"
grep -Fq "Home/Launcher/Recents 如在强证据链之后出现，只能作为结果现象" <<<"$report"

write_fixture() {
  local dir="$1"
  local serial="$2"
  local pid="$3"
  local proc="$4"
  local channel="$5"
  mkdir -p "$dir"
  printf '%s\n' "$serial" > "$dir/serial.txt"
  touch "$dir/logcat_events.txt" "$dir/logcat_crash.txt"
  cat > "$dir/logcat_system.txt" <<EOF
05-30 23:55:51.430   405   447 I ActivityManager: Killing $pid:$proc/u0a96 (adj 900): excessive cpu 64520 during 300001 dur=1003167 limit=2
EOF
  cat > "$dir/logcat_main.txt" <<EOF
05-30 23:55:51.434   405   514 W InputDispatcher: channel '$channel com.example.reader/com.example.reader.ui.ReaderActivity (server)' ~ Consumer closed input channel or an error occurred.  events=0x9
05-30 23:55:51.436   193   193 I Zygote  : Process $pid exited due to signal 9 (Killed)
05-30 23:55:55.000   405   514 I ActivityTaskManager: START u0 {act=android.intent.action.MAIN cat=[android.intent.category.HOME] cmp=com.android.launcher3/.Launcher} from uid 10079
EOF
}

write_fixture "$tmp_dir/hostA_c1" "192.0.2.10:5555" "18788" "pluginhost.alpha:p0" "eac7608"
write_fixture "$tmp_dir/hostA_c2" "192.0.2.10:5556" "13998" "pluginhost.beta:p0" "d562883"
write_fixture "$tmp_dir/hostB_c1" "198.51.100.20:5555" "20123" "pluginhost.gamma:p0" "aa55bb"

multi_report="$("$script_dir/analyze_adb_causality.py" "$tmp_dir/hostA_c1" "$tmp_dir/hostA_c2" "$tmp_dir/hostB_c1")"

grep -Fq "不能原样作为对外结论" <<<"$multi_report"
grep -Fq "端点数: 3" <<<"$multi_report"
grep -Fq "192.0.2.10=2端" <<<"$multi_report"
grep -Fq "198.51.100.20=1端" <<<"$multi_report"
grep -Fq "拓扑判断: 存在同宿主多容器" <<<"$multi_report"
grep -Fq "跨宿主校验" <<<"$multi_report"
grep -Fq 'pluginhost.*:p0 | excessive cpu | com.example.reader/com.example.reader.ui.ReaderActivity | kill->channel_broken->zygote_signal' <<<"$multi_report"

midnight_dir="$tmp_dir/midnight"
mkdir -p "$midnight_dir"
printf '%s\n' "192.0.2.10:5557" > "$midnight_dir/serial.txt"
touch "$midnight_dir/logcat_events.txt" "$midnight_dir/logcat_crash.txt"
cat > "$midnight_dir/logcat_system.txt" <<'EOF'
05-30 23:59:59.900   405   447 I ActivityManager: Killing 30123:pluginhost.midnight:p0/u0a96 (adj 900): excessive cpu 64520 during 300001 dur=1003167 limit=2
EOF
cat > "$midnight_dir/logcat_main.txt" <<'EOF'
05-31 00:00:00.100   405   514 W InputDispatcher: channel 'bb66cc com.example.reader/com.example.reader.ui.ReaderActivity (server)' ~ Consumer closed input channel or an error occurred.  events=0x9
05-31 00:00:00.120   193   193 I Zygote  : Process 30123 exited due to signal 9 (Killed)
EOF

midnight_report="$("$script_dir/analyze_adb_causality.py" "$midnight_dir")"
grep -Fq "Chain 1: 时间窗关联（进程 kill/signal 实锤） kill -> channel_broken -> zygote_signal" <<<"$midnight_report"

process_only_dir="$tmp_dir/process_only"
mkdir -p "$process_only_dir"
printf '%s\n' "203.0.113.30:5555" > "$process_only_dir/serial.txt"
touch "$process_only_dir/logcat_system.txt" "$process_only_dir/logcat_main.txt" "$process_only_dir/logcat_crash.txt"
cat > "$process_only_dir/logcat_events.txt" <<'EOF'
05-31 00:15:58.929   375   514 I am_kill : [0,18690,pluginhost.delta:p0,900,excessive cpu 17550 during 300007 dur=1789994 limit=2]
05-31 00:15:59.048   375  1036 I am_proc_died: [0,18690,pluginhost.delta:p0,900,17]
EOF

process_only_report="$("$script_dir/analyze_adb_causality.py" "$process_only_dir")"
grep -Fq "进程级实锤" <<<"$process_only_report"
grep -Fq "kill->proc_died" <<<"$process_only_report"
grep -Fq "当前聚合只有进程级 kill/died 证据" <<<"$process_only_report"

echo "rc-analysis selftest passed"

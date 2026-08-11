---
name: rc-analysis
description: Use when the user writes `RC分析:` or asks to diagnose Android/ADB/cloud-phone/container logs, logcat history, /data/misc/logd, 结合日志, 必然联系, 根因, 别瞎猜, Launcher exits, excessive CPU kills, InputDispatcher channel broken, ANR/crash/LMKD, or cross-buffer system/events/main evidence.
---

# RC分析

## Trigger And Boundary

Use this skill before answering any Android/container/cloud-phone incident where the user provides ADB endpoints or log snippets and asks for cause, root cause, 必然联系, or whether it is a system/app/script issue.

Shortcut trigger: `RC分析:`. Do not use this for `RC资料:` internal-doc retrieval; `RC资料:` is a separate evidence-only source-scope workflow.

Hard boundary:

- This skill is only for incident causality analysis from logs and live ADB evidence.
- Do not answer from memory, platform assumptions, current UI state, or generic Android knowledge when the log chain is incomplete.
- First report whether the log buffers cover the incident window. If current ADB buffers are rolled past the window, absence of evidence is not negative evidence.
- Before declaring current logcat coverage insufficient, check persistent logd history under `/data/misc/logd` when the device is reachable; rotated files such as `logcat`, `logcat.01`, `logcat.02` may preserve the incident window after `logcat -d` has rolled.
- No closed timestamp chain -> no firm root-cause conclusion.
- No thread/profile evidence -> no specific CPU-hot code claim.
- No crash/ANR/kill evidence -> do not claim crash/ANR/kill.
- User-provided unified logs are first-class evidence and can outrank current ADB buffers.

## Iron Rule

Do not infer the root cause from current foreground state, `recents`, screenshots, or later Launcher state. Those are terminal symptoms until a timestamp-merged log chain proves otherwise.

Accuracy beats time and efficiency. If a supplemental command, A/B run, screenshot, thread dump, or comparison endpoint can falsify the conclusion and is reachable, collect it before writing `最终分析报告.md`.

If the missing evidence can change the root-cause conclusion and you cannot collect it yourself, stop and ask the user for help in chat. Do not bury that blocker inside the final report.

Use `实锤` / `推断` / `需补证` as internal working labels or interim chat labels. `最终分析报告.md` is not the place for analysis-process noise: no unrun test TODOs, no "下一次要抓", and no speculative branch that has not been converted into either proof, exclusion, or an explicit evidence boundary.

## Tool Report Boundary

`scripts/analyze_adb_causality.py` output is an internal evidence report only. Do not use the aggregate report, endpoint matrix, chain distribution, or raw script wording as the final user-facing conclusion.

Final answers and outward-facing documents must be rewritten from the evidence into a concise conclusion document:

- what happened
- log evidence
- cause / responsibility boundary
- result / impact
- counter-evidence and evidence limits
- verified exclusions and conclusion boundary

The tool report path may be linked as supporting data, but the report itself is not the conclusion.

## Case Folder Rule

When the user triggers `RC分析:`, create or reuse this root folder under the current working directory:

```text
incident-analysis/
```

Then create one case folder inside it before or during collection. The case folder name must briefly describe:

- platform short name from the user, such as `android-arm64`, `android-container`, `multi-platform`
- project short name from the user, such as `reader-demo`, `gps`, `sensor`
- short problem phrase from the user, such as `CPUkill退桌面`, `分屏异常`
- incident time, preferably compact `MMDD-HHMM`; use `unknown` if unclear

Recommended name:

```text
RC-<平台名>-<项目名>-<问题短述>-<MMDD-HHMM>
```

Keep the folder name concise. Target 30-45 characters when possible. Do not put the full incident sentence, long ADB details, every platform/card, or root-cause wording in the folder name. Use the user's short labels; if the user has not provided them, ask for them with the fixed input prompt. If details are unknown, use `unknown` rather than inventing them. If the user provides a long phrase for a directory field, ask for or derive a short neutral label before creating the folder; never use the long phrase directly.

Required contents:

```text
incident-analysis/
  RC-<case>/
  README.md                    # case summary and file map
  原始问题描述.md                # user's original problem, supplements, and raw ask
  devices-adb.md               # platform/card/container/ADB address/reachability
  aggregate-evidence.md        # internal aggregate evidence, generated or summarized
  最终分析报告.md                # outward-facing final analysis report in Chinese
  raw/                         # per-endpoint adb collection folders/log snippets
```

Use `scripts/init_rc_case_dir.sh <platform-short> <project-short> <incident-time> <problem-short> [root]` when useful. If `root` is omitted, the script uses `./incident-analysis`. If collecting live ADB data, put each endpoint directory under `raw/`, then write the combined analyzer output to `aggregate-evidence.md`. Always write the final user-facing document to `最终分析报告.md`.

## Privacy And Publication Boundary

Live evidence may contain customer names, device serials, host/container addresses, instance IDs, package names, account data, tokens, and proprietary paths. Preserve original evidence unchanged inside the private incident case while diagnosing; redact only an exported copy intended for sharing.

- Never commit `incident-analysis/`, `raw/`, tombstones, DropBox entries, logcat captures, screenshots, or customer-supplied snippets to the skill repository.
- Before sharing an exported report, replace customer/project labels, endpoint addresses, serials, instance IDs, private package/process names, usernames, and absolute home paths with stable placeholders.
- Use RFC 5737 documentation addresses (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) in examples.
- Keep a private mapping only when operational follow-up requires it; never place that mapping in a public repository.
- Redaction must not change timestamps, event order, PID relationships, reason strings, or other facts needed to audit causality.

## Fixed Input Prompt

If the user sends only `RC分析:` or the incident input is missing the original problem or ADB list, ask for this fixed format before drawing conclusions:

```text
请按这个格式给我：

【目录字段】
平台名（短，用于目录，例：android-arm64 / android-container / multi-platform）：
项目名（短，用于目录，例：reader-demo / gps / sensor）：
大概的问题描述（短，用于目录，例：CPUkill退桌面 / 分屏异常）：
发生时间（用于目录，可粗略，例：0530-2355 / 0531-1100 / unknown）：

【原始问题描述】
发生时间：
现象：
操作/脚本/业务背景：
用户或测试同事看到的结果：
已知补充口径：

【ADB 地址清单】
平台/机型：
卡位/宿主：
容器/实例：
ADB 地址：
备注（可能连不上/已确认异常/正常对照等）：

【已有日志片段】可选
直接粘贴原始 logcat/系统日志，不要先改写。
```

After receiving it, create the case directory from `目录字段` only, then save the full original text into `原始问题描述.md` before summarizing or analyzing. Keep user's wording intact where possible; add a separate `整理字段` section only for normalization.

## Completion And Cleanup Rule

After writing `最终分析报告.md`, tell the user the case folder path and ask them to confirm whether the analysis quality is acceptable.

Only after the user confirms the quality is acceptable, ask whether to delete temporary files. Define the default temporary files as:

- `raw/` per-endpoint ADB collection folders
- ad hoc scratch logs or generated duplicate reports not referenced by `最终分析报告.md`

Do not delete these unless the user explicitly confirms. By default, preserve:

- `README.md`
- `原始问题描述.md`
- `devices-adb.md`
- `aggregate-evidence.md`
- `最终分析报告.md`

If the user explicitly asks to delete the whole case folder, confirm that scope before removing it.

## Required Workflow

1. Normalize ADB connection before collection:
   - Run `adb devices` first.
   - If the serial already appears with state `device`, do not run `adb connect`; collect directly.
   - If the serial appears as `offline` or `unauthorized`, do not hide that by repeated connect loops; record the state as a collection gap.
   - If the serial is absent, run exactly `adb connect <adb-address>`, then recheck `adb devices`.
2. Collect the same evidence for every endpoint:
   - `logcat -b system -d -v threadtime`
   - `logcat -b events -d -v threadtime`
   - `logcat -b main -d -v threadtime`
   - `logcat -b crash -d -v threadtime`
   - If the incident window may be outside current buffers, inspect persistent logd history: `adb -s <serial> shell "ls -al /data/misc/logd 2>&1"`. If normal shell cannot read it and root is available, retry read-only through `su 0`.
   - Pull or inspect relevant `/data/misc/logd/logcat*` rotated files into `raw/logd-history-<timestamp>/<serial>-logcat.N`; record file name, size, mtime, and first/last timestamps. Treat these files as first-class historical logcat evidence.
   - Do not parallelize large `/data/misc/logd` pulls on unstable network ADB; pull sequentially to avoid pushing devices offline.
   - `dumpsys activity activities`, `dumpsys activity recents`, `ps -A`
   - Prefer `scripts/collect_adb_causality_window.sh <serial> <start-time> <out-dir>` when a device is reachable.
3. Record each buffer and logd history file's first/last timestamp, then merge logs by timestamp around the reported window. If the user gives a snippet, align local logs to that exact second.
4. Build a process map before explaining: PID -> process name, UID -> package, window/activity -> hosting process, plugin/container host vs apparent app package.
5. Rank evidence in this order:
   - `am_kill`, `ActivityManager: Killing`, `am_proc_died`, `Zygote ... signal`, `am_crash`, `am_anr`, LMKD/lowmemory
   - `InputDispatcher ... channel ... broken`
   - activity lifecycle: pause/stop/destroy/resume
   - `START ... HOME`, Recents, Launcher, `wm_task_moved`
   - current focus and `recents` lastActiveTime
6. Build the minimum closed chain: trigger event -> affected PID/process -> affected activity/window -> immediate system result -> final user-visible symptom.
7. State only what logs directly prove. Keep unproven explanations in `aggregate-evidence.md` or chat while investigating; do not write `最终分析报告.md` until they have been proven, ruled out, or reduced to a clear evidence boundary.

## Single And Multi Endpoint Rule

Analyze every endpoint independently first, then aggregate. This applies equally to:

- one endpoint / one container
- one host with multiple containers
- multiple hosts with one or more containers each
- mixed Android architectures, container images, cloud-phone devices, or platform variants

Do not let aggregation erase per-endpoint truth:

- Single endpoint: never extrapolate to the whole host, platform, script fleet, or device model.
- Same host, multiple containers: same-second failures may indicate shared host pressure, shared script action, or shared image/config; require host CPU/load/container/lmkd evidence before naming the host/platform as root cause.
- Multiple hosts: the same process/reason/activity chain across hosts strengthens a component/script/clone-link hypothesis, but does not prove the exact CPU-hot thread or method.
- Mixed results: if some endpoints form a chain and others do not, report `已成链端点` and `未成链端点` separately. Missing chains are not counter-evidence unless buffer coverage proves the window was captured.

## Causality Gate

Before writing `结论`, reject any chain that fails one of these:

- Time order: cause timestamp must be before effect timestamp.
- Subject continuity: PID/process/UID/activity/window must map across buffers.
- Strongest evidence: kill/crash/anr/signal/channel evidence beats later UI state.
- Alternative check: name the plausible competing cause and the log line that supports or weakens it.
- Responsibility split: separate system mechanism, component fault domain, and user-visible symptom.

During interim diagnosis and `aggregate-evidence.md`, use confidence labels only: `实锤`, `高概率`, `需补证`. Do not use vague certainty words when the chain is incomplete. For `最终分析报告.md`, unresolved `需补证` items must be resolved, excluded, moved to a conclusion boundary, or raised to the user before finalizing.

## Final Report Gate

Before writing or updating `最终分析报告.md`, apply this gate:

1. If a test or A/B comparison is still needed and you can run it, run it first.
2. If a needed test requires user/device/business-side help, ask the user before finalizing; write an interim chat update or `aggregate-evidence.md`, not a final report.
3. If the evidence is enough, write the final report only from closed evidence:
   - `已证实`: directly proven by logs, dumps, screenshots, traces, or controlled comparison
   - `已排除`: disproven by counter-evidence or normal comparison
   - `结论边界`: what the current evidence covers and does not cover
4. Never put these in `最终分析报告.md`:
   - "需补证"
   - "下一次要抓"
   - "还需要抓"
   - unexecuted command lists
   - speculative root-cause branches that were not tested
   - raw thinking trails, tool report phrasing, or collection process notes
5. Future validation for a proposed fix is allowed only under a repair/verification section, and must be phrased as validation criteria, not as missing evidence for the current root cause.

## CPU Kill Rule

If logs show:

```text
ActivityManager: Killing <pid>:<proc>/... excessive cpu ...
am_kill: [...,<pid>,<proc>,...,excessive cpu ...]
InputDispatcher: channel '<activity>' ... broken
Zygote: Process <pid> exited due to signal 9
```

Then the proven direct cause is: the hosting process was killed for excessive CPU, and the activity disappeared because its input channel broke. Do not say the app "self-crashed" unless crash logs prove it. Do not say the system is the root cause unless the kill policy itself is abnormal. For plugin/container apps, the visible activity may be `com.example.reader/...ReaderActivity` while the killed host is `pluginhost.*:p0`; explain that the activity was running inside the plugin/container host.

If logs only show `am_kill` / `ActivityManager: Killing` plus `am_proc_died`, classify it as `进程级实锤`: the process was killed and died. Do not promote it to `ReaderActivity disappeared because channel broke` unless `InputDispatcher channel broken`, `Zygote signal`, activity lifecycle, or window-to-process mapping also covers that moment.

If asked "why CPU was high", answer only to the proven level:

- proven: which PID/process exceeded CPU and was killed
- not proven without stacks/profiles: which thread, method, script action, or app logic consumed CPU
- required evidence: `top -H`, `debuggerd -b`, Perfetto/simpleperf, or thread stacks before kill

## Recents/Home Rule

Treat Recents/Home/Launcher logs carefully:

- They prove the final UI state only when they occur after a stronger kill/crash/channel-broken chain.
- They can be direct cause only if they immediately precede the disappearance and no stronger kill/crash/channel evidence exists.
- Later user/tester inspection can generate Recents/Home logs; do not promote those to root cause.

## Final Output Shape

```markdown
## 结论
一句话说明已被证据闭合的事实，明确系统/应用/脚本/分身责任边界。
## 日志证据
- timestamp -> exact event -> 证明什么
## 发生原因
- 直接触发:
- 根因归属:
- 系统机制:
- 伴随/放大因素:
## 结果/影响
- 用户看到什么:
- 哪些端点受影响:
- 哪些端点已复现或已对照正常:
## 反证与边界
- 不能归因的对象:
- 不能外推的范围:
## 已证实
- ...
## 已排除
- ...
## 结论边界
- 当前结论覆盖到哪里；不写待补命令或未执行测试清单。
## 支撑数据
- 内部工具报告路径，可选；不要把工具报告原样当结论。
```

## Helper Scripts

- `scripts/init_rc_case_dir.sh`: create the standard case folder and placeholder files in the current working directory or chosen root.
- `scripts/collect_adb_causality_window.sh`: collect one endpoint and create `serial.txt`, `topology_hint.txt`, `log_buffer_ranges.txt`, `merged_key_events.txt`, and `rc_analysis_report.md`.
- `scripts/analyze_adb_causality.py`: analyze one or more collected directories without reconnecting to the device; emits internal evidence data, not the final external conclusion.
- `scripts/selftest_rc_analysis.sh`: regression test for the kill -> channel broken -> signal -> Launcher trap.

## Self-Check Before Final

- Did I merge `system/events/main/crash` by timestamp?
- Did I check buffer coverage before treating missing lines as meaningful?
- If current buffers missed the incident window, did I check `/data/misc/logd/logcat*` history before calling the evidence missing?
- Did I privilege `kill/crash/anr/signal/channel broken` over current focus?
- Did every cause happen before its claimed effect?
- Did PID/process/UID/activity mapping stay continuous across buffers?
- Did the user's snippet contain stronger evidence than my collected current buffer?
- Did I separate `实锤` from `推断` and `需补证`?
- If I still have `需补证`, did I keep it out of `最终分析报告.md` and ask the user instead when it can affect the conclusion?
- Did I rewrite the tool report into a user-facing evidence/cause/result document instead of pasting aggregate data as the conclusion?
- Did I ask for the fixed `原始问题描述` / `ADB 地址清单` format when the input was incomplete?
- Did I create the case folder under `incident-analysis/` in the current working directory and save `原始问题描述.md`, `devices-adb.md`, `aggregate-evidence.md`, and `最终分析报告.md` there?
- After completing the analysis, did I ask the user to confirm quality before asking whether to delete temporary files?
- Would one extra line of log change my conclusion? If yes, collect it before final; if I cannot collect it, ask the user and do not write a final report yet.

Regression cases: see [REGRESSION.md](REGRESSION.md).

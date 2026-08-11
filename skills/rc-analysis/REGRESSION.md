# RC分析 Regression Cases

Use these as pressure cases when editing this skill.

## Case 1: Kill Chain Beats Launcher

Input contains:

```text
ActivityManager: Killing <pid>:pluginhost.x:p0 excessive cpu
InputDispatcher: channel 'com.example.reader/...ReaderActivity' broken
Zygote: Process <pid> exited due to signal 9
START ... HOME ... Launcher
```

Expected: process kill/signal is proven and Launcher is 后续现象. A nearby channel break is only a time-window association unless separate window-to-PID evidence maps that activity to the killed process.

## Case 2: User Unified Log Beats Current Buffer

Input: user provides unified logs for 23:55, but current `adb logcat -d` starts at 00:30.

Expected: trust user unified log for 23:55, mark current buffer as incomplete, do not say "current logs do not show kill".

## Case 3: CPU Root Needs Thread Evidence

Input contains only process-level `excessive cpu`.

Expected: identify PID/process as proven; do not claim exact thread, method, app logic, or script action without `top -H`, stack, Perfetto, or simpleperf.

## Case 4: Time Order Trap

Input contains a later `START HOME` line and an earlier `Killing -> channel broken` line.

Expected: classify HOME as 后续现象 unless it is earlier than disappearance and no stronger evidence exists. Never use a later event as the cause of an earlier effect.

## Case 5: Responsibility Split

Input shows ActivityManager killed a process for policy reasons.

Expected: separate:

- system mechanism: ActivityManager policy kill
- fault domain: component that exceeded CPU or caused the host to exceed CPU
- symptom: app window disappeared or Launcher shown

## Case 6: Single Endpoint Boundary

Input has one collected directory with a complete excessive CPU kill chain.

Expected: conclude for that endpoint only. Do not extrapolate to all containers, the host, other platform variants, or the whole script fleet.

## Case 7: Same Host Multiple Containers

Input has two directories with documentation-only serials `192.0.2.10:5555` and `192.0.2.10:5556`; both show the same normalized `pluginhost.*:p0 | excessive cpu | ReaderActivity` chain.

Expected: aggregate as a same-host multi-container common time-window signature, but require window-to-PID mapping before claiming a specific Activity causal chain and host CPU/load/container/lmkd evidence before naming host/platform root cause.

## Case 8: Multiple Hosts Same Signature

Input has endpoints on different hosts with the same normalized process/reason/activity chain.

Expected: strengthen component/script/clone-link hypothesis and weaken single-host explanation. Keep thread/method/script action out of the final root-cause sentence unless thread/profile evidence exists; if that evidence is necessary and unavailable, ask the user or keep it only in interim `aggregate-evidence.md`, not in `最终分析报告.md`.

## Case 9: Mixed Coverage

Input has three endpoints: two form a kill/channel/signal chain, one has buffers missing or no incident-window logs.

Expected: report `已成链端点` and `未成链端点` separately. Do not count the missing endpoint as a contradiction.

## Case 10: Overnight Time Order

Input has `ActivityManager: Killing` at `05-30 23:59:59.900`, then `InputDispatcher channel broken` and `Zygote signal 9` at `05-31 00:00:00.xxx`.

Expected: preserve the cross-midnight `kill -> channel_broken -> zygote_signal` order; classify the channel as a time-window association unless window-to-PID mapping exists, and never treat midnight rollover as a negative time delta.

## Case 11: Process-Level Kill Evidence

Input has `am_kill ... excessive cpu` followed by matching `am_proc_died`, but `main` buffer has rolled and lacks `InputDispatcher channel broken` / `Zygote signal`.

Expected: classify as `进程级实锤`: process was killed and died. Do not say there is no kill evidence. Do not claim the ReaderActivity/window disappeared from this evidence alone.

## Case 12: Tool Report Is Not The Final Answer

Input has a generated `rc-analysis-combined.md` aggregate report with endpoint matrix and chain signatures.

Expected: use it only as internal evidence data. Final user-facing output must be rewritten as a closed-evidence report: `结论 / 日志证据 / 发生原因 / 结果影响 / 反证与边界 / 已证实 / 已排除 / 结论边界 / 支撑数据`, not pasted as the aggregate report and not polluted with collection TODOs.

## Case 13: Case Folder Deliverables

Input starts with `RC分析:` and includes directory fields, original problem, and one or more ADB endpoints.

Expected: create one concise case folder under `./incident-analysis/` named like `RC-<平台名>-<项目名>-<问题短述>-<MMDD-HHMM>`. The folder must contain `原始问题描述.md`, `devices-adb.md`, `aggregate-evidence.md`, `最终分析报告.md`, and `raw/`. The final answer should point to these files.

## Case 14: Quality Gate Before Cleanup

Input has a completed RC case folder and generated final report.

Expected: first ask the user whether analysis quality is acceptable. Only after the user confirms quality, ask whether to delete temporary files. Never delete `raw/` or scratch logs before explicit cleanup confirmation, and never delete `最终分析报告.md`, `原始问题描述.md`, `devices-adb.md`, or `aggregate-evidence.md` unless explicitly requested.

## Case 15: Fixed Intake Prompt And Short Directory

Input is only `RC分析:` or lacks directory fields, original problem description, or ADB address list.

Expected: do not start guessing and do not produce a conclusion. Ask the user to provide the fixed format containing `目录字段`, `原始问题描述`, `ADB 地址清单`, and optional `已有日志片段`. Directory fields must include `平台名`, `项目名`, `大概的问题描述`, and `发生时间`, and the case directory must be generated from these short fields only. After receiving the input, save the raw wording into `原始问题描述.md` before analysis.

## Case 16: ADB Connect Only When Missing

Input provides one or more TCP ADB addresses.

Expected: first run `adb devices`. If the serial is already listed as `device`, collect directly and do not run `adb connect` again. If the serial is listed as `offline` or `unauthorized`, record that state as a collection gap instead of repeating connect loops. Only when the serial is absent, run `adb connect <address>` and then recheck `adb devices`.

## Case 17: Final Report Must Not Contain Investigation Noise

Input has a live ADB endpoint and an initial hypothesis, plus a reachable normal comparison endpoint. Initial evidence suggests device ID failure, but a comparison run may prove whether that is differentiating.

Expected: run the reachable comparison before writing `最终分析报告.md`. If the comparison shows the same device ID failure on a normal endpoint, downgrade device ID to non-differentiating evidence and write the final report from the closed evidence. The final report must not contain `需补证`, `下一次要抓`, unrun commands, or "need more testing" sections. If the comparison endpoint is not reachable and the missing comparison can change the conclusion, ask the user in chat and do not write a final report yet.

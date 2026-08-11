#!/usr/bin/env python3
import argparse
import datetime as dt
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


TS_RE = re.compile(r"^(?:(\d{4})-)?(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})\.(\d+)")


@dataclass
class Event:
    key: tuple
    ts: str
    buffer: str
    kind: str
    subject: str
    detail: str
    line: str


@dataclass
class DirAnalysis:
    log_dir: Path
    events: list
    ranges: list
    chains: list
    context_lines: list
    serial: str
    host: str
    endpoint: str


def ts_key(line: str):
    m = TS_RE.match(line)
    if not m:
        return None
    year = int(m.group(1) or 0)
    month, day, hour, minute, second = map(int, m.groups()[1:6])
    frac = int((m.group(7) + "000000")[:6])
    return year, month, day, hour, minute, second, frac


def ts_text(line: str):
    m = TS_RE.match(line)
    return m.group(0) if m else ""


def classify(buffer_name: str, line: str):
    patterns = [
        ("kill", re.compile(r"ActivityManager: Killing\s+(\d+):([^/\s]+).*?:\s*(.*)$")),
        ("am_kill", re.compile(r"am_kill\s*: \[\d+,(\d+),([^,\]]+),[^,\]]+,([^\]]+)\]")),
        ("zygote_signal", re.compile(r"Zygote\s*: Process\s+(\d+) exited due to signal\s+(\d+)")),
        ("proc_died", re.compile(r"am_proc_died\s*: \[\d+,(\d+),([^,\]]+),")),
        ("channel_broken", re.compile(r"InputDispatcher: channel '([^']+)'.*(?:unrecoverably broken|Consumer closed input channel)")),
        ("crash", re.compile(r"(?:am_crash|FATAL EXCEPTION|AndroidRuntime).*")),
        ("anr", re.compile(r"(?:am_anr|ANR in ).*")),
        ("home_start", re.compile(r"START u0 .*?(?:category\.HOME|\.Launcher|Launcher).*")),
        ("recents_start", re.compile(r"START u0 .*?RecentsActivity.*")),
        ("activity_lifecycle", re.compile(r"am_(?:pause|stop|resume|destroy|finish|set_resumed)_activity.*")),
    ]
    for kind, pattern in patterns:
        m = pattern.search(line)
        if not m:
            continue
        if kind == "kill":
            return kind, f"pid={m.group(1)} proc={m.group(2)}", m.group(3)
        if kind == "am_kill":
            return kind, f"pid={m.group(1)} proc={m.group(2)}", m.group(3)
        if kind == "zygote_signal":
            return kind, f"pid={m.group(1)}", f"signal={m.group(2)}"
        if kind == "proc_died":
            return kind, f"pid={m.group(1)} proc={m.group(2)}", "process died"
        if kind == "channel_broken":
            return kind, "activity/window", m.group(1)
        return kind, "-", line.strip()
    return None


def read_events(log_dir: Path):
    events = []
    ranges = []
    seen = set()
    for buffer_name in ("system", "events", "main", "crash"):
        path = log_dir / f"logcat_{buffer_name}.txt"
        if not path.exists():
            ranges.append((buffer_name, "MISSING", "MISSING"))
            continue
        first = last = None
        with path.open(errors="replace") as f:
            for raw in f:
                line = raw.rstrip("\n")
                key = ts_key(line)
                if key:
                    first = first or ts_text(line)
                    last = ts_text(line)
                classified = classify(buffer_name, line)
                if key and classified:
                    kind, subject, detail = classified
                    event_id = (key, buffer_name, kind, subject, detail)
                    if event_id in seen:
                        continue
                    seen.add(event_id)
                    events.append(Event(key, ts_text(line), buffer_name, kind, subject, detail, line))
        ranges.append((buffer_name, first or "NONE", last or "NONE"))
    return sorted(events, key=lambda e: e.key), ranges


def subject_pid(subject: str):
    m = re.search(r"pid=(\d+)", subject)
    return m.group(1) if m else None


def seconds_between(a: Event, b: Event):
    def as_datetime(event: Event):
        year, month, day, hour, minute, second, frac = event.key
        # Android threadtime logs often omit the year. Use a stable leap year so
        # month/day ordering and overnight windows remain valid.
        return dt.datetime(year or 2000, month, day, hour, minute, second, frac)

    return (as_datetime(b) - as_datetime(a)).total_seconds()


def safe_read(path: Path):
    if not path.exists():
        return ""
    return path.read_text(errors="replace").strip()


def infer_serial(log_dir: Path):
    serial = safe_read(log_dir / "serial.txt").splitlines()
    if serial and serial[0].strip():
        return serial[0].strip()

    merged = safe_read(log_dir / "merged_key_events.txt")
    m = re.search(r"^# serial=(\S+)", merged, re.MULTILINE)
    if m:
        return m.group(1)

    # Handles names like adb-causality-192_0_2_10_5555 or 192.0.2.10:5555.
    m = re.search(r"((?:\d{1,3}[_\.]){3}\d{1,3})[_:](\d{2,5})", log_dir.name)
    if m:
        return f"{m.group(1).replace('_', '.')}:{m.group(2)}"
    return log_dir.name


def split_serial(serial: str):
    m = re.match(r"^([^:]+):(\d+)$", serial)
    if m:
        return m.group(1), m.group(2)
    return "unknown-host", serial or "unknown-endpoint"


def context_lines(log_dir: Path):
    lines = []
    serial = infer_serial(log_dir)
    if serial:
        lines.append(f"- serial: {serial}")
    for name in ("adb_state.txt", "device_date.txt"):
        value = safe_read(log_dir / name).replace("\n", " | ")
        if value:
            lines.append(f"- {name}: {value}")
    return lines


def load_analysis(log_dir: Path):
    events, ranges = read_events(log_dir)
    chains = build_chains(events)
    serial = infer_serial(log_dir)
    host, endpoint = split_serial(serial)
    return DirAnalysis(
        log_dir=log_dir,
        events=events,
        ranges=ranges,
        chains=chains,
        context_lines=context_lines(log_dir),
        serial=serial,
        host=host,
        endpoint=endpoint,
    )


def build_chains(events):
    chains = []
    raw_kills = [e for e in events if e.kind in ("kill", "am_kill")]
    kills_by_pid = {}
    for kill in raw_kills:
        pid = subject_pid(kill.subject)
        if not pid:
            continue
        existing = kills_by_pid.get(pid)
        if existing is None or (existing.kind == "am_kill" and kill.kind == "kill"):
            kills_by_pid[pid] = kill
    kills = sorted(kills_by_pid.values(), key=lambda e: e.key)
    signals = [e for e in events if e.kind == "zygote_signal"]
    proc_died = [e for e in events if e.kind == "proc_died"]
    channels = [e for e in events if e.kind == "channel_broken"]
    homes = [e for e in events if e.kind in ("home_start", "recents_start")]
    for kill in kills:
        pid = subject_pid(kill.subject)
        if not pid:
            continue
        linked_signal = next((s for s in signals if subject_pid(s.subject) == pid and 0 <= seconds_between(kill, s) <= 5), None)
        linked_proc_died = next((p for p in proc_died if subject_pid(p.subject) == pid and 0 <= seconds_between(kill, p) <= 5), None)
        channel_end = linked_signal or linked_proc_died or kill
        candidate_channels = []
        seen_channels = set()
        for c in channels:
            if not (0 <= seconds_between(kill, c) <= max(1.0, seconds_between(kill, channel_end) + 0.5)):
                continue
            channel_id = c.detail.split()[0] if c.detail else c.ts
            if channel_id in seen_channels:
                continue
            seen_channels.add(channel_id)
            candidate_channels.append(c)
        if linked_signal and candidate_channels:
            before_signal = [c for c in candidate_channels if seconds_between(c, linked_signal) >= 0]
            linked_channels = [min(before_signal or candidate_channels, key=lambda c: abs(seconds_between(c, linked_signal)))]
        else:
            linked_channels = candidate_channels
        linked_home = next((h for h in homes if 0 <= seconds_between(kill, h) <= 30), None)
        if linked_signal or linked_channels or linked_proc_died:
            chain = [kill]
            chain.extend(linked_channels)
            if linked_signal:
                chain.append(linked_signal)
            elif linked_proc_died:
                chain.append(linked_proc_died)
            sorted_chain = sorted(chain, key=lambda e: e.key)
            chains.append((sorted_chain, linked_home))
    return chains


def buffer_coverage_label(ranges):
    present = [b for b, first, last in ranges if first not in ("MISSING", "NONE") and last not in ("MISSING", "NONE")]
    missing = [b for b, first, last in ranges if first in ("MISSING", "NONE") or last in ("MISSING", "NONE")]
    if not present:
        return "0/4 buffers covered"
    if missing:
        return f"{len(present)}/4 buffers covered; missing={','.join(missing)}"
    return "4/4 buffers covered"


def normalize_proc(subject: str):
    m = re.search(r"proc=([^\s]+)", subject)
    proc = m.group(1) if m else subject
    proc = re.sub(r"^pluginhost\.[^:]+(:p\d+)$", r"pluginhost.*\1", proc)
    proc = re.sub(r"^pluginhost\.[^:]+$", "pluginhost.*", proc)
    return proc


def kill_reason(detail: str):
    lower = detail.lower()
    if "excessive cpu" in lower:
        return "excessive cpu"
    if "lowmemory" in lower or "lmk" in lower:
        return "lowmemory/lmkd"
    if "empty" in lower:
        return "empty process"
    if "cached" in lower:
        return "cached process"
    return detail[:60] if detail else "unknown reason"


def activity_from_chain(chain):
    for e in chain:
        if e.kind != "channel_broken":
            continue
        m = re.search(r"([A-Za-z0-9_.]+/[A-Za-z0-9_.$]+)", e.detail)
        if m:
            return m.group(1)
    return "activity/window"


def chain_signature(chain):
    first = chain[0]
    kinds = "->".join(e.kind for e in chain)
    return f"{normalize_proc(first.subject)} | {kill_reason(first.detail)} | {activity_from_chain(chain)} | {kinds}"


def strongest_label(analysis: DirAnalysis):
    if analysis.chains:
        chain, _ = analysis.chains[0]
        if any(e.kind == "channel_broken" for e in chain) and any(e.kind == "zygote_signal" for e in chain):
            confidence = "时间窗关联（进程 kill/signal 实锤）"
        elif any(e.kind in ("zygote_signal", "proc_died") for e in chain):
            confidence = "进程级实锤"
        else:
            confidence = "高概率"
        return f"{confidence}: {chain_signature(chain)}"
    if any(e.kind == "crash" for e in analysis.events):
        return "需排序: crash evidence present"
    if any(e.kind == "anr" for e in analysis.events):
        return "需排序: ANR evidence present"
    return "需补证: no closed kill/crash/channel chain"


def has_later_home(analysis: DirAnalysis):
    return any(home for _, home in analysis.chains)


def render_endpoint_matrix(analyses):
    rows = ["| endpoint | host | directory | coverage | strongest evidence | later Home/Launcher |",
            "|---|---|---|---|---|---|"]
    for a in analyses:
        label = strongest_label(a).replace("|", "\\|")
        rows.append(
            f"| {a.serial} | {a.host} | {a.log_dir.name} | {buffer_coverage_label(a.ranges)} | {label} | {'yes' if has_later_home(a) else 'no'} |"
        )
    return "\n".join(rows)


def render_aggregate(analyses):
    lines = ["# RC分析汇总", ""]
    lines.append("> 工具中间报告：仅用于整理证据、覆盖范围、端点矩阵和链路签名；不能原样作为对外结论。最终结论必须重写为“日志证据 -> 发生原因 -> 结果/影响 -> 证据边界”。")
    lines.append("")
    endpoint_count = len(analyses)
    host_map = defaultdict(list)
    for a in analyses:
        host_map[a.host].append(a)

    lines.append("## 范围")
    lines.append(f"- 端点数: {endpoint_count}")
    host_summary = ", ".join(f"{host}={len(items)}端" for host, items in sorted(host_map.items()))
    lines.append(f"- 宿主分布: {host_summary}")
    if endpoint_count == 1:
        lines.append("- 拓扑判断: 单端分析；只能确认该端事实，不能外推为整宿主、整平台或所有容器同因。")
    elif any(len(items) > 1 for items in host_map.values()):
        lines.append("- 拓扑判断: 存在同宿主多容器；需要同时看容器间共性和宿主级压力证据。")
    else:
        lines.append("- 拓扑判断: 多宿主/多端分散；跨宿主同类链路更支持组件/脚本/分身共性，单宿主资源异常解释会被削弱。")
    lines.append("")

    chain_analyses = [(a, chain, home) for a in analyses for chain, home in a.chains]
    signature_counts = Counter(chain_signature(chain) for _, chain, _ in chain_analyses)
    lines.append("## 聚合结论")
    if not chain_analyses:
        lines.append("- 需补证: 所有输入端点均未形成 kill/crash/channel 闭环，不能给确定根因。")
    else:
        top_signature, top_count = signature_counts.most_common(1)[0]
        chain_endpoint_count = len({a.serial for a, _, _ in chain_analyses})
        full_chains = [
            (a, chain, home) for a, chain, home in chain_analyses
            if any(e.kind == "channel_broken" for e in chain) and any(e.kind == "zygote_signal" for e in chain)
        ]
        process_chains = [
            (a, chain, home) for a, chain, home in chain_analyses
            if any(e.kind in ("zygote_signal", "proc_died") for e in chain)
        ]
        lines.append(f"- 实锤: {chain_endpoint_count}/{endpoint_count} 个端点形成进程级 kill/died 证据；最高频时间窗签名为 `{top_signature}`，出现 {top_count} 次。")
        if full_chains:
            lines.append(f"- 时间窗关联: {len({a.serial for a, _, _ in full_chains})}/{endpoint_count} 个端点出现 kill/channel/signal 顺序；未取得 window-to-PID 映射时，不得提升为特定 Activity 的因果实锤。")
        elif process_chains:
            lines.append("- 需补证: 当前聚合只有进程级 kill/died 证据；若要证明具体 Activity/窗口退出，需要 Activity/window-to-PID 映射，并配合 channel broken 或 lifecycle 等时序证据。")
        if len(signature_counts) == 1 and chain_endpoint_count == endpoint_count:
            lines.append("- 高概率: 所有输入端点的闭环类型一致，可作为共同故障域候选，但仍需按拓扑区分宿主因素和组件因素。")
        elif len(signature_counts) == 1:
            lines.append("- 高概率: 已成链端点的闭环类型一致；未成链端点只能标为缺证或未复现，不能强行归同因。")
        else:
            lines.append("- 需分流: 多种闭环签名并存，不能写单一根因；应按签名拆分端点结论。")
        no_chain = [a.serial for a in analyses if not a.chains]
        if no_chain:
            lines.append(f"- 需补证: {len(no_chain)} 个端点未成链: {', '.join(no_chain)}。")

    same_host_multi = {host: items for host, items in host_map.items() if len(items) > 1}
    if same_host_multi:
        lines.append("- 同宿主多容器校验: 若同一宿主多个容器同秒级异常，需补宿主 CPU/load、容器调度、lmkd/pressure；没有这些证据不得直接归平台。")
    if len(host_map) > 1 and chain_analyses:
        lines.append("- 跨宿主校验: 若不同宿主出现同一进程/同一 kill reason/同一 Activity 链路，可增强组件、脚本或分身链路假设，但线程级原因仍需 profiling。")
    lines.append("")

    lines.append("## 端点矩阵")
    lines.append(render_endpoint_matrix(analyses))
    lines.append("")

    if signature_counts:
        lines.append("## 链路签名分布")
        for signature, count in signature_counts.most_common():
            endpoints = sorted({a.serial for a, chain, _ in chain_analyses if chain_signature(chain) == signature})
            lines.append(f"- `{signature}`: {count} 条链，端点={', '.join(endpoints)}")
        lines.append("")

    lines.append("## 聚合护栏")
    lines.append("- 多端不是天然同因；只有时间窗、事件类型、PID/进程/Activity 映射连续时，才可提升为共同故障域。")
    lines.append("- 一个宿主多个容器同时异常，需要额外宿主级证据；多个宿主同类异常，需要排除统一脚本/分身版本/业务动作。")
    lines.append("- 后续 Home/Launcher 只能在强链路之后作为结果现象；不能用最终桌面状态反推根因。")
    lines.append("- 进程级 excessive CPU 只能证明进程超限，不能证明具体线程、方法或脚本动作。")
    return "\n".join(lines) + "\n"


def md_table(events, limit=80):
    rows = ["| time | buffer | kind | subject | detail |",
            "|---|---|---|---|---|"]
    for e in events[:limit]:
        detail = e.detail.replace("|", "\\|")
        rows.append(f"| {e.ts} | {e.buffer} | {e.kind} | {e.subject} | {detail} |")
    if len(events) > limit:
        rows.append(f"| ... | ... | ... | ... | truncated {len(events) - limit} events |")
    return "\n".join(rows)


def render_dir_analysis(analysis: DirAnalysis):
    events = analysis.events
    ranges = analysis.ranges
    chains = analysis.chains
    lines = [f"# RC分析自动证据报告: {analysis.log_dir}", ""]
    if analysis.context_lines:
        lines.append("## 采集上下文")
        lines.extend(analysis.context_lines)
        lines.append("")
    lines.append("## 自动结论草案")
    if chains:
        full_chains = [
            chain for chain, _ in chains
            if any(e.kind == "channel_broken" for e in chain) and any(e.kind == "zygote_signal" for e in chain)
        ]
        if full_chains:
            lines.append(f"- 进程级实锤 + 时间窗关联: 发现 {len(full_chains)} 条 kill/channel/signal 顺序；进程 kill/signal 可证，但未取得 window-to-PID 映射时不能确认特定 Activity 因果。")
        else:
            lines.append(f"- 实锤: 发现 {len(chains)} 条进程级 kill/died 证据，可证明进程被系统杀死，但当前窗口/Activity 断开证据不足。")
        if any(home for _, home in chains):
            lines.append("- 后续现象: 检测到 Home/Launcher/Recents 相关事件，但它发生在强证据链之后，不应反推为根因。")
        lines.append("- 需补证: 如果要解释 CPU 为什么高，仍需线程栈、top -H、Perfetto/simpleperf 等证据。")
    else:
        lines.append("- 需补证: 当前采集窗口未检测到 kill/crash/channel 的闭环证据，不能给确定根因。")
    lines.append("")
    lines.append("## Log Buffer 覆盖")
    for buffer_name, first, last in ranges:
        lines.append(f"- {buffer_name}: first={first}; last={last}")
    lines.append("")
    lines.append("## 高优先级事件")
    lines.append(md_table(events))
    lines.append("")
    lines.append("## 候选因果链")
    if not chains:
        lines.append("- 需补证: no kill/crash/channel closed chain detected in the collected window.")
    for i, (chain, later_home) in enumerate(chains, 1):
        kinds = " -> ".join(e.kind for e in chain)
        if any(e.kind == "channel_broken" for e in chain) and any(e.kind == "zygote_signal" for e in chain):
            confidence = "时间窗关联（进程 kill/signal 实锤）"
        elif any(e.kind in ("zygote_signal", "proc_died") for e in chain):
            confidence = "进程级实锤"
        else:
            confidence = "高概率"
        lines.append(f"### Chain {i}: {confidence} {kinds}")
        for e in chain:
            lines.append(f"- {e.ts} [{e.buffer}] {e.kind}: {e.subject}; {e.detail}")
        if later_home:
            lines.append(f"- 后续现象: {later_home.ts} [{later_home.buffer}] {later_home.kind}: {later_home.detail}")
        first = chain[0]
        lines.append("- 分层判断:")
        lines.append(f"  - 直接触发: {first.kind} {first.subject} {first.detail}")
        lines.append("  - 系统机制: Android 系统策略/机制执行了该事件；只有证明策略异常，才能归为平台根因。")
        lines.append("  - 根因归属: 故障域优先落在被杀/崩溃进程及其驱动方；CPU 内因需要线程栈或性能采样补证。")
        lines.append("  - 后续现象: Home/Launcher/Recents 如在强证据链之后出现，只能作为结果现象。")
        if any(e.kind == "channel_broken" for e in chain):
            lines.append("  - 映射说明: InputDispatcher channel 通常不带 PID；无论单个还是多个相邻 channel broken，都只能视为同时间窗证据，除非另有 window-to-PID 映射。")
    lines.append("")
    lines.append("## 反证检查")
    if any(e.kind in ("crash", "anr") for e in events):
        lines.append("- 应用自身 crash/ANR: 当前窗口存在 crash/ANR 线索，需要和 kill/channel 链竞争排序。")
    else:
        lines.append("- 应用自身 crash/ANR: 高优先级事件中未见 crash/ANR；仅当 buffer 覆盖事故窗口时才可作为反证。")
    if any(home for _, home in chains):
        lines.append("- Home/Launcher 主动导致退出: 当前候选链中 Home/Launcher 晚于 kill/channel/signal，归类为后续现象。")
    else:
        lines.append("- Home/Launcher 主动导致退出: 当前窗口未形成可证明的 Home-before-disappear 链。")
    lines.append("- 系统平台根因: 目前只能证明系统机制执行事件；平台策略异常需要额外证据。")
    lines.append("")
    lines.append("## 护栏")
    lines.append("- 当前 buffer 未覆盖事故窗口时，缺失日志不能当反证。")
    lines.append("- 只有进程级 excessive CPU 时，不得解释到线程、方法、脚本动作级别。")
    return "\n".join(lines) + "\n"


def analyze_dir(log_dir: Path):
    return render_dir_analysis(load_analysis(log_dir))


def main():
    parser = argparse.ArgumentParser(description="Analyze collected Android ADB logcat evidence for RC分析.")
    parser.add_argument("log_dirs", nargs="+", help="Directories containing logcat_system/events/main/crash.txt")
    parser.add_argument("-o", "--output", help="Write combined markdown report to this file")
    args = parser.parse_args()
    analyses = [load_analysis(Path(d)) for d in args.log_dirs]
    report_parts = [render_aggregate(analyses)]
    report_parts.extend(render_dir_analysis(analysis) for analysis in analyses)
    report = "\n".join(report_parts)
    if args.output:
        Path(args.output).write_text(report)
    else:
        print(report, end="")


if __name__ == "__main__":
    main()

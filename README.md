# Android RC 分析与资料检索 Skills

这个仓库提供两个可独立使用的 Codex skill：

| Skill | 解决什么问题 | 触发方式 |
|---|---|---|
| `rc-analysis` | 分析 Android、ADB、云手机和容器环境中的崩溃、ANR、应用无法启动、进程被杀、Launcher 退出等故障 | `RC分析:` 或直接要求分析 Android/ADB 日志根因 |
| `rc-internal-docs-only` | 仅从你指定的本地 RC 资料目录中检索和回答，避免混入网络、模型记忆或其他文件的内容 | `RC资料:` |

## `rc-analysis`：Android 故障因果分析

### 适用问题

- 应用启动后立即退出、无法进入 Activity，或强制回到 Launcher。
- Java crash、native crash、ANR、tombstone、DropBox 事件。
- `ActivityManager: Killing`、`am_kill`、LMKD、`excessive cpu` 等进程终止问题。
- `InputDispatcher channel broken`、Binder 死亡、Activity 生命周期异常。
- 当前 logcat 已轮转，需要结合 `/data/misc/logd`、tombstone 或用户提供的历史日志。
- 同宿主多容器、跨宿主多端点的共性故障对比。
- 判定“是应用问题、系统执行机制，还是容器/宿主责任域”。

### 它会做什么

1. 先检查日志是否覆盖事故时间，避免把“当前缓冲区没有”误当成“没发生”。
2. 按时间合并 `system` / `events` / `main` / `crash` 证据。
3. 建立 PID、进程、UID、Activity 和 window 的映射关系。
4. 构建“触发事件 → 受影响进程 → 系统结果 → 用户可见现象”的最小闭环。
5. 分开说明系统执行了什么、故障责任域在哪里，以及当前证据不能证明什么。
6. 生成事故目录、聚合证据和最终分析报告。

### 如何使用

有 ADB 现场时：

```text
RC分析:

【目录字段】
平台名（短）：android-container
项目名（短）：reader-demo
大概的问题描述（短）：应用启动闪退
发生时间：0811-0948

【原始问题描述】
现象：应用启动后立即退出
操作：am start -n com.example.reader/.MainActivity
已知补充：重装后仍复现

【ADB 地址清单】
平台/机型：android-arm64
容器/实例：demo-01
ADB 地址：192.0.2.10:5555
备注：只读分析，不允许重启、清数据或重装
```

只有日志、没有可连接设备时，直接粘贴或附上日志：

```text
RC分析: 请结合附件日志判定应用退出原因。
事故时间：08-11 09:48:00
限制：只读分析，不要操作设备。
```

`rc-analysis` 不需要额外环境变量。如果需要实时采集，本机必须已安装 `adb`，并且 Codex 有权访问目标设备。

## `rc-internal-docs-only`：限定本地资料检索

### 适用问题

- 查找内部命令、平台行为、故障处理方案或历史 RC 结论。
- 要求回答必须有指定资料原文支撑。
- 不允许使用网络、模型记忆或指定目录之外的文件补全答案。

### 配置资料目录

此 skill 必须通过 `RC_INTERNAL_DOCS_DIR` 获取资料根目录。值必须是本机上已存在且可读的绝对路径。

Codex CLI 或从终端启动 Codex 时：

```bash
export RC_INTERNAL_DOCS_DIR="/absolute/path/to/rc-docs"
codex
```

macOS Codex 桌面端：

```bash
launchctl setenv RC_INTERNAL_DOCS_DIR "/absolute/path/to/rc-docs"
```

配置后完全退出并重新打开 Codex。可用以下命令检查 macOS 当前配置：

```bash
launchctl getenv RC_INTERNAL_DOCS_DIR
```

Linux 图形界面下，应在启动 Codex 的桌面会话或服务环境中设置同名变量。

### 如何使用

```text
RC资料: 查找资料中对“持久化 logd 日志保留时间”的说明，列出命中的相对文件路径和结论。
```

返回状态含义：

- `未配置`：`RC_INTERNAL_DOCS_DIR` 没有设置或为空。
- `读取失败`：已配置，但目录不存在、不可读或无法解析。
- `未覆盖`：目录读取正常，但没有找到支持该问题的资料。

## 安装

### 1. 下载仓库

```bash
git clone https://github.com/poll-poll134/rc-android-skills.git
cd rc-android-skills
```

### 2. 安装到 Codex skills 目录

Codex 使用默认目录 `~/.codex` 时：

```bash
mkdir -p ~/.codex/skills/rc-analysis ~/.codex/skills/rc-internal-docs-only
rsync -a skills/rc-analysis/ ~/.codex/skills/rc-analysis/
rsync -a skills/rc-internal-docs-only/ ~/.codex/skills/rc-internal-docs-only/
```

如果你配置了自定义 `CODEX_HOME`，请将上述目标路径改为 `$CODEX_HOME/skills/...`。

### 3. 检查安装

```bash
test -f ~/.codex/skills/rc-analysis/SKILL.md
test -f ~/.codex/skills/rc-internal-docs-only/SKILL.md
```

然后重新打开 Codex，或新建一个任务，分别输入：

```text
RC分析:
```

```text
RC资料: 查找一个只有本地资料才能回答的问题
```

第一个 skill 应请求你补充事故字段；第二个 skill 应只从已配置的资料目录回答。

## 更新

```bash
cd rc-android-skills
git pull
rsync -a skills/rc-analysis/ ~/.codex/skills/rc-analysis/
rsync -a skills/rc-internal-docs-only/ ~/.codex/skills/rc-internal-docs-only/
```

## License

[MIT](LICENSE)

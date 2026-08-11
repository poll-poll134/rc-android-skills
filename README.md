# RC Android Skills

一组面向 Codex 的 Android / ADB / 云手机事故分析 skill。仓库只包含可复用的方法、脚本和脱敏回归样例，不包含任何客户现场日志或内部资料正文。

## 包含的 skills

### `rc-analysis`

用于从 Android `system` / `events` / `main` / `crash` 缓冲区、持久化 logd 历史、tombstone 和运行时证据中建立时间闭环。核心边界是：

- 当前 Launcher / 前台状态只是现象，不能直接当根因。
- 无闭合时间链，不下确定根因。
- 无线程或 profile 证据，不指定 CPU 热点方法。
- 区分系统执行机制、故障责任域和用户可见结果。
- 中间工具报告不直接当作对外结论。

附带脚本：

- `collect_adb_causality_window.sh`：按端点采集同口径证据。
- `analyze_adb_causality.py`：按时间聚合事件并生成中间证据报告。
- `init_rc_case_dir.sh`：生成标准事故目录。
- `selftest_rc_analysis.sh`：运行脱敏回归测试。

### `rc-internal-docs-only`

用于显式的 `RC资料:` 请求。它只定义“限定资料根目录内检索”的证据边界，不包含内部文档。资料目录由使用者本地配置：

```bash
export RC_INTERNAL_DOCS_DIR=/absolute/path/to/internal-docs
```

未配置、路径不可读或证据未覆盖时，skill 会明确报告对应边界，不从网络、模型记忆或其他本地路径补全。

## 安装

```bash
git clone https://github.com/poll-poll134/rc-android-skills.git
mkdir -p ~/.codex/skills
cp -R rc-android-skills/skills/rc-analysis ~/.codex/skills/
cp -R rc-android-skills/skills/rc-internal-docs-only ~/.codex/skills/
```

重启 Codex 或新建任务后使用。

## 测试

需要 Bash 和 Python 3；实际采集日志时还需要 `adb`。

```bash
./tests/test_public_release.sh
```

该测试会检查 skill 结构、Shell/Python 语法、脱敏规则、最终报告模板和因果聚合回归用例。

## 隐私边界

- 不要把 `incident-analysis/`、`raw/`、logcat、tombstone、DropBox、截图或客户提供的片段提交到此仓库。
- 诊断时保留私有原始证据不变；只对用于分享的副本做脱敏。
- 脱敏不能改变时间戳、事件顺序、PID 映射、reason 或其他因果判定依据。

## License

[MIT](LICENSE)

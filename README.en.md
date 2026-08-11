# Android Cloud-Service Incident Analysis and Local Documentation Retrieval Skills

[简体中文](README.md) | [English](README.en.md)

This repository provides two standalone skills for Codex:

| Skill | Problem it solves | Trigger |
|---|---|---|
| `rc-analysis` | Diagnoses crashes, ANRs, launch failures, process kills, Launcher exits, and similar incidents in Android, ADB, and container environments | `RC分析:` or a direct request to diagnose Android/ADB logs |
| `rc-internal-docs-only` | Answers questions using only a local RC documentation directory selected by the user, without mixing in web content, model memory, or unrelated files | `RC资料:` |

The trigger phrases remain in Chinese because they are the explicit shortcuts defined by the skills.

## `rc-analysis`: Android Incident Causality Analysis

### Problems and use cases

- **`RC分析:` + one ADB endpoint + a short problem description**: run an automated incident analysis.
- Analyze abnormal behavior in online Android cloud-service and container environments, and automatically collect the relevant diagnostic logs.
- Compare common failures across multiple containers on the same host or endpoints on different hosts. Keep conclusions grounded in direct log evidence instead of guesses or hallucinations.
- Determine whether the supported fault domain is the application, an Android system mechanism, or the container/host, then archive the raw logs and analysis in a consistent structure.

### What it does

1. Checks whether the available logs cover the incident window, so "not present in the current buffer" is not mistaken for "did not happen."
2. Merges evidence from the `system`, `events`, `main`, and `crash` buffers by timestamp.
3. Builds mappings between PIDs, processes, UIDs, activities, and windows.
4. Constructs the smallest supported chain from trigger event to affected process, immediate system result, and user-visible symptom.
5. Separates the system mechanism, the likely fault domain, and the limits of the available evidence.
6. Produces a case directory, an aggregate evidence report, and a final incident report.

### Usage

When a live ADB endpoint is available:

```text
RC分析:

[Case directory fields]
Platform short name: android-container
Project short name: reader-demo
Short problem description: app exits on launch
Incident time: 0811-0948

[Original problem]
Symptom: the app exits immediately after launch
Command: am start -n com.example.reader/.MainActivity
Additional context: reinstalling the app did not resolve the issue

[ADB endpoints]
Platform/device: android-arm64
Container/instance: demo-01
ADB address: 192.0.2.10:5555
Constraint: read-only analysis; do not reboot, clear data, or reinstall
```

When only logs are available, paste or attach them directly:

```text
RC分析: Diagnose why the app exited using the attached logs.
Incident time: 08-11 09:48:00
Constraint: read-only analysis; do not operate on the device.
```

`rc-analysis` does not require additional environment variables. Live collection requires `adb` on the local machine and permission for Codex to access the target device.

## `rc-internal-docs-only`: Scoped Local Documentation Retrieval

### Problems and use cases

- **`RC资料:` + an internal question**: use LLM-assisted parsing to search a local internal knowledge base.
- Find internal commands, platform behavior, incident procedures, or historical root-cause conclusions.
- Require every answer to be supported by the designated source documents.
- Prevent answers from being supplemented with web content, model memory, or files outside the approved directory.
- Search the configured local documentation automatically.
- Produce reliable answers grounded in the internal documentation.
- Retrieve stable operational knowledge and reference information that changes infrequently.

### Configure the documentation directory

This skill reads its documentation root from `RC_INTERNAL_DOCS_DIR`. The value must be an existing, readable absolute path on the local machine.

For Codex CLI, or when launching Codex from a terminal:

```bash
export RC_INTERNAL_DOCS_DIR="/absolute/path/to/rc-docs"
codex
```

For the Codex desktop app on macOS:

```bash
launchctl setenv RC_INTERNAL_DOCS_DIR "/absolute/path/to/rc-docs"
```

Quit Codex completely and reopen it after setting the variable. Check the current macOS value with:

```bash
launchctl getenv RC_INTERNAL_DOCS_DIR
```

On Linux desktops, set the same variable in the desktop session or service environment that launches Codex.

### Usage

```text
RC资料: Find the documentation that defines the retention period for persistent logd logs. Return the matching relative file paths and the supported conclusion.
```

Possible status responses:

- `未配置` (`not configured`): `RC_INTERNAL_DOCS_DIR` is unset or empty.
- `读取失败` (`read failed`): the variable is set, but the directory is missing, unreadable, or cannot be resolved.
- `未覆盖` (`not covered`): the directory was read successfully, but it contains no evidence supporting the question.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/poll-poll134/rc-android-skills.git
cd rc-android-skills
```

### 2. Install the skills

When Codex uses its default `~/.codex` directory:

```bash
mkdir -p ~/.codex/skills/rc-analysis ~/.codex/skills/rc-internal-docs-only
rsync -a skills/rc-analysis/ ~/.codex/skills/rc-analysis/
rsync -a skills/rc-internal-docs-only/ ~/.codex/skills/rc-internal-docs-only/
```

If you use a custom `CODEX_HOME`, replace the target paths above with `$CODEX_HOME/skills/...`.

### 3. Verify the installation

```bash
test -f ~/.codex/skills/rc-analysis/SKILL.md
test -f ~/.codex/skills/rc-internal-docs-only/SKILL.md
```

Reopen Codex or create a new task, then try:

```text
RC分析:
```

```text
RC资料: Find an answer that is available only in the configured local documentation.
```

The first skill should ask for the missing incident fields. The second should answer only from the configured documentation directory.

## Updating

```bash
cd rc-android-skills
git pull
rsync -a skills/rc-analysis/ ~/.codex/skills/rc-analysis/
rsync -a skills/rc-internal-docs-only/ ~/.codex/skills/rc-internal-docs-only/
```

## License

[MIT](LICENSE)

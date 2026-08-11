#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "usage: $0 <platform-short> <project-short> <incident-time> <problem-short> [root-dir]" >&2
  echo "example: $0 'android-container' 'reader-demo' '20260530-2355' 'CPUkill退桌面'" >&2
  exit 2
fi

platform="$1"
project="$2"
incident_time="$3"
problem="$4"
root="${5:-./incident-analysis}"

slug_part() {
  printf '%s' "$1" \
    | tr '[:space:]' '-' \
    | sed -E 's/[\/:*?"<>|]+/-/g; s/-+/-/g; s/^-//; s/-$//'
}

compact_time() {
  local value
  value="$(slug_part "$1")"
  if [[ "$value" =~ ^[0-9]{8}-[0-9]{4}$ ]]; then
    printf '%s-%s' "${value:4:4}" "${value:9:4}"
  else
    printf '%s' "$value"
  fi
}

folder="RC-$(slug_part "$platform")-$(slug_part "$project")-$(slug_part "$problem")-$(compact_time "$incident_time")"
case_dir="$root/$folder"

mkdir -p "$case_dir/raw"

cat > "$case_dir/README.md" <<EOF
# $folder

## 文件说明

- \`devices-adb.md\`: 设备、平台、卡位、容器、ADB 地址和连通性。
- \`原始问题描述.md\`: 用户原始问题、补充口径、原始 ADB 输入和已有日志片段。
- \`aggregate-evidence.md\`: 工具中间报告，只做证据数据层。
- \`最终分析报告.md\`: 对外中文最终分析报告。
- \`raw/\`: 每个端点的原始 ADB 采集目录或用户提供日志片段。
EOF

cat > "$case_dir/原始问题描述.md" <<EOF
# 原始问题描述

## 原始输入

待粘贴用户原始描述。保留原话，不要先改写成结论。

## 整理字段

- 平台名（短，用于目录）：$platform
- 项目名（短，用于目录）：$project
- 大概的问题描述（短，用于目录）：$problem
- 发生时间（用于目录）：$incident_time
- 发生时间：
- 现象：
- 操作/脚本/业务背景：
- 用户或测试同事看到的结果：
- 已知补充口径：

## 原始 ADB 地址清单

待粘贴用户提供的原始 ADB 地址、平台、卡位、宿主、容器和备注。

## 已有日志片段

待粘贴用户提供的原始日志片段。
EOF

cat > "$case_dir/devices-adb.md" <<EOF
# 设备与 ADB 地址

| 平台 | 卡位/宿主 | 容器/实例 | ADB 地址 | 状态 | 备注 |
|---|---|---|---|---|---|
|  |  |  |  |  |  |
EOF

cat > "$case_dir/aggregate-evidence.md" <<EOF
# 聚合证据中间报告

> 只用于整理日志证据、覆盖范围、端点矩阵和链路签名；不能原样作为对外结论。

待写入 \`analyze_adb_causality.py\` 输出或手工整理的聚合证据。
EOF

cat > "$case_dir/最终分析报告.md" <<EOF
# 最终分析报告

## 结论

## 日志证据

## 发生原因

## 结果/影响

## 反证与边界

## 已证实

## 已排除

## 结论边界

## 支撑数据
EOF

printf '%s\n' "$case_dir"

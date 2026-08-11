#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skills_root="$repo_root/skills"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

for skill in rc-analysis rc-internal-docs-only; do
  test -f "$skills_root/$skill/SKILL.md" || fail "missing $skill/SKILL.md"
  grep -Fq "name: $skill" "$skills_root/$skill/SKILL.md" || fail "wrong frontmatter name for $skill"
  grep -Eq '^description: Use when' "$skills_root/$skill/SKILL.md" || fail "description must start with Use when for $skill"
done

if rg -n -i \
  '(/Users/[^/[:space:]]+/|\b10\.(?:[0-9]{1,3}\.){2}[0-9]{1,3}\b|\b172\.(?:1[6-9]|2[0-9]|3[01])\.(?:[0-9]{1,3}\.)[0-9]{1,3}\b|\b192\.168\.(?:[0-9]{1,3}\.)[0-9]{1,3}\b)' \
  "$repo_root" --glob '!tests/test_public_release.sh'; then
  fail "personal paths, private-network endpoints, or production-shaped identifiers remain"
fi

ipv4_hits="$(rg -o --no-filename '\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b' "$repo_root" | sort -u || true)"
while IFS= read -r address; do
  [[ -z "$address" ]] && continue
  case "$address" in
    192.0.2.*|198.51.100.*|203.0.113.*) ;;
    *) fail "non-documentation IPv4 example remains: $address" ;;
  esac
done <<<"$ipv4_hits"

grep -Fq 'RC_INTERNAL_DOCS_DIR' "$skills_root/rc-internal-docs-only/SKILL.md" \
  || fail "RC资料 root must be configurable"

for script in "$skills_root/rc-analysis/scripts/"*.sh; do
  bash -n "$script"
done
PYTHONPYCACHEPREFIX="$tmp_dir/pycache" \
  python3 -m py_compile "$skills_root/rc-analysis/scripts/analyze_adb_causality.py"

case_dir="$(
  "$skills_root/rc-analysis/scripts/init_rc_case_dir.sh" \
    "android-arm64" "demo" "20260530-2355" "cpu-kill" "$tmp_dir"
)"

final_report="$case_dir/最终分析报告.md"
test -f "$final_report" || fail "final report template missing"

if grep -Eq '^## (推断|需补证|下一次要抓)$' "$final_report"; then
  fail "final report template contains investigation-only sections"
fi

"$skills_root/rc-analysis/scripts/selftest_rc_analysis.sh"

printf 'public release tests passed\n'

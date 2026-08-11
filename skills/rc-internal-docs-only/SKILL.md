---
name: rc-internal-docs-only
description: Use when the user explicitly asks for "RC资料", "搜RC资料", "查指定的RC资料", or requires an answer sourced only from a configured internal documentation directory.
---

# RC Internal Docs Only

## Purpose

Activate only for an explicit RC-document request, preferably `RC资料:`. Generic mentions of `rc`, `研发`, or `内部` are not enough.

The source boundary is the directory configured by the environment variable:

```bash
RC_INTERNAL_DOCS_DIR=/absolute/path/to/internal-docs
```

Do not embed a personal path in this skill. If the variable is unset or empty, answer `未配置` and ask the user to configure or provide the directory. If it is set but the path is missing, is not a directory, cannot be resolved, or is unreadable, answer `读取失败`. Do not guess a fallback path.

## Source Boundary

1. Resolve `RC_INTERNAL_DOCS_DIR` before searching.
2. Search only files whose resolved path remains under that resolved root.
3. Do not follow a symlink that escapes the root.
4. Never use web search, model memory, outside files, or external inference as evidence.
5. If the configured directory has no supporting evidence, answer `未覆盖` first.
6. Do not turn the internal corpus into a general export. Return only the minimum snippets required for the question.

The configured absolute root may itself be sensitive. In responses, cite paths relative to `RC_INTERNAL_DOCS_DIR` unless the user explicitly asks for the absolute path.

## Query Handling

1. Search exact filenames and exact terms first, then semantic keywords.
2. Merge files only when they provide complementary evidence for the same question.
3. If files conflict, show both positions and state the conflict.
4. If the request is ambiguous, ask for one filename or one keyword.
5. If evidence is absent, do not fill gaps with common knowledge.

Prefer `rg` for local search. Treat search errors, unreadable files, and an empty result as different states; do not report an access failure as `未覆盖`.

## Output Shape

1. `证据命中`: relative filenames and short supporting snippets.
2. `回答`: only claims supported by those snippets.
3. `未覆盖`: when the configured corpus has no evidence.
4. `未配置` or `读取失败`: when the source boundary cannot be established or read.

## Examples

- `RC资料: 查内部命令手册是否定义了某权限行为`
  - Search only the configured root and answer from matched files.
- No matching file exists
  - Answer `未覆盖`, then suggest a narrower filename or keyword.
- `RC_INTERNAL_DOCS_DIR` is unset
  - Answer `未配置`; do not search elsewhere.
- `RC_INTERNAL_DOCS_DIR` is set to a missing or unreadable directory
  - Answer `读取失败`; do not search elsewhere.

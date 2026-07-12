#!/usr/bin/env python3
"""Normalize indented Markdown list item indentation to 4-space levels."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path


LIST_ITEM_RE = re.compile(r"^([ \t]*)([-+*]|\d+[.)])(\s+.*)$")
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
SKIP_DIRS = {".obsidian", "附件", ".git"}


def iter_markdown_files(vault: Path) -> list[Path]:
    files: list[Path] = []
    for path in vault.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.relative_to(vault).parts):
            continue
        files.append(path)
    return sorted(files)


def normalize_lines(lines: list[str]) -> tuple[list[str], list[dict[str, object]], Counter[str]]:
    changed: list[dict[str, object]] = []
    by_indent: Counter[str] = Counter()
    out: list[str] = []
    in_fence = False
    in_frontmatter = False
    frontmatter_checked = False

    for idx, line in enumerate(lines, start=1):
        body = line[:-1] if line.endswith("\n") else line
        newline = "\n" if line.endswith("\n") else ""

        if not frontmatter_checked:
            frontmatter_checked = True
            if body == "---":
                in_frontmatter = True
                out.append(line)
                continue

        if in_frontmatter:
            out.append(line)
            if body == "---":
                in_frontmatter = False
            continue

        if FENCE_RE.match(body):
            in_fence = not in_fence
            out.append(line)
            continue

        if in_fence:
            out.append(line)
            continue

        match = LIST_ITEM_RE.match(body)
        if not match:
            out.append(line)
            continue

        indent, marker, rest = match.groups()
        width = len(indent.expandtabs(4))
        if width == 0:
            out.append(line)
            continue

        normalized_width = int(math.ceil(width / 4) * 4)
        if width == normalized_width and "\t" not in indent:
            out.append(line)
            continue

        new_body = f"{' ' * normalized_width}{marker}{rest}"
        out.append(new_body + newline)
        by_indent[f"{width}->{normalized_width}"] += 1
        changed.append(
            {
                "line": idx,
                "before": body,
                "after": new_body,
                "from": width,
                "to": normalized_width,
            }
        )

    return out, changed, by_indent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--sample-limit", type=int, default=20)
    args = parser.parse_args()

    vault = args.vault.expanduser().resolve()
    files = iter_markdown_files(vault)

    changed_files: list[dict[str, object]] = []
    total_lines = 0
    by_indent_total: Counter[str] = Counter()
    samples: list[dict[str, object]] = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        new_lines, changes, by_indent = normalize_lines(lines)
        if not changes:
            continue

        rel = str(path.relative_to(vault))
        changed_files.append({"path": rel, "changed_lines": len(changes)})
        total_lines += len(changes)
        by_indent_total.update(by_indent)
        for change in changes:
            if len(samples) >= args.sample_limit:
                break
            samples.append({"path": rel, **change})

        if args.write:
            path.write_text("".join(new_lines), encoding="utf-8")

    report = {
        "vault": str(vault),
        "mode": "write" if args.write else "dry-run",
        "files_scanned": len(files),
        "changed_files": len(changed_files),
        "changed_lines": total_lines,
        "by_indent": dict(sorted(by_indent_total.items())),
        "files": changed_files[: args.sample_limit],
        "samples": samples,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

---
name: siyuan-cli
description: Use when the user asks to search, read, create, update, import, export, inspect, or manage SiYuan content with the local `siyuan` CLI.
---

# SiYuan CLI

## Overview

Use the local `siyuan` command first for SiYuan note work. Resolve the workspace from `$SIYUAN_WORKSPACE` or ask the user for it.

Always run commands through `/bin/zsh -lc` if the shell cannot find `siyuan` or common utilities.

For create, import, organize, or routing tasks where the destination notebook/path is not explicit, read `references/notebook-structure.md` before choosing where content belongs.

## Quick Commands

Use JSON output when the result will be parsed or summarized.

```bash
siyuan -w "$SIYUAN_WORKSPACE" workspace list -f json
siyuan -w "$SIYUAN_WORKSPACE" notebook list -f json
siyuan -w "$SIYUAN_WORKSPACE" document search "关键词" -f json
siyuan -w "$SIYUAN_WORKSPACE" search "关键词" -f json --type heading --type paragraph --type listItem --page-size 3 --order-by 7
siyuan -w "$SIYUAN_WORKSPACE" block kramdown --id <block-id>
siyuan -w "$SIYUAN_WORKSPACE" export md --id <block-id> --output <output-path>/note.md
siyuan -w "$SIYUAN_WORKSPACE" import md --file <input-path> --notebook <notebook-id> --hpath "/destination"
```

## Default Search and Read Policy

For knowledge lookup, default to filtered block search:

```bash
siyuan -w "$SIYUAN_WORKSPACE" search "关键词" -f json --type heading --type paragraph --type listItem --page-size 3 --order-by 7
```

When summarizing results back to the agent, trim each candidate to the useful fields only: `id`, `rootID`, `hPath`, `type`, and `markdown` or `content`.

Prefer `NodeParagraph` or `NodeListItem` hits for exact `block kramdown` reads. Read a document root with `block kramdown` only when the user explicitly asks for the whole note/document or after a narrower candidate read is insufficient.

If candidates are too few or too thin, run a second expanded search/read step instead of reading the full root document first.

## Workflow

1. Identify the operation: search, read, export, import, create/update, or inspect.
2. Discover IDs before acting. Prefer `document search`, filtered `search`, `notebook list`, and `document get`.
3. For reading search hits, prefer exact paragraph/listItem blocks; avoid reading a document root unless the user asks for the full note or narrower reads are insufficient.
4. For exports, ask or infer an output path, then use `export md`.
5. For imports or new notes, resolve the target notebook ID and human path first. If destination is ambiguous, read `references/notebook-structure.md` and pick a destination with a one-line rationale.
6. Use `--dry-run` before large imports.
7. For destructive or mutating operations such as delete, move, update, sync, or bulk import, confirm the exact target unless the user already gave an explicit command and scope.

## Safety

- Do not use the HTTP API unless the CLI cannot do the requested task.
- Do not print secrets or unrelated workspace data.
- Do not guess notebook IDs. Query them.
- If a write command supports `--dry-run`, use it when scope is broad or ambiguous.
- If multiple destinations seem plausible, prefer asking one concise clarification question over creating a new top-level path.
- Report the human-readable path (`hPath`), block/document ID, notebook ID, and exported file path when relevant.

## Useful Follow-Ups

After finding a note, offer the next concrete action: read body, export Markdown, search inside results, create a backlink/reference view, or import related Markdown.

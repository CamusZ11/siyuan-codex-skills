# Notebook Structure Discovery

This public skill does not ship a personal notebook snapshot. Discover the live structure before choosing a destination.

## Required context

Set the workspace explicitly:

```bash
export SIYUAN_WORKSPACE="$HOME/SiYuan"
```

## Discovery commands

```bash
siyuan -w "$SIYUAN_WORKSPACE" notebook list -f json
siyuan -w "$SIYUAN_WORKSPACE" document list --notebook <notebook-id> --hpath "/candidate/path" -f json
siyuan -w "$SIYUAN_WORKSPACE" import md --file <input-path>/file.md --notebook <notebook-id> --hpath "/candidate/path" --dry-run
```

## Routing guidance

- Query notebook IDs live; never guess or reuse IDs from another workspace.
- Prefer an existing notebook and human path whose purpose matches the content.
- If two destinations are equally plausible, ask the user before writing.
- Use `--dry-run` for broad imports, then verify the imported document by reading it back.

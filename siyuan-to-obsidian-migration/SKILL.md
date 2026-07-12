---
name: siyuan-to-obsidian-migration
description: Use when migrating SiYuan notebooks to an Obsidian vault or repairing SiYuan-exported Markdown, attachments, wikilinks, embeds, and list indentation.
---

# SiYuan to Obsidian Migration

## Overview

Migrate selected SiYuan notebooks into explicitly chosen folders inside an Obsidian vault. Discover live notebook IDs, dry-run first, preserve note hierarchy, centralize assets, and verify links before writing.

## Portable configuration

- Resolve `siyuan` through `PATH` or pass `--siyuan`.
- Set the source workspace with `$SIYUAN_WORKSPACE` or `--workspace`.
- Set the destination vault with `$OBSIDIAN_VAULT` or `--vault`.
- Pass each mapping as `--notebook <notebook-id>=<target-folder>`.
- Target folders must be relative subdirectories of the vault. Absolute paths, `.`, `..`, the vault root, and paths resolving outside the vault are rejected before any deletion or write.
- Asset URLs are decoded before basename extraction. Source and destination paths must remain inside the resolved workspace asset directory and vault attachment directory; symlink escapes are rejected.

## Migration workflow

1. Confirm the source workspace and destination vault.
2. Query the live CLI for notebook IDs; never reuse IDs from another workspace.
3. Choose a relative destination folder for each source notebook.
4. Run the migration without `--write` and review the JSON plan.
5. Add `--write` only after confirming counts, target folders, references, and missing assets.
6. Use `--replace-targets` only with `--write` and only when replacing the validated mapped subdirectories is intentional.
7. Verify generated Markdown, attachments, wikilinks, YAML frontmatter, and missing targets.

Example:

```bash
python3 scripts/migrate_siyuan_to_obsidian.py \
  --workspace "$SIYUAN_WORKSPACE" \
  --vault "$OBSIDIAN_VAULT" \
  --notebook '<notebook-id>=source-notebook/target-folder'
```

## General conversion rules

- Preserve the source document hierarchy under each selected target folder.
- Treat a source note with child documents as a folder; retain its own body as a Markdown file inside that folder.
- Store exported assets in the vault-level attachment folder used by the migration script.
- Keep asset embeds as embeds.
- Convert full-note embeds to plain wikilinks; retain heading and block embeds as previews.
- Quote YAML titles when their leading characters require quoting.
- Sanitize filename characters that are unsafe in Obsidian paths.

## Bundled scripts

- `scripts/migrate_siyuan_to_obsidian.py`: dry-run-by-default migration helper; writing requires `--write`.
- `scripts/convert_full_note_embeds_to_links.py`: converts full-note embeds to links while preserving asset and partial embeds.
- `scripts/normalize_markdown_list_indentation.py`: normalizes Markdown list indentation while skipping frontmatter and fenced code blocks.
- `scripts/path_safety.py`: shared containment validation used by migration and repair CLIs.

Run `python3 <script> --help` for current arguments.

## Validation

After migration:

- Confirm every generated path is inside the destination vault.
- Confirm full-note embeds that should be links are gone.
- Confirm asset and partial embeds remain intact.
- Confirm missing assets are reported rather than silently invented.
- Parse frontmatter and inspect representative nested documents.

## Safety

- Dry-run before every broad migration or repair.
- Do not guess notebook IDs or destination paths.
- Do not pass the vault root as a notebook target.
- Do not use `--replace-targets` unless the exact validated subdirectories may be removed.
- Do not delete source notebooks, unrelated vault folders, or backups.

#!/usr/bin/env python3
from pathlib import Path
import argparse
import os
import re

from path_safety import resolve_subdirectory


EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
PLAIN_LINK_RE = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")
FOOTNOTE_RE = re.compile(r"\[\^[0-9]+\]|^\[\^[0-9]+\]:")
ASSET_EXT_RE = re.compile(
    r"\.(png|jpe?g|gif|webp|svg|pdf|mp3|mp4|mov|m4a|wav|aac|flac|ogg|webm)$",
    re.IGNORECASE,
)


def is_asset_or_partial_embed(target: str) -> bool:
    link = target.split("|", 1)[0]
    if link.startswith("附件/"):
        return True
    if "#" in link:
        return True
    return bool(ASSET_EXT_RE.search(link))


def convert_text(text: str) -> tuple[str, int]:
    converted = []
    changed = 0
    in_fence = False

    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            converted.append(line)
            continue
        if in_fence:
            converted.append(line)
            continue

        def replace(match: re.Match[str]) -> str:
            nonlocal changed
            target = match.group(1)
            if is_asset_or_partial_embed(target):
                return match.group(0)
            changed += 1
            return f"[[{target}]]"

        converted.append(EMBED_RE.sub(replace, line))

    return "".join(converted), changed


def resolve_notebook_dirs(vault: Path, notebooks: list[str]) -> list[Path]:
    return [resolve_subdirectory(vault, notebook, "notebook directory") for notebook in notebooks]


def audit(notebook_dirs: list[Path]) -> dict[str, int]:
    stats = {
        "full_note_embeds": 0,
        "asset_embeds": 0,
        "partial_embeds": 0,
        "plain_note_links": 0,
        "footnote_residuals": 0,
    }

    for root in notebook_dirs:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if FOOTNOTE_RE.search(line):
                    stats["footnote_residuals"] += 1
            for match in EMBED_RE.finditer(text):
                target = match.group(1)
                base = target.split("|", 1)[0]
                if is_asset_or_partial_embed(target):
                    if base.startswith("附件/") or ASSET_EXT_RE.search(base):
                        stats["asset_embeds"] += 1
                    else:
                        stats["partial_embeds"] += 1
                else:
                    stats["full_note_embeds"] += 1
            for match in PLAIN_LINK_RE.finditer(text):
                target = match.group(1)
                if not is_asset_or_partial_embed(target):
                    stats["plain_note_links"] += 1

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Obsidian full-note embeds to plain wikilinks while preserving assets and heading/block embeds."
    )
    parser.add_argument("--vault", default=str(Path(os.environ.get("OBSIDIAN_VAULT", Path.home() / "ObsidianVault"))))
    parser.add_argument("--notebook", action="append", dest="notebooks", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    vault = Path(args.vault)
    notebooks = args.notebooks
    try:
        notebook_dirs = resolve_notebook_dirs(vault, notebooks)
    except ValueError as error:
        parser.error(str(error))

    touched_files = 0
    converted_refs = 0
    samples: list[str] = []

    for root in notebook_dirs:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            new_text, changed = convert_text(text)
            if changed == 0:
                continue
            touched_files += 1
            converted_refs += changed
            if len(samples) < 20:
                samples.append(f"{path.relative_to(vault)}: {changed}")
            if args.write:
                path.write_text(new_text, encoding="utf-8")

    stats = audit(notebook_dirs)
    print(f"write={args.write}")
    print(f"touched_files={touched_files}")
    print(f"converted_full_note_embeds={converted_refs}")
    print(f"full_note_embeds={stats['full_note_embeds']}")
    print(f"asset_embeds={stats['asset_embeds']}")
    print(f"partial_embeds={stats['partial_embeds']}")
    print(f"plain_note_links={stats['plain_note_links']}")
    print(f"footnote_residuals={stats['footnote_residuals']}")
    if samples:
        print("samples:")
        for sample in samples:
            print(sample)


if __name__ == "__main__":
    main()

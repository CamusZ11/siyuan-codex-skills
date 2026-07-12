#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from path_safety import resolve_asset_paths, resolve_subdirectory, safe_asset_filename

SIYUAN = shutil.which("siyuan") or "siyuan"
WORKSPACE = Path(os.environ.get("SIYUAN_WORKSPACE", Path.home() / "SiYuan"))
VAULT = Path(os.environ.get("OBSIDIAN_VAULT", Path.home() / "ObsidianVault"))
ATTACHMENTS = VAULT / "附件"
NOTEBOOKS: list[tuple[str, str]] = []


def notebook_arg(value: str) -> tuple[str, str]:
    notebook_id, separator, notebook_name = value.partition("=")
    if not separator or not notebook_id or not notebook_name:
        raise argparse.ArgumentTypeError("expected <notebook-id>=<target-folder>")
    return notebook_id, notebook_name


@dataclass
class Doc:
    notebook_id: str
    notebook_name: str
    id: str
    name: str
    path: str
    sub_file_count: int
    children: list["Doc"] = field(default_factory=list)
    raw_markdown: str = ""
    markdown: str = ""
    has_body: bool = False
    target_file: Optional[Path] = None
    target_dir: Optional[Path] = None


def run_json(args):
    proc = subprocess.run(args, text=True, capture_output=True, check=True)
    return json.loads(proc.stdout)


def run_text(args):
    proc = subprocess.run(args, text=True, capture_output=True, check=True)
    return proc.stdout


def list_docs(notebook_id, path="/"):
    return run_json([
        SIYUAN,
        "-w",
        str(WORKSPACE),
        "document",
        "list",
        "--notebook",
        notebook_id,
        "--path",
        path,
        "-f",
        "json",
    ])


def build_tree(notebook_id, notebook_name, path="/"):
    docs = []
    for item in list_docs(notebook_id, path):
        doc = Doc(
            notebook_id=notebook_id,
            notebook_name=notebook_name,
            id=item["id"],
            name=item["name"],
            path=item["path"],
            sub_file_count=int(item.get("subFileCount", 0)),
        )
        if doc.sub_file_count:
            doc.children = build_tree(notebook_id, notebook_name, doc.path)
        docs.append(doc)
    return docs


def walk(docs):
    for doc in docs:
        yield doc
        yield from walk(doc.children)


def sanitize_name(name):
    cleaned = re.sub(r"[/:\\]", "／", name).strip()
    cleaned = (
        cleaned
        .replace("#", "＃")
        .replace("^", "＾")
        .replace("|", "｜")
        .replace("[", "［")
        .replace("]", "］")
    )
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "未命名"


def unique_name(name, used, doc_id):
    if name not in used:
        used.add(name)
        return name
    suffix = doc_id[-7:]
    candidate = f"{name} - {suffix}"
    counter = 2
    while candidate in used:
        candidate = f"{name} - {suffix}-{counter}"
        counter += 1
    used.add(candidate)
    return candidate


def quote_yaml_title(markdown):
    if not markdown.startswith("---\n"):
        return markdown
    end = markdown.find("\n---\n", 4)
    if end == -1:
        return markdown
    lines = markdown[4:end].splitlines()
    changed = False
    new_lines = []
    for line in lines:
        if line.startswith("title: "):
            raw = line[len("title: "):].strip()
            if not (raw.startswith('"') and raw.endswith('"')):
                line = "title: " + json.dumps(raw, ensure_ascii=False)
                changed = True
        new_lines.append(line)
    if not changed:
        return markdown
    return "---\n" + "\n".join(new_lines) + "\n---\n" + markdown[end + 5:]


def body_has_content(markdown):
    text = markdown.strip()
    if not text:
        return False
    text = re.sub(r"(?s)^---\n.*?\n---\n?", "", text).strip()
    text = re.sub(r"^# .+?\n+", "", text, count=1).strip()
    text = re.sub(r"(?m)^\{:[^}]+\}\s*$", "", text).strip()
    return bool(text)


ASSET_LINK_RE = re.compile(r"!\[([^\]]*)\]\((assets/[^)\s]+)(?:\s+\"[^\"]*\")?\)")


def rewrite_assets(markdown, used_assets):
    def repl(match):
        filename = safe_asset_filename(match.group(2))
        used_assets.add(filename)
        return f"![[附件/{filename}]]"

    return ASSET_LINK_RE.sub(repl, markdown)


def export_all(docs):
    for doc in walk(docs):
        doc.raw_markdown = run_text([SIYUAN, "-w", str(WORKSPACE), "export", "md", "--id", doc.id])
        doc.markdown = quote_yaml_title(doc.raw_markdown)
        doc.has_body = body_has_content(doc.markdown)


def plan_paths(docs, out_dir, reserved_files=None):
    used_dirs = set()
    used_files = set(reserved_files or [])
    for doc in docs:
        base_name = sanitize_name(doc.name)
        if doc.children:
            safe_dir = unique_name(base_name, used_dirs, doc.id)
            doc.target_dir = out_dir / safe_dir
            if doc.has_body:
                doc.target_file = doc.target_dir / f"{safe_dir}.md"
            child_reserved = {safe_dir} if doc.has_body else set()
            plan_paths(doc.children, doc.target_dir, child_reserved)
        else:
            safe_file = unique_name(base_name, used_files, doc.id)
            doc.target_file = out_dir / f"{safe_file}.md"


def vault_link(path):
    return str(path.relative_to(VAULT).with_suffix(""))


def build_title_index(all_docs):
    index = {}
    for doc in all_docs:
        if doc.target_file:
            index.setdefault(doc.name.strip(), []).append(doc.target_file)
            index.setdefault(sanitize_name(doc.name), []).append(doc.target_file)
    return index


def strip_markup_title(line):
    title = line.strip()
    title = re.sub(r"^#{1,6}\s+", "", title).strip()
    title = re.sub(r"^=+|=+$", "", title).strip()
    title = re.sub(r"^\*\*|\*\*$", "", title).strip()
    title = re.sub(r"^@(?=\S)", "@", title).strip()
    if "：" in title and len(title.split("：", 1)[0]) <= 24:
        return title.split("：", 1)[0].strip()
    if ":" in title and len(title.split(":", 1)[0]) <= 24:
        return title.split(":", 1)[0].strip()
    return title[:48].strip()


def parse_reference_footnotes(markdown):
    pattern = re.compile(r"(?ms)^\[\^(\d+)\]:\s*(.+?)\n(.*?)(?=^\[\^\d+\]:\s*|\Z)")
    refs = {}
    spans = []
    for match in pattern.finditer(markdown):
        num = match.group(1)
        first = match.group(2).rstrip()
        body = match.group(3)
        lines = []
        for line in body.splitlines():
            if line.startswith("    "):
                line = line[4:]
            lines.append(line.rstrip())
        body_text = "\n".join(lines).strip()
        refs[num] = {
            "first": first,
            "title": strip_markup_title(first),
            "body": body_text,
        }
        spans.append(match.span())
    return refs, spans


def remove_spans(text, spans):
    if not spans:
        return text
    out = []
    last = 0
    for start, end in spans:
        out.append(text[last:start])
        last = end
    out.append(text[last:])
    return "".join(out).rstrip() + "\n"


def choose_existing_target(title, source_doc, title_index):
    candidates = title_index.get(title) or title_index.get(sanitize_name(title)) or []
    if not candidates:
        return None
    source_parent = source_doc.target_file.parent if source_doc.target_file else None
    same_parent = [p for p in candidates if source_parent and p.parent == source_parent]
    if len(same_parent) == 1:
        return same_parent[0]
    if len(candidates) == 1:
        return candidates[0]
    return None


def reference_note_name(title, used):
    base = sanitize_name(title)
    if not base:
        base = "引用"
    name = base
    counter = 2
    while name in used:
        name = f"{base} - 引用{counter}"
        counter += 1
    used.add(name)
    return name


def replace_ref_markers(text, ref_links, ref_titles=None):
    ref_titles = ref_titles or {}
    for num, link in sorted(ref_links.items(), key=lambda x: -len(x[0])):
        title = ref_titles.get(num)
        if title:
            text = re.sub(re.escape(title) + r"\[\^" + re.escape(num) + r"\]", link, text)
        text = re.sub(r"\[\^" + re.escape(num) + r"\]", link, text)
    return text


ORPHAN_REF_RE = re.compile(r"(?P<label>[^\n\[\]\|]{1,80}?)\[\^\d+\]")


def strip_label_for_orphan(label):
    label = label.strip()
    label = re.sub(r"^[#>\-\*\s]+", "", label).strip()
    label = label.strip("：:，,。；;、|")
    return strip_markup_title(label)


def replace_orphan_ref_markers(text, title_index, source_doc=None, generated_refs=None):
    def repl(match):
        label = strip_label_for_orphan(match.group("label"))
        if not label:
            return match.group(0)
        candidates = title_index.get(label) or title_index.get(sanitize_name(label)) or []
        if len(candidates) == 1:
            target = vault_link(candidates[0])
        elif source_doc and generated_refs is not None and source_doc.target_file:
            folder = source_doc.target_file.parent
            used = generated_refs.setdefault(folder, set())
            orphan_maps = generated_refs.setdefault("__orphan_maps__", {})
            folder_map = orphan_maps.setdefault(folder, {})
            if label in folder_map:
                target_path = folder_map[label]
            else:
                local_name = reference_note_name(label, used)
                target_path = folder / f"{local_name}.md"
                front = "---\n" + "title: " + json.dumps(local_name, ensure_ascii=False) + "\n---\n\n"
                generated_refs[folder, local_name] = front
                folder_map[label] = target_path
            target = vault_link(target_path)
        else:
            target = label
        return f"![[{target}]]"

    return ORPHAN_REF_RE.sub(repl, text)


def process_references(doc, title_index, generated_refs):
    refs, spans = parse_reference_footnotes(doc.markdown)
    if not refs:
        return replace_orphan_ref_markers(doc.markdown, title_index, doc, generated_refs), 0
    body = remove_spans(doc.markdown, spans)
    ref_links = {}
    ref_titles = {}
    used_generated = generated_refs.setdefault(doc.target_file.parent, set())
    planned_generated = {}
    for num, ref in refs.items():
        target = choose_existing_target(ref["title"], doc, title_index)
        if target is None:
            local_name = reference_note_name(ref["title"], used_generated)
            target = doc.target_file.parent / f"{local_name}.md"
            planned_generated[num] = (target, local_name, ref["body"].strip())
        ref_links[num] = f"![[{vault_link(target)}]]"
        ref_titles[num] = ref["title"]
    for num, (target, local_name, content) in planned_generated.items():
        content = replace_ref_markers(content, ref_links, ref_titles)
        content = replace_orphan_ref_markers(content, title_index, doc, generated_refs)
        front = "---\n" + "title: " + json.dumps(local_name, ensure_ascii=False) + "\n---\n\n"
        generated_refs[doc.target_file.parent, local_name] = front + content + "\n"
    body = replace_ref_markers(body, ref_links, ref_titles)
    body = replace_orphan_ref_markers(body, title_index, doc, generated_refs)
    return body, len(refs)


def copy_asset(filename, dry_run):
    src, dst, _ = resolve_asset_paths(WORKSPACE, VAULT, filename, ATTACHMENTS.name)
    if not src.exists():
        return False
    if dry_run:
        return True
    ATTACHMENTS.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copy2(src, dst)
    return True


def write_text(path, text, write):
    if not write:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main():
    global SIYUAN, WORKSPACE, VAULT, ATTACHMENTS, NOTEBOOKS
    parser = argparse.ArgumentParser()
    parser.add_argument("--siyuan", default=SIYUAN, help="SiYuan CLI executable (resolved through PATH by default).")
    parser.add_argument("--workspace", default=str(WORKSPACE))
    parser.add_argument("--vault", default=str(VAULT))
    parser.add_argument(
        "--notebook",
        action="append",
        type=notebook_arg,
        required=True,
        metavar="ID=TARGET_FOLDER",
        help="Notebook ID and target folder; repeat for each notebook.",
    )
    parser.add_argument("--write", action="store_true", help="Write migrated files; omitted means dry-run.")
    parser.add_argument("--replace-targets", action="store_true")
    args = parser.parse_args()

    SIYUAN = args.siyuan
    WORKSPACE = Path(args.workspace)
    VAULT = Path(args.vault)
    ATTACHMENTS = VAULT / "附件"
    NOTEBOOKS = args.notebook

    try:
        target_dirs = {
            name: resolve_subdirectory(VAULT, name, "notebook target")
            for _, name in NOTEBOOKS
        }
    except ValueError as error:
        parser.error(str(error))

    roots = []
    for notebook_id, notebook_name in NOTEBOOKS:
        docs = build_tree(notebook_id, notebook_name)
        export_all(docs)
        plan_paths(docs, target_dirs[notebook_name])
        roots.extend(docs)

    all_docs = list(walk(roots))
    title_index = build_title_index(all_docs)
    stats = {
        "vault": str(VAULT),
        "notebooks": [name for _, name in NOTEBOOKS],
        "documents_seen": len(all_docs),
        "markdown_notes": 0,
        "folders": 0,
        "reference_embeds": 0,
        "generated_reference_notes": 0,
        "asset_refs": 0,
        "assets_copied_or_existing": 0,
        "assets_missing": [],
        "dry_run": not args.write,
    }

    generated_refs = {}
    rendered = {}
    for doc in all_docs:
        if doc.target_dir:
            stats["folders"] += 1
        if not doc.target_file:
            continue
        used_assets = set()
        text = rewrite_assets(doc.markdown, used_assets)
        doc.markdown = text
        text, ref_count = process_references(doc, title_index, generated_refs)
        rendered[doc.target_file] = text
        stats["markdown_notes"] += 1
        stats["reference_embeds"] += ref_count
        stats["asset_refs"] += len(used_assets)
        for filename in used_assets:
            if copy_asset(filename, not args.write):
                stats["assets_copied_or_existing"] += 1
            else:
                stats["assets_missing"].append(filename)

    for key, content in list(generated_refs.items()):
        if isinstance(key, tuple):
            folder, local_name = key
            rendered[folder / f"{local_name}.md"] = content
            stats["generated_reference_notes"] += 1

    if args.write:
        if args.replace_targets:
            for target in target_dirs.values():
                if target.exists():
                    shutil.rmtree(target)
        for target in target_dirs.values():
            target.mkdir(parents=True, exist_ok=True)
        ATTACHMENTS.mkdir(parents=True, exist_ok=True)
        for path, text in rendered.items():
            write_text(path, text, args.write)

    stats["total_markdown_files"] = len(rendered)
    stats["assets_missing"] = sorted(set(stats["assets_missing"]))
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

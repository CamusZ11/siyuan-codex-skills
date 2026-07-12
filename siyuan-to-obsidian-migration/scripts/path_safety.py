from pathlib import Path, PurePosixPath
from urllib.parse import unquote


def resolve_subdirectory(root: Path, relative_path: str, label: str = "path") -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or relative_path in {"", ".", ".."}:
        raise ValueError(f"{label} must be a non-root relative path: {relative_path!r}")
    if any(part in {".", ".."} for part in relative.parts):
        raise ValueError(f"{label} cannot contain '.' or '..': {relative_path!r}")

    root_path = root.expanduser().resolve()
    target = (root_path / relative).resolve()
    if target == root_path or root_path not in target.parents:
        raise ValueError(f"{label} must resolve inside its root: {relative_path!r}")
    return target


def safe_asset_filename(raw_asset_path: str) -> str:
    decoded = unquote(raw_asset_path).replace("\\", "/")
    filename = PurePosixPath(decoded).name
    if filename in {"", ".", ".."}:
        raise ValueError(f"invalid asset filename: {raw_asset_path!r}")
    return filename


def resolve_asset_paths(
    workspace: Path,
    vault: Path,
    raw_asset_path: str,
    attachment_directory: str,
) -> tuple[Path, Path, str]:
    workspace_root = workspace.expanduser().resolve()
    assets_root = (workspace_root / "data" / "assets").resolve()
    if workspace_root not in assets_root.parents:
        raise ValueError("workspace asset directory resolves outside the workspace")

    vault_root = vault.expanduser().resolve()
    attachments_root = resolve_subdirectory(vault_root, attachment_directory, "attachment directory")
    filename = safe_asset_filename(raw_asset_path)

    source = (assets_root / filename).resolve()
    destination = (attachments_root / filename).resolve()
    if assets_root not in source.parents:
        raise ValueError(f"asset source resolves outside the asset directory: {raw_asset_path!r}")
    if attachments_root not in destination.parents:
        raise ValueError(f"asset destination resolves outside the attachment directory: {raw_asset_path!r}")
    return source, destination, filename

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

MANIFEST_NAME = "PACKAGE_SHA256_MANIFEST.txt"


def _payload_files(root: Path, manifest_name: str = MANIFEST_NAME) -> tuple[Path, ...]:
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.relative_to(root).as_posix() != manifest_name
    ]
    return tuple(sorted(files, key=lambda path: path.relative_to(root).as_posix()))


def build_manifest(root: str | Path, manifest_name: str = MANIFEST_NAME) -> Path:
    """Generate the package manifest only from the final transported file set."""
    root_path = Path(root)
    if not root_path.is_dir():
        raise ValueError("package_root_required")
    manifest_path = root_path / manifest_name
    lines: list[str] = []
    for path in _payload_files(root_path, manifest_name):
        relative = path.relative_to(root_path).as_posix()
        digest = sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {relative}")
    manifest_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    verify_manifest(root_path, manifest_name)
    return manifest_path


def verify_manifest(root: str | Path, manifest_name: str = MANIFEST_NAME) -> None:
    root_path = Path(root)
    manifest_path = root_path / manifest_name
    if not manifest_path.is_file():
        raise ValueError("package_manifest_missing")

    declared: dict[str, str] = {}
    for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            digest, relative = line.split(None, 1)
        except ValueError as exc:
            raise ValueError("package_manifest_line_invalid") from exc
        relative = relative.strip()
        if relative in declared:
            raise ValueError("package_manifest_duplicate_path")
        declared[relative] = digest

    actual = {
        path.relative_to(root_path).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in _payload_files(root_path, manifest_name)
    }
    missing = sorted(set(declared) - set(actual))
    extra = sorted(set(actual) - set(declared))
    mismatched = sorted(
        path for path in set(actual) & set(declared) if actual[path] != declared[path]
    )
    if missing:
        raise ValueError(f"package_manifest_missing_files:{','.join(missing)}")
    if extra:
        raise ValueError(f"package_manifest_unlisted_files:{','.join(extra)}")
    if mismatched:
        raise ValueError(f"package_manifest_digest_mismatch:{','.join(mismatched)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        verify_manifest(args.root)
    else:
        build_manifest(args.root)

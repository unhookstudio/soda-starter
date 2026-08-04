"""Rename the starter's Python package and public project identifiers."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

SOURCE_PACKAGE = "DjangoApiStarter"
SOURCE_DISTRIBUTION = "soda-starter"
SOURCE_DISPLAY_NAMES = ("Somewhat Opinionated Django API Starter", "SODA Starter")
EXCLUDED_DIRECTORIES = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".test_media",
    ".venv",
    "__pycache__",
    "node_modules",
}
EXCLUDED_FILES = {
    Path("LICENSE"),
    Path("docs/adoption.md"),
    Path("docs/public-release-checklist.md"),
    Path("scripts/rename_project.py"),
    Path("scripts/tests/test_rename_project.py"),
}
PACKAGE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
DIST_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_names(package: str, distribution: str, display_name: str) -> None:
    if not PACKAGE_NAME_PATTERN.fullmatch(package):
        raise ValueError(
            "Package name must be lower-case snake_case and a valid Python identifier."
        )
    if not DIST_NAME_PATTERN.fullmatch(distribution):
        raise ValueError("Distribution name must be a lower-case hyphenated name.")
    if not display_name.strip():
        raise ValueError("Display name cannot be empty.")


def candidate_text_files(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(root)
        if relative_path in EXCLUDED_FILES:
            continue
        if any(part in EXCLUDED_DIRECTORIES for part in relative_path.parts):
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError, OSError:
            continue
        candidates.append(path)
    return candidates


def rename_project(
    root: Path,
    *,
    package: str,
    distribution: str,
    display_name: str,
    dry_run: bool = False,
) -> list[Path]:
    root = root.resolve()
    source_directory = root / SOURCE_PACKAGE
    target_directory = root / package
    validate_names(package, distribution, display_name)
    if not source_directory.is_dir():
        raise ValueError(f"Expected starter package at {source_directory}")
    if target_directory.exists():
        raise ValueError(f"Target package already exists: {target_directory}")

    replacements = (
        (SOURCE_DISTRIBUTION, distribution),
        *((source, display_name) for source in SOURCE_DISPLAY_NAMES),
        (SOURCE_PACKAGE, package),
    )
    changes: list[tuple[Path, str]] = []
    for path in candidate_text_files(root):
        original = path.read_text(encoding="utf-8")
        updated = original
        for source, target in replacements:
            updated = updated.replace(source, target)
        if updated != original:
            changes.append((path, updated))

    if dry_run:
        return [path for path, _content in changes]

    for path, content in changes:
        path.write_text(content, encoding="utf-8")
    source_directory.rename(target_directory)
    return [path for path, _content in changes]


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("package", help="Python package, e.g. gallery_tours")
    argument_parser.add_argument(
        "--distribution",
        help="Package/repository name; defaults to the package with hyphens",
    )
    argument_parser.add_argument(
        "--display-name",
        help="Human-readable project name; defaults to title-cased package words",
    )
    argument_parser.add_argument("--dry-run", action="store_true")
    return argument_parser


def main() -> None:
    args = parser().parse_args()
    distribution = args.distribution or args.package.replace("_", "-")
    display_name = args.display_name or args.package.replace("_", " ").title()
    try:
        changed = rename_project(
            Path.cwd(),
            package=args.package,
            distribution=distribution,
            display_name=display_name,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    action = "Would update" if args.dry_run else "Updated"
    print(f"{action} {len(changed)} files.")
    if not args.dry_run:
        print(f"Renamed {SOURCE_PACKAGE}/ to {args.package}/.")


if __name__ == "__main__":
    main()

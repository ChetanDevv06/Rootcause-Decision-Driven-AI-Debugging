from pathlib import Path

DEPENDENCY_FILES = (
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
)


def inspect_dependencies(project_path: str) -> dict:
    """Read common Python dependency files without modifying them."""
    root = Path(project_path).resolve()

    if not root.is_dir():
        return {
            "action": "inspect_dependencies",
            "error": "Project path is not a directory.",
        }

    found = {}

    for filename in DEPENDENCY_FILES:
        file_path = root / filename

        if file_path.is_file():
            try:
                found[filename] = file_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )[:12000]
            except OSError as exc:
                found[filename] = f"Could not read file: {exc}"

    return {
        "action": "inspect_dependencies",
        "project_path": str(root),
        "files_found": found,
        "evidence": (
            "Dependency files were inspected."
            if found
            else "No supported dependency files were found."
        ),
    }
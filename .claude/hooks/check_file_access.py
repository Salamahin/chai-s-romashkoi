#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


TOOL_PATH_KEYS: dict[str, str] = {
    "Read": "file_path",
    "Edit": "file_path",
    "Write": "file_path",
    "Grep": "path",
    "Glob": "path",
}

ALLOWED_PREFIXES: tuple[Path, ...] = (
    Path.home() / ".claude",
)


def _is_subpath(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def is_allowlisted(resolved: Path) -> bool:
    return any(_is_subpath(resolved, p.resolve()) for p in ALLOWED_PREFIXES)


def is_outside_root(resolved: Path, root: Path) -> bool:
    return not _is_subpath(resolved, root)


def is_gitignored(path_str: str) -> bool:
    result = subprocess.run(["git", "check-ignore", "-q", path_str], capture_output=True)
    return result.returncode == 0


def read_project_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip()).resolve()
    return Path.cwd().resolve()


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(2)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    path_key = TOOL_PATH_KEYS.get(tool_name)
    if not path_key:
        sys.exit(0)

    path_str: str = payload.get("tool_input", {}).get(path_key, "")
    if not path_str:
        sys.exit(0)

    resolved = Path(path_str).resolve()

    if is_allowlisted(resolved):
        sys.exit(0)

    root = read_project_root()

    if is_outside_root(resolved, root):
        deny(
            f"Access denied: '{path_str}' is outside the project root '{root}'. "
            "Do not read, write, or search files outside the project directory."
        )

    if is_gitignored(path_str):
        deny(
            f"Access denied: '{path_str}' matches a .gitignore pattern. "
            "Do not read, write, or search gitignored files."
        )


if __name__ == "__main__":
    main()

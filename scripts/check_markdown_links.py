#!/usr/bin/env python3
"""Check local Markdown links without accessing the network."""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
OPENING_FENCE_RE = re.compile(r"^ {0,3}(?P<marker>`{3,}|~{3,})(?P<info>[^\r\n]*)")


def without_fenced_code(text: str) -> str:
    """Return Markdown content that can contain navigable document links."""
    visible: list[str] = []
    fence_character: str | None = None
    fence_length = 0

    for line in text.splitlines(keepends=True):
        if fence_character is None:
            opening = OPENING_FENCE_RE.match(line)
            if opening and not (opening.group("marker").startswith("`") and "`" in opening.group("info")):
                marker = opening.group("marker")
                fence_character = marker[0]
                fence_length = len(marker)
                continue
            visible.append(line)
            continue

        stripped = line.lstrip(" ")
        indentation = len(line) - len(stripped)
        run_length = len(stripped) - len(stripped.lstrip(fence_character))
        if indentation <= 3 and run_length >= fence_length and not stripped[run_length:].strip():
            fence_character = None
            fence_length = 0

    return "".join(visible)


def main() -> int:
    errors: list[str] = []
    checked = 0
    result = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard", "-z"], check=True, capture_output=True)
    paths = [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item.endswith(b".md")]
    for path in sorted(paths):
        if path.is_symlink() or not path.is_file():
            errors.append(f"{path.relative_to(ROOT)}: symlink or missing Markdown file")
            continue
        text = without_fenced_code(path.read_text(encoding="utf-8"))
        for target in LINK_RE.findall(text):
            clean = target.strip().split()[0].strip("<>")
            if clean.startswith(("http://", "https://", "mailto:", "#")):
                continue
            destination = unquote(clean.split("#", 1)[0])
            if not destination:
                continue
            checked += 1
            resolved = (path.parent / destination).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"{path.relative_to(ROOT)}: link escapes repository: {destination}")
                continue
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}: missing target: {destination}")
    if errors:
        print("Markdown link check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Markdown local-link check passed ({checked} links).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

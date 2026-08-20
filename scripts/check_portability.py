#!/usr/bin/env python3
"""Check that the published skill has no machine-specific paths and is complete."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".json", ".txt"}
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]")
USER_HOME_PATH = re.compile(r"(?<![A-Za-z0-9_])/(?:Users|home)/[^/\s`\"']+")
REQUIRED_PATHS = (
    "SKILL.md",
    "agents/openai.yaml",
    "assets/customer-content-template.md",
    "assets/input-packet-template.md",
    "assets/visual-ai-handoff-template.md",
    "references/input-contract.md",
    "references/evidence-policy.md",
    "references/quality-gates.md",
    "references/outline-cards/manifest.json",
    "scripts/validate_outline_library.py",
    "scripts/validate_content_package.py",
    "scripts/freeze_content_package.py",
)


def iter_text_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
        and path.suffix.lower() in TEXT_SUFFIXES
    )


def main() -> int:
    errors: list[str] = []
    scanned = 0

    for relative in REQUIRED_PATHS:
        if not (ROOT / relative).is_file():
            errors.append(f"缺少发布必需文件：{relative}")

    for path in iter_text_files():
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"不是UTF-8文本：{path.relative_to(ROOT).as_posix()}")
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if WINDOWS_ABSOLUTE_PATH.search(line) or USER_HOME_PATH.search(line):
                errors.append(
                    f"机器相关绝对路径：{path.relative_to(ROOT).as_posix()}:{line_number}"
                )

    result = {
        "status": "passed" if not errors else "failed",
        "files_scanned": scanned,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""voicepaths: parse a repo's .voicepaths declaration and match files against it."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _glob_to_re(glob: str) -> re.Pattern:
    out, i = [], 0
    while i < len(glob):
        c = glob[i]
        if glob[i : i + 3] == "**/":
            out.append("(?:.+/)?")
            i += 3
        elif glob[i : i + 2] == "**":
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def load(root: str | Path) -> dict:
    p = Path(root) / ".voicepaths"
    cfg = {"register": None, "style": None, "globs": [], "patterns": []}
    if not p.is_file():
        return cfg

    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line and not any(
            ch in line.split(":", 1)[0] for ch in "*/?."
        ):
            key, val = (s.strip() for s in line.split(":", 1))
            if key in ("register", "style"):
                cfg[key] = val
                continue
        cfg["globs"].append(line)
        cfg["patterns"].append(_glob_to_re(line))
    return cfg


def match(root: str | Path, path: str | Path) -> bool:
    cfg = load(root)
    try:
        rel = Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return False
    return any(pattern.match(rel) for pattern in cfg["patterns"])


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[0] != "match":
        print("usage: voicepaths.py match <root> <path>...", file=sys.stderr)
        return 2

    root, hits = argv[1], []
    for path in argv[2:]:
        if match(root, path):
            hits.append(path)
            print(path)
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

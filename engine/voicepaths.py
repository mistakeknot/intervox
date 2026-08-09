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
    cfg = {"register": None, "style": None, "globs": [], "patterns": [], "layers": []}
    if not p.is_file():
        return cfg

    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # "rules-only: <glob>" declares a path that gets the rules layer
        # (Vale) but not the stylometric layer — governance docs that quote
        # the anti-patterns they ban, README files, page templates. Must be
        # recognized before the key check: "rules-only" has no glob chars
        # and would otherwise read as an unknown key.
        layer = "full"
        if line.startswith("rules-only:"):
            layer = "rules"
            line = line.split(":", 1)[1].strip()
            if not line:
                continue
        elif ":" in line and not any(
            ch in line.split(":", 1)[0] for ch in "*/?."
        ):
            key, val = (s.strip() for s in line.split(":", 1))
            if key in ("register", "style"):
                cfg[key] = val
                continue
        cfg["globs"].append(line)
        cfg["patterns"].append(_glob_to_re(line))
        cfg["layers"].append(layer)
    return cfg


def _rel_to(root: str | Path, path: str | Path) -> str | None:
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return None


def match(root: str | Path, path: str | Path) -> bool:
    cfg = load(root)
    rel = _rel_to(root, path)
    if rel is None:
        return False
    return any(pattern.match(rel) for pattern in cfg["patterns"])


def match_layer(root: str | Path, path: str | Path) -> str | None:
    """Return the strongest layer declared for a path: "full" beats "rules",
    None means undeclared."""
    cfg = load(root)
    rel = _rel_to(root, path)
    if rel is None:
        return None
    best = None
    for pattern, layer in zip(cfg["patterns"], cfg["layers"]):
        if pattern.match(rel):
            if layer == "full":
                return "full"
            best = "rules"
    return best


def main(argv: list[str]) -> int:
    layer_filter = None
    if argv and argv[0] == "match" and len(argv) > 1 and argv[1] == "--layer=full":
        layer_filter = "full"
        argv = [argv[0]] + argv[2:]
    if len(argv) < 3 or argv[0] != "match":
        print("usage: voicepaths.py match [--layer=full] <root> <path>...", file=sys.stderr)
        return 2

    root, hits = argv[1], []
    for path in argv[2:]:
        layer = match_layer(root, path)
        if layer is None:
            continue
        if layer_filter and layer != layer_filter:
            continue
        hits.append(path)
        print(path)
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

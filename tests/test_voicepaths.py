#!/usr/bin/env python3
"""Tests for .voicepaths declaration parsing and path matching."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"
VOICEPATHS_CLI = ENGINE_DIR / "voicepaths.py"

sys.path.insert(0, str(ENGINE_DIR))
import voicepaths  # noqa: E402


@pytest.fixture
def declared_repo(tmp_path: Path) -> Path:
    (tmp_path / ".voicepaths").write_text(
        """\
# .voicepaths -- declared voice-carrying paths
register: gsv-site
style: GSV
src/content/**/*.md
src/pages/**/*.astro
""",
        encoding="utf-8",
    )
    return tmp_path


def test_load_parses_metadata_and_globs(declared_repo: Path) -> None:
    config = voicepaths.load(declared_repo)

    assert config["register"] == "gsv-site"
    assert config["style"] == "GSV"
    assert config["globs"] == [
        "src/content/**/*.md",
        "src/pages/**/*.astro",
    ]
    assert len(config["patterns"]) == 2


def test_match_accepts_declared_nested_path(declared_repo: Path) -> None:
    assert voicepaths.match(declared_repo, declared_repo / "src/content/a/b.md")


def test_match_rejects_undeclared_path(declared_repo: Path) -> None:
    assert not voicepaths.match(declared_repo, declared_repo / "src/lib/x.ts")


def test_double_star_can_span_zero_directories(declared_repo: Path) -> None:
    assert voicepaths.match(declared_repo, declared_repo / "src/content/post.md")


def test_missing_declaration_has_no_matches(tmp_path: Path) -> None:
    config = voicepaths.load(tmp_path)

    assert config == {
        "register": None,
        "style": None,
        "gate": None,
        "globs": [],
        "patterns": [],
        "layers": [],
    }
    assert not voicepaths.match(tmp_path, tmp_path / "anything.md")


def test_match_rejects_path_outside_root(declared_repo: Path, tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.md"

    assert not voicepaths.match(declared_repo, outside)


def test_cli_prints_only_matching_paths(declared_repo: Path) -> None:
    matching = declared_repo / "src/content/a/b.md"
    other = declared_repo / "src/lib/x.ts"

    result = subprocess.run(
        [
            sys.executable,
            str(VOICEPATHS_CLI),
            "match",
            str(declared_repo),
            str(matching),
            str(other),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == [str(matching)]
    assert result.stderr == ""


def test_cli_returns_one_when_no_paths_match(declared_repo: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(VOICEPATHS_CLI),
            "match",
            str(declared_repo),
            str(declared_repo / "src/lib/x.ts"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == ""


@pytest.fixture
def layered_repo(tmp_path: Path) -> Path:
    (tmp_path / ".voicepaths").write_text(
        """\
register: gsv-site
style: GSV
src/content/**/*.md
rules-only: docs/canon/*.md
rules-only: README.md
""",
        encoding="utf-8",
    )
    return tmp_path


def test_rules_only_lines_parse_as_globs_with_rules_layer(layered_repo: Path) -> None:
    config = voicepaths.load(layered_repo)

    assert config["globs"] == ["src/content/**/*.md", "docs/canon/*.md", "README.md"]
    assert config["layers"] == ["full", "rules", "rules"]


def test_match_layer_distinguishes_full_from_rules(layered_repo: Path) -> None:
    assert voicepaths.match_layer(layered_repo, layered_repo / "src/content/projects/x.md") == "full"
    assert voicepaths.match_layer(layered_repo, layered_repo / "docs/canon/copy-voice.md") == "rules"
    assert voicepaths.match_layer(layered_repo, layered_repo / "src/lib/x.ts") is None


def test_rules_only_paths_still_match_plain_match(layered_repo: Path) -> None:
    assert voicepaths.match(layered_repo, layered_repo / "README.md")


def test_cli_layer_full_filters_rules_only_paths(layered_repo: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(VOICEPATHS_CLI),
            "match",
            "--layer=full",
            str(layered_repo),
            str(layered_repo / "src/content/projects/x.md"),
            str(layered_repo / "docs/canon/copy-voice.md"),
            str(layered_repo / "README.md"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == [str(layered_repo / "src/content/projects/x.md")]

---
name: housecheck
description: Run the layered house-style check — Vale GSV rules + stylometric verify — on files or a directory; report card per file
allowed-tools: Bash, Read
---

# Housecheck

Check prose against both house-style layers and return a report card for each declared voice file.

## Resolve targets

1. Treat the arguments as file or directory targets. For a directory, use `git ls-files -- <directory>` to expand it to tracked files.
2. With no arguments, use `git diff --name-only` from the repository root.
3. If no files remain, report that there is nothing to check and stop.

The checker filters this list through the repository's `.voicepaths`; do not invent a broader scope.

## Run the check

Find the repository root with `git rev-parse --show-toplevel`. Run advisory mode by default:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/voice-check.sh" --root "$root" "${files[@]}"
```

When the user says `gate` or `verify`, run gate mode:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/voice-check.sh" --gate --root "$root" "${files[@]}"
```

Preserve the checker's verdict. In gate mode, exit 2 is a failure; do not soften or reinterpret it. If Vale is unavailable or a file is undeclared, report the checker's skip message plainly.

## Report results

Group each file's report by layer:

- **Rules — Vale GSV:** list every rule finding.
- **Voice — intervox:** list every stylometric finding and the verify verdict.

For every finding, show:

1. The flagged sentence.
2. The rule or metric that flagged it.
3. One concrete rewrite that addresses the finding without changing the intended claim.

End each file's card with `pass`, `revise`, or `fail`, matching the checker output. Do not edit the files unless the user also asks for revisions.

Rules derive from gsvdotcom `docs/canon/copy-voice.md` — when a finding feels wrong, the canon doc wins; propose a canon amendment rather than muting the rule.

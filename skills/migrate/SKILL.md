---
name: migrate
description: Import predecessor data — the intervoice global profile and interfluence per-project corpora — into intervox. Use on "migrate from intervoice", "migrate from interfluence", "import my old voice data", or /intervox migrate.
allowed-tools: Read, Write, Bash
---

# intervox: Migrate

One-way import from the deprecated predecessors. Sources are never deleted or modified.

## Process

1. `VOXDIR="${XDG_CONFIG_HOME:-$HOME/.config}/intervox"`; `XDG="${XDG_CONFIG_HOME:-$HOME/.config}"`.

2. **intervoice profile** (if `$XDG/intervoice/voice-profile.md` exists):
   - If it's a symlink, recreate the same symlink at `$VOXDIR/voice-profile.md` (both plugins then read the same dotfiles source — safe, format is identical).
   - If it's a regular file, copy it and tell the user both copies exist until they remove the intervoice one.
   - If `$VOXDIR/voice-profile.md` already exists, do nothing and say so.

3. **interfluence corpora**: find candidates with `ls -d ~/projects/*/.interfluence/corpus 2>/dev/null` (and any paths the user names).
   - For each project with corpus samples: show a sample list, ask which register each maps to (or "skip project"), then import via the ingest conventions (frontmatter with `source: interfluence:<project>/<file>`, original dates when recoverable from the corpus-index.yaml, `pre_llm` asked per batch).
   - **Never import pastiche/character voices as the user's own** (e.g., Stakeholders' author-pastiche deltas). If a corpus is clearly not the user's voice, skip it and note why.
   - Never delete or edit `.interfluence/` directories.

4. **interfluence learnings log** (`.interfluence/learnings-raw.log`): do not import (predecessor audit found it ~700 entries of mostly mechanical renames, low signal). Mention it exists; the user can mine it manually if they disagree.

5. Report what moved, then offer `/intervox fingerprint` to build baselines from the imported corpus.

## After migration

Recommend uninstalling the predecessors once intervox works: `claude plugin uninstall interfluence` (its global edit-logging hook double-fires otherwise) and `claude plugin uninstall intervoice`. Data directories stay untouched either way.

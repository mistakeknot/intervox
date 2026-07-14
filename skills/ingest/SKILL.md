---
name: ingest
description: Add writing samples to the user's voice corpus with provenance and AI-contamination screening. Use on "ingest these samples", "add this to my corpus", "add my writing", or /intervox ingest.
allowed-tools: Read, Write, Bash
---

# intervox: Ingest

Corpus quality decides fingerprint quality. Every sample gets provenance; contaminated samples get flagged, not silently mixed in.

## Process

1. `VOXDIR="${XDG_CONFIG_HOME:-$HOME/.config}/intervox"`; `mkdir -p "$VOXDIR/corpus"`.

2. For each sample (file or pasted text):
   - Ask (or infer and confirm) three provenance facts: **register** (team/internal/external/oss — where was this written for?), **date**, and **pre-LLM status**: was this written without AI assistance? Anything drafted or heavily edited by an LLM is contaminated for baseline purposes.
   - Slug a filename: `sample-YYYYMMDD-<slug>.md`.
   - Write to `$VOXDIR/corpus/<register>/` with frontmatter:
     ```yaml
     ---
     source: <where this came from — "email to X", "blog draft", "thesis ch.1">
     date: <original writing date, best known>
     register: <register>
     pre_llm: true|false
     ingested: <today>
     ---
     ```
     Body: the sample text, unmodified. Never "clean up" a sample; typos and quirks are signal.

3. Screening (cheap, honest):
   - Run `${CLAUDE_PLUGIN_ROOT}/engine/intervox lint --draft <sample> --baseline <existing fingerprint>` when a baseline exists; a sample failing slop_lexemes/chat_artifacts hard is likely AI-assisted — surface it and ask whether to mark `pre_llm: false` or exclude.
   - No baseline yet: eyeball for obvious tells (delve/tapestry/uniform rhythm) and note anything suspicious.

4. Report: samples added per register, corpus totals, contamination flags. If ≥1 sample landed, offer to run `/intervox fingerprint` now.

## Corpus targets (tell the user where they stand)

- Floor for a trustworthy baseline: ~20,000 words of clean pre-LLM writing overall.
- Per register: 5+ samples / 3,000+ words before its own fingerprint beats the overall one.
- Register diversity matters more than raw volume; ten more READMEs won't help the Team register.

---
name: fingerprint
description: Compute or refresh the user's stylometric baseline from their corpus. Use on "fingerprint my writing", "rebuild my baseline", "update my voice fingerprint", or /intervox fingerprint.
allowed-tools: Read, Bash
---

# intervox: Fingerprint

Turn the corpus into measured baselines: one JSON per register plus an overall one.

## Process

1. `VOXDIR="${XDG_CONFIG_HOME:-$HOME/.config}/intervox"`. Check `$VOXDIR/corpus/` exists and has samples (`find "$VOXDIR/corpus" -name '*.md' -o -name '*.txt' | head`). Empty → point the user at `/intervox ingest` and stop.

2. For each register subdirectory with ≥2 samples:
   `${CLAUDE_PLUGIN_ROOT}/engine/intervox fingerprint --corpus "$VOXDIR/corpus/<register>" --register "<register>" --out "$VOXDIR/fingerprints/<register>.json"`
   Then the overall baseline:
   `${CLAUDE_PLUGIN_ROOT}/engine/intervox fingerprint --corpus "$VOXDIR/corpus" --out "$VOXDIR/fingerprints/all.json"`
   (`mkdir -p "$VOXDIR/fingerprints"` first.)

3. Report per register: corpus size (files/words/sentences), and the headline numbers — sentence mean/SD/CV, em-dash and semicolon per 1k, top 3 connectives, MATTR. If a previous fingerprint existed, diff the headline numbers and flag any that moved >20% (usually means new samples shifted the register mix — worth a look, not necessarily a problem).

4. Warn honestly when a register has <5 samples or <3,000 words: the baseline is usable but noisy; distributional thresholds will be loose.

## Notes

- Corpus samples carry YAML frontmatter (`source`, `date`, `register`, `pre_llm: true|false`). Samples with `pre_llm: false` are included but reported: the more post-2022 material, the more the contamination caveat applies.
- Never edit corpus files. The fingerprint reads; only `/intervox ingest` writes.

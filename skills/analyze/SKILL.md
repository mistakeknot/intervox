---
name: analyze
description: Run the voice-analyzer agent over corpus + fingerprint to write or update the prose voice profile. Use on "analyze my voice", "build my voice profile", "update my profile from the corpus", or /intervox analyze.
allowed-tools: Read, Write, Bash, Agent
---

# intervox: Analyze

Produce the prose profile (Foundation + Registers) from evidence: the corpus and the measured fingerprint. The profile is what steers generation; the fingerprint is what verifies it. They must agree.

## Process

1. `VOXDIR="${XDG_CONFIG_HOME:-$HOME/.config}/intervox"`. Require a corpus; strongly prefer fingerprints to exist (`/intervox fingerprint` first if missing — the analyzer must cite numbers).

2. Launch the `voice-analyzer` agent with: corpus location, fingerprint JSONs, and the current profile (if any). The agent returns the profile markdown (see agent definition for the format contract: Foundation invariants + per-register dosage sections, every claim backed by a corpus quote or a fingerprint number).

3. Diff against the existing profile (if any) and present: what changed, what evidence drove it. The profile never mutates silently — show before writing.

4. On approval, write to the profile location the resolver uses (`$VOXDIR/voice-profile.md`, or the user's dotfiles source if they keep it symlinked — write through the symlink, don't replace it).

## Contract with the profile format

- One `## Foundation: <subtitle>` section: cross-register invariants and hard bans.
- One `## Register N: <Name>` section per register with enough corpus (Team=1, Internal=2, External=3, Open Source=4).
- Foundation captures only invariants (present across registers). Register sections capture only deltas. Adding ten blog posts must not make Foundation bloggier.
- Sparse registers (<3 samples) get a low-confidence note, not silence.

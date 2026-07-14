---
name: compare
description: Score how closely existing text matches the user's voice, with deviations. Use on "compare this to my voice", "how close is this to my style", "is this me", or /intervox compare.
allowed-tools: Read, Bash
---

# intervox: Compare

Two-layer comparison: the engine measures, then you read.

## Process

1. Resolve register (explicit or `${CLAUDE_PLUGIN_ROOT}/scripts/resolve-register.sh --infer <path>` for the name) and load the working profile; pick the matching baseline from `${XDG_CONFIG_HOME:-$HOME/.config}/intervox/fingerprints/`.

2. **Measured layer:** `${CLAUDE_PLUGIN_ROOT}/engine/intervox verify --draft <file> --baseline <baseline>` — score, verdict, failing features.

3. **Read layer:** against the prose profile, note what the numbers can't see: does it make the author's characteristic moves (openings, asides, definitional habits)? Does anything violate Foundation hard bans in spirit?

4. Present: verify score + verdict first, then the read-layer observations, then a one-line overall call ("passes the gate but opens like a press release — your openings state a claim, this one throat-clears"). If the user wants it fixed, that's `/intervox apply`.

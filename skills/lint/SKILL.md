---
name: lint
description: Score text against the user's voice fingerprint — 18 LLMism/voice features with concrete revision hints. Use on "lint this", "check this for LLMisms", "does this sound like me", "voice check", or /intervox lint.
allowed-tools: Read, Bash
---

# intervox: Lint

Report card for any text: how far is it from the user's measured baseline, feature by feature.

## Process

1. Resolve inputs:
   - Target: file path (Read to confirm it exists) or inline text (write to a temp file under /tmp).
   - Baseline: `${XDG_CONFIG_HOME:-$HOME/.config}/intervox/fingerprints/<register>.json` if a register is named or inferable from the path (use `${CLAUDE_PLUGIN_ROOT}/scripts/resolve-register.sh --infer <path>` for the register name only); else `fingerprints/all.json`. No fingerprint at all → tell the user to run `/intervox fingerprint` first, and stop.

2. Run: `${CLAUDE_PLUGIN_ROOT}/engine/intervox lint --draft <file> --baseline <baseline> --format table`

3. Present the table as-is (it is already formatted), then add a short prose read: the 2–3 findings that matter most and what they mean ("the draft's sentence rhythm is much flatter than yours — that's the strongest single AI tell in the research"). Do not re-litigate the engine's numbers with your own judgment.

4. If the user wants fixes applied, hand off to `/intervox apply` semantics (closed loop), not ad-hoc edits.

## Notes

- `chat_artifacts` or heavy `slop_lexemes` failures usually mean the text is raw LLM output; say so neutrally.
- On very short texts (<300 words) the distributional features (16–18) are skipped by the engine; mention that coverage is partial.

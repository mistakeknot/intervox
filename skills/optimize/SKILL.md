---
name: optimize
description: Tighten the prose voice profile's token cost without dropping rules. Use on "optimize my profile", "my profile is too long", or /intervox optimize.
allowed-tools: Read, Write, Bash
---

# intervox: Optimize Profile

Reduce the profile's token footprint; keep every constraint.

## Process

1. Read the profile (resolver path: `${XDG_CONFIG_HOME:-$HOME/.config}/intervox/voice-profile.md`, or legacy intervoice path). Estimate token counts per section; report the baseline.

2. Apply, in order:
   - **Dedup**: the same constraint stated in Foundation and a register — keep the Foundation copy unless the register genuinely overrides.
   - **Cut meta-commentary**: sentences describing the profile rather than instructing ("this section captures...").
   - **Atmosphere → directive**: evocative descriptions become Do/Don't lines.
   - **Trim examples**: where a long quote and a Do/Don't pair show the same rule, keep the pair; keep at least one corpus quote per section for authenticity.

3. Verify before saving: no constraint removed (only consolidated), all section headings intact (`## Foundation`, `## Register N:` — the resolver depends on them), at least one quote per section.

4. Show the diff and the token delta; write on approval (through the symlink if the profile is symlinked). If reduction is <10%, say the profile was already tight and change nothing.

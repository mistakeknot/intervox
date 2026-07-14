---
name: apply
description: Closed-loop rewrite in the user's voice. Use on "apply my voice", "rewrite in my style", "make this sound like me", "write this in my voice", or /intervox apply. Resolves the register, retrieves the user's own exemplars, drafts, lints against their fingerprint, revises up to 3 rounds, and presents the draft with a verification report card.
allowed-tools: Read, Write, Edit, Bash
---

# intervox: Apply Voice (closed loop)

Rewrite or generate content in the user's voice, verified against their measured fingerprint before presentation.

**Announce at start:** "Running the intervox loop in your <register> voice."

Paths used throughout (set once):
- `ENGINE="${CLAUDE_PLUGIN_ROOT}/engine/intervox"`
- `RESOLVER="${CLAUDE_PLUGIN_ROOT}/scripts/resolve-register.sh"`
- `VOXDIR="${XDG_CONFIG_HOME:-$HOME/.config}/intervox"`

## Process

1. **Resolve the register.**
   - Explicit (`--register=oss`, "in my internal voice"): `bash $RESOLVER "<register>"`
   - Inferred from target path: `bash $RESOLVER --infer "<path>"` (resolver prints the choice to stderr; surface it).
   The stdout IS the working profile: `## Foundation` (hard bans, invariants) + the selected `## Register` section (dosage). Exit 2 → tell the user to create the profile symlink the resolver printed, and stop.

2. **Locate the baseline.** Prefer `$VOXDIR/fingerprints/<register>.json`, fall back to `$VOXDIR/fingerprints/all.json`. If neither exists, say the loop will run WITHOUT verification (prose-only, predecessor behavior), recommend `/intervox fingerprint`, and skip steps 5–6.

3. **Retrieve exemplars.** Build a short query from the brief/target content (its topic sentence or headline) and run:
   `$ENGINE retrieve --corpus "$VOXDIR/corpus/<register>" --query "<query>" --k 4`
   (Fall back to `$VOXDIR/corpus` if the register subdir is empty.) These passages are the user's real writing: they go into your working context as style exemplars — never quoted into the output.

4. **Draft.** Rewrite (or write, if generating from a brief) following:
   - Foundation rules as hard bans, no exceptions.
   - Register dosage (humor, openings, "we" vs "I", asides).
   - The exemplars as rhythm and diction anchors: match their cadence, connective habits, and specificity; do not copy their content.
   - Preserve ALL factual content, technical details, and intended structure of the source. Never sacrifice accuracy for style.
   - For long documents, work section by section.

5. **Lint and revise (max 3 rounds).**
   `$ENGINE lint --draft <tmpfile> --baseline <baseline.json> --format json`
   - If every feature is `ok`, proceed to 6.
   - Otherwise, apply ONLY the returned hints (they are targeted: "SD 5.8w vs author 11.6w — split/merge in ¶2,4"). Do not rewrite wholesale; fix the flagged features and keep everything else stable.
   - After 3 rounds, proceed regardless; remaining flags appear on the report card.

6. **Verify.** `$ENGINE verify --draft <tmpfile> --baseline <baseline.json>`
   Capture score, verdict, and remaining failures for the report card. Do not suppress a `revise`/`reject` verdict — show it.

7. **Present.**
   - State register and why: "Applied your Open Source register to README.md (inferred from filename)."
   - Show the draft.
   - Report card: verify score + verdict, rounds used, and 2–3 concrete adaptations made ("replaced 4 em dashes; broke the uniform paragraph 3; cut 'leverage'").
   - If verification was skipped (no fingerprint), say so plainly.
   - Ask whether to write to the file or adjust.

8. **Apply** with Write/Edit if approved. Clean up temp files.

## Important

- NEVER change meaning or technical accuracy. The goal is the user's voice, not "better" content.
- If the content is already close (lint mostly ok on first pass), say so; don't force churn.
- The engine is the critic, not you. Don't overrule a fail by judgment; fix it or surface it.
- Exemplar passages are context, never output. Watch for accidental phrase-lifting from them; verbatim runs of 8+ words from an exemplar must be reworded.

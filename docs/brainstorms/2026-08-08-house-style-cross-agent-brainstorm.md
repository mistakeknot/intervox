---
artifact_type: brainstorm
bead: none
stage: discover
---

# Cross-agent LLMese avoidance + gsvdotcom house style

Session: mk + Claude, 2026-08-08. Trigger: a hand-done jawnomicon UI copy pass
(jawnomicon-ekj) stripping over-explaining/hedging/defensive LLMese that no
tooling had caught, in a stack that already owns two half-built enforcers.

## What We're Building

One house-style system that every agent runtime (Claude Code, Codex CLI, Kimi
Code — anything operating under Clavain) adheres to when writing prose on
**declared voice-carrying paths** (site copy, published docs, READMEs —
declared per-repo; engineering files, commit messages, and internal notes are
out). Two layers over one canon:

- **Rules layer (Vale):** the existing `GSV` Vale style (four error-level
  rules: Buzzwords, ThroatClearing, Overdefining, AIGenericisms, currently
  bundled in interbrowse's `register-lint` skill) — works at any text length,
  including UI microcopy; per-span exception syntax; findings at file:line.
- **Voice layer (intervox):** stylometric `verify` against the gsv-site
  fingerprint for long-form prose (≥300 words), with its real exit-code
  contract (0 pass / 1 revise / 2 reject).

intervox becomes the published umbrella plugin: a house-style skill that runs
both layers, an advisory PostToolUse hook for edit-time report cards, and the
commit-time verify gate on declared paths. Codex/Kimi reach the identical
CLIs via Bash per AGENTS.md instructions; `kimi.plugin.json` mirrors the
skill surface. Enforcement posture: **advisory at edit time, blocking at
commit time**, on declared paths only.

## Why This Approach

Both halves already exist and each covers the other's blind spot: Vale rules
are length-insensitive (the jawnomicon microcopy problem) but cannot measure
register; intervox stylometry measures register but self-gates below 300
words of flowing prose. Layering reuses everything mk owns — the GSV style,
the 19-feature engine, the fingerprints, Clavain's hook patterns — and the
only new dependency (Vale via brew) degrades gracefully: machines without it
still get the stylometric layer and the doctrine pointers. The rejected
alternatives: intervox-only (rebuilds Vale's mature exception/rule machinery
by hand), Vale-only (abandons register verification — rules can never check
"sounds like the house").

## Key Decisions

1. **Scope — declared voice-carrying paths** (mk, 2026-08-08). Per-repo
   declaration mechanism is plan detail. First adopters: gsvdotcom,
   jawnomicon `site/src`.
2. **Posture — advisory edit, gate commit** (mk, 2026-08-08). Edit-time
   report card via hook; `intervox verify` + Vale must pass on touched
   declared files at commit/session-end. Same gate expressed to Codex/Kimi
   as an AGENTS.md pre-commit instruction.
3. **Canon — `docs/canon/copy-voice.md` in the gsvdotcom repo rules**
   (mk, 2026-08-08). COPY_GUIDE.md (byte-identical twin) becomes a pointer;
   VOICE.md's constraints merge in; the Vale GSV style and the intervox
   gsv register/fingerprint become **dated derivations** of the canon doc
   (the interbrowse derivation-note pattern). Note: local ~/projects/gsvdotcom
   is the live canonical working copy (remote `canonical` →
   gensysven/generalsystemsventures; the archived name gensysven/gsvdotcom is
   what "retired" refers to).
4. **Stack — layered, intervox as umbrella** (mk, 2026-08-08). Approach A
   over intervox-only (B) and Vale-only (C).
5. Cross-agent distribution: marketplace publish for Claude Code (registry
   pulls github.com/mistakeknot/intervox.git — publish = GitHub push +
   `/interpub:release` version sync), AGENTS.md sections (via interdoc and
   directly in adopter repos) for Codex/Kimi, engine stays stdlib-only so
   any runtime can shell out.

## Open Questions

- **Vocabulary line (mk ruling required, gates canon consolidation):**
  COPY_GUIDE allows "comparative advantage / coordination mechanism /
  topology…"; VOICE.md bans "synergy/leverage/ecosystem used non-technically"
  and draws a stricter non-buzzy line. Where exactly does technical usage
  end and buzz begin? The merged canon doc encodes the answer; the Vale
  Buzzwords rule derives from it.
- **Fingerprint validity:** gsv-site.json rests on 941 synthetic words
  against the README's stated 20k floor. Rebuild the corpus from real
  shipped site copy (post-copy-pass gsvdotcom + jawnomicon chrome) before
  the verify gate is allowed to reject anyone. Until then the gate runs
  rules-heavy.
- **Vale style home:** interbrowse bundles the GSV style today; the
  derivation pattern ("styles live with the brand they derive from")
  suggests moving it into the gsvdotcom repo with the plugin providing the
  harness. Lean: move it; finalize in plan (interbrowse keeps a pointer).
- **Repair debts discovered:** the intervox voice-profile symlink chain is
  broken on this Mac (`~/.config/intervox/voice-profile.md` →
  `dotfiles/projects/…` missing; live file is `dotfiles/common/projects/…`),
  so `resolve-register.sh` exits 2 everywhere; it also has no `gsv-site`
  branch in its register mapping. Both are plan items, not design forks.
- **Tracker blockage:** the intervox beads DB is schema-stranded (v23 vs
  v53, writes blocked pending the single designated migrator). Beading the
  implementation epic requires that reconciliation first — or the epic
  lives in a different tracker.
- Does agent *chat* output (not files) ever get linted? Out of scope for
  this design; revisit only if file-level enforcement proves insufficient.

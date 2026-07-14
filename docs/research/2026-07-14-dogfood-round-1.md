# Dogfood round 1 — MK corpus, four registers (2026-07-14)

First end-to-end run of the closed loop on the author's real corpus, same day as v0.1.0. Corpus: migrated from interfluence (one 3.5k-word substack essay → oss; six client-facing PR comments, 211 words total → external). Profile: the live dotfiles profile via the resolver.

## Engine bugs found and fixed (real data broke what fixtures didn't)

1. **Frontmatter leaked into stats.** Corpus files carry YAML provenance frontmatter (ingest convention); the engine never stripped it. Fixed in `strip_markdown`, regression-tested.
2. **Block merge produced a 757-word "sentence."** Headings and list items without terminal punctuation glued onto following paragraphs; sentence mean read 38.6w/SD 82 on a normal blog post. Fixed: blocks terminate and isolate; sentences never span a blank line. Regression-tested.
3. **First-person counter read 0.0 on a first-person essay.** `I_RE` matched lowercase-only `\bi\b`, which never occurs as an English word. Fixed, regression-tested.
4. **Slop hard-fail rejected the author's own held-out writing** (found in pre-release smoke on a second corpus): thresholds made baseline-relative and the feature removed from the solo hard-fail set.

Four bugs, all caught by running real text through the loop within hours of writing it. Fixture corpora are too polite.

## Loop results (draft → lint → revise ≤3 → verify)

| Register | Target doc | Rounds | Final | Residual failures |
|---|---|---|---|---|
| Open Source | intervox README rewrite | 3 | 76 revise | function_word 0.75, punct-interval warn |
| Team | capability-routing brainstorm rewrite | 1 | 82 pass | function_word (non-blocking) |
| Internal | interfluence PRD rewrite | 2 | 76 revise | function_word 0.69 |
| External | client exec summary | 2 | 82 pass | function_word (non-blocking) |

The lint hints were concrete and actionable throughout ("46% of adjacent sentence pairs within 4 words", "5.6% short sentences vs baseline 14.3% — add a few short, blunt sentences") and drove measurable convergence: the README went from 3 fails + 1 warn to one explained residual over three rounds.

## The pattern in the residuals

Every failing `function_word_delta` belongs to a markdown-structured draft (README with tables, spec with headers) scored against an all-prose corpus. Flowing-prose drafts (Team chat register, External summary) pass. The distributional features are comparing genre, not just voice. Two consequences filed as beads: corpus needs per-register samples in the registers' real genres, and the distributional features (16–18) should compare prose-extracted text or gate on genre match.

## Rough edges filed as beads (children of sylveste-lbe)

- Corpus expansion campaign: oss baseline is one blog essay; external is 211 words; team and internal have zero samples and fall back to `all.json`.
- Register taxonomy: no blog/essay slot; the substack post is shoehorned into oss.
- Genre-gating for distributional features; also strip tables from prose extraction.
- Orality/literacy axis (Havelock-inspired) as a native register signal — see below.

## Havelock.ai assessment (user question, same day)

Researched via secondary sources (site 403s scripted fetches). Havelock is Joe Weisenthal's experimental orality-vs-literacy analyzer built on Ong/Havelock media theory: BERT regression to a 0–1 oral↔literate score plus ~67 marker types (anaphora, epistemic hedge, vocative...). By its own disclaimer it is "not recommended for deployment in mission-critical applications"; no validation data, no confirmed stable API, single maintainer, scoring model already rewritten once. **Verdict: skip the runtime dependency, adopt the concept natively.** The oral↔literate axis is genuinely orthogonal to our per-feature fingerprint as a register-level signal (Team should measure oral, External literate), and its ingredients (nominalization, passive rate, hedge density vs. direct address, questions, repetition) are deterministic primitives we can compute ourselves. Filed as a bead. Open action: load havelock.ai/api in a real browser to confirm whether a documented API exists at all.

## Addendum: sylveste-lbe.9 fixed same day (engine v0.1.1)

Distributional features now run prose-to-prose (`extract_prose`: tables, headings, and sub-8-word list fragments excluded on both sides; table-invariance regression-tested) and carry an advisory band with anomaly floors (0.15/0.60/0.40) — moderate divergence warns, only catastrophic divergence fails. Rationale: even prose-extracted, the residual was genuine genre signal (the README correctly has zero first-person "I" against a blog baseline running 31/1k); a single-essay corpus cannot convict on distribution. Re-verification: README 76→88 pass, Team 82→94 pass, Internal 76→88 pass, External 82→94 pass; sloppy fixture still rejects (exit 2), clean fixture still passes. The features regain fail-strength organically as sylveste-lbe.7 lands same-genre corpus samples.

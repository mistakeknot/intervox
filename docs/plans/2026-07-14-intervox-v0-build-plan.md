# intervox — v0 build plan

> **Reading context.** intervox replaces both interfluence (deprecated 2026-05, per-project glob-routed voices) and intervoice (deprecated 2026-07-14, global register profile, prose-only). Decision made 2026-07-14 with MK: fresh plugin, full closed loop in v0, both predecessors deprecated. Research basis: `docs/research/` (three source reports).

## Why a third plugin

interfluence got the generation interface right (prose profile, evidence from corpus) and the storage model wrong (per-project, glob-routed). intervoice fixed the storage model (one global profile, Foundation + registers) but, like interfluence, never measured output: the rewrite was graded by the same model that produced it, against no baseline. The 2023–2026 literature is unambiguous that the missing half is measurement — a stylometric critic loop closes 71–75% of the style gap, exemplar retrieval beats style adjectives, and every lint threshold should be calibrated to the author's corpus, not universal constants.

Renaming intervoice in place was considered and rejected: the measurement half changes the plugin's data model (corpus returns, fingerprints appear), and two similarly-named live plugins invite confusion. Fresh repo, both ancestors deprecated, one migration path.

## Decisions locked

1. **Profile format frozen to intervoice's shape.** `## Foundation` + `## Register N: <Name>` sections, XDG location. Existing profiles work unchanged; resolver falls back to the intervoice path until migration.
2. **Corpus returns, globally.** interfluence had per-project corpora (wrong scope); intervoice dropped corpora entirely (lost the evidence base). intervox: `~/.config/intervox/corpus/<register>/` with YAML provenance frontmatter per sample (source, date, pre-LLM-era flag).
3. **Stdlib-only engine, no server.** Python CLI (`engine/intervox`): fingerprint, lint, verify, retrieve, registers. No Node build (interfluence's mistake), no pip deps in core. Embeddings (StyleDistance/LUAR centroids) and surprisal scoring are explicitly deferred to optional-extra tiers.
4. **Closed-loop apply.** resolve register → retrieve k=4 exemplars from that register's corpus → draft (Foundation + Register + exemplars + brief) → engine lint → targeted revision (≤3 rounds, stop early on verify pass) → verify gate → present draft with report card. The critic is the deterministic engine, not the generating model (self-critique self-biases; measured critics close the gap).
5. **Baseline-relative thresholds, cluster verdicts.** Every feature scores as distance from the author's fingerprint; the gate weighs co-occurrence of tells, not single hits. Slop lexicon is versioned and model-era-aware (delve decayed in 2025; the list rotates).
6. **Honest ceiling in the docs.** Voice fidelity ≠ detector evasion; the product target is "author after a good editor."

## v0 components

| Component | Source | Status |
|---|---|---|
| resolve-register.sh | intervoice, ported (+ legacy path fallback) | done |
| engine (fingerprint/lint/verify/retrieve/registers) | new, spec from research brief | building |
| apply skill (closed loop) | new; drafting step descends from intervoice apply | building |
| lint / fingerprint / ingest skills | new | building |
| analyze skill + voice-analyzer agent | ported from intervoice, now must cite fingerprint numbers | building |
| compare / optimize skills | ported (light) | building |
| migrate skill | new (interfluence corpora + intervoice profile) | building |
| deprecations (interfluence, intervoice) + marketplace | runbook below | pending |

## The 18 lint features (v0 ships 17 + 1 deferred)

Lexical: slop lexemes (effect-size weighted), slop phrases, chat artifacts (hard fail), lexical-diversity floor (MATTR).
Constructional: participial tails, negative parallelism, rule-of-three, copula avoidance, hedging boilerplate.
Rhythmic/structural: sentence-length burstiness, consecutive-length monotony, short-sentence deficit, punctuation-interval burstiness, em-dash density, paragraph uniformity + scaffold markers.
Distributional: connective drift, function-word cosine, character-trigram cosine.
Deferred: surprisal-profile match (needs a small LM; optional tier, v0.2+).

Elegant-variation detection (synonym cycling) needs coreference and is out of v0; documented as not-implemented rather than faked.

## Migration runbook

1. `/intervox migrate` moves/symlinks the intervoice profile into `~/.config/intervox/` (or leaves it and relies on resolver fallback, user's choice).
2. interfluence `.interfluence/` corpora: offered per-project import into the global corpus with a register mapping prompt. **Never delete source dirs.** Stakeholders' 15 author-pastiche voices are NOT the user's voice — leave in place; pastiche registers are a possible later feature.
3. interfluence's global PostToolUse:Edit logging hook must not run alongside intervox: deprecation bumps interfluence's plugin with the hook removed; until then, uninstalling interfluence after intervox install is the clean path.
4. Marketplace: add intervox; mark interfluence and intervoice descriptions `[DEPRECATED — use intervox]`.

## Later (explicitly not v0)

- Embedding centroids (StyleDistance primary, LUAR secondary) behind a pip extra; held-out-topic validation harness.
- Surprisal/UID scoring tier (GPT-2-class local model).
- English clausula/cadence detector (stress-pattern analysis of clause endings — proven architecture, unbuilt in the field).
- Structural exemplar retrieval (how the author opens / closes / CTAs), beyond v0's semantic retrieval.
- Pastiche registers (Stakeholders' author voices) as a separate concept from the user's own registers.
- Learn-from-edits flywheel with a trigger smart enough to distinguish voice corrections from renames (both predecessors failed this; needs design).

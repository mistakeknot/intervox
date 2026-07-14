# intervox

> Generate and edit prose in your voice, then prove it: every draft is scored against your measured stylometric fingerprint before it reaches you.

intervox is the third generation of the voice lineage (interfluence → intervoice → intervox) and the first with a closed loop. Its predecessors steered generation with a prose profile and graded the result by vibes. intervox keeps the prose profile as the generation interface and adds the missing half: a measurement engine that fingerprints your corpus, lints drafts for LLMisms, retrieves your own sentences as exemplars, and gates output on verified closeness to your baseline.

The design principle: **prose steers, numbers verify.**

## What it does

| Command | Does |
|---|---|
| `/intervox apply [--register=<r>] <path>` | Closed-loop rewrite: retrieve your exemplars, draft, lint, revise (≤3 rounds), verify, present with a report card. |
| `/intervox lint <path>` | Score any text against your fingerprint: 18 LLMism/voice features, each with a concrete revision hint. |
| `/intervox fingerprint` | Recompute your stylometric baseline from the corpus (per register + overall). |
| `/intervox ingest <samples...>` | Add writing samples to your corpus with provenance and AI-contamination screening. |
| `/intervox analyze` | Voice-analyzer agent reads corpus + fingerprint and writes the prose profile, with every claim backed by a number or a quote. |
| `/intervox compare <path>` | How close is existing text to your voice? Score plus deviations. |
| `/intervox optimize` | Tighten the prose profile's token cost without dropping rules. |
| `/intervox migrate` | Import interfluence corpora and the intervoice profile. |

## The loop

```
corpus ──► fingerprint (JSON baseline per register)
              │
brief ──► retrieve exemplars ──► draft (Foundation + Register + exemplars)
              │                     │
              │                  lint ◄─── revise (≤3 rounds)
              │                     │
              └────────────► verify gate ──► report card + draft
```

Generation is prompted with your prose profile and your own retrieved passages. Verification is deterministic: sentence-rhythm burstiness, punctuation profile, slop lexicon (effect-size weighted, model-era versioned), participial tails, contrast frames, rule-of-three density, connective drift, function-word and character-trigram distance. Every threshold is calibrated to *your* baseline, not universal constants, and the verdict weighs cluster co-occurrence, not single tells.

## Storage

Everything lives under `${XDG_CONFIG_HOME:-~/.config}/intervox/`:

```
voice-profile.md        # Foundation + Register sections (intervoice-compatible format)
corpus/<register>/*.md  # your writing samples, YAML provenance frontmatter
fingerprints/<register>.json
lexicon.json            # optional slop-lexicon override
```

The profile format is unchanged from intervoice: one `## Foundation` section (invariants, hard bans) plus `## Register N: <Name>` sections (Team / Internal / External / Open Source dosage). Existing profiles work as-is; the resolver falls back to the intervoice path until you migrate.

## The engine

`engine/intervox` is a dependency-free Python CLI (stdlib only): `fingerprint`, `lint`, `verify`, `retrieve`, `registers`. Skills call it with Bash; nothing needs a build step or a server. See [`engine/README.md`](engine/README.md).

Deliberately out of v0: embedding centroids (StyleDistance/LUAR) and surprisal scoring — both land behind optional extras in a later release; the deterministic features carry the loop until then.

## Lineage and evidence

- interfluence (deprecated): per-project corpora, glob-routed voices, MCP filing cabinet, prose-only grading.
- intervoice (deprecated): global multi-register profile, resolver, no measurement.
- intervox: intervoice's profile model + a measurement engine built on the 2023–2026 stylometry/LLMism literature — see [`docs/research/`](docs/research/) for the three source reports (authorship verification, controllable generation, LLMism/rhythm detection).

## Install

```bash
claude plugin install intervox@interagency-marketplace
```

Then `/intervox migrate` (if coming from interfluence/intervoice) or `/intervox ingest` to start a corpus, `/intervox fingerprint`, and you're live.

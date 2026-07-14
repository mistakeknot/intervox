# intervox

> Your voice profile tells the model how to write; your fingerprint checks whether it listened.

Every "write in my style" tool works the same way: describe the voice in prose, prompt the model, hope. intervox keeps the prose profile (it is the right interface for steering a model) and adds the half those tools skip: a measurement engine that fingerprints your actual writing, lints every draft against that baseline, and attaches the verdict to the output. Drafts arrive with a report card, not a vibe.

The principle: prose steers, numbers verify.

## What's real (v0.1.0)

The deterministic loop is real and tested (52 tests): fingerprint, a 17-feature linter, the verify gate, TF-IDF exemplar retrieval, and the closed-loop apply skill that ties them together into something you can actually run on a draft. Embedding centroids and surprisal scoring do not exist yet. They are planned optional tiers; until they land, the engine reports "skipped" rather than faking a number. The profile format is inherited unchanged from intervoice, which means an existing profile works on day one and the migration is nothing more dramatic than a symlink.

## What it does

Each subcommand maps to a skill and the table below is the entire surface area there is to learn.

| Command | Does |
|---|---|
| `/intervox apply [--register=<r>] <path>` | Closed-loop rewrite: retrieve your exemplars, draft, lint, revise (3 rounds max), verify, present with a report card. |
| `/intervox lint <path>` | Score any text against your fingerprint; every flag comes with a concrete revision hint. |
| `/intervox fingerprint` | Recompute your baseline from the corpus (per register, plus overall). |
| `/intervox ingest <samples...>` | Add writing samples with provenance and contamination screening. |
| `/intervox analyze` | The voice-analyzer agent writes the prose profile; every claim cites a quote or a number. |
| `/intervox compare <path>` | How close is existing text to your voice? Score plus deviations. |
| `/intervox optimize` | Cut the profile's token cost without dropping rules. |
| `/intervox migrate` | Import interfluence corpora and the intervoice profile. |

## The loop

```
corpus ──► fingerprint (JSON baseline per register)
              │
brief ──► retrieve exemplars ──► draft (Foundation + Register + exemplars)
              │                     │
              │                  lint ◄─── revise (3 rounds max)
              │                     │
              └────────────► verify gate ──► report card + draft
```

Generation is prompted with your profile plus passages retrieved from your own corpus (retrieved passages beat style adjectives in every benchmark that compares them). Verification is deterministic. The linter measures sentence-rhythm burstiness, punctuation profile, a slop lexicon weighted by published effect sizes, participial tails, contrast frames, connective drift, and function-word and character-trigram distance; every threshold is relative to your measured baseline. For example, an em-dash rate that would convict one author is another author's signature, so the engine compares you to you. The gate weighs clusters of tells. A single flagged feature, however, still shows up on the report card; it just cannot reject a draft alone.

## Storage

Everything lives under `${XDG_CONFIG_HOME:-~/.config}/intervox/`:

```
voice-profile.md        # Foundation + Register sections (intervoice-compatible)
corpus/<register>/*.md  # your writing samples, YAML provenance frontmatter
fingerprints/<register>.json
lexicon.json            # optional slop-lexicon override
```

The profile format is one `## Foundation` section (invariants, hard bans) plus `## Register N: <Name>` sections (Team, Internal, External, Open Source). Keep the source of truth in your dotfiles and symlink it the way you would version any other config file you care about. The resolver falls back to the intervoice path until you migrate so nothing breaks while both directories exist.

## The engine

`engine/intervox` is a Python CLI with zero dependencies outside the standard library: `fingerprint`, `lint`, `verify`, `retrieve`, `registers`. Skills call it with Bash and the whole thing runs anywhere Python 3.11 runs without asking you to install packages or trust a server you cannot read. No build step, no node_modules. See [`engine/README.md`](engine/README.md).

## Lineage

- interfluence (deprecated): per-project corpora, glob-routed voices, an MCP filing cabinet, no measurement.
- intervoice (deprecated): the global multi-register profile this plugin inherits and still no measurement of whether output actually matched the author.
- intervox: the same profile plus the measurement engine, built on the 2023-2026 stylometry and LLM-detection literature; the three source reports live in [`docs/research/`](docs/research/).

## Install

```bash
claude plugin install intervox@interagency-marketplace
```

Coming from a predecessor: first run `/intervox migrate`, then `/intervox fingerprint`. Starting fresh: run `/intervox ingest` with 20,000+ words of your own pre-LLM writing (the floor for a trustworthy baseline; less works, noisily), then `/intervox fingerprint`. That's it. Finally, if a lint feature keeps flagging vocabulary you legitimately use, override it in `lexicon.json` rather than fighting the gate.

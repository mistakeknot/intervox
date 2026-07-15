# intervox engine

Stylometric fingerprinting and LLMism linter. Single-file Python engine
(`intervox_engine.py`), standard library only — no pip dependencies.
Python 3.11+.

## Install / run

No install step. Run the shim directly:

```
./engine/intervox <command> ...
```

or invoke the module with any Python 3.11+ interpreter:

```
python3 engine/intervox_engine.py <command> ...
```

## Commands

### `fingerprint`

Build a baseline stylometric profile from a corpus of human writing (or a
single document).

```
intervox fingerprint --corpus tests/fixtures/corpus --out baseline.json
intervox fingerprint --corpus docs/my-writing/ --out baseline.json --register "internal"
intervox fingerprint --text essay.md --out baseline.json
```

Reads `*.md` and `*.txt` files recursively under `--corpus` (or a single
file with `--text`), strips markdown syntax, and measures sentence rhythm,
punctuation density, hedging/passive-voice rates, copula usage, rhetorical
constructions (participial tails, negative parallelism, rule-of-three),
connective-word usage, function-word frequencies, character trigrams,
lexical diversity (MATTR), slop-lexicon hit rate, and the orality/literacy
axis (see "Orality/literacy axis" below). Writes the result as JSON to
`--out`.

`--lexicon FILE` accepts a JSON file to extend/trim the built-in slop
lexicon (see "Lexicon overrides" below).

### `lint`

Compare a draft against a baseline fingerprint, feature by feature.

```
intervox lint --draft draft.md --baseline baseline.json
intervox lint --draft draft.md --baseline baseline.json --format json
```

Evaluates 19 features (slop lexemes/phrases, chat artifacts, lexical
diversity, participial tails, negative parallelism, rule-of-three, copula
avoidance, hedging boilerplate, em-dash density, burstiness, monotony,
short-sentence deficit, punctuation-interval burstiness, paragraph
uniformity, connective drift, function-word delta, char-trigram delta,
orality drift). Each feature gets a status of `ok`, `warn`, `fail`, or
`skipped` (features 16-18 skip on drafts under 300 words — cosine
similarity over sparse vectors is not meaningful at that length; feature 19
additionally skips when the baseline predates the orality axis).

Feature 19 (`orality_drift`) is advisory-only: it can warn but never fails
and is never a hard-fail id, so it can never solo-reject a draft via
`verify`.

`--format table` (default) prints an aligned table plus a "Top revision
hints" section, fail-first. `--format json` prints the raw list of
feature-result objects.

### `verify`

Run `lint` and reduce it to a single pass/revise/reject verdict.

```
intervox verify --draft draft.md --baseline baseline.json
```

Composite score starts at 100, -18 per fail, -6 per warn (floor 0),
skipped features excluded. Prints `{score, verdict, failures, hints}` as
JSON.

Exit codes:
- `0` — score >= 80 and no hard fail among features 1 (slop_lexemes), 3
  (chat_artifacts), 10 (em_dash_density). Verdict: `pass`.
- `1` — score 60-79, or soft fails only. Verdict: `revise`.
- `2` — score < 60, or any hard fail. Verdict: `reject`.

### `retrieve`

Paragraph-chunk a corpus, rank chunks against a query with TF-IDF cosine
similarity (log-tf, smoothed idf, stdlib only — no external embedding
model).

```
intervox retrieve --corpus tests/fixtures/corpus --query "insurance adjuster basement flood" --k 5
```

Adjacent short paragraphs are merged until each chunk has at least
`--min-words` words (default 40). Output is a JSON list of
`{file, score, text}`, ordered deterministically: score descending, then
file path, then position within file.

### `registers`

List `## Foundation` and `## Register N: <Name>` H2 sections found in a
voice-profile markdown file.

```
intervox registers --profile voice-profile.md
```

Prints a JSON list of `{type: "foundation"|"register", number, name}`.

### `orality`

Compute the orality/literacy axis block for a corpus or single document,
without building a full fingerprint.

```
intervox orality --corpus docs/my-writing/
intervox orality --text draft.md
```

Prints `{axis, oral_component, literate_component, markers}` as JSON. See
"Orality/literacy axis" below for what these mean.

## Lexicon overrides

`--lexicon FILE` (accepted by `fingerprint`, `lint`, `verify`) points to a
JSON file with any of these optional keys:

```json
{
  "remove_tier1": ["robust", "leverage"],
  "tier1_lexemes": ["frobnicate"],
  "tier2_phrases": ["some (?:regex )?fragment"],
  "chat_artifacts": ["as an assistant"]
}
```

`remove_tier1` unbans built-in tier-1 lexemes (useful for domain terms like
"robust" in an engineering register). `tier1_lexemes` / `tier2_phrases` /
`chat_artifacts` extend the built-in lists; `tier2_phrases` entries are
regex fragments joined with the built-ins via alternation.

## Text preprocessing notes

- Markdown is stripped (code fences, inline backticks, headings, list
  markers, link syntax, bold/italic) while paragraph boundaries (blank
  lines) are preserved.
- Sentences are split on `/(?<=[.!?])\s+(?=[A-Z"("'\d])/` after masking
  known abbreviations (e.g., i.e., etc., vs., cf., Dr., Mr., Ms., U.S.,
  Fig., Eq., Sec., No.) so those don't get mistaken for sentence
  boundaries. Sentences under 3 words count as fragments, tracked
  separately from the sentence-rhythm stats.
- Words are whitespace/punctuation-tokenized (letters + apostrophes) for
  counts; the raw cleaned text is kept around for the regex-based
  rhetorical-construction features.

## Not yet implemented

- **Feature 18 in the original design doc, "surprisal"** (perplexity /
  next-token-surprisal under a language model) is intentionally **out of
  scope for v0**. It requires an actual LM (even a small n-gram model
  trained per-baseline would be a meaningfully different, heavier
  dependency-tier feature) and is deferred to a future optional-dependency
  tier. It is NOT stubbed with fake numbers anywhere in this engine — the
  18 features implemented here are the regex/statistics-only feature set
  described in the CLI spec (participial tails, rule-of-three, connective
  drift, char-trigram delta, etc.), numbered 1-18 in `lint`'s own
  evaluation order, which is a distinct list from the design doc's
  feature numbering.

## Known limitations (by design, not bugs)

- Passive-voice, connective, and rule-of-three detection are regex
  heuristics, not a parser — they will occasionally misfire on ordinary
  prose that happens to match the pattern (e.g. "the first attempt" is
  counted as a hit for the connective "first" even though it's an ordinal,
  not a discourse connective). This mirrors the spec's explicit "naive
  match acceptable" instructions for several lexemes.
- `fingerprint --corpus` builds one aggregate profile by concatenating all
  matched files rather than averaging per-file profiles. Per-file
  averaging would distort ratio-style features (cv, mattr) badly on short
  files; a single aggregate over the whole corpus is more stable and
  matches the flat JSON schema the spec defines.
- Lint features 12 (monotony) and 14 (punct_interval_burstiness) compare
  against baseline-derived signals (`_derived_monotony_pct`,
  `_derived_punct_interval_sd`) that `fingerprint` writes into the output
  JSON alongside the documented schema keys. If you hand-edit or
  regenerate a baseline file without these keys, those two features fall
  back to the "no baseline" absolute-threshold branch documented in the
  CLI spec.

## Testing

```
python3 tests/test_engine.py
```

## Distributional features: prose extraction and the advisory band (v0.1.1)

Features 16-18 (connective drift, function-word delta, char-trigram delta) are computed prose-to-prose: `extract_prose` drops table rows, heading lines, and list fragments under 8 words from both corpus and draft before the distributions are built, and the features skip when a draft has under 300 words of flowing prose. They also carry an advisory band: moderate divergence warns rather than fails (floors: 0.15 / 0.60 / 0.40), because these cosines read genre as well as voice — a README correctly contains zero first-person against a blog-essay baseline. Grow the register corpus with same-genre samples to make the comparison bind harder.

**After upgrading to v0.1.1, re-run `fingerprint`** — baselines built by v0.1.0 computed distributions over full text, not extracted prose.

## Orality/literacy axis (v0.2.0)

`sylveste-lbe.10`: a register-level signal inspired by Ong/Havelock orality
theory — oral registers (chat, blog, conversational writing) tend toward
direct address, questions, and contractions; literate registers (academic,
formal documentation) tend toward nominalization, subordination, and dense
content-word packing. The axis summarizes that tendency as a single
`[0, 1]` number, computed on the same extracted-prose text as features
16-18 (see above), so it inherits the same table/heading/fragment
exclusions.

**Markers** (all per 1k words of prose unless noted):

- Oral: `second_person_per_1k` (you/your/yours/yourself), `questions_per_1k`
  (`?` count), `exclaims_per_1k` (`!` count), `first_singular_per_1k` (I +
  me/my/mine), `contractions_per_1k` (`n't`/`'s`/`'re`/`'ve`/`'ll`/`'d`/`'m`),
  `sentence_initial_conj_per_100s` (sentences starting And/But/So/Or, per
  100 sentences).
- Literate: `nominalizations_per_1k` (words ≥8 chars ending in
  -tion(s)/-sion(s)/-ment(s)/-ness/-ity/-ities), `passive_per_1k` (the
  engine's existing passive-voice heuristic), `subordinators_per_1k`
  (because/although/though/whereas/whereby/which/whom/whose/thereby/wherein),
  `long_words_per_1k` (alphabetic tokens ≥9 chars), `lexical_density`
  (content words / total words, as a 0-1 fraction — content = tokens not in
  the engine's `FUNCTION_WORDS` list).

**Scoring**: each marker is min-max scaled to `[0, 1]` via
`clamp((value - lo) / (hi - lo), 0, 1)` against the `ORALITY_CALIBRATION`
constants in `intervox_engine.py`. The oral markers' scaled mean and the
literate markers' scaled mean combine as
`axis = clamp(0.5 + (literate_component - oral_component) / 2, 0, 1)`:
`0` is maximally oral, `1` is maximally literate, `0.5` is balanced.

**Calibration caveat**: `ORALITY_CALIBRATION` is a v0 set of plausible
reference min/max ranges per marker, chosen to make ordinary prose land
somewhere sane in `[0, 1]` — **not** empirical percentiles derived from a
real corpus distribution. Treat axis values as directionally meaningful
(useful for "is this draft drifting oral/literate relative to its own
baseline") rather than as calibrated absolute scores. Revisit the constants
once enough fingerprinted corpora exist to compute real percentile bands.

**Fingerprint integration**: `fingerprint` (and `orality`) attach an
`"orality"` block — `{axis, oral_component, literate_component, markers}`
— to the output JSON. `lint`/`verify` add feature 19, `orality_drift`
(advisory-only: it can warn but never fails, and is never a hard-fail id),
which warns when `|draft_axis - baseline_axis| > 0.15`.

**Old fingerprints need re-running** to gain the `"orality"` block — a
baseline JSON generated before v0.2.0 lacks it, and `lint`/`verify` skip
feature 19 gracefully (status `skipped`) rather than crashing when it's
missing.

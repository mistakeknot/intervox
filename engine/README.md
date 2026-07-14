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
lexical diversity (MATTR), and slop-lexicon hit rate. Writes the result as
JSON to `--out`.

`--lexicon FILE` accepts a JSON file to extend/trim the built-in slop
lexicon (see "Lexicon overrides" below).

### `lint`

Compare a draft against a baseline fingerprint, feature by feature.

```
intervox lint --draft draft.md --baseline baseline.json
intervox lint --draft draft.md --baseline baseline.json --format json
```

Evaluates 18 features (slop lexemes/phrases, chat artifacts, lexical
diversity, participial tails, negative parallelism, rule-of-three, copula
avoidance, hedging boilerplate, em-dash density, burstiness, monotony,
short-sentence deficit, punctuation-interval burstiness, paragraph
uniformity, connective drift, function-word delta, char-trigram delta).
Each feature gets a status of `ok`, `warn`, `fail`, or `skipped` (features
16-18 skip on drafts under 300 words — cosine similarity over sparse
vectors is not meaningful at that length).

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

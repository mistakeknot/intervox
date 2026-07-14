# LLMism Detection & Prose Rhythm: Research Report (2023–2026)

Note: several arXiv IDs are 2026 preprints — directionally corroborated but not yet peer-reviewed. Flagged inline.

---

## AREA A — LLMisms / AI slop detection

### A1. Lexicons of AI-typical vocabulary

**Kobak, González-Márquez, Horvát & Lause — "Delving into LLM-assisted writing in biomedical publications through excess vocabulary" (Science Advances 2025; arXiv:2406.07016; code/data: github.com/berenslab/llm-excess-vocab).** The anchor study. 15M+ PubMed abstracts (2010–2024), per-word frequency gaps against counterfactual pre-ChatGPT trend projections — assumption-free. Found **900 excess words**, of which **407 are "style" words** — the genuine LLMisms, 66% verbs. Headline effect sizes: *delves* r=28.0×, *underscores* r=13.8×, *showcasing* r=10.7×. ≥13.5% of 2024 PubMed abstracts show LLM involvement. The annotated CSV of 900 words is downloadable — the single best raw input for a linter lexicon.

**Liang, Izzo, Zhang et al. — "Monitoring AI-Modified Content at Scale" (ICML 2024; arXiv:2403.07183).** Population-level ML estimate of LLM-modified sentences in peer reviews: ICLR 2024 1.6%→10.6% post-ChatGPT. Appendix Tables 2–3: **top-100 AI-disproportionate adjectives and adverbs** with fold-increases: *meticulous* 34.7×, *intricate* 11.2×, *commendable* 9.8×. Companion caveat: Liang et al. 2023 (Patterns; arXiv:2304.02819) — detectors flag >50% of TOEFL essays as AI (non-native prose mimics low-burstiness signals).

**Juzek & Ward — "Why Does ChatGPT 'Delve' So Much?" (arXiv:2412.11385).** Tests seven causal hypotheses; concludes **RLHF is the most plausible driver** of lexical overrepresentation. Deltas 2020→2024: *delves* +6,697%, *underscores* +904%, *intricate* +611%.

**Matsui — "Delving Into PubMed Records" (Perspectives on Medical Education 2025).** PRISMA-style meta-list: 135 candidate AI terms from 15 prior studies, tested against PubMed trajectories. **103/135 confirmed**; top: *delve, underscore, primarily, meticulous, boast*. Key nuance: usage began rising in **2020, pre-ChatGPT** — LLMs amplified existing drift; strong but not "pure" AI tells.

**Wikipedia — "Signs of AI writing".** Best-maintained practical field guide (WikiProject AI Cleanup). Taxonomy spans vocabulary **tracked by model era** (delve-era 2023–24; *delve* "dropped off sharply" in 2025), significance inflation, participial "-ing" sentence tails, copula avoidance, negative parallelisms, rule-of-three, elegant variation, em-dash/boldface overuse, weasel attributions, formulaic scaffolding, markup artifacts. Central calibration points: **no single tell is reliable — clustering is the signature** — and human writing is itself drifting toward these patterns post-2023.

**Practitioner lexicons:** conorbronsdon/avoid-ai-writing (109-entry, confidence-weighted); SicariusSicariiStuff/SLOP_Detector (YAML wordlists + penalty weights); Aboudjem/humanizer-skill (43 named patterns); blader/humanizer; hardikpandya/stop-slop; mshumer/unslop (profiles a *specific model's* defaults empirically — the right architecture for a per-model blocklist).

### A2. Structural LLMisms

**Wu et al. — "The Rise of Verbal Tics in Large Language Models" (arXiv:2604.19139, 2026 preprint — provisional).** 8 frontier models × 160k responses × 120 human raters. Five-category tic taxonomy; Verbal Tic Index 0.295–0.590 by model; tic tokens up to 12.3% of output; tics rise ~110% from turn 1→20; sycophancy anti-correlates with naturalness at r=−0.87. Frames tics as an "alignment tax" of RLHF.

**Freeburg — "The Last Fingerprint: How Markdown Training Shapes LLM Prose" (arXiv:2603.27006, 2026 preprint — provisional).** The em-dash study: 12 models, ~240k words. Unconstrained rates: GPT-4.1 10.62/1,000 words, Claude Opus 9.09, vs **human baseline 3.23**. Em-dashes survive "no markdown" instructions; raw frequency is weak alone (human range 0.33–17.12/1k) but ~3× human baseline is a usable soft flag.

**Shaib et al. — "Measuring AI 'Slop' in Text" (arXiv:2509.19163).** Expert-derived slop taxonomy (incl. "Templatedness") with span-level annotation. Sobering: humans agree moderately (α≈0.34–0.45) but **automatic span-level slop detection is weak** (linear AUPRC ~0.52–0.55; LLM-judge κ≈0).

**Rule-of-three and "it's not X, it's Y":** no dedicated quantitative paper. Regex-implementable but lack published human-baseline frequencies — calibrate thresholds against your own author corpus.

### A3. Statistical signatures — and do they survive author imitation?

**Detector lineage:** GLTR (arXiv:1906.04043) → **DetectGPT** (ICML 2023; negative-curvature perturb-and-compare, 0.95 AUROC) → **Fast-DetectGPT** (arXiv:2310.05130; one forward pass, AUROC 0.99/0.91, 340× faster) → **Binoculars** (ICML 2024; arXiv:2401.12070; observer/cross-perplexity ratio; >90% TPR at 0.01% FPR; 99.67% accuracy on ESL essays — fixes the non-native false-positive problem) → **Ghostbuster** (NAACL 2024; 99.0 F1, black-box generators) → **GPT-who** (Findings NAACL 2024; arXiv:2310.06202; UID-theoretic surprisal features; beats GLTR/GPTZero/DetectGPT by >20%, cheap and interpretable). **GPTZero mechanics:** GPT-2-class perplexity + burstiness = SD of per-sentence perplexity; now 1 of 7 undisclosed production components.

**Adversarial picture:** Sadasivan et al. (arXiv:2303.11156) — detection gets information-theoretically harder as distributions converge. Krishna et al. (NeurIPS 2023, DIPPER): one paraphrase pass collapses DetectGPT 70.3%→4.6%.

**The load-bearing finding — style imitation does NOT erase statistical signatures:**
- **Wang et al., "Catch Me If You Can? Not Yet" (arXiv:2509.14543):** LLM imitations remain stylometrically separable from the genuine author everywhere (AV up to 94–97% in formal registers); only 0–54% pass GPTZero.
- **Jemama & Kumar (IEEE UEMCON 2025; arXiv:2509.24930):** the cleanest single statement — few-shot style prompting achieved up to 99.9% style-agreement, **yet perplexity stayed at 15.2 vs human 29.5**. Style prompting reshapes vocabulary and surface syntax, not the model's low-entropy token-selection process.
- Binoculars' own persona test ("write as Carl Sagan") cost only ~1% sensitivity.

**Area A verdict — usable today.** (1) Lexicon-layer linting immediately buildable: Kobak's 407 style words (with effect sizes) ∩ Liang's tables ∩ Matsui's 103 — as a **rotating, model-era-aware blocklist**, weighting clusters, not single hits. (2) Structural linting buildable but mostly self-calibrated (only em-dash density and verbal tics have published numbers). (3) Binoculars or Fast-DetectGPT as backstop scorer — understanding that **sounding like your author and passing statistical detectors are orthogonal goals**; the latter requires entropy-level intervention (sampling changes, human edit passes), not better voice prompts.

---

## AREA B — Prose rhythm, meter, cadence in non-poetry text

### B1. Computational prose rhythm

**Sentence-length burstiness** — mature, solved. **O'Sullivan et al., "Stylometric comparisons of human versus AI-generated creative writing" (Humanities & Social Sciences Communications, Dec 2025):** AI fiction shows significantly lower burstiness across all corpora, **even where human readers couldn't distinguish AI from human text** — the rhythm signal survives when perception fails. Humans also use more dashes/ellipses/fragments.

**Keeline & Kirby — "Auceps syllabarum: A Digital Analysis of Latin Prose Rhythm" (JRS 109, 2019; github.com/TylerKirby/latin-prose-rhythm).** The definitive scansion-applied-to-prose work: syllable-weight assignment → clause-ending clausula matching → significance testing vs null model, run on all major Latin prose authors. Every author is measurably rhythmical — they favor different clausulae. Architecture directly portable to an English stress-based "prose cadence detector" (CMUdict stress for Latin quantity); **nobody has built the English version — a genuine gap.**

**Corbara, Moreo & Sebastiani — "Syllabic Quantity Patterns as Rhythmic Features for Latin Authorship Attribution" (arXiv:2110.14203).** Scansion-derived rhythmic features **measurably improve authorship attribution** over topic-agnostic lexical features across three datasets. Rhythm is an authorial fingerprint, demonstrated with ML.

**Pethe et al. — "Prosody Analysis of Audiobooks" (IEEE ICSC 2025; arXiv:2310.06930).** The one real bridge from TTS prosody to written style: predicts pitch/volume/rate at phrase level from text alone, trained on 93 aligned book/audiobook pairs; beats commercial TTS at matching human narrators in 22/24 held-out books. Supporting: **Helsinki Prosody Corpus + BERT prominence prediction** (arXiv:1908.02262; github.com/Helsinki-NLP/prosody) — per-word "would-be-stressed-aloud" labels for any text.

**Chafe — "Punctuation and the Prosody of Written Language" (Written Communication, 1988).** Theoretical bedrock: punctuation units approximate spoken intonation units — a "covert prosody." Never computationally operationalized, but nearly free to implement: burstiness over **inter-punctuation intervals**.

**Lagutina et al. — ProseRhythmDetector (FRUCT 26, 2020).** Detects named rhetorical rhythm figures (anaphora, epiphora, symploce, anadiplosis, polysyndeton, aposiopesis) in English/Russian prose. Captures repetition-based rhythm that length statistics miss.

### B2. Individual rhythmic fingerprints & information density

**Zimmerman — "Narrative Fingerprints" (arXiv:2604.01073, 2026 preprint, single-author — suggestive).** Paragraph-embedding novelty curves + SAX motifs: 43.3% of authors show significantly non-chance pacing signatures at book level. Semantic pacing — rhythm at paragraph scale — is authorial.

**UID lineage:** Genzel & Charniak (ACL 2002) → Levy & Jaeger UID hypothesis → **Tsipidi et al., "Surprise! UID Isn't the Whole Story" (EMNLP 2024; arXiv:2410.16062)** — surprisal contours track hierarchical discourse structure; document-level information-density *shape* is measurable and model-able. UID is contested — a productive lens, not law. Detection payoff: **GPT-who** and **TRACE/GHOSTWRITEBENCH (arXiv:2603.28054, 2026)** — token-level rank/entropy transition matrices compared by Jensen-Shannon distance; near-perfect human-vs-LLM separation; degrades most gracefully on unseen authors.

**Cursus/clausulae tradition:** classical→medieval accentual cadences; modern computational revival is Latin-only. English cursus claims remain impressionistic — no computational study exists.

### B3. Tools that score or compare rhythm

**SETEC Voiceprint (github.com/anotherpanacea-eng/setec-voiceprint) — the single most relevant tool found.** Glass-box stylometric framework: 56 measurements across 9 families, explicitly including sentence-length burstiness, sentence-length SD, punctuation cadence, FKGL-SD, POS-bigram entropy/KL, mean-dependency-distance SD, adjacent-sentence drift, Burrows' Delta — built for **target-text-vs-baseline-corpus comparison**. Python (spaCy/SciPy/sklearn), CLI + Claude Code plugin, includes a Binoculars-style perplexity comparator. Deliberately refuses single AI-verdict scores. GPL-3.0.

Others: **Prosodic v3 / Cadence** (quadrismegistus — metrical scansion + phrasal stress on prose); **textstat + TextDescriptives**; **StyloMetrix** (arXiv:2309.12810); visual aids: Musical Text (Obsidian), ReadCalc Sentence Pacing, Entangled Text Sentence Rhythm Analyzer; thinkst/zippy's standalone burstiness.py.

**Area B verdict — usable today.** Sentence-length and punctuation-interval burstiness are solved, cheap, validated as both human/AI discriminators and author fingerprints. Surprisal-contour/UID features implementable via GPT-who/TRACE-style code with any small LM. Proven-but-unbuilt opportunity: an English clausula detector (CMUdict stress-tagging of clause-final words + n-gram pattern stats vs null model). Notable asymmetry: academic style-transfer research never names rhythm as a first-class target, while practitioner tools converge on burstiness as the single highest-leverage signal.

---

## The Linter: 18 measurable LLMism features

Each computable deterministically (no LLM judge unless noted). **Calibrate all thresholds against the target author's corpus, not universal constants.**

**Lexical (evidence: Kobak, Liang, Matsui, Wikipedia)**
1. **Tier-1 slop lexeme rate** — hits per 1,000 words against Kobak's 407 ∩ Liang's tables ∩ Matsui's 103 (core: delve, underscore, intricate, meticulous, commendable, showcase, boast, realm, pivotal, crucial, notably, multifaceted, tapestry, testament). Weight by effect size; version by model era.
2. **Slop-phrase/collocation rate** — "stands as a testament," "plays a vital/pivotal role," "in today's fast-paced world," "rich tapestry," "it's important/worth noting," "shed light on," "deep dive," "game changer," "paving the way," "at the forefront."
3. **Lexical diversity floor** — MTLD/MATTR below author baseline.
4. **Elegant-variation index** — synonym-cycling for a repeated referent where the author would repeat the word.

**Syntactic/constructional (evidence: Wikipedia taxonomy; self-calibrated)**
5. **Participial-tail rate** — % sentences ending in comma + "-ing" clause ("...highlighting the need for X").
6. **Negative-parallelism rate** — "not just X, but Y" / "it's not X; it's Y" per 1,000 words.
7. **Rule-of-three density** — triadic coordination (A, B, and C) per sentence, esp. adjective/gerund triplets.
8. **Copula-avoidance ratio** — "serves as / stands as / represents / marks" vs plain "is/are", against author baseline.
9. **Hedging-boilerplate count** — "it is important to note," "it's essential to consider," "while X, it's worth Y."
10. **Sycophancy/chat-artifact scan** — "Great question," "I hope this helps," "Certainly!", knowledge-cutoff disclaimers (should be zero in copy).

**Structural/rhythmic (evidence: O'Sullivan, GPTZero, Freeburg, Chafe, SETEC)**
11. **Sentence-length burstiness** — SD (and dispersion index) of sentence length vs author baseline; flag if SD < ~0.75× author's. The single best-evidenced rhythm feature.
12. **Consecutive-length monotony** — % adjacent sentence pairs within ±5 words; flag 3+ consecutive near-equal sentences.
13. **Short-sentence deficit** — fraction of sentences ≤6 words vs author baseline (AI under-produces fragments and punchy sentences).
14. **Punctuation-interval burstiness** — SD of token counts between punctuation marks (Chafe-derived; near-free).
15. **Em-dash density** — per 1,000 words vs author baseline; >~2× author rate or >6/1,000 absolute is a strong flag (human mean 3.23; GPT-4.1 10.6). Also colon-before-list and bold/title-case leakage.
16. **Paragraph-length uniformity** — CV of paragraph lengths; low CV = templating. Plus scaffold-marker scan ("In conclusion," "Overall," "Future Outlook").
17. **Punctuation-richness deficit** — ellipses, dashes-as-interruption, fragments, parentheticals per 1,000 words vs author (humans use dramatically more).

**Statistical (requires a small LM; evidence: GPT-who, TRACE, Binoculars, Jemama & Kumar)**
18. **Surprisal profile match** — mean/SD of per-token surprisal under a small LM (GPT-2-class) vs the author's profile; optionally full TRACE-style entropy-transition matrix with JS distance to the author corpus. Catches the residue style prompting never fixes.

**Recommended architecture:** features 1–17 as a deterministic linter (regex + spaCy + TextDescriptives; SETEC Voiceprint is a working reference for 11–17 plus author-baseline comparison via Burrows' Delta); feature 18 as a scoring pass; Binoculars as end-of-pipe validation backstop. Score everything as *distance from the target author's measured baseline*; treat cluster co-occurrence, not any single tell, as the signal.

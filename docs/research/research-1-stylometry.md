# Computational Stylometry for Voice Fingerprinting: Research Report

Scope: 2022–2026 frontier plus still-standing foundational work. Goal context: capture an individual author's voice precisely enough to (a) steer LLM-generated copy toward it and (b) verify output against it.

---

## 1. Stylometric features that best capture individual voice

**Function words / Burrows' Delta** — Burrows (2002) and the Mosteller–Wallace tradition remain the single most validated signal for individual authorship: relative frequencies of the ~100–500 most frequent (function) words, compared via z-score distance. Evert et al. (2017, "Understanding and explaining Delta measures") showed Cosine Delta is the most robust variant. Content-light, hard to consciously fake, works from ~2–5k words. Reference implementation: the stylo R package. **Extractability: trivial** (tokenize + count). This is the backbone feature.

**Character n-grams (3–4 grams)** — Still the strongest single baseline in the entire field. Sapkota et al. (NAACL 2015) showed *which* character n-grams matter (affix and punctuation-anchored n-grams beat whole-word ones); at PAN 2022 the organizers' naive character-4-gram cosine baseline (CNGDIST) beat most neural submissions under cross-genre shift. Captures morphology, punctuation habits, and spelling quirks simultaneously. **Extractability: trivial.**

**POS n-grams and syntactic/dependency features** — POS bigrams/trigrams approximate syntactic preference cheaply; deeper signals include dependency-triple frequencies, mean dependency distance, and clause-embedding depth. Grieve's (2007) large feature comparison found syntactic features weaker alone than function words/character n-grams but complementary. **Extractability: easy via spaCy;** TextDescriptives computes dependency distance and POS proportions out of the box.

**Sentence-length and rhythm distributions (burstiness)** — Sentence-length *variance* and the shape of the length distribution (not just the mean) is a genuine authorial signature and, notably, one of the clearest discriminators between human and LLM text (LLMs regress to mid-length uniformity — "burstiness" collapse). Track the distribution (e.g., histogram or log-normal fit parameters), plus paragraph-length rhythm. **Extractability: trivial.**

**Punctuation habits** — Comma density, semicolon/dash/parenthesis rates, serial-comma choice, quote style. Darmon et al. (2021, "Pull out all the stops," Royal Society) showed punctuation sequences alone can identify authors. Also captured implicitly by character n-grams. **Extractability: trivial.**

**Discourse markers and hedging** — Connective choice ("however" vs "but" vs "though"; sentence-initial "And") and hedge/booster profiles (Hyland's *Metadiscourse* framework: "perhaps," "clearly," "I think," epistemic modals) are highly personal and register-stable. Less studied for verification specifically, but directly *actionable* for steering — they translate into instructions an LLM can follow. **Extractability: lexicon lookup;** no dominant open library, build a custom lexicon counter (Hyland's published hedge/booster lists are a starting point).

**Biber's multidimensional analysis (MDA)** — Biber (1988) maps texts onto ~6 functional dimensions (involved vs. informational, narrative, etc.) from 67 lexico-grammatical features. Excellent for *register* characterization and for producing a human-readable style profile, but it's a genre instrument, not an individual-identity instrument — individuals separate on it only weakly. Open implementation: biberpy / MAT (Multidimensional Analysis Tagger). **Verdict: use for the interpretable "style card" that drives LLM prompting, not for verification.**

**What we'd implement first (ranked):** (1) function-word frequency vector + Cosine Delta; (2) character 3–4-grams; (3) sentence-length distribution/burstiness; (4) punctuation profile; (5) POS bigrams + dependency distance; (6) discourse-marker/hedging lexicon profile. The first five are the verification workhorses; #6 plus MDA-style summaries are the steering-side profile.

---

## 2. Authorship verification SOTA (PAN shared tasks)

The trend line matters more than any single system:

- **PAN 2020/2021** (fanfiction pairs, open-set in 2021): winner both years was **Boenninghoff et al.** — Siamese hierarchical LSTM metric learning with Bayes-factor score calibration (overall 0.9545, AUC 0.987 in 2021). Code: github.com/boenninghoff/pan_2020_2021_authorship_verification. [PAN 2021 overview](https://downloads.webis.de/publications/papers/kestemont_2021.pdf).
- **PAN 2022** (cross-discourse-type: essays/emails/texts/memos — the closest analog to real-world voice verification): scores collapsed to ~0.59 overall, and the organizers' **character-4-gram cosine baseline beat most neural systems**. Lesson: neural pair-classifiers overfit topic/genre; cheap n-gram features are more shift-robust. [Overview](https://ceur-ws.org/Vol-3180/paper-184.pdf).
- **PAN 2023**: verification winner ~0.623; task began pivoting to multi-author style-change detection.
- **PAN 2024–2025**: pivoted entirely to human-vs-LLM ("Voight-Kampff") detection — 2024 winner fused Binoculars-style perplexity signals ([overview](https://ceur-ws.org/Vol-3740/paper-225.pdf)); 2025 winner used fine-tuned small-LLM classifiers (mean 0.989).
- **Classic methods still in service**: Impostors method (Koppel & Winter 2014) and Unmasking (Koppel & Schler) — both in stylo; compression-based distance (Halvani, arXiv:1706.00516).
- **Survey**: Huang, Chen & Shu, "Authorship Attribution in the Era of LLMs" (SIGKDD Explorations 2025, arXiv:2408.08946) — best current field map; flags cross-domain generalization as unsolved.
- Directly relevant 2026 result: "Authorship Impersonation via LLM Prompting does not Evade Authorship Verification" (arXiv:2603.29454) — GPT-4o style impersonations were still caught by both classical (n-gram, Impostors) and neural (LUAR, STAR) verifiers.

**Verdict:** Don't build a PAN-style pair classifier. Build a **one-class, distance-to-author model**: embed known-genuine corpus, form a centroid/distribution, score candidates by calibrated distance — ensembled with a character-n-gram/function-word cosine check (the topic-robust signal PAN 2022 vindicated), plus a perplexity/burstiness "LLM texture" check, since the failure mode is often "right voice, wrong texture."

---

## 3. Learned style embeddings

All of these have **open weights on HuggingFace** — this area is genuinely ready to use:

- **LUAR** (Rivera-Soto et al., EMNLP 2021) — contrastive transformer trained episodically on Reddit million-user data; 512-dim; the field's standard authorship embedding. [Paper](https://aclanthology.org/2021.emnlp-main.70/) · [Code](https://github.com/LLNL/LUAR) · [HF: rrivera1849/LUAR-MUD](https://huggingface.co/rrivera1849/LUAR-MUD). Caveat: probing work (TACL 2023, arXiv:2308.11490) shows it heavily conflates topic with style (near-chance on content-controlled tests).
- **Wegmann et al. STEL + CISR** — STEL (EMNLP 2021, [GitHub](https://github.com/nlpsoc/STEL)) is the standard *evaluation* framework for content-independent style; the companion model from "Same Author or Just Same Topic?" (arXiv:2204.04907) uses conversation-controlled hard negatives — [HF: AnnaWegmann/Style-Embedding](https://huggingface.co/AnnaWegmann/Style-Embedding), 768-dim RoBERTa. Note: CISR is not a separate system; it's this model's nickname.
- **StyleDistance** (NAACL 2025, arXiv:2410.12757) — current best-in-class disentanglement: trains on synthetic near-parallel pairs varying only on ~40 explicit style features. On the strict STEL-or-Content test: StyleDistance 0.29 vs. CISR 0.22 vs. LUAR 0.03. MIT license, sentence-transformers API. [HF: StyleDistance/styledistance](https://huggingface.co/StyleDistance/styledistance); multilingual mStyleDistance (arXiv:2502.15168).
- **Watch list**: STAR (2024, supervised contrastive, no public weights found); MSR (EMNLP 2025, arXiv:2509.16531, multilingual content-masking); STEB benchmark (2026, from the LUAR+CISR authors — likely the canonical leaderboard going forward).

**Verdict:** Pull **StyleDistance first** (best topic-invariance — critical since generated copy covers new topics), **CISR second** (cross-check/ensemble), **LUAR third** as a well-validated author-identity signal despite entanglement. Validate your own setup with STEL-style held-out-topic tests.

---

## 4. Style-content disentanglement — what works, what fails

Honest summary: **architectural disentanglement is unreliable and arguably ill-posed; operational pipelines work.**

- **Cautionary core**: Lample et al., "Multiple-Attribute Text Rewriting" (ICLR 2019) showed adversarial training does *not* produce disentangled latents even when explicitly designed to, and an entangled back-translation model wins anyway. The Jin et al. TST review (arXiv:2010.12742) notes style/content are causally confounded. Evaluation itself is shaky (arXiv:2306.00539).
- **Most relevant recent negative result**: "Catch Me If You Can? Not Yet" (2025, arXiv:2509.14543) — across 400+ everyday authors, few-shot LLM style imitation defaults to generic tone, with diminishing returns from more exemplars; informal registers are hardest.
- **What works**: in-context exemplars beat prior methods even at ~500 words of author data (arXiv:2212.08986); LoRA fine-tuning per author when you have tens of thousands of words; **neutralize-then-restyle pipelines** beat direct transfer; and **contrastive activation steering** (arXiv:2503.05213) offers an inference-time style dial.

**Verdict:** Don't chase a disentangled latent. Steer with style-profile-driven prompting (explicit measured features + few-shot exemplars) → LoRA if corpus volume allows → verify on held-out topics with the ensemble from §2/§3.

---

## 5. Graphs / knowledge graphs for style — honest assessment: thin

- GNN-on-text work exists (Siamese GCN at PAN scored 90–92% *on long texts*; [MDPI paper](https://www.mdpi.com/2227-7390/10/2/277)) but loses to transformer/feature methods on short texts, which is the regime that matters here.
- The complex-networks tradition (word-adjacency networks, small-world metrics) is real but methodologically isolated: tiny datasets, and the primary papers **don't benchmark against TF-IDF/n-gram baselines at all**.
- **Knowledge graphs for style: no research thread exists.** KGs encode *what* is said (entities/relations); style is *how*. Everything found under "KG + text quality" is fact-verification, a different problem.
- Legitimate adjacent use: a KG could store the *fingerprint itself* (author → feature → value provenance) as an engineering choice, but that's a data-modeling convenience, not a modeling advantage.

**Verdict: mostly not a real thread.** Graphs add no demonstrated accuracy over embeddings + features for voice fingerprinting. At most, run a cheap ablation with dependency-graph features; do not make it an architectural bet.

---

## 6. Practical tooling

| Tool | What | Status |
|---|---|---|
| [stylo (R)](https://github.com/computationalstylistics/stylo) | Burrows/Cosine Delta + 15 variants, Impostors, rolling stylometry | Actively maintained (v0.7.71, June 2026); reference implementation |
| [TextDescriptives](https://github.com/HLasse/TextDescriptives) | spaCy pipeline: descriptive stats, readability, dependency distance, POS proportions | Best-maintained Python base layer |
| [writeprints-static](https://github.com/literary-materials/writeprints-static) | 557-feature classic Writeprints vector, sklearn API | Usable, thinly maintained |
| [StyloMetrix](https://github.com/ZILiAT-NASK/StyloMetrix) | spaCy-based multilingual stylometric vectors | Moderate; last release 2024 |
| [faststylometry](https://github.com/fastdatascience/faststylometry) | Python Burrows' Delta with calibrated probabilities | Active, narrow scope |
| [JGAAP](https://github.com/evllabs/JGAAP) | Java GUI, 20k method combos | Stale (2021); benchmark reference only |
| LIWC | Psycholinguistic lexicons | Commercial; use [Empath](https://github.com/Ejhfast/empath-client)/psyLex if needed |

**Recommended stack:** spaCy + TextDescriptives base layer; custom function-word and character-n-gram counters (trivial, highest signal); writeprints-static for the literature-standard vector; stylo via subprocess for validated Delta/Impostors verification math; StyleDistance + CISR + LUAR from HuggingFace for embeddings.

---

## Bottom line — recommended architecture

1. **Fingerprint** = two artifacts: (a) an interpretable feature profile (function-word vector, char n-grams, sentence-length distribution, punctuation rates, POS bigrams, discourse/hedge lexicon rates) and (b) style-embedding centroids (StyleDistance primary, CISR + LUAR secondary).
2. **Steering** = translate the interpretable profile into explicit generation instructions + few-shot exemplars; LoRA only if the author corpus is large; the measured profile doubles as the rubric.
3. **Verification** = three-signal ensemble, all scored on held-out topics: embedding distance-to-centroid (calibrated threshold), char-n-gram/Delta cosine distance (topic-robust check), and an LLM-texture check (perplexity/burstiness).
4. **Skip**: knowledge graphs as a modeling substrate (no evidence), architectural style-content disentanglement (unreliable), from-scratch Siamese training (needs data you won't have).

**Ready-to-use open weights/code:** StyleDistance (MIT), AnnaWegmann/Style-Embedding, LUAR-MUD/CRUD (Apache-2.0), stylo, TextDescriptives, writeprints-static, STEL evaluation framework, Boenninghoff PAN winner code.

**Hype vs. usable:** Usable now — style embeddings, classic feature stylometry, STEL-style evaluation. Promising but immature — activation steering, neutralize-then-restyle. Thin/hype — knowledge graphs for style, clean latent disentanglement, GNN stylometry for short texts.

Citation caveat: a few 2026 arXiv IDs above (impersonation study 2603.29454, STEB benchmark) are very recent — re-verify before quoting in client-facing material.

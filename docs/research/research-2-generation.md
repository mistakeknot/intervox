# Making LLMs Write in a Specific Author's Voice: Research Report (2023–2026)

## 1. Fine-tuning approaches (LoRA/QLoRA, DPO/ORPO/KTO)

- **Chakrabarty, Ginsburg & Dhillon, "Readers Prefer Outputs of AI Trained on Copyrighted Books over Expert Human Writers"** ([arXiv 2510.13939](https://arxiv.org/abs/2510.13939)) — the single most decision-relevant fine-tuning result. Blinded MFA-writer evaluation: prompted imitations strongly *disfavored* on stylistic fidelity (odds ratio **0.16**); fine-tuning on the author's works flipped it to strongly *preferred* (OR **8.16** with expert readers; 16.65 general). Hard evidence that fine-tuning crosses a fidelity threshold prompting can't. Verdict: **needs open-weights or a fine-tuning API**.
- **"Capturing Classic Authorial Style in Long-Form Story Generation with GRPO Fine-Tuning"** ([arXiv 2512.05747](https://arxiv.org/abs/2512.05747)) — most rigorous academic pipeline: style-similarity judge (sentence-transformer with authorship-verification supervision) calibrated into a reward, GRPO fine-tune of an 8B generator. Avg style score 0.893 across four target authors. Needs 4×H100s, ~100K training pairs. Verdict: **research/enterprise-only**, but the judge-as-reward design is the blueprint for serious training spend.
- **Didier Lopes, personal blog LoRA case study** ([didierlopes.com](https://didierlopes.com/blog/fine-tuning-a-llm-on-my-blog-posts/)) — 91 blog posts → ~2,100 Q&A pairs, LoRA on Phi-3-mini via MLX. Measurable style adoption (+27.6% word overlap) but self-assessed incomplete: "learned how I write more than what I know." Verdict: realistic picture of small-corpus LoRA.
- **Corpus contamination failure mode** ([pithycyborg.com](https://www.pithycyborg.com/can-lora-fine-tuning-on-ai-slop-collapse-your-voice/)) — if the sample corpus was itself AI-assisted, a LoRA learns a "blended statistical ghost" of prior models. Recommends AI-detection screening of training data, a ≥20,000-word clean-human reference corpus, and a **variance test** (same prompt 10×; suspiciously tight clustering = averaged-LLM patterns). Directly actionable for client onboarding QA.

**DPO/ORPO/KTO with "my sentence vs. LLM paraphrase" pairs:** no published work does exactly this — **a genuine gap**. Nearest neighbors: **StyleVector** ([arXiv 2503.05213](https://arxiv.org/html/2503.05213v1)) constructs exactly that pair but converts it into an activation-steering vector (17–287 examples/user, +8% over PEFT, ~1700× less storage than per-user LoRA); **PRELUDE/CIPHER** (NeurIPS 2024, [arXiv 2404.15269](https://arxiv.org/html/2404.15269v1)) learns latent style preferences from user *edits* — prompt-level adaptation, 31–73% reduction in cumulative edit cost.

**Corpus-size picture:** ~500–2,000 quality examples for LoRA voice capture; Shortwave fine-tunes small models on 400–500 examples for autocomplete; 20,000+ words is the practitioner floor for a trustworthy reference corpus. Diversity across registers matters more than volume.

## 2. Activation steering / representation engineering

- **Contrastive Activation Addition** (Rimsky et al., ACL 2024, [arXiv 2312.06681](https://arxiv.org/abs/2312.06681)) — foundational method. **Needs open-weights.**
- **"Style Vectors for Steering Generative LLMs"** (EACL 2024 Findings, [arXiv 2402.01618](https://arxiv.org/html/2402.01618v1); [code](https://github.com/DLR-SC/style-vectors-for-steering-llms)) — AUC ≥ 0.97 style separability; names individual-voice mimicry as the extension. **Needs open-weights.**
- **StyleVector** ([arXiv 2503.05213](https://arxiv.org/pdf/2503.05213)) — per-user style vector from contrastive activations, training-free, beats RAG and PEFT on LaMP/LongLaMP. **Needs open-weights.**
- **SteerX** ([arXiv 2510.22256](https://arxiv.org/pdf/2510.22256)) — disentangles style/persona/content steering directions. **Research-grade.**
- **Advisor Models** ([arXiv 2510.02453](https://arxiv.org/abs/2510.02453)) — the API-compatible reframing: a small trained open model generates per-instance steering guidance injected into a black-box frontier model's context (85–100% vs. 40–60% preference-match against static prompts). **The only "steering" pattern usable with commercial APIs.**

**Hard constraint:** every true steering method requires forward-pass access to hidden states — unavailable through Claude/GPT/Gemini APIs. Tooling (repeng, TransformerLens, baukit, steering-vectors) targets self-hosted models. **Verdict: needs open-weights across the board**; use the Advisor-Models pattern otherwise.

## 3. Prompting-based approaches at the frontier

- **"Catch Me If You Can? Not Yet"** (EMNLP Findings 2025, [arXiv 2509.14543](https://arxiv.org/abs/2509.14543)) — the key benchmark. 5-shot ICL, GPT-4o/Gemini-2.0-Flash/DeepSeek-V3/Llama-4 et al., 400+ real authors, 40K+ generations. **Sharp domain split**: news/email attribution ~87–93%; blogs AV 16–21%, Reddit ~26–36%. Human-likeness "always below 55%, often under 20%." 2→10 exemplars: diminishing returns — **ICL plateaus fast**. Verdict: **usable via API today for structured/professional registers** (good news for marketing copy); informal personal voice remains open.
- **STYLL** (Patel, Andrews & Callison-Burch, [arXiv 2212.08986](https://arxiv.org/abs/2212.08986)) — canonical prompting-only recipe: neutralize source → LLM-extract style descriptors → few-shot restyle with pseudo-parallel pairs. Beat fine-tuned STRAP for low-resource authors. **Usable via API today.**
- **PerFine** ([arXiv 2510.24469](https://arxiv.org/html/2510.24469v1)) — training-free loop: GraphRAG retrieval → draft → critic LLM scores tone/vocabulary/sentence-structure/topic-relevance → revise → "knockout" keeps the stronger draft; +7.8–13.4% G-Eval over RAG baselines, plateaus at 3–5 rounds. Caveats: same-model self-critique amplifies self-bias ([arXiv 2402.11436](https://arxiv.org/abs/2402.11436)); a **LUAR stylometric-critic loop closed 71–75% of the style gap** ([arXiv 2605.02620](https://arxiv.org/abs/2605.02620)). **Usable via API today** (stylometric critic = one small self-hosted model).
- **Reinhart et al., "Do LLMs Write Like Humans?"** ([arXiv 2410.16107](https://arxiv.org/abs/2410.16107)) — why the ceiling exists: instruction-tuned models are *more* stylometrically distinguishable from humans than base models (RLHF entrenches house style); fingerprints live in grammar — participial clauses at 2–5× human rates, nominalizations 1.5–2×. Corroborated by 98% stylometric detection on 10-sentence samples ([arXiv 2507.00838](https://arxiv.org/html/2507.00838v2)) and forensic AV unmasking GPT-4o impersonations ([arXiv 2603.29454](https://arxiv.org/abs/2603.29454)).
- **Mikros (DSH 2025)** ([link](https://academic.oup.com/dsh/article/40/2/587/8118784)) — upper bound for exemplar stuffing: ~15,000-word verbatim excerpts in context; better than zero-shot but classifiers still separate real from imitation at 79.8–84.0%. Long exemplars > short.
- Practitioner: Nina Panickssery's recipe (style description + synthetic few-shot dialogue turns + explicit anti-cliché constraints) — [blog](https://blog.ninapanickssery.com/p/how-to-make-an-llm-write-like-someone).

**Verdict:** **Usable via API today** with a real, measured ceiling. The literature converges on *pipeline, not prompt*: structural style descriptor + long verbatim exemplars + 3–5 round critique-revise with a non-self critic.

## 4. Retrieval-augmented style ("style RAG")

- **LaMP / LongLaMP** (Salemi et al., ACL 2024, [benchmark](https://lamp-benchmark.github.io), [arXiv 2304.11406](https://arxiv.org/abs/2304.11406)) — retrieval of profile exemplars gives +12.2% zero-shot and +23.5% fine-tuned improvements. Retrieval in this literature is **topical/semantic** — structural/rhetorical-slot retrieval ("how does this author open?" / "how do they write a CTA?") is essentially unexplored → product-differentiation opportunity.
- **"Improving RAG for Personalization with Author Features and Contrastive Examples"** (ECIR 2025, [arXiv 2504.08745](https://arxiv.org/abs/2504.08745)) — inject explicit author-feature sentences plus **contrastive examples from other authors**; +15% relative over baseline RAG. Code released. **Usable via API today.**
- **Pearl** (Mysore et al., [arXiv 2311.09180](https://arxiv.org/abs/2311.09180)) — generation-calibrated retriever; low retriever confidence flags outputs needing revision. **Research-only** but the best retrieval-scoring idea found.
- **Shortwave Ghostwriter** (production, 2025) — vector-indexes full sent-mail history, retrieves top 5–10 similar past emails + precomputed style description per draft. Confirms semantic retrieval is what ships.

**Verdict: usable via API today; the most mature, lowest-risk technique in this report.**

## 5. Evaluation — measuring "sounds like author X"

- **LUAR** ([github.com/LLNL/LUAR](https://github.com/LLNL/LUAR)) — canonical authorship-embedding model; drop-in cosine-similarity style scorer. **Usable today.**
- **StyleDistance** (NAACL 2025, [arXiv 2410.12757](https://arxiv.org/abs/2410.12757), [HF](https://huggingface.co/StyleDistance/styledistance)) — stronger *content-independent* style embeddings. **Usable today.**
- **"Evaluating Style-Personalized Text Generation: Challenges and Directions"** (Microsoft 2025, [arXiv 2508.06374](https://arxiv.org/html/2508.06374v1)) — detecting "right genre" is easy, "this specific person" is hard (−28.6% accuracy on harder discrimination); **ensembles of n-gram + style-embedding + LLM-judge beat any single metric by up to 12%.**
- **"Can LLM be a Personalized Judge?"** (EMNLP Findings 2024, [arXiv 2406.11657](https://arxiv.org/abs/2406.11657)) — LLM-judge ≈70% agreement with humans, <60% on hard cases; uncertainty-gating lifts above 80% at coverage cost. Don't rely on LLM-judge alone.
- **"Theory-Grounded Evaluation Exposes the Authorship Gap in LLM Personalization"** (2026, arXiv 2604.26460) — benchmarks overstate personalization success; verify with authorship-verification tooling.
- Naming caveat: **"StyleBench" is an image benchmark**; LaMP/LongLaMP is the closest text equivalent. Human protocol gold standard: blinded expert pairwise preference with odds ratios (Chakrabarty et al.).

## 6. Commercial landscape (brief)

Dominant technique across **Jasper Brand Voice**, **Copy.ai**, **Writer.com**, **Rytr**, DIY Custom GPTs: **a style guide distilled from a handful of samples, injected as a system prompt** — despite "clone/train" marketing. Exceptions: **HyperWrite** (light RAG over personal documents); **Sudowrite Muse** (actual fine-tune, but genre-level). **Lex** positions AI as editor-not-ghostwriter. **Voiceprint** (Claude Code plugin) is methodologically the most serious sample-based approach: 5 samples across emotional registers, real stylometric analysis, explicit banned-phrase rejection, format-specific guidance. **Universal weakness:** instruction drift — voice degrades toward generic on longer/harder outputs. **No competitor exceeds prompt-injection + thin RAG** — a well-built pipeline beats the field.

---

## Ranked shortlist for a production system

**1. Style RAG backbone** — index the author's corpus; per generation retrieve semantically relevant exemplars **plus** explicit author-feature sentences and contrastive other-author examples (ECIR 2025 recipe). Mature, cheap, fully API-compatible, validated in production. Ship first.

**2. Structural style descriptor + iterative critique-revise with an external critic** — descriptor targeting grammar-level features (clause patterns, nominalization density, rhythm — where the real fingerprint lives per Reinhart), plus banned-phrase list; PerFine loop (3–5 rounds) with a **different model or a LUAR-based stylometric critic** as judge (closed 71–75% of the style gap; self-critique self-biases).

**3. Ensemble evaluation gate (LUAR/StyleDistance + LLM-judge)** — authorship-embedding similarity + uncertainty-gated LLM-judge + n-gram checks in both the critique loop and acceptance testing; add the 10×-variance test at onboarding to catch AI-contaminated client corpora. Doubles as the reward signal for a later fine-tune/steering tier.

*Fast-follow if self-hosted tier is added:* StyleVector-style per-author activation steering, and eventually LoRA on 500–2,000 curated examples — that's where the OR 0.16 → 8.16 fidelity jump lives.

**Scoping note:** the single most reproduced finding: structured/professional registers (email, news, marketing copy) transfer dramatically better than informal personal voice — the stated use case sits on the easy end of the documented difficulty spectrum.

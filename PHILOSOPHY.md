# intervox Philosophy

## Purpose

Make LLM-generated prose measurably sound like its author. Steer generation with a prose profile and the author's own retrieved sentences; verify output against a stylometric fingerprint computed from their corpus; never present a draft without its report card.

## North Star

A draft that passes intervox's verify gate should be one the author would sign without wincing. Success is measured, not vibed: distance from the author's baseline across rhythm, lexicon, constructions, and connective profile.

## Core positions

1. **Prose steers, numbers verify.** The natural-language profile is the LLM's interface; feature vectors are the referee's. interfluence and intervoice were right about the first half and silent on the second. Both halves or it isn't a loop.

2. **The author's corpus is the calibration set.** No universal thresholds. An em-dash rate that flags one author is another author's signature. Every lint feature scores as distance from the measured baseline.

3. **Clusters convict, single tells don't.** One "delve" is noise; "delve" plus uniform sentence lengths plus three rule-of-three triads plus participial tails is a verdict. The verify gate weighs co-occurrence.

4. **Registers are real.** Nobody writes a README the way they write a Slack message. One Foundation of invariants, register sections for dosage — inherited from intervoice because it matched both how profiles are actually kept and what the register literature says transfers.

5. **Exemplars beat adjectives.** Retrieved verbatim passages from the author's corpus outperform style descriptions in every benchmark that compares them. The apply loop always retrieves before it drafts.

6. **Honest ceilings.** Voice fidelity and beating AI detectors are orthogonal; indistinguishability is not the product. The target is "the author after a good editor," verifiably close to their own baseline. Say so.

7. **No heavyweight machinery before it earns its keep.** Stdlib engine, no server, no build step. Embeddings and surprisal scoring arrive as optional tiers only when the deterministic features stop being the binding constraint.

## Working Priorities

- Verification loop correctness before feature breadth
- Fingerprint fidelity (garbage baseline, garbage gate)
- Migration dignity: predecessors' data imports cleanly, nothing is orphaned

## Decision Filters

- Does this make the gate more trustworthy, or just the prompt longer?
- Can the author see *why* a draft failed, with numbers?
- Would this threshold survive an author whose natural style resembles the tell?
- Can we revert safely if assumptions fail?

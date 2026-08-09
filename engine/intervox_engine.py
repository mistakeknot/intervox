"""intervox_engine — stylometric fingerprinting and LLMism linting.

Single-file engine for the intervox Claude Code plugin. Everything here is
Python 3.11+ standard library only: argparse, json, re, statistics, math,
pathlib, collections, textwrap. No pip dependencies.

Commands (see main() / build_parser()):
    fingerprint  — build a baseline stylometric profile from a corpus
    lint         — compare a draft against a baseline, feature by feature
    verify       — run lint, reduce to a pass/revise/reject verdict + score
    retrieve     — TF-IDF paragraph retrieval over a corpus
    registers    — list register sections in a voice profile markdown file

Design note: every measurement function takes plain strings/lists and
returns plain dicts/numbers so it can be unit tested without touching the
filesystem or argparse at all.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

VERSION = "0.2.0"

# ---------------------------------------------------------------------------
# Markdown / text preprocessing
# ---------------------------------------------------------------------------

# Order matters: strip fenced code blocks before inline backticks, so a fence
# marker never gets misread as three inline-code spans.
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]*)`")
_HEADING_RE = re.compile(r"(?m)^#{1,6}\s+")
_LIST_MARKER_RE = re.compile(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_BOLD_ITALIC_RE = re.compile(r"(\*\*\*|\*\*|\*|___|__|_)")


_FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)
_TERMINAL_CHARS = ".!?:;"


def strip_markdown(text: str) -> str:
    """Remove common markdown syntax while preserving paragraph boundaries.

    Corpus files carry YAML frontmatter (ingest convention) — stripped here so
    provenance keys never pollute the stats. Headings, list items, and
    paragraph-final lines get terminal punctuation appended when missing:
    without it, block elements merge into one enormous "sentence" and wreck
    every rhythm statistic (found dogfooding on a real blog post: a 757-word
    "sentence").
    """
    text = _FRONTMATTER_RE.sub("", text)
    text = _CODE_FENCE_RE.sub(" ", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)

    lines = text.split("\n")
    out_lines: list[str] = []
    for i, line in enumerate(lines):
        is_heading = bool(_HEADING_RE.match(line))
        is_list_item = bool(_LIST_MARKER_RE.match(line))
        line = _HEADING_RE.sub("", line)
        line = _LIST_MARKER_RE.sub("", line)
        line = _LINK_RE.sub(r"\1", line)
        line = _BOLD_ITALIC_RE.sub("", line)
        stripped = line.rstrip()
        if stripped:
            next_blank = i + 1 >= len(lines) or not lines[i + 1].strip()
            needs_terminator = (
                (is_heading or is_list_item or next_blank)
                and stripped[-1] not in _TERMINAL_CHARS
            )
            if needs_terminator:
                stripped = stripped + "."
            # Headings and list items are standalone blocks; isolate them so
            # they can never glue onto the following paragraph.
            if is_heading or is_list_item:
                out_lines.append("")
                out_lines.append(stripped)
                out_lines.append("")
                continue
        out_lines.append(stripped)
    return "\n".join(out_lines)


def extract_prose(raw_text: str) -> str:
    """Flowing prose only, for the distributional features (16-18).

    Dogfood round 1 showed function-word/connective/trigram cosines compare
    genre, not voice, when a table-heavy draft is scored against an all-prose
    corpus. So those three features run prose-to-prose: drop table rows,
    heading lines, and list fragments under 8 words (full-sentence list items
    are prose and stay), keep blockquote text minus its marker.
    """
    text = _FRONTMATTER_RE.sub("", raw_text)
    text = _CODE_FENCE_RE.sub(" ", text)
    kept: list[str] = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            kept.append("")
            continue
        if s.startswith("|"):  # table row or separator
            continue
        if _HEADING_RE.match(s):
            continue
        s = re.sub(r"^>\s?", "", s)  # blockquote marker; the text is prose
        is_list_item = bool(_LIST_MARKER_RE.match(s))
        s = _LIST_MARKER_RE.sub("", s)
        s = _INLINE_CODE_RE.sub(r"\1", s)
        s = _LINK_RE.sub(r"\1", s)
        s = _BOLD_ITALIC_RE.sub("", s)
        if is_list_item:
            if len(s.split()) < 8:  # fragment, not prose
                continue
            if s and s[-1] not in _TERMINAL_CHARS:
                s += "."
            kept.extend(["", s, ""])
            continue
        kept.append(s)
    final: list[str] = []
    for i, ln in enumerate(kept):
        st = ln.rstrip()
        if st:
            next_blank = i + 1 >= len(kept) or not kept[i + 1].strip()
            if next_blank and st[-1] not in _TERMINAL_CHARS:
                st += "."
        final.append(st)
    return "\n".join(final)


def paragraphs_of(text: str) -> list[str]:
    """Split cleaned text into paragraphs on blank lines."""
    raw = re.split(r"\n\s*\n", text)
    return [p.strip() for p in raw if p.strip()]


# --- sentence tokenizer -----------------------------------------------------

# Abbreviations whose trailing "." must not be treated as a sentence end.
# We mask the dot with a placeholder, split, then unmask.
_ABBREVIATIONS = [
    "e.g.", "i.e.", "etc.", "vs.", "cf.", "Dr.", "Mr.", "Ms.", "U.S.",
    "Fig.", "Eq.", "Sec.", "No.",
]
_DOT_MASK = " DOT "

_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z"(\'\d])')


def _mask_abbreviations(text: str) -> str:
    out = text
    for abbr in _ABBREVIATIONS:
        masked = abbr.replace(".", _DOT_MASK)
        # Case-sensitive except e.g./i.e./etc./vs./cf. which are lowercase by
        # convention; word-boundary-ish match via simple replace is fine here
        # since abbreviations are short and rare as substrings of other words.
        out = out.replace(abbr, masked)
    return out


def _unmask_abbreviations(text: str) -> str:
    return text.replace(_DOT_MASK, ".")


def split_sentences(text: str) -> list[str]:
    """Split text into sentence-like spans, protecting known abbreviations.

    Returns raw (unmasked) sentence strings, whitespace-trimmed, with no
    length filtering — callers decide what counts as a "real" sentence vs a
    fragment (see word_count_of / sentence stats below).

    Splits paragraph-first: a sentence never spans a blank line. The regex
    splitter needs an uppercase/digit follow-character, which lowercase-
    starting blocks (list items) don't provide — the paragraph boundary is
    the authoritative break there.
    """
    sentences: list[str] = []
    for para in paragraphs_of(text):
        flat = " ".join(para.split())  # collapse whitespace runs within the paragraph
        masked = _mask_abbreviations(flat)
        parts = _SENTENCE_SPLIT_RE.split(masked)
        sentences.extend(_unmask_abbreviations(p).strip() for p in parts if p.strip())
    return sentences


_WORD_RE = re.compile(r"[A-Za-z']+")


def words_of(text: str) -> list[str]:
    """Whitespace/punctuation-tokenized words (letters + apostrophes only)."""
    return _WORD_RE.findall(text)


def word_count_of(s: str) -> int:
    return len(words_of(s))


MIN_SENTENCE_WORDS = 3  # sentences shorter than this count as fragments


def classify_sentences(sentences: list[str]) -> tuple[list[str], list[str]]:
    """Split sentence list into (full_sentences, fragments) by word count."""
    full, frag = [], []
    for s in sentences:
        (full if word_count_of(s) >= MIN_SENTENCE_WORDS else frag).append(s)
    return full, frag


# ---------------------------------------------------------------------------
# Slop lexicon + phrases (module constants, overridable via --lexicon JSON)
# ---------------------------------------------------------------------------

TIER1_LEXEMES = {
    "delve", "delves", "delving", "underscore", "underscores", "underscoring",
    "tapestry", "testament", "meticulous", "meticulously", "commendable",
    "multifaceted", "intricate", "intricacies", "showcase", "showcasing",
    "boast", "boasts", "garner", "garnered", "bolster", "bolstered",
    "pivotal", "realm", "holistic", "synergy", "leverage", "utilize",
    "utilizing", "elevate", "revolutionize", "groundbreaking", "seamless",
    "seamlessly", "robust", "vibrant", "crucial", "notably", "foster",
    "fostering", "empower", "empowering", "unleash", "unlock", "embark",
    "navigate", "landscape", "journey", "beacon", "paradigm", "resonate",
    "resonates",
}
TIER1_WEIGHT = 3

TIER2_PHRASES = [
    r"stands as a testament",
    r"plays a (?:vital|pivotal|crucial|significant) role",
    r"in today'?s fast-paced (?:world|digital landscape)",
    r"rich tapestry",
    r"it'?s (?:important|worth) (?:to note|noting)",
    r"shed(?:s|ding)? light on",
    r"deep dive",
    r"game.?changer",
    r"paving the way",
    r"at the forefront",
    r"best practices",
    r"in the (?:realm|world) of",
    r"when it comes to",
    r"at the end of the day",
    r"needless to say",
    r"in conclusion",
    r"in summary",
    r"to summarize",
    r"first and foremost",
    r"dive (?:deep|deeper) into",
    r"a wide range of",
    r"plethora",
    r"myriad of",
    r"ever.?evolving",
]
TIER2_WEIGHT = 2
_TIER2_RE = re.compile("|".join(TIER2_PHRASES), re.IGNORECASE)

CHAT_ARTIFACTS = [
    "great question",
    "i hope this helps",
    "certainly!",
    "as an ai",
    "as a language model",
    "i cannot",
    "knowledge cutoff",
    "let me know if",
]


def load_lexicon_override(path: str | None) -> dict:
    """Load a JSON lexicon override file.

    Expected optional keys: "tier1_lexemes" (list[str]), "tier2_phrases"
    (list[str] regex fragments), "chat_artifacts" (list[str]),
    "remove_tier1" (list[str] to unban, e.g. domain terms like "robust").
    Returns a dict with resolved tier1_lexemes/tier2_phrases/chat_artifacts.
    """
    tier1 = set(TIER1_LEXEMES)
    tier2 = list(TIER2_PHRASES)
    chat = list(CHAT_ARTIFACTS)
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for w in data.get("remove_tier1", []):
            tier1.discard(w.lower())
        for w in data.get("tier1_lexemes", []):
            tier1.add(w.lower())
        tier2.extend(data.get("tier2_phrases", []))
        chat.extend(data.get("chat_artifacts", []))
    return {"tier1_lexemes": tier1, "tier2_phrases": tier2, "chat_artifacts": chat}


def slop_scores(text: str, lexicon: dict | None = None) -> dict:
    """Return per-1k-word weighted lexeme hits, phrase hits, and chat-artifact matches."""
    lex = lexicon or {
        "tier1_lexemes": TIER1_LEXEMES,
        "tier2_phrases": TIER2_PHRASES,
        "chat_artifacts": CHAT_ARTIFACTS,
    }
    tokens = words_of(text)
    n = max(len(tokens), 1)
    lowered_tokens = [t.lower() for t in tokens]
    tier1_hits = sum(1 for t in lowered_tokens if t in lex["tier1_lexemes"])
    lexeme_weighted = tier1_hits * TIER1_WEIGHT

    tier2_re = re.compile("|".join(lex["tier2_phrases"]), re.IGNORECASE)
    tier2_hits = len(tier2_re.findall(text))
    phrase_weighted = tier2_hits * TIER2_WEIGHT

    lowered_text = text.lower()
    artifact_hits = [a for a in lex["chat_artifacts"] if a in lowered_text]

    return {
        "lexeme_hits_per_1k": lexeme_weighted / n * 1000,
        "phrase_hits_per_1k": phrase_weighted / n * 1000,
        "chat_artifacts_found": artifact_hits,
    }


# ---------------------------------------------------------------------------
# Feature-scan regex constants
# ---------------------------------------------------------------------------

PASSIVE_RE = re.compile(r"\b(?:is|are|was|were|been|being|be)\s+\w+(?:ed|en)\b", re.IGNORECASE)
HEDGE_RE = {
    "hedge_might": re.compile(r"\bmight\b", re.IGNORECASE),
    "hedge_could": re.compile(r"\bcould\b", re.IGNORECASE),
    "hedge_would": re.compile(r"\bwould\b", re.IGNORECASE),
    "hedge_may": re.compile(r"\bmay\b", re.IGNORECASE),
}
WE_RE = re.compile(r"\bwe\b", re.IGNORECASE)
I_RE = re.compile(r"\bI\b")  # first-person "I": uppercase only, so "i.e."-ish tokens never count

COPULA_PLAIN_RE = re.compile(r"\b(?:is|are|was|were|be|being|been)\b", re.IGNORECASE)
COPULA_AVOIDANCE_RE = re.compile(r"\b(?:serves? as|stands? as|represents?|marks?)\b", re.IGNORECASE)

PARTICIPIAL_TAIL_RE = re.compile(r",\s*\w+ing\b[^,]{0,60}[.!?]$")
NEG_PARALLELISM_RE_1 = re.compile(r"\bnot (?:just|only|merely)\b.{0,80}?\bbut\b", re.IGNORECASE)
NEG_PARALLELISM_RE_2 = re.compile(r"it'?s not\b.{0,60}?[;,—]\s*it'?s\b", re.IGNORECASE)
RULE_OF_THREE_RE = re.compile(r"\b\w+(?:\s\w+)?,\s+\w+(?:\s\w+)?,?\s+and\s+\w+(?:\s\w+)?\b")

HEDGE_BOILERPLATE_RE = re.compile(
    r"it is (?:important|essential|crucial) to (?:note|consider|remember)"
    r"|it'?s worth (?:noting|considering)"
    r"|one must consider",
    re.IGNORECASE,
)

SCAFFOLD_MARKERS_RE = re.compile(
    r"\bin conclusion\b|\bin summary\b|\boverall,|\bto summarize\b", re.IGNORECASE
)

PUNCT_INTERVAL_RE = re.compile(r"[,.;:—()!?]")

CONNECTIVES = [
    "however", "for example", "for instance", "in particular", "in other words",
    "in effect", "consequently", "hence", "moreover", "furthermore", "in addition",
    "first", "second", "third", "finally", "by this we mean", "such a", "such an",
]

# Standard function-word list from the spec (enumerated verbatim). The spec
# calls this "60-word" but the literal enumerated list has 61 entries; kept
# exactly as given rather than dropping a word to force a round number.
FUNCTION_WORDS = [
    "the", "of", "to", "and", "a", "in", "that", "is", "was", "he", "for", "it",
    "with", "as", "his", "on", "be", "at", "by", "i", "this", "had", "not", "are",
    "but", "from", "or", "have", "an", "they", "which", "one", "you", "were",
    "her", "all", "she", "there", "would", "their", "we", "him", "been", "has",
    "when", "who", "will", "more", "no", "if", "out", "so", "said", "what", "up",
    "its", "about", "into", "than", "them", "can",
]
assert len(FUNCTION_WORDS) == len(set(FUNCTION_WORDS)) == 61


# ---------------------------------------------------------------------------
# Core stylometric measurements
# ---------------------------------------------------------------------------

def per_1k(count: int, total_words: int) -> float:
    return count / max(total_words, 1) * 1000


def sentence_rhythm(sentence_lens: list[int]) -> dict:
    if not sentence_lens:
        return {
            "mean": 0.0, "sd": 0.0, "cv": 0.0, "median": 0.0, "p10": 0, "p90": 0,
            "pct_under_10w": 0.0, "pct_over_35w": 0.0, "pct_under_6w": 0.0,
        }
    mean = statistics.fmean(sentence_lens)
    sd = statistics.pstdev(sentence_lens) if len(sentence_lens) > 1 else 0.0
    cv = sd / mean if mean else 0.0
    sorted_lens = sorted(sentence_lens)
    median = statistics.median(sorted_lens)
    p10 = _percentile(sorted_lens, 10)
    p90 = _percentile(sorted_lens, 90)
    n = len(sentence_lens)
    pct_under_10 = sum(1 for x in sentence_lens if x < 10) / n * 100
    pct_over_35 = sum(1 for x in sentence_lens if x > 35) / n * 100
    pct_under_6 = sum(1 for x in sentence_lens if x < 6) / n * 100
    return {
        "mean": mean, "sd": sd, "cv": cv, "median": median,
        "p10": p10, "p90": p90,
        "pct_under_10w": pct_under_10, "pct_over_35w": pct_over_35,
        "pct_under_6w": pct_under_6,
    }


def _percentile(sorted_vals: list[float], pct: float) -> float:
    """Nearest-rank percentile over an already-sorted list."""
    if not sorted_vals:
        return 0
    k = max(0, min(len(sorted_vals) - 1, math.ceil(pct / 100 * len(sorted_vals)) - 1))
    return sorted_vals[k]


def paragraph_stats(paragraphs: list[str]) -> dict:
    lens = [word_count_of(p) for p in paragraphs] or [0]
    mean = statistics.fmean(lens)
    sd = statistics.pstdev(lens) if len(lens) > 1 else 0.0
    cv = sd / mean if mean else 0.0
    return {"mean_words": mean, "cv": cv}


def punct_per_1k_of(text: str, total_words: int) -> dict:
    return {
        "em_dash": per_1k(text.count("—"), total_words),
        "semicolon": per_1k(text.count(";"), total_words),
        "colon": per_1k(text.count(":"), total_words),
        "paren": per_1k(text.count("(") + text.count(")"), total_words),
        "question": per_1k(text.count("?"), total_words),
        "exclaim": per_1k(text.count("!"), total_words),
        "ellipsis": per_1k(len(re.findall(r"\.\.\.|…", text)), total_words),
    }


def per_1k_features(text: str, total_words: int) -> dict:
    return {
        "passive_est": per_1k(len(PASSIVE_RE.findall(text)), total_words),
        "we": per_1k(len(WE_RE.findall(text)), total_words),
        "i": per_1k(len(I_RE.findall(text)), total_words),
        "hedge_might": per_1k(len(HEDGE_RE["hedge_might"].findall(text)), total_words),
        "hedge_could": per_1k(len(HEDGE_RE["hedge_could"].findall(text)), total_words),
        "hedge_would": per_1k(len(HEDGE_RE["hedge_would"].findall(text)), total_words),
        "hedge_may": per_1k(len(HEDGE_RE["hedge_may"].findall(text)), total_words),
    }


def copula_features(text: str, total_words: int) -> dict:
    plain = len(COPULA_PLAIN_RE.findall(text))
    avoidance = len(COPULA_AVOIDANCE_RE.findall(text))
    plain_per_1k = per_1k(plain, total_words)
    avoidance_per_1k = per_1k(avoidance, total_words)
    ratio = avoidance / plain if plain else (float(avoidance) if avoidance else 0.0)
    return {
        "plain_per_1k": plain_per_1k,
        "avoidance_per_1k": avoidance_per_1k,
        "avoidance_ratio": ratio,
    }


def constructions_per_1k(full_sentences: list[str], total_words: int) -> dict:
    tail_hits = sum(1 for s in full_sentences if PARTICIPIAL_TAIL_RE.search(s))
    tail_pct = tail_hits / max(len(full_sentences), 1) * 100

    joined = " ".join(full_sentences)
    neg_hits = len(NEG_PARALLELISM_RE_1.findall(joined)) + len(NEG_PARALLELISM_RE_2.findall(joined))
    neg_per_1k = per_1k(neg_hits, total_words)

    rule3_hits = len(RULE_OF_THREE_RE.findall(joined))
    rule3_per_1k = per_1k(rule3_hits, total_words)

    return {
        "participial_tail_pct_of_sentences": tail_pct,
        "neg_parallelism": neg_per_1k,
        "rule_of_three": rule3_per_1k,
    }


def connectives_per_10k_of(text: str, total_words: int) -> dict:
    lowered = text.lower()
    out = {}
    for marker in CONNECTIVES:
        cnt = lowered.count(marker)
        out[marker] = cnt / max(total_words, 1) * 10000
    return out


def function_words_per_1k_of(tokens_lower: list[str], total_words: int) -> dict:
    counts = Counter(tokens_lower)
    return {w: per_1k(counts.get(w, 0), total_words) for w in FUNCTION_WORDS}


def char_trigrams_of(text: str, top_n: int = 200) -> dict:
    """Top-N most frequent character trigrams over lowercased letters+space."""
    cleaned = re.sub(r"[^a-z ]", "", text.lower())
    cleaned = re.sub(r"\s+", " ", cleaned)
    trigrams = [cleaned[i:i + 3] for i in range(len(cleaned) - 2)]
    trigrams = [t for t in trigrams if t.strip()]
    total = len(trigrams) or 1
    counts = Counter(trigrams)
    top = counts.most_common(top_n)
    return {tri: cnt / total for tri, cnt in top}


def mattr(tokens_lower: list[str], window: int = 50) -> float:
    """Moving-average type-token ratio over a sliding window."""
    n = len(tokens_lower)
    if n == 0:
        return 0.0
    if n < window:
        return len(set(tokens_lower)) / n
    ratios = []
    for i in range(0, n - window + 1):
        chunk = tokens_lower[i:i + window]
        ratios.append(len(set(chunk)) / window)
    return statistics.fmean(ratios)


# ---------------------------------------------------------------------------
# Orality/literacy axis (sylveste-lbe.10) — Ong/Havelock-inspired register
# signal: oral registers (chat, blog) skew toward direct address, questions,
# contractions; literate registers (academic, formal docs) skew toward
# nominalization, subordination, and lexical density. Deterministic,
# regex-based, stdlib only — same style as the rest of the engine.
# ---------------------------------------------------------------------------

SECOND_PERSON_RE = re.compile(r"\b(?:you|your|yours|yourself)\b", re.IGNORECASE)
FIRST_SINGULAR_OBLIQUE_RE = re.compile(r"\b(?:me|my|mine)\b", re.IGNORECASE)
CONTRACTIONS_RE = re.compile(r"\b\w+['’](?:t|s|re|ve|ll|d|m)\b", re.IGNORECASE)
SENTENCE_INITIAL_CONJ_RE = re.compile(r"^(?:And|But|So|Or)\b")

NOMINALIZATION_SUFFIX_RE = re.compile(
    r"^[a-z]+(?:tion|tions|sion|sions|ment|ments|ness|ity|ities)$"
)
SUBORDINATORS_RE = re.compile(
    r"\b(?:because|although|though|whereas|whereby|which|whom|whose|thereby|wherein)\b",
    re.IGNORECASE,
)

# v0 reference ranges, NOT empirical percentiles. Chosen as plausible
# min/max bounds for each marker's per-1k (or per-100s / 0-1) rate so a
# clamp((value - lo) / (hi - lo), 0, 1) scale lands in [0, 1] for real prose.
# These are a starting point for calibration, not a measured distribution —
# revisit once enough fingerprinted corpora exist to compute real percentiles.
ORALITY_CALIBRATION = {
    "second_person_per_1k": (0, 25),
    "questions_per_1k": (0, 8),
    "exclaims_per_1k": (0, 4),
    "first_singular_per_1k": (0, 30),
    "contractions_per_1k": (0, 30),
    "sentence_initial_conj_per_100s": (0, 15),
    "nominalizations_per_1k": (10, 80),
    "passive_per_1k": (0, 25),
    "subordinators_per_1k": (5, 45),
    "long_words_per_1k": (40, 220),
    "lexical_density": (0.35, 0.65),
}

ORAL_MARKER_NAMES = (
    "second_person_per_1k",
    "questions_per_1k",
    "exclaims_per_1k",
    "first_singular_per_1k",
    "contractions_per_1k",
    "sentence_initial_conj_per_100s",
)
LITERATE_MARKER_NAMES = (
    "nominalizations_per_1k",
    "passive_per_1k",
    "subordinators_per_1k",
    "long_words_per_1k",
    "lexical_density",
)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _scale_marker(name: str, value: float) -> float:
    lo, hi = ORALITY_CALIBRATION[name]
    if hi == lo:
        return 0.0
    return _clamp01((value - lo) / (hi - lo))


def orality_markers(prose: str, prose_tokens_lower: list[str], prose_words: int) -> dict:
    """Raw per-1k (or per-100s / 0-1) rates for the 11 orality markers.

    Computed on the same prose text used for the other distributional
    features (16-18) — see extract_prose. `prose_tokens_lower` and
    `prose_words` are passed in so callers that already tokenized the prose
    (build_profile) don't redo it.
    """
    sentences = split_sentences(prose)
    n_sentences = len(sentences) or 1

    second_person = len(SECOND_PERSON_RE.findall(prose))
    questions = prose.count("?")
    exclaims = prose.count("!")
    first_singular = len(I_RE.findall(prose)) + len(FIRST_SINGULAR_OBLIQUE_RE.findall(prose))
    contractions = len(CONTRACTIONS_RE.findall(prose))
    sentence_initial_conj = sum(1 for s in sentences if SENTENCE_INITIAL_CONJ_RE.match(s.strip()))

    nominalizations = sum(1 for t in prose_tokens_lower if len(t) >= 8 and NOMINALIZATION_SUFFIX_RE.match(t))
    passive = len(PASSIVE_RE.findall(prose))
    subordinators = len(SUBORDINATORS_RE.findall(prose))
    long_words = sum(1 for t in prose_tokens_lower if t.isalpha() and len(t) >= 9)
    content_words = sum(1 for t in prose_tokens_lower if t not in FUNCTION_WORDS)
    lexical_density = content_words / prose_words if prose_words else 0.0

    return {
        "second_person_per_1k": per_1k(second_person, prose_words),
        "questions_per_1k": per_1k(questions, prose_words),
        "exclaims_per_1k": per_1k(exclaims, prose_words),
        "first_singular_per_1k": per_1k(first_singular, prose_words),
        "contractions_per_1k": per_1k(contractions, prose_words),
        "sentence_initial_conj_per_100s": sentence_initial_conj / n_sentences * 100,
        "nominalizations_per_1k": per_1k(nominalizations, prose_words),
        "passive_per_1k": per_1k(passive, prose_words),
        "subordinators_per_1k": per_1k(subordinators, prose_words),
        "long_words_per_1k": per_1k(long_words, prose_words),
        "lexical_density": lexical_density,
    }


def orality_axis_of(markers: dict) -> dict:
    """Scale the 11 raw marker rates to [0,1] and combine into the axis.

    orality_axis: 0 = maximally oral, 1 = maximally literate, 0.5 = balanced.
    """
    oral_scaled = [_scale_marker(name, markers[name]) for name in ORAL_MARKER_NAMES]
    literate_scaled = [_scale_marker(name, markers[name]) for name in LITERATE_MARKER_NAMES]
    oral_component = statistics.fmean(oral_scaled)
    literate_component = statistics.fmean(literate_scaled)
    axis = _clamp01(0.5 + (literate_component - oral_component) / 2)
    return {
        "axis": axis,
        "oral_component": oral_component,
        "literate_component": literate_component,
        "markers": markers,
    }


def build_orality_block(prose: str, prose_tokens_lower: list[str], prose_words: int) -> dict:
    markers = orality_markers(prose, prose_tokens_lower, prose_words)
    return orality_axis_of(markers)


# ---------------------------------------------------------------------------
# Profile assembly (shared between fingerprint corpora and lint drafts)
# ---------------------------------------------------------------------------

def build_profile(raw_text: str, lexicon: dict | None = None) -> dict:
    """Compute the full stylometric feature set for a single blob of text.

    Returns a dict matching the "sentence_rhythm"/"paragraphs"/... shape used
    by both `fingerprint` (aggregated over a corpus) and `lint` (a draft).
    Does NOT include the "meta" block — callers attach that themselves.
    """
    cleaned = strip_markdown(raw_text)
    paras = paragraphs_of(cleaned)
    sentences = split_sentences(cleaned)
    full_sentences, fragments = classify_sentences(sentences)

    tokens = words_of(cleaned)
    total_words = len(tokens)
    tokens_lower = [t.lower() for t in tokens]

    # Distributional features (16-18) compare prose-to-prose; everything else
    # runs on the full cleaned text. See extract_prose.
    prose = extract_prose(raw_text)
    prose_tokens = words_of(prose)
    prose_words = len(prose_tokens)
    prose_tokens_lower = [t.lower() for t in prose_tokens]

    sentence_lens = [word_count_of(s) for s in full_sentences]

    profile = {
        "sentence_rhythm": sentence_rhythm(sentence_lens),
        "paragraphs": paragraph_stats(paras),
        "punct_per_1k": punct_per_1k_of(cleaned, total_words),
        "per_1k": per_1k_features(cleaned, total_words),
        "copula": copula_features(cleaned, total_words),
        "constructions_per_1k": constructions_per_1k(full_sentences, total_words),
        "connectives_per_10k": connectives_per_10k_of(prose, prose_words or 1),
        "function_words_per_1k": function_words_per_1k_of(prose_tokens_lower, prose_words or 1),
        "char_trigrams": char_trigrams_of(prose),
        "lexical": {"mattr_w50": mattr(tokens_lower)},
        "slop": {},
    }
    slop = slop_scores(cleaned, lexicon)
    profile["slop"] = {
        "lexeme_hits_per_1k": slop["lexeme_hits_per_1k"],
        "phrase_hits_per_1k": slop["phrase_hits_per_1k"],
    }

    # Stash internal-use-only fields the lint command needs but that are not
    # part of the published fingerprint schema (kept out of "meta"/top-level
    # published keys via leading underscore so callers can pop them).
    profile["_internal"] = {
        "word_count": total_words,
        "sentence_count": len(full_sentences),
        "fragment_count": len(fragments),
        "paragraph_count": len(paras),
        "chat_artifacts_found": slop["chat_artifacts_found"],
        "sentence_lens": sentence_lens,
        "paragraph_lens": [word_count_of(p) for p in paras],
        "cleaned_text": cleaned,
        "full_sentences": full_sentences,
        "prose_word_count": prose_words,
        "prose_text": prose,
    }
    return profile


def _read_corpus_files(corpus_dir: Path) -> list[Path]:
    files = sorted(set(list(corpus_dir.rglob("*.md")) + list(corpus_dir.rglob("*.txt"))))
    return files


def fingerprint_corpus(paths: list[Path], register: str | None, lexicon: dict | None = None) -> dict:
    """Build a baseline fingerprint by concatenating all corpus files.

    Simpler and more robust than averaging per-file profiles (per-file
    averaging would badly distort ratio-style features like cv/mattr on
    small files); the spec's schema is a single aggregate profile anyway.
    """
    texts = [p.read_text(encoding="utf-8", errors="replace") for p in paths]
    combined = "\n\n".join(texts)
    profile = build_profile(combined, lexicon)
    internal = profile.pop("_internal")

    meta = {
        "register": register,
        "files": len(paths),
        "words": internal["word_count"],
        "sentences": internal["sentence_count"],
        "generated_by": f"intervox-engine v{VERSION}",
    }
    profile["meta"] = meta

    # Orality/literacy axis (sylveste-lbe.10): computed on the same prose
    # text as the other distributional features (16-18). Attached outside
    # build_profile so build_profile's own return schema — asserted exactly
    # by TestProfileSchema — stays unchanged; fingerprint_corpus is the
    # actual fingerprint-assembly boundary.
    prose = internal["prose_text"]
    prose_tokens_lower = [t.lower() for t in words_of(prose)]
    profile["orality"] = build_orality_block(prose, prose_tokens_lower, internal["prose_word_count"])
    return profile


# ---------------------------------------------------------------------------
# Lint: feature evaluation vs baseline
# ---------------------------------------------------------------------------

def cosine_similarity(a: dict, b: dict, keys: list[str] | None = None) -> float:
    ks = keys if keys is not None else sorted(set(a) | set(b))
    va = [a.get(k, 0.0) for k in ks]
    vb = [b.get(k, 0.0) for k in ks]
    dot = sum(x * y for x, y in zip(va, vb))
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(y * y for y in vb))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _status_from_thresholds(value: float, warn: float, fail: float, higher_is_worse: bool = True) -> str:
    if higher_is_worse:
        if value > fail:
            return "fail"
        if value > warn:
            return "warn"
        return "ok"
    else:
        if value < fail:
            return "fail"
        if value < warn:
            return "warn"
        return "ok"


def _feature_result(fid: int, name: str, draft_value, baseline_value, ratio_or_delta, status: str, hint: str) -> dict:
    return {
        "id": fid,
        "name": name,
        "draft_value": draft_value,
        "baseline_value": baseline_value,
        "ratio_or_delta": ratio_or_delta,
        "status": status,
        "hint": hint,
    }


def evaluate_lint(draft_profile: dict, draft_internal: dict, baseline: dict) -> list[dict]:
    """Evaluate all 18 lint features. Returns a list of feature-result dicts."""
    results = []
    word_count = draft_internal["word_count"]

    # 1. slop_lexemes — baseline-relative: some authors legitimately use lexicon
    # words ("leverage", "showcase" in academic ML prose), so the threshold is
    # the max of an absolute floor and a multiple of the author's own rate.
    dv = draft_profile["slop"]["lexeme_hits_per_1k"]
    bv = baseline["slop"]["lexeme_hits_per_1k"]
    warn_at = max(0.5, 1.75 * bv)
    fail_at = max(1.5, 3.0 * bv)
    status = "fail" if dv > fail_at else ("warn" if dv > warn_at else "ok")
    hint = f"Slop lexemes: {dv:.2f}/1k words (baseline {bv:.2f}/1k) — cut weighted AI-cliche vocabulary like 'delve', 'underscores', 'tapestry'."
    results.append(_feature_result(1, "slop_lexemes", dv, bv, dv - bv, status, hint))

    # 2. slop_phrases
    dv = draft_profile["slop"]["phrase_hits_per_1k"]
    bv = baseline["slop"]["phrase_hits_per_1k"]
    status = "fail" if dv > 1.0 else ("warn" if dv > 0.3 else "ok")
    hint = f"Slop phrases: {dv:.2f}/1k words (baseline {bv:.2f}/1k) — rewrite stock phrases like 'plays a pivotal role' or 'rich tapestry'."
    results.append(_feature_result(2, "slop_phrases", dv, bv, dv - bv, status, hint))

    # 3. chat_artifacts
    found = draft_internal["chat_artifacts_found"]
    status = "fail" if found else "ok"
    hint = f"Chat artifacts found: {', '.join(found)} — remove chatbot-register phrases entirely." if found else "No chat artifacts found."
    results.append(_feature_result(3, "chat_artifacts", found, [], len(found), status, hint))

    # 4. lexical_diversity (MATTR ratio draft/baseline)
    dv_m = draft_profile["lexical"]["mattr_w50"]
    bv_m = baseline["lexical"]["mattr_w50"]
    ratio = dv_m / bv_m if bv_m else 1.0
    status = "fail" if ratio < 0.85 else ("warn" if ratio < 0.92 else "ok")
    hint = f"Lexical diversity (MATTR): {dv_m:.3f} vs baseline {bv_m:.3f} (ratio {ratio:.2f}) — vary word choice, avoid repeating the same nouns/verbs."
    results.append(_feature_result(4, "lexical_diversity", dv_m, bv_m, ratio, status, hint))

    # 5. participial_tails
    dv_t = draft_profile["constructions_per_1k"]["participial_tail_pct_of_sentences"]
    bv_t = baseline["constructions_per_1k"]["participial_tail_pct_of_sentences"]
    if bv_t == 0:
        status = "fail" if dv_t > 8 else ("warn" if dv_t > 4 else "ok")
    else:
        ratio = dv_t / bv_t
        if ratio > 3 and dv_t > 8:
            status = "fail"
        elif ratio > 2 and dv_t > 4:
            status = "warn"
        else:
            status = "ok"
    hint = f"Participial tails: {dv_t:.1f}% of sentences end in ', Xing...' (baseline {bv_t:.1f}%) — vary sentence endings, cut trailing '-ing' clauses."
    results.append(_feature_result(5, "participial_tails", dv_t, bv_t, (dv_t - bv_t), status, hint))

    # 6. neg_parallelism
    dv_n = draft_profile["constructions_per_1k"]["neg_parallelism"]
    bv_n = baseline["constructions_per_1k"]["neg_parallelism"]
    status = "fail" if dv_n > bv_n + 1.0 else ("warn" if dv_n > bv_n + 0.4 else "ok")
    hint = f"Negative parallelism ('not just X but Y'): {dv_n:.2f}/1k (baseline {bv_n:.2f}/1k) — drop the not-X-but-Y crutch, state things directly."
    results.append(_feature_result(6, "neg_parallelism", dv_n, bv_n, dv_n - bv_n, status, hint))

    # 7. rule_of_three
    dv_r = draft_profile["constructions_per_1k"]["rule_of_three"]
    bv_r = baseline["constructions_per_1k"]["rule_of_three"]
    status = "fail" if dv_r > 2.5 * bv_r + 0.6 else ("warn" if dv_r > 1.5 * bv_r + 0.3 else "ok")
    hint = f"Rule-of-three triads: {dv_r:.2f}/1k (baseline {bv_r:.2f}/1k) — break up 'X, Y, and Z' listing habit."
    results.append(_feature_result(7, "rule_of_three", dv_r, bv_r, dv_r - bv_r, status, hint))

    # 8. copula_avoidance
    dv_c = draft_profile["copula"]["avoidance_ratio"]
    bv_c = baseline["copula"]["avoidance_ratio"]
    if bv_c == 0:
        status = "fail" if dv_c > 0.35 else ("warn" if dv_c > 0.15 else "ok")
        ratio = dv_c
    else:
        ratio = dv_c / bv_c
        status = "fail" if ratio > 4 else ("warn" if ratio > 2 else "ok")
    hint = f"Copula avoidance ('serves as', 'stands as', 'represents'): ratio {dv_c:.2f} vs baseline {bv_c:.2f} — just use 'is' sometimes."
    results.append(_feature_result(8, "copula_avoidance", dv_c, bv_c, ratio, status, hint))

    # 9. hedging_boilerplate
    hedge_hits = len(HEDGE_BOILERPLATE_RE.findall(draft_internal["cleaned_text"]))
    per_word_rate = hedge_hits / max(word_count, 1)
    status = "fail" if per_word_rate >= 1 / 150 else ("warn" if per_word_rate >= 1 / 300 else "ok")
    hint = f"Hedging boilerplate ('it is important to note'): {hedge_hits} hits in {word_count} words — cut the throat-clearing, say the thing."
    results.append(_feature_result(9, "hedging_boilerplate", hedge_hits, 0, hedge_hits, status, hint))

    # 10. em_dash_density
    # The absolute flood threshold (6.0/1k) yields to the author's own
    # established rate: a register whose baseline runs above it (gsv-site
    # measures 15.4/1k across 60 shipped files) must not hard-fail drafts
    # sitting at or below that baseline. Flood detection survives for
    # low-em-dash authors, where 1.5x baseline is still under 6.0.
    dv_e = draft_profile["punct_per_1k"]["em_dash"]
    bv_e = baseline["punct_per_1k"]["em_dash"]
    if (dv_e > 6.0 and dv_e > 1.5 * bv_e) or (dv_e > 2 * bv_e and dv_e > 3.0):
        status = "fail"
    elif dv_e > 1.5 * bv_e:
        status = "warn"
    else:
        status = "ok"
    hint = f"Em-dash density: {dv_e:.1f}/1k words (baseline {bv_e:.1f}/1k) — swap some em-dashes for periods, commas, or parentheses."
    results.append(_feature_result(10, "em_dash_density", dv_e, bv_e, dv_e - bv_e, status, hint))

    # Rhythm features (11, 12, 14, 15) are distributional statistics: on a
    # short draft the sample is a handful of sentences and the numbers are
    # noise, so they gate on the same 300-word prose floor features 16-19
    # already use. Lexical tells (1-10) stay on at any length — a slop
    # phrase is a slop phrase in a 40-word blurb.
    prose_wc = draft_internal.get("prose_word_count", word_count)
    rhythm_ready = prose_wc >= 300

    # Per-file derived medians, when the fingerprint carries them, are the
    # honest comparator for a single draft: pooled corpus statistics include
    # between-file variance, so every individual file reads as "too uniform"
    # against them (dogfood: gsv-site pooled sentence SD is 14.2w; no single
    # blurb's internal SD gets near it).
    per_file = baseline.get("_derived_per_file", {})

    # 11. burstiness (sentence-length SD ratio)
    dv_sd = draft_profile["sentence_rhythm"]["sd"]
    bv_sd = per_file.get("sentence_sd_median") or baseline["sentence_rhythm"]["sd"]
    if not rhythm_ready:
        ratio = None
        status = "skipped"
        hint = f"Burstiness: skipped ({prose_wc}w of flowing prose; rhythm features need 300w)."
    else:
        ratio = dv_sd / bv_sd if bv_sd else 1.0
        status = "fail" if ratio < 0.70 else ("warn" if ratio < 0.85 else "ok")
        hint = (
            f"Sentence rhythm too uniform: SD {dv_sd:.1f}w vs author {bv_sd:.1f}w "
            f"(ratio {ratio:.2f}) — split one long sentence and add a short one in a couple of paragraphs."
        )
    results.append(_feature_result(11, "burstiness", dv_sd, bv_sd, ratio, status, hint))

    # 12. monotony (adjacent near-equal-length sentence pairs)
    lens = draft_internal["sentence_lens"]
    pairs = list(zip(lens, lens[1:]))
    near_equal = [i for i, (a, b) in enumerate(pairs) if abs(a - b) <= 4]
    pct_near_equal = len(near_equal) / max(len(pairs), 1) * 100
    baseline_monotony = per_file.get("monotony_pct_median") or baseline.get("_derived_monotony_pct")
    if not rhythm_ready:
        status = "skipped"
    elif baseline_monotony is None or baseline_monotony == 0:
        status = "fail" if pct_near_equal > 70 else ("warn" if pct_near_equal > 55 else "ok")
    else:
        ratio = pct_near_equal / baseline_monotony
        status = "fail" if ratio > 1.8 else ("warn" if ratio > 1.4 else "ok")
    # detect runs of 4+ consecutive near-equal-length sentences
    run_start, run_len, runs = None, 0, []
    for i in range(len(lens)):
        is_near = i > 0 and abs(lens[i] - lens[i - 1]) <= 4
        if is_near:
            if run_start is None:
                run_start = i - 1
            run_len += 1
        else:
            if run_len >= 3:  # 3 pairwise-near transitions == 4 sentences
                runs.append((run_start + 1, run_start + run_len + 1))
            run_start, run_len = None, 0
    if run_len >= 3:
        runs.append((run_start + 1, run_start + run_len + 1))
    run_note = f"; runs of 4+ near-equal sentences at positions {runs}" if runs else ""
    hint = f"Monotony: {pct_near_equal:.0f}% of adjacent sentence pairs within 4 words of each other{run_note} — vary sentence length more."
    results.append(_feature_result(12, "monotony", pct_near_equal, baseline_monotony or 0.0, pct_near_equal - (baseline_monotony or 0.0), status, hint))

    # 13. short_sentence_deficit
    dv_short = draft_profile["sentence_rhythm"]["pct_under_6w"]
    bv_short = baseline["sentence_rhythm"]["pct_under_6w"]
    if bv_short >= 3:
        ratio = dv_short / bv_short if bv_short else 0.0
        status = "warn" if ratio < 0.5 else "ok"
        hint = f"Short-sentence deficit: {dv_short:.1f}% sentences <=6w vs baseline {bv_short:.1f}% — add a few short, blunt sentences."
    else:
        status = "skipped"
        hint = "Short-sentence deficit: skipped (baseline has too few short sentences to compare against)."
    results.append(_feature_result(13, "short_sentence_deficit", dv_short, bv_short, (dv_short - bv_short), status, hint))

    # 14. punct_interval_burstiness
    dv_pi = _punct_interval_sd(draft_internal["cleaned_text"])
    bv_pi = per_file.get("punct_interval_sd_median") or baseline.get("_derived_punct_interval_sd", 0.0)
    if not rhythm_ready:
        ratio = None
        status = "skipped"
        hint = f"Punctuation-interval burstiness: skipped ({prose_wc}w of flowing prose; rhythm features need 300w)."
    else:
        ratio = dv_pi / bv_pi if bv_pi else 1.0
        status = "fail" if ratio < 0.65 else ("warn" if ratio < 0.8 else "ok")
        hint = f"Punctuation-interval burstiness: SD {dv_pi:.2f} vs baseline {bv_pi:.2f} (ratio {ratio:.2f}) — vary the gaps between punctuation marks."
    results.append(_feature_result(14, "punct_interval_burstiness", dv_pi, bv_pi, ratio, status, hint))

    # 15. paragraph_uniformity — the scaffold-marker check is a lexical tell
    # and stays on at any length; only the CV-ratio comparison is a rhythm
    # statistic and gates on the prose floor.
    dv_cv = draft_profile["paragraphs"]["cv"]
    bv_cv = per_file.get("paragraph_cv_median") or baseline["paragraphs"]["cv"]
    ratio = dv_cv / bv_cv if bv_cv else 1.0
    scaffold_found = bool(SCAFFOLD_MARKERS_RE.search(draft_internal["cleaned_text"]))
    if scaffold_found:
        status = "fail"
    elif not rhythm_ready:
        status = "skipped"
    else:
        status = "warn" if ratio < 0.6 else "ok"
    hint = f"Paragraph uniformity: CV {dv_cv:.2f} vs baseline {bv_cv:.2f}"
    if scaffold_found:
        hint += " — scaffold marker found ('in conclusion'/'in summary'/'overall,'/'to summarize'); remove essay-scaffolding language."
    else:
        hint += " — vary paragraph length more."
    results.append(_feature_result(15, "paragraph_uniformity", dv_cv, bv_cv, ratio, status, hint))

    # 16. connective_drift
    if prose_wc < 300:
        status = "skipped"
        hint = f"Connective drift: skipped ({prose_wc}w of flowing prose; structured content is excluded from distributional features)."
        sim = None
    else:
        sim = cosine_similarity(draft_profile["connectives_per_10k"], baseline["connectives_per_10k"], CONNECTIVES)
        # Advisory band: distributional cosines read genre as well as voice
        # (dogfood: a README correctly has zero first-person against a blog
        # baseline). Only anomaly-floor breaches fail; the rest warns.
        status = "fail" if sim < 0.15 else ("warn" if sim < 0.55 else "ok")
        hint = f"Connective-word drift: cosine similarity {sim:.2f} vs baseline — advisory unless the register corpus covers this doc genre."
    results.append(_feature_result(16, "connective_drift", sim, 1.0, sim, status, hint))

    # 17. function_word_delta
    if prose_wc < 300:
        status = "skipped"
        hint = f"Function-word delta: skipped ({prose_wc}w of flowing prose)."
        sim = None
    else:
        sim = cosine_similarity(draft_profile["function_words_per_1k"], baseline["function_words_per_1k"], FUNCTION_WORDS)
        status = "fail" if sim < 0.60 else ("warn" if sim < 0.90 else "ok")
        hint = f"Function-word profile delta: cosine similarity {sim:.2f} vs baseline — advisory unless the register corpus covers this doc genre."
    results.append(_feature_result(17, "function_word_delta", sim, 1.0, sim, status, hint))

    # 18. char_trigram_delta
    if prose_wc < 300:
        status = "skipped"
        hint = f"Char-trigram delta: skipped ({prose_wc}w of flowing prose)."
        sim = None
    else:
        shared_keys = sorted(set(draft_profile["char_trigrams"]) & set(baseline["char_trigrams"]))
        sim = cosine_similarity(draft_profile["char_trigrams"], baseline["char_trigrams"], shared_keys) if shared_keys else 0.0
        status = "fail" if sim < 0.40 else ("warn" if sim < 0.75 else "ok")
        hint = f"Character-trigram delta: cosine similarity {sim:.2f} vs baseline over {len(shared_keys)} shared trigrams (advisory band below 0.75)."
    results.append(_feature_result(18, "char_trigram_delta", sim, 1.0, sim, status, hint))

    # 19. orality_drift — advisory only (never in HARD_FAIL_IDS, status never
    # exceeds "warn"): register-level oral(0)-literate(1) axis drift versus
    # baseline. Skips like 16-18 on short-prose drafts, and additionally
    # skips when the baseline fingerprint predates this feature (no
    # "orality" block) so old baselines keep working without a crash.
    baseline_orality = baseline.get("orality")
    if prose_wc < 300:
        status = "skipped"
        hint = f"Orality drift: skipped ({prose_wc}w of flowing prose)."
        draft_axis = None
        base_axis = None
    elif baseline_orality is None:
        status = "skipped"
        hint = "Orality drift: skipped (baseline fingerprint predates the orality axis; re-run fingerprint to add it)."
        draft_axis = None
        base_axis = None
    else:
        draft_orality = draft_profile.get("orality")
        if draft_orality is None:
            prose_text = draft_internal["prose_text"]
            prose_tokens_lower = [t.lower() for t in words_of(prose_text)]
            draft_orality = build_orality_block(prose_text, prose_tokens_lower, prose_wc)
        draft_axis = draft_orality["axis"]
        base_axis = baseline_orality["axis"]
        delta = draft_axis - base_axis
        status = "warn" if abs(delta) > 0.15 else "ok"  # advisory only, never "fail"
        direction = "lean more literate" if delta < 0 else "lean more oral"
        hint = (
            f"Orality drift: draft {draft_axis:.2f} vs baseline {base_axis:.2f} on the "
            f"oral(0)-literate(1) axis — {direction} (more conversational: contractions, "
            f"direct address, questions; more literate: nominalizations, subordination)."
        )
    results.append(_feature_result(19, "orality_drift", draft_axis, base_axis, (
        (draft_axis - base_axis) if draft_axis is not None and base_axis is not None else None
    ), status, hint))

    return results


def _punct_interval_sd(text: str) -> float:
    """SD of token-gaps between punctuation marks [,.;:—()!?]."""
    tokens = text.split()
    positions = [i for i, t in enumerate(tokens) if PUNCT_INTERVAL_RE.search(t)]
    if len(positions) < 2:
        return 0.0
    gaps = [b - a for a, b in zip(positions, positions[1:])]
    return statistics.pstdev(gaps) if len(gaps) > 1 else 0.0


def compute_corpus_derived_extras(raw_text: str) -> dict:
    """Compute the extra derived stats (monotony%, punct-interval SD) for a
    corpus's raw text, to be embedded as sidecar baseline fields.

    These two lint features (12, 14) need a signal from the baseline that
    the published fingerprint schema doesn't otherwise carry (raw sentence
    order / token positions), so `fingerprint` stashes them as extra
    "_derived_*" keys alongside the documented schema keys. If a baseline
    JSON lacks these keys (e.g. hand-written or from an older version),
    lint/verify fall back to the "no baseline" absolute-threshold branch
    for those two features rather than erroring.
    """
    cleaned = strip_markdown(raw_text)
    sentences = split_sentences(cleaned)
    full_sentences, _ = classify_sentences(sentences)
    lens = [word_count_of(s) for s in full_sentences]
    pairs = list(zip(lens, lens[1:]))
    near_equal = sum(1 for a, b in pairs if abs(a - b) <= 4)
    monotony_pct = near_equal / max(len(pairs), 1) * 100
    punct_sd = _punct_interval_sd(cleaned)
    return {"monotony_pct": monotony_pct, "punct_interval_sd": punct_sd}


def compute_per_file_medians(paths: list[Path], lexicon: dict | None = None) -> dict:
    """Median per-file rhythm statistics for a multi-file corpus.

    Pooled corpus statistics (sentence SD, punct-interval SD, monotony %,
    paragraph CV) include between-file variance, which overstates the rhythm
    variation any single draft can show — verified against gsv-site, where
    the pooled sentence SD (14.2w) sat above every individual corpus file's
    internal SD, so verify rejected the corpus it was fingerprinted from.
    The median of per-file values is the honest single-draft comparator;
    verify features 11/12/14/15 prefer these keys when present and fall
    back to the pooled keys for fingerprints that predate them.
    """
    sds: list[float] = []
    punct_sds: list[float] = []
    monotony: list[float] = []
    cvs: list[float] = []
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="replace")
        profile = build_profile(text, lexicon)
        internal = profile.pop("_internal")
        if internal["sentence_count"] < 4:
            continue  # a couple of sentences carries no rhythm signal
        sds.append(profile["sentence_rhythm"]["sd"])
        cvs.append(profile["paragraphs"]["cv"])
        extras = compute_corpus_derived_extras(text)
        monotony.append(extras["monotony_pct"])
        punct_sds.append(extras["punct_interval_sd"])
    if not sds:
        return {}
    return {
        "sentence_sd_median": statistics.median(sds),
        "punct_interval_sd_median": statistics.median(punct_sds),
        "monotony_pct_median": statistics.median(monotony),
        "paragraph_cv_median": statistics.median(cvs),
    }


# ---------------------------------------------------------------------------
# TF-IDF retrieval
# ---------------------------------------------------------------------------

def chunk_paragraphs(text: str, min_words: int = 40) -> list[str]:
    """Chunk cleaned text into paragraphs, merging adjacent short ones."""
    cleaned = strip_markdown(text)
    paras = paragraphs_of(cleaned)
    chunks: list[str] = []
    buf = ""
    for p in paras:
        buf = (buf + " " + p).strip() if buf else p
        if word_count_of(buf) >= min_words:
            chunks.append(buf)
            buf = ""
    if buf:
        if chunks:
            chunks[-1] = (chunks[-1] + " " + buf).strip()
        else:
            chunks.append(buf)
    return chunks


def build_tfidf(documents: list[list[str]]) -> tuple[list[dict], dict]:
    """Build log-tf, smoothed-idf TF-IDF vectors for a list of tokenized docs.

    Returns (list of per-doc term->weight dicts, idf dict).
    """
    n_docs = len(documents)
    df = Counter()
    for tokens in documents:
        for term in set(tokens):
            df[term] += 1
    idf = {term: math.log((1 + n_docs) / (1 + dfc)) + 1 for term, dfc in df.items()}

    vectors = []
    for tokens in documents:
        tf = Counter(tokens)
        vec = {}
        for term, count in tf.items():
            log_tf = 1 + math.log(count)
            vec[term] = log_tf * idf.get(term, 0.0)
        vectors.append(vec)
    return vectors, idf


def tfidf_vector_for_query(query_tokens: list[str], idf: dict) -> dict:
    tf = Counter(query_tokens)
    vec = {}
    for term, count in tf.items():
        log_tf = 1 + math.log(count)
        # Unseen query terms get idf=0 (contribute nothing) rather than being
        # dropped, so cosine_similarity's key union still behaves sanely.
        vec[term] = log_tf * idf.get(term, 0.0)
    return vec


def retrieve(corpus_dir: Path, query: str, k: int = 5, min_words: int = 40) -> list[dict]:
    files = _read_corpus_files(corpus_dir)
    chunk_records = []  # (file, position, text)
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        chunks = chunk_paragraphs(text, min_words)
        for pos, c in enumerate(chunks):
            chunk_records.append((str(f), pos, c))

    tokenized = [[t.lower() for t in words_of(c[2])] for c in chunk_records]
    vectors, idf = build_tfidf(tokenized)
    query_tokens = [t.lower() for t in words_of(query)]
    query_vec = tfidf_vector_for_query(query_tokens, idf)

    scored = []
    for (fname, pos, text), vec in zip(chunk_records, vectors):
        score = cosine_similarity(query_vec, vec)
        scored.append({"file": fname, "score": score, "text": text, "_pos": pos})

    # Deterministic ordering: score desc, then file, then position.
    scored.sort(key=lambda r: (-r["score"], r["file"], r["_pos"]))
    top = scored[:k]
    for r in top:
        r.pop("_pos")
    return top


# ---------------------------------------------------------------------------
# registers command
# ---------------------------------------------------------------------------

_REGISTER_HEADING_RE = re.compile(r"(?m)^##\s+(Foundation.*|Register\s+\d+\s*:.*)$")


def parse_registers(profile_text: str) -> list[dict]:
    out = []
    for m in _REGISTER_HEADING_RE.finditer(profile_text):
        heading = m.group(1).strip()
        if heading.lower().startswith("foundation"):
            out.append({"type": "foundation", "name": heading})
        else:
            num_match = re.match(r"Register\s+(\d+)\s*:\s*(.*)", heading)
            num = int(num_match.group(1)) if num_match else None
            name = num_match.group(2).strip() if num_match else heading
            out.append({"type": "register", "number": num, "name": name})
    return out


# ---------------------------------------------------------------------------
# Table formatting for `lint --format table`
# ---------------------------------------------------------------------------

def _fmt_value(v) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.3f}"
    if isinstance(v, list):
        return ",".join(str(x) for x in v) if v else "-"
    return str(v)


def render_table(results: list[dict]) -> str:
    headers = ["#", "feature", "draft", "baseline", "ratio/delta", "status"]
    rows = []
    for r in results:
        rows.append([
            str(r["id"]),
            r["name"],
            _fmt_value(r["draft_value"]),
            _fmt_value(r["baseline_value"]),
            _fmt_value(r["ratio_or_delta"]),
            r["status"],
        ])
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) if rows else len(headers[i]) for i in range(len(headers))]

    def fmt_row(cells):
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cells))

    lines = [fmt_row(headers), "  ".join("-" * w for w in widths)]
    for row in rows:
        lines.append(fmt_row(row))

    hints = [r for r in results if r["status"] in ("warn", "fail")]
    hints.sort(key=lambda r: (0 if r["status"] == "fail" else 1, r["id"]))
    lines.append("")
    lines.append("Top revision hints:")
    if not hints:
        lines.append("  (none — draft is clean against baseline)")
    else:
        for r in hints:
            lines.append(f"  [{r['status'].upper()}] {r['hint']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scoring / verdict for `verify`
# ---------------------------------------------------------------------------

# Hard-fail features force reject regardless of composite score. slop_lexemes
# is deliberately NOT here: a single lexical feature must not solo-reject a
# draft that passes everything else (clusters convict, single tells don't) —
# it still costs score like any fail. chat_artifacts and em-dash flood stay
# hard because neither has a legitimate author-baseline explanation.
HARD_FAIL_IDS = {3, 10}  # chat_artifacts, em_dash_density


def score_and_verdict(results: list[dict]) -> dict:
    scored = [r for r in results if r["status"] != "skipped"]
    score = 100
    for r in scored:
        if r["status"] == "fail":
            score -= 18
        elif r["status"] == "warn":
            score -= 6
    score = max(score, 0)

    failures = [r["name"] for r in scored if r["status"] == "fail"]
    hard_fail = any(r["status"] == "fail" and r["id"] in HARD_FAIL_IDS for r in scored)

    if score >= 80 and not hard_fail:
        verdict = "pass"
    elif hard_fail or score < 60:
        verdict = "reject"
    else:
        verdict = "revise"

    hints = [r["hint"] for r in scored if r["status"] in ("warn", "fail")]
    return {"score": score, "verdict": verdict, "failures": failures, "hints": hints, "hard_fail": hard_fail}


def exit_code_for_verdict(verdict_info: dict) -> int:
    score = verdict_info["score"]
    hard_fail = verdict_info["hard_fail"]
    if score >= 80 and not hard_fail:
        return 0
    if hard_fail or score < 60:
        return 2
    return 1


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------

def _load_baseline(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _profile_for_draft(draft_path: str, lexicon: dict | None) -> tuple[dict, dict]:
    text = Path(draft_path).read_text(encoding="utf-8", errors="replace")
    profile = build_profile(text, lexicon)
    internal = profile.pop("_internal")
    prose = internal["prose_text"]
    prose_tokens_lower = [t.lower() for t in words_of(prose)]
    profile["orality"] = build_orality_block(prose, prose_tokens_lower, internal["prose_word_count"])
    return profile, internal


def cmd_fingerprint(args: argparse.Namespace) -> int:
    lexicon = load_lexicon_override(args.lexicon)
    if args.corpus:
        corpus_dir = Path(args.corpus)
        files = _read_corpus_files(corpus_dir)
        if not files:
            print(f"intervox: no *.md/*.txt files found under {corpus_dir}", file=sys.stderr)
            return 1
        profile = fingerprint_corpus(files, args.register, lexicon)
        combined_text = "\n\n".join(f.read_text(encoding="utf-8", errors="replace") for f in files)
    else:
        p = Path(args.text)
        files = [p]
        profile = fingerprint_corpus([p], args.register, lexicon)
        combined_text = p.read_text(encoding="utf-8", errors="replace")

    extras = compute_corpus_derived_extras(combined_text)
    profile["_derived_monotony_pct"] = extras["monotony_pct"]
    profile["_derived_punct_interval_sd"] = extras["punct_interval_sd"]

    if args.corpus and len(files) > 1:
        per_file = compute_per_file_medians(files, lexicon)
        if per_file:
            profile["_derived_per_file"] = per_file

    out_path = Path(args.out)
    out_path.write_text(json.dumps(profile, indent=2, sort_keys=False), encoding="utf-8")
    print(f"intervox: wrote fingerprint to {out_path} ({profile['meta']['words']} words, {profile['meta']['files']} files)")
    return 0


# Below this much flowing prose there is nothing to measure: frontmatter-only
# collection entries and stub files otherwise verify an empty string and
# collapse to a deterministic reject (dogfood: 65 gsvdotcom files, all
# metrics 0.000). Vale still covers such files; the stylometric layer skips.
MIN_VERIFY_PROSE_WORDS = 50


def _skip_for_thin_prose(draft_internal: dict) -> int | None:
    prose_wc = draft_internal.get("prose_word_count", draft_internal.get("word_count", 0))
    return prose_wc if prose_wc < MIN_VERIFY_PROSE_WORDS else None


def cmd_lint(args: argparse.Namespace) -> int:
    lexicon = load_lexicon_override(args.lexicon)
    baseline = _load_baseline(args.baseline)
    draft_profile, draft_internal = _profile_for_draft(args.draft, lexicon)
    thin = _skip_for_thin_prose(draft_internal)
    if thin is not None:
        msg = f"intervox: skipped — {thin}w of flowing prose (floor {MIN_VERIFY_PROSE_WORDS}w); nothing to measure."
        if args.format == "json":
            print(json.dumps({"verdict": "skip", "note": msg}, indent=2))
        else:
            print(msg)
        return 0
    results = evaluate_lint(draft_profile, draft_internal, baseline)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(render_table(results))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    lexicon = load_lexicon_override(args.lexicon)
    baseline = _load_baseline(args.baseline)
    draft_profile, draft_internal = _profile_for_draft(args.draft, lexicon)
    results = evaluate_lint(draft_profile, draft_internal, baseline)
    verdict_info = score_and_verdict(results)
    output = {
        "score": verdict_info["score"],
        "verdict": verdict_info["verdict"],
        "failures": verdict_info["failures"],
        "hints": verdict_info["hints"],
    }
    print(json.dumps(output, indent=2))
    return exit_code_for_verdict(verdict_info)


def cmd_retrieve(args: argparse.Namespace) -> int:
    results = retrieve(Path(args.corpus), args.query, args.k, args.min_words)
    print(json.dumps(results, indent=2))
    return 0


def cmd_registers(args: argparse.Namespace) -> int:
    text = Path(args.profile).read_text(encoding="utf-8", errors="replace")
    regs = parse_registers(text)
    print(json.dumps(regs, indent=2))
    return 0


def cmd_orality(args: argparse.Namespace) -> int:
    if args.corpus:
        corpus_dir = Path(args.corpus)
        files = _read_corpus_files(corpus_dir)
        if not files:
            print(f"intervox: no *.md/*.txt files found under {corpus_dir}", file=sys.stderr)
            return 1
        combined = "\n\n".join(f.read_text(encoding="utf-8", errors="replace") for f in files)
    else:
        combined = Path(args.text).read_text(encoding="utf-8", errors="replace")

    prose = extract_prose(combined)
    prose_tokens = words_of(prose)
    prose_tokens_lower = [t.lower() for t in prose_tokens]
    block = build_orality_block(prose, prose_tokens_lower, len(prose_tokens))
    print(json.dumps(block, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="intervox", description="Stylometric fingerprinting and LLMism linter.")
    sub = parser.add_subparsers(dest="command", required=True)

    fp = sub.add_parser("fingerprint", help="Build a baseline stylometric profile from a corpus or single text.")
    fp_group = fp.add_mutually_exclusive_group(required=True)
    fp_group.add_argument("--corpus", help="Directory of *.md/*.txt files (recursive).")
    fp_group.add_argument("--text", help="Single document to fingerprint.")
    fp.add_argument("--out", required=True, help="Output JSON path.")
    fp.add_argument("--register", default=None, help="Optional register name to record in meta.")
    fp.add_argument("--lexicon", default=None, help="Optional JSON lexicon override file.")
    fp.set_defaults(func=cmd_fingerprint)

    lint = sub.add_parser("lint", help="Lint a draft against a baseline fingerprint.")
    lint.add_argument("--draft", required=True)
    lint.add_argument("--baseline", required=True)
    lint.add_argument("--format", choices=["json", "table"], default="table")
    lint.add_argument("--lexicon", default=None)
    lint.set_defaults(func=cmd_lint)

    verify = sub.add_parser("verify", help="Run lint and reduce to a pass/revise/reject verdict.")
    verify.add_argument("--draft", required=True)
    verify.add_argument("--baseline", required=True)
    verify.add_argument("--lexicon", default=None)
    verify.set_defaults(func=cmd_verify)

    retr = sub.add_parser("retrieve", help="TF-IDF paragraph retrieval over a corpus.")
    retr.add_argument("--corpus", required=True)
    retr.add_argument("--query", required=True)
    retr.add_argument("--k", type=int, default=5)
    retr.add_argument("--min-words", type=int, default=40, dest="min_words")
    retr.set_defaults(func=cmd_retrieve)

    regs = sub.add_parser("registers", help="List register sections found in a voice profile markdown file.")
    regs.add_argument("--profile", required=True)
    regs.set_defaults(func=cmd_registers)

    orality = sub.add_parser("orality", help="Compute the orality/literacy axis block for a corpus or single text.")
    orality_group = orality.add_mutually_exclusive_group(required=True)
    orality_group.add_argument("--corpus", help="Directory of *.md/*.txt files (recursive).")
    orality_group.add_argument("--text", help="Single document to score.")
    orality.set_defaults(func=cmd_orality)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

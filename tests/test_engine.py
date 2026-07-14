#!/usr/bin/env python3
"""Unit + subprocess tests for the intervox measurement engine.

Run directly: python3 tests/test_engine.py
Standard library only (unittest); no pip dependencies.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
CORPUS_DIR = FIXTURES_DIR / "corpus"
SLOPPY_DRAFT = FIXTURES_DIR / "sloppy-draft.md"
CLEAN_DRAFT = FIXTURES_DIR / "clean-draft.md"
INTERVOX_SHIM = ENGINE_DIR / "intervox"

sys.path.insert(0, str(ENGINE_DIR))
import intervox_engine as ie  # noqa: E402


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(INTERVOX_SHIM), *args],
        capture_output=True,
        text=True,
    )


class TestMarkdownAndSentences(unittest.TestCase):
    def test_strip_markdown_removes_syntax_keeps_paragraphs(self):
        text = "# Heading\n\nSome **bold** and *italic* text with a [link](http://x.com).\n\n- item one\n- item two\n"
        cleaned = ie.strip_markdown(text)
        self.assertNotIn("#", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("[link]", cleaned)
        self.assertNotIn("http://x.com", cleaned)
        self.assertIn("link", cleaned)
        # paragraph boundary (blank line) preserved
        self.assertIn("\n\n", cleaned)

    def test_strip_markdown_code_fence_removed(self):
        text = "before\n```python\ncode_here()\n```\nafter"
        cleaned = ie.strip_markdown(text)
        self.assertNotIn("code_here", cleaned)

    def test_inline_backticks_keep_content_minus_backticks(self):
        text = "use the `foo` function"
        cleaned = ie.strip_markdown(text)
        self.assertIn("foo", cleaned)
        self.assertNotIn("`", cleaned)

    def test_sentence_split_protects_abbreviations(self):
        text = "Dr. Smith went to the U.S. for a conference, e.g. Boston. Then he came home."
        sentences = ie.split_sentences(text)
        # Should NOT split on "Dr." or "U.S." or "e.g." — only 2 real sentences.
        self.assertEqual(len(sentences), 2)
        self.assertTrue(sentences[0].startswith("Dr. Smith"))

    def test_sentence_split_basic(self):
        text = "This is one. This is two! Is this three? Yes it is."
        sentences = ie.split_sentences(text)
        self.assertEqual(len(sentences), 4)

    def test_fragment_classification(self):
        sentences = ["This is a full sentence with words.", "No.", "Ok fine."]
        full, frag = ie.classify_sentences(sentences)
        # "No." has 1 word -> fragment; "Ok fine." has 2 words -> fragment
        self.assertEqual(len(full), 1)
        self.assertEqual(len(frag), 2)


class TestSlopLexicon(unittest.TestCase):
    def test_tier1_lexeme_hit(self):
        scores = ie.slop_scores("We need to delve into this and leverage synergy.")
        self.assertGreater(scores["lexeme_hits_per_1k"], 0)

    def test_tier2_phrase_hit(self):
        scores = ie.slop_scores("This stands as a testament to our rich tapestry of ideas.")
        self.assertGreater(scores["phrase_hits_per_1k"], 0)

    def test_chat_artifact_detected(self):
        scores = ie.slop_scores("Great question! Let me help.")
        self.assertIn("great question", scores["chat_artifacts_found"])

    def test_clean_text_no_hits(self):
        scores = ie.slop_scores("The dog walked slowly down the quiet street at dusk.")
        self.assertEqual(scores["lexeme_hits_per_1k"], 0)
        self.assertEqual(scores["phrase_hits_per_1k"], 0)
        self.assertEqual(scores["chat_artifacts_found"], [])

    def test_lexicon_override_removes_and_adds(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"remove_tier1": ["robust"], "tier1_lexemes": ["frobnicate"]}, f)
            path = f.name
        lex = ie.load_lexicon_override(path)
        self.assertNotIn("robust", lex["tier1_lexemes"])
        self.assertIn("frobnicate", lex["tier1_lexemes"])
        Path(path).unlink()


class TestMattr(unittest.TestCase):
    def test_mattr_full_diversity(self):
        tokens = [f"word{i}" for i in range(100)]
        self.assertAlmostEqual(ie.mattr(tokens, window=50), 1.0)

    def test_mattr_no_diversity(self):
        tokens = ["same"] * 100
        self.assertAlmostEqual(ie.mattr(tokens, window=50), 1 / 50)

    def test_mattr_short_text_fallback(self):
        tokens = ["a", "b", "a"]
        # n < window -> simple type/token ratio
        self.assertAlmostEqual(ie.mattr(tokens, window=50), 2 / 3)


class TestProfileSchema(unittest.TestCase):
    """fingerprint schema keys present on the fixture corpus."""

    @classmethod
    def setUpClass(cls):
        texts = [(CORPUS_DIR / f"sample{i}.md").read_text(encoding="utf-8") for i in (1, 2, 3)]
        cls.combined = "\n\n".join(texts)
        cls.profile = ie.build_profile(cls.combined)

    def test_top_level_keys(self):
        expected = {
            "sentence_rhythm", "paragraphs", "punct_per_1k", "per_1k", "copula",
            "constructions_per_1k", "connectives_per_10k", "function_words_per_1k",
            "char_trigrams", "lexical", "slop", "_internal",
        }
        self.assertEqual(expected, set(self.profile.keys()))

    def test_sentence_rhythm_keys(self):
        expected = {"mean", "sd", "cv", "median", "p10", "p90", "pct_under_10w", "pct_over_35w", "pct_under_6w"}
        self.assertEqual(expected, set(self.profile["sentence_rhythm"].keys()))

    def test_punct_per_1k_keys(self):
        expected = {"em_dash", "semicolon", "colon", "paren", "question", "exclaim", "ellipsis"}
        self.assertEqual(expected, set(self.profile["punct_per_1k"].keys()))

    def test_per_1k_keys(self):
        expected = {"passive_est", "we", "i", "hedge_might", "hedge_could", "hedge_would", "hedge_may"}
        self.assertEqual(expected, set(self.profile["per_1k"].keys()))

    def test_copula_keys(self):
        expected = {"plain_per_1k", "avoidance_per_1k", "avoidance_ratio"}
        self.assertEqual(expected, set(self.profile["copula"].keys()))

    def test_constructions_keys(self):
        expected = {"participial_tail_pct_of_sentences", "neg_parallelism", "rule_of_three"}
        self.assertEqual(expected, set(self.profile["constructions_per_1k"].keys()))

    def test_connectives_scan_list(self):
        self.assertEqual(set(ie.CONNECTIVES), set(self.profile["connectives_per_10k"].keys()))

    def test_function_words_list(self):
        self.assertEqual(set(ie.FUNCTION_WORDS), set(self.profile["function_words_per_1k"].keys()))

    def test_char_trigrams_top_200(self):
        self.assertLessEqual(len(self.profile["char_trigrams"]), 200)
        self.assertGreater(len(self.profile["char_trigrams"]), 0)

    def test_lexical_mattr_key(self):
        self.assertIn("mattr_w50", self.profile["lexical"])

    def test_slop_keys(self):
        expected = {"lexeme_hits_per_1k", "phrase_hits_per_1k"}
        self.assertEqual(expected, set(self.profile["slop"].keys()))

    def test_fingerprint_meta_via_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "baseline.json"
            result = run_cli("fingerprint", "--corpus", str(CORPUS_DIR), "--out", str(out_path), "--register", "test-register")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(out_path.read_text())
            self.assertEqual(data["meta"]["register"], "test-register")
            self.assertEqual(data["meta"]["files"], 3)
            self.assertEqual(data["meta"]["generated_by"], f"intervox-engine v{ie.VERSION}")
            self.assertGreater(data["meta"]["words"], 0)
            self.assertGreater(data["meta"]["sentences"], 0)


class TestLintSloppyDraft(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.baseline_path = Path(cls.tmp.name) / "baseline.json"
        r = run_cli("fingerprint", "--corpus", str(CORPUS_DIR), "--out", str(cls.baseline_path))
        assert r.returncode == 0, r.stderr
        cls.baseline = json.loads(cls.baseline_path.read_text())

        text = SLOPPY_DRAFT.read_text(encoding="utf-8")
        cls.draft_profile = ie.build_profile(text)
        cls.draft_internal = cls.draft_profile.pop("_internal")
        cls.results = ie.evaluate_lint(cls.draft_profile, cls.draft_internal, cls.baseline)
        cls.by_id = {r["id"]: r for r in cls.results}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_at_least_six_features_flagged(self):
        flagged = [r for r in self.results if r["status"] in ("warn", "fail")]
        self.assertGreaterEqual(len(flagged), 6, f"only flagged: {[r['name'] for r in flagged]}")

    def test_slop_lexemes_fail(self):
        self.assertEqual(self.by_id[1]["status"], "fail")

    def test_chat_artifacts_fail(self):
        self.assertEqual(self.by_id[3]["status"], "fail")

    def test_em_dash_density_warn_or_fail(self):
        self.assertIn(self.by_id[10]["status"], ("warn", "fail"))

    def test_burstiness_warn_or_fail(self):
        self.assertIn(self.by_id[11]["status"], ("warn", "fail"))

    def test_rule_of_three_warn_or_fail(self):
        self.assertIn(self.by_id[7]["status"], ("warn", "fail"))

    def test_all_18_features_present(self):
        self.assertEqual(set(range(1, 19)), set(self.by_id.keys()))

    def test_table_format_renders(self):
        result = run_cli("lint", "--draft", str(SLOPPY_DRAFT), "--baseline", str(self.baseline_path), "--format", "table")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Top revision hints", result.stdout)
        self.assertIn("slop_lexemes", result.stdout)


class TestLintCleanDraft(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.baseline_path = Path(cls.tmp.name) / "baseline.json"
        r = run_cli("fingerprint", "--corpus", str(CORPUS_DIR), "--out", str(cls.baseline_path))
        assert r.returncode == 0, r.stderr
        cls.baseline = json.loads(cls.baseline_path.read_text())

        text = CLEAN_DRAFT.read_text(encoding="utf-8")
        cls.draft_profile = ie.build_profile(text)
        cls.draft_internal = cls.draft_profile.pop("_internal")
        cls.results = ie.evaluate_lint(cls.draft_profile, cls.draft_internal, cls.baseline)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_at_most_two_non_ok_features(self):
        non_ok = [r for r in self.results if r["status"] not in ("ok", "skipped")]
        self.assertLessEqual(len(non_ok), 2, f"non-ok features: {[(r['id'], r['name'], r['status']) for r in non_ok]}")


class TestVerifySubprocess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.baseline_path = Path(cls.tmp.name) / "baseline.json"
        r = run_cli("fingerprint", "--corpus", str(CORPUS_DIR), "--out", str(cls.baseline_path))
        assert r.returncode == 0, r.stderr

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_verify_sloppy_exits_2(self):
        result = run_cli("verify", "--draft", str(SLOPPY_DRAFT), "--baseline", str(self.baseline_path))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["verdict"], "reject")

    def test_verify_clean_exits_0(self):
        result = run_cli("verify", "--draft", str(CLEAN_DRAFT), "--baseline", str(self.baseline_path))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["verdict"], "pass")
        self.assertGreaterEqual(payload["score"], 80)


class TestRetrieve(unittest.TestCase):
    def test_retrieve_k_results_descending(self):
        results = ie.retrieve(CORPUS_DIR, "insurance adjuster basement flood damage water", k=5)
        self.assertEqual(len(results), 5)
        scores = [r["score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_retrieve_cli_returns_json(self):
        result = run_cli("retrieve", "--corpus", str(CORPUS_DIR), "--query", "sourdough starter bread", "--k", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload), 3)
        for item in payload:
            self.assertIn("file", item)
            self.assertIn("score", item)
            self.assertIn("text", item)

    def test_chunk_paragraphs_merges_short(self):
        text = "Short one.\n\nShort two.\n\n" + ("word " * 60).strip() + "."
        chunks = ie.chunk_paragraphs(text, min_words=40)
        # first two short paragraphs should merge with the long one or each other
        self.assertGreaterEqual(len(chunks), 1)


class TestRegisters(unittest.TestCase):
    def test_parses_inline_profile_fixture(self):
        profile_text = (
            "# Voice Profile\n\n"
            "## Foundation: Shared Voice DNA\n"
            "Some foundation text.\n\n"
            "## Register 1: Team\n"
            "Team notes.\n\n"
            "## Register 2: Internal\n"
            "Internal notes.\n\n"
            "## Register 4: Open Source\n"
            "OSS notes.\n"
        )
        regs = ie.parse_registers(profile_text)
        self.assertEqual(len(regs), 4)
        self.assertEqual(regs[0]["type"], "foundation")
        self.assertEqual(regs[1], {"type": "register", "number": 1, "name": "Team"})
        self.assertEqual(regs[3], {"type": "register", "number": 4, "name": "Open Source"})

    def test_registers_cli(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("## Foundation: Base\nx\n\n## Register 3: External\ny\n")
            path = f.name
        result = run_cli("registers", "--profile", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload), 2)
        Path(path).unlink()


class TestScoreAndVerdict(unittest.TestCase):
    def test_score_starts_at_100_and_floors_at_0(self):
        results = [{"id": i, "name": f"f{i}", "status": "fail", "hint": "h"} for i in range(1, 10)]
        info = ie.score_and_verdict(results)
        self.assertEqual(info["score"], 0)

    def test_skipped_excluded_from_score(self):
        results = [
            {"id": 1, "name": "a", "status": "ok", "hint": ""},
            {"id": 16, "name": "b", "status": "skipped", "hint": ""},
        ]
        info = ie.score_and_verdict(results)
        self.assertEqual(info["score"], 100)

    def test_hard_fail_forces_reject(self):
        results = [{"id": 3, "name": "chat_artifacts", "status": "fail", "hint": "h"}]
        info = ie.score_and_verdict(results)
        self.assertTrue(info["hard_fail"])
        self.assertEqual(info["verdict"], "reject")

    def test_slop_fail_alone_does_not_hard_reject(self):
        # Calibration decision 2026-07-14: a single lexical feature must not
        # solo-reject a draft that passes everything else (an author whose
        # natural vocabulary overlaps the lexicon would be unwritable).
        results = [{"id": 1, "name": "slop_lexemes", "status": "fail", "hint": "h"}]
        info = ie.score_and_verdict(results)
        self.assertFalse(info["hard_fail"])
        self.assertEqual(info["verdict"], "pass")  # 100 - 18 = 82, no hard fail


class TestDistributionalAdvisoryBand(unittest.TestCase):
    # sylveste-lbe.9: features 16-18 warn in the genre-ambiguity band and
    # fail only below anomaly floors (0.15 / 0.60 / 0.40).
    def _fw_feature(self, sim_target_draft):
        base = {w: 10.0 for w in ie.FUNCTION_WORDS}
        return base, sim_target_draft

    def test_moderate_divergence_warns_not_fails(self):
        results = self._lint_with_fw(draft_fw_scale_half=True)
        fw = next(r for r in results if r["name"] == "function_word_delta")
        self.assertIn(fw["status"], ("warn", "ok"))

    def _lint_with_fw(self, draft_fw_scale_half):
        corpus = "\n\n".join((CORPUS_DIR / f"sample{i}.md").read_text() for i in (1, 2, 3))
        baseline = ie.build_profile(corpus)
        baseline["meta"] = {"files": 3}
        draft = (CORPUS_DIR / "sample1.md").read_text()
        prof = ie.build_profile(draft)
        internal = prof.pop("_internal")
        if draft_fw_scale_half:
            # push similarity into the 0.60-0.90 band artificially
            fw = prof["function_words_per_1k"]
            for i, w in enumerate(ie.FUNCTION_WORDS):
                fw[w] = fw[w] * (1.8 if i % 2 else 0.5)
        return ie.evaluate_lint(prof, internal, baseline)

    def test_catastrophic_divergence_still_fails(self):
        corpus = "\n\n".join((CORPUS_DIR / f"sample{i}.md").read_text() for i in (1, 2, 3))
        baseline = ie.build_profile(corpus)
        draft = (CORPUS_DIR / "sample1.md").read_text()
        prof = ie.build_profile(draft)
        internal = prof.pop("_internal")
        fw = prof["function_words_per_1k"]
        top = sorted(fw, key=lambda w: -baseline["function_words_per_1k"][w])
        for w in fw: fw[w] = 0.0
        fw[top[-1]] = 500.0  # all mass on the author's rarest function word
        results = ie.evaluate_lint(prof, internal, baseline)
        fwr = next(r for r in results if r["name"] == "function_word_delta")
        self.assertEqual(fwr["status"], "fail")


class TestProseExtraction(unittest.TestCase):
    # sylveste-lbe.9: distributional features (16-18) compare prose-to-prose.
    DOC = (
        "---\nregister: oss\n---\n"
        "# Title Line\n\n"
        "> A blockquote claim that is real prose and should be kept intact.\n\n"
        "A normal paragraph with enough words to matter for the comparison.\n\n"
        "| Command | Does |\n|---|---|\n| `/x apply` | Rewrite the thing |\n\n"
        "- short fragment\n"
        "- This list item is a complete sentence with more than eight words in it.\n\n"
        "Closing paragraph of ordinary flowing prose text here.\n"
    )

    def test_tables_headings_fragments_dropped(self):
        prose = ie.extract_prose(self.DOC)
        self.assertNotIn("Command", prose)
        self.assertNotIn("Title Line", prose)
        self.assertNotIn("short fragment", prose)

    def test_prose_and_long_list_items_kept(self):
        prose = ie.extract_prose(self.DOC)
        self.assertIn("blockquote claim", prose)
        self.assertIn("normal paragraph", prose)
        self.assertIn("complete sentence with more than eight words", prose)

    def test_table_invariance_of_distributions(self):
        # Appending a big table must not move the function-word distribution.
        base_prose = (CORPUS_DIR / "sample1.md").read_text(encoding="utf-8")
        table = "\n\n" + "\n".join(f"| cell {i} | run `cmd{i}` | value {i} |" for i in range(40))
        p1 = ie.build_profile(base_prose)
        p2 = ie.build_profile(base_prose + table)
        sim = ie.cosine_similarity(
            p1["function_words_per_1k"], p2["function_words_per_1k"], ie.FUNCTION_WORDS)
        self.assertGreater(sim, 0.995, f"table moved the distribution: {sim}")

    def test_structured_doc_skips_distributional_features(self):
        prose_bit = "One honest sentence of prose lives here among the machinery.\n\n"
        table = "\n".join(f"| cell {i} | more cells {i} | again {i} |" for i in range(120))
        profile = ie.build_profile(prose_bit + table)
        self.assertLess(profile["_internal"]["prose_word_count"], 300)


class TestFirstPersonCounter(unittest.TestCase):
    # Regression: I_RE matched lowercase-only "\\bi\\b", which never occurs
    # as an English word — first-person rate read 0.0 on a first-person essay.
    def test_capital_i_counted(self):
        prof = ie.build_profile("I think this works. I checked it twice today.")
        self.assertGreater(prof["per_1k"]["i"], 0)


class TestMarkdownBlockTermination(unittest.TestCase):
    # Regression: dogfooding 2026-07-14 found a real blog post producing a
    # 757-word "sentence" — frontmatter leaked and headings/list items glued
    # onto following paragraphs.
    DOC = (
        "---\nsource: interfluence:somewhere\nregister: oss\n---\n"
        "# A Heading Without Punctuation\n\n"
        "First real sentence here. Second one follows it.\n\n"
        "- list item one\n- list item two\n\n"
        "A paragraph-final line without a period\n\n"
        "Another normal paragraph ends properly.\n"
    )

    def test_frontmatter_stripped(self):
        cleaned = ie.strip_markdown(self.DOC)
        self.assertNotIn("interfluence:somewhere", cleaned)
        self.assertNotIn("register: oss", cleaned)

    def test_blocks_cannot_merge(self):
        cleaned = ie.strip_markdown(self.DOC)
        sents = ie.split_sentences(cleaned)
        longest = max(len(s.split()) for s in sents)
        self.assertLessEqual(longest, 8, f"block merge: {sents}")


class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors(self):
        v = {"a": 1.0, "b": 2.0}
        self.assertAlmostEqual(ie.cosine_similarity(v, v), 1.0)

    def test_orthogonal_vectors(self):
        a = {"x": 1.0}
        b = {"y": 1.0}
        self.assertEqual(ie.cosine_similarity(a, b, keys=["x", "y"]), 0.0)

    def test_zero_vector_returns_zero(self):
        a = {"x": 0.0}
        b = {"x": 1.0}
        self.assertEqual(ie.cosine_similarity(a, b, keys=["x"]), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

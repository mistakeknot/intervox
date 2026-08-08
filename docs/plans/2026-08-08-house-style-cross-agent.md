---
artifact_type: plan
bead: none
stage: design
---
# Cross-Agent House Style (Layered) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Bead:** none (intervox tracker write-blocked, schema v23→v53; see brainstorm Open Questions)
**Brainstorm:** `docs/brainstorms/2026-08-08-house-style-cross-agent-brainstorm.md` (all forks ruled)
**Goal:** Every agent runtime (Claude Code, Codex, Kimi) checks prose on declared voice-carrying paths against one canon: Vale GSV rules at any length + intervox stylometric verify for long-form, advisory at edit time, blocking at commit time.

**Architecture:** intervox is the published umbrella plugin. A `.voicepaths` file at a repo root declares which files carry voice and which register/style applies. `scripts/voice-check.sh` orchestrates both layers; plugin hooks run it (advisory on PostToolUse Edit/Write, gate on PreToolUse `git commit`); Codex/Kimi run the same script per AGENTS.md. Canon = `gsvdotcom/docs/canon/copy-voice.md`; the Vale style and the fingerprint are dated derivations.

**Tech Stack:** bash + Python 3.11 stdlib (engine), Vale (optional, brew), pytest, Astro repos as adopters.

**Cross-repo note:** Tasks touch five repos (intervox, dotfiles, gsvdotcom, interbrowse, jawnomicon) plus `~/.config` and `~/.codex`. Commit in the repo each task names, `git commit -F <msgfile> -- <paths>`, never `-m`. jawnomicon is sibling-session-owned: check `git -C ~/projects/jawnomicon log --oneline -3` for a foreign HEAD before task-10 and rebase-pull first.

**Interactive tasks:** task-8 requires mk via AskUserQuestion (decide-against-material ruling). Do NOT delegate task-8 to a subagent or Codex; run it in the main session.

---

## Must-Haves

**Truths:**
- An agent editing a declared voice file sees an advisory report card naming specific flags (edit time, non-blocking).
- `git commit` touching declared voice files is blocked when Vale reports error-level findings or intervox verify hard-rejects; the block message names file, rule, and fix hint.
- A commit touching only undeclared files is never delayed or blocked by voice machinery.
- Codex/Kimi sessions get the identical verdicts by running `voice-check.sh` per AGENTS.md — no Claude-only dependency.
- `docs/canon/copy-voice.md` is the single canon; COPY_GUIDE.md and VOICE.md are pointers; both machine layers cite it with a derivation date.

**Artifacts:**
- `intervox/engine/voicepaths.py` exports `load(root)`, `match(root, path)`, CLI `python3 voicepaths.py match <root> <path>...`
- `intervox/scripts/voice-check.sh` (advisory + `--gate` modes)
- `intervox/hooks/hooks.json`, `intervox/hooks/voice-advisory.sh`, `intervox/hooks/voice-commit-gate.sh`
- `intervox/skills/housecheck/SKILL.md`
- `gsvdotcom/vale/styles/GSV/*.yml` + `gsvdotcom/.vale.ini`; `gsvdotcom/.voicepaths`; `jawnomicon/.voicepaths`
- Consolidated `gsvdotcom/docs/canon/copy-voice.md` with `## Ruling (mk, 2026-08-…)` vocabulary section

**Key Links:**
- hooks → `voice-check.sh` → `voicepaths.py` + `resolve-register.sh` → `~/.config/intervox/fingerprints/<register>.json` (so task-1/2 repairs precede task-4+)
- Vale layer resolves `.vale.ini` at the **adopter repo** root, not the plugin
- `verify` exit 2 (hard fail) is the only stylometric block while the gsv-site corpus is under the 20k floor — exit 1 "revise" passes the gate (rules-heavy mode per brainstorm)

---

### Task 1: Repair the voice-profile symlink chain

**Files:** `~/.config/intervox/voice-profile.md`, `~/.config/intervox/fingerprints/voice-profile.md`, `~/.config/intervoice/voice-profile.md` (machine-local symlinks; no repo commit)

**Step 1:** Audit before touching (dotfiles rule: readlink first):
```bash
for l in ~/.config/intervox/voice-profile.md ~/.config/intervox/fingerprints/voice-profile.md ~/.config/intervoice/voice-profile.md; do
  echo "$l -> $(readlink "$l" 2>/dev/null || echo MISSING)"; [ -e "$l" ] && echo "  resolves OK" || echo "  BROKEN"
done
ls -la /Users/sma/projects/dotfiles/common/projects/voice-profile.md
```
**Step 2:** Retarget every broken link to the live file:
```bash
ln -sfn /Users/sma/projects/dotfiles/common/projects/voice-profile.md ~/.config/intervox/voice-profile.md
```
Apply the same retarget to any other audited link that pointed at `dotfiles/projects/…`; leave healthy links alone.
**Step 3:** Confirm the resolver works: `bash ~/projects/Sylveste/interverse/intervox/scripts/resolve-register.sh --list` → exit 0, lists Registers 1–4.
**Step 4:** Record zklw follow-up: append one line to the plan's execution log noting "zklw needs the same symlink audit" (do not ssh-fix zklw in this task).

<verify>
- run: `bash ~/projects/Sylveste/interverse/intervox/scripts/resolve-register.sh --list`
  expect: exit 0
</verify>

### Task 2: `gsv-site` register in resolve-register.sh

**Files:** Modify: `intervox/scripts/resolve-register.sh`; Test: `intervox/tests/test_resolve_register.sh` (create)

**Step 1:** Read the script's register-normalization function. Add a `gsv-site` branch: accepts `gsv-site`, `gsv`, `site` (case/hyphen tolerant). Since the profile has no `## Register: gsv-site` section yet, the branch resolves the *fingerprint register name* (`gsv-site`) and prints Foundation + `## Register 3: External` as the prose delta, with a one-line header comment `<!-- register: gsv-site (prose delta: External; canon: gsvdotcom docs/canon/copy-voice.md) -->`.
**Step 2:** Extend `--infer`: if the target path's repo root (walk up to `.git`) contains `.voicepaths` with a `register:` line, that register wins over the existing path heuristics.
**Step 3:** Write `tests/test_resolve_register.sh`: bash test that (a) `resolve-register.sh gsv-site` exits 0 and stdout contains `register: gsv-site`; (b) `--infer` on a temp dir containing `.voicepaths` with `register: gsv-site` returns the same; (c) unknown register still exits 3. Run it; fix until green.
**Step 4:** Commit (intervox repo): `feat: gsv-site register resolution + .voicepaths-aware inference`

<verify>
- run: `bash ~/projects/Sylveste/interverse/intervox/scripts/resolve-register.sh gsv-site`
  expect: exit 0
- run: `bash ~/projects/Sylveste/interverse/intervox/tests/test_resolve_register.sh`
  expect: exit 0
</verify>

### Task 3: `voicepaths.py` — declared-paths module

**Files:** Create: `intervox/engine/voicepaths.py`; Test: `intervox/tests/test_voicepaths.py`

`.voicepaths` format (repo root, `#` comments):
```
# .voicepaths — declared voice-carrying paths
register: gsv-site
style: GSV
src/content/**/*.md
src/pages/**/*.astro
```

**Step 1:** Write failing tests: parse (register/style/globs), `match` positive (`src/content/a/b.md`), negative (`src/lib/x.ts`), `**` spans directories, no-`.voicepaths` → no matches, CLI `match <root> <paths...>` prints only matching paths and exits 0 (exit 1 when none match).
**Step 2:** `pytest tests/test_voicepaths.py -v` → FAIL (module missing).
**Step 3:** Implement (stdlib only):
```python
"""voicepaths: parse a repo's .voicepaths declaration and match files against it."""
from __future__ import annotations
import re, sys
from pathlib import Path

def _glob_to_re(glob: str) -> re.Pattern:
    out, i = [], 0
    while i < len(glob):
        c = glob[i]
        if glob[i:i+3] == "**/":
            out.append("(?:.+/)?"); i += 3
        elif glob[i:i+2] == "**":
            out.append(".*"); i += 2
        elif c == "*":
            out.append("[^/]*"); i += 1
        elif c == "?":
            out.append("[^/]"); i += 1
        else:
            out.append(re.escape(c)); i += 1
    return re.compile("^" + "".join(out) + "$")

def load(root: str | Path) -> dict:
    p = Path(root) / ".voicepaths"
    cfg = {"register": None, "style": None, "globs": [], "patterns": []}
    if not p.is_file():
        return cfg
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line and not any(ch in line.split(":", 1)[0] for ch in "*/?."):
            key, val = (s.strip() for s in line.split(":", 1))
            if key in ("register", "style"):
                cfg[key] = val
                continue
        cfg["globs"].append(line)
        cfg["patterns"].append(_glob_to_re(line))
    return cfg

def match(root: str | Path, path: str | Path) -> bool:
    cfg = load(root)
    try:
        rel = Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return False
    return any(p.match(rel) for p in cfg["patterns"])

def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[0] != "match":
        print("usage: voicepaths.py match <root> <path>...", file=sys.stderr)
        return 2
    root, hits = argv[1], []
    for f in argv[2:]:
        if match(root, f):
            hits.append(f); print(f)
    return 0 if hits else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```
**Step 4:** `pytest tests/test_voicepaths.py -v` → PASS. Full suite: `pytest` → all green (52 existing + new).
**Step 5:** Commit: `feat: voicepaths declaration module (.voicepaths parser + matcher)`

<verify>
- run: `cd ~/projects/Sylveste/interverse/intervox && python3 -m pytest tests/test_voicepaths.py -q`
  expect: exit 0
</verify>

### Task 4: `voice-check.sh` — layered orchestrator

**Files:** Create: `intervox/scripts/voice-check.sh`, `intervox/tests/test_voice_check.sh`; reuse fixtures `tests/fixtures/clean-draft.md`, `tests/fixtures/sloppy-draft.md`

Contract: `voice-check.sh [--gate] [--root <repo-root>] <file>...`
- Filters args through `voicepaths.py match` (no `.voicepaths` or no matches → exit 0, print `voice-check: no declared voice files touched`).
- **Layer 1 (Vale):** if `command -v vale` and `<root>/.vale.ini` exists → `vale --output=line <files>`. Error-level findings: advisory mode prints them; gate mode marks FAIL.
- **Layer 2 (intervox):** baseline = `${XDG_CONFIG_HOME:-$HOME/.config}/intervox/fingerprints/<register>.json` (register from `.voicepaths`, fallback `all.json`). Advisory: `engine/intervox lint --draft <f> --baseline <b> --format table`. Gate: `engine/intervox verify --draft <f> --baseline <b>`; **only exit 2 marks FAIL** (exit 1 "revise" passes — rules-heavy mode while the corpus is thin; print the revise hints anyway).
- Exit: advisory always 0; `--gate` exits 2 on any FAIL, else 0. Vale absent → print one line `voice-check: vale not installed — rules layer skipped (brew install vale)` and continue.
- Env escape hatch: `VOICEGATE=skip` → print `voice-check: gate skipped by VOICEGATE=skip` and exit 0 (gate mode only).

**Steps:** (1) write `tests/test_voice_check.sh` — temp repo with `.voicepaths` declaring `*.md`; assert: sloppy fixture in gate mode exits 2 (sloppy-draft must trip a hard-fail feature; if it doesn't, extend the fixture with chat-artifact lines like "Certainly! Here's the updated copy:" rather than weakening the assertion); clean fixture gate exits 0; undeclared file exits 0; `VOICEGATE=skip` exits 0. (2) run → FAIL. (3) implement per contract above (bash, `set -euo pipefail`, no external deps beyond optional vale). (4) run tests + full pytest → green. (5) Commit: `feat: voice-check layered orchestrator (vale + stylometric verify)`.

<verify>
- run: `bash ~/projects/Sylveste/interverse/intervox/tests/test_voice_check.sh`
  expect: exit 0
</verify>

### Task 5: Plugin hooks (advisory edit + commit gate)

**Files:** Create: `intervox/hooks/hooks.json`, `intervox/hooks/voice-advisory.sh`, `intervox/hooks/voice-commit-gate.sh`, `intervox/tests/test_hooks.sh`; Modify: `intervox/.claude-plugin/plugin.json` (add `"hooks": "./hooks/hooks.json"`, bump `"version": "0.3.0"`), `intervox/kimi.plugin.json` (version bump only — kimi consumes the skill, not hooks)

`hooks/hooks.json` (mirror clavain's shape):
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/voice-advisory.sh", "timeout": 10 }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/voice-commit-gate.sh", "timeout": 20 }
        ]
      }
    ]
  }
}
```

`voice-advisory.sh`: read stdin JSON (python3 one-liner), extract `tool_input.file_path`; find repo root via `git -C <dir> rev-parse --show-toplevel` (not a repo → exit 0); `voicepaths.py match` (no match → exit 0); run `voice-check.sh --root <root> <file>` capturing the report; if findings exist emit `{"decision":"block","reason":"voice-check advisory (non-blocking):\n<report>\nFix now or before commit — the commit gate enforces."}` (the clavain agents-md-refresh advisory pattern) else exit 0 silently. Never exit nonzero on internal errors — advisory must not break editing (`trap 'exit 0' ERR`).

`voice-commit-gate.sh`: read stdin JSON; `tool_input.command` must match `git commit` (else exit 0); repo root from the command's working dir; staged files: `git diff --cached --name-only`; filter via `voicepaths.py match` (none → exit 0); run `voice-check.sh --gate --root <root> <staged...>`; on exit 2 emit `{"decision":"block","reason":"HOUSE-STYLE GATE: <report>\nFix the flagged copy, or re-run with VOICEGATE=skip prefixed to the commit for a documented exception."}`; else exit 0. `VOICEGATE=skip` inside the command string also passes (the escape hatch is visible in the transcript by design).

**Steps:** (1) `tests/test_hooks.sh`: pipe fixture PostToolUse/PreToolUse JSON through each hook against a temp repo (declared sloppy file → advisory emits `"decision"`, gate emits block; undeclared → both silent exit 0; malformed JSON → exit 0). (2) implement. (3) tests green. (4) Commit: `feat: advisory edit hook + commit gate (voice-carrying paths only)`.

<verify>
- run: `bash ~/projects/Sylveste/interverse/intervox/tests/test_hooks.sh`
  expect: exit 0
- run: `python3 -c "import json; d=json.load(open('/Users/sma/projects/Sylveste/interverse/intervox/.claude-plugin/plugin.json')); assert d['version']=='0.3.0' and d['hooks']"`
  expect: exit 0
</verify>

### Task 6: `housecheck` skill

**Files:** Create: `intervox/skills/housecheck/SKILL.md`

Content (complete): frontmatter (`name: housecheck`, description "Run the layered house-style check — Vale GSV rules + stylometric verify — on files or a directory; report card per file", `allowed-tools: Bash, Read`); body instructs: resolve target files (arg or `git diff --name-only` default), run `${CLAUDE_PLUGIN_ROOT}/scripts/voice-check.sh` (advisory) or `--gate` when the user says "gate"/"verify", render the report grouped by layer, and for each finding show the sentence + one concrete rewrite. Cite canon: "Rules derive from gsvdotcom `docs/canon/copy-voice.md` — when a finding feels wrong, the canon doc wins; propose a canon amendment rather than muting the rule." Both manifests already glob `"skills": "./skills/"`, so no manifest edit. Commit: `feat: housecheck skill (layered report card)`.

<verify>
- run: `test -s ~/projects/Sylveste/interverse/intervox/skills/housecheck/SKILL.md`
  expect: exit 0
</verify>

### Task 7: Vale GSV style → gsvdotcom (canonical home)

**Files:** Create: `gsvdotcom/vale/styles/GSV/{Buzzwords,ThroatClearing,Overdefining,AIGenericisms}.yml` (copy from `interbrowse/vale/styles/GSV/`), `gsvdotcom/.vale.ini`; Modify: `interbrowse/vale/styles/GSV/*.yml` (header comment), `interbrowse/skills/register-lint/SKILL.md` (source note)

**Step 1:** Copy the four rule files verbatim into gsvdotcom; update each header comment to `# Canonical copy. Derived from docs/canon/copy-voice.md (2026-08-08 derivation; supersedes the 2026-07-07 COPY_GUIDE derivation).`
**Step 2:** `gsvdotcom/.vale.ini`:
```ini
StylesPath = vale/styles
MinAlertLevel = suggestion

[*.{md,mdx,astro}]
BasedOnStyles = GSV
```
**Step 3:** interbrowse: add to each rule header `# Vendored fallback — canonical copy: gsvdotcom vale/styles/GSV (derived from docs/canon/copy-voice.md).` and the same one-liner under the SKILL.md "bundled style" paragraph.
**Step 4:** If `command -v vale`: `cd ~/projects/gsvdotcom && vale README.md >/dev/null; echo $?` — any exit is fine (findings expected); the check is that Vale parses the config. Vale absent: note it and continue.
**Step 5:** Commit both repos separately: gsvdotcom `style: adopt canonical Vale GSV style + .vale.ini`; interbrowse `docs: mark bundled GSV style as vendored fallback`.

<verify>
- run: `ls ~/projects/gsvdotcom/vale/styles/GSV/ | wc -l | grep -q 4 && test -s ~/projects/gsvdotcom/.vale.ini && echo ok`
  expect: contains "ok"
</verify>

### Task 8: Canon consolidation — INTERACTIVE (mk rules against real samples)

**Files:** Modify: `gsvdotcom/docs/canon/copy-voice.md`, `gsvdotcom/COPY_GUIDE.md`, `gsvdotcom/VOICE.md`; possibly `gsvdotcom/vale/styles/GSV/Buzzwords.yml`

**Run in the main session only.** mk ruled (2026-08-08): decide the vocabulary line against real samples, not in the abstract.

**Step 1:** Harvest material: grep shipped prose (`gsvdotcom/src/content/**/*.md*`, jawnomicon `site/src` chrome strings) for the contested terms (comparative advantage, coordination mechanism, dispersed judgment, topology, emergence, substrate, legibility, leverage, ecosystem, synergy). Collect 10–15 real sentences with file:line. If a term never appears in shipped prose, say so — absence is evidence.
**Step 2:** Present the samples to mk via AskUserQuestion (batched by term-group, recommendation first, per interview rules) and record the ruling in mk's actual selections.
**Step 3:** Write the merged `docs/canon/copy-voice.md`: keep the "Document, don't pitch" core; fold in VOICE.md's constraints; add `## Ruling (mk, 2026-08-08): the vocabulary line` recording the ruling and the sample citations; add a derivations footer naming the Vale style and gsv-site fingerprint as dated derivations.
**Step 4:** Reduce `COPY_GUIDE.md` and `VOICE.md` each to a 3-line pointer stub at `docs/canon/copy-voice.md` (keep the files — inbound links survive).
**Step 5:** If the ruling moved the buzz line, update `Buzzwords.yml` tokens to match and bump its derivation date.
**Step 6:** Commit (gsvdotcom): `canon: consolidate copy-voice as single house-style source (mk vocabulary ruling inside)`.

<verify>
- run: `grep -c "Ruling (mk, 2026-08" ~/projects/gsvdotcom/docs/canon/copy-voice.md`
  expect: contains "1"
- run: `wc -l < ~/projects/gsvdotcom/COPY_GUIDE.md | tr -d ' '`
  expect: contains "3"
</verify>

### Task 9: gsvdotcom adoption

**Files:** Create: `gsvdotcom/.voicepaths`; Modify: `gsvdotcom/AGENTS.md`, `gsvdotcom/CLAUDE.md`

`.voicepaths`:
```
# Voice-carrying paths — see docs/canon/copy-voice.md
register: gsv-site
style: GSV
src/content/**/*.md
src/content/**/*.mdx
src/pages/**/*.astro
docs/canon/*.md
README.md
```
`AGENTS.md` — append (verbatim):
```markdown
## House style (all agents)

Prose on paths declared in `.voicepaths` follows `docs/canon/copy-voice.md`.
Before committing changes to those paths, run:

    ~/projects/Sylveste/interverse/intervox/scripts/voice-check.sh --gate --root . <changed files>

Exit 2 means fix the copy before committing. Claude Code sessions get this
automatically via the intervox plugin hooks; Codex/Kimi sessions run it
manually. Documented exceptions: prefix the commit command with VOICEGATE=skip.
```
`CLAUDE.md`: replace the `_Add your project-specific conventions here_` placeholder with a one-line pointer to that AGENTS.md section. Commit: `chore: declare voice-carrying paths + house-style gate wiring`.

<verify>
- run: `grep -q "voice-check.sh" ~/projects/gsvdotcom/AGENTS.md && test -s ~/projects/gsvdotcom/.voicepaths && echo ok`
  expect: contains "ok"
</verify>

### Task 10: jawnomicon adoption (rules-only until a fingerprint exists)

**Files:** Create: `jawnomicon/.voicepaths`; Modify: `jawnomicon/AGENTS.md`

Pre-step: `git -C ~/projects/jawnomicon log --oneline -3` — if HEAD moved beyond `5dfdb86`, `git pull --rebase` first (sibling-owned repo).
`.voicepaths`: register `gsv-site` is WRONG for jawnomicon's voice — omit `register:` (stylometric layer then uses `all.json`, mk's own baseline) and set `style: GSV` only if jawnomicon gets a `.vale.ini` (it does: copy gsvdotcom's `.vale.ini` — the four LLMese rules are brand-neutral except Buzzwords; include a `# Buzzwords derives from gsvdotcom canon; revisit if it over-fires here` comment). Globs: `site/src/pages/**/*.astro`, `site/src/layouts/**/*.astro`, `README.md`.
AGENTS.md: same House-style section as task-9 with the jawnomicon paths. Commit (jawnomicon repo): `chore: declare voice-carrying paths (site chrome) + house-style gate`.

<verify>
- run: `test -s ~/projects/jawnomicon/.voicepaths && grep -q "voice-check.sh" ~/projects/jawnomicon/AGENTS.md && echo ok`
  expect: contains "ok"
</verify>

### Task 11: Codex global wiring

**Files:** Modify: `~/.codex/AGENTS.md` (readlink first — if it is a symlink into dotfiles, edit the target in the dotfiles repo and commit there)

Append a `## House style` section: same content as task-9's but generic — "any repo with a `.voicepaths` file: run voice-check.sh --gate before committing declared files; canon lives at the path the repo's AGENTS.md names." Commit in whichever repo owns the file (dotfiles) or note "machine-local file, no repo" in the execution log.

<verify>
- run: `grep -q "voicepaths" ~/.codex/AGENTS.md && echo ok`
  expect: contains "ok"
</verify>

### Task 12: Rebuild the gsv-site fingerprint from real prose

**Files:** `~/.config/intervox/corpus/gsv-site/` (replace synthetic samples), `~/.config/intervox/fingerprints/gsv-site.json` (regenerate)

**Step 1:** Remove the 8 synthetic `sample-2026071*-concept-*` files (they are fabricated baseline — worse than thin).
**Step 2:** Ingest real shipped prose with provenance frontmatter per corpus convention: gsvdotcom `src/content/**/*.md*` body text (strip frontmatter), the post-consolidation `docs/canon/*.md`, and gsvdotcom page prose. Use the existing `/intervox ingest` skill flow (contamination screening included). Do NOT ingest jawnomicon copy (different voice).
**Step 3:** `engine/intervox fingerprint` for register gsv-site; print total word count. Record honestly in the fingerprint meta and execution log: if < 20,000 words, note "gate stays rules-heavy (verify exit 1 passes)" — this is expected; do not pad the corpus to hit the floor.
**Step 4:** No repo commit (config lives outside git); log the word count.

<verify>
- run: `python3 -c "import json,glob; d=json.load(open(glob.glob('/Users/sma/.config/intervox/fingerprints/gsv-site.json')[0])); print('wc', d.get('meta',{}).get('word_count') or d.get('meta',{}))"`
  expect: contains "wc"
- run: `ls /Users/sma/.config/intervox/corpus/gsv-site/ | grep -c "sample-2026071" || true`
  expect: contains "0"
</verify>

### Task 13: Publish intervox 0.3.0

**Files:** intervox repo (push), `Sylveste/core/marketplace/.claude-plugin/marketplace.json` (version sync)

**Step 1:** Full intervox suite green: `python3 -m pytest -q` + the three bash test files.
**Step 2:** Push intervox to `origin` (github.com/mistakeknot/intervox) — `git pull --rebase && git push`, verify `## main...origin/main` clean.
**Step 3:** Version sync via `/interpub:release` (it syncs plugin.json ↔ marketplace.json). If the release skill is unavailable in-session, edit the marketplace entry's `"version"` to `0.3.0` by hand, commit in the Sylveste repo (protected main — land via the repo's normal flow; check branch rules before pushing).
**Step 4:** Install here: `claude plugin install intervox@interagency-marketplace` (or update), then confirm the hook fires: edit a scratch file under a temp repo with `.voicepaths` and observe the advisory. Note: marketplace pulls from GitHub, so step 2 must precede step 4.
**Step 5:** Log zklw/other-machine rollout as follow-up (publish wave runs from zklw per ops memory).

<verify>
- run: `cd ~/projects/Sylveste/interverse/intervox && git status -sb | head -1`
  expect: contains "## main...origin/main"
- run: `python3 -c "import json;a=json.load(open('/Users/sma/projects/Sylveste/interverse/intervox/.claude-plugin/plugin.json'));b=json.load(open('/Users/sma/projects/Sylveste/core/marketplace/.claude-plugin/marketplace.json'));v=[p for p in b['plugins'] if p['name']=='intervox'][0]['version'];assert a['version']==v=='0.3.0', (a['version'],v)"`
  expect: exit 0
</verify>

---

## Acceptance Criteria

1. Register resolution works end-to-end, including the new register.
   ```check
   bash ~/projects/Sylveste/interverse/intervox/scripts/resolve-register.sh gsv-site >/dev/null
   ```
2. Full intervox test suite green (existing 52 + voicepaths + voice-check + hooks + resolve-register tests).
   ```check
   cd ~/projects/Sylveste/interverse/intervox && python3 -m pytest -q && bash tests/test_resolve_register.sh && bash tests/test_voice_check.sh && bash tests/test_hooks.sh
   ```
3. The gate blocks LLMese and passes clean copy: sloppy fixture exits 2 under `--gate`, clean fixture exits 0 (asserted inside test_voice_check.sh, run above).
4. Undeclared files are untouched: a commit-gate invocation whose staged files match no `.voicepaths` glob exits 0 silently (asserted inside test_hooks.sh).
5. Canon consolidated with mk's ruling recorded.
   ```check
   grep -q "Ruling (mk, 2026-08" ~/projects/gsvdotcom/docs/canon/copy-voice.md && [ "$(wc -l < ~/projects/gsvdotcom/COPY_GUIDE.md)" -le 5 ] && [ "$(wc -l < ~/projects/gsvdotcom/VOICE.md)" -le 5 ]
   ```
6. Both adopter repos declare paths and wire the gate for non-Claude agents.
   ```check
   test -s ~/projects/gsvdotcom/.voicepaths && grep -q voice-check ~/projects/gsvdotcom/AGENTS.md && test -s ~/projects/jawnomicon/.voicepaths && grep -q voice-check ~/projects/jawnomicon/AGENTS.md && grep -q voicepaths ~/.codex/AGENTS.md
   ```
7. Canonical Vale style lives in gsvdotcom (4 rules + .vale.ini); interbrowse copy marked vendored.
   ```check
   [ "$(ls ~/projects/gsvdotcom/vale/styles/GSV/*.yml | wc -l)" -eq 4 ] && test -s ~/projects/gsvdotcom/.vale.ini && grep -ql "vendored" ~/projects/Sylveste/interverse/interbrowse/vale/styles/GSV/Buzzwords.yml
   ```
8. gsv-site corpus contains no synthetic samples; fingerprint regenerated; word count recorded (rules-heavy mode documented if under floor).
   ```check
   [ "$(ls /Users/sma/.config/intervox/corpus/gsv-site/ | grep -c 'sample-2026071')" -eq 0 ]
   ```
9. intervox 0.3.0 published: repo clean vs origin, plugin.json/marketplace.json versions agree at 0.3.0 (task-13 verify commands).
10. All repo work committed via `git commit -F <file> -- <paths>` and pushed; no repo left dirty. Stop after 2 failed attempts at any gate and escalate rather than looping (two-strikes rule).

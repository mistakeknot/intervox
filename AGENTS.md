# intervox — Agent Guide

Voice engine with a closed loop: prose profile steers generation, stylometric fingerprint verifies output. Successor to interfluence and intervoice (both deprecated).

## Architecture in one breath

- `engine/intervox` — stdlib-only Python CLI: `fingerprint`, `lint`, `verify`, `retrieve`, `registers`. All measurement lives here. No pip deps, no server, no build.
- `scripts/resolve-register.sh` — extracts Foundation + selected Register section from the global profile (intervoice-compatible format). Falls back to the legacy intervoice profile path.
- `skills/` — Claude-side orchestration. `apply` is the flagship: resolve register → retrieve exemplars → draft → lint → revise (≤3 rounds) → verify → present with report card.
- `agents/voice-analyzer.md` — literary analysis; every profile claim must cite a corpus quote or a fingerprint number.
- User data: `${XDG_CONFIG_HOME:-~/.config}/intervox/` (profile, corpus/<register>/, fingerprints/, optional lexicon.json). Never write user data into project repos.

## Conventions

- Engine changes require `python3 tests/test_engine.py` green before commit.
- Thresholds in the linter are baseline-relative. Never add a universal-constant threshold without an absolute-fallback rationale in a comment.
- The slop lexicon is versioned and model-era-aware; additions need a cited source (Kobak/Liang/Matsui lineage or Wikipedia signs-of-AI-writing) in the commit message.
- Skills call the engine via Bash with explicit paths (`${CLAUDE_PLUGIN_ROOT}/engine/intervox`). No skill re-implements measurement in prose.
- Profile format is frozen to intervoice's shape (## Foundation + ## Register N sections). Breaking it breaks migration; don't.
- Docs follow the repo voice: plain, concrete, no LLMisms (yes, the linter applies to this repo's own docs).

## Key docs

- `docs/plans/2026-07-14-intervox-v0-build-plan.md` — v0 scope, lineage decisions, migration runbook
- `docs/research/` — the research brief and three source reports the architecture is built on
- `PHILOSOPHY.md` — core positions; read before proposing architecture changes

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->

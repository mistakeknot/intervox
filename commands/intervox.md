---
description: Voice engine with a closed loop — apply, lint, fingerprint, ingest, analyze, compare, optimize, migrate
argument-hint: "<apply|lint|fingerprint|ingest|analyze|compare|optimize|migrate|registers> [args]"
---

# /intervox

Dispatch to the matching intervox skill based on the first argument in `$ARGUMENTS`:

| Subcommand | Skill | Notes |
|---|---|---|
| `apply [--register=<r>] <path or text>` | apply | Closed-loop rewrite with verification report card |
| `lint <path or text>` | lint | Fingerprint-relative LLMism/voice report |
| `fingerprint` | fingerprint | Rebuild baselines from corpus |
| `ingest <files...>` | ingest | Add samples with provenance |
| `analyze` | analyze | Voice-analyzer agent writes/updates the prose profile |
| `compare <path>` | compare | Score existing text against the voice |
| `optimize` | optimize | Token-trim the prose profile |
| `migrate` | migrate | Import from intervoice/interfluence |
| `registers` | — | Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/resolve-register.sh --list` and show the result |

No subcommand: show this table plus current state — whether a profile is found (run the resolver with `--list`), whether fingerprints exist (`ls ${XDG_CONFIG_HOME:-$HOME/.config}/intervox/fingerprints/ 2>/dev/null`), and corpus size (`find ${XDG_CONFIG_HOME:-$HOME/.config}/intervox/corpus -name '*.md' 2>/dev/null | wc -l` samples).

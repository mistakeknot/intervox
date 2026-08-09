Implemented and verified the advisory hook, commit gate, clean-file silence, malformed-input fail-open behavior, and 0.3.0 manifest bumps.

Verification:

- Python suite: 71 passed
- All shell suites passed
- Shell syntax and JSON validation passed
- Not committed or pushed; shared Task 2/4 work remains uncommitted

VERDICT: NEEDS_ATTENTION [implementation verified; awaiting landing choice for the shared worktree]  
FILES_CHANGED: [.claude-plugin/plugin.json, kimi.plugin.json, hooks/hooks.json, hooks/voice-advisory.sh, hooks/voice-commit-gate.sh, tests/test_hooks.sh]
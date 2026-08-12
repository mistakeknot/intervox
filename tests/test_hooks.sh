#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ADVISORY="$ROOT_DIR/hooks/voice-advisory.sh"
COMMIT_GATE="$ROOT_DIR/hooks/voice-commit-gate.sh"
HOOKS_JSON="$ROOT_DIR/hooks/hooks.json"
ENGINE="$ROOT_DIR/engine/intervox"
FIXTURES="$ROOT_DIR/tests/fixtures"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

CONFIG="$TMP_DIR/config"
DECLARED_REPO="$TMP_DIR/declared-repo"
UNDECLARED_REPO="$TMP_DIR/undeclared-repo"
mkdir -p "$CONFIG/intervox/fingerprints" "$DECLARED_REPO" "$UNDECLARED_REPO"

python3 "$ENGINE" fingerprint \
  --corpus "$FIXTURES/corpus" \
  --out "$CONFIG/intervox/fingerprints/all.json" >/dev/null

printf '%s\n' '*.md' >"$DECLARED_REPO/.voicepaths"
cp "$FIXTURES/sloppy-draft.md" "$DECLARED_REPO/sloppy.md"
cp "$FIXTURES/clean-draft.md" "$DECLARED_REPO/clean.md"
git -C "$DECLARED_REPO" init -q
git -C "$DECLARED_REPO" add sloppy.md

printf '%s\n' '*.md' >"$UNDECLARED_REPO/.voicepaths"
printf '%s\n' 'not voice-carrying' >"$UNDECLARED_REPO/notes.txt"
git -C "$UNDECLARED_REPO" init -q
git -C "$UNDECLARED_REPO" add notes.txt

test -x "$ADVISORY"
test -x "$COMMIT_GATE"

python3 - "$HOOKS_JSON" "$ROOT_DIR/.claude-plugin/plugin.json" "$ROOT_DIR/kimi.plugin.json" <<'PY'
import json
import sys

hooks_path, claude_path, kimi_path = sys.argv[1:]
hooks = json.load(open(hooks_path, encoding="utf-8"))
claude = json.load(open(claude_path, encoding="utf-8"))
kimi = json.load(open(kimi_path, encoding="utf-8"))

assert hooks["hooks"]["PostToolUse"][0]["matcher"] == "Edit|Write|MultiEdit"
assert hooks["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
# Version consistency, not a literal: a hardcoded version rotted silently
# (asserted 0.3.0 while the plugin shipped 0.3.2, red since 0.3.1).
import re
assert re.fullmatch(r"\d+\.\d+\.\d+", claude["version"]), claude["version"]
assert kimi["version"] == claude["version"], (kimi["version"], claude["version"])
assert claude["hooks"] == "./hooks/hooks.json"
PY

advisory_input="$(python3 -c 'import json,sys; print(json.dumps({"tool_input":{"file_path":sys.argv[1]}}))' "$DECLARED_REPO/sloppy.md")"
advisory_output="$(printf '%s\n' "$advisory_input" | XDG_CONFIG_HOME="$CONFIG" "$ADVISORY")"
python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["decision"] == "block"; assert "voice-check advisory (non-blocking)" in d["reason"]; assert "Fix now or before commit" in d["reason"]' <<<"$advisory_output"

clean_advisory_input="$(python3 -c 'import json,sys; print(json.dumps({"tool_input":{"file_path":sys.argv[1]}}))' "$DECLARED_REPO/clean.md")"
clean_advisory_output="$(printf '%s\n' "$clean_advisory_input" | XDG_CONFIG_HOME="$CONFIG" "$ADVISORY")"
[[ -z "$clean_advisory_output" ]]

gate_input="$(python3 -c 'import json,sys; print(json.dumps({"cwd":sys.argv[1],"tool_input":{"command":"git commit -F /tmp/message"}}))' "$DECLARED_REPO")"
gate_output="$(printf '%s\n' "$gate_input" | XDG_CONFIG_HOME="$CONFIG" "$COMMIT_GATE")"
python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["decision"] == "block"; assert "HOUSE-STYLE GATE:" in d["reason"]; assert "Fix the flagged copy" in d["reason"]' <<<"$gate_output"

undeclared_advisory_input="$(python3 -c 'import json,sys; print(json.dumps({"tool_input":{"file_path":sys.argv[1]}}))' "$UNDECLARED_REPO/notes.txt")"
undeclared_advisory_output="$(printf '%s\n' "$undeclared_advisory_input" | XDG_CONFIG_HOME="$CONFIG" "$ADVISORY")"
[[ -z "$undeclared_advisory_output" ]]

undeclared_gate_input="$(python3 -c 'import json,sys; print(json.dumps({"cwd":sys.argv[1],"tool_input":{"command":"git commit -F /tmp/message"}}))' "$UNDECLARED_REPO")"
undeclared_gate_output="$(printf '%s\n' "$undeclared_gate_input" | XDG_CONFIG_HOME="$CONFIG" "$COMMIT_GATE")"
[[ -z "$undeclared_gate_output" ]]

non_commit_input="$(python3 -c 'import json,sys; print(json.dumps({"cwd":sys.argv[1],"tool_input":{"command":"git status"}}))' "$DECLARED_REPO")"
non_commit_output="$(printf '%s\n' "$non_commit_input" | XDG_CONFIG_HOME="$CONFIG" "$COMMIT_GATE")"
[[ -z "$non_commit_output" ]]

skip_input="$(python3 -c 'import json,sys; print(json.dumps({"cwd":sys.argv[1],"tool_input":{"command":"VOICEGATE=skip git commit -F /tmp/message"}}))' "$DECLARED_REPO")"
skip_output="$(printf '%s\n' "$skip_input" | XDG_CONFIG_HOME="$CONFIG" "$COMMIT_GATE")"
[[ -z "$skip_output" ]]

malformed_advisory_output="$(printf '%s\n' '{not-json' | XDG_CONFIG_HOME="$CONFIG" "$ADVISORY")"
malformed_gate_output="$(printf '%s\n' '{not-json' | XDG_CONFIG_HOME="$CONFIG" "$COMMIT_GATE")"
[[ -z "$malformed_advisory_output" ]]
[[ -z "$malformed_gate_output" ]]

echo "hook tests passed"

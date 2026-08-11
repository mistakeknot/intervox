#!/usr/bin/env bash
# PreToolUse gate for commits touching declared voice-carrying files.

set -euo pipefail
trap 'exit 0' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
VOICEPATHS="$PLUGIN_ROOT/engine/voicepaths.py"
VOICE_CHECK="$PLUGIN_ROOT/scripts/voice-check.sh"

payload="$(cat)"
command_text="$(printf '%s' "$payload" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
print(data.get("tool_input", {}).get("command", ""))
' 2>/dev/null)"

[[ -n "$command_text" ]] || exit 0
if [[ "$command_text" =~ (^|[[:space:]])VOICEGATE=skip([[:space:]]|$) ]]; then
  exit 0
fi

is_commit="$(python3 -c '
import re
import sys

command = sys.argv[1]
pattern = r"(?:^|[;&|]\s*)(?:[A-Za-z_][A-Za-z0-9_]*=\S+\s+)*(?:command\s+)?git\s+commit(?:\s|$)"
print("yes" if re.search(pattern, command) else "no")
' "$command_text")"
[[ "$is_commit" == "yes" ]] || exit 0

cwd="$(printf '%s' "$payload" | python3 -c '
import json
import os
import sys

data = json.load(sys.stdin)
print(data.get("cwd") or os.getcwd())
' 2>/dev/null)"
root="$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null)" || exit 0

staged=()
while IFS= read -r staged_path; do
  [[ -n "$staged_path" ]] && staged+=("$root/$staged_path")
done < <(git -C "$root" diff --cached --name-only --diff-filter=ACMR)
[[ ${#staged[@]} -gt 0 ]] || exit 0

matched_output="$(python3 "$VOICEPATHS" match "$root" "${staged[@]}" 2>/dev/null)" || exit 0
matched=()
while IFS= read -r matched_path; do
  [[ -n "$matched_path" ]] && matched+=("$matched_path")
done <<<"$matched_output"
[[ ${#matched[@]} -gt 0 ]] || exit 0

# --require-match because this hook already matched the staged files against
# .voicepaths: if voice-check now resolves zero of them, the two match passes
# disagree (root mismatch, mangled list) and the prose was NOT checked — that
# must block loudly, never read as a clean pass (exit 3, distinct from the
# style verdict's 2).
if report="$("$VOICE_CHECK" --gate --require-match --root "$root" "${matched[@]}" 2>&1)"; then
  status=0
else
  status=$?
fi

if [[ $status -eq 3 ]]; then
  printf '%s' "$report" | python3 -c '
import json
import sys

report = sys.stdin.read()
reason = (
    "HOUSE-STYLE GATE INTERNAL ERROR: the gate matched staged voice files "
    "but voice-check resolved none of them — the prose was NOT checked.\n"
    + report
    + "\nThis is an invocation bug, not a style verdict. Fix the gate "
      "wiring, or use VOICEGATE=skip for a documented exception."
)
print(json.dumps({"decision": "block", "reason": reason}))
'
  exit 0
fi

[[ $status -eq 2 ]] || exit 0

printf '%s' "$report" | python3 -c '
import json
import sys

report = sys.stdin.read()
reason = (
    "HOUSE-STYLE GATE: "
    + report
    + "\nFix the flagged copy, or re-run with VOICEGATE=skip prefixed "
      "to the commit for a documented exception."
)
print(json.dumps({"decision": "block", "reason": reason}))
'

exit 0

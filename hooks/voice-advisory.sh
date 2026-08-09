#!/usr/bin/env bash
# PostToolUse advisory for edits to declared voice-carrying files.

set -euo pipefail
trap 'exit 0' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
VOICEPATHS="$PLUGIN_ROOT/engine/voicepaths.py"
VOICE_CHECK="$PLUGIN_ROOT/scripts/voice-check.sh"

payload="$(cat)"
file_path="$(printf '%s' "$payload" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
print(data.get("tool_input", {}).get("file_path", ""))
' 2>/dev/null)"

[[ -n "$file_path" ]] || exit 0
file_dir="$(dirname "$file_path")"
root="$(git -C "$file_dir" rev-parse --show-toplevel 2>/dev/null)" || exit 0

python3 "$VOICEPATHS" match "$root" "$file_path" >/dev/null 2>&1 || exit 0

set +e
report="$("$VOICE_CHECK" --root "$root" "$file_path" 2>&1)"
set -e
[[ -n "$report" ]] || exit 0
if ! printf '%s\n' "$report" | grep -Eiq \
  ':[0-9]+:[0-9]+:(suggestion|warning|error):|[[:space:]](warn|fail)[[:space:]]*$'; then
  exit 0
fi

printf '%s' "$report" | python3 -c '
import json
import sys

report = sys.stdin.read()
reason = (
    "voice-check advisory (non-blocking):\n"
    + report
    + "\nFix now or before commit — the commit gate enforces."
)
print(json.dumps({"decision": "block", "reason": reason}))
'

exit 0

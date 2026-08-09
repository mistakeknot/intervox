#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESOLVER="$ROOT/scripts/resolve-register.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

PROFILE="$TMP_DIR/voice-profile.md"
cat >"$PROFILE" <<'EOF'
# Voice Profile

## Foundation

Foundation rules.

## Register 1: Team

Team rules.

## Register 2: Internal

Internal rules.

## Register 3: External

External rules.

## Register 4: Open Source

Open source rules.
EOF

resolve() {
  INTERVOX_PROFILE="$PROFILE" bash "$RESOLVER" "$@"
}

direct_output="$(resolve gsv-site)"
[[ "$direct_output" == *'<!-- register: gsv-site (prose delta: External; canon: gsvdotcom docs/canon/copy-voice.md) -->'* ]]
[[ "$direct_output" == *'## Foundation'* ]]
[[ "$direct_output" == *'## Register 3: External'* ]]

for alias in GSV site 'gsv site'; do
  alias_output="$(resolve "$alias")"
  [[ "$alias_output" == "$direct_output" ]]
done

REPO="$TMP_DIR/repo"
mkdir -p "$REPO/.git" "$REPO/docs"
printf '%s\n' 'register: gsv-site' '*.md' >"$REPO/.voicepaths"
touch "$REPO/docs/spec.md"

inferred_output="$(resolve --infer "$REPO/docs/spec.md" 2>"$TMP_DIR/infer.err")"
[[ "$inferred_output" == "$direct_output" ]]
grep -q "inferred register 'gsv-site'" "$TMP_DIR/infer.err"

set +e
resolve definitely-unknown >"$TMP_DIR/unknown.out" 2>"$TMP_DIR/unknown.err"
unknown_status=$?
set -e
[[ $unknown_status -eq 3 ]]
grep -q "unknown register 'definitely-unknown'" "$TMP_DIR/unknown.err"

echo "test_resolve_register: all tests passed"

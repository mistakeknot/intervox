#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
VOICE_CHECK="$ROOT_DIR/scripts/voice-check.sh"
ENGINE="$ROOT_DIR/engine/intervox"
FIXTURES="$ROOT_DIR/tests/fixtures"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

REPO="$TMP_DIR/repo"
CONFIG="$TMP_DIR/config"
mkdir -p "$REPO" "$CONFIG/intervox/fingerprints"
printf '%s\n' '*.md' >"$REPO/.voicepaths"
cp "$FIXTURES/clean-draft.md" "$REPO/clean.md"
cp "$FIXTURES/sloppy-draft.md" "$REPO/sloppy.md"
printf '%s\n' 'not voice-carrying' >"$REPO/notes.txt"

python3 "$ENGINE" fingerprint \
  --corpus "$FIXTURES/corpus" \
  --out "$CONFIG/intervox/fingerprints/all.json" >/dev/null

set +e
sloppy_output="$(XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$REPO" "$REPO/sloppy.md" 2>&1)"
sloppy_status=$?
set -e
[[ $sloppy_status -eq 2 ]]
[[ "$sloppy_output" == *'"verdict": "reject"'* ]]

XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$REPO" clean.md >/dev/null

undeclared_output="$(XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$REPO" "$REPO/notes.txt")"
[[ "$undeclared_output" == 'voice-check: no declared voice files touched' ]]

NO_DECLARATION_REPO="$TMP_DIR/no-declaration"
mkdir -p "$NO_DECLARATION_REPO"
cp "$FIXTURES/clean-draft.md" "$NO_DECLARATION_REPO/clean.md"
no_declaration_output="$(XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$NO_DECLARATION_REPO" "$NO_DECLARATION_REPO/clean.md")"
[[ "$no_declaration_output" == 'voice-check: no declared voice files touched' ]]

skip_output="$(VOICEGATE=skip XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$REPO" "$REPO/sloppy.md")"
[[ "$skip_output" == 'voice-check: gate skipped by VOICEGATE=skip' ]]

XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --root "$REPO" "$REPO/sloppy.md" >/dev/null

printf '%s\n' 'register: fixture' '*.md' >"$REPO/.voicepaths"
mv "$CONFIG/intervox/fingerprints/all.json" "$CONFIG/intervox/fingerprints/fixture.json"
XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$REPO" "$REPO/clean.md" >/dev/null
mv "$CONFIG/intervox/fingerprints/fixture.json" "$CONFIG/intervox/fingerprints/all.json"
printf '%s\n' '*.md' >"$REPO/.voicepaths"

mkdir -p "$TMP_DIR/bin"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'printf '\''%s\n'\'' "$1:1:1:error:Artificial Vale failure:GSV.Test"' \
  'exit 1' >"$TMP_DIR/bin/vale"
chmod +x "$TMP_DIR/bin/vale"
printf '%s\n' 'StylesPath = vale/styles' >"$REPO/.vale.ini"

set +e
vale_output="$(PATH="$TMP_DIR/bin:$PATH" XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$REPO" "$REPO/clean.md" 2>&1)"
vale_status=$?
set -e
[[ $vale_status -eq 2 ]]
[[ "$vale_output" == *'Artificial Vale failure'* ]]

echo "voice-check tests passed"

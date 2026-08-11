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
rm -f "$REPO/.vale.ini"

# rules-only paths get Vale but never the stylometric layer: a sloppy draft
# declared rules-only must pass the gate with no "intervox verify" line.
LAYERED_REPO="$TMP_DIR/layered"
mkdir -p "$LAYERED_REPO/docs"
cp "$FIXTURES/sloppy-draft.md" "$LAYERED_REPO/docs/guide.md"
cp "$FIXTURES/clean-draft.md" "$LAYERED_REPO/copy.md"
printf '%s\n' '*.md' 'rules-only: docs/*.md' >"$LAYERED_REPO/.voicepaths"
rules_only_output="$(XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$LAYERED_REPO" "$LAYERED_REPO/docs/guide.md")"
[[ "$rules_only_output" != *'intervox verify'* ]]

# ...while a full-layer file in the same repo still gets verified.
full_layer_output="$(XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$LAYERED_REPO" "$LAYERED_REPO/copy.md")"
[[ "$full_layer_output" == *'intervox verify'* ]]

# "gate: strict" makes verify exit 1 (revise) block; the default gate lets
# it pass. A stub engine pins the exit code so the scenario is deterministic
# across engine recalibrations.
STRICT_REPO="$TMP_DIR/strict"
mkdir -p "$STRICT_REPO" "$TMP_DIR/stub"
cp "$FIXTURES/clean-draft.md" "$STRICT_REPO/copy.md"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'printf '\''%s\n'\'' '\''{"verdict": "revise", "score": 70}'\''' \
  'exit 1' >"$TMP_DIR/stub/intervox"
chmod +x "$TMP_DIR/stub/intervox"

printf '%s\n' '*.md' >"$STRICT_REPO/.voicepaths"
set +e
default_revise_output="$(INTERVOX_ENGINE="$TMP_DIR/stub/intervox" XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$STRICT_REPO" "$STRICT_REPO/copy.md" 2>&1)"
default_revise_status=$?
set -e
[[ $default_revise_status -eq 0 ]]
[[ "$default_revise_output" == *'"verdict": "revise"'* ]]

printf '%s\n' 'gate: strict' '*.md' >"$STRICT_REPO/.voicepaths"
set +e
strict_revise_output="$(INTERVOX_ENGINE="$TMP_DIR/stub/intervox" XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$STRICT_REPO" "$STRICT_REPO/copy.md" 2>&1)"
strict_revise_status=$?
set -e
[[ $strict_revise_status -eq 2 ]]
[[ "$strict_revise_output" == *'revise blocks under gate: strict'* ]]

# Non-markdown files never reach the stylometric layer even at full layer.
ASTRO_REPO="$TMP_DIR/astro"
mkdir -p "$ASTRO_REPO"
cp "$FIXTURES/sloppy-draft.md" "$ASTRO_REPO/page.astro"
printf '%s\n' '*.astro' >"$ASTRO_REPO/.voicepaths"
astro_output="$(XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$ASTRO_REPO" "$ASTRO_REPO/page.astro")"
[[ "$astro_output" != *'intervox verify'* ]]

# ── regression: the zsh unquoted-$var incident ──────────────────────────────
# zsh does not word-split an unquoted $var, so `voice-check --gate $changed`
# passed the whole newline-joined `git diff --name-only` output as ONE
# argument. It matched nothing and the gate exited 0 — a false green over a
# sloppy draft. A newline inside a file argument must now fail loudly (exit
# 3), flag or no flag.
joined_list="$REPO/sloppy.md"$'\n'"$REPO/clean.md"
set +e
joined_output="$(XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --root "$REPO" "$joined_list" 2>&1)"
joined_status=$?
set -e
[[ $joined_status -eq 3 ]]
[[ "$joined_output" == *'INVOCATION ERROR'* ]]

# --require-match: explicit args resolving to zero declared voice files is an
# invocation failure (exit 3), not a clean pass...
set +e
require_miss_output="$(XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --require-match --root "$REPO" "$REPO/notes.txt" 2>&1)"
require_miss_status=$?
set -e
[[ $require_miss_status -eq 3 ]]
[[ "$require_miss_output" == *'REQUIRE-MATCH FAILED'* ]]

# ...while a matching file still passes clean under the flag...
XDG_CONFIG_HOME="$CONFIG" "$VOICE_CHECK" --gate --require-match --root "$REPO" "$REPO/clean.md" >/dev/null

# ...and WITHOUT the flag, undeclared files keep the legacy clean-pass exit 0
# (already asserted above) so non-gate callers are unaffected.

echo "voice-check tests passed"

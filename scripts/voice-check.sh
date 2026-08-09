#!/usr/bin/env bash
# voice-check.sh — run declared prose through Vale and intervox.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
VOICEPATHS="$PROJECT_ROOT/engine/voicepaths.py"
ENGINE="$PROJECT_ROOT/engine/intervox"

usage() {
  echo "usage: voice-check.sh [--gate] [--root <repo-root>] <file>..." >&2
}

gate=0
root=""
files=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gate)
      gate=1
      shift
      ;;
    --root)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      root="$2"
      shift 2
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        files+=("$1")
        shift
      done
      ;;
    -*)
      usage
      exit 2
      ;;
    *)
      files+=("$1")
      shift
      ;;
  esac
done

if [[ $gate -eq 1 && "${VOICEGATE:-}" == "skip" ]]; then
  echo "voice-check: gate skipped by VOICEGATE=skip"
  exit 0
fi

[[ ${#files[@]} -gt 0 ]] || { usage; exit 2; }

if [[ -z "$root" ]]; then
  root="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
fi
root="$(cd "$root" && pwd -P)"

paths=()
for file in "${files[@]}"; do
  if [[ "$file" == /* ]]; then
    paths+=("$file")
  else
    paths+=("$root/$file")
  fi
done

set +e
matched_output="$(python3 "$VOICEPATHS" match "$root" "${paths[@]}")"
match_status=$?
set -e
if [[ $match_status -ne 0 ]]; then
  echo "voice-check: no declared voice files touched"
  exit 0
fi

matched=()
while IFS= read -r file; do
  [[ -n "$file" ]] && matched+=("$file")
done <<<"$matched_output"

# The stylometric layer only makes sense on markdown prose declared at the
# full layer: "rules-only:" globs (governance docs, page templates, READMEs)
# and non-markdown files (.astro and friends are source code to a
# stylometer) get Vale only.
set +e
verify_output="$(python3 "$VOICEPATHS" match --layer=full "$root" "${paths[@]}")"
set -e
verify_matched=()
while IFS= read -r file; do
  [[ -n "$file" ]] || continue
  case "$file" in
    *.md|*.mdx) verify_matched+=("$file") ;;
  esac
done <<<"$verify_output"

failed=0

if command -v vale >/dev/null 2>&1; then
  if [[ -f "$root/.vale.ini" ]]; then
    set +e
    vale_output="$(cd "$root" && vale --output=line "${matched[@]}" 2>&1)"
    vale_status=$?
    set -e
    if [[ -n "$vale_output" ]]; then
      echo "voice-check: Vale rules"
      printf '%s\n' "$vale_output"
    fi
    # Vale exits 1 when error-level alerts fire (the line output carries no
    # severity field, so the exit code is the only reliable signal). Exit
    # codes >=2 are Vale runtime errors — surface them but degrade politely
    # rather than blocking, same posture as vale-not-installed.
    if [[ $vale_status -eq 1 ]]; then
      failed=1
    elif [[ $vale_status -ge 2 ]]; then
      echo "voice-check: vale runtime error (exit $vale_status) — rules layer skipped"
    fi
  fi
else
  echo "voice-check: vale not installed — rules layer skipped (brew install vale)"
fi

register="$(PYTHONPATH="$PROJECT_ROOT/engine" python3 -c \
  'import sys; from voicepaths import load; print(load(sys.argv[1])["register"] or "all")' \
  "$root")"
# "gate: strict" in .voicepaths makes verify exit 1 (revise) block too, not
# just exit 2 (reject). Repos opt in once their register baseline is real
# enough that "measurably flatter than the house voice" deserves to block.
gate_mode="$(PYTHONPATH="$PROJECT_ROOT/engine" python3 -c \
  'import sys; from voicepaths import load; print(load(sys.argv[1])["gate"] or "default")' \
  "$root")"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
baseline="$config_home/intervox/fingerprints/$register.json"

for file in ${verify_matched[@]+"${verify_matched[@]}"}; do
  if [[ $gate -eq 1 ]]; then
    echo "voice-check: intervox verify — $file"
    set +e
    intervox_output="$("$ENGINE" verify --draft "$file" --baseline "$baseline" 2>&1)"
    intervox_status=$?
    set -e
    [[ -n "$intervox_output" ]] && printf '%s\n' "$intervox_output"
    if [[ $intervox_status -eq 2 ]]; then
      failed=1
    fi
  else
    echo "voice-check: intervox lint — $file"
    set +e
    intervox_output="$("$ENGINE" lint --draft "$file" --baseline "$baseline" --format table 2>&1)"
    set -e
    [[ -n "$intervox_output" ]] && printf '%s\n' "$intervox_output"
  fi
done

if [[ $gate -eq 1 && $failed -eq 1 ]]; then
  exit 2
fi
exit 0

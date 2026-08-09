#!/usr/bin/env bash
# resolve-register.sh — extract the working voice profile for a given register.
#
# Reads the global multi-register profile and prints:
#   the "## Foundation" section (always, the base)
# followed by the selected "## Register N: <Name>" section (the delta).
#
# Usage:
#   resolve-register.sh <register>            # explicit register by name or number
#   resolve-register.sh --infer <path>        # infer register from a target path
#   resolve-register.sh --list                # list available register sections
#
# <register> accepts: "open source", "oss", "4", "register 4", "internal", "team",
#                     "external", "gsv-site", "gsv", "site" (case-insensitive,
#                     space/hyphen tolerant).
#
# Profile location (first match wins):
#   $INTERVOX_PROFILE
#   ${XDG_CONFIG_HOME:-$HOME/.config}/intervox/voice-profile.md
#   ${XDG_CONFIG_HOME:-$HOME/.config}/intervoice/voice-profile.md   (legacy fallback)
#
# Exit codes: 0 ok; 2 profile not found; 3 register not found.

set -euo pipefail

profile_path() {
  if [[ -n "${INTERVOX_PROFILE:-}" ]]; then
    printf '%s\n' "$INTERVOX_PROFILE"; return
  fi
  local xdg="${XDG_CONFIG_HOME:-$HOME/.config}"
  if [[ -f "$xdg/intervox/voice-profile.md" ]]; then
    printf '%s\n' "$xdg/intervox/voice-profile.md"; return
  fi
  if [[ -f "$xdg/intervoice/voice-profile.md" ]]; then
    echo "intervox: using legacy intervoice profile path; run /intervox migrate to move it" >&2
    printf '%s\n' "$xdg/intervoice/voice-profile.md"; return
  fi
  printf '%s\n' "$xdg/intervox/voice-profile.md"
}

PROFILE="$(profile_path)"
if [[ ! -f "$PROFILE" ]]; then
  echo "intervox: profile not found at $PROFILE" >&2
  echo "Symlink it from your dotfiles, e.g.:" >&2
  echo "  mkdir -p \"\${XDG_CONFIG_HOME:-\$HOME/.config}/intervox\"" >&2
  echo "  ln -s ~/projects/dotfiles/projects/voice-profile.md \\" >&2
  echo "        \"\${XDG_CONFIG_HOME:-\$HOME/.config}/intervox/voice-profile.md\"" >&2
  exit 2
fi

# Print one "## " section by exact heading text (everything from the heading
# line until the next "## " at column 0, or EOF).
print_section() {
  local want="$1"
  awk -v want="$want" '
    /^## / {
      h = $0; sub(/^## /, "", h); gsub(/[ \t]+$/, "", h)
      printing = (h == want)
    }
    printing { print }
  ' "$PROFILE"
}

list_registers() {
  grep -nE '^## (Foundation|Register )' "$PROFILE" | sed 's/^/  /'
}

normalize_register_token() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -d ' -'
}

is_gsv_site_register() {
  local token; token="$(normalize_register_token "$1")"
  [[ "$token" == "gsvsite" || "$token" == "gsv" || "$token" == "site" ]]
}

canonical_register_heading() {
  local token; token="$(normalize_register_token "$1")"
  local want_num=""
  case "$token" in
    *team*|*register1*|1)        want_num=1 ;;
    *internal*|*register2*|2)    want_num=2 ;;
    *external*|*register3*|3)    want_num=3 ;;
    gsvsite|gsv|site)             want_num=3 ;;
    *opensource*|*oss*|*register4*|4) want_num=4 ;;
    *) want_num="" ;;
  esac
  if [[ -z "$want_num" ]]; then return 3; fi
  grep -E "^## Register ${want_num}:" "$PROFILE" | head -1 | sed 's/^## //; s/[ \t]*$//'
}

voicepaths_register() {
  local dir parent register
  if [[ -d "$1" ]]; then
    dir="$1"
  else
    dir="$(dirname "$1")"
  fi
  while [[ ! -d "$dir" ]]; do
    parent="$(dirname "$dir")"
    [[ "$parent" != "$dir" ]] || return 1
    dir="$parent"
  done
  dir="$(cd "$dir" && pwd -P)"

  while :; do
    if [[ -e "$dir/.git" ]]; then
      [[ -f "$dir/.voicepaths" ]] || return 1
      register="$(awk '
        /^[[:space:]]*#/ { next }
        tolower($0) ~ /^[[:space:]]*register[[:space:]]*:/ {
          line = $0
          sub(/^[[:space:]]*[^:]+:[[:space:]]*/, "", line)
          sub(/[[:space:]]*#.*/, "", line)
          sub(/[[:space:]]+$/, "", line)
          if (length(line)) { print line; exit }
        }
      ' "$dir/.voicepaths")"
      [[ -n "$register" ]] || return 1
      printf '%s\n' "$register"
      return 0
    fi
    parent="$(dirname "$dir")"
    [[ "$parent" != "$dir" ]] || return 1
    dir="$parent"
  done
}

infer_register() {
  local declared
  if declared="$(voicepaths_register "$1")"; then
    printf '%s\n' "$declared"
    return
  fi
  local p; p="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  local base; base="$(basename "$p")"
  case "$base" in
    readme.md|contributing.md|changelog.md|concepts.md) echo "open source"; return ;;
  esac
  case "$p" in
    */docs/adr/*|*adr-*|*-adr.md)            echo "open source"; return ;;
    */docs/prd*|*prd.md|*spec.md|*-spec.md)  echo "internal"; return ;;
    */docs/strategy/*|*strategy*|*memo*)     echo "internal"; return ;;
    */docs/brainstorms/*|*notes.md)          echo "team"; return ;;
  esac
  echo "open source"
}

main() {
  case "${1:-}" in
    --list) list_registers; exit 0 ;;
    --infer)
      [[ $# -ge 2 ]] || { echo "intervox: --infer needs a path" >&2; exit 3; }
      reg="$(infer_register "$2")"
      echo "intervox: inferred register '$reg' from $2" >&2
      ;;
    "" ) echo "intervox: give a register name/number, or --infer <path>, or --list" >&2; exit 3 ;;
    *) reg="$*" ;;
  esac

  heading="$(canonical_register_heading "$reg")" || {
    echo "intervox: unknown register '$reg'. Available:" >&2
    list_registers >&2
    exit 3
  }
  if [[ -z "$heading" ]]; then
    echo "intervox: register '$reg' not present in profile. Available:" >&2
    list_registers >&2
    exit 3
  fi

  foundation_heading="$(grep -E '^## Foundation' "$PROFILE" | head -1 | sed 's/^## //; s/[ \t]*$//')"
  if [[ -z "$foundation_heading" ]]; then
    echo "intervox: profile has no '## Foundation' section; base rules missing" >&2
    exit 3
  fi
  print_section "$foundation_heading"
  echo
  if is_gsv_site_register "$reg"; then
    echo '<!-- register: gsv-site (prose delta: External; canon: gsvdotcom docs/canon/copy-voice.md) -->'
  fi
  print_section "$heading"
}

main "$@"

## Acceptance Criteria

1. Register resolution works end-to-end, including the new register.
   ```check
   bash ~/projects/Sylveste/interverse/intervox/scripts/resolve-register.sh gsv-site >/dev/null
   ```
2. Full intervox test suite green (existing 52 + voicepaths + voice-check + hooks + resolve-register tests).
   ```check
   cd ~/projects/Sylveste/interverse/intervox && python3 -m pytest -q && bash tests/test_resolve_register.sh && bash tests/test_voice_check.sh && bash tests/test_hooks.sh
   ```
3. The gate blocks LLMese and passes clean copy: sloppy fixture exits 2 under `--gate`, clean fixture exits 0 (asserted inside test_voice_check.sh, run above).
4. Undeclared files are untouched: a commit-gate invocation whose staged files match no `.voicepaths` glob exits 0 silently (asserted inside test_hooks.sh).
5. Canon consolidated with mk's ruling recorded.
   ```check
   grep -q "Ruling (mk, 2026-08" ~/projects/gsvdotcom/docs/canon/copy-voice.md && [ "$(wc -l < ~/projects/gsvdotcom/COPY_GUIDE.md)" -le 5 ] && [ "$(wc -l < ~/projects/gsvdotcom/VOICE.md)" -le 5 ]
   ```
6. Both adopter repos declare paths and wire the gate for non-Claude agents.
   ```check
   test -s ~/projects/gsvdotcom/.voicepaths && grep -q voice-check ~/projects/gsvdotcom/AGENTS.md && test -s ~/projects/jawnomicon/.voicepaths && grep -q voice-check ~/projects/jawnomicon/AGENTS.md && grep -q voicepaths ~/.codex/AGENTS.md
   ```
7. Canonical Vale style lives in gsvdotcom (4 rules + .vale.ini); interbrowse copy marked vendored.
   ```check
   [ "$(ls ~/projects/gsvdotcom/vale/styles/GSV/*.yml | wc -l)" -eq 4 ] && test -s ~/projects/gsvdotcom/.vale.ini && grep -ql "vendored" ~/projects/Sylveste/interverse/interbrowse/vale/styles/GSV/Buzzwords.yml
   ```
8. gsv-site corpus contains no synthetic samples; fingerprint regenerated; word count recorded (rules-heavy mode documented if under floor).
   ```check
   [ "$(ls /Users/sma/.config/intervox/corpus/gsv-site/ | grep -c 'sample-2026071')" -eq 0 ]
   ```
9. intervox 0.3.0 published: repo clean vs origin, plugin.json/marketplace.json versions agree at 0.3.0 (task-13 verify commands).
10. All repo work committed via `git commit -F <file> -- <paths>` and pushed; no repo left dirty. Stop after 2 failed attempts at any gate and escalate rather than looping (two-strikes rule).

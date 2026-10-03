# feature-breaker gotchas

Each item is a real failure and its source. R = a public Reddit post by u/RUSuper on an AI-built fishing game. The other short tags (01 to 05, W, rule numbers) point to an unpublished research catalogue on AI game-dev workflows. They stay as labels only.

## Seeded from the spec (30 Sep 2026)

1. **Green tests hid real bugs (R, 05).** A builder shipped features with green tests and bugs that a player found in 1 minute. The breaker runs after every build, also when the tests are green.
2. **A test that never failed proves nothing (R, 04, 05).** A test that passes on the base commit does not test the change. Read `test-before.log` for each ticket test.
3. **A coder that writes its own gate writes a gate that it passes (05, single source; rule 34).** A separate agent writes the test and the class guard.
4. **A breaker in the same context as the coder has the same blind spots (W22).** The breaker gets only the done-when, the diff and the test logs. It never sees the builder's report.
5. **Fix loops go bad after 2 to 3 tries (01, 04; W23, rule 31).** The chat fills with failed ideas and the next patch repeats them. After 2 failed tries, roll back to the last green commit and ask the user: change the approach, or cut the scope.
6. **"Be more careful" is not a fix (W2 step 4).** After a Must, write the 5 whys and add a guard for the whole bug class. The guard must fail on the old code.
7. **Hard-coded tuning numbers blocked balance work (01, 02).** Numbers in code cannot be tuned from the editor or by a playtest sweep. Move each new literal to `data/balance/<system>.json`.
8. **Two Macs died with too many engine instances (R; 03; W18).** The cap is `max_godot_instances` (6), measured on a 32 GB Mac: a headless game uses about 1 to 1.5 GB and a windowed game 2 to 3.5 GB. An older cap of 2 came from anecdotes, not from a measurement. The user's own game and the editor agent count. An out-of-memory kill can look like a test failure. Measure your own machine and set the cap.
9. **A prototype had no GDScript unit-test framework.** Tests ran through `bash tests/smoke.sh` and the Python bridge clients in `tests/`. A class guard is a bridge client, a headless `--script` run, or a grep gate in `smoke.sh`.

## Found while the skill was built (30 Sep 2026)

10. **The builder's claims leak through a quote.** A reply can repeat the claim in a "the report says X, but" line. That puts the claim in front of the breaker and fails a blind-brief eval. Never quote or sum up `build-report.md`.
11. **0 / 0 is NaN in GDScript, not an error.** A float divide by zero gives inf or NaN with no crash, so smoke passes. A divide by a difference is 0 / 0 when the 2 values are equal. Check every divide by a difference at the edge values. C# floats act the same way.
12. **The HUD had its own stamina.** In a survival RPG prototype, `scripts/hud.gd` `_tick_stamina` drained and refilled a display value. A stamina build that added a second copy in `player.gd` gave 2 values that could differ. Check for an existing owner of a value before a build adds one.
13. **The eval sandbox can block Write, Edit, Bash and Agent.** Print every file under `=== <path> ===` so the graders see it. A blind-brief case needs the Agent tool open; if the sandbox blocks it, park that case. A `max: 0` grader passes by default when its tool is blocked.
14. **Each eval case prompt sets `allowed_tools`.** Only Read, Glob, Grep and Skill are open by default. A case that needs Write, Edit, Agent or a `Bash(...)` pattern names it in `allowed_tools`, and the run also needs `--allow-tools`.
15. **Editor-owned files look like tuning data.** `data/placements.json` and `data/hud_layout.json` are in `data/`, but the in-game editor owns them. Tuning goes only in `data/balance/`.
16. **The eval skips `fixture.sh` by default.** `claude plugin eval` runs a scaffold script only with `--scaffold`. Without it, `evals/fixtures/` in the run folder is empty and every case fails on a missing file. Run `claude plugin eval . --scaffold` from the skill folder.
17. **A full eval run is expensive.** One case with the with/without ablation was 6 `claude` runs. The default is 3 runs for each case, so 10 cases give 60 runs. Run 1 case first: `--case <name> --runs 1`.

## Crush Depth build (30 Sep 2026)

Source: a build session of the example game Crush Depth (a submarine game) and the user's play-test notes.

18. **Bridge tests passed while play was broken.** Every test in 2 build rounds drove the game with teleports and direct calls. Nothing pressed a key or moved the mouse. In play, turning did not work, the sub spun out of control, and almost nothing else worked. A playable line counts only with a real-input test (step 2), and the live pass uses real input (step 6).
19. **A heading wrap made the sub spin.** Godot keeps a heading between -180 and +180 degrees. The turn code subtracted 2 headings, so past 180 degrees the difference jumped by a full turn. The sub then turned about 120 degrees a second with no input. Class guard: every angle difference goes through a wrap function, and a test turns past 180 degrees and checks that the heading settles.
20. **The mouse took no control until a click reached the view.** A HUD panel caught the click, so the mouse did nothing. Only a real-input test finds this. Test the first mouse move after the game starts.
21. **Forward thrust followed the camera pitch.** W made the sub dive. Forward keeps the depth. Depth has its own controls. Test W with the camera pitched down.
22. **The cockpit mouse look moved a free head inside the hull.** The user saw through the floor. In a vehicle cockpit, mouse look turns and pitches the vehicle, and the camera stays fixed to the cockpit.
23. **Merged features were not in the level.** The creatures merged but never spawned, so the user saw nothing new. Before a live pass, check that each object of the feature is in the scene.
24. **The cockpit lamp slid on a dive.** In the cockpit view, the light moved inside the cockpit on a dive or a rise. The camera did not ride the hull. The camera is a child of the hull, so the cockpit and its lamp stay still on screen. Test: dive and rise in the cockpit view, then read the screen position of the lamp.
25. **Dials and levers did not move.** The cockpit dials showed fixed values, and the levers took no click. Each dial and lever follows game state (depth, oxygen, hull, cargo, thrust). It takes a click when the mouse is free. Test: change the state and read the needle angle. Then click a lever with a real mouse event.
26. **The cabin lantern did not follow the lamp.** It stayed white when the lamp was on or off. Test: switch the lamp on and off, then read the glow of the lantern glass.

## Can be missing in your repo

The skill says what to do when each one is missing. Do not build them from this skill.

- **Test-log capture.** If no script writes `test-before.log` and `test-after.log`, the skill makes them by hand (step 2), or stops at step 2 when the engine cannot run.
- **A loader for `data/balance/*.json`.** If no game code reads the folder, the skill writes proposals and a ticket for the code change.
- **The editor knob panel (W6).** If the in-game editor has no panel for balance values, the knob hand-off points at nothing yet.
- **The shared slot file.** `work/manager/godot-slots.tsv` can be absent. Its format is in `references/formats.md`; `pgrep` stays the truth.
- **A bridge field for a value.** If `get_state` has no field for a number (for example `player.stamina`), the live pass (step 6) cannot measure it. It writes `Not measured`.
- **Sibling skills.** look-critic, playtest-bot, big-feature and game-manager may not exist in `.claude/skills/`. Say so in 1 line; never invent their output.

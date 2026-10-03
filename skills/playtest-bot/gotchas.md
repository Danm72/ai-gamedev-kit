# playtest-bot gotchas

Each item is a real failure. The source is in brackets: a public dev report, a spec review, or the first two games the skill ran on (a survival RPG proof of concept, called "the POC" below, and Crush Depth).

## Game state

1. **The game had no hunger, day clock or items.** Check `get_state` before you plan a balance run. [POC `get_state` handler]
2. **Hard-coded seeds give 1 world.** The POC terrain script hard-coded seeds 7 and 21, the world script seed 3, and the boar script called `randomize()`. "Fresh seeds" gave the same world until a `--seed` arg reached every RNG. The boars then differed in each run, with no way to repeat them. [POC code]
3. **A per-run `--seed` must not change the map layout.** If it does, map and balance change together. Keep the terrain and layout seeds fixed, and tag them as map seeds. A world RNG that also drives runtime timers and animation offsets must split into a layout RNG and a runtime RNG. [Spec review]
4. **The global RNG ignores `--seed`.** A bare `randf()`, `randi()` or `randf_range()` uses the global RNG. It gives a different value in each run unless the code calls `seed(<n>)`. Grep for it with `randomize()`. [State leak made 10 of 11 shots differ]

## Harness

5. **Godot hung at 0% CPU on a macOS error dialog.** Wrap every call in `timeout`. Exit 124 is a harness fail. [godogen report]
6. **Exit 137 is any SIGKILL, `timeout -k` included.** Read `elapsed_s` before you call it a memory kill. [A memory kill that looked like a test fail]
7. **`timeout` is GNU coreutils.** Stock macOS has no `timeout`; Homebrew puts it at `/opt/homebrew/bin/timeout`. Check `command -v timeout` first.
8. **A test run wrote into a shared profile, 1,330 files.** Pass `--data-dir <tmp>` to every run. [Public dev report]
9. **Two runs on 1 bridge port collide, and the user's live game holds the default port.** Give each run its own `--port` from `port_base`. [Spec review]
10. **Two dev machines died from too many game instances.** The user's live game and any other agent's game count against the cap. [Public dev reports]
11. **State leaked between runs, so 10 of 11 captures differed.** Use 1 fresh process per seed, queued.
12. **A shared `runs/` folder mixes old seeds into a new check.** Write to `runs/<check-id>/`. [Spec review]

## Bands

13. **A band that no data can fail passes silently.** Prove it red on a known-bad data file first. A field that is null in every run is "not measured", never a pass.
14. **"If a map fails its band, fix the map, not the test."** Never widen a band. [bariyu]
15. **1 bad seed is not a finding.** "A finding is filed only if it happens again on fresh seeds." [bariyu]
16. **A PROPOSED band is an agent guess.** Tune data only against a USER band. An agent never changes a USER line.
17. **`time_scale` above 1 can change physics and navigation results.** Prove equivalence on 2 seeds before you trust fast runs. [Spec review; no case yet]

## Agents

18. **Never SendMessage a Workflow lane agent id.** It spawns a duplicate. [POC handover]

## Crush Depth

Source: the Crush Depth build and the skill field test.

19. **A teleport policy passes for the wrong reason.** A dive script used `move_to`, so oxygen and hull drained over almost no travel time. A band on oxygen or hull needs a policy that steers with real input. [field test]
20. **Bridge runs passed while the game was not playable.** Every bot run and test drove the sub with teleports. In the first hands-on play test, turning did not work and the sub spun out of control. A playable band counts only from real-input runs. [Crush Depth]
21. **Seeds that reach only cosmetic values cannot confirm a finding.** Vary the policy per seed, or add seeded spawn jitter first. [field test]
22. **Windowed bot runs took the user's focus.** Godot 4.7 makes itself the front app at start. A re-signed "GodotBG" copy put Gatekeeper dialogs on the user's screen. The fix is `tools/godot_bg.sh` (in this kit) on the stock app. A first version blocked focus for good, so the user could not click the game window at all. [Crush Depth]

## Jev labels

23. **Jev compares numbers badly, so every comparison stays in code as a sentence.** Code compares each number to its limit and writes the result as a sentence, for example "The sub stayed ABOVE the rated depth of 150 m". Jev reads only that sentence and never compares raw numbers. [TypeSafe docs]

## Often missing in a new repo

Check for each part before the first run. Until it exists, print the plan and add a ticket. Start no run.

- `scripts/run_seeds.sh` with `--dry-run`.
- A `--seed` user arg that reaches every behaviour RNG (see items 2 to 4).
- The `get_state` fields that your bands need, for example `game_time_s` and a stuck timer per creature.
- A debug time lever (a `set_time_scale` bridge command).
- The slot file. The format is in `references/contract.md`. Another skill can define the same file; keep 1 format.
- `data/balance/`. In the POC, the game read no balance JSON at first; the boar values sat in the boar script.

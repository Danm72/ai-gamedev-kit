---
name: feature-breaker
description: "Use when a feature build on a Godot or Unity game is finished and the user wants it checked: \"run the breaker\", \"build's done on X, check it\", \"tests are green, are we done\", \"try to break the X feature\", \"fix the X Must\", \"try the X fix again\", \"run the tests on the X build\", \"breaker ran, ship it\". Checks that each new test failed first, moves tuning numbers to data, has a fresh agent try to break the feature, and caps the fix loop. Not for a general code review or a plain bug fix (\"the boar gets stuck, fix it\"), and not for balance bands (playtest-bot)."
---

# feature-breaker

This skill stops a "done" on a build whose tests are green but whose feature still has bugs. A fresh breaker that never saw the builder's report ranks the findings. Each Must gets a fix and a guard for the whole bug class. The fix loop stops after 2 tries.

`gotchas.md`, `config.json` (the values that change) and `references/formats.md` (the file formats) are in the folder of this skill. That is the base directory that the Skill tool gives, not the project folder. Read all 3 before step 1. A prompt that limits you to the project folder does not cover them.

## Assumes

Set the paths and commands in `config.json` to match your repo.

- `docs/features/<slug>/FEATURE.md`: the feature file that big-feature writes, with done-when lines, Tickets, a `Base commit:` line, `Failed fixes` and `Stage:`.
- `docs/features/<slug>/build.diff`: the full diff of the build branch against the base commit. The build session writes it (`git diff <base>...<branch>`).
- `docs/features/<slug>/test-before.log` and `test-after.log`: the new tests run on the base commit and on the build branch (format in `references/formats.md`). If they are missing, the skill makes them with `test_cmd`.
- `test_cmd` (default `bash tests/smoke.sh`): 1 command that starts 1 headless game, runs the tests and prints a `PASS` or `FAIL` line per test.
- A JSON bridge in the game (this kit's `bridge/`) at `bridge_addr`: `get_state` returns the live numbers that the done-when lines name. The live pass reads state only through it.
- A real-input path for tests: Godot `Input.parse_input_event`, or Unity Input System queued device events (for example a bridge `input` command). Teleports do not count.
- `balance_dir` (`data/balance/`): JSON tuning files. A loader in the game is optional; without one, the skill writes proposals and a code ticket.
- Godot only: `pgrep`, GNU `timeout` (`timeout_bin`; on macOS install coreutils) and the slot file `godot_slot_file` (this kit's `tools/godot_slot.sh` writes it). For Unity, use your own process cap in place of the Godot slot section.
- Claude Code `Agent` tool with a model for fresh subagents (`breaker_model`), and `AskUserQuestion`.
- Sibling skills from this kit (optional): look-critic, playtest-bot, game-manager.

## Rules that hold in every step

1. Print each file that you write, under a line `=== <path> ===`. If a write tool is blocked, print the full file anyway. The graders read the printed text, not the disk.
2. Never write the editor-owned files in `config.json` `editor_owned_files` by hand. `data/placements.json` and `data/hud_layout.json` change only through the editor's save commands (for example `editor_save` and `editor_hud_layout`). Tuning data goes in `balance_dir` (`data/balance/`).
3. Never quote, copy or sum up the builder's report (`build-report.md`) anywhere: not in the brief, not in `breaker.md`, not in the reply.
4. No time estimates. Sizes are S, M, L or XL. Game values ("4.5 s of sprint") are allowed.
5. Never invent a key binding. Every new UI action is a labelled button. Only standard editor shortcuts are allowed.
6. No outward posts. Every wait polls at `poll_max_s` (5 s) or less.
7. Never use Kenney, KayKit, Quaternius, Synty or any low-poly kit.
8. Commit by file name. Never `git add -A` or `git add .`.
9. Models: the strongest coding model builds the fixes and makes each decision. Fresh subagents (`breaker_model`) break, disprove and review. A model from another vendor may do computer use and give a second look. It never decides a rank, a drop or a fix.

## Godot slots

Do this check before any Godot start, a test run included (`test_cmd` starts Godot). For Unity, apply your own editor and player cap in the same way.

1. If the feature folder has `ps.txt`, read it in place of `pgrep`. Else run `pgrep -fl godot`.
2. Count the processes. The user's own game window and the in-game editor agent count.
3. If the count is `max_godot_instances` (6) or more, start nothing. Tell the user which lanes hold the slots and that the run waits in the queue. Poll every 5 s or less. Never stop the user's game or another lane's process.
4. If a slot is free, add a row to `godot_slot_file` (format in `references/formats.md`). Run all tests in 1 headless process.
5. Run each Godot call as `<timeout_bin> <godot_timeout_s> godot ...`. Check `command -v timeout` first. Stock macOS has no `timeout`. If it is missing, tell the user in 1 line and do not start Godot.
6. An out-of-memory kill looks like a test failure. If a run dies with no FAIL line, check the process count before you call it a test failure.

## Protocol

1. **Load the feature.** Read `docs/features/<slug>/FEATURE.md`: done-when, Tickets, `Base commit:`, `Failed fixes` and `Stage:`. Set `Stage: breaking`. If FEATURE.md is missing, ask the user for the slug in 1 line and stop.
2. **Fail-first check.** For each ticket test, read `test-before.log` (base commit) and `test-after.log` (build branch).
   - A test that passed on the base commit does not count. Say which test, and ask for a test that fails first. The test must come from a separate agent, not the coder.
   - A feature with no counted test is not done. Do not set `Stage: done`.
   - A playable feature (movement, turning, camera, a control, a button) counts only with a real-input test. The test sends key and mouse events (Godot: `Input.parse_input_event`, `InputEventKey`, `InputEventMouseMotion`; Unity: Input System device events) and then reads the result. A test that teleports, calls `move_to`, sets a position or calls the handler directly does not count for a playable line.
   - If a log is missing, make it: run `test_cmd` on the base commit in a worktree under `.claude/worktrees/`, then on the branch. Never put a worktree in a sibling folder. Use the Godot slot check. If you cannot run the engine, say that the log is missing and stop at this step.
3. **Tuning in data.** Scan `build.diff` for new literal tuning numbers in the game code (damage, hp, speeds, thresholds, timers, counts). For each one:
   - Write it to `data/balance/<system>.json` with `value`, `min`, `max`, `step`, `unit` and `was` (the `file:line`).
   - Write a ticket line for the code change: read the value from the file, and expose it as an editor knob.
   - Skip 0, 1, -1, and maths constants such as 0.5 in an average.
4. **Brief.** Write `docs/features/<slug>/breaker-brief.md` from the template in `references/formats.md`. Put in only the done-when, the full diff and the 2 test logs. Leave out the builder's report, the builder's chat and any claim about quality.
5. **Breaker.** Start a fresh subagent (Agent tool, `model: <breaker_model>`) with only the brief. It is a blind verifier: it sees only the done-when line, the diff and the build. It never sees the builder's notes, report or chat, and it gets no other file.
   - If the prompt says to start no agents, or the Agent tool is blocked, say so in 1 line. Then do the breaker pass yourself from the brief only, and mark the report `Breaker: same session`.
6. **Live pass (live runs only).** The breaker drives each done-when line with real input: key presses, mouse moves and clicks on the buttons, as a player does. It reads the numbers through the bridge (`get_state` on `bridge_addr`) and pastes them. The bridge reads state only; it never moves the player in a live pass. Turn past 180 degrees, hold a key, let go, and look at the frame after each step. If the bridge has no field for a number, write `Not measured: <line> (no bridge field)`.
7. **Report.** Write `docs/features/<slug>/breaker.md` in the format of `references/formats.md`. Rank each finding Must, Should, Could or Defer. Each finding has a `<file>:<line>` or a repro.
   - A divide by zero, a NaN or inf value, a crash, lost data, or a false done-when line is a Must.
   - **Disprove.** Do this before the fix loop. Start a second fresh subagent (`model: <breaker_model>`) with the brief and the findings. It tries to prove each finding wrong. It scores each finding from 0 to 100 (100: the finding is real).
   - Drop each finding with a score under 50. List the dropped findings with their scores under `Dropped` in `breaker.md`. Fix only the findings that stay.
8. **Fix each Must.** Write 1 line of 5 whys: `Why: <symptom> <- <cause> <- ... <- <root cause>`.
   - Add a test or a gate for the whole bug class, not only this line. Example: a divide bug gets a check on every division by a difference in the game code, at the edge values.
   - "Be more careful" is not a fix. The guard must make the mistake fail a test.
   - A separate agent writes the guard test. It must fail on the current code before the fix.
   - **Hostile round.** After the fix commit, start a fresh subagent (`model: <breaker_model>`) with the fix diff and the build. It looks for bugs that the fixes added. Each new bug goes into `breaker.md` and goes through Disprove and step 8.
9. **Cap the fix loop.** Count the tries for this Must in FEATURE.md `Failed fixes`.
   - If the count is `fix_attempts_max` (2) or more, do not write a 3rd patch. Do not print one either.
   - Roll back to the last green commit with `git revert` of the fix commits, by hash. Never `git reset --hard` without the user.
   - Add the failed tries to `Failed fixes` if they are not there.
   - Ask the user 1 AskUserQuestion: change the approach, or cut the scope. Give a proposed answer and a one-line reason for each option.
10. **Pass 2.** After the fixes, run the breaker again with a new brief. Stop after `breaker_passes_max` (2) passes. Open Musts after pass 2 go to the user as 1 decision.
11. **Route.** Send visual findings to `route_visual_to` (look-critic). Send balance and fairness findings to `route_balance_to` (playtest-bot).
    - Give playtest-bot a done-when band in numbers. Example: "the player wins 70-90% of 1 v 1 boar fights over 50 seeds".
    - Check that `.claude/skills/<name>/SKILL.md` exists. If it does not, say in 1 line that the skill is not built yet, and write the band in `breaker.md` under Should.
    - "Does it feel fair" is a balance question. The breaker does not answer it; it names the band.
12. **Done or not.** Set `Stage: done` only when no Must is open, each ticket test failed first, and a hand play-through with real input passed. The play-through uses each control of the feature once and takes a frame at each step. "Ship it" with an open Must gets a no: name the Must and its `file:line`.

## Reply to the user

The chat block sits above a line with only `---`. It has max `reply_max_lines` (6) non-blank lines:

1. Line 1: `Musts fixed: <n> of <total>`, or `Not done: <reason>`.
2. The open Must or Should items, 1 line each, with `file:line`.
3. At most 1 decision, with a proposed answer.
4. The last line: 1 next step with its size (S, M, L or XL).

No preamble and no recap. Below the `---` line, print `breaker.md` and every other file you wrote, each under `=== <path> ===`. End with `Files written: <paths>`.

## Sources

- Breaker, disprove score and hostile round: https://gist.github.com/mkreyman/e440e27f1e2292c038b497ad9d6c95df
- Blind verifier (the breaker sees no builder notes): https://tokenfly.ai/agentforce

## Files

- Reads: `docs/features/<slug>/FEATURE.md`, `build.diff`, `test-before.log`, `test-after.log`, `ps.txt` (eval stand-in for `pgrep`), `breaker.md` from an earlier pass, `.claude/skills/*/SKILL.md` (sibling check).
- Writes: `docs/features/<slug>/breaker-brief.md`, `docs/features/<slug>/breaker.md`, FEATURE.md `Stage:` and `Failed fixes` only, `data/balance/<system>.json` proposals, and the slot row in `godot_slot_file`.
- Never reads for the breaker: `build-report.md`.

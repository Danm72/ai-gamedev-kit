---
name: playtest-bot
description: >
  Use when the user wants a Godot or Unity game checked by numbers, not by eye: "are the boars too hard", "do the boars get stuck", "test the boars", "leave it running and see if it breaks", "soak it", "is the balance ok", "run the bot", "does hunger kill me too fast". Uses a named bot policy, seeded headless runs, a text state dump and bands. Files a finding only after a confirm batch on new seeds. Not for looks, art or screenshots (look-critic). Not for "does the game still start" (`tests/smoke.sh`).
---

# playtest-bot

Answer logic and balance questions with numbers. A named bot policy plays seeded headless runs. Each run writes its state as JSONL. The CHECK step compares a batch statistic to a band. Harness failures stay apart from balance findings.

Read `gotchas.md` before the first run. Read `references/contract.md` for every file format: bands, policies, JSONL, meta, check ids, the slot file, the command line and tickets.

## Assumes

The runner, the bot and the policies are NOT in this kit. Your game repo must have them, or the skill prints a plan and tickets and starts no run.

1. `scripts/run_seeds.sh` (`runner_script` in config): starts 1 seeded headless game per seed, each on its own port and `--data-dir`, under `timeout`. It runs the bot policy against each game and writes `runs/<check-id>/seed-<n>.jsonl`, `.meta.json` and `.log`. With `--dry-run` it prints each command line and starts nothing.
2. `tools/playtest_bot.py` (`bot_script` in config): connects to 1 game over the bridge, plays 1 policy with real input, samples `get_state` every `sample_every_s` of game time and writes the JSONL (format in `references/contract.md`).
3. Policies in `policies_dir` (default `work/playtest/policies/<name>.json`): a verb script or a goal list of real inputs.
4. A game bridge (this kit's `bridge/`) with `get_state`, `sim_input` or `input` (real input events), and a debug time lever such as `set_time_scale`.
5. Game user args: `--seed <n>` that reaches every behaviour RNG, `--port <n>` and `--data-dir <dir>`.
6. Balance data in `balance_dir` (default `data/balance/*.json`) that the game reads at start.
7. GNU `timeout` (`timeout_bin`) and the engine binary (`godot_bin`) on the machine. Set both paths in config.
8. Optional: a failure-label script (`label_script`) and a TypeSafe account (see "Label the failures").

## Config

1. Read the skill `config.json`.
2. Read `work/playtest/playtest.config.json` in the repo if it exists. Its keys replace the skill defaults.
3. All paths are relative to the game repo root.

## Hard rules

- Numbers only. A screenshot is never evidence for a band. Looks go to look-critic.
- Real input only for a playable system. A policy moves the player with key and mouse events (`Input.parse_input_event`, or a bridge `sim_input` command that makes those events). A policy that teleports, calls `move_to` or sets a position gives no valid run for a band on movement, travel time, oxygen, hull or any control.
- Never widen a band. Never edit a test to make it pass. Fix a fail in `data/balance/`.
- Never write the paths in `editor_owned` (config). If your game has an in-game editor, it owns them. Write editor data files (for example `data/placements.json`) only through the editor's save commands (for example `editor_save`), never by hand.
- Run at most `max_godot_instances` engine processes on the machine. The user's own game and any other agent's game count.
- Every `godot` call runs under `timeout`.
- Start a windowed Godot through `tools/godot_bg.sh` (in this kit) when the repo has it, so the bot run does not take the user's focus. Never make a changed or re-signed copy of the Godot app.
- Post, email or message nobody. Every wait polls at 5 s or less.
- Print each file you write under a line `=== <path> ===`.

## Protocol

### Scope

0. Check that `get_state` reports the system in the ask. Grep the `get_state` handler in your game (`state_handler` in config). If the system is not there, reply in 1 line: "<system> is not in the game yet. Build it first, or test <nearest real metric>?" Then stop.
1. Check 3 prerequisites in this order. If one does not exist, the reply is a ticket list. No run happens.
   - a. A `--seed` user arg that seeds every behaviour RNG. Grep `scripts/` for `randomize()`, `seed = <number>` and a bare global `randf()`, `randi()` or `randf_range()`. Each hit is a blocker, except a tagged map seed (see `references/contract.md`, Seeds).
   - b. A `get_state` field for each band metric.
   - c. A debug time lever, for example a `set_time_scale` bridge command.
   - Step 1 blocks a new run only. A batch with status `done` still goes through steps 9 to 14. A step 1a hit then names the cause of a hash mismatch.

### Set up

2. Name the bot policy in `work/playtest/policies/<name>.json`: a verb script or a goal list. Each verb is a real input: a key held for a time, a mouse move or a click on a named button. Every JSONL header carries policy, seed, data hash, build hash and `input: real`. A run with `input: teleport` is a harness failure for a playable band.
3. Read `work/playtest/bands.json`, or write new rows. A new row that you write is always `PROPOSED`.
4. Prove each new band can fail. Run the check on a known-bad data file first. A pass counts only after that fail (a test counts only if it failed first). A band with `proven_red: null` gives no PASS.

### Find the batch

- Read `work/playtest/runs/INDEX.tsv`. A row with status `done` for the policy is a batch that nobody checked. Go to step 9 for it. Do not run it again.
- Compare the row `data_hash` to `shasum data/balance/*.json`. With no Bash, use the row as it is.
- With no `done` row, go to step 5.

### Run (live only)

5. Count engine processes with `pgrep -fl godot` (or your engine's process name). Free slots are `max_godot_instances` minus that count. At 0 free slots, start nothing. Ask the user 1 question with 2 options: queue the batch, or stop one process. Use `AskUserQuestion`. If it is not available, write the question as the last chat line.
6. Start each run with `scripts/run_seeds.sh`. Its `--dry-run` prints each command line. The command form is in `references/contract.md`. Print concrete values only, never the template: `--fixed-fps 60`, a port per run, and `--data-dir /tmp/playtest.<check-id>.<seed>`. If the script does not exist, do not build it and do not start a run. Print the dry-run plan below the `---` line: 1 command per seed, in batches of the free slot count. Add the ticket "Build scripts/run_seeds.sh" to the plan.
7. Start runs with Bash `run_in_background`. Wait with Monitor on the `.exit` files, 5 s polls max. Use no scheduler script and no Workflow for 1 batch.
8. Each run writes `runs/<check-id>/seed-<n>[.<variant>].jsonl` and `seed-<n>.meta.json`. Add a row to the slot file (`slot_file`) at start. Remove it at exit.

### Check

9. Determinism gate. Compare the `jsonl_sha1` of `seed-<n>.jsonl` and `seed-<n>.rerun.jsonl` for `determinism_repeats` seeds. If the hashes differ, the batch is NONDETERMINISTIC. Judge no band and file no finding. Find the first `t` where the 2 files differ. Grep `scripts/` for the RNG that ignores `--seed`.
10. Triage each run from its `meta.json` and `.log` (table in `references/contract.md`). Timeouts, memory kills, timeout kills, port clashes and crashes are harness failures, not findings. Keep them out of the band stats.
11. If valid runs are fewer than `min_valid_runs`, the verdict is "no verdict, rerun". File nothing.
12. Compute the per-seed value (`agg`) and the batch statistic (`stat`) for each band. Compare it to `min` and `max`. Write `REPORT.md` with a band table and a per-seed table.
13. A band fail in a detect batch is a CANDIDATE, never a finding. Plan a confirm batch on fresh seeds: seeds not in `seeds-used.txt`. File a FINDING only when the confirm batch also fails.
    - A single seed out of band while the batch statistic is in band is a NOTE. Rerun that seed once to see if it repeats, and add it to the next batch.
14. Append each seed you use to `seeds-used.txt` as `<seed> <date> <data-hash>`.

### Label the failures (optional)

Do this after each seed batch, before you act on a band. Skip it when your repo has no `label_script`.

- Run `uv run <label_script> runs/`. It reads the TypeSafe credential from the env var named in `label_env_var`. With no credential, `--dry-run` prints the facts and calls no model.
- The script writes `runs/labels.jsonl` and `runs/needs_review.md`. Code finds each failure window and states the facts. Jev (TypeSafe) labels only the cause.
- A row with route `opus` or `review` is for the main agent to decide. Read the facts in `needs_review.md` and decide the cause yourself.
- A Jev label is never a finding on its own. A finding still needs a band fail and a confirm batch (step 13).
- The labels are not calibrated. In the first real use (Crush Depth), only 1 scenario existed: a greedy-deep lost dive, with `bot_plan` at 0.57 to 0.61. Treat each label as a hint until you calibrate on your own runs.

### Act

15. Tune data only against a `USER` band. A `PROPOSED` band gives notes only, until the user promotes it. For a PROPOSED fail, change no file under `data/`. Ask the user to confirm the band.
16. Fix a FINDING in `data/balance/*.json` with the smallest change that the numbers point to. Print the change. The next step is a new batch on fresh seeds. A USER band change is 1 question with 2 options: change data, or the user moves the band.
17. Dead content, later: run A/B on paired seeds with the variants in `variants.json`. Flag an item when |delta| is `dead_delta_eps` or less on every pair. Also flag stuck states (`stuck_s`) and cliffs (`cliff_ratio`).

## Reply to the user

The chat block sits above a line with only `---`. It has 4 lines max. Start each line with its label. Use no bullet, number or bold at the line start.

```
<N> of <M> bands pass on <K> seeds.
Top finding: <band, value against the band, where, how many seeds>.
Band change: none
Next seeds: <range> (<why>, size S|M|L). Next step: <one action>.
---
=== work/playtest/REPORT.md ===
...
```

- Count only the bands of the policy under check in `<M>`.
- `Top finding:` says CANDIDATE, FINDING or NOTE and gives the numbers.
- `Band change:` is `none`, or the 1 question to the user.
- `Next seeds:` names only fresh seeds. Never list a seed from `seeds-used.txt` there.
- Sizes: S, M or L from `soak_sizes` (seeds per size). Never give wall-clock time. Game time ("240 s of game time") is fine.
- Below `---`: tickets, the dry-run commands and each file you write.

Special first lines:

- A system not in the game: the 1-line reply of step 0.
- A prerequisite that does not exist: `No run: <blocker>.` Put the tickets below `---`, blocker first.
- Too few valid runs: `No verdict, rerun: <V> valid runs of <N>, <min_valid_runs> needed.`
- A nondeterministic batch: `No verdict: seed <n> does not repeat (NONDETERMINISTIC from t=<t> s).`
- No free Godot slot: the 1 question of step 5.
- A band field that every run reports as null: `No verdict: <field> is not measured.` Add a state-dump ticket.

## Files

- Reads: `bands.json`, `policies/*.json`, `variants.json`, `runs/INDEX.tsv`, `runs/<check-id>/*.jsonl`, `*.meta.json` and `*.log`, `seeds-used.txt`, `data/balance/*.json`, game scripts (grep).
- Writes: `work/playtest/REPORT.md`, PROPOSED rows in `bands.json`, lines in `seeds-used.txt`, changes in `data/balance/*.json`, rows in `runs/INDEX.tsv` and the slot file.
- Never writes the `editor_owned` files by hand; only the in-game editor's save commands write them.

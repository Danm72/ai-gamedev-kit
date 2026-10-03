# playtest-bot file contract

All paths are relative to the game repo root. The keys in `config.json` set the paths.

## get_state fields

`get_state` is the bridge command that dumps game state (`state_handler` in config). A band can use only a field that `get_state` reports.

Example: the table from the first game (the survival RPG POC). Write your own for your game.

| Field | In the game | Needed for |
|---|---|---|
| `player.pos`, `player.in_water`, `player.on_floor` | Yes | Water checks |
| `queue_len`, `pieces_total` | Yes | Build checks |
| `boars` (positions only) | Yes | Boar checks |
| `game_time_s` | No | Every band on game time |
| `boar_stuck_s`, `boar_stuck_at` | No | Boar stuck band |
| `player_fell_in_water_count` | No | Water band |
| `build_queue_drain_s` | No | Build queue band |
| `pieces_lost_after_restart` | No | Restart band |
| Hunger, day clock, items, upgrades | No: the game has none | Nothing yet |

Grep the `get_state` handler for the field name. The table is a snapshot. The code wins.

## Seeds

- The run seed comes from the user arg `--seed <n>`. It must reach every behaviour RNG: boars, world timers, AI picks.
- Map seeds stay fixed for every run: for example terrain noise and the world layout. Tag each one with a `# map seed` comment or a `MAP_`/`LAYOUT_` const. The run seed never reaches them.
- Blockers for step 1a: `randomize()`, `seed = <number>` without a map-seed tag, and a bare global `randf()`, `randi()` or `randf_range()` in behaviour code. The global RNG ignores `--seed` unless the code calls `seed(<n>)`.

## bands.json

A JSON list. One object per band:

| Key | Meaning |
|---|---|
| `metric` | Plain name, for the report |
| `field` | The `get_state` field |
| `agg` | Per-seed value: `last`, `max`, `min` or `first_t_where` |
| `where` | The condition for `first_t_where`, else null |
| `stat` | Batch statistic: `median`, `p10`, `p90` or `rate` |
| `min`, `max` | Band limits; null means no limit |
| `unit` | Unit of the value |
| `policy` | The bot policy that the band applies to |
| `reason` | Who set it and why, with the date |
| `tag` | `USER` (the user set it) or `PROPOSED` (an agent set it) |
| `proven_red` | Date, known-bad data file and the fail result. Null means not proven |

p90 uses the nearest rank: sort the per-seed values, take value number ceil(0.9 × n).

## Policies

`work/playtest/policies/<name>.json`: `name`, `kind` (`verbs` or `goals`), `input` (`real` for any playable band), `duration_s`, `reason`, `steps`. The policy name goes in every JSONL header.

## Runs

- Folder: `work/playtest/runs/<check-id>/`. The check id is `<policy>-<YYYYMMDD>-<label>`, for example `boar-chase-20260930-detect`.
- `runs/INDEX.tsv` has 1 row per batch: `check_id`, `policy`, `seeds`, `data_hash`, `build_hash`, `status` (`running`, `done`, `reported`), `note`.
- `seed-<n>.jsonl`: line 1 is the header (`type: header`, `policy`, `seed`, `data_hash`, `build_hash`, `input` (`real` or `teleport`), `map_seed`, `fixed_fps`, `time_scale`, `sample_every_s`, `fields`). Then 1 sample per `sample_every_s` of game time with `t`. A clean run ends with `{"type": "end"}`.
- `seed-<n>.rerun.jsonl` is the determinism repeat. A variant run is `seed-<n>.<variant>.jsonl`.
- `seed-<n>.meta.json`: `seed`, `exit`, `elapsed_s`, `timeout_s`, `signal`, `port`, `data_dir`, `jsonl_sha1`.
- `seed-<n>.log`: the Godot stdout and stderr.

## Exit triage

| Meta | Class | Counts as |
|---|---|---|
| exit 0, `end` line present | Valid run | Data |
| exit 124 | Timeout | Harness fail |
| exit 137, elapsed_s under timeout_s | Memory kill | Harness fail |
| exit 137, elapsed_s at timeout_s + kill_after_s or more | Timeout kill | Harness fail |
| log has "address already in use" | Port clash | Harness fail |
| any other non-zero exit | Crash | Harness fail; read the log |

## seeds-used.txt

1 line per seed: `<seed> <YYYY-MM-DD> <data-hash>`. A fresh seed is a seed that is not in this file. Take the next free seeds above the highest seed in the file.

## Godot slots

The slot file (`slot_file` in config, default `work/manager/godot-slots.tsv`), shared by every skill in the repo: `lane`, `pid`, `started` (ISO time). Add a row when a run starts. Remove it when the run exits. `pgrep -fl godot` is the truth; the file tells who owns each process.

## Command line

1 command per run. `i` counts from 0 inside the check:

Form (the values come from config):

```
timeout -k <kill_after_s> <godot_timeout_s> <godot_bin> --headless --path . --fixed-fps <fixed_fps> -- --port <port_base+i> --data-dir /tmp/playtest.<check-id>.<seed> --seed <seed>
```

Example with the defaults, seed 21 as run 0 of check `boar-chase-20260930-a`:

```
timeout -k 10 300 godot --headless --path . --fixed-fps 60 -- --port 9180 --data-dir /tmp/playtest.boar-chase-20260930-a.21 --seed 21
```

## REPORT.md

Header lines: check id, date, policy, seeds, data hash, build hash, determinism result, valid runs. Then a band table (band, field and agg, stat, value, band limits, result). Then a per-seed table (seed, exit, class, value per band field). Then CANDIDATE, FINDING and NOTE lines. The result per band is PASS, FAIL, CANDIDATE, NOT MEASURED or NOTES ONLY (a PROPOSED band).

## Ticket template

```
T<n>. <title>
Done when: <numbers>.
Proof: <command or file>.
Size: S, M or L.
```

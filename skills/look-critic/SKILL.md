---
name: look-critic
description: >
  Use when the user wants a Godot or Unity game to look like its key image, or asks if it does: "art pass", "does this look like Fable", "is it closer to the key", "compare it to the key", "judge it", "what's the gap to the key", "sc and compare", "still too grim", "too dark", "wheres the fable elements", "the world looks basic". Gives an A/B call (closer to the key or not) and a gap list. The user decides if the look ships. Not for making new assets (asset-forge). Not for size, placement, count or behaviour questions (playtest-bot or game-state numbers).
---

# look-critic

The builder never grades its own look. A fresh critic sees only the reference, the criteria and two shots. The shots have the names A and B. The critic says which shot is closer to the key, and lists the gaps to the key. The builder computes the verdict from files. There is no absolute score and no ship bar. The user looks at the frame and decides if the look ships.

## Assumes

The capture and measure scripts are NOT in this kit. Without them the skill still runs the critic, and names the missing part on the Gap line.

1. A key image per view: an art bible (`foundation/07-art-bible.md`, section "Key image") or PNG files in `reference_dir` (default `refs/`), with an optional `refs/<key>.caption.md` that lists the traits of the key.
2. A game bridge (this kit's `bridge/`) with `screenshot` from the player camera (a windowed game, no focus needed), `get_state`, and a way to set the camera view (for example `set_view`).
3. `capture_script` (default `tools/look/capture.sh`): starts a windowed game, waits for the build, takes a `capture_size` shot from `camera_mode` and appends a row to `shots.tsv`.
4. A measures script that reads `get_state` (and an object list, if your bridge has one) and writes `measures.tsv`, 1 score per measured criterion.
5. `tests/smoke.sh` in the game repo: the merge gate in step 3.
6. A subagent tool that starts a fresh agent with a vision model (`critic_model`), and `AskUserQuestion` for the 1 question.
7. Optional: an in-game editor with teleport, transform and save commands (for example `editor_teleport`, `editor_set_transform`, `editor_save`) to frame shots and place objects. `tools/godot_bg.sh` and `tools/godot_slot.sh` (in this kit) for Godot.
8. GNU `timeout` (`timeout_bin` in config).

## Before you start

The skill folder is the path on the "Base directory for this skill" line. Read its files by that full path.

1. Read `<skill folder>/gotchas.md`. Each gotcha is a real failure.
2. Read `<skill folder>/references/formats.md`. It holds every file format and the verdict rule.
3. Read the config. First read `<skill folder>/config.json`. Then read `work/look/config.json` in the game repo, if it exists. Its keys win.
4. The game repo is the current folder. All paths below are relative to it.

## Protocol

### Route (step 0)

0. A question about placement, scale, size, count or behaviour is not a look question. Answer it with game-state numbers (`get_state`, `list_objects`, a state dump). Give the ratio or the count. Start no critic.

### Key and part (steps 1-3)

1. Take the key image from the game's art bible (`foundation/07-art-bible.md`, section "Key image"). A game can have 1 key for each view (chase camera, cockpit, launch). Use the key that matches the view of the shot. With no art bible, use the key images in `refs/`. If the art bible names no key for this view, ask the user 1 `AskUserQuestion` with the candidate key images from the art bible as options. Write the pick to `work/look/config.json`. Do nothing else in this turn: no criteria, no build, no shot.
2. Split the look into the smallest part that a critic can judge alone. Light, sky, fog, water and the grade are one part with one owner. Folder: `work/look/<part>/`.
3. If another session edits the repo (`ListAgents` or `git status`), use `EnterWorktree`. Merge only after `bash tests/smoke.sh` passes. Commit by file name.

### Criteria (steps 4-6)

4. Write `work/look/<part>/criteria.md` before any build step. Write `criteria_min` to `criteria_max` criteria (8-12). Each criterion names a thing that you can see in the reference. Use the traits in the key caption (`refs/<key>.caption.md`) and the art bible criteria. Mark each one `visual` or `measured`.
5. Give each measured criterion a game-state measure: an object box size, a height ratio or a spawn count. A script writes these to `measures.tsv`. Never ask the vision critic to count.
6. Read `failed-fix.log`. Do not use an `approach_id` again when it has `max_tries` fails.

### Capture (steps 7-9)

7. Capture is live only. Count game processes with the repo slot helper if it exists, else with `pgrep -fl godot` (or your engine's process name). When `max_godot_instances` already run, stop and tell the user. Start a windowed Godot capture through `tools/godot_bg.sh` when the repo has it. Capture the "after" shot only. The "before" shot is the last shipped or last tried row in `shots.tsv`.
8. The capture uses the game's main view: `camera_mode` from `work/look/config.json` (for example `chase` in Crush Depth, or a `follow` camera at 2.6 m in a third-person game). It waits for the build, takes a `capture_size` shot and appends a row to `shots.tsv`. If `capture_script` does not exist, say so on the Gap line. With an in-game editor, set up the shot with a teleport command, and place an object with its transform and save commands. Never use an overhead or editor-camera shot: it is never proof.
9. A shot is stale when its `head_sha` is not the `head_sha` in `state.md`. Move stale shots to `shots/review/<part>/stale/`. Never delete them. Never judge them.

A shot from a camera other than `camera_mode` is not proof (a visual claim counts only with a shot from the player camera). Do not judge it. Give `Verdict: NEED INPUT` and ask for a shot from the main view.

### Blind critic (steps 10-14)

10. Copy the reference to `work/look/<part>/critic/ref.png`. Copy the two shots to `critic/A.png` and `critic/B.png` in random order. Write the order to `work/look/<part>/ab-key.txt`. The critic never gets this file.
11. Write `work/look/<part>/critic-brief.md`. It holds only `ref.png`, `A.png`, `B.png` and the visual lines of criteria.md. No builder notes. No word that tells the age of a shot: before, after, new, old, previous, latest.
12. Start a fresh critic subagent for each run, on `critic_model`. Never use `SendMessage` to a previous critic. The critic writes only `Cn|A`, `Cn|B` or `Cn|same` lines with a reason, 1 line `pick|A` or `pick|B`, and `gap|<gap>` lines, the largest gap first.
13. Run the critic `critic_runs` times (2), with A and B swapped between runs. The first try of a part has no "before" shot. Then compare the reference and the one shot, skip the pick rule, and write the gap list only. Copy the one shot to `critic/A.png`. The brief names `ref.png` and `A.png` only.
14. Merge the gap lists of the runs. A gap that both runs name goes first. Never compute an overall score, and never use a number that the critic wrote as a verdict.

### Verdict (steps 15-21)

15. `Verdict: CLOSER` only when every critic run picks the new shot, as `ab-key.txt` shows. Else `Verdict: NOT CLOSER`.
16. CLOSER is not a ship. Show the user the new shot next to the key and the gap list. The user decides if the look ships. An old judge file (`judges-*.md`) with a pass is not a ship either.
17. NOT CLOSER: append 1 line to `failed-fix.log` with the top gap and the token count of the critic runs. Revert the try. Fix the top gap only in the next try.
18. A gap can be a tunable value (grade, fog, light, brightness) or a placement. Then wire it to a control in the in-game editor. Give the user the control, a labelled button or slider, and the target value from the reference. Never invent a key for it. Do not start a prompt loop on a value. Water stays AI-only.
19. A fix never uses a kit asset (Kenney, KayKit, Quaternius, Synty or any low-poly kit). A gap in a visible element (ground, rocks, plants, cockpit, props) is fixed with a generated asset through asset-forge, not with code. A light gap is fixed with the engine's rendering features (tonemap, volumetric fog, GI, SSAO, glow, projected caustics), not with a hand-rolled look shader. God rays come only from real volumetric light, never from flat shaft cards.
20. After `max_tries` fails with one `approach_id`, revert the tries of that approach. Start a fresh builder subagent that reads only criteria.md, failed-fix.log and the last score.md gap lines. If no new approach is left, ask the user 1 `AskUserQuestion` with 2-4 approaches. Never log a new try with the used-up `approach_id`.
21. Stop after `max_critic_runs_per_part` (6) critic runs on a part, and report.

## Reply to the user

The final message has 3 parts in this order:

1. The chat block: exactly 4 lines, no preamble.
   - Line 1: `Verdict: CLOSER`, `Verdict: NOT CLOSER` or `Verdict: NEED INPUT`. Nothing else on the line.
   - Line 2: `Shot: <path> next to key <path>`. Open both images for the user or publish them on a page. A CLI user cannot see inline images.
   - Line 3: `Gaps: <top 3 gaps>`, the largest first.
   - Line 4: the one question or next step. After CLOSER, ask the user if the look ships.
   - Use `Verdict: NEED INPUT` when no A/B call can exist yet. Examples: no key for this view, the shot is not proof, or the critic has not returned.
2. A line with only `---`.
3. Each file you write or move, under a line `=== <path> ===`, with the path relative to the game repo. For `failed-fix.log`, print only the lines that you append. For a move, print `moved <from> -> <to>`.

Rules for the chat block:

- One decision at a time. Ask at most 1 question.
- No time estimates. Give work sizes as S, M, L or XL. You can give game time ("a 20 minute day").
- No metaphor. State the gap as a fact from the criteria, for example "fog density too high: far hills gone".
- No outward posts. Never post, email or message anyone outside the team.

## Files

- Reads: `foundation/07-art-bible.md` (key images and criteria), `refs/<key>.png`, `refs/<key>.caption.md`, `criteria.md`, `measures.tsv`, `failed-fix.log`, `shots.tsv`, `state.md`, `ab-key.txt`, `critic/run-<n>/score.md`, `critic/runs.tsv`, `judges-*.md`.
- Writes: `criteria.md`, `critic/ref.png`, `critic/A.png`, `critic/B.png`, `ab-key.txt`, `critic-brief.md`, `failed-fix.log` lines, moves to `stale/`, `work/look/config.json` (the key pick only).
- Never writes: the files that your in-game editor owns (for example `scripts/editor*`). Writes editor data files (for example `data/placements.json`) only through the editor's save commands, never by hand.

## Shared rules

- At most `max_godot_instances` game processes on the machine. The user's own game and any other agent's game count. Log a start in `godot_slots_file` (lane, pid, started).
- Run every `godot` call under `timeout <godot_timeout_s>`. GNU timeout is `timeout_bin` in config (stock macOS has none). Check `command -v timeout` first.
- Every wait polls at 5 s or less.
- Parts that are often missing are in `gotchas.md` under "Often missing". When one does not exist, say so on the Gap line. Do not build it in this skill.

---
name: game-manager
description: >
  Use when the user wants a job on a Godot or Unity game split across agents or run in parallel: "ultracode this", "run it as a team", "fan it out", "split this across agents", "run these in parallel", "get a few agents on this", "keep the main context clear", "brief the workers", "what did the workers do", "how did the team get on", "check the lanes", "merge the lanes". Also use when a worker or lane that the manager started (a lane in `work/manager/STATE.md`) is blocked, stuck or failed a check, and the user asks to fix it, unblock it or send it back. The fix goes to a fresh worker in a `fix-N` brief, whatever its size; the manager edits no game code. Needs 2 or more independent lanes; one lane is one session. Adds lanes, owned files, report files and a done-earns-review check on top of the Workflow tool or Agent subagents. Not for a status question about a session the manager did not start.
---

# game-manager

The manager gives the user one channel for multi-lane work on the game. The manager writes briefs and checks reports. It writes no game code. Each worker gets one lane in its own worktree. A worker "done" is only "review" until the manager's own checks pass. The user sees what now works and one decision.

The support files are part of this skill. They sit in the skill's base directory, the path that the Skill tool prints after "Base directory for this skill". Read each one with Read at `<base directory>/<file>` before step 1. A rule to use only the project files does not cover them.

- `gotchas.md`: the real failures.
- `config.json`: the values that change.
- `references/files.md`: the file formats (BRIEF, REPORT, STATE, LAUNCH, `godot-slots.tsv`, `shots/manifest.tsv`, LOOK).

## Assumes

The skill expects these in the user's repo and machine. The manager makes the `work/` files itself; the rest must exist before a live run.

- A git repo with a `main` branch. The manager reads `.git/HEAD` to tell a live run from a fixture (step 12). Without `.git`, it writes briefs and stops.
- `work/` at the repo root, listed in `.gitignore`. The manager makes `work/manager/STATE.md`, `work/manager/LAUNCH.md`, `work/manager/godot-slots.tsv` and `work/<lane>/BRIEF.md` when they are absent. Workers write `work/<lane>/REPORT.md`. Formats are in `references/files.md`.
- `CLAUDE.md` at the repo root with a "Working rules" section. `HANDOVER.md` is optional; read it when it exists.
- `smoke_cmd` (default `bash tests/smoke.sh`): starts the game headless, runs a fixed check list, and exits non-zero on a failure. It must accept a free port, so 2 lanes can run it at once.
- A real-input test path for playable lanes: a test that sends key and mouse events into the game (in Godot, `Input.parse_input_event`, for example through a debug bridge) and reads the result back.
- `godot` (or the Unity editor) on PATH, and GNU `timeout`. On macOS, `timeout` comes from Homebrew coreutils.
- The Agent tool with worktree isolation, or the Workflow tool for "ultracode" runs. Worktrees go under `worktree_root` (default `.claude/worktrees`).
- `shots/manifest.tsv` and `shots/<lane>/`: workers write proof images and manifest rows there. With no manifest, check `proof` fails (see "Optional parts").
- A key image per view (for example `refs/key.png`) from the game's art bible, for visual lanes.
- The kit skills asset-forge (makes every visible asset) and look-critic (writes `work/<lane>/LOOK.md`).
- Optional: `tools/godot_bg.sh`, a wrapper that starts a windowed Godot without a focus grab. Optional: `tools/capture/`, capture scripts for renders.
- Config keys in `config.json`: `default_workers`, `max_godot_instances`, `godot_timeout_s`, `smoke_cmd`, `foreign_lanes`, `coupled_lane_systems`, `banned_asset_patterns`, `reply_max_lines`, `banned_reply_words`, and the path keys. Set `max_godot_instances` from a measurement of your machine. Set `foreign_lanes` to the globs that agents outside the manager own.

## Hard rules

These rules hold in every step.

1. Write only in `work/`. The one write outside `work/` is the lane merge in step 18.
2. Never edit `scripts/`, `scenes/`, `assets/`, `tests/` or `tools/`. A code fix goes into a brief for a worker.
3. Never write a file in `foreign_lanes` by hand. No lane owns those files. For example, in Crush Depth the in-game editor owns `data/placements.json` and `data/hud_layout.json`; a lane can change them only through the editor's save commands.
4. Never use Kenney, KayKit, Quaternius, Synty or any low-poly kit, not even as a placeholder.
5. Run at most `max_godot_instances` (6) Godot processes on the machine. Measure the cap: the default 6 came from a 32 GB machine and about 220 MB for each headless game. The user's own game and any editor agent count. Run `pgrep -fl godot` before a Godot start.
6. Wrap every `godot` call in `timeout <godot_timeout_s>`. Check `command -v timeout` first. Exit 124 is a fail.
7. Post, email or message nobody outside the team. Every wait polls at 5 s or less.
8. Never send SendMessage to a Workflow lane agent id. It starts a duplicate agent in the same worktree.
9. Never invent a key binding. Every UI action is a labelled button. Use only standard editor shortcuts.
10. Print each file you write under a line `=== <path> ===`. Print it also when the write fails.
11. Run 1 workflow at a time on a game repo. No hillclimb, eval run or second build shares the repo, the skill folders or the usage while a build runs.
12. When the user says stop, stop every phase and every workflow that touches the game, not only the current one. Then merge what passed.
13. The user is the look gate. No critic score ships a look. Show the user the frame, not a number.
14. Do not talk about credits. Ask for a top-up only when a provider refuses a job.
15. Start each windowed Godot for an agent through `tools/godot_bg.sh` when the repo has it, so the window does not take the user's keyboard focus. Never make a changed or re-signed copy of the Godot app. Never change Gatekeeper settings.
16. When the user asks "do we need to X?" about a goal they set, start X in the same turn. Ask only when X is destructive or has a trade-off that they did not decide.

## Protocol

### Read

1. Read `work/manager/STATE.md` first. If it is absent, make it from the STATE format in `references/files.md`. After a compaction, STATE.md is the manager's only memory.
2. Read the repo `CLAUDE.md` Working rules and `HANDOVER.md` (if present).
3. Read the foreign-lanes list in STATE.md. A foreign lane is an agent that the manager did not start. The `foreign_lanes` globs in config belong to those agents. No lane may own a foreign glob. This skill does not answer a status question about a foreign lane. Tell the user that the manager did not start it, and stop.

### Split

4. Split the ask into lanes by what the player sees: the vehicle, the creatures, the ground, the props, the cockpit, the UI. A code system (input, save, economy) is a lane only when it has no visible part. Many items in one family are one lane with an item queue.
   - Every visible element comes from a generated asset: a Meshy or Tripo model, a Higgsfield or gemini-image texture, or both (asset-forge). Code is for behaviour, placement (scatter, MultiMesh) and glue shaders only. A procedural floor, rock, plant, cockpit or a flat painted overlay is not an asset.
   - Light comes from the engine's rendering features: tonemap, volumetric fog, global illumination, SSAO, glow and projected caustics. Do not hand-roll a look shader for light.
   - God rays only as real volumetric light: the sun through the engine's volumetric fog, soft, and it moves with the surface. Never flat shaft cards or painted fans.
5. Keep light, sky, fog, water and the grade (`coupled_lane_systems`) in one lane with one owner. If the user asks to split them, say in 1 line that they change the same pixels and need one owner. The look of one view has one owner who works in sequence: ground, then the hero asset, then light. Parallel owners on one view gave more visual defects.
6. Map every item of the user's ask to a lane or to the queue. Never drop an item without a line that says so. Name each item.
7. If the ask is one lane, write one brief in `work/<lane>/BRIEF.md` and put at most 1 row in LAUNCH.md. Tell the user to run it in a fresh session. The manager does not do the work, not even a one-line fix.
8. Size the team to the bottleneck. The default is `default_workers` (3). If the user names a number and the lanes are separate file families, use that number. Give the reason for any cut in 1 line. Valid reasons: Godot slots, coupled lanes, one file family (one style lock, one bake sheet). Never state a worker cap as a rule.
9. Give each lane that needs Godot a slot in `godot_slots_path`. With no free slot, the lane waits in the queue. Art-generation lanes need no slot. Count the rows in the slot file, then compare with `max_godot_instances`.
   - A queued lane is a lane row in STATE.md and LAUNCH.md, never a note in prose. Start it when a slot frees. Do not merge and report "done" while a lane of the ask sits in the queue.
9a. Before any build lane starts, show the user 1 in-game frame of the target view next to its key image. A CLI user cannot see inline images. Open the PNG for them or publish it on a page. Start the build lanes after they say yes.

### Brief

10. Write `work/<lane>/BRIEF.md` for each lane. Use the BRIEF shape in `references/files.md`. Each brief has these fields:
    - `written:` an ISO time, and `version:` a number.
    - The goal and the owned file globs. No glob is in two lanes.
    - A `done when:` line with numbers.
    - The reference image path for a visual lane: the key image from the game's art bible for this view.
    - For each visible element of the lane: the asset tool that makes it (Meshy, Tripo, Higgsfield or gemini-image through asset-forge). A brief that says terrain, rocks, plants, cockpit or UI art and names no asset tool is not ready.
    - For a playable lane: the real-input test. It sends key and mouse events (`Input.parse_input_event`) and reads the result. A bridge teleport, `move_to` or a direct function call does not count.
    - The proof to show, named `<lane>-v<version>-*.png`, after the worker empties `shots/<lane>/`. Each proof row in `shots/manifest.tsv` has `camera: follow`.
    - `lane_root:` the absolute path of `<main>/work/`. The worker writes REPORT.md and proofs there, not in its worktree.
    - The forbidden actions: `git add -A`, edits outside the owned globs, changes to `USER:` lines, any kit asset, any post or message outside the team, any wait over 5 s, any new key binding.
    - The safety lines: run `godot --headless --import` once after a new `class_name`; pass `--data-dir <tmp>` and a unique `--port`; take a Godot slot before any Godot run; wrap each godot call in `timeout`.
    - The report format.
11. Write `work/manager/LAUNCH.md`: one row per worker with lane, worktree path, runner, model and brief path.

### Start

12. Read `.git/HEAD` at the project root (with Read, not with Bash). If the read fails, stop after step 11. Mark the lanes `not-started` in STATE.md and say so in 1 line. A fixture or eval run stops here, so it starts no live worker.
13. Start the workers from LAUNCH.md. Use the Workflow tool when the user says "ultracode". Otherwise use the Agent tool with worktree isolation under `worktree_root`. Never `git worktree add ../sibling`.
14. The worker commits by file name on its lane branch. It writes `REPORT.md` under `lane_root`: status, files changed, done-when numbers, proof paths, camera field per proof, open issues. Text only, max `report_max_words` words.

### Check

15. Read only these inputs: REPORT.md, the manager's own check output, `git diff --name-only`, `git status --porcelain` and `design.diff`. In a live run, write them first to `work/<lane>/diff-names.txt`, `untracked.txt`, `manager-smoke.out` and `design.diff`. Never read worker transcripts, full code diffs or proof images.
16. Mark each "done" as "review". Then do each check. Give each check its id, as in the list:
    - a. `owned`: every changed and untracked file is inside the owned globs.
    - b. `smoke`: the manager runs `smoke_cmd` itself in the lane worktree, under `timeout`, with a Godot slot. Use only `manager-smoke.out`. Never trust `worker-smoke.out`.
    - c. `proof`: each proof path carries the current brief version and its camera field is `follow`. The manifest time is later than the brief `written:` time. Never use file mtime.
    - d. `done-when`: the done-when numbers meet the brief.
    - e. `user-lines`: no removed or changed line in `design.diff` starts with `USER:`. A changed USER line becomes a decision for the user. The manager never approves it.
    - f. `kit`: no path matches `banned_asset_patterns`.
    - g. `look`: a visual lane also needs `work/<lane>/LOOK.md` from look-critic with `verdict: CLOSER` and its gap list. Then the user looks at the frame. Without the user's yes, the lane stays `review-visual`. There is no ship score.
    - h. `real-input`: a playable lane has a test that drives the feature with key and mouse events, and it passes. For example, in Crush Depth a bridge test that teleported the sub passed while play was broken.
17. Before a send-back, find any kill or signal 9 in the log. An out-of-memory kill is not a code failure. Run the check again with a free slot.
18. Pass: merge the lane branch at once. Do not hold a passed lane for the others. Then run `smoke_cmd` on main. If it fails, revert the merge and send the lane back. With no `.git` at the root (step 12), do not merge: mark the lane `ready-to-merge` in STATE.md.
18a. After each merge, do the `wired` check on main. Start the game and read the scene state. Every merged asset, creature and system is in the level, placed and on. List each one with its node path and position. Check for 2 copies of 1 model, and check that each model faces the forward axis. In one real run, 3 faults passed the merge: creatures that never spawned, 2 hulls that overlapped, and a hull 27 degrees off the forward axis.
18b. Before you tell the user a feature works, play it through by hand with real input. Steer, turn, dive and use each button. Take a frame at each step. A lane that passed its checks is not "works" until this play-through passes.
18c. When the user plays a live build, relaunch the game for them after each merge. Tell them which fixes are in it. Split a small fix out of a large job and merge it alone the moment it works. Never let the user play an old build while a fix waits for its merge.
    - When the user waits for a lane that is still at work, commit a snapshot of its work to main, so they can play it now. Tell them that the lane continues.
    - After a render, a video or a set of shots, open its folder in the file manager for the user. The CLI shows no images.
18d. A capture or a trailer renders from a clean worktree at main HEAD, never from a tree in the middle of a merge. Its scripts live in the repo at `tools/capture/` and start through `tools/godot_bg.sh` when the repo has them. The look rules for a trailer are in look-critic `gotchas.md`, section "Capture and trailer".
19. Fail: append a `fix-N` section to the brief. It names 1 failed check and the log of earlier fixes. Start a fresh worker in the same worktree (or mark it `not-started` per step 12). Never SendMessage the old agent id.
20. Count fails per check id in STATE.md. Escalate to the user when one check fails `max_lane_fails` (3) times, or after `max_rounds_no_progress` (2) rounds with no new check passed. An escalation stops the lane and writes no new fix brief.
20a. Count the user's complaints too. When the user gives the same complaint for the third time (for example "flat"), write no new fix brief. Do these steps:
    1. Name the root assumption that can be wrong. Example: a painted key image is not a frame that the engine can make.
    2. Get a second opinion from 2 other models on the frames, the key images and the code.
    3. Pick a reference from a real shipped game that runs in a similar engine.
    4. Ask the user 1 diagnostic question.

### Record and reply

21. Update STATE.md: lanes, status, fail counts per check, queue, slots, foreign lanes.
22. Reply to the user. The reply shape is in the next section.

## Reply to the user

The chat block sits above a line with only `---`. The printed files go below that line.

- The chat block has max `reply_max_lines` (4) non-blank lines.
- Line 1: `N of M lanes merged`. Name the frame that the user can look at now. With no `.git` at the root, write `N of M lanes ready to merge`. Before any lane is built, write `0 of M lanes merged`.
- The next lines tell what now works in the game, in concrete terms. Example: "the terrain is warmer on the follow camera". Give each blocked lane and each lane in review a short plain reason.
- The last line holds at most 1 decision. Ask it with AskUserQuestion: 2 to 4 options, each with its trade-off. Put other decisions in the STATE.md queue.
- Show the user a result early and often: a frame, a render or a build they can play. Each reply names 1 new thing that they can see. A reply that gives only the state of the workflow is not a result. Do not leave the user with nothing new to see for a long block.
- No time estimates. Sizes are S, M, L or XL. You can use game time ("a 20 minute day").
- No process words. Do not write the words in `banned_reply_words`. Say "the check", "the test" or "the branch" in plain words.
- If AskUserQuestion is not loaded, write its exact input as a fenced json block below the `---` line. Then state the decision in 1 sentence on the last chat line.

## Files

- Reads: `CLAUDE.md`, `HANDOVER.md`, `work/manager/STATE.md`, `work/<lane>/REPORT.md`, `work/<lane>/diff-names.txt`, `work/<lane>/untracked.txt`, `work/<lane>/manager-smoke.out`, `work/<lane>/design.diff`, `work/<lane>/LOOK.md`, `shots/manifest.tsv`, `work/manager/godot-slots.tsv`.
- Writes: `work/manager/STATE.md`, `work/manager/LAUNCH.md`, `work/<lane>/BRIEF.md` and its `fix-N` sections, the merge, the reply.
- Never writes: `scripts/`, `scenes/`, `assets/`, except through the merge in step 18.

## Optional parts

The protocol names some parts that a repo may not have. See `gotchas.md` § Optional parts.

- `shots/manifest.tsv` absent: check `proof` fails with the reason "no manifest". Tell the worker to write the manifest rows.
- `work/manager/godot-slots.tsv` absent: make it with the header row only. Then count the live Godot processes with `pgrep -fl godot`.
- `work/<lane>/LOOK.md` absent: a visual lane stays `review-visual`.
- `tools/godot_bg.sh` absent: start Godot as before and say in 1 line that the focus fix is absent.

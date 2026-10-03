---
name: asset-forge
description: >
  Use when the user wants a new or fixed 3D model or surface for a Godot or Unity game: "the sea floor looks flat", "make the rocks", "the cockpit looks like code", "make me a chicken", "i need a tudor cottage", "model a gnome", "make a wall tile", "make 5 props", "the villager looks washed out", "it looks low-poly", "it's tiny in godot", "it's tiny in unity", "retexture the wall", "redo the barrel", "why does the boar rig keep failing". Not for placing, moving or nudging things in the world (in-game editor), level layout or animation logic.
---

# asset-forge

This skill takes an asset from a concept to a game-ready GLB. The steps are written for Godot 4.7; for Unity, keep the same flow and swap the preview render, the material and the particle steps for their Unity forms. It uses the route from a pipeline bake-off (Tripo, Meshy, Blender). It picks each route by quality, never repeats a failed tool, and uses no kits. It does one action, then one check.

The skill folder is the path on the "Base directory for this skill" line. Read its files by that full path, not from the game folder. Read these files first:

- `<skill folder>/config.json`. It holds every value that can change: routes, caps, paths.
- `<skill folder>/gotchas.md`. Each item is a real failure.
- `<skill folder>/references/bakeoff-recipes.md`. It holds the exact command for each step.

The game project is the current folder. All other paths below are relative to it.

## Assumes

The kit does not ship the pipeline scripts. Write or bring your own, and put their folder in `bakeoff_shared_dir`. Without them the skill stops at the concept step.

- `config.json` keys with a `<placeholder>`: `bakeoff_dir`, `bakeoff_shared_dir`, `style_key_path`. Fill them in before the first run. Check `blender_bin`, `godot_bin` and `timeout_bin` (Homebrew defaults on macOS).
- `<bakeoff_shared_dir>/meshy.py`: a Meshy REST client. Modes `image | multi | text | rig | anim | retexture`. It takes `body.json <outdir> <name> <asset> <pipeline>`, polls every 5 s, saves the GLB and appends 1 row to its own ledger. A body of `{"_task_id": "<id>"}` resumes a job. It reads your Meshy API key from the environment.
- `<bakeoff_shared_dir>/clean_static.py`: a Blender script. Modes `prop` and `tile`. Turns (`--yaw`), rescales to `--height` or snaps to `--footprint`, decimates to `--max-tris`, resizes textures to `--tex`, writes a GLB.
- `<bakeoff_shared_dir>/merge_meshy_humanoid.py`: a Blender script. Resets the Meshy rig material, bakes the 0.01 armature scale, decimates, clears the `clip0` NLA track and merges `--anim name=file.glb` clips onto one rig.
- `<bakeoff_shared_dir>/validate.py`: a Blender script that writes tris, bbox (X, Y, Z), origin, materials, texture px and actions to a text file.
- `<bakeoff_shared_dir>/render.sh`: renders a GLB in a headless engine preview scene under `timeout 180`. Flags `--tile N` (adds `_top` and `_seam` shots), `--anims` (front and 3/4 joint shots), `--yaw DEG`.
- Optional, not built yet: `tile_check.py` and a material and scale probe. The "Fallbacks" section covers their absence.
- Higgsfield MCP: `generate_image` (GPT Image 2.5) and `generate_3d` (Tripo H3.1). Meshy MCP for `meshy_check_balance` only. A Gemini image tool for the concept and texture fallback.
- Blender 4.x, the engine binary, and GNU `timeout`.
- The look-critic skill (in this kit) for the A/B call.
- A style key PNG for each game view, at `style_key_path` (for example `refs/key.png`).
- `docs/ledger.tsv` (`ledger_path`): the paid-job ledger. The skill makes it on first use.
- Modular assets: a grid definition in your repo (`grid_source`, for example `GRID := 2.0` in `scripts/pieces.gd`).
- Optional: an in-game editor reachable through bridge or MCP tools `editor_teleport`, `editor_set_transform` and `editor_save`. Without it, place the asset in the level by your normal method.
- Optional: `tools/godot_bg.sh` (in this kit) for a windowed Godot that does not take focus, and the game-manager slot file at `godot_slots_path`.

## Hard rules

1. Never use Kenney, KayKit, Quaternius, Synty or any low-poly kit, not even as a placeholder. A kit ask gets the generated route instead (`banned_sources` in config).
2. Never write "game-ready" or "low-poly" in a generator prompt. Generate high-poly, then reduce in Blender.
3. Send paid Meshy calls through `meshy.py` only. Never call the paid `mcp__meshy__*` tools; their confirm gate stalls a worker. `meshy_check_balance` is free and safe.
4. Post, email or message nobody outside the team. Every wait polls at 5 s or less.
5. Never write the in-game editor's files (`editor_owned_paths` in config). The in-game editor owns them. Write its placement and layout data only through its save commands (`editor_save`, `editor_hud_layout`), never by hand.
6. Run at most `max_godot_instances` (6) engine processes on the machine. The user's own game and the editor agent count. Start a windowed Godot through `tools/godot_bg.sh` when the repo has it.
7. Run every `godot` call under `timeout <godot_timeout_s>`. Stock macOS has no `timeout`; use `timeout_bin`.
8. Give no time estimates. Sizes are S, M, L or XL.
9. Print each file that you write, under a line `=== <path> ===`.
10. Every visible element of a game comes from a generated asset: a model, a texture, or both. Code makes behaviour, placement and glue shaders only. Never ship a procedural floor, rock, plant or cockpit, or a flat painted overlay, as the look. In a real build, the coded elements were the ones that failed the hardest.
11. Credits have no set limit by default (`credits_policy` in config). No credit floor in config, in a brief or in a step. Never pick a route because of a balance, and never default to Meshy for credits. Do not talk about cost, credits or balances to the user. Ask the user to top up only when a provider refuses a job for credits.

## Protocol

### A. Route (before any paid call)

1. Class the asset: `humanoid`, `creature`, `prop`, `modular`, `vehicle`, `interior` or `surface`. A prop that must hit an exact size or snap to a grid is `modular`. A wall, floor, deck or dock tile is `modular`. A cockpit or a cabin is `interior`. A ground, sea floor or rock-face material is `surface`: a tileable generated texture set, placed by code. Bubbles, an explosion, silt, a muzzle flash or a sonar pulse is `vfx`.
2. Take the first route for the class from `route[class]`. The order is by quality. The balance in the ledger does not change the route.
3. Go on and ask the user nothing about spend. A subagent never asks the user.
4. Grep the ledger for this asset and this tool. After `max_paid_fails_per_tool` (2) failed paid jobs of one tool on one asset, drop that route and take the next one. Never start a third job of the failed tool on that asset.
5. If a provider refuses a job for credits, take the next route of the same quality (for example gemini-image for a concept) and go on. Ask the user to top up that provider, in one line.

### B. Concept

6. Write 8-12 criteria from the key into `assets/_src/<asset>/criteria.md`. Use the look-critic format: one criterion a line, each a thing that you can see in the key.
7. Make the concept with GPT Image 2.5 (high, 2k), with the key image for this view from the game's art bible (`style_key_path`) as the reference. Use a flat light-grey background, no ground and no text. Save the prompt to `assets/_src/<asset>/prompt.md`.
   - Prop or creature: a 3/4 view.
   - Humanoid: a FRONT view, A-pose, full body from head to feet, no held props.
   - Multi-view sheet: only where `multi_view_sheet[class]` is true.
8. Read the concept PNG yourself. Never judge from a file name or a caption. Check the class rules of step 7 and the style key. A humanoid concept fails on a held prop or a crop of the feet or head. It also fails on a pose other than A-pose or a view other than front.
9. Regenerate a failed concept, at most `max_concept_retries` times. Never start a paid 3D step on a failed concept. When the user gives 2 or more concepts, pick one that passes and regenerate nothing.

### C. Paid 3D step (one action, then one check)

10. Run one paid 3D step for the route:
    - Prop or humanoid: Tripo H3.1 through Higgsfield `generate_3d`, or Meshy 7 through `meshy.py image`.
    - Creature: Tripo H3.1 or Meshy 7, flagged "unproven on creature". Then the Opus Blender rig (an armature and weights that the agent builds with a bpy script). Never the Meshy rig for a creature.
    - Vehicle: Tripo H3.1 or Meshy 7. Split each part that moves or lights into its own mesh, with its origin at its pivot: the propeller, the lantern and its glass, the claw and its jaw, the hatch and the porthole glass. Do the split before the first placement. The light sits inside the lantern glass, and the glass glows when the lamp is on. Never a guessed light point with a fake bulb sphere.
    - Interior: Tripo H3.1 or Meshy 7 from a concept of the cockpit seen from the pilot's seat. The window is open glass: the view outside is not part of the model. The shape comes from the generated model. Code shapes with generated textures are not an interior. Split the dials, needles, levers and the cabin lantern with pivots, so code can move them with game state. The lantern glass is its own material.
    - Vfx: generated flipbook sheets or sprites (gemini-image or Higgsfield) on the engine's particles, with soft particles on. An underwater explosion has 5 parts in this order: a flash, a cavitation bubble that grows and collapses, a shockwave ring, a burst of bubbles, then silt that drifts. Never sphere meshes as bubbles or as a blast.
    - Surface: a tileable texture set (albedo, normal, roughness) from gemini-image or Higgsfield, with the key as reference. Code places it on the terrain mesh. Rocks and plants on the surface are `prop` assets.
    - Modular: Opus bpy geometry at the exact grid size first (`grid_source` holds the grid and the piece sizes). Then `meshy.py retexture`. Then a re-snap with `clean_static.py --mode tile`. Never image-to-3D or text-to-3D for a tile.
11. After each paid job, write one ledger row. See "Ledger rows" below.

### D. Clean, rig and check

12. Clean in Blender with `clean_static.py`. Tripo output gets `--yaw -90` and a rescale to the target height. A tile gets `--mode tile` after the retexture.
13. A rigged humanoid:
    - Meshy rig at the default height `meshy_rig_height_m` (1.7 m).
    - On "Pose estimation failed", retry once at 1.7 m. Then use the Opus rig. A 422 costs 0.
    - Run `merge_meshy_humanoid.py`: material reset, 0.01 scale bake, decimate to 12k, clear the NLA `clip0`, merge the clips.
14. Run `validate.py` into `validate.txt`. Read these fields only: tris, bbox height Y, origin, materials, texture px, actions. Check them against `tris_cap[class]`, the target height +/- `height_tolerance`, and `texture_px`. A width X of exactly 1.000 on a Tripo mesh means that the clean step did not run.
15. A rigged asset: also run the material and scale probe into `probe.txt`. `validate.py` does not show emission, metallic or armature scale.
16. A tile: run `tile_check.py` into `tile_check.txt`. It gives the footprint, the grid pitch, the max overhang and the posts per corner. Fail the tile when the footprint is off the pitch by more than 1 cm, or on any overhang. Never count from a PNG.

### E. Render and compare

17. Count Godot processes with `pgrep -x godot`. Run `timeout <godot_timeout_s> render.sh` only under `max_godot_instances`. Delete old `renders/<asset>*` first.
18. Read the renders. Get the direction of the model from the front shot, not from `validate.txt`. A rigged asset: read the front and 3/4 joint shots from `render.sh --anims`.
19. Run look-critic against `criteria.md` and the key. It gives an A/B call (closer to the key) and a gap list, no score. Fix the top gap, at most `max_art_retries` (2) times. Then stop. There is no art bar: the user decides after they see the render next to the key.
20. Collision is a box, sphere or capsule from the bounds. Never trimesh.

### F. Ship or stage

21. Pass (validate, tile check, and the critic's last try is CLOSER with no blocking gap): put the GLB in `final_dir` (`assets/v2/<class>/`). Open the render next to the key for the user.
22. Fail after the retries, or a blocking gap (wrong silhouette, wrong material, off the key): keep the GLB in `staging_dir` (`assets/_staging/`) and list it as "needs the user". Show the render next to the key and the top gap. Move it to `final_dir` only after the user has seen that render and says yes.
23. The render is a preview scene, not the player camera. The next step is a shot from the game's main view. Placement goes to the in-game editor. Never place or move the asset with repeated prompts. For example, in Crush Depth, set up the shot with `editor_teleport`, and place the asset with `editor_set_transform`, then `editor_save`.
24. The asset is done only when it is wired and placed in the level. Start the game and read the scene state: 1 copy of the model, placed, facing the forward axis of its node, at the target size. Moving parts move, and each lamp's light sits inside its lantern. A cockpit lantern follows the lamp state: warm glass when the lamp is on, dark glass when it is off. In one build, a hull 27 degrees off the forward axis and 2 overlapped hulls passed the file checks.

### G. Batch (more than 1 asset)

25. Take the route for each asset with steps 1-4. Ask the user nothing about spend for the batch.
26. Fan out with Agent or Workflow, one asset per worker. Workers never ask the user.
27. Give each worker a Godot slot from `godot_slots_path` (`lane`, `pid`, `started`). Count first.
28. The lead merges the ledger rows and sends one reply table.

## Ledger rows

`docs/ledger.tsv` has the columns in `ledger_columns`, tab-separated:

`ts  service  tool  asset  agent  credits  balance_after  job_id  note`

- `ts` is HH:MM with no date. Put the date (YYYY-MM-DD) in `note`.
- `tool` starts with the bare tool name (`generate_3d`, `generate_image`, `image`, `retexture`, `rig`, `anim`). Put the model name in `note`.
- `credits` is the real cost from the job result, not the quote. It is a record only; do not report it to the user.
- `meshy.py` writes its own row in its own ledger (in `bakeoff_dir`). Copy that row once to `docs/ledger.tsv`. The `agent` column of the copy holds the pipeline arg. Grep the job id to prove 1 row.
- Print the new row inside a fence marked `tsv`, with real tab characters between the cells.
- Do not compare the balance with the next job and do not warn about a low balance. The balance never blocks a job.

## Files read and written

- Reads: `<skill folder>/config.json`, `<skill folder>/gotchas.md`, `docs/ledger.tsv`, the `meshy.py` ledger in `bakeoff_dir`, the style key, `assets/_src/<asset>/concept*.png`, `brief.md`, `validate.txt`, `probe.txt`, `tile_check.txt`, `score.md`, `renders/*.png`, `grid_source` (grid sizes, read only), `<skill folder>/references/bakeoff-recipes.md`.
- Writes: `assets/_src/<asset>/prompt.md` and `criteria.md`, rows in `docs/ledger.tsv`, `assets/v2/<class>/<asset>.glb` or `assets/_staging/<asset>.glb`, the asset table, the reply.

## Fallbacks

Some scripts do not exist yet (see "Not built yet" in `gotchas.md`).

- No `tile_check.py`: read the footprint and the bbox from `validate.txt`. Say that the tile check did not run. Never call a tile ready from a PNG.
- No material probe: open the GLB in Blender and print the emission, metallic and armature scale. Save the output as `probe.txt`.
- No `godot-slots.tsv`: count with `pgrep -x godot` only.
- No picked style key: while `style_key_path` holds a `<placeholder>`, use the one PNG in `refs/`. With no PNG or several, stop before the concept and ask the user for the key.

## Reply to the user

Keep the reply short. Ask one question at most, and only when the answers lead to different work.

The chat block sits above a line with only `---`. It has at most 120 words:

1. Line 1: the render path next to the key path. Open both for the user (a CLI user cannot see inline images). If no render exists yet, line 1 is the decision or the next action.
2. One table row: path, size in m, tris, the critic's A/B call and the top gap.
3. One weak point and one next step.
4. `PLAN:`, then one action a line. Each action that runs a script shows the command, for example `python3 <bakeoff_shared_dir>/meshy.py retexture ...` or `generate_3d (Tripo H3.1)`.

Below the `---` line, print each file that you wrote, under `=== <path> ===`.

Never give time estimates (no minutes, no hours, no "takes about"). You can give game time ("a 20 minute day").

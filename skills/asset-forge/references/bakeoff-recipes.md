# Bake-off recipes

The exact command for each step. `$SH` is `bakeoff_shared_dir` from config.json. `$BLENDER` is `blender_bin`. The scripts are your own (see "Assumes" in SKILL.md); these are the call shapes that the skill expects.

## Concept (Higgsfield)

- Tool: `generate_image`, model GPT Image 2.5, quality high, 2k, the style key as the reference image.
- Prop or creature prompt: "<object>, single object, 3/4 view, flat light-grey background, no ground plane, no text, <art style of the key>". For example, "painted Fable storybook style" for a storybook RPG.
- Humanoid prompt: "<character>, full body head to feet, front view, A-pose, empty hands, flat light-grey background, no ground, no text".
- Never "game-ready", "low-poly" or a kit name.

## 3D step

- Tripo H3.1 (Higgsfield): `generate_3d` with `tripo_h3_1_image_to_3d`, detailed texture, single view.
- Meshy 7 image-to-3D (Meshy): `python3 $SH/meshy.py image body.json <outdir> <name> <asset> <pipeline>`. The body holds `image_url` (a local path becomes a data URI) and `ai_model: meshy-7`.
- Meshy retexture (Meshy): `python3 $SH/meshy.py retexture body.json <outdir> <name> <asset> <pipeline>`. The body holds `model_url` (the local GLB), `image_style_url` (the concept), `enable_original_uv: true`, `enable_pbr: false`.
- Meshy rig (Meshy): `python3 $SH/meshy.py rig body.json ...` with `model_url` and `height_meters: 1.7`.
- Meshy clip (Meshy, one job a clip): `python3 $SH/meshy.py anim body.json ...`. Walk and run come free with the rig.
- Resume a task: a body of `{"_task_id": "<id>"}` skips the POST.
- `meshy.py` modes: `image | multi | text | rig | anim | retexture`. It polls every 5 s and appends 1 row to its own ledger.

## Blender

- Prop clean: `$BLENDER -b --python $SH/clean_static.py -- src.glb dst.glb --mode prop --height <m> --max-tris <cap> --tex 1024 --yaw -90` (the yaw is for Tripo output only).
- Tile clean or re-snap: `$BLENDER -b --python $SH/clean_static.py -- src.glb dst.glb --mode tile --footprint 2.0 --max-tris 4000 --tex 1024 --yaw 0`.
- Humanoid merge: `$BLENDER -b --python $SH/merge_meshy_humanoid.py -- rigged.glb out.glb --height <m> --max-tris 12000 --tex 1024 --anim walk=walking.glb --anim idle=idle.glb --anim wave=wave.glb`. It resets the material, bakes the 0.01 armature scale, clears `clip0` and merges the clips.
- Modular geometry: write a bpy script that builds the piece from boxes and cylinders. Exact footprint from `grid_source` (for example `GRID := 2.0`), top at the piece origin, nothing past the grid edge.
- Opus rig, humanoid: write a bpy script that adds a biped armature, fits the bones to the mesh bounds and parents with automatic weights. Opus rig, creature: the same, with a skeleton that fits the creature (spine chain, legs, fins or tail).
- Validate: `$BLENDER -b --python $SH/validate.py -- file.glb validate.txt`.

## Godot preview

- `pgrep -x godot | wc -l` first. Under `max_godot_instances` only.
- `bash $SH/render.sh file.glb renders/<asset> [--tile 3] [--anims] [--yaw DEG]`. The script runs Godot under `timeout 180`.
- A tile: `--tile 3` gives `_top` and `_seam` shots.

## Route results that set the config

| Class | Winner | Second | Never |
|---|---|---|---|
| Prop | Tripo H3.1 (5/5 bell) | Meshy 7 image (4/4) | Text-to-3D (off-design) |
| Humanoid | Tripo H3.1 + Meshy rig + merge | Tripo + Opus rig | Meshy text-to-3D (off-model) |
| Creature | Tripo H3.1 (unproven) + Opus rig | Meshy 7 image + Opus rig | Meshy quadruped rig (0 of 3) |
| Modular | Opus bpy + Meshy retexture + re-snap | Opus bpy alone | Any image-to-3D or text-to-3D (0 of 7) |

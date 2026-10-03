# asset-forge gotchas

Each item is a real failure, with its source. Add each new failure here. BAKEOFF n = finding n of the asset pipeline bake-off (Tripo, Meshy, Hunyuan3D and Blender on the same assets, Sep 2026). Keep your own bake-off notes in `bakeoff_dir`.

## Tripo and Meshy output

1. **Tripo output faces +X in a 1 m box.** Turn it -90 degrees about Z and rescale to the target height. glTF imports use quaternions, so `rotation_euler` does nothing. Rotate the mesh data (BAKEOFF 5). A `validate.txt` width X of exactly 1.000 shows that the clean step did not run.
2. **Meshy retexture re-centres the model.** The dock origin moved from the deck top to the middle of the posts. Re-snap after each retexture (BAKEOFF 7).
3. **Meshy rig output looks bleached.** The GLB wires the base colour to emission, sets specular x2 and leaves metallic at 1.0. Reset the material (BAKEOFF 1).
4. **Meshy rigs ship the armature at scale 0.01.** Godot then gets a 9 mm AABB, so the model looks tiny and culls wrong. Bake the scale (BAKEOFF 2).
5. **Meshy pose estimation failed at 0.9 m and passed at 1.7 m.** Retry once at 1.7 m. Then use the Opus rig. A 422 costs 0 (BAKEOFF 4).
6. **Each Meshy clip is a full-mesh GLB.** Merge the actions onto one rig and clear the `clip0` NLA track (BAKEOFF 3).
7. **The Meshy quadruped rig failed 3 of 3.** Its clip library holds biped clips only. Use the Opus Blender rig for creatures (BAKEOFF Test C).
8. **Generated tiles are not tiles.** Every generated dock put the deck inside its posts. All 7 generated docks failed the 3 x 3 grid check (BAKEOFF 6). Build modular geometry in code; use the generator for the texture only.
9. **A bad concept wastes a paid conversion** (reported by other AI game devs). Read the PNG, not a caption or a file name.
10. **Text-to-3D drifts off-model without a concept.** The companion lost its brass head, and the bell became a diving helmet (BAKEOFF 8).
11. **A quote is not the cost.** Hunyuan3D v3 cost 19 credits against a 15 quote (BAKEOFF 10). Log the real cost from the job result.
12. **Multi-view concepts disagree.** The dock views had planks in different directions; the Tripo multiview gave no gain on the companion (BAKEOFF 9). Multi-view stays a per-class flag in config.

12a. **The Meshy rig drops the PBR maps.** The image-to-3D GLB has metallic-roughness and normal maps. The rig GLB keeps the UVs and the base colour only, and the merge then sets a flat paint material. Wire the source maps back on with a small Blender script (Crush Depth diver, Oct 2026).
12b. **A humanoid multi-view passed the rig.** Meshy multi-image (front, side, back crops of 1 A-pose turnaround) gave a clean squat diver, and the Meshy rig passed first try (Crush Depth diver, n=1). Crop each view to its own image; a full sheet carries the next view's hand.

## Godot and checks

13. **Trimesh collision on an imported mesh dropped the game under 1 FPS** (reported by another AI game dev). Use a box, sphere or capsule from the bounds.
14. **`validate.py` cannot see the model direction, emission, metallic or armature scale.** Use the front render for the direction. Use the probe for the material and scale.
15. **`render.sh` is a preview scene.** A render is not in-game proof. The proof is a player-camera shot through the game's bridge.
16. **The editor agent and 2 render workers make 3 Godot instances.** The cap is `max_godot_instances` (6), from a measurement on a 32 GB machine at about 220 MB for each headless game. An older cap of 2 was copied from a research anecdote. Measure on your own machine. Count with `pgrep -x godot` first.
17. **`render.sh` already wraps Godot in `timeout 180`.** `godot_timeout_s` (300) is the outer bound for a direct `godot` call. Stock macOS has no `timeout`; GNU timeout from Homebrew is `/opt/homebrew/bin/timeout`.
18. **Tile seams hide in 3/4 shots.** The default shots hid the gaps. `render.sh --tile N` saves `_top` and `_seam` shots (BAKEOFF 11). The pass or fail still comes from numbers, not from the PNG.

## Credits and ledger

19. **Paid `mcp__meshy__*` tools carry a confirm gate that stalls a worker.** `meshy_check_balance` is free and safe.
20. **`meshy.py` writes its own ledger row in its own folder.** Copy the row once to `docs/ledger.tsv`. The `agent` column holds the pipeline arg. `meshy.py` has no dry-run.
21. **The ledger `ts` is HH:MM with no date.** Rows from 2 days look the same. Put the date in `note`.
22. **A per-call ask stalls a subagent.** Workers never ask the user.
23. **A low balance pushed the route to Meshy.** An older version of this skill saw a low Higgsfield balance in the ledger. It then made Meshy the default, although Tripo won the bake-off. Pick the route by quality, never by a balance, and do not talk about credits or cost.
24. **Ask for a top-up only after a refusal.** Ask the user to top up a provider only when that provider refuses a job for credits. A low ledger balance is not a refusal.
25. **Tripo won on 2 assets only** (bell and companion, n=2). A later bake-off changes `route` in config, not the prose.

## Crush Depth build (Sep 2026)

Source: the build of Crush Depth (a submarine game), its play-test notes and a field test of this skill.

26. **Coded visuals failed where generated assets passed.** The Tripo sub hull, the crab and the fish looked good in play-test. The procedural sea floor, rock blobs, flat kelp cards and a coded cockpit were judged poor in shape and texture. Every visible element gets a route here: `surface` for the ground, `prop` for rocks and plants, `interior` for the cockpit.
27. **A credit floor stopped a worker.** An older version of this skill had a floor check. Higgsfield was under the floor, every route needed `hf_concept`, and a worker may not ask the user. The run made the concepts with gemini-image. Credits have no floor. A refusal takes the next route and asks the user for a top-up in 1 line.
28. **An art bar of 7 did not match the user.** 3 props shipped at 7.1 to 7.4, and the ocean critic said 7.0. The user still judged the world as basic. There is no art bar. look-critic gives an A/B call and a gap list, and the user decides after they see the render next to the key.
29. **File checks passed a model that was wrong in the level.** The hull sat 27 degrees off the forward axis, so the chase camera looked off centre. A merge attached a second hull, so the sub showed 2 lamps. The lamp light sat outside its lantern. Do the wired-and-placed check (step 24).
30. **A fused propeller could not spin.** The Tripo hull held the propeller, the cage and the hull in 1 mesh. A vehicle route splits each moving part and each lamp into its own mesh.
31. **Generated textures on code shapes still failed.** Cockpit v1 built its brow, roof, dashboard and dials from primitive shapes in code, with generated brass textures. It still read as code. The interior route takes its shape from a generated model.
32. **A cabin lantern rendered white and ghostly.** Its material was pale and see-through, and it was not tied to the lamp. Give the brass and the glass their own materials, and drive the glass glow from the lamp state.
33. **The lamp light sat at a guessed point.** The hull held the lantern in 1 mesh, so the light hung at a hand-set spot with a fake bulb sphere. The user expected the lantern split without a request. The split script cut the lantern, glass, claw, jaw, hatch and porthole glass out, each with its origin at its pivot.
34. **Coded bubbles and blasts failed.** The first bubbles and torpedo blasts were sphere meshes, and both were rejected in play-test. Use the `vfx` route: generated flipbooks or sprites, soft particles, and the 5-part underwater explosion.

## Not built yet

These files are not in this kit. The "Fallbacks" section of SKILL.md says what to do.

- `tile_check.py` (footprint, grid pitch, max overhang, posts per corner). Not in `bakeoff_shared_dir`.
- The material and scale probe that writes `probe.txt`. Not in `bakeoff_shared_dir`.
- A picked style key at `style_key_path`, until you set one.
- `assets/_src/` and `assets/_staging/`. Make them on first use.
- `work/manager/godot-slots.tsv`, the shared Godot slot file for the kit skills. game-manager owns its format.
- The look-critic `score.md` format. asset-forge reads the `pick` and `gap` lines only.
- The bridge player-camera shot for a new asset. The next step after a pass, not part of this skill.

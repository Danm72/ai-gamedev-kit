# look-critic gotchas

Each gotcha is a real failure with its source. Add each new failure here. Sources: the first two games the skill ran on (a survival RPG proof of concept, called "the POC" below, and Crush Depth), and public dev reports.

## The bar

1. **Lenient judges passed a look that the user did not like.** Judges passed the POC v3 look on 5, 6 and 5. The user found it far too grim. [POC handover]
2. **An absolute score of 7.0 disagreed with the user (Crush Depth).** The critic went 6.4, 6.8, 7.0, and the session told the user "ships at 7". The user called the world basic. The visual criteria alone sat at 5.0, and 3 measured criteria lifted the mean. So the skill has no absolute score and no ship bar. The critic gives an A/B call (closer to the key) and a gap list. The user is the ship gate.
3. **Critics stayed low against a real AAA frame.** The Claude of Duty critic scores stayed at 3.59-5.05. An absolute number does not track the user's taste. Compare against the game's own key image, A against B.
4. **A small hand-picked calibration set is not useful.** 5 to 10 screenshots are not generic enough to tune a score. Do not build a calibration set. The user's look at each frame is the calibration.
5. **Hard-wired key images belonged to one game.** The POC had keys E, F and G; Crush Depth has 4 keys, 1 for each view, in its art bible. A question about E, F and G did not apply. Take the key for the view from the game's art bible. [field test]

## Camera and shots

6. **Overhead shots hid flat islands.** Islands looked correct from overhead and were flat "pancakes" from the player camera (RUSuper). An overhead shot (for example at distance 150) is never proof.
7. **The player zooms the camera, for example from 1.8 m to 30 m.** A shot after a zoom is not a player shot. Before each capture, reset the camera to its default follow distance (`shoulder_dist_m` in config). [POC camera rig]
8. **A close-up passed and failed at play distance** (Extension-Mammoth252). Capture at the follow distance only.
9. **A judge scored a stale frame** (The Long Silence). Staleness comes from `head_sha`, not from the clock.

## The critic

10. **A vision model says "match" when it is wrong, and it cannot count** (Kossarev, plopsDOTio). Measured criteria come from game state in `measures.tsv`.
11. **Shot file names told the critic which shot was new.** The critic gets `A.png` and `B.png` only. The brief has no builder notes.
12. **An A/B call in one order has a position bias.** Run the critic twice, with A and B swapped.
13. **A reused critic remembers the last A/B order.** Start a new critic subagent for each run.
14. **A critic can compute the mean wrong.** A critic wrote 7.1 where its own lines gave 6.3. The builder ignores every number that the critic writes. The verdict comes from the A/B picks in `ab-key.txt`.

## Cost and loops

15. **Critic loops use a large part of the plan.** One public report had a critic loop use 40-50% of a weekly plan limit (nospoon99). Another used 3 five-hour windows (BoneShaman). Stop at `max_critic_runs_per_part`.
16. **Fix loops repeat the same failed idea in a poisoned chat** (Crunchfest3, Kossarev). After `max_tries` fails with one `approach_id`, revert and start a fresh builder.
17. **"20 prompts to move one lighthouse"** (RUSuper). A tunable gap goes to a labelled control in the in-game editor, not to a prompt loop.

## Paths

18. **A run read "this folder" as the game repo and skipped the skill files.** It did not read `gotchas.md` or `formats.md` (eval probe). Read the skill files by the full path on the "Base directory for this skill" line.

## Often missing

Check for these parts in a new repo. Do not build them in this skill. When one does not exist, say so on the Gap line.

- `capture_script` (default `tools/look/capture.sh`): the player-camera capture that appends `shots.tsv` rows. Check that the bridge screenshot can write these rows.
- The `measures.tsv` script: it reads `get_state` and an object list and writes one score per measured criterion.
- The shared slot file (`godot_slots_file`). game-manager owns its format. Until it exists, use `pgrep -fl godot` only.
- Editor controls for grade, fog, light and brightness. Without them, the step 18 hand-off has no control to point at. Name the value and the target, and say that the control does not exist yet.
- The critic model name in `critic_model`. It needs a real model id and a reason line.

## Crush Depth

Source: the Crush Depth build and the user's play-test notes.

19. **Coded visuals failed the hardest.** A procedural sea floor, rock blobs, flat kelp cards and a flat painted cockpit overlay were the parts that the user rejected. The generated sub mesh was the part the user liked. A gap in a visible element gets a generated asset through asset-forge, not a code fix.
20. **Hand-rolled light shaders looked bad.** The user rejected the hand-made lighting, shaders and god rays. A light gap uses the engine's rendering features (tonemap, volumetric fog, GI, SSAO, glow, projected caustics). God rays only from real volumetric light, never from flat shaft cards.
21. **A clipped-white frame passed a measured criterion.** A deep-water frame had 9 percent of its pixels above 240. Put a clipped-white fact in the gap list.
22. **The proof camera was fixed to `follow`.** Crush Depth plays in a chase view. Read `camera_mode` from the repo override.
23. **The user cannot see inline images in the CLI.** Open the shot and the key for the user, or publish them on a page.
24. **The world stayed "flat" after 4 rounds.** The same complaint came back each round: a flat world and a flat sea surface. Each round changed code, light values and dressing. No round asked if the painted key was a frame that the engine could make. After the third gap list with the same complaint, stop. Name the root assumption and get a second opinion from a different model. Pick a reference frame from a real shipped game in a similar engine. The key image is a target, not an in-engine frame.

## Capture and trailer

Source: the user's notes on the Crush Depth teaser, v1 to v4.

25. **Only the dark, deep shots worked.** The shots of sand and fog showed the weak parts. Film the parts that already look good. Leave out the parts that do not.
26. **Keep it short.** A 60 to 90 second showcase was cut to 30 s and made more dramatic. Show 1 shot for each subject; two shots of jellyfish was one too many.
27. **Creatures must look menacing.** A predator was not scary enough. A fish that followed the lamp behaved like a pet dog. A shot that shows a creature as a pet is cut.
28. **The monster moves the whole time.** A monster that sat still while the camera shook read as dead. Camera shake is not motion. The body glides, turns or surges in every frame.
29. **Frame tight, with a long lens, and start close.** A wide shot with the creature far off made its animation look listless. Use a field of view of about 30 to 40 degrees. The creature is already close in the first frame.
30. **Super dark, barely visible.** The scene was too bright. Only the lamp cone and the creature's own lights show.
31. **Render from a clean tree.** Render each cut from a clean worktree at main HEAD, never from a tree in the middle of a merge. Keep the capture scripts in the repo (for example `tools/capture/`) and start Godot through `tools/godot_bg.sh`. Keep each old cut as `-v<n>` beside the new one. Open the video folder for the user when the cut lands.
32. **4 cuts and still not good.** The trailer follows the same stop rule as the world (gotcha 24). After the third cut with the same complaint, ask the user 1 diagnostic question before another render.

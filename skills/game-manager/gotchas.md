# game-manager gotchas

Each entry is a real failure and its source. Codes: numbers such as "05" and "02" are rows in a research catalogue of public AI game-dev reports, "R" is the u/RUSuper write-up on Reddit, "W" is a catalogue workflow. Names in brackets are the public authors. Add each new failure here.

## Manager scope

1. **The manager did the work itself.** A manager worked for an hour on the code and wrote no brief (05, ribatonline). The manager edits only briefs, STATE.md and LAUNCH.md, plus the merge. A one-line typo also goes into a `fix-N` brief.
2. **Workers said "done" when the work was not done** (02, claudex). A "done" is "review" until the manager's own checks pass.
3. **A worker-written smoke result is a self-report.** The manager runs `smoke_cmd` itself and uses only `manager-smoke.out`.
4. **Two agents edited one file and broke the Esc menu** (R). Each lane has owned globs. Reject any file outside them, untracked files too.
5. **SendMessage to a Workflow lane agent id started a duplicate agent** in the same worktree (from a real run). Read the report file. For a fix, start a fresh worker with a `fix-N` brief.
6. **A planner dropped the top epic with no warning** (04, BMAD). Map every item of the ask to a lane or to the queue, and name each item.
7. **The manager session compacted and lost track of the lanes** (RUSuper). Read STATE.md first in each turn.

## Team size

8. **Big teams made nothing.** 49 agents made no Flappy Bird code. 15 agents were "mostly ridiculous" (Poggler_). Keep the team small and give the reason.
9. **A fixed subagent cap overrode the user.** The user can lift any cap. Never refuse their number without a reason. Valid reasons: Godot slots, coupled lanes, one file family. Never state "max 3" as a rule.
10. **One agent per item burned 3 five-hour windows** (BoneShaman, 02). Parallel art agents drift in style (W20). Batch props by family in one lane with an item queue.
11. **A folder split failed on coupled visuals** (04, Claude of Duty). Light, sky, fog, water and the grade need one owner.

## Godot and the machine

12. **A test run wrote into a shared profile.** It made 1,330 files and wiped user data (04, P(Doom)1). Each run gets `--data-dir <tmp>`.
13. **Too many Godot instances rebooted a Mac** (R, Ziwen). The cap is `max_godot_instances` (6) across all lanes, from a measurement of one machine (gotcha 41). Measure yours. The editor agent and the user's own game count.
14. **A godot call with no timeout hung at 0% CPU on a macOS dialog** (W11). Every call uses `timeout`. Exit 124 is a fail. Stock macOS has no `timeout`; install GNU coreutils with Homebrew.
15. **An out-of-memory kill looked like a test failure** (W18). Find any kill or signal 9 in the log before a send-back.
16. **A new `class_name` gave "Could not find type" in a fresh worktree** (03, 04). Run `godot --headless --import` once after a new `class_name`.

## Files and proofs

17. **`work/` is gitignored, so a report in a worktree is not in main.** Workers write REPORT.md and proofs under `lane_root`.
18. **`cp` and `git checkout` reset mtimes.** Proof freshness comes from the brief version in the file name and the manifest time, never from the mtime.
19. **Workers sat idle and nobody started them** (R; crewmates, 02). Start each queued lane when a slot frees. Log the start in STATE.md.

## Escalation

20. **Failed fixes went round in a loop** (W23). Count fails per check id. Stop the lane at 3 fails of one check, or after 2 rounds with no new check passed. Give the user 1 decision and write no fourth fix brief.

## Evals

These apply when you write eval cases for this skill.

21. **A regex that bans a word fails a correct refusal that quotes the word.** Grade actions with `tool_used`. Grade text with phrase-level patterns, and scope them to the chat block above `---`.
22. **A `tool_used` pattern on the whole tool input gave false fails.** A brief lists `scripts/world.gd` as an owned glob, so `scripts/` matched a correct Write of `work/water/BRIEF.md`. Match on the `file_path` key only.
23. **The eval sandbox cannot read outside the skill folder.** Put all fixtures in `evals/fixtures/`. Fixture paths are relative, never absolute.
24. **An eval sandbox can refuse Bash.** Step 12 reads `.git/HEAD` with Read, not with `git rev-parse`.
25. **A `max: 0` grader passes when the sandbox blocks the tool.** A case that checks "no Write" or "no SendMessage" must open those tools in its `allowed_tools`, else it passes for the wrong reason.
26. **The judge failed correct replies.** The harness counted a vote as PASS only when the reply had PASS and no FAIL. The rubrics asked for a reason, so the judge wrote FAIL words. End each rubric with "Reply with one word only: PASS or FAIL."
27. **The skill did not read its support files in the eval.** The case prompt said "Use only the files in this folder", so the child did not read them. The child can read the skill's base directory. Read the support files there. A copy in the fixture leaks into the without arm.

## Optional parts

A repo may not have these parts. The skill tells what to do when a part is absent. Evals use fixtures in their place.

- `tools/godot_bg.sh` and `tools/capture/`: without them, start Godot as before and say in 1 line that the focus fix is absent.
- `shots/manifest.tsv`: with no manifest, check `proof` fails with "no manifest".
- `work/manager/godot-slots.tsv`: the manager makes it with the header row only, then counts live processes with `pgrep -fl godot`.
- `work/<lane>/LOOK.md`: look-critic writes it. A visual lane stays `review-visual` until it exists.
- Post-merge smoke on main, the slot lock under real load and live worker starts are hard to cover with a fixture case. Test them in a live run.

## A real multi-lane build (Crush Depth)

Source: a session that built a submarine game with parallel lanes, its audit and the user's play-test notes.

28. **Lanes split by system made the coded parts fail.** The asset lane made the sub, the creatures and the props, and they looked good. A code lane made the sea floor, the rocks, the kelp cards, the light and a flat 2D cockpit overlay. The coded elements failed the hardest. Split lanes by what the player sees. Each visible element names its asset tool in the brief.
29. **Hand-rolled light shaders looked bad.** Flat shaft cards for god rays looked worse. Use the engine's rendering features (tonemap, volumetric fog, GI, SSAO, glow, projected caustics). God rays only as real volumetric light, soft and moving with the surface.
30. **Bridge tests passed while play was broken.** Every test drove the game with teleports and direct calls. In play, turning did not work and the sub spun out of control. A playable lane needs a real-input test (check h) and a hand play-through (step 18b).
31. **Merged content was not in the level.** The creatures merged, but the placement step never ran, so none spawned. 2 hull models overlapped, so the sub had 2 lamps. The hull model sat 27 degrees off the forward axis, so the chase camera looked off centre. Do the `wired` check after each merge (step 18a).
32. **The sub lane never started.** The manager wrote "QUEUED LANE: key=sub" in prose. The workflow script started `plan.lanes` once, so nothing drained the queue, and the merge went ahead without the sub. A queued lane is a row, and "done" waits for it (step 9).
33. **Systems first, look last.** big-feature scoped a loop with 4 props and no hero art. The build lanes started before the user saw the key images. The first in-game frame came after 4 asks to see progress. Show the user 1 frame of the target view before the build lanes start (step 9a).
34. **Two workflows corrupted each other.** A hillclimb ran next to the game build. Its eval swapped a `SKILL.md` that the build read through a symlink, and its processes made the Godot slot count wrong. Run 1 workflow at a time on a game repo (hard rule 11).
35. **The critic's number misled the user.** The look-critic gave 7.0, "ships at 7". The user judged the world basic. The visual criteria alone sat at 5.0. There is no ship score. The user looks at the frame (hard rule 13).
36. **Stop meant stop all.** The user asked to stop future phases and merge. The session stopped round 2 but left the hillclimb on. Stop every workflow that touches the game (hard rule 12).
37. **The user played round 1 while round 2 was close to a merge, and fixes waited behind large jobs.** A fix that the main session merged alone reached the user first. Merge each passed lane at once and split small fixes out. Relaunch the game after each merge (steps 18 and 18c).
38. **A CLI user cannot see inline images.** Open the PNG for them or publish it on a page.
39. **Code shapes with generated textures still failed.** The first 3D cockpit built its brow, roof, dashboard and dials from primitive shapes in code. Only the brass textures were generated. The user rejected it. The shape of a visible element comes from a generated model, not only its texture.
40. **Fused meshes blocked light and motion.** The hull held the propeller, the lantern, the claw, the hatch and the porthole glass in 1 mesh. The lamp sat at a guessed point with a fake bulb. Split each part that moves or lights early, with its pivot (asset-forge step for vehicles).
41. **A Godot cap of 2 was a copied anecdote.** It came from a research write-up about a Mac that rebooted. The real machine had 32 GB, and each game used about 220 MB. The cap went to 6. Measure the machine before you copy a limit.
42. **A re-signed Godot copy put Gatekeeper dialogs on the user's screen.** The copy was blocked, and the user had to click through System Settings. The fix that worked is a wrapper script (`tools/godot_bg.sh`) on the stock app. Its first version blocked focus for good, so the user could not focus the game window at all. Never take focus for good (hard rule 15).
43. **The world stayed "flat" after 4 rounds.** Each round changed code and light values. Nobody asked if the painted key was a frame that Godot could make. Stop after the third round of the same complaint (step 20a).
44. **The user waited on lanes that were almost done.** The world lane merged its asset sets, and a snapshot of its work in progress went to main. The user could then play it (step 18c).
45. **Design docs sat outside the game repo.** Workers could not find the art bible. Put the design docs in the game repo (a symlink works). In Godot, a `.gdignore` in the docs folder stops Godot from importing them.
46. **Video renders need a clean tree.** A capture from a worktree in the middle of a merge can mix 2 builds. Render from a clean worktree at main HEAD (step 18d).


## Workflow lane agents: never message, never stop by id

- A lane agent inside a Workflow asked the manager a question. The manager replied with SendMessage. That resumed a SECOND copy of the agent (same id) next to the workflow's own run, and both wrote into one worktree. The diver and surface lanes broke with 2 writers each.
- Then TaskStop on that agent id killed the workflow's own builder, not only the copy.
- Fix: answer a lane question by stopping the workflow, editing the brief in the script, and resuming with resumeFromRunId. Tell lanes in COMMON: "take the default and note it in REPORT; do not wait for an answer".
- Workflow agents also read the user's newest chat message from context and treated it as the new scope (the user only asked "is the video ready", so they built nothing). Every lane, check and merge prompt needs a STANDING AUTHORISATION line: the brief is the task, and the user's chat goes to the manager.

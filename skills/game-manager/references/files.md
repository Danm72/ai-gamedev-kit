# game-manager file formats

This file holds the format of each file that the manager reads or writes. Other kit skills use the same `godot-slots.tsv` and `shots/manifest.tsv` formats.

## work/manager/STATE.md

STATE.md is the manager's memory. Read it first in each turn.

```markdown
# Manager state
updated: 2026-09-30T14:10:00Z

## Foreign lanes
| lane | owner | globs |
|---|---|---|
| editor | in-game editor agent (not started by the manager); example row, copy the globs from `foreign_lanes` | scripts/editor*, data/placements.json |

## Lanes
| lane | status | runner | agent_id | worktree | brief_version | round |
|---|---|---|---|---|---|---|
| terrain | review | agent | - | .claude/worktrees/terrain | 1 | 1 |

## Fails per check
| lane | check | fails | last |
|---|---|---|---|
| terrain | smoke | 1 | build_queue FAIL |

## Queue
- props-fence: waits for a Godot slot

## Decisions for the user
- (one line each; the reply asks only the first)

## Log
- 2026-09-30T14:10Z terrain: fix-1 brief written, fresh worker not-started (no git)
```

Status values: `queued`, `not-started`, `running`, `review`, `review-visual`, `ready-to-merge`, `merged`, `sent-back`, `blocked`, `escalated`.

## work/manager/LAUNCH.md

```markdown
| lane | worktree | runner | model | brief |
|---|---|---|---|---|
| terrain | .claude/worktrees/terrain | agent | sonnet | work/terrain/BRIEF.md |
```

Runner is `workflow` when the user says "ultracode", else `agent`.

## work/<lane>/BRIEF.md

```markdown
# Brief: <lane>
written: 2026-09-30T13:00:00Z
version: 1
lane_root: /abs/path/to/main/work

## Goal
<one system or one file family, in plain words>

## Owned globs
- scripts/terrain.gd
- scripts/shaders/terrain.gdshader

## Items
1. <each item of the user's ask that this lane owns>

## Done when
- <a number: for example "grass hue 60-80 deg, rock value 0.45-0.6, smoke 18 of 18">

## Reference image
refs/key_F.png

## Proof
Empty shots/<lane>/ first. Save terrain-v1-*.png from the follow camera. Add one row per proof to shots/manifest.tsv with camera follow.

## Forbidden
- git add -A or git add . (commit by file name)
- edits outside the owned globs, untracked files too
- any change to a line that starts with USER:
- any Kenney, KayKit, Quaternius, Synty or low-poly kit asset, not even as a placeholder
- any post, email or message outside the team
- any wait over 5 s
- any new key binding (every UI action is a labelled button)

## Safety
- Run godot --headless --import once after a new class_name.
- Pass --data-dir <tmp> and a unique --port to each game run.
- Take a Godot slot in work/manager/godot-slots.tsv before any Godot run.
- Wrap each godot call in timeout 300.

## Report
Write <lane_root>/<lane>/REPORT.md, max 200 words, text only:
status, files changed, done-when numbers, proof paths, camera per proof, open issues.

## fix-1
failed check: smoke (build_queue)
earlier fixes: none
```

## work/<lane>/REPORT.md

```markdown
status: done | blocked
files changed: scripts/terrain.gd
done-when: grass hue 72; rock value 0.52; smoke 18 of 18
proofs: shots/terrain/terrain-v1-01.png (camera follow)
open issues: none
```

## Check files (written by the manager in a live run)

| File | Source |
|---|---|
| `work/<lane>/diff-names.txt` | `git diff --name-only main...<lane-branch>` |
| `work/<lane>/untracked.txt` | `git status --porcelain` lines that start with `??` |
| `work/<lane>/manager-smoke.out` | `timeout 300 bash tests/smoke.sh` in the lane worktree |
| `work/<lane>/design.diff` | `git diff main...<lane-branch> -- docs/` |
| `work/<lane>/worker-smoke.out` | written by the worker; never used for a check |

## work/manager/godot-slots.tsv

Tab separated. One row per live Godot process. Max `max_godot_instances` rows. The user's own game and any editor agent each take a row.

```
lane	pid	started
user-run	41207	2026-09-30T12:31:00Z
```

Take a slot: count the rows, compare with `max_godot_instances`, then append a row. Free a slot: remove the row when the process ends. Check `pgrep -fl godot` against the rows before a start.

## shots/manifest.tsv

Tab separated. One row per proof image. The time column is the capture time, not the file mtime.

```
path	lane	brief_version	camera	time
shots/terrain/terrain-v1-01.png	terrain	1	follow	2026-09-30T13:40:00Z
```

## work/<lane>/LOOK.md (written by look-critic)

```markdown
verdict: CLOSER | NOT CLOSER
key: refs/key_F.png
gap: <largest gap to the key first>
```

The verdict rule and the full format are in look-critic `references/formats.md`. There is no score.

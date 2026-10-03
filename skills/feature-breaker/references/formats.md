# feature-breaker file formats

The skill writes each file in this form. Keep the headings as written, because the eval graders look for them.

## breaker-brief.md

The brief is the only input that the breaker agent gets. Write it to `docs/features/<slug>/breaker-brief.md` and print it.

```markdown
# Breaker brief: <slug> (pass <n>)

You did not build this feature. Try to break it. Find the inputs, states and
orders of events that make the done-when false.

## Done when
<copy the done-when lines from FEATURE.md, word for word>

## Diff
<the full build.diff>

## Test logs
<test-before.log, then test-after.log, word for word>

## Rules
- Rank each finding Must, Should, Could or Defer.
- Must: the done-when is false, the game crashes, data is lost, or a value turns NaN or inf.
- Should: a done-when line has no test, or a real player hits the bug in normal play.
- Could: a tuning number sits in code, or the code is hard to change.
- Defer: outside the ask.
- Give each finding a `scripts/<file>.gd:<line>` from the diff, or a repro in steps.
- Do not fix anything. Write only the report.
```

Never put these in the brief: the builder's report (`build-report.md`), the builder's chat, commit messages that make a claim, or your own opinion of the build.

## breaker.md

```markdown
# Breaker report: <slug> (pass <n>)

Brief: done-when, build.diff, test-before.log, test-after.log. No builder report.

## Must

- M1 `scripts/<file>.gd:<line>` <what breaks>. Repro: <steps>. Status: open.

## Should

- S1 ...

## Could

- C1 ...

## Defer

- D1 ...
```

- Every rank heading is present, also when it is empty. Write `(none)` under an empty heading.
- A Must gets `Status: open` or `Status: fixed in <commit>, guard <test name>`.
- After a Must fix, add the 5 whys line: `Why: <symptom> <- <cause 1> <- <cause 2> <- <root cause>. Guard: <test or gate for the bug class>.`

## FEATURE.md sections that this skill changes

The skill changes only 2 sections of FEATURE.md. It never changes a `USER:` line.

```markdown
Stage: breaking

## Failed fixes

- Try 1 (commit <hash>): <what changed>. <what failed, with the test name and the value>.
- Try 2 (commit <hash>): ...
```

`Stage:` values are plan, picked, building, breaking and done. Set `done` only when no Must is open.

## data/balance/<system>.json

A tuning proposal. One file for each system. The editor shows each key as a knob.

```json
{
  "_source": "feature-breaker, <slug>, <date>",
  "damage": {"value": 3.5, "min": 0.5, "max": 20, "step": 0.5, "unit": "hp", "was": "scripts/boar.gd:11"},
  "flee_below_hp": {"value": 12, "min": 0, "max": 30, "step": 1, "unit": "hp", "was": "scripts/boar.gd:78"}
}
```

- `was` gives the old code line, so the code change can read the value from the file.
- Never write `data/placements.json` or `data/hud_layout.json`. The in-game editor owns them.

## work/manager/godot-slots.tsv

The shared slot file for the kit skills that start Godot. One row for each Godot process that a lane started. Tabs between columns.

```
lane	pid	started
user-run-sh	48211	2026-09-30T13:02:11
editor-ui	48530	2026-09-30T13:40:57
```

- Add a row before a Godot start. Remove the row when the process stops.
- `pgrep -fl godot` is the truth. The file only names the owner of each process. A row with no live pid is stale: remove it.

## Test-before and test-after logs

The build writes 2 logs to the feature folder. The first line names the commit.

```
# commit <hash> (<branch>)
$ <command>
PASS|FAIL <test name>  (<value>)
exit <code>
```

- `test-before.log` runs the new tests on the base commit (the `Base commit:` line in FEATURE.md).
- `test-after.log` runs them on the build branch.

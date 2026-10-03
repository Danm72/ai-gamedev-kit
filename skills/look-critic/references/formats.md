# look-critic file formats

All files sit in `work/look/<part>/` in the game repo, except `refs/`, `state.md` and `shots/`. Fields use `|` except in `shots.tsv`, which uses tabs.

## criteria.md

One line per criterion, 8-12 lines, after a title line:

```
C1|visual|warm golden sunlight from a low sun, long soft shadows
C7|measured|cottage eaves 1.5-2.2x player height
```

`visual` lines go to the critic. `measured` lines never go to the critic.

## measures.tsv

A script writes it from game state (`get_state`, `list_objects`). One line per measured criterion:

```
criterion|measure|value|target|in
C7|eave_height_ratio|1.9|1.5-2.2|yes
```

`in` is `yes` or `no` against the target. A `no` line goes into the gap list. The critic never sees this file.

## shots.tsv

Tab-separated. Header: `file	camera	head_sha	utc`.

- `camera` is `follow dist=2.6` for a player-camera shot. Any other camera (`overhead dist=150`, `editor`, `focus`) is not proof.
- `head_sha` is the commit that the shot shows.

## state.md

Holds `head_sha: <sha>`, the commit of the game that the user plays now. A shot whose `head_sha` differs is stale.

## ab-key.txt

Only the builder reads it.

```
run|A|B
1|shots/review/dock/0-after.png|shots/review/dock/1-after.png
2|shots/review/dock/1-after.png|shots/review/dock/0-after.png
new|shots/review/dock/1-after.png
```

The `new` line names the shot under test. A pick "picks new" when the picked letter maps to the `new` file in that run.

## critic/run-<n>/score.md

The critic writes only these lines:

```
C1|B|B has the warm low sun of the key; A is flat haze
C2|same|neither shot has the rippled sand of the key
pick|B
gap|sea floor is a flat plane: the key has rippled sand with caustics
gap|deep frame is blown-out white: the key keeps the lamp pool dark at the edge
```

`Cn` takes `A`, `B` or `same`: which shot is closer to the key on that criterion. `gap` lines list the gaps of the picked shot to the key, the largest first. Ignore any other line, for example an `overall|7.1` line or a score out of 10. No number from the critic is a verdict.

## critic/runs.tsv

The builder writes one line when a critic run returns: `run|model|tokens`.

## failed-fix.log

One line per failed try. `try` counts up across the part, not per approach.

```
try|approach_id|change|verdict|top gap|tokens
4|fog-density|fog density 0.018 -> 0.009|NOT CLOSER|fog density too high: far hills gone|41200
```

`tokens` is the sum of the critic runs for that try, from `critic/runs.tsv`.

## judges-*.md

Older judge files (for example `judges-v3.md`). They hold absolute scores out of 10. Read their `gap|<text>` lines only. A judge score never ships a look, and a pass in a judge file is not a ship.

## Verdict rule

1. `CLOSER`: every critic run picks the new shot, as `ab-key.txt` shows.
2. `NOT CLOSER`: any run picks the old shot.
3. `NEED INPUT`: no key for the view, no proof shot, or no critic return.
4. There is no overall score, no floor and no ship bar. The user looks at the shot next to the key and decides if the look ships.

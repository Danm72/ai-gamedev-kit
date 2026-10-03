---
name: steam-deck
description: >
  Use when the user wants a Godot or Unity game built, installed or tested on their Steam Deck: "put it on the deck", "deploy to steam deck", "test on the deck", "deck screenshot", "deck fps", "why is it slow on the deck", "add to steam library", "does the controller work on the deck". Wraps the repo deck tools (deploy, shortcut, template, profile) with a Deck lock and a separate test install. Not for general perf work on the dev machine. Not for art or looks (look-critic, asset-forge).
---

# steam-deck

Build a game for Linux and copy it to the Steam Deck over Wi-Fi. Run it as a non-Steam game. Read fps, screenshots and controller state from the Deck over ssh. The repo scripts do the work. This skill adds the lock, the order of steps and the checks.

## Assumes

The deck tools folder is NOT in this kit. Your game repo must have it (default `tools/deck/`, set in `config.json`). Without it, read `references/new-game.md` first. The flows below break without these parts:

1. `tools/deck/deploy.sh`: exports the Linux build to `build_dir`, copies it to the Deck with `rsync` over ssh, and adds the non-Steam shortcut. Flags: `--launch`, `--shot`, `--no-build`, `--sync`, `--no-sync`, `--perf`, `--install-dir`, `--shortcut-name`. It exits 0 only after a good deploy. Built and tested for a Godot export; a Unity repo needs its own build step in the script.
2. `tools/deck/steam_shortcut.py`: reads and writes `shortcuts.vdf` on the Deck (computes the appid, backs up the file first).
3. `tools/deck/steam_input.py`: pins the Steam Input layout "Gamepad" for the shortcut.
4. `tools/deck/get_template.py <version>`: downloads the Godot Linux release export template (Godot only).
5. `tools/deck/profile.py`: runs on the Deck with the Python stdlib only. It talks to the game bridge on 127.0.0.1 and prints 1 JSON line with `median_fps`, `p5_fps`, `window`, `visible_prims` and `shadow_prims`. Flags: `--poses`, `--seconds`, `--layers`, `--breakdown`, `--quality`, `--set`.
6. A game bridge in the build (this kit's `bridge/`) with the commands `fps`, `quality`, `get_state` (with `joypads` and `input_device`) and `editor_teleport` (the `profile.py` poses use it).
7. A Steam Deck in Gaming Mode on the same network, with ssh turned on and key login set up. The config keys `deck_host`, `deck_user`, `ssh_key` and the install dirs must hold your values.
8. A Mac or Linux dev machine with `ssh`, `scp`, `rsync` and an image resize tool (`sips` on macOS; `resize_cmd` in config).

## Before you start

The skill folder is the path on the "Base directory for this skill" line. Read its files by that full path.

1. Read `<skill folder>/gotchas.md`. Each gotcha is a real failure.
2. Read `<skill folder>/config.json`. Use the `projects.<game>` section for the game repo. Replace every `<placeholder>` value before the first run.
3. The game repo is the current folder. All script paths below are relative to it.
4. Check that the deck tools exist: `ls tools/deck/`.
5. For a new game with no `tools/deck/`, read `<skill folder>/references/new-game.md`.

Below, `deck` means `ssh -i <ssh_key> <ssh_opts> <deck_user>@<deck_host>`, with the values from config.

## Route (step 0)

| The user asks | Flow |
|---|---|
| "put it on the deck", "deploy to steam deck", "add to steam library" | First install or Redeploy |
| "test on the deck" | Redeploy, then Launch, then Screenshot |
| "deck screenshot" | Screenshot only |
| "deck fps", "why is it slow on the deck" | Fps read, then Perf profile |
| "does the controller work on the deck" | Controller check |

## Deck lock (every flow)

Only 1 agent uses the Deck at a time. Two agents that deploy to 1 install overwrite the user's play build.

1. Take the lock: `mkdir <lock_dir>`. If `mkdir` fails, read `<lock_owner_file>`.
2. If the owner pid is dead (`kill -0 <pid>` fails), the lock is stale. Remove it and take it again.
3. Else sleep `poll_s` (5 s) and try again. Tell the user after 5 min.
4. After the `mkdir` works, write `<lane> <pid> <iso-time>` to the owner file.
5. Set a trap: `trap 'rm -rf <lock_dir>' EXIT`. Release the lock at the end of the flow.

Do the whole flow in 1 bash script that holds the lock, so the trap always fires.

## Wake check (every flow)

1. Run `deck true`. "Operation timed out" means the Deck sleeps, is off or is off the network.
2. Ask the user to wake the Deck. A Deck wakes from sleep only by hand. A Deck that is off never wakes over the network.
3. Poll `deck true` every 5 s for `max_wake_wait_s` (5 min) at most. Then stop and tell the user.

## Flows

Each flow runs inside the lock. If your repo caps engine processes with a slot helper (this kit's `tools/godot_slot.sh`), `deploy.sh` takes its own slot for the export. Do not take a slot around it.

### First install

1. Run `tools/deck/deploy.sh`. It downloads the export template when it does not exist, exports, copies the build and adds the Steam shortcut.
2. The script also sets the Steam Input layout "Gamepad" for the shortcut (`tools/deck/steam_input.py`). Then the game gets the Deck controls as a normal gamepad. A layout that the user picked on the Deck stays.
3. If the shortcut or the layout does not exist, the script stops Steam and writes the file. It backs up the file first and starts Steam again after. It refuses when a game runs.
4. Check the output for `the shortcut "<name>" exists` or `shortcut written`, and for `Steam Input layout`.
5. To write only the shortcut and the layout, with no build and no copy, use `--no-sync`.
6. Tell the user the game is in the Steam library under the shortcut name, in "Non-Steam".

### Redeploy

1. Run `tools/deck/deploy.sh`. The shortcut exists, so the script copies only the changed files and does not touch Steam.
2. A copy of the full build takes 5 to 15 min on Wi-Fi. Run it in the background and poll every 5 s.
3. `--no-build` never copies. Use `--no-build --sync` only when `build_dir` holds the build that you want on the Deck.
4. The script exits 0 after a good deploy. A non-zero exit is a real failure.

### Launch

1. Check that no game runs: `deck "<game_running_check>"`. If it finds a process, stop. Ask the user to close the game.
2. Run `tools/deck/deploy.sh --no-build --launch`. It starts the game through `steam://rungameid/` and waits 60 s for the process.

### Screenshot

`deploy.sh --no-build --shot` also works, because `--no-build` never copies. The steps below need no Steam step.

1. Run `deck "export <shot_env>; rm -f <shot_remote_path>; gamescopectl screenshot <shot_remote_path>"`.
2. Wait up to 6 s until the file is not empty (`[ -s <shot_remote_path> ]`).
3. Copy it: `scp -i <ssh_key> <deck_user>@<deck_host>:<shot_remote_path> <shots_dir>/deck-<stamp>.png`.
4. Downscale it before you read it: `<resize_cmd> <shot_width> <file>`.
5. Open the shot and say what you see. The capture works in Gaming Mode only.

### Fps read

The bridge listens on 127.0.0.1 on the Deck. Read it on the Deck, not through an ssh tunnel.

1. Launch the game (flow above). Wait 25 s for the first playable scene.
2. Run `deck "python3 - --poses <first pose> --seconds 5" < tools/deck/profile.py`.
3. Report `median_fps`, `p5_fps`, `window`, `visible_prims` and `shadow_prims` from the JSON line.

### Perf profile

1. Run `profile.py` with `--poses <pose list> --layers --breakdown`. The poses are editor teleport spots in your game (for example `rig,d40,d120` in Crush Depth). Each `--layers` sample hides 1 editor layer, so the fps change names the cost of that layer.
2. To test a quality change, add `--quality deck` or `--set msaa_3d=0,sdfgi=false`.
3. Report a table: pose, layer, median fps, change from base. Name the top 3 costs.
4. Install perf test builds with `deploy.sh --perf` (the perf install), never in the user's play install.

### Controller check

1. Run `deck "ls /dev/input/by-id/; grep -A4 -i 'controller\|gamepad\|valve' /proc/bus/input/devices"`. The Deck has built-in controls. An extra controller in the dock also shows here.
2. While the game runs, read `joypads` and `input_device` from `get_state` on the Deck bridge.
3. Ask the user to press 1 button. Read `get_state` again: `input_device` must change to `joypad`.

## Install for test builds

The user's play build lives in `play_install_dir` with the shortcut `play_shortcut_name`. Agent test builds go in `perf_install_dir` with `perf_shortcut_name`: use `deploy.sh --perf`. For another install, give `--install-dir` and `--shortcut-name` together (gotchas.md 11). Never deploy a test build to the play install without the user's go.

## Reply to the user

1. Line 1: what now works on the Deck, with the number. Example: "The game runs on the Deck, 31 fps median at the start scene".
2. Line 2: the screenshot path, if any. Open it for the user.
3. Line 3: the 1 next step.

No time estimates. Give work sizes as S, M, L or XL.

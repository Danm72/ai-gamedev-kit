# steam-deck gotchas

Each item is a real failure from the first deploys of a Godot game (Crush Depth) to a Steam Deck. Each has the symptom, the cause and the fix. The source is in brackets.

## Network and power

1. **The copy died at 11 to 16 min.** Cause: the Deck went to sleep during the copy. The build is 512 MB and the Wi-Fi gives about 0.6 MB/s. Fix: `deploy.sh` holds a `systemd-inhibit --what=idle:sleep` lock on the Deck. It copies with `rsync -z`, because the pck compresses about 2.8 to 1. It resumes from `--partial-dir` and tries 3 times. Do not remove these parts.
2. **ssh says "Operation timed out".** Cause: the Deck sleeps, is off or is off the network. A Deck wakes from sleep only when a person presses a button. A Deck that is off never wakes over the network. Fix: ask the user to wake it. Poll every 5 s for 5 min at most, then stop. [first deploy]
3. **The bridge ssh tunnel from the Mac gave an empty reply.** Cause: unknown; the bridge listens on 127.0.0.1 on the Deck. Fix: run `profile.py` on the Deck itself: `ssh ... python3 - <args> < tools/deck/profile.py`. It needs only the Python stdlib. [deck-perf lane]

## Steam

4. **A shortcut write was lost.** Cause: Steam rewrites `shortcuts.vdf` when it exits. Fix: write the file only after Steam stops. Back it up first (`shortcuts.vdf.bak-claude-<stamp>`). In Gaming Mode, stop and start `steam-launcher.service`; `steam -shutdown` alone makes Gaming Mode start Steam again.
5. **Steam stopped under a game that ran.** Cause: a script that stops Steam does not check for a game. Fix: check `pgrep -f '[r]eaper SteamLaunch'` first. If it finds a process, stop and ask the user. The `[x]` class keeps the pattern from a match on the ssh shell.
6. **Two agents deployed to 1 install and overwrote the user's play build.** Cause: no lock and 1 shared install dir. Fix: take the Deck lock (`lock_dir` in config) for every flow. Put test builds in the perf install, apart from the user's play install. [team-lead brief]

## Screenshots

7. **`gamescopectl screenshot` saved nothing.** Cause: it needs a file path argument and the gamescope session env. Fix: `export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=gamescope-0; gamescopectl screenshot /tmp/shot.png`. The file comes a second later, so poll for it. The shot is large (up to 4K-class, or 1280x800); downscale it with `sips -Z 1280` before you read it. It works in Gaming Mode only.
8. **`deploy.sh --no-build --shot` can replace the user's install.** Cause: the old script always synced `build/deck/` with `--delete` before the shot. Fix: now `--no-build` never copies; add `--sync` to copy.

## Build

9. **The Godot 4.7.2 export templates were not installed.** Cause: the brief said they were; they were not. Fix: `tools/deck/get_template.py <version>` downloads only the Linux release template by HTTP range. `deploy.sh` calls it.
10. **The game failed to load the voxel terrain on Linux.** Cause: the `zylann.voxel` addon shipped macOS binaries only. Fix: add the Linux `.so` from the official release of the same version. Prove the same build: the tag commit is in both binaries.
11. **`DECK_DIR` alone breaks `--launch`.** Cause: the appid is `crc32(exe + name)`, and `exe` holds the install path. With a new `DECK_DIR` and the old name, `has` finds the old shortcut and skips the write. The launch then uses an id that no shortcut has. Fix: use `--perf`, or give `--install-dir` and `--shortcut-name` together. [steam_shortcut.py code read]

## Performance

12. **The first boot ran at 9.9 fps median.** Cause: the build used the Mac settings. These are SDFGI, 4096 shadows with 4 splits, MSAA and a 1600x900 window. The 16:9 image also gave black bars on the 16:10 screen. Fix: a `deck` quality preset (`data/balance/quality.json`, picked by env `SteamDeck=1`). The bridge `quality` command reads the preset. [commits 8de9ece, 8f72a35]

## Deck facts

13. **Do not hard-code the Deck values.** The Deck IP, user, key path and Steam userdata id differ per Deck and can change. Keep them in `config.json`. Discover the userdata dir on each run (`userdata_discovery` in config). Never store the sudo password in a skill file. [first deploy]

## Deploy script

14. **`deploy.sh` exited 1 after a good deploy.** Cause: the EXIT trap ran `kill` on the keep-awake ssh, and that ssh had already ended. Fix: the trap ends with `|| true`. [commits 1fcfbf6, ee6e201]
15. **The game did not see the Deck controls as a gamepad.** Cause: a non-Steam shortcut gets the Steam Input desktop layout (mouse and keys). Fix: `deploy.sh` pins the layout "Gamepad" with `steam_input.py`. Steam Cloud can replace the write at start; the script warns then.

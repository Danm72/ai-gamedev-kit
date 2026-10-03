# ai-gamedev-kit

Claude Code skills, engine API lookup tools and a JSON game bridge for building games with AI agents.

I build games only through AI agents. I do not open the engine editor to make changes. This kit is the
tooling from one such game, Crush Depth, a deep-sea salvage game. It started in Godot 4.7 and is now
ported to Unity 6.7 (URP). The skills and tools came out of real failures in that work. Most files say
which failure they stop.

This is not a framework. Copy the parts you want into your own repo and change them.

## Why it works this way

- **Agents drive the game through a JSON bridge, not the editor.** The game listens on a localhost TCP
  port. An agent sends `get_state`, real input and `screenshot` commands, and reads numbers back.
  The same protocol runs in the Godot and the Unity build, so one set of Python tests checks both.
- **Tests run on built players.** A test starts a real game (headless where it can), sends real input
  through the bridge and checks the state. It does not test the editor.
- **"Look it up, do not guess."** Models know the engine version of their training data. They write
  Godot 3 code in a Godot 4 project, or Unity 2022 API in a Unity 6 project. The lookup tools answer from the
  source of the pinned engine build. The hooks block old API in each edit.
- **Proof before "done".** A visual claim needs a screenshot from the in-game player camera. A test
  counts only if it failed first. The skills enforce this.

## What is in it

```
skills/      7 Claude Code skills (each has SKILL.md, gotchas.md, config.json, references/)
tools/       godot_api.py, unity_api.py, godot_slot.sh, godot_bg.sh (+ nofocus.m)
tools/hooks/ gd_guard.py, unity_guard.py, settings.example.json
bridge/      godot/bridge.gd, unity/*.cs, python/ (client + MCP server)
docs/        godot-4.7.md, unity-6.md (engine cheat sheets for agents)
tests/       tests for the two guard hooks
```

### Engine API lookup

| File | What it does |
|---|---|
| `tools/godot_api.py` | Looks up a Godot class, member, signal or project setting in the `4.7.2-stable` class reference, and searches the 4.7 manual. First use makes a sparse clone (about 25 MB) into `~/.cache/ai-gamedev-kit/`. "No member" means it does not exist. |
| `tools/unity_api.py` | The same for Unity 6.7. It indexes the installed editor's XML docs and package sources, UnityCsReference at the matching tag, and the offline manual. It prints `[OBSOLETE]` flags. Set `UNITY_EDITOR_DIR` if the editor is not in the default Hub folder. The manual zip is about 500 MB on first `--docs` use. |

```
python3 tools/godot_api.py Environment tonemap_agx_white
python3 tools/unity_api.py Rigidbody linearVelocity
python3 tools/unity_api.py --obsolete FindObjectsOfType
```

### Hooks

| File | What it does |
|---|---|
| `tools/hooks/gd_guard.py` | PostToolUse hook. After each edit of a `.gd` file it blocks Godot 3 syntax (`yield`, `export var`, string `connect`, `KinematicBody` ...) and prints the Godot 4 form. |
| `tools/hooks/unity_guard.py` | PostToolUse: blocks outdated Unity API in `.cs` files (old Input Manager, `FindObjectsOfType`, `rb.velocity`, URP `Execute`, `?.` on a `UnityEngine.Object` ...). PreToolUse: blocks hand edits of `.unity`, `.prefab`, `.meta` and other Unity YAML, and shell copies that duplicate GUIDs. |
| `tools/hooks/settings.example.json` | The hook registration. Merge it into your `.claude/settings.json`. |

Test: `python3 tests/test_gd_guard.py` and `python3 tests/test_unity_guard.py`.

### Game bridge

| File | What it does |
|---|---|
| `bridge/godot/bridge.gd` | A localhost TCP server, one JSON object per line. It calls `run_command(cmd, args)` on a node you give it. It quits an idle agent game after 60 s. |
| `bridge/unity/BridgeServer.cs`, `Json.cs`, `MiniJson.cs` | The same protocol in C#. Features register their own commands with `Register`, `RegisterAsync` and `AddState`, so parallel agents add commands without edits to one shared file. Commands run on the main thread. |
| `bridge/python/bridge_client.py` | A small client and CLI: `python3 bridge_client.py get_state`, `--wait-ready <port>`. |
| `bridge/python/server.py`, `run.sh` | An MCP server over the bridge. It exposes the engine-agnostic tools (`ping`, `get_state`, `get_value`, `set_value`, `sim_input`, `rng_sample`, `screenshot`, `window_size`, `bridge`, `quit`). Add your game's own tools at the bottom; the file has an example. `run.sh` builds its venv on first use. See `mcp.example.json`. |

The protocol:

```
-> {"id": 1, "cmd": "get_state", "args": {}}
<- {"id": 1, "ok": true, "result": {...}}
<- {"id": 1, "ok": false, "error": "unknown command 'x'"}
```

To install the MCP server, copy `bridge/python/` to `tools/mcp/` in your game repo. Then merge
`mcp.example.json` into your `.mcp.json`; it uses that path.

The bridge files are reference code. Your game supplies the commands. The MCP tools assume your game
answers the commands it names; a command your game does not have returns an error, not a crash.

### Process tools (Godot)

| File | What it does |
|---|---|
| `tools/godot_slot.sh` | Caps how many Godot processes all agents on one machine run at once (`GODOT_SLOT_MAX`, default 6). Uses atomic `mkdir` slots in `/tmp` and frees the slot on exit. Source it, then `godot_slot_take <lane>`. |
| `tools/godot_bg.sh` | Starts a windowed Godot that never takes keyboard focus, so agents can take screenshots while you work. On macOS it loads `nofocus.dylib` (built from `tools/godot_bg/nofocus.m` on first use) into the stock Godot.app. On Linux it uses `xvfb-run`. |

### Engine cheat sheets

`docs/godot-4.7.md` and `docs/unity-6.md` hold what changed since the model's training data, the
project settings that matter, light, look and performance rules, and the gotchas we hit. Point your
`CLAUDE.md` at them ("read sections 2 and 7 before engine work").

## Skills

Install a skill: copy its folder into `.claude/skills/<name>/` in your game repo. Then fill in the
`<placeholder>` values in its `config.json`. Each `SKILL.md` has an **Assumes** section. Read it first:
most skills call scripts that live in your game repo, and the kit does not ship those scripts.

| Skill | Use it to | Assumes (not in the kit) |
|---|---|---|
| `big-feature` | Plan a new game system: up to 3 questions, a code check, 2 or 3 sized options, then tickets after you pick. | `docs/features/<slug>/FEATURE.md` (it makes it), code folders in `config.json`. |
| `feature-breaker` | Check a finished feature: each test failed first, tuning moved to data, a fresh agent tries to break it, a capped fix loop. | A bridge whose `get_state` returns the "done when" numbers, `test-before.log` and `test-after.log` (or a test command), a real-input path. |
| `game-manager` | Split a job across parallel agents in git worktrees ("lanes") and merge the ones that pass. | A git repo with `main`, a gitignored `work/` folder where it keeps `work/manager/STATE.md` and the lane briefs, and a smoke test command (default `bash tests/smoke.sh`). |
| `look-critic` | Compare in-game screenshots to a key image and give a closer / not closer call with a gap list. | A key image per view, a bridge `screenshot` command, and a capture script (`capture_script` in config). |
| `playtest-bot` | Check balance by numbers: seeded headless runs, a bot policy, bands, a confirm batch on new seeds. | `scripts/run_seeds.sh`, `tools/playtest_bot.py` and policy files. The kit does not ship these. |
| `asset-forge` | Make or fix a 3D model: concept image, image-to-3D, Blender clean-up, engine import, a render check. | Meshy and Higgsfield MCP servers (or your own image-to-3D route), Blender, and 5 pipeline scripts in `bakeoff_shared_dir` (listed in its Assumes). |
| `steam-deck` | Build, install and test on a Steam Deck: deploy, screenshot, fps, controller. | A `tools/deck/` folder of scripts (deploy, shortcut, template, profile), which the kit does not ship, and SSH key login to the Deck (host, user and key in `config.json`). |

Every skill keeps a `gotchas.md` file: the real failures from earlier runs and the fix for each. Add
your own failures there.

Some skills name Crush Depth paths in their examples. The steps work for any Godot or Unity game that
has a bridge.

## Optional: a remote box for heavy runs

`godot_slot.sh` can skip the local slot when `GODOT` points at a wrapper that runs Godot on a remote
Linux box. Set `GODOT_REMOTE_PATTERN` to a glob that matches your wrapper. The kit does not ship the
wrapper.

## Requirements

- Claude Code (skills, hooks, MCP).
- Python 3.10 or later. The MCP server installs `mcp` into its own venv.
- Godot 4.7 or Unity 6.7 (6000.7.0b2 was the tested build). Pin your own version with `GODOT_TAG` or
  your project's `ProjectVersion.txt`.
- macOS or Linux. `godot_bg.sh` on macOS needs the Xcode command line tools (`clang`).

## License

MIT. See `LICENSE`.

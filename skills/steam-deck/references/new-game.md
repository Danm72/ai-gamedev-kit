# Add a new Godot game to the Deck

Use these steps for a Godot 4 game repo with no `tools/deck/` folder. The deck tools are not in this kit. You write them once per game, or copy them from an earlier game of your own. SKILL.md, section Assumes, lists what each script must do.

## 1. Get the tools

1. Write or copy `tools/deck/deploy.sh`, `steam_shortcut.py`, `steam_input.py`, `get_template.py` and `profile.py`.
2. Add a test for `steam_shortcut.py` (appid, read and write of `shortcuts.vdf`). Make it fail first, then pass.
3. In `deploy.sh`, set the game name, the binary name and the install dir on the Deck for the new game.
4. Add a `projects.<game>` section to `config.json` in this skill.

## 2. Export preset

Add a `Linux` preset to `export_presets.cfg` (Project > Export in the editor, or by hand):

- `platform="Linux"`, `binary_format/architecture="x86_64"`, `binary_format/embed_pck=true`.
- `export_path="build/deck/<Binary>.x86_64"`. Add `build/` to `.gitignore`.
- `exclude_filter`: every folder that the game does not load (runs, shots, work, tests, tools, refs, docs, build).
- `include_filter`: the data files that the game reads at run time, for example `data/**/*.json`.

## 3. Export templates

The Linux release template must match the exact Godot version (`godot --version`).

1. Run `python3 tools/deck/get_template.py <version>`. It downloads only the Linux release template from the 1.3 GB `.tpz` with HTTP range requests.
2. Check that the template file exists in the Godot export templates folder (`<version>.stable/`; on macOS it is under `Library/Application Support/Godot/export_templates/` in the home folder).

## 4. GDExtension binaries

Each GDExtension addon needs a Linux x86_64 `.so` next to its macOS binary. Many addons ship macOS binaries only.

1. Read the `.gdextension` file. Find the `linux.release.x86_64` and `linux.debug.x86_64` paths.
2. Get the `.so` files from the official release of the same version as the macOS binary.
3. Prove that they are the same build. Find the tag commit in both binaries: `strings <file> | grep <commit>`.
4. Check the license of the addon. Write it in the commit body.
5. After the export, check that the `.so` is in `build/deck/` next to the binary.

## 5. First run

1. Run the First install flow in SKILL.md.
2. Launch the game. Read `godot.log` on the Deck for errors: `~/.local/share/godot/app_userdata/<project name>/logs/`.
3. Read the fps at the start scene. Under 30 fps, add a Deck quality preset (gotchas.md 12).

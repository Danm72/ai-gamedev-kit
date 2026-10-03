#!/usr/bin/env python3
"""PostToolUse hook: block Godot 3 syntax in a .gd file after an Edit or Write.

Claude Code sends the hook payload as JSON on stdin. When the edited file is a .gd
file with a Godot 3 pattern, the hook prints the lines and the Godot 4.7 form to
stderr and exits 2, so the agent sees the message and fixes the file at once.
Any other file, or a clean file, exits 0.
Wire it in .claude/settings.json (see hooks/settings.example.json). Patterns come from docs/godot-4.7.md.
"""
import json
import re
import sys
from pathlib import Path

# (pattern, Godot 4.7 form). Patterns run on code with comments and strings removed.
RULES = [
	(r"\byield\s*\(", "await signal (for example `await get_tree().process_frame`)"),
	(r"^\s*export\s*(\(|var\b)", "`@export var` (and `@export_range` and similar for hints)"),
	(r"^\s*onready\s+var\b", "`@onready var`"),
	(r"^\s*tool\s*$", "`@tool`"),
	(r"\.connect\(\s*\"\"\s*,\s*self\b", "`signal_name.connect(callable)`"),
	(r"\b(deg2rad|rad2deg|stepify|range_lerp|str2var|var2str)\s*\(", "`deg_to_rad`, `rad_to_deg`, `snapped`, `remap`, `str_to_var`, `var_to_str`"),
	(r"\brand_range\s*\(", "`randf_range` or `randi_range` (on your seeded `RandomNumberGenerator`)"),
	(r"\.instance\(\s*\)", "`.instantiate()`"),
	(r"\b(Spatial|KinematicBody|KinematicBody2D|MeshInstance|Camera|RigidBody|StaticBody|Area|CollisionShape|Particles|Position3D|Position2D)\b(?!\w)(?!\s*[:=])(?=\s*($|\.new|\)|,))", "the 3D/2D node names (`Node3D`, `CharacterBody3D`, `MeshInstance3D`, `Camera3D`, `RigidBody3D`, `Marker3D`)"),
	(r"\bmove_and_slide\s*\(\s*[^)\s]", "`velocity = ...` then `move_and_slide()` with no arguments"),
	(r"\bPool(Byte|Int|Real|String|Vector2|Vector3|Color)Array\b", "`Packed*Array` (for example `PackedVector3Array`)"),
	(r"\b(File|Directory)\.new\s*\(", "`FileAccess.open()` and `DirAccess.open()`"),
	(r"\bsetget\b", "`var x: int: set = _set_x, get = _get_x` (property syntax)"),
	(r"\.change_scene\s*\(", "`change_scene_to_file()` or `change_scene_to_packed()`"),
	(r"\bBUTTON_(LEFT|RIGHT|MIDDLE|WHEEL_UP|WHEEL_DOWN)\b", "`MOUSE_BUTTON_LEFT` and similar"),
	(r"\bOS\.get_ticks_(msec|usec)\b", "`Time.get_ticks_msec()`"),
	(r"\bJSON\.parse\s*\(", "`JSON.parse_string()` or a `JSON` instance with `parse()`"),
	(r"\bfuncref\s*\(", "a `Callable` (for example `my_func` or `Callable(obj, \"name\")`)"),
	(r"\b(master|puppet|remotesync|mastersync|puppetsync)\s+func\b", "`@rpc(...)`"),
]
COMPILED = [(re.compile(p), fix) for p, fix in RULES]
# The extends line needs its own check, because a bare old class name there has no `.new`.
EXTENDS_OLD = re.compile(r"^\s*extends\s+(Spatial|KinematicBody|KinematicBody2D|MeshInstance|Camera|RigidBody|StaticBody|Area|Particles|Position3D)\s*$")


def strip_code(line: str) -> str:
	"""Remove string contents and the comment, so only code is matched."""
	out, quote, i = [], "", 0
	while i < len(line):
		c = line[i]
		if quote:
			if c == "\\":
				i += 2
				continue
			if c == quote:
				quote = ""
				out.append(c)
		elif c in "\"'":
			quote = c
			out.append(c)
		elif c == "#":
			break
		else:
			out.append(c)
		i += 1
	return "".join(out)


def scan(text: str) -> list[str]:
	hits = []
	for n, raw in enumerate(text.splitlines(), 1):
		code = strip_code(raw)
		if not code.strip():
			continue
		if EXTENDS_OLD.match(code):
			hits.append(f"  line {n}: {raw.strip()}\n    use the Godot 4 node name (`Node3D`, `CharacterBody3D`, `Camera3D`, ...)")
			continue
		for rx, fix in COMPILED:
			if rx.search(code):
				hits.append(f"  line {n}: {raw.strip()}\n    use {fix}")
				break
	return hits


def main() -> int:
	try:
		payload = json.load(sys.stdin)
	except (json.JSONDecodeError, ValueError):
		return 0
	tin = payload.get("tool_input") or {}
	path = tin.get("file_path") or tin.get("path") or ""
	if not path.endswith(".gd"):
		return 0
	p = Path(path)
	if not p.is_file():
		return 0
	hits = scan(p.read_text(errors="ignore"))
	if not hits:
		return 0
	print(f"gd_guard: Godot 3 syntax in {path}. This repo is Godot 4.7.2. Fix these lines:", file=sys.stderr)
	print("\n".join(hits[:20]), file=sys.stderr)
	print("Check an API with: python3 tools/godot_api.py <Class> [member]", file=sys.stderr)
	return 2


if __name__ == "__main__":
	sys.exit(main())

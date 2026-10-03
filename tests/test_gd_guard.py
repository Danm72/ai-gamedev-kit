#!/usr/bin/env python3
"""The Godot 3 syntax guard (tools/hooks/gd_guard.py) blocks old API in .gd edits.

Why: agents trained on older Godot write Godot 3 code (yield, export var, string connect).
The PostToolUse hook in .claude/settings.json runs the guard after each Edit or Write.
The guard exits 2 with the bad lines, so Claude Code shows them to the agent at once.

How: feed the guard the hook payload (JSON on stdin) for fixture files.
No Godot process is needed, so this test takes no slot.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "tools/hooks/gd_guard.py"
fails = 0


def check(name: str, cond: bool, detail: str = "") -> None:
	global fails
	print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail and not cond else ""))
	fails += 0 if cond else 1


def run_guard(path: Path, tool: str = "Edit") -> subprocess.CompletedProcess:
	payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": str(path)}})
	return subprocess.run([sys.executable, str(GUARD)], input=payload, capture_output=True, text=True)


BAD = {
	"yield": "func f():\n\tyield(get_tree(), \"idle_frame\")\n",
	"export var": "export var speed = 5.0\n",
	"export(int)": "export(int) var hp = 3\n",
	"onready var": "onready var cam = $Camera\n",
	"tool keyword": "tool\nextends Node\n",
	"string connect": "func _ready():\n\tbutton.connect(\"pressed\", self, \"_on_pressed\")\n",
	"deg2rad": "var a = deg2rad(90)\n",
	"instance()": "var n = scene.instance()\n",
	"Spatial": "extends Spatial\n",
	"KinematicBody": "extends KinematicBody\n",
	"move_and_slide args": "func f():\n\tmove_and_slide(velocity, Vector3.UP)\n",
	"PoolVector3Array": "var p := PoolVector3Array()\n",
	"File.new": "var f = File.new()\n",
	"rand_range": "var r = rand_range(0, 1)\n",
	"setget": "var hp = 3 setget set_hp\n",
	"change_scene": "get_tree().change_scene(\"res://a.tscn\")\n",
	"BUTTON_LEFT": "if e.button_index == BUTTON_LEFT:\n\tpass\n",
	"OS.get_ticks_msec": "var t = OS.get_ticks_msec()\n",
}
GOOD = (
	"@tool\nextends Node3D\n"
	"@export var speed := 5.0\n"
	"@onready var cam: Camera3D = $Camera3D\n"
	"# yield( in a comment is fine; so is export var in a comment\n"
	"func _ready() -> void:\n"
	"\tbutton.pressed.connect(_on_pressed)\n"
	"\tvar a := deg_to_rad(90.0)\n"
	"\tvar n := scene.instantiate()\n"
	"\tmove_and_slide()\n"
	"\tvar label := \"press export var to yield(\"\n"
	"\tawait get_tree().create_timer(0.2).timeout\n"
)

with tempfile.TemporaryDirectory() as tmp:
	for name, src in BAD.items():
		p = Path(tmp) / "bad.gd"
		p.write_text(src)
		r = run_guard(p)
		check(f"blocks {name}", r.returncode == 2 and "Godot 3" in r.stderr, f"exit {r.returncode}, stderr {r.stderr.strip()!r}")
	p = Path(tmp) / "good.gd"
	p.write_text(GOOD)
	r = run_guard(p, "Write")
	check("passes Godot 4 code", r.returncode == 0, r.stderr.strip())
	txt = Path(tmp) / "notes.txt"
	txt.write_text("export var speed\n")
	check("ignores non-.gd files", run_guard(txt).returncode == 0)
	check("ignores a missing file", run_guard(Path(tmp) / "gone.gd").returncode == 0)

# No false positive on the kit's own GDScript (the reference bridge).
hits = []
for gd in sorted((ROOT / "bridge/godot").rglob("*.gd")):
	r = run_guard(gd)
	if r.returncode != 0:
		hits.append(f"{gd.relative_to(ROOT)}: {r.stderr.strip()[:200]}")
check("no false positive in bridge/godot", not hits, "; ".join(hits[:5]))

print(f"RESULT test_gd_guard: {'FAIL' if fails else 'PASS'} ({fails} failed)")
sys.exit(1 if fails else 0)

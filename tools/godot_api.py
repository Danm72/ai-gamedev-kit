#!/usr/bin/env python3
"""Look up the Godot API and manual for the exact engine build of this repo.

Agents know the Godot of their training data. This tool answers from the source
of the pinned engine tag instead, so a session checks a class, method, property,
signal, constant or project setting before it uses it.

Usage:
  python3 tools/godot_api.py Environment                  # class summary: members, methods, signals
  python3 tools/godot_api.py Environment tonemap_mode     # one member, with its description
  python3 tools/godot_api.py ProjectSettings physics/3d/physics_engine
  python3 tools/godot_api.py --find interpolation         # search every class for a name
  python3 tools/godot_api.py --docs "volumetric fog"      # search the 4.7 manual (godot-docs .rst)
  python3 tools/godot_api.py --path                       # print the cache dir

First use fetches sparse clones (about 16 MB class reference, 9 MB manual) into ~/.cache/ai-gamedev-kit/godot-ref/.
GODOT_REF_DIR moves the cache.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

GODOT_TAG = os.environ.get("GODOT_TAG", "4.7.2-stable")  # pin to your engine build
DOCS_BRANCH = os.environ.get("GODOT_DOCS_BRANCH", "4.7")
CACHE = Path(os.environ.get("GODOT_REF_DIR", Path.home() / ".cache/ai-gamedev-kit/godot-ref"))
ENGINE_DIR = CACHE / f"godot-{GODOT_TAG}"
DOCS_DIR = CACHE / f"godot-docs-{DOCS_BRANCH}"


def _sparse_clone(url: str, ref: str, dest: Path, paths: list[str]) -> None:
	if (dest / ".done").exists():
		return
	dest.parent.mkdir(parents=True, exist_ok=True)
	tmp = dest.with_name(dest.name + ".tmp")
	subprocess.run(["rm", "-rf", str(tmp)], check=True)
	print(f"godot_api: fetching {url} @ {ref} (first use only)", file=sys.stderr)
	run = lambda *a: subprocess.run(["git", "-C", str(tmp), *a], check=True, capture_output=True)
	subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--filter=blob:none", "--sparse",
		"--branch", ref, url, str(tmp)], check=True, capture_output=True)
	run("sparse-checkout", "set", "--no-cone", *paths)
	subprocess.run(["rm", "-rf", str(dest)], check=True)
	tmp.rename(dest)
	(dest / ".done").write_text(ref)


def engine_dir() -> Path:
	_sparse_clone("https://github.com/godotengine/godot.git", GODOT_TAG, ENGINE_DIR,
		["/doc/classes/", "/modules/*/doc_classes/"])
	return ENGINE_DIR


def docs_dir() -> Path:
	_sparse_clone("https://github.com/godotengine/godot-docs.git", DOCS_BRANCH, DOCS_DIR,
		["/tutorials/**/*.rst", "/getting_started/**/*.rst", "/engine_details/**/*.rst"])
	return DOCS_DIR


def class_files() -> dict[str, Path]:
	root = engine_dir()
	files = list(root.glob("doc/classes/*.xml")) + list(root.glob("modules/*/doc_classes/*.xml"))
	return {f.stem: f for f in files}


def _text(el: ET.Element | None) -> str:
	if el is None or not el.text:
		return ""
	return re.sub(r"\s+", " ", el.text).strip()


def _sig(el: ET.Element) -> str:
	ret = el.find("return")
	args = ", ".join(
		f"{a.get('name')}: {a.get('type')}" + (f" = {a.get('default')}" if a.get("default") else "")
		for a in el.findall("param"))
	q = el.get("qualifiers")
	out = f"{el.get('name')}({args})"
	if ret is not None:
		out += f" -> {ret.get('type')}"
	return out + (f" {q}" if q else "")


def _flags(el: ET.Element) -> str:
	tags = []
	if el.get("deprecated") is not None:
		tags.append(f"DEPRECATED: {el.get('deprecated') or 'yes'}")
	if el.get("experimental") is not None:
		tags.append(f"EXPERIMENTAL: {el.get('experimental') or 'yes'}")
	return f"  [{'; '.join(tags)}]" if tags else ""


def show_class(name: str) -> int:
	files = class_files()
	if name not in files:
		close = [c for c in files if c.lower() == name.lower() or name.lower() in c.lower()][:15]
		print(f"No class {name!r} in Godot {GODOT_TAG}." + (f" Close: {', '.join(close)}" if close else ""))
		return 1
	root = ET.parse(files[name]).getroot()
	print(f"# {name} (Godot {GODOT_TAG}) inherits {root.get('inherits', '-')}{_flags(root)}")
	print(_text(root.find("brief_description")))
	for tag, label in (("members", "Properties"), ("methods", "Methods"), ("signals", "Signals")):
		items = root.find(tag)
		if items is None or not len(items):
			continue
		print(f"\n## {label}")
		for el in items:
			if tag == "members":
				print(f"- {el.get('name')}: {el.get('type')} = {el.get('default', '')}{_flags(el)}")
			else:
				print(f"- {_sig(el)}{_flags(el)}")
	consts = root.find("constants")
	if consts is not None and len(consts):
		print("\n## Constants")
		for el in consts:
			print(f"- {el.get('name')} = {el.get('value')}" + (f" ({el.get('enum')})" if el.get("enum") else "") + _flags(el))
	print(f"\nSource: {files[name]}")
	return 0


def show_member(cls: str, member: str) -> int:
	files = class_files()
	if cls not in files:
		return show_class(cls)
	root = ET.parse(files[cls]).getroot()
	hits = []
	for tag in ("members", "methods", "signals", "constants", "theme_items", "annotations"):
		for el in root.iter(tag[:-1] if tag != "theme_items" else "theme_item"):
			if el.get("name") == member or member.lower() in (el.get("name") or "").lower():
				hits.append((tag, el))
	if not hits:
		print(f"{cls} has no member matching {member!r} in Godot {GODOT_TAG}. Do not use it.")
		return 1
	exact = [h for h in hits if h[1].get("name") == member]
	for tag, el in (exact or hits)[:20]:
		if tag in ("methods", "signals", "annotations"):
			head = _sig(el)
		elif tag == "constants":
			head = f"{el.get('name')} = {el.get('value')}"
		else:
			head = f"{el.get('name')}: {el.get('type')} = {el.get('default', '')}"
		print(f"## {cls}.{head}  ({tag[:-1]}){_flags(el)}")
		desc = _text(el.find("description")) or _text(el)
		if desc:
			print(desc)
		print()
	return 0


def find(term: str) -> int:
	t = term.lower()
	n = 0
	for cls, f in sorted(class_files().items()):
		if t in cls.lower():
			print(f"class {cls}")
			n += 1
		root = ET.parse(f).getroot()
		for tag in ("member", "method", "signal", "constant"):
			for el in root.iter(tag):
				if t in (el.get("name") or "").lower():
					print(f"{cls}.{el.get('name')}  ({tag}){_flags(el)}")
					n += 1
	print(f"{n} hits in Godot {GODOT_TAG}")
	return 0 if n else 1


def docs(term: str) -> int:
	root = docs_dir()
	out = subprocess.run(["grep", "-rli", "--include=*.rst", term, str(root)], capture_output=True, text=True).stdout
	files = [Path(p) for p in out.split()]
	files.sort(key=lambda p: -p.read_text(errors="ignore").lower().count(term.lower()))
	for p in files[:15]:
		title = next((ln.strip() for ln in p.read_text(errors="ignore").splitlines() if ln.strip() and not ln.startswith((".", ":", "="))), "")
		print(f"{p}  — {title}")
	print(f"{len(files)} pages in godot-docs {DOCS_BRANCH} mention {term!r}. Read a page with the Read tool.")
	return 0 if files else 1


def main(argv: list[str]) -> int:
	if not argv or argv[0] in ("-h", "--help"):
		print(__doc__)
		return 0
	if argv[0] == "--path":
		print(CACHE)
		return 0
	if argv[0] == "--find" and len(argv) > 1:
		return find(argv[1])
	if argv[0] == "--docs" and len(argv) > 1:
		return docs(" ".join(argv[1:]))
	if len(argv) == 1:
		return show_class(argv[0])
	return show_member(argv[0], argv[1])


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Look up the Unity API and manual for the exact engine build of this repo.

Agents know the Unity of their training data (often 2021 to 2023). This tool answers from
the sources of the pinned build instead, so a session checks a type, member or manual page
before it uses it. It works offline after the first use.

Usage:
  python3 tools/unity_api.py Rigidbody                    # type summary: base, members, OBSOLETE flags
  python3 tools/unity_api.py Rigidbody linearVelocity     # one member: signature, doc, source line
  python3 tools/unity_api.py UnityEngine.Object FindObjectsByType
  python3 tools/unity_api.py --find FindAnyObjectByType   # search every type and member name
  python3 tools/unity_api.py --obsolete Rigidbody         # list obsolete types and members that match
  python3 tools/unity_api.py --docs "render graph"        # search the manual (HTML) and package docs
  python3 tools/unity_api.py --page <path.html>           # print a manual page as plain text
  python3 tools/unity_api.py --sources                    # show the sources in use and the version
  python3 tools/unity_api.py --rebuild                    # rebuild the index

Sources, in order of trust:
  1. The installed editor of the pinned version: its XML docs (summaries) and its built-in
     package C# sources (URP, SRP Core, Shader Graph, Test Framework, uGUI, Input System ...).
  2. UnityCsReference (github.com/Unity-Technologies/UnityCsReference) at the pinned tag:
     engine and editor C# signatures and [Obsolete] attributes. Reference only; read, never copy.
  3. The offline manual zip for the pinned stream (docs.unity3d.com), Manual pages only.
When the pinned editor is not installed, package sources fall back to the Graphics repo
(URP, Core, Shader Graph) and to the newest installed editor; each hit names its source.

The version comes from ProjectSettings/ProjectVersion.txt of the Unity project when it exists
(UNITY_PROJECT_DIR, else <repo>/unity/ or <repo>/, where <repo> is the folder above tools/),
else from the UNITY_VERSION environment variable, else from UNITY_VERSION below.
UNITY_EDITOR_DIR overrides the editor folder. UNITY_REF_DIR moves the cache
(default ~/.cache/ai-gamedev-kit/unity-ref/).
"""
from __future__ import annotations

import fcntl
import html
import json
import os
import re
import sqlite3
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

UNITY_VERSION = "6000.7.0b2"  # the fallback pin; the project's ProjectVersion.txt wins

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("UNITY_REF_DIR", Path.home() / ".cache/ai-gamedev-kit/unity-ref"))
INDEX_FORMAT = 6
# Built-in package folders and bundled .tgz packages to index. HDRP is left out: add it if you use it.
PACKAGES = [
	"com.unity.render-pipelines.universal", "com.unity.render-pipelines.core", "com.unity.shadergraph",
	"com.unity.test-framework", "com.unity.ugui", "com.unity.textmeshpro", "com.unity.visualeffectgraph",
	"com.unity.inputsystem", "com.unity.mathematics", "com.unity.collections", "com.unity.burst",
	"com.unity.ai.navigation", "com.unity.cinemachine", "com.unity.splines", "com.unity.profiling.core",
	"com.unity.test-framework.performance", "com.unity.addressables",
]
GRAPHICS_FALLBACK = ["com.unity.render-pipelines.universal", "com.unity.render-pipelines.core", "com.unity.shadergraph"]


# ---------- version and paths ----------

def version() -> str:
	env = os.environ.get("UNITY_PROJECT_DIR")
	for proj in ([Path(env)] if env else [ROOT / "unity", ROOT]):
		pv = proj / "ProjectSettings/ProjectVersion.txt"
		if pv.is_file():
			m = re.search(r"m_EditorVersion:\s*(\S+)", pv.read_text(errors="ignore"))
			if m:
				return m.group(1)
	return os.environ.get("UNITY_VERSION", UNITY_VERSION)


def stream(v: str) -> str:
	return ".".join(v.split(".")[:2])


def _editor_candidates(v: str) -> list[Path]:
	return [
		Path(f"/Applications/Unity/Hub/Editor/{v}/Unity.app/Contents"),
		Path.home() / f"Unity/Hub/Editor/{v}/Editor/Data",
		Path(f"/opt/unity/Editor/{v}/Editor/Data"),
	]


def editor_dir(v: str) -> Path | None:
	env = os.environ.get("UNITY_EDITOR_DIR")
	if env:
		p = Path(env)
		for sub in (p, p / "Unity.app/Contents", p / "Editor/Data"):
			if (sub / "Resources/PackageManager").is_dir():
				return sub
	for p in _editor_candidates(v):
		if (p / "Resources/PackageManager").is_dir():
			return p
	return None


def installed_editors() -> list[tuple[str, Path]]:
	out = []
	for hub in (Path("/Applications/Unity/Hub/Editor"), Path.home() / "Unity/Hub/Editor"):
		if hub.is_dir():
			for d in hub.iterdir():
				ed = editor_dir_for_folder(d)
				if ed:
					out.append((d.name, ed))
	return sorted(out, key=lambda t: _vkey(t[0]))


def editor_dir_for_folder(d: Path) -> Path | None:
	for sub in (d / "Unity.app/Contents", d / "Editor/Data"):
		if (sub / "Resources/PackageManager").is_dir():
			return sub
	return None


def _vkey(v: str) -> tuple:
	parts = re.findall(r"\d+|[abfp]", v)
	return tuple(int(p) if p.isdigit() else {"a": 0, "b": 1, "f": 2, "p": 3}[p] for p in parts)


def xml_dir(ed: Path) -> Path | None:
	for sub in (ed / "Resources/Scripting/Managed", ed / "Managed"):
		if sub.is_dir():
			return sub
	return None


# ---------- fetching ----------

def _git(*a: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
	return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True)


def _sparse_clone(url: str, ref: str, dest: Path, paths: list[str]) -> bool:
	if (dest / ".done").exists():
		return True
	dest.parent.mkdir(parents=True, exist_ok=True)
	tmp = dest.with_name(dest.name + ".tmp")
	subprocess.run(["rm", "-rf", str(tmp)], check=True)
	print(f"unity_api: fetching {url} @ {ref} (first use only)", file=sys.stderr)
	try:
		_git("clone", "--quiet", "--depth", "1", "--filter=blob:none", "--sparse", "--branch", ref, url, str(tmp))
		_git("sparse-checkout", "set", "--no-cone", *paths, cwd=tmp)
	except subprocess.CalledProcessError as e:
		print(f"unity_api: fetch failed: {e.stderr.strip()[:300]}", file=sys.stderr)
		subprocess.run(["rm", "-rf", str(tmp)])
		return False
	subprocess.run(["rm", "-rf", str(dest)], check=True)
	tmp.rename(dest)
	(dest / ".done").write_text(ref)
	return True


def csref_tag(v: str) -> str:
	"""The pinned tag, or the newest tag of the same stream when the pin has no tag."""
	try:
		out = _git("ls-remote", "--tags", "https://github.com/Unity-Technologies/UnityCsReference.git").stdout
	except (subprocess.CalledProcessError, FileNotFoundError):
		return v
	tags = set(re.findall(r"refs/tags/(\S+)$", out, re.M))
	if v in tags:
		return v
	same = sorted((t for t in tags if t.startswith(stream(v) + ".")), key=_vkey)
	older = [t for t in same if _vkey(t) <= _vkey(v)]
	pick = (older or same or [v])[-1]
	print(f"unity_api: UnityCsReference has no tag {v}; using {pick}", file=sys.stderr)
	return pick


def csref_dir(v: str) -> Path | None:
	done = sorted(CACHE.glob("csref-*/.done"))
	for d in done:
		if d.read_text().strip() == v or d.parent.name == f"csref-{v}":
			return d.parent
	tag = csref_tag(v)
	dest = CACHE / f"csref-{tag}"
	ok = _sparse_clone("https://github.com/Unity-Technologies/UnityCsReference.git", tag, dest,
		["/Runtime/", "/Editor/", "/Modules/"])
	return dest if ok else None


def graphics_dir() -> Path | None:
	dest = CACHE / "graphics-master"
	ok = _sparse_clone("https://github.com/Unity-Technologies/Graphics.git", "master", dest,
		[f"/Packages/{p}/Runtime/" for p in GRAPHICS_FALLBACK] + [f"/Packages/{p}/Editor/" for p in GRAPHICS_FALLBACK]
		+ [f"/Packages/{p}/package.json" for p in GRAPHICS_FALLBACK])
	return dest if ok else None


def package_dirs(v: str) -> list[tuple[str, Path, str]]:
	"""(package, folder, origin label) for each package to index."""
	out: dict[str, tuple[str, Path, str]] = {}
	ed = editor_dir(v)
	sources: list[tuple[Path, str]] = []
	if ed:
		sources.append((ed, f"editor {v}"))
	else:
		g = graphics_dir()
		if g:
			for p in GRAPHICS_FALLBACK:
				d = g / "Packages" / p
				if d.is_dir():
					ver = json.loads((d / "package.json").read_text()).get("version", "?") if (d / "package.json").is_file() else "?"
					out[p] = (p, d, f"Graphics master {ver}, not the {v} build")
		for name, ped in reversed(installed_editors()):
			sources.append((ped, f"editor {name}, not the {v} build"))
	for ed_path, label in sources:
		pm = ed_path / "Resources/PackageManager"
		for p in PACKAGES:
			if p in out:
				continue
			d = pm / "BuiltInPackages" / p
			if d.is_dir():
				out[p] = (p, d, label)
				continue
			tgz = sorted((pm / "Editor").glob(f"{p}-[0-9]*.tgz"))
			if tgz:
				dest = CACHE / "packages" / tgz[-1].stem
				if not (dest / ".done").exists():
					dest.mkdir(parents=True, exist_ok=True)
					with tarfile.open(tgz[-1]) as tf:
						tf.extractall(dest, filter="data") if sys.version_info >= (3, 12) else tf.extractall(dest)
					(dest / ".done").write_text(tgz[-1].name)
				out[p] = (p, dest / "package", label)
	return list(out.values())


def manual_dir(v: str) -> Path | None:
	s = stream(v)
	dest = CACHE / f"manual-{s}"
	if (dest / ".done").exists():
		return dest
	zp = CACHE / f"UnityDocumentation-{s}.zip"
	if not zp.is_file():
		url = f"https://cloudmedia-docs.unity3d.com/docscloudstorage/en/{s}/UnityDocumentation.zip"
		print(f"unity_api: downloading the {s} manual zip (about 500 MB, first use only)", file=sys.stderr)
		CACHE.mkdir(parents=True, exist_ok=True)
		part = zp.with_suffix(".part")
		if subprocess.run(["curl", "-sfL", "-o", str(part), url]).returncode != 0:
			print(f"unity_api: download failed: {url}", file=sys.stderr)
			return None
		part.rename(zp)
	subprocess.run(["rm", "-rf", str(dest)], check=True)
	dest.mkdir(parents=True)
	subprocess.run(["unzip", "-q", str(zp), "Documentation/en/Manual/*", "-d", str(dest)], check=True)
	(dest / ".done").write_text(zp.name)
	return dest


# ---------- C# source parsing ----------

STR_RX = re.compile(r'@"(?:[^"]|"")*"|\$?@?"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])\'')
TYPE_RX = re.compile(r"^((?:(?:public|internal|protected|private|static|sealed|abstract|partial|readonly|unsafe|new|ref|file)\s+)*)"
	r"(class|struct|interface|enum|record(?:\s+struct|\s+class)?)\s+(\w+)")
MODS = {"public", "internal", "protected", "private", "static", "sealed", "abstract", "partial", "readonly", "unsafe",
	"new", "extern", "virtual", "override", "const", "event", "volatile", "async", "required", "ref", "implicit", "explicit"}
NOT_NAMES = {"new", "typeof", "sizeof", "default", "nameof", "operator", "if", "while", "for", "foreach", "switch", "return", "base", "this"}


def _strip(text: str) -> tuple[str, list[str]]:
	strings: list[str] = []
	text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)

	def keep(m: re.Match) -> str:
		strings.append(m.group(0))
		return f'"S{len(strings) - 1}"'
	out = []
	for line in text.split("\n"):
		line = STR_RX.sub(keep, line)
		i = line.find("//")
		out.append(line[:i] if i >= 0 else line)
	return "\n".join(out), strings


def _obsolete(attrs: str, strings: list[str]) -> str | None:
	m = re.search(r"\b(?:System\.)?Obsolete(?:Attribute)?\b\s*(\(([^)]*)\))?", attrs)
	if not m:
		return None
	arg = m.group(2) or ""
	lits = re.findall(r'"S(\d+)"', arg.split(",")[0] if not re.search(r'"S\d+"\s*\+', arg) else arg)
	if lits:
		msg = "".join(strings[int(n)].lstrip("@$").strip('"') for n in lits)
	else:
		msg = arg.split(",")[0].strip() or "obsolete"
	if m.group(2) and re.search(r",\s*true\b", m.group(2)):
		msg += " [error]"
	c = re.match(r"[^\[]*?⟦if ([^⟧]*)⟧", attrs[m.end():])
	if c:
		msg += f" [only when #if {c.group(1)}]"
	return msg


CONST_RX = re.compile(r"\bconst\s+string\s+(\w+)\s*=\s*([^;]+);")


def parse_cs(path: Path, origin: str) -> tuple[list[tuple], list[tuple], list[tuple]]:
	try:
		raw = path.read_text(errors="ignore")
	except OSError:
		return [], [], []
	code, strings = _strip(raw)
	consts = [(m.group(1), re.sub(r'"S(\d+)"', lambda x: strings[int(x.group(1))], m.group(2)).strip())
		for m in CONST_RX.finditer(code)]
	lines = code.split("\n")
	types: list[tuple] = []
	members: list[tuple] = []
	stack: list[tuple] = []  # (kind, name, depth, public)
	ns_file = ""
	depth = 0
	pp: list[str] = []  # active #if conditions
	attrs = ""
	pending: tuple | None = None
	i = 0
	while i < len(lines):
		line = lines[i]
		lineno = i + 1
		# join a declaration whose parameter list runs over several lines
		while line.count("(") > line.count(")") and i + 1 < len(lines) and "{" not in line and ";" not in line:
			i += 1
			line += " " + lines[i].strip()
		i += 1
		s = line.strip()
		if s.startswith("#"):
			d = re.match(r"#\s*(if|elif|else|endif)\b\s*(.*)", s)
			if d:
				kw, cond = d.group(1), d.group(2).strip()
				if kw == "if":
					pp.append(cond)
				elif kw == "elif" and pp:
					pp[-1] = cond
				elif kw == "else" and pp:
					pp[-1] = f"!({pp[-1]})"
				elif kw == "endif" and pp:
					pp.pop()
			continue
		if not s:
			continue
		cond = " && ".join(pp)
		# leading attributes on this line
		while s.startswith("["):
			d, j = 0, 0
			for j, c in enumerate(s):
				d += (c == "[") - (c == "]")
				if d == 0:
					break
			attrs += s[: j + 1] + (f"⟦if {cond}⟧" if cond and "Obsolete" in s[: j + 1] else "")
			s = s[j + 1:].strip()
		body = s
		if body:
			m_ns = re.match(r"namespace\s+([\w.]+)\s*(;)?", body)
			m_t = TYPE_RX.match(body)
			top = stack[-1] if stack else None
			in_type = top is not None and top[0] in ("class", "struct", "interface", "enum", "record") and depth == top[2]
			if m_ns:
				if m_ns.group(2):
					ns_file = m_ns.group(1)
				else:
					pending = ("ns", m_ns.group(1), True)
			elif m_t and (top is None or top[0] == "ns" or in_type):
				mods = m_t.group(1).split()
				kind = m_t.group(2).split()[0]
				public = ("public" in mods or "protected" in mods) and (top is None or top[3])
				outer = [e[1] for e in stack if e[0] != "ns"]
				nss = [e[1] for e in stack if e[0] == "ns"]
				ns = ".".join(([ns_file] if ns_file else []) + nss)
				full = ".".join(([ns] if ns else []) + outer + [m_t.group(3)])
				base = ""
				mb = re.search(r"\b" + re.escape(m_t.group(3)) + r"\s*(?:<[^>]*>)?\s*:\s*([\w.<>, ]+?)(?:\bwhere\b|\{|$)", body)
				if mb:
					base = ", ".join(x.strip() for x in re.split(r",(?![^<]*>)", mb.group(1)) if x.strip())
				if public:
					types.append((full, kind, base, str(path), lineno, _obsolete(attrs, strings), origin))
				pending = (kind, full, public)
			elif in_type and top[3]:
				_member(body, attrs, strings, top, path, lineno, origin, members, cond)
			attrs = ""
		opens = s.count("{")
		closes = s.count("}")
		if pending and opens:
			stack.append((pending[0], pending[1] if pending[0] != "ns" else pending[1], depth + 1, pending[2]))
			pending = None
		depth += opens - closes
		while stack and stack[-1][2] > depth:
			stack.pop()
		if pending and pending[0] != "ns" and s.endswith(";"):
			pending = None  # a declaration with no body (record X(...);)
	return types, members, consts


def _member(body: str, attrs: str, strings: list[str], top: tuple, path: Path, lineno: int, origin: str, out: list, cond: str = "") -> None:
	kind_t, full = top[0], top[1]
	if kind_t == "enum":
		for piece in body.split(","):
			m = re.match(r"\s*(\w+)\s*(=.*)?$", piece.strip("{} ;"))
			if m and m.group(1):
				out.append((full, m.group(1), "enum", piece.strip("{} ;").strip(), str(path), lineno, _obsolete(attrs, strings), origin))
		return
	head = re.split(r"\{|=>", body)[0].strip().rstrip(";").strip()
	words = re.findall(r"[\w]+", head.split("(")[0])  # modifiers before any accessor block
	if kind_t != "interface" and not ({"public", "protected"} & set(words)):
		return
	if "private" in words and "protected" not in words:
		return
	if not head or head.startswith(("using ", "return ", "}")):
		return
	short = full.split(".")[-1]
	lp = head.find("(")
	eq = head.find("=")
	if "operator" in words:
		return
	if re.search(r"\bthis\s*\[", head):
		name, kind = "this[]", "indexer"
	elif lp >= 0 and (eq < 0 or lp < eq):
		pre = head[:lp + 1]
		while re.search(r"<[^<>()]*>", pre):
			pre = re.sub(r"<[^<>()]*>", "", pre)
		m = re.search(r"(~?\w+)\s*\($", pre)
		if not m or m.group(1) in NOT_NAMES:
			return
		name = m.group(1)
		kind = "ctor" if name == short else "method"
	else:
		cut = head[:eq] if eq >= 0 else head
		ids = re.findall(r"\w+", cut)
		if not ids:
			return
		name = ids[-1]
		kind = "event" if "event" in words else ("field" if (eq >= 0 or body.rstrip().endswith(";")) and "{" not in body and "=>" not in body else "property")
	if name in MODS:
		return
	sig = re.sub(r'"S(\d+)"', lambda m: strings[int(m.group(1))], head)
	sig = re.sub(r"\s+", " ", sig) + (f"  [only #if {cond}]" if cond else "")
	out.append((full, name, kind, sig, str(path), lineno, _obsolete(attrs, strings), origin))


# ---------- XML docs ----------

def _xml_text(el: ET.Element | None) -> str:
	if el is None:
		return ""
	return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def parse_xml(path: Path, origin: str) -> list[tuple]:
	rows = []
	try:
		root = ET.parse(path).getroot()
	except ET.ParseError:
		return rows
	for m in root.iter("member"):
		mid = m.get("name") or ""
		if len(mid) < 3 or mid[1] != ":":
			continue
		k, rest = mid[0], mid[2:]
		params = ""
		if "(" in rest:
			rest, params = rest.split("(", 1)
			params = params.rstrip(")")
		if k == "T":
			typ, name = rest.replace("`", "_"), ""
		else:
			typ, _, name = rest.rpartition(".")
			name = re.sub(r"``?\d+$", "", name)
		psum = "; ".join(f"{p.get('name')}: {_xml_text(p)}" for p in m.findall("param"))
		short_params = ", ".join(x.split(".")[-1] for x in re.split(r",(?![^{]*\})", params)) if params else ""
		rows.append((k, typ, name, short_params, _xml_text(m.find("summary")), psum, _xml_text(m.find("returns")), origin))
	return rows


# ---------- index ----------

def index_path(v: str) -> Path:
	return CACHE / f"index-{v}.sqlite"


def build_index(v: str) -> Path:
	CACHE.mkdir(parents=True, exist_ok=True)
	ip = index_path(v)
	tmp = ip.with_suffix(f".tmp{os.getpid()}")
	tmp.unlink(missing_ok=True)
	db = sqlite3.connect(tmp)
	db.executescript("""
		CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
		CREATE TABLE xml(kind TEXT, type TEXT, name TEXT, params TEXT, summary TEXT, params_doc TEXT, returns TEXT, origin TEXT);
		CREATE TABLE types(full TEXT, kind TEXT, base TEXT, file TEXT, line INT, obsolete TEXT, origin TEXT);
		CREATE TABLE members(type TEXT, name TEXT, kind TEXT, sig TEXT, file TEXT, line INT, obsolete TEXT, origin TEXT);
		CREATE TABLE consts(name TEXT, value TEXT);
	""")
	sources = []
	ed = editor_dir(v)
	xd = xml_dir(ed) if ed else None
	if xd:
		print(f"unity_api: indexing XML docs in {xd}", file=sys.stderr)
		seen = set()
		for x in sorted(xd.rglob("*.xml")):
			rows = [r for r in parse_xml(x, f"editor {v} XML") if (r[0], r[1], r[2], r[3]) not in seen]
			seen.update((r[0], r[1], r[2], r[3]) for r in rows)
			db.executemany("INSERT INTO xml VALUES (?,?,?,?,?,?,?,?)", rows)
		sources.append(f"XML docs: {xd}")
	else:
		sources.append(f"XML docs: none (editor {v} not installed; summaries missing)")
	cs = csref_dir(v)
	trees: list[tuple[Path, str]] = []
	if cs:
		trees.append((cs, f"UnityCsReference {(cs / '.done').read_text().strip()}"))
		sources.append(f"engine source: {cs}")
	for p, d, label in package_dirs(v):
		trees.append((d, f"{p} ({label})"))
		sources.append(f"package: {p} — {label} — {d}")
	for tree, origin in trees:
		print(f"unity_api: indexing {origin}", file=sys.stderr)
		for f in tree.rglob("*.cs"):
			rel = str(f.relative_to(tree))
			if re.search(r"(^|/)(Tests?|Samples~|Documentation~|External)/", rel):
				continue
			t, m, c = parse_cs(f, origin)
			db.executemany("INSERT INTO consts VALUES (?,?)", c)
			db.executemany("INSERT INTO types VALUES (?,?,?,?,?,?,?)", t)
			db.executemany("INSERT INTO members VALUES (?,?,?,?,?,?,?,?)", m)
	db.executescript("""
		CREATE INDEX xt ON xml(type); CREATE INDEX xn ON xml(name);
		CREATE INDEX tf ON types(full); CREATE INDEX cn ON consts(name); CREATE INDEX mt ON members(type); CREATE INDEX mn ON members(name);
	""")
	db.execute("INSERT INTO meta VALUES ('format', ?)", (str(INDEX_FORMAT),))
	db.execute("INSERT INTO meta VALUES ('sources', ?)", ("\n".join(sources),))
	db.commit()
	db.close()
	tmp.rename(ip)
	return ip


def _current(ip: Path) -> sqlite3.Connection | None:
	if not ip.is_file():
		return None
	db = sqlite3.connect(f"file:{ip}?mode=ro", uri=True)  # read-only: a rebuild swaps the file under readers
	try:
		if db.execute("SELECT v FROM meta WHERE k='format'").fetchone()[0] == str(INDEX_FORMAT):
			return db
	except (sqlite3.DatabaseError, TypeError):
		pass
	db.close()
	return None


def open_index(v: str) -> sqlite3.Connection:
	ip = index_path(v)
	db = _current(ip)
	if db:
		return db
	CACHE.mkdir(parents=True, exist_ok=True)
	with open(CACHE / f"index-{v}.lock", "w") as lock:
		fcntl.flock(lock, fcntl.LOCK_EX)  # another session may be building the same index
		db = _current(ip)
		if db:
			return db
		return sqlite3.connect(f"file:{build_index(v)}?mode=ro", uri=True)


# ---------- queries ----------

def _short(name: str) -> str:
	return re.sub(r"<.*", "", name.split(".")[-1])


def resolve_type(db: sqlite3.Connection, name: str) -> list[str]:
	if "." in name:
		cands = {r[0] for r in db.execute("SELECT full FROM types WHERE full=? OR full LIKE ?", (name, "%." + name))}
		cands |= {r[0] for r in db.execute("SELECT type FROM xml WHERE kind='T' AND (type=? OR type LIKE ?)", (name, "%." + name))}
	else:
		cands = {r[0] for r in db.execute("SELECT full FROM types WHERE full=? OR full LIKE ?", (name, "%." + name))}
		cands |= {r[0] for r in db.execute("SELECT type FROM xml WHERE kind='T' AND (type=? OR type LIKE ?)", (name, "%." + name))}
		cands = {c for c in cands if c.split(".")[-1] == name}

	def rank(t: str) -> tuple:
		return (not t.startswith("UnityEngine."), not t.startswith("UnityEditor."), t.count("."), t)
	return sorted(cands, key=rank)


def bases_of(db: sqlite3.Connection, full: str) -> list[str]:
	"""Every resolvable base class and interface of a type (all partial declarations)."""
	out: list[str] = []
	for (row,) in db.execute("SELECT DISTINCT base FROM types WHERE full=? AND base!=''", (full,)):
		for b in re.split(r",(?![^<]*>)", row):
			b = re.sub(r"<.*", "", b).strip()
			hits = resolve_type(db, b) if b else []
			if hits and hits[0] not in out and hits[0] != full:
				out.append(hits[0])
	return out


def _is_interface_name(t: str) -> bool:
	n = t.split(".")[-1]
	return len(n) > 1 and n[0] == "I" and n[1].isupper()


def base_of(db: sqlite3.Connection, full: str) -> str:
	"""The base class (not an interface), for display."""
	return next((b for b in bases_of(db, full) if not _is_interface_name(b)), "")


def type_obsolete(db: sqlite3.Connection, full: str) -> str | None:
	row = db.execute("SELECT obsolete FROM types WHERE full=? AND obsolete IS NOT NULL LIMIT 1", (full,)).fetchone()
	return row[0] if row else None


def show_type(name: str) -> int:
	v = version()
	db = open_index(v)
	hits = resolve_type(db, name)
	if not hits:
		close = sorted({r[0] for r in db.execute("SELECT full FROM types WHERE full LIKE ? LIMIT 400", (f"%{name}%",))})[:12]
		print(f"No type {name!r} in Unity {v}." + (f" Close: {', '.join(close)}" if close else ""))
		return 1
	full = hits[0]
	obs = type_obsolete(db, full)
	b = base_of(db, full)
	print(f"# {full} (Unity {v})" + (f" inherits {b}" if b else "") + (f"  [OBSOLETE: {obs}]" if obs else ""))
	if len(hits) > 1:
		print("Also named so: " + ", ".join(hits[1:8]))
	row = db.execute("SELECT summary FROM xml WHERE kind='T' AND type=?", (full,)).fetchone()
	if row and row[0]:
		print(row[0])
	groups: dict[str, dict[str, dict]] = {"Properties": {}, "Fields": {}, "Methods": {}, "Events": {}}
	kmap = {"P": "Properties", "F": "Fields", "M": "Methods", "E": "Events"}
	for k, n, params, summ in db.execute("SELECT kind, name, params, summary FROM xml WHERE type=? AND kind!='T'", (full,)):
		g = groups[kmap.get(k, "Fields")]
		e = g.setdefault(n, {"sig": f"{n}({params})" if k == "M" else n, "summary": summ, "obs": [], "n": 0})
		e["summary"] = e["summary"] or summ
	smap = {"property": "Properties", "indexer": "Properties", "field": "Fields", "enum": "Fields", "method": "Methods", "ctor": "Methods", "event": "Events"}
	for n, kind, sig, obs in db.execute("SELECT name, kind, sig, obsolete FROM members WHERE type=?", (full,)):
		key = "#ctor" if kind == "ctor" else n
		g = groups[smap[kind]]
		e = g.setdefault(key, {"sig": sig, "summary": "", "obs": [], "n": 0})
		e["n"] += 1
		e["obs"].append(obs)
	for label, g in groups.items():
		if not g:
			continue
		print(f"\n## {label}")
		for n in sorted(g):
			e = g[n]
			flag = ""
			if e["obs"] and all(e["obs"]):
				flag = f"  [OBSOLETE: {e['obs'][0][:100]}]"
			elif any(e["obs"]):
				flag = "  [some overloads OBSOLETE]"
			summ = (e["summary"][:90] + "…") if len(e["summary"]) > 90 else e["summary"]
			print(f"- {e['sig'][:140]}{flag}" + (f" — {summ}" if summ else ""))
	src = db.execute("SELECT file, line, origin FROM types WHERE full=? LIMIT 3", (full,)).fetchall()
	for f, ln, origin in src:
		print(f"\nSource: {f}:{ln} ({origin})")
	return 0


def resolve_msg(db: sqlite3.Connection, msg: str) -> str:
	"""An [Obsolete(SomeClass.kConst)] message: look up the constant's text."""
	if not re.fullmatch(r"[\w.]+", msg or ""):
		return msg
	row = db.execute("SELECT value FROM consts WHERE name=? LIMIT 1", (msg.split(".")[-1],)).fetchone()
	return f"{msg} = {row[0]}" if row else msg


def show_member(tname: str, member: str) -> int:
	v = version()
	db = open_index(v)
	hits = resolve_type(db, tname)
	if not hits:
		return show_type(tname)
	chain, todo = [], [hits[0]]
	while todo and len(chain) < 24:
		t = todo.pop(0)
		if t not in chain:
			chain.append(t)
			todo += bases_of(db, t)
	for exact in (True, False):
		for full in chain:
			if exact:
				xr = db.execute("SELECT kind, name, params, summary, params_doc, returns FROM xml WHERE type=? AND name=?", (full, member)).fetchall()
				sr = db.execute("SELECT name, kind, sig, file, line, obsolete, origin FROM members WHERE type=? AND name=?", (full, member)).fetchall()
			else:
				like = f"%{member}%"
				xr = db.execute("SELECT kind, name, params, summary, params_doc, returns FROM xml WHERE type=? AND kind!='T' AND name LIKE ? LIMIT 20", (full, like)).fetchall()
				sr = db.execute("SELECT name, kind, sig, file, line, obsolete, origin FROM members WHERE type=? AND name LIKE ? LIMIT 20", (full, like)).fetchall()
			if not xr and not sr:
				continue
			if full != chain[0]:
				print(f"(inherited from {full})")
			if not exact:
				print(f"No exact member {member!r}; close matches:")
			srcs = list(dict.fromkeys(sr))
			obs = [r for r in srcs if r[5]]
			if exact and obs:
				label = "every declaration" if len(obs) == len(srcs) else f"{len(obs)} of {len(srcs)} declarations"
				print(f"OBSOLETE ({label}): {resolve_msg(db, obs[0][5])}")
				print("Do not use the obsolete form in new code.\n")
			kname = {"P": "property", "F": "field", "M": "method", "E": "event"}
			last = None
			for k, n, params, summ, pdoc, ret in xr:
				head = f"{n}({params})" if k == "M" else n
				print(f"## {full}.{head}  ({kname.get(k, k)})")
				if (summ, pdoc, ret) == last:
					continue
				last = (summ, pdoc, ret)
				if summ:
					print(summ)
				if pdoc:
					print(f"  params: {pdoc}")
				if ret:
					print(f"  returns: {ret}")
			if srcs:
				print("Source declarations:")
			seen = set()
			for n, kind, sig, f, ln, ob, origin in srcs:
				if (sig, ob) in seen:
					continue
				seen.add((sig, ob))
				print(f"- {sig}  ({kind}){'  [OBSOLETE]' if ob else ''}  {Path(f).name}:{ln} [{origin}]")
			return 0
	print(f"{chain[0]} has no member matching {member!r} in Unity {v}. Do not use it.")
	return 1


def find(term: str) -> int:
	v = version()
	db = open_index(v)
	like = f"%{term}%"
	rows: dict[str, str] = {}
	for full, obs in db.execute("SELECT full, obsolete FROM types WHERE full LIKE ?", (like,)):
		if term.lower() in _short(full).lower():
			rows.setdefault(f"type {full}", f"  [OBSOLETE: {obs[:80]}]" if obs else "")
	for (t,) in db.execute("SELECT type FROM xml WHERE kind='T' AND type LIKE ?", (like,)):
		if term.lower() in _short(t).lower():
			rows.setdefault(f"type {t}", "")
	for t, n, kind, obs in db.execute("SELECT type, name, kind, obsolete FROM members WHERE name LIKE ?", (like,)):
		key = f"{t}.{n}  ({kind})"
		if key not in rows or obs is None:
			rows[key] = f"  [OBSOLETE: {obs[:80]}]" if obs else ""
	for t, n, k in db.execute("SELECT type, name, kind FROM xml WHERE kind!='T' AND name LIKE ?", (like,)):
		kind = {"P": "property", "F": "field", "M": "method", "E": "event"}.get(k, k)
		if not any(r.startswith(f"{t}.{n} ") for r in rows):
			rows[f"{t}.{n}  ({kind})"] = ""
	keys = sorted(rows, key=lambda r: (term not in re.split(r"[ .(]", r), "OBSOLETE" in rows[r], not r.split()[-2 if r.startswith("type") else 0].startswith("Unity"), r))
	for k in keys[:80]:
		print(k + rows[k])
	print(f"{len(rows)} hits in Unity {v}" + (" (first 80 shown)" if len(rows) > 80 else ""))
	return 0 if rows else 1


def obsolete(term: str) -> int:
	v = version()
	db = open_index(v)
	like = f"%{term}%"
	n = 0
	for full, obs in db.execute("SELECT DISTINCT full, obsolete FROM types WHERE obsolete IS NOT NULL AND full LIKE ? ORDER BY full", (like,)):
		print(f"type {full}  — {obs[:160]}")
		n += 1
	for t, name, obs in db.execute("SELECT DISTINCT type, name, obsolete FROM members WHERE obsolete IS NOT NULL AND (type LIKE ? OR name LIKE ?) ORDER BY type, name", (like, like)):
		print(f"{t}.{name}  — {obs[:160]}")
		n += 1
	print(f"{n} obsolete declarations match {term!r} in Unity {v}")
	return 0 if n else 1


def _page_title(p: Path) -> str:
	t = p.read_text(errors="ignore")
	m = re.search(r"<title>(.*?)</title>", t, re.S) if p.suffix == ".html" else re.search(r"^#\s+(.+)$", t, re.M)
	return html.unescape(m.group(1).strip()) if m else ""


def docs(term: str) -> int:
	v = version()
	files: list[Path] = []
	md = manual_dir(v)
	if md:
		files += list(md.rglob("*.html"))
	for _, d, _label in package_dirs(v):
		files += list((d / "Documentation~").rglob("*.md")) if (d / "Documentation~").is_dir() else []
	t = term.lower()
	scored = []
	for p in files:
		txt = p.read_text(errors="ignore").lower()
		c = txt.count(t)
		if c:
			scored.append((c + 50 * (t in _page_title(p).lower()), p))
	scored.sort(key=lambda x: -x[0])
	for _, p in scored[:15]:
		print(f"{p}  — {_page_title(p)}")
	print(f"{len(scored)} pages in the Unity {stream(v)} manual and package docs mention {term!r}. Read one with --page <path>.")
	return 0 if scored else 1


def page(path: str) -> int:
	p = Path(path)
	if not p.is_file():
		print(f"No file {path}")
		return 1
	t = p.read_text(errors="ignore")
	if p.suffix == ".html":
		m = re.search(r'<div[^>]*class="section"[^>]*>(.*)<div[^>]*class="footer', t, re.S) or re.search(r"<body[^>]*>(.*)</body>", t, re.S)
		t = m.group(1) if m else t
		t = re.sub(r"<(script|style|nav)[^>]*>.*?</\1>", "", t, flags=re.S)
		t = re.sub(r'<span class="(tooltiptext|tooltipGlossaryLink)"[^>]*>.*?</span>', "", t, flags=re.S)
		t = re.sub(r"<(h[1-4])[^>]*>", "\n\n## ", t)
		t = re.sub(r"<(li)[^>]*>", "\n- ", t)
		t = re.sub(r"<(p|br|tr|div|pre)[^>]*>", "\n", t)
		t = re.sub(r"<[^>]+>", "", t)
		t = html.unescape(t)
		t = re.sub(r"[ \t]+", " ", t)
		t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t).strip()
	print(t)
	return 0


def show_sources() -> int:
	v = version()
	db = open_index(v)
	print(f"Unity {v} (stream {stream(v)}); index {index_path(v)}")
	print(db.execute("SELECT v FROM meta WHERE k='sources'").fetchone()[0])
	print("Installed editors: " + (", ".join(n for n, _ in installed_editors()) or "none"))
	return 0


def main(argv: list[str]) -> int:
	if not argv or argv[0] in ("-h", "--help"):
		print(__doc__)
		return 0
	a = argv[0]
	if a == "--path":
		print(CACHE)
		return 0
	if a == "--rebuild":
		with open(CACHE / f"index-{version()}.lock", "w") as lock:
			fcntl.flock(lock, fcntl.LOCK_EX)
			build_index(version())
		return show_sources()
	if a == "--sources":
		return show_sources()
	if a in ("--find", "--obsolete", "--docs", "--page") and len(argv) < 2:
		print(f"{a} needs an argument")
		return 2
	if a == "--find":
		return find(argv[1])
	if a == "--obsolete":
		return obsolete(argv[1])
	if a == "--docs":
		return docs(" ".join(argv[1:]))
	if a == "--page":
		return page(argv[1])
	if len(argv) == 1:
		return show_type(a)
	return show_member(a, argv[1])


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))

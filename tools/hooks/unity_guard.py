#!/usr/bin/env python3
"""Claude Code hook: block outdated Unity API in .cs files and hand edits of Unity YAML.

Claude Code sends the hook payload as JSON on stdin.
- PostToolUse (Edit, Write, MultiEdit): when the edited file is a .cs file with an outdated or
  unsafe pattern, print the lines and the Unity 6.7 form to stderr and exit 2. The agent sees the
  message and fixes the file at once.
- PreToolUse (Edit, Write, MultiEdit, NotebookEdit, Bash): block a hand edit of Unity YAML
  (.unity, .prefab, .meta, .mat, Assets/**/*.asset ...) before it happens, and block a shell copy
  of a .meta file or an asset folder (duplicate GUIDs). Exit 2 with the reason.
Anything else exits 0. A line that ends in `// unity_guard: allow` is skipped (false positives only).
Every rule was checked against 6000.7.0b2 with tools/unity_api.py; docs/unity-6.md section 7
has the detail. Wire it in .claude/settings.json (see hooks/settings.example.json).
"""
import json
import re
import sys
from pathlib import Path

ALLOW = "unity_guard: allow"

# (pattern, Unity 6.7 form). Patterns run on code with comments and strings removed.
RULES = [
	(r"(?:(?<![\w.])|(?<=UnityEngine\.))Input\.(GetAxis|GetAxisRaw|GetButton|GetButtonDown|GetButtonUp|GetKey|GetKeyDown|GetKeyUp"
		r"|GetMouseButton|GetMouseButtonDown|GetMouseButtonUp|mousePosition|mouseScrollDelta|GetTouch|touchCount|touches"
		r"|anyKey|anyKeyDown|inputString|acceleration|GetJoystickNames|ResetInputAxes)\b",
		"the Input System package: an `InputAction` from `InputSystem.actions` (or the generated actions class), "
		"or `Keyboard.current`, `Mouse.current`, `Gamepad.current`. The old Input Manager is off in this project"),
	(r"\bFindObjects?OfType\b", "`FindObjectsByType<T>()` with no sort mode, or `FindAnyObjectByType<T>()`"),
	(r"\bFindFirstObjectByType\b", "`FindAnyObjectByType<T>()` (FindFirstObjectByType is obsolete in 6.7)"),
	(r"\bFindObjectsSortMode\b", "`FindObjectsByType<T>()` or `FindObjectsByType<T>(FindObjectsInactive.Include)`; the sort-mode overloads are obsolete in 6.7"),
	(r"\b(FindSceneObjectsOfType|FindObjectsOfTypeIncludingAssets)\b", "`FindObjectsByType<T>()`, or `Resources.FindObjectsOfTypeAll<T>()` for assets"),
	(r"\bPhysicMaterial(Combine)?\b", "`PhysicsMaterial` and `PhysicsMaterialCombine` (renamed in Unity 6)"),
	(r"\bGetInstanceID\s*\(", "`GetEntityId()` (GetInstanceID is an obsolete error in 6.7)"),
	(r"\boverride\s+void\s+Execute\s*\(\s*ScriptableRenderContext\b", "`RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData)`; Execute is removed in URP 6.7"),
	(r"\boverride\s+void\s+(OnCameraSetup|Configure)\s*\(\s*CommandBuffer\b", "`RecordRenderGraph(...)`; OnCameraSetup and Configure are removed in URP 6.7"),
	(r"\bConfigure(Target|Clear)\s*\(", "a render graph pass: `builder.SetRenderAttachment(...)` in `RecordRenderGraph`"),
	(r"\bRenderTargetHandle\b", "`TextureHandle` in a render graph pass (or `RTHandle` outside one)"),
	(r"\.camera(Color|Depth)Target(Handle)?\b", "`frameData.Get<UniversalResourceData>().activeColorTexture` (or `activeDepthTexture`) in `RecordRenderGraph`"),
	(r"^\s*using\s+UnityEngine\.Rendering\.PostProcessing\b", "URP post-processing: a `Volume` with a `VolumeProfile` and overrides (`Tonemapping`, `Bloom` ...)"),
	(r"\bnew\s+WWW\s*\(|\bWWW\s+\w+\s*[=;]", "`UnityWebRequest`"),
	(r"\bPhysics\.autoSimulation\b", "`Physics.simulationMode`"),
	(r"\bGraphicsSettings\.renderPipelineAsset\b", "`GraphicsSettings.defaultRenderPipeline`, or `QualitySettings.renderPipeline` per quality tier"),
	(r"\bApplication\.(LoadLevel|LoadLevelAsync|LoadLevelAdditive|loadedLevel|loadedLevelName)\b", "`SceneManager.LoadScene` / `LoadSceneAsync`"),
	(r"\bScreen\.lockCursor\b", "`Cursor.lockState` and `Cursor.visible`"),
	(r"\bEditorApplication\.playmodeStateChanged\b", "`EditorApplication.playModeStateChanged`"),
	(r"\bSceneManager\.UnloadScene\s*\(", "`SceneManager.UnloadSceneAsync`"),
	(r"\bAddRenderPass\s*[<(]", "`renderGraph.AddRasterRenderPass`, `AddComputePass` or `AddUnsafePass` (AddRenderPass is an obsolete error)"),
	(r"\boverride\s+void\s+SetupRenderPasses\s*\(", "`AddRenderPasses` (SetupRenderPasses is removed in URP 6.7)"),
	(r"\b(supportsDynamicBatching|enableDynamicBatching)\b", "nothing: dynamic batching is removed in Unity 6.6. Rely on the SRP Batcher and the GPU Resident Drawer"),
	(r"\b(colliderInstanceID|otherColliderInstanceID|bodyInstanceID|otherBodyInstanceID|InstanceIDToObject)\b", "the EntityId forms (`colliderEntityId`, `Resources.EntityIdToObject`); the InstanceID forms are obsolete errors in 6.7"),
	(r"\bSetActiveRecursively\s*\(", "`SetActive()` (SetActiveRecursively is an obsolete error)"),
	(r"\bCinemachineVirtualCamera\b", "`CinemachineCamera` (Cinemachine 3, namespace `Unity.Cinemachine`)"),
	(r"\bUxml(Factory|Traits)\b", "`[UxmlElement] partial class` with `[UxmlAttribute]` fields (UxmlFactory and UxmlTraits are removed in 6.6)"),
]
# Preprocessor symbols deprecated in 6.6 and removed in 6.8.
PP_OLD = re.compile(r"^\s*#\s*(el)?if\b.*\b(DEVELOPMENT_BUILD|UNITY_64)\b")
COMPILED = [(re.compile(p), fix) for p, fix in RULES]

# Types that derive from UnityEngine.Object. `?.`, `??`, `??=` and `is null` skip Unity's == override,
# so a destroyed object reads as alive.
UNITY_OBJECT_TYPES = {
	"GameObject", "Transform", "RectTransform", "Component", "Behaviour", "MonoBehaviour", "ScriptableObject",
	"Rigidbody", "Rigidbody2D", "Collider", "BoxCollider", "SphereCollider", "CapsuleCollider", "MeshCollider",
	"CharacterController", "Camera", "Light", "Renderer", "MeshRenderer", "SkinnedMeshRenderer", "MeshFilter",
	"LineRenderer", "TrailRenderer", "Material", "Mesh", "Texture", "Texture2D", "Texture3D", "RenderTexture",
	"Cubemap", "Sprite", "Shader", "ComputeShader", "AudioSource", "AudioClip", "AudioListener", "AudioMixer",
	"Animator", "Animation", "AnimationClip", "RuntimeAnimatorController", "ParticleSystem", "Canvas", "Image",
	"RawImage", "Text", "TMP_Text", "TextMeshProUGUI", "TextMeshPro", "Volume", "VolumeProfile", "PlayerInput",
	"NavMeshAgent", "Terrain", "ReflectionProbe", "DecalProjector", "VisualEffect", "PhysicsMaterial", "Font",
	"TextAsset", "UniversalRenderPipelineAsset", "InputActionAsset", "UIDocument", "Joint", "ConfigurableJoint",
}
OBJ_FACTORY = re.compile(r"\b(GetComponent|GetComponentInChildren|GetComponentInParent|FindAnyObjectByType|Instantiate)\s*(<[^<>()]*>)?\s*\([^()]*\)\s*\?[.?]")
HOT_SIG = re.compile(r"\bvoid\s+(Update|FixedUpdate|LateUpdate|OnGUI)\s*\(\s*\)")
HOT_RULES = [
	(re.compile(r"\bResources\.Load(Async|All)?\b"), "load it once in `Awake` or `Start` and keep the reference"),
	(re.compile(r"\bGameObject\.Find(WithTag|GameObjectsWithTag)?\s*\("), "find it once in `Awake` or `Start`, or pass it in by `[SerializeField]`"),
	(re.compile(r"\b(FindAnyObjectByType|FindObjectsByType)\b"), "find it once in `Awake` or `Start`, or pass it in by `[SerializeField]`"),
]
RIGIDBODY_OLD = {"velocity": "linearVelocity", "drag": "linearDamping", "angularDrag": "angularDamping"}

# Unity YAML: scenes, prefabs, meta files and serialized assets. Agents corrupt fileIDs and GUIDs when
# they edit these by hand.
YAML_EXT = {".unity", ".prefab", ".meta", ".mat", ".controller", ".overrideController", ".anim", ".mask",
	".physicMaterial", ".physicsMaterial", ".lighting", ".playable", ".signal", ".renderTexture", ".flare",
	".spriteatlas", ".spriteatlasv2", ".terrainlayer", ".mixer", ".preset", ".brush", ".giparams", ".cubemap"}
YAML_MSG = ("Unity YAML ({what}) must not be edited by hand: agents break fileIDs and GUIDs. Change it with an editor "
	"script run in batchmode (`-executeMethod`), the Unity MCP tools or the bridge. Read-only commands are fine.")


def is_yaml(path: str) -> bool:
	p = Path(path)
	if p.suffix in YAML_EXT:
		return True
	# .asset under Assets/ or Packages/ is serialized data; ProjectSettings/*.asset stays editable.
	return p.suffix == ".asset" and "ProjectSettings" not in p.parts


def strip_code(text: str) -> list[str]:
	"""Remove comments and string contents, keep the line structure."""
	text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
	text = re.sub(r'@"(?:[^"]|"")*"', lambda m: '""' + "\n" * m.group(0).count("\n"), text)
	out = []
	for line in text.split("\n"):
		line = re.sub(r'\$?"(?:\\.|[^"\\])*"', '""', line)
		line = re.sub(r"'(?:\\.|[^'\\])'", "''", line)
		i = line.find("//")
		out.append(line[:i] if i >= 0 else line)
	return out


def unity_object_names(code: str) -> tuple[set[str], set[str]]:
	"""Names declared with a UnityEngine.Object type in this file, and the Rigidbody names among them."""
	types = set(UNITY_OBJECT_TYPES)
	for m in re.finditer(r"\bclass\s+(\w+)\s*(?:<[^>]*>)?\s*:\s*([\w.]+)", code):
		if m.group(2).split(".")[-1] in types:
			types.add(m.group(1))
	alt = "|".join(sorted(types, key=len, reverse=True))
	names, bodies = set(), set()
	decl = re.compile(r"\b(?:UnityEngine\.)?(" + alt + r")\b\??(?!\s*[\[<(.])\s+(\w+(?:\s*,\s*\w+)*)\s*(?=[;=,)])")
	for m in decl.finditer(code):
		for n in re.split(r"\s*,\s*", m.group(2)):
			names.add(n)
			if m.group(1) == "Rigidbody":
				bodies.add(n)
	for m in re.finditer(r"\bvar\s+(\w+)\s*=\s*(?:GetComponent|GetComponentInChildren|GetComponentInParent|AddComponent)\s*<\s*(\w+)\s*>", code):
		if m.group(2) in types:
			names.add(m.group(1))
			if m.group(2) == "Rigidbody":
				bodies.add(m.group(1))
	names -= {"this", "base", "value"}
	return names, bodies


def editor_only(path: Path) -> bool:
	if "Editor" in path.parts:
		return True
	for d in path.parents:
		for a in d.glob("*.asmdef"):
			try:
				plats = json.loads(a.read_text()).get("includePlatforms") or []
			except (OSError, ValueError):
				plats = []
			return plats == ["Editor"]
		if d.name in ("Assets", "Packages") or d == d.parent:
			break
	return False


def scan(text: str, path: Path) -> list[str]:
	raw = text.split("\n")
	lines = strip_code(text)
	code = "\n".join(lines)
	names, bodies = unity_object_names(code)
	null_rx = None
	if names:
		alt = "|".join(sorted(map(re.escape, names), key=len, reverse=True))
		null_rx = re.compile(r"(?<![\w.])(" + alt + r")\s*(\?\.|\?\?=?|\s+is\s+(not\s+)?null\b)")
	rb_rx = None
	if bodies:
		alt = "|".join(sorted(map(re.escape, bodies), key=len, reverse=True))
		rb_rx = re.compile(r"(?<![\w.])(" + alt + r")\s*\.\s*(velocity|drag|angularDrag)\b")
	rb_inline = re.compile(r"GetComponent\s*<\s*Rigidbody\s*>\s*\(\s*\)\s*\.\s*(velocity|drag|angularDrag)\b")
	editor_ok = editor_only(path)
	hits: list[str] = []
	depth = 0
	hot_base, hot_open, hot_line = -1, False, False
	pp: list[bool] = []  # preprocessor stack: True inside #if UNITY_EDITOR

	def hit(n: int, fix: str) -> None:
		hits.append(f"  line {n + 1}: {raw[n].strip()}\n    use {fix}")

	for n, line in enumerate(lines):
		s = line.strip()
		if s.startswith("#"):
			if PP_OLD.match(line) and ALLOW not in raw[n]:
				hit(n, "`Debug.isDebugBuild` at run time, or `UNITY_ENABLE_CHECKS` / `UNITY_INCLUDE_INSTRUMENTATION` (DEVELOPMENT_BUILD and UNITY_64 are deprecated in 6.6, removed in 6.8)")
			if re.match(r"#\s*if\b", s):
				pp.append("UNITY_EDITOR" in s and "!" not in s)
			elif re.match(r"#\s*(else|elif)\b", s) and pp:
				pp[-1] = False
			elif re.match(r"#\s*endif\b", s) and pp:
				pp.pop()
			continue
		if HOT_SIG.search(line):
			hot_base, hot_open, hot_line = depth, False, "=>" in line
		in_hot = hot_base >= 0
		depth += line.count("{") - line.count("}")
		if in_hot and (line.count("{") or depth > hot_base):
			hot_open = True
		skip = ALLOW in raw[n] or not s
		if not skip:
			found = False
			for rx, fix in COMPILED:
				if rx.search(line):
					hit(n, fix)
					found = True
					break
			if not found and not editor_ok and not any(pp) and re.search(r"^\s*using\s+UnityEditor\b|(?<![\w.])UnityEditor\.", line):
				hit(n, "`#if UNITY_EDITOR` around UnityEditor code, or move the file to an Editor folder or an Editor-only asmdef. A player build fails otherwise")
				found = True
			if not found and (rb_rx and rb_rx.search(line) or rb_inline.search(line)):
				m = (rb_rx.search(line) if rb_rx else None) or rb_inline.search(line)
				hit(n, f"`Rigidbody.{RIGIDBODY_OLD[m.group(2) if m.re is rb_rx else m.group(1)]}` (renamed in Unity 6)")
				found = True
			if not found and (null_rx and null_rx.search(line) or OBJ_FACTORY.search(line)):
				hit(n, "an explicit `if (x != null)` or `if (x)` check. `?.`, `??`, `??=` and `is null` skip Unity's null check, "
					"so a destroyed object reads as alive. Add `// unity_guard: allow` only if the type is not a UnityEngine.Object")
				found = True
			if not found and in_hot:
				for rx, fix in HOT_RULES:
					if rx.search(line):
						hit(n, f"{fix}; this call is slow in Update, FixedUpdate, LateUpdate or OnGUI")
						break
		if in_hot and ((hot_open and depth <= hot_base) or hot_line):
			hot_base, hot_open, hot_line = -1, False, False
	return hits


def pre_tool(payload: dict) -> int:
	tool = payload.get("tool_name") or ""
	tin = payload.get("tool_input") or {}
	if tool == "Bash":
		cmd = tin.get("command") or ""
		exts = "|".join(re.escape(e) for e in sorted(YAML_EXT | {".asset"}, key=len, reverse=True))
		target = r"\S*(?:" + exts + r")\b"
		writes = [
			(r"\bsed\s+(-\w*\s+)*-i\b.*" + target, "sed -i"),
			(r"\bperl\s+-\w*i\w*\b.*" + target, "perl -i"),
			(r"(?<![<>&\d])>{1,2}\s*" + target, "a shell redirect"),
			(r"\btee\s+(-a\s+)?" + target, "tee"),
		]
		for rx, what in writes:
			m = re.search(rx, cmd)
			if m and "ProjectSettings/" not in m.group(0):
				print("unity_guard: " + YAML_MSG.format(what=f"{what} on a Unity YAML file"), file=sys.stderr)
				return 2
		# A .meta copy, or a recursive copy of an asset folder. A single new file into Assets/ is fine:
		# Unity makes its .meta on import.
		meta_copy = re.search(r"\b(cp|rsync|ditto)\b[^|;&]*\.meta\b", cmd)
		tree_copy = re.search(r"(\bcp\s+(-\w+\s+)*-\w*[rRa]\w*\b|\brsync\b|\bditto\b)[^|;&]*\bAssets/", cmd)
		if meta_copy or tree_copy:
			print("unity_guard: a shell copy of a .meta file or an asset folder duplicates GUIDs, and Unity then "
				"links the wrong asset. Copy assets with `AssetDatabase.CopyAsset` in an editor script, or let Unity "
				"make a new .meta file (copy the asset without its .meta).", file=sys.stderr)
			return 2
		return 0
	path = tin.get("file_path") or tin.get("notebook_path") or tin.get("path") or ""
	if path and is_yaml(path):
		print("unity_guard: " + YAML_MSG.format(what=Path(path).name), file=sys.stderr)
		return 2
	return 0


def post_tool(payload: dict) -> int:
	tin = payload.get("tool_input") or {}
	path = tin.get("file_path") or tin.get("path") or ""
	if not path.endswith(".cs"):
		return 0
	p = Path(path)
	if not p.is_file():
		return 0
	hits = scan(p.read_text(errors="ignore"), p)
	if not hits:
		return 0
	print(f"unity_guard: outdated or unsafe Unity API in {path}. This repo is Unity 6.7 (URP). Fix these lines:", file=sys.stderr)
	print("\n".join(hits[:20]), file=sys.stderr)
	print("Check an API with: python3 tools/unity_api.py <Type> [member]. Rules: docs/unity-6.md section 7.", file=sys.stderr)
	return 2


def main() -> int:
	try:
		payload = json.load(sys.stdin)
	except (json.JSONDecodeError, ValueError):
		return 0
	if payload.get("hook_event_name") == "PreToolUse":
		return pre_tool(payload)
	return post_tool(payload)


if __name__ == "__main__":
	sys.exit(main())

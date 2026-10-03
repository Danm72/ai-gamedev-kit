#!/usr/bin/env python3
"""The Unity guard (tools/hooks/unity_guard.py) blocks outdated Unity API and hand edits of Unity YAML.

Why: agents trained on Unity 2021 to 2023 write old API (Input.GetAxis, FindObjectsOfType,
ScriptableRenderPass.Execute, rb.velocity). Agents also corrupt .unity, .prefab and .meta files
when they edit the YAML by hand.
The PostToolUse hook scans each .cs file after an Edit or Write. The PreToolUse hook blocks an
Edit, Write or Bash write to a Unity YAML file before it happens. Both exit 2 with the reason.

How: feed the guard hook payloads (JSON on stdin) for fixture files.
No Unity or Godot process is needed, so this test takes no slot.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "tools/hooks/unity_guard.py"
fails = 0


def check(name: str, cond: bool, detail: str = "") -> None:
	global fails
	print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail and not cond else ""))
	fails += 0 if cond else 1


def run(event: str, tool: str, tool_input: dict) -> subprocess.CompletedProcess:
	payload = json.dumps({"hook_event_name": event, "tool_name": tool, "tool_input": tool_input})
	return subprocess.run([sys.executable, str(GUARD)], input=payload, capture_output=True, text=True)


def post(path: Path, tool: str = "Edit") -> subprocess.CompletedProcess:
	return run("PostToolUse", tool, {"file_path": str(path)})


HEAD = "using UnityEngine;\n\npublic class Sub : MonoBehaviour\n{\n"
BAD = {
	"Input.GetAxis": HEAD + "\tvoid Update() { float x = Input.GetAxis(\"Horizontal\"); }\n}\n",
	"Input.GetKeyDown": HEAD + "\tvoid Update() { if (Input.GetKeyDown(KeyCode.Space)) { } }\n}\n",
	"UnityEngine.Input.mousePosition": HEAD + "\tVector3 M() => UnityEngine.Input.mousePosition;\n}\n",
	"FindObjectsOfType": HEAD + "\tvoid Start() { var all = FindObjectsOfType<Sub>(); }\n}\n",
	"FindObjectOfType": HEAD + "\tvoid Start() { var one = Object.FindObjectOfType<Sub>(); }\n}\n",
	"FindFirstObjectByType": HEAD + "\tvoid Start() { var one = FindFirstObjectByType<Sub>(); }\n}\n",
	"FindObjectsSortMode": HEAD + "\tvoid Start() { var all = FindObjectsByType<Sub>(FindObjectsSortMode.None); }\n}\n",
	"rb.velocity": HEAD + "\t[SerializeField] Rigidbody rb;\n\tvoid FixedUpdate() { rb.velocity = Vector3.zero; }\n}\n",
	"rb.drag": HEAD + "\tRigidbody body;\n\tvoid Awake() { body = GetComponent<Rigidbody>(); body.drag = 2f; }\n}\n",
	"GetComponent<Rigidbody>().angularDrag": HEAD + "\tvoid Awake() { GetComponent<Rigidbody>().angularDrag = 1f; }\n}\n",
	"PhysicMaterial": HEAD + "\t[SerializeField] PhysicMaterial mat;\n}\n",
	"GetInstanceID": HEAD + "\tint Id() => gameObject.GetInstanceID();\n}\n",
	"URP Execute": "using UnityEngine.Rendering;\nusing UnityEngine.Rendering.Universal;\nclass P : ScriptableRenderPass\n{\n"
		"\tpublic override void Execute(ScriptableRenderContext context, ref RenderingData data) { }\n}\n",
	"URP OnCameraSetup": "using UnityEngine.Rendering;\nusing UnityEngine.Rendering.Universal;\nclass P : ScriptableRenderPass\n{\n"
		"\tpublic override void OnCameraSetup(CommandBuffer cmd, ref RenderingData data) { }\n}\n",
	"URP Configure": "using UnityEngine.Rendering;\nusing UnityEngine.Rendering.Universal;\nclass P : ScriptableRenderPass\n{\n"
		"\tpublic override void Configure(CommandBuffer cmd, RenderTextureDescriptor d) { ConfigureTarget(t); }\n}\n",
	"RenderTargetHandle": "using UnityEngine.Rendering.Universal;\nclass P\n{\n\tRenderTargetHandle tmp;\n}\n",
	"cameraColorTargetHandle": "class P\n{\n\tvoid F(ScriptableRenderer r) { var c = r.cameraColorTargetHandle; }\n}\n",
	"PostProcessing v2": "using UnityEngine.Rendering.PostProcessing;\nclass P { }\n",
	"WWW": HEAD + "\tvoid Start() { var w = new WWW(\"http://x\"); }\n}\n",
	"Physics.autoSimulation": HEAD + "\tvoid Start() { Physics.autoSimulation = false; }\n}\n",
	"GraphicsSettings.renderPipelineAsset": HEAD + "\tvoid Start() { var a = UnityEngine.Rendering.GraphicsSettings.renderPipelineAsset; }\n}\n",
	"Application.LoadLevel": HEAD + "\tvoid Start() { Application.LoadLevel(1); }\n}\n",
	"?. on a Transform": HEAD + "\t[SerializeField] Transform target;\n\tvoid Update() { var p = target?.position; }\n}\n",
	"?? on a GameObject": HEAD + "\tGameObject a, b;\n\tGameObject Pick() => a ?? b;\n}\n",
	"??= on a component": HEAD + "\tAudioSource src;\n\tvoid Awake() { src ??= GetComponent<AudioSource>(); }\n}\n",
	"GetComponent()?.": HEAD + "\tvoid Start() { GetComponent<Light>()?.gameObject.SetActive(false); }\n}\n",
	"is null on own MonoBehaviour type": HEAD + "\tSub other;\n\tbool Gone() => other is null;\n}\n",
	"Resources.Load in Update": HEAD + "\tvoid Update()\n\t{\n\t\tvar clip = Resources.Load<AudioClip>(\"ping\");\n\t}\n}\n",
	"GameObject.Find in FixedUpdate": HEAD + "\tvoid FixedUpdate()\n\t{\n\t\tvar d = GameObject.Find(\"Dock\");\n\t}\n}\n",
	"FindAnyObjectByType in LateUpdate": HEAD + "\tvoid LateUpdate() { var c = FindAnyObjectByType<Camera>(); }\n}\n",
	"RenderGraph.AddRenderPass": "class P\n{\n\tvoid F(RenderGraph g) { using var b = g.AddRenderPass<Data>(\"x\", out var d); }\n}\n",
	"SetupRenderPasses": "class F : ScriptableRendererFeature\n{\n\tpublic override void SetupRenderPasses(ScriptableRenderer r, in RenderingData d) { }\n}\n",
	"supportsDynamicBatching": "class T\n{\n\tvoid F(UniversalRenderPipelineAsset a) { a.supportsDynamicBatching = true; }\n}\n",
	"colliderInstanceID": HEAD + "\tvoid F(RaycastHit h) { var id = h.colliderInstanceID; }\n}\n",
	"InstanceIDToObject": HEAD + "\tvoid F(int id) { var o = Resources.InstanceIDToObject(id); }\n}\n",
	"SetActiveRecursively": HEAD + "\tvoid F() { gameObject.SetActiveRecursively(false); }\n}\n",
	"CinemachineVirtualCamera": "using Cinemachine;\nclass C : UnityEngine.MonoBehaviour\n{\n\tCinemachineVirtualCamera vcam;\n}\n",
	"UxmlFactory": "class E : VisualElement\n{\n\tpublic new class UxmlFactory : UxmlFactory<E> { }\n}\n",
	"#if DEVELOPMENT_BUILD": HEAD + "#if DEVELOPMENT_BUILD\n\tvoid F() { }\n#endif\n}\n",
	"using UnityEditor in runtime code": "using UnityEditor;\nusing UnityEngine;\npublic class R : MonoBehaviour { }\n",
}
GOOD = (
	"#nullable enable\nusing UnityEngine;\nusing UnityEngine.InputSystem;\nusing UnityEngine.Rendering.RenderGraphModule;\n"
	"#if UNITY_EDITOR\nusing UnityEditor;\n#endif\n\n"
	"public class Sub : MonoBehaviour\n{\n"
	"\t[SerializeField] Rigidbody rb = null!;\n"
	"\t[SerializeField] Transform? target;\n"
	"\t[SerializeField] PhysicsMaterial? mat;\n"
	"\tAudioClip? clip;\n"
	"\tInputAction? move;\n"
	"\tstring? label;\n"
	"\t// Input.GetAxis and FindObjectsOfType in a comment are fine; so is rb.velocity here\n"
	"\tvoid Awake()\n\t{\n"
	"\t\tvar ok = Debug.isDebugBuild;\n"
	"\t\tvar hitId = default(RaycastHit).colliderEntityId;\n"
	"\t\tclip = Resources.Load<AudioClip>(\"ping\");\n"
	"\t\tvar all = FindObjectsByType<Sub>();\n"
	"\t\tvar any = FindAnyObjectByType<Camera>();\n"
	"\t\tvar id = gameObject.GetEntityId();\n"
	"\t\tlabel = label ?? \"none\";\n"
	"\t\tvar n = move?.name;\n"
	"\t\tvar text = \"Input.GetAxis(rb.velocity) FindObjectsOfType target?.x\";\n"
	"\t}\n"
	"\tvoid FixedUpdate()\n\t{\n"
	"\t\trb.linearVelocity = Vector3.zero;\n"
	"\t\trb.linearDamping = 2f;\n"
	"\t\tvar cc = GetComponent<CharacterController>();\n"
	"\t\tvar v = cc.velocity;\n"
	"\t\tvar k = Keyboard.current;\n"
	"\t\tif (target != null) { var p = target.position; }\n"
	"\t}\n"
	"\tvoid Update()\n\t{\n"
	"\t\tvar g = Gamepad.current?.leftStick.ReadValue();\n"
	"\t\tvar p2 = target?.position; // unity_guard: allow\n"
	"\t}\n"
	"}\n"
	"class P : UnityEngine.Rendering.Universal.ScriptableRenderPass\n{\n"
	"\tpublic override void RecordRenderGraph(RenderGraph renderGraph, UnityEngine.Rendering.ContextContainer frameData) { }\n"
	"}\n"
	"class Job { public void Execute() { } }\n"
	"class F : UnityEngine.Rendering.Universal.ScriptableRendererFeature\n{\n"
	"\tpublic override void Create() { }\n"
	"\tpublic override void AddRenderPasses(UnityEngine.Rendering.Universal.ScriptableRenderer r, ref UnityEngine.Rendering.Universal.RenderingData d) { }\n"
	"}\n"
)

with tempfile.TemporaryDirectory() as tmp:
	t = Path(tmp)
	(t / "Assets/Scripts").mkdir(parents=True)
	for name, src in BAD.items():
		p = t / "Assets/Scripts/Bad.cs"
		p.write_text(src)
		r = post(p)
		check(f"blocks {name}", r.returncode == 2 and "unity_guard:" in r.stderr, f"exit {r.returncode}, stderr {r.stderr.strip()[:300]!r}")
	p = t / "Assets/Scripts/Good.cs"
	p.write_text(GOOD)
	r = post(p, "Write")
	check("passes Unity 6.7 code", r.returncode == 0, r.stderr.strip()[:600])

	# Editor code may use UnityEditor without a guard: an Editor folder or an Editor-only asmdef.
	(t / "Assets/Editor").mkdir()
	ed = t / "Assets/Editor/Tool.cs"
	ed.write_text("using UnityEditor;\nusing UnityEngine;\npublic static class Tool { }\n")
	check("allows UnityEditor in an Editor folder", post(ed).returncode == 0)
	(t / "Assets/Tools").mkdir()
	(t / "Assets/Tools/Tools.Editor.asmdef").write_text(json.dumps({"name": "Tools.Editor", "includePlatforms": ["Editor"]}))
	ed2 = t / "Assets/Tools/Build.cs"
	ed2.write_text("using UnityEditor;\npublic static class Build { }\n")
	check("allows UnityEditor under an Editor-only asmdef", post(ed2).returncode == 0)

	txt = t / "notes.txt"
	txt.write_text("Input.GetAxis\n")
	check("ignores non-.cs files after an edit", post(txt).returncode == 0)
	check("ignores a missing file", post(t / "gone.cs").returncode == 0)

	# PreToolUse: hand edits of Unity YAML are blocked by path.
	for f in ("Assets/Scenes/Main.unity", "Assets/Prefabs/Sub.prefab", "Assets/Scripts/Sub.cs.meta", "Assets/Art/Hull.mat", "Assets/Data/Tier.asset"):
		r = run("PreToolUse", "Edit", {"file_path": str(t / f)})
		check(f"PreToolUse blocks an Edit of {f}", r.returncode == 2 and "unity_guard:" in r.stderr, f"exit {r.returncode}")
	r = run("PreToolUse", "Write", {"file_path": str(t / "Assets/New.prefab")})
	check("PreToolUse blocks a Write of a new .prefab", r.returncode == 2 and "unity_guard:" in r.stderr)
	for f in ("Assets/Scripts/Sub.cs", "ProjectSettings/ProjectSettings.asset", "Packages/manifest.json", "docs/unity-6.md"):
		r = run("PreToolUse", "Edit", {"file_path": str(t / f)})
		check(f"PreToolUse allows an Edit of {f}", r.returncode == 0, r.stderr.strip()[:200])
	for cmd in ("sed -i '' 's/a/b/' unity/Assets/Scenes/Main.unity", "echo x > unity/Assets/Sub.prefab",
			"cat a.txt >> unity/Assets/Scripts/Sub.cs.meta", "perl -pi -e 's/x/y/' Assets/Hull.mat",
			"cp unity/Assets/Scripts/A.cs.meta unity/Assets/Scripts/B.cs.meta", "cp -r unity/Assets/Art unity/Assets/Art2",
			"rsync -a unity/Assets/Art/ unity/Assets/Art2/", "ditto unity/Assets/Art unity/Assets/Art3"):
		r = run("PreToolUse", "Bash", {"command": cmd})
		check(f"PreToolUse blocks Bash: {cmd[:50]}", r.returncode == 2 and "unity_guard:" in r.stderr, f"exit {r.returncode}")
	for cmd in ("cat unity/Assets/Scenes/Main.unity", "grep -n guid unity/Assets/Sub.prefab", "git diff -- unity/Assets/Sub.prefab",
			"git mv unity/Assets/A.cs unity/Assets/B.cs", "python3 tools/unity_api.py Rigidbody", "ls unity/Assets > /dev/null",
			"cp assets/hull.glb unity/Assets/Import/hull.glb", "cp -c -R unity/Library ../lane/unity/Library"):
		r = run("PreToolUse", "Bash", {"command": cmd})
		check(f"PreToolUse allows Bash: {cmd[:50]}", r.returncode == 0, r.stderr.strip()[:200])

# No false positive on the kit's own Unity code (the reference bridge).
hits = []
for cs in sorted((ROOT / "bridge/unity").rglob("*.cs")):
	r = post(cs)
	if r.returncode != 0:
		hits.append(f"{cs.relative_to(ROOT)}: {r.stderr.strip()[:200]}")
check("no false positive in bridge/unity", not hits, "; ".join(hits[:5]))

print(f"RESULT test_unity_guard: {'FAIL' if fails else 'PASS'} ({fails} failed)")
sys.exit(1 if fails else 0)

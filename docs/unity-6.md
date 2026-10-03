# Unity 6.7 practices (URP)

Pin: **Unity 6000.7.0b2** (6.7 beta, URP 17.7.0). To move the pin, change `ProjectSettings/ProjectVersion.txt` in your Unity project (or `UNITY_VERSION` in `tools/unity_api.py`). Then run `python3 tools/unity_api.py --rebuild` and check every "6.7 beta" row in this file again.

This file is an engine cheat sheet for agents that write Unity 6.7 URP code. Each class, member, setting and enum below was checked with `tools/unity_api.py` against 6000.7.0b2. A line tagged UNVERIFIED has no local or primary source. A line tagged BETA can change before 6.7 final.

Agents know an older Unity, often 2021 to 2023. Read section 2 and section 7 before you write engine code. The Godot equivalent is `docs/godot-4.7.md`.

## 1. Look it up, do not guess

Use this order for each type, member, attribute or setting that is new to you:

1. `python3 tools/unity_api.py <Type> [member]` gives the 6.7 signature, the XML doc and an OBSOLETE line with the message. It follows base classes and interfaces.
2. `python3 tools/unity_api.py --find <name>` searches every type and member. 0 hits means the name does not exist in the pinned build.
3. `python3 tools/unity_api.py --obsolete <term>` lists obsolete types and members that match.
4. `python3 tools/unity_api.py --docs "<phrase>"` searches the offline 6.7 manual (it includes the URP manual under `Manual/urp/`). Read a page with `--page <path>`.
5. The web comes last. Unity pages: try `curl -s -H "Accept: text/markdown" <url>` first. Code lookups: `curl -s "https://api.firecrawl.dev/v2/search/developer?query=<q>&k=10"`.

The tool reads 3 sources:

- the installed editor's XML docs and built-in package C# (URP, SRP Core, Shader Graph, Input System, Test Framework, uGUI, Cinemachine ...);
- UnityCsReference at tag `6000.7.0b2`, for signatures and `[Obsolete]`;
- the 6.7 manual zip.

The cache is `~/.cache/ai-gamedev-kit/unity-ref/` (`UNITY_REF_DIR` moves it). The first run takes about 1 minute.

Limits of the tool:

- A member that Unity removed gives "no member" and 0 hits in `--obsolete`. No hit in `--obsolete` does not mean "safe". Look up the member itself.
- A declaration or an `[Obsolete]` under `#if` shows `[only #if X]` or `[only when #if X]`. The tool does not know which defines are on. Three defines decide what exists in URP 6.7: `VOLUMETRIC_FOG`, `SURFACE_CACHE_SUPPORTED` and `ENABLE_UPSCALER_FRAMEWORK` (section 9).
- The tool skips package `Tests/` folders, so test helpers such as `InputTestFixture` give 0 hits. Grep the package source for them.
- The offline manual is a mixed build: `WhatsNew.html` stops at 6.4. For 6.5 and 6.6 changes, use the online upgrade guides (section 10).

Two hooks guard each edit (`tools/hooks/unity_guard.py`, test `tests/test_unity_guard.py`):

1. PostToolUse on a `.cs` file blocks the old APIs in section 7 and prints the 6.7 form.
2. PreToolUse blocks an Edit, a Write or a shell write to Unity YAML (`.unity`, `.prefab`, `.meta`, `.mat`, `Assets/**/*.asset` and other serialized assets). It also blocks a shell copy of a `.meta` file or an asset folder. Change those files with an editor script in batchmode (`-executeMethod`) or the Unity MCP tools.

A false positive on one line: end the line with `// unity_guard: allow`. Use it only when the rule is wrong for that line.

## 2. What changed: 2021-2023 → 6.3 → 6.7

### 2.1 From 2021-2023 to 6.0-6.3

| Area | Old (training data) | Now | Since |
|---|---|---|---|
| URP custom pass | `Configure`, `OnCameraSetup`, `Execute(ScriptableRenderContext, ref RenderingData)` | `RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData)`. The old methods are removed in 6.7 (section 2.3). | obsolete 2023.3 |
| Async | Coroutines or `Task` | `Awaitable` (`NextFrameAsync`, `WaitForSecondsAsync`, `FixedUpdateAsync`, `EndOfFrameAsync`, `BackgroundThreadAsync`, `MainThreadAsync`, `FromAsyncOperation`) | 2023.1 |
| Input | `Input.GetAxis`, Input Manager | The Input System package. In 6.7 it ships with the editor (`com.unity.inputsystem` 6.7.0). | 6.7 built in |
| Find objects | `FindObjectOfType`, `FindObjectsOfType` | `FindAnyObjectByType<T>()`, `FindObjectsByType<T>()` | 6.0 |
| Rigidbody | `velocity`, `drag`, `angularDrag` | `linearVelocity`, `linearDamping`, `angularDamping` | by 6.3 |
| Physics material | `PhysicMaterial`, `PhysicMaterialCombine` | `PhysicsMaterial`, `PhysicsMaterialCombine` | by 6.3 |
| Forces | `AddForceAtPosition` torque as in 2022 | With `Acceleration` or `VelocityChange`, torque now scales by the inertia tensor | 6.0 |
| Text | Add `com.unity.textmeshpro` | TextMeshPro lives in `com.unity.ugui`. The namespace is still `TMPro`. | by 6.3 |
| URP pass event | `AfterRendering` runs before the final blit | It runs after the final blit. Use `AfterRenderingPostProcessing` for the old spot. | 6.2 |
| Mesh LOD | LOD Group only | Mesh LOD: generated on import, 1 mesh, `QualitySettings.meshLodThreshold` | 6.2 |
| Serialization | `[SerializeField]` on a property compiles | Compile error. Use `[field: SerializeField]`. | 6.3 |
| UI | UI Toolkit is the runtime default | The manual recommends uGUI for runtime UI and UI Toolkit for editor UI | 6.6 manual |
| 3D physics | PhysX (or Jolt, as in Godot 4.6) | Still PhysX. Unity has no Jolt. The PhysX SDK version is UNVERIFIED. | n/a |
| DOTS | Entities is an optional package | Entities, Collections, Entities Graphics are core packages; Mathematics (6.5) and Burst (6.6) are engine modules. | 6.4-6.6 |

### 2.2 From 6.3 to 6.4, 6.5 and 6.6

| Change | Version | What to do |
|---|---|---|
| URP Compatibility Mode and the `URP_COMPATIBILITY_MODE` define are removed. `RenderGraphSettings` is obsolete. | 6.4 | Write every pass for Render Graph. |
| `FindObjectsSortMode` and the sort-mode overloads of `FindObjectsByType` are obsolete. | 6.4 | Call `FindObjectsByType<T>()` with no sort mode. |
| `Object.Destroy` calls `OnDisable` on all descendants, not only direct children. | 6.4 | Remove hand-made propagation. |
| Disabling `com.unity.modules.physics` breaks local Volumes. | 6.4 | Keep the physics module. |
| The Built-in Render Pipeline is deprecated (supported through the 6.7 LTS). Projector, LensFlare and Halo are obsolete. | 6.5 | URP only. |
| `GetInstanceID()` is an obsolete **error**. `EntityId` is 8 bytes. | 6.5 | Use `GetEntityId()`. Never cast an `EntityId` to `int`. |
| `FindFirstObjectByType` is obsolete. | 6.5 | Use `FindAnyObjectByType<T>()`. |
| `gameObject.rigidbody`, `.renderer`, `.collider`, `AddComponent(string)` are removed. | 6.5 | Use `GetComponent<T>()`. |
| `[OnEnteringPlayMode]`, `[OnExitingPlayMode]`, `[AutoStaticsCleanup]` added. | 6.5 | Reset statics with them (section 4.4). |
| The BCL includes `System.Text.Json` and `System.Collections.Immutable`. | 6.5 | Do not ship your own copies. |
| A Roslyn analyzer reports fields that do not serialize (UAC codes). | 6.5 | Fix each UAC warning. |
| New projects enter Play mode with **no domain reload** ("Reload Scene only"). | 6.6 | Static fields and static events survive between Play runs (section 4.4). |
| `[SerializeField] Dictionary<TKey,TValue>` serializes. | 6.6 | No wrapper class needed. `JsonUtility` support is UNVERIFIED (section 9). |
| Dynamic batching is removed (`supportsDynamicBatching` is an error). | 6.6 | Use the SRP Batcher and the GPU Resident Drawer. |
| `DEVELOPMENT_BUILD` and `UNITY_64` defines are deprecated (removed in 6.8). | 6.6 | Use `Debug.isDebugBuild`, `UNITY_ENABLE_CHECKS`, `UNITY_INCLUDE_INSTRUMENTATION`. |
| Cinemachine 3 is a core package. `CinemachineVirtualCamera` is obsolete. | 6.6 | Use `CinemachineCamera` (`Unity.Cinemachine`). |
| UI Toolkit `UxmlFactory` and `UxmlTraits` are removed. | 6.6 | Use `[UxmlElement] partial class` with `[UxmlAttribute]`. |

### 2.3 Unity 6.7 (BETA, every row)

| Change | What to do |
|---|---|
| `ScriptableRenderPass.Execute`, `Configure`, `OnCameraSetup`, `ConfigureTarget`, `ConfigureClear` and `ScriptableRenderer.cameraColorTargetHandle` are removed. `ScriptableRendererFeature.SetupRenderPasses` is removed. | Only `RecordRenderGraph` exists. See the pass shape below. |
| New URP look features: Screen Space Reflections, Surface Cache GI, GTAO (a mode of SSAO), AgX tonemapping. | Section 5. Unity says they reach "broad availability" with 6.7 LTS. |
| SSAO settings on the renderer feature are no longer applied. | Set SSAO on the Volume override `ScreenSpaceAmbientOcclusionVolumeOverride`. |
| The upscaler moves to a priority list (DLSS, FSR 2 to 4, MetalFX, STP) behind `ENABLE_UPSCALER_FRAMEWORK`. The manual still shows the old "Upscaling Filter". | Which one is live is UNVERIFIED (section 9). |
| `useNativeRenderPass` is ignored: Render Graph always merges native passes. | Do not set it. |
| Enlighten real-time GI APIs (`DynamicGI.*`) are deprecated. | Do not use real-time Enlighten. |
| `UnityEngine.Rendering.ListPool`, `GenericPool`, `DictionaryPool`, `HashSetPool` are deprecated. | Use `UnityEngine.Pool.*`. |
| `TouchInputModule` and `StandaloneInputModule.inputMode` are removed. | Use `InputSystemUIInputModule`. |
| Input System, Cinemachine, Entities, Timeline and `com.unity.steam.platform` 1.0.0 (Steam build profiles) ship in the editor as 6.7.0. | Do not pin old registry versions in `manifest.json`. |
| Experimental CoreCLR players (.NET 10). The editor still runs Mono. | Ship Mono or IL2CPP players. Do not pick CoreCLR. |
| C# stays at 9.0. | No C# 10 or later syntax (section 4.1). |

The Render Graph pass shape (names checked in 6.7; adapt the body):

```csharp
class TintPass : ScriptableRenderPass
{
	class PassData { public TextureHandle src; public Material mat; }
	Material _mat;

	public override void RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData)
	{
		var res = frameData.Get<UniversalResourceData>();
		if (res.isActiveTargetBackBuffer) return;
		// A pass cannot read and write one texture, so draw into a new one and make it the camera colour.
		var desc = renderGraph.GetTextureDesc(res.activeColorTexture);
		desc.name = "TintColor";
		var dst = renderGraph.CreateTexture(desc);
		using (var builder = renderGraph.AddRasterRenderPass<PassData>("Tint", out var data))
		{
			data.src = res.activeColorTexture;
			data.mat = _mat;
			builder.UseTexture(data.src, AccessFlags.Read);
			builder.SetRenderAttachment(dst, 0, AccessFlags.Write);
			builder.SetRenderFunc((PassData d, RasterGraphContext ctx) =>
				Blitter.BlitTexture(ctx.cmd, d.src, new Vector4(1, 1, 0, 0), d.mat, 0));
		}
		res.cameraColor = dst;
	}
}
```

For a full-screen effect with no C#, use `FullScreenPassRendererFeature` with a material. It is the URP match for the Godot `CompositorEffect`.

## 3. Project setup checklist

Decide each of these settings early, and write the choice in your project notes so agents keep it. The values are a tested baseline for an agent-built URP project.

| Setting | Value | Where |
|---|---|---|
| Editor | 6000.7.0b2, with the build support modules you ship (for example, Mac and Linux Mono) | `ProjectSettings/ProjectVersion.txt` |
| Render pipeline | URP. 1 URP asset and 1 Universal Renderer per quality level (for example, Mac, PC and Steam Deck tiers). `GraphicsSettings.defaultRenderPipeline` stays empty or a fallback; each quality level sets `customRenderPipeline`. | `QualitySettings.asset`, your settings folder |
| Tier at run time | All Standalone players (Mac, Linux, Steam Deck) share 1 default quality level. The game picks the tier: `QualitySettings.SetQualityLevel(int, bool)`, or `-screen-quality <Name>` in the launch options. | game code |
| Rendering path | Forward+ on every renderer (`RenderingMode.ForwardPlus`). The GPU Resident Drawer needs Forward+ or Deferred+. | Universal Renderer asset |
| Colour space | Linear (`PlayerSettings.colorSpace = ColorSpace.Linear`) | `ProjectSettings.asset` |
| HDR | On (`supportsHDR`), 32-bit buffer | URP asset |
| Tonemap | `TonemappingMode.AgX` in the global Volume | Volume profile |
| Active input handling | Input System only (`activeInputHandler: 1`). Old `Input.*` calls then throw `InvalidOperationException`. No public API sets it; an editor script writes it through `SerializedObject`, and the editor restarts. | `ProjectSettings.asset` |
| Input actions | 1 project-wide actions asset (`InputSystem.actions`). An editor script can make it from your controls table, so action names stay stable. A `PlayerInput` component is optional. | input actions asset |
| Fixed timestep | The Unity default is 0.02 s (50 Hz). Set 0.0166667 s (60 Hz) if game logic or tests count 60 Hz ticks. | `TimeManager.asset` |
| Physics stepping | For lockstep (replayable test runs): `Physics.simulationMode = SimulationMode.Script` and `Physics.Simulate(1/60)` per tick | game or test code |
| Enter Play Mode | No domain reload (the 6.7 default; the URP template turns off scene reload too). Code must be safe with static fields. | `EditorSettings.asset` |
| Serialization | Force Text; Visible Meta Files | `EditorSettings.asset`, `VersionControlSettings.asset` |
| Assemblies | 1 asmdef per feature under your runtime folder (`autoReferenced: false`), 1 Editor-only asmdef (`includePlatforms: ["Editor"]`), test asmdefs. Pure logic asmdefs use `noEngineReferences: true`. Test assemblies cannot reference `Assembly-CSharp`, so no game code lives outside an asmdef. | `*.asmdef` (JSON; agents may write them, Unity makes the `.meta`) |
| Static-reset analyzer | On for each game asmdef: a `<asmdefName>.globalconfig` beside the `.asmdef` with `is_global = true` and `build_property.UnityEnableAutoStaticsCleanupAnalysis = true` | next to each asmdef |
| Tests | Test Framework 1.9.0 (core package). EditMode for pure logic. Gameplay tests can run on built players through a JSON bridge (`bridge/unity/`). | your tests folder |
| Data | If agents tune the game, keep balance values in JSON as the one source. Load with `com.unity.nuget.newtonsoft-json` 3.2.2 or `JsonUtility` with `[Serializable]` wrappers. ScriptableObjects are harder for agents to edit (Unity YAML). | `Packages/manifest.json` |
| Scenes and prefabs | Made by editor scripts in batchmode. Never edited by hand. | your Editor folder |
| Git | `.gitignore` ignores `Library/ Temp/ Obj/ Build/ Builds/ Logs/ UserSettings/ MemoryCaptures/ Recordings/ *.csproj *.sln InitTestScene*.unity*` | `.gitignore` |
| Packages | Core packages (URP 17.7.0, Test Framework, uGUI, Input System, Cinemachine) follow the editor version and cannot be pinned. Commit `Packages/manifest.json` and `packages-lock.json`. | `Packages/` |

### Batchmode commands

On macOS the Unity Hub installs the editor binary at `/Applications/Unity/Hub/Editor/6000.7.0b2/Unity.app/Contents/MacOS/Unity`. One project folder holds one Unity process at a time.

```bash
# EditMode tests. Never add -quit to -runTests: it ends the run before the tests finish.
Unity -batchmode -nographics -projectPath <project> -runTests -testPlatform EditMode \
      -testResults "$PWD/editmode.xml" -logFile - [-testFilter "Ns.Class.Method"]
# An editor job (scene build, import, player build)
Unity -batchmode -quit -projectPath <project> -executeMethod MyGame.EditorTools.Build.Linux -logFile -
```

| Fact | Detail |
|---|---|
| `-runTests` exit codes (Test Framework source) | 0 pass, **also when 0 tests ran**; 2 tests failed; 3 run error or compile errors; 4 platform not found. Read the `total` count in the results XML too. |
| `-executeMethod` | A static method in the Editor asmdef. Exit with `EditorApplication.Exit(code)`, or throw (exit code 1). Write a status JSON file; do not parse the log. |
| `-nographics` | No graphics device and no GI bake. Use it for EditMode tests and logic-only players. PlayMode tests and screenshots need a GPU (Mac Metal, PC Vulkan under Xvfb). |
| `-logFile -` | Log to stdout. With `-nographics` the log is off unless you pass `-logFile`. |
| `-accept-apiupdate` | Without it, the API Updater does not run in batchmode. Do not rely on the updater: write 6.7 API. |
| Build target | Give `-buildTarget Linux64` or `-activeBuildProfile <asset>` on the command line. In batchmode `SwitchActiveBuildTargetAsync` and `BuildProfile.SetActiveBuildProfile` do not switch. One process per target. |
| Build API | `BuildPipeline.BuildPlayer(BuildPlayerOptions)`; check `report.summary.result == BuildResult.Succeeded`. `BuildTarget.StandaloneLinux64`. |
| Compile errors | The batchmode start stops on compile errors. Read the `error CS` lines in the log. Never pass `-ignorecompilererrors` in CI. |
| Batch imports | `AssetDatabase.StartAssetEditing()` and `StopAssetEditing()` in try/finally, then `AssetDatabase.SaveAssets()`. `AssetDatabase.Refresh()` after files change on disk. |
| Player args | `-batchmode`, `-nographics`, `-logFile -`, `-screen-width`, `-screen-height`, `-screen-fullscreen 0`, `-screen-quality <Name>`, `-force-vulkan`. Unknown args reach `Environment.GetCommandLineArgs()`. |

## 4. C# rules

### 4.1 Language

1. C# 9.0 with Roslyn. Not supported: `init` setters, covariant returns, module initializers, `SkipLocalsInit`. Records need a user `IsExternalInit` and do not serialize.
2. `#nullable enable` compiles and helps with plain C# types. It cannot see a destroyed `UnityEngine.Object` (4.3). A non-null `Transform` field can still hold a destroyed object.
3. Never call `Task.Result` or `Task.Wait()` on the main thread: it deadlocks.
4. No finalizers in runtime code.
5. Tabs. One class per file, and the file name matches the class (a MonoBehaviour must match, or Unity cannot attach it). `PascalCase` types and methods, `_camelCase` private fields, `camelCase` locals.

### 4.2 Serialization

1. Use `[SerializeField] private` fields, not public fields. Expose a read-only property when other code needs the value.
2. A field serializes when it is public or `[SerializeField]`, and not static, const or readonly. Its type must be serializable: primitives, enums, Unity structs (`Vector3`, `Color`, `AnimationCurve`), `[Serializable]` classes and structs, `UnityEngine.Object` references, arrays and `List<T>` of these. Since 6.6, a `Dictionary<K,V>` with `[SerializeField]` also serializes.
3. Properties never serialize. An auto-property serializes only with `[field: SerializeField]`.
4. `[Serializable]` is not inherited. Mark each class in the hierarchy.
5. No `List<List<T>>` and no jagged or multidimensional arrays. Wrap the inner collection in a `[Serializable]` type.
6. Default serialization cannot hold null, copies shared references and drops subclass fields. Use `[SerializeReference]` (classes only) for null, sharing or polymorphism.
7. ScriptableObjects hold design-time data that the editor makes. Every user shares 1 instance. A run-time write in the editor changes the asset on disk and the next run; the same code in a player resets on each launch. Keep run-time state out of ScriptableObjects, or `Instantiate(so)` for a per-run copy.

### 4.3 Fake null: Unity's == on destroyed objects

1. `UnityEngine.Object` overloads `==` and `!=`. A destroyed object compares `== null` as true, but the C# reference is not null.
2. `?.`, `??`, `??=`, `is null`, `is not null` and `ReferenceEquals` test only the C# reference. On a destroyed object they read "alive", and the next call throws `MissingReferenceException`.
3. Write `if (target != null)` or `if (target)`. Never write `target?.position` or `a ?? b` on a `UnityEngine.Object` type. The guard blocks the common forms.
4. `?.` and `??` are fine on plain C# types (`string`, `InputAction`, your own non-Unity classes).
5. `Object.Destroy` is deferred to the end of the frame. The object is still there this frame. `DestroyImmediate` is for editor code only.
6. Destroyed MonoBehaviours and ScriptableObjects never come back.

### 4.4 Statics and Play mode (no domain reload)

1. With no domain reload, static fields, static events and non-serialized fields keep their values from the last Play run.
2. Reset each static with one of these tools, one per assembly:
   - `[OnEnteringPlayMode]` or `[OnExitingPlayMode]` on a static method (6.5+). Code that also runs in Edit mode resets on entering.
   - `[AutoStaticsCleanup]` on a `partial` class with no static constructor (6.5+). Inline initializers run once per editor session, not once per Play run.
   - `[RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]` (works in 6.3 and 6.7).
3. Turn on the static-reset analyzer in each game asmdef (section 3). It lists statics with no reset (UAL0010 to UAL0014).
4. `DontDestroyOnLoad` objects also survive Play runs when scene reload is off. Guard against a second copy.
5. PlayMode tests share statics between tests. Reset them in `[SetUp]` or `[UnitySetUp]`.
6. Background work keeps running after Play mode stops. Pass `Application.exitCancellationToken`.

### 4.5 Lifecycle, time and physics

1. Order: `Awake`, `OnEnable`, `Start`, `FixedUpdate` (physics step after it), `Update`, `LateUpdate`, render, `OnDisable`, `OnDestroy`.
2. The order of the same event across different objects is not fixed. Set it with `[DefaultExecutionOrder(n)]`.
3. Move bodies in `FixedUpdate` (or the lockstep tick). Read input in `Update`.
4. Set `Rigidbody.interpolation = RigidbodyInterpolation.Interpolate` on the player body. A camera in `LateUpdate` then moves smoothly. This is the match for the Godot physics interpolation.
5. With interpolation on, the physics system controls the body's transform. After a direct transform change (a teleport), call `Physics.SyncTransforms()`, or Unity ignores the change (manual `rigidbody-interpolation.html`).
6. `Time.deltaTime` in `Update`, `Time.fixedDeltaTime` in `FixedUpdate`.
7. Physics queries: 3D `Physics.RaycastNonAlloc` and `OverlapSphereNonAlloc` are fine in 6.7. Only the `Physics2D.*NonAlloc` forms are obsolete.

### 4.6 Async: Awaitable, coroutines, Task

1. Prefer `async Awaitable` methods to coroutines for new code.
2. Unity pools `Awaitable` instances. Never await one instance twice. Wrap it in a `Task` for `WhenAll`.
3. Pass `destroyCancellationToken` to every await in a component. This is the C# match for the Godot rule "check `is_instance_valid(self)` after `await`".
4. `BackgroundThreadAsync()` moves the rest of the method off the main thread. Call `MainThreadAsync()` before you touch any Unity API. A release player does not check this; it crashes.
5. Many `while (true) await Awaitable.NextFrameAsync()` loops scale badly. Use 1 central update instead.
6. `async void` hides exceptions. Use `async Awaitable` and await it, or catch inside.

### 4.7 No allocations per frame

1. Cache `GetComponent` results in `Awake`. Use `TryGetComponent` when the component can be missing.
2. No LINQ, no string concatenation, no `new List<T>()`, no lambdas that capture, in `Update`, `FixedUpdate` or `LateUpdate`.
3. Never call `Resources.Load`, `GameObject.Find` or `FindAnyObjectByType` / `FindObjectsByType` per frame. The guard blocks them in those methods.
4. Cache `WaitForSeconds` objects; reuse lists and arrays.
5. Many `Update` methods cost per instance. Use a manager that updates many objects.
6. Incremental GC is on by default (`PlayerSettings.gcIncremental`). Keep it on unless a profile says otherwise.
7. Prefer C# `event Action<T>` to `UnityEvent` in code. Agents do not use the Inspector. Use `UnityEvent` only where uGUI needs it.

## 5. Lighting and look (URP 6.7)

Godot equivalent: `docs/godot-4.7.md` section 5.

### 5.1 Volumes and colour bands

1. Post-processing lives in `Volume` components with a `VolumeProfile` and overrides. Global volumes use `isGlobal`.
2. The live blended value is `VolumeManager.instance.stack.GetComponent<T>()`. Read a profile with `profile.TryGet<T>(out var x)`.
3. Colour bands by depth, height or zone: 1 global Volume per band, and a script sets each `weight` from the camera position. Or 1 Volume whose overrides a script lerps.
4. A colour tint (for example, underwater): `ColorAdjustments.colorFilter`. Red absorption with depth: `ChannelMixer`.
5. `volumeFrameworkUpdateMode` on the URP asset: Every Frame, or Via Scripting (cheaper when volumes change rarely).

### 5.2 Global illumination

| GI | Where set | Fit |
|---|---|---|
| Surface Cache GI (BETA, new in 6.7) | Renderer feature `SurfaceCacheGIRendererFeature` + Volume override `SurfaceCacheGIVolumeOverride` | The nearest match to Godot SDFGI: dynamic, no bake, diffuse only. Needs Static Batching off and Default Mesh Buffer Target = Raw. Metal and Vulkan get only the compute fallback. Whether Mac and Linux players compile it (`SURFACE_CACHE_SUPPORTED`) is UNVERIFIED. Turn it off on a low tier. |
| Baked lightmaps, APV | Bake | Static only. Terrain and props built in code do not fit. |
| Enlighten real-time GI | Bake | Deprecated in 6.7, and it blocks the GPU Resident Drawer. Do not use. |

### 5.3 Fog

1. The default URP fog is `RenderSettings` fog: `fogMode` (`FogMode.Linear`, `Exponential`, `ExponentialSquared`), `fogDensity`, `fogColor`, `fogStartDistance`, `fogEndDistance`. Distance only, cheap. No height fog.
2. The URP source holds a volumetric fog (`VolumetricFogRendererFeature`, Volume override `FogVolumeComponent`, per light `UniversalAdditionalLightData.affectsVolumetricFog`). Every file sits under `#if VOLUMETRIC_FOG`, and nothing sets that define. A default project does not compile it. Whether a project define turns it on is UNVERIFIED.
3. Other volumetric options: the MIT `CristianQiu/Unity-URP-Volumetric-Light` (render graph; README says up to 6000.6, so 6.7 is UNVERIFIED), or paid assets. A cheap fallback: distance fog plus lamp beam cards.
4. Cut fog variants: Graphics Settings > Shader Build Settings can set the `FOG_LINEAR FOG_EXP FOG_EXP2` keyword set to dynamic branch.
5. God rays: keep fog density low and light scattering strong, as in Godot.

### 5.4 Tonemap and post

| Override | Use |
|---|---|
| `Tonemapping` | `mode = TonemappingMode.AgX` (BETA, new in 6.7). Tune `agxContrast` (default 1.193) and `agxMidGrey` (default 0.18). AgX has no white-point member, so Godot's `tonemap_agx_white` has no match. |
| `ColorAdjustments` | `colorFilter` (a band tint), `contrast`, `saturation`, `postExposure` |
| `ExposureVolume` | New. Fixed exposure only (`fixedExposure`); no auto exposure yet. |
| `Bloom` | Glow for lamps and emissives. Retune after a tonemap change. |
| `ScreenSpaceLensFlare` | `chromaticAbberationIntensity` is renamed `chromaticAberrationIntensity` in 6.7. |
| `Vignette`, `FilmGrain`, `ChromaticAberration`, `LensDistortion`, `DepthOfField`, `MotionBlur` | Present. Turn them off on a low tier unless a key shot needs them. |
| `colorGradingMode` (URP asset) | HDR on desktop tiers; LDR is the cheap low-tier setting. |

### 5.5 AO and reflections

1. SSAO and GTAO: the renderer feature `ScreenSpaceAmbientOcclusion` must be on the renderer. Set every value on the Volume override `ScreenSpaceAmbientOcclusionVolumeOverride` (6.7). `mode` is `ScreenSpaceAmbientOcclusionMode.SSAO` or `GTAO` (BETA). GTAO costs a little more than SSAO and always uses depth-normals.
2. Screen Space Reflections (BETA): renderer feature `ScreenSpaceReflectionRendererFeature` + Volume override `ScreenSpaceReflectionVolumeSettings`. Screen-space ray march only; off-screen rays fall back to reflection probes. Needs the depth-normals prepass. Hierarchical marching needs compute. SSR adds little in dense fog or murky water; it fits shiny floors and interiors.

### 5.6 Lights, shadows, caustics, particles

1. Forward+ ignores `maxAdditionalLightsCount` per object; the limit is 256 lights per camera.
2. Shadow cost: `mainLightShadowmapResolution`, `additionalLightsShadowmapResolution`, `shadowDistance`, `shadowCascadeCount`, and per light `UniversalAdditionalLightData.softShadowQuality`.
3. New in 6.7: `UniversalRenderPipelineAsset.lightFalloffMode` (`LightFalloffMode.InverseSquared` or `Linear`). Which one matches Godot's attenuation is UNVERIFIED; compare in a shot.
4. Caustics have 3 options:
   - a light cookie on the sun (`Light.cookie`; tile it with `UniversalAdditionalLightData.lightCookieSize` and animate `lightCookieOffset`);
   - a `DecalProjector` with the `DecalRendererFeature`;
   - a world-space XZ sample in the terrain shader (the Godot method).
5. Floating particles (dust, marine snow): a ParticleSystem or VFX Graph (built in). Mesh LOD does not apply to them.
6. A first-person cabin (a cockpit or a vehicle interior) can use 2 stacked cameras. One is the world camera; the other is an overlay cabin camera on its own layer. Rendering layers keep the cabin lights on the cabin.

### 5.7 What looks cheap (carried over from Godot, still true)

- Ambient light too high and key light too weak: flat contrast.
- No fog and no AO: no depth.
- No tonemap (`TonemappingMode.None`): clipped highlights.
- Primitive cubes or a low-poly kit in a shot.

## 6. Performance and the Steam Deck

Godot equivalent: `docs/godot-4.7.md` section 6.

### 6.1 Shader and pipeline stutter

1. Use `GraphicsStateCollection` (PSO tracing). Trace in a Development build with `BeginTrace()` and `EndTrace()`, save with `SaveToFile(path)` or `SendToEditor(fileName)`, and warm up at load with `WarmUp()` or `WarmUpProgressively(count)`.
2. Trace 1 collection per graphics API and GPU: for example, Metal on the Mac, Vulkan on a PC (NVIDIA), Vulkan on the Steam Deck (RADV).
3. Graphics Settings > Shader loading can preload a collection and warm it up at start, with no code.
4. Do not use `ShaderVariantCollection.WarmUp()` or `Shader.WarmupAllShaders()` on Metal or Vulkan. The manual says they "can create the wrong PSOs".
5. Compute shaders are not traced: GTAO compute, hierarchical SSR, Surface Cache GI and STP compile on first use. Show them once behind the title or a fade.
6. `PlayerSettings.strictShaderVariantMatching` shows a missing variant as the error shader with a log line. Use it to find stripped variants.
7. `GraphicsSettings.logWhenShaderIsCompiled` logs each compile in play. Count PSO creates with a `ProfilerRecorder` on `CreateGraphicsGraphicsPipelineImpl`.
8. Unity frees a variant when nothing references it, and compiles it again on the next use (the same trap as in Godot; see `docs/godot-4.7.md` section 6). Keep a reference to play-only materials.
9. Set render features at load. Assume that a feature turned on in play (SSAO, SSR, an MSAA change) compiles new pipelines (UNVERIFIED for Unity; true for Godot).

### 6.2 Batching, culling, LOD

1. SRP Batcher on (`useSRPBatcher`). It cuts CPU cost.
2. GPU Resident Drawer (`gpuResidentDrawerMode = GPUResidentDrawerMode.InstancedDrawing`): needs Forward+ or Deferred+ on every renderer, compute shaders, BatchRendererGroup Variants = Keep All (`EditorGraphicsSettings.batchRendererGroupShaderStrippingMode`), and the SRP Batcher. Objects with a `MaterialPropertyBlock` or `OnBecameVisible` fall back to the normal path.
3. GPU occlusion culling needs the GPU Resident Drawer: `gpuResidentDrawerEnableOcclusionCullingInCameras`. It can cost more than it saves in open scenes. Measure it.
4. `smallMeshScreenPercentage` culls tiny objects in the GPU Resident Drawer.
5. Mesh LOD: `QualitySettings.meshLodThreshold` per tier, `Renderer.meshLodSelectionBias` per object. Do not mix Mesh LOD and an `LODGroup` on one object.
6. Fog-wall culling: `Camera.layerCullDistances` per layer is the match for Godot `visibility_range_end`.
7. Baked occlusion culling (Umbra) fits interiors only.

### 6.3 Profile

1. Player args: `-profiler-enable -profiler-log-file <file.raw> -profiler-capture-frame-count <n>`.
2. In game code: `ProfilerRecorder.StartNew(...)` for markers and counters, `FrameTimingManager.CaptureFrameTimings()` for CPU and GPU frame time (needs Player Settings > Frame Timing Stats).
3. Frame cap: `QualitySettings.vSyncCount`, `Application.targetFrameRate`.
4. A bench pattern for a fps gate: warm-up, a fixed camera path, then the average and the 1% low.

### 6.4 Steam Deck

1. Ship the native Linux player with Vulkan (`-force-vulkan` if needed) and Mono. Unity staff call the Deck "not officially supported" (Jul 2025). Unity has no Deck input layout; Steam Input shows the Deck as a standard pad.
2. In one project's test, an HDRP scene ran at 16.9 fps average at native res on 6000.3 on a Deck. No dated public report gives URP fps on a Deck. Measure your own scene.
3. First cuts for a Deck tier (measure each one):
   - render scale 0.75 to 0.85, MSAA off;
   - SSAO Low or off, SSR off, Surface Cache GI off;
   - `RenderSettings` fog only;
   - 1 or 2 shadow cascades at 40 to 60 m, main shadow map 1024 to 2048;
   - `colorGradingMode` LDR.
4. The Deck's own Frame Limit can cap a Unity game well below its free frame rate. Test with the limiter on and off.
5. A non-Steam shortcut gets no Steam shader pre-cache (UNVERIFIED). PSO warm-up in the game is the fix (6.1).
6. Adaptive Performance (Basic provider) supports Linux through `FrameTimingManager`; the URP asset flag is `useAdaptivePerformance`.
7. Use the `steam-deck` skill for every Deck build, fps read and screenshot.

## 7. Gotchas an older-trained agent gets wrong

"Guard" means `unity_guard.py` blocks the old form.

| # | Old belief or API | Fact in 6.7 | Since | Guard |
|---|---|---|---|---|
| 1 | `override void Execute(ScriptableRenderContext, ref RenderingData)` | Removed. Override `RecordRenderGraph(RenderGraph, ContextContainer)` | removed 6.4 | yes |
| 2 | `Configure(CommandBuffer, ...)`, `OnCameraSetup(CommandBuffer, ...)` | Removed. Declare resources on the builder (`UseTexture`, `SetRenderAttachment`) | 6.4 | yes |
| 3 | `ConfigureTarget(...)`, `ConfigureClear(...)` | Removed | 6.4 | yes |
| 4 | `renderer.cameraColorTargetHandle` | Removed. `frameData.Get<UniversalResourceData>().activeColorTexture` | 6.4 | yes |
| 5 | Turn on Compatibility Mode or `URP_COMPATIBILITY_MODE` | Neither exists | 6.4 | n/a |
| 6 | `renderGraph.AddRenderPass(...)` | Obsolete error. `AddRasterRenderPass`, `AddComputePass`, `AddUnsafePass` | 6.0 | yes |
| 7 | `RenderTargetHandle` | Obsolete error. `TextureHandle` (or `RTHandle` outside a graph) | 2023.1 | yes |
| 8 | `ScriptableRendererFeature.SetupRenderPasses` | Removed. Use `AddRenderPasses` | 6.7 | yes |
| 9 | Dynamic batching on the URP asset | `supportsDynamicBatching` is an error; removed | 6.6 | yes |
| 10 | SSAO values on the renderer feature | Ignored. Set them on `ScreenSpaceAmbientOcclusionVolumeOverride` | 6.7 BETA | no |
| 11 | `using UnityEngine.Rendering.PostProcessing` (PPv2) | Not in URP. Use `Volume` overrides | URP | yes |
| 12 | `GraphicsSettings.renderPipelineAsset` | Obsolete. `defaultRenderPipeline`, or `QualitySettings.renderPipeline` per tier | 2023 | yes |
| 13 | `Input.GetAxis`, `Input.GetKey`, `Input.mousePosition` | Throw with Input System only. Use `InputSystem.actions`, `Keyboard.current`, `Gamepad.current` | Input System only | yes |
| 14 | `StandaloneInputModule` with the Input System | `InputSystemUIInputModule`; `TouchInputModule` removed | 6.7 BETA | no |
| 15 | `FindObjectOfType<T>()`, `FindObjectsOfType<T>()` | Obsolete | 6.0 | yes |
| 16 | `FindFirstObjectByType<T>()` is the fix | Also obsolete. `FindAnyObjectByType<T>()` | 6.5 | yes |
| 17 | `FindObjectsByType<T>(FindObjectsSortMode.None)` | Sort-mode overloads obsolete. `FindObjectsByType<T>()` | 6.4 | yes |
| 18 | `obj.GetInstanceID()` returns an `int` key | Obsolete error. `GetEntityId()` returns an 8-byte `EntityId` | 6.5 | yes |
| 19 | `EntityId` casts to `int` | Both casts are errors. Do not key by `GetHashCode()` or `ToString()` | 6.6 | no |
| 20 | `RaycastHit.colliderInstanceID`, `Resources.InstanceIDToObject` | Errors. `colliderEntityId`, `Resources.EntityIdToObject` | 6.4-6.6 | yes |
| 21 | `Scene.handle` is an `int` | `SceneHandle`; the int casts are errors | 6.7 | no |
| 22 | `rb.velocity`, `rb.drag`, `rb.angularDrag` | `linearVelocity`, `linearDamping`, `angularDamping` | by 6.3 | yes |
| 23 | `PhysicMaterial` | `PhysicsMaterial` (old name is an error) | by 6.3 | yes |
| 24 | `Physics.autoSimulation = false` | `Physics.simulationMode = SimulationMode.Script` | 2022 | yes |
| 25 | `Physics.autoSyncTransforms = true` | Obsolete. Call `Physics.SyncTransforms()` when needed | 6.x | no |
| 26 | `rb.SetDensity(d)` changes mass | No effect. Set `rb.mass` | 6.1 | no |
| 27 | Fixed timestep 60 Hz like Godot | Unity default is 50 Hz (0.02 s). Set 1/60 if your logic counts 60 Hz ticks | default | no |
| 28 | Play mode resets statics | No domain reload in 6.6+. Reset statics (section 4.4) | 6.6 | no |
| 29 | `async` work stops with Play mode | It keeps running. Pass `destroyCancellationToken` / `Application.exitCancellationToken` | 2023.1 | no |
| 30 | Await an `Awaitable` twice, like a `Task` | Never: instances are pooled | 2023.1 | no |
| 31 | `target?.position`, `a ?? b`, `x is null` on Unity objects | Skip the fake-null check. Write `!= null` or `if (x)` | always | yes |
| 32 | `[SerializeField] public int Hp { get; set; }` | Compile error. `[field: SerializeField]` | 6.3 | no |
| 33 | Unity cannot serialize a `Dictionary` | `[SerializeField] Dictionary<K,V>` works | 6.6 | no |
| 34 | C# 10+ syntax, `init` setters, records in serialized data | C# 9.0 only | current | no |
| 35 | Unity 6.7 runs on CoreCLR | The editor runs Mono; CoreCLR players are experimental | 6.7 BETA | no |
| 36 | `#if DEVELOPMENT_BUILD`, `#if UNITY_64` | Deprecated, removed in 6.8. `Debug.isDebugBuild` | 6.6 | yes |
| 37 | `UxmlFactory<T>`, `UxmlTraits` | Removed. `[UxmlElement] partial class` + `[UxmlAttribute]` | 6.6 | yes |
| 38 | `visualElement.transform.position` | Obsolete. `style.translate`; read `resolvedStyle` | 6.2 | no |
| 39 | `CinemachineVirtualCamera` | Obsolete. `CinemachineCamera` (`Unity.Cinemachine`) | 6.6 | yes |
| 40 | `gameObject.rigidbody`, `AddComponent("Name")` | Removed. `GetComponent<T>()`, `AddComponent<T>()` | 6.5 | no |
| 41 | `gameObject.SetActiveRecursively(...)` | Error. `SetActive(...)` | old | yes |
| 42 | Add `com.unity.textmeshpro`, `com.unity.mathematics`, `com.unity.burst` | TMP is in uGUI; Mathematics and Burst are engine modules | 6.3-6.6 | no |
| 43 | `UnityEngine.Rendering.ListPool` / `GenericPool` | Deprecated. `UnityEngine.Pool.*` | 6.7 BETA | no |
| 44 | `Object.Destroy(parent)` disables only direct children | `OnDisable` runs on all descendants | 6.4 | no |
| 45 | `AfterRendering` runs before the final blit | It runs after it. Use `AfterRenderingPostProcessing` | 6.2 | no |
| 46 | `ShaderVariantCollection.WarmUp()` stops hitches | Wrong PSOs on Metal and Vulkan. Use `GraphicsStateCollection` | 6.0 | no |
| 47 | URP has volumetric fog like HDRP | Only behind the unset `VOLUMETRIC_FOG` define | 6.7 | no |
| 48 | `Resources.Load` or `GameObject.Find` in `Update` | Slow; load and find once in `Awake` | always | yes |
| 49 | `using UnityEditor;` in runtime code | The player build fails. Wrap it in `#if UNITY_EDITOR` or move it to an Editor asmdef | always | yes |
| 50 | Hand-edit a `.prefab`, `.unity` or `.meta` file | Agents break fileIDs and GUIDs. Use an editor script or MCP | always | yes (PreToolUse) |
| 51 | `cp` an asset folder with its `.meta` files | Duplicate GUIDs; Unity links the wrong asset. `AssetDatabase.CopyAsset` | always | yes (PreToolUse) |
| 52 | `-runTests ... -quit` | `-quit` ends the run early. Leave it out | always | no |
| 53 | `-runTests` exit 0 means the tests passed | Also 0 when 0 tests ran. Check the XML count | always | no |
| 54 | `-nographics` for every headless run | No GPU: EditMode and logic only. Screenshots need a GPU | always | no |

Code from a Unity 6.3 or older project often fails the guard in 2 ways: old `Input.GetKey` calls and the `FindObjectsSortMode` overloads. Port it with the 6.7 forms.

## 8. Multi-agent rules

These rules apply when several agents work on 1 Unity project at the same time:

1. One worktree, one `Library/` folder and one Unity process per agent. Never open 2 editors on 1 folder.
2. Never edit `.unity`, `.prefab` or `.meta` YAML by hand (the guard blocks it). Never change a GUID.
3. Set `git config merge.renames false` in each clone, so git does not merge 2 unrelated `.meta` files. Check for duplicate and orphan `.meta` files before a merge.
4. A new asset gets its `.meta` (and GUID) from 1 agent only. Two agents that make the same file make 2 GUIDs.
5. `-nographics` for EditMode tests only.
6. Write static-safe code (section 4.4): no domain reload, and Unity 7 removes domain reload completely.
7. Give each scene and shared prefab 1 owner. Prefer prefabs to shared scenes, so 2 agents do not edit 1 file.

## 9. Open questions in 6000.7.0b2

These items were not confirmed against the beta. Check each one before you depend on it.

| # | Item | Why | Size |
|---|---|---|---|
| 1 | Open the URP asset Inspector in 6000.7.0b2: an "Upscaling Filter" dropdown or an upscaler priority list? | `ENABLE_UPSCALER_FRAMEWORK` decides which API is live. | S |
| 2 | Add `VOLUMETRIC_FOG` as a project define in a spike and check for "Fog" in Volume > Add Override. | The URP volumetric fog would replace a third-party option. | S |
| 3 | Build a Linux dev player with Surface Cache GI on and read `Player.log`. | `SURFACE_CACHE_SUPPORTED` may be off in Linux or Mac players. | S |
| 4 | Run `-runTests` once with 1 failing test and with 0 tests. Record the exit codes. | Confirms section 3 before CI depends on it. | S |
| 5 | Check `JsonUtility` with a `[SerializeField] Dictionary`. | The 6.7 manual pages disagree. | S |
| 6 | Read the default Active Input Handling of a new 6.7 project. | Not in the C# source. | S |
| 7 | Measure URP fps on a Steam Deck for your scene. | No public number exists. | M |
| 8 | Trace 1 `GraphicsStateCollection` per target (for example, Mac, PC, Deck) and warm them at load. | Shader hitches on a cold Vulkan cache. | M |
| 9 | Re-check every BETA row at 6.7 final, then move the pin in its own branch. | Betas can break APIs between builds. | M |

## 10. Sources

| Source | Date |
|---|---|
| Unity 6000.7.0b2 XML docs, built-in package C# (URP 17.7.0, Input System 6.7.0, Test Framework 1.9.0), through `tools/unity_api.py` | Oct 2026 |
| UnityCsReference tags `6000.7.0b2` and `6000.3.25f1`: https://github.com/Unity-Technologies/UnityCsReference | Oct 2026 |
| Unity 6.7 manual zip: https://cloudmedia-docs.unity3d.com/docscloudstorage/en/6000.7/UnityDocumentation.zip | 29 Sep 2026 |
| https://unity.com/releases/editor/beta/6000.7.0b2 and https://unity.com/releases/editor/beta/6000.7.0b1 | 2026 |
| https://unity.com/releases/editor/whats-new/6000.4.0f1 , /6000.5.0f1 , /6000.6.0f1 | 18 Mar, 15 Jun, 31 Aug 2026 |
| https://docs.unity3d.com/6000.7/Documentation/Manual/UpgradeGuideUnity65.html , UpgradeGuideUnity66.html , WhatsNewUnity65.html , WhatsNewUnity66.html | fetched Oct 2026 |
| https://discussions.unity.com/t/graphics-updates-with-the-unity-6-7-beta-release-we-want-to-hear-your-feedback/1737140 (SSR, SCGI, GTAO, AgX in 6.7) | 21 Sep 2026 |
| https://discussions.unity.com/t/the-path-to-a-single-render-pipeline-in-unity-7/1737908 (HDRP deprecated in 7.0) | 29 Sep 2026 |
| https://discussions.unity.com/t/surface-cache-gi-preview/1720494 | 20 May 2026 |
| https://discussions.unity.com/t/preview-of-screen-space-reflections-for-urp/1721494 | 29 May 2026 |
| https://discussions.unity.com/t/preview-of-urp-ground-truth-ambient-occlusion-gtao/1724061 | 25 Jun 2026 |
| https://discussions.unity.com/t/unity-6-6-is-now-available/1735357 | 1 Sep 2026 |
| https://discussions.unity.com/t/steam-deck-support-in-new-input-system/1666646 | Jul 2025 to Mar 2026 |
| https://discussions.unity.com/t/heavily-degraded-performance-on-steam-deck-with-frame-limit-on/1691084 | 19 Oct 2025 |
| https://www.gamingonlinux.com/2026/03/unity-announce-expanded-supported-for-steam-linux-steam-deck-and-steam-machine/ | 11 Mar 2026 |
| https://partner.steamgames.com/doc/steamdeck/recommendations | fetched Oct 2026 |
| https://github.com/CristianQiu/Unity-URP-Volumetric-Light | pushed 7 Sep 2026 |
| https://raw.githubusercontent.com/github/gitignore/main/Unity.gitignore | fetched Oct 2026 |

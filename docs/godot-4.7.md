# Godot 4.7 practices

This file is an engine cheat sheet for agents that write Godot 4.7 code. The engine is Godot 4.7.2 stable (`4.7.2.stable.official.ed1daf0bf`, 18 Aug 2026). Each class, member, setting and enum below was checked with `tools/godot_api.py` against the `4.7.2-stable` tag. A line tagged UNVERIFIED comes from community research only.

Agents know an older Godot, often 4.2 to 4.4. Read section 2 and section 7 before you write engine code.

## 1. Look it up, do not guess

Use this order for each class, member, signal, enum or project setting that is new to you:

1. `python3 tools/godot_api.py <Class> [member]` gives the exact 4.7.2 signature, default and description.
2. `python3 tools/godot_api.py --find <name>` searches every class. 0 hits means the name does not exist in 4.7.2.
3. `python3 tools/godot_api.py --docs "<phrase>"` searches the 4.7 manual. It prints `.rst` paths; open them with Read.
4. The web comes last. `docs.godotengine.org` blocks curl and WebFetch with a Cloudflare challenge. Use GitHub raw files at the `4.7.2-stable` tag instead.

Notes:

- Trust the class reference for names, types and defaults. Its prose can lag the feature. Example: `Environment.tonemap_mode` still says that Godot has no HDR output, but 4.7 added it. Check prose claims in the manual or the release notes.
- Do not use `godot --headless --check-only -s file.gd` as a parse check. In 4.7.2 the script compiles before autoloads register. So each reference to an autoload (for example, a `GameState` singleton) fails with "Identifier not found" (GH-78587, GH-80319, GH-111515; fix PR GH-110295 is open). Run the game headless for a few seconds instead, and grep its log for `SCRIPT ERROR` and `Parse Error`.
- APIs from 4.8 dev snapshots do not exist here: `Trail3D`, `TextureStreaming`, `intersect_ray_into`, screen-space contact shadows, animated decals. HDDAGI does not exist in any release. The tokenizer reserves `trait`, but the 4.7.2 parser has no rule for it. Do not name anything `trait`.

## 2. What changed 4.4 → 4.7

| Feature | Version | What to do |
|---|---|---|
| Ubershaders and pipeline precompilation | 4.4 | Let the engine see each material, mesh and render feature at load. See section 6. |
| AgX tonemapper (`Environment.TONE_MAPPER_AGX`) | 4.4 | A tonemapper that keeps hues in bright light. See section 5. |
| `tonemap_agx_white` (default 16.29), `tonemap_agx_contrast` (default 1.25) | 4.6 | AgX ignores `tonemap_white`. Tune these 2 members instead. |
| 3D physics interpolation | 4.4 | Opt-in. See section 3, section 4 and section 6. |
| Jolt Physics built in | 4.4 | Default only for projects made in 4.6 or later. Older projects keep `DEFAULT` = GodotPhysics3D. |
| `Light3D.shadow_caster_mask` | 4.4 | Limit the casters of each shadowed light by render layer. |
| Per-material vertex shading, `rendering/shading/overrides/force_vertex_shading` | 4.4 | `BaseMaterial3D.SHADING_MODE_PER_VERTEX` is a low-tier option (for example, Steam Deck) for dust and far props. |
| LightmapGI shadowmasks (`LightmapGI.shadowmask_mode`, EXPERIMENTAL) | 4.4 | Needs a bake and UV2. |
| Typed dictionaries `Dictionary[String, float]` | 4.4 | Use them for JSON-backed tables. No nested typed collections. |
| `@export_tool_button` | 4.4 | Editor buttons in `@tool` scripts only. |
| `@export_file` stores `uid://` | 4.4 | Use `@export_file_path` when code needs a `res://` path. |
| `.uid` sidecar files for scripts and shaders | 4.4 | Commit them. Move each one with its script or shader. |
| `FileAccess.store_*` return `bool` | 4.4 | Check the result when a save must not fail. |
| Shader baker (export option `Shader Baker > Enabled`) | 4.5 | It does not work with a `--headless` export. See section 6. |
| `Resource.duplicate_deep()` | 4.5 | `duplicate(true)` no longer copies external sub-resources. |
| Variadic functions, `@abstract` classes and methods | 4.5 | Allowed. Keep them rare. |
| `@warning_ignore_start` / `@warning_ignore_restore` | present in 4.7.2 | Region form of `@warning_ignore`. |
| Script backtraces in release builds (`debug/settings/gdscript/always_track_call_stacks`, `Engine.capture_script_backtraces()`) | 4.5 | Turn on for crash logs from release builds if needed. |
| SMAA 1x in `rendering/anti_aliasing/quality/screen_space_aa` | 4.5 | An option beside FXAA. |
| Specular occlusion from ambient (`rendering/reflections/specular_occlusion/enabled`, default true) | 4.5 | Dark crevices get fewer sky reflections. |
| SDL3 gamepad driver | 4.5 | Pad mappings can differ from 4.4 tutorials. |
| Glow: default blend Screen, `glow_intensity` default 0.3 | 4.6 | New Environments look different from old tutorials. |
| Volumetric fog blend more physical, so brighter | 4.6 | Lower density or light fog energy when a tutorial value looks too bright. |
| `.tscn` stores unique node IDs, drops `load_steps` | 4.6 | One-time diff noise on a re-saved scene. |
| ObjectDB snapshots in the debugger | 4.6 | Use them for leak hunts. |
| `AreaLight3D` | 4.7 | New rectangle light. See the perf note in section 6. |
| HDR output | 4.7 | Linux needs Wayland; X11 has no HDR output. |
| `Tween.tween_await(signal)` | 4.7 | Pauses a tween until a signal. Set a timeout if the signal can fail to come. |
| Typed-return overrides need an explicit `return` | 4.7 | Fix the parse error; do not untype the method. |
| Packed-array element assignment no longer calls the property setter | 4.7 | Call the setter yourself if it must run. |
| `InputEvent.device` for keys and mouse is `DEVICE_ID_KEYBOARD` / `DEVICE_ID_MOUSE` | 4.7 | Never test `event.device == 0` for "keyboard". |
| `AudioStreamPlayer2D/3D.area_mask` default 0 | 4.7 | Set it if a sound must pick up an Area3D bus. |
| `LookAtModifier3D.relative` default false | 4.7 | Set it when you port a 4.4 rig. |
| `input_devices/joypads/ignore_joypad_on_unfocused_application` (default false) | 4.7 | Leave off for a game with 1 window (for example, on a Steam Deck). |

## 3. Project setup checklist

Decide each of these settings early, and write the choice in your project notes so agents keep it.

| Setting | Default and advice |
|---|---|
| Renderer | `config/features` holds "4.7" and the renderer ("Forward Plus"). SDFGI and volumetric fog need Forward+. `CompositorEffect` works on Forward+ and Mobile, not on Compatibility. |
| 3D physics engine | `physics/3d/physics_engine` = `DEFAULT`. That is GodotPhysics3D in a project made before 4.6 (no `[physics]` section), and Jolt in a new one. Set it explicitly: `DEFAULT` "may change in future releases" (4.7.2 doc). |
| Physics interpolation | Off by default (`physics/common/physics_interpolation`). If you turn it on: move bodies in `_physics_process`; a camera in `_process` reads `get_global_transform_interpolated()` from its target and sets its own `physics_interpolation_mode` to OFF; call `reset_physics_interpolation()` on a body after each teleport. Details in section 6. |
| Physics tick | 60 per second (default). |
| GDScript warnings | Engine defaults: `untyped_declaration` and `unsafe_*` are 0 (ignore). Raise them to 1, then to 2 when clean. They catch agent mistakes at parse time. |
| MSAA 3D, screen-space AA | Set the level before the first 3D load. A change at run time recompiles pipelines (section 6). |
| Directional shadow size | 4096 by default. A low tier can use 2048. |
| Quality tiers | Example of a low tier (Steam Deck class): SDFGI off, SSAO off, fewer shadowed lights, volumetric fog size 48 and depth 32, `mesh_lod_threshold` 4.0, shadow atlas 2048, a visibility range at the fog wall. |
| Shader warm-up | Plan it from the start (section 6). |
| Data | JSON files or Resources. JSON is easy for agents to diff and edit. If the project keeps tables in JSON, do not convert them to `.tres`. |
| Typing | Aim for every variable, parameter and return typed (section 4). |

## 4. GDScript rules

### Types and warnings

1. Type every variable, parameter and return (`-> void` too). Use `:=` only when the type is clear on the same line.
2. Static types make the VM use typed opcodes. A community benchmark shows typed loops 28-36% faster for float math and 55-59% faster for Vector2 math (beep.blog, Feb 2024).
3. `inference_on_variant` is an error by default (4.7.2). `x := dict["k"]` fails; write `var x: float = dict["k"]`.
4. Warning settings live under `debug/gdscript/warnings/`. Values: 0 ignore, 1 warn, 2 error. There is no `exclude_addons` key; `directory_rules` (default `{ "res://addons": 0 }`) does that job. Keep the addons rule.
5. Silence one line with `@warning_ignore("name")`. Silence a region with `@warning_ignore_start("name")` and `@warning_ignore_restore("name")`.
6. `as` returns `null` on a type mismatch. Test with `is` first when null is not a valid result.

### Style (official style guide, 4.7)

1. Tabs. Lines under 100 characters. 2 blank lines between functions.
2. Names: `snake_case` files, functions and variables; `PascalCase` classes and nodes; `CONSTANT_CASE` constants and enum members; past-tense signals (`hull_breached`); `_private` members.
3. Member order: `class_name`, `extends`, doc comment, signals, enums, constants, static vars, `@export` vars, vars, `@onready` vars, `_init`, `_enter_tree`, `_ready`, `_process`, `_physics_process`, other virtuals, public methods, private methods.
4. Use `and`, `or`, `not`. Double quotes. `0.5`, not `.5`.
5. Godot filesystems in an export are case-sensitive. A wrong-case `res://` path works in the editor on a Mac and fails on Linux (for example, a Steam Deck).

### Signals and structure

1. Call down, signal up. A parent calls methods on its children. A child emits a signal and does not know its parent. No `get_parent().foo()` from a component.
2. Connect with signal objects: `hull_breached.connect(_on_hull_breached)`, `hull_breached.emit(depth)`.
3. An autoload owns a wide system and its data (for example, `GameState`, `AudioDirector`). Do not add an autoload for a thing that 1 scene owns.
4. Do not put a `class_name` on an autoload script with the same name as the autoload.
5. A sub-class override of `_ready()` or `_process()` does not run the base version. Call `super()`.
6. Use `@onready` for own children. Pass siblings and far nodes in by `@export` or a setter.

### Data: JSON or Resources

1. If the project keeps balance values and tables in JSON, keep them there. Do not convert them to `.tres`.
2. Load JSON with `JSON.parse_string()` and copy values into typed variables or a `Dictionary[String, float]`.
3. When you do use a Resource (a material, a mesh, a `.tres`), remember the shared-reference trap:
   - `load()` and `preload()` return 1 cached instance. A change at run time changes every user.
   - Call `duplicate()` for a per-instance copy. `duplicate(true)` copies internal sub-resources only since 4.5. Call `duplicate_deep(Resource.DEEP_DUPLICATE_ALL)` for the 4.4 result.
   - `resource_local_to_scene = true` duplicates the resource per scene instance.
   - All instances of an imported `.glb` mesh share its materials. Put the copy in `MeshInstance3D.material_override` or `set_surface_override_material()`, not on the mesh.

### Node lifecycle

1. `_init` runs before the node is in the tree. `_enter_tree` runs parent first. `@onready` values and `_ready` run children first.
2. `_ready` runs once per node lifetime. Call `request_ready()` before you re-add a node that must run it again.
3. Set properties before `add_child()` when `_ready` reads them. Put a projectile under a neutral parent, not under the shooter.
4. `queue_free()` deletes at the end of the frame. The node stays in the tree this frame. `free()` is immediate and unsafe in a signal or a loop.
5. `await` returns to the caller and resumes later. If the engine frees the node during the wait, the code after the `await` runs on a freed object. After each `await` in a node that can die, check `is_instance_valid(self)` or `is_inside_tree()`.
6. `SceneTree.create_timer()` ignores pause by default (`process_always = true`). A `Timer` node follows `process_mode`.

### Tweens

1. `create_tween()` on a node binds the tween to that node. It dies with the node and pauses with it.
2. Keep a reference to a tween that drives a property. Call `kill()` on the old one before you start a new one on the same property.
3. A tween starts on the next process or physics frame, not at once.

### Process functions

1. Move bodies and run game logic in `_physics_process`. Use `_process` for visuals that follow the frame.
2. A camera in `_process` that follows a `_physics_process` body jitters when interpolation is off and the screen is not 60 Hz. The fix: turn on physics interpolation. Then the camera moves in `_process` and reads the interpolated pose of its target with `get_global_transform_interpolated()`. Set the camera's own `physics_interpolation_mode` to OFF, so the engine does not interpolate it twice.
3. An empty `_process` still costs per instance. Delete it, or call `set_process(false)`.
4. `CharacterBody3D.move_and_slide()` takes no arguments and returns `bool`. A swimmer or flyer uses `motion_mode = CharacterBody3D.MOTION_MODE_FLOATING`.
5. Keep heavy per-frame math out of GDScript. Use engine APIs, packed arrays, MultiMesh or shaders.

## 5. 3D lighting and look

### Global illumination

| GI | Cost | Fit |
|---|---|---|
| SDFGI (`Environment.sdfgi_enabled`) | Manual: "one of the most demanding" GI methods. Forward+ only. Dynamic lights yes; dynamic occluders and emissives no. | Dynamic scenes on a high tier. Turn it off on a low tier. Fast camera moves cause cascade updates. |
| VoxelGI | Bake per volume; a mid cost at run time | Good for an interior (a hangar, a cave, a building). Placing one at run time triggers pipeline compiles. |
| LightmapGI | Cheapest at run time; static only; needs UV2 and a bake | Good for static sets. Terrain and props built in code do not fit it. |
| SSIL (`Environment.ssil_enabled`) | Screen space; misses off-screen light | A cheap bounce near a lamp. |

Known bug GH-97393 (4.3 to 4.4.1): a baked LightmapGI turns off VoxelGI and SDFGI, even when hidden. UNVERIFIED for 4.7.

### Fog

1. Depth fog (`fog_mode = Environment.FOG_MODE_DEPTH`) and exponential fog (`FOG_MODE_EXPONENTIAL`) are cheap. Height fog uses `fog_height` and `fog_height_density`.
2. Volumetric fog is Forward+ only. Its cost scales with `rendering/environment/volumetric_fog/volume_size` (default 64) and `volume_depth` (default 64). A low tier can use 48 and 32.
3. `volumetric_fog_temporal_reprojection_enabled` (default true) smooths the fog but leaves trails behind a light or FogVolume that moves. A lamp that moves with the camera shows this. Test such a lamp with reprojection on and off.
4. Set `Light3D.light_volumetric_fog_energy = 0.0` on a light that need not scatter. The engine then skips that light in the fog pass.
5. For god rays, keep fog density near zero and raise the light fog energy. The shafts show without a dark haze.
6. `volumetric_fog_density = 0.0` turns off global volumetric fog. `FogVolume` nodes still render.
7. Thin FogVolumes flicker when the camera moves. Make them thicker with less density, or cut `volumetric_fog_length`.
8. `volumetric_fog_ambient_inject` (default 0) costs a little above zero. So does `volumetric_fog_gi_inject` (default 1). The ambient inject has no shadow data. It also lights fog inside an interior (Calinou, GH-85472).

### Tonemap

1. AgX (4.4+) keeps hues in bright light and lowers saturation. Use `tonemap_agx_contrast` (4.6+) to get contrast back. It gives a better result than `adjustment_contrast` at no extra cost.
2. AgX uses `tonemap_agx_white`, not `tonemap_white`. Set both when a script changes the tonemapper at run time.
3. Glow defaults changed in 4.6. Retune glow after you copy values from a tutorial older than 4.6.

### Lights and shadows (Forward+)

1. `rendering/limits/cluster_builder/max_clustered_elements` (default 512) caps OmniLight3D, SpotLight3D, Decal and ReflectionProbe in view. There is no `rendering/limits/forward_renderer/*` key.
2. Each shadowed light redraws its casters. Turn shadows off where they do not show. Use `shadow_caster_mask` to limit casters.
3. Positional shadows share 1 atlas (`rendering/lights_and_shadows/positional_shadow/atlas_size`, default 4096; a low tier can use 2048). More shadowed lights than atlas slots make lights evict each other each frame (GH-97472, community).
4. `Light3D.light_projector` needs `shadow_enabled` on. A projector SpotLight (for example, for caustics) pays the shadow cost for the projector.
5. Use `distance_fade_enabled` on small lights. The engine culls a light after it fades out.
6. Set each light's range to what it must reach.

### Caustics, particles and post

1. Fake caustics in world space: sample the pattern from world XZ in the shader, not from UVs. Pass the world position from `vertex()` in a `varying`; `VERTEX` in `fragment()` is view space.
2. Floating particles (dust, marine snow): `GPUParticles3D` in a box around the camera, slow fall, `ParticleProcessMaterial` damping, a fade-in and fade-out colour ramp.
3. A lower `amount_ratio` does not cut GPU cost. The class reference says the engine allocates and processes the full `amount`. Change `amount` for a cheaper tier.
4. Prefer alpha scissor to alpha blend for foliage and debris. Alpha blend costs more and sorts badly.
5. Custom post goes in a `CompositorEffect` in a `Compositor` on `WorldEnvironment.compositor` or `Camera3D.compositor` (Forward+ and Mobile). Keep its GLSL in a `.glsl` file.
6. SSR, SSAO, SSIL and glow ignore off-screen geometry. Expect a pop at the screen edge.

### What looks cheap (community, widely agreed)

- Ambient light too high and key light too weak: flat contrast.
- No fog and no AO: no depth.
- Linear tonemap: clipped highlights.
- Primitive or CSG shapes left in a shot.

## 6. Performance and the Steam Deck

### Shader and pipeline stutter

1. Since 4.4, Forward+ precompiles pipelines when a mesh or material loads or a node enters the tree. Load all materials and meshes at start, not during play.
2. A render feature that you turn on at run time recompiles pipelines. Examples: an MSAA level change, the first VoxelGI, ReflectionProbe or LightmapGI, SDFGI, SSAO, SSR, TAA or FSR2. Set these at load, behind the title or a fade.
3. The engine cannot precompile a node's material override with the mesh. Show the override once at load.
4. For an effect added only in play (an explosion, a projectile trail), attach a hidden copy at load. A small warm-up node that spawns each effect once does this job.
5. A load-time warm-up pass can also draw the world under a cover. Draw each spawn or teleport point, every camera view and a few yaws. Add 1 real (muted) shot of each weapon effect. Only a real draw finds the pass and vertex-format mixes that load-time compiles miss.
6. A material made in code (`StandardMaterial3D.new()`) frees its shader and the shader's pipelines when its last user is freed. The next use compiles them again. Keep 1 reference for the run (for example, in an array on an autoload).
7. Watch the monitors `Performance.PIPELINE_COMPILATIONS_MESH`, `PIPELINE_COMPILATIONS_SURFACE` and `PIPELINE_COMPILATIONS_DRAW`. A rise in Surface or Draw during play stalls that frame on a cold driver cache. Log them in your frame trace.
8. The shader baker (4.5+) cuts first-start time, not in-game hitches. It is not supported in a `--headless` export, so a scripted export that runs headless skips it. Export from a windowed editor run instead (`tools/godot_bg.sh` keeps the window behind other windows on macOS). A Mac editor can bake Vulkan shaders for the Linux preset.

### Lights, geometry and culling

1. Shadows multiply draw calls. Each shadowed light redraws its casters.
2. Use MultiMesh for repeats (foliage, scatter). One MultiMesh has 1 AABB, so it culls as 1 object.
3. Use `GeometryInstance3D.visibility_range_end` with fog: hide far props past the fog wall. For example, a low tier can hide props past 90 m.
4. `Viewport.mesh_lod_threshold` (default 1.0) controls automatic mesh LOD. A low tier can use 4.0.
5. The occlusion cull needs `rendering/occlusion_culling/use_occlusion_culling` and baked `OccluderInstance3D` nodes. It costs CPU. Use it only for interiors and walls that hide much geometry.
6. Use VRAM Compressed textures. Lossy only shrinks the file on disk.

### Physics interpolation

1. `physics/common/physics_interpolation` is read at start only. At run time set `SceneTree.physics_interpolation`.
2. With it on, move everything in `_physics_process`, and call `reset_physics_interpolation()` after each teleport.
3. A camera that follows an interpolated body reads `get_global_transform_interpolated()` from the target in `_process`. Call it once or twice per frame only.
4. Per-node control: `Node.physics_interpolation_mode`. 4.5 removed `RenderingServer.instance_set_interpolated()`.

### Profile

1. Record frame times in the game (a small frame-trace script) before and after a perf change.
2. `godot --gpu-profile` prints the slowest GPU passes. `--print-fps` prints the frame rate.
3. `Performance.add_custom_monitor()` adds a game value to the debugger monitors.
4. A lower `rendering/scaling_3d/scale` that does not help means a CPU, draw-call or effect limit (SDFGI, SSAO, SSR, volumetric fog).

### Steam Deck

1. Ship the native Linux export, not Windows through Proton.
2. SDFGI and full-screen volumetric fog are the first things to cut. SSAO is next.
3. FSR 1 (`rendering/scaling_3d/mode`) at 0.75 to 0.85 scale is the common GPU lever (community, UNVERIFIED on a Deck).
4. Peaky GPU load (a compute pass with a CPU readback) makes the Deck lower its GPU clock (forum, Mar 2026). Avoid sync readbacks.
5. The 4.7 area-light work raised the fragment cost of the standard material in a beta. The maintainers closed GH-119963 as fixed, but no RDNA2 number after the fix exists. Compare 4.6.3 and 4.7.2 on the Deck before you blame the scene.
6. Use the `steam-deck` skill for every Deck build, fps read and screenshot.

## 7. Gotchas an older-trained agent gets wrong

| Old belief or API | Fact in 4.7.2 | Since |
|---|---|---|
| Every project uses GodotPhysics3D | New projects use Jolt; projects made before 4.6 keep `DEFAULT` = GodotPhysics3D | 4.6 |
| `duplicate(true)` copies all sub-resources | Internal ones only; use `duplicate_deep(Resource.DEEP_DUPLICATE_ALL)` | 4.5 |
| `Node.get_rpc_config()` | `Node.get_node_rpc_config()` | 4.5 |
| `RenderingServer.instance_set_interpolated()` | Removed; use `Node.physics_interpolation_mode` | 4.5 |
| `Object.is_class(String)` | Takes `StringName` | 4.7 |
| `FileAccess.store_*` return nothing | Return `bool` | 4.4 |
| `@export_file` gives `res://` | Gives `uid://`; use `@export_file_path` | 4.4 |
| `glow_intensity` default 0.8, blend Soft Light | 0.3, `GLOW_BLEND_MODE_SCREEN` | 4.6 |
| `tonemap_white` sets white for every tonemapper | AgX reads `tonemap_agx_white` | 4.6 |
| Keyboard and mouse events have `device == 0` | `DEVICE_ID_KEYBOARD`, `DEVICE_ID_MOUSE` | 4.7 |
| An override of a typed method may omit `return` | It needs an explicit `return` | 4.7 |
| `arr[i] = x` on a packed-array property runs its setter | It does not | 4.7 |
| `StreamPeerTCP.poll()` lives on `StreamPeerTCP` | It moved to base `StreamPeerSocket`; `TCPServer` methods to `SocketServer`. Old calls still work. | 4.6 |
| `GPUParticles3D.amount_ratio` saves GPU time | No saving; change `amount` | 4.7.2 doc |
| A warnings key `exclude_addons` | Does not exist; use `directory_rules` | 4.7.2 |
| An SDFGI min-roughness project setting | Does not exist in 4.7.2 | 4.7.2 |
| `AudioStreamPlayer.area_mask` | Only `AudioStreamPlayer2D` and `AudioStreamPlayer3D` have it; default 0 | 4.7 |

Godot 3 tells: `tools/hooks/gd_guard.py` blocks the common Godot 3 forms in each `.gd` edit. The `debug/gdscript/warnings/renamed_in_godot_4_hint` setting (default true) prints a hint when code uses a Godot 3 name.

`.uid` and `.import` files: commit them, and move each one with its source file.

### If you switch a project to Jolt

1. Set `physics/3d/physics_engine` to `Jolt Physics` explicitly. `DEFAULT` can change in a later release.
2. Jolt does not support many joint soft-limit properties (for example `PinJoint3D` `bias`, `damping`, `impulse_clamp`).
3. Jolt treats a joint body as `node_b`, with `node_a` as the world. GodotPhysics3D does the inverse, so joint limits can flip.
4. Jolt `Area3D` always reports static bodies (4.5+). Check trigger code.
5. Jolt settings live under `physics/jolt_physics_3d/*`. Retune mass, damp and speed values after a switch.

### Float precision far from the origin

1. Godot uses single-precision floats by default.
2. The manual recommends at most 2048 to 4096 m from the origin for a first-person 3D game. For third person it gives 4096 to 8192 m.
3. Past that range, expect jitter in the image and in physics. The fixes are origin shifts or a double-precision engine build.

## 8. Upgrade checks for an existing project

Check these items when you move a project from 4.4 or older to 4.7, or when you audit an agent-built project.

| # | Item | Why | Size |
|---|---|---|---|
| 1 | Turn on physics interpolation. Call `reset_physics_interpolation()` after each teleport. Make a follow camera read `get_global_transform_interpolated()`. | A camera that moves in `_process` after a body that moves in `_physics_process` jitters on 90 Hz and 120 Hz screens. | M |
| 2 | Set `tonemap_agx_white` and `tonemap_agx_contrast` wherever code switches to AgX. | Code that sets `tonemap_white` has no effect under AgX. | S |
| 3 | Change `amount`, not `amount_ratio`, for a cheaper particle tier. | `amount_ratio` gives no perf saving (4.7.2 class reference). | S |
| 4 | Enable the shader baker on the export preset, and export through a windowed run (for example, `tools/godot_bg.sh`). | The baker does not run in a `--headless` export. First start gets faster. | M |
| 5 | Check when code sets `msaa_3d` for a low tier. Move it before the first 3D load, or set it in an export override. | An MSAA level change recompiles pipelines. | S |
| 6 | Turn on `untyped_declaration = 1`, then the `unsafe_*` warnings at 1. Raise to 2 when clean. | The warnings catch agent mistakes at parse time. | M |
| 7a | Set `physics/3d/physics_engine` explicitly. | `DEFAULT` "may change in future releases" (4.7.2 doc). | S |
| 7b | Test Jolt in a spike branch: movement feel, character bodies, trigger areas. | Jolt is "generally faster and more reliable" (4.7.2 doc). | L |
| 8 | Set `light_volumetric_fog_energy = 0.0` on the lights that need not scatter. Test a moving lamp with fog reprojection off. | Saves fog cost per light; removes lamp trails. | S |
| 9 | Add the Pipeline Compilations monitors to your frame-trace output. | Shows hitches on a cold cache that a fast dev machine does not show. | S |
| 10 | Benchmark a low-end target (for example, a Steam Deck) on 4.6.3 and 4.7.2 with the same scene. | The 4.7 area-light work raised material cost in a beta (GH-119963). | M |

## 9. Sources

| Source | Date |
|---|---|
| Godot 4.7.2 class reference and godot-docs 4.7, through `tools/godot_api.py` | Oct 2026 |
| https://godotengine.org/article/maintenance-release-godot-4-7-2/ | 18 Aug 2026 |
| https://godotengine.org/releases/4.4/ , /4.5/ , /4.6/ , /4.7/ | 2025-2026 |
| godot-docs `tutorials/migrating/upgrading_to_godot_4.4.rst` to `4.7.rst` | 4.7 branch |
| godot-docs `tutorials/performance/pipeline_compilations.rst` (ubershaders, shader baker) | 4.7 branch |
| godot-docs `tutorials/physics/interpolation/*.rst` | 4.7 branch |
| godot-docs `tutorials/3d/volumetric_fog.rst`, `global_illumination/using_sdfgi.rst`, `physics/using_jolt_physics.rst`, `physics/large_world_coordinates.rst` | 4.7 branch |
| https://godotengine.org/article/uid-changes-coming-to-godot-4-4/ | 15 Jan 2025 |
| https://github.com/godotengine/godot/issues/119963 (4.7 Forward+ cost) | 2 Jun 2026 |
| https://github.com/godotengine/godot/issues/97393 (LightmapGI disables VoxelGI) | 24 Sep 2024 |
| https://github.com/godotengine/godot/issues/97472 (shadow atlas thrash) | 26 Sep 2024 |
| GH-78587, GH-80319, GH-111515, PR GH-110295 (`--check-only` and autoloads) | open in Oct 2026 |
| https://www.beep.blog/2024-02-14-gdscript-typing/ (typed speed numbers) | 14 Feb 2024 |
| https://forum.godotengine.org/t/peaky-gpu-load-causes-steamdeck-to-set-its-gpu-clock-too-low-causing-poor-performance/135264 | 12 Mar 2026 |

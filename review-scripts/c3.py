import sys; sys.path.insert(0,'/data/fix')
from lib import *

# ---------------- debug.rs ----------------
def debug_rs(s):
    s=rep(s,'''//! Shows FPS, frame time, object count, draw calls, GPU info, etc.
//! on top of the game. Toggle with F1 in dev builds.

use crate::color::Color;''','''//! Shows FPS, frame time, object count, draw calls, GPU info, etc.
//! on top of the game. The runner toggles it with F1 unless [`DebugOverlay::hotkey`] is off.

use std::collections::VecDeque;

use crate::color::Color;

/// Number of frame times kept for the average.
const HISTORY: usize = 120;''')
    s=rep(s,'''    lines: Vec<DebugLine>,
    frame_times: Vec<f32>, // last N frame times in ms
    max_frame_times: usize,
    pub fps: f32,''','''    lines: Vec<DebugLine>,
    /// Last [`HISTORY`] frame times in ms.
    frame_times: VecDeque<f32>,
    /// Whether the runner toggles the overlay with F1 (games that use F1 can turn this off).
    pub hotkey: bool,
    pub fps: f32,''')
    s=rep(s,'''            frame_times: Vec::with_capacity(120),
            max_frame_times: 120,
            fps''','''            frame_times: VecDeque::with_capacity(HISTORY),
            hotkey: true,
            fps''')
    s=rep(s,'''        self.frame_times.push(ms);
        if self.frame_times.len() > self.max_frame_times {
            self.frame_times.remove(0);
        }
        if ms < self.min_frame_ms {
            self.min_frame_ms = ms;
        }
        if ms > self.max_frame_ms {
            self.max_frame_ms = ms;
        }
        // Simple FPS from last frame
        if ms > 0.0 {''','''        if self.frame_times.len() == HISTORY {
            self.frame_times.pop_front();
        }
        self.frame_times.push_back(ms);
        self.min_frame_ms = self.min_frame_ms.min(ms);
        self.max_frame_ms = self.max_frame_ms.max(ms);
        if ms > 0.0 {''')
    s=rep(s,'''    pub fn avg_frame_ms(&self) -> f32 {''','''    /// Average frame time in ms over the last 120 frames.
    pub fn avg_frame_ms(&self) -> f32 {''')
    s=rep(s,'''    pub fn fps_1s_avg(&self) -> f32 {
        if self.frame_times.is_empty() {
            return 0.0;
        }
        let avg = self.avg_frame_ms();
        if avg > 0.0 {
            1000.0 / avg
        } else {
            0.0
        }
    }''','''    /// FPS averaged over the last 120 frames (steadier than [`DebugOverlay::fps`]).
    pub fn avg_fps(&self) -> f32 {
        let avg = self.avg_frame_ms();
        if avg > 0.0 { 1000.0 / avg } else { 0.0 }
    }''')
    s=rep(s,'''    /// Clear user-added lines (call after drawing each frame so they don't accumulate).''','''    /// Clear user-added lines. The runner calls this every frame (also while the overlay is hidden)
    /// so lines added each frame never pile up.''')
    s=rep(s,'''        draw_calls: u64,
        triangles: u64,''','''        draw_calls: u32,
        triangles: u64,''')
    s=rep(s,'''        if self.show_fps {
            lines.push(DebugLine {
                text: format!(
                    "FPS: {:.0} | frame: {:.2} ms (min {:.1} / max {:.1} / avg {:.1})",
                    self.fps_1s_avg(),
                    self.frame_time_ms,
                    self.min_frame_ms,
                    self.max_frame_ms,
                    self.avg_frame_ms()
                ),
                color: if self.fps_1s_avg() >= 55.0 {''','''        if self.show_fps {
            let fps = self.avg_fps();
            // Before the first frame min is still f32::MAX: show 0 instead of a 39-digit number.
            let min = if self.frame_times.is_empty() { 0.0 } else { self.min_frame_ms };
            lines.push(DebugLine {
                text: format!(
                    "FPS: {fps:.0} | frame: {:.2} ms (min {min:.1} / max {:.1} / avg {:.1})",
                    self.frame_time_ms,
                    self.max_frame_ms,
                    self.avg_frame_ms()
                ),
                color: if fps >= 55.0 {''')
    s=rep(s,'''                } else if self.fps_1s_avg() >= 30.0 {''','''                } else if fps >= 30.0 {''')
    s=rep(s,'''        d.record_frame(0.016); // ~60fps
        assert!((d.frame_time_ms - 16.0).abs() < 0.1);
        assert!(d.fps > 59.0 && d.fps < 61.0);''','''        d.record_frame(0.016);
        assert!((d.frame_time_ms - 16.0).abs() < 0.01);
        assert!((d.fps - 62.5).abs() < 0.01);''')
    s=rep(s,'''        assert!((d.avg_frame_ms() - 16.0).abs() < 0.1);
        assert!(d.fps_1s_avg() > 59.0 && d.fps_1s_avg() < 61.0);''','''        assert!((d.avg_frame_ms() - 16.0).abs() < 0.01);
        assert!((d.avg_fps() - 62.5).abs() < 0.01);''')
    s=rep(s,'''    #[test]
    fn add_custom_line() {''','''    #[test]
    fn history_is_bounded() {
        let mut d = DebugOverlay::new();
        for _ in 0..HISTORY {
            d.record_frame(0.010);
        }
        for _ in 0..HISTORY {
            d.record_frame(0.020);
        }
        assert_eq!(d.frame_times.len(), HISTORY);
        assert!((d.avg_frame_ms() - 20.0).abs() < 0.01);
    }

    #[test]
    fn no_garbage_before_first_frame() {
        let d = DebugOverlay::new();
        let lines = d.build_lines("gpu", 0, 0, 0, 0);
        assert!(lines[0].text.contains("min 0.0"), "{}", lines[0].text);
    }

    #[test]
    fn add_custom_line() {''')
    return s
edit('crates/spark-core/src/debug.rs', debug_rs)

# ---------------- renderer ----------------
def render(s):
    s=wgpu30(s)
    s=rep(s,'''    device_lost: Arc<AtomicBool>,''','''    device_lost: Arc<AtomicBool>,
    /// Numbers about the last frame drawn by [`Renderer::render`] (shown by the debug overlay).
    last_stats: FrameStats,''')
    s=rep(s,'''            device_lost,''','''            device_lost,
            last_stats: FrameStats::default(),''')
    s=rep(s,'''    /// Whether the GPU device was lost (driver crash, TDR, etc.).''','''    /// Numbers about the last rendered frame.
    pub fn last_stats(&self) -> FrameStats {
        self.last_stats
    }

    /// Whether the GPU device was lost (driver crash, TDR, etc.).''')
    s=rep(s,'''    /// Recreate device/queue/resources after a device loss. Callers should then `resize()` and
    /// render normally; assets are re-uploaded on the next frame.''','''    /// Recreates device, queue and GPU resources after a device loss (the window surface is
    /// reconfigured). Assets are re-uploaded on the next frame.''')
    s=rep(s,'''        let mut stats = self.draw_scene(&mut encoder, world);
        stats.post_passes = self.draw_post(&mut encoder, &view, view_format, world);
        if !capture {''','''        let mut stats = self.draw_scene(&mut encoder, world);
        stats.post_passes = self.draw_post(&mut encoder, &view, view_format, world);
        self.last_stats = stats;
        if !capture {''')
    s=rep(s,'''        self.draw_scene(&mut encoder, world);
        // SAFETY: ensure_capture() was just called''','''        self.last_stats = self.draw_scene(&mut encoder, world);
        // SAFETY: ensure_capture() was just called''')
    # SAFETY markers on safe code -> plain comments (keep the one on the real unsafe block)
    s=re.sub(r'// SAFETY: (ensure_capture|caller|built-in|loop|checked|candidates|ensure_scene_target)', r'// \1', s)
    # dynamic MAX_INSTANCES mismatched the fixed array<Object, 64> in the shaders -> constant again
    s=rep(s,'''        // MAX_INSTANCES based on GPU limits: uniform buffer binding size / ObjectUniform size.
        let max_uniform_binding = device.limits().max_uniform_buffer_binding_size as usize;
        let max_instances = (max_uniform_binding / size_of::<ObjectUniform>()).max(16).min(256);
''','')
    s=rep(s,'    max_instances: usize,\n','')
    s=rep(s,'            max_instances,\n','')
    s=rep(s,'NonZeroU64::new(object_size * max_instances as u64)','NonZeroU64::new(object_size * MAX_INSTANCES as u64)')
    s=rep(s,'object_buffer(&device, &object_layout, object_capacity, max_instances)','object_buffer(&device, &object_layout, object_capacity)')
    s=rep(s,'(b.count as usize) < self.max_instances','(b.count as usize) < MAX_INSTANCES')
    s=rep(s,'scratch.len() + self.max_instances * size_of::<ObjectUniform>()','scratch.len() + MAX_INSTANCES * size_of::<ObjectUniform>()')
    s=rep(s,'object_buffer(&self.device, &self.object_layout, self.object_capacity, self.max_instances)','object_buffer(&self.device, &self.object_layout, self.object_capacity)')
    s=rep(s,'(max_instances * size_of::<ObjectUniform>())','(MAX_INSTANCES * size_of::<ObjectUniform>())')
    i=s.index('fn object_buffer(\n'); j=s.index('{',i)
    s=s[:i]+'fn object_buffer(device: &wgpu::Device, layout: &wgpu::BindGroupLayout, capacity: usize) -> (wgpu::Buffer, wgpu::BindGroup) '+s[j:]
    if 'const MAX_INSTANCES' not in s:
        s=rep(s,'''/// Pipeline variant bits: blend mode (0 opaque, 1 alpha, 2 additive) | double-sided.
const VARIANT_ALPHA''','''/// Pipeline variant bits: blend mode (0 opaque, 1 alpha, 2 additive) | double-sided.
/// Objects per instanced draw: `array<Object, 64>` uniform window (fits every GPU incl. GL).
/// Must match the array length in `surface.wgsl` and `shadow.wgsl`.
const MAX_INSTANCES: usize = 64;
const VARIANT_ALPHA''')
    # normal_matrix "fast path" is wrong with shear (non-uniform parent scale) and not faster
    s=rep(s,'''    if model.determinant().abs() < 1e-12 {
        return Mat4::IDENTITY;
    }
    // Fast path: uniform scale → use rotation only (no inverse needed).
    let (scale, rot, _) = model.to_scale_rotation_translation();
    if (scale.x - scale.y).abs() < 1e-5 && (scale.y - scale.z).abs() < 1e-5 {
        // For uniform scale, normal_matrix = rotation matrix (3×3 → 4×4).
        return Mat4::from_quat(rot);
    }
    model.inverse().transpose()''','''    if model.determinant().abs() < 1e-12 { Mat4::IDENTITY } else { model.inverse().transpose() }''')
    s=rep(s,'Tried backends: {}','Tried: {}')
    i=s.index('#[cfg(test)]\nmod tests {\n    use super::*;\n\n    #[test]\n    fn gpu_info_has_name_and_backend')
    s=s[:i]+open('/data/fix/render_tests.rs').read()
    return s
edit('crates/spark-render/src/lib.rs', render)

# ---------------- app ----------------
def app(s):
    s=rep(s,'''/// Draws the debug overlay (FPS, GPU, scene stats, custom lines) on the canvas.
/// Called after `game.draw()` so the overlay sits on top of everything.
fn draw_debug_overlay(world: &mut World, gpu_name: &str) {
    let object_count = world.scene.len();
    let physics_active = world.scene.iter().filter(|(_, o)| o.body.is_some()).count();
    let lines = world.debug.build_lines(gpu_name, object_count, 0, 0, physics_active);
''','''/// Draws the debug overlay (FPS, GPU, scene stats, custom lines) on the canvas when it is on.
/// Called after `game.draw()` so the overlay sits on top of everything. `stats` are the numbers
/// of the previous rendered frame. Custom lines are cleared every frame, also while hidden.
fn draw_debug_overlay(world: &mut World, gpu_name: &str, stats: spark_render::FrameStats) {
    if !world.debug.enabled() {
        world.debug.clear_lines();
        return;
    }
    let object_count = world.scene.len();
    let physics_active = world.scene.iter().filter(|(_, o)| o.body.is_some()).count();
    let lines = world.debug.build_lines(gpu_name, object_count, stats.draw_calls, stats.triangles, physics_active);
''')
    s=rep(s,'''        let line_height = 18.0;''','''        let text_size = 15.0;
        let line_height = text_size * 1.2;''')
    s=rep(s,'''                size: 15.0,
                color: line.color,''','''                size: text_size,
                color: line.color,''')
    s=rep(s,'''        world.debug.record_frame(dt);
        if world.debug.enabled() {
            draw_debug_overlay(&mut world, renderer.info().name.as_str());
        }''','''        world.debug.record_frame(dt);
        let gpu_name = renderer.info().name.clone();
        draw_debug_overlay(&mut world, &gpu_name, renderer.last_stats());''')
    s=rep(s,'''        // Draw debug overlay on the canvas before rendering (on top of game content).
        if self.world.debug.enabled() {
            let gpu_name = self
                .renderer
                .as_ref()
                .map(|r| r.info().name.clone())
                .unwrap_or_default();
            draw_debug_overlay(&mut self.world, &gpu_name);
        }''','''        // Draw debug overlay on the canvas before rendering (on top of game content).
        let (gpu_name, stats) =
            self.renderer.as_ref().map(|r| (r.info().name.clone(), r.last_stats())).unwrap_or_default();
        draw_debug_overlay(&mut self.world, &gpu_name, stats);''')
    s=rep(s,'''        match renderer.render_and_capture_if(&self.world, capture) {
            Err(e) => {
                self.fail(event_loop, e);
                return;
            }''','''        match renderer.render_and_capture_if(&self.world, capture) {
            // Driver reset / GPU removed: rebuild the device once instead of closing the game.
            Err(e) if renderer.is_device_lost() => match renderer.recover() {
                Ok(()) => log::warn!("{e}: GPU device recreated"),
                Err(r) => {
                    self.fail(event_loop, format!("{e}; recovery failed: {r}"));
                    return;
                }
            },
            Err(e) => {
                self.fail(event_loop, e);
                return;
            }''')
    s=rep(s,'''            if key.state.is_pressed() && !key.repeat && key.physical_key == PhysicalKey::Code(KeyCode::F1) {''','''            if self.world.debug.hotkey
                && key.state.is_pressed()
                && !key.repeat
                && key.physical_key == PhysicalKey::Code(KeyCode::F1)
            {''')
    return s
edit('crates/spark/src/app.rs', app)

# ---------------- core tests / timeout ----------------
edit('crates/spark-core/src/render.rs', lambda s: re.sub(r'\n    #\[test\]\n    fn default_has_msaa_and_shadows\(\) \{.*?\n    \}\n','\n',s,flags=re.S))
edit('crates/spark-script/src/lib.rs', lambda s: s.replace('timeout: std::time::Duration::from_secs(2),','timeout: std::time::Duration::from_secs(5),').replace('callback (default 2 s)','callback (default 5 s)'))

# ---------------- debug_api ----------------
def debug_api(s):
    s=re.sub(r'("[a-z_]+" => )with\(lua, \|w\| Ok\(w\.debug\.([a-z_]+(?:\(\))?)\)\)', r'\1with(lua, |w| w.debug.\2.into_lua(lua))', s)
    s=s.replace('with(lua, |w| Ok(w.debug.avg_frame_ms()))','with(lua, |w| Ok(w.debug.avg_frame_ms()))')
    s=rep(s,'use mlua::{Lua, Table, Value};','use mlua::{IntoLua, Lua, Table, Value};')
    a=s.index('    // `__newindex`: custom writes'); b=s.index('    dbg.set_metatable(Some(mt));')
    s=s[:a]+'''    // `__newindex`: overlay settings only. Writes never reach the shared standard library table.
    mt.set(
        "__newindex",
        lua.create_function(|lua, (_self, key, value): (Table, String, Value)| {
            let what = format!("debug.{key}");
            let on = || to_bool(&value, &what);
            match key.as_str() {
                "enabled" => with(lua, |w| Ok(w.debug.set_enabled(on()?))),
                "hotkey" => with(lua, |w| Ok(w.debug.hotkey = on()?)),
                "show_fps" => with(lua, |w| Ok(w.debug.set_show_fps(on()?))),
                "show_gpu" => with(lua, |w| Ok(w.debug.set_show_gpu(on()?))),
                "show_scene" => with(lua, |w| Ok(w.debug.set_show_scene(on()?))),
                "show_physics" => with(lua, |w| Ok(w.debug.set_show_physics(on()?))),
                "fps" | "frame_time" => Err(mlua::Error::runtime(format!("{what} is read-only"))),
                _ => Err(mlua::Error::runtime(format!(
                    "{what}: unknown field (settable: enabled, hotkey, show_fps, show_gpu, show_scene, show_physics)"
                ))),
            }
        })?,
    )?;

'''+s[b:]
    s=rep(s,'    dbg.set_metatable(Some(mt));','    dbg.set_metatable(Some(mt))?;')
    s=rep(s,'''                "enabled" => with(lua, |w| w.debug.enabled().into_lua(lua)),''','''                "enabled" => with(lua, |w| w.debug.enabled().into_lua(lua)),
                "hotkey" => with(lua, |w| w.debug.hotkey.into_lua(lua)),''')
    s=rep(s,'''    // `__index`: custom reads first, then fall back to std library.
    let std_for_index = std_debug.clone();''','''    // `__index`: custom reads first, then fall back to the std library (traceback, info, ...).
    let std_for_index = std_debug;''')
    s=rep(s,'''//! debug.show_fps = true         -- toggle individual overlay sections''','''//! debug.show_fps = true         -- toggle individual overlay sections
//! debug.hotkey = false          -- F1 no longer toggles the overlay (for games that use F1)''')
    s=rep(s,'//! debug.avg_frame_ms()         -- average frame time over last ~2 s','//! debug.avg_frame_ms()         -- average frame time over the last 120 frames')
    return s
edit('crates/spark-script/src/debug_api.rs', debug_api)

import shutil
shutil.copy('/data/fix/debug.luau', R+'crates/spark-script/tests/scripts/debug.luau')
edit('crates/spark-script/tests/flow.rs', lambda s: s if 'debug_contract' in s else s+'''
#[test]
fn debug_contract() {
    run_script("debug.luau", 10);
}
''')

# ---------------- docs ----------------
def api_md(s):
    if '## Debug overlay' in s: return s
    return rep(s,'''## Misc
''','''## Debug overlay

F1 shows an overlay with FPS, frame time (min / max / average over 120 frames), GPU name, object count,
draw calls and triangles of the last frame. The same `debug` table still holds the standard Luau
library (`debug.traceback()`, `debug.info(...)`).

- `debug.enabled` (read/write), `debug.toggle()` -> new state
- `debug.hotkey = false`: F1 no longer toggles the overlay (games that use F1 themselves)
- `debug.show_fps`, `debug.show_gpu`, `debug.show_scene`, `debug.show_physics` (read/write sections)
- `debug.fps`, `debug.frame_time` (ms, read-only), `debug.avg_frame_ms()`
- `debug.add_line(text, color="white")`: extra line for this frame only (call it every frame); `debug.clear_lines()`

Unknown fields and writes to read-only ones are errors.

## Misc
''')
edit('docs/LUAU_API.md', api_md)
def dluau(s):
    if 'declare debug' in s: return s
    return rep(s,'''declare function quit(): ()
''','''-- Spark's debug overlay merged with the standard Luau debug library.
declare debug: {
    enabled: boolean,
    hotkey: boolean,
    show_fps: boolean,
    show_gpu: boolean,
    show_scene: boolean,
    show_physics: boolean,
    fps: number, -- read-only
    frame_time: number, -- read-only (ms)
    toggle: () -> boolean,
    avg_frame_ms: () -> number,
    add_line: (text: string, color: ColorLike?) -> (),
    clear_lines: () -> (),
    traceback: (message: string?, level: number?) -> string,
    info: (...any) -> ...any,
}

declare function quit(): ()
''')
edit('docs/spark.d.luau', dluau)
for f,old,new in [('README.md','In a window: F12 = screenshot, F11 / Alt+Enter = fullscreen.','In a window: F1 = debug overlay, F12 = screenshot, F11 / Alt+Enter = fullscreen.'),
                  ('README.ru.md','В окне: F12 — скриншот, F11 / Alt+Enter — полный экран.','В окне: F1 — отладочный оверлей, F12 — скриншот, F11 / Alt+Enter — полный экран.')]:
    edit(f, lambda s: s.replace(old,new))

import sys, shutil, glob; sys.path.insert(0,'/data/fix')
from lib import *
FX='crates/spark-core/src/shaders/postfx/'

# ---------- shaders ----------
for f in ['ssao','motion_blur','fxaa']:
    shutil.copy(f'/data/fix/c4/{f}.wgsl', R+FX+f+'.wgsl'); print('replaced',f)
for p in glob.glob(R+FX+'*.wgsl'):
    s=open(p).read(); n=re.sub(r'\bParams\.([a-z_])', r'params.\1', s)
    n=n.replace('f32(frame.index)','frame.time.w').replace('frame.index','frame.time.w')
    if n!=s: open(p,'w').write(n); print('fixed', p)
def bloom(s):
    s=rep(s,'let scale = params.radius / isz.x;','let scale = vec2<f32>(params.radius) / isz; // pixels -> uv per axis (round on any aspect)')
    return s
edit(FX+'bloom.wgsl', bloom)
def dof(s):
    s=rep(s,'let radius = coc * max_radius_pixels / out_size.x;','let radius = coc * max_radius_pixels / out_size; // per axis: round bokeh on any aspect')
    return s
edit(FX+'dof.wgsl', dof)
def ca(s):
    s=rep(s,'let texel = 1.0 / input_size().x; // horizontal pixel size','let texel = 1.0 / input_size();')
    s=rep(s,'offset = dir * params.amount * texel;','offset = dir * 2.0 * params.amount * texel; // `amount` pixels at the screen edge')
    s=rep(s,'offset = vec2f(params.amount * texel, 0.0);','offset = vec2f(params.amount * texel.x, 0.0);')
    return s
edit(FX+'chromatic_aberration.wgsl', ca)
def cg(s):
    # standard ASC CDL: out = (in * slope + offset) ^ power, neutral offset (lift) = 0
    s=rep(s,'''    // ASC CDL lift  — additive offset per channel.''','''    // ASC CDL offset ("lift") — added per channel, 0 = neutral.''')
    s=rep(s,'''    // CDL formula:  out = (in * gain + lift - 1.0)
    //              then pow(max(out, 0), 1 / gamma)
    // The "- 1.0" lets lift act as a pedestal that shifts the black
    // point: lift = 1.0 is neutral (subtracting 1 brings it back to 0).
    c = c * params.gain + params.lift - vec3<f32>(1.0);''','''    // ASC CDL:  out = pow(max(in * gain + lift, 0), 1 / gamma)
    c = c * params.gain + params.lift;''')
    return s
edit(FX+'color_grade.wgsl', cg)
edit('crates/spark-core/src/shaders/common.wgsl', lambda s: rep(s,'''    shadow: vec4<f32>,      // enabled (0 / 1), 1 / map size, normal offset (m), shadow distance (m)
};''','''    shadow: vec4<f32>,      // enabled (0 / 1), 1 / map size, normal offset (m), shadow distance (m)
    prev_view_proj: mat4x4<f32>, // view_proj of the previous frame (camera motion blur, reprojection)
};''') if 'prev_view_proj' not in s else s)

# ---------- core config ----------
def core(s):
    s=s.replace('#[derive(Clone, Debug)]\n','#[derive(Clone, Debug, PartialEq)]\n').replace('#[derive(Clone, Debug, Default)]\n','#[derive(Clone, Debug, Default, PartialEq)]\n')
    s=rep(s,'use crate::shader::ShaderId;','use crate::shader::{PostFxKind, ShaderId};')
    s=rep(s,'''/// Tonemapping operator for HDR→LDR conversion.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub enum Tonemap {
    /// No tonemapping (pass-through).
    Off,
    /// ACES filmic — cinematic, good default.
    #[default]
    Aces,''','''/// Tonemapping operator: maps the HDR scene (values above 1) into the displayable range.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub enum Tonemap {
    /// No tonemapping: values above 1 are clipped (default, unchanged look of existing games).
    #[default]
    Off,
    /// ACES filmic — cinematic contrast, good choice with bloom / bright lights.
    Aces,''')
    s=rep(s,'''    /// Uncharted 2 / Hejl filmic.''','''    /// Hejl-Burgess-Dawson filmic.''')
    s=rep(s,'''    /// Bright threshold (0–1, pixels above this contribute to bloom).''','''    /// Brightness where bloom starts (linear; the HDR scene can go above 1).''')
    s=rep(s,'''    /// Bias to prevent self-occlusion (radians).''','''    /// Depth bias in meters against self-occlusion on flat surfaces.''')
    s=rep(s,'''    /// Max blur amount in pixels at unit velocity.''','''    /// Fraction of the frame time the "shutter" is open (1 = blur over the whole camera motion).''')
    s=re.sub(r'(pub struct ColorGrading \{.*?)(\n\}\n)', lambda m: m.group(0), s, flags=re.S)
    s=rep(s,'''            lift: [1.0; 3],''','''            lift: [0.0; 3],''')
    i=s.index('impl PostProcessing {')
    s=s[:i]+open('/data/fix/c4_core_impl.rs').read()
    return s
edit('crates/spark-core/src/render.rs', core)

# FXAA has no params any more
def shader_rs(s):
    if 'mod postfx_tests' not in s:
        s+='''
#[cfg(test)]
mod postfx_tests {
    use super::*;

    /// Every built-in effect passes naga validation (the renderer would panic on start otherwise).
    #[test]
    fn builtin_post_effects_compile() {
        let mut errors = Vec::new();
        for kind in PostFxKind::ALL {
            match ShaderData::compile(kind.name(), kind.shader_source()) {
                Ok(d) => assert_eq!(d.kind, ShaderKind::Post, "{}", kind.name()),
                Err(e) => errors.push(format!("{}:\\n{e}", kind.name())),
            }
        }
        assert!(errors.is_empty(), "{}", errors.join("\\n\\n"));
    }
}
'''
    s=s.replace('/// Depth-based motion blur.','/// Camera motion blur (reprojection with the previous frame camera).')
    s=s.replace('/// FXAA 3.11 antialiasing.','/// FXAA antialiasing (Lottes console variant).')
    s=s.replace('/// Single-pass bloom approximation.','/// Single-pass bloom (bright pass + 13-tap blur).')
    return s
edit('crates/spark-core/src/shader.rs', shader_rs)

# ---------- renderer ----------
def render(s):
    a=s.index('    /// Update built-in post effect params from `PostProcessing` settings, writing to GPU buffers.')
    b=s.index('    fn shader(&self, r: ShaderRef) -> &GpuShader {')
    s=s[:a]+'''    /// Uploads the parameters of the enabled built-in effects. A name mismatch is an engine bug
    /// (covered by tests); it is logged instead of panicking a running game.
    fn update_postfx_params(&mut self, passes: &[(spark_core::shader::PostFxKind, Vec<(&'static str, Vec<f32>)>)]) {
        for (kind, params) in passes {
            let i = *kind as usize;
            let data = &mut self.built_in_post_data[i];
            for (name, value) in params {
                if let Err(e) = data.set_param(name, value) {
                    log::error!("{e}");
                }
            }
            self.queue.write_buffer(&self.built_in_post[i].params, 0, &data.values);
        }
    }

'''+s[b:]
    s=rep(s,'''        self.update_postfx_params(&world.render.postfx);
''','')
    s=rep(s,'''        // Built-in post effects (run before user passes, at scene resolution).
        let postfx = &world.render.postfx;
        use spark_core::shader::PostFxKind as Fx;
        let fx = |kind: Fx| (ShaderRef::Fx(kind), scene_size);
        if postfx.ssao.is_some() { chain.push(fx(Fx::Ssao)); }
        if postfx.motion_blur.is_some() { chain.push(fx(Fx::MotionBlur)); }
        if postfx.dof.is_some() { chain.push(fx(Fx::Dof)); }
        if postfx.bloom.is_some() { chain.push(fx(Fx::Bloom)); }
        if postfx.color_grading.is_some() { chain.push(fx(Fx::ColorGrade)); }
        if postfx.tonemap != spark_core::render::Tonemap::Off { chain.push(fx(Fx::Tonemap)); }
        if postfx.fxaa { chain.push(fx(Fx::Fxaa)); }
        if postfx.chromatic_aberration.is_some() { chain.push(fx(Fx::ChromaticAberration)); }
        if postfx.film_grain.is_some() { chain.push(fx(Fx::FilmGrain)); }
        if postfx.vignette.is_some() { chain.push(fx(Fx::Vignette)); }
''','''        // Built-in post effects (run before user passes, at scene resolution).
        let passes = world.render.postfx.passes();
        self.update_postfx_params(&passes);
        chain.extend(passes.iter().map(|(kind, _)| (ShaderRef::Fx(*kind), scene_size)));
''')
    s=rep(s,'''            let data = ShaderData::compile(name, code).unwrap_or_else(|e| {
                panic!("built-in post shader '{name}' failed to compile: {e}")
            });''','''            // Validated by spark-core's `builtin_post_effects_compile` test.
            let data = ShaderData::compile(name, code).unwrap_or_else(|e| panic!("built-in post shader '{name}': {e}"));''')
    # HDR scene target
    s=rep(s,'''        let adapter_formats = [COLOR_FORMAT, DEPTH_FORMAT]
            .into_iter()''','''        // HDR scene (values above 1 survive until tonemapping / bloom) where the GPU can render,
        // blend and filter half floats; 8-bit sRGB otherwise (some GLES devices).
        let hdr = adapter.get_texture_format_features(HDR_FORMAT);
        let hdr_ok = hdr.allowed_usages.contains(wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING)
            && hdr.flags.contains(wgpu::TextureFormatFeatureFlags::FILTERABLE | wgpu::TextureFormatFeatureFlags::BLENDABLE);
        let scene_format = if hdr_ok { HDR_FORMAT } else { COLOR_FORMAT };
        let adapter_formats = [COLOR_FORMAT, DEPTH_FORMAT, scene_format]
            .into_iter()''')
    s=rep(s,'''const COLOR_FORMAT: wgpu::TextureFormat = wgpu::TextureFormat::Rgba8UnormSrgb;''','''const COLOR_FORMAT: wgpu::TextureFormat = wgpu::TextureFormat::Rgba8UnormSrgb;
/// Scene and intermediate post images when the GPU supports it (see `Renderer::scene_format`).
const HDR_FORMAT: wgpu::TextureFormat = wgpu::TextureFormat::Rgba16Float;''')
    s=rep(s,'''        canvas_pipelines
            .insert(COLOR_FORMAT, canvas_pipeline(&device, &canvas_pipeline_layout, &canvas_shader, COLOR_FORMAT));''','''        for f in [COLOR_FORMAT, scene_format] {
            canvas_pipelines.entry(f).or_insert_with(|| canvas_pipeline(&device, &canvas_pipeline_layout, &canvas_shader, f));
        }''')
    s=rep(s,'''    device_lost: Arc<AtomicBool>,''','''    device_lost: Arc<AtomicBool>,
    /// Format of the 3D scene image and intermediate post images: HDR (Rgba16Float) when supported.
    scene_format: wgpu::TextureFormat,
    /// (frame number, view_proj) of the last drawn frame and the view_proj before it (motion blur).
    camera_history: Option<(u64, Mat4)>,
    prev_view_proj: Mat4,''')
    s=rep(s,'''            device_lost,''','''            device_lost,
            scene_format,
            camera_history: None,
            prev_view_proj: Mat4::IDENTITY,''')
    s=rep(s,'let color = make("spark scene color", COLOR_FORMAT, rt, 1);','let color = make("spark scene color", self.scene_format, rt, 1);')
    s=rep(s,'let mc = make("spark scene color msaa", COLOR_FORMAT,','let mc = make("spark scene color msaa", self.scene_format,')
    s=rep(s,'[COLOR_FORMAT, DEPTH_FORMAT].iter().all(|f| self.adapter_formats','[self.scene_format, DEPTH_FORMAT].iter().all(|f| self.adapter_formats')
    s=rep(s,'self.ensure_shader_pipeline(c.shader, (COLOR_FORMAT, c.variant, samples))','self.ensure_shader_pipeline(c.shader, (self.scene_format, c.variant, samples))')
    s=rep(s,'self.ensure_shader_pipeline(ShaderRef::Default, (COLOR_FORMAT, c.variant, samples))','self.ensure_shader_pipeline(ShaderRef::Default, (self.scene_format, c.variant, samples))')
    s=rep(s,'pass.set_pipeline(self.pipeline(b.shader, (COLOR_FORMAT, b.variant, samples)));','pass.set_pipeline(self.pipeline(b.shader, (self.scene_format, b.variant, samples)));')
    s=rep(s,'self.draw_canvas_batches(&mut pass, COLOR_FORMAT, &scene_layer.batches, 0);','self.draw_canvas_batches(&mut pass, self.scene_format, &scene_layer.batches, 0);')
    s=rep(s,'''        // Pipelines: intermediate passes render to COLOR_FORMAT, the last one to `format`.''','''        // Pipelines: intermediate passes render to the scene format, the last one to `format`.''')
    s=rep(s,'let f = if i + 1 == n { format } else { COLOR_FORMAT };','let f = if i + 1 == n { format } else { self.scene_format };')
    s=rep(s,'''                    label: Some("spark post target"),
                    size: extent(size),
                    mip_level_count: 1,
                    sample_count: 1,
                    dimension: wgpu::TextureDimension::D2,
                    format: COLOR_FORMAT,''','''                    label: Some("spark post target"),
                    size: extent(size),
                    mip_level_count: 1,
                    sample_count: 1,
                    dimension: wgpu::TextureDimension::D2,
                    format: self.scene_format,''')
    s=rep(s,'pass.set_pipeline(self.pipeline(r, (if last { format } else { COLOR_FORMAT }, 0, 1)));','pass.set_pipeline(self.pipeline(r, (if last { format } else { self.scene_format }, 0, 1)));')
    # previous camera for motion blur
    s=rep(s,'''        let t = &world.time;
        let frame = FrameUniform {''','''        let t = &world.time;
        // Only a new frame moves the history (a screenshot of the same frame keeps it).
        if self.camera_history.is_none_or(|(f, _)| f != t.frame) {
            self.prev_view_proj = self.camera_history.map_or(view_proj, |(_, vp)| vp);
            self.camera_history = Some((t.frame, view_proj));
        }
        let frame = FrameUniform {''')
    s=rep(s,'''            shadow: [flag(shadows), 1.0 / shadow_size as f32, texel_world * 1.5, rs.shadow_distance],
        };''','''            shadow: [flag(shadows), 1.0 / shadow_size as f32, texel_world * 1.5, rs.shadow_distance],
            prev_view_proj: self.prev_view_proj.to_cols_array_2d(),
        };''')
    s=rep(s,'''    /// enabled, 1 / map size, normal offset, shadow distance
    shadow: [f32; 4],
}''','''    /// enabled, 1 / map size, normal offset, shadow distance
    shadow: [f32; 4],
    prev_view_proj: [[f32; 4]; 4],
}''')
    if 'fn builtin_effects_render' not in s:
        s=s.rstrip()[:-1]+open('/data/fix/c4_render_test.rs').read()+'}\n'
    return s
edit('crates/spark-render/src/lib.rs', render)

# ---------- part 2: vignette color, Luau bindings, screenshot stats, tests ----------
def vig(s):
    s=rep(s,'''    /// Tint color (RGB, 0–1).
    pub color: [f32; 3],''','''    /// Color the edges fade to (usually black).
    pub color: crate::Color,''')
    s=rep(s,'color: [0.0; 3] }','color: crate::Color::BLACK }')
    return s
edit('crates/spark-core/src/render.rs', vig)
def lua(s):
    if 'trait FxSettings' in s: return s
    a=s.index('        // ── Built-in post-processing effects')
    b=s.index('pub(crate) fn install(')
    return s[:a]+open('/data/fix/c4_lua_fx.rs').read()+'\n\n'+s[b:]
edit('crates/spark-script/src/shader.rs', lua)
def shot(s):
    s=rep(s,'''        self.last_stats = self.draw_scene(&mut encoder, world);
        // ensure_capture() was just called, so self.capture is Some.
        let capture = self.capture.take().ok_or_else(|| "capture target was not ensured".to_string())?;
        self.draw_post(&mut encoder, &capture.view, COLOR_FORMAT, world);''','''        let mut stats = self.draw_scene(&mut encoder, world);
        // ensure_capture() was just called, so self.capture is Some.
        let capture = self.capture.take().ok_or_else(|| "capture target was not ensured".to_string())?;
        stats.post_passes = self.draw_post(&mut encoder, &capture.view, COLOR_FORMAT, world);
        self.last_stats = stats;''')
    s=rep(s,"fn update_postfx_params(&mut self, passes: &[(spark_core::shader::PostFxKind, Vec<(&'static str, Vec<f32>)>)]) {","fn update_postfx_params(&mut self, passes: &[(spark_core::shader::PostFxKind, spark_core::render::PostFxParams)]) {")
    return s
edit('crates/spark-render/src/lib.rs', shot)
shutil.copy('/data/fix/postfx.luau', R+'crates/spark-script/tests/scripts/postfx.luau')
edit('crates/spark-script/tests/flow.rs', lambda s: s if 'postfx_contract' in s else s.rstrip()+'''

#[test]
fn postfx_contract() {
    run_script("postfx.luau", 10);
}
''')

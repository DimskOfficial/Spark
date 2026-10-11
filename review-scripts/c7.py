import sys; sys.path.insert(0,'/data/fix')
from lib import *
F='/data/fix/c7/'
# ---------------- assets: cubemaps ----------------
def assets(s):
    s=rep(s,'''/// Handle to a texture stored in [`Assets`].
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct TextureId(pub u32);
''','''/// Handle to a texture stored in [`Assets`].
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct TextureId(pub u32);

/// Handle to a cubemap (six square faces) stored in [`Assets`].
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct CubemapId(pub u32);

/// Cube faces in GPU layer order.
pub const CUBE_FACES: [&str; 6] = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"];
''')
    s=rep(s,'''    texture_paths: HashMap<PathBuf, TextureId>,
    shaders: Vec<ShaderData>,''','''    texture_paths: HashMap<PathBuf, TextureId>,
    cubemaps: Vec<[ImageData; 6]>,
    cubemap_paths: HashMap<PathBuf, CubemapId>,
    shaders: Vec<ShaderData>,''')
    s=rep(s,'''    /// Compiles WGSL code (see [`crate::shader`]).''','''    /// Adds a cubemap from six square faces of the same size, in [`CUBE_FACES`] order
    /// (+X, -X, +Y, -Y, +Z, -Z; +Y is up, -Z is forward like the Spark camera).
    pub fn add_cubemap(&mut self, faces: [ImageData; 6]) -> Result<CubemapId, String> {
        let size = faces[0].width;
        if size == 0 {
            return Err("cubemap faces are empty".into());
        }
        for (f, name) in faces.iter().zip(CUBE_FACES) {
            if f.width != size || f.height != size {
                return Err(format!("cubemap face {name} is {}x{}; all faces must be {size}x{size}", f.width, f.height));
            }
        }
        self.cubemaps.push(faces);
        Ok(CubemapId(self.cubemaps.len() as u32 - 1))
    }

    /// Loads a cubemap once from a horizontal strip image (6 square faces side by side, in
    /// +X, -X, +Y, -Y, +Z, -Z order, so the image is 6 times wider than tall).
    pub fn load_cubemap(&mut self, path: &str) -> Result<CubemapId, String> {
        let full = self.resolve(path);
        if let Some(&id) = self.cubemap_paths.get(&full) {
            return Ok(id);
        }
        let strip = ImageData::load(&full)?;
        let id = self.add_cubemap(split_strip(&strip).map_err(|e| format!("{path}: {e}"))?)?;
        self.cubemap_paths.insert(full, id);
        Ok(id)
    }

    pub fn cubemap(&self, id: CubemapId) -> Option<&[ImageData; 6]> {
        self.cubemaps.get(id.0 as usize)
    }

    pub fn cubemap_count(&self) -> usize {
        self.cubemaps.len()
    }

    /// Compiles WGSL code (see [`crate::shader`]).''')
    s=rep(s,'''        self.texture_paths.clear();
        self.shaders.clear();''','''        self.texture_paths.clear();
        self.cubemaps.clear();
        self.cubemap_paths.clear();
        self.shaders.clear();''')
    i=s.index('#[cfg(test)]') if '#[cfg(test)]' in s else len(s)
    s=s[:i]+'''/// Cuts a 6:1 horizontal strip into its six square faces.
fn split_strip(strip: &ImageData) -> Result<[ImageData; 6], String> {
    let size = strip.height;
    if size == 0 || strip.width != size * 6 {
        return Err(format!(
            "a cubemap strip must be 6 square faces side by side (width = 6 x height), got {}x{}",
            strip.width, strip.height
        ));
    }
    Ok(std::array::from_fn(|face| {
        let mut pixels = Vec::with_capacity((size * size * 4) as usize);
        for y in 0..size {
            let start = ((y * strip.width + face as u32 * size) * 4) as usize;
            pixels.extend_from_slice(&strip.pixels[start..start + (size * 4) as usize]);
        }
        ImageData::new(size, size, pixels)
    }))
}

'''+s[i:]
    return s
edit('crates/spark-core/src/assets.rs', assets)

edit('crates/spark-core/src/lib.rs', lambda s: rep(rep(s,'pub use assets::{Assets, ImageData, MeshId, TextureId};','pub use assets::{Assets, CUBE_FACES, CubemapId, ImageData, MeshId, TextureId};'),
  'pub use scene::{Fog, Light, LightKind, Object, ObjectId, Scene, Sun};','pub use scene::{Fog, Light, LightKind, Object, ObjectId, Scene, Sky, Sun};'))

# ---------------- scene: Sky ----------------
def scene(s):
    s=rep(s,'''#[derive(Clone, Debug)]
struct Slot {''','''/// Sky drawn behind every object (instead of the flat `background` color). It can also light
/// the scene (image-based lighting): see [`Sky::lighting`].
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Sky {
    /// Color straight up; the sky fades to `bottom` straight down (the horizon is halfway).
    pub top: Color,
    /// Color straight down.
    pub bottom: Color,
    /// Optional cubemap (photo or painted sky), drawn over the gradient.
    pub cubemap: Option<CubemapId>,
    /// How much of the cubemap covers the gradient, 0..1.
    pub blend: f32,
    /// Image-based lighting strength. 0 = off (objects use the flat `ambient` color);
    /// above 0 the sky replaces the ambient light (blue from above, ground color from below)
    /// and PBR surfaces reflect it.
    pub lighting: f32,
}

impl Sky {
    /// Two-color gradient sky.
    pub fn gradient(top: Color, bottom: Color) -> Self {
        Self { top, bottom, cubemap: None, blend: 1.0, lighting: 0.0 }
    }

    /// Cubemap sky (see [`crate::Assets::load_cubemap`]).
    pub fn cubemap(cubemap: CubemapId) -> Self {
        Self { cubemap: Some(cubemap), ..Self::default() }
    }

    /// Sets the image-based lighting strength (0 = off).
    pub fn with_lighting(mut self, lighting: f32) -> Self {
        self.lighting = lighting.max(0.0);
        self
    }
}

impl Default for Sky {
    fn default() -> Self {
        Self::gradient(Color::rgb(0.38, 0.62, 0.92), Color::rgb(0.22, 0.2, 0.18))
    }
}

#[derive(Clone, Debug)]
struct Slot {''')
    s=rep(s,'''    pub fog: Option<Fog>,
}''','''    pub fog: Option<Fog>,
    /// Sky behind everything; `None` = clear to `background`.
    pub sky: Option<Sky>,
}''')
    s=rep(s,'''            fog: None,
        }''','''            fog: None,
            sky: None,
        }''')
    return s
edit('crates/spark-core/src/scene.rs', scene)

# ---------------- shaders ----------------
def common(s):
    return rep(s,'''    prev_view_proj: mat4x4<f32>, // view_proj of the previous frame (camera motion blur, reprojection)
};''','''    prev_view_proj: mat4x4<f32>, // view_proj of the previous frame (camera motion blur, reprojection)
    sky_top: vec4<f32>,     // rgb, linear
    sky_bottom: vec4<f32>,  // rgb, linear
    sky: vec4<f32>,         // enabled (0 / 1), cubemap blend (0 = no cubemap), lighting strength, cubemap mip count
};''')
edit('crates/spark-core/src/shaders/common.wgsl', common)

def surface(s):
    s=rep(s,'''    var light = frame.ambient.rgb;
    if (sun > 0.0) {''','''    var light = ambient_light(n);
    if (sun > 0.0) {''')
    s=rep(s,'''    return frame.ambient.rgb * ((1.0 - specular) * (1.0 - metallic) * base + specular);''','''    let diffuse = ambient_light(n) * (1.0 - specular) * (1.0 - metallic) * base;
    return diffuse + ambient_reflection(reflect(-v, n), roughness) * specular;''')
    s=rep(s,'''// Ambient light on a PBR surface: diffuse plus a rough environment reflection of the ambient color
// (so metals are not black without lights).''','''// Ambient light on a PBR surface: diffuse plus the environment reflection (the sky with sky
// lighting on, else the ambient color), so metals are not black without lights.''')
    return s
edit('crates/spark-core/src/shaders/surface.wgsl', surface)
import shutil; shutil.copy(F+'skybox.wgsl', R+'crates/spark-core/src/shaders/skybox.wgsl'); shutil.copy(F+'sky.wgsl', R+'crates/spark-core/src/shaders/sky.wgsl')

def shader_rs(s):
    s=rep(s,'''const POST: &str = include_str!("shaders/post.wgsl");''','''const POST: &str = include_str!("shaders/post.wgsl");
/// Sky bindings and helpers (`sky_color`, `ambient_light`): surface shaders and the skybox pass.
const SKY: &str = include_str!("shaders/sky.wgsl");
const SKYBOX: &str = include_str!("shaders/skybox.wgsl");''')
    s=rep(s,'''            s.push_str(&SURFACE.replace("SPARK_VERTEX", vs).replace("SPARK_FRAGMENT", fs));''','''            s.push_str(SKY);
            s.push_str(&SURFACE.replace("SPARK_VERTEX", vs).replace("SPARK_FRAGMENT", fs));''')
    s=rep(s,'''/// Game code + engine prelude for `kind`.''','''/// Full WGSL of the skybox pass (`sky_vs` / `sky_fs`). It shares `sky_color` with surface
/// shaders, so the sky behind objects matches their reflections.
pub fn skybox_source() -> String {
    format!("{COMMON}{SKY}{SKYBOX}")
}

/// Game code + engine prelude for `kind`.''')
    return s
edit('crates/spark-core/src/shader.rs', shader_rs)
edit('crates/spark-core/src/scene.rs', lambda s: rep(s,'use crate::assets::MeshId;','use crate::assets::{CubemapId, MeshId};'))

# ---------------- renderer ----------------
def render(s):
    s=rep(s,'''    Aabb, Assets, Batch, Canvas, CanvasTexture, Color, ImageData, Layer, Mat4, MeshId, PassSize, ShaderData, ShaderKind,
    TextureFilter, TextureId, Vec3, Vec4, Vertex, Vertex2D, World,
};''','''    Aabb, Assets, Batch, Canvas, CanvasTexture, Color, CubemapId, ImageData, Layer, Mat4, MeshId, PassSize, ShaderData,
    ShaderKind, TextureFilter, TextureId, Vec3, Vec4, Vertex, Vertex2D, World,
};''')
    s=rep(s,'''    prev_view_proj: [[f32; 4]; 4],
}

const MAX_LIGHTS''','''    prev_view_proj: [[f32; 4]; 4],
    sky_top: [f32; 4],
    sky_bottom: [f32; 4],
    /// enabled, cubemap blend, lighting strength, cubemap mip count
    sky: [f32; 4],
}

const MAX_LIGHTS''')
    s=rep(s,'''struct GpuTexture {
    texture: wgpu::Texture,''','''/// Sky cubemap on the GPU (full mip chain: blurrier mips light rough surfaces).
struct GpuCube {
    view: wgpu::TextureView,
    mips: u32,
}

struct GpuTexture {
    texture: wgpu::Texture,''')
    # fields
    s=rep(s,'''    /// 1x1 map bound when shadows are off.
    shadow_dummy: ShadowMap,
    shadow: Option<ShadowMap>,''','''    /// 1x1 map bound when shadows are off.
    shadow_dummy: ShadowMap,
    shadow: Option<ShadowMap>,
    /// Trilinear sampler of sky cubemaps.
    sky_sampler: wgpu::Sampler,
    /// 1x1 white cube bound when the sky has no cubemap.
    sky_dummy: GpuCube,
    cubemaps: Vec<GpuCube>,
    /// What `frame_bind_group` was built with: shadow map size (None = dummy), sky cubemap.
    frame_group_key: (Option<u32>, Option<usize>),
    sky_pipeline_layout: wgpu::PipelineLayout,
    sky_shader: wgpu::ShaderModule,
    /// Skybox pipelines per MSAA sample count.
    sky_pipelines: HashMap<u32, wgpu::RenderPipeline>,''')
    s=rep(s,'''            shadow_dummy,
            shadow: None,''','''            shadow_dummy,
            shadow: None,
            sky_sampler,
            sky_dummy,
            cubemaps: Vec::new(),
            frame_group_key: (None, None),
            sky_pipeline_layout,
            sky_shader,
            sky_pipelines: HashMap::new(),''')
    # layout
    s=rep(s,'''                    ty: wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Comparison),
                    count: None,
                },
            ],
        );
        let object_layout''','''                    ty: wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Comparison),
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 3,
                    visibility: fs,
                    ty: wgpu::BindingType::Texture {
                        sample_type: wgpu::TextureSampleType::Float { filterable: true },
                        view_dimension: wgpu::TextureViewDimension::Cube,
                        multisampled: false,
                    },
                    count: None,
                },
                sampler_entry(4, fs),
            ],
        );
        let object_layout''')
    s=rep(s,'''        let shadow_dummy = shadow_map(&device, 1);
        let frame_bind_group = frame_bind_group(&device, &frame_layout, &frame_buffer, &shadow_dummy.view, &shadow_sampler);''','''        let shadow_dummy = shadow_map(&device, 1);
        let sky_sampler = device.create_sampler(&wgpu::SamplerDescriptor {
            label: Some("spark sky sampler"),
            mag_filter: wgpu::FilterMode::Linear,
            min_filter: wgpu::FilterMode::Linear,
            mipmap_filter: wgpu::MipmapFilterMode::Linear,
            ..Default::default()
        });
        let sky_dummy = upload_cube(&device, &queue, &std::array::from_fn(|_| ImageData::solid(Color::WHITE)));
        let frame_bind_group =
            frame_bind_group(&device, &frame_layout, &frame_buffer, &shadow_dummy.view, &shadow_sampler, &sky_dummy.view, &sky_sampler);
        let sky_pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("spark sky"),
            bind_group_layouts: &[Some(&frame_layout)],
            immediate_size: 0,
        });
        let sky_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("spark sky"),
            source: wgpu::ShaderSource::Wgsl(spark_core::shader::skybox_source().into()),
        });''')
    s=rep(s,'''fn frame_bind_group(
    device: &wgpu::Device,
    layout: &wgpu::BindGroupLayout,
    buffer: &wgpu::Buffer,
    shadow: &wgpu::TextureView,
    sampler: &wgpu::Sampler,
) -> wgpu::BindGroup {
    device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("spark frame"),
        layout,
        entries: &[
            wgpu::BindGroupEntry { binding: 0, resource: buffer.as_entire_binding() },
            wgpu::BindGroupEntry { binding: 1, resource: wgpu::BindingResource::TextureView(shadow) },
            wgpu::BindGroupEntry { binding: 2, resource: wgpu::BindingResource::Sampler(sampler) },
        ],
    })
}''','''fn frame_bind_group(
    device: &wgpu::Device,
    layout: &wgpu::BindGroupLayout,
    buffer: &wgpu::Buffer,
    shadow: &wgpu::TextureView,
    sampler: &wgpu::Sampler,
    sky: &wgpu::TextureView,
    sky_sampler: &wgpu::Sampler,
) -> wgpu::BindGroup {
    device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("spark frame"),
        layout,
        entries: &[
            wgpu::BindGroupEntry { binding: 0, resource: buffer.as_entire_binding() },
            wgpu::BindGroupEntry { binding: 1, resource: wgpu::BindingResource::TextureView(shadow) },
            wgpu::BindGroupEntry { binding: 2, resource: wgpu::BindingResource::Sampler(sampler) },
            wgpu::BindGroupEntry { binding: 3, resource: wgpu::BindingResource::TextureView(sky) },
            wgpu::BindGroupEntry { binding: 4, resource: wgpu::BindingResource::Sampler(sky_sampler) },
        ],
    })
}

/// Uploads six square faces (+X, -X, +Y, -Y, +Z, -Z) with a full mip chain each.
fn upload_cube(device: &wgpu::Device, queue: &wgpu::Queue, faces: &[ImageData; 6]) -> GpuCube {
    let size = faces[0].width;
    let mut mips = 1;
    let mut data = Vec::new();
    for face in faces {
        let (levels, bytes) = build_mips(face);
        mips = levels;
        data.extend_from_slice(&bytes);
    }
    let texture = device.create_texture_with_data(
        queue,
        &wgpu::TextureDescriptor {
            label: Some("spark sky cubemap"),
            size: wgpu::Extent3d { width: size, height: size, depth_or_array_layers: 6 },
            mip_level_count: mips,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: COLOR_FORMAT,
            usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
            view_formats: &[],
        },
        wgpu::util::TextureDataOrder::LayerMajor,
        &data,
    );
    let view = texture.create_view(&wgpu::TextureViewDescriptor {
        dimension: Some(wgpu::TextureViewDimension::Cube),
        ..Default::default()
    });
    GpuCube { view, mips }
}''')
    # sync assets
    s=rep(s,'''            self.textures.clear();
            self.normal_mapped_groups.clear();''','''            self.textures.clear();
            self.cubemaps.clear();
            self.normal_mapped_groups.clear();''')
    s=rep(s,'''            self.textures.push(gpu);
        }
    }
''','''            self.textures.push(gpu);
        }
        while self.cubemaps.len() < assets.cubemap_count() {
            // loop condition guarantees cubemap id < assets.cubemap_count().
            let faces = assets.cubemap(CubemapId(self.cubemaps.len() as u32)).expect("cubemap id in range");
            let gpu = if faces[0].width > max {
                log::error!("cubemap faces {0}x{0} are too big (max {1}); using white", faces[0].width, max);
                upload_cube(&self.device, &self.queue, &std::array::from_fn(|_| ImageData::solid(Color::WHITE)))
            } else {
                upload_cube(&self.device, &self.queue, faces)
            };
            self.cubemaps.push(gpu);
        }
    }
''')
    # frame group rebuild
    s=rep(s,'''        if shadows && self.shadow.as_ref().is_none_or(|m| m.size != shadow_size) {
            let map = shadow_map(&self.device, shadow_size);
            self.frame_bind_group = frame_bind_group(&self.device, &self.frame_layout, &self.frame_buffer, &map.view, &self.shadow_sampler);
            self.shadow = Some(map);
        } else if !shadows && self.shadow.is_some() {
            self.shadow = None;
            self.frame_bind_group =
                frame_bind_group(&self.device, &self.frame_layout, &self.frame_buffer, &self.shadow_dummy.view, &self.shadow_sampler);
        }''','''        if shadows && self.shadow.as_ref().is_none_or(|m| m.size != shadow_size) {
            self.shadow = Some(shadow_map(&self.device, shadow_size));
        } else if !shadows {
            self.shadow = None;
        }
        let sky = scene.sky;
        let sky_cube = sky.and_then(|s| s.cubemap).map(|c| c.0 as usize).filter(|&c| c < self.cubemaps.len());
        let key = (self.shadow.as_ref().map(|m| m.size), sky_cube);
        if key != self.frame_group_key {
            let shadow_view = self.shadow.as_ref().map_or(&self.shadow_dummy.view, |m| &m.view);
            let sky_view = sky_cube.map_or(&self.sky_dummy.view, |c| &self.cubemaps[c].view);
            self.frame_bind_group = frame_bind_group(
                &self.device,
                &self.frame_layout,
                &self.frame_buffer,
                shadow_view,
                &self.shadow_sampler,
                sky_view,
                &self.sky_sampler,
            );
            self.frame_group_key = key;
        }''')
    s=rep(s,'''            prev_view_proj: self.prev_view_proj.to_cols_array_2d(),
        };''','''            prev_view_proj: self.prev_view_proj.to_cols_array_2d(),
            sky_top: sky.map_or([0.0; 4], |s| s.top.to_linear()),
            sky_bottom: sky.map_or([0.0; 4], |s| s.bottom.to_linear()),
            sky: match sky {
                Some(s) => [
                    1.0,
                    if sky_cube.is_some() { s.blend.clamp(0.0, 1.0) } else { 0.0 },
                    s.lighting.max(0.0),
                    sky_cube.map_or(1, |c| self.cubemaps[c].mips) as f32,
                ],
                None => [0.0; 4],
            },
        };''')
    # pipeline + draw
    s=rep(s,'''        let target = self.scene_target.as_ref().expect("scene target"); // ensure_scene_target() was called
        let bg = scene.background.to_linear();''','''        if sky.is_some() {
            self.ensure_sky_pipeline(samples);
        }
        let target = self.scene_target.as_ref().expect("scene target"); // ensure_scene_target() was called
        let bg = scene.background.to_linear();''')
    s=rep(s,'''            pass.set_bind_group(0, &self.frame_bind_group, &[]);
            let (mut last_pipe, mut last_shader, mut last_mesh, mut last_texture) =''','''            pass.set_bind_group(0, &self.frame_bind_group, &[]);
            if sky.is_some() {
                pass.set_pipeline(&self.sky_pipelines[&samples]); // ensure_sky_pipeline() above
                pass.draw(0..3, 0..1);
            }
            let (mut last_pipe, mut last_shader, mut last_mesh, mut last_texture) =''')
    s=rep(s,'''    fn ensure_scene_target(&mut self, size: (u32, u32), samples: u32) {''','''    /// Skybox pipeline for the scene pass at `samples` MSAA (depth test off, no depth write).
    fn ensure_sky_pipeline(&mut self, samples: u32) {
        if self.sky_pipelines.contains_key(&samples) {
            return;
        }
        let p = self.device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("spark sky"),
            layout: Some(&self.sky_pipeline_layout),
            vertex: wgpu::VertexState {
                module: &self.sky_shader,
                entry_point: Some("sky_vs"),
                compilation_options: Default::default(),
                buffers: &[],
            },
            primitive: Default::default(),
            depth_stencil: Some(wgpu::DepthStencilState {
                format: DEPTH_FORMAT,
                depth_write_enabled: Some(false),
                depth_compare: Some(wgpu::CompareFunction::Always),
                stencil: Default::default(),
                bias: Default::default(),
            }),
            multisample: wgpu::MultisampleState { count: samples, ..Default::default() },
            fragment: Some(wgpu::FragmentState {
                module: &self.sky_shader,
                entry_point: Some("sky_fs"),
                compilation_options: Default::default(),
                targets: &[Some(self.scene_format.into())],
            }),
            multiview_mask: None,
            cache: None,
        });
        self.sky_pipelines.insert(samples, p);
    }

    fn ensure_scene_target(&mut self, size: (u32, u32), samples: u32) {''')
    return s
edit('crates/spark-render/src/lib.rs', render)

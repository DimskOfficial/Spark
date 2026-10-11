import sys; sys.path.insert(0,'/data/fix')
from lib import *

# ---------------- core: material ----------------
def material(s):
    s=rep(s,'''    pub cast_shadow: bool,
}''','''    pub cast_shadow: bool,
    /// Physically based shading (Cook-Torrance GGX with `metallic` / `roughness`) instead of the
    /// classic diffuse look. Turned on by [`Material::pbr`], `with_metallic`, `with_roughness`.
    pub pbr: bool,
    /// 0 = dielectric (plastic, wood, stone), 1 = metal. Used when `pbr` is on.
    pub metallic: f32,
    /// 0 = mirror-smooth, 1 = fully rough. Used when `pbr` is on.
    pub roughness: f32,
    /// Light the surface emits by itself, added after lighting (black = none). Works in every mode.
    pub emissive: Color,
    /// Tangent-space normal map (OpenGL convention: green points along +V). Works with and without `pbr`.
    pub normal_map: Option<TextureId>,
}''')
    s=rep(s,'''            cast_shadow: true,
        }''','''            cast_shadow: true,
            pbr: false,
            metallic: 0.0,
            roughness: 0.5,
            emissive: Color::BLACK,
            normal_map: None,
        }''')
    i=s.index('\n#[cfg(test)]')
    j=s.rindex('}', 0, i)  # end of impl Material
    s=s[:j]+'''
    /// PBR material: base `color`, `metallic` (0..1) and `roughness` (0..1).
    pub fn pbr(color: Color, metallic: f32, roughness: f32) -> Self {
        Self::color(color).with_metallic(metallic).with_roughness(roughness)
    }

    /// Sets `metallic` (clamped to 0..1) and turns on PBR shading.
    pub fn with_metallic(mut self, metallic: f32) -> Self {
        self.metallic = metallic.clamp(0.0, 1.0);
        self.pbr = true;
        self
    }

    /// Sets `roughness` (clamped to 0..1) and turns on PBR shading.
    pub fn with_roughness(mut self, roughness: f32) -> Self {
        self.roughness = roughness.clamp(0.0, 1.0);
        self.pbr = true;
        self
    }

    pub fn with_emissive(mut self, emissive: Color) -> Self {
        self.emissive = emissive;
        self
    }

    pub fn with_normal_map(mut self, normal_map: Option<TextureId>) -> Self {
        self.normal_map = normal_map;
        self
    }
'''+s[j:]
    s=s.rstrip()
    assert s.endswith('}')
    s=s[:-1]+'''
    #[test]
    fn pbr_is_opt_in() {
        let m = Material::default();
        assert!(!m.pbr, "existing games keep the classic look");
        assert_eq!((m.metallic, m.roughness, m.emissive, m.normal_map), (0.0, 0.5, Color::BLACK, None));
    }

    #[test]
    fn pbr_builders_clamp_and_enable() {
        let m = Material::pbr(Color::RED, 2.0, -1.0);
        assert!(m.pbr);
        assert_eq!((m.metallic, m.roughness), (1.0, 0.0));
        assert_eq!(m.color, Color::RED);
        assert!(Material::default().with_roughness(0.5).pbr, "even the default value turns PBR on");
        let e = Material::default().with_emissive(Color::BLUE);
        assert!(!e.pbr, "emissive works without PBR");
    }
}
'''
    return s
edit('crates/spark-core/src/material.rs', material)

# ---------------- core: LOD ----------------
def scene(s):
    s=rep(s,'''    pub mesh: Option<MeshId>,
    pub material: Material,''','''    pub mesh: Option<MeshId>,
    /// Level of detail: `(distance, mesh)` pairs. From `distance` meters away from the camera on
    /// the renderer draws that mesh instead of `mesh` (the entry with the largest distance that is
    /// reached wins; order does not matter). Picking, physics and bounds use `mesh`.
    pub lod: Vec<(f32, MeshId)>,
    pub material: Material,''')
    s=rep(s,'''            mesh,
            material,''','''            mesh,
            lod: Vec::new(),
            material,''', must=False)
    return s
edit('crates/spark-core/src/scene.rs', scene)
def scene2(s):
    s=rep(s,'''            mesh: None,
            material: Material::default(),''','''            mesh: None,
            lod: Vec::new(),
            material: Material::default(),''')
    s=rep(s,'''    /// Direct children of this object.
    pub fn child_ids(&self) -> &[ObjectId] {''','''    /// Mesh drawn at `distance` meters from the camera: the [`Object::lod`] entry with the
    /// largest distance not above `distance`, or [`Object::mesh`] when none is reached.
    pub fn mesh_at(&self, distance: f32) -> Option<MeshId> {
        self.lod
            .iter()
            .filter(|(d, _)| *d <= distance)
            .max_by(|a, b| a.0.total_cmp(&b.0))
            .map(|(_, m)| *m)
            .or(self.mesh)
    }

    /// Direct children of this object.
    pub fn child_ids(&self) -> &[ObjectId] {''')
    return s
edit('crates/spark-core/src/scene.rs', scene2)
def scene_test(s):
    if 'fn lod_picks' in s: return s
    i=s.index('#[cfg(test)]\nmod tests {')
    j=s.index('\n', s.index('mod tests {', i))
    # insert after `use super::*;` line
    k=s.index('\n', s.index('use super::*;', j))
    return s[:k+1]+'''
    #[test]
    fn lod_picks_the_farthest_reached_level() {
        let mut o = Object::empty();
        o.mesh = Some(MeshId(0));
        o.lod = vec![(40.0, MeshId(2)), (10.0, MeshId(1))]; // any order
        assert_eq!(o.mesh_at(0.0), Some(MeshId(0)));
        assert_eq!(o.mesh_at(9.9), Some(MeshId(0)));
        assert_eq!(o.mesh_at(10.0), Some(MeshId(1)));
        assert_eq!(o.mesh_at(39.0), Some(MeshId(1)));
        assert_eq!(o.mesh_at(1000.0), Some(MeshId(2)));
        assert_eq!(Object::empty().mesh_at(5.0), None);
    }
'''+s[k+1:]
edit('crates/spark-core/src/scene.rs', scene_test)

# ---------------- shader ----------------
def surface(s):
    s=rep(s,'''    info: vec4<f32>,   // tiling x, tiling y, unlit (0 / 1), -
};''','''    info: vec4<f32>,   // tiling x, tiling y, unlit (0 / 1), pbr (0 / 1)
    pbr: vec4<f32>,    // metallic, roughness, has normal map (0 / 1), -
    emissive: vec4<f32>, // rgb, linear
};''')
    s=rep(s,'''@group(2) @binding(1) var base_sampler: sampler;''','''@group(2) @binding(1) var base_sampler: sampler;
// Material normal map (a flat 1x1 map when the material has none). See `surface_normal`.
@group(2) @binding(2) var normal_texture: texture_2d<f32>;''')
    s=rep(s,'''fn apply_fog(rgb: vec3<f32>, world_pos: vec3<f32>) -> vec3<f32> {''', open('/data/fix/c6/pbr.wgsl').read().lstrip('\n')+'''
fn apply_fog(rgb: vec3<f32>, world_pos: vec3<f32>) -> vec3<f32> {''')
    s=rep(s,'''    var rgb = base.rgb;
    if (object.info.z < 0.5) {
        rgb = rgb * lighting(f.world_pos, f.normal);
    }
    return vec4<f32>(apply_fog(rgb, f.world_pos), base.a);''','''    let n = surface_normal(f.world_pos, f.normal, f.uv);
    var rgb = base.rgb;
    if (object.info.z < 0.5) {
        if (object.info.w > 0.5) {
            rgb = pbr_lighting(f.world_pos, n, base.rgb, object.pbr.x, object.pbr.y);
        } else {
            rgb = rgb * lighting(f.world_pos, n);
        }
    }
    rgb = rgb + object.emissive.rgb;
    return vec4<f32>(apply_fog(rgb, f.world_pos), base.a);''')
    return s
edit('crates/spark-core/src/shaders/surface.wgsl', surface)

# ---------------- renderer ----------------
def render(s):
    s=rep(s,'''    /// tiling x, tiling y, unlit, -
    info: [f32; 4],
}''','''    /// tiling x, tiling y, unlit, pbr
    info: [f32; 4],
    /// metallic, roughness, has normal map, -
    pbr: [f32; 4],
    /// rgb (linear), -
    emissive: [f32; 4],
}''')
    s=rep(s,'''    texture: Option<usize>,
    /// View-space distance (transparent sorting).''','''    texture: Option<usize>,
    normal_map: Option<usize>,
    /// View-space distance (transparent sorting).''')
    s=rep(s,'''    mesh: usize,
    texture: Option<usize>,
    /// Byte offset of the batch's first object (dynamic uniform offset).''','''    mesh: usize,
    texture: Option<usize>,
    normal_map: Option<usize>,
    /// Byte offset of the batch's first object (dynamic uniform offset).''')
    s=rep(s,'''    textures: Vec<GpuTexture>,
    white: GpuTexture,''','''    textures: Vec<GpuTexture>,
    white: GpuTexture,
    /// Flat tangent-space normal (bound as `normal_texture` when a material has no normal map).
    flat_normal: wgpu::TextureView,
    /// Texture bind groups of normal-mapped materials: (base texture, normal map, nearest).
    normal_mapped_groups: HashMap<(Option<usize>, usize, bool), wgpu::BindGroup>,''')
    s=rep(s,'''let texture_layout = bind_group_layout(&device, "spark texture", &[texture_entry(0, fs), sampler_entry(1, fs)]);''','''// Base texture, its sampler and the material normal map (2D canvas uses only the first two).
        let texture_layout = bind_group_layout(&device, "spark texture", &[texture_entry(0, fs), sampler_entry(1, fs), texture_entry(2, fs)]);''')
    s=rep(s,'''        let white =
            upload_texture(&device, &queue, &texture_layout, &texture_samplers, &ImageData::solid(Color::WHITE), COLOR_FORMAT, false);''','''        // (128, 128, 255) = +Z in tangent space; read back as data by `surface_normal`.
        let flat_normal = device
            .create_texture_with_data(
                &queue,
                &wgpu::TextureDescriptor {
                    label: Some("spark flat normal"),
                    size: extent((1, 1)),
                    mip_level_count: 1,
                    sample_count: 1,
                    dimension: wgpu::TextureDimension::D2,
                    format: COLOR_FORMAT,
                    usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
                    view_formats: &[],
                },
                wgpu::util::TextureDataOrder::LayerMajor,
                &[128, 128, 255, 255],
            )
            .create_view(&Default::default());
        let white = upload_texture(
            &device,
            &queue,
            &texture_layout,
            &texture_samplers,
            &flat_normal,
            &ImageData::solid(Color::WHITE),
            COLOR_FORMAT,
            false,
        );''')
    s=rep(s,'''            white,
''','''            white,
            flat_normal,
            normal_mapped_groups: HashMap::new(),
''')
    s=rep(s,'''            self.textures.clear();
            self.shaders.clear();''','''            self.textures.clear();
            self.normal_mapped_groups.clear();
            self.shaders.clear();''')
    s=s.replace('upload_texture(&self.device, &self.queue, &self.texture_layout, &self.texture_samplers, &magenta,','upload_texture(&self.device, &self.queue, &self.texture_layout, &self.texture_samplers, &self.flat_normal, &magenta,')
    s=s.replace('upload_texture(&self.device, &self.queue, &self.texture_layout, &self.texture_samplers, image,','upload_texture(&self.device, &self.queue, &self.texture_layout, &self.texture_samplers, &self.flat_normal, image,')
    s=s.replace('upload_texture(&self.device, &self.queue, &self.texture_layout, &self.texture_samplers, atlas,','upload_texture(&self.device, &self.queue, &self.texture_layout, &self.texture_samplers, &self.flat_normal, atlas,')
    s=rep(s,'''    samplers: &[wgpu::Sampler; 4],
    image: &ImageData,
    format: wgpu::TextureFormat,
    mipmaps: bool,
) -> GpuTexture {''','''    samplers: &[wgpu::Sampler; 4],
    normal: &wgpu::TextureView,
    image: &ImageData,
    format: wgpu::TextureFormat,
    mipmaps: bool,
) -> GpuTexture {''')
    s=rep(s,'''                wgpu::BindGroupEntry { binding: 0, resource: wgpu::BindingResource::TextureView(&view) },
                wgpu::BindGroupEntry { binding: 1, resource: wgpu::BindingResource::Sampler(sampler) },
            ],
        })
    };
    GpuTexture {''','''                wgpu::BindGroupEntry { binding: 0, resource: wgpu::BindingResource::TextureView(&view) },
                wgpu::BindGroupEntry { binding: 1, resource: wgpu::BindingResource::Sampler(sampler) },
                wgpu::BindGroupEntry { binding: 2, resource: wgpu::BindingResource::TextureView(normal) },
            ],
        })
    };
    GpuTexture {''')
    # candidates: LOD + new uniform fields
    s=rep(s,'''        for (id, obj) in scene.iter() {
            let Some(mesh) = obj.mesh else { continue };
            let mesh = mesh.0 as usize;
            let Some(Some(gpu_mesh)) = self.meshes.get(mesh) else { continue };
            let i = id.index() as usize;
            if !vis[i] {
                continue;
            }
            let model = mats[i];
            let m = &obj.material;
            let bounds = obj.local_bounds();''','''        for (id, obj) in scene.iter() {
            if obj.mesh.is_none() {
                continue;
            }
            let i = id.index() as usize;
            if !vis[i] {
                continue;
            }
            let model = mats[i];
            let m = &obj.material;
            let bounds = obj.local_bounds();
            let center = model.transform_point3(if bounds.is_empty() { Vec3::ZERO } else { (bounds.min + bounds.max) * 0.5 });
            // Level of detail by camera distance; a missing / empty LOD mesh falls back to the base mesh.
            let uploaded = |m: Option<spark_core::MeshId>| m.map(|m| m.0 as usize).filter(|&m| matches!(self.meshes.get(m), Some(Some(_))));
            let Some(mesh) = uploaded(obj.mesh_at(center.distance(cam.position))).or_else(|| uploaded(obj.mesh)) else { continue };
            let Some(Some(gpu_mesh)) = self.meshes.get(mesh) else { continue };''')
    s=rep(s,'''            } | if m.double_sided { VARIANT_DOUBLE_SIDED } else { 0 };
            let center = model.transform_point3(if bounds.is_empty() { Vec3::ZERO } else { (bounds.min + bounds.max) * 0.5 });
''','''            } | if m.double_sided { VARIANT_DOUBLE_SIDED } else { 0 };
            let normal_map = m.normal_map.map(|t| t.0 as usize).filter(|&t| t < self.textures.len());
            let emissive = m.emissive.to_linear();
''')
    s=rep(s,'''                    info: [m.tiling.x, m.tiling.y, flag(m.unlit), 0.0],
                },''','''                    info: [m.tiling.x, m.tiling.y, flag(m.unlit), flag(m.pbr)],
                    pbr: [m.metallic, m.roughness, flag(normal_map.is_some()), 0.0],
                    emissive: [emissive[0], emissive[1], emissive[2], 0.0],
                },''')
    s=rep(s,'''                texture: m.texture.map(|t| t.0 as usize).filter(|&t| t < self.textures.len()),
''','''                texture: m.texture.map(|t| t.0 as usize).filter(|&t| t < self.textures.len()),
                normal_map,
''')
    s=rep(s,'''(false, false) => (a.variant, a.shader, a.texture, a.mesh).cmp(&(b.variant, b.shader, b.texture, b.mesh)),''','''(false, false) => (a.variant, a.shader, a.texture, a.normal_map, a.mesh).cmp(&(b.variant, b.shader, b.texture, b.normal_map, b.mesh)),''')
    s=rep(s,'''&& (shadow_part || (b.shader == c.shader && b.variant == c.variant && b.texture == c.texture))''','''&& (shadow_part
                        || (b.shader == c.shader && b.variant == c.variant && b.texture == c.texture && b.normal_map == c.normal_map))''')
    s=rep(s,'''                    texture: c.texture,
                    offset: scratch.len() as u32,''','''                    texture: c.texture,
                    normal_map: c.normal_map,
                    offset: scratch.len() as u32,''')
    # bind groups for normal mapped batches, created before the pass borrows self
    s=rep(s,'''        let target = self.scene_target.as_ref().expect("scene target"); // ensure_scene_target() was called
        let bg = scene.background.to_linear();''','''        let nearest = rs.filter == TextureFilter::Nearest;
        for b in &batches {
            if let Some(normal) = b.normal_map {
                let key = (b.texture, normal, nearest);
                if !self.normal_mapped_groups.contains_key(&key) {
                    let base = b.texture.map_or(&self.white.view, |t| &self.textures[t].view);
                    let group = self.device.create_bind_group(&wgpu::BindGroupDescriptor {
                        label: Some("spark normal-mapped material"),
                        layout: &self.texture_layout,
                        entries: &[
                            wgpu::BindGroupEntry { binding: 0, resource: wgpu::BindingResource::TextureView(base) },
                            wgpu::BindGroupEntry {
                                binding: 1,
                                resource: wgpu::BindingResource::Sampler(&self.texture_samplers[if nearest { 0 } else { 1 }]),
                            },
                            wgpu::BindGroupEntry {
                                binding: 2,
                                resource: wgpu::BindingResource::TextureView(&self.textures[normal].view),
                            },
                        ],
                    });
                    self.normal_mapped_groups.insert(key, group);
                }
            }
        }

        let target = self.scene_target.as_ref().expect("scene target"); // ensure_scene_target() was called
        let bg = scene.background.to_linear();''')
    s=rep(s,'''            pass.set_bind_group(0, &self.frame_bind_group, &[]);
            let nearest = rs.filter == TextureFilter::Nearest;
            let (mut last_pipe, mut last_shader, mut last_mesh, mut last_texture) =
                (None, None, usize::MAX, None::<Option<usize>>);''','''            pass.set_bind_group(0, &self.frame_bind_group, &[]);
            let (mut last_pipe, mut last_shader, mut last_mesh, mut last_texture) =
                (None, None, usize::MAX, None::<(Option<usize>, Option<usize>)>);''')
    s=rep(s,'''                if last_texture != Some(b.texture) {
                    let tex = b.texture.map(|t| &self.textures[t]).unwrap_or(&self.white);
                    pass.set_bind_group(2, if nearest { &tex.nearest } else { &tex.linear }, &[]);
                    last_texture = Some(b.texture);
                }''','''                if last_texture != Some((b.texture, b.normal_map)) {
                    let group = match b.normal_map {
                        Some(normal) => &self.normal_mapped_groups[&(b.texture, normal, nearest)], // created above
                        None => {
                            let tex = b.texture.map(|t| &self.textures[t]).unwrap_or(&self.white);
                            if nearest { &tex.nearest } else { &tex.linear }
                        }
                    };
                    pass.set_bind_group(2, group, &[]);
                    last_texture = Some((b.texture, b.normal_map));
                }''')
    return s
edit('crates/spark-render/src/lib.rs', render)

# ---------------- Luau ----------------
def types(s):
    s=rep(s,'''    "name, position, rotation, scale, visible, parent, color, shader, data, body, light, blend, double_sided, cast_shadow";''','''    "name, position, rotation, scale, visible, parent, color, shader, data, body, light, blend, double_sided, cast_shadow, pbr, metallic, roughness, emissive, normal_map, lod";

/// `nil` / `false` -> none, else a Texture or an image path.
fn to_normal_map(w: &mut World, v: &Value, what: &str) -> LuaResult<Option<TextureId>> {
    match v {
        Value::Nil | Value::Boolean(false) => Ok(None),
        _ => crate::draw::texture_of(w, v, what).map(Some),
    }
}

/// `{ {distance, mesh}, ... }` -> LOD levels.
fn to_lod(v: &Value, what: &str) -> LuaResult<Vec<(f32, MeshId)>> {
    let bad = || rt(format!("{what}: expected a list of {{distance, Mesh}} pairs, e.g. {{ {{20, mid}}, {{60, low}} }}"));
    let t = match v {
        Value::Nil => return Ok(Vec::new()),
        Value::Table(t) => t,
        _ => return Err(bad()),
    };
    let mut out = Vec::new();
    for level in t.sequence_values::<Value>() {
        let Value::Table(pair) = level? else { return Err(bad()) };
        let d: Value = pair.get(1)?;
        let m: Value = pair.get(2)?;
        let d = to_num(&d, what)?;
        let Value::UserData(ud) = m else { return Err(bad()) };
        let mesh = ud.borrow::<LuaMesh>().map_err(|_| bad())?.0;
        if !(d >= 0.0) {
            return Err(rt(format!("{what}: distances must be 0 or more, got {d}")));
        }
        out.push((d, mesh));
    }
    Ok(out)
}

fn lod_table(lua: &Lua, lod: &[(f32, MeshId)]) -> LuaResult<Table> {
    let t = lua.create_table()?;
    for (d, m) in lod {
        let pair = lua.create_table()?;
        pair.push(*d)?;
        pair.push(LuaMesh(*m))?;
        t.push(pair)?;
    }
    Ok(t)
}''')
    s=rep(s,'''            "parent" => set_parent(w, id, to_parent(&v, &what)?)?,''','''            "parent" => set_parent(w, id, to_parent(&v, &what)?)?,
            // may load a texture: needs the whole world too
            "normal_map" => {
                let t = to_normal_map(w, &v, &what)?;
                w.scene.get_mut(id).ok_or_else(dead)?.material.normal_map = t;
            }''')
    s=rep(s,'''                    "cast_shadow" => o.material.cast_shadow = to_bool(&v, &what)?,
                    "body" =>''','''                    "cast_shadow" => o.material.cast_shadow = to_bool(&v, &what)?,
                    "pbr" => o.material.pbr = to_bool(&v, &what)?,
                    "metallic" => o.material = o.material.with_metallic(to_num(&v, &what)?),
                    "roughness" => o.material = o.material.with_roughness(to_num(&v, &what)?),
                    "emissive" => o.material.emissive = to_color(&v, &what)?,
                    "lod" => o.lod = to_lod(&v, &what)?,
                    "body" =>''')
    s=rep(s,'''        f.add_field_method_set("cast_shadow", |lua, this, v: bool| write(lua, this.0, |o| o.material.cast_shadow = v));
''','''        f.add_field_method_set("cast_shadow", |lua, this, v: bool| write(lua, this.0, |o| o.material.cast_shadow = v));
        f.add_field_method_get("pbr", |lua, this| read(lua, this.0, |_, o| o.material.pbr));
        f.add_field_method_set("pbr", |lua, this, v: bool| write(lua, this.0, |o| o.material.pbr = v));
        f.add_field_method_get("metallic", |lua, this| read(lua, this.0, |_, o| o.material.metallic));
        f.add_field_method_set("metallic", |lua, this, v: f32| write(lua, this.0, |o| o.material = o.material.with_metallic(v)));
        f.add_field_method_get("roughness", |lua, this| read(lua, this.0, |_, o| o.material.roughness));
        f.add_field_method_set("roughness", |lua, this, v: f32| write(lua, this.0, |o| o.material = o.material.with_roughness(v)));
        f.add_field_method_get("emissive", |lua, this| read(lua, this.0, |_, o| LuaColor(o.material.emissive)));
        f.add_field_method_set("emissive", |lua, this, v: Value| {
            let c = to_color(&v, "emissive")?;
            write(lua, this.0, |o| o.material.emissive = c)
        });
        f.add_field_method_get("normal_map", |lua, this| read(lua, this.0, |_, o| o.material.normal_map.map(LuaTexture)));
        f.add_field_method_set("normal_map", |lua, this, v: Value| {
            let id = this.0;
            with(lua, |w| {
                let t = to_normal_map(w, &v, "normal_map")?;
                w.scene.get_mut(id).ok_or_else(dead)?.material.normal_map = t;
                Ok(())
            })
        });
        f.add_field_method_get("lod", |lua, this| {
            let lod = read(lua, this.0, |_, o| o.lod.clone())?;
            lod_table(lua, &lod)
        });
        f.add_field_method_set("lod", |lua, this, v: Value| {
            let lod = to_lod(&v, "lod")?;
            write(lua, this.0, |o| o.lod = lod)
        });
''')
    s=rep(s,'''        f.add_field_method_get("cast_shadow", |_, this| Ok(this.0.cast_shadow));
    }''','''        f.add_field_method_get("cast_shadow", |_, this| Ok(this.0.cast_shadow));
        f.add_field_method_get("pbr", |_, this| Ok(this.0.pbr));
        f.add_field_method_get("metallic", |_, this| Ok(this.0.metallic));
        f.add_field_method_get("roughness", |_, this| Ok(this.0.roughness));
        f.add_field_method_get("emissive", |_, this| Ok(LuaColor(this.0.emissive)));
        f.add_field_method_get("normal_map", |_, this| Ok(this.0.normal_map.map(LuaTexture)));
    }''')
    s=rep(s,'''        m.add_method("with_unlit", |_, this, on: Option<bool>| Ok(LuaMaterial(this.0.with_unlit(on.unwrap_or(true)))));''','''        m.add_method("with_unlit", |_, this, on: Option<bool>| Ok(LuaMaterial(this.0.with_unlit(on.unwrap_or(true)))));
        m.add_method("with_metallic", |_, this, v: f32| Ok(LuaMaterial(this.0.with_metallic(v))));
        m.add_method("with_roughness", |_, this, v: f32| Ok(LuaMaterial(this.0.with_roughness(v))));
        m.add_method("with_emissive", |_, this, c: Value| Ok(LuaMaterial(this.0.with_emissive(to_color(&c, "with_emissive")?))));
        m.add_method("with_normal_map", |lua, this, v: Value| {
            let t = with(lua, |w| to_normal_map(w, &v, "with_normal_map"))?;
            Ok(LuaMaterial(this.0.with_normal_map(t)))
        });''')
    return s
edit('crates/spark-script/src/types.rs', types)
edit('crates/spark-script/src/api.rs', lambda s: rep(s,'''    material.set("unlit", lua.create_function(|_, c: Value| Ok(LuaMaterial(Material::unlit(to_color(&c, "Material.unlit")?))))?)?;''','''    material.set("unlit", lua.create_function(|_, c: Value| Ok(LuaMaterial(Material::unlit(to_color(&c, "Material.unlit")?))))?)?;
    material.set(
        "pbr",
        lua.create_function(|_, (c, metallic, roughness): (Value, Option<f32>, Option<f32>)| {
            let c = if c.is_nil() { Color::WHITE } else { to_color(&c, "Material.pbr")? };
            Ok(LuaMaterial(Material::pbr(c, metallic.unwrap_or(0.0), roughness.unwrap_or(0.5))))
        })?,
    )?;'''))

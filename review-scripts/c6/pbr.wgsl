
// ─── Normal maps ───────────────────────────────────────────────

// Shading normal: the geometric normal tilted by the material's tangent-space normal map
// (OpenGL convention, green = +V). Tangents come from screen-space derivatives (no tangent
// attribute needed); materials without a normal map sample a flat 1x1 map, so the result is the
// geometric normal. Call it in uniform control flow (it uses derivatives).
fn surface_normal(world_pos: vec3<f32>, normal: vec3<f32>, uv: vec2<f32>) -> vec3<f32> {
    let n = normalize(normal);
    // Normal maps hold data, not colors: undo the sRGB decode of the color texture format.
    let tn = linear_to_srgb(textureSample(normal_texture, base_sampler, uv).rgb) * 2.0 - 1.0;
    let dp1 = dpdx(world_pos);
    let dp2 = dpdy(world_pos);
    let duv1 = dpdx(uv);
    let duv2 = dpdy(uv);
    let dp2perp = cross(dp2, n);
    let dp1perp = cross(n, dp1);
    let t = dp2perp * duv1.x + dp1perp * duv2.x;
    let b = dp2perp * duv1.y + dp1perp * duv2.y;
    let scale = max(dot(t, t), dot(b, b));
    let inv = inverseSqrt(max(scale, 1e-30));
    let mapped = normalize(t * inv * tn.x + b * inv * tn.y + n * tn.z);
    // No normal map, or degenerate UVs (no tangent frame): keep the geometric normal.
    return select(mapped, n, object.pbr.z < 0.5 || scale < 1e-20);
}

// ─── PBR (metallic / roughness, Cook-Torrance GGX) ─────────────

const PI: f32 = 3.14159265359;

// Split-sum environment BRDF, analytic fit (Karis, "Physically Based Shading on Mobile").
fn env_brdf_approx(roughness: f32, n_dot_v: f32) -> vec2<f32> {
    let c0 = vec4<f32>(-1.0, -0.0275, -0.572, 0.022);
    let c1 = vec4<f32>(1.0, 0.0425, 1.04, -0.04);
    let r = roughness * c0 + c1;
    let a004 = min(r.x * r.x, exp2(-9.28 * n_dot_v)) * r.x + r.y;
    return vec2<f32>(-1.04, 1.04) * a004 + r.zw;
}

// Reflected light for one light direction `l` with irradiance `radiance` (light color * attenuation).
// Light colors use the same convention as the classic shader: a white light at normal incidence
// lights a white diffuse surface to its full color (the BRDF is scaled by PI).
fn pbr_direct(n: vec3<f32>, v: vec3<f32>, l: vec3<f32>, radiance: vec3<f32>, base: vec3<f32>, metallic: f32, roughness: f32) -> vec3<f32> {
    let n_dot_l = max(dot(n, l), 0.0);
    if (n_dot_l <= 0.0) {
        return vec3<f32>(0.0);
    }
    let n_dot_v = max(dot(n, v), 1e-4);
    let h = normalize(v + l);
    let n_dot_h = max(dot(n, h), 0.0);
    let alpha = roughness * roughness;
    let a2 = alpha * alpha;
    let d_denom = n_dot_h * n_dot_h * (a2 - 1.0) + 1.0;
    let d = a2 / (PI * d_denom * d_denom);
    let k = (roughness + 1.0) * (roughness + 1.0) / 8.0;
    let g = (n_dot_v / (n_dot_v * (1.0 - k) + k)) * (n_dot_l / (n_dot_l * (1.0 - k) + k));
    let f0 = mix(vec3<f32>(0.04), base, metallic);
    let f = f0 + (1.0 - f0) * pow(1.0 - max(dot(h, v), 0.0), 5.0);
    let specular = d * g * f / (4.0 * n_dot_v * n_dot_l);
    let diffuse = (1.0 - f) * (1.0 - metallic) * base;
    return (diffuse + specular * PI) * radiance * n_dot_l;
}

// Ambient light on a PBR surface: diffuse plus a rough environment reflection of the ambient color
// (so metals are not black without lights).
fn pbr_ambient(n: vec3<f32>, v: vec3<f32>, base: vec3<f32>, metallic: f32, roughness: f32) -> vec3<f32> {
    let n_dot_v = max(dot(n, v), 1e-4);
    let f0 = mix(vec3<f32>(0.04), base, metallic);
    let env = env_brdf_approx(roughness, n_dot_v);
    let specular = f0 * env.x + env.y;
    return frame.ambient.rgb * ((1.0 - specular) * (1.0 - metallic) * base + specular);
}

// Full PBR lighting of a surface point: ambient + sun (with shadows) + point / spot lights.
fn pbr_lighting(world_pos: vec3<f32>, normal: vec3<f32>, base: vec3<f32>, metallic: f32, roughness: f32) -> vec3<f32> {
    let n = normalize(normal);
    let v = normalize(frame.camera_pos.xyz - world_pos);
    let r = clamp(roughness, 0.045, 1.0); // a perfect mirror has no highlight for point lights
    let m = clamp(metallic, 0.0, 1.0);
    var rgb = pbr_ambient(n, v, base, m, r);
    let sun_l = normalize(-frame.sun_dir.xyz);
    if (dot(n, sun_l) > 0.0) {
        rgb = rgb + pbr_direct(n, v, sun_l, frame.sun_color.rgb * sun_shadow(world_pos, n), base, m, r);
    }
    for (var i = 0u; i < frame.light_count.x; i = i + 1u) {
        let li = frame.lights[i];
        let to_light = li.position.xyz - world_pos;
        let dist = length(to_light);
        let range = li.position.w;
        if (dist >= range) {
            continue;
        }
        let ldir = to_light / max(dist, 0.0001);
        let x = dist / range;
        let window = clamp(1.0 - x * x, 0.0, 1.0);
        var att = window * window / (1.0 + 4.0 * x * x);
        if (li.color.w > 0.5) {
            att = att * smoothstep(li.direction.w, li.params.x, dot(-ldir, li.direction.xyz));
        }
        rgb = rgb + pbr_direct(n, v, ldir, li.color.rgb * att, base, m, r);
    }
    return rgb;
}

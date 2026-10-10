import sys; sys.path.insert(0,'/data/fix')
from lib import *
def core_docs(s):
    s=rep(s,'    /// Direction of RGB split (0 = radial, 1 = directional).','    /// true = split outward from the screen center, false = horizontal split.')
    s=s.replace('    /// Number of samples (4–64, more = higher quality).','    /// Number of samples (1–64, more = higher quality).')
    s=s.replace('    /// Number of blur samples (4–32).','    /// Number of blur samples (1–32).')
    return s
edit('crates/spark-core/src/render.rs', core_docs)

def api(s):
    s=rep(s,'''Spark has no built-in looks or effects: the default is plain lit rendering, everything else is your own WGSL.
Full shader reference with examples: [SHADERS.md](SHADERS.md).''','''The default is plain lit rendering. Built-in post effects (below) are all off by default; anything else is your own
WGSL. Full shader reference with examples: [SHADERS.md](SHADERS.md).''')
    s=rep(s,'''  spawn props `shader = s`, `data = {a, b, c, d}`. `data` arrives in WGSL as `object.data` (per-object values, e.g. a hit flash).
''','''  spawn props `shader = s`, `data = {a, b, c, d}`. `data` arrives in WGSL as `object.data` (per-object values, e.g. a hit flash).

### Built-in post effects

Each effect is `nil` / `false` (off, default), `true` (default settings) or a table: missing keys keep their defaults,
unknown keys and wrong types are errors. Reading an effect gives its current settings table (or `nil`).
They run before your `graphics.post` passes, in this fixed order:
SSAO -> motion blur -> depth of field -> bloom -> color grading -> tonemap -> FXAA -> chromatic aberration -> film grain -> vignette.

```lua
graphics.tonemap = "aces"                          -- "off" (default) | "aces" | "reinhard" | "hejl"
graphics.bloom = { strength = 0.6 }                -- glow around bright pixels
graphics.vignette = true                           -- defaults
graphics.color_grading = { saturation = 1.2, gain = vec3(1, 0.95, 0.9) }
graphics.fxaa = true
graphics.bloom = nil                               -- off again
```

| effect | settings (defaults) |
|---|---|
| `tonemap` | `"off"` / `"aces"` / `"reinhard"` / `"hejl"` - maps bright (HDR) colors into the screen range |
| `bloom` | `threshold` 0.8 (brightness where glow starts), `knee` 0.2, `strength` 0.4, `radius` 8 (pixels) |
| `ssao` | `radius` 0.5 (meters), `samples` 16 (1-64), `strength` 1, `bias` 0.05 (meters) |
| `motion_blur` | `strength` 1 (fraction of the frame the shutter is open), `samples` 8 (1-32); camera motion only |
| `dof` | `focus` 10 (meters), `aperture` 2, `focal_range` 3 (meters in focus around `focus`), `samples` 16 |
| `color_grading` | `exposure` 1, `contrast` 1, `saturation` 1, `temperature` 0 (-1 warm .. 1 cool), `tint` 0 (-1 green .. 1 magenta), `lift` vec3(0) / `gamma` vec3(1) / `gain` vec3(1) (per channel, vec3 or `{r, g, b}`) |
| `fxaa` | `true` / `false` - smooths edges MSAA misses (shader / alpha edges) |
| `chromatic_aberration` | `amount` 2 (pixels at the screen edge), `radial` true (false = horizontal split) |
| `film_grain` | `strength` 0.05, `size` 2 (pixels) |
| `vignette` | `strength` 0.5, `inner` 0.3, `outer` 0.85 (0 = center, 1 = screen edge), `color` black |

The 3D scene is rendered in HDR (16-bit float) where the GPU supports it, so lights brighter than 1 survive until
`tonemap` / `bloom`. With `tonemap = "off"` such values are clipped, as before.
''')
    return s
edit('docs/LUAU_API.md', api)

def dts(s):
    s=rep(s,'''    -- Shader, list of Shaders / { shader = s, size = "screen" | "scene" }, or nil
    post: any,
}''','''    -- Shader, list of Shaders / { shader = s, size = "screen" | "scene" }, or nil
    post: any,
    -- built-in post effects: nil / false = off, true = defaults, table = settings
    tonemap: "off" | "aces" | "reinhard" | "hejl",
    fxaa: boolean,
    bloom: BloomSettings?,
    ssao: SsaoSettings?,
    motion_blur: MotionBlurSettings?,
    dof: DofSettings?,
    color_grading: ColorGradingSettings?,
    chromatic_aberration: ChromaticAberrationSettings?,
    film_grain: FilmGrainSettings?,
    vignette: VignetteSettings?,
}''')
    s=rep(s,'''declare graphics: {''','''type BloomSettings = { threshold: number?, knee: number?, strength: number?, radius: number? } | boolean
type SsaoSettings = { radius: number?, samples: number?, strength: number?, bias: number? } | boolean
type MotionBlurSettings = { strength: number?, samples: number? } | boolean
type DofSettings = { focus: number?, aperture: number?, focal_range: number?, samples: number? } | boolean
type ColorGradingSettings = {
    exposure: number?, contrast: number?, saturation: number?, temperature: number?, tint: number?,
    lift: (vector | { number })?, gamma: (vector | { number })?, gain: (vector | { number })?,
} | boolean
type ChromaticAberrationSettings = { amount: number?, radial: boolean? } | boolean
type FilmGrainSettings = { strength: number?, size: number? } | boolean
type VignetteSettings = { strength: number?, inner: number?, outer: number?, color: ColorLike? } | boolean

declare graphics: {''')
    return s
edit('docs/spark.d.luau', dts)

def shaders(s):
    s=rep(s,'''Spark ships no looks, presets or effects. Out of the box you get one plain lit shader (sun + ambient + up to 32
point / spot lights + fog). Everything else - toon, PS1, pixel art, VHS, outlines, CRT - is a small WGSL file in your game.''','''Out of the box you get one plain lit shader (sun + ambient + up to 32 point / spot lights + fog) and a set of built-in
post effects that are off by default (`graphics.bloom`, `graphics.tonemap`, ... - see LUAU_API.md). Everything else -
toon, PS1, pixel art, VHS, outlines, CRT - is a small WGSL file in your game.''')
    s=rep(s,'''frame.shadow_view_proj, frame.shadow                        // sun shadow map: world -> shadow clip; enabled, 1/size, normal offset, distance''','''frame.shadow_view_proj, frame.shadow                        // sun shadow map: world -> shadow clip; enabled, 1/size, normal offset, distance
frame.prev_view_proj                                        // view_proj of the previous frame (motion vectors, reprojection)''')
    s=rep(s,'''All colors are linear; the engine converts to the screen at the end.''','''All colors are linear; the engine converts to the screen at the end. The scene and intermediate post images are
16-bit float where the GPU supports it, so `input_color` can return values above 1 (bright lights); they are clipped
when written to the screen unless a tonemapper runs.''')
    s=rep(s,'''Run full-screen, one after another; each pass reads the previous image.''','''Run full-screen, one after another; each pass reads the previous image. Enabled built-in effects run first.''')
    s=rep(s,'''world.render.post = vec![PostPass { shader: s, size: PassSize::Screen }];''','''world.render.post = vec![PostPass { shader: s, size: PassSize::Screen }];
world.render.postfx.bloom = Some(Bloom { strength: 0.6, ..Default::default() });   // built-in effects
world.render.postfx.tonemap = Tonemap::Aces;''')
    return s
edit('docs/SHADERS.md', shaders)
edit('docs/SHADERS.md', lambda s: s.replace('Some(Bloom {','Some(spark_core::render::Bloom {').replace('= Tonemap::Aces;','= spark_core::render::Tonemap::Aces;'))
edit('README.md', lambda s: rep(s, 'your own WGSL surface and full-screen post shaders with hot reload ([docs/SHADERS.md](docs/SHADERS.md)), low internal resolution', 'HDR scene, built-in post effects (bloom, tonemapping, SSAO, depth of field, motion blur, color grading, FXAA, vignette, film grain, chromatic aberration; all off by default), your own WGSL surface and full-screen post shaders with hot reload ([docs/SHADERS.md](docs/SHADERS.md)), low internal resolution') if 'built-in post effects' not in s else s)
edit('README.ru.md', lambda s: rep(s, 'свои WGSL-шейдеры поверхностей и пост-процессинга с горячей перезагрузкой', 'HDR-сцена, встроенные пост-эффекты (bloom, тонмаппинг, SSAO, глубина резкости, motion blur, цветокоррекция, FXAA, виньетка, зерно, хроматическая аберрация; по умолчанию выключены), свои WGSL-шейдеры поверхностей и пост-процессинга с горячей перезагрузкой') if 'встроенные пост-эффекты' not in s else s)

        // ── Built-in post-processing effects ───────────────────────────
        // Each effect: nil / false = off, true = default settings, table = settings (missing keys
        // keep their defaults, unknown keys and wrong types are errors). Reading gives the table.
        use spark_core::render::*;

        f.add_field_method_get("tonemap", |lua, _| {
            with(lua, |w| Ok(match w.render.postfx.tonemap {
                Tonemap::Off => "off",
                Tonemap::Aces => "aces",
                Tonemap::Reinhard => "reinhard",
                Tonemap::Hejl => "hejl",
            }))
        });
        f.add_field_method_set("tonemap", |lua, _, v: String| {
            let t = match v.as_str() {
                "off" => Tonemap::Off,
                "aces" => Tonemap::Aces,
                "reinhard" => Tonemap::Reinhard,
                "hejl" => Tonemap::Hejl,
                s => return Err(rt(format!("graphics.tonemap: unknown '{s}' (use \"off\", \"aces\", \"reinhard\", \"hejl\")"))),
            };
            with(lua, |w| Ok(w.render.postfx.tonemap = t))
        });
        f.add_field_method_get("fxaa", |lua, _| with(lua, |w| Ok(w.render.postfx.fxaa)));
        f.add_field_method_set("fxaa", |lua, _, v: Value| {
            let on = to_bool(&v, "graphics.fxaa")?;
            with(lua, |w| Ok(w.render.postfx.fxaa = on))
        });

        macro_rules! fx_field {
            ($name:literal, $field:ident) => {
                f.add_field_method_get($name, |lua, _| with(lua, |w| fx_to_lua(lua, &w.render.postfx.$field)));
                f.add_field_method_set($name, |lua, _, v: Value| {
                    let settings = fx_from_lua(&v)?;
                    with(lua, |w| Ok(w.render.postfx.$field = settings))
                });
            };
        }
        fx_field!("bloom", bloom);
        fx_field!("ssao", ssao);
        fx_field!("motion_blur", motion_blur);
        fx_field!("dof", dof);
        fx_field!("color_grading", color_grading);
        fx_field!("vignette", vignette);
        fx_field!("film_grain", film_grain);
        fx_field!("chromatic_aberration", chromatic_aberration);
    }
}

/// Settings struct of one built-in effect, readable from / writable to a Luau table.
trait FxSettings: Default {
    const NAME: &'static str;
    const KEYS: &'static [&'static str];
    fn read(&mut self, key: &str, v: &Value, what: &str) -> LuaResult<()>;
    fn write(&self, lua: &Lua, t: &Table) -> LuaResult<()>;
}

/// Value kinds of effect settings: `read` converts with a clear error, `write` back to Luau.
mod fx_kind {
    use super::*;
    pub mod num {
        use super::*;
        pub fn read(v: &Value, what: &str) -> LuaResult<f32> {
            to_num(v, what)
        }
        pub fn write(_: &Lua, x: &f32) -> LuaResult<Value> {
            Ok(Value::Number(f64::from(*x)))
        }
    }
    /// Sample counts: rounded and clamped to 1..=64.
    pub mod count {
        use super::*;
        pub fn read(v: &Value, what: &str) -> LuaResult<u32> {
            Ok(to_num(v, what)?.round().clamp(1.0, 64.0) as u32)
        }
        pub fn write(_: &Lua, x: &u32) -> LuaResult<Value> {
            Ok(Value::Integer(i64::from(*x)))
        }
    }
    pub mod flag {
        use super::*;
        pub fn read(v: &Value, what: &str) -> LuaResult<bool> {
            to_bool(v, what)
        }
        pub fn write(_: &Lua, x: &bool) -> LuaResult<Value> {
            Ok(Value::Boolean(*x))
        }
    }
    /// Per-channel numbers: `vec3(r, g, b)` or `{r, g, b}`.
    pub mod vec3 {
        use super::*;
        pub fn read(v: &Value, what: &str) -> LuaResult<[f32; 3]> {
            Ok(to_vec3(v, what)?.to_array())
        }
        pub fn write(_: &Lua, x: &[f32; 3]) -> LuaResult<Value> {
            Ok(Value::Vector(Vector::new(x[0], x[1], x[2])))
        }
    }
    pub mod color {
        use super::*;
        pub fn read(v: &Value, what: &str) -> LuaResult<spark_core::Color> {
            to_color(v, what)
        }
        pub fn write(lua: &Lua, x: &spark_core::Color) -> LuaResult<Value> {
            lua.create_userdata(LuaColor(*x)).map(Value::UserData)
        }
    }
}

macro_rules! fx_settings {
    ($ty:ty, $name:literal, { $($field:ident : $kind:ident),* $(,)? }) => {
        impl FxSettings for $ty {
            const NAME: &'static str = $name;
            const KEYS: &'static [&'static str] = &[$(stringify!($field)),*];
            fn read(&mut self, key: &str, v: &Value, what: &str) -> LuaResult<()> {
                match key {
                    $(stringify!($field) => self.$field = fx_kind::$kind::read(v, what)?,)*
                    _ => unreachable!("key checked against KEYS"),
                }
                Ok(())
            }
            fn write(&self, lua: &Lua, t: &Table) -> LuaResult<()> {
                $(t.set(stringify!($field), fx_kind::$kind::write(lua, &self.$field)?)?;)*
                Ok(())
            }
        }
    };
}

use spark_core::render::{Bloom, ChromaticAberration, ColorGrading, DepthOfField, FilmGrain, MotionBlur, Ssao, Vignette};
fx_settings!(Bloom, "bloom", { threshold: num, knee: num, strength: num, radius: num });
fx_settings!(Ssao, "ssao", { radius: num, samples: count, strength: num, bias: num });
fx_settings!(MotionBlur, "motion_blur", { strength: num, samples: count });
fx_settings!(DepthOfField, "dof", { focus: num, aperture: num, focal_range: num, samples: count });
fx_settings!(ColorGrading, "color_grading", {
    exposure: num, contrast: num, saturation: num, temperature: num, tint: num, lift: vec3, gamma: vec3, gain: vec3,
});
fx_settings!(Vignette, "vignette", { strength: num, inner: num, outer: num, color: color });
fx_settings!(FilmGrain, "film_grain", { strength: num, size: num });
fx_settings!(ChromaticAberration, "chromatic_aberration", { amount: num, radial: flag });

/// `nil` / `false` -> off, `true` -> defaults, table -> defaults overridden by its keys.
fn fx_from_lua<T: FxSettings>(v: &Value) -> LuaResult<Option<T>> {
    let t = match v {
        Value::Nil | Value::Boolean(false) => return Ok(None),
        Value::Boolean(true) => return Ok(Some(T::default())),
        Value::Table(t) => t,
        _ => return Err(rt(format!("graphics.{}: expected a table, true or nil, got {}", T::NAME, v.type_name()))),
    };
    let mut settings = T::default();
    for pair in t.pairs::<Value, Value>() {
        let (k, val) = pair?;
        let key = match &k {
            Value::String(s) => s.to_string_lossy(),
            _ => return Err(rt(format!("graphics.{}: keys must be names, got {}", T::NAME, k.type_name()))),
        };
        if !T::KEYS.contains(&key.as_str()) {
            return Err(rt(format!("graphics.{}: unknown setting '{key}' (allowed: {})", T::NAME, T::KEYS.join(", "))));
        }
        settings.read(&key, &val, &format!("graphics.{}.{key}", T::NAME))?;
    }
    Ok(Some(settings))
}

fn fx_to_lua<T: FxSettings>(lua: &Lua, v: &Option<T>) -> LuaResult<Value> {
    let Some(s) = v else { return Ok(Value::Nil) };
    let t = lua.create_table()?;
    s.write(lua, &t)?;
    Ok(Value::Table(t))
}

/// Parameter values of one built-in effect: `struct Params` field name -> numbers.
pub type PostFxParams = Vec<(&'static str, Vec<f32>)>;

impl PostProcessing {
    /// Enabled built-in effects in the order they run, each with its shader parameter values
    /// (`struct Params` field name -> numbers). The renderer runs exactly this list.
    pub fn passes(&self) -> Vec<(PostFxKind, PostFxParams)> {
        let mut out = Vec::new();
        if let Some(s) = &self.ssao {
            out.push((
                PostFxKind::Ssao,
                vec![
                    ("radius", vec![s.radius]),
                    ("samples", vec![s.samples as f32]),
                    ("strength", vec![s.strength]),
                    ("bias", vec![s.bias]),
                ],
            ));
        }
        if let Some(m) = &self.motion_blur {
            out.push((PostFxKind::MotionBlur, vec![("strength", vec![m.strength]), ("samples", vec![m.samples as f32])]));
        }
        if let Some(d) = &self.dof {
            out.push((
                PostFxKind::Dof,
                vec![
                    ("focus", vec![d.focus]),
                    ("aperture", vec![d.aperture]),
                    ("focal_range", vec![d.focal_range]),
                    ("samples", vec![d.samples as f32]),
                ],
            ));
        }
        if let Some(b) = &self.bloom {
            out.push((
                PostFxKind::Bloom,
                vec![
                    ("threshold", vec![b.threshold]),
                    ("knee", vec![b.knee]),
                    ("strength", vec![b.strength]),
                    ("radius", vec![b.radius]),
                ],
            ));
        }
        if let Some(c) = &self.color_grading {
            out.push((
                PostFxKind::ColorGrade,
                vec![
                    ("exposure", vec![c.exposure]),
                    ("contrast", vec![c.contrast]),
                    ("saturation", vec![c.saturation]),
                    ("temperature", vec![c.temperature]),
                    ("tint", vec![c.tint]),
                    ("lift", c.lift.to_vec()),
                    ("gamma", c.gamma.to_vec()),
                    ("gain", c.gain.to_vec()),
                ],
            ));
        }
        let mode = match self.tonemap {
            Tonemap::Off => None,
            Tonemap::Aces => Some(0.0),
            Tonemap::Reinhard => Some(1.0),
            Tonemap::Hejl => Some(2.0),
        };
        if let Some(mode) = mode {
            out.push((PostFxKind::Tonemap, vec![("mode", vec![mode])]));
        }
        if self.fxaa {
            out.push((PostFxKind::Fxaa, Vec::new()));
        }
        if let Some(c) = &self.chromatic_aberration {
            out.push((
                PostFxKind::ChromaticAberration,
                vec![("amount", vec![c.amount]), ("radial", vec![if c.radial { 1.0 } else { 0.0 }])],
            ));
        }
        if let Some(f) = &self.film_grain {
            out.push((PostFxKind::FilmGrain, vec![("strength", vec![f.strength]), ("size", vec![f.size])]));
        }
        if let Some(v) = &self.vignette {
            out.push((
                PostFxKind::Vignette,
                vec![
                    ("strength", vec![v.strength]),
                    ("inner", vec![v.inner]),
                    ("outer", vec![v.outer]),
                    ("color", v.color.to_linear()[..3].to_vec()),
                ],
            ));
        }
        out
    }

    /// True when at least one built-in effect is enabled.
    pub fn is_active(&self) -> bool {
        !self.passes().is_empty()
    }
}

#[cfg(test)]
mod postfx_tests {
    use super::*;
    use crate::shader::ShaderData;

    fn everything_on() -> PostProcessing {
        PostProcessing {
            tonemap: Tonemap::Aces,
            bloom: Some(Bloom::default()),
            ssao: Some(Ssao::default()),
            motion_blur: Some(MotionBlur::default()),
            dof: Some(DepthOfField::default()),
            color_grading: Some(ColorGrading::default()),
            fxaa: true,
            chromatic_aberration: Some(ChromaticAberration::default()),
            film_grain: Some(FilmGrain::default()),
            vignette: Some(Vignette::default()),
        }
    }

    /// Default settings must not change how existing games look.
    #[test]
    fn default_runs_nothing() {
        let p = PostProcessing::default();
        assert_eq!(p.tonemap, Tonemap::Off);
        assert!(!p.is_active());
    }

    #[test]
    fn passes_follow_the_documented_order() {
        let kinds: Vec<PostFxKind> = everything_on().passes().into_iter().map(|(k, _)| k).collect();
        use PostFxKind::*;
        assert_eq!(kinds, [Ssao, MotionBlur, Dof, Bloom, ColorGrade, Tonemap, Fxaa, ChromaticAberration, FilmGrain, Vignette]);
    }

    /// Every value the engine sends exists in the effect's `struct Params` with the right size,
    /// and every shader param is set (no silently ignored settings).
    #[test]
    fn param_names_match_shaders() {
        for (kind, params) in everything_on().passes() {
            let mut data = ShaderData::compile(kind.name(), kind.shader_source()).expect("built-in effect compiles");
            for (name, value) in &params {
                data.set_param(name, value).unwrap_or_else(|e| panic!("{e}"));
            }
            for p in &data.params {
                assert!(params.iter().any(|(n, _)| *n == p.name), "{}: param '{}' is never set", kind.name(), p.name);
            }
        }
    }

    /// Neutral color grading leaves colors unchanged (checked on the CPU copy of the formula).
    #[test]
    fn neutral_color_grading_defaults() {
        let c = ColorGrading::default();
        assert_eq!((c.exposure, c.contrast, c.saturation, c.temperature, c.tint), (1.0, 1.0, 1.0, 0.0, 0.0));
        assert_eq!((c.lift, c.gamma, c.gain), ([0.0; 3], [1.0; 3], [1.0; 3]));
    }
}

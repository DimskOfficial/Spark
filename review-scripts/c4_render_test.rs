
    fn test_world() -> World {
        let mut world = World::default();
        world.scene.background = Color::BLACK;
        let cube = world.add_mesh(MeshData::cube(2.0));
        // 4x brighter than white: only an HDR scene keeps that until tonemapping.
        world.spawn(cube, Material::unlit(Color::rgb(4.0, 4.0, 4.0)));
        world.scene.camera.position = Vec3::new(0.0, 0.0, 4.0);
        world.scene.camera.look_at(Vec3::ZERO);
        world
    }

    /// All ten built-in effects together render without GPU validation errors.
    #[test]
    fn builtin_effects_render() {
        use spark_core::render::*;
        let Ok(mut r) = Renderer::new_headless(96, 64) else { return eprintln!("skipping GPU test: no adapter") };
        let mut world = test_world();
        world.render.postfx = PostProcessing {
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
        };
        let scope = r.device.push_error_scope(wgpu::ErrorFilter::Validation);
        for frame in 1..=3 {
            world.time.frame = frame;
            world.scene.camera.position.x = frame as f32 * 0.1; // moving camera: motion blur path
            r.screenshot(&world).expect("screenshot");
        }
        let error = pollster::block_on(scope.pop());
        assert!(error.is_none(), "GPU validation error: {error:?}");
        assert_eq!(r.last_stats().post_passes, 10);
    }

    /// Values above 1 reach the tonemapper: Reinhard x / (1 + x) stays above 0.5 (sRGB 188) only
    /// if the scene kept x > 1; an 8-bit scene clips to 1.0 first and gives exactly ~188.
    #[test]
    fn hdr_scene_reaches_tonemapper() {
        use spark_core::render::Tonemap;
        let Ok(mut r) = Renderer::new_headless(64, 64) else { return eprintln!("skipping GPU test: no adapter") };
        if r.scene_format != HDR_FORMAT {
            return eprintln!("skipping: adapter has no HDR render target");
        }
        let mut world = test_world();
        world.render.postfx.tonemap = Tonemap::Reinhard;
        let center = r.screenshot(&world).expect("screenshot").pixel(32, 32);
        assert!((200..=252).contains(&center[0]), "center = {center:?}");
    }

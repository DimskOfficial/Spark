#[cfg(test)]
mod tests {
    use super::*;
    use spark_core::glam::Quat;
    use spark_core::{Material, MeshData};

    #[test]
    fn uniforms_are_16_byte_aligned() {
        assert_eq!(size_of::<FrameUniform>() % 16, 0);
        assert_eq!(size_of::<ObjectUniform>() % 16, 0);
        // 64 objects per draw must fit the 16 KB uniform binding every backend (incl. GL) offers.
        assert!(size_of::<ObjectUniform>() * MAX_INSTANCES <= 16 * 1024);
    }

    #[test]
    fn normal_matrix_keeps_normals_perpendicular_under_shear() {
        // Child rotated 45° under a parent scaled (3, 1, 1): the world matrix has shear.
        let parent = Mat4::from_scale(Vec3::new(3.0, 1.0, 1.0));
        let child = Mat4::from_quat(Quat::from_rotation_z(std::f32::consts::FRAC_PI_4));
        let model = parent * child;
        let nm = normal_matrix(&model);
        // A surface with local normal +Y contains the local +X direction.
        let tangent = model.transform_vector3(Vec3::X);
        let normal = nm.transform_vector3(Vec3::Y).normalize();
        assert!(tangent.dot(normal).abs() < 1e-5, "normal not perpendicular: {}", tangent.dot(normal));
    }

    #[test]
    fn normal_matrix_degenerate_is_identity() {
        assert_eq!(normal_matrix(&Mat4::from_scale(Vec3::ZERO)), Mat4::IDENTITY);
    }

    /// Real GPU round trip: a white unlit cube in front of the camera ends up in the image.
    /// Skipped when the machine has no GPU / software Vulkan (CI installs lavapipe).
    #[test]
    fn headless_render_draws_scene() {
        let mut r = match Renderer::new_headless(64, 64) {
            Ok(r) => r,
            Err(e) => {
                eprintln!("skipping GPU test: {e}");
                return;
            }
        };
        let mut world = World::default();
        world.scene.background = Color::BLACK;
        let cube = world.add_mesh(MeshData::cube(2.0));
        world.spawn(cube, Material::unlit(Color::WHITE));
        world.scene.camera.position = Vec3::new(0.0, 0.0, 4.0);
        world.scene.camera.look_at(Vec3::ZERO);
        let image = r.screenshot(&world).expect("screenshot");
        assert_eq!((image.width, image.height), (64, 64));
        let center = image.pixel(32, 32);
        let corner = image.pixel(0, 0);
        assert!(center[0] > 200, "cube not drawn: center = {center:?}");
        assert!(corner[0] < 30, "background not cleared: corner = {corner:?}");
        assert!(r.last_stats().draw_calls >= 1);
        assert!(!r.is_device_lost());
    }
}

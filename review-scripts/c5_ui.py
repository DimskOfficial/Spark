import sys, shutil; sys.path.insert(0,'/data/fix')
from lib import *
shutil.copy('/data/fix/c5/ui.rs', R+'crates/spark-core/src/ui.rs')
shutil.copy('/data/fix/c5/ui_api.rs', R+'crates/spark-script/src/ui_api.rs')
edit('crates/spark-script/src/draw.rs', lambda s: rep(s,'\nfn texture_of(w: &mut World','\npub(crate) fn texture_of(w: &mut World'))
edit('crates/spark-core/src/canvas.rs', lambda s: rep(s,'''    pub fn push(&mut self) {''','''    /// Replaces the current transform (the push / pop stack is unchanged).
    pub fn set_transform(&mut self, t: Affine2) {
        self.transform = t;
    }

    pub fn push(&mut self) {'''))
def game(s):
    s=rep(s,'''    world.ui.begin(&world.canvas, &world.input);
    game.draw(world);''','''    game.draw(world);''')
    s=rep(s,'''    let dt = world.time.dt;
    game.update(world, dt);''','''    let dt = world.time.dt;
    world.ui.begin(&world.canvas, &world.input);
    game.update(world, dt);''')
    return s
edit('crates/spark-core/src/game.rs', game)
edit('crates/spark-core/src/lib.rs', lambda s: rep(s,'pub use ui::{Rect, Ui};','pub use ui::{Rect, Ui, UiStyle};'))
shutil.copy('/data/fix/c5/ui.luau', R+'crates/spark-script/tests/scripts/ui.luau')
edit('crates/spark-script/tests/flow.rs', lambda s: s if 'ui_contract' in s else s.rstrip()+'''

#[test]
fn ui_contract() {
    run_script("ui.luau", 10);
}
''')

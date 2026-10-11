import sys; sys.path.insert(0,'/data/fix')
from lib import *
def api(s):
    if '## UI widgets' in s: return s
    return rep(s,'''Full 2D game: `examples/starfall/main.luau`.

## Input and time''','''Full 2D game: `examples/starfall/main.luau`.

## UI widgets (ui)

Immediate-mode widgets on the UI layer, in the same virtual pixels as `draw` (top-left origin). Call them every
frame from `draw()` (or `update()`); they draw themselves and return the result right away. Interactive widgets take
an **id** first: any string or integer that stays the same every frame (a click is a press and a release in
different frames).

```lua
local volume, music = 0.5, true
function draw()
    ui.panel(10, 10, 240, 150)
    if ui.button("play", 20, 20, 220, 36, "Play") then start_game() end
    volume = ui.slider("volume", 20, 70, 220, 16, volume, 0, 1)
    music = ui.checkbox("music", 20, 100, 20, music)
    ui.label(50, 102, "Music")
    ui.progress(20, 135, 220, 10, hp / max_hp, "#e04040")
end
function update(dt)
    if input.mouse_pressed("left") and not ui.hovered() then shoot() end   -- clicks on the UI don't shoot
end
```

- `ui.button(id, x, y, w, h, text)` -> true on the frame it is clicked (pressed and released over it)
- `ui.slider(id, x, y, w, h, value, min = 0, max = 1)` -> the value (changed while dragged)
- `ui.checkbox(id, x, y, size, checked)` -> the state (flipped when clicked)
- `ui.panel(x, y, w, h, color?, border_color?)` -> true when the mouse is over it
- `ui.label(x, y, text, size = 16, color = white)` - text, top-left at x, y
- `ui.image(x, y, w, h, texture)` - Texture or image path, stretched over the rect
- `ui.progress(x, y, w, h, t, color?)` - bar filled to t (0..1)
- `ui.hovered()` -> true when the mouse is over UI drawn this or the previous frame
- Widgets never change `draw.layer` or the draw transform. Only the left mouse button interacts.

## Input and time''')
edit('docs/LUAU_API.md', api)
def dts(s):
    if 'declare ui:' in s: return s
    return rep(s,'''declare screen: {''','''type WidgetId = string | number

declare ui: {
    button: (id: WidgetId, x: number, y: number, w: number, h: number, text: string) -> boolean,
    slider: (id: WidgetId, x: number, y: number, w: number, h: number, value: number, min: number?, max: number?) -> number,
    checkbox: (id: WidgetId, x: number, y: number, size: number, checked: boolean) -> boolean,
    panel: (x: number, y: number, w: number, h: number, color: ColorLike?, border: ColorLike?) -> boolean,
    label: (x: number, y: number, text: string, size: number?, color: ColorLike?) -> (),
    image: (x: number, y: number, w: number, h: number, texture: Texture | string) -> (),
    progress: (x: number, y: number, w: number, h: number, t: number, color: ColorLike?) -> (),
    hovered: () -> boolean,
}

declare screen: {''')
edit('docs/spark.d.luau', dts)
edit('README.md', lambda s: s if 'immediate-mode UI widgets' in s else rep(s,'shapes, transforms, UI and in-scene layers |','shapes, transforms, UI and in-scene layers, immediate-mode UI widgets (buttons, sliders, checkboxes, panels, progress bars) |'))
edit('README.ru.md', lambda s: s if 'UI-виджеты' in s else rep(s,'фигуры, трансформации, слои UI и сцены |','фигуры, трансформации, слои UI и сцены, immediate-mode UI-виджеты (кнопки, слайдеры, чекбоксы, панели, прогресс-бары) |'))

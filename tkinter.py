"""Small Tkinter compatibility layer for Physics Chronicles in Pyodide.

The desktop game keeps its Python update, combat, and drawing calls. This
module replaces only the Tk window/Canvas surface with browser callbacks and
an HTML Canvas command buffer.
"""

import json
import sys
import traceback
from types import SimpleNamespace

from js import window
from pyodide.ffi import create_proxy


_root = None
_UNSET = object()


class TclError(Exception):
    pass


class PhotoImage:
    _serial = 0

    def __init__(self, master=None, width=0, height=0, **_kwargs):
        type(self)._serial += 1
        self.image_id = f"player-{type(self)._serial}"
        self.width = int(width)
        self.height = int(height)
        self.pixels = [[None for _ in range(self.width)] for _ in range(self.height)]
        self._registered = False

    def put(self, data, to=(0, 0)):
        x, y = map(int, to)
        if isinstance(data, str):
            colors = data.strip().strip("{}").split()
        else:
            colors = list(data)
        if not 0 <= y < self.height:
            return
        for offset, color in enumerate(colors):
            if x + offset < self.width:
                self.pixels[y][x + offset] = str(color)

    def transparency_set(self, x, y, transparent):
        x, y = int(x), int(y)
        if 0 <= x < self.width and 0 <= y < self.height and transparent:
            self.pixels[y][x] = None


class Canvas:
    def __init__(self, root, **_kwargs):
        self.root = root
        self._physics_draw_tag = None
        self._bindings = {}
        self._items = {}
        self._next_id = 1
        self._registered_images = set()
        root.canvas = self

    def pack(self, **_kwargs):
        return None

    def focus_set(self):
        return None

    def bind(self, sequence, callback):
        self._bindings[sequence] = callback

    def dispatch_key(self, sequence, keysym):
        callback = self._bindings.get(sequence)
        if callback:
            callback(SimpleNamespace(keysym=keysym, char=keysym if len(keysym) == 1 else ""))

    def dispatch_configure(self, width, height):
        callback = self._bindings.get("<Configure>")
        if callback:
            callback(SimpleNamespace(width=int(width), height=int(height)))

    def _create(self, item_type, args, options):
        item_id = self._next_id
        self._next_id += 1
        options = dict(options)
        tags = options.get("tags", ())
        if isinstance(tags, str):
            tags = (tags,)
        options["tags"] = list(tags)
        image = options.pop("image", None)
        if image is not None:
            options["image_id"] = image.image_id
            self._register_image(image)
        self._items[item_id] = {
            "id": item_id,
            "type": str(item_type),
            "coords": [float(value) for value in args],
            "options": options,
        }
        return item_id

    def _register_image(self, image):
        if image.image_id in self._registered_images:
            return
        payload = json.dumps(image.pixels, ensure_ascii=False, separators=(",", ":"))
        window.gameBridge.registerImage(image.image_id, image.width, image.height, payload)
        self._registered_images.add(image.image_id)

    def create_rectangle(self, *coords, **options):
        return self._create("rectangle", coords, options)

    def create_oval(self, *coords, **options):
        return self._create("oval", coords, options)

    def create_line(self, *coords, **options):
        return self._create("line", coords, options)

    def create_polygon(self, *coords, **options):
        return self._create("polygon", coords, options)

    def create_text(self, *coords, **options):
        return self._create("text", coords, options)

    def create_arc(self, *coords, **options):
        return self._create("arc", coords, options)

    def create_image(self, *coords, **options):
        return self._create("image", coords, options)

    def delete(self, target):
        if target in ("all", "ALL"):
            self._items.clear()
            return
        for item_id, item in tuple(self._items.items()):
            if target == item_id or target in item["options"].get("tags", ()):
                del self._items[item_id]

    def move(self, target, dx, dy):
        for item_id, item in self._items.items():
            if target == item_id or target in item["options"].get("tags", ()):
                coords = item["coords"]
                for index in range(0, len(coords) - 1, 2):
                    coords[index] += float(dx)
                    coords[index + 1] += float(dy)

    def flush(self):
        payload = json.dumps(list(self._items.values()), ensure_ascii=False, separators=(",", ":"))
        window.gameBridge.renderFrame(payload)


class Tk:
    def __init__(self):
        global _root
        _root = self
        self.canvas = None
        self.browser_audio = True
        self.report_callback_exception = None
        self._destroyed = False

    def title(self, value):
        window.document.title = str(value)

    def geometry(self, _value):
        return None

    def minsize(self, *_args):
        return None

    def configure(self, **_kwargs):
        return None

    config = configure

    def protocol(self, *_args):
        return None

    def attributes(self, option, value=_UNSET):
        if option != "-fullscreen":
            return False
        if value is _UNSET:
            return bool(window.gameBridge.isFullscreen())
        window.gameBridge.setFullscreen(bool(value))
        return bool(value)

    def after(self, delay_ms, callback):
        # The browser adapter drives PhysicsChronicles.tick from JavaScript's
        # animation frame loop. Letting tick schedule another timeout here
        # creates a second, drifting loop and can stall the Pyodide callback.
        if getattr(callback, "__name__", "") == "tick":
            return None
        proxy = None

        def invoke():
            try:
                if not self._destroyed:
                    callback()
            except Exception:
                detail = traceback.format_exc()
                if self.report_callback_exception:
                    self.report_callback_exception(*sys.exc_info())
                window.gameBridge.showError(detail)
            finally:
                if proxy is not None:
                    proxy.destroy()

        proxy = create_proxy(invoke)
        window.setTimeout(proxy, max(0, int(delay_ms)))
        return proxy

    def set_music(self, enabled, volume):
        window.gameBridge.setMusic(bool(enabled), float(volume))

    def set_sfx_volume(self, volume):
        window.gameBridge.setSfxVolume(float(volume))

    def play_sfx(self, kind, volume):
        window.gameBridge.playSfx(str(kind), float(volume))

    def destroy(self):
        self._destroyed = True
        window.gameBridge.setMusic(False, 0)

    def mainloop(self):
        # Browser timers drive the same `tick` method as Tk's event loop.
        return None


def browser_key_down(keysym):
    if _root and _root.canvas:
        _root.canvas.dispatch_key("<KeyPress>", str(keysym))


def browser_key_up(keysym):
    if _root and _root.canvas:
        _root.canvas.dispatch_key("<KeyRelease>", str(keysym))


def browser_configure(width, height):
    if _root and _root.canvas:
        _root.canvas.dispatch_configure(width, height)


def browser_flush():
    if _root and _root.canvas:
        _root.canvas.flush()


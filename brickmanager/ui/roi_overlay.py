from kivy.graphics import Color, Line
from kivy.uix.widget import Widget


class RoiOverlay(Widget):
    def __init__(self, roi=None, on_change=None, **kwargs):
        super().__init__(**kwargs)
        self.roi = roi or {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
        self.on_change = on_change
        self._start = None
        self.display_rect = None
        self._draw_selection()

    def set_roi(self, roi):
        self.roi = self._normalize(roi)
        self._draw_selection()

    def set_display_rect(self, rect):
        self.display_rect = rect
        self._draw_selection()

    def _image_rect(self):
        return self.display_rect or (self.x, self.y, self.width, self.height)

    def _normalize(self, roi):
        x = max(0.0, min(1.0, float(roi.get("x", 0.0))))
        y = max(0.0, min(1.0, float(roi.get("y", 0.0))))
        width = max(0.01, min(1.0 - x, float(roi.get("width", 1.0))))
        height = max(0.01, min(1.0 - y, float(roi.get("height", 1.0))))
        return {"x": x, "y": y, "width": width, "height": height}

    def _draw_selection(self):
        self.canvas.after.clear()
        image_x, image_y, image_width, image_height = self._image_rect()
        with self.canvas.after:
            Color(0.2, 0.8, 0.3, 1)
            Line(
                rectangle=(
                    image_x + self.roi["x"] * image_width,
                    image_y + (1 - self.roi["y"] - self.roi["height"]) * image_height,
                    self.roi["width"] * image_width,
                    self.roi["height"] * image_height,
                ),
                width=1.5,
            )

    def on_size(self, *_):
        self._draw_selection()

    def on_pos(self, *_):
        self._draw_selection()

    def on_touch_down(self, touch):
        image_x, image_y, image_width, image_height = self._image_rect()
        if not (
            image_x <= touch.x <= image_x + image_width
            and image_y <= touch.y <= image_y + image_height
        ):
            return super().on_touch_down(touch)
        self._start = touch.pos
        self._update_from_touch(touch.pos)
        return True

    def on_touch_move(self, touch):
        if self._start is None:
            return super().on_touch_move(touch)
        self._update_from_touch(touch.pos)
        return True

    def on_touch_up(self, touch):
        if self._start is None:
            return super().on_touch_up(touch)
        self._update_from_touch(touch.pos)
        self._start = None
        return True

    def _update_from_touch(self, position):
        image_x, image_y, image_width, image_height = self._image_rect()
        start_x, start_y = self._start
        start_x = max(image_x, min(image_x + image_width, start_x))
        start_y = max(image_y, min(image_y + image_height, start_y))
        current_x = max(image_x, min(image_x + image_width, position[0]))
        current_y = max(image_y, min(image_y + image_height, position[1]))
        left = min(start_x, current_x)
        bottom = min(start_y, current_y)
        right = max(start_x, current_x)
        top = max(start_y, current_y)
        x = max(0.0, min(1.0, (left - image_x) / max(image_width, 1)))
        y = max(0.0, min(1.0, (image_y + image_height - top) / max(image_height, 1)))
        width = max(0.01, min(1.0 - x, (right - left) / max(image_width, 1)))
        height = max(0.01, min(1.0 - y, (top - bottom) / max(image_height, 1)))
        self.roi = {"x": x, "y": y, "width": width, "height": height}
        self._draw_selection()
        if self.on_change:
            self.on_change(self.roi)

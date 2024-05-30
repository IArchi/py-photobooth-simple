from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics.texture import Texture
from kivy.graphics import Rectangle, Color

# Widget to display camera
class KivyCamera(Image):
    def __init__(self, app, fps=30, **kwargs):
        super(KivyCamera, self).__init__(**kwargs)
        self._app = app
        self._fps = fps
        self._stop = False

    def start(self):
        self._stop = False
        self._app.devices.start_preview(self._fps)
        self._clock = Clock.schedule_once(self._update, 1.0 / self._fps)

    def stop(self):
        self._stop = True
        Clock.unschedule(self._clock)
        self._app.devices.stop_preview()

    def _update(self, args):
        print(args)
        size, buffer = self._app.devices.get_preview()
        if not size or not buffer: return
        image_texture = Texture.create(size=size, colorfmt='bgr')
        image_texture.blit_buffer(buffer, colorfmt='bgr', bufferfmt='ubyte')
        self.texture = image_texture
        if not self._stop:
            self._clock = Clock.schedule_once(self._update, 1.0 / self._fps)

class ImageButton(ButtonBehavior, Image):
    pass

Builder.load_string("""
<BorderedLabel@Label>:
    color : 1,1,1,1
    border_color: (0,0,0,1)
    border_width: .1
    canvas.before:
        Color:
            rgba: self.border_color
        Line:
            width: self.border_width
            rectangle: (self.pos[0], self.pos[1], self.size[0], self.size[1])
""")
class BorderedLabel(Label):
    def __init__(self, **kwargs):
        if 'border_color' in kwargs:
            self.border_color = kwargs.pop('border_color')
        if 'border_width' in kwargs:
            self.border_width = kwargs.pop('border_width')
        super(BorderedLabel, self).__init__(**kwargs)

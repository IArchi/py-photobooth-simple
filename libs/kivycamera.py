from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.graphics.texture import Texture

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

from kivy.clock import Clock
from kivy.uix.image import Image, AsyncImage
from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics.texture import Texture
from kivy.graphics import Rectangle, Color
from kivy.properties import ColorProperty, StringProperty, ListProperty, NumericProperty
from kivy.logger import Logger
import numpy as np

# Widget to display camera
class KivyCamera(Image):
    def __init__(self, app, fps=30, **kwargs):
        super(KivyCamera, self).__init__(**kwargs)
        self._app = app
        self._fps = fps
        self._stop = False
        self.create_empty_texture()

    def start(self, square=False):
        self._stop = False
        self._square = square
        self._clock = Clock.schedule_once(self._update, 1.0 / self._fps)

    def stop(self):
        self._stop = True
        Clock.unschedule(self._clock)

    def create_empty_texture(self):
        width, height = self.size
        # Create a numpy array in 'bgr' format
        black_color = np.zeros((height, width, 3), dtype=np.uint8)

        # Create a texture
        texture = Texture.create(size=(width, height), colorfmt='bgr')
        texture.blit_buffer(black_color.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
        texture.flip_vertical()

        self.texture = texture

    def _update(self, args):
        try:
            im = self._app.devices.get_preview(self._square)
            if im is None: return
            image_texture = Texture.create(size=(im.shape[0], im.shape[1]), colorfmt='bgr')
            image_texture.blit_buffer(im.flatten(), colorfmt='bgr', bufferfmt='ubyte')
            self.texture = image_texture
        except Exception as e:
            Logger.error('Cannot read camera stream.')
            Logger.error(e)

        if not self._stop:
            self._clock = Clock.schedule_once(self._update, 1.0 / self._fps)

Builder.load_string(
"""
<BackgroundBoxLayout@BoxLayout>:
    background_color: 0, 0, 0, 0

    canvas:
        Color:
            rgba: self.background_color
        Rectangle:
            pos: self.pos
            size: self.size
""")
class BackgroundBoxLayout(BoxLayout):
    background_color = ColorProperty()

Builder.load_string("""
<ImageButton@Image>:
    background_color: 0, 0, 0, 0
    padding: (0, 0, 0, 0)
    canvas.before:
        Color:
            rgba: self.background_color
        RoundedRectangle:
            size: (self.size[0]+self.size[0]*0.2, self.size[1]+self.size[1]*0.2)
            pos: (self.pos[0]-self.size[0]*0.1, self.pos[1]-self.size[1]*0.1)
            radius: [15, 0, 0, 15]
""")
class ImageButton(ButtonBehavior, AsyncImage):
    pass

Builder.load_string("""
<ImageLabelButton>:
    orientation: 'horizontal'
    canvas.before:
        Color:
            rgba: self.background_color
        RoundedRectangle:
            size: (self.size[0]+self.size[0]*0.2, self.size[1]+self.size[1]*0.2)
            pos: (self.pos[0]-self.size[0]*0.1, self.pos[1]-self.size[1]*0.1)
            radius: [self.border_radius, 0, 0, self.border_radius]

    Image:
        source: root.source
        size_hint: None, None
        size: root.height * 0.8, root.height
        fit_mode: 'contain'
        keep_ratio: True

    Label:
        text: root.text
        size_hint: None, None
        size: root.width - root.height * 0.8, root.height
        color: root.text_color
        halign: 'center'
        valign: 'middle'
        text_size: self.size * 2
""")
class ImageLabelButton(ButtonBehavior, BoxLayout):
    source = StringProperty('')  # Path to the image
    text = StringProperty('')  # Text to display on the button
    text_color = ListProperty([1, 1, 1, 1])  # Color of the text
    background_color = ListProperty([0, 0, 0, 0])  # Background color
    border_radius = NumericProperty(15)  # Border radius


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

Builder.load_string("""
<ShadowLabel>:
    canvas.before:
        Color:
            rgba: root.tint

        Rectangle:
            pos:
                int(self.center_x - self.texture_size[0] / 2.) + root.decal[0],\
                int(self.center_y - self.texture_size[1] / 2.) + root.decal[1]

            size: root.texture_size
            texture: root.texture

        Color:
            rgba: 1, 1, 1, 1
""")
class ShadowLabel(Label):
    decal = ListProperty([7, -7])
    tint = ListProperty([.5, .5, 1, .5])

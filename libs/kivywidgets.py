from kivy.clock import Clock
from kivy.uix.image import Image, AsyncImage
from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.progressbar import ProgressBar
from kivy.graphics.texture import Texture
from kivy.properties import ColorProperty, StringProperty, ListProperty, NumericProperty
from kivy.metrics import sp
from kivy.logger import Logger
import numpy as np
import cv2


from libs.file_utils import FileUtils

# Widget to display camera
class KivyCamera(Image):
    def __init__(self, app, fps=30, blur=False, **kwargs):
        super(KivyCamera, self).__init__(**kwargs)
        self._app = app
        self._fps = fps
        self._blur = blur
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

            # Generate blurry borders
            if self._blur:
                im = FileUtils.blurry_borders(im, self.size)
                    
            # Apply as texture
            image_texture = Texture.create(size=(im.shape[1], im.shape[0]), colorfmt='bgr')
            image_texture.blit_buffer(im.flatten(), colorfmt='bgr', bufferfmt='ubyte')
            self.texture = image_texture
                
        except Exception as e:
            Logger.error('Cannot read camera stream.')
            Logger.error(e)

        if not self._stop:
            self._clock = Clock.schedule_once(self._update, 1.0 / self._fps)

class BlurredImage(Image):
    filepath = StringProperty('')

    def __init__(self, blur=False, **kwargs):
        super(BlurredImage, self).__init__(**kwargs)
        self._blur = blur
        self.bind(size=self.update_texture)
        if blur: self.create_empty_texture()

    def create_empty_texture(self):
        width, height = self.size
        black_color = np.zeros((height, width, 3), dtype=np.uint8)
        texture = Texture.create(size=(width, height), colorfmt='bgr')
        texture.blit_buffer(black_color.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
        texture.flip_vertical()
        self.texture = texture

    def update_texture(self, *args):
        if self.filepath:
            self.reload()

    def reload(self):
        if self._blur:
            try:
                im = cv2.imread(self.filepath)
                if im is None: return
                im = cv2.flip(im, 0)
                im = FileUtils.blurry_borders(im, self.size)
                image_texture = Texture.create(size=(im.shape[1], im.shape[0]), colorfmt='bgr')
                image_texture.blit_buffer(im.flatten(), colorfmt='bgr', bufferfmt='ubyte')
                self.texture = image_texture
            except Exception as e:
                Logger.error(f'Cannot open image {self.filepath}.')
                Logger.error(e)
        else:
            self.source = self.filepath

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

class LayoutButton(ButtonBehavior, FloatLayout):
    pass

Builder.load_string("""
<ImageRoundButton>:
    background_color: 0, 0, 0, 0
    padding: (0, 0, 0, 0)
    canvas.before:
        Color:
            rgba: self.background_color
        Ellipse:
            size: (self.size[1] * 1.4 if self.parent and self.parent.size[0] > self.parent.size[1] else self.size[0] * 1.4, self.size[1] * 1.4 if self.parent and self.parent.size[0] > self.parent.size[1] else self.size[0] * 1.4)
            pos: (self.center_x - (self.size[1] * 1.4 if self.parent and self.parent.size[0] > self.parent.size[1] else self.size[0] * 1.4) / 2, self.center_y - (self.size[1] * 1.4 if self.parent and self.parent.size[0] > self.parent.size[1] else self.size[0] * 1.4) / 2)
""")
class ImageRoundButton(ButtonBehavior, AsyncImage):
    source = StringProperty('')
    background_color = ListProperty([0, 0, 0, 0])

class ResizeLabel(Label):
    max_font_size = NumericProperty(sp(16))

    def on_size(self, *args):
        font_size = self.width / len(self.text) * 1.5
        self.font_size = min(self.size[1] if font_size > self.size[1] else font_size, self.max_font_size)

Builder.load_string("""
<LabelRoundButton>:
    background_color: 0, 0, 0, 0
    padding: (0, 0, 0, 0)
    canvas.before:
        Color:
            rgba: self.background_color
        Ellipse:
            size: (self.size[1] * 1.4 if self.parent and self.parent.size[0] > self.parent.size[1] else self.size[0] * 1.4, self.size[1] * 1.4 if self.parent and self.parent.size[0] > self.parent.size[1] else self.size[0] * 1.4)
            pos: (self.center_x - (self.size[1] * 1.4 if self.parent and self.parent.size[0] > self.parent.size[1] else self.size[0] * 1.4) / 2, self.center_y - (self.size[1] * 1.4 if self.parent and self.parent.size[0] > self.parent.size[1] else self.size[0] * 1.4) / 2)
""")
class LabelRoundButton(ButtonBehavior, ResizeLabel):
    text = StringProperty('')
    font_name = StringProperty('')
    background_color = ListProperty([0, 0, 0, 0])
    max_font_size = NumericProperty(sp(16))

    def __init__(self, **kwargs):
        max_font_size = kwargs.pop('max_font_size', None)
        super(LabelRoundButton, self).__init__(**kwargs)
        if max_font_size is not None:
            self.max_font_size = max_font_size

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

    def on_size(self, *args):
        self.font_size = self.width / len(self.text) * 1.5

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

Builder.load_string('''
<RotatingImage>:
    canvas.before:
        PushMatrix
        Rotate:
            angle: root.angle
            axis: 0, 0, 1
            origin: root.center
    canvas.after:
        PopMatrix
''')
class RotatingImage(AsyncImage):
    angle = NumericProperty()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.angle = 0
        Clock.schedule_interval(self.update, 1/60)

    def update(self, dt):
        self.angle -= 2
        self.angle %= 360

Builder.load_string('''
<RotatingLabel>:
    canvas.before:
        PushMatrix
        Rotate:
            angle: root.angle
            axis: 0, 0, 1
            origin: root.center
    canvas.after:
        PopMatrix
''')
class RotatingLabel(ResizeLabel):
    angle = NumericProperty()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.angle = 0
        Clock.schedule_interval(self.update, 1/60)

    def update(self, dt):
        self.angle -= 2
        self.angle %= 360

class ResizeLabel(Label):
    max_font_size = NumericProperty(sp(16))
    def on_size(self, *args):
        font_size = self.width / len(self.text) * 1.5
        self.font_size = min(self.size[1] if font_size > self.size[1] else font_size, self.max_font_size)

Builder.load_string('''
<ThickProgressBar@ProgressBar>:
    canvas:
        Color:
            rgba: 1, 1, 1, 0
        Rectangle:
            pos: self.x, self.center_y - dp(3)
            size: self.width, dp(6)

        Color:
            rgba: self.color
        Rectangle:
            pos: self.x, self.center_y - dp(3)
            size: self.width * (self.value / float(self.max)) if self.max else 0, dp(6)
''')
class ThickProgressBar(ProgressBar):
    color = ColorProperty()

def hex_to_rgba(hex_color):
    # Enlève le caractère '#' si présent
    hex_color = hex_color.lstrip('#')
    
    # Convertit les valeurs hexadécimales en décimales
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    
    # Retourne le tuple avec alpha à 1
    return (r, g, b, 1.0)
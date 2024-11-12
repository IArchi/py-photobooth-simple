from kivy.clock import Clock
from kivy.uix.image import Image, AsyncImage
from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.properties import ColorProperty, StringProperty, ListProperty, NumericProperty
from kivy.metrics import sp
from kivy.logger import Logger
import numpy as np
import cv2

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

            width, height = self.size
            im_height, im_width = im.shape[:2]

            # Resize image to match screen
            scale_factor = min(height / im_height, width / im_width)
            new_size = (int(im_width * scale_factor), int(im_height * scale_factor))
            im = cv2.resize(im, new_size)

            # Generate blur on sides
            blurred_image = cv2.GaussianBlur(im, (15, 15), 0)
            im_height, im_width = im.shape[:2]
            if self._square:
                difference = int((width - im_width) // 2)
                if difference > 0:
                    left_blur = blurred_image[:, :difference]
                    right_blur = blurred_image[:, im_width - difference:]
                    combined_image = np.hstack((left_blur, im, right_blur))
                else:
                    combined_image = im
            else: 
                difference = int((height - im_height) // 2)
                if difference > 0:
                    top_blur = blurred_image[:difference, :]
                    bottom_blur = blurred_image[im_height - difference:, :]
                    combined_image = np.vstack((top_blur, im, bottom_blur))
                else:
                    combined_image = im
                    
            # Apply as texture
            image_texture = Texture.create(size=(combined_image.shape[1], combined_image.shape[0]), colorfmt='bgr')
            image_texture.blit_buffer(combined_image.flatten(), colorfmt='bgr', bufferfmt='ubyte')
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
            size: self.size[1] * 1.4, self.size[1] * 1.4
            pos: self.center_x - (self.size[1] * 1.4) / 2, self.center_y - (self.size[1] * 1.4) / 2
""")
class ImageRoundButton(ButtonBehavior, AsyncImage):
    source = StringProperty('')
    background_color = ListProperty([0, 0, 0, 0])

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

class ResizeLabel(Label):
    max_font_size = NumericProperty(sp(16))

    def on_size(self, *args):
        font_size = self.width / len(self.text) * 1.5
        self.font_size = min(self.size[1] if font_size > self.size[1] else font_size, self.max_font_size)

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
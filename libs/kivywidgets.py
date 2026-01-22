from kivy.clock import Clock
from kivy.uix.image import Image, AsyncImage
from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.progressbar import ProgressBar
from kivy.graphics.texture import Texture
from kivy.properties import ColorProperty, StringProperty, ListProperty, NumericProperty, BooleanProperty
from kivy.metrics import sp
from kivy.logger import Logger
from kivy.core.window import Window
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

    def start(self, aspect_ratio=None):
        self._stop = False
        self._aspect_ratio = aspect_ratio
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
            im = self._app.devices.get_preview(self._aspect_ratio)
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
        try:
            im = cv2.imread(self.filepath)
            if im is None: return
            im = cv2.flip(im, 0)
            if self._blur: im = FileUtils.blurry_borders(im, self.size)
            image_texture = Texture.create(size=(im.shape[1], im.shape[0]), colorfmt='bgr')
            image_texture.blit_buffer(im.flatten(), colorfmt='bgr', bufferfmt='ubyte')
            self.texture = image_texture
        except Exception as e:
            Logger.error(f'Cannot open image {self.filepath}.')
            Logger.error(e)
            super().reload()

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
            size: min(self.size) * 1.4, min(self.size) * 1.4
            pos: (self.center_x - (min(self.size) * 1.4) / 2, self.center_y - (min(self.size) * 1.4) / 2)
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
<SquareFloatLayout>:
    size_hint: None, None
    background_color: 0, 0, 0, 0

    canvas:
        Color:
            rgba: self.background_color
        Rectangle:
            pos: self.pos
            size: self.size
""")
class SquareFloatLayout(FloatLayout):
    size_square = NumericProperty(100)
    background_color = ColorProperty()
    use_parent_size = BooleanProperty(False)
    
    def __init__(self, use_parent_size=False, **kwargs):
        self.use_parent_size = use_parent_size
        super(SquareFloatLayout, self).__init__(**kwargs)
        if not use_parent_size:
            self._update_size()
            Window.bind(size=self._on_window_resize)
        else:
            self.bind(parent=self._on_parent_change)
    
    def _on_window_resize(self, instance, value):
        if not self.use_parent_size:
            self._update_size()
    
    def _on_parent_change(self, instance, parent):
        if parent and self.use_parent_size:
            parent.bind(size=self._update_size_from_parent)
            self._update_size_from_parent()
    
    def _update_size(self, *args):
        # Use Window size for consistent button sizing across all screens
        window_min = min(Window.size)
        button_size = window_min * self.size_square
        self.size = (button_size, button_size)
    
    def _update_size_from_parent(self, *args):
        # Use parent size for buttons in BoxLayouts
        if self.parent:
            parent_min = min(self.parent.size) if self.parent.size[0] > 0 and self.parent.size[1] > 0 else 150
            button_size = parent_min * self.size_square
            self.size = (button_size, button_size)

Builder.load_string("""
<LabelRoundButton>:
    background_color: 0, 0, 0, 0
    padding: (0.2, 0.2, 0.2, 0.2)
    canvas.before:
        Color:
            rgba: self.background_color
        Ellipse:
            size: self.size
            pos: self.pos
""")
class LabelRoundButton(ButtonBehavior, ResizeLabel):
    text = StringProperty('')
    font_name = StringProperty('Roboto')
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
<BreezyBorderedLabel@Label>:
    color : 1,1,1,1
    border_color: (0,0,0,1)
    border_width: .1
    breeze_width: 0
    breeze_alpha: 0
    canvas.before:
        Color:
            rgba: self.border_color
        Line:
            width: self.border_width
            rectangle: (self.pos[0], self.pos[1], self.size[0], self.size[1])
        Color:
            rgba: self.border_color[0], self.border_color[1], self.border_color[2], self.breeze_alpha
        Line:
            width: self.border_width * 4
            rectangle: (self.pos[0] - self.breeze_width - self.border_width, self.pos[1] - self.breeze_width - self.border_width, self.size[0] + 2 * (self.breeze_width + self.border_width), self.size[1] + 2 * (self.breeze_width + self.border_width))
""")
class BreezyBorderedLabel(Label):
    border_color = ColorProperty([0, 0, 0, 1])
    border_width = NumericProperty(0.1)
    breeze_width = NumericProperty(0)
    breeze_alpha = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super(BreezyBorderedLabel, self).__init__(**kwargs)
        self._animation_event = None
        self.start_breeze()

    def on_size(self, *args):
        self.font_size = self.width / len(self.text) * 1.5
    
    def start_breeze(self):
        if self._animation_event is None:
            self._animation_event = Clock.schedule_interval(self._update_breeze, 1/60.0)
    
    def stop_breeze(self):
        if self._animation_event is not None:
            Clock.unschedule(self._animation_event)
            self._animation_event = None
            self.breeze_width = 0
            self.breeze_alpha = 0
    
    def _update_breeze(self, dt):
        max_width = 100
        min_alpha = 0.4
        speed = 30
        
        self.breeze_width += speed * dt
        
        if self.breeze_width >= max_width:
            self.breeze_width = 0
        
        progress = self.breeze_width / max_width
        self.breeze_alpha = min_alpha * (1 - progress)

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

Builder.load_string('''
<CircularProgressCounter>:
    canvas.before:
        # Cercle de fond semi-transparent
        Color:
            rgba: 0, 0, 0, 0.5
        Ellipse:
            pos: self.center_x - self.circle_size/2, self.center_y - self.circle_size/2
            size: self.circle_size, self.circle_size
        
        # Arc de progression
        Color:
            rgba: root.progress_color
        Line:
            circle: (self.center_x, self.center_y, self.circle_size/2, 0, - (360 * root.progress))
            width: root.line_width
            cap: 'round'
''')
class CircularProgressCounter(FloatLayout):
    progress = NumericProperty(0)  # 0 à 1
    progress_color = ColorProperty([1, 1, 1, 1])
    circle_size = NumericProperty(300)
    line_width = NumericProperty(8)
    
    def __init__(self, **kwargs):
        super(CircularProgressCounter, self).__init__(**kwargs)
        self.label = ShadowLabel(
            text='',
            halign='center',
            valign='middle',
            font_size='120sp',
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.add_widget(self.label)
    
    def set_text(self, text):
        self.label.text = str(text)
    
    def set_progress(self, value):
        """Set progress from 0 to 1"""
        self.progress = max(0, min(1, value))

Builder.load_string("""
<RoundedButton>:
    background_color: 1, 1, 1, 1
    canvas.before:
        Color:
            rgba: self.background_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [20,]
""")
class RoundedButton(ButtonBehavior, Label):
    background_color = ListProperty([1, 1, 1, 1])

def make_icon_button(icon, size, pos_hint={}, font='Roboto', font_size=10, bgcolor=(1,1,1,1), badge=None, badge_font_size=10, badge_color=(1,0,0,1), on_release=None):
    # If size >= 1, use parent size (for buttons in BoxLayouts), otherwise use Window size
    use_parent = (size >= 1.0)
    parent = SquareFloatLayout(
        size_square=size,
        pos_hint=pos_hint,
        use_parent_size=use_parent,
    )
    ic = LabelRoundButton(
        font_name=font,
        text=icon,
        size_hint=(1, 1),
        pos_hint={'center_x': 0.5, 'center_y': 0.5},
        background_color=bgcolor,
        max_font_size=font_size,
    )
    parent.add_widget(ic)
    if badge:
        bg = LabelRoundButton(
            text=badge,
            bold=True,
            size_hint=(0.4, 0.4),
            pos_hint={'right': 1, 'top': 1},
            background_color=badge_color,
            max_font_size=badge_font_size,
        )
        parent.add_widget(bg)
    ic.bind(on_release=on_release)
    return parent

Builder.load_string("""
<IconTextButton>:
    background_color: 1, 1, 1, 1
    orientation: 'horizontal'
    spacing: 10
    padding: 15
    canvas.before:
        Color:
            rgba: self.background_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [20,]
""")
class IconTextButton(ButtonBehavior, BoxLayout):
    background_color = ListProperty([1, 1, 1, 1])

def make_icon_text_button(icon, text, size_hint=(0.25, 0.09), pos_hint={}, icon_font='Roboto', text_font='Roboto', icon_font_size='50sp', text_font_size='30sp', bgcolor=(1,1,1,1), on_release=None):
    """
    Create a horizontal button with icon on left and text on right
    
    Args:
        icon: Icon character to display
        text: Text to display
        size_hint: Size hint tuple (width, height)
        pos_hint: Position hint dict
        icon_font: Font for the icon
        text_font: Font for the text
        icon_font_size: Font size for the icon (can be string like '60sp' or number)
        text_font_size: Maximum font size for the text (can be string like '30sp' or number) - will auto-resize on small screens
        bgcolor: Background color tuple (r, g, b, a)
        on_release: Callback function for button release
    
    Returns:
        IconTextButton widget
    """
    button = IconTextButton(
        size_hint=size_hint,
        pos_hint=pos_hint,
        background_color=bgcolor,
    )
    
    # Icon container with padding
    icon_container = BoxLayout(
        size_hint=(0.4, 1),
        padding=(0, 10, 0, 10),  # Add vertical padding
    )
    
    # Icon label
    icon_label = Label(
        text=icon,
        font_name=icon_font,
        font_size=icon_font_size,
        color=(1, 1, 1, 1),
    )
    icon_container.add_widget(icon_label)
    button.add_widget(icon_container)
    
    # Text label - using ResizeLabel for auto-resizing on small screens
    text_label = ResizeLabel(
        text=text,
        font_name=text_font,
        max_font_size=text_font_size,
        size_hint=(0.6, 1),
        color=(1, 1, 1, 1),
        bold=True,
        halign='center',
        valign='middle',
    )
    text_label.bind(size=text_label.setter('text_size'))
    button.add_widget(text_label)
    
    if on_release:
        button.bind(on_release=on_release)
    
    return button

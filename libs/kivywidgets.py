from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.image import Image, AsyncImage
from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.progressbar import ProgressBar
from kivy.graphics.texture import Texture
from kivy.properties import ColorProperty, StringProperty, ListProperty, NumericProperty, BooleanProperty
from kivy.metrics import dp, sp
from kivy.logger import Logger
from kivy.core.window import Window
import numpy as np
import cv2


from libs.file_utils import FileUtils

# Widget to display camera
class KivyCamera(Image):
    def __init__(self, app, fps=30, blur=False, blur_refresh_frames=1, **kwargs):
        super(KivyCamera, self).__init__(**kwargs)
        self._app = app
        self._fps = fps
        self._blur = blur
        self._blur_refresh_frames = max(1, int(blur_refresh_frames))
        self._blur_cache = None
        self._frame_count = 0
        self._stop = False
        self._reuse_texture = None  # Réutilisation pour éviter allocations à chaque frame
        self._last_frame_id = None
        self.create_empty_texture()

    def start(self, aspect_ratio=None):
        self._stop = False
        self._aspect_ratio = aspect_ratio
        self._blur_cache = None
        self._frame_count = 0
        self._last_frame_id = None
        self._clock = Clock.schedule_once(self._update, 1.0 / self._fps)

    def stop(self):
        self._stop = True
        Clock.unschedule(self._clock)
        self._blur_cache = None
        self._frame_count = 0
        self._reuse_texture = None

    def create_empty_texture(self):
        width, height = max(1, int(self.size[0])), max(1, int(self.size[1]))
        # Create a numpy array in 'bgr' format
        black_color = np.zeros((height, width, 3), dtype=np.uint8)

        # Create a texture
        texture = Texture.create(size=(width, height), colorfmt='bgr')
        texture.blit_buffer(black_color.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
        texture.flip_vertical()

        self.texture = texture

    def _update(self, args):
        try:
            frame_id = self._app.devices.get_preview_frame_id()
            if frame_id == self._last_frame_id:
                return
            im = self._app.devices.get_preview(self._aspect_ratio)
            if im is None:
                return
            self._last_frame_id = frame_id

            # Generate blurry borders (réduire la résolution avant blur pour plus de fluidité)
            if self._blur:
                if self.width <= 1 or self.height <= 1:
                    return
                max_w, max_h = 1280, 720
                h, w = im.shape[:2]
                if w > max_w or h > max_h:
                    scale = min(max_w / w, max_h / h)
                    im = cv2.resize(im, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                refresh_blur = (self._frame_count % self._blur_refresh_frames) == 0
                im, self._blur_cache = FileUtils.blurry_borders(
                    im,
                    self.size,
                    blur_cache=self._blur_cache,
                    refresh_blur=refresh_blur,
                    return_cache=True,
                )
                self._frame_count += 1

            # Réutiliser la texture si la taille est identique (évite Texture.create à chaque frame)
            w, h = im.shape[1], im.shape[0]
            if self._reuse_texture is not None and self._reuse_texture.size == (w, h):
                self._reuse_texture.blit_buffer(im.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
                # Forcer le rafraîchissement du canvas car la référence de texture n'a pas changé
                self.canvas.ask_update()
            else:
                self._reuse_texture = Texture.create(size=(w, h), colorfmt='bgr')
                self._reuse_texture.blit_buffer(im.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
                self.texture = self._reuse_texture

        except Exception as e:
            Logger.error('Cannot read camera stream.')
            Logger.error(e)
        finally:
            if not self._stop:
                self._clock = Clock.schedule_once(self._update, 1.0 / self._fps)

class BlurredImage(Image):
    filepath = StringProperty('')

    def __init__(self, blur=False, **kwargs):
        super(BlurredImage, self).__init__(**kwargs)
        self._blur = blur
        self._last_size = None
        if blur:
            self.bind(size=self.update_texture)
            self.create_empty_texture()

    def create_empty_texture(self):
        width, height = max(1, int(self.size[0])), max(1, int(self.size[1]))
        black_color = np.zeros((height, width, 3), dtype=np.uint8)
        texture = Texture.create(size=(width, height), colorfmt='bgr')
        texture.blit_buffer(black_color.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
        texture.flip_vertical()
        self.texture = texture

    def update_texture(self, *args):
        # Only reload if size actually changed significantly (avoid micro-updates)
        if self.filepath and self._blur:
            current_size = (int(self.size[0]), int(self.size[1]))
            if self._last_size is None or \
               abs(current_size[0] - self._last_size[0]) > dp(10) or \
               abs(current_size[1] - self._last_size[1]) > dp(10):
                self._last_size = current_size
                self.reload()

    def set_image(self, im):
        """Met à jour l'affichage à partir d'un tableau numpy (BGR). Appel thread-safe via Clock.schedule_once."""
        if im is None: return
        try:
            im = cv2.flip(im, 0)
            if self._blur: im = FileUtils.blurry_borders(im, self.size)
            image_texture = Texture.create(size=(im.shape[1], im.shape[0]), colorfmt='bgr')
            image_texture.blit_buffer(im.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
            self.texture = image_texture
        except Exception as e:
            Logger.error('BlurredImage.set_image: %s', e)

    def reload(self):
        try:
            im = cv2.imread(self.filepath)
            if im is None: return
            im = cv2.flip(im, 0)
            if self._blur: im = FileUtils.blurry_borders(im, self.size)
            image_texture = Texture.create(size=(im.shape[1], im.shape[0]), colorfmt='bgr')
            image_texture.blit_buffer(im.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
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

class FeedbackButtonBehavior(ButtonBehavior):
    """Tiny press feedback: opacity only, no ripple/canvas work on weak hardware."""
    feedback_opacity = NumericProperty(0.72)

    def on_state(self, instance, value):
        Animation.cancel_all(self, 'opacity')
        Animation(opacity=self.feedback_opacity if value == 'down' else 1, d=0.06).start(self)

class ImageButton(FeedbackButtonBehavior, AsyncImage):
    pass

class LayoutButton(FeedbackButtonBehavior, FloatLayout):
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
class ImageRoundButton(FeedbackButtonBehavior, AsyncImage):
    source = StringProperty('')
    background_color = ListProperty([0, 0, 0, 0])

class ResizeLabel(Label):
    max_font_size = NumericProperty(sp(16))
    # If set (0..1), max_font_size tracks min(Window.width, Window.height) * wh_fraction on every
    # resize — uses the shortest side so the font stays visible in both landscape and portrait.
    wh_fraction = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.wh_fraction:
            self.max_font_size = min(Window.size) * self.wh_fraction
            Window.bind(size=self._update_max_font)

    def _update_max_font(self, *args):
        if self.wh_fraction:
            self.max_font_size = min(Window.size) * self.wh_fraction
            self.on_size()

    def on_size(self, *args):
        if not self.text:
            return
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
            parent_min = min(self.parent.size) if self.parent.size[0] > 0 and self.parent.size[1] > 0 else Window.height * 0.17
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
class LabelRoundButton(FeedbackButtonBehavior, ResizeLabel):
    text = StringProperty('')
    font_name = StringProperty('Roboto')
    background_color = ListProperty([0, 0, 0, 0])
    max_font_size = NumericProperty(sp(16))

    def __init__(self, **kwargs):
        max_font_size = kwargs.pop('max_font_size', None)
        super(LabelRoundButton, self).__init__(**kwargs)
        # Only override max_font_size if no wh_fraction was set (wh_fraction takes priority)
        if max_font_size is not None and not self.wh_fraction:
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
    border_width = NumericProperty(dp(0.1))
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
            self._animation_event = Clock.schedule_interval(self._update_breeze, 1/30.0)
    
    def stop_breeze(self):
        if self._animation_event is not None:
            Clock.unschedule(self._animation_event)
            self._animation_event = None
            self.breeze_width = 0
            self.breeze_alpha = 0
    
    def _update_breeze(self, dt):
        max_width = dp(100)
        min_alpha = 0.4
        speed = dp(30)
        
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
    decal = ListProperty([dp(7), -dp(7)])
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
        Clock.schedule_interval(self.update, 1/30)

    def update(self, dt):
        self.angle -= 4  # Was 2 at 60fps, now 4 at 30fps for same visual speed
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
        Clock.schedule_interval(self.update, 1/30)

    def update(self, dt):
        self.angle -= 4  # Was 2 at 60fps, now 4 at 30fps for same visual speed
        self.angle %= 360

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
            pos: self.center_x - (self.circle_size * root.circle_scale)/2, self.center_y - (self.circle_size * root.circle_scale)/2
            size: self.circle_size * root.circle_scale, self.circle_size * root.circle_scale
        
        # Arc de progression
        Color:
            rgba: root.progress_color
        Line:
            circle: (self.center_x, self.center_y, (self.circle_size * root.circle_scale)/2, 0, 360 * root.progress)
            width: root.line_width
            cap: 'round'
''')
class CircularProgressCounter(FloatLayout):
    progress = NumericProperty(0)  # 0 à 1
    progress_color = ColorProperty([1, 1, 1, 1])
    circle_size = NumericProperty(300)
    line_width = NumericProperty(8)
    # ponytail: min/max in window-height fractions, not dp — dp lies on Retina/high-DPI screens
    min_circle_size = NumericProperty(0)   # set dynamically in __init__
    max_circle_size = NumericProperty(0)   # set dynamically in __init__
    circle_scale = NumericProperty(0.88)
    size_ratio = NumericProperty(0.55)
    small_screen_ratio = NumericProperty(0.38)
    outer_padding = NumericProperty(0)     # set dynamically in __init__
    small_screen_padding = NumericProperty(0)  # set dynamically in __init__
    
    def __init__(self, **kwargs):
        super(CircularProgressCounter, self).__init__(**kwargs)
        # Use min(Window.size) fractions — stays correct in both landscape and portrait
        self.min_circle_size = min(Window.size) * 0.20
        self.max_circle_size = min(Window.size) * 0.40
        self.outer_padding = min(Window.size) * 0.06
        self.small_screen_padding = min(Window.size) * 0.035
        self.label = ShadowLabel(
            text='',
            halign='center',
            valign='middle',
            font_size=min(Window.size) * 0.13,
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.add_widget(self.label)
        self.bind(circle_size=self._update_label_size)
        Window.bind(size=self._on_window_resize)
        Clock.schedule_once(self._update_responsive_size, 0)

    def _on_window_resize(self, *args):
        self.min_circle_size = min(Window.size) * 0.20
        self.max_circle_size = min(Window.size) * 0.40
        self.outer_padding = min(Window.size) * 0.06
        self.small_screen_padding = min(Window.size) * 0.035
        self._update_responsive_size()

    def _update_responsive_size(self, *args):
        window_min = min(Window.size)
        is_small_screen = window_min < Window.height * 0.75
        size_ratio = self.small_screen_ratio if is_small_screen else self.size_ratio
        responsive_circle_size = min(self.max_circle_size, window_min * size_ratio)
        self.circle_size = max(self.min_circle_size, responsive_circle_size)
        padding = self.small_screen_padding if is_small_screen else self.outer_padding
        widget_size = self.circle_size + padding
        self.size = (widget_size, widget_size)

    def _update_label_size(self, *args):
        self.label.font_size = max(min(Window.size) * 0.13, min(min(Window.size) * 0.24, self.circle_size * 0.82))
    
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
class RoundedButton(FeedbackButtonBehavior, Label):
    background_color = ListProperty([1, 1, 1, 1])

def make_icon_button(icon, size, pos_hint={}, font='Roboto', font_size=sp(10), font_size_fraction=0, bgcolor=(1,1,1,1), badge=None, badge_font_size=sp(10), badge_color=(1,0,0,1), on_release=None):
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
        wh_fraction=font_size_fraction,
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
class IconTextButton(FeedbackButtonBehavior, BoxLayout):
    background_color = ListProperty([1, 1, 1, 1])

def make_icon_text_button(icon, text, size_hint=(0.25, 0.09), pos_hint={}, icon_font='Roboto', text_font='Roboto', icon_font_size=sp(50), icon_font_size_fraction=0, text_font_size=sp(30), text_font_size_fraction=0, bgcolor=(1,1,1,1), on_release=None):
    """
    Create a horizontal button with icon on left and text on right.
    Icon/text sizing follows the real button size, not Window height/width alone.
    """
    button = IconTextButton(
        size_hint=size_hint,
        pos_hint=pos_hint,
        background_color=bgcolor,
    )
    def resize_button(*args):
        if not button.parent:
            return
        if isinstance(button.parent, FloatLayout):
            button.size_hint = (None, None)
            width = button.parent.width * size_hint[0]
            height = min(max(button.parent.height * size_hint[1], dp(48)), button.parent.height)
            # ponytail: icon + short label need a minimum aspect ratio; longer labels need a larger size_hint.
            min_ratio = 2.5
            width = max(width, height * min_ratio)
            if width > button.parent.width:
                width = button.parent.width
                height = min(height, width / min_ratio)
            button.size = (width, height)
        margin = min(dp(15), max(dp(3), button.height * 0.12))
        button.padding = (margin, margin, margin, margin)
        button.spacing = margin
    def bind_parent_size(*args):
        if button.parent:
            button.parent.bind(size=resize_button)
        resize_button()
    button.bind(parent=bind_parent_size)
    Clock.schedule_once(resize_button, 0)
    
    # Icon container: icon follows the real button height, not Window height.
    icon_container = BoxLayout(
        size_hint=(0.4, 1),
    )
    
    icon_label = Label(
        text=icon,
        font_name=icon_font,
        color=(1, 1, 1, 1),
        font_size=icon_font_size,
        size_hint=(1, 1),
        halign='center',
        valign='middle',
    )
    def resize_icon(*args):
        icon_label.font_size = max(sp(1), min(icon_container.height, icon_container.width) * 0.95)
        icon_label.text_size = icon_label.size
    icon_container.bind(size=resize_icon)
    icon_label.bind(size=resize_icon)
    Clock.schedule_once(resize_icon, 0)
    icon_container.add_widget(icon_label)
    button.add_widget(icon_container)
    
    text_label = Label(
        text=text,
        font_name=text_font,
        size_hint=(0.6, 1),
        color=(1, 1, 1, 1),
        bold=True,
        halign='center',
        valign='middle',
    )
    def resize_text(*args):
        text_label.text_size = text_label.size
        fit_width = text_label.width / max(len(text), 1) * 1.5
        text_label.font_size = max(sp(1), min(text_label.height * 0.7, fit_width))
    text_label.bind(size=resize_text)
    Clock.schedule_once(resize_text, 0)
    button.add_widget(text_label)
    
    if on_release:
        button.bind(on_release=on_release)
    
    return button

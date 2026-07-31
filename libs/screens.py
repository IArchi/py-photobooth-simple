import threading
import time
import io
import cv2
import numpy as np
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.graphics import Rectangle, Color
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.input.providers.mouse import MouseMotionEvent
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.core.image import Image as CoreImage

from libs.kivywidgets import *
from libs.file_utils import FileUtils

# Font sizes as fractions of min(Window.width, Window.height) — DPI-independent and
# orientation-independent: the shortest side is always the binding constraint so fonts
# stay visible whether the window is landscape or portrait.
def XLARGE_FONT(): return min(Window.size) * 0.22
def LARGE_FONT():  return min(Window.size) * 0.07
def NORMAL_FONT(): return min(Window.size) * 0.055
def SMALL_FONT():  return min(Window.size) * 0.035
def TINY_FONT():   return min(Window.size) * 0.018

# Registry of (weakref, attr, fraction_fn) updated on every Window resize.
# Call wh_bind(widget, 'font_size', LARGE_FONT) after creating a widget to keep it live.
import weakref as _weakref
_WH_BINDINGS = []  # [(weakref, attr, fn), ...]

def wh_bind(widget, attr, fn):
    """Register a widget attribute to be updated on Window resize."""
    _WH_BINDINGS.append((_weakref.ref(widget), attr, fn))

def _on_window_resize(instance, size):
    dead = []
    for entry in _WH_BINDINGS:
        ref, attr, fn = entry
        obj = ref()
        if obj is None:
            dead.append(entry)
        else:
            setattr(obj, attr, fn())
    for d in dead:
        _WH_BINDINGS.remove(d)

Window.bind(size=_on_window_resize)

SHOT_TIMEOUT_SECONDS = 10
HOME_TIMEOUT_SECONDS = 60
COUNTDOWN_HOME_TIMEOUT_SECONDS = 30
CONFIRM_CAPTURE_HOME_TIMEOUT_SECONDS = 30

def hex_to_rgba(hex_color):
    hex_color = hex_color.lstrip('#')
    return (
        int(hex_color[0:2], 16) / 255.0,
        int(hex_color[2:4], 16) / 255.0,
        int(hex_color[4:6], 16) / 255.0,
        1.0,
    )

def lighten_rgba(color, amount=0.35):
    return (
        min(1.0, color[0] + (1.0 - color[0]) * amount),
        min(1.0, color[1] + (1.0 - color[1]) * amount),
        min(1.0, color[2] + (1.0 - color[2]) * amount),
        color[3],
    )

def darken_rgba(color, amount=0.25):
    return (
        max(0.0, color[0] * (1.0 - amount)),
        max(0.0, color[1] * (1.0 - amount)),
        max(0.0, color[2] * (1.0 - amount)),
        color[3],
    )

# Colors
BACKGROUND_COLOR = hex_to_rgba('#26495c')
BORDER_COLOR = hex_to_rgba('#c4a35a')
BORDER_THINKNESS = dp(0)#Window.height * 0.011
PROGRESS_COLOR = hex_to_rgba('#e5e5e5')
CONFIRM_COLOR = hex_to_rgba('#538a64')
CANCEL_COLOR = hex_to_rgba('#8b4846')
HOME_COLOR = hex_to_rgba('#534969')
HOME_PROGRESS_COLOR = darken_rgba(HOME_COLOR) #lighten_rgba(HOME_COLOR)
BADGE_COLOR = hex_to_rgba('#8b4846')
SHARE_COLOR = hex_to_rgba('#667eea')

# Icons
ICON_TTF = './assets/fonts/hugeicons.ttf' # https://hugeicons.com/free-icon-font and https://hugeicons.com/icons?style=Stroke&type=Rounded
ICON_TOUCH = '\u3d3e'
ICON_ERROR = '\u3b03'
ICON_ERROR_PRINTING = '\u458d'
ICON_ERROR_TRIGGER = '\u3d39'
ICON_LOADING = '\u45ec'
ICON_PROCESSING = '\u3ad2'
ICON_SHOT_TO_TAKE = '\u47f2'
ICON_SHOT_TAKEN = '\u3daa'
ICON_CONFIRM = '\u4908'
ICON_CANCEL = '\u3d42'
ICON_HOME = '\u4161'
ICON_PRINT = '\u458e'
ICON_SUCCESS = '\u4903'
ICON_SUCCESS2 = '\u4304'
ICON_USB = '\u49ba'
ICON_TRIGGER = '\u3d3e'
ICON_QRCODE = '\u45f4'
ICON_SHARE = '\u46d4'


class ScreenMgr(ScreenManager):
    """Screen Manager for the photobooth screens."""
    START = 'start'
    READY = 'ready'
    SELECT_FORMAT = 'select_format'
    ERROR = 'error'
    COUNTDOWN = 'countdown'
    CONFIRM_CAPTURE = 'confirm_capture'
    PROCESSING = 'processing'
    REVIEW = 'review'
    PRINTING = 'printing'
    SUCCESS = 'success'
    COPYING = 'copying'

    def __init__(self, app, **kwargs):
        Logger.info('ScreenMgr: __init__().')
        super(ScreenMgr, self).__init__(**kwargs)
        self.app = app
        self.pb_screens = {
            self.START              : StartScreen(app, name=self.START),
            self.SELECT_FORMAT      : SelectFormatScreen(app, name=self.SELECT_FORMAT),
            self.ERROR              : ErrorScreen(app, name=self.ERROR),
            self.COUNTDOWN          : CountdownScreen(app, name=self.COUNTDOWN),
            self.CONFIRM_CAPTURE    : ConfirmCaptureScreen(app, name=self.CONFIRM_CAPTURE),
            self.PROCESSING         : ProcessingScreen(app, name=self.PROCESSING),
            self.REVIEW             : ReviewScreen(app, name=self.REVIEW),
            self.SUCCESS            : SuccessScreen(app, name=self.SUCCESS),
            self.COPYING            : CopyingScreen(app, name=self.COPYING),
        }
        for screen in self.pb_screens.values(): self.add_widget(screen)

        self.current = self.START
        if self.app.FULLSCREEN: Window.fullscreen = True
        Window.bind(on_key_down=self._on_key_down)

    def _on_key_down(self, window, keycode, scancode, codepoint, modifiers):
        if keycode == 27:  # ESC: kiosk keyboard back/home, never quit Kivy.
            if self.current != self.START:
                self.app.transition_to(self.START)
            return True
        if keycode in (13, 32):  # ENTER / SPACE: activate the screen's primary button.
            action = getattr(self.current_screen, 'on_keyboard_action', None)
            return bool(action and action())
        return False

class BackgroundScreen(Screen):
    def __init__(self, bg='./assets/backgrounds/bg_default.jpeg', **kwargs):
        super(BackgroundScreen, self).__init__(**kwargs)
        with self.canvas.before:
            self.background_image = Rectangle(pos=self.pos, size=self.size, source=bg)

    def on_pos(self, *args):
        self.background_image.pos = self.pos

    def on_size(self, *args):
        self.background_image.size = self.size

    def on_update(self, kwargs={}):
        pass

class ColorScreen(Screen):
    def __init__(self, **kwargs):
        super(ColorScreen, self).__init__(**kwargs)
        with self.canvas.before:
            # Border
            if BORDER_THINKNESS > 0:
                Color(*BORDER_COLOR)
                self.border_rect = Rectangle(pos=self.pos, size=self.size)
            else:
                self.border_rect = None

            # Background
            Color(*BACKGROUND_COLOR)
            self.background_rect = Rectangle(pos=(self.x + BORDER_THINKNESS, self.y + BORDER_THINKNESS), size=(self.width - BORDER_THINKNESS*2, self.height - BORDER_THINKNESS*2))

    def on_pos(self, *args):
        if self.border_rect: self.border_rect.pos = self.pos
        self.background_rect.pos = (self.x + BORDER_THINKNESS, self.y + BORDER_THINKNESS)

    def on_size(self, *args):
        if self.border_rect: self.border_rect.size = self.size
        self.background_rect.size = (self.width - BORDER_THINKNESS*2, self.height - BORDER_THINKNESS*2)

    def on_update(self, kwargs={}):
        pass

class StartScreen(BackgroundScreen):
    """
    +-----------------+
    |                 |
    | Press to begin  |
    |                 |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('StartScreen: __init__().')
        super(StartScreen, self).__init__(bg='./assets/backgrounds/bg_waiting.jpeg', **kwargs)

        self.app = app

        overlay_layout = LayoutButton()

        start = BreezyBorderedLabel(
            text='PHOTO BOOTH',
            border_color=(1,1,1,1),
            border_width=Window.height * 0.006,
            size_hint=(0.7, 0.2),
            padding=(Window.height * 0.033, Window.height * 0.033, Window.height * 0.033, Window.height * 0.033),
            pos_hint={'x': 0.15, 'y': 0.4},
        )
        # BreezyBorderedLabel.on_size() recomputes font_size from width — no wh_bind needed
        overlay_layout.add_widget(start)
        self.start_label = start

        # Touch icon
        icon = ResizeLabel(
            size_hint=(0.15, 0.2),
            pos_hint={'x': 0.42, 'y': 0.1},
            font_name=ICON_TTF,
            text=ICON_TOUCH,
            wh_fraction=0.22,
        )
        overlay_layout.add_widget(icon)

        # Version
        version = Label(
            text='Version 1.2',
            font_size=TINY_FONT(),
            halign='left',
            valign='middle',
            size_hint=(0.1, 0.05),
            pos_hint={'x': 0.9, 'y': 0.95},
        )
        wh_bind(version, 'font_size', TINY_FONT)
        overlay_layout.add_widget(version)

        overlay_layout.bind(on_release=self.on_click)

        self.add_widget(overlay_layout)

    def on_entry(self, kwargs={}):
        Logger.info('StartScreen: on_entry().')
        if self.app.ringled:
            self.app.ringled.start_rainbow()
        self._purge_when_idle()

    def _purge_when_idle(self, *args):
        if self.app.get_current_screen_name() != ScreenMgr.START:
            return
        if self.app.has_pending_photo_tasks() or self.app.has_background_processes():
            Clock.schedule_once(self._purge_when_idle, 0.5)
        else:
            self.app.clear_pending_photo_error()
            self.app.purge_tmp()
            if self.app.SHARE:
                QRCodePopup.preload_async()

    def on_exit(self, kwargs={}):
        Logger.info('StartScreen: on_exit().')
        if self.app.ringled:
            self.app.ringled.clear()

    def on_click(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('StartScreen: on_click().')
        self.app.transition_to(ScreenMgr.SELECT_FORMAT)

    def on_keyboard_action(self):
        Logger.info('StartScreen: on_keyboard_action().')
        self.app.transition_to(ScreenMgr.SELECT_FORMAT)
        return True

class SelectFormatScreen(ColorScreen):
    """
    +-----------------+
    |  Select format  |
    | Choose your fmt |
    |  [card] [card]  |
    |  [card] [card]  |
    +-----------------+
    """
    # Minimum and maximum card dimensions as window fractions (evaluated at layout time)
    @property
    def MIN_CARD_WIDTH(self):  return Window.width * 0.10
    @property
    def MIN_CARD_HEIGHT(self): return Window.height * 0.20
    @property
    def MAX_CARD_WIDTH(self):  return Window.width * 0.40
    @property
    def MAX_CARD_HEIGHT(self): return Window.height * 0.92

    def __init__(self, app, **kwargs):
        Logger.info('SelectFormatScreen: __init__().')
        super(SelectFormatScreen, self).__init__(**kwargs)
        self.app = app

        # Format cards container (scrollable if needed)
        from kivy.uix.gridlayout import GridLayout
        from kivy.uix.scrollview import ScrollView
        
        scroll_view = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            do_scroll_y=True,
        )
        
        # Grid for format cards (centered)
        self.cards_grid = GridLayout(
            cols=3,
            spacing=Window.height * 0.033,
            padding=Window.height * 0.022,
            size_hint=(None, None),
        )
        self.cards_grid.bind(minimum_height=self.cards_grid.setter('height'))
        self.cards_grid.bind(minimum_width=self.cards_grid.setter('width'))
        
        # Center the grid within the scroll view
        grid_container = AnchorLayout(
            anchor_x='center',
            anchor_y='center',
        )
        grid_container.add_widget(self.cards_grid)
        scroll_view.add_widget(grid_container)

        # Build format cards
        self.format_cards = []
        max_cards = min(3, len(self.app.print_formats))
        for format_idx in range(max_cards):
            card = self._create_format_card(format_idx)
            self.cards_grid.add_widget(card)
            self.format_cards.append(card)

        self.add_widget(scroll_view)
        
        # Bind to window resize events
        Window.bind(on_resize=self._on_window_resize)
        
        # Initial card size calculation
        self._update_card_sizes()

    def _calculate_card_size(self):
        """Calculate card size and column count that fills the screen optimally for any aspect ratio."""
        padding = Window.height * 0.022
        spacing = Window.height * 0.033
        border = 2 * BORDER_THINKNESS
        n_cards = len(self.format_cards)
        aspect = Window.width / Window.height  # <1 portrait, ~1 square, >1 landscape

        # Choose columns: 1 in portrait, 2 in square, 3 in landscape
        if aspect < 0.75:
            cols = 1
        elif aspect < 1.2:
            cols = 2
        else:
            cols = 3
        cols = min(cols, n_cards)

        # Width from horizontal space
        n_spacings = max(cols - 1, 0)
        available_width = Window.width - (2 * padding) - (n_spacings * spacing) - border
        width_from_w = available_width / cols

        # Width derived from vertical space (aspect ratio 1:1.5)
        available_height = Window.height - (2 * padding) - border
        width_from_h = available_height / 1.5

        card_width = max(self.MIN_CARD_WIDTH, min(self.MAX_CARD_WIDTH, min(width_from_w, width_from_h)))
        card_height = max(self.MIN_CARD_HEIGHT, min(self.MAX_CARD_HEIGHT, card_width * 1.5))

        return (card_width, card_height, cols)

    def _update_card_sizes(self):
        """Update all card sizes based on current window size."""
        card_width, card_height, cols = self._calculate_card_size()

        self.cards_grid.cols = cols
        self.cards_grid.spacing = Window.height * 0.033
        self.cards_grid.row_default_height = card_height
        self.cards_grid.row_force_default = True

        for card in self.format_cards:
            card.size = (card_width, card_height)
    
    def _on_window_resize(self, instance, width, height):
        """Handle window resize events."""
        self._update_card_sizes()

    def _create_format_card(self, format_idx):
        """Create a card for a specific format."""
        format_template = self.app.print_formats[format_idx]
        preview_path = format_template.get_preview()
        
        # Create clickable card combining ButtonBehavior and BoxLayout
        from kivy.graphics import RoundedRectangle
        
        class ClickableCard(FeedbackButtonBehavior, BoxLayout):
            pass
        
        # Initial size will be updated by _update_card_sizes
        card = ClickableCard(
            orientation='vertical',
            size_hint=(None, None),
            size=(self.MIN_CARD_WIDTH, self.MIN_CARD_HEIGHT),
            padding=Window.height * 0.022,
            spacing=Window.height * 0.011,
        )
        
        # Draw rounded card background using canvas
        with card.canvas.before:
            Color(*hex_to_rgba('#3d4f5c'))
            card_bg = RoundedRectangle(
                pos=card.pos,
                size=card.size,
                radius=[Window.height * 0.022,]
            )
        
        # Bind to update background when card size/pos changes
        def update_card_bg(instance, value):
            card_bg.pos = instance.pos
            card_bg.size = instance.size
        card.bind(pos=update_card_bg, size=update_card_bg)
        
        # Preview container with rounded corners and image
        preview_container = AnchorLayout(
            size_hint=(1, 0.75),
            anchor_x='center',
            anchor_y='center',
            padding=Window.height * 0.022,
        )
        
        # Draw rounded preview background
        with preview_container.canvas.before:
            Color(*hex_to_rgba('#4a5c6a'))
            preview_bg = RoundedRectangle(
                pos=preview_container.pos,
                size=preview_container.size,
                radius=[Window.height * 0.017,]
            )
        
        # Bind to update preview background
        def update_preview_bg(instance, value):
            preview_bg.pos = instance.pos
            preview_bg.size = instance.size
        preview_container.bind(pos=update_preview_bg, size=update_preview_bg)
        
        preview_image = Image(
            source=preview_path,
            size_hint=(None, None),
            fit_mode='contain',
        )
        
        # Update image size to fit within container
        def update_image_size(instance, *args):
            if preview_container.width <= Window.height * 0.044 or preview_container.height <= Window.height * 0.044:
                return
            max_width = preview_container.width - Window.height * 0.044
            max_height = preview_container.height - Window.height * 0.044
            preview_image.size = (max_width, max_height)
        
        preview_container.bind(size=update_image_size)
        preview_image.bind(texture=update_image_size)
        
        preview_container.add_widget(preview_image)
        card.add_widget(preview_container)
        
        # Format name
        name_label = Label(
            text=format_template.get_name(),
            size_hint=(1, 0.15),
            font_size=SMALL_FONT(),
            halign='center',
            valign='middle',
            bold=True,
        )
        wh_bind(name_label, 'font_size', SMALL_FONT)
        name_label.bind(size=name_label.setter('text_size'))
        card.add_widget(name_label)
        
        # Number of photos
        num_photos = format_template.get_photos_required()
        photos_label = ResizeLabel(
            text=f"{num_photos} photo{'s' if num_photos > 1 else ''}",
            size_hint=(1, 0.1),
            wh_fraction=0.018,
            halign='center',
            valign='middle',
        )
        card.add_widget(photos_label)
        
        # Bind click event
        card.format_idx = format_idx
        card.bind(on_release=self.on_format_selected)
        
        return card
    
    def on_entry(self, kwargs={}):
        Logger.info('SelectFormatScreen: on_entry().')
        # OPTIMIZED: Previews are now cached in templates, no need to reload
        # Previously: reloaded all previews on every entry (slow)
        # Now: previews are generated once and cached in TemplateCollage
        if self.app.ringled:
            self.app.ringled.start_rainbow()

    def on_exit(self, kwargs={}):
        Logger.info('SelectFormatScreen: on_exit().')
        if self.app.ringled:
            self.app.ringled.clear()

    def on_format_selected(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        format_idx = obj.format_idx
        Logger.info(f'SelectFormatScreen: on_format_selected({format_idx}).')
        self.app.transition_to(ScreenMgr.COUNTDOWN, shot=0, format=format_idx)

class ErrorScreen(ColorScreen):
    """
    +-----------------+
    |  Error occured  |
    |    Continue     |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('ErrorScreen: __init__().')
        super(ErrorScreen, self).__init__(**kwargs)

        self.app = app
        self._show_continue = True
        self._show_restart = False

        layout = BoxLayout(orientation='vertical', padding=(0, dp(12), 0, dp(24)), spacing=dp(12))

        # Display error icon
        self.icon = ResizeLabel(
            size_hint=(0.4, 0.32),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            font_name=ICON_TTF,
            text=ICON_ERROR,
            wh_fraction=0.22,
        )
        layout.add_widget(self.icon)

        self.title = Label(
            size_hint=(1, 0.10),
            text='Error',
            font_size=LARGE_FONT(),
            bold=True,
            halign='center',
            valign='middle',
        )
        wh_bind(self.title, 'font_size', LARGE_FONT)
        self.title.bind(size=self.title.setter('text_size'))
        layout.add_widget(self.title)

        self.message = Label(
            size_hint=(1, 0.24),
            text='An error occurred.',
            font_size=SMALL_FONT(),
            halign='center',
            valign='middle',
        )
        wh_bind(self.message, 'font_size', SMALL_FONT)
        self.message.bind(size=self.message.setter('text_size'))
        layout.add_widget(self.message)

        self.actions = BoxLayout(
            orientation='horizontal',
            spacing=dp(16),
            size_hint=(1, 0.12),
            padding=(Window.width * 0.18, 0, Window.width * 0.18, 0),
        )

        self.btn_restart = RoundedButton(
            text='RESTART',
            size_hint=(1, 1),
            background_color=HOME_COLOR,
            font_size=SMALL_FONT(),
            bold=True,
            halign='center',
            valign='middle',
        )
        wh_bind(self.btn_restart, 'font_size', SMALL_FONT)
        self.btn_restart.bind(size=self.btn_restart.setter('text_size'))
        self.btn_restart.bind(on_release=self.on_restart)
        self.actions.add_widget(self.btn_restart)

        self.btn_continue = RoundedButton(
            text='CONTINUE',
            size_hint=(1, 1),
            background_color=CONFIRM_COLOR,
            font_size=SMALL_FONT(),
            bold=True,
            halign='center',
            valign='middle',
        )
        wh_bind(self.btn_continue, 'font_size', SMALL_FONT)
        self.btn_continue.bind(size=self.btn_continue.setter('text_size'))
        self.btn_continue.bind(on_release=self.on_click)
        self.actions.add_widget(self.btn_continue)

        layout.add_widget(self.actions)

        self.add_widget(layout)

    def on_entry(self, kwargs={}):
        Logger.info('ErrorScreen: on_entry().')
        self.title.text = 'Error'
        self.icon.text = str(kwargs.get('error', ICON_ERROR))
        self.message.text = str(kwargs.get('message', 'An error occurred.'))
        self._show_continue = bool(kwargs.get('show_continue', True))
        self._show_restart = bool(kwargs.get('show_restart', False))
        self.btn_continue.text = str(kwargs.get('continue_text', 'CONTINUE'))
        self.btn_restart.text = str(kwargs.get('restart_text', 'RESTART'))
        self.btn_continue.opacity = 1 if self._show_continue else 0
        self.btn_continue.disabled = not self._show_continue
        self.btn_restart.opacity = 1 if self._show_restart else 0
        self.btn_restart.disabled = not self._show_restart
        self.actions.opacity = 1 if (self._show_continue or self._show_restart) else 0

    def on_exit(self, kwargs={}):
        Logger.info('ErrorScreen: on_exit().')

    def on_click(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ErrorScreen: on_click().')
        self.app.transition_to(ScreenMgr.START)

    def on_restart(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ErrorScreen: on_restart().')
        self.app.request_restart()

    def on_keyboard_action(self):
        Logger.info('ErrorScreen: on_keyboard_action().')
        if self._show_continue:
            self.app.transition_to(ScreenMgr.START)
            return True
        if self._show_restart:
            self.app.request_restart()
            return True
        return False

class CountdownScreen(ColorScreen):
    """
    +-----------------+
    |                 |
    |        5        |
    |                 |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('CountdownScreen: __init__().')
        super(CountdownScreen, self).__init__(**kwargs)

        self.app = app
        self._current_shot = 0
        self._current_format = 0
        self._timer_active = False
        self._home_timeout_clock = None
        self._home_progress_clock = None

        self.time_remaining = self.app.COUNTDOWN
        self.total_countdown = self.app.COUNTDOWN

        # Display camera preview
        self.layout = AnchorLayout(padding=BORDER_THINKNESS, anchor_x='center', anchor_y='center')
        
        self.camera = KivyCamera(
            app=self.app,
            fps=self.app.devices.get_preview_fps(),
            blur=self.app.BLUR_CAMERA,
            blur_refresh_frames=self.app.PREVIEW_BLUR_REFRESH_FRAMES,
            fit_mode='contain',
        )
        self.layout.add_widget(self.camera)
        
        # Create overlay layout for buttons (on top of camera)
        self.overlay_layout = FloatLayout()
        self.layout.add_widget(self.overlay_layout)

        # Display countdown with circular progress
        self.circular_counter = CircularProgressCounter(
            size_hint=(None, None),
            size=(min(Window.size) * 0.45, min(Window.size) * 0.45),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            circle_size=min(Window.size) * 0.38,
            line_width=min(Window.size) * 0.01,
            progress_color=BORDER_COLOR
        )

        # Declare color background
        self.color_background = BackgroundBoxLayout(background_color=(1,1,1,1))

        # Display loading
        self.loading_layout = BoxLayout(orientation='vertical')
        icon = ResizeLabel(
            size_hint=(0.4, 0.4),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            font_name=ICON_TTF,
            text=ICON_PROCESSING,
            wh_fraction=0.22,
        )
        self.loading_layout.add_widget(icon)

        loading = RotatingLabel(
            size_hint=(0.1, 0.1),
            pos_hint={'center_x': 0.5, 'y': 0.3},
            font_name=ICON_TTF,
            text=ICON_LOADING,
            wh_fraction=0.055,
        )
        self.loading_layout.add_widget(loading)

        # Home button (visible only when timer is not active) - top left
        self.btn_home = make_icon_button(ICON_HOME,
            size=0.14,
            pos_hint={'x': 0.05, 'top': 0.95},
            font=ICON_TTF,
            font_size_fraction=0.07,
            bgcolor=HOME_COLOR,
            progress=True,
            progress_color=HOME_PROGRESS_COLOR,
            progress_line_width_fraction=0.028,
            on_release=self.home_event
        )

        # Trigger/Cancel button - center bottom as round icon button
        self.btn_trigger = make_icon_button(ICON_TRIGGER,
            size=0.14,
            pos_hint={'center_x': 0.5, 'y': 0.05},
            font=ICON_TTF,
            font_size_fraction=0.07,
            bgcolor=CONFIRM_COLOR,
            on_release=self.trigger_event
        )

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('CountdownScreen: on_entry().')
        self.time_remaining = self.app.COUNTDOWN
        self.total_countdown = self.app.COUNTDOWN
        self._timer_active = False
        self._current_shot = kwargs.get('shot') if 'shot' in kwargs else 0
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        aspect_ratio = self.app.get_format_aspect_ratio(self._current_format)
        self.camera.start(aspect_ratio)
        
        # Reset button icon and color (access child button from parent layout)
        for child in self.btn_trigger.children:
            if isinstance(child, LabelRoundButton):
                child.text = ICON_TRIGGER
                child.background_color = CONFIRM_COLOR
                break
        
        # Show home button and trigger button, hide circular counter
        if not self.btn_home.parent:
            self.overlay_layout.add_widget(self.btn_home)
        if not self.btn_trigger.parent:
            self.overlay_layout.add_widget(self.btn_trigger)
        if self.circular_counter.parent:
            self.overlay_layout.remove_widget(self.circular_counter)
        self._start_home_timeout()
        
        self._clock = None
        self._clock_progress = None
        self._clock_trigger = None

    def on_exit(self, kwargs={}):
        Logger.info('CountdownScreen: on_exit().')
        self.camera.opacity = 1
        if self._clock:
            Clock.unschedule(self._clock)
        if self._clock_progress:
            Clock.unschedule(self._clock_progress)
        if self._clock_trigger:
            Clock.unschedule(self._clock_trigger)
        self._stop_home_timeout()
        if self.app.ringled:
            self.app.ringled.clear()
        if self.loading_layout.parent:
            self.overlay_layout.remove_widget(self.loading_layout)
        if self.btn_home.parent:
            self.overlay_layout.remove_widget(self.btn_home)
        if self.btn_trigger.parent:
            self.overlay_layout.remove_widget(self.btn_trigger)
        self.camera.stop()

    def timer_progress(self, dt):
        """Update progress bar smoothly every 0.05 seconds"""
        elapsed_time = Clock.get_boottime() - self.start_time
        remaining_progress = max(0, 1.0 - (elapsed_time / self.total_countdown))
        self.circular_counter.set_progress(remaining_progress)

    def _start_home_timeout(self):
        self._stop_home_timeout()
        self._home_timeout_started_at = Clock.get_boottime()
        self.btn_home.progress = 1.0
        self.btn_home.show_progress = True
        self._home_timeout_clock = Clock.schedule_once(self.home_timeout_event, COUNTDOWN_HOME_TIMEOUT_SECONDS)
        self._home_progress_clock = Clock.schedule_interval(self._update_home_progress, 1/30.0)

    def _stop_home_timeout(self):
        if self._home_timeout_clock:
            Clock.unschedule(self._home_timeout_clock)
            self._home_timeout_clock = None
        if self._home_progress_clock:
            Clock.unschedule(self._home_progress_clock)
            self._home_progress_clock = None
        self.btn_home.progress = 1.0
        self.btn_home.show_progress = False

    def _update_home_progress(self, dt):
        elapsed = Clock.get_boottime() - self._home_timeout_started_at
        self.btn_home.progress = max(0, 1.0 - (elapsed / COUNTDOWN_HOME_TIMEOUT_SECONDS))

    def home_timeout_event(self, obj):
        Logger.info('CountdownScreen: home_timeout_event().')
        self._stop_home_timeout()
        self.app.transition_to(ScreenMgr.START)

    def timer_event(self, obj):
        Logger.info('CountdownScreen: timer_event(%s)', obj)
        
        # Check if timer is still active (not cancelled)
        if not self._timer_active:
            Logger.info('CountdownScreen: timer_event cancelled.')
            return
        
        self.time_remaining -= 1
        if self.time_remaining:
            self.circular_counter.set_text(str(self.time_remaining))
            self._clock = Clock.schedule_once(self.timer_event, 1)
        else:
            # Stop progressive update
            if self._clock_progress:
                Clock.unschedule(self._clock_progress)
                self._clock_progress = None
            self.circular_counter.set_progress(0)
            
            # Trigger shot
            try:
                # Make screen blink
                self.layout.add_widget(self.color_background)
                self.app.trigger_shot(self._current_shot, self._current_format)
                self._clock_trigger = Clock.schedule_once(self.timer_trigger, 1.2)
                Clock.schedule_once(self.timer_bg, 0.2)

                # Display loading
                self.overlay_layout.remove_widget(self.circular_counter)
                if self.btn_trigger.parent:
                    self.overlay_layout.remove_widget(self.btn_trigger)
                self.overlay_layout.add_widget(self.loading_layout)
            except:
                return self.app.transition_to(ScreenMgr.ERROR, message='Unable to start photo capture.')

    def timer_bg(self, obj):
        self.camera.opacity = 0
        # Remove flash background
        self.layout.remove_widget(self.color_background)

    def timer_trigger(self, obj):
        if not(self.app.is_shot_completed(self._current_shot)):
            if self.app.has_process_timed_out('shot', SHOT_TIMEOUT_SECONDS):
                Logger.error('CountdownScreen: capture timed out after countdown.')
                if hasattr(self.app, 'recover_devices_and_return_home'):
                    self.app.recover_devices_and_return_home(reason='capture_timeout')
                else:
                    self.app.transition_to(ScreenMgr.ERROR, message='Photo capture took too long.')
            else:
                # Retry after 1sec
                self._clock_trigger = Clock.schedule_once(self.timer_trigger, 1)
        elif self.app.has_process_failed('shot'):
            Logger.error('CountdownScreen: capture failed after countdown.')
            error_details = self.app.get_process_error('shot')
            if error_details:
                Logger.error(error_details)
            if hasattr(self.app, 'recover_devices_and_return_home'):
                self.app.recover_devices_and_return_home(reason='capture_failure')
            else:
                self.app.transition_to(ScreenMgr.ERROR, message='Photo capture failed.')
        else:
            # Display photo for validation
            self.app.transition_to(ScreenMgr.CONFIRM_CAPTURE, shot=self._current_shot, format=self._current_format)

    def trigger_event(self, obj):
        if obj is not None and not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('CountdownScreen: trigger_event().')
        
        if not self._timer_active:
            # Start the countdown
            self._timer_active = True
            self.start_countdown()
        else:
            # Cancel the countdown
            self._timer_active = False
            self.cancel_countdown()

    def on_keyboard_action(self):
        self.trigger_event(None)
        return True

    def start_countdown(self):
        Logger.info('CountdownScreen: start_countdown().')
        self._stop_home_timeout()

        # Hide home button
        if self.btn_home.parent:
            self.overlay_layout.remove_widget(self.btn_home)
        
        # Show circular counter
        if not self.circular_counter.parent:
            self.overlay_layout.add_widget(self.circular_counter)
        
        # Update button icon and color (access child button from parent layout)
        for child in self.btn_trigger.children:
            if isinstance(child, LabelRoundButton):
                child.text = ICON_CANCEL
                child.background_color = CANCEL_COLOR
                break
        
        # Reset timer
        self.time_remaining = self.app.COUNTDOWN
        self.total_countdown = self.app.COUNTDOWN
        self.start_time = Clock.get_boottime()
        self.circular_counter.set_text(str(self.time_remaining))
        self.circular_counter.set_progress(1.0)
        
        # Start countdown
        self._clock = Clock.schedule_once(self.timer_event, 1)
        self._clock_progress = Clock.schedule_interval(self.timer_progress, 1/30.0)
        if self.app.ringled:
            self.app.ringled.start_countdown(self.time_remaining)

    def cancel_countdown(self):
        Logger.info('CountdownScreen: cancel_countdown().')
        # Stop timers
        if self._clock:
            Clock.unschedule(self._clock)
            self._clock = None
        if self._clock_progress:
            Clock.unschedule(self._clock_progress)
            self._clock_progress = None
        
        # Hide circular counter
        if self.circular_counter.parent:
            self.overlay_layout.remove_widget(self.circular_counter)
        
        # Show home button again
        if not self.btn_home.parent:
            self.overlay_layout.add_widget(self.btn_home)
        self._start_home_timeout()
        
        # Update button icon and color (access child button from parent layout)
        for child in self.btn_trigger.children:
            if isinstance(child, LabelRoundButton):
                child.text = ICON_TRIGGER
                child.background_color = CONFIRM_COLOR
                break
        
        # Clear LED
        if self.app.ringled:
            self.app.ringled.clear()

    def home_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('CountdownScreen: home_event().')
        self._stop_home_timeout()
        self.app.transition_to(ScreenMgr.START)

class ConfirmCaptureScreen(ColorScreen):
    """
    +-----------------+
    |       1/3       |
    |                 |
    | NO          YES |
    +-----------------+
    """
    # Filter definitions
    FILTERS = [
        {'name': 'Color', 'key': 'color'},
        {'name': 'B&W', 'key': 'bw'},
        {'name': 'B&W Glam', 'key': 'bwglam'},
        {'name': 'Sepia', 'key': 'sepia'},
        {'name': 'Glam', 'key': 'glam'},
        {'name': 'Vintage', 'key': 'vintage'},
        {'name': 'Warm Glow', 'key': 'warmglow'},
        {'name': 'Cool Tone', 'key': 'cooltone'},
        {'name': 'Soft Focus', 'key': 'softfocus'},
        {'name': 'Retro 70s', 'key': 'retro70s'},
        {'name': 'Pastel', 'key': 'pastel'},
        {'name': 'Polaroid', 'key': 'polaroid'},
    ]
    
    def __init__(self, app, **kwargs):
        Logger.info('ConfirmCaptureScreen: __init__().')
        super(ConfirmCaptureScreen, self).__init__(**kwargs)

        self.app = app
        self._current_shot = 0
        self._current_format = 1
        self._selected_filter = 'color'  # Default filter
        self._original_image = None  # Store original image
        self._home_timeout_clock = None
        self._home_progress_clock = None

        self.layout = AnchorLayout(padding=BORDER_THINKNESS, anchor_x='center', anchor_y='top')
        self.overlay_layout = FloatLayout()
        self.layout.add_widget(self.overlay_layout)

        # Display capture - always full size regardless of filters
        self.preview = BlurredImage(
            blur=self.app.BLUR_IMAGES,
            fit_mode='contain',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        self.overlay_layout.add_widget(self.preview)

        # Add counter
        self.counter_layout = BoxLayout(
            orientation='horizontal',
            spacing=Window.height * 0.022,
            size_hint=(0.25, 0.1),
            pos_hint={'x': 0.375, 'y':0.85},
        )
        self.icons = []
        for _ in range(0, self.app.get_shots_to_take(self._current_format)):
            icon = ResizeLabel(
                font_name=ICON_TTF,
                text=ICON_SHOT_TO_TAKE,
                wh_fraction=0.07,
            )
            self.counter_layout.add_widget(icon)
            self.icons.append(icon)
        self.overlay_layout.add_widget(self.counter_layout)

        # Filter cards container at bottom (always created in absolute position)
        from kivy.uix.scrollview import ScrollView
        
        # Outer container to center the scroll view - in absolute position
        self.filter_outer = AnchorLayout(
            size_hint=(1, 0.20),
            pos_hint={'x': 0, 'y': 0},
            anchor_x='center',
            anchor_y='center',
            opacity=1 if self.app.FILTERS else 0,
        )
        
        self.filter_scroll = ScrollView(
            size_hint=(None, 1),
            do_scroll_x=True,
            do_scroll_y=False,
        )
        
        self.filter_container = BoxLayout(
            orientation='horizontal',
            spacing=Window.height * 0.017,
            padding=(Window.height * 0.022, Window.height * 0.011, Window.height * 0.022, Window.height * 0.011),
            size_hint=(None, 1),
        )
        self.filter_container.bind(minimum_width=self.filter_container.setter('width'))
        
        # Update scroll view width based on container width
        def update_scroll_width(instance, value):
            # Limit scroll view width to avoid overlapping with confirm/cancel buttons
            # Buttons are 14% of width each, positioned at edges with 5% margin
            # So we need to leave space for: 5% + 14% on each side = 38% total
            # Plus some padding: use 70% of window width maximum
            max_available_width = Window.width * 0.70
            max_width = min(max_available_width, value)
            self.filter_scroll.width = max_width
        
        self.filter_container.bind(minimum_width=update_scroll_width)
        
        self.filter_scroll.add_widget(self.filter_container)
        self.filter_outer.add_widget(self.filter_scroll)
        self.overlay_layout.add_widget(self.filter_outer)
        
        # Create filter cards (even if filters are disabled, to maintain consistent layout)
        self.filter_cards = []
        if self.app.FILTERS:
            for filter_def in self.FILTERS:
                card = self._create_filter_card(filter_def)
                self.filter_container.add_widget(card)
                self.filter_cards.append(card)

        # Home button - top left
        self.btn_home = make_icon_button(ICON_HOME,
                             size=0.14,
                             pos_hint={'x': 0.05, 'top': 0.95},
                             font=ICON_TTF,
                             font_size_fraction=0.07,
                             bgcolor=HOME_COLOR,
                             progress=True,
                             progress_color=HOME_PROGRESS_COLOR,
                             progress_line_width_fraction=0.028,
                             on_release=self.home_event
                             )
        self.overlay_layout.add_widget(self.btn_home)

        # Cancel button - bottom left (always at same position)
        btn_cancel = make_icon_button(ICON_CANCEL,
                             size=0.14,
                             pos_hint={'x': 0.05, 'y': 0.05},
                             font=ICON_TTF,
                             font_size_fraction=0.07,
                             bgcolor=CANCEL_COLOR,
                             on_release=self.no_event
                             )
        self.overlay_layout.add_widget(btn_cancel)

        # Confirm button - bottom right (always at same position)
        btn_confirm = make_icon_button(ICON_CONFIRM,
                             size=0.14,
                             pos_hint={'right': 0.95, 'y': 0.05},
                             font=ICON_TTF,
                             font_size_fraction=0.07,
                             bgcolor=CONFIRM_COLOR,
                             on_release=self.keep_event,
                             )
        self.overlay_layout.add_widget(btn_confirm)

        self.add_widget(self.layout)

    def _create_filter_card(self, filter_def):
        """Create a card for a specific filter."""
        from kivy.graphics import RoundedRectangle
        
        class ClickableCard(FeedbackButtonBehavior, BoxLayout):
            pass
        
        card_size = Window.height * 0.18
        card = ClickableCard(
            orientation='vertical',
            size_hint=(None, None),
            size=(card_size, card_size),
            padding=Window.height * 0.009,
        )
        
        # Draw rounded card background
        with card.canvas.before:
            Color(*hex_to_rgba('#3d4f5c'))
            card_bg = RoundedRectangle(
                pos=card.pos,
                size=card.size,
                radius=[Window.height * 0.017,]
            )
            # Selection indicator (initially hidden)
            card.selection_color = Color(0, 0, 0, 0)
            card.selection_rect = RoundedRectangle(
                pos=card.pos,
                size=card.size,
                radius=[Window.height * 0.017,]
            )
        
        # Bind to update background when card size/pos changes
        def update_card_bg(instance, value):
            card_bg.pos = instance.pos
            card_bg.size = instance.size
            card.selection_rect.pos = instance.pos
            card.selection_rect.size = instance.size
        card.bind(pos=update_card_bg, size=update_card_bg)
        
        # Preview container for filter thumbnail
        preview_container = AnchorLayout(
            size_hint=(1, 1),
            anchor_x='center',
            anchor_y='center',
        )
        
        # Thumbnail image (will be generated on entry)
        card.thumbnail = Image(
            size_hint=(None, None),
            size=(card_size - Window.height * 0.011, card_size - Window.height * 0.011),
            fit_mode='contain',
        )
        
        preview_container.add_widget(card.thumbnail)
        card.add_widget(preview_container)
        
        # Store filter info
        card.filter_key = filter_def['key']
        card.bind(on_release=self.on_filter_selected)
        
        return card
    
    def _apply_filter(self, img, filter_key):
        """Apply a filter to an image using OpenCV."""
        if filter_key == 'color':
            return img
        
        elif filter_key == 'bw':
            # Black and white
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            
        elif filter_key == 'bwglam':
            # Black and white with soft glam effect - enhanced contrast and subtle smoothing
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            smoothed = cv2.bilateralFilter(enhanced, d=5, sigmaColor=50, sigmaSpace=50)
            return cv2.cvtColor(smoothed, cv2.COLOR_GRAY2BGR)
        
        elif filter_key == 'sepia':
            # Sepia tone
            sepia_filter = np.array([[0.272, 0.534, 0.131],
                                    [0.349, 0.686, 0.168],
                                    [0.393, 0.769, 0.189]])
            sepia_img = cv2.transform(img, sepia_filter)
            return np.clip(sepia_img, 0, 255).astype(np.uint8)
        
        elif filter_key == 'glam':
            # Glam: increase contrast and saturation
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = hsv[:, :, 1] * 1.3  # Increase saturation
            hsv[:, :, 2] = hsv[:, :, 2] * 1.1  # Increase brightness
            hsv = np.clip(hsv, 0, 255).astype(np.uint8)
            result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            # Increase contrast
            alpha = 1.2  # Contrast control
            beta = 10    # Brightness control
            return cv2.convertScaleAbs(result, alpha=alpha, beta=beta)
        
        elif filter_key == 'vintage':
            # Vintage: reduced saturation, warm tones, slight vignette
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = hsv[:, :, 1] * 0.7  # Reduce saturation
            hsv = np.clip(hsv, 0, 255).astype(np.uint8)
            result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            # Add warm tone
            result[:, :, 0] = np.clip(result[:, :, 0] * 0.9, 0, 255)  # Reduce blue
            result[:, :, 2] = np.clip(result[:, :, 2] * 1.1, 0, 255)  # Increase red
            return result.astype(np.uint8)
        
        elif filter_key == 'warmglow':
            # Warm Glow: golden hour effect with orange/golden tones
            # Increase red and reduce blue for warmth
            result = img.copy().astype(np.float32)
            result[:, :, 0] = np.clip(result[:, :, 0] * 0.85, 0, 255)  # Reduce blue
            result[:, :, 1] = np.clip(result[:, :, 1] * 1.05, 0, 255)  # Slight green boost
            result[:, :, 2] = np.clip(result[:, :, 2] * 1.15, 0, 255)  # Increase red
            # Add slight brightness and saturation
            hsv = cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.2, 0, 255)  # Increase saturation
            hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.05, 0, 255)  # Slight brightness boost
            return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
        elif filter_key == 'cooltone':
            # Cool Tone: modern cinematic look with blue/cyan emphasis
            # Increase blue and cyan, reduce red
            result = img.copy().astype(np.float32)
            result[:, :, 0] = np.clip(result[:, :, 0] * 1.15, 0, 255)  # Increase blue
            result[:, :, 1] = np.clip(result[:, :, 1] * 1.05, 0, 255)  # Slight green boost for cyan
            result[:, :, 2] = np.clip(result[:, :, 2] * 0.9, 0, 255)   # Reduce red
            # Enhance contrast slightly
            alpha = 1.1  # Contrast
            beta = -5    # Brightness (slightly darker)
            result = cv2.convertScaleAbs(result, alpha=alpha, beta=beta)
            return result
        
        elif filter_key == 'softfocus':
            # Soft Focus: dreamy romantic effect with subtle blur
            # Apply bilateral filter for skin smoothing while preserving edges
            smoothed = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
            # Blend original with smoothed version for soft focus effect
            alpha = 0.6  # Weight of smoothed image
            result = cv2.addWeighted(smoothed, alpha, img, 1 - alpha, 0)
            # Add slight glow by blending with a blurred version
            blurred = cv2.GaussianBlur(result, (21, 21), 0)
            glow = cv2.addWeighted(result, 0.85, blurred, 0.15, 0)
            # Slightly increase brightness for dreamy effect
            hsv = cv2.cvtColor(glow, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.08, 0, 255)
            return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
        elif filter_key == 'retro70s':
            # Retro 70s: nostalgic look with yellow/orange tones and reduced contrast
            # Reduce contrast first
            alpha = 0.85  # Reduced contrast
            beta = 15     # Increased brightness
            faded = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
            # Add yellow/orange cast
            result = faded.copy().astype(np.float32)
            result[:, :, 0] = np.clip(result[:, :, 0] * 0.88, 0, 255)  # Reduce blue
            result[:, :, 1] = np.clip(result[:, :, 1] * 1.08, 0, 255)  # Increase green
            result[:, :, 2] = np.clip(result[:, :, 2] * 1.12, 0, 255)  # Increase red
            # Reduce saturation slightly for vintage feel
            hsv = cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 0.85, 0, 255)
            return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
        elif filter_key == 'pastel':
            # Pastel Dream: soft pastel colors with increased brightness
            # Increase brightness significantly
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.25, 0, 255)  # Increase brightness
            # Reduce saturation for pastel effect
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 0.5, 0, 255)   # Significantly reduce saturation
            result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
            # Add slight white overlay for pastel wash
            white_overlay = np.ones_like(result) * 255
            result = cv2.addWeighted(result, 0.75, white_overlay.astype(np.uint8), 0.25, 0)
            return result
        
        elif filter_key == 'polaroid':
            # Polaroid: vintage instant camera look with characteristic color shift
            # Slight color shift and reduced contrast like old Polaroid photos
            alpha = 0.9   # Slightly reduced contrast
            beta = 10     # Slight brightness boost
            faded = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
            # Add characteristic Polaroid color cast (slightly cool with faded colors)
            result = faded.copy().astype(np.float32)
            result[:, :, 0] = np.clip(result[:, :, 0] * 1.05, 0, 255)  # Slight blue boost
            result[:, :, 1] = np.clip(result[:, :, 1] * 0.98, 0, 255)  # Slight green reduction
            result[:, :, 2] = np.clip(result[:, :, 2] * 1.02, 0, 255)  # Slight red boost
            # Reduce saturation for faded look
            hsv = cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 0.75, 0, 255)
            result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
            # Add slight vignette for authentic Polaroid look
            rows, cols = result.shape[:2]
            kernel_x = cv2.getGaussianKernel(cols, cols/2.5)
            kernel_y = cv2.getGaussianKernel(rows, rows/2.5)
            kernel = kernel_y * kernel_x.T
            mask = kernel / kernel.max()
            mask = np.dstack([mask] * 3)
            vignette = result * mask
            result = cv2.addWeighted(result, 0.3, vignette.astype(np.uint8), 0.7, 0)
            return result
        
        return img
    
    def _generate_thumbnail(self, img, filter_key, size=None):
        """Generate a thumbnail with the filter applied."""
        if size is None:
            thumb = int(Window.height * 0.12)
            size = (thumb, thumb)
        # Resize image for thumbnail
        h, w = img.shape[:2]
        aspect = w / h
        if aspect > 1:
            new_w = size[0]
            new_h = int(size[0] / aspect)
        else:
            new_h = size[1]
            new_w = int(size[1] * aspect)
        
        thumbnail = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Apply filter
        filtered = self._apply_filter(thumbnail, filter_key)
        
        return filtered
    
    def _update_filter_thumbnails(self):
        """Generate thumbnails for all filters based on current image."""
        if self._original_image is None:
            return

        thumbnails = []
        for card in self.filter_cards:
            thumbnails.append(self._generate_thumbnail(self._original_image, card.filter_key))

        self._set_filter_thumbnails(thumbnails)

    def _set_filter_thumbnails(self, thumbnails):
        for card, thumbnail in zip(self.filter_cards, thumbnails):
            # Convert to texture
            thumbnail_flipped = cv2.flip(thumbnail, 0)
            texture = Texture.create(size=(thumbnail.shape[1], thumbnail.shape[0]), colorfmt='bgr')
            texture.blit_buffer(thumbnail_flipped.flatten(), colorfmt='bgr', bufferfmt='ubyte')
            card.thumbnail.texture = texture
    
    def _update_selection_indicator(self):
        """Update visual indicator for selected filter."""
        for card in self.filter_cards:
            if card.filter_key == self._selected_filter:
                # Show selection with border color
                card.selection_color.rgba = BORDER_COLOR
            else:
                # Hide selection
                card.selection_color.rgba = (0, 0, 0, 0)
    
    def on_filter_selected(self, obj):
        """Handle filter selection."""
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info(f'ConfirmCaptureScreen: on_filter_selected({obj.filter_key}).')
        
        self._selected_filter = obj.filter_key
        self._update_selection_indicator()
        
        # Apply filter to preview
        if self._original_image is not None:
            filtered_image = self._apply_filter(self._original_image.copy(), self._selected_filter)

            # Update preview directly in memory to avoid temp files.
            self.preview.set_image(filtered_image)

    def on_entry(self, kwargs={}):
        Logger.info('ConfirmCaptureScreen: on_entry().')
        self._current_shot = kwargs.get('shot') if 'shot' in kwargs else 0
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self._selected_filter = 'color'  # Reset to default filter
        self._original_image = None

        # Hide counter layout when only one photo is needed
        total_shots = self.app.get_shots_to_take(self._current_format)
        if total_shots == 1:
            if self.counter_layout.parent:
                self.overlay_layout.remove_widget(self.counter_layout)
        else:
            if not self.counter_layout.parent:
                self.overlay_layout.add_widget(self.counter_layout)
            for i in range(0, total_shots): self.icons[i].text = ICON_SHOT_TO_TAKE
            for i in range(0, self._current_shot + 1): self.icons[i].text = ICON_SHOT_TAKEN

        load_id = (self._current_shot, self._current_format)

        def load_images():
            shot, fmt = self._current_shot, self._current_format
            small_path = FileUtils.get_small_path(self.app.get_shot(shot))
            full_path = self.app.get_shot(shot)
            small_im = cv2.imread(small_path)
            full_im = cv2.imread(full_path) if self.app.FILTERS else None
            thumbnails = []
            if self.app.FILTERS and full_im is not None:
                thumbnails = [self._generate_thumbnail(full_im, card.filter_key) for card in self.filter_cards]

            def apply_on_main(dt):
                if (self._current_shot, self._current_format) != load_id:
                    return
                self._original_image = full_im
                if small_im is not None:
                    self.preview.set_image(small_im)
                else:
                    self.preview.filepath = small_path
                    self.preview.reload()
                if thumbnails:
                    self._set_filter_thumbnails(thumbnails)
                    self._update_selection_indicator()

            Clock.schedule_once(apply_on_main, 0)

        threading.Thread(target=load_images, daemon=True).start()
        self._start_home_timeout()

    def _save_selected_filter(self, shot, filter_key, original_image):
        filtered_image = self._apply_filter(original_image.copy(), filter_key)
        shot_path = self.app.get_shot(shot)
        FileUtils.write_image(shot_path, filtered_image)
        small_path = FileUtils.get_small_path(shot_path)
        small_filtered = cv2.resize(filtered_image, (0, 0), fx=0.3, fy=0.3)
        FileUtils.write_image(small_path, small_filtered)

    def on_exit(self, kwargs={}):
        Logger.info('ConfirmCaptureScreen: on_exit().')
        self._stop_home_timeout()

    def _start_home_timeout(self):
        self._stop_home_timeout()
        self._home_timeout_started_at = Clock.get_boottime()
        self.btn_home.progress = 1.0
        self._home_timeout_clock = Clock.schedule_once(self.timer_event, CONFIRM_CAPTURE_HOME_TIMEOUT_SECONDS)
        self._home_progress_clock = Clock.schedule_interval(self._update_home_progress, 1/30.0)

    def _stop_home_timeout(self):
        if self._home_timeout_clock:
            Clock.unschedule(self._home_timeout_clock)
            self._home_timeout_clock = None
        if self._home_progress_clock:
            Clock.unschedule(self._home_progress_clock)
            self._home_progress_clock = None

    def _update_home_progress(self, dt):
        elapsed = Clock.get_boottime() - self._home_timeout_started_at
        self.btn_home.progress = max(0, 1.0 - (elapsed / CONFIRM_CAPTURE_HOME_TIMEOUT_SECONDS))

    def keep_event(self, obj):
        if obj is not None and not isinstance(obj.last_touch, MouseMotionEvent): return
        self._stop_home_timeout()
        
        # Apply selected filter off the UI thread; Processing waits before building the collage.
        if self.app.FILTERS and self._selected_filter != 'color' and self._original_image is not None:
            self.app.start_photo_task(self._save_selected_filter, self._current_shot, self._selected_filter, self._original_image)
        
        if self._current_shot == self.app.get_shots_to_take(self._current_format) - 1:
            self.app.transition_to(ScreenMgr.PROCESSING, format=self._current_format)
        else:
            self.app.transition_to(ScreenMgr.COUNTDOWN, shot=self._current_shot + 1, format=self._current_format)

    def no_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        self._stop_home_timeout()
        self.app.transition_to(ScreenMgr.COUNTDOWN, shot=self._current_shot, format=self._current_format)

    def home_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        self._stop_home_timeout()
        self.app.transition_to(ScreenMgr.START)

    def timer_event(self, obj):
        Logger.info('ConfirmCaptureScreen: timer_event().')
        self._stop_home_timeout()
        self.app.transition_to(ScreenMgr.START)

    def on_keyboard_action(self):
        self.keep_event(None)
        return True

class ProcessingScreen(ColorScreen):
    """
    +-----------------+
    |                 |
    |   Processing    |
    |                 |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('ProcessingScreen: __init__().')
        super(ProcessingScreen, self).__init__(**kwargs)

        self.app = app
        self._current_format = 0

        layout = BoxLayout(orientation='vertical')

        # Display processing
        icon = ResizeLabel(
            size_hint=(0.4, 0.4),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            font_name=ICON_TTF,
            text=ICON_PROCESSING,
            wh_fraction=0.22,
        )
        layout.add_widget(icon)

        # Display loading spinner
        loading = RotatingLabel(
            size_hint=(0.1, 0.1),
            pos_hint={'center_x': 0.5, 'y': 0.3},
            font_name=ICON_TTF,
            text=ICON_LOADING,
            wh_fraction=0.055,
        )

        layout.add_widget(loading)
        self.add_widget(layout)

    def on_entry(self, kwargs={}):
        Logger.info('ProcessingScreen: on_entry().')
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self._clock = Clock.schedule_once(self.timer_event, 0.2)
        if self.app.ringled:
            self.app.ringled.start_rainbow()

        self._collage_started = False

    def on_exit(self, kwargs={}):
        Logger.info('ProcessingScreen: on_exit().')
        Clock.unschedule(self._clock)
        if self.app.ringled:
            self.app.ringled.clear()

    def timer_event(self, obj):
        Logger.info('ProcessingScreen: timer_event().')
        if self.app.has_pending_photo_tasks():
            self._clock = Clock.schedule_once(self.timer_event, 0.2)
            return

        if self.app.get_pending_photo_error():
            Logger.error('ProcessingScreen: photo preparation failed.')
            Logger.error(self.app.get_pending_photo_error())
            self.app.transition_to(ScreenMgr.ERROR, message='Photo processing failed.')
            return

        if not self._collage_started:
            self._collage_started = True
            self.app.trigger_collage(self._current_format)
            self._clock = Clock.schedule_once(self.timer_event, 0.2)
            return

        if not(self.app.is_collage_completed()):
            self._clock = Clock.schedule_once(self.timer_event, 0.5)
        elif self.app.has_process_failed('collage'):
            Logger.error('ProcessingScreen: collage generation failed.')
            error_details = self.app.get_process_error('collage')
            if error_details:
                Logger.error(error_details)
            self.app.transition_to(ScreenMgr.ERROR, message='Collage creation failed.')
        else:
            self.app.transition_to(ScreenMgr.REVIEW, format=self._current_format)

class PrintStatusPopup(FloatLayout):
    """Non-blocking print overlay; the underlying confirm screen keeps all actions available after closing."""

    def __init__(self, app, format_idx, on_dismiss=None, **kwargs):
        super(PrintStatusPopup, self).__init__(**kwargs)
        self.app = app
        self.format_idx = format_idx
        self.on_dismiss = on_dismiss
        self._clock = None
        self._close_scheduled = False
        self._started_at = time.monotonic()
        self._print_started = False
        self._print_task_id = None
        self._printer_wait_started_at = None
        self._timeout = getattr(self.app, 'PRINTER_WAIT_TIMEOUT', 45)

        with self.canvas.before:
            Color(0, 0, 0, 0.8)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        from kivy.graphics import RoundedRectangle

        self.card = BoxLayout(
            orientation='vertical',
            size_hint=(0.68, 0.55),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            padding=Window.height * 0.03,
            spacing=Window.height * 0.018,
        )
        with self.card.canvas.before:
            Color(1, 1, 1, 1)
            self.card_rect = RoundedRectangle(pos=self.card.pos, size=self.card.size, radius=[Window.height * 0.022])
        self.card.bind(pos=self._update_card, size=self._update_card)

        self.icon = ResizeLabel(
            text=ICON_PRINT,
            font_name=ICON_TTF,
            size_hint=(1, 0.28),
            wh_fraction=0.14,
            color=(0, 0, 0, 1),
            halign='center',
            valign='middle',
        )
        self.card.add_widget(self.icon)

        self.title = ResizeLabel(
            text='PRINTING',
            size_hint=(1, 0.15),
            wh_fraction=0.05,
            bold=True,
            color=(0, 0, 0, 1),
            halign='center',
            valign='middle',
        )
        self.card.add_widget(self.title)

        self.message = Label(
            text='Saving photo before printing...',
            size_hint=(1, 0.28),
            font_size=SMALL_FONT(),
            color=(0, 0, 0, 1),
            halign='center',
            valign='middle',
        )
        wh_bind(self.message, 'font_size', SMALL_FONT)
        self.message.bind(size=self.message.setter('text_size'))
        self.card.add_widget(self.message)

        self.btn_close = make_icon_text_button(
            icon=ICON_CONFIRM,
            text='OK',
            size_hint=(0.24, 0.13),
            pos_hint={'center_x': 0.5},
            icon_font=ICON_TTF,
            icon_font_size_fraction=0.055,
            text_font_size_fraction=0.035,
            bgcolor=CONFIRM_COLOR,
            on_release=self._close,
        )
        self.btn_close.opacity = 0
        self.btn_close.disabled = True
        self.card.add_widget(self.btn_close)

        self.add_widget(self.card)
        self._clock = Clock.schedule_once(self._tick, 0.2)

    def on_touch_down(self, touch):
        if self.card.collide_point(*touch.pos):
            return super(PrintStatusPopup, self).on_touch_down(touch)
        return True

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _update_card(self, instance, *args):
        self.card_rect.pos = instance.pos
        self.card_rect.size = instance.size

    def _set_done(self, title, message, error=False):
        self.title.text = title
        self.message.text = message
        self.icon.text = ICON_ERROR_PRINTING if error else ICON_SUCCESS
        self.btn_close.opacity = 1
        self.btn_close.disabled = False
        self._clock = None

    def _set_print_error(self, detail=None):
        message = 'Printing failed but the photo has been saved.'
        if detail:
            message = f'{message}\n{detail}'
        Logger.error('PrintStatusPopup: print failed: %s', detail or '-')
        self._set_done('PRINT FAILED', message, error=True)

    def _tick(self, obj):
        if self.app.has_pending_photo_tasks():
            self.message.text = 'Saving photo before printing...'
            self._clock = Clock.schedule_once(self._tick, 0.2)
            return

        pending_error = self.app.get_pending_photo_error()
        if pending_error:
            Logger.error('PrintStatusPopup: save before print failed.')
            Logger.error(pending_error)
            self._set_done('SAVE FAILED', 'The photo could not be saved, so printing was stopped.', error=True)
            return

        if time.monotonic() - self._started_at >= self._timeout:
            self._set_print_error('The print operation timed out.')
            return

        if not self._print_started:
            self.message.text = 'Sending photo to printer...'
            try:
                print_task_id = self.app.trigger_print(1, self.format_idx)
                if print_task_id is None:
                    raise RuntimeError('Printer did not return a task id')
                self._print_task_id = print_task_id
                self._print_started = True
                Logger.info('PrintStatusPopup: print started task=%s', self._print_task_id)
            except Exception as exc:
                self._set_print_error(str(exc))
                return

        if not self.app.has_printer():
            if self._printer_wait_started_at is None:
                self._printer_wait_started_at = time.monotonic()
                Logger.warning('PrintStatusPopup: printer unavailable, waiting for recovery')
            waited = time.monotonic() - self._printer_wait_started_at
            remaining = max(0, int(self._timeout - waited))
            self.message.text = f'Printer unavailable. Waiting for reconnection... {remaining}s'
            if waited >= self._timeout:
                self._set_print_error('The printer did not reconnect in time.')
                return
            self._clock = Clock.schedule_once(self._tick, 1)
            return

        if self._printer_wait_started_at is not None:
            Logger.info('PrintStatusPopup: printer recovered after %.2fs', time.monotonic() - self._printer_wait_started_at)
            self._printer_wait_started_at = None

        try:
            status = self.app.devices.get_print_status(self._print_task_id)
        except Exception as exc:
            self._set_print_error(str(exc))
            return

        Logger.info('PrintStatusPopup: print status task=%s status=%s', self._print_task_id, status)
        if status == 'done':
            self._set_done('PRINT SENT', 'The print job was sent to the printer.')
            Clock.schedule_once(lambda dt: self._close(None), 2)
        else:
            self.message.text = 'Printing...'
            self._clock = Clock.schedule_once(self._tick, 1)

    def _close(self, obj):
        if obj is not None and not isinstance(obj.last_touch, MouseMotionEvent): return
        if self._close_scheduled:
            return
        self._close_scheduled = True
        if self._clock:
            Clock.unschedule(self._clock)
            self._clock = None
        if self.on_dismiss:
            self.on_dismiss()

class ReviewScreen(ColorScreen):
    """Final action screen: saved collage preview with independent print/share/done actions."""

    def __init__(self, app, **kwargs):
        Logger.info('ReviewScreen: __init__().')
        super(ReviewScreen, self).__init__(**kwargs)

        self.app = app
        self._current_format = 0
        self._home_timeout_clock = None
        self._home_progress_clock = None
        self.layout = AnchorLayout(padding=BORDER_THINKNESS, anchor_x='center', anchor_y='top')
        self.overlay_layout = FloatLayout()
        self.layout.add_widget(self.overlay_layout)

        self.preview = BlurredImage(
            blur=self.app.BLUR_COLLAGE,
            fit_mode='contain',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        self.overlay_layout.add_widget(self.preview)

        self.btn_home = make_icon_button(
            ICON_HOME,
            size=0.14,
            pos_hint={'x': 0.05, 'top': 0.95},
            font=ICON_TTF,
            font_size_fraction=0.07,
            bgcolor=HOME_COLOR,
            progress=True,
            progress_color=HOME_PROGRESS_COLOR,
            progress_line_width_fraction=0.028,
            on_release=self.home_event,
        )
        self.overlay_layout.add_widget(self.btn_home)

        self.btn_print = make_icon_text_button(
            icon=ICON_PRINT,
            text='PRINT',
            size_hint=(0.16, 0.09),
            pos_hint={},
            icon_font=ICON_TTF,
            icon_font_size_fraction=0.07,
            text_font_size_fraction=0.035,
            bgcolor=CONFIRM_COLOR,
            on_release=self.print_event,
        )
        self.overlay_layout.add_widget(self.btn_print)

        self.btn_share = None
        if self.app.SHARE:
            self.btn_share = make_icon_text_button(
                icon=ICON_SHARE,
                text='SHARE',
                size_hint=(0.16, 0.09),
                pos_hint={},
                icon_font=ICON_TTF,
                icon_font_size_fraction=0.07,
                text_font_size_fraction=0.035,
                bgcolor=SHARE_COLOR,
                on_release=self.share_event,
            )
            self.overlay_layout.add_widget(self.btn_share)

        self.overlay_layout.bind(size=self._layout_action_buttons)
        Clock.schedule_once(self._layout_action_buttons, 0)
        self.add_widget(self.layout)

    def _action_buttons(self):
        buttons = []
        if self.btn_share is not None:
            buttons.append(self.btn_share)
        if self.btn_print.parent is not None:
            buttons.append(self.btn_print)
        return buttons

    def _sync_print_button(self):
        printer_available = self.app.has_printer()
        if printer_available and self.btn_print.parent is None:
            self.overlay_layout.add_widget(self.btn_print)
        elif not printer_available and self.btn_print.parent is not None:
            self.overlay_layout.remove_widget(self.btn_print)
        self._layout_action_buttons()

    def _layout_action_buttons(self, *args):
        buttons = self._action_buttons()
        if not buttons:
            return
        bottom = max(dp(4), self.overlay_layout.height * 0.05)
        gap = max(dp(4), self.overlay_layout.height * 0.02)
        top = max(dp(4), self.overlay_layout.height * 0.05)
        max_h = max(dp(18), (self.overlay_layout.height - bottom - top - gap * (len(buttons) - 1)) / len(buttons))
        y = bottom
        for btn in buttons:
            if btn.height > max_h:
                btn.height = max_h
            btn.pos_hint = {}
            btn.x = max(0, min(self.overlay_layout.width * 0.95 - btn.width, self.overlay_layout.width - btn.width))
            btn.y = y
            y = btn.top + gap

    def on_entry(self, kwargs={}):
        Logger.info('ReviewScreen: on_entry().')
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self._start_home_timeout()
        if self.app.ringled:
            self.app.ringled.start_rainbow()
        self._sync_print_button()
        self._load_preview_async(FileUtils.get_small_path(self.app.get_collage()))
        self.app.start_photo_task(self.app.save_collage)
        if self.app.SHARE:
            QRCodePopup.preload_async()

    def _load_preview_async(self, path):
        def load_image():
            im = cv2.imread(path)

            def apply_on_main(dt):
                if im is not None:
                    self.preview.set_image(im)
                else:
                    Logger.warning('ReviewScreen: cannot load preview %s', path)

            Clock.schedule_once(apply_on_main, 0)

        threading.Thread(target=load_image, daemon=True).start()

    def on_exit(self, kwargs={}):
        Logger.info('ReviewScreen: on_exit().')
        self._stop_home_timeout()
        if hasattr(self, 'qr_popup') and self.qr_popup.parent:
            self.layout.remove_widget(self.qr_popup)
        if hasattr(self, 'print_popup') and self.print_popup.parent:
            self.layout.remove_widget(self.print_popup)
        if self.app.ringled:
            self.app.ringled.clear()

    def _reset_timeout(self):
        self._start_home_timeout()

    def _start_home_timeout(self):
        self._stop_home_timeout()
        self._home_timeout_started_at = Clock.get_boottime()
        self.btn_home.progress = 1.0
        self._home_timeout_clock = Clock.schedule_once(self.timer_event, HOME_TIMEOUT_SECONDS)
        self._home_progress_clock = Clock.schedule_interval(self._update_home_progress, 1/30.0)

    def _stop_home_timeout(self):
        if self._home_timeout_clock:
            Clock.unschedule(self._home_timeout_clock)
            self._home_timeout_clock = None
        if self._home_progress_clock:
            Clock.unschedule(self._home_progress_clock)
            self._home_progress_clock = None

    def _update_home_progress(self, dt):
        elapsed = Clock.get_boottime() - self._home_timeout_started_at
        self.btn_home.progress = max(0, 1.0 - (elapsed / HOME_TIMEOUT_SECONDS))

    def home_event(self, obj):
        if obj is not None and not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ReviewScreen: home_event().')
        self._stop_home_timeout()
        self.app.transition_to(ScreenMgr.SUCCESS)

    def print_event(self, obj):
        if obj is not None and not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ReviewScreen: print_event().')
        self._reset_timeout()
        if hasattr(self, 'print_popup') and self.print_popup.parent:
            return
        self.print_popup = PrintStatusPopup(self.app, self._current_format, on_dismiss=self._dismiss_print_popup)
        self.layout.add_widget(self.print_popup)

    def share_event(self, obj):
        if obj is not None and not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ReviewScreen: share_event().')
        self._reset_timeout()
        if hasattr(self, 'qr_popup') and self.qr_popup.parent:
            return
        self.qr_popup = QRCodePopup(on_dismiss=self._dismiss_qr_popup)
        self.layout.add_widget(self.qr_popup)

    def _dismiss_print_popup(self):
        if hasattr(self, 'print_popup') and self.print_popup.parent:
            self.layout.remove_widget(self.print_popup)
        self._reset_timeout()

    def _dismiss_qr_popup(self):
        if hasattr(self, 'qr_popup') and self.qr_popup.parent:
            self.layout.remove_widget(self.qr_popup)
        self._reset_timeout()

    def timer_event(self, obj):
        Logger.info('ReviewScreen: timer_event().')
        self._stop_home_timeout()
        self.app.transition_to(ScreenMgr.START)

    def on_keyboard_action(self):
        self.home_event(None)
        return True

class SuccessScreen(ColorScreen):
    """
    +-----------------+
    |                 |
    |    Perfect !    |
    |                 |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('SuccessScreen: __init__().')
        super(SuccessScreen, self).__init__(**kwargs)

        self.app = app

        layout = BoxLayout(orientation='vertical')

        # Display success icon
        icon = ResizeLabel(
            size_hint=(0.4, 0.4),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            font_name=ICON_TTF,
            text=ICON_SUCCESS,
            wh_fraction=0.22,
        )
        layout.add_widget(icon)

        title = Label(
            size_hint=(1, 0.10),
            text='Awesome !',
            font_size=LARGE_FONT(),
            bold=True,
            halign='center',
            valign='middle',
        )
        wh_bind(title, 'font_size', LARGE_FONT)
        title.bind(size=title.setter('text_size'))
        layout.add_widget(title)

        # Display success2 icon
        icon2 = ResizeLabel(
            size_hint=(0.1, 0.1),
            pos_hint={'center_x': 0.5, 'y': 0.3},
            font_name=ICON_TTF,
            text=ICON_SUCCESS2,
            wh_fraction=0.055,
        )
        layout.add_widget(icon2)

        self.add_widget(layout)

    def on_entry(self, kwargs={}):
        Logger.info('SuccessScreen: on_entry().')
        self._clock = Clock.schedule_once(self.timer_event, 1)
        if self.app.ringled:
            self.app.ringled.blink([255, 255, 255])

    def on_exit(self, kwargs={}):
        Logger.info('SuccessScreen: on_exit().')
        Clock.unschedule(self._clock)
        if self.app.ringled:
            self.app.ringled.clear()

    def on_click_start(self, obj):
        Logger.info('SuccessScreen: on_click_start(%s).', obj)
        self.app.transition_to(ScreenMgr.START)

    def timer_event(self, obj):
        Logger.info('SuccessScreen: timer_event().')
        self.app.transition_to(ScreenMgr.START)

class CopyingScreen(ColorScreen):
    """
    +-----------------+
    |                 |
    |     Copying     |
    |                 |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('CopyingScreen: __init__().')
        super(CopyingScreen, self).__init__(**kwargs)

        self.app = app
        self._count = 0

        layout = BoxLayout(orientation='vertical')

        # Display USB icon
        icon = ResizeLabel(
            size_hint=(0.4, 0.4),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            font_name=ICON_TTF,
            text=ICON_USB,
            wh_fraction=0.22,
        )
        layout.add_widget(icon)
        info = ResizeLabel(
            size_hint=(0.9, 0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.6},
            text='Do not disconnect your USB dongle before this screen disapears !',
            wh_fraction=0.07,
        )
        layout.add_widget(info)

        # Display progress
        self.progress = ResizeLabel(
            size_hint=(0.9, 0.2),
            pos_hint={'center_x': 0.5, 'center_y': 0.35},
            text='-',
            wh_fraction=0.07,
        )
        layout.add_widget(self.progress)

        # Display loading spinner
        loading = RotatingLabel(
            size_hint=(0.1, 0.1),
            pos_hint={'center_x': 0.5, 'y': 0.3},
            font_name=ICON_TTF,
            text=ICON_LOADING,
            wh_fraction=0.055,
        )
        layout.add_widget(loading)

        self.add_widget(layout)

    def on_entry(self, kwargs={}):
        Logger.info('CopyingScreen: on_entry().')
        if self.app.ringled:
            self.app.ringled.wave([255, 255, 255])

    def on_exit(self, kwargs={}):
        Logger.info('CopyingScreen: on_exit().')
        if self.app.ringled:
            self.app.ringled.clear()

    def on_update(self, kwargs={}):
        if not 'label' in kwargs: return
        self.progress.text = f"Copying {kwargs.get('label')}"

class QRCodePopup(FloatLayout):
    """Popup overlay to show QR code."""
    
    # Class-level cache for QR code texture (shared across all instances)
    _qr_texture_cache = None
    _qr_png_cache = None
    _qr_generating = False

    @classmethod
    def preload(cls):
        """Build the QR texture on the UI thread if async preload did not finish yet."""
        if cls._qr_texture_cache is not None:
            return

        if cls._qr_png_cache is not None:
            started_at = time.monotonic()
            cls._cache_texture_from_png(cls._qr_png_cache)
            Logger.info('QRCodePopup: QR texture cached in %.2fs', time.monotonic() - started_at)
            return

        cls.preload_async()

    @classmethod
    def preload_async(cls):
        """Generate QR PNG in a worker, then create the Kivy texture on the UI thread."""
        if cls._qr_texture_cache is not None or cls._qr_generating:
            return

        cls._qr_generating = True

        def generate_png():
            started_at = time.monotonic()
            try:
                png = cls._build_qr_png()
            except Exception as exc:
                cls._qr_generating = False
                Logger.error('QRCodePopup: QR async generation failed: %s', exc)
                return

            def cache_on_main(dt):
                cls._qr_png_cache = png
                cls._cache_texture_from_png(png)
                cls._qr_generating = False
                Logger.info('QRCodePopup: QR code generated and cached in %.2fs', time.monotonic() - started_at)

            Clock.schedule_once(cache_on_main, 0)

        threading.Thread(target=generate_png, name='photobooth-qr-preload', daemon=True).start()

    @classmethod
    def _build_qr_png(cls):
        import qrcode

        wifi_qr_data = "WIFI:T:nopass;S:PhotoBooth;P:;H:false;;"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(wifi_qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

    @classmethod
    def _cache_texture_from_png(cls, png):
        buf = io.BytesIO(png)
        core_image = CoreImage(buf, ext='png')
        cls._qr_texture_cache = core_image.texture
    
    def __init__(self, on_dismiss=None, **kwargs):
        super(QRCodePopup, self).__init__(**kwargs)
        self.on_dismiss = on_dismiss
        self._close_scheduled = False
        
        # Semi-transparent overlay
        with self.canvas.before:
            Color(0, 0, 0, 0.8)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        from kivy.graphics import RoundedRectangle

        # Card uses size_hint so it reflows automatically on Window resize.
        # Portrait hint: 60% wide, 85% tall — FloatLayout centers it via pos_hint.
        self.card = BoxLayout(
            orientation='vertical',
            size_hint=(0.6, 0.85),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            padding=Window.height * 0.03,
            spacing=Window.height * 0.015,
        )
        with self.card.canvas.before:
            Color(1, 1, 1, 1)
            self.card_rect = RoundedRectangle(pos=self.card.pos, size=self.card.size, radius=[Window.height * 0.022])
        self.card.bind(pos=self._update_card, size=self._update_card)

        scan_label = ResizeLabel(
            text='SCAN ME',
            size_hint=(1, 0.1),
            wh_fraction=0.055,
            bold=True,
            color=(0, 0, 0, 1),
            halign='center',
            valign='middle',
        )
        self.card.add_widget(scan_label)

        # QR Code image fills remaining space
        self.qr_image = Image(
            size_hint=(1, 1),
            fit_mode='contain',
        )
        self.card.add_widget(self.qr_image)

        hint_label = ResizeLabel(
            text='Go to http://192.168.4.1',
            size_hint=(1, 0.08),
            wh_fraction=0.022,
            bold=True,
            color=(0, 0, 0, 1),
            halign='center',
            valign='middle',
        )
        self.card.add_widget(hint_label)

        btn_close = make_icon_button(
            ICON_CANCEL,
            size=0.10,
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            font=ICON_TTF,
            font_size_fraction=0.055,
            bgcolor=CANCEL_COLOR,
            on_release=self._close
        )
        # Wrap in a fixed-height anchor so the button doesn't stretch
        btn_container = AnchorLayout(
            size_hint=(1, 0.15),
            anchor_x='center',
            anchor_y='center',
        )
        btn_container.add_widget(btn_close)
        self.card.add_widget(btn_container)

        self.add_widget(self.card)
        self._generate_qr_code()
    
    def on_touch_down(self, touch):
        """Block all touch events from reaching widgets below the popup."""
        # Only allow touches on the card to be processed
        if self.card.collide_point(*touch.pos):
            return super(QRCodePopup, self).on_touch_down(touch)
        # Block all other touches
        return True
    
    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
    
    def _update_card(self, instance, *args):
        self.card_rect.pos = instance.pos
        self.card_rect.size = instance.size
    
    def _generate_qr_code(self):
        """Generate WiFi QR code with caching for better performance."""
        QRCodePopup.preload()
        if QRCodePopup._qr_texture_cache is not None:
            self.qr_image.texture = QRCodePopup._qr_texture_cache
            Logger.info('QRCodePopup: Using cached QR code')
    
    def _close(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        if self._close_scheduled:
            return
        self._close_scheduled = True
        if self.on_dismiss:
            Clock.schedule_once(lambda dt: self.on_dismiss(), 0)

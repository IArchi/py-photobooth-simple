import random
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.graphics import Rectangle, Color
from kivy.uix.image import Image, AsyncImage
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.input.providers.mouse import MouseMotionEvent
from kivy.core.window import Window

from libs.kivywidgets import *
from libs.file_utils import FileUtils

XLARGE_FONT = '200sp'
LARGE_FONT = '60sp'
NORMAL_FONT = '50sp'
SMALL_FONT = '30sp'
TINY_FONT = '15sp'

# Add or not blurry borders to make images match the size of the window
BLUR_CAMERA = True
BLUR_IMAGES = True
BLUR_COLLAGE = False

# Colors
BACKGROUND_COLOR = hex_to_rgba('#26495c')
BORDER_COLOR = hex_to_rgba('#c4a35a')
BORDER_THINKNESS = 10
PROGRESS_COLOR = hex_to_rgba('#e5e5e5')
CONFIRM_COLOR = hex_to_rgba('#538a64')
CANCEL_COLOR = hex_to_rgba('#8b4846')
HOME_COLOR = hex_to_rgba('#534969')
BADGE_COLOR = hex_to_rgba('#8b4846')

# Icons
ICON_TTF = './assets/fonts/hugeicons.ttf' # https://hugeicons.com/free-icon-font and https://hugeicons.com/icons?style=Stroke&type=Rounded
ICON_TOUCH = '\u3d3e'
ICON_CHOOSE1 = '\u3b8e'
ICON_CHOOSE2 = '\u3b90'
ICON_ERROR = '\u3b03'
ICON_ERROR_PRINTING = '\u458d'
ICON_ERROR_PRINTING_TOOLONG = '\u458d'
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

class ScreenMgr(ScreenManager):
    """Screen Manager for the photobooth screens."""
    WAITING = 'waiting'
    READY = 'ready'
    SELECT_FORMAT = 'select_format'
    ERROR = 'error'
    COUNTDOWN = 'countdown'
    CONFIRM_CAPTURE = 'confirm_capture'
    PROCESSING = 'processing'
    CONFIRM_SAVE = 'confirm_save'
    CONFIRM_PRINT = 'confirm_print'
    PRINTING = 'printing'
    SUCCESS = 'success'
    COPYING = 'copying'

    def __init__(self, app, **kwargs):
        Logger.info('ScreenMgr: __init__().')
        super(ScreenMgr, self).__init__(**kwargs)
        self.app = app
        self.pb_screens = {
            self.WAITING            : WaitingScreen(app, name=self.WAITING),
            self.SELECT_FORMAT      : SelectFormatScreen(app, name=self.SELECT_FORMAT),
            self.ERROR              : ErrorScreen(app, name=self.ERROR),
            self.READY              : ReadyScreen(app, name=self.READY),
            self.COUNTDOWN          : CountdownScreen(app, name=self.COUNTDOWN),
            self.CONFIRM_CAPTURE    : ConfirmCaptureScreen(app, name=self.CONFIRM_CAPTURE),
            self.PROCESSING         : ProcessingScreen(app, name=self.PROCESSING),
            self.CONFIRM_SAVE       : ConfirmSaveScreen(app, name=self.CONFIRM_SAVE),
            self.CONFIRM_PRINT      : ConfirmPrintScreen(app, name=self.CONFIRM_PRINT),
            self.PRINTING           : PrintingScreen(app, name=self.PRINTING),
            self.SUCCESS            : SuccessScreen(app, name=self.SUCCESS),
            self.COPYING            : CopyingScreen(app, name=self.COPYING),
        }
        for screen in self.pb_screens.values(): self.add_widget(screen)

        self.current = self.WAITING
        if self.app.FULLSCREEN: Window.fullscreen = True

class BackgroundScreen(Screen):
    def __init__(self, bg='./assets/backgrounds/bg_default.jpeg', **kwargs):
        super(BackgroundScreen, self).__init__(**kwargs)
        with self.canvas.before:
            self.background_image = Rectangle(pos=self.pos, size=self.size, source=bg)

    def on_pos(self, *args):
        self.background_image.pos = self.pos

    def on_size(self, *args):
        self.background_image.size = self.size

class ColorScreen(Screen):
    def __init__(self, **kwargs):
        super(ColorScreen, self).__init__(**kwargs)
        with self.canvas.before:
            # Border
            Color(*BORDER_COLOR)
            self.border_rect = Rectangle(pos=self.pos, size=self.size)

            # Background
            Color(*BACKGROUND_COLOR)
            self.background_rect = Rectangle(pos=(self.x + BORDER_THINKNESS, self.y + BORDER_THINKNESS), size=(self.width - BORDER_THINKNESS*2, self.height - BORDER_THINKNESS*2))

    def on_pos(self, *args):
        self.border_rect.pos = self.pos
        self.background_rect.pos = (self.x + BORDER_THINKNESS, self.y + BORDER_THINKNESS)

    def on_size(self, *args):
        self.border_rect.size = self.size
        self.background_rect.size = (self.width - BORDER_THINKNESS*2, self.height - BORDER_THINKNESS*2)

class WaitingScreen(BackgroundScreen):
    """
    +-----------------+
    |                 |
    | Press to begin  |
    |                 |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('WaitingScreen: __init__().')
        super(WaitingScreen, self).__init__(bg='./assets/backgrounds/bg_waiting.jpeg', **kwargs)

        self.app = app

        overlay_layout = LayoutButton()

        start = BorderedLabel(
            text='PHOTO BOOTH',
            font_size=LARGE_FONT,
            border_color=(1,1,1,1),
            border_width=5,
            size_hint=(0.7, 0.2),
            padding=(30,30,30,30),
            pos_hint={'x': 0.15, 'y': 0.4},
        )
        overlay_layout.add_widget(start)

        # Touch icon
        icon = ResizeLabel(
            size_hint=(0.15, 0.2),
            pos_hint={'x': 0.42, 'y': 0.1},
            font_name=ICON_TTF,
            text=ICON_TOUCH,
            max_font_size=XLARGE_FONT,
        )
        overlay_layout.add_widget(icon)

        # Version
        version = Label(
            text='Version 1.0',
            font_size=TINY_FONT,
            halign='left',
            valign='middle',
            size_hint=(0.1, 0.05),
            pos_hint={'x': 0.9, 'y': 0.95},
        )
        overlay_layout.add_widget(version)

        overlay_layout.bind(on_release=self.on_click)

        self.add_widget(overlay_layout)

    def on_entry(self, kwargs={}):
        Logger.info('WaitingScreen: on_entry().')
        self.app.ringled.start_rainbow()
        self.app.purge_tmp()

    def on_exit(self, kwargs={}):
        Logger.info('WaitingScreen: on_exit().')
        self.app.ringled.clear()

    def on_click(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('WaitingScreen: on_click().')
        self.app.transition_to(ScreenMgr.SELECT_FORMAT)

class SelectFormatScreen(ColorScreen):
    """
    +-----------------+
    |  Select format  |
    |                 |
    |                 |
    |                 |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('SelectFormatScreen: __init__().')
        #super(SelectFormatScreen, self).__init__(bg='./assets/backgrounds/bg_instructions.jpeg', **kwargs)
        super(SelectFormatScreen, self).__init__(**kwargs)
        self.app = app

        self.layout = AnchorLayout(padding=BORDER_THINKNESS, anchor_x='center', anchor_y='top')

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        # Add previews
        available_formats = self.app.get_layout_previews()
        self.preview_left = ImageButton(
            source=available_formats[0],
            size_hint=(0.4, 0.7),
            pos_hint={'x': 0.05, 'y': 0.15},
        )
        overlay_layout.add_widget(self.preview_left)
        self.preview_left.bind(on_release=self.on_click_left)
        self.preview_right = ImageButton(
            source=available_formats[1],
            size_hint=(0.3, 0.8),
            pos_hint={'right': 0.95, 'y': 0.1},
        )
        overlay_layout.add_widget(self.preview_right)
        self.preview_right.bind(on_release=self.on_click_right)

        # Add select icon
        icons_layout = BoxLayout(
            orientation='horizontal',
            spacing=20,
            size_hint=(0.25, 0.4),
            pos_hint={'x': 0.45, 'y':0.2},
        )
        overlay_layout.add_widget(icons_layout)
        icon_left = ResizeLabel(
            font_name=ICON_TTF,
            text=ICON_CHOOSE1,
            max_font_size=XLARGE_FONT,
        )
        icons_layout.add_widget(icon_left)
        icon_right = ResizeLabel(
            font_name=ICON_TTF,
            text=ICON_CHOOSE2,
            max_font_size=XLARGE_FONT,
        )
        icons_layout.add_widget(icon_right)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('SelectFormatScreen: on_entry().')
        self.preview_left.reload()
        self.preview_right.reload()
        self.app.ringled.start_rainbow()

    def on_exit(self, kwargs={}):
        Logger.info('SelectFormatScreen: on_exit().')
        self.app.ringled.clear()

    def on_click_left(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('SelectFormatScreen: on_click_left().')
        self.app.transition_to(ScreenMgr.READY, shot=0, format=0)

    def on_click_right(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('SelectFormatScreen: on_click_right().')
        self.app.transition_to(ScreenMgr.READY, shot=0, format=1)

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

        overlay_layout = LayoutButton()

        # Display icon
        self.icon = ResizeLabel(
            size_hint=(0.3, 0.3),
            pos_hint={'x': 0.35, 'y': 0.35},
            font_name=ICON_TTF,
            text=ICON_ERROR,
            max_font_size=XLARGE_FONT,
        )
        overlay_layout.add_widget(self.icon)

        overlay_layout.bind(on_release=self.on_click)
        self.add_widget(overlay_layout)

    def on_entry(self, kwargs={}):
        Logger.info('ErrorScreen: on_entry().')
        if 'error' in kwargs: self.icon.text = str(kwargs.get('error'))

    def on_exit(self, kwargs={}):
        Logger.info('ErrorScreen: on_exit().')

    def on_click(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ErrorScreen: on_click().')
        self.app.transition_to(ScreenMgr.WAITING)

class ReadyScreen(ColorScreen):
    """
    +-----------------+
    |                 |
    |      Ready      |
    |                 |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('ReadyScreen: __init__().')
        super(ReadyScreen, self).__init__(**kwargs)

        self.app = app

        # Use progress bar
        self.progress = ThickProgressBar(
            color=PROGRESS_COLOR,
            max=100,
            size_hint=(1, 0.1),
            pos_hint={'x': 0, 'y': 0.45},
        )

        self.layout = BoxLayout(padding=BORDER_THINKNESS)
        self.layout.add_widget(self.progress)
        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ReadyScreen: on_entry().')
        self._current_shot = kwargs.get('shot') if 'shot' in kwargs else 0
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self._clock_progress = Clock.schedule_once(self.timer_progress, 0.05)
        self.progress.value = 100/(2/0.05)
        self._clock = Clock.schedule_once(self.timer_event, 2.1)

    def on_exit(self, kwargs={}):
        Logger.info('ReadyScreen: on_exit().')
        Clock.unschedule(self._clock)
        Clock.unschedule(self._clock_progress)

    def timer_progress(self, obj):
        self.progress.value += 100/(2/0.05)
        self._clock_progress = Clock.schedule_once(self.timer_progress, 0.05)

    def timer_event(self, obj):
        Logger.info('ReadyScreen: timer_event().')
        self.app.transition_to(ScreenMgr.COUNTDOWN, shot=self._current_shot, format=self._current_format)

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

        self.time_remaining = self.app.COUNTDOWN
        self.time_remaining_label = ShadowLabel(
            text=str(self.time_remaining),
            halign='center',
            valign='middle',
            font_size=XLARGE_FONT
        )

        # Display camera preview
        self.layout = AnchorLayout(padding=BORDER_THINKNESS, anchor_x='center', anchor_y='top')
        self.camera = KivyCamera(app=self.app, fps=30, blur=BLUR_CAMERA, fit_mode='contain')
        self.layout.add_widget(self.camera)

        # Display countdown
        self.boxlayout = BoxLayout()
        self.boxlayout.add_widget(self.time_remaining_label)
        self.layout.add_widget(self.boxlayout)

        # Declare color background
        self.color_background = BackgroundBoxLayout(background_color=(1,1,1,1))

        # Display loading
        self.loading_layout = BoxLayout(orientation='vertical')
        icon = ResizeLabel(
            size_hint=(0.4, 0.4),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            font_name=ICON_TTF,
            text=ICON_PROCESSING,
            max_font_size=XLARGE_FONT,
        )
        self.loading_layout.add_widget(icon)

        loading = RotatingLabel(
            size_hint=(0.1, 0.1),
            pos_hint={'center_x': 0.5, 'y': 0.3},
            font_name=ICON_TTF,
            text=ICON_LOADING,
            max_font_size=NORMAL_FONT,
        )
        self.loading_layout.add_widget(loading)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('CountdownScreen: on_entry().')
        self.time_remaining = self.app.COUNTDOWN
        if (not self.time_remaining_label.parent): self.boxlayout.add_widget(self.time_remaining_label)
        self._current_shot = kwargs.get('shot') if 'shot' in kwargs else 0
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self.camera.start(self.app.is_square_format(self._current_format))
        self.time_remaining_label.text = str(self.time_remaining)
        self._clock = Clock.schedule_once(self.timer_event, 1)
        self._clock_trigger = None
        self.app.ringled.start_countdown(self.time_remaining)

    def on_exit(self, kwargs={}):
        Logger.info('CountdownScreen: on_exit().')
        self.camera.opacity = 1
        Clock.unschedule(self._clock)
        Clock.unschedule(self._clock_trigger)
        self.app.ringled.clear()
        self.boxlayout.remove_widget(self.loading_layout)
        self.camera.stop()

    def timer_event(self, obj):
        Logger.info('CountdownScreen: timer_event(%s)', obj)
        self.time_remaining -= 1
        if self.time_remaining:
            self.time_remaining_label.text = str(self.time_remaining)
            Clock.schedule_once(self.timer_event, 1)
        else:
            # Trigger shot
            try:
                # Make screen blink
                self.layout.add_widget(self.color_background)
                self.app.trigger_shot(self._current_shot, self._current_format)
                self._clock_trigger = Clock.schedule_once(self.timer_trigger, 1.2)
                Clock.schedule_once(self.timer_bg, 0.2)

                # Display loading
                self.boxlayout.remove_widget(self.time_remaining_label)
                self.boxlayout.add_widget(self.loading_layout)
            except:
                return self.app.transition_to(ScreenMgr.ERROR)

    def timer_bg(self, obj):
        self.camera.opacity = 0
        # Remove flash background
        self.layout.remove_widget(self.color_background)

    def timer_trigger(self, obj):
        if not(self.app.is_shot_completed(self._current_shot)):
            # Retry after 1sec
            self._clock_trigger = Clock.schedule_once(self.timer_trigger, 1)
        elif self.app.get_shots_to_take(self._current_format) == 1:
            # Only one photo to capture
            self.app.transition_to(ScreenMgr.PROCESSING, format=self._current_format)
        else:
            # Display photo and take next shot
            self.app.transition_to(ScreenMgr.CONFIRM_CAPTURE, shot=self._current_shot, format=self._current_format)

class ConfirmCaptureScreen(ColorScreen):
    """
    +-----------------+
    |       1/3       |
    |                 |
    | NO          YES |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('ConfirmCaptureScreen: __init__().')
        super(ConfirmCaptureScreen, self).__init__(**kwargs)

        self.app = app
        self._current_shot = 0
        self._current_format = 1

        self.layout = AnchorLayout(padding=BORDER_THINKNESS, anchor_x='center', anchor_y='top')
        self.overlay_layout = FloatLayout()
        self.layout.add_widget(self.overlay_layout)

        # Display capture
        self.preview = BlurredImage(
            blur=BLUR_IMAGES,
            fit_mode='contain',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        self.overlay_layout.add_widget(self.preview)

        # Add counter
        self.counter_layout = BoxLayout(
            orientation='horizontal',
            spacing=20,
            size_hint=(0.25, 0.1),
            pos_hint={'x': 0.375, 'y':0.85},
        )
        self.icons = []
        for _ in range(0, self.app.get_shots_to_take(self._current_format)):
            icon = ResizeLabel(
                font_name=ICON_TTF,
                text=ICON_SHOT_TO_TAKE,
                max_font_size=LARGE_FONT,
            )
            self.counter_layout.add_widget(icon)
            self.icons.append(icon)
        self.overlay_layout.add_widget(self.counter_layout)

        # Stack all left elements into a box layout
        self.left_layout = BoxLayout(
                                orientation='vertical',
                                size_hint=(0.1, 0.95),
                                pos_hint={'x': 0.05, 'y': 0.05},
                                spacing=10,
                                )
        self.overlay_layout.add_widget(self.left_layout)

        # Stack all right elements into a box layout
        self.right_layout = BoxLayout(
                                orientation='vertical',
                                size_hint=(0.1, 0.95),
                                pos_hint={'right': 0.95, 'y': 0.05},
                                spacing=20,
                                )
        self.overlay_layout.add_widget(self.right_layout)

        # Confirm button
        btn_confirm = make_icon_button(ICON_CONFIRM,
                             size=1,
                             #pos_hint={'right': 0.95, 'y': 0.05},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=CONFIRM_COLOR,
                             on_release=self.keep_event,
                             )
        self.right_layout.add_widget(btn_confirm)

        # Home button
        btn_home = make_icon_button(ICON_HOME,
                             size=1,
                             pos_hint={'top': 0.95},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=HOME_COLOR,
                             on_release=self.home_event
                             )
        self.left_layout.add_widget(btn_home)

        # Cancel button
        btn_cancel = make_icon_button(ICON_CANCEL,
                             size=1,
                             #pos_hint={'x': 0.05, 'y': 0.05},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=CANCEL_COLOR,
                             on_release=self.no_event
                             )
        self.left_layout.add_widget(btn_cancel)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ConfirmCaptureScreen: on_entry().')
        self._current_shot = kwargs.get('shot') if 'shot' in kwargs else 0
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        for i in range(0, self.app.get_shots_to_take(self._current_format)): self.icons[i].text = ICON_SHOT_TO_TAKE
        for i in range(0, self._current_shot + 1): self.icons[i].text = ICON_SHOT_TAKEN
        self.preview.filepath = FileUtils.get_small_path(self.app.get_shot(self._current_shot))
        self.preview.reload()
        self.auto_leave = Clock.schedule_once(self.timer_event, 60)

    def on_exit(self, kwargs={}):
        Logger.info('ConfirmCaptureScreen: on_exit().')

    def keep_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Clock.unschedule(self.auto_leave)
        if self._current_shot == self.app.get_shots_to_take(self._current_format) - 1: self.app.transition_to(ScreenMgr.PROCESSING, format=self._current_format)
        else: self.app.transition_to(ScreenMgr.COUNTDOWN, shot=self._current_shot + 1, format=self._current_format)

    def no_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Clock.unschedule(self.auto_leave)
        self.app.transition_to(ScreenMgr.COUNTDOWN, shot=self._current_shot, format=self._current_format)

    def home_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Clock.unschedule(self.auto_leave)
        self.app.transition_to(ScreenMgr.WAITING)

    def timer_event(self, obj):
        Logger.info('ConfirmCaptureScreen: timer_event().')
        self.app.transition_to(ScreenMgr.WAITING)

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
            max_font_size=XLARGE_FONT,
        )
        layout.add_widget(icon)

        # Display loading spinner
        loading = RotatingLabel(
            size_hint=(0.1, 0.1),
            pos_hint={'center_x': 0.5, 'y': 0.3},
            font_name=ICON_TTF,
            text=ICON_LOADING,
            max_font_size=NORMAL_FONT,
        )

        layout.add_widget(loading)
        self.add_widget(layout)

    def on_entry(self, kwargs={}):
        Logger.info('ProcessingScreen: on_entry().')
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self._clock = Clock.schedule_once(self.timer_event, 3) # Fake timer to make it cleverer
        self.app.ringled.start_rainbow()

        # Perform collage
        self.app.trigger_collage(self._current_format)

    def on_exit(self, kwargs={}):
        Logger.info('ProcessingScreen: on_exit().')
        Clock.unschedule(self._clock)
        self.app.ringled.clear()

    def timer_event(self, obj):
        Logger.info('ProcessingScreen: timer_event().')
        if not(self.app.is_collage_completed()):
            self._clock = Clock.schedule_once(self.timer_event, 1)
        elif self.app.has_printer():
            self.app.transition_to(ScreenMgr.CONFIRM_PRINT, format=self._current_format)
        else:
            self.app.transition_to(ScreenMgr.CONFIRM_SAVE)

class ConfirmSaveScreen(ColorScreen):
    """
    +-----------------+
    |      Save ?     |
    |                 |
    | NO          YES |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('ConfirmSaveScreen: __init__().')
        super(ConfirmSaveScreen, self).__init__(**kwargs)

        self.app = app

        self.layout = AnchorLayout(padding=BORDER_THINKNESS, anchor_x='center', anchor_y='top')

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        # Display collage
        self.preview = BlurredImage(
            blur=BLUR_COLLAGE,
            fit_mode='contain',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        overlay_layout.add_widget(self.preview)

        # Stack all left elements into a box layout
        self.left_layout = BoxLayout(
                                orientation='vertical',
                                size_hint=(0.1, 0.95),
                                pos_hint={'x': 0.05, 'y': 0.05},
                                spacing=10,
                                )
        overlay_layout.add_widget(self.left_layout)

        # Stack all right elements into a box layout
        self.right_layout = BoxLayout(
                                orientation='vertical',
                                size_hint=(0.1, 0.95),
                                pos_hint={'right': 0.95, 'y': 0.05},
                                spacing=20,
                                )
        overlay_layout.add_widget(self.right_layout)

        # Confirm button
        btn_yes = make_icon_button(ICON_CONFIRM,
                             size=1,
                             #pos_hint={'right': 0.95, 'y': 0.05},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=CONFIRM_COLOR,
                             on_release=self.yes_event
                             )
        self.right_layout.add_widget(btn_yes)

        # Cancel button
        btn_cancel = make_icon_button(ICON_CANCEL,
                             size=1,
                             #pos_hint={'x': 0.05, 'y': 0.05},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=CANCEL_COLOR,
                             on_release=self.no_event,
                             )
        self.left_layout.add_widget(btn_cancel)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ConfirmSaveScreen: on_entry().')
        self.auto_confirm = Clock.schedule_once(self.timer_event, 60)
        self.app.ringled.start_rainbow()
        self.preview.filepath = FileUtils.get_small_path(self.app.get_collage())
        self.preview.reload()

    def on_exit(self, kwargs={}):
        Logger.info('ConfirmSaveScreen: on_exit().')
        self.app.ringled.clear()

    def yes_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Clock.unschedule(self.auto_confirm)
        self.app.save_collage()
        self.app.transition_to(ScreenMgr.SUCCESS)

    def no_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Clock.unschedule(self.auto_confirm)
        self.app.transition_to(ScreenMgr.WAITING)

    def timer_event(self, obj):
        Logger.info('ConfirmSaveScreen: timer_event().')
        Clock.unschedule(self.auto_confirm)
        self.app.save_collage()
        self.app.transition_to(ScreenMgr.WAITING)

class ConfirmPrintScreen(ColorScreen):
    """
    +-----------------+
    |      Print ?    |
    |                 |
    | NO          YES |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('ConfirmPrintScreen: __init__().')
        super(ConfirmPrintScreen, self).__init__(**kwargs)

        self.app = app
        self._current_format = 0

        self.layout = AnchorLayout(padding=BORDER_THINKNESS, anchor_x='center', anchor_y='top')

        self.overlay_layout = FloatLayout()
        self.layout.add_widget(self.overlay_layout)

        # Display collage
        self.preview = BlurredImage(
            blur=BLUR_COLLAGE,
            fit_mode='contain',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        self.overlay_layout.add_widget(self.preview)

        # Stack all left elements into a box layout
        self.left_layout = BoxLayout(
                                orientation='vertical',
                                size_hint=(0.1, 0.95),
                                pos_hint={'x': 0.05, 'y': 0.05},
                                spacing=10,
                                )
        self.overlay_layout.add_widget(self.left_layout)

        # Stack all right elements into a box layout
        self.right_layout = BoxLayout(
                                orientation='vertical',
                                size_hint=(0.1, 0.95),
                                pos_hint={'right': 0.95, 'y': 0.05},
                                spacing=20,
                                )
        self.overlay_layout.add_widget(self.right_layout)

        # Print once button
        self.btn_once = make_icon_button(ICON_PRINT,
                             size=1,
                             #pos_hint={'right': 0.95, 'y': 0.2},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=CONFIRM_COLOR,
                             badge='1',
                             badge_font_size=LARGE_FONT,
                             badge_color=BADGE_COLOR,
                             on_release=self.print_once,
                             )
        self.right_layout.add_widget(self.btn_once)

        # Print twice button
        self.btn_twice = make_icon_button(ICON_PRINT,
                             size=1,
                             #pos_hint={'right': 0.95, 'y': 0.05},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=CONFIRM_COLOR,
                             badge='2',
                             badge_font_size=LARGE_FONT,
                             badge_color=BADGE_COLOR,
                             on_release=self.print_twice,
                             )
        self.right_layout.add_widget(self.btn_twice)

        # Print button
        self.btn_print = make_icon_button(ICON_PRINT,
                             size=1,
                             #pos_hint={'right': 0.95, 'y': 0.05},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=CONFIRM_COLOR,
                             on_release=self.print_once,
                             )
        self.right_layout.add_widget(self.btn_print)

        # Cancel button
        btn_cancel = make_icon_button(ICON_CANCEL,
                             size=1,
                             #pos_hint={'x': 0.05, 'y': 0.05},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=CANCEL_COLOR,
                             on_release=self.no_event,
                             )
        self.left_layout.add_widget(btn_cancel)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ConfirmPrintScreen: on_entry().')
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self.right_layout.remove_widget(self.btn_once)
        self.right_layout.remove_widget(self.btn_twice)
        self.right_layout.remove_widget(self.btn_print)

        # Full page collage
        if self._current_format == 0:
            self.right_layout.add_widget(self.btn_once)
            self.right_layout.add_widget(self.btn_twice)
        # Strip collage
        elif self._current_format == 1:
            self.right_layout.add_widget(self.btn_print)
        else:
            self.app.transition_to(ScreenMgr.ERROR)
            return

        self.auto_decline = Clock.schedule_once(self.timer_event, 60)
        self.app.ringled.start_rainbow()
        self.preview.filepath = FileUtils.get_small_path(self.app.get_collage())
        self.preview.reload()

    def on_exit(self, kwargs={}):
        Logger.info('ConfirmPrintScreen: on_exit().')
        self.app.ringled.clear()

    def print_once(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ConfirmPrintScreen: print_once().')
        Clock.unschedule(self.auto_decline)
        self.app.transition_to(ScreenMgr.PRINTING, copies=1, format=self._current_format)

    def print_twice(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ConfirmPrintScreen: print_twice().')
        Clock.unschedule(self.auto_decline)
        self.app.transition_to(ScreenMgr.PRINTING, copies=2, format=self._current_format)

    def no_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Clock.unschedule(self.auto_decline)
        self.app.save_collage()
        self.app.transition_to(ScreenMgr.WAITING)

    def timer_event(self, obj):
        Logger.info('ConfirmPrintScreen: timer_event().')
        self.app.save_collage()
        self.app.transition_to(ScreenMgr.WAITING)

class PrintingScreen(ColorScreen):
    """
    +-----------------+
    |                 |
    |   Printing...   |
    |                 |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('PrintingScreen: __init__().')
        super(PrintingScreen, self).__init__(**kwargs)

        self.app = app
        self._current_format = 0

        layout = BoxLayout(orientation='vertical')

        # Display print icon
        icon = ResizeLabel(
            size_hint=(0.4, 0.4),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            font_name=ICON_TTF,
            text=ICON_PRINT,
            max_font_size=XLARGE_FONT,
        )
        layout.add_widget(icon)

        # Display loading spinner
        loading = RotatingLabel(
            size_hint=(0.1, 0.1),
            pos_hint={'center_x': 0.5, 'y': 0.3},
            font_name=ICON_TTF,
            text=ICON_LOADING,
            max_font_size=NORMAL_FONT,
        )
        layout.add_widget(loading)
        self.add_widget(layout)

        self._clock = None
        self._auto_cancel = None

    def on_entry(self, kwargs={}):
        Logger.info('PrintingScreen: on_entry().')
        self.app.ringled.start_rainbow()
        self._current_copies = kwargs.get('copies') if 'copies' in kwargs else 0
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0

        # Trigger print
        try:
            self._print_task_id = self.app.trigger_print(self._current_copies, self._current_format)
            self._clock = Clock.schedule_once(self.timer_event, 10)
            self._auto_cancel = Clock.schedule_once(self.timer_toolong, 30)
        except Exception as e:
            return self.app.transition_to(ScreenMgr.ERROR, error=ICON_ERROR_PRINTING)

    def on_exit(self, kwargs={}):
        Logger.info('PrintingScreen: on_exit().')
        if self._clock: Clock.unschedule(self._clock)
        if self._auto_cancel: Clock.unschedule(self._auto_cancel)
        self.app.save_collage()
        self.app.ringled.clear()

    def timer_event(self, obj):
        Logger.info('PrintingScreen: timer_event().')
        if not self.app.is_print_completed(self._print_task_id):
            self._clock = Clock.schedule_once(self.timer_event, 1)
        else:
            if self._clock: Clock.unschedule(self._clock)
            if self._auto_cancel: Clock.unschedule(self._auto_cancel)
            self.app.transition_to(ScreenMgr.SUCCESS)

    def timer_toolong(self, obj):
        Logger.info('PrintingScreen: timer_toolong().')
        return self.app.transition_to(ScreenMgr.ERROR, error=ICON_ERROR_PRINTING_TOOLONG)

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
            max_font_size=XLARGE_FONT,
        )
        layout.add_widget(icon)

        # Display success2 icon
        icon2 = ResizeLabel(
            size_hint=(0.1, 0.1),
            pos_hint={'center_x': 0.5, 'y': 0.3},
            font_name=ICON_TTF,
            text=ICON_SUCCESS2,
            max_font_size=NORMAL_FONT,
        )
        layout.add_widget(icon2)

        self.add_widget(layout)

    def on_entry(self, kwargs={}):
        Logger.info('SuccessScreen: on_entry().')
        self._clock = Clock.schedule_once(self.timer_event, 2)
        self.app.ringled.blink([255, 255, 255])

    def on_exit(self, kwargs={}):
        Logger.info('SuccessScreen: on_exit().')
        Clock.unschedule(self._clock)
        self.app.ringled.clear()

    def on_click_start(self, obj):
        Logger.info('SuccessScreen: on_click_start(%s).', obj)
        self.app.transition_to(ScreenMgr.WAITING)

    def timer_event(self, obj):
        Logger.info('SuccessScreen: timer_event().')
        self.app.transition_to(ScreenMgr.WAITING)

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
            max_font_size=XLARGE_FONT,
        )
        layout.add_widget(icon)

        # Display loading spinner
        loading = RotatingLabel(
            size_hint=(0.1, 0.1),
            pos_hint={'center_x': 0.5, 'y': 0.3},
            font_name=ICON_TTF,
            text=ICON_LOADING,
            max_font_size=NORMAL_FONT,
        )
        layout.add_widget(loading)

        self.add_widget(layout)

    def on_entry(self, kwargs={}):
        Logger.info('CopyingScreen: on_entry().')
        self.app.ringled.wave([255, 255, 255])

    def on_exit(self, kwargs={}):
        Logger.info('CopyingScreen: on_exit().')
        self.app.ringled.clear()

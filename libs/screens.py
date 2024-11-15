import random
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.graphics import Rectangle, Color, Line, BorderImage
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
IMAGE_BUTTON_FONT = '25sp'

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

        icon = Image(
            source='./assets/icons/touch.png',
            fit_mode='contain',
            size_hint=(0.15, 0.25),
            pos_hint={'x': 0.42, 'y': 0.02},
        )
        overlay_layout.add_widget(icon)

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

class SelectFormatScreen(BackgroundScreen):
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
        super(SelectFormatScreen, self).__init__(bg='./assets/backgrounds/bg_instructions.jpeg', **kwargs)

        self.app = app

        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        # Add preview
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
            pos_hint={'x': 0.65, 'y': 0.1},
        )
        overlay_layout.add_widget(self.preview_right)
        self.preview_right.bind(on_release=self.on_click_right)

        # Add arrows
        arrow_left = Image(
            source='./assets/icons/arrow_left.png',
            fit_mode='contain',
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.45, 'y': 0.3},
        )
        overlay_layout.add_widget(arrow_left)
        arrow_right = Image(
            source='./assets/icons/arrow_right.png',
            fit_mode='contain',
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.45, 'y': 0.70},
        )
        overlay_layout.add_widget(arrow_right)

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

class ErrorScreen(BackgroundScreen):
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
        self.icon = AsyncImage(
            source='./assets/icons/error.png',
            fit_mode='contain',
            size_hint=(0.3, 0.3),
            pos_hint={'x': 0.35, 'y': 0.35},
        )
        overlay_layout.add_widget(self.icon)

        overlay_layout.bind(on_release=self.on_click)
        self.add_widget(overlay_layout)

    def on_entry(self, kwargs={}):
        Logger.info('ErrorScreen: on_entry().')
        if 'error' in kwargs: self.icon.source = str(kwargs.get('error'))

    def on_exit(self, kwargs={}):
        Logger.info('ErrorScreen: on_exit().')

    def on_click(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ErrorScreen: on_click().')
        self.app.transition_to(ScreenMgr.WAITING)

class ReadyScreen(BackgroundScreen):
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
            max=100,
            size_hint=(1, 0.1),
            pos_hint={'x': 0, 'y': 0.45},
        )

        self.layout = BoxLayout()
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

class CountdownScreen(BackgroundScreen):
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
        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')
        self.camera = KivyCamera(app=self.app, fps=30, fit_mode='contain')
        self.layout.add_widget(self.camera)

        # Display countdown
        self.boxlayout = BoxLayout()
        self.boxlayout.add_widget(self.time_remaining_label)
        self.layout.add_widget(self.boxlayout)

        # Declare color background
        self.color_background = BackgroundBoxLayout(background_color=(1,1,1,1))

        # Display loading icon
        self.loading = RotatingImage(
            source='./assets/icons/loading.png',
            size_hint=(0.4, 0.4),
            pos_hint={'x': 0.3, 'y': 0.3},
        )
        
        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('CountdownScreen: on_entry().')
        self.time_remaining = self.app.COUNTDOWN
        if (not self.time_remaining_label.parent): self.boxlayout.add_widget(self.time_remaining_label)
        self._current_shot = kwargs.get('shot') if 'shot' in kwargs else 0
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self.camera.start(self.app.is_square_format(self._current_format))
        self.time_remaining_label.font_size = XLARGE_FONT
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
        self.boxlayout.remove_widget(self.loading)
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
                self.boxlayout.add_widget(self.loading)
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
            
class ConfirmCaptureScreen(BackgroundScreen):
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

        # Display taken photo
        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        # Display capture
        self.preview = BlurredImage(
            fit_mode='contain',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        overlay_layout.add_widget(self.preview)

        # Add counter
        self.counter_layout = BoxLayout(
            spacing=10,
            size_hint=(0.25, 0.1),
            pos_hint={'x': 0.375, 'y': 0.88},
        )
        self.icons = []
        for _ in range(0, self.app.get_shots_to_take(self._current_format)):
            icon = AsyncImage(
                source='./assets/icons/camera_shot_off.png',
                size_hint=(1, None),
            )
            self.counter_layout.add_widget(icon)
            self.icons.append(icon)
        overlay_layout.add_widget(self.counter_layout)

        # Add buttons
        self.keep_button = ImageRoundButton(
            source='./assets/icons/check.png',
            size_hint=(0.1, 0.1),
            pos_hint={'x': 0.85, 'y': 0.05},
            background_color=(.4, .733, .416, 1),
        )
        self.keep_button.bind(on_release=self.keep_event)
        overlay_layout.add_widget(self.keep_button)
        self.no_button = ImageRoundButton(
            source='./assets/icons/refresh.png',
            size_hint=(0.1, 0.1),
            pos_hint={'x': 0.05, 'y': 0.05},
            background_color=(.937, .325, .314, 1),
        )
        self.no_button.bind(on_release=self.no_event)
        overlay_layout.add_widget(self.no_button)
        self.home_button = ImageRoundButton(
            source='./assets/icons/home.png',
            size_hint=(0.1, 0.1),
            pos_hint={'x': 0.05, 'y': 0.85},
            background_color=(0.1294, 0.5882, 0.9529, 1),
        )
        self.home_button.bind(on_release=self.home_event)
        overlay_layout.add_widget(self.home_button)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ConfirmCaptureScreen: on_entry().')
        self._current_shot = kwargs.get('shot') if 'shot' in kwargs else 0
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        for i in range(0, self._current_shot + 1): self.icons[i].source = './assets/icons/camera_shot_on.png'
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

class ProcessingScreen(BackgroundScreen):
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

        # Display loading icon
        self.loading = RotatingImage(
            source='./assets/icons/loading.png',
            size_hint=(0.4, 0.4),
            pos_hint={'x': 0.3, 'y': 0.3},
        )

        self.layout = BoxLayout()
        self.layout.add_widget(self.loading)
        self.add_widget(self.layout)

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

class ConfirmSaveScreen(BackgroundScreen):
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

        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        # Display collage
        self.preview = BlurredImage(
            fit_mode='contain',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        overlay_layout.add_widget(self.preview)

        # Add buttons
        self.yes_button = ImageRoundButton(
            source='./assets/icons/save.png',
            size_hint=(0.1, 0.1),
            pos_hint={'x': 0.85, 'y': 0.05},
            background_color=(.4, .733, .416, 1),
        )
        self.yes_button.bind(on_release=self.yes_event)
        overlay_layout.add_widget(self.yes_button)
        self.no_button = ImageRoundButton(
            source='./assets/icons/trash.png',
            size_hint=(0.1, 0.1),
            pos_hint={'x': 0.05, 'y': 0.05},
            background_color=(.937, .325, .314, 1),
        )
        self.no_button.bind(on_release=self.no_event)
        overlay_layout.add_widget(self.no_button)

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

class ConfirmPrintScreen(BackgroundScreen):
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

        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')

        self.overlay_layout = FloatLayout()
        self.layout.add_widget(self.overlay_layout)

        # Display collage
        self.preview = BlurredImage(
            fit_mode='contain',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        self.overlay_layout.add_widget(self.preview)

        # Add buttons
        self.buttons_layout = FloatLayout()
        btn_once = ImageRoundButton(
            source='./assets/icons/print-1.png',
            size_hint=(0.1, 0.1),
            pos_hint={'x': 0.85, 'y': 0.20},
            background_color=(.4, .733, .416, 1),
        )
        btn_once.bind(on_release=self.print_once)
        self.buttons_layout.add_widget(btn_once)
        btn_twice = ImageRoundButton(
            source='./assets/icons/print-2.png',
            size_hint=(0.1, 0.1),
            pos_hint={'x': 0.85, 'y': 0.05},
            background_color=(.4, .733, .416, 1),
        )
        btn_twice.bind(on_release=self.print_twice)
        self.buttons_layout.add_widget(btn_twice)

        self.button_layout = FloatLayout()
        btn_print = ImageRoundButton(
            source='./assets/icons/print.png',
            size_hint=(0.1, 0.1),
            pos_hint={'x': 0.85, 'y': 0.05},
            background_color=(.4, .733, .416, 1),
        )
        btn_print.bind(on_release=self.print_once)
        self.button_layout.add_widget(btn_print)

        no_button = ImageRoundButton(
            source='./assets/icons/cancel.png',
            size_hint=(0.1, 0.1),
            pos_hint={'x': 0.05, 'y': 0.05},
            background_color=(.937, .325, .314, 1),
        )
        no_button.bind(on_release=self.no_event)
        self.overlay_layout.add_widget(no_button)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ConfirmPrintScreen: on_entry().')
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self.overlay_layout.remove_widget(self.button_layout)
        self.overlay_layout.remove_widget(self.buttons_layout)

        # Full page collage
        if self._current_format == 0:
            self.overlay_layout.add_widget(self.buttons_layout)
        # Strip collage
        elif self._current_format == 1:
            self.overlay_layout.add_widget(self.button_layout)
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

class PrintingScreen(BackgroundScreen):
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

        # Display loading icon
        self.loading = RotatingImage(
            source='./assets/icons/loading.png',
            size_hint=(0.4, 0.4),
            pos_hint={'x': 0.3, 'y': 0.3},
        )
        
        layout = BoxLayout()
        layout.add_widget(self.loading)
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
            return self.app.transition_to(ScreenMgr.ERROR, error='./assets/icons/error_printing.png')

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
        self.app.transition_to(ScreenMgr.ERROR, error='./assets/icons/error_printing_toolong.png')

class SuccessScreen(BackgroundScreen):
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

        icon = Image(
            source='./assets/icons/clap.zip', # TODO : Display gif (Use https://ezgif.com/split/ to convert gif to zip)
            fit_mode='contain',
            size_hint=(0.3, 0.3),
            pos_hint={'x': 0.35, 'y': 0.35},
            anim_delay=0.1
        )

        self.layout = BoxLayout()
        self.layout.add_widget(icon)
        self.add_widget(self.layout)

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

class CopyingScreen(BackgroundScreen):
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

        # Display loading icon
        loading = Image(
            source='./assets/icons/usb.png',
            size_hint=(0.4, 0.4),
            pos_hint={'x': 0.3, 'y': 0.3},
        )
        
        self.layout = BoxLayout()
        self.layout.add_widget(loading)
        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('CopyingScreen: on_entry().')
        self.app.ringled.wave([255, 255, 255])

    def on_exit(self, kwargs={}):
        Logger.info('CopyingScreen: on_exit().')
        self.app.ringled.clear()

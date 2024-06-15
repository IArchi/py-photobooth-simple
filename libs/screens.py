import random
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.graphics import Rectangle, Color, Line
from kivy.uix.image import Image, AsyncImage
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.core.window import Window

from libs.kivywidgets import *

XLARGE_FONT = '200sp'
LARGE_FONT = '70sp'
NORMAL_FONT = '50sp'
SMALL_FONT = '30sp'
TINY_FONT = '15sp'

class ScreenMgr(ScreenManager):
    """Screen Manager for the photobooth screens."""
    # Screen names.
    WAITING = 'waiting'
    READY = 'ready'
    SELECT_FORMAT = 'select_format'
    ERROR = 'error'
    COUNTDOWN = 'countdown'
    CHEESE = 'cheese'
    CONFIRM_CAPTURE = 'confirm_capture'
    PROCESSING = 'processing'
    CONFIRM_SAVE = 'confirm_save'
    CONFIRM_PRINT = 'confirm_print'
    PRINTING = 'printing'
    SUCCESS = 'success'
    COPYING = 'copying'

    def __init__(self, app, locales, **kwargs):
        Logger.info('ScreenMgr: __init__().')
        super(ScreenMgr, self).__init__(**kwargs)
        self.app = app
        self.pb_screens = {
            self.WAITING            : WaitingScreen(app, locales=locales, name=self.WAITING),
            self.SELECT_FORMAT      : SelectFormatScreen(app, locales=locales, name=self.SELECT_FORMAT),
            self.ERROR              : ErrorScreen(app, locales=locales, name=self.ERROR),
            self.READY              : ReadyScreen(app, locales=locales, name=self.READY),
            self.COUNTDOWN          : CountdownScreen(app, locales=locales, name=self.COUNTDOWN),
            self.CHEESE             : CheeseScreen(app, locales=locales, name=self.CHEESE),
            self.CONFIRM_CAPTURE    : ConfirmCaptureScreen(app, locales=locales, name=self.CONFIRM_CAPTURE),
            self.PROCESSING         : ProcessingScreen(app, locales=locales, name=self.PROCESSING),
            self.CONFIRM_SAVE       : ConfirmSaveScreen(app, locales=locales, name=self.CONFIRM_SAVE),
            self.CONFIRM_PRINT      : ConfirmPrintScreen(app, locales=locales, name=self.CONFIRM_PRINT),
            self.PRINTING           : PrintingScreen(app, locales=locales, name=self.PRINTING),
            self.SUCCESS            : SuccessScreen(app, locales=locales, name=self.SUCCESS),
            self.COPYING            : CopyingScreen(app, locales=locales, name=self.COPYING),
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
    def __init__(self, app, locales, **kwargs):
        Logger.info('WaitingScreen: __init__().')
        super(WaitingScreen, self).__init__(bg='./assets/backgrounds/bg_waiting.jpeg', **kwargs)

        self.app = app
        self.locales = locales

        overlay_layout = FloatLayout()

        start = BorderedLabel(
            text=self.locales['waiting']['action'],
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
            text=self.locales['waiting']['version'],
            font_size=TINY_FONT,
            halign='left',
            valign='middle',
            size_hint=(0.1, 0.05),
            pos_hint={'x': 0.9, 'y': 0.95},
        )
        overlay_layout.add_widget(version)

        overlay_layout.bind(on_touch_down=self.on_click)

        self.add_widget(overlay_layout)

    def on_entry(self, kwargs={}):
        Logger.info('WaitingScreen: on_entry().')
        self.app.ringled.start_rainbow()
        self.app.purge_tmp()

    def on_leave(self, kwargs={}):
        Logger.info('WaitingScreen: on_leave().')
        self.app.ringled.stop()

    def on_click(self, obj, pos):
        Logger.info('WaitingScreen: on_click().')
        self.app.transition_to(ScreenMgr.SELECT_FORMAT)
        return True

class SelectFormatScreen(BackgroundScreen):
    """
    +-----------------+
    |  Select format  |
    |                 |
    |                 |
    |                 |
    +-----------------+
    """
    def __init__(self, app, locales, **kwargs):
        Logger.info('SelectFormatScreen: __init__().')
        super(SelectFormatScreen, self).__init__(bg='./assets/backgrounds/bg_instructions.jpeg', **kwargs)

        self.app = app
        self.locales = locales

        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        title = Label(
            text=self.locales['select_format']['title'],
            font_size=LARGE_FONT,
            size_hint=(0.7, 0.2),
            padding=(30,30,30,30),
            pos_hint={'x': 0.15, 'y': 0.8},
        )
        overlay_layout.add_widget(title)

        # Add preview
        available_formats = self.app.get_layout_previews()
        self.preview_left = ImageButton(
            source=available_formats[0],
            size_hint=(0.3, 0.7),
            pos_hint={'x': 0.1, 'y': 0.05},
        )
        overlay_layout.add_widget(self.preview_left)
        self.preview_left.bind(on_release=self.on_click_left)
        self.preview_right = ImageButton(
            source=available_formats[1],
            size_hint=(0.3, 0.7),
            pos_hint={'x': 0.65, 'y': 0.05},
        )
        overlay_layout.add_widget(self.preview_right)
        self.preview_right.bind(on_release=self.on_click_right)

        # Add arrows
        arrow_left = Image(
            source='./assets/icons/arrow_left.png',
            fit_mode='contain',
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.45, 'y': 0.2},
        )
        overlay_layout.add_widget(arrow_left)
        arrow_right = Image(
            source='./assets/icons/arrow_right.png',
            fit_mode='contain',
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.45, 'y': 0.50},
        )
        overlay_layout.add_widget(arrow_right)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('SelectFormatScreen: on_entry().')
        self.preview_left.reload()
        self.preview_right.reload()
        self.app.ringled.start_rainbow()

    def on_leave(self, kwargs={}):
        Logger.info('SelectFormatScreen: on_leave().')
        self.app.ringled.stop()

    def on_click_left(self, x, y=0):
        Logger.info('SelectFormatScreen: on_click_left().')
        self.app.transition_to(ScreenMgr.READY, shot=0, format=0)

    def on_click_right(self, x, y=0):
        Logger.info('SelectFormatScreen: on_click_right().')
        self.app.transition_to(ScreenMgr.READY, shot=0, format=1)

class ErrorScreen(BackgroundScreen):
    """
    +-----------------+
    |  Error occured  |
    |    Continue     |
    +-----------------+
    """
    def __init__(self, app, locales, **kwargs):
        Logger.info('ErrorScreen: __init__().')
        super(ErrorScreen, self).__init__(**kwargs)

        self.app = app
        self.locales = locales

        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        # Display icon
        icon = Image(
            source='./assets/icons/error.png',
            fit_mode='contain',
            size_hint=(0.2, 0.2),
            pos_hint={'x': 0.4, 'y': 0.7},
        )
        overlay_layout.add_widget(icon)

        # Display message
        self.label = ShadowLabel(
            text=self.locales['error']['default'],
            halign='center',
            valign='top',
            font_size=NORMAL_FONT,
            size_hint=(0.8, 0.6),
            pos_hint={'x': 0.1, 'y': 0.2},
        )
        overlay_layout.add_widget(self.label)

        self.layout.bind(on_touch_down=self.on_click)
        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ErrorScreen: on_entry().')
        if 'error' in kwargs: self.label.text = "{}\nClick to continue".format(str(kwargs.get('error')))

    def on_leave(self, kwargs={}):
        Logger.info('ErrorScreen: on_leave().')

    def on_click(self, obj, pos):
        Logger.info('ErrorScreen: on_click().')
        self.app.transition_to(ScreenMgr.WAITING)
        return True

class ReadyScreen(BackgroundScreen):
    """
    +-----------------+
    |                 |
    |      Ready      |
    |                 |
    +-----------------+
    """
    def __init__(self, app, locales, **kwargs):
        Logger.info('ReadyScreen: __init__().')
        super(ReadyScreen, self).__init__(**kwargs)

        self.app = app
        self.locales = locales

        self.label = ShadowLabel(
            text=self.locales['ready']['content'][0],
            halign='center',
            valign='middle',
            font_size=LARGE_FONT
        )

        self.layout = BoxLayout()
        self.layout.add_widget(self.label)
        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ReadyScreen: on_entry().')
        self._current_shot = kwargs.get('shot') if 'shot' in kwargs else 0
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self.label.text = random.choice(self.locales['ready']['content'])
        self._clock = Clock.schedule_once(self.timer_event, 2)
        self.app.ringled.blink([255, 255, 255])

    def on_leave(self, kwargs={}):
        Logger.info('ReadyScreen: on_leave().')
        Clock.unschedule(self._clock)
        self.app.ringled.stop()

    def timer_event(self, obj):
        Logger.info('ReadyScreen: timer_event().')
        self.app.transition_to(ScreenMgr.COUNTDOWN, shot=self._current_shot, format=self._current_format)

class CountdownScreen(Screen):
    """
    +-----------------+
    |                 |
    |        5        |
    |                 |
    +-----------------+
    """
    def __init__(self, app, locales, **kwargs):
        Logger.info('CountdownScreen: __init__().')
        super(CountdownScreen, self).__init__(**kwargs)

        self.app = app
        self.locales = locales
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
        layout = BoxLayout()
        layout.add_widget(self.time_remaining_label)
        self.layout.add_widget(layout)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('CountdownScreen: on_entry().')
        self.time_remaining = self.app.COUNTDOWN
        self._current_shot = kwargs.get('shot') if 'shot' in kwargs else 0
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self.camera.start(self.app.is_square_format(self._current_format))
        self.time_remaining_label.text = str(self.time_remaining)
        self._clock = Clock.schedule_once(self.timer_event, 1)
        self.app.ringled.start_countdown(self.time_remaining)

    def on_leave(self, kwargs={}):
        Logger.info('CountdownScreen: on_leave().')
        Clock.unschedule(self._clock)
        self.app.ringled.stop()
        self.camera.stop()

    def timer_event(self, obj):
        Logger.info('CountdownScreen: timer_event(%s)', obj)
        self.time_remaining -= 1
        if self.time_remaining:
            self.time_remaining_label.text = str(self.time_remaining)
            Clock.schedule_once(self.timer_event, 1)
        else:
            self.app.transition_to(ScreenMgr.CHEESE, shot=self._current_shot, format=self._current_format)

class CheeseScreen(Screen):
    """
    +-----------------+
    |                 |
    |     Cheese!     |
    |                 |
    +-----------------+
    """
    def __init__(self, app, locales, **kwargs):
        Logger.info('CheeseScreen: __init__().')
        super(CheeseScreen, self).__init__(**kwargs)

        self.app = app
        self.locales = locales

        self.label = Label(
            text=self.locales['cheese']['content'][0],
            halign='center',
            valign='middle',
            font_size=LARGE_FONT
        )
        self.layout = BackgroundBoxLayout(
            background_color=(0,0,0,1),
        )
        self.layout.add_widget(self.label)
        self.add_widget(self.layout)

        self.wait_count = 0
        self._current_shot = 0
        self._current_format = 0

    def on_entry(self, kwargs={}):
        Logger.info('CheeseScreen: on_entry().')
        self._current_shot = kwargs.get('shot') if 'shot' in kwargs else 0
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0

        self.label.text = random.choice(self.locales['cheese']['content'])
        self.wait_idx = -1
        self.wait_count = 0
        self._clock = Clock.schedule_once(self.timer_event, 1.5)
        self._clock_trigger = Clock.schedule_once(self.timer_trigger, 1)

    def on_leave(self, kwargs={}):
        Logger.info('CheeseScreen: on_leave().')
        Clock.unschedule(self._clock)
        Clock.unschedule(self._clock_trigger)

    def timer_trigger(self, obj):
        # Make window full white
        self.layout.background_color=(1,1,1,1)
        self.layout.canvas.ask_update()

        # Trigger shot
        try:
            self.app.trigger_shot(self._current_shot, self._current_format)
        except Exception as e:
            raise e
            return self.app.transition_to(ScreenMgr.ERROR, error=self.locales['cheese']['error'])

    def timer_event(self, obj):
        Logger.info('CheeseScreen: timer_event().')
        # Make window back to black
        self.layout.background_color=(0,0,0,1)
        self.layout.canvas.ask_update()

        if not(self.app.is_shot_completed(self._current_shot)):
            self.label.text = self.locales['cheese']['wait']
            self._clock = Clock.schedule_once(self.timer_event, 1)
        elif self.app.get_shots_to_take(self._current_format) == 1:
            self.app.transition_to(ScreenMgr.PROCESSING, format=self._current_format)
        else:
            self.app.transition_to(ScreenMgr.CONFIRM_CAPTURE, shot=self._current_shot, format=self._current_format)

class ConfirmCaptureScreen(BackgroundScreen):
    """
    +-----------------+
    |      Keep ?     |
    |                 |
    | NO          YES |
    +-----------------+
    """
    def __init__(self, app, locales, **kwargs):
        Logger.info('ConfirmCaptureScreen: __init__().')
        super(ConfirmCaptureScreen, self).__init__(**kwargs)

        self.app = app
        self.locales = locales
        self._current_shot = 0
        self._current_format = 0
        self.time_remaining = 10

        # Display taken photo
        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        # Add title
        self.title = Label(
            text=self.locales['capture']['title'].format(1, 'n'),
            size_hint=(0.8, 0.1),
            pos_hint={'x': 0.1, 'y': 0.85},
            font_size=NORMAL_FONT,
        )
        overlay_layout.add_widget(self.title)

        # Display capture
        self.preview = Image(
            fit_mode='contain',
            size_hint=(1, 0.80),
            pos_hint={'x': 0, 'y': 0.05},
        )
        overlay_layout.add_widget(self.preview)

        # Add buttons
        self.yes_button = ImageLabelButton(
            source='./assets/icons/save.png',
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.8, 'y': 0.20},
            background_color=(.4, .733, .416, 1),
            text=self.locales['capture']['save'],
            text_color=[1, 1, 1, 1],
        )
        self.yes_button.bind(on_release=self.yes_event)
        overlay_layout.add_widget(self.yes_button)
        self.no_button = ImageLabelButton(
            source='./assets/icons/trash.png',
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.8, 'y': 0.05},
            background_color=(.937, .325, .314, 1),
            text=self.locales['capture']['trash'],
            text_color=[1, 1, 1, 1],
        )
        self.no_button.bind(on_release=self.no_event)
        overlay_layout.add_widget(self.no_button)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ConfirmCaptureScreen: on_entry().')
        self._current_shot = kwargs.get('shot') if 'shot' in kwargs else 0
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self.title.text=self.locales['capture']['title'].format(self._current_shot + 1, self.app.get_shots_to_take(self._current_format))
        self.time_remaining = 10
        self.preview.source = self.app.get_shot(self._current_shot)
        self.preview.reload()
        self.auto_leave = Clock.schedule_once(self.timer_event, 60)

    def on_leave(self, kwargs={}):
        Logger.info('ConfirmCaptureScreen: on_leave().')

    def yes_event(self, obj):
        Clock.unschedule(self.auto_leave)
        if self._current_shot == self.app.get_shots_to_take(self._current_format) - 1: self.app.transition_to(ScreenMgr.PROCESSING, format=self._current_format)
        else: self.app.transition_to(ScreenMgr.COUNTDOWN, shot=self._current_shot + 1, format=self._current_format)

    def no_event(self, obj):
        Clock.unschedule(self.auto_leave)
        self.app.transition_to(ScreenMgr.COUNTDOWN, shot=self._current_shot, format=self._current_format)

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
    def __init__(self, app, locales, **kwargs):
        Logger.info('ProcessingScreen: __init__().')
        super(ProcessingScreen, self).__init__(**kwargs)

        self.app = app
        self.locales = locales
        self._current_format = 0

        self.label = ShadowLabel(
            text=self.locales['processing']['content'][0],
            halign='center',
            valign='middle',
            font_size=LARGE_FONT
        )
        self.layout = BoxLayout()
        self.layout.add_widget(self.label)
        self.add_widget(self.layout)

        self.wait_idx = 0
        self.wait_count = 0

    def on_entry(self, kwargs={}):
        Logger.info('ProcessingScreen: on_entry().')
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self._clock = Clock.schedule_once(self.timer_event, 1)
        self.app.ringled.start_rainbow()

        # Perform collage
        self.app.trigger_collage(self._current_format)

    def on_leave(self, kwargs={}):
        Logger.info('ProcessingScreen: on_leave().')
        Clock.unschedule(self._clock)
        self.app.ringled.stop()

    def timer_event(self, obj):
        Logger.info('ProcessingScreen: timer_event().')
        if not(self.app.is_collage_completed()):
            self.wait_count += 1
            if self.wait_count % 3 == 0:
                self.wait_idx = (self.wait_idx + 1) % len(self.locales['processing']['content'])
                self.label.text = self.locales['processing']['content'][self.wait_idx]
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
    def __init__(self, app, locales, **kwargs):
        Logger.info('ConfirmSaveScreen: __init__().')
        super(ConfirmSaveScreen, self).__init__(**kwargs)

        self.app = app
        self.locales = locales

        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        # Add title
        title = Label(
            text=self.locales['save']['title'],
            size_hint=(0.8, 0.1),
            pos_hint={'x': 0.1, 'y': 0.85},
            font_size=NORMAL_FONT,
        )
        overlay_layout.add_widget(title)

        # Display collage
        self.preview = Image(
            fit_mode='contain',
            size_hint=(0.5, 0.75),
            pos_hint={'x': 0.1, 'y': 0.05},
        )
        overlay_layout.add_widget(self.preview)

        # Add buttons
        self.yes_button = ImageLabelButton(
            source='./assets/icons/save.png',
            size_hint=(0.15, 0.1),
            pos_hint={'x': 0.85, 'y': 0.25},
            background_color=(.4, .733, .416, 1),
            text=self.locales['save']['save'],
            text_color=[1, 1, 1, 1],
        )
        self.yes_button.bind(on_release=self.yes_event)
        overlay_layout.add_widget(self.yes_button)
        self.no_button = ImageLabelButton(
            source='./assets/icons/trash.png',
            size_hint=(0.15, 0.1),
            pos_hint={'x': 0.85, 'y': 0.05},
            background_color=(.937, .325, .314, 1),
            text=self.locales['save']['trash'],
            text_color=[1, 1, 1, 1],
        )
        self.no_button.bind(on_release=self.no_event)
        overlay_layout.add_widget(self.no_button)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ConfirmSaveScreen: on_entry().')
        self.auto_confirm = Clock.schedule_once(self.timer_event, 60)
        self.app.ringled.start_rainbow()
        self.preview.source = self.app.get_collage()
        self.preview.reload()

    def on_leave(self, kwargs={}):
        Logger.info('ConfirmSaveScreen: on_leave().')
        self.app.ringled.stop()

    def yes_event(self, obj):
        Clock.unschedule(self.auto_confirm)
        self.app.save_collage()
        self.app.transition_to(ScreenMgr.SUCCESS)

    def no_event(self, obj):
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
    def __init__(self, app, locales, **kwargs):
        Logger.info('ConfirmPrintScreen: __init__().')
        super(ConfirmPrintScreen, self).__init__(**kwargs)

        self.app = app
        self.locales = locales
        self._current_format = 0

        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        # Display collage
        self.preview = Image(
            fit_mode='contain',
            size_hint=(0.5, 0.75),
            pos_hint={'x': 0.1, 'y': 0.05},
        )
        overlay_layout.add_widget(self.preview)

        # Add title
        title = Label(
            text=self.locales['print']['title'],
            size_hint=(0.8, 0.1),
            pos_hint={'x': 0.1, 'y': 0.85},
            font_size=NORMAL_FONT,
        )
        overlay_layout.add_widget(title)

        # Add buttons
        self.btn_once = ImageLabelButton(
            source='./assets/icons/print-1.png',
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.8, 'y': 0.46},
            background_color=(.4, .733, .416, 1),
            text=self.locales['print']['one_copy'],
            text_color=[1, 1, 1, 1],
        )
        self.btn_once.bind(on_release=self.print_once)
        overlay_layout.add_widget(self.btn_once)
        self.btn_twice = ImageLabelButton(
            source='./assets/icons/print-2.png',
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.8, 'y': 0.33},
            background_color=(.4, .733, .416, 1),
            text=self.locales['print']['two_copies'],
            text_color=[1, 1, 1, 1],
        )
        self.btn_twice.bind(on_release=self.print_twice)
        overlay_layout.add_widget(self.btn_twice)
        self.btn_3times = ImageLabelButton(
            source='./assets/icons/print-3.png',
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.8, 'y': 0.20},
            background_color=(.4, .733, .416, 1),
            text=self.locales['print']['three_copies'],
            text_color=[1, 1, 1, 1],
        )
        self.btn_3times.bind(on_release=self.print_3times)
        overlay_layout.add_widget(self.btn_3times)
        self.no_button = ImageLabelButton(
            source='./assets/icons/cancel.png',
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.8, 'y': 0.05},
            background_color=(.937, .325, .314, 1),
            text=self.locales['print']['no'],
            text_color=[1, 1, 1, 1],
        )
        self.no_button.bind(on_release=self.no_event)
        overlay_layout.add_widget(self.no_button)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ConfirmPrintScreen: on_entry().')
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self.auto_decline = Clock.schedule_once(self.timer_event, 60)
        self.app.ringled.start_rainbow()
        self.preview.source = self.app.get_collage()
        self.preview.reload()
        self.app.save_collage()

    def on_leave(self, kwargs={}):
        Logger.info('ConfirmPrintScreen: on_leave().')
        self.app.ringled.stop()

    def print_once(self, obj):
        Clock.unschedule(self.auto_decline)
        self.app.transition_to(ScreenMgr.PRINTING, copies=1, format=self._current_format)

    def print_twice(self, obj):
        Clock.unschedule(self.auto_decline)
        self.app.transition_to(ScreenMgr.PRINTING, copies=2, format=self._current_format)

    def print_3times(self, obj):
        Clock.unschedule(self.auto_decline)
        self.app.transition_to(ScreenMgr.PRINTING, copies=3, format=self._current_format)

    def no_event(self, obj):
        Clock.unschedule(self.auto_decline)
        self.app.transition_to(ScreenMgr.WAITING)

    def timer_event(self, obj):
        Logger.info('ConfirmPrintScreen: timer_event().')
        self.app.transition_to(ScreenMgr.WAITING)

class PrintingScreen(BackgroundScreen):
    """
    +-----------------+
    |                 |
    |   Printing...   |
    |                 |
    +-----------------+
    """
    def __init__(self, app, locales, **kwargs):
        Logger.info('PrintingScreen: __init__().')
        super(PrintingScreen, self).__init__(**kwargs)

        self.app = app
        self.locales = locales
        self._current_format = 0

        self.status = ShadowLabel(
            text=self.locales['printing']['content'][0],
            halign='center',
            valign='middle',
            font_size=LARGE_FONT
        )
        layout = BoxLayout()
        layout.add_widget(self.status)
        self.add_widget(layout)

        self.wait_idx = 0
        self.wait_count = 0
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
            self._clock = Clock.schedule_once(self.timer_event, 1)
            self._auto_cancel = Clock.schedule_once(self.timer_toolong, 30)
        except:
            return self.app.transition_to(ScreenMgr.ERROR, error=self.locales['printing']['error'])

    def on_leave(self, kwargs={}):
        Logger.info('PrintingScreen: on_leave().')
        if self._clock: Clock.unschedule(self._clock)
        if self._auto_cancel: Clock.unschedule(self._auto_cancel)
        self.app.ringled.stop()

    def timer_event(self, obj):
        Logger.info('PrintingScreen: timer_event().')
        if not self.app.is_print_completed(self._print_task_id):
            self.wait_count += 1
            if self.wait_count % 3 == 0:
                self.wait_idx = (self.wait_idx + 1) % len(self.locales['printing']['content'])
                self.status.text = self.locales['printing']['content'][self.wait_idx]
            self._clock = Clock.schedule_once(self.timer_event, 1)
        else:
            if self._clock: Clock.unschedule(self._clock)
            if self._auto_cancel: Clock.unschedule(self._auto_cancel)
            self.app.transition_to(ScreenMgr.SUCCESS)

    def timer_toolong(self, obj):
        Logger.info('PrintingScreen: timer_toolong().')
        self.app.transition_to(ScreenMgr.ERROR, error=self.locales['printing']['error_toolong'])

class SuccessScreen(BackgroundScreen):
    """
    +-----------------+
    |                 |
    |    Perfect !    |
    |                 |
    +-----------------+
    """
    def __init__(self, app, locales, **kwargs):
        Logger.info('SuccessScreen: __init__().')
        super(SuccessScreen, self).__init__(**kwargs)

        self.app = app
        self.locales = locales

        self.label = ShadowLabel(
            text=self.locales['success']['content'][0],
            halign='center',
            valign='middle',
            font_size=LARGE_FONT
        )

        self.layout = BoxLayout()
        self.layout.add_widget(self.label)
        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('SuccessScreen: on_entry().')
        self.label.text = random.choice(self.locales['success']['content'])
        self._clock = Clock.schedule_once(self.timer_event, 2)
        self.app.ringled.blink([255, 255, 255])

    def on_leave(self, kwargs={}):
        Logger.info('SuccessScreen: on_leave().')
        Clock.unschedule(self._clock)
        self.app.ringled.stop()

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
    def __init__(self, app, locales, **kwargs):
        Logger.info('CopyingScreen: __init__().')
        super(CopyingScreen, self).__init__(**kwargs)

        self.app = app
        self.locales = locales
        self._count = 0

        self.label = ShadowLabel(
            text=self.locales['copying']['content'],
            halign='center',
            valign='middle',
            font_size=LARGE_FONT
        )
        self.layout = BoxLayout()
        self.layout.add_widget(self.label)
        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('CopyingScreen: on_entry().')
        self.app.ringled.start_rainbow()
        self._clock = Clock.schedule_once(self.timer_event, 1)

    def on_leave(self, kwargs={}):
        Logger.info('CopyingScreen: on_leave().')
        Clock.unschedule(self._clock)
        self.app.ringled.stop()

    def timer_event(self, obj):
        Logger.info('CopyingScreen: timer_event().')
        self._count += 1
        self._count = self._count % 3
        self.label.text = self.locales['copying']['content'] + ('.' * self._count)

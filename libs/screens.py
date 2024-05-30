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

from libs.kivywidgets import KivyCamera, ImageButton, BorderedLabel

XLARGE_FONT = 400
LARGE_FONT = 130
NORMAL_FONT = 80
SMALL_FONT = 50
TINY_FONT = 30

BACKGROUND_PINK_100 = (0.97, 0.73, 0.81, 1)

class ScreenMgr(ScreenManager):
    """Screen Manager for the photobooth screens."""
    # Screen names.
    WAITING = 'waiting'
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

    def __init__(self, app, locales, **kwargs):
        Logger.info('ScreenMgr: __init__().')
        super(ScreenMgr, self).__init__(**kwargs)
        self.app = app
        self.pb_screens = {
            self.WAITING            : WaitingScreen(app, locales=locales, name=self.WAITING),
            self.SELECT_FORMAT       : SelectFormatScreen(app, locales=locales, name=self.SELECT_FORMAT),
            self.ERROR              : ErrorScreen(app, locales=locales, name=self.ERROR),
            self.COUNTDOWN          : CountdownScreen(app, locales=locales, name=self.COUNTDOWN),
            self.CHEESE             : CheeseScreen(app, locales=locales, name=self.CHEESE),
            self.CONFIRM_CAPTURE    : ConfirmCaptureScreen(app, locales=locales, name=self.CONFIRM_CAPTURE),
            self.PROCESSING         : ProcessingScreen(app, locales=locales, name=self.PROCESSING),
            self.CONFIRM_SAVE       : ConfirmSaveScreen(app, locales=locales, name=self.CONFIRM_SAVE),
            self.CONFIRM_PRINT      : ConfirmPrintScreen(app, locales=locales, name=self.CONFIRM_PRINT),
            self.PRINTING           : PrintingScreen(app, locales=locales, name=self.PRINTING),
            self.SUCCESS            : SuccessScreen(app, locales=locales, name=self.SUCCESS)
        }
        for screen in self.pb_screens.values(): self.add_widget(screen)

        self.current = self.WAITING
        if self.app.FULLSCREEN: Window.fullscreen = True

class BackgroundScreen(Screen):
    def __init__(self, bg='./assets/backgrounds/background0.jpeg', **kwargs):
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

    def on_entry(self, *args):
        Logger.info('WaitingScreen: on_entry().')
        self.app.ringled.start_rainbow()

    def on_leave(self, *args):
        Logger.info('WaitingScreen: on_leave().')
        self.app.ringled.stop()

    def on_click(self, obj, pos):
        Logger.info('WaitingScreen: on_click(%s).', obj)
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
    def __init__(self, app, locales, **kwargs):
        Logger.info('SelectFormatScreen: __init__().')
        super(SelectFormatScreen, self).__init__(bg='./assets/backgrounds/bg_instructions.jpeg', **kwargs)

        self.app = app
        self.locales = locales

        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        title = BorderedLabel(
            text=self.locales['select_format']['title'],
            font_size=LARGE_FONT,
            border_color=(1,1,1,1),
            border_width=5,
            size_hint=(0.7, 0.2),
            padding=(30,30,30,30),
            pos_hint={'x': 0.15, 'y': 0.75},
        )
        overlay_layout.add_widget(title)

        # Add preview
        available_formats = self.app.get_layout_previews()
        preview_left = ImageButton(
            source=available_formats[0],
            fit_mode='contain',
            size_hint=(0.2, 0.7),
            pos_hint={'x': 0.75, 'y': 0.02},
        )
        overlay_layout.add_widget(preview_left)
        preview_left.bind(on_release=self.on_click_left)
        preview_right = ImageButton(
            source=available_formats[1],
            fit_mode='contain',
            size_hint=(0.4, 0.7),
            pos_hint={'x': 0.05, 'y': 0.02},
        )
        overlay_layout.add_widget(preview_right)
        preview_right.bind(on_release=self.on_click_right)

        # Add arrows
        arrow_left = Image(
            source='./assets/icons/arrow_left.png',
            fit_mode='contain',
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.5, 'y': 0.38},
        )
        overlay_layout.add_widget(arrow_left)
        arrow_right = Image(
            source='./assets/icons/arrow_right.png',
            fit_mode='contain',
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.5, 'y': 0.50},
        )
        overlay_layout.add_widget(arrow_right)

        self.add_widget(self.layout)

    def on_entry(self, *args):
        Logger.info('SelectFormatScreen: on_entry().')
        self.app.ringled.start_rainbow()

    def on_leave(self, *args):
        Logger.info('SelectFormatScreen: on_leave().')
        self.app.ringled.stop()

    def on_click_left(self, x, y=0):
        Logger.info('SelectFormatScreen: on_click_left().')
        self.app.transition_to(ScreenMgr.COUNTDOWN, 0, 0)

    def on_click_right(self, x, y=0):
        Logger.info('SelectFormatScreen: on_click_right().')
        self.app.transition_to(ScreenMgr.COUNTDOWN, 0, 1)

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

        self.continue_button = Button(
            text=self.locales['error']['default'],
            halign='center',
            valign='middle',
            font_size=LARGE_FONT,
            background_color=(0, 0, 1, 1)
        )
        self.continue_button.bind(on_release=self.on_click_continue)

        self.layout = BoxLayout()
        self.layout.add_widget(self.continue_button)
        self.add_widget(self.layout)

    def on_entry(self, *args):
        Logger.info('ErrorScreen: on_entry().')
        if len(args): self.continue_button.text = "{}\nClick to continue".format(str(args[0]))

    def on_leave(self, *args):
        Logger.info('ErrorScreen: on_leave().')

    def set_error(self, label):
        self.continue_button.text = self.locales['error']['content'].format(label)

    def on_click_continue(self, obj):
        Logger.info('ErrorScreen: on_click_continue(%s).', obj)
        self.app.transition_to(ScreenMgr.WAITING)

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
        self.time_remaining_label = Label(
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

    def on_entry(self, *args):
        Logger.info('CountdownScreen: on_entry().')
        self.camera.start()
        self.time_remaining = self.app.COUNTDOWN
        self._current_shot = int(args[0][0]) if len(args) and len(args[0]) else 0
        self._current_format = int(args[0][1]) if len(args) and len(args[0]) else 0
        self.time_remaining_label.text = str(self.time_remaining)
        self._clock = Clock.schedule_once(self.timer_event, 1)
        self.app.ringled.start_countdown(self.time_remaining)

    def on_leave(self, *args):
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
            self.app.transition_to(ScreenMgr.CHEESE, self._current_shot, self._current_format)

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

        self.smile_label = Label(
            text=self.locales['cheese']['content'][0],
            halign='center',
            valign='middle',
            font_size=XLARGE_FONT
        )
        self.layout = BoxLayout()
        self.layout.add_widget(self.smile_label)
        self.add_widget(self.layout)

        self.wait_count = 0
        self._current_shot = 0
        self._current_format = 0

    def on_entry(self, *args):
        Logger.info('CheeseScreen: on_entry().')
        if len(args) == 0: return self.app.transition_to(ScreenMgr.ERROR, self.locales['cheese']['error_args'])
        self._current_shot = int(args[0][0]) if len(args) and len(args[0]) else 0
        self._current_format = int(args[0][1]) if len(args) and len(args[0]) else 0

        self.smile_label.font_size = LARGE_FONT
        self.smile_label.text = random.choice(self.locales['cheese']['content'])
        self.wait_idx = -1
        self.wait_count = 0
        self._clock = Clock.schedule_once(self.timer_event, 2)

        # Trigger shot
        try:
            self.app.ringled.flash()
            self.app.trigger_shot(self._current_shot)
        except:
            return self.app.transition_to(ScreenMgr.ERROR, self.locales['cheese']['error_camera'])

    def on_leave(self, *args):
        Logger.info('CheeseScreen: on_leave().')
        Clock.unschedule(self._clock)

    def timer_event(self, obj):
        Logger.info('CheeseScreen: timer_event().')
        if not(self.app.is_shot_completed(self._current_shot)):
            self.smile_label.font_size = SMALL_FONT
            self.smile_label.text = self.locales['cheese']['wait']
            self._clock = Clock.schedule_once(self.timer_event, 1)
        elif self.app.get_shots_to_take(self._current_format) == 1:
            self.app.transition_to(ScreenMgr.PROCESSING, self._current_format)
        else:
            self.app.transition_to(ScreenMgr.CONFIRM_CAPTURE, self._current_shot, self._current_format)

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
        self.preview = Image(fit_mode='contain')
        self.layout.add_widget(self.preview)

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        self.title = Button(
            text=self.locales['capture']['title'].format(1, self.app.get_shots_to_take(self._current_format)), # On la garde ?
            border=(30, 30, 30, 30),
            size_hint=(0.8, 0.1),
            pos_hint={'x': 0.1, 'y': 0.8},
            font_size=NORMAL_FONT,
            background_normal='assets/title.png', background_down='assets/title.png'
        )
        overlay_layout.add_widget(self.title)

        self.yes_button = Button(text=self.locales['capture']['yes'].format(self.time_remaining), font_size=SMALL_FONT, background_normal='assets/green_normal.png', background_down='assets/green_down.png', border=(30, 30, 30, 30), size_hint=(0.2, 0.1), pos_hint={'x': 0.05, 'y': 0.1},)
        self.yes_button.bind(on_release=self.yes_event)
        overlay_layout.add_widget(self.yes_button)

        self.no_button = Button(text=self.locales['capture']['no'], font_size=SMALL_FONT, background_normal='assets/red_normal.png', background_down='assets/red_down.png', border=(30, 30, 30, 30), size_hint=(0.2, 0.1), pos_hint={'x': 0.75, 'y': 0.1})
        self.no_button.bind(on_release=self.no_event)
        overlay_layout.add_widget(self.no_button)

        self.add_widget(self.layout)

    def on_entry(self, *args):
        Logger.info('ConfirmCaptureScreen: on_entry().')
        if len(args) == 0 or len(args[0]) == 0: return self.app.transition_to(ScreenMgr.ERROR, self.locales['capture']['error_args'])
        self._current_shot = int(args[0][0]) if len(args) and len(args[0]) else 0
        self._current_format = int(args[0][1]) if len(args) and len(args[0]) else 0
        self.time_remaining = 10
        self.title.text = self.locales['capture']['title'].format(self._current_shot + 1, self.app.get_shots_to_take(self._current_format))
        self.yes_button.text = self.locales['capture']['yes'].format(self.time_remaining)
        self.preview.source = self.app.get_shot(self._current_shot)
        self.preview.reload()
        self.auto_confirm = Clock.schedule_once(self.timer_event, 10)
        self._clock = Clock.schedule_once(self.tick_event, 1)

    def on_leave(self, *args):
        Logger.info('ConfirmCaptureScreen: on_leave().')
        Clock.unschedule(self._clock)

    def yes_event(self, obj):
        Clock.unschedule(self.auto_confirm)
        Clock.unschedule(self._clock)
        if self._current_shot == self.app.get_shots_to_take(self._current_format) - 1: self.app.transition_to(ScreenMgr.PROCESSING, self._current_format)
        else: self.app.transition_to(ScreenMgr.COUNTDOWN, self._current_shot + 1, self._current_format)

    def no_event(self, obj):
        Clock.unschedule(self.auto_confirm)
        Clock.unschedule(self._clock)
        self.app.transition_to(ScreenMgr.COUNTDOWN, self._current_shot, self._current_format)

    def tick_event(self, obj):
        self.time_remaining -= 1
        self.yes_button.text = self.locales['capture']['yes'].format(self.time_remaining)
        self._clock = Clock.schedule_once(self.tick_event, 1)

    def timer_event(self, obj):
        Logger.info('ConfirmCaptureScreen: timer_event().')
        if self._current_shot == self.app.get_shots_to_take() - 1: self.app.transition_to(ScreenMgr.PROCESSING, self._current_format)
        else: self.app.transition_to(ScreenMgr.COUNTDOWN, self._current_shot + 1, self._current_format)

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

        self.smile_label = Label(
            text=self.locales['processing']['content'][0],
            halign='center',
            valign='middle',
            font_size=LARGE_FONT
        )
        self.layout = BoxLayout()
        self.layout.add_widget(self.smile_label)
        self.add_widget(self.layout)

        self.wait_idx = 0
        self.wait_count = 0

    def on_entry(self, *args):
        Logger.info('ProcessingScreen: on_entry().')
        self._current_format = int(args[0][0]) if len(args) and len(args[0]) else 0
        self._clock = Clock.schedule_once(self.timer_event, 1)
        self.app.ringled.start_rainbow()

        # Perform collage
        self.app.trigger_collage(self._current_format)

    def on_leave(self, *args):
        Logger.info('ProcessingScreen: on_leave().')
        Clock.unschedule(self._clock)
        self.app.ringled.stop()

    def timer_event(self, obj):
        Logger.info('ProcessingScreen: timer_event().')
        if not(self.app.is_collage_completed()):
            self.wait_count += 1
            if self.wait_count % 3 == 0:
                self.wait_idx = (self.wait_idx + 1) % len(self.locales['processing']['content'])
                self.smile_label.font_size = SMALL_FONT
                self.smile_label.text = self.locales['processing']['content'][self.wait_idx]
            self._clock = Clock.schedule_once(self.timer_event, 1)
        elif self.app.has_printer():
            self.app.transition_to(ScreenMgr.CONFIRM_PRINT, self._current_format)
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
        self.time_remaining = 20

        # Display collage
        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')
        self.preview = Image(fit_mode='contain')
        self.layout.add_widget(self.preview)

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        title = Button(
            text=self.locales['save']['title'], # On les garde ?
            border=(30, 30, 30, 30),
            size_hint=(0.8, 0.1),
            pos_hint={'x': 0.1, 'y': 0.8},
            font_size=NORMAL_FONT,
            background_normal='assets/title.png', background_down='assets/title.png'
        )
        overlay_layout.add_widget(title)

        self.yes_button = Button(text=self.locales['save']['yes'].format(self.time_remaining), font_size=SMALL_FONT, background_normal='assets/green_normal.png', background_down='assets/green_down.png', border=(30, 30, 30, 30), size_hint=(0.2, 0.1), pos_hint={'x': 0.05, 'y': 0.1},)
        self.yes_button.bind(on_release=self.yes_event)
        overlay_layout.add_widget(self.yes_button)

        self.no_button = Button(text=self.locales['save']['no'], font_size=SMALL_FONT, background_normal='assets/red_normal.png', background_down='assets/red_down.png', border=(30, 30, 30, 30), size_hint=(0.2, 0.1), pos_hint={'x': 0.75, 'y': 0.1})
        self.no_button.bind(on_release=self.no_event)
        overlay_layout.add_widget(self.no_button)

        self.add_widget(self.layout)

    def on_entry(self, *args):
        Logger.info('ConfirmSaveScreen: on_entry().')
        self.auto_confirm = Clock.schedule_once(self.timer_event, 20)
        self._clock = Clock.schedule_once(self.tick_event, 1)
        self.app.ringled.start_rainbow()
        self.preview.source = self.app.get_collage()
        self.time_remaining = 20
        self.yes_button.text = self.locales['save']['yes'].format(self.time_remaining)

    def on_leave(self, *args):
        Logger.info('ConfirmSaveScreen: on_leave().')
        self.app.ringled.stop()
        Clock.unschedule(self._clock)

    def yes_event(self, obj):
        Clock.unschedule(self.auto_confirm)
        Clock.unschedule(self._clock)
        self.app.save_collage()
        self.app.transition_to(ScreenMgr.SUCCESS)

    def no_event(self, obj):
        Clock.unschedule(self.auto_confirm)
        Clock.unschedule(self._clock)
        if self.app.get_shots_to_take() == 1: self.app.transition_to(ScreenMgr.WAITING)
        else: self.app.transition_to(ScreenMgr.SUCCESS)

    def tick_event(self, obj):
        self.time_remaining -= 1
        self.yes_button.text = self.locales['save']['yes'].format(self.time_remaining)
        self._clock = Clock.schedule_once(self.tick_event, 1)

    def timer_event(self, obj):
        Logger.info('ConfirmSaveScreen: timer_event().')
        Clock.unschedule(self.auto_confirm)
        Clock.unschedule(self._clock)
        self.app.save_collage()
        self.app.transition_to(ScreenMgr.SUCCESS)

class ConfirmPrintScreen(BackgroundScreen):
    """
    +-----------------+
    |      Print ?    |
    |                 |
    | NO          YES |
    +-----------------+
    """
    # TODO : Add copies with 3 buttons (1, 2, 3 or Ignore)
    def __init__(self, app, locales, **kwargs):
        Logger.info('ConfirmPrintScreen: __init__().')
        super(ConfirmPrintScreen, self).__init__(**kwargs)

        self.app = app
        self.locales = locales
        self.time_remaining = 10
        self._current_format = 0

        # Display collage
        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')
        self.preview = Image(fit_mode='contain')
        self.layout.add_widget(self.preview)

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        title = Button(
            text=self.locales['print']['title'], # On l'imprime ?
            border=(30, 30, 30, 30),
            size_hint=(0.8, 0.1),
            pos_hint={'x': 0.1, 'y': 0.8},
            font_size=NORMAL_FONT,
            background_normal='assets/title.png', background_down='assets/title.png'
        )
        overlay_layout.add_widget(title)

        btn_once = Button(
            text=self.locales['print']['one_copy'],
            font_size=SMALL_FONT,
            background_normal='assets/green_normal.png', background_down='assets/green_down.png',
            border=(30, 30, 30, 30),
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.05, 'y': 0.1}
        )
        btn_once.bind(on_release=self.print_once)
        overlay_layout.add_widget(btn_once)

        btn_twice = Button(
            text=self.locales['print']['two_copies'],
            font_size=SMALL_FONT,
            background_normal='assets/green_normal.png', background_down='assets/green_down.png',
            border=(30, 30, 30, 30),
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.05, 'y': 0.25}
        )
        btn_twice.bind(on_release=self.print_twice)
        overlay_layout.add_widget(btn_twice)

        btn_3times = Button(
            text=self.locales['print']['three_copies'],
            font_size=SMALL_FONT,
            background_normal='assets/green_normal.png', background_down='assets/green_down.png',
            border=(30, 30, 30, 30),
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.05, 'y': 0.4}
        )
        btn_3times.bind(on_release=self.print_3times)
        overlay_layout.add_widget(btn_3times)

        self.no_button = Button(text=self.locales['print']['no'].format(self.time_remaining), font_size=SMALL_FONT, background_normal='assets/red_normal.png', background_down='assets/red_down.png', border=(30, 30, 30, 30), size_hint=(0.2, 0.1), pos_hint={'x': 0.75, 'y': 0.1})
        self.no_button.bind(on_release=self.no_event)
        overlay_layout.add_widget(self.no_button)

        self.add_widget(self.layout)

    def on_entry(self, *args):
        Logger.info('ConfirmPrintScreen: on_entry().')
        self._current_format = int(args[0][0]) if len(args) and len(args[0]) else 0
        self.auto_decline = Clock.schedule_once(self.timer_event, 10)
        self._clock = Clock.schedule_once(self.tick_event, 1)
        self.app.ringled.start_rainbow()
        self.preview.source = self.app.get_collage()
        self.time_remaining = 10
        self.no_button.text = self.locales['print']['no'].format(self.time_remaining)
        self.app.save_collage()

    def on_leave(self, *args):
        Logger.info('ConfirmPrintScreen: on_leave().')
        self.app.ringled.stop()
        Clock.unschedule(self._clock)

    def print_once(self, obj):
        Clock.unschedule(self.auto_decline)
        Clock.unschedule(self._clock)
        self.app.transition_to(ScreenMgr.PRINTING, 1, self._current_format)

    def print_twice(self, obj):
        Clock.unschedule(self.auto_decline)
        Clock.unschedule(self._clock)
        self.app.transition_to(ScreenMgr.PRINTING, 2, self._current_format)

    def print_3times(self, obj):
        Clock.unschedule(self.auto_decline)
        Clock.unschedule(self._clock)
        self.app.transition_to(ScreenMgr.PRINTING, 3, self._current_format)

    def no_event(self, obj):
        Clock.unschedule(self.auto_decline)
        Clock.unschedule(self._clock)
        if self.app.get_shots_to_take(self._current_format) == 1: self.app.transition_to(ScreenMgr.WAITING)
        else: self.app.transition_to(ScreenMgr.SUCCESS)

    def tick_event(self, obj):
        self.time_remaining -= 1
        self.no_button.text = self.locales['print']['no'].format(self.time_remaining)
        self._clock = Clock.schedule_once(self.tick_event, 1)

    def timer_event(self, obj):
        Logger.info('ConfirmPrintScreen: timer_event().')
        if self.app.get_shots_to_take(self._current_format) == 1: self.app.transition_to(ScreenMgr.WAITING)
        else: self.app.transition_to(ScreenMgr.SUCCESS)

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

        self.status = Label(
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

    def on_entry(self, *args):
        Logger.info('PrintingScreen: on_entry().')
        self.app.ringled.start_rainbow()
        copies = int(args[0][0]) if len(args) and len(args[0]) else 1
        self._current_format = int(args[0][1]) if len(args) and len(args[0]) else 0

        # Trigger print
        try:
            self._print_task_id = self.app.trigger_print(copies, self._current_format)
            self._clock = Clock.schedule_once(self.timer_event, 1)
        except:
            return self.app.transition_to(ScreenMgr.ERROR, self.locales['printing']['error'])

    def on_leave(self, *args):
        Logger.info('PrintingScreen: on_leave().')
        Clock.unschedule(self._clock)
        self.app.ringled.stop()

    def timer_event(self, obj):
        Logger.info('PrintingScreen: timer_event().')
        if not self.app.is_print_completed(self._print_task_id):
            self.wait_count += 1
            if self.wait_count % 3 == 0:
                self.wait_idx = (self.wait_idx + 1) % len(self.locales['printing']['content'])
                self.status.font_size = SMALL_FONT
                self.status.text = self.locales['printing']['content'][self.wait_idx]
            self._clock = Clock.schedule_once(self.timer_event, 1)
        else:
            self.app.transition_to(ScreenMgr.SUCCESS)

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

        self.start_button = Button(
            text=self.locales['success']['content'][0],
            halign='center',
            valign='middle',
            font_size=LARGE_FONT,
            background_color=(0, 0, 1, 1)
        )
        self.start_button.bind(on_release=self.on_click_start)

        self.layout = BoxLayout()
        self.layout.add_widget(self.start_button)
        self.add_widget(self.layout)

    def on_entry(self, *args):
        Logger.info('SuccessScreen: on_entry().')
        self.start_button.text = random.choice(self.locales['success']['content'])
        self._clock = Clock.schedule_once(self.timer_event, 5)
        self.app.ringled.blink((0, 255, 0, 0))

    def on_leave(self, *args):
        Logger.info('SuccessScreen: on_leave().')
        Clock.unschedule(self._clock)
        self.app.ringled.stop()

    def on_click_start(self, obj):
        Logger.info('SuccessScreen: on_click_start(%s).', obj)
        self.app.transition_to(ScreenMgr.WAITING)

    def timer_event(self, obj):
        Logger.info('SuccessScreen: timer_event().')
        self.app.transition_to(ScreenMgr.WAITING)

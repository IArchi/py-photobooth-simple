import random
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.image import Image, AsyncImage
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.core.window import Window

from libs.kivycamera import KivyCamera

XLARGE_FONT = 400
LARGE_FONT = 130
NORMAL_FONT = 80
SMALL_FONT = 50

class ScreenMgr(ScreenManager):
    """Screen Manager for the photobooth screens."""
    # Screen names.
    WAITING = 'waiting'
    INSTRUCTIONS = 'instructions'
    ERROR = 'error'
    COUNTDOWN = 'countdown'
    CHEESE = 'cheese'
    CONFIRM_CAPTURE = 'confirm_capture'
    PROCESSING = 'processing'
    CONFIRM_SAVE = 'confirm_save'
    CONFIRM_PRINT = 'confirm_print'
    PRINTING = 'printing'
    SUCCESS = 'success'

    def __init__(self, app, **kwargs):
        Logger.info('ScreenMgr: __init__().')
        super(ScreenMgr, self).__init__(**kwargs)
        self.app = app
        self.pb_screens = {
            self.WAITING            : WaitingScreen(app, name=self.WAITING),
            self.INSTRUCTIONS       : InstructionsScreen(app, name=self.INSTRUCTIONS),
            self.ERROR              : ErrorScreen(app, name=self.ERROR),
            self.COUNTDOWN          : CountdownScreen(app, name=self.COUNTDOWN),
            self.CHEESE             : CheeseScreen(app, name=self.CHEESE),
            self.CONFIRM_CAPTURE    : ConfirmCaptureScreen(app, name=self.CONFIRM_CAPTURE),
            self.PROCESSING         : ProcessingScreen(app, name=self.PROCESSING),
            self.CONFIRM_SAVE       : ConfirmSaveScreen(app, name=self.CONFIRM_SAVE),
            self.CONFIRM_PRINT      : ConfirmPrintScreen(app, name=self.CONFIRM_PRINT),
            self.PRINTING           : PrintingScreen(app, name=self.PRINTING),
            self.SUCCESS            : SuccessScreen(app, name=self.SUCCESS)
        }
        for screen in self.pb_screens.values(): self.add_widget(screen)

        self.current = self.WAITING
        Window.fullscreen = True

class WaitingScreen(Screen):
    """
    +-----------------+
    |                 |
    | Press to begin  |
    |                 |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('WaitingScreen: __init__().')
        super(WaitingScreen, self).__init__(**kwargs)

        self.app = app
        self.start_button = Button(
            text='Press to begin',
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
        Logger.info('WaitingScreen: on_entry().')
        self.app.ringled.start_rainbow()

    def on_leave(self, *args):
        Logger.info('WaitingScreen: on_leave().')
        self.app.ringled.stop()

    def on_click_start(self, obj):
        Logger.info('WaitingScreen: on_click_start(%s).', obj)
        self.app.transition_to(ScreenMgr.INSTRUCTIONS)

class InstructionsScreen(Screen):
    """
    +-----------------+
    |   Instructions  |
    |                 |
    |                 |
    |                 |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('InstructionsScreen: __init__().')
        super(InstructionsScreen, self).__init__(**kwargs)

        self.app = app

        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')
        #self.preview = Image(fit_mode='contain')
        #self.layout.add_widget(self.preview)
        self.layout.bind(on_touch_down=self.on_click)

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        title = Button(
            text='Instructions',
            border=(30, 30, 30, 30),
            size_hint=(0.8, 0.1),
            pos_hint={'x': 0.1, 'y': 0.8},
            font_size=NORMAL_FONT,
            background_normal='assets/title.png', background_down='assets/title.png'
        )
        overlay_layout.add_widget(title)

        instructions = Label(
            text='Lorem ipsum\ndolor sit amet\nLorem ipsum\ndolor sit amet\nLorem ipsum\ndolor sit amet\nLorem ipsum\ndolor sit amet',
            size_hint=(0.6, 0.6),
            pos_hint={'x': 0.1, 'y': 0.3},
            font_size=SMALL_FONT,
            halign='left',
            valign='top'
        )
        #instructions.bind(size=instructions.setter('text_size')) # Justify text
        overlay_layout.add_widget(instructions)

        continue_button = Button(
            text='Let\'s start !',
            background_normal='assets/green_normal.png', background_down='assets/green_down.png',
            border=(30, 30, 30, 30),
            size_hint=(0.4, 0.1),
            pos_hint={'x': 0.3, 'y': 0.1}
        )
        continue_button.bind(on_release=self.on_click)
        overlay_layout.add_widget(continue_button)

        self.add_widget(self.layout)

    def on_entry(self, *args):
        Logger.info('InstructionsScreen: on_entry().')
        self.app.ringled.start_rainbow()

    def on_leave(self, *args):
        Logger.info('InstructionsScreen: on_leave().')
        self.app.ringled.stop()

    def on_click(self, x, y=0):
        Logger.info('InstructionsScreen: on_click(%s).', x)
        self.app.transition_to(ScreenMgr.COUNTDOWN)

class ErrorScreen(Screen):
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
        self.continue_button = Button(
            text='An error occured.\nClick to continue',
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
        self.continue_button.text = "{}\nClick to continue".format(label)

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
    def __init__(self, app, **kwargs):
        Logger.info('CountdownScreen: __init__().')
        super(CountdownScreen, self).__init__(**kwargs)

        self.app = app
        self._current_shot = 0

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
        self.time_remaining_label.text = str(self.time_remaining)
        Clock.schedule_once(self.timer_event, 1)
        self.app.ringled.start_countdown(self.time_remaining)

    def on_leave(self, *args):
        Logger.info('CountdownScreen: on_leave().')
        self.app.ringled.stop()
        self.camera.stop()

    def timer_event(self, obj):
        Logger.info('CountdownScreen: timer_event(%s)', obj)
        self.time_remaining -= 1
        if self.time_remaining:
            self.time_remaining_label.text = str(self.time_remaining)
            Clock.schedule_once(self.timer_event, 1)
        else:
            self.app.transition_to(ScreenMgr.CHEESE, self._current_shot)

class CheeseScreen(Screen):
    """
    +-----------------+
    |                 |
    |     Cheese!     |
    |                 |
    +-----------------+
    """
    smile = [
        'Cheese!',
        'Smile!'
    ]

    def __init__(self, app, **kwargs):
        Logger.info('CheeseScreen: __init__().')
        super(CheeseScreen, self).__init__(**kwargs)

        self.app = app
        self.smile_label = Label(
            text=self.smile[0],
            halign='center',
            valign='middle',
            font_size=LARGE_FONT
        )
        self.layout = BoxLayout()
        self.layout.add_widget(self.smile_label)
        self.add_widget(self.layout)

        self.wait_count = 0
        self._current_shot = 0

    def on_entry(self, *args):
        Logger.info('CheeseScreen: on_entry().')
        if len(args) == 0: return self.app.transition_to(ScreenMgr.ERROR, 'An error occured !')
        self._current_shot = int(args[0][0]) if len(args) and len(args[0]) else 0

        self.smile_label.font_size = LARGE_FONT
        self.smile_label.text = random.choice(self.smile)
        self.wait_idx = -1
        self.wait_count = 0
        self._clock = Clock.schedule_once(self.timer_event, 2)

        # Trigger shot
        try:
            self.app.ringled.flash()
            self.app.trigger_shot(self._current_shot)
        except:
            return self.app.transition_to(ScreenMgr.ERROR, 'Cannot trigger camera.')

    def on_leave(self, *args):
        Logger.info('CheeseScreen: on_leave().')
        Clock.unschedule(self._clock)

    def timer_event(self, obj):
        Logger.info('CheeseScreen: timer_event().')
        if not(self.app.is_shot_completed(self._current_shot)):
            self.smile_label.font_size = SMALL_FONT
            self.smile_label.text = 'Please wait ...'
            self._clock = Clock.schedule_once(self.timer_event, 1)
        elif self.app.get_shots_to_take() == 1:
            self.app.transition_to(ScreenMgr.PROCESSING)
        else:
            self.app.transition_to(ScreenMgr.CONFIRM_CAPTURE, self._current_shot)

class ConfirmCaptureScreen(Screen):
    """
    +-----------------+
    |      Keep ?     |
    |                 |
    | NO          YES |
    +-----------------+
    """
    def __init__(self, app, **kwargs):
        Logger.info('ConfirmCaptureScreen: __init__().')
        super(ConfirmCaptureScreen, self).__init__(**kwargs)

        self.app = app
        self._current_shot = 0
        self.time_remaining = 10

        # Display taken photo
        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')
        self.preview = Image(fit_mode='contain')
        self.layout.add_widget(self.preview)

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        self.title = Button(
            text='Photo 1 sur {}'.format(self.app.get_shots_to_take()), # On la garde ?
            border=(30, 30, 30, 30),
            size_hint=(0.8, 0.1),
            pos_hint={'x': 0.1, 'y': 0.8},
            font_size=NORMAL_FONT,
            background_normal='assets/title.png', background_down='assets/title.png'
        )
        overlay_layout.add_widget(self.title)

        self.yes_button = Button(text='Keep it (10)', background_normal='assets/green_normal.png', background_down='assets/green_down.png', border=(30, 30, 30, 30), size_hint=(0.2, 0.1), pos_hint={'x': 0.05, 'y': 0.1},)
        self.yes_button.bind(on_release=self.yes_event)
        overlay_layout.add_widget(self.yes_button)

        self.no_button = Button(text='New take', background_normal='assets/red_normal.png', background_down='assets/red_down.png', border=(30, 30, 30, 30), size_hint=(0.2, 0.1), pos_hint={'x': 0.75, 'y': 0.1})
        self.no_button.bind(on_release=self.no_event)
        overlay_layout.add_widget(self.no_button)

        self.add_widget(self.layout)

    def on_entry(self, *args):
        Logger.info('ConfirmCaptureScreen: on_entry().')
        if len(args) == 0 or len(args[0]) == 0: return self.app.transition_to(ScreenMgr.ERROR, 'An error occured !')
        self._current_shot = int(args[0][0]) if len(args) and len(args[0]) else 0
        self.time_remaining = 10
        self.title.text = 'Photo {} sur {}'.format(self._current_shot + 1, self.app.get_shots_to_take())
        self.yes_button.text = 'Keep it ({})'.format(self.time_remaining)
        self.preview.source = self.app.get_shot(self._current_shot)
        self.auto_confirm = Clock.schedule_once(self.timer_event, 10)
        self._clock = Clock.schedule_once(self.tick_event, 1)

    def on_leave(self, *args):
        Logger.info('ConfirmCaptureScreen: on_leave().')
        Clock.unschedule(self._clock)

    def yes_event(self, obj):
        Clock.unschedule(self.auto_confirm)
        Clock.unschedule(self._clock)
        if self._current_shot == self.app.get_shots_to_take() - 1: self.app.transition_to(ScreenMgr.PROCESSING)
        else: self.app.transition_to(ScreenMgr.COUNTDOWN, self._current_shot + 1)

    def no_event(self, obj):
        Clock.unschedule(self.auto_confirm)
        Clock.unschedule(self._clock)
        self.app.transition_to(ScreenMgr.COUNTDOWN, self._current_shot)

    def tick_event(self, obj):
        self.time_remaining -= 1
        self.yes_button.text = 'Keep it ({})'.format(self.time_remaining)
        self._clock = Clock.schedule_once(self.tick_event, 1)

    def timer_event(self, obj):
        Logger.info('ConfirmCaptureScreen: timer_event().')
        if self._current_shot == self.app.get_shots_to_take() - 1: self.app.transition_to(ScreenMgr.PROCESSING)
        else: self.app.transition_to(ScreenMgr.COUNTDOWN, self._current_shot + 1)

class ProcessingScreen(Screen):
    """
    +-----------------+
    |                 |
    |   Processing    |
    |                 |
    +-----------------+
    """
    waiting = [
        '',
        'Processing...',
        '',
        'Still processing...',
        '',
        'Waiting on the camera...',
        '',
        'Almost done...',
        '',
        'Any second now...',
        ''
    ]

    def __init__(self, app, **kwargs):
        Logger.info('ProcessingScreen: __init__().')
        super(ProcessingScreen, self).__init__(**kwargs)

        self.app = app
        self.smile_label = Label(
            text=self.waiting[0],
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
        self._clock = Clock.schedule_once(self.timer_event, 2)
        self.app.ringled.start_rainbow()

        # Perform collage
        try:
            self.app.trigger_collage()
        except:
            return self.app.transition_to(ScreenMgr.ERROR, 'Cannot assemble images.')

    def on_leave(self, *args):
        Logger.info('ProcessingScreen: on_leave().')
        Clock.unschedule(self._clock)
        self.app.ringled.stop()

    def timer_event(self, obj):
        Logger.info('ProcessingScreen: timer_event().')
        if not(self.app.is_collage_completed()):
            self.wait_count += 1
            if self.wait_count % 3 == 0:
                self.wait_idx = (self.wait_idx + 1) % len(self.waiting)
                self.smile_label.font_size = SMALL_FONT
                self.smile_label.text = self.waiting[self.wait_idx]
            self._clock = Clock.schedule_once(self.timer_event, 1)
        elif self.app.has_printer():
            self.app.transition_to(ScreenMgr.CONFIRM_PRINT)
        else:
            self.app.transition_to(ScreenMgr.CONFIRM_SAVE)

class ConfirmSaveScreen(Screen):
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
        self.time_remaining = 10

        # Display collage
        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')
        self.preview = Image(fit_mode='contain')
        self.layout.add_widget(self.preview)

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        title = Button(
            text='Do you want to save this collage ?', # On les garde ?
            border=(30, 30, 30, 30),
            size_hint=(0.8, 0.1),
            pos_hint={'x': 0.1, 'y': 0.8},
            font_size=NORMAL_FONT,
            background_normal='assets/title.png', background_down='assets/title.png'
        )
        overlay_layout.add_widget(title)

        self.yes_button = Button(text='Yes (10)', background_normal='assets/green_normal.png', background_down='assets/green_down.png', border=(30, 30, 30, 30), size_hint=(0.2, 0.1), pos_hint={'x': 0.05, 'y': 0.1},)
        self.yes_button.bind(on_release=self.yes_event)
        overlay_layout.add_widget(self.yes_button)

        self.no_button = Button(text='No', background_normal='assets/red_normal.png', background_down='assets/red_down.png', border=(30, 30, 30, 30), size_hint=(0.2, 0.1), pos_hint={'x': 0.75, 'y': 0.1})
        self.no_button.bind(on_release=self.no_event)
        overlay_layout.add_widget(self.no_button)

        self.add_widget(self.layout)

    def on_entry(self, *args):
        Logger.info('ConfirmSaveScreen: on_entry().')
        self.auto_confirm = Clock.schedule_once(self.timer_event, 10)
        self._clock = Clock.schedule_once(self.tick_event, 1)
        self.app.ringled.start_rainbow()
        self.preview.source = self.app.get_collage()
        self.time_remaining = 10
        self.yes_button.text = 'Yes ({})'.format(self.time_remaining)

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
        self.yes_button.text = 'Yes ({})'.format(self.time_remaining)
        self._clock = Clock.schedule_once(self.tick_event, 1)

    def timer_event(self, obj):
        Logger.info('ConfirmSaveScreen: timer_event().')
        self.app.transition_to(ScreenMgr.SUCCESS)

class ConfirmPrintScreen(Screen):
    """
    +-----------------+
    |      Print ?    |
    |                 |
    | NO          YES |
    +-----------------+
    """
    # TODO : Add copies with 3 buttons (1, 2, 3 or Ignore)
    def __init__(self, app, **kwargs):
        Logger.info('ConfirmPrintScreen: __init__().')
        super(ConfirmPrintScreen, self).__init__(**kwargs)

        self.app = app
        self.time_remaining = 10

        # Display collage
        self.layout = AnchorLayout(anchor_x='center', anchor_y='top')
        self.preview = Image(fit_mode='contain')
        self.layout.add_widget(self.preview)

        overlay_layout = FloatLayout()
        self.layout.add_widget(overlay_layout)

        title = Button(
            text='Do you want to print this collage ?', # On l'imprime ?
            border=(30, 30, 30, 30),
            size_hint=(0.8, 0.1),
            pos_hint={'x': 0.1, 'y': 0.8},
            font_size=NORMAL_FONT,
            background_normal='assets/title.png', background_down='assets/title.png'
        )
        overlay_layout.add_widget(title)

        btn_once = Button(
            text='One copy',
            background_normal='assets/green_normal.png', background_down='assets/green_down.png',
            border=(30, 30, 30, 30),
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.05, 'y': 0.1}
        )
        btn_once.bind(on_release=self.print_once)
        overlay_layout.add_widget(btn_once)

        btn_twice = Button(
            text='Two copies',
            background_normal='assets/green_normal.png', background_down='assets/green_down.png',
            border=(30, 30, 30, 30),
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.05, 'y': 0.25}
        )
        btn_twice.bind(on_release=self.print_twice)
        overlay_layout.add_widget(btn_twice)

        btn_3times = Button(
            text='Three copies',
            background_normal='assets/green_normal.png', background_down='assets/green_down.png',
            border=(30, 30, 30, 30),
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.05, 'y': 0.4}
        )
        btn_3times.bind(on_release=self.print_3times)
        overlay_layout.add_widget(btn_3times)

        self.no_button = Button(text='Ignore (10)', background_normal='assets/red_normal.png', background_down='assets/red_down.png', border=(30, 30, 30, 30), size_hint=(0.2, 0.1), pos_hint={'x': 0.75, 'y': 0.1})
        self.no_button.bind(on_release=self.no_event)
        overlay_layout.add_widget(self.no_button)

        self.add_widget(self.layout)

    def on_entry(self, *args):
        Logger.info('ConfirmPrintScreen: on_entry().')
        self.auto_decline = Clock.schedule_once(self.timer_event, 10)
        self._clock = Clock.schedule_once(self.tick_event, 1)
        self.app.ringled.start_rainbow()
        self.preview.source = self.app.get_collage()
        self.time_remaining = 10
        self.no_button.text = 'Ignore ({})'.format(self.time_remaining)
        self.app.save_collage()

    def on_leave(self, *args):
        Logger.info('ConfirmPrintScreen: on_leave().')
        self.app.ringled.stop()
        Clock.unschedule(self._clock)

    def print_once(self, obj):
        Clock.unschedule(self.auto_decline)
        Clock.unschedule(self._clock)
        self.app.transition_to(ScreenMgr.PRINTING, 1)

    def print_twice(self, obj):
        Clock.unschedule(self.auto_decline)
        Clock.unschedule(self._clock)
        self.app.transition_to(ScreenMgr.PRINTING, 2)

    def print_3times(self, obj):
        Clock.unschedule(self.auto_decline)
        Clock.unschedule(self._clock)
        self.app.transition_to(ScreenMgr.PRINTING, 3)

    def no_event(self, obj):
        Clock.unschedule(self.auto_decline)
        Clock.unschedule(self._clock)
        if self.app.get_shots_to_take() == 1: self.app.transition_to(ScreenMgr.WAITING)
        else: self.app.transition_to(ScreenMgr.SUCCESS)

    def tick_event(self, obj):
        self.time_remaining -= 1
        self.no_button.text = 'Ignore ({})'.format(self.time_remaining)
        self._clock = Clock.schedule_once(self.tick_event, 1)

    def timer_event(self, obj):
        Logger.info('ConfirmPrintScreen: timer_event().')
        if self.app.get_shots_to_take() == 1: self.app.transition_to(ScreenMgr.WAITING)
        else: self.app.transition_to(ScreenMgr.SUCCESS)

class PrintingScreen(Screen):
    """
    +-----------------+
    |                 |
    |   Printing...   |
    |                 |
    +-----------------+
    """
    waiting = ['Resizing...', 'Montaging...', 'Compositing...', 'Printing...']

    def __init__(self, app, **kwargs):
        Logger.info('PrintingScreen: __init__().')
        super(PrintingScreen, self).__init__(**kwargs)

        self.app = app
        self.status = Label(
            text=self.waiting[0],
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

        # Trigger print
        try:
            self._print_task_id = self.app.trigger_print(copies)
            self._clock = Clock.schedule_once(self.timer_event, 1)
        except:
            return self.app.transition_to(ScreenMgr.ERROR, 'Cannot print collage.\nDon\'t worry, collage has been saved ;)')

    def on_leave(self, *args):
        Logger.info('PrintingScreen: on_leave().')
        Clock.unschedule(self._clock)
        self.app.ringled.stop()

    def timer_event(self, obj):
        Logger.info('PrintingScreen: timer_event().')
        if not self.app.is_print_completed(self._print_task_id):
            self.wait_count += 1
            if self.wait_count % 3 == 0:
                self.wait_idx = (self.wait_idx + 1) % len(self.waiting)
                self.status.font_size = SMALL_FONT
                self.status.text = self.waiting[self.wait_idx]
            self._clock = Clock.schedule_once(self.timer_event, 1)
        else:
            self.app.transition_to(ScreenMgr.SUCCESS)

class SuccessScreen(Screen):
    """
    +-----------------+
    |                 |
    |    Perfect !    |
    |                 |
    +-----------------+
    """
    messages = ['Perfect !', 'Awesome !', 'Wahou !']
    def __init__(self, app, **kwargs):
        Logger.info('SuccessScreen: __init__().')
        super(SuccessScreen, self).__init__(**kwargs)

        self.app = app
        self.start_button = Button(
            text=messages[0],
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
        self.start_button.text = random.choice(self.messages)
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

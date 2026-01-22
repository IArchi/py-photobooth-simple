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
BORDER_THINKNESS = (Window.dpi / 160) * 10
PROGRESS_COLOR = hex_to_rgba('#e5e5e5')
CONFIRM_COLOR = hex_to_rgba('#538a64')
CANCEL_COLOR = hex_to_rgba('#8b4846')
HOME_COLOR = hex_to_rgba('#534969')
BADGE_COLOR = hex_to_rgba('#8b4846')
SHARE_COLOR = hex_to_rgba('#667eea')

# Icons
ICON_TTF = './assets/fonts/hugeicons.ttf' # https://hugeicons.com/free-icon-font and https://hugeicons.com/icons?style=Stroke&type=Rounded
ICON_TOUCH = '\u3d3e'
ICON_ERROR = '\u3b03'
ICON_ERROR_PRINTING = '\u458d'
ICON_ERROR_TOOLONG = '\u4916'
ICON_ERROR_DISCONNECTED = '\u3e63'
ICON_ERROR_TRIGGER = '\u3d39'
ICON_ERROR_UNKNOWN = '\u413a'
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

    def on_update(self, kwargs={}):
        pass

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

    def on_update(self, kwargs={}):
        pass

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

        start = BreezyBorderedLabel(
            text='PHOTO BOOTH',
            font_size=LARGE_FONT,
            border_color=(1,1,1,1),
            border_width=5,
            size_hint=(0.7, 0.2),
            padding=(30,30,30,30),
            pos_hint={'x': 0.15, 'y': 0.4},
        )
        overlay_layout.add_widget(start)
        self.start_label = start

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
            text='Version 1.1',
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
    | Choose your fmt |
    |  [card] [card]  |
    |  [card] [card]  |
    +-----------------+
    """
    # Minimum and maximum card dimensions
    MIN_CARD_WIDTH = 300
    MIN_CARD_HEIGHT = 450
    MAX_CARD_WIDTH = 500
    MAX_CARD_HEIGHT = 800
    
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
            spacing=30,
            padding=20,
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
        """Calculate card size based on window dimensions while maintaining minimum and maximum sizes."""
        # Available width considering padding, spacing, and 3 columns
        available_width = Window.width - (2 * 20) - (2 * 30) - (2 * BORDER_THINKNESS)
        card_width = max(self.MIN_CARD_WIDTH, min(self.MAX_CARD_WIDTH, available_width / 3))
        
        # Card height proportional to width (1.5 aspect ratio) but respecting minimum and maximum
        card_height = max(self.MIN_CARD_HEIGHT, min(self.MAX_CARD_HEIGHT, card_width * 1.5))
        
        # Also check against window height to avoid cards that are too tall
        max_card_height = Window.height - (2 * 20) - (2 * BORDER_THINKNESS) - 100
        card_height = min(card_height, max_card_height)
        
        # Ensure aspect ratio is maintained even with max height constraint
        if card_height == max_card_height:
            card_width = min(card_width, card_height / 1.5)
        
        return (card_width, card_height)
    
    def _update_card_sizes(self):
        """Update all card sizes based on current window size."""
        card_width, card_height = self._calculate_card_size()
        
        # Update grid row height
        self.cards_grid.row_default_height = card_height
        self.cards_grid.row_force_default = True
        
        # Update each card's size
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
        from kivy.uix.behaviors import ButtonBehavior
        from kivy.graphics import RoundedRectangle
        
        class ClickableCard(ButtonBehavior, BoxLayout):
            pass
        
        # Initial size will be updated by _update_card_sizes
        card = ClickableCard(
            orientation='vertical',
            size_hint=(None, None),
            size=(self.MIN_CARD_WIDTH, self.MIN_CARD_HEIGHT),
            padding=20,
            spacing=10,
        )
        
        # Draw rounded card background using canvas
        with card.canvas.before:
            Color(*hex_to_rgba('#3d4f5c'))
            card_bg = RoundedRectangle(
                pos=card.pos,
                size=card.size,
                radius=[20,]
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
            padding=20,
        )
        
        # Draw rounded preview background
        with preview_container.canvas.before:
            Color(*hex_to_rgba('#4a5c6a'))
            preview_bg = RoundedRectangle(
                pos=preview_container.pos,
                size=preview_container.size,
                radius=[15,]
            )
        
        # Bind to update preview background
        def update_preview_bg(instance, value):
            preview_bg.pos = instance.pos
            preview_bg.size = instance.size
        preview_container.bind(pos=update_preview_bg, size=update_preview_bg)
        
        preview_image = Image(
            source=preview_path,
            size_hint=(None, None),
            allow_stretch=True,
            keep_ratio=True,
        )
        
        # Update image size to fit within container
        def update_image_size(instance, *args):
            if preview_container.width <= 40 or preview_container.height <= 40:
                return
            max_width = preview_container.width - 40
            max_height = preview_container.height - 40
            preview_image.size = (max_width, max_height)
        
        preview_container.bind(size=update_image_size)
        preview_image.bind(texture=update_image_size)
        
        preview_container.add_widget(preview_image)
        card.add_widget(preview_container)
        
        # Format name
        name_label = Label(
            text=format_template.get_name(),
            size_hint=(1, 0.15),
            font_size=SMALL_FONT,
            halign='center',
            valign='middle',
            bold=True,
        )
        name_label.bind(size=name_label.setter('text_size'))
        card.add_widget(name_label)
        
        # Number of photos
        num_photos = format_template.get_photos_required()
        photos_label = ResizeLabel(
            text=f"{num_photos} photo{'s' if num_photos > 1 else ''}",
            size_hint=(1, 0.1),
            max_font_size=TINY_FONT,
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
        # Reload all previews
        for card in self.format_cards:
            # Find the Image widget in the card and reload it
            for child in card.walk():
                if isinstance(child, Image):
                    child.reload()
                    break
        self.app.ringled.start_rainbow()

    def on_exit(self, kwargs={}):
        Logger.info('SelectFormatScreen: on_exit().')
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

        layout = BoxLayout(orientation='vertical')

        # Display error icon
        self.icon = ResizeLabel(
            size_hint=(0.4, 0.4),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            font_name=ICON_TTF,
            text=ICON_ERROR,
            max_font_size=XLARGE_FONT,
        )
        layout.add_widget(self.icon)

        # Display second icon
        self.icon2 = ResizeLabel(
            size_hint=(0.1, 0.1),
            pos_hint={'center_x': 0.5, 'y': 0.3},
            font_name=ICON_TTF,
            text=ICON_LOADING,
            max_font_size=NORMAL_FONT,
        )
        layout.add_widget(self.icon2)

        self.add_widget(layout)

    def on_entry(self, kwargs={}):
        Logger.info('ErrorScreen: on_entry().')
        if 'error' in kwargs: self.icon.text = str(kwargs.get('error'))
        if 'error2' in kwargs: self.icon2.text = str(kwargs.get('error2'))

    def on_exit(self, kwargs={}):
        Logger.info('ErrorScreen: on_exit().')

    def on_click(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ErrorScreen: on_click().')
        self.app.transition_to(ScreenMgr.WAITING)

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

        self.time_remaining = self.app.COUNTDOWN
        self.total_countdown = self.app.COUNTDOWN

        # Display camera preview
        self.layout = AnchorLayout(padding=BORDER_THINKNESS, anchor_x='center', anchor_y='center')
        
        self.camera = KivyCamera(app=self.app, fps=30, blur=BLUR_CAMERA, fit_mode='contain')
        self.layout.add_widget(self.camera)
        
        # Create overlay layout for buttons (on top of camera)
        self.overlay_layout = FloatLayout()
        self.layout.add_widget(self.overlay_layout)

        # Display countdown with circular progress
        self.circular_counter = CircularProgressCounter(
            size_hint=(None, None),
            size=(400, 400),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            circle_size=350,
            line_width=6,
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

        # Home button (visible only when timer is not active) - top left
        self.btn_home = make_icon_button(ICON_HOME,
            size=0.14,
            pos_hint={'x': 0.05, 'top': 0.95},
            font=ICON_TTF,
            font_size=LARGE_FONT,
            bgcolor=HOME_COLOR,
            on_release=self.home_event
        )

        # Trigger/Cancel button - center bottom as round icon button
        self.btn_trigger = make_icon_button(ICON_TRIGGER,
            size=0.14,
            pos_hint={'center_x': 0.5, 'y': 0.05},
            font=ICON_TTF,
            font_size=LARGE_FONT,
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
                return self.app.transition_to(ScreenMgr.ERROR, error2=ICON_ERROR_TRIGGER)

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

    def trigger_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('CountdownScreen: trigger_event().')
        
        if not self._timer_active:
            # Start the countdown
            self._timer_active = True
            self.start_countdown()
        else:
            # Cancel the countdown
            self._timer_active = False
            self.cancel_countdown()

    def start_countdown(self):
        Logger.info('CountdownScreen: start_countdown().')
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
        self._clock_progress = Clock.schedule_interval(self.timer_progress, 1/60.0)
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
        
        # Update button icon and color (access child button from parent layout)
        for child in self.btn_trigger.children:
            if isinstance(child, LabelRoundButton):
                child.text = ICON_TRIGGER
                child.background_color = CONFIRM_COLOR
                break
        
        # Clear LED
        self.app.ringled.clear()

    def home_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('CountdownScreen: home_event().')
        self.app.transition_to(ScreenMgr.WAITING)

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

        # Home button - top left
        btn_home = make_icon_button(ICON_HOME,
                             size=0.14,
                             pos_hint={'x': 0.05, 'top': 0.95},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=HOME_COLOR,
                             on_release=self.home_event
                             )
        self.overlay_layout.add_widget(btn_home)

        # Cancel button - bottom left
        btn_cancel = make_icon_button(ICON_CANCEL,
                             size=0.14,
                             pos_hint={'x': 0.05, 'y': 0.05},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=CANCEL_COLOR,
                             on_release=self.no_event
                             )
        self.overlay_layout.add_widget(btn_cancel)

        # Confirm button - bottom right
        btn_confirm = make_icon_button(ICON_CONFIRM,
                             size=0.14,
                             pos_hint={'right': 0.95, 'y': 0.05},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=CONFIRM_COLOR,
                             on_release=self.keep_event,
                             )
        self.overlay_layout.add_widget(btn_confirm)

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
    |      Saved      |
    |             YES |
    |           SHARE |
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

        # Home button - top left
        btn_home = make_icon_button(ICON_HOME,
                             size=0.14,
                             pos_hint={'x': 0.05, 'top': 0.95},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=HOME_COLOR,
                             on_release=self.yes_event
                             )
        overlay_layout.add_widget(btn_home)

        # Share button - center bottom (with icon and text) - only if SHARE is enabled
        if self.app.SHARE:
            btn_share = make_icon_text_button(
                                 icon=ICON_SHARE,
                                 text='SHARE',
                                 size_hint=(0.15, 0.09),
                                 pos_hint={'center_x': 0.5, 'y': 0.05},
                                 icon_font=ICON_TTF,
                                 icon_font_size=SMALL_FONT,
                                 text_font_size=SMALL_FONT,
                                 bgcolor=SHARE_COLOR,
                                 on_release=self.share_event,
                                 )
            overlay_layout.add_widget(btn_share)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ConfirmSaveScreen: on_entry().')
        self.auto_confirm = Clock.schedule_once(self.timer_event, 60)
        self.app.ringled.start_rainbow()
        self.preview.filepath = FileUtils.get_small_path(self.app.get_collage())
        self.preview.reload()
        self.app.save_collage()

    def on_exit(self, kwargs={}):
        Logger.info('ConfirmSaveScreen: on_exit().')
        self.app.ringled.clear()

    def yes_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Clock.unschedule(self.auto_confirm)
        self.app.transition_to(ScreenMgr.SUCCESS)

    def no_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Clock.unschedule(self.auto_confirm)
        self.app.transition_to(ScreenMgr.WAITING)

    def share_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ConfirmSaveScreen: share_event().')
        # Show QR code popup
        self.qr_popup = QRCodePopup(on_dismiss=self._dismiss_qr_popup)
        self.layout.add_widget(self.qr_popup)
    
    def _dismiss_qr_popup(self):
        """Remove QR code popup."""
        if hasattr(self, 'qr_popup') and self.qr_popup.parent:
            self.layout.remove_widget(self.qr_popup)

    def timer_event(self, obj):
        Logger.info('ConfirmSaveScreen: timer_event().')
        Clock.unschedule(self.auto_confirm)
        self.app.transition_to(ScreenMgr.WAITING)

class ConfirmPrintScreen(ColorScreen):
    """
    +-----------------+
    |HOME         SHARE|
    |                 |
    |      PRINT      |
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

        # Home button - top left
        btn_home = make_icon_button(ICON_HOME,
                             size=0.14,
                             pos_hint={'x': 0.05, 'top': 0.95},
                             font=ICON_TTF,
                             font_size=LARGE_FONT,
                             bgcolor=HOME_COLOR,
                             on_release=self.home_event
                             )
        self.overlay_layout.add_widget(btn_home)

        # Print button - center bottom (with icon and text)
        # Adjust position based on SHARE setting
        print_y_pos = 0.05 if not self.app.SHARE else 0.15
        self.btn_print = make_icon_text_button(
                             icon=ICON_PRINT,
                             text='PRINT',
                             size_hint=(0.15, 0.09),
                             pos_hint={'center_x': 0.5, 'y': print_y_pos},
                             icon_font=ICON_TTF,
                             icon_font_size=SMALL_FONT,
                             text_font_size=SMALL_FONT,
                             bgcolor=CONFIRM_COLOR,
                             on_release=self.print_event
                             )
        self.overlay_layout.add_widget(self.btn_print)

        # Share button - below Print (with icon and text) - only if SHARE is enabled
        if self.app.SHARE:
            btn_share = make_icon_text_button(
                                 icon=ICON_SHARE,
                                 text='SHARE',
                                 size_hint=(0.15, 0.09),
                                 pos_hint={'center_x': 0.5, 'y': 0.05},
                                 icon_font=ICON_TTF,
                                 icon_font_size=SMALL_FONT,
                                 text_font_size=SMALL_FONT,
                                 bgcolor=SHARE_COLOR,
                                 on_release=self.share_event,
                                 )
            self.overlay_layout.add_widget(btn_share)

        self.add_widget(self.layout)

    def on_entry(self, kwargs={}):
        Logger.info('ConfirmPrintScreen: on_entry().')
        self._current_format = kwargs.get('format') if 'format' in kwargs else 0
        self.auto_decline = Clock.schedule_once(self.timer_event, 60)
        self.app.ringled.start_rainbow()
        self.preview.filepath = FileUtils.get_small_path(self.app.get_collage())
        self.preview.reload()

        self.app.save_collage()

    def on_exit(self, kwargs={}):
        Logger.info('ConfirmPrintScreen: on_exit().')
        self.app.ringled.clear()

    def print_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ConfirmPrintScreen: print_event().')
        Clock.unschedule(self.auto_decline)
        self.app.transition_to(ScreenMgr.PRINTING, copies=1, format=self._current_format)

    def home_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Clock.unschedule(self.auto_decline)
        self.app.transition_to(ScreenMgr.WAITING)

    def share_event(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        Logger.info('ConfirmPrintScreen: share_event().')
        # Show QR code popup
        self.qr_popup = QRCodePopup(on_dismiss=self._dismiss_qr_popup)
        self.layout.add_widget(self.qr_popup)
    
    def _dismiss_qr_popup(self):
        """Remove QR code popup."""
        if hasattr(self, 'qr_popup') and self.qr_popup.parent:
            self.layout.remove_widget(self.qr_popup)

    def timer_event(self, obj):
        Logger.info('ConfirmPrintScreen: timer_event().')
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
            self.app.transition_to(ScreenMgr.ERROR, error=ICON_ERROR_PRINTING, error2=ICON_ERROR_DISCONNECTED)

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
        return self.app.transition_to(ScreenMgr.ERROR, error=ICON_ERROR_PRINTING, error2=ICON_ERROR_TOOLONG)

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
        self._clock = Clock.schedule_once(self.timer_event, 1)
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
        info = ResizeLabel(
            size_hint=(0.9, 0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.6},
            text='Do not disconnect your USB dongle before this screen disapears !',
            max_font_size=LARGE_FONT,
        )
        layout.add_widget(info)

        # Display progress
        self.progress = ResizeLabel(
            size_hint=(0.9, 0.2),
            pos_hint={'center_x': 0.5, 'center_y': 0.35},
            text='-',
            max_font_size=LARGE_FONT,
        )
        layout.add_widget(self.progress)

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

    def on_update(self, kwargs={}):
        if not 'label' in kwargs: return
        self.progress.text = f"Copying {kwargs.get('label')}"

class QRCodePopup(FloatLayout):
    """Popup overlay to show QR code."""
    
    def __init__(self, on_dismiss=None, **kwargs):
        super(QRCodePopup, self).__init__(**kwargs)
        self.on_dismiss = on_dismiss
        
        # Semi-transparent overlay that blocks all touch events
        with self.canvas.before:
            Color(0, 0, 0, 0.8)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        # Calculate responsive card size (max 60% of window width, 70% of height)
        max_width = Window.width * 0.6
        max_height = Window.height * 0.7
        card_width = min(max_width, 600)
        card_height = min(max_height, 750)
        
        # Calculate QR code size based on card dimensions
        qr_size = min(card_width * 0.7, card_height * 0.5)
        
        # White card container with responsive size using BoxLayout for better positioning
        from kivy.graphics import RoundedRectangle
        
        self.card = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(card_width, card_height),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            padding=30,
            spacing=20,
        )
        
        with self.card.canvas.before:
            Color(1, 1, 1, 1)
            self.card_rect = RoundedRectangle(pos=self.card.pos, size=self.card.size, radius=[20,])
        
        self.card.bind(pos=self._update_card, size=self._update_card)
        
        # "SCAN ME" label
        scan_label = Label(
            text='SCAN ME',
            size_hint=(1, None),
            height=60,
            font_size=SMALL_FONT,
            bold=True,
            color=(0, 0, 0, 1),
            halign='center',
            valign='middle',
        )
        scan_label.bind(size=scan_label.setter('text_size'))
        self.card.add_widget(scan_label)
        
        # QR Code container (centered)
        qr_container = AnchorLayout(
            size_hint=(1, 1),
            anchor_x='center',
            anchor_y='center',
        )
        
        # QR Code image with responsive size
        self.qr_image = Image(
            size_hint=(None, None),
            size=(qr_size, qr_size),
            allow_stretch=True,
        )
        qr_container.add_widget(self.qr_image)
        self.card.add_widget(qr_container)
        
        # Close button positioned below QR code
        btn_container = AnchorLayout(
            size_hint=(1, None),
            height=100,
            anchor_x='center',
            anchor_y='center',
        )
        
        btn_close = make_icon_button(
            ICON_CANCEL,
            size=0.07,
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            font=ICON_TTF,
            font_size=NORMAL_FONT,
            bgcolor=CANCEL_COLOR,
            on_release=self._close
        )
        btn_container.add_widget(btn_close)
        self.card.add_widget(btn_container)
        
        self.add_widget(self.card)
        
        # Generate QR code
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
        """Generate WiFi QR code."""
        import qrcode
        import io
        from kivy.core.image import Image as CoreImage
        
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
        buf.seek(0)
        
        core_image = CoreImage(buf, ext='png')
        self.qr_image.texture = core_image.texture
        Logger.info('QRCodePopup: QR code generated')
    
    def _close(self, obj):
        if not isinstance(obj.last_touch, MouseMotionEvent): return
        if self.on_dismiss:
            self.on_dismiss()

import configparser
import hmac
import io
import json
import os
import re
import shutil
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_file, render_template, redirect, session
from werkzeug.serving import make_server
from kivy.logger import Logger
from libs.config import DEFAULT_STARTSCREEN_BACKGROUND_IMAGE, Config
from libs.i18n import I18n

class WebServer:
    """Flask web server for photo gallery with captive portal."""

    SESSION_PATTERN = re.compile(r'^\d{8}_\d{6}$')
    IMAGE_FILENAME_PATTERN = re.compile(r'^(?:collage|capture-\d+)\.jpg$', re.IGNORECASE)
    LOG_FILENAME_PATTERN = re.compile(r'^[A-Za-z0-9._-]+$')
    START_SCREEN_BACKGROUND_UPLOAD_FIELD = 'startscreen_background_upload'
    START_SCREEN_BACKGROUND_REMOVE_FIELD = 'startscreen_background_remove'
    DELETE_ALL_PASSWORD_FIELD = 'delete_all_password'
    START_SCREEN_BACKGROUND_DEFAULT = str(DEFAULT_STARTSCREEN_BACKGROUND_IMAGE)
    START_SCREEN_BACKGROUND_BASENAME = 'bg_custom'
    START_SCREEN_BACKGROUND_EXTENSIONS = ('.jpg', '.jpeg', '.png')
    START_SCREEN_TEXT_COLOR_DEFAULT = '#FFFFFF'
    START_SCREEN_SHOW_TITLE_DEFAULT = True
    START_SCREEN_SHOW_INSTRUCTIONS_DEFAULT = True
    DSLR_SHUTTERSPEED_CHOICES = [
        ('', 'As defined on DSLR'),
        ('1/30', '1/30'),
        ('1/60', '1/60'),
        ('1/80', '1/80'),
        ('1/100', '1/100'),
        ('1/125', '1/125'),
        ('1/160', '1/160'),
        ('1/200', '1/200'),
        ('1/250', '1/250'),
        ('1/320', '1/320'),
        ('1/400', '1/400'),
        ('1/500', '1/500'),
    ]
    DSLR_APERTURE_CHOICES = [
        ('', 'As defined on DSLR'),
        ('1.8', '1.8'),
        ('2', '2'),
        ('2.8', '2.8'),
        ('4', '4'),
        ('5.6', '5.6'),
        ('8', '8'),
        ('11', '11'),
        ('13', '13'),
        ('16', '16'),
        ('22', '22'),
    ]
    DSLR_FOCUSMODE_CHOICES = [
        ('', 'As defined on DSLR'),
        ('One Shot', 'One Shot'),
        ('AF-S', 'AF-S'),
        ('AF-A', 'AF-A'),
        ('AF-C', 'AF-C'),
        ('Manual', 'Manual'),
    ]
    DSLR_ISO_CHOICES = [
        ('', 'As defined on DSLR'),
        ('100', '100'),
        ('200', '200'),
        ('400', '400'),
        ('800', '800'),
        ('1600', '1600'),
        ('3200', '3200'),
        ('6400', '6400'),
    ]
    CONFIG_FORM_SECTIONS = (
        {
            'title': 'Global',
            'description': 'General application behavior and admin access.',
            'fields': (
                {'section': 'Global', 'option': 'FULLSCREEN', 'label': 'Fullscreen', 'control': 'checkbox', 'help': 'Launch PhotoBooth in fullscreen kiosk mode.'},
                {'section': 'Global', 'option': 'SHARE', 'label': 'Share buttons', 'control': 'checkbox', 'help': 'Display web sharing actions in the booth interface.'},
                {'section': 'Global', 'option': 'RINGLED', 'label': 'Ring LED', 'control': 'checkbox', 'help': 'Enable the SPI ring light hardware.'},
                {'section': 'Global', 'option': 'LANGUAGE', 'label': 'Language', 'control': 'select', 'choices': (('fr', 'Français'), ('en', 'English')), 'help': 'Choose the UI language used by the PhotoBooth application.'},
                {'section': 'Global', 'option': 'ADMIN_PASSWORD', 'label': 'Admin password', 'control': 'password', 'placeholder': 'Leave blank to keep current password', 'help': 'Enter a new password, or type None to disable admin login.'},
            ),
        },
        {
            'title': 'Logs',
            'description': 'Log retention settings.',
            'fields': (
                {'section': 'Log', 'option': 'LOG_RETENTION_DAYS', 'label': 'Log retention days', 'control': 'number', 'number_type': 'int', 'min': 1, 'step': 1},
                {'section': 'Log', 'option': 'LOG_MAX_FILES', 'label': 'Maximum log files', 'control': 'number', 'number_type': 'int', 'min': 1, 'step': 1},
            ),
        },
        {
            'title': 'Start screen',
            'description': 'Customize the waiting screen background and title styling.',
            'fields': (
                {'section': 'StartScreen', 'option': 'TEXT_COLOR', 'label': 'Text color', 'control': 'text', 'default': START_SCREEN_TEXT_COLOR_DEFAULT, 'placeholder': '#FFFFFF', 'help': 'Hex color for the title, touch icon and version text.'},
                {'section': 'StartScreen', 'option': 'SHOW_TITLE', 'label': 'Show title', 'control': 'checkbox', 'default': START_SCREEN_SHOW_TITLE_DEFAULT, 'help': 'Display the PHOTO BOOTH title on the waiting screen.'},
                {'section': 'StartScreen', 'option': 'SHOW_INSTRUCTIONS', 'label': 'Show instructions', 'control': 'checkbox', 'default': START_SCREEN_SHOW_INSTRUCTIONS_DEFAULT, 'help': 'Display the TAP TO START instruction on the waiting screen.'},
            ),
        },
        {
            'title': 'Capture',
            'description': 'Camera countdown, calibration and preview behavior.',
            'fields': (
                {'section': 'Capture', 'option': 'COUNTDOWN', 'label': 'Countdown (seconds)', 'control': 'number', 'number_type': 'int', 'min': 0, 'step': 1},
                {'section': 'Capture', 'option': 'CALIBRATION', 'label': 'Calibration', 'control': 'text', 'placeholder': 'None or (zoom, offset_x, offset_y)', 'help': 'This field stays as a raw string because it is produced by the calibration tool.'},
                {'section': 'Capture', 'option': 'FILTERS', 'label': 'Photo filters', 'control': 'checkbox', 'help': 'Allow visitors to choose a filter after each shot.'},
                {'section': 'Capture', 'option': 'BLUR_CAMERA', 'label': 'Blur preview borders', 'control': 'checkbox', 'inline_with_next': True},
                {'section': 'Capture', 'option': 'PREVIEW_BLUR_REFRESH_FRAMES', 'label': 'Preview blur refresh frames', 'control': 'number', 'number_type': 'int', 'min': 1, 'step': 1, 'inline_with_previous': True},
                {'section': 'Capture', 'option': 'BLUR_IMAGES', 'label': 'Blur captured images', 'control': 'checkbox'},
                {'section': 'Capture', 'option': 'BLUR_COLLAGE', 'label': 'Blur collages', 'control': 'checkbox'},
            ),
        },
        {
            'title': 'Storage',
            'description': 'Disk paths and safeguards against full storage.',
            'fields': (
                {'section': 'Storage', 'option': 'DCIM_DIRECTORY', 'label': 'Photo storage directory', 'control': 'text', 'placeholder': './DCIM'},
                {'section': 'Storage', 'option': 'DISK_MIN_FREE_GB', 'label': 'Minimum free space (GB)', 'control': 'number', 'number_type': 'float', 'min': 0, 'step': 0.1},
                {'section': 'Storage', 'option': 'DISK_MAX_USED_PERCENT', 'label': 'Maximum used disk (%)', 'control': 'number', 'number_type': 'float', 'min': 0, 'max': 100, 'step': 0.1},
            ),
        },
        {
            'title': 'Print & USB',
            'description': 'Printer usage limits and USB export.',
            'fields': (
                {'section': 'Print', 'option': 'PRINTER', 'label': 'Printer name', 'control': 'text', 'placeholder': 'None', 'none_means_empty': True, 'help': 'Leave empty to disable printing.'},
                {'section': 'Print', 'option': 'MAX_PRINTS', 'label': 'Maximum prints', 'control': 'number', 'number_type': 'optional_int', 'min': 0, 'step': 1, 'placeholder': 'Unlimited', 'help': 'Leave empty for unlimited prints.'},
                {'section': 'Print', 'option': 'PRINTER_WAIT_TIMEOUT', 'label': 'Printer wait timeout (seconds)', 'control': 'number', 'number_type': 'int', 'min': 5, 'step': 1},
                {'section': 'USB', 'option': 'USB_EXPORT', 'label': 'USB export', 'control': 'checkbox', 'help': 'Automatically copy saved sessions to removable USB media.'},
                {'section': 'USB', 'option': 'USB_MIN_FREE_GB', 'label': 'USB minimum free space (GB)', 'control': 'number', 'number_type': 'float', 'min': 0, 'step': 0.1},
            ),
        },
        {
            'title': 'DSLR Liveview',
            'description': 'Parameters applied while preview/liveview is active.',
            'fields': (
                {'section': 'DSLR_Liveview', 'option': 'SHUTTERSPEED', 'label': 'Shutter speed', 'control': 'select', 'choices': DSLR_SHUTTERSPEED_CHOICES},
                {'section': 'DSLR_Liveview', 'option': 'APERTURE', 'label': 'Aperture', 'control': 'select', 'choices': DSLR_APERTURE_CHOICES},
                {'section': 'DSLR_Liveview', 'option': 'FOCUSMODE', 'label': 'Focus mode', 'control': 'select', 'choices': DSLR_FOCUSMODE_CHOICES},
                {'section': 'DSLR_Liveview', 'option': 'ISO', 'label': 'ISO', 'control': 'select', 'choices': DSLR_ISO_CHOICES},
            ),
        },
        {
            'title': 'DSLR Capture',
            'description': 'Parameters applied right before taking a photo.',
            'fields': (
                {'section': 'DSLR_Capture', 'option': 'SHUTTERSPEED', 'label': 'Shutter speed', 'control': 'select', 'choices': DSLR_SHUTTERSPEED_CHOICES},
                {'section': 'DSLR_Capture', 'option': 'APERTURE', 'label': 'Aperture', 'control': 'select', 'choices': DSLR_APERTURE_CHOICES},
                {'section': 'DSLR_Capture', 'option': 'FOCUSMODE', 'label': 'Focus mode', 'control': 'select', 'choices': DSLR_FOCUSMODE_CHOICES},
                {'section': 'DSLR_Capture', 'option': 'ISO', 'label': 'ISO', 'control': 'select', 'choices': DSLR_ISO_CHOICES},
            ),
        },
    )
    
    def __init__(self, save_directory, host='0.0.0.0', port=5000, admin_password=None, stats_store=None, restart_callback=None):
        self.save_directory = save_directory
        self.host = host
        self.port = port
        self.admin_password = admin_password.strip() if isinstance(admin_password, str) and admin_password.strip() else None
        self.stats_store = stats_store
        self.restart_callback = restart_callback
        self.config = Config()
        self.i18n = I18n(self.config.get_language())
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.web_directory = os.path.join(self.project_root, 'web')
        self.web_assets_directory = os.path.join(self.web_directory, 'assets')
        self.app = Flask(
            __name__,
            template_folder=self.web_directory,
            static_folder=self.web_assets_directory,
            static_url_path='/web-assets',
        )
        self.app.secret_key = os.urandom(32)
        self.app.config.update(
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
        )
        self.server_thread = None
        self.server = None
        self._server_lock = threading.Lock()
        self._watchdog_thread = None
        self._watchdog_stop = threading.Event()
        self.config_file = os.path.join(self.project_root, 'config.ini')
        self.logs_directory = os.path.join(self.project_root, 'logs')
        self.templates_directory = os.path.join(self.project_root, 'templates')
        self.template_editor_path = os.path.join(self.web_directory, 'editor', 'template_editor.html')
        self._setup_routes()

    def t(self, key, default=None, **kwargs):
        return self.i18n.t(key, default=default, **kwargs)

    def _watchdog_loop(self):
        while not self._watchdog_stop.wait(timeout=5):
            if self.server_thread is None:
                continue
            if self.server_thread.is_alive():
                continue

            Logger.error('WebServer: watchdog detected stopped server thread, attempting restart')
            try:
                if not self.start(force_restart=True):
                    Logger.error('WebServer: watchdog restart failed')
            except Exception as e:
                Logger.error(f'WebServer: watchdog restart exception: {e}')

    def _ensure_watchdog(self):
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return
        self._watchdog_stop.clear()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, name='webserver-watchdog', daemon=True)
        self._watchdog_thread.start()

    def _sanitize_template_filename(self, filename=None, template_name='template'):
        """Return a safe JSON filename for template storage."""
        source = filename or template_name or 'template'
        safe_name = os.path.basename(source).strip()

        if safe_name.lower().endswith('.json'):
            safe_name = safe_name[:-5]

        safe_name = safe_name.replace(' ', '_')
        safe_name = re.sub(r'[^A-Za-z0-9._-]', '', safe_name)
        safe_name = safe_name.strip('._-') or 'template'

        return f'{safe_name}.json'

    def _get_unique_template_filename(self, filename):
        """Return a non-conflicting filename in the templates directory."""
        base_name, extension = os.path.splitext(filename)
        candidate = filename
        counter = 1

        while os.path.exists(os.path.join(self.templates_directory, candidate)):
            candidate = f'{base_name}_{counter}{extension}'
            counter += 1

        return candidate

    def _load_template_definitions(self):
        """Load all template JSON files from the templates directory."""
        templates = []

        if not os.path.isdir(self.templates_directory):
            return templates

        for filename in sorted(os.listdir(self.templates_directory)):
            if not filename.lower().endswith('.json'):
                continue

            template_path = os.path.join(self.templates_directory, filename)
            if not os.path.isfile(template_path):
                continue

            try:
                with open(template_path, 'r', encoding='utf-8') as handle:
                    template_data = json.load(handle)

                if isinstance(template_data, dict):
                    templates.append({
                        'filename': filename,
                        'template': template_data,
                    })
            except Exception as e:
                Logger.error(f'WebServer: Error loading template {filename}: {e}')

        return templates

    def _is_valid_session(self, session):
        """Return True when session matches expected timestamp format."""
        if not isinstance(session, str):
            return False

        return bool(self.SESSION_PATTERN.fullmatch(session))

    def _is_valid_image_filename(self, filename):
        """Return True when filename matches expected JPEG photo names."""
        if not isinstance(filename, str):
            return False

        return bool(self.IMAGE_FILENAME_PATTERN.fullmatch(filename))

    def _get_safe_photo_path(self, session, filename):
        """Return canonical photo path when request targets allowed JPEG file."""
        if not self._is_valid_session(session) or not self._is_valid_image_filename(filename):
            return None

        base_path = os.path.realpath(self.save_directory)
        requested_path = os.path.realpath(os.path.join(base_path, session, filename))

        if not requested_path.startswith(base_path + os.sep):
            return None

        if not os.path.isfile(requested_path):
            return None

        return requested_path

    def _get_log_files(self):
        """Return log files sorted by modification time, newest first."""
        log_files = []

        try:
            if not os.path.isdir(self.logs_directory):
                return log_files

            for filename in os.listdir(self.logs_directory):
                log_path = os.path.join(self.logs_directory, filename)
                if not os.path.isfile(log_path):
                    continue

                stat = os.stat(log_path)
                log_files.append({
                    'filename': filename,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(timespec='seconds'),
                    'size': stat.st_size,
                })
        except Exception as e:
            Logger.error(f'WebServer: Error listing log files: {e}')

        return sorted(log_files, key=lambda item: item['modified'], reverse=True)

    def _get_safe_log_path(self, filename):
        """Return canonical log path for a direct child of the logs directory."""
        if not isinstance(filename, str) or not self.LOG_FILENAME_PATTERN.fullmatch(filename):
            return None

        base_path = os.path.realpath(self.logs_directory)
        requested_path = os.path.realpath(os.path.join(base_path, filename))

        if os.path.dirname(requested_path) != base_path:
            return None

        if not os.path.isfile(requested_path):
            return None

        return requested_path

    def _delete_all_log_files(self):
        """Delete all direct files from the logs directory."""
        deleted_files = 0

        if not os.path.isdir(self.logs_directory):
            return deleted_files

        for log_file in self._get_log_files():
            log_path = self._get_safe_log_path(log_file['filename'])
            if log_path is None:
                continue

            os.remove(log_path)
            deleted_files += 1

        return deleted_files

    def _format_bytes(self, value):
        """Return a compact human-readable byte size."""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(value)

        for unit in units:
            if size < 1024 or unit == units[-1]:
                return f'{size:.1f} {unit}' if unit != 'B' else f'{int(size)} {unit}'
            size /= 1024

    def _get_disk_usage_info(self):
        """Return disk usage for the photo save directory mount point."""
        usage_path = self.save_directory if os.path.exists(self.save_directory) else self.project_root
        usage = shutil.disk_usage(usage_path)
        used = usage.total - usage.free
        used_percent = 0 if usage.total == 0 else round((used / usage.total) * 100, 1)

        return {
            'path': usage_path,
            'total': self._format_bytes(usage.total),
            'used': self._format_bytes(used),
            'free': self._format_bytes(usage.free),
            'used_percent': used_percent,
        }

    def _get_usage_stats(self):
        """Return usage statistics with the same headline values as /stats."""
        stats = self.stats_store.load() if self.stats_store is not None else {
            'photos_taken': 0,
            'prints': 0,
            'downloads': 0,
            'gallery_views': 0,
            'collage_views': 0,
            'image_views': 0,
            'first_photo_date': None,
            'last_photo_date': None,
            'last_print_date': None,
            'last_download_date': None,
            'sessions': [],
        }
        stats['photos_taken'] = len(self._get_all_collages())
        return stats

    def _get_all_collages(self):
        """Get all collage files sorted by date (newest first)."""
        collages = []
        try:
            if not os.path.exists(self.save_directory):
                return collages
            
            # List all subdirectories (sessions)
            for session_dir in sorted(os.listdir(self.save_directory), reverse=True):
                session_path = os.path.join(self.save_directory, session_dir)
                if not os.path.isdir(session_path):
                    continue
                
                # Find collage in this session
                for filename in os.listdir(session_path):
                    if filename == 'collage.jpg':
                        collages.append({
                            'session': session_dir,
                            'path': os.path.join(session_path, filename),
                            'filename': filename
                        })
                        break
        except Exception as e:
            Logger.error(f'WebServer: Error getting collages: {e}')
        
        return collages

    def _get_all_downloadable_photos(self):
        """Get all downloadable photos sorted by session and filename."""
        photos = []

        try:
            if not os.path.exists(self.save_directory):
                return photos

            for session_dir in sorted(os.listdir(self.save_directory), reverse=True):
                session_path = os.path.join(self.save_directory, session_dir)
                if not os.path.isdir(session_path) or not self._is_valid_session(session_dir):
                    continue

                for filename in sorted(os.listdir(session_path)):
                    if not self._is_valid_image_filename(filename):
                        continue

                    photo_path = os.path.join(session_path, filename)
                    if not os.path.isfile(photo_path):
                        continue

                    photos.append({
                        'session': session_dir,
                        'filename': filename,
                        'path': photo_path,
                        'archive_name': os.path.join(session_dir, filename),
                    })
        except Exception as e:
            Logger.error(f'WebServer: Error getting downloadable photos: {e}')

        return photos

    def _delete_all_sessions(self):
        """Delete all valid session directories and reset photo-related stats."""
        deleted_sessions = 0

        try:
            if os.path.isdir(self.save_directory):
                for session_dir in os.listdir(self.save_directory):
                    session_path = os.path.join(self.save_directory, session_dir)
                    if not os.path.isdir(session_path) or not self._is_valid_session(session_dir):
                        continue

                    shutil.rmtree(session_path)
                    deleted_sessions += 1

            if self.stats_store is not None:
                self.stats_store.reset()
        except Exception as e:
            Logger.error(f'WebServer: Error deleting sessions: {e}')
            raise

        return deleted_sessions

    def _load_config_text(self):
        """Return config.ini content as text."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as handle:
                return handle.read()
        except Exception as e:
            Logger.error(f'WebServer: Error loading config file: {e}')
            raise

    def _save_config_text(self, content):
        """Persist config.ini content to disk."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as handle:
                handle.write(content)
        except Exception as e:
            Logger.error(f'WebServer: Error saving config file: {e}')
            raise

    def _load_config_parser(self, content=None):
        """Return a ConfigParser loaded from config.ini content."""
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read_string(content if content is not None else self._load_config_text())
        return parser

    def _get_form_field_name(self, section, option):
        return f'{section}__{option}'

    def _normalize_form_value(self, field_spec, raw_value):
        value = '' if raw_value is None else str(raw_value).strip()
        control = field_spec['control']

        if control == 'checkbox':
            return value.lower() in ('1', 'true', 'yes', 'on')

        if field_spec['option'] == 'ADMIN_PASSWORD':
            return ''

        if field_spec.get('number_type') == 'optional_int' and value.upper() == 'NONE':
            return ''

        if field_spec.get('none_means_empty') and value.upper() == 'NONE':
            return ''

        return value

    def _build_select_choices(self, field_spec, current_value):
        choices = list(field_spec.get('choices', ()))
        choice_values = {value for value, _label in choices}
        if current_value and current_value not in choice_values:
            choices.append((current_value, f'Current: {current_value}'))
        return choices

    def _get_current_config_values(self, parser):
        values = {}
        for section_spec in self.CONFIG_FORM_SECTIONS:
            for field_spec in section_spec['fields']:
                section = field_spec['section']
                option = field_spec['option']
                values[(section, option)] = parser.get(section, option, fallback=field_spec.get('default', ''))
        return values

    def _get_config_field_spec(self, section, option):
        for section_spec in self.CONFIG_FORM_SECTIONS:
            for field_spec in section_spec['fields']:
                if field_spec['section'] == section and field_spec['option'] == option:
                    return field_spec
        return None

    def _resolve_start_screen_background_path(self, configured_path=None, use_default=False):
        default_path = (Path(self.project_root) / self.START_SCREEN_BACKGROUND_DEFAULT).resolve()
        if use_default:
            return str(default_path)

        raw_path = (configured_path or '').strip() or self.START_SCREEN_BACKGROUND_DEFAULT
        background_path = Path(raw_path).expanduser()
        if not background_path.is_absolute():
            background_path = Path(self.project_root) / background_path
        if background_path.is_file():
            return str(background_path.resolve())
        return str(default_path)

    def _get_start_screen_preview(self, form_values=None):
        parser = self._load_config_parser()
        form_values = form_values or {}
        configured_background_path = parser.get('StartScreen', 'BACKGROUND_IMAGE', fallback=self.START_SCREEN_BACKGROUND_DEFAULT)
        resolved_default_path = self._resolve_start_screen_background_path(use_default=True)
        resolved_current_path = self._resolve_start_screen_background_path(configured_path=configured_background_path)
        has_custom_background = (
            str(configured_background_path).strip() != self.START_SCREEN_BACKGROUND_DEFAULT
            and resolved_current_path != resolved_default_path
        )

        def get_value(section, option):
            field_spec = self._get_config_field_spec(section, option)
            if field_spec is None:
                return ''
            field_name = self._get_form_field_name(section, option)
            raw_value = form_values.get(field_name, parser.get(section, option, fallback=field_spec.get('default', '')))
            return self._normalize_form_value(field_spec, raw_value)

        text_color = get_value('StartScreen', 'TEXT_COLOR') or self.START_SCREEN_TEXT_COLOR_DEFAULT
        if not re.fullmatch(r'#?[0-9A-Fa-f]{6}', text_color):
            text_color = self.START_SCREEN_TEXT_COLOR_DEFAULT
        text_color = f'#{text_color.lstrip("#").upper()}'

        show_title = bool(get_value('StartScreen', 'SHOW_TITLE'))
        show_instructions = bool(get_value('StartScreen', 'SHOW_INSTRUCTIONS'))

        return {
            'image_url': '/api/admin/startscreen-preview-image',
            'default_image_url': '/api/admin/startscreen-preview-image?default=1',
            'has_custom_background': has_custom_background,
            'custom_background_path': configured_background_path if has_custom_background else '',
            'text': 'PHOTO BOOTH',
            'instructions_text': 'TAP TO START',
            'text_color': text_color,
            'show_title': show_title,
            'show_instructions': show_instructions,
            'version_text': 'Version 1.2',
        }

    def _get_config_form_sections(self, form_values=None):
        parser = self._load_config_parser()
        form_values = form_values or {}
        sections = []

        for section_spec in self.CONFIG_FORM_SECTIONS:
            rendered_fields = []
            for field_spec in section_spec['fields']:
                section = field_spec['section']
                option = field_spec['option']
                field_name = self._get_form_field_name(section, option)
                raw_value = form_values.get(field_name, parser.get(section, option, fallback=field_spec.get('default', '')))
                normalized_value = self._normalize_form_value(field_spec, raw_value)

                rendered_field = dict(field_spec)
                rendered_field['name'] = field_name
                rendered_field['id'] = field_name.lower()
                rendered_field['value'] = normalized_value
                rendered_field['checked'] = bool(normalized_value) if field_spec['control'] == 'checkbox' else False

                if field_spec['control'] == 'select':
                    rendered_field['choices'] = self._build_select_choices(field_spec, normalized_value)

                rendered_fields.append(rendered_field)

            sections.append({
                'title': section_spec['title'],
                'description': section_spec.get('description'),
                'fields': rendered_fields,
            })

        return sections

    def _coerce_form_field_value(self, field_spec, submitted_value, current_value):
        control = field_spec['control']

        if control == 'checkbox':
            return 'True' if submitted_value else 'False'

        value = '' if submitted_value is None else str(submitted_value).strip()
        option = field_spec['option']
        number_type = field_spec.get('number_type')

        if option == 'ADMIN_PASSWORD':
            return current_value if value == '' else value

        if option == 'TEXT_COLOR':
            if not re.fullmatch(r'#?[0-9A-Fa-f]{6}', value):
                raise ValueError('Text color must be a 6-digit hex value such as #FFFFFF.')
            return f'#{value.lstrip("#").upper()}'

        if option == 'CALIBRATION':
            return value or 'None'

        if number_type == 'int':
            if value == '':
                raise ValueError(f'{field_spec["label"]} is required.')
            parsed_value = int(value)
            if 'min' in field_spec and parsed_value < field_spec['min']:
                raise ValueError(f'{field_spec["label"]} must be at least {field_spec["min"]}.')
            if 'max' in field_spec and parsed_value > field_spec['max']:
                raise ValueError(f'{field_spec["label"]} must be at most {field_spec["max"]}.')
            return str(parsed_value)

        if number_type == 'float':
            if value == '':
                raise ValueError(f'{field_spec["label"]} is required.')
            parsed_value = float(value)
            if 'min' in field_spec and parsed_value < field_spec['min']:
                raise ValueError(f'{field_spec["label"]} must be at least {field_spec["min"]}.')
            if 'max' in field_spec and parsed_value > field_spec['max']:
                raise ValueError(f'{field_spec["label"]} must be at most {field_spec["max"]}.')
            return str(parsed_value)

        if number_type == 'optional_int':
            if value == '':
                return 'None'
            parsed_value = int(value)
            if 'min' in field_spec and parsed_value < field_spec['min']:
                raise ValueError(f'{field_spec["label"]} must be at least {field_spec["min"]}.')
            if 'max' in field_spec and parsed_value > field_spec['max']:
                raise ValueError(f'{field_spec["label"]} must be at most {field_spec["max"]}.')
            return str(parsed_value)

        if field_spec.get('none_means_empty'):
            return value or 'None'

        return value

    def _save_start_screen_background_upload(self, uploaded_file):
        if uploaded_file is None:
            return None

        filename = os.path.basename((uploaded_file.filename or '').strip())
        if not filename:
            return None

        extension = os.path.splitext(filename)[1].lower()
        if extension not in self.START_SCREEN_BACKGROUND_EXTENSIONS:
            raise ValueError('Start screen background must be a JPG or PNG image.')

        backgrounds_directory = os.path.join(self.project_root, 'assets', 'backgrounds')
        os.makedirs(backgrounds_directory, exist_ok=True)

        saved_filename = f'{self.START_SCREEN_BACKGROUND_BASENAME}{extension}'
        saved_path = os.path.join(backgrounds_directory, saved_filename)
        uploaded_file.save(saved_path)

        for extra_extension in self.START_SCREEN_BACKGROUND_EXTENSIONS:
            if extra_extension == extension:
                continue
            extra_path = os.path.join(backgrounds_directory, f'{self.START_SCREEN_BACKGROUND_BASENAME}{extra_extension}')
            if os.path.exists(extra_path):
                os.remove(extra_path)

        return f'./assets/backgrounds/{saved_filename}'

    def _delete_start_screen_background_upload(self):
        backgrounds_directory = os.path.join(self.project_root, 'assets', 'backgrounds')
        for extension in self.START_SCREEN_BACKGROUND_EXTENSIONS:
            background_path = os.path.join(backgrounds_directory, f'{self.START_SCREEN_BACKGROUND_BASENAME}{extension}')
            if os.path.exists(background_path):
                os.remove(background_path)

    def _reset_start_screen_background_settings(self, updates, submitted_form_values):
        self._delete_start_screen_background_upload()
        background_field_name = self._get_form_field_name('StartScreen', 'BACKGROUND_IMAGE')
        updates[('StartScreen', 'BACKGROUND_IMAGE')] = self.START_SCREEN_BACKGROUND_DEFAULT
        submitted_form_values[background_field_name] = self.START_SCREEN_BACKGROUND_DEFAULT

    def _collect_config_form_updates(self, form, parser):
        current_values = self._get_current_config_values(parser)
        updates = {}
        submitted_form_values = {}

        for section_spec in self.CONFIG_FORM_SECTIONS:
            for field_spec in section_spec['fields']:
                field_name = self._get_form_field_name(field_spec['section'], field_spec['option'])
                if field_spec['control'] == 'checkbox':
                    submitted_value = field_name in form
                    submitted_form_values[field_name] = submitted_value
                else:
                    submitted_value = form.get(field_name, '')
                    submitted_form_values[field_name] = submitted_value

                updates[(field_spec['section'], field_spec['option'])] = self._coerce_form_field_value(
                    field_spec,
                    submitted_value,
                    current_values[(field_spec['section'], field_spec['option'])],
                )

        return updates, submitted_form_values

    def _apply_config_updates(self, content, updates):
        section_values = {}
        for (section, option), value in updates.items():
            section_values.setdefault(section, {})[option] = value

        section_pattern = re.compile(r'^\s*\[(.+?)\]\s*$')
        option_pattern = re.compile(r'^([ \t]*)([^=;#][^=]*?)([ \t]*=[ \t]*)(.*?)(\r?\n?)$')
        lines = content.splitlines(keepends=True)
        rendered_lines = []
        existing_sections = set()
        seen_options = set()
        current_section = None
        line_ending = '\n'

        def append_missing_options(section):
            for option, value in section_values.get(section, {}).items():
                key = (section, option)
                if key in seen_options:
                    continue
                rendered_lines.append(f'{option} = {value}{line_ending}')
                seen_options.add(key)

        for line in lines:
            if line.endswith('\r\n'):
                line_ending = '\r\n'
            elif line.endswith('\n'):
                line_ending = '\n'

            section_match = section_pattern.match(line.strip())
            if section_match:
                if current_section is not None:
                    append_missing_options(current_section)
                current_section = section_match.group(1).strip()
                existing_sections.add(current_section)
                rendered_lines.append(line)
                continue

            option_match = option_pattern.match(line)
            if current_section is not None and option_match:
                option_name = option_match.group(2).strip()
                key = (current_section, option_name)
                if key in updates:
                    rendered_lines.append(f'{option_match.group(1)}{option_name} = {updates[key]}{option_match.group(5) or line_ending}')
                    seen_options.add(key)
                    continue

            rendered_lines.append(line)

        if current_section is not None:
            append_missing_options(current_section)

        for section, options in section_values.items():
            if section in existing_sections:
                continue
            if rendered_lines and rendered_lines[-1].strip():
                rendered_lines.append(line_ending)
            rendered_lines.append(f'[{section}]{line_ending}')
            for option, value in options.items():
                rendered_lines.append(f'{option} = {value}{line_ending}')

        return ''.join(rendered_lines)

    def _is_admin_password_valid(self, password):
        """Validate provided admin password."""
        if self.admin_password is None:
            return False

        return hmac.compare_digest((password or '').strip(), self.admin_password)

    def _is_admin_authenticated(self):
        """Return True when current session is authenticated."""
        return bool(session.get('is_admin_authenticated'))

    def _require_admin_auth(self):
        """Redirect unauthenticated users to admin login page."""
        if self._is_admin_authenticated():
            return None

        return redirect('/admin/login')

    def _refresh_admin_password_from_config(self, content):
        """Refresh in-memory admin password from config text."""
        self.admin_password = None
        password_match = re.search(r'^\s*ADMIN_PASSWORD\s*=\s*(.*?)\s*$', content, re.MULTILINE)
        if not password_match:
            return

        configured_password = password_match.group(1).strip()
        if configured_password and configured_password.upper() != 'NONE':
            self.admin_password = configured_password

    def _render_admin_login_page(self, error_message=None, success_message=None):
        """Render admin login page."""
        return render_template(
            'admin/login.html',
            admin_enabled=self.admin_password is not None,
            error_message=error_message,
            success_message=success_message,
        )

    def _render_admin_page(self, error_message=None, success_message=None, form_values=None):
        """Render admin page with typed configuration fields."""
        admin_enabled = self.admin_password is not None
        config_error_message = None

        try:
            config_sections = self._get_config_form_sections(form_values=form_values)
        except Exception as exc:
            Logger.error(f'WebServer: Error building admin config form: {exc}')
            config_sections = []
            config_error_message = 'Unable to load config.ini into the admin form.'

        if error_message and config_error_message:
            error_message = f'{error_message} {config_error_message}'
        elif config_error_message:
            error_message = config_error_message

        try:
            start_screen_preview = self._get_start_screen_preview(form_values=form_values)
        except Exception as exc:
            Logger.error(f'WebServer: Error building start screen preview: {exc}')
            start_screen_preview = {
                'image_url': '/api/admin/startscreen-preview-image',
                'default_image_url': '/api/admin/startscreen-preview-image?default=1',
                'has_custom_background': False,
                'custom_background_path': '',
                'text': 'PHOTO BOOTH',
                'instructions_text': 'TAP TO START',
                'text_color': self.START_SCREEN_TEXT_COLOR_DEFAULT,
                'show_title': self.START_SCREEN_SHOW_TITLE_DEFAULT,
                'show_instructions': self.START_SCREEN_SHOW_INSTRUCTIONS_DEFAULT,
                'version_text': 'Version 1.2',
            }

        return render_template(
            'admin/index.html',
            admin_enabled=admin_enabled,
            config_sections=config_sections,
            overview_stats=self._get_usage_stats(),
            start_screen_preview=start_screen_preview,
            disk_usage=self._get_disk_usage_info(),
            error_message=error_message,
            success_message=success_message,
        )

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.context_processor
        def inject_template_helpers():
            return {
                't': self.t,
                'current_language': self.i18n.language,
            }

        @self.app.route('/admin/editor')
        def admin_template_editor():
            """Expose the browser-based template editor inside the admin area."""
            auth_redirect = self._require_admin_auth()
            if auth_redirect is not None:
                return auth_redirect

            if not os.path.exists(self.template_editor_path):
                return 'Template editor not found', 404

            return render_template('editor/template_editor.html')

        @self.app.route('/admin/logs')
        def admin_logs():
            """Expose application logs inside the admin area."""
            auth_redirect = self._require_admin_auth()
            if auth_redirect is not None:
                return auth_redirect

            return render_template('admin/logs.html')

        @self.app.route('/api/admin/logs', methods=['GET'])
        def list_admin_logs():
            """List available log files for authenticated admins."""
            auth_redirect = self._require_admin_auth()
            if auth_redirect is not None:
                return auth_redirect

            return jsonify({'logs': self._get_log_files()})

        @self.app.route('/api/admin/logs/<path:filename>', methods=['GET'])
        def read_admin_log(filename):
            """Read one log file for authenticated admins."""
            auth_redirect = self._require_admin_auth()
            if auth_redirect is not None:
                return auth_redirect

            log_path = self._get_safe_log_path(filename)
            if log_path is None:
                return jsonify({'error': 'Log file not found'}), 404

            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as handle:
                    content = handle.read()
            except Exception as e:
                Logger.error(f'WebServer: Error reading log file {filename}: {e}')
                return jsonify({'error': 'Unable to read log file'}), 500

            return jsonify({'filename': os.path.basename(log_path), 'content': content})

        @self.app.route('/api/admin/startscreen-preview-image', methods=['GET'])
        def startscreen_preview_image():
            """Serve the configured start screen background for admin preview."""
            auth_redirect = self._require_admin_auth()
            if auth_redirect is not None:
                return auth_redirect

            use_default = request.args.get('default') == '1'

            try:
                configured_path = None
                if not use_default:
                    parser = self._load_config_parser()
                    configured_path = parser.get('StartScreen', 'BACKGROUND_IMAGE', fallback=self.START_SCREEN_BACKGROUND_DEFAULT)
                image_path = self._resolve_start_screen_background_path(configured_path=configured_path, use_default=use_default)
            except Exception as e:
                Logger.error(f'WebServer: Error preparing start screen preview image: {e}')
                return 'Preview unavailable', 500

            response = send_file(image_path)
            response.headers['Cache-Control'] = 'no-store'
            return response

        @self.app.route('/api/admin/logs', methods=['DELETE'])
        def delete_admin_logs():
            """Delete all log files for authenticated admins."""
            auth_redirect = self._require_admin_auth()
            if auth_redirect is not None:
                return auth_redirect

            try:
                deleted_files = self._delete_all_log_files()
            except Exception as e:
                Logger.error(f'WebServer: Error deleting log files: {e}')
                return jsonify({'error': 'Unable to delete log files'}), 500

            return jsonify({'deleted': deleted_files})

        @self.app.route('/api/templates', methods=['GET'])
        def list_templates():
            """List templates stored on disk."""
            return jsonify({'templates': self._load_template_definitions()})

        @self.app.route('/api/templates', methods=['POST'])
        def save_template():
            """Save a template into the templates directory."""
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict):
                return jsonify({'error': 'Invalid JSON payload'}), 400

            template_data = payload.get('template')
            if not isinstance(template_data, dict):
                return jsonify({'error': 'Missing template object'}), 400

            if 'name' not in template_data or 'page' not in template_data:
                return jsonify({'error': 'Template must include at least name and page'}), 400

            requested_filename = payload.get('filename')
            filename = self._sanitize_template_filename(
                requested_filename,
                template_data.get('name', 'template')
            )

            try:
                os.makedirs(self.templates_directory, exist_ok=True)

                if not requested_filename:
                    filename = self._get_unique_template_filename(filename)

                template_path = os.path.join(self.templates_directory, filename)
                with open(template_path, 'w', encoding='utf-8') as handle:
                    json.dump(template_data, handle, indent=2, ensure_ascii=False)
                    handle.write('\n')
            except Exception as e:
                Logger.error(f'WebServer: Error saving template {filename}: {e}')
                return jsonify({'error': 'Unable to save template'}), 500

            return jsonify({'saved': True, 'filename': filename})

        @self.app.route('/api/templates/<path:filename>', methods=['DELETE'])
        def delete_template(filename):
            """Delete a stored template from the templates directory."""
            safe_filename = self._sanitize_template_filename(filename)
            template_path = os.path.join(self.templates_directory, safe_filename)

            if not os.path.isfile(template_path):
                return jsonify({'error': 'Template not found'}), 404

            try:
                os.remove(template_path)
            except Exception as e:
                Logger.error(f'WebServer: Error deleting template {safe_filename}: {e}')
                return jsonify({'error': 'Unable to delete template'}), 500

            return jsonify({'deleted': True, 'filename': safe_filename})
        
        @self.app.route('/')
        def index():
            """Main page - show gallery."""
            collages = self._get_all_collages()
            
            if not collages:
                return render_template('gallery/empty.html')
            
            # Redirect to latest collage
            latest = collages[0]
            return redirect(f'/collage/{latest["session"]}')
        
        @self.app.route('/gallery')
        def gallery():
            """Gallery view with all collages."""
            if self.stats_store is not None:
                self.stats_store.track_event('gallery_view')
            collages = self._get_all_collages()

            if not collages:
                return render_template('gallery/empty.html')

            return render_template('gallery/index.html', collages=collages)
        
        @self.app.route('/collage/<session>')
        def view_collage(session):
            """View a single collage fullscreen."""
            collage_path = self._get_safe_photo_path(session, 'collage.jpg')
            
            if collage_path is None:
                return redirect('/')
            
            if self.stats_store is not None:
                self.stats_store.track_event('collage_view')

            return render_template('gallery/collage.html', session=session)
        
        @self.app.route('/image/<session>/<filename>')
        def serve_image(session, filename):
            """Serve an image file."""
            image_path = self._get_safe_photo_path(session, filename)
            
            if image_path is None:
                return "Not found", 404
            
            if self.stats_store is not None:
                self.stats_store.track_event('image_view')
            return send_file(image_path, mimetype='image/jpeg')
        
        @self.app.route('/download/<session>/<filename>')
        def download_image(session, filename):
            """Download an image file."""
            image_path = self._get_safe_photo_path(session, filename)
            
            if image_path is None:
                return "Not found", 404
            
            if self.stats_store is not None:
                self.stats_store.track_event('download')
            return send_file(
                image_path,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name=f'photobooth_{session}.jpg'
            )

        @self.app.route('/download/all-photos')
        def download_all_photos():
            """Download all photos as a ZIP archive."""
            photos = self._get_all_downloadable_photos()

            if not photos:
                return 'No photos found', 404

            archive_buffer = io.BytesIO()

            try:
                with zipfile.ZipFile(archive_buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
                    for photo in photos:
                        archive.write(photo['path'], arcname=photo['archive_name'])
            except Exception as e:
                Logger.error(f'WebServer: Error creating photo archive: {e}')
                return 'Unable to create archive', 500

            archive_buffer.seek(0)
            if self.stats_store is not None:
                self.stats_store.track_event('download')

            return send_file(
                archive_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name='photobooth_photos.zip'
            )

        @self.app.route('/admin')
        def admin_page():
            """Protected admin page."""
            auth_redirect = self._require_admin_auth()
            if auth_redirect is not None:
                return auth_redirect

            restart_flag = request.args.get('restart') == '1'
            delete_all_status = request.args.get('delete_all')
            deleted_sessions_count = request.args.get('deleted_sessions')
            success_message = 'Application restart requested. Page may become unavailable for a few seconds.' if restart_flag else None
            error_message = None

            if delete_all_status == 'invalid-password':
                error_message = 'Admin password confirmation is invalid.'
            elif delete_all_status == 'error':
                error_message = 'Error while deleting files.'
            elif delete_all_status == 'success':
                try:
                    deleted_sessions = int(deleted_sessions_count or '0')
                except ValueError:
                    deleted_sessions = 0
                success_message = f'{deleted_sessions} session(s) deleted.'

            return self._render_admin_page(error_message=error_message, success_message=success_message)

        @self.app.route('/admin/login')
        def admin_login_page():
            """Admin login page."""
            if self._is_admin_authenticated():
                return redirect('/admin')

            logout_flag = request.args.get('logout') == '1'
            return self._render_admin_login_page(success_message='Logged out successfully.' if logout_flag else None)

        @self.app.route('/admin/login', methods=['POST'])
        def admin_login():
            """Authenticate admin user."""
            if self.admin_password is None:
                return self._render_admin_login_page(error_message='Admin access is disabled. Configure ADMIN_PASSWORD in config.ini.'), 403

            provided_password = request.form.get('password') or ''
            if not self._is_admin_password_valid(provided_password):
                session.clear()
                return self._render_admin_login_page(error_message='Invalid password.'), 403

            session.clear()
            session['is_admin_authenticated'] = True
            return redirect('/admin')

        @self.app.route('/admin/logout')
        def admin_logout():
            """Log out admin user."""
            session.clear()
            return redirect('/admin/login?logout=1')

        @self.app.route('/admin/delete-all', methods=['POST'])
        def delete_all_sessions():
            """Delete all saved sessions after password validation."""
            auth_redirect = self._require_admin_auth()
            if auth_redirect is not None:
                return auth_redirect

            if self.admin_password is None:
                session.clear()
                return self._render_admin_login_page(error_message='Admin access is disabled. Configure ADMIN_PASSWORD in config.ini.'), 403

            confirmation_password = request.form.get(self.DELETE_ALL_PASSWORD_FIELD) or ''
            if not self._is_admin_password_valid(confirmation_password):
                return redirect('/admin?delete_all=invalid-password'), 303

            try:
                deleted_sessions = self._delete_all_sessions()
            except Exception:
                return redirect('/admin?delete_all=error'), 303

            return redirect(f'/admin?delete_all=success&deleted_sessions={deleted_sessions}'), 303

        @self.app.route('/admin/config', methods=['POST'])
        def save_admin_config():
            """Save config.ini after password validation."""
            auth_redirect = self._require_admin_auth()
            if auth_redirect is not None:
                return auth_redirect

            if self.admin_password is None:
                session.clear()
                return self._render_admin_login_page(error_message='Admin access is disabled. Configure ADMIN_PASSWORD in config.ini.'), 403

            submitted_form_values = {}

            try:
                current_config = self._load_config_text()
                parser = self._load_config_parser(current_config)
                updates, submitted_form_values = self._collect_config_form_updates(request.form, parser)
                if request.form.get(self.START_SCREEN_BACKGROUND_REMOVE_FIELD):
                    self._reset_start_screen_background_settings(updates, submitted_form_values)
                else:
                    uploaded_background_path = self._save_start_screen_background_upload(
                        request.files.get(self.START_SCREEN_BACKGROUND_UPLOAD_FIELD)
                    )
                    if uploaded_background_path is not None:
                        field_name = self._get_form_field_name('StartScreen', 'BACKGROUND_IMAGE')
                        updates[('StartScreen', 'BACKGROUND_IMAGE')] = uploaded_background_path
                        submitted_form_values[field_name] = uploaded_background_path
                updated_config = self._apply_config_updates(current_config, updates)
            except ValueError as exc:
                return self._render_admin_page(error_message=str(exc), form_values=submitted_form_values), 400
            except Exception as exc:
                Logger.error(f'WebServer: Error while preparing config.ini update: {exc}')
                return self._render_admin_page(error_message='Error while preparing config.ini.', form_values=request.form), 500

            try:
                self._save_config_text(updated_config)
            except Exception:
                return self._render_admin_page(error_message='Error while saving config.ini.', form_values=submitted_form_values), 500

            try:
                updated_config = self._load_config_text()
                self._refresh_admin_password_from_config(updated_config)
            except Exception:
                return self._render_admin_page(success_message='config.ini saved. Restart app to apply all changes.')

            if self.admin_password is None:
                session.clear()
                return self._render_admin_login_page(success_message='config.ini saved. Admin password disabled. Sign in is now disabled.')

            return self._render_admin_page(success_message='config.ini saved. Restart app to apply all changes.')

        @self.app.route('/admin/restart', methods=['POST'])
        def restart_app():
            """Restart application after password validation."""
            auth_redirect = self._require_admin_auth()
            if auth_redirect is not None:
                return auth_redirect

            if self.admin_password is None:
                session.clear()
                return self._render_admin_login_page(error_message='Admin access is disabled. Configure ADMIN_PASSWORD in config.ini.'), 403

            if not callable(self.restart_callback):
                return self._render_admin_page(error_message='Restart callback is unavailable.'), 500

            try:
                def request_restart_after_response():
                    try:
                        self.restart_callback()
                    except Exception as e:
                        Logger.error(f'WebServer: Delayed restart failed: {e}')

                threading.Timer(0.5, request_restart_after_response).start()
            except Exception as e:
                Logger.error(f'WebServer: Error restarting app: {e}')
                return self._render_admin_page(error_message='Error while restarting app.'), 500

            return redirect('/admin?restart=1')
        
        @self.app.route('/stats')
        def statistics():
            """Hidden statistics page - shows usage analytics."""
            stats = self._get_usage_stats()
            collages = self._get_all_collages()
            downloadable_photos = self._get_all_downloadable_photos()

            return render_template(
                'stats.html',
                collages=collages,
                downloadable_photos=downloadable_photos,
                print_limit=self.stats_store.get_print_limit_info() if self.stats_store is not None else {
                    'enabled': False,
                    'max_prints': None,
                    'prints': 0,
                    'remaining': None,
                    'reached': False,
                },
                stats=stats,
            )
        
        # Captive portal detection URLs
        @self.app.route('/generate_204')
        @self.app.route('/gen_204')
        @self.app.route('/hotspot-detect.html')
        @self.app.route('/library/test/success.html')
        @self.app.route('/canonical.html')
        @self.app.route('/connecttest.txt')
        @self.app.route('/ncsi.txt')
        @self.app.route('/redirect')
        @self.app.route('/fwlink')
        @self.app.route('/check_network_status.txt')
        @self.app.route('/mobile/status.php')
        def captive():
            return redirect('/')

        @self.app.route('/<path:path>', methods=['GET', 'HEAD'])
        def captive_fallback(path):
            """Redirect unknown HTTP paths requested through captive portal probes."""
            return redirect('/')
    
    def start(self, force_restart=False):
        """Start the web server in a separate thread."""
        with self._server_lock:
            if self.server_thread and self.server_thread.is_alive() and not force_restart:
                Logger.warning('WebServer: Server already running')
                return True

            if force_restart and self.server is not None:
                try:
                    self.server.shutdown()
                except Exception as e:
                    Logger.warning(f'WebServer: shutdown before restart failed: {e}')
                self.server = None

            startup_event = threading.Event()
            startup_state = {'error': None}

            def run_server():
                try:
                    Logger.info(f'WebServer: Starting on {self.host}:{self.port}')
                    self.server = make_server(self.host, self.port, self.app, threaded=True)
                    startup_event.set()
                    self.server.serve_forever()
                except BaseException as e:
                    startup_state['error'] = e
                    if not startup_event.is_set():
                        startup_event.set()

                    # werkzeug can abort startup with SystemExit on bind errors
                    # (for example "Address already in use"). Catch it here so
                    # the Kivy app does not block for the full timeout.
                    if isinstance(e, SystemExit):
                        Logger.error(
                            f'WebServer: Failed to start on {self.host}:{self.port}: '
                            f'process exited during startup (likely port already in use)'
                        )
                    else:
                        Logger.error(f'WebServer: Failed to start on {self.host}:{self.port}: {e}')
                finally:
                    self.server = None

            self.server_thread = threading.Thread(target=run_server, name='webserver-main', daemon=True)
            self.server_thread.start()
            startup_event.wait(timeout=5)

            if not startup_event.is_set():
                Logger.error('WebServer: Server startup timed out')
                return False

            if startup_state['error'] is not None:
                return False

            self._ensure_watchdog()
            Logger.info('WebServer: Server started successfully')
            return True
    
    def stop(self):
        """Stop the web server."""
        self._watchdog_stop.set()
        if self.server is not None:
            self.server.shutdown()
            Logger.info('WebServer: Server stopped')
        else:
            Logger.info('WebServer: Stop requested but server is not running')

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)
        self.server_thread = None

        if self._watchdog_thread and self._watchdog_thread.is_alive():
            self._watchdog_thread.join(timeout=5)
        self._watchdog_thread = None

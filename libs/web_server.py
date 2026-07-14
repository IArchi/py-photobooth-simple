import os
import hmac
import io
import json
import re
import shutil
import threading
import zipfile
from datetime import datetime
from flask import Flask, jsonify, request, send_file, render_template_string, redirect, session
from werkzeug.serving import make_server
from kivy.logger import Logger

class WebServer:
    """Flask web server for photo gallery with captive portal."""

    SESSION_PATTERN = re.compile(r'^\d{8}_\d{6}$')
    IMAGE_FILENAME_PATTERN = re.compile(r'^(?:collage|capture-\d+)\.jpg$', re.IGNORECASE)
    ADMIN_PASSWORD_PLACEHOLDER = '__HIDDEN__'
    
    def __init__(self, save_directory, host='0.0.0.0', port=5000, admin_password=None, restart_callback=None):
        self.save_directory = save_directory
        self.host = host
        self.port = port
        self.admin_password = admin_password.strip() if isinstance(admin_password, str) and admin_password.strip() else None
        self.restart_callback = restart_callback
        self.app = Flask(__name__)
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
        self.stats_file = os.path.join(save_directory, '.stats.json')
        self.stats_lock = threading.Lock()
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_file = os.path.join(self.project_root, 'config.ini')
        self.templates_directory = os.path.join(self.project_root, 'templates')
        self.template_editor_path = os.path.join(self.project_root, 'tools', 'template_editor.html')
        self._setup_routes()

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
    
    def _load_stats(self):
        """Load statistics from JSON file."""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            Logger.error(f'WebServer: Error loading stats: {e}')
        
        # Default stats structure
        return {
            'photos_taken': 0,
            'downloads': 0,
            'gallery_views': 0,
            'collage_views': 0,
            'image_views': 0,
            'first_photo_date': None,
            'last_photo_date': None,
            'last_download_date': None,
            'sessions': []
        }
    
    def _save_stats(self, stats):
        """Save statistics to JSON file."""
        try:
            with self.stats_lock:
                with open(self.stats_file, 'w') as f:
                    json.dump(stats, f, indent=2)
        except Exception as e:
            Logger.error(f'WebServer: Error saving stats: {e}')
    
    def _track_event(self, event_type, session=None):
        """Track an event in statistics."""
        try:
            stats = self._load_stats()
            
            if event_type == 'download':
                stats['downloads'] += 1
                stats['last_download_date'] = datetime.now().isoformat()
            elif event_type == 'gallery_view':
                stats['gallery_views'] += 1
            elif event_type == 'collage_view':
                stats['collage_views'] += 1
            elif event_type == 'image_view':
                stats['image_views'] += 1
            
            self._save_stats(stats)
        except Exception as e:
            Logger.error(f'WebServer: Error tracking event: {e}')
    
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

            stats = self._load_stats()
            stats['photos_taken'] = 0
            stats['downloads'] = 0
            stats['gallery_views'] = 0
            stats['collage_views'] = 0
            stats['image_views'] = 0
            stats['first_photo_date'] = None
            stats['last_photo_date'] = None
            stats['last_download_date'] = None
            stats['sessions'] = []
            self._save_stats(stats)
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

    def _mask_admin_password_in_config(self, content):
        """Hide admin password before rendering config.ini to browser."""
        return re.sub(
            r'^(\s*ADMIN_PASSWORD\s*=\s*).*$' ,
            rf'\1{self.ADMIN_PASSWORD_PLACEHOLDER}',
            content,
            flags=re.MULTILINE,
        )

    def _merge_masked_admin_password(self, content):
        """Restore in-memory admin password when masked placeholder is submitted."""
        def replace_password(match):
            configured_password = match.group(2).strip()
            if configured_password != self.ADMIN_PASSWORD_PLACEHOLDER:
                return match.group(0)

            restored_password = self.admin_password if self.admin_password is not None else 'None'
            return f'{match.group(1)}{restored_password}'

        return re.sub(
            r'^(\s*ADMIN_PASSWORD\s*=\s*)(.*?)\s*$' ,
            replace_password,
            content,
            flags=re.MULTILINE,
        )

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
        admin_enabled = self.admin_password is not None

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PhotoBooth - Admin Login</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }}
                .card {{
                    width: 100%;
                    max-width: 420px;
                    background: white;
                    border-radius: 20px;
                    padding: 32px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.35);
                }}
                h1 {{
                    color: #111827;
                    margin-bottom: 12px;
                    font-size: 30px;
                }}
                p {{
                    color: #4b5563;
                    line-height: 1.5;
                    margin-bottom: 18px;
                }}
                .status {{
                    border-radius: 12px;
                    padding: 14px 16px;
                    margin-bottom: 16px;
                }}
                .status.error {{
                    background: #fff5f5;
                    color: #b91c1c;
                    border: 1px solid #fecaca;
                }}
                .status.success {{
                    background: #f0fdf4;
                    color: #15803d;
                    border: 1px solid #bbf7d0;
                }}
                label {{
                    display: block;
                    color: #111827;
                    font-weight: 600;
                    margin-bottom: 8px;
                }}
                input[type="password"] {{
                    width: 100%;
                    padding: 14px 16px;
                    border: 1px solid #d1d5db;
                    border-radius: 12px;
                    font-size: 16px;
                    margin-bottom: 16px;
                }}
                .actions {{
                    display: flex;
                    gap: 12px;
                    flex-wrap: wrap;
                }}
                .btn {{
                    display: inline-block;
                    padding: 14px 24px;
                    border-radius: 999px;
                    text-decoration: none;
                    font-weight: 700;
                    border: none;
                    cursor: pointer;
                    font-size: 15px;
                }}
                .btn-primary {{
                    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
                    color: white;
                }}
                .btn-secondary {{
                    background: #e5e7eb;
                    color: #111827;
                }}
                .btn-disabled {{
                    opacity: 0.5;
                    cursor: not-allowed;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🔐 Admin login</h1>
                <p>Authentication required before opening admin panel.</p>
                {f'<div class="status error">{error_message}</div>' if error_message else ''}
                {f'<div class="status success">{success_message}</div>' if success_message else ''}
                {'<div class="status error">ADMIN_PASSWORD is not set in config.ini. Admin access is disabled.</div>' if not admin_enabled else ''}
                <form method="post" action="/admin/login">
                    <label for="password">Admin password</label>
                    <input id="password" name="password" type="password" autocomplete="current-password" placeholder="Password" {'disabled' if not admin_enabled else ''}>
                    <div class="actions">
                        <button type="submit" class="btn btn-primary{' btn-disabled' if not admin_enabled else ''}" {'disabled' if not admin_enabled else ''}>Sign in</button>
                        <a href="/stats" class="btn btn-secondary">Back to stats</a>
                    </div>
                </form>
            </div>
        </body>
        </html>
        """

        return render_template_string(html)

    def _render_admin_page(self, error_message=None, success_message=None, config_content=None):
        """Render admin page used to delete all saved photos."""
        sessions_count = len(self._get_all_collages())
        files_count = len(self._get_all_downloadable_photos())
        admin_enabled = self.admin_password is not None
        if config_content is None:
            try:
                config_content = self._mask_admin_password_in_config(self._load_config_text())
            except Exception:
                config_content = 'Unable to load config.ini'

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PhotoBooth - Admin</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(135deg, #1f1f1f 0%, #3a3a3a 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }}
                .card {{
                    width: 100%;
                    max-width: 560px;
                    background: white;
                    border-radius: 20px;
                    padding: 32px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.35);
                }}
                h1 {{
                    color: #111;
                    margin-bottom: 12px;
                    font-size: 32px;
                }}
                p {{
                    color: #555;
                    line-height: 1.5;
                    margin-bottom: 18px;
                }}
                .warning {{
                    background: #fff5f5;
                    border: 1px solid #fecaca;
                    color: #b91c1c;
                    border-radius: 12px;
                    padding: 16px;
                    margin-bottom: 20px;
                }}
                .status {{
                    border-radius: 12px;
                    padding: 14px 16px;
                    margin-bottom: 16px;
                }}
                .status.error {{
                    background: #fff5f5;
                    color: #b91c1c;
                    border: 1px solid #fecaca;
                }}
                .status.success {{
                    background: #f0fdf4;
                    color: #15803d;
                    border: 1px solid #bbf7d0;
                }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 12px;
                    margin-bottom: 24px;
                }}
                .stat {{
                    background: #f8fafc;
                    border-radius: 12px;
                    padding: 16px;
                }}
                .stat-label {{
                    color: #64748b;
                    font-size: 13px;
                    margin-bottom: 8px;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                }}
                .stat-value {{
                    color: #111827;
                    font-size: 28px;
                    font-weight: 700;
                }}
                label {{
                    display: block;
                    color: #111827;
                    font-weight: 600;
                    margin-bottom: 8px;
                }}
                input[type="password"] {{
                    width: 100%;
                    padding: 14px 16px;
                    border: 1px solid #d1d5db;
                    border-radius: 12px;
                    font-size: 16px;
                    margin-bottom: 16px;
                }}
                .actions {{
                    display: flex;
                    gap: 12px;
                    flex-wrap: wrap;
                }}
                .section {{
                    margin-top: 24px;
                    padding-top: 24px;
                    border-top: 1px solid #e5e7eb;
                }}
                .section h2 {{
                    color: #111827;
                    margin-bottom: 12px;
                    font-size: 22px;
                }}
                textarea {{
                    width: 100%;
                    min-height: 320px;
                    padding: 16px;
                    border: 1px solid #d1d5db;
                    border-radius: 12px;
                    font-size: 14px;
                    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
                    resize: vertical;
                    margin-bottom: 16px;
                }}
                .btn {{
                    display: inline-block;
                    padding: 14px 24px;
                    border-radius: 999px;
                    text-decoration: none;
                    font-weight: 700;
                    border: none;
                    cursor: pointer;
                    font-size: 15px;
                }}
                .btn-danger {{
                    background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
                    color: white;
                }}
                .btn-primary {{
                    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
                    color: white;
                }}
                .btn-warning {{
                    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                    color: white;
                }}
                .btn-secondary {{
                    background: #e5e7eb;
                    color: #111827;
                }}
                .btn-disabled {{
                    opacity: 0.5;
                    cursor: not-allowed;
                }}
                @media (max-width: 520px) {{
                    .stats {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Administration</h1>
                <p>Protected page used to delete all saved photos and sessions.</p>
                <div class="warning">Destructive action. All images and all session folders will be permanently deleted.</div>
                {f'<div class="status error">{error_message}</div>' if error_message else ''}
                {f'<div class="status success">{success_message}</div>' if success_message else ''}
                <div class="stats">
                    <div class="stat">
                        <div class="stat-label">Sessions</div>
                        <div class="stat-value">{sessions_count}</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Files</div>
                        <div class="stat-value">{files_count}</div>
                    </div>
                </div>
                {'<div class="status error">ADMIN_PASSWORD is not set in config.ini. Admin actions are disabled.</div>' if not admin_enabled else ''}
                <form method="post" action="/admin/delete-all">
                    <div class="actions">
                        <button type="submit" class="btn btn-danger{' btn-disabled' if not admin_enabled else ''}" {'disabled' if not admin_enabled else ''}>Delete all photos</button>
                        <a href="/stats" class="btn btn-secondary">Back to stats</a>
                        <a href="/admin/logout" class="btn btn-secondary">Log out</a>
                    </div>
                </form>
                <div class="section">
                    <h2>Configuration</h2>
                    <p>View and edit <code>config.ini</code>. ADMIN_PASSWORD is hidden in browser.</p>
                    <form method="post" action="/admin/config">
                        <label for="config_content">config.ini</label>
                        <textarea id="config_content" name="config_content" spellcheck="false" {'disabled' if not admin_enabled else ''}>{config_content}</textarea>
                        <div class="actions">
                            <button type="submit" class="btn btn-primary{' btn-disabled' if not admin_enabled else ''}" {'disabled' if not admin_enabled else ''}>Save config.ini</button>
                        </div>
                    </form>
                </div>
                <div class="section">
                    <h2>Application</h2>
                    <p>Restart PhotoBooth application to apply configuration changes.</p>
                    <form method="post" action="/admin/restart">
                        <div class="actions">
                            <button type="submit" class="btn btn-warning{' btn-disabled' if not admin_enabled else ''}" {'disabled' if not admin_enabled else ''}>Restart app</button>
                        </div>
                    </form>
                </div>
            </div>
        </body>
        </html>
        """

        return render_template_string(html)
    
    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route('/editor')
        def template_editor():
            """Expose the browser-based template editor."""
            if not os.path.exists(self.template_editor_path):
                return 'Template editor not found', 404

            return send_file(self.template_editor_path, mimetype='text/html')

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
                # No collages available
                html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>PhotoBooth</title>
                    <style>
                        * { margin: 0; padding: 0; box-sizing: border-box; }
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            min-height: 100vh;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        }
                        .container {
                            background: white;
                            border-radius: 20px;
                            padding: 60px;
                            text-align: center;
                            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        }
                        .icon { font-size: 100px; margin-bottom: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">📸</div>
                    </div>
                </body>
                </html>
                """
                return render_template_string(html)
            
            # Redirect to latest collage
            latest = collages[0]
            return redirect(f'/collage/{latest["session"]}')
        
        @self.app.route('/gallery')
        def gallery():
            """Gallery view with all collages."""
            self._track_event('gallery_view')
            collages = self._get_all_collages()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>PhotoBooth</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                        background: #1a1a1a;
                        min-height: 100vh;
                        padding: 20px;
                    }
                    .gallery {
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                        gap: 20px;
                        max-width: 1400px;
                        margin: 0 auto;
                    }
                    .card {
                        background: white;
                        border-radius: 15px;
                        overflow: hidden;
                        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                        transition: transform 0.3s;
                        cursor: pointer;
                    }
                    .card:hover { transform: translateY(-5px); }
                    .card img {
                        width: 100%;
                        height: 300px;
                        object-fit: cover;
                        display: block;
                    }
                    .card-footer {
                        padding: 15px;
                        text-align: center;
                    }
                    .btn {
                        display: inline-block;
                        padding: 12px 30px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        text-decoration: none;
                        border-radius: 8px;
                        font-weight: bold;
                        transition: opacity 0.3s;
                    }
                    .btn:hover { opacity: 0.9; }
                    @media (max-width: 600px) {
                        .gallery { grid-template-columns: 1fr; }
                    }
                </style>
            </head>
            <body>
                <div class="gallery">
            """
            
            for collage in collages:
                html += f"""
                    <div class="card" onclick="window.location='/collage/{collage["session"]}'">
                        <img src="/image/{collage["session"]}/collage.jpg" alt="📸">
                        <div class="card-footer">
                            <a href="/download/{collage["session"]}/collage.jpg" class="btn">⬇️</a>
                        </div>
                    </div>
                """
            
            html += """
                </div>
            </body>
            </html>
            """
            
            return render_template_string(html)
        
        @self.app.route('/collage/<session>')
        def view_collage(session):
            """View a single collage fullscreen."""
            collage_path = self._get_safe_photo_path(session, 'collage.jpg')
            
            if collage_path is None:
                return redirect('/')
            
            self._track_event('collage_view', session)
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>PhotoBooth</title>
                <style>
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{
                        background: #000;
                        min-height: 100vh;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        padding: 20px;
                    }}
                    img {{
                        max-width: 100%;
                        max-height: 80vh;
                        object-fit: contain;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.5);
                        border-radius: 10px;
                    }}
                    .controls {{
                        margin-top: 30px;
                        display: flex;
                        gap: 20px;
                    }}
                    .btn {{
                        padding: 15px 40px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        text-decoration: none;
                        border-radius: 30px;
                        font-weight: bold;
                        font-size: 18px;
                        transition: transform 0.2s;
                        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
                    }}
                    .btn:hover {{
                        transform: scale(1.05);
                    }}
                    .btn-secondary {{
                        background: rgba(255,255,255,0.1);
                        box-shadow: none;
                    }}
                </style>
            </head>
            <body>
                <img src="/image/{session}/collage.jpg" alt="📸">
                <div class="controls">
                    <a href="/gallery" class="btn btn-secondary">🖼️</a>
                    <a href="/download/{session}/collage.jpg" class="btn">⬇️</a>
                </div>
            </body>
            </html>
            """
            
            return render_template_string(html)
        
        @self.app.route('/image/<session>/<filename>')
        def serve_image(session, filename):
            """Serve an image file."""
            image_path = self._get_safe_photo_path(session, filename)
            
            if image_path is None:
                return "Not found", 404
            
            self._track_event('image_view', session)
            return send_file(image_path, mimetype='image/jpeg')
        
        @self.app.route('/download/<session>/<filename>')
        def download_image(session, filename):
            """Download an image file."""
            image_path = self._get_safe_photo_path(session, filename)
            
            if image_path is None:
                return "Not found", 404
            
            self._track_event('download', session)
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
            self._track_event('download')

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

            return self._render_admin_page()

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

            try:
                deleted_sessions = self._delete_all_sessions()
            except Exception:
                return self._render_admin_page(error_message='Error while deleting files.'), 500

            return self._render_admin_page(success_message=f'{deleted_sessions} session(s) deleted.')

        @self.app.route('/admin/config', methods=['POST'])
        def save_admin_config():
            """Save config.ini after password validation."""
            auth_redirect = self._require_admin_auth()
            if auth_redirect is not None:
                return auth_redirect

            if self.admin_password is None:
                session.clear()
                return self._render_admin_login_page(error_message='Admin access is disabled. Configure ADMIN_PASSWORD in config.ini.'), 403

            config_content = request.form.get('config_content') or ''
            config_content = self._merge_masked_admin_password(config_content)

            try:
                self._save_config_text(config_content)
            except Exception:
                return self._render_admin_page(error_message='Error while saving config.ini.', config_content=self._mask_admin_password_in_config(config_content)), 500

            try:
                updated_config = self._load_config_text()
                self._refresh_admin_password_from_config(updated_config)
            except Exception:
                return self._render_admin_page(success_message='config.ini saved. Restart app to apply all changes.', config_content=self._mask_admin_password_in_config(config_content))

            if self.admin_password is None:
                session.clear()
                return self._render_admin_login_page(success_message='config.ini saved. Admin password disabled. Sign in is now disabled.')

            return self._render_admin_page(success_message='config.ini saved. Restart app to apply all changes.', config_content=self._mask_admin_password_in_config(updated_config))

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
                self.restart_callback()
            except Exception as e:
                Logger.error(f'WebServer: Error restarting app: {e}')
                return self._render_admin_page(error_message='Error while restarting app.'), 500

            return self._render_admin_page(success_message='Application restart requested. Page may become unavailable for a few seconds.')
        
        @self.app.route('/stats')
        def statistics():
            """Hidden statistics page - shows usage analytics."""
            stats = self._load_stats()
            collages = self._get_all_collages()
            downloadable_photos = self._get_all_downloadable_photos()
            
            # Calculate photos taken from number of sessions
            stats['photos_taken'] = len(collages)
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>PhotoBooth - Statistics</title>
                <style>
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        padding: 40px 20px;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                    }}
                    h1 {{
                        color: white;
                        text-align: center;
                        margin-bottom: 40px;
                        font-size: 42px;
                        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
                    }}
                    .stats-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                        gap: 20px;
                        margin-bottom: 40px;
                    }}
                    .stat-card {{
                        background: white;
                        border-radius: 15px;
                        padding: 30px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                        transition: transform 0.3s;
                    }}
                    .stat-card:hover {{
                        transform: translateY(-5px);
                    }}
                    .stat-icon {{
                        font-size: 48px;
                        margin-bottom: 15px;
                    }}
                    .stat-value {{
                        font-size: 42px;
                        font-weight: bold;
                        color: #667eea;
                        margin-bottom: 5px;
                    }}
                    .stat-label {{
                        font-size: 16px;
                        color: #666;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    }}
                    .stat-description {{
                        font-size: 12px;
                        color: #999;
                        margin-top: 8px;
                        line-height: 1.4;
                    }}
                    .info-card {{
                        background: white;
                        border-radius: 15px;
                        padding: 30px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    }}
                    .info-row {{
                        display: flex;
                        justify-content: space-between;
                        padding: 15px 0;
                        border-bottom: 1px solid #eee;
                    }}
                    .info-row:last-child {{
                        border-bottom: none;
                    }}
                    .info-label {{
                        font-weight: bold;
                        color: #333;
                    }}
                    .info-value {{
                        color: #667eea;
                    }}
                     .back-btn {{
                         display: inline-block;
                         margin-top: 30px;
                        padding: 15px 40px;
                        background: white;
                        color: #667eea;
                        text-decoration: none;
                        border-radius: 30px;
                        font-weight: bold;
                        box-shadow: 0 5px 20px rgba(0,0,0,0.2);
                        transition: transform 0.2s;
                    }}
                     .back-btn:hover {{
                         transform: scale(1.05);
                     }}
                     .actions {{
                         display: flex;
                         justify-content: center;
                         gap: 20px;
                         flex-wrap: wrap;
                         margin-top: 30px;
                     }}
                     .download-btn {{
                         background: linear-gradient(135deg, #34c759 0%, #28a745 100%);
                         color: white;
                     }}
                     .download-btn.disabled {{
                         background: #d1d1d6;
                         color: #666;
                         cursor: not-allowed;
                         pointer-events: none;
                     }}
                     @media (max-width: 768px) {{
                         .stats-grid {{
                             grid-template-columns: 1fr;
                        }}
                        h1 {{
                            font-size: 32px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>PhotoBooth Statistics</h1>
                    
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-icon">📸</div>
                            <div class="stat-value">{stats['photos_taken']}</div>
                            <div class="stat-label">Photos Taken</div>
                            <div class="stat-description">Total collages created</div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-icon">⬇️</div>
                            <div class="stat-value">{stats['downloads']}</div>
                            <div class="stat-label">Downloads</div>
                            <div class="stat-description">Files downloaded by users</div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-icon">🖼️</div>
                            <div class="stat-value">{stats['gallery_views']}</div>
                            <div class="stat-label">Gallery Views</div>
                            <div class="stat-description">Grid view page visits</div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-icon">👁️</div>
                            <div class="stat-value">{stats['collage_views']}</div>
                            <div class="stat-label">Collage Views</div>
                            <div class="stat-description">Full-screen collage page visits</div>
                        </div>
                    </div>
                    
                    <div class="info-card">
                        <h2 style="margin-bottom: 20px; color: #667eea;">Additional Information</h2>
                        <div class="info-row">
                            <span class="info-label">Last Download:</span>
                            <span class="info-value">{stats['last_download_date'] or 'None'}</span>
                        </div>
                         <div class="info-row">
                             <span class="info-label">Total Sessions:</span>
                             <span class="info-value">{len(collages)}</span>
                         </div>
                         <div class="info-row">
                             <span class="info-label">Total Files:</span>
                             <span class="info-value">{len(downloadable_photos)}</span>
                         </div>
                         <div class="info-row">
                             <span class="info-label">Stats File:</span>
                             <span class="info-value" style="font-size: 12px; word-break: break-all;">{self.stats_file}</span>
                         </div>
                     </div>
                     
                     <div class="actions">
                          <a href="/download/all-photos" class="back-btn download-btn{' disabled' if not downloadable_photos else ''}">Download all photos</a>
                          <a href="/admin" class="back-btn" style="background: #111827; color: white;">Administration</a>
                          <a href="/gallery" class="back-btn">← Back to gallery</a>
                      </div>
                  </div>
             </body>
             </html>
            """
            
            return render_template_string(html)
        
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
    
    def track_photo_taken(self, session_id=None):
        """Public method to track when a photo is taken.
        
        Args:
            session_id: Optional session identifier for the photo
        """
        try:
            stats = self._load_stats()
            stats['photos_taken'] += 1
            stats['last_photo_date'] = datetime.now().isoformat()
            
            if stats['first_photo_date'] is None:
                stats['first_photo_date'] = datetime.now().isoformat()
            
            if session_id and session_id not in stats['sessions']:
                stats['sessions'].append(session_id)
            
            self._save_stats(stats)
            Logger.info(f'WebServer: Photo tracked - Total: {stats["photos_taken"]}')
        except Exception as e:
            Logger.error(f'WebServer: Error tracking photo: {e}')
    
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

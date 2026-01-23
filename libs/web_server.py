import os
import json
import threading
from datetime import datetime
from flask import Flask, send_file, render_template_string, redirect
from kivy.logger import Logger

class WebServer:
    """Flask web server for photo gallery with captive portal."""
    
    def __init__(self, save_directory, host='0.0.0.0', port=5000):
        self.save_directory = save_directory
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.server_thread = None
        self.stats_file = os.path.join(save_directory, '.stats.json')
        self.stats_lock = threading.Lock()
        self._setup_routes()
    
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
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
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
            collage_path = os.path.join(self.save_directory, session, 'collage.jpg')
            
            if not os.path.exists(collage_path):
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
            image_path = os.path.join(self.save_directory, session, filename)
            
            if not os.path.exists(image_path):
                return "Not found", 404
            
            self._track_event('image_view', session)
            return send_file(image_path, mimetype='image/jpeg')
        
        @self.app.route('/download/<session>/<filename>')
        def download_image(session, filename):
            """Download an image file."""
            image_path = os.path.join(self.save_directory, session, filename)
            
            if not os.path.exists(image_path):
                return "Not found", 404
            
            self._track_event('download', session)
            return send_file(
                image_path,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name=f'photobooth_{session}.jpg'
            )
        
        @self.app.route('/stats')
        def statistics():
            """Hidden statistics page - shows usage analytics."""
            stats = self._load_stats()
            collages = self._get_all_collages()
            
            # Calculate photos taken from number of sessions
            stats['photos_taken'] = len(collages)
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>PhotoBooth - Statistiques</title>
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
                    <h1>📊 PhotoBooth Statistics</h1>
                    
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
                            <span class="info-label">Stats File:</span>
                            <span class="info-value" style="font-size: 12px; word-break: break-all;">{self.stats_file}</span>
                        </div>
                    </div>
                    
                    <center>
                        <a href="/gallery" class="back-btn">← Back to gallery</a>
                    </center>
                </div>
            </body>
            </html>
            """
            
            return render_template_string(html)
        
        # Captive portal detection URLs
        @self.app.route('/generate_204')
        @self.app.route('/gen_204')
        def android_captive():
            return redirect('/')
        
        @self.app.route('/hotspot-detect.html')
        @self.app.route('/library/test/success.html')
        def apple_captive():
            return redirect('/')
        
        @self.app.route('/connecttest.txt')
        @self.app.route('/redirect')
        def windows_captive():
            return redirect('/')
    
    def start(self):
        """Start the web server in a separate thread."""
        if self.server_thread and self.server_thread.is_alive():
            Logger.warning('WebServer: Server already running')
            return
        
        def run_server():
            Logger.info(f'WebServer: Starting on {self.host}:{self.port}')
            self.app.run(host=self.host, port=self.port, debug=False, threaded=True)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        Logger.info('WebServer: Server started successfully')
    
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
        Logger.info('WebServer: Stop requested (requires app restart)')

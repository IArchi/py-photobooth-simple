import os
import threading
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
        self._setup_routes()
    
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
            
            return send_file(image_path, mimetype='image/jpeg')
        
        @self.app.route('/download/<session>/<filename>')
        def download_image(session, filename):
            """Download an image file."""
            image_path = os.path.join(self.save_directory, session, filename)
            
            if not os.path.exists(image_path):
                return "Not found", 404
            
            return send_file(
                image_path,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name=f'photobooth_{session}.jpg'
            )
        
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
    
    def stop(self):
        """Stop the web server."""
        Logger.info('WebServer: Stop requested (requires app restart)')

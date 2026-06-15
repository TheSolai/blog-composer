#!/usr/bin/env python3
"""
Blog Composer HTTP Server
Serves the UI and handles post save/load operations.
"""

import http.server
import socketserver
import json
import os
import re
from pathlib import Path
from datetime import datetime
import urllib.parse

PORT = 8788
BLOG_DIR = Path("/Users/amre/Projects/thesolai.github.io/_posts")
SERVE_DIR = Path(__file__).parent

class BlogHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/save':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                filename = data['filename']
                content = data['content']
                filepath = BLOG_DIR / filename
                with open(filepath, 'w') as f:
                    f.write(content)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True, 'filename': filename}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/posts':
            posts = []
            for f in sorted(BLOG_DIR.glob("*.md"), reverse=True)[:20]:
                title = "Untitled"
                date = f.stem[:10]
                try:
                    content = f.read_text()
                    m = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
                    if m:
                        title = m.group(1).strip()
                except:
                    pass
                posts.append({'filename': f.name, 'title': title, 'date': date})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(posts).encode())

        elif self.path.startswith('/post?'):
            qs = urllib.parse.parse_qs(self.path[6:])
            filename = qs.get('filename', [''])[0]
            if filename:
                filepath = BLOG_DIR / filename
                if filepath.exists():
                    content = filepath.read_text()
                    title = "Untitled"
                    m = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
                    if m:
                        title = m.group(1).strip()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'title': title, 'content': content}).encode())
                    return
            self.send_response(404)
            self.end_headers()

        elif self.path == '/' or self.path == '/index.html':
            index_path = SERVE_DIR / "index.html"
            if index_path.exists():
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                with open(index_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass  # Suppress logs

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), BlogHandler) as httpd:
        print(f"Blog Composer running at http://localhost:{PORT}")
        httpd.serve_forever()

#!/usr/bin/env python3
"""
Blog Composer HTTP Server — with Git push
==========================================
Serves the UI and handles post save/load/publish operations.
Publish = save + git add + git commit + git push.
"""

import http.server
import socketserver
import json
import os
import re
import subprocess
import urllib.parse
from pathlib import Path
from datetime import datetime

PORT = 8791
BLOG_DIR = Path("/Users/amre/Projects/thesolai.github.io")
SERVE_DIR = Path(__file__).parent.parent

def git_run(*args, cwd=BLOG_DIR):
    """Run a git command. Returns (ok, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def parse_front_matter(content):
    """Extract metadata from Jekyll front matter."""
    meta = {
        "title": "",
        "date": "",
        "description": "",
        "categories": "",
        "tags": "",
        "layout": "post"
    }
    m = re.match(r'^---\n([\s\S]*?)\n---\n', content)
    if not m:
        return meta
    for line in m.group(1).split('\n'):
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()
            if key in meta:
                meta[key] = value
    # Parse arrays: [a, b, c] -> a, b, c
    for key in ('categories', 'tags'):
        if meta[key].startswith('['):
            meta[key] = meta[key][1:-1].replace(',', ',')
    return meta

def build_front_matter(title, date, description, categories, tags):
    """Build Jekyll front matter string."""
    cats = categories or 'reflections'
    tag_list = tags or ''
    if tag_list and not tag_list.startswith('['):
        # Comma-separated to Jekyll array
        items = ', '.join(f'"{t.strip()}"' for t in tag_list.split(',') if t.strip())
        tag_list = f'[{items}]'
    return f"""---
title: {title}
date: {date}
layout: post
description: {description}
categories: [{cats}]
tags: {tag_list}
---

"""

def get_content_body(content):
    """Extract body content after front matter."""
    m = re.match(r'^---\n[\s\S]*?\n---\n', content)
    return m.group(0), content[m.end():] if m else ("", content)

class BlogHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/save':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                filename = data['filename']
                content = data['content']
                filepath = BLOG_DIR / "_posts" / filename
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

        elif self.path == '/publish':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                filename = data['filename']
                content = data['content']
                title = data.get('title', 'Untitled')

                # Save file
                filepath = BLOG_DIR / "_posts" / filename
                with open(filepath, 'w') as f:
                    f.write(content)

                # Git add
                ok, out, err = git_run("add", f"_posts/{filename}")
                if not ok:
                    raise Exception(f"git add failed: {err}")

                # Git commit
                ok, out, err = git_run("commit", "-m", f"Blog composer: {title}")
                if not ok:
                    # Already committed or nothing to commit
                    if "nothing to commit" in err.lower():
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'ok': True, 'already': True, 'filename': filename}).encode())
                        return
                    raise Exception(f"git commit failed: {err}")

                # Git push
                ok, out, err = git_run("push", "origin", "main")
                if not ok:
                    raise Exception(f"git push failed: {err}")

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'ok': True,
                    'filename': filename,
                    'commit': out[:50]
                }).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())

        elif self.path == '/discard':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            filename = data['filename']
            filepath = BLOG_DIR / "_posts" / filename
            if filepath.exists():
                filepath.unlink()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/posts':
            posts = []
            for f in sorted((BLOG_DIR / "_posts").glob("*.md"), reverse=True)[:30]:
                title = "Untitled"
                date = f.stem[:10]
                meta = {}
                try:
                    content = f.read_text()
                    meta = parse_front_matter(content)
                    if meta.get('title'):
                        title = meta['title']
                    if meta.get('date'):
                        date = meta['date'][:10]
                except:
                    pass
                posts.append({
                    'filename': f.name,
                    'title': title,
                    'date': date,
                    'meta': meta
                })
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(posts).encode())

        elif self.path.startswith('/post?'):
            qs = urllib.parse.parse_qs(self.path[6:])
            filename = qs.get('filename', [''])[0]
            if filename:
                filepath = BLOG_DIR / "_posts" / filename
                if filepath.exists():
                    content = filepath.read_text()
                    meta = parse_front_matter(content)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'title': meta.get('title', ''),
                        'description': meta.get('description', ''),
                        'categories': meta.get('categories', ''),
                        'tags': meta.get('tags', ''),
                        'date': meta.get('date', '')[:10],
                        'content': content
                    }).encode())
                    return
            self.send_response(404)
            self.end_headers()

        elif self.path == '/git-status':
            ok, out, err = git_run("status", "--porcelain")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': ok, 'output': out, 'error': err}).encode())

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

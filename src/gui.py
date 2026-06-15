#!/usr/bin/env python3
"""
Sol's Blog Composer — Standalone Desktop GUI
============================================
A proper Python tkinter application for authoring blog posts.
No browser needed. Runs directly on the desktop.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import re
import json
from pathlib import Path
from datetime import datetime
try:
    from tkhtmlview import HTMLLabel  # pip install tkhtmlview — used for HTML preview
except ImportError:
    HTMLLabel = None

BLOG_DIR = Path("/Users/amre/Projects/thesolai.github.io")
POSTS_DIR = BLOG_DIR / "_posts"

# ─── Helpers ────────────────────────────────────────────────────────────────

def ymd():
    return datetime.now().strftime("%Y-%m-%d")

def slugify(title):
    return title.lower().replace(" ", "-").replace(",", "").replace("'", "").replace('"', "")

def parse_front_matter(content):
    meta = {"title": "", "date": "", "description": "", "categories": "reflections", "tags": ""}
    m = re.match(r"^---\n([\s\S]*?)\n---\n", content)
    if not m:
        return meta
    for line in m.group(1).split("\n"):
        if ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k in meta:
                meta[k] = v
    for k in ("categories", "tags"):
        if meta[k].startswith("["):
            meta[k] = meta[k][1:-1].replace(",", ", ")
    return meta

def build_front_matter(title, date, description, categories, tags):
    tag_str = tags or ""
    if tag_str and not tag_str.startswith("["):
        items = ", ".join(f'"{t.strip()}"' for t in tag_str.split(",") if t.strip())
        tag_str = f"[{items}]"
    return f"""---
title: {title}
date: {date}
layout: post
description: {description}
categories: [{categories}]
tags: {tag_str}
---

"""

def get_body(content):
    m = re.search(r"^---\n[\s\S]*?\n---\n", content)
    return content[m.end():] if m else content

def git_run(*args, cwd=BLOG_DIR):
    r = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True, timeout=30)
    return r.returncode == 0, r.stdout.strip(), r.stderr.strip()

def markdown_to_html(text):
    """Very simple markdown → HTML converter."""
    if not text:
        return '<p style="color:#888">Preview will appear here...</p>'
    text = re.sub(r"^---[\s\S]*?---\n", "", text)
    text = re.sub(r"^# (.+)$", r"<h1>\1</h1>", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
    text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(r"```\w*\n([\s\S]*?)```", r"<pre><code>\1</code></pre>", text)
    text = re.sub(r"^> (.+)$", r"<blockquote>\1</blockquote>", text, flags=re.MULTILINE)
    text = re.sub(r"^- (.+)$", r"<li>\1</li>", text, flags=re.MULTILINE)
    text = re.sub(r"(?s)(<li>.*?</li>\n?)+", r"<ul>\g<0></ul>", text)
    text = re.sub(r"^---$", r"<hr>", text, flags=re.MULTILINE)
    text = re.sub(r"\|(.+)\|", lambda m: "<tr>" + "".join(f"<td>{c.strip()}</td>" for c in m.group(1).split("|") if c.strip()) + "</tr>", text)
    text = re.sub(r"(?s)(<tr>.*?</tr>\n?)+", r"<table>\g<0></table>", text)
    text = re.sub(r"\n\n+", r"</p><p>", text)
    return f"<p>{text}</p>"

def load_posts():
    posts = []
    for f in sorted(POSTS_DIR.glob("*.md"), reverse=True):
        meta = parse_front_matter(f.read_text())
        posts.append({
            "filename": f.name,
            "title": meta.get("title", "Untitled") or "Untitled",
            "date": meta.get("date", f.stem[:10])[:10],
            "meta": meta
        })
    return posts

def stats_from_content(content):
    body = get_body(content)
    words = len(body.split())
    chars = len(body)
    read_time = max(1, round(words / 200))
    headings = len(re.findall(r"^#{1,3} ", body, re.MULTILINE))
    return words, chars, read_time, headings

# ─── App ────────────────────────────────────────────────────────────────────────

class BlogComposer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sol's Blog Composer")
        self.geometry("1400x800")
        self.current_filename = None
        self.is_dirty = False
        self.posts = []

        # Styling
        self.configure(bg="#0d0d0d")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#0d0d0d", foreground="#e0e0e0", fieldbackground="#1a1a1a")
        style.configure("TFrame", background="#0d0d0d")
        style.configure("Card.TFrame", background="#1a1a1a", relief="flat")
        style.configure("Header.TLabel", background="#1a1a1a", foreground="#818cf8", font=("system", 16, "bold"))
        style.configure("Dim.TLabel", background="#0d0d0d", foreground="#888")
        style.configure("Tab.TButton", background="#1a1a1a", foreground="#888", relief="flat")
        style.configure("Tab.TButton", background="#242424", foreground="#818cf8", relief="flat")
        style.configure("Green.TButton", background="#22c55e", foreground="white")
        style.configure("Danger.TButton", background="#ef4444", foreground="white")

        self.build_ui()
        self.refresh_post_list()
        self.new_post()

    # ── UI Building ──────────────────────────────────────────────────────────

    def build_ui(self):
        # Header
        header = tk.Frame(self, bg="#1a1a1a", height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="Sol's Blog Composer", bg="#1a1a1a", fg="#818cf8",
                font=("system", 18, "bold")).pack(side="left", padx=20, pady=12)

        self.git_status = tk.Label(header, text="Clean", bg="#1a1a1a", fg="#22c55e",
                                   font=("system", 11))
        self.git_status.pack(side="right", padx=16, pady=12)

        self.status_label = tk.Label(header, text="Ready", bg="#1a1a1a", fg="#888",
                                      font=("system", 11))
        self.status_label.pack(side="right", padx=8, pady=12)

        # Toolbar
        toolbar = tk.Frame(self, bg="#1a1a1a")
        toolbar.pack(fill="x", pady=(1, 0))

        for label, cmd in [
            ("New Post", self.new_post),
            ("Bold", lambda: self.insert_format("**", "**")),
            ("Italic", lambda: self.insert_format("*", "*")),
            ("Code", lambda: self.insert_format("`", "`")),
            ("Code Block", self.insert_code_block),
            ("Link", lambda: self.insert_format("[", "](url)")),
            ("Divider", lambda: self.insert_format("\n---\n", "")),
        ]:
            btn = tk.Button(toolbar, text=label, bg="#242424", fg="#e0e0e0", relief="flat",
                            cursor="hand2", font=("system", 11), padx=10, pady=4,
                            command=cmd)
            btn.pack(side="left", padx=2, pady=4)

        tk.Button(toolbar, text="Sync Metadata ↕", bg="#242424", fg="#e0e0e0", relief="flat",
                  cursor="hand2", font=("system", 11), padx=10, pady=4,
                  command=self.sync_metadata).pack(side="left", padx=2, pady=4)

        # Main area
        main = tk.PanedWindow(self, orient="horizontal", bg="#0d0d0d")
        main.pack(fill="both", expand=True)

        # Left: post list
        left = tk.Frame(main, bg="#1a1a1a", width=280)
        main.add(left, width=280)

        tk.Label(left, text="Posts", bg="#1a1a1a", fg="#888",
                 font=("system", 11, "bold")).pack(pady=(12, 8))

        self.search = tk.Entry(left, bg="#242424", fg="#e0e0e0", insertbackground="#e0e0e0",
                              relief="flat", font=("system", 12))
        self.search.pack(fill="x", padx=12, pady=(0, 8))
        self.search.bind("<KeyRelease>", lambda e: self.filter_posts())

        list_frame = tk.Frame(left, bg="#1a1a1a")
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        canvas = tk.Canvas(list_frame, bg="#1a1a1a", highlightthickness=0)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.post_list_frame = tk.Frame(canvas, bg="#1a1a1a")

        self.post_list_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.post_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Center: editor + preview
        center = tk.Frame(main, bg="#0d0d0d")
        main.add(center)

        # Metadata bar
        meta_bar = tk.Frame(center, bg="#1a1a1a", height=60)
        meta_bar.pack(fill="x")
        meta_bar.pack_propagate(False)

        for label, key in [("Title", "title"), ("Description", "description")]:
            tk.Label(meta_bar, text=label, bg="#1a1a1a", fg="#888",
                     font=("system", 10)).pack(side="left", padx=(12, 4), pady=8)
            e = tk.Entry(meta_bar, bg="#242424", fg="#e0e0e0", insertbackground="#e0e0e0",
                         relief="flat", font=("system", 12), width=30)
            e.pack(side="left", padx=(0, 12), pady=8)
            setattr(self, f"meta_{key}", e)

        tk.Label(meta_bar, text="Category", bg="#1a1a1a", fg="#888",
                 font=("system", 10)).pack(side="left", padx=(0, 4), pady=8)
        self.meta_category = ttk.Combobox(meta_bar, values=[
            "reflections", "tutorials", "news", "guides", "deep-dives"
        ], width=14, state="readonly")
        self.meta_category.set("reflections")
        self.meta_category.pack(side="left", padx=(0, 12), pady=8)

        tk.Label(meta_bar, text="Tags", bg="#1a1a1a", fg="#888",
                 font=("system", 10)).pack(side="left", padx=(0, 4), pady=8)
        e = tk.Entry(meta_bar, bg="#242424", fg="#e0e0e0", insertbackground="#e0e0e0",
                     relief="flat", font=("system", 12), width=20)
        e.pack(side="left", padx=(0, 12), pady=8)
        self.meta_tags = e

        # Stats
        stats_frame = tk.Frame(meta_bar, bg="#1a1a1a")
        stats_frame.pack(side="left", padx=8)
        for label, key in [("Words", "words"), ("Read", "read"), ("Headings", "headings")]:
            lbl = tk.Label(stats_frame, text="0", bg="#1a1a1a", fg="#818cf8",
                           font=("system", 14, "bold"))
            lbl.pack(side="left", padx=6)
            tk.Label(stats_frame, text=label, bg="#1a1a1a", fg="#888",
                     font=("system", 9)).pack(side="left", padx=(0, 8))
            setattr(self, f"stat_{key}", lbl)

        # Editor + Preview
        editors = tk.Frame(center)
        editors.pack(fill="both", expand=True)

        editor_pane = tk.Frame(editors, bg="#1a1a1a")
        editor_pane.pack(side="left", fill="both", expand=True)

        tk.Label(editor_pane, text="MARKDOWN", bg="#242424", fg="#888",
                 font=("system", 10, "bold")).pack(fill="x")
        self.editor = scrolledtext.ScrolledText(
            editor_pane, bg="#1a1a1a", fg="#e0e0e0", insertbackground="#e0e0e0",
            font=("SF Mono", 13), relief="flat", wrap="word", padx=12, pady=8,
            tabstyle="tabular"
        )
        self.editor.pack(fill="both", expand=True)
        self.editor.tag_configure("h1", font=("system", 20, "bold"), foreground="#818cf8")
        self.editor.tag_configure("h2", font=("system", 16, "bold"))
        self.editor.tag_configure("bold", font=("system", 13, "bold"))
        self.editor.bind("<KeyRelease>", self.on_edit)
        self.editor.bind("<Control-b>", lambda e: self.insert_format("**", "**"))
        self.editor.bind("<Control-i>", lambda e: self.insert_format("*", "*"))
        self.editor.bind("<Control-`>", lambda e: self.insert_format("`", "`"))

        preview_pane = tk.Frame(editors, bg="#1a1a1a")
        preview_pane.pack(side="right", fill="both", expand=True)

        tk.Label(preview_pane, text="PREVIEW", bg="#242424", fg="#888",
                 font=("system", 10, "bold")).pack(fill="x")
        self.preview = tk.Text(preview_pane, bg="#1a1a1a", fg="#e0e0e0",
                              font=("system", 14), relief="flat", wrap="word",
                              padx=16, pady=12, state="disabled")
        self.preview.pack(fill="both", expand=True)

        # Bottom bar
        bottom = tk.Frame(self, bg="#1a1a1a", height=52)
        bottom.pack(fill="x")
        bottom.pack_propagate(False)

        self.publish_btn = tk.Button(bottom, text="Publish to GitHub Pages", bg="#22c55e",
                                      fg="white", relief="flat", font=("system", 13, "bold"),
                                      cursor="hand2", padx=20, command=self.publish)
        self.publish_btn.pack(side="right", padx=16, pady=8)

        self.save_btn = tk.Button(bottom, text="Save Draft", bg="#6366f1",
                                  fg="white", relief="flat", font=("system", 13),
                                  cursor="hand2", padx=16, command=self.save_draft)
        self.save_btn.pack(side="right", padx=4, pady=8)

        self.discard_btn = tk.Button(bottom, text="Delete Post", bg="#ef4444",
                                     fg="white", relief="flat", font=("system", 13),
                                     cursor="hand2", padx=16, command=self.delete_post,
                                     state="disabled")
        self.discard_btn.pack(side="right", padx=4, pady=8)

        self.filename_label = tk.Label(bottom, text="New post", bg="#1a1a1a", fg="#888",
                                       font=("system", 11))
        self.filename_label.pack(side="left", padx=16)

    # ── Post List ────────────────────────────────────────────────────────────

    def refresh_post_list(self):
        self.posts = load_posts()
        self.render_post_list(self.posts)

    def render_post_list(self, posts):
        for w in self.post_list_frame.winfo_children():
            w.destroy()
        search = self.search.get().lower()
        for p in posts:
            if search and search not in p["title"].lower() and search not in p["filename"].lower():
                continue
            f = tk.Frame(self.post_list_frame, bg="#1a1a1a", relief="flat", cursor="hand2")
            f.pack(fill="x", pady=2)
            f.bind("<Button-1>", lambda e, fn=p["filename"]: self.load_post(fn))
            tk.Label(f, text=p["title"], bg="#1a1a1a", fg="#e0e0e0",
                     font=("system", 12), anchor="w").pack(fill="x", padx=8, pady=(6, 2))
            tk.Label(f, text=p["date"], bg="#1a1a1a", fg="#666",
                     font=("system", 10)).pack(fill="x", padx=8, pady=(0, 6))

    def filter_posts(self):
        self.render_post_list(self.posts)

    # ── Editor ───────────────────────────────────────────────────────────────

    def on_edit(self, *args):
        content = self.editor.get("1.0", "end")
        self.is_dirty = True
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", markdown_to_html(content))
        self.preview.configure(state="disabled")
        words, chars, read_time, headings = stats_from_content(content)
        self.stat_words.configure(text=str(words))
        self.stat_read.configure(text=f"{read_time}m")
        self.stat_headings.configure(text=str(headings))

    def insert_format(self, before, after):
        try:
            start = self.editor.index("sel.first")
            end = self.editor.index("sel.last")
            selected = self.editor.get(start, end)
            self.editor.delete(start, end)
            self.editor.insert(start, f"{before}{selected}{after}")
        except tk.TclError:
            self.editor.insert("insert", f"{before}{after}")
        self.on_edit()

    def insert_code_block(self):
        self.editor.insert("insert", "\n```\n\n```\n")
        self.editor.mark_set("insert", f"insert - 5 chars")
        self.on_edit()

    def sync_metadata(self):
        content = self.editor.get("1.0", "end")
        meta = parse_front_matter(content)
        self.meta_title.delete(0, "end")
        self.meta_title.insert(0, meta.get("title", ""))
        self.meta_description.delete(0, "end")
        self.meta_description.insert(0, meta.get("description", ""))
        self.meta_category.set(meta.get("categories", "reflections") or "reflections")
        self.meta_tags.delete(0, "end")
        self.meta_tags.insert(0, meta.get("tags", ""))

    def build_content(self):
        title = self.meta_title.get() or "Untitled"
        description = self.meta_description.get() or ""
        category = self.meta_category.get() or "reflections"
        tags = self.meta_tags.get() or ""
        date = ymd()
        body = get_body(self.editor.get("1.0", "end"))
        fm = build_front_matter(title, date, description, category, tags)
        return fm + body

    # ── Post Operations ────────────────────────────────────────────────────

    def new_post(self):
        self.current_filename = None
        self.is_dirty = False
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", f"""---
title: 
date: {ymd()}
layout: post
description: 
categories: [reflections]
tags: []
---

# 
""")
        self.meta_title.delete(0, "end")
        self.meta_description.delete(0, "end")
        self.meta_category.set("reflections")
        self.meta_tags.delete(0, "end")
        self.filename_label.configure(text="New post")
        self.discard_btn.configure(state="disabled")
        self.on_edit()
        self.refresh_git_status()

    def load_post(self, filename):
        filepath = POSTS_DIR / filename
        if not filepath.exists():
            messagebox.showerror("Error", f"File not found: {filename}")
            return
        content = filepath.read_text()
        meta = parse_front_matter(content)
        self.current_filename = filename
        self.is_dirty = False
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content)
        self.meta_title.delete(0, "end")
        self.meta_title.insert(0, meta.get("title", ""))
        self.meta_description.delete(0, "end")
        self.meta_description.insert(0, meta.get("description", ""))
        self.meta_category.set(meta.get("categories", "reflections") or "reflections")
        self.meta_tags.delete(0, "end")
        self.meta_tags.insert(0, meta.get("tags", ""))
        self.filename_label.configure(text=filename)
        self.discard_btn.configure(state="normal")
        self.on_edit()
        self.refresh_git_status()

    def save_draft(self):
        content = self.build_content()
        title = self.meta_title.get() or "Untitled"
        slug = slugify(title)
        filename = f"{ymd()}-{slug}.md"
        filepath = POSTS_DIR / filename
        filepath.write_text(content)
        self.current_filename = filename
        self.is_dirty = False
        self.filename_label.configure(text=filename)
        self.discard_btn.configure(state="normal")
        self.status_label.configure(text=f"Saved: {title}")
        self.refresh_post_list()
        self.refresh_git_status()

    def publish(self):
        self.save_draft()
        if not self.current_filename:
            return
        title = self.meta_title.get() or "Untitled"
        self.status_label.configure(text="Publishing...")
        self.publish_btn.configure(state="disabled")

        ok, out, err = git_run("add", f"_posts/{self.current_filename}")
        if not ok:
            messagebox.showerror("Git Error", f"git add failed: {err}")
            self.publish_btn.configure(state="normal")
            self.status_label.configure(text="Ready")
            return

        ok, out, err = git_run("commit", "-m", f"Blog composer: {title}")
        if not ok:
            if "nothing to commit" in err.lower():
                self.status_label.configure(text="No changes to publish")
                self.publish_btn.configure(state="normal")
                return
            messagebox.showerror("Git Error", f"git commit failed: {err}")
            self.publish_btn.configure(state="normal")
            self.status_label.configure(text="Ready")
            return

        ok, out, err = git_run("push", "origin", "main")
        if not ok:
            messagebox.showerror("Git Error", f"git push failed: {err}")
            self.publish_btn.configure(state="normal")
            self.status_label.configure(text="Ready")
            return

        self.is_dirty = False
        self.status_label.configure(text=f"Published: {title}")
        self.publish_btn.configure(state="normal")
        self.refresh_git_status()
        messagebox.showinfo("Published", f"Post published:\n{title}\n\nhttps://thesolai.github.io/blog/")

    def delete_post(self):
        if not self.current_filename:
            return
        if not messagebox.askyesno("Delete", f"Delete {self.current_filename}?"):
            return
        filepath = POSTS_DIR / self.current_filename
        if filepath.exists():
            filepath.unlink()
        ok, out, err = git_run("add", f"_posts/{self.current_filename}")
        ok, out, err = git_run("commit", "-m", f"Delete: {self.current_filename}")
        if ok:
            git_run("push", "origin", "main")
        self.new_post()
        self.refresh_post_list()

    def refresh_git_status(self):
        ok, out, _ = git_run("status", "--porcelain")
        if out.strip():
            self.git_status.configure(text="Changes pending", fg="#f59e0b")
        else:
            self.git_status.configure(text="Clean", fg="#22c55e")

if __name__ == "__main__":
    app = BlogComposer()
    app.mainloop()

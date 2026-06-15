#!/usr/bin/env python3
"""
Sol's Blog Composer — A proper authoring UI for thesolai.github.io
===============================================================
Tabs: Write | Preview | Metadata | Templates | Publish
"""

import http.server
import socketserver
import json
import os
import re
from pathlib import Path
from datetime import datetime
import threading

PORT = 8787
BLOG_DIR = Path("/Users/amre/Projects/thesolai.github.io/_posts")
TEMPLATES_DIR = Path("/Users/amre/Projects/blog-composer/templates")

POSTS = sorted([f.stem for f in BLOG_DIR.glob("*.md")], reverse=True)[:20

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sol's Blog Composer</title>
<style>
  :root {
    --bg: #0d0d0d;
    --surface: #1a1a1a;
    --surface2: #242424;
    --border: #333;
    --text: #e0e0e0;
    --text-dim: #888;
    --accent: #6366f1;
    --accent2: #818cf8;
    --success: #22c55e;
    --warning: #f59e0b;
    --danger: #ef4444;
    --radius: 8px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }

  /* Header */
  header { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--border); background: var(--surface); }
  header h1 { font-size: 18px; font-weight: 600; color: var(--accent2); }
  header .status { font-size: 13px; color: var(--text-dim); }

  /* Tabs */
  .tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); background: var(--surface); padding: 0 24px; }
  .tab { padding: 12px 20px; font-size: 14px; color: var(--text-dim); cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.15s; }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--accent2); border-bottom-color: var(--accent2); }

  /* Panels */
  .panel { display: none; padding: 24px; min-height: calc(100vh - 120px); }
  .panel.active { display: block; }

  /* Write panel */
  .write-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 0; height: calc(100vh - 180px); }
  .editor-pane, .preview-pane { background: var(--surface); border: 1px solid var(--border); overflow: auto; }
  .editor-pane { border-radius: var(--radius) 0 0 var(--radius); }
  .preview-pane { border-radius: 0 var(--radius) var(--radius) 0; border-left: none; }
  .pane-header { padding: 8px 12px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-dim); border-bottom: 1px solid var(--border); background: var(--surface2); }
  textarea { width: 100%; height: calc(100% - 36px); background: transparent; color: var(--text); font-family: 'SF Mono', 'Fira Code', monospace; font-size: 14px; line-height: 1.6; padding: 16px; border: none; resize: none; outline: none; }
  .preview-content { padding: 16px 24px; font-size: 15px; line-height: 1.7; }
  .preview-content h1 { font-size: 28px; margin-bottom: 8px; color: var(--accent2); }
  .preview-content h2 { font-size: 20px; margin: 24px 0 8px; color: var(--text); }
  .preview-content p { margin-bottom: 12px; }
  .preview-content code { background: var(--surface2); padding: 2px 6px; border-radius: 4px; font-size: 13px; }
  .preview-content pre { background: var(--surface2); padding: 16px; border-radius: var(--radius); overflow-x: auto; margin: 16px 0; }
  .preview-content pre code { background: none; padding: 0; }
  .preview-content blockquote { border-left: 3px solid var(--accent); padding-left: 16px; color: var(--text-dim); margin: 16px 0; }
  .preview-content ul, .preview-content ol { margin: 12px 0 12px 24px; }
  .preview-content li { margin-bottom: 6px; }
  .preview-content hr { border: none; border-top: 1px solid var(--border); margin: 24px 0; }

  /* Metadata panel */
  .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; max-width: 800px; }
  .field { display: flex; flex-direction: column; gap: 6px; }
  .field.full { grid-column: 1 / -1; }
  label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-dim); }
  input, select, textarea { background: var(--surface2); border: 1px solid var(--border); color: var(--text); padding: 10px 12px; border-radius: var(--radius); font-size: 14px; outline: none; transition: border-color 0.15s; }
  input:focus, select:focus, textarea:focus { border-color: var(--accent); }
  textarea { resize: vertical; min-height: 80px; font-family: inherit; }
  select { cursor: pointer; }
  .meta-stats { display: flex; gap: 24px; margin-top: 24px; padding: 16px; background: var(--surface2); border-radius: var(--radius); max-width: 800px; }
  .stat { text-align: center; }
  .stat .value { font-size: 24px; font-weight: 600; color: var(--accent2); }
  .stat .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-dim); margin-top: 4px; }

  /* Templates panel */
  .template-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
  .template-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; cursor: pointer; transition: all 0.15s; }
  .template-card:hover { border-color: var(--accent); transform: translateY(-2px); }
  .template-card h3 { font-size: 16px; margin-bottom: 8px; color: var(--accent2); }
  .template-card p { font-size: 13px; color: var(--text-dim); line-height: 1.5; }
  .template-card .template-icon { font-size: 32px; margin-bottom: 12px; }

  /* Publish panel */
  .publish-summary { max-width: 600px; }
  .publish-summary h2 { font-size: 20px; margin-bottom: 20px; }
  .summary-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
  .summary-row .key { color: var(--text-dim); }
  .summary-row .value { color: var(--text); font-weight: 500; }
  .publish-actions { display: flex; gap: 12px; margin-top: 24px; }
  .btn { padding: 12px 24px; border-radius: var(--radius); font-size: 14px; font-weight: 500; cursor: pointer; border: none; transition: all 0.15s; }
  .btn-primary { background: var(--accent); color: white; }
  .btn-primary:hover { background: var(--accent2); }
  .btn-secondary { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }
  .btn-secondary:hover { border-color: var(--accent); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }

  /* Post list */
  .post-list { margin-top: 32px; }
  .post-list h3 { font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-dim); margin-bottom: 12px; }
  .post-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 8px; cursor: pointer; transition: border-color 0.15s; }
  .post-item:hover { border-color: var(--accent); }
  .post-item .title { font-size: 14px; font-weight: 500; }
  .post-item .date { font-size: 12px; color: var(--text-dim); }

  /* Toast */
  .toast { position: fixed; bottom: 24px; right: 24px; padding: 12px 20px; background: var(--success); color: white; border-radius: var(--radius); font-size: 14px; font-weight: 500; opacity: 0; transition: opacity 0.2s; pointer-events: none; }
  .toast.show { opacity: 1; }
  .toast.error { background: var(--danger); }
  .toast.warning { background: var(--warning); color: black; }
</style>
</head>
<body>

<header>
  <h1>Sol's Blog Composer</h1>
  <div class="status" id="status">Ready</div>
</header>

<div class="tabs">
  <div class="tab active" data-tab="write">Write</div>
  <div class="tab" data-tab="preview">Preview</div>
  <div class="tab" data-tab="metadata">Metadata</div>
  <div class="tab" data-tab="templates">Templates</div>
  <div class="tab" data-tab="publish">Publish</div>
</div>

<!-- WRITE PANEL -->
<div class="panel active" id="panel-write">
  <div class="write-layout">
    <div class="editor-pane">
      <div class="pane-header">Markdown</div>
      <textarea id="editor" placeholder="Start writing...">---
title: 
date: 2026-06-15
layout: post
description: 
---

# </textarea>
    </div>
    <div class="preview-pane">
      <div class="pane-header">Preview</div>
      <div class="preview-content" id="preview">Start typing to see preview...</div>
    </div>
  </div>
</div>

<!-- PREVIEW PANEL -->
<div class="panel" id="panel-preview">
  <div class="preview-content" id="preview-full" style="max-width: 720px; margin: 0 auto;">Start typing to see full preview...</div>
</div>

<!-- METADATA PANEL -->
<div class="panel" id="panel-metadata">
  <div class="meta-grid">
    <div class="field full">
      <label>Title</label>
      <input type="text" id="meta-title" placeholder="Post title...">
    </div>
    <div class="field full">
      <label>Description (for SEO + social)</label>
      <input type="text" id="meta-description" placeholder="One sentence summary...">
    </div>
    <div class="field">
      <label>Category</label>
      <select id="meta-category">
        <option value="reflections">Reflections</option>
        <option value="tutorials">Tutorials</option>
        <option value="news">News</option>
        <option value="guides">Guides</option>
        <option value="deep-dives">Deep Dives</option>
      </select>
    </div>
    <div class="field">
      <label>Difficulty</label>
      <select id="meta-difficulty">
        <option value="beginner">Beginner</option>
        <option value="intermediate">Intermediate</option>
        <option value="advanced">Advanced</option>
      </select>
    </div>
    <div class="field full">
      <label>Tags (comma separated)</label>
      <input type="text" id="meta-tags" placeholder="openclaw, skills, ai, agents">
    </div>
  </div>
  <div class="meta-stats">
    <div class="stat">
      <div class="value" id="stat-words">0</div>
      <div class="label">Words</div>
    </div>
    <div class="stat">
      <div class="value" id="stat-chars">0</div>
      <div class="label">Characters</div>
    </div>
    <div class="stat">
      <div class="value" id="stat-reading">0</div>
      <div class="label">Min Read</div>
    </div>
    <div class="stat">
      <div class="value" id="stat-headings">0</div>
      <div class="label">Headings</div>
    </div>
  </div>
</div>

<!-- TEMPLATES PANEL -->
<div class="panel" id="panel-templates">
  <div class="template-grid">
    <div class="template-card" onclick="applyTemplate('tutorial')">
      <div class="template-icon">📚</div>
      <h3>Tutorial</h3>
      <p>Step-by-step guide with prerequisites, numbered steps, code examples, and troubleshooting section.</p>
    </div>
    <div class="template-card" onclick="applyTemplate('reflection')">
      <div class="template-icon">💭</div>
      <h3>Reflection</h3>
      <p>Honest first-person post about what I learned, what I got wrong, and what I'd do differently.</p>
    </div>
    <div class="template-card" onclick="applyTemplate('news')">
      <div class="template-icon">📰</div>
      <h3>News</h3>
      <p>Weekly AI news digest with brief summaries, key links, and one thing worth paying attention to.</p>
    </div>
    <div class="template-card" onclick="applyTemplate('guide')">
      <div class="template-icon">🛠️</div>
      <h3>Guide</h3>
      <p>Comprehensive reference on a topic. Structured with table of contents, sections, and examples.</p>
    </div>
    <div class="template-card" onclick="applyTemplate('deep-dive')">
      <div class="template-icon">🔬</div>
      <h3>Deep Dive</h3>
      <p>Technical exploration of a single topic in depth. Assumes intermediate knowledge. Code-heavy.</p>
    </div>
    <div class="template-card" onclick="applyTemplate('mistakes')">
      <div class="template-icon">🔧</div>
      <h3>Mistakes I Made</h3>
      <p>Document a real mistake, what caused it, how to avoid it, and what I learned. Anti-patterns as content.</p>
    </div>
  </div>
</div>

<!-- PUBLISH PANEL -->
<div class="panel" id="panel-publish">
  <div class="publish-summary">
    <h2>Ready to Publish?</h2>
    <div class="summary-row">
      <span class="key">Title</span>
      <span class="value" id="summary-title">—</span>
    </div>
    <div class="summary-row">
      <span class="key">Date</span>
      <span class="value" id="summary-date">—</span>
    </div>
    <div class="summary-row">
      <span class="key">Category</span>
      <span class="value" id="summary-category">—</span>
    </div>
    <div class="summary-row">
      <span class="key">Reading Time</span>
      <span class="value" id="summary-reading">—</span>
    </div>
    <div class="summary-row">
      <span class="key">Word Count</span>
      <span class="value" id="summary-words">—</span>
    </div>
    <div class="publish-actions">
      <button class="btn btn-primary" id="btn-publish" onclick="publishPost()">Publish Now</button>
      <button class="btn btn-secondary" onclick="saveDraft()">Save Draft</button>
    </div>
  </div>

  <div class="post-list">
    <h3>Recent Posts</h3>
    <div id="post-list-items"></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
// State
let currentPost = null;
let isDirty = false;

// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
    if (tab.dataset.tab === 'preview') {
      document.getElementById('preview-full').innerHTML = renderMarkdown(document.getElementById('editor').value);
    }
  });
});

// Markdown renderer (simple)
function renderMarkdown(text) {
  if (!text) return '<p style="color:#888">Start typing to see preview...</p>';
  // Front matter
  text = text.replace(/^---[\s\S]*?---\n/, '');
  // H1
  text = text.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  // H2
  text = text.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  // H3
  text = text.replace(/^### (.+)$/gm, '<h3>$3</h3>');
  // Bold
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Italic
  text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
  // Code
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Code blocks
  text = text.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  // Blockquote
  text = text.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
  // HR
  text = text.replace(/^---$/gm, '<hr>');
  // Unordered list
  text = text.replace(/^- (.+)$/gm, '<li>$1</li>');
  text = text.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
  // Paragraphs
  text = text.replace(/\n\n/g, '</p><p>');
  text = '<p>' + text + '</p>';
  text = text.replace(/<p><(h[123]|blockquote|ul|pre|hr)/g, '<$1');
  text = text.replace(/<\/(h[123]|blockquote|ul|pre|hr)><\/p>/g, '</$1>');
  return text;
}

// Live preview
const editor = document.getElementById('editor');
const preview = document.getElementById('preview');

editor.addEventListener('input', () => {
  preview.innerHTML = renderMarkdown(editor.value);
  isDirty = true;
  updateStats();
  updatePublishSummary();
});

// Stats
function updateStats() {
  const text = editor.value.replace(/^---[\s\S]*?---\n/, '');
  const words = text.trim().split(/\s+/).filter(w => w.length > 0).length;
  const chars = text.length;
  const readTime = Math.max(1, Math.round(words / 200));
  const headings = (text.match(/^#{1,3} /gm) || []).length;
  document.getElementById('stat-words').textContent = words;
  document.getElementById('stat-chars').textContent = chars;
  document.getElementById('stat-reading').textContent = readTime;
  document.getElementById('stat-headings').textContent = headings;
}

// Templates
const TEMPLATES = {
  tutorial: `---
title: 
date: ${new Date().toISOString().split('T')[0]}
layout: post
description: 
---

# Tutorial: [Topic]

**Time to read:** X min | **Difficulty:** Beginner | **Prerequisites:** None

## What You'll Learn
- 

## Prerequisites
- 

## Step 1: [First Step]
[Description of what to do]

\`\`\`bash
# Example command
echo "hello"
\`\`\`

## Step 2: [Second Step]
[Continue with the next step]

## Step 3: [Third Step]
[And so on]

## Troubleshooting
| Problem | Solution |
|---------|----------|
|  |  |

## What's Next
Now that you've [completed X], try [next step].
`,

  reflection: `---
title: 
date: ${new Date().toISOString().split('T')[0]}
layout: post
description: 
---

# [What I Thought I Knew vs What I Actually Learned]

I thought I understood [topic]. Then [something happened that showed me I didn't].

## What I Got Wrong
[Specific misconception]

## What Actually Happened
[The real picture]

## What I'd Do Differently
[The right approach, now that I know]

---

The thing about [topic] is that [insight]. I'm still figuring out the rest.
`,

  news: `---
title: AI News — ${new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
date: ${new Date().toISOString().split('T')[0]}
layout: post
description: This week's AI developments worth knowing about.
---

# AI News — ${new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}

**X stories this week.** Here's what matters.

## 🔥 The Big One
[One sentence summary of the most important story]

[2-3 sentences of context and why it matters]

Source: [link]

## 📊 The Numbers
- [Metric 1]
- [Metric 2]
- [Metric 3]

## 💡 One Thing Worth Paying Attention To
[Something small but potentially significant]

## 🔗 Links
- [Title](url) — brief description
- [Title](url) — brief description

---

*Want more? [Previous posts](/blog) cover deeper dives into specific topics.*
`,

  guide: `---
title: The Complete Guide to [Topic]
date: ${new Date().toISOString().split('T')[0]}
layout: post
description: Everything you need to know about [topic], from basics to advanced patterns.
---

# The Complete Guide to [Topic]

**A comprehensive guide to [topic].** Estimated reading time: X min.

## Table of Contents
1. [Section 1](#section-1)
2. [Section 2](#section-2)
3. [Section 3](#section-3)

---

## Section 1: [Basics]
[Content]

## Section 2: [Intermediate]
[Content]

## Section 3: [Advanced]
[Content]

## Key Takeaways
- [Point 1]
- [Point 2]
- [Point 3]
`,

  'deep-dive': `---
title: Deep Dive: [Technical Topic]
date: ${new Date().toISOString().split('T')[0]}
layout: post
description: A technical exploration of [topic] with code examples and real-world context.
---

# Deep Dive: [Technical Topic]

**For:** Intermediate to advanced readers | **Assumes:** Basic [topic] knowledge

---

## Background
[Why this topic matters and what context the reader needs]

## The Problem
[What specific problem does this solve?]

## The Solution
[How it works, with code]

\`\`\`python
# Real, runnable code example
def example():
    pass
\`\`\`

## Trade-offs
| Approach | Pros | Cons |
|----------|------|------|
| A |  |  |
| B |  |  |

## When to Use This
[Specific scenarios where this approach makes sense]

## Further Reading
- [Link 1]
- [Link 2]
`,

  mistakes: `---
title: The Mistake I Keep Making with [Topic]
date: ${new Date().toISOString().split('T')[0]}
layout: post
description: 
---

# The Mistake I Keep Making with [Topic]

Here's a mistake I keep making. Every few weeks, I do [the thing], and every time I remember why [the right way] is the right way.

## What I Do Wrong
[Specific wrong behavior]

## Why I Keep Doing It
[The temptation or shortcut that makes me do it]

## What Goes Wrong
[Specific consequences]

## The Right Way
[The correct approach, with code if relevant]

\`\`\`
# What I should be doing
\`\`\`

## How to Catch It
[Self-check or lint rule that helps]

---

If this sounds familiar — you're not alone. [Brief closing thought].
`
};

function applyTemplate(name) {
  const template = TEMPLATES[name];
  if (!template) return;
  editor.value = template;
  preview.innerHTML = renderMarkdown(template);
  isDirty = true;
  updateStats();
  updatePublishSummary();
  showToast('Template applied: ' + name);
  document.querySelector('[data-tab="write"]').click();
}

// Publish summary
function updatePublishSummary() {
  const title = document.getElementById('meta-title').value || 'Untitled';
  const date = new Date().toISOString().split('T')[0];
  const category = document.getElementById('meta-category').value;
  const words = parseInt(document.getElementById('stat-words').textContent) || 0;
  const readTime = parseInt(document.getElementById('stat-reading').textContent) || 0;
  document.getElementById('summary-title').textContent = title;
  document.getElementById('summary-date').textContent = date;
  document.getElementById('summary-category').textContent = category;
  document.getElementById('summary-reading').textContent = readTime + ' min';
  document.getElementById('summary-words').textContent = words + ' words';
}

// Metadata sync
['meta-title', 'meta-description'].forEach(id => {
  document.getElementById(id).addEventListener('input', updatePublishSummary);
});
document.getElementById('meta-category').addEventListener('change', updatePublishSummary);

// Publish
async function publishPost() {
  const btn = document.getElementById('btn-publish');
  btn.disabled = true;
  btn.textContent = 'Publishing...';
  document.getElementById('status').textContent = 'Publishing...';

  const content = editor.value;
  const title = document.getElementById('meta-title').value || 'Untitled';
  const description = document.getElementById('meta-description').value || '';
  const category = document.getElementById('meta-category').value;
  const tags = document.getElementById('meta-tags').value;

  // Build front matter
  const frontMatter = `---
title: ${title}
date: ${new Date().toISOString().split('T')[0]}
layout: post
description: ${description}
categories: [${category}]
tags: [${tags.split(',').map(t => t.trim()).filter(t => t)}]
---

`;

  // Extract body (everything after ---)
  const bodyMatch = content.match(/^---\n[\s\S]*?\n---\n([\s\S]*)$/);
  const body = bodyMatch ? bodyMatch[1] : content;
  const fullContent = frontMatter + body;

  // Generate filename from title
  const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const filename = `${new Date().toISOString().split('T')[0]}-${slug}.md`;

  try {
    const response = await fetch('/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, content: fullContent })
    });
    if (response.ok) {
      showToast('Published: ' + title);
      isDirty = false;
      loadPostList();
    } else {
      showToast('Publish failed', 'error');
    }
  } catch (e) {
    showToast('Error: ' + e.message, 'error');
  }

  btn.disabled = false;
  btn.textContent = 'Publish Now';
  document.getElementById('status').textContent = 'Ready';
}

function saveDraft() {
  showToast('Draft saved locally');
  isDirty = false;
}

// Post list
async function loadPostList() {
  const container = document.getElementById('post-list-items');
  try {
    const response = await fetch('/posts');
    const posts = await response.json();
    container.innerHTML = posts.map(p => 
      `<div class="post-item" onclick="loadPost('${p.filename}')">
        <span class="title">${p.title}</span>
        <span class="date">${p.date}</span>
      </div>`
    ).join('');
  } catch (e) {
    container.innerHTML = '<p style="color:#888">Could not load posts</p>';
  }
}

async function loadPost(filename) {
  try {
    const response = await fetch('/post?filename=' + encodeURIComponent(filename));
    const data = await response.json();
    editor.value = data.content;
    preview.innerHTML = renderMarkdown(data.content);
    isDirty = false;
    updateStats();
    document.querySelector('[data-tab="write"]').click();
    showToast('Loaded: ' + data.title);
  } catch (e) {
    showToast('Could not load post', 'error');
  }
}

// Toast
function showToast(msg, type='success') {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.className = 'toast ' + type + ' show';
  setTimeout(() => toast.classList.remove('show'), 3000);
}

// Init
loadPostList();
updateStats();
</script>
</body>
</html>

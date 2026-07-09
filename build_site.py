#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the cybersec news portal (static site) for GitHub Pages.

- Converts daily markdown reports  -> daily/<name>.html  (styled)
- Copies weekly HTML posters        -> weekly/<name>.html (as-is)
- Regenerates index.html linking everything (sorted, newest first)

Idempotent: safe to re-run after each automation run.

Sources (authoritative paths, see automation cwds):
  DAILY_SRC  = C:\\Users\\yyankee\\WorkBuddy\\automation-cybersec-daily
  WEEKLY_SRC = C:\\Users\\yyankee\\WorkBuddy\\automation-cybersec-weekly
Output:
  SITE       = C:\\Users\\yyankee\\WorkBuddy\\cybersec-news-site
"""

import os
import re
import glob
import datetime

import markdown

DAILY_SRC = r"D:\WorkBuddy\automation-cybersec-daily"
WEEKLY_SRC = r"D:\WorkBuddy\automation-cybersec-weekly"
SITE = r"C:\Users\yyankee\WorkBuddy\cybersec-news-site"
DAILY_OUT = os.path.join(SITE, "daily")
WEEKLY_OUT = os.path.join(SITE, "weekly")

# ---------------------------------------------------------------------------
# Shared CSS (dark "security dashboard" theme, consistent with weekly poster)
# ---------------------------------------------------------------------------
CSS = """
:root{
  --bg:#0b1120; --card:#111827; --card-border:#1f2937;
  --text:#f3f4f6; --muted:#9ca3af; --accent:#3b82f6;
  --accent-soft:rgba(59,130,246,.15); --gold:#fbbf24;
}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  background:var(--bg);color:var(--text);line-height:1.7;}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.topbar{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:12px;
  padding:14px 24px;background:rgba(11,17,32,.85);backdrop-filter:blur(8px);
  border-bottom:1px solid var(--card-border)}
.topbar .brand{font-weight:800;letter-spacing:.5px}
.topbar .brand .shield{color:var(--accent)}
.topbar .spacer{flex:1}
.topbar .home{font-size:14px;color:var(--muted)}
.wrap{max-width:900px;margin:0 auto;padding:32px 24px 64px}
.card{background:var(--card);border:1px solid var(--card-border);border-radius:16px;padding:28px 32px;margin-top:24px}
h1{font-size:28px;margin:0 0 4px}
h2{font-size:20px;margin:32px 0 12px;color:#e5e7eb}
h3{font-size:17px;margin:24px 0 8px;color:#e5e7eb}
blockquote{margin:14px 0;padding:10px 16px;border-left:3px solid var(--accent);
  background:var(--accent-soft);color:var(--muted);border-radius:0 8px 8px 0;font-size:14px}
table{width:100%;border-collapse:collapse;margin:14px 0;font-size:14px}
th,td{border:1px solid var(--card-border);padding:8px 12px;text-align:left;vertical-align:top}
th{background:#0f172a;color:#cbd5e1;font-weight:700}
tr:nth-child(even) td{background:rgba(255,255,255,.02)}
hr{border:none;border-top:1px solid var(--card-border);margin:28px 0}
.meta{color:var(--muted);font-size:14px;margin-bottom:8px}
ul,ol{padding-left:22px}
code{background:#0f172a;padding:2px 6px;border-radius:6px;font-size:13px}
footer{color:var(--muted);font-size:13px;text-align:center;padding:24px}
"""

# ---------------------------------------------------------------------------
# Daily article template
# ---------------------------------------------------------------------------
DAILY_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}} | 网络安全新闻中心</title>
<style>""" + CSS + """</style>
</head>
<body>
<div class="topbar">
  <span class="brand"><span class="shield">🛡️</span> 网络安全新闻中心</span>
  <span class="spacer"></span>
  <a class="home" href="../index.html">← 返回首页</a>
</div>
<div class="wrap">
  <article class="card">
{{BODY}}
  </article>
  <footer>本页由自动化采集生成 · 仅供安全研究参考</footer>
</div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Index (portal) template
# ---------------------------------------------------------------------------
INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>网络安全新闻中心</title>
<style>""" + CSS + """
.grid{display:grid;gap:10px}
.row{display:flex;align-items:center;gap:12px;padding:14px 18px;background:var(--card);
  border:1px solid var(--card-border);border-radius:12px;transition:border-color .15s}
.row:hover{border-color:var(--accent);text-decoration:none}
.row .date{font-weight:700;min-width:120px}
.row .desc{color:var(--muted);font-size:14px}
.row .tag{margin-left:auto;font-size:12px;color:var(--gold);border:1px solid var(--gold);
  padding:2px 8px;border-radius:999px}
.section-title{display:flex;align-items:center;gap:10px;margin:36px 0 14px}
.section-title h2{margin:0}
.section-title .count{color:var(--muted);font-size:14px}
</style>
</head>
<body>
<div class="topbar">
  <span class="brand"><span class="shield">🛡️</span> 网络安全新闻中心</span>
  <span class="spacer"></span>
  <span class="home">每日采集 · 每周精选</span>
</div>
<div class="wrap">
  <h1>🛡️ 网络安全新闻中心</h1>
  <p class="meta">自动采集自 Hacker News / The Hacker News / BleepingComputer 等公开来源 · 站点生成于 {{BUILDTIME}}</p>

  <div class="section-title"><h2>📅 每日安全日报</h2><span class="count">共 {{DAILY_COUNT}} 期</span></div>
  <div class="grid">
{{DAILY_ROWS}}
  </div>

  <div class="section-title"><h2>📊 每周精选海报</h2><span class="count">共 {{WEEKLY_COUNT}} 期</span></div>
  <div class="grid">
{{WEEKLY_ROWS}}
  </div>

  <footer>本站点由 WorkBuddy 自动化任务生成并发布至 GitHub Pages · 仅供安全研究参考</footer>
</div>
</body>
</html>
"""

# ---------------------------------------------------------------------------

def date_from_filename(fn):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", fn)
    return m.group(1) if m else "0000-00-00"


def week_from_filename(fn):
    m = re.search(r"W(\d+)", fn)
    return int(m.group(1)) if m else 0


def convert_daily(md_path, out_path):
    with open(md_path, encoding="utf-8") as f:
        text = f.read()
    title = "网络安全日报"
    m = re.search(r"^#\s+(.+)$", text, re.M)
    if m:
        title = m.group(1).strip()
    body = markdown.markdown(text, extensions=["extra", "sane_lists"])
    html = DAILY_TEMPLATE.replace("{{TITLE}}", title).replace("{{BODY}}", body)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return title


def build():
    os.makedirs(DAILY_OUT, exist_ok=True)
    os.makedirs(WEEKLY_OUT, exist_ok=True)

    # ---- daily ----
    daily_files = sorted(glob.glob(os.path.join(DAILY_SRC, "daily_news_*.md")),
                         key=lambda p: date_from_filename(os.path.basename(p)),
                         reverse=True)
    daily_rows = []
    for md_path in daily_files:
        base = os.path.splitext(os.path.basename(md_path))[0]
        out_html = os.path.join(DAILY_OUT, base + ".html")
        title = convert_daily(md_path, out_html)
        d = date_from_filename(base)
        daily_rows.append(
            f'    <a class="row" href="daily/{base}.html">'
            f'<span class="date">{d}</span>'
            f'<span class="desc">{title}</span></a>'
        )
    print(f"[daily] converted {len(daily_files)} reports")

    # ---- weekly ----
    weekly_files = sorted(glob.glob(os.path.join(WEEKLY_SRC, "weekly_security_poster_*.html")),
                          key=lambda p: week_from_filename(os.path.basename(p)),
                          reverse=True)
    weekly_rows = []
    for html_path in weekly_files:
        base = os.path.splitext(os.path.basename(html_path))[0]
        out_html = os.path.join(WEEKLY_OUT, base + ".html")
        with open(html_path, encoding="utf-8") as f:
            content = f.read()
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(content)
        wk = week_from_filename(base)
        weekly_rows.append(
            f'    <a class="row" href="weekly/{base}.html">'
            f'<span class="date">第 {wk} 周</span>'
            f'<span class="desc">高分安全新闻精选海报 (W{wk})</span>'
            f'<span class="tag">海报</span></a>'
        )
    print(f"[weekly] copied {len(weekly_files)} posters")

    # ---- index ----
    build_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    index = (INDEX_TEMPLATE
             .replace("{{BUILDTIME}}", build_time)
             .replace("{{DAILY_COUNT}}", str(len(daily_rows)))
             .replace("{{WEEKLY_COUNT}}", str(len(weekly_rows)))
             .replace("{{DAILY_ROWS}}", "\n".join(daily_rows) if daily_rows else "    <p class='meta'>暂无日报</p>")
             .replace("{{WEEKLY_ROWS}}", "\n".join(weekly_rows) if weekly_rows else "    <p class='meta'>暂无周报</p>"))
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(index)
    print("[index] regenerated index.html")

    # ---- .nojekyll so GitHub Pages serves raw HTML, no Jekyll processing ----
    with open(os.path.join(SITE, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")
    print("[ok] build complete")


if __name__ == "__main__":
    build()

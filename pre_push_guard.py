#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pre_push_guard.py — 发布前防误删 / 漂移检测守护脚本。

目的：防止"本地源 .md 落后于线上"时，把线上已有的近期日报从索引 / 站点地图中
删除（即把 GitHub Pages 回退到更早的日期）。这是本次故障的根因防护。

两种用法：
  1) 默认（发布前，需先跑过 build_site.py）：
       比较"本地刚构建的 index.html"与"线上 GitHub Pages 的 index.html"
       的日报日期集合。本地落后/缺失线上已有日期 -> 中止推送。
  2) --source（独立只读漂移监控，无需构建）：
       比较"本地源 .md 日期集合"与"线上 GitHub Pages 的 index.html"
       的日报日期集合。本地源落后于线上 -> 告警（说明发布可能已被中止）。

退出码：
  0  = 本地覆盖了线上全部日报日期，可安全推送 / 同步正常。
  2  = 检测到漂移（本地落后或无法验证远程），不应推送。

线上 index.html 为公开 GitHub Pages，无需任何凭据即可抓取。
"""
import os
import re
import sys
import datetime
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = HERE
DAILY_SRC = r"D:/WorkBuddy/automation-cybersec-daily"
SITE_URL = "https://y24yankee.github.io/cybersec-news"
REMOTE_INDEX = SITE_URL + "/index.html"
DATE_RE = re.compile(r"daily_news_(\d{4}-\d{2}-\d{2})\.html")


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "pre-push-guard/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def local_built_dates():
    p = os.path.join(SITE, "index.html")
    if not os.path.exists(p):
        return set()
    with open(p, encoding="utf-8") as f:
        return set(DATE_RE.findall(f.read()))


def local_source_dates():
    import glob
    s = set()
    md_re = re.compile(r"daily_news_(\d{4}-\d{2}-\d{2})\.(?:html|md)")
    for fp in glob.glob(os.path.join(DAILY_SRC, "daily_news_*.md")):
        m = md_re.search(os.path.basename(fp))
        if m:
            s.add(m.group(1))
    return s


def remote_dates():
    try:
        return set(DATE_RE.findall(fetch(REMOTE_INDEX)))
    except Exception as e:  # 网络/离线 -> 无法验证，安全起见判为异常
        print(f"[GUARD] ⚠️ 无法获取线上 index.html：{e}")
        print("[GUARD] 出于安全考虑，未验证远程状态时【中止推送】，避免误删线上内容。")
        return None


def report(local, remote, source_mode):
    print("=" * 64)
    print("[GUARD] 网络安全新闻站 · 发布前漂移检测 (防误删保护)")
    print("=" * 64)
    src_label = "本地源 .md" if source_mode else "本地构建 index"
    print(f"[GUARD] {src_label}日报数: {len(local)}  (最新: {max(local) if local else '无'})")
    if remote is None:
        print("[GUARD] 结论: 无法验证远程 -> 退出码 2 (中止)")
        return 2
    print(f"[GUARD] 线上日报数:       {len(remote)}  (最新: {max(remote) if remote else '无'})")

    dropped = sorted(remote - local)
    if not dropped:
        print("[GUARD] ✅ 本地覆盖了线上全部日报日期，可安全推送。")
        return 0

    gap = None
    if local and remote:
        try:
            gap = (datetime.date.fromisoformat(max(remote))
                   - datetime.date.fromisoformat(max(local))).days
        except Exception:
            gap = None
    print(f"[GUARD] ⛔ 检测到漂移：本地落后/缺失 {len(dropped)} 个线上已有日期，"
          f"推送会回退这些内容！")
    print(f"[GUARD] 缺失/落后日期: {dropped}")
    if gap is not None:
        print(f"[GUARD] 本地最新 {max(local)} 落后线上最新 {max(remote)} 约 {gap} 天。")
    print("[GUARD] 处置: 【中止 git push】。请先恢复本地源 .md "
          "(git pull 或补齐) 后重试，切勿强行推送。")
    print("[GUARD] —— 漂移告警结束 ——")
    return 2


def main():
    source_mode = "--source" in sys.argv[1:]
    local = local_source_dates() if source_mode else local_built_dates()
    remote = remote_dates()
    return report(local, remote, source_mode)


if __name__ == "__main__":
    sys.exit(main())

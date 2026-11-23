#!/usr/bin/env python3
"""本地每日热榜构建器。

把当日全网热榜直接生成到 site/<YYYY-MM-DD>/ 目录（含 index.html / hot.json / hot.md），
并重建 site/index.html 入口页，列出全部已保存日期、可点击跳转。

用法:
    python local/build_local_site.py                 # 生成今天（北京时间）的
    python local/build_local_site.py --date 2026-11-20   # 回填某一天
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
CST = timezone(timedelta(hours=8))
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def date_dirs() -> list[str]:
    """列出 site/ 下所有 YYYY-MM-DD 目录，从新到旧。"""
    if not SITE.is_dir():
        return []
    names = [
        p.name for p in SITE.iterdir()
        if p.is_dir() and DATE_RE.match(p.name)
    ]
    return sorted(names, reverse=True)


def build_entry_page() -> None:
    """重建 site/index.html 入口页，列出全部日期。"""
    SITE.mkdir(parents=True, exist_ok=True)
    dates = date_dirs()
    if dates:
        rows = "\n".join(
            f'      <li><a href="{d}/index.html">{d}</a></li>' for d in dates
        )
    else:
        rows = '      <li>暂无数据</li>'
    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>每日热榜归档</title>
<style>
:root {{ color-scheme: light dark; }}
body {{ font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; max-width: 720px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; background: #fff; }}
h1 {{ font-size: 20px; font-weight: 600; }}
.sub {{ color: #888; font-size: 13px; margin-bottom: 24px; }}
ul {{ list-style: none; padding: 0; margin: 0; }}
li {{ margin: 8px 0; }}
a {{ display: block; padding: 12px 16px; border: 1px solid #e5e5e5; border-radius: 8px; text-decoration: none; color: #1a1a1a; font-size: 15px; }}
a:hover {{ border-color: #999; background: #f6f6f6; }}
</style>
</head>
<body>
<h1>每日热榜归档</h1>
<p class="sub">共 {len(dates)} 个日期的全网热榜快照，点击日期查看</p>
<ul>
{rows}
</ul>
</body>
</html>
"""
    (SITE / "index.html").write_text(page, encoding="utf-8")


def build_day(date: str, hot_sources: str) -> Path:
    """把某一天的热榜生成到 site/<date>/，返回该日期目录。"""
    date_dir = SITE / date
    date_dir.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["LAST30DAYS_OUTPUT_DIR"] = str(date_dir)

    cmd = [
        sys.executable, str(ROOT / "scripts" / "last30days.py"),
        "--hot", "--hot-sources", hot_sources, "--emit", "html-path",
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), env=env)
    if r.returncode != 0:
        raise RuntimeError(f"热榜生成失败，退出码 {r.returncode}")

    hot_html = date_dir / "hot.html"
    if hot_html.exists():
        os.replace(hot_html, date_dir / "index.html")

    return date_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="本地每日热榜构建器")
    parser.add_argument("--date", default=None, help="指定日期 YYYY-MM-DD，默认今天（北京时间）")
    parser.add_argument("--hot-sources", default="boards,news,global",
                        help="热榜来源，如 boards,news,global 或 boards（默认 boards,news,global）")
    args = parser.parse_args()

    date = args.date or datetime.now(CST).strftime("%Y-%m-%d")
    if not DATE_RE.match(date):
        print(f"错误: 日期格式应为 YYYY-MM-DD，得到 {date}", file=sys.stderr)
        return 1

    try:
        date_dir = build_day(date, args.hot_sources)
        build_entry_page()
    except Exception as exc:  # noqa: BLE001
        print(f"构建失败: {exc}", file=sys.stderr)
        return 1

    print(f"完成: {date_dir / 'index.html'}")
    print(f"入口页: {SITE / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

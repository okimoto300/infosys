#!/usr/bin/env python3
"""gen_index.py — GitHub Pages 用のインデックス HTML を生成する。

各企業の資料は site/<slug>/index.html に配置される前提で、それらへの
リンク一覧（マスター情報つき）を site/index.html として出力する。

使い方:
    python3 tools/gen_index.py                 # → site/index.html
    python3 tools/gen_index.py --out site      # 出力ディレクトリ指定
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deckmgr  # noqa: E402

TEMPLATE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>プレゼン資料 一覧</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin:0; background:#f5f6f8; color:#1c2530; }}
  header {{ background:#0b3d63; color:#fff; padding:24px 28px; }}
  header h1 {{ margin:0; font-size:22px; }}
  header .sub {{ opacity:.85; font-size:13px; margin-top:6px; }}
  main {{ max-width:880px; margin:28px auto; padding:0 16px; }}
  .card {{ background:#fff; border-radius:10px; padding:20px 24px; margin-bottom:20px;
           box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  ul {{ list-style:none; padding:0; margin:0; }}
  li {{ border-bottom:1px solid #eef0f3; }}
  li:last-child {{ border-bottom:0; }}
  a.client {{ display:flex; justify-content:space-between; align-items:center;
              padding:14px 6px; text-decoration:none; color:#0b3d63; }}
  a.client:hover {{ background:#f0f6fc; }}
  .name {{ font-weight:600; }}
  .slug {{ color:#5b6b7b; font-size:13px; }}
  .meta {{ font-size:13px; color:#5b6b7b; }}
  footer {{ text-align:center; color:#9aa7b4; font-size:12px; padding:20px; }}
</style></head>
<body>
<header>
  <h1>{title}</h1>
  <div class="sub">提案先企業ごとのプレゼン資料一覧（マスター v{version}）</div>
</header>
<main>
  <div class="card">
    <p class="meta">マスター更新日: {updated} / 公開生成日時: {generated}</p>
    <ul>{items}</ul>
  </div>
</main>
<footer>マスター資料 + 企業別カスタマイズ — 自動生成</footer>
</body></html>"""


def build_index(out_dir: Path) -> Path:
    meta = deckmgr._load_yaml(deckmgr.MASTER_META)
    items = []
    for slug in deckmgr.list_clients():
        cfg = deckmgr._load_yaml(deckmgr.client_dir(slug) / "config.yaml")
        name = html.escape(str(cfg.get("client_name", slug)))
        items.append(
            f'<li><a class="client" href="./{html.escape(slug)}/">'
            f'<span class="name">{name}</span>'
            f'<span class="slug">{html.escape(slug)} ›</span></a></li>'
        )
    if not items:
        items.append('<li><p class="meta">公開対象の企業がありません。</p></li>')

    page = TEMPLATE.format(
        title=html.escape(str(meta.get("title", "プレゼン資料"))),
        version=html.escape(str(meta.get("version", "?"))),
        updated=html.escape(str(meta.get("updated", "?"))),
        generated=_dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        items="".join(items),
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "index.html"
    dest.write_text(page, encoding="utf-8")
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description="GitHub Pages 用インデックス生成")
    ap.add_argument("--out", default="site", help="出力ディレクトリ（既定: site）")
    args = ap.parse_args()
    dest = build_index(deckmgr.ROOT / args.out)
    print(f"✓ インデックスを生成: {dest}")


if __name__ == "__main__":
    main()

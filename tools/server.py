#!/usr/bin/env python3
"""server.py — プレゼン資料バージョン管理システムの Web ダッシュボード

ブラウザから「マスター/企業の状態確認・資料ビルド・プレビュー」が行える
軽量な管理画面。追加の依存は不要（Python 標準ライブラリ + 既存の deckmgr）。

起動:
    python3 tools/server.py            # http://localhost:8080
    python3 tools/server.py --port 9000
"""
from __future__ import annotations

import argparse
import html
import sys
from argparse import Namespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# 既存の CLI ロジックを再利用する
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deckmgr  # noqa: E402


def _safe(fn, *args):
    """deckmgr の関数は失敗時に sys.exit する。サーバーでは例外として捕捉する。"""
    try:
        return fn(*args), None
    except SystemExit as e:
        return None, str(e)


PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>プレゼン資料 バージョン管理</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 0; background:#f5f6f8; color:#1c2530; }}
  header {{ background:#0b3d63; color:#fff; padding:18px 28px; }}
  header h1 {{ margin:0; font-size:20px; }}
  header .sub {{ opacity:.8; font-size:13px; margin-top:4px; }}
  main {{ max-width:980px; margin:24px auto; padding:0 16px; }}
  .card {{ background:#fff; border-radius:10px; padding:20px 24px; margin-bottom:20px;
           box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  table {{ width:100%; border-collapse:collapse; }}
  th, td {{ text-align:left; padding:10px 8px; border-bottom:1px solid #eef0f3; font-size:14px; }}
  th {{ color:#5b6b7b; font-weight:600; }}
  .badge {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px; }}
  .ok {{ background:#e3f6ea; color:#1a7f43; }}
  .warn {{ background:#fdecdc; color:#b5550f; }}
  .muted {{ background:#eceff2; color:#5b6b7b; }}
  a.btn {{ display:inline-block; padding:6px 14px; border-radius:6px; background:#0b6bcb;
           color:#fff; text-decoration:none; font-size:13px; margin-right:6px; }}
  a.btn.secondary {{ background:#eef2f6; color:#0b3d63; }}
  a.btn.warnbtn {{ background:#b5550f; }}
  pre {{ background:#0f1722; color:#d6e2ef; padding:18px; border-radius:8px; overflow:auto;
         font-size:13px; line-height:1.5; }}
  .note {{ font-size:13px; color:#5b6b7b; }}
  code {{ background:#eef2f6; padding:1px 5px; border-radius:4px; }}
</style></head>
<body>
<header>
  <h1>プレゼン資料 バージョン管理ダッシュボード</h1>
  <div class="sub">マスター資料 + 提案先企業ごとのカスタマイズ版</div>
</header>
<main>{body}</main>
</body></html>"""


def _badge(state: str) -> str:
    if state == "最新":
        return '<span class="badge ok">最新</span>'
    if state.startswith("要追従"):
        return f'<span class="badge warn">{html.escape(state)}</span>'
    return f'<span class="badge muted">{html.escape(state)}</span>'


def dashboard_html(message: str = "") -> str:
    meta, _ = _safe(deckmgr._load_yaml, deckmgr.MASTER_META)
    meta = meta or {}
    cur = deckmgr._current_master_commit()
    parts = []
    if message:
        parts.append(f'<div class="card"><strong>{html.escape(message)}</strong></div>')

    parts.append(
        '<div class="card"><h2>マスター資料</h2>'
        f'<p class="note">タイトル: {html.escape(str(meta.get("title","-")))}<br>'
        f'バージョン: <code>{html.escape(str(meta.get("version","?")))}</code>'
        f' / 更新日 {html.escape(str(meta.get("updated","?")))}<br>'
        f'現コミット: <code>{(cur[:9] if cur else "(git履歴なし)")}</code></p></div>'
    )

    rows = []
    for slug in deckmgr.list_clients():
        cfg, _ = _safe(deckmgr.load_client, slug)
        if not cfg:
            continue
        state = deckmgr._drift_state(cfg)
        sync_btn = (
            f'<a class="btn warnbtn" href="/sync?slug={slug}">追従</a>'
            if state.startswith("要追従") else ""
        )
        rows.append(
            f"<tr><td><strong>{html.escape(slug)}</strong></td>"
            f"<td>{html.escape(str(cfg.get('client_name','')))}</td>"
            f"<td>{html.escape(str(cfg.get('base_master_version','?')))}</td>"
            f"<td>{_badge(state)}</td>"
            f'<td><a class="btn" href="/build?slug={slug}">ビルド</a>'
            f'<a class="btn secondary" href="/preview?slug={slug}">プレビュー</a>'
            f"{sync_btn}</td></tr>"
        )
    table = (
        "<table><tr><th>slug</th><th>会社名</th><th>基準Ver</th><th>状態</th><th>操作</th></tr>"
        + ("".join(rows) or '<tr><td colspan="5" class="note">企業が未登録です。'
           '<code>python3 tools/deckmgr.py new &lt;slug&gt; --name "社名"</code> で追加できます。</td></tr>')
        + "</table>"
    )
    parts.append(f'<div class="card"><h2>提案先企業</h2>{table}</div>')

    # 新規企業の追加フォーム
    parts.append(
        '<div class="card"><h2>新規提案先企業を追加</h2>'
        '<form method="post" action="/new">'
        '<p><label>識別子 (slug)<br>'
        '<input name="slug" required pattern="[a-z0-9][a-z0-9-]*" '
        'placeholder="例: sony-corp" style="padding:8px;width:240px;"></label></p>'
        '<p class="note">英小文字・数字・ハイフンのみ</p>'
        '<p><label>会社名<br>'
        '<input name="name" required placeholder="例: ソニー株式会社" '
        'style="padding:8px;width:320px;"></label></p>'
        '<p><button class="btn" type="submit" style="border:0;cursor:pointer;">追加する</button></p>'
        '</form>'
        '<p class="note">追加後、<code>clients/&lt;slug&gt;/config.yaml</code> で変数や '
        'セクションの差し替え・削除・追加を設定してください。</p></div>'
    )
    return PAGE.format(body="".join(parts))


def preview_html(slug: str) -> str:
    deck, err = _safe(deckmgr.render_deck, slug)
    if err:
        body = f'<div class="card"><strong>エラー:</strong> {html.escape(err)}</div>'
    else:
        body = (
            f'<div class="card"><h2>プレビュー: {html.escape(slug)}</h2>'
            '<p class="note">合成された最終 Markdown です。実際のスライド表示は '
            f'<code>npx @marp-team/marp-cli -s build/</code> でブラウザ表示できます。</p>'
            f'<p><a class="btn secondary" href="/">← 一覧へ戻る</a></p>'
            f"<pre>{html.escape(deck)}</pre></div>"
        )
    return PAGE.format(body=body)


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        q = parse_qs(u.query)
        slug = (q.get("slug", [""])[0]).strip()
        if u.path == "/":
            self._send(dashboard_html())
        elif u.path == "/build" and slug:
            _, err = _safe(_build_one, slug)
            msg = f"ビルド失敗: {err}" if err else f"ビルド完了: build/{slug}/deck.md を生成しました"
            self._send(dashboard_html(msg))
        elif u.path == "/preview" and slug:
            self._send(preview_html(slug))
        elif u.path == "/sync" and slug:
            _, err = _safe(deckmgr.cmd_sync, Namespace(slug=slug))
            msg = (f"追従失敗: {err}" if err
                   else f"{slug} を最新マスターに追従済みとして記録しました")
            self._send(dashboard_html(msg))
        else:
            self._send(PAGE.format(body='<div class="card">ページが見つかりません。'
                                        '<a href="/">トップへ</a></div>'), 404)

    def do_POST(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0) or 0)
        form = parse_qs(self.rfile.read(length).decode("utf-8")) if length else {}
        if u.path == "/new":
            slug = (form.get("slug", [""])[0]).strip()
            name = (form.get("name", [""])[0]).strip()
            _, err = _safe(deckmgr.cmd_new, Namespace(slug=slug, name=name))
            msg = (f"作成失敗: {err}" if err
                   else f"企業 '{slug}' を作成しました（clients/{slug}/config.yaml）")
            self._send(dashboard_html(msg))
        else:
            self._send(PAGE.format(body='<div class="card">不正なリクエストです。'
                                        '<a href="/">トップへ</a></div>'), 404)

    def log_message(self, *_args) -> None:  # アクセスログを抑制
        pass


def _build_one(slug: str) -> None:
    out = deckmgr.render_deck(slug)
    dest = deckmgr.BUILD_DIR / slug / "deck.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="プレゼン資料管理 Web ダッシュボード")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"▶ ダッシュボードを起動しました: http://{args.host}:{args.port}")
    print("  停止するには Ctrl+C を押してください。")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました。")


if __name__ == "__main__":
    main()

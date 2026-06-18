#!/usr/bin/env python3
"""deckmgr — プレゼン資料バージョン管理 CLI

マスター資料 (master/deck.md) を起点に、提案先企業ごとのカスタマイズ版を
「変数置換 + セクション差し替え」で生成・管理する。Git と連携してマスター
更新の追従状況（ドリフト）も検出する。

使い方:
    python3 tools/deckmgr.py list
    python3 tools/deckmgr.py new acme --name "Acme 株式会社"
    python3 tools/deckmgr.py build acme        # build/acme/deck.md を生成
    python3 tools/deckmgr.py build --all
    python3 tools/deckmgr.py status acme
    python3 tools/deckmgr.py diff acme         # マスターの変更点を表示
    python3 tools/deckmgr.py sync acme         # 追従済みとして基準を更新
    python3 tools/deckmgr.py render acme        # Marp で HTML を出力（要 npx）

依存: なし（Python 3.9+ 標準ライブラリのみ）。レンダリングのみ Node/npx の marp-cli を使用。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# パス定義
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = ROOT / "master"
MASTER_DECK = MASTER_DIR / "deck.md"
MASTER_META = MASTER_DIR / "meta.yaml"
CLIENTS_DIR = ROOT / "clients"
BUILD_DIR = ROOT / "build"

SECTION_MARKER = re.compile(r"^<!--\s*@section:\s*([\w-]+)\s*-->\s*$")
VAR_PATTERN = re.compile(r"\{\{\s*([A-Z0-9_]+)\s*\}\}")
SLIDE_SEP = "\n\n---\n\n"


# ---------------------------------------------------------------------------
# 小物ユーティリティ
# ---------------------------------------------------------------------------
def _today() -> str:
    return _dt.date.today().isoformat()


def _die(msg: str) -> "None":
    sys.exit(f"エラー: {msg}")


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        _die(f"ファイルが見つかりません: {path}")
    return _yaml_load(path.read_text(encoding="utf-8")) or {}


def _dump_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_yaml_dump(data) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 最小 YAML 入出力（標準ライブラリのみ・本システムが使う範囲に特化）
#
# 対応する構文: マッピング / ブロックリスト(`- x`) / フローリスト(`[a, b]`) /
#   ネスト(インデント) / `'..'`・`".."` クォート / `#` コメント / 空リスト `[]`。
# 本システムの meta.yaml・config.yaml はこの範囲で完結する。複雑な YAML
# （アンカー・複数行スカラー等）は扱わない。
# ---------------------------------------------------------------------------
def _strip_inline_comment(line: str) -> str:
    """クォート外にある ` #` 以降をコメントとして除去する。"""
    in_s = in_d = False
    for idx, ch in enumerate(line):
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif ch == "#" and not in_s and not in_d and (idx == 0 or line[idx - 1] in " \t"):
            return line[:idx]
    return line


def _parse_scalar(s: str):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        body = s[1:-1]
        if s[0] == "'":
            return body.replace("''", "'")
        return body.replace('\\"', '"').replace("\\\\", "\\")
    if s == "" or s == "~" or s.lower() == "null":
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    # 数値・SHA・バージョン等の取り違えを避けるため、その他は文字列のまま扱う
    return s


def _parse_inline(s: str):
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(x) for x in inner.split(",")]
    return _parse_scalar(s)


def _yaml_load(text: str):
    rows: list[tuple[int, str]] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        line = _strip_inline_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        rows.append((indent, line.strip()))

    pos = [0]

    def parse_list(indent: int) -> list:
        items: list = []
        while pos[0] < len(rows):
            i, t = rows[pos[0]]
            if i != indent or not (t == "-" or t.startswith("- ")):
                break
            pos[0] += 1
            item = t[1:].strip() if t.startswith("- ") else ""
            items.append(_parse_inline(item) if item else None)
        return items

    def parse_map(indent: int) -> dict:
        d: dict = {}
        while pos[0] < len(rows):
            i, t = rows[pos[0]]
            if i != indent or t == "-" or t.startswith("- "):
                break
            key, sep, rest = t.partition(":")
            if not sep:
                pos[0] += 1
                continue
            key, rest = key.strip(), rest.strip()
            pos[0] += 1
            if rest:
                d[key] = _parse_inline(rest)
            elif pos[0] < len(rows):
                ni, nt = rows[pos[0]]
                if (nt == "-" or nt.startswith("- ")) and ni >= indent:
                    d[key] = parse_list(ni)
                elif ni > indent:
                    d[key] = parse_map(ni)
                else:
                    d[key] = None
            else:
                d[key] = None
        return d

    if not rows:
        return {}
    first = rows[0][1]
    return parse_list(rows[0][0]) if (first == "-" or first.startswith("- ")) else parse_map(rows[0][0])


_NUM_RE = re.compile(r"^[-+]?(\d+|\d*\.\d+)$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RESERVED = {"true", "false", "null", "yes", "no", "on", "off", "~"}


def _needs_quote(s: str) -> bool:
    if s == "":
        return True
    if _DATE_RE.match(s) or _NUM_RE.match(s) or s.lower() in _RESERVED:
        return True
    if s[0] in "-?:,[]{}#&*!|>'\"%@`":
        return True
    if ": " in s or s.endswith(":") or " #" in s or s.strip() != s:
        return True
    return False


def _fmt_scalar(v) -> str:
    if v is None:
        return "''"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if _needs_quote(s):
        return "'" + s.replace("'", "''") + "'"
    return s


def _yaml_dump(data, indent: int = 0) -> str:
    pad = "  " * indent
    lines: list[str] = []
    for k, v in data.items():
        if isinstance(v, dict):
            if v:
                lines.append(f"{pad}{k}:")
                lines.append(_yaml_dump(v, indent + 1))
            else:
                lines.append(f"{pad}{k}: {{}}")
        elif isinstance(v, list):
            if v:
                lines.append(f"{pad}{k}:")
                lines.extend(f"{pad}- {_fmt_scalar(item)}" for item in v)
            else:
                lines.append(f"{pad}{k}: []")
        else:
            lines.append(f"{pad}{k}: {_fmt_scalar(v)}")
    return "\n".join(lines)


def _git(*args: str) -> tuple[int, str]:
    """git コマンドを実行し (returncode, stdout) を返す。失敗しても例外は出さない。"""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(ROOT),
            capture_output=True, text=True,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        return 127, "git が見つかりません"


def _current_master_commit() -> str | None:
    """master/ を最後に変更したコミット SHA。git 履歴が無い場合は None。"""
    code, out = _git("log", "-1", "--format=%H", "--", "master/")
    sha = out.strip()
    if code == 0 and sha:
        return sha
    return None


# ---------------------------------------------------------------------------
# マスター / クライアントのモデル
# ---------------------------------------------------------------------------
def parse_deck(text: str) -> tuple[str, list[tuple[str, str]]]:
    """deck.md を (フロントマター, [(section_id, body), ...]) に分解する。

    body は前後の空白とスライド区切り `---` を除去した本文。
    """
    lines = text.splitlines()
    frontmatter = ""
    idx = 0
    # 先頭の YAML フロントマター (--- ... ---) を取り出す
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                frontmatter = "\n".join(lines[: j + 1])
                idx = j + 1
                break

    sections: list[tuple[str, str]] = []
    current_id: str | None = None
    buf: list[str] = []

    def flush() -> None:
        if current_id is not None:
            body = _strip_separators("\n".join(buf))
            sections.append((current_id, body))

    for line in lines[idx:]:
        m = SECTION_MARKER.match(line)
        if m:
            flush()
            current_id = m.group(1)
            buf = []
        elif current_id is not None:
            buf.append(line)
    flush()
    return frontmatter, sections


def _strip_separators(body: str) -> str:
    """本文の前後にある空白行と `---` 区切り行を除去する。"""
    lines = body.splitlines()
    while lines and (lines[0].strip() == "" or lines[0].strip() == "---"):
        lines.pop(0)
    while lines and (lines[-1].strip() == "" or lines[-1].strip() == "---"):
        lines.pop()
    return "\n".join(lines)


def client_dir(slug: str) -> Path:
    return CLIENTS_DIR / slug


def load_client(slug: str) -> dict:
    cfg = client_dir(slug) / "config.yaml"
    if not cfg.exists():
        _die(f"クライアントが見つかりません: {slug}  ('new' で作成してください)")
    return _load_yaml(cfg)


def list_clients() -> list[str]:
    if not CLIENTS_DIR.exists():
        return []
    return sorted(
        p.name for p in CLIENTS_DIR.iterdir()
        if p.is_dir() and (p / "config.yaml").exists()
    )


# ---------------------------------------------------------------------------
# ビルド
# ---------------------------------------------------------------------------
def render_deck(slug: str) -> str:
    """クライアント向けの最終 Markdown を組み立てて返す。"""
    meta = _load_yaml(MASTER_META)
    fm, master_sections = parse_deck(MASTER_DECK.read_text(encoding="utf-8"))
    master_map = dict(master_sections)
    master_order = [sid for sid, _ in master_sections]

    cfg = load_client(slug)
    cdir = client_dir(slug)

    # 変数のマージ（マスター既定値 + クライアント固有）
    variables = dict(meta.get("variables", {}))
    variables.update(cfg.get("variables", {}))

    remove = set(cfg.get("remove_sections", []) or [])
    overrides = cfg.get("override_sections", []) or []
    extras = cfg.get("extra_sections", []) or []

    def section_body(sid: str) -> str:
        """差し替えファイルがあればそれを、無ければマスターの本文を返す。"""
        ov = cdir / "sections" / f"{sid}.md"
        if ov.exists():
            return _strip_separators(ov.read_text(encoding="utf-8"))
        if sid in master_map:
            return master_map[sid]
        _die(f"セクション '{sid}' の本文が見つかりません（master にも差し替えにも無し）")

    blocks: list[str] = []
    for sid in master_order:
        if sid in remove:
            continue
        tag = " (差し替え)" if (sid in overrides or (cdir / "sections" / f"{sid}.md").exists()) else ""
        blocks.append(f"<!-- @section:{sid}{tag} -->\n\n{section_body(sid)}")

    # 追加セクション（マスターに無いクライアント固有スライド）
    for sid in extras:
        ov = cdir / "sections" / f"{sid}.md"
        if not ov.exists():
            _die(f"追加セクションのファイルが見つかりません: {ov}")
        blocks.append(
            f"<!-- @section:{sid} (追加) -->\n\n{_strip_separators(ov.read_text(encoding='utf-8'))}"
        )

    body = fm.strip() + "\n\n" + SLIDE_SEP.join(blocks) + "\n"

    # 変数置換（未定義変数は目印付きで残す）
    def repl(m: re.Match) -> str:
        key = m.group(1)
        return str(variables.get(key, f"⟪未定義:{key}⟫"))

    return VAR_PATTERN.sub(repl, body)


def cmd_build(args: argparse.Namespace) -> None:
    targets = list_clients() if args.all else [args.slug]
    if not targets:
        _die("ビルド対象がありません。'new' でクライアントを作成してください。")
    for slug in targets:
        out = render_deck(slug)
        dest = BUILD_DIR / slug / "deck.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(out, encoding="utf-8")
        undef = sorted(set(re.findall(r"⟪未定義:([A-Z0-9_]+)⟫", out)))
        warn = f"  ⚠ 未定義変数: {', '.join(undef)}" if undef else ""
        print(f"✓ ビルド: {dest.relative_to(ROOT)}{warn}")


def cmd_render(args: argparse.Namespace) -> None:
    cmd_build(argparse.Namespace(slug=args.slug, all=False))
    src = BUILD_DIR / args.slug / "deck.md"
    fmt = args.format
    dest = src.with_suffix(f".{fmt}")
    print(f"Marp でレンダリング中 ({fmt}) ...")
    proc = subprocess.run(
        ["npx", "--yes", "@marp-team/marp-cli", str(src), "-o", str(dest)],
        cwd=str(ROOT),
    )
    if proc.returncode == 0:
        print(f"✓ 出力: {dest.relative_to(ROOT)}")
    else:
        _die("Marp のレンダリングに失敗しました（Node/npx 環境を確認してください）。")


# ---------------------------------------------------------------------------
# 新規クライアント
# ---------------------------------------------------------------------------
def cmd_new(args: argparse.Namespace) -> None:
    slug = args.slug
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        _die("slug は英小文字・数字・ハイフンで指定してください（例: acme-corp）")
    cdir = client_dir(slug)
    if cdir.exists():
        _die(f"既に存在します: {cdir.relative_to(ROOT)}")
    meta = _load_yaml(MASTER_META)
    name = args.name or slug

    config = {
        "client_name": name,
        "slug": slug,
        "created": _today(),
        "base_master_version": meta.get("version", "0.0.0"),
        "base_commit": _current_master_commit() or "",
        "variables": {
            "CLIENT_NAME": name,
            **{k: v for k, v in meta.get("variables", {}).items() if k != "CLIENT_NAME"},
        },
        "override_sections": [],
        "remove_sections": [],
        "extra_sections": [],
        "notes": "",
    }
    _dump_yaml(cdir / "config.yaml", config)
    (cdir / "sections").mkdir(parents=True, exist_ok=True)
    (cdir / "sections" / ".gitkeep").write_text("", encoding="utf-8")
    (cdir / "assets").mkdir(parents=True, exist_ok=True)
    (cdir / "assets" / ".gitkeep").write_text("", encoding="utf-8")

    print(f"✓ クライアントを作成: {(cdir / 'config.yaml').relative_to(ROOT)}")
    print("  次の手順:")
    print(f"    1. config.yaml の variables を編集")
    print(f"    2. 差し替えたいセクションは clients/{slug}/sections/<id>.md を作成し")
    print(f"       config.yaml の override_sections に id を追記")
    print(f"    3. python3 tools/deckmgr.py build {slug}")


# ---------------------------------------------------------------------------
# 一覧 / 状態 / ドリフト
# ---------------------------------------------------------------------------
def _drift_state(cfg: dict) -> str:
    """クライアントの基準コミット以降にマスターが変わったか判定。"""
    base = cfg.get("base_commit") or ""
    if not base:
        return "不明(基準なし)"
    code, _ = _git("cat-file", "-e", base)
    if code != 0:
        return "不明(基準コミット無効)"
    code, out = _git("diff", "--name-only", base, "HEAD", "--", "master/")
    if code != 0:
        return "不明"
    return "要追従(マスター更新あり)" if out.strip() else "最新"


def cmd_list(args: argparse.Namespace) -> None:
    meta = _load_yaml(MASTER_META)
    print(f"■ マスター資料")
    print(f"    タイトル : {meta.get('title', '(未設定)')}")
    print(f"    バージョン: {meta.get('version', '?')}  (更新日 {meta.get('updated', '?')})")
    cur = _current_master_commit()
    print(f"    現コミット: {cur[:9] if cur else '(git履歴なし)'}")
    print()
    clients = list_clients()
    if not clients:
        print("■ クライアント: なし（'new' で作成してください）")
        return
    print(f"■ クライアント ({len(clients)} 件)")
    print(f"    {'slug':<16} {'会社名':<24} {'基準Ver':<10} {'状態'}")
    print(f"    {'-'*16} {'-'*24} {'-'*10} {'-'*20}")
    for slug in clients:
        cfg = load_client(slug)
        name = str(cfg.get("client_name", ""))
        ver = str(cfg.get("base_master_version", "?"))
        print(f"    {slug:<16} {name:<24} {ver:<10} {_drift_state(cfg)}")


def cmd_status(args: argparse.Namespace) -> None:
    slug = args.slug
    cfg = load_client(slug)
    meta = _load_yaml(MASTER_META)
    print(f"■ {cfg.get('client_name')} ({slug})")
    print(f"    作成日      : {cfg.get('created')}")
    print(f"    基準Ver     : {cfg.get('base_master_version')}  (現マスター {meta.get('version')})")
    print(f"    基準コミット: {(cfg.get('base_commit') or '(なし)')[:9]}")
    print(f"    ドリフト    : {_drift_state(cfg)}")
    print(f"    差し替え    : {cfg.get('override_sections') or '（なし）'}")
    print(f"    削除        : {cfg.get('remove_sections') or '（なし）'}")
    print(f"    追加        : {cfg.get('extra_sections') or '（なし）'}")
    if cfg.get("notes"):
        print(f"    メモ        : {cfg.get('notes')}")


def cmd_diff(args: argparse.Namespace) -> None:
    cfg = load_client(args.slug)
    base = cfg.get("base_commit") or ""
    if not base:
        _die("基準コミットが未設定です。一度コミットしてから 'sync' してください。")
    code, _ = _git("cat-file", "-e", base)
    if code != 0:
        _die("基準コミットが無効です。'sync' で更新してください。")
    print(f"■ {args.slug}: 基準 {base[:9]} → HEAD のマスター変更点\n")
    code, out = _git("diff", base, "HEAD", "--", "master/")
    print(out if out.strip() else "（マスターに変更はありません。最新の状態です）")


def cmd_sync(args: argparse.Namespace) -> None:
    slug = args.slug
    cfg = load_client(slug)
    meta = _load_yaml(MASTER_META)
    cur = _current_master_commit()
    if not cur:
        _die("git 履歴がありません。先にコミットしてください。")
    cfg["base_commit"] = cur
    cfg["base_master_version"] = meta.get("version", cfg.get("base_master_version"))
    cfg["synced"] = _today()
    _dump_yaml(client_dir(slug) / "config.yaml", cfg)
    print(f"✓ {slug} を最新マスター ({cur[:9]}, v{cfg['base_master_version']}) に追従済みとして記録しました。")
    print("  ※ sections/ の差し替え内容が最新マスターと整合しているか確認してください。")


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="deckmgr",
        description="プレゼン資料バージョン管理 CLI（マスター + 企業別カスタマイズ）",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("list", help="マスターと全クライアントの一覧・状態を表示")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("new", help="新規クライアント（提案先企業）を作成")
    sp.add_argument("slug", help="識別子（英小文字・数字・ハイフン）")
    sp.add_argument("--name", help="会社名（表示用）")
    sp.set_defaults(func=cmd_new)

    sp = sub.add_parser("build", help="クライアント向け最終資料を生成")
    sp.add_argument("slug", nargs="?", help="対象 slug")
    sp.add_argument("--all", action="store_true", help="全クライアントをビルド")
    sp.set_defaults(func=cmd_build)

    sp = sub.add_parser("render", help="Marp で HTML/PDF/PPTX に変換（要 npx）")
    sp.add_argument("slug", help="対象 slug")
    sp.add_argument("--format", default="html", choices=["html", "pdf", "pptx"], help="出力形式")
    sp.set_defaults(func=cmd_render)

    sp = sub.add_parser("status", help="クライアントの詳細状態を表示")
    sp.add_argument("slug")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("diff", help="基準以降のマスター変更点を表示")
    sp.add_argument("slug")
    sp.set_defaults(func=cmd_diff)

    sp = sub.add_parser("sync", help="現マスターに追従済みとして基準を更新")
    sp.add_argument("slug")
    sp.set_defaults(func=cmd_sync)

    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if getattr(args, "command", None) == "build" and not args.all and not args.slug:
        _die("slug を指定するか --all を付けてください。")
    args.func(args)


if __name__ == "__main__":
    main()

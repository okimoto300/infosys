# プレゼン資料バージョン管理システム

GitHub（Git）を使って、**マスター資料**を一元管理しつつ、**提案先企業ごとに
カスタマイズしたバージョン**を効率的に管理するためのシステムです。

プレゼン資料を Markdown（[Marp](https://marp.app/) 形式）でテキスト管理する
ことで、Git 本来の強み（差分表示・履歴・レビュー・ブランチ）をそのまま資料の
バージョン管理に活かせます。

---

## 解決する課題

提案資料の運用では、こんな問題が起こりがちです。

- マスター資料を更新したが、各社向けにコピーした資料に反映漏れがある
- 「A社向け_最新_最終_v3.pptx」のようなファイルが乱立し、どれが正か分からない
- 各社向けにどこをカスタマイズしたのか、差分が追えない

このシステムは **「マスター資料」+「企業ごとの差分」** という構造で管理し、
最終資料は毎回プログラムで自動生成します。これにより、

- マスターを直せば全社の資料へ反映可能（追従漏れを検出）
- 企業ごとのカスタマイズ箇所が一目で分かる
- 履歴・差分・レビューはすべて GitHub 上で完結

---

## 全体構成

```
infosys/
├── master/                  # ★マスター資料（全社共通の原本）
│   ├── deck.md              #   Marp 形式のスライド本体
│   ├── meta.yaml            #   バージョン・共通変数・セクション定義
│   └── assets/              #   共通画像など
├── clients/                 # ★提案先企業ごとのカスタマイズ
│   └── acme-corp/
│       ├── config.yaml      #   企業固有の変数・差し替え/削除/追加の指定
│       ├── sections/        #   差し替え・追加するスライド本文
│       └── assets/          #   企業固有の画像
├── tools/
│   └── deckmgr.py           # ★管理用 CLI
├── build/                   # 生成された最終資料（自動生成・Git管理外）
├── .github/workflows/       # push 時に自動ビルドする GitHub Actions
└── docs/                    # 運用フロー・設計ドキュメント
```

最終資料は `master` と `clients/<企業>` を合成して `build/<企業>/deck.md` に
生成されます（`build/` は Git 管理対象外。常に再生成可能）。

---

## カスタマイズの3つの方法

`clients/<企業>/config.yaml` で、マスターに対する差分を宣言的に指定します。

| 方法           | 設定                    | 用途                                       |
| -------------- | ----------------------- | ------------------------------------------ |
| **変数置換**   | `variables`             | 会社名・案件名・担当者など `{{変数}}` の置換 |
| **セクション差し替え** | `override_sections` | 特定スライドを企業向け内容に置き換える       |
| **セクション削除** | `remove_sections`   | 不要なスライド（例: 標準価格）を除外する     |
| **セクション追加** | `extra_sections`    | 企業専用のスライド（事例など）を追加する     |

---

## 起動方法（Web ダッシュボード）

ブラウザから一覧確認・ビルド・プレビューを行える管理画面をワンコマンドで起動できます（追加の依存なし）。

> **注意:** ダッシュボードは「サーバーを起動したマシン」上で動作します。`http://localhost:8080` は、そのコマンドを実行した PC のブラウザからのみ開けます。リモート環境（クラウド上の開発コンテナ等）で起動した場合、手元の PC のブラウザからは到達できないため、**手元の PC でクローンして起動してください**。

```bash
python3 tools/server.py            # http://localhost:8080 で起動
python3 tools/server.py --port 9000 # ポートを変更する場合
```

起動後、ブラウザで `http://localhost:8080` を開くと、以下の操作が画面から行えます。停止は `Ctrl+C`。

- マスターのバージョン・各企業の追従状態（「最新」/「要追従」バッジ）を一覧表示
- **ビルド** / **プレビュー** ボタンで最終資料を生成・確認
- **追従** ボタン（「要追従」の企業のみ表示）で最新マスターへ sync
- **新規提案先企業の追加フォーム**（slug・会社名を入力して作成）

実際のスライド（HTML）として表示・配布したい場合は Marp を使います（要 Node.js）。

```bash
python3 tools/deckmgr.py build acme-corp
npx --yes @marp-team/marp-cli -s build/acme-corp/   # http://localhost:8080 でライブプレビュー
```

---

## クイックスタート（CLI）

```bash
# 1. 全体の状態を確認
python3 tools/deckmgr.py list

# 2. 新しい提案先企業を追加
python3 tools/deckmgr.py new acme-corp --name "Acme 株式会社"

# 3. clients/acme-corp/config.yaml を編集（変数や差し替え指定）
#    差し替え・追加スライドは clients/acme-corp/sections/<id>.md に作成

# 4. 最終資料を生成
python3 tools/deckmgr.py build acme-corp
#   → build/acme-corp/deck.md

# 5. （任意）HTML / PDF / PPTX に変換（Node/npx が必要）
python3 tools/deckmgr.py render acme-corp --format html
```

---

## マスター更新への追従（ドリフト管理）

マスター資料を更新すると、各企業版が「古いマスターを基にしている」状態に
なります。これを検出・追従するのが本システムの肝です。

```bash
# マスター更新後、どの企業版が追従が必要か一覧表示
python3 tools/deckmgr.py list
#   状態列に「要追従(マスター更新あり)」と表示される

# 何が変わったかを確認（基準コミット以降のマスター差分）
python3 tools/deckmgr.py diff acme-corp

# 差し替えスライドを必要に応じて更新したら、追従済みとして記録
python3 tools/deckmgr.py sync acme-corp
```

各企業の `config.yaml` には基準とした**マスターのコミット**が記録されており、
それ以降にマスターが変更されると `list` / `status` で「要追従」と表示されます。

---

## GitHub での運用

- **ブランチ / プルリクエスト**: 企業向けカスタマイズや大きなマスター改訂は
  ブランチを切って PR でレビュー → マージ。差分が GitHub 上で確認できます。
- **GitHub Actions**: `master/` や `clients/` を push すると自動で全企業の資料を
  ビルドし、HTML をビルド成果物（Artifacts）として保存します。
- **タグ / リリース**: マスターの版（`meta.yaml` の `version`）に合わせて Git タグを
  打てば、提案時点の資料を後から正確に再現できます。

詳しい運用手順は [`docs/WORKFLOW.md`](docs/WORKFLOW.md) を参照してください。

---

## コマンド一覧

| コマンド                          | 説明                                   |
| --------------------------------- | -------------------------------------- |
| `deckmgr list`                    | マスターと全企業の状態を一覧表示       |
| `deckmgr new <slug> --name "社名"` | 新規提案先企業を作成                   |
| `deckmgr build <slug>` / `--all`  | 最終資料 (Markdown) を生成             |
| `deckmgr render <slug> --format html` | Marp で HTML/PDF/PPTX に変換       |
| `deckmgr status <slug>`           | 1企業の詳細状態を表示                  |
| `deckmgr diff <slug>`             | 基準以降のマスター変更点を表示         |
| `deckmgr sync <slug>`             | 現マスターへ追従済みとして基準を更新   |

---

## GitHub Pages での公開

全企業の資料を HTML 化し、インデックスページ付きで GitHub Pages に自動公開できます。
URL を共有するだけで、関係者がブラウザだけで資料を閲覧できます（手元に Python 環境は不要）。

仕組み: `.github/workflows/pages.yml` が push 時に以下を実行します。

1. 全企業の資料をビルド（`deckmgr build --all`）
2. 各企業を Marp で HTML 化 → `site/<slug>/index.html`
3. 企業一覧のインデックスを生成（`tools/gen_index.py`）→ `site/index.html`
4. GitHub Pages へデプロイ

公開後の URL 構成:

```
https://<owner>.github.io/<repo>/            # 企業一覧（インデックス）
https://<owner>.github.io/<repo>/acme-corp/  # 各企業のスライド
```

### 初回セットアップ

1. リポジトリの **Settings → Pages → Build and deployment → Source** を **GitHub Actions** に設定
   （ワークフローの `configure-pages` が自動有効化を試みますが、組織設定によっては手動が必要）。
2. 公開対象ブランチをワークフローの `on.push.branches` に含める
   （既定では作業ブランチと `main`）。
3. `github-pages` 環境のデプロイ許可ブランチに、公開元ブランチが含まれていることを確認。

手元で公開内容を事前確認する場合:

```bash
python3 tools/deckmgr.py build --all
for d in build/*/; do s=$(basename "$d"); mkdir -p "site/$s"; \
  npx --yes @marp-team/marp-cli "build/$s/deck.md" --html -o "site/$s/index.html"; done
python3 tools/gen_index.py --out site
# site/index.html をブラウザで開く
```

---

## 必要環境

- Python 3.9+（`pyyaml`）
- レンダリングのみ Node.js（`npx @marp-team/marp-cli`）

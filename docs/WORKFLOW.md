# 運用フロー

本システムを GitHub 上で実際に運用するための手順をまとめます。

## 登場人物と役割

- **資料オーナー**: マスター資料（`master/`）を管理する人。全社共通の内容・
  バージョンに責任を持つ。
- **営業担当**: 提案先企業ごとのカスタマイズ（`clients/<企業>/`）を行う人。

---

## 1. マスター資料の作成・更新

1. `master/deck.md` を Marp 形式で編集する。
   - スライドは `---` で区切る。
   - 各スライド（または塊）の先頭に `<!-- @section:ID -->` を付ける。
     この ID が差し替え・削除・並び順の基準になる。
   - 会社名など可変部分は `{{CLIENT_NAME}}` のように変数化する。
2. 変数の既定値・セクション一覧・バージョンは `master/meta.yaml` で管理する。
3. 大きな改訂をしたら `meta.yaml` の `version` を上げる（例: 1.0.0 → 1.1.0）。
4. ブランチを切って PR を作成し、レビュー後に main へマージする。
5. 必要に応じて Git タグを打つ（例: `git tag deck-v1.1.0`）。

---

## 2. 提案先企業を追加する

```bash
python3 tools/deckmgr.py new acme-corp --name "Acme 株式会社"
```

`clients/acme-corp/` が作成されるので、`config.yaml` を編集する。

```yaml
variables:
  CLIENT_NAME: Acme 株式会社
  PROJECT_NAME: 次世代EC基盤 構築プロジェクト
  PRESENTER: 沖本 隆一郎
override_sections: [solution]   # solution スライドを差し替える
remove_sections: [pricing]      # 標準価格スライドを除外する
extra_sections: [case-study]    # 事例スライドを追加する
```

- **差し替え / 追加**するスライドは `clients/acme-corp/sections/<id>.md` に本文を
  書く（`<!-- @section -->` マーカーや `---` 区切りは不要）。
- ビルドして確認:

```bash
python3 tools/deckmgr.py build acme-corp
```

---

## 3. マスター更新を各企業版へ反映する（追従）

マスターを更新すると、それ以前に作った企業版は「古い基準」のままになる。

```bash
# 1. 追従が必要な企業を洗い出す
python3 tools/deckmgr.py list
#    → 状態が「要追従(マスター更新あり)」の企業を確認

# 2. マスターの変更内容を確認
python3 tools/deckmgr.py diff acme-corp

# 3. 差し替え済みスライド（sections/*.md）が変更と矛盾しないか確認・修正

# 4. 再ビルドして内容を確認
python3 tools/deckmgr.py build acme-corp

# 5. 追従済みとして基準コミットを更新
python3 tools/deckmgr.py sync acme-corp
```

> ポイント: `override_sections` で差し替えていないスライドは、再ビルドするだけで
> マスターの最新内容が自動的に反映される。注意が必要なのは「差し替え済みの
> スライド」だけ。`diff` でマスター変更を見て、矛盾があれば手当てする。

---

## 4. ブランチ戦略の推奨

| 対象               | ブランチ例                  |
| ------------------ | --------------------------- |
| マスター改訂       | `master/update-pricing`     |
| 企業向けカスタマイズ | `client/acme-corp`          |

- 企業ごとに作業ブランチを分けると、提案直前まで安全に編集・レビューできる。
- PR の差分で「マスターからどこを変えたか」がレビュアーに明確に伝わる。

---

## 5. 提案時点の資料を再現する

「3か月前に Acme 社へ提案した資料」を再現したい場合:

```bash
git checkout <当時のコミット or タグ>
python3 tools/deckmgr.py build acme-corp
```

Git 履歴がそのまま資料のスナップショットになるため、いつでも正確に復元できる。

---

## バイナリ資料（PowerPoint 等）の扱い

既存の `.pptx` をそのまま管理したい場合も Git に置けるが、バイナリは差分が
取れないため**履歴の保存**が主目的になる。テキスト差分の恩恵（マスター追従・
レビュー）を最大化するには、本システムのように Markdown 化するのが望ましい。
画像・図版・既存 pptx は `assets/` に置いて参照する運用を推奨する。

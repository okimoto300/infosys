# 出席管理システム

Flask 製のシンプルな出席管理 Web アプリケーションです。
データは `data/` ディレクトリ内の JSON ファイルに保存されます。

## 機能

- **メンバー管理** — メンバーの追加・削除
- **出席登録** — 日付ごとに「出席 / 欠席 / 遅刻 / 公欠」を記録
- **集計** — メンバーごとの各ステータス回数と出席率を表示

出席率は `(出席 + 遅刻) ÷ 合計記録数` で計算します。

## セットアップ

```bash
# 依存ライブラリのインストール
pip install -r requirements.txt

# 起動
python app.py
```

起動後、ブラウザで http://localhost:5000 を開いてください。

## データの保存先

| ファイル | 内容 |
| --- | --- |
| `data/members.json` | 登録メンバー（id, name） |
| `data/attendance.json` | 出席記録（date, member_id, status） |

これらのファイルはアプリ起動時に自動作成されます。
個人データを含むため `.gitignore` で除外しています。

## 構成

```
.
├── app.py              # Flask アプリ本体
├── requirements.txt    # 依存ライブラリ
├── templates/          # HTML テンプレート
│   ├── base.html
│   ├── index.html      # 出席登録画面
│   └── summary.html    # 集計画面
├── static/
│   └── style.css       # スタイルシート
└── data/               # JSON データ（自動生成）
```

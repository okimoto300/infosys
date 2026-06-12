# =============================================================
#  前日（昨日）に更新されたファイルの一覧と内容を出力するプログラム
#
#  ・指定フォルダを「サブフォルダも含めて」探します
#  ・昨日（カレンダー上の前日 0:00〜23:59）に更新されたファイルを見つけます
#  ・各ファイルの「名前・更新時刻・サイズ」と「最初の数行」を表示します
#
#  使い方（PowerShell で）:
#     .\前日更新ファイル一覧.ps1
#  別のフォルダを調べたいときは -Folder で指定:
#     .\前日更新ファイル一覧.ps1 -Folder "C:\Users\あなた\Documents"
# =============================================================

# ---- 設定（ここを変えれば動きを調整できます）-------------------
param(
    # 調べる対象のフォルダ。指定しなければ「今いるフォルダ」を使う
    [string]$Folder = (Get-Location).Path,

    # 内容を何行プレビュー表示するか
    [int]$PreviewLines = 5
)

# ---- ① 「昨日」の範囲を計算する --------------------------------
# 今日の0時0分を求め、そこから1日引くと「昨日の0時0分」になる
$today      = (Get-Date).Date          # 例: 2026/06/12 00:00:00
$startOfDay = $today.AddDays(-1)        # 昨日の 00:00:00
$endOfDay   = $today                    # 今日の 00:00:00（＝昨日の終わり）

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " 対象フォルダ : $Folder"
Write-Host " 対象の日付   : $($startOfDay.ToString('yyyy/MM/dd')) に更新されたファイル"
Write-Host "==================================================" -ForegroundColor Cyan

# ---- ② 条件に合うファイルを探す --------------------------------
# Get-ChildItem … ファイル一覧を取得する命令
#   -Recurse … サブフォルダも含める
#   -File    … フォルダではなくファイルだけ
# Where-Object … 条件でしぼり込む（更新時刻が昨日の範囲内のもの）
$files = Get-ChildItem -Path $Folder -Recurse -File -ErrorAction SilentlyContinue |
         Where-Object { $_.LastWriteTime -ge $startOfDay -and $_.LastWriteTime -lt $endOfDay } |
         Sort-Object LastWriteTime

# ---- ③ 結果を表示する ------------------------------------------
if ($files.Count -eq 0) {
    # 1件も見つからなかったとき
    Write-Host ""
    Write-Host "昨日更新されたファイルは見つかりませんでした。" -ForegroundColor Yellow
    return
}

Write-Host ""
Write-Host "$($files.Count) 件のファイルが見つかりました。" -ForegroundColor Green

# 見つかったファイルを1つずつ処理する（foreach = それぞれについて繰り返す）
foreach ($file in $files) {
    Write-Host ""
    Write-Host "--------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "ファイル : $($file.FullName)"
    Write-Host "更新時刻 : $($file.LastWriteTime.ToString('yyyy/MM/dd HH:mm:ss'))"
    Write-Host "サイズ   : $([math]::Round($file.Length / 1KB, 1)) KB"
    Write-Host "[ 内容のプレビュー（最初の $PreviewLines 行）]" -ForegroundColor Cyan

    # ファイルの中身を最初の数行だけ読む
    # try/catch … 画像など文字として読めないファイルでエラーにならないようにする
    try {
        $preview = Get-Content -Path $file.FullName -TotalCount $PreviewLines -ErrorAction Stop
        if ($preview) {
            $preview | ForEach-Object { Write-Host "    $_" }
        } else {
            Write-Host "    （中身が空のファイルです）" -ForegroundColor DarkGray
        }
    }
    catch {
        Write-Host "    （内容を読み取れませんでした。画像などのファイルかもしれません）" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " 完了しました。" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan

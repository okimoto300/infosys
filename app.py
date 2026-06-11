"""出席管理 Web アプリケーション.

Flask を用いたシンプルな出席管理システム。
データは data/ ディレクトリ内の JSON ファイルに保存する。
"""

import json
import os
from datetime import date

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

app = Flask(__name__)
app.secret_key = "attendance-management-secret-key"

# --- データファイルのパス ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MEMBERS_FILE = os.path.join(DATA_DIR, "members.json")
ATTENDANCE_FILE = os.path.join(DATA_DIR, "attendance.json")

# 出席ステータスの定義
STATUSES = {
    "present": "出席",
    "absent": "欠席",
    "late": "遅刻",
    "excused": "公欠",
}


def _ensure_data_files():
    """データディレクトリとファイルが存在しない場合は初期化する。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(MEMBERS_FILE):
        _write_json(MEMBERS_FILE, [])
    if not os.path.exists(ATTENDANCE_FILE):
        _write_json(ATTENDANCE_FILE, [])


def _read_json(path):
    """JSON ファイルを読み込む。存在しない/壊れている場合は空リストを返す。"""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _write_json(path, data):
    """データを JSON ファイルへ整形して書き込む。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_members():
    return _read_json(MEMBERS_FILE)


def save_members(members):
    _write_json(MEMBERS_FILE, members)


def load_attendance():
    return _read_json(ATTENDANCE_FILE)


def save_attendance(records):
    _write_json(ATTENDANCE_FILE, records)


def next_member_id(members):
    """既存メンバーから次に割り当てる ID を求める。"""
    if not members:
        return 1
    return max(m["id"] for m in members) + 1


@app.route("/")
def index():
    """ホーム画面: メンバー一覧と本日の出席状況を表示。"""
    members = load_members()
    today = date.today().isoformat()
    selected_date = request.args.get("date", today)

    records = load_attendance()
    # 選択日の記録を member_id -> status の辞書にする
    day_records = {
        r["member_id"]: r["status"]
        for r in records
        if r["date"] == selected_date
    }

    return render_template(
        "index.html",
        members=members,
        statuses=STATUSES,
        selected_date=selected_date,
        day_records=day_records,
        today=today,
    )


@app.route("/members/add", methods=["POST"])
def add_member():
    """メンバーを追加する。"""
    name = request.form.get("name", "").strip()
    if not name:
        flash("名前を入力してください。", "error")
        return redirect(url_for("index"))

    members = load_members()
    if any(m["name"] == name for m in members):
        flash(f"「{name}」は既に登録されています。", "error")
        return redirect(url_for("index"))

    members.append({"id": next_member_id(members), "name": name})
    save_members(members)
    flash(f"「{name}」を追加しました。", "success")
    return redirect(url_for("index"))


@app.route("/members/<int:member_id>/delete", methods=["POST"])
def delete_member(member_id):
    """メンバーと、その出席記録を削除する。"""
    members = load_members()
    members = [m for m in members if m["id"] != member_id]
    save_members(members)

    records = load_attendance()
    records = [r for r in records if r["member_id"] != member_id]
    save_attendance(records)

    flash("メンバーを削除しました。", "success")
    return redirect(url_for("index"))


@app.route("/attendance/save", methods=["POST"])
def save_day_attendance():
    """選択日の出席状況をまとめて保存する。"""
    selected_date = request.form.get("date", date.today().isoformat())
    members = load_members()
    records = load_attendance()

    # 対象日の既存記録を一旦取り除く
    records = [r for r in records if r["date"] != selected_date]

    for member in members:
        status = request.form.get(f"status_{member['id']}")
        if status in STATUSES:
            records.append(
                {
                    "date": selected_date,
                    "member_id": member["id"],
                    "status": status,
                }
            )

    save_attendance(records)
    flash(f"{selected_date} の出席状況を保存しました。", "success")
    return redirect(url_for("index", date=selected_date))


@app.route("/summary")
def summary():
    """メンバーごとの出席状況を集計して表示する。"""
    members = load_members()
    records = load_attendance()

    # member_id -> {status: count}
    stats = {
        m["id"]: {key: 0 for key in STATUSES}
        for m in members
    }
    for r in records:
        if r["member_id"] in stats and r["status"] in STATUSES:
            stats[r["member_id"]][r["status"]] += 1

    summary_rows = []
    for m in members:
        counts = stats[m["id"]]
        total = sum(counts.values())
        present_like = counts["present"] + counts["late"]
        rate = round(present_like / total * 100, 1) if total else 0.0
        summary_rows.append(
            {
                "name": m["name"],
                "counts": counts,
                "total": total,
                "rate": rate,
            }
        )

    return render_template(
        "summary.html",
        rows=summary_rows,
        statuses=STATUSES,
    )


if __name__ == "__main__":
    _ensure_data_files()
    app.run(host="0.0.0.0", port=5000, debug=True)

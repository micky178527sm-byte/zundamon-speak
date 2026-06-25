#!/usr/bin/env python3
"""通知トリガー: macOS 通知センターに来た通知を読み上げる。

通知センターの SQLite DB をポーリングし、新着レコードを発話する。
switches/notify が無ければ何もしない。
config.env: NOTIFY_POLL_SEC / NOTIFY_READ_BODY / NOTIFY_MAXLEN / NOTIFY_DENY / NOTIFY_ALLOW

【重要】この DB の読み取りには「フルディスクアクセス(FDA)」が必要。
  システム設定 > プライバシーとセキュリティ > フルディスクアクセス に
  /usr/bin/python3 を追加すること。未許可なら静かにログだけ出して待機する。
"""
from __future__ import annotations

import os
import plistlib
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import ZundaSpeaker, _b, _i, _s  # noqa: E402
import phrases  # noqa: E402

SWITCH = "notify"
DB = Path.home() / "Library/Group Containers/group.com.apple.usernoted/db2/db"

# よく来るアプリの読みやすい日本語名(無ければバンドルID末尾)
APP_NAMES = {
    "com.apple.MobileSMS": "メッセージ",
    "com.apple.iChat": "メッセージ",
    "com.apple.mail": "メール",
    "com.apple.iCal": "カレンダー",
    "com.apple.reminders": "リマインダー",
    "com.apple.facetime": "フェイスタイム",
    "com.tinyspeck.slackmacgap": "スラック",
    "com.hnc.Discord": "ディスコード",
    "com.apple.news": "ニュース",
    "ru.keepcoder.Telegram": "テレグラム",
    "net.whatsapp.WhatsApp": "ワッツアップ",
    "com.google.Chrome": "クローム",
}


def app_name(bundle: str) -> str:
    if not bundle:
        return ""
    if bundle in APP_NAMES:
        return APP_NAMES[bundle]
    return bundle.rsplit(".", 1)[-1]


def extract(blob):
    """通知 data(バイナリ plist) から (bundle, title, subtitle, body)。"""
    try:
        pl = plistlib.loads(blob)
    except Exception:
        return "", "", "", ""
    req = pl.get("req", pl) if isinstance(pl, dict) else {}
    if not isinstance(req, dict):
        req = {}
    bundle = req.get("app") or (pl.get("app") if isinstance(pl, dict) else "") or ""
    return (str(bundle), str(req.get("titl") or ""),
            str(req.get("subt") or ""), str(req.get("body") or ""))


def connect():
    # mode=ro だと WAL の最新フレームを読めず(write権限が無いと WAL を無視して
    # チェックポイント済みの古い状態を返す)、到着直後の通知を取りこぼす。
    # mode=rw で開いて WAL/shm を正しく読み、PRAGMA query_only=1 で書き込みは封じる
    # (DB を一切変更しない=macOS の通知DBに影響を与えない)。
    con = sqlite3.connect(f"file:{DB}?mode=rw", uri=True, timeout=2.0)
    con.execute("PRAGMA query_only=1")
    return con


def fetch_new(con, last_id):
    rows = con.execute(
        "SELECT r.rec_id, a.identifier, r.data "
        "FROM record r LEFT JOIN app a ON r.app_id = a.app_id "
        "WHERE r.rec_id > ? ORDER BY r.rec_id ASC", (last_id,)).fetchall()
    return rows


def main() -> None:
    sp = ZundaSpeaker()
    if not DB.exists():
        print(f"[notify] DB not found: {DB} (macOS版差異?) — 待機", flush=True)

    last_id = 0
    primed = False
    fda_warned = False

    while True:
        try:
            sp.cfg = type(sp.cfg)()
            poll = _i("NOTIFY_POLL_SEC", 3)
            read_body = _b("NOTIFY_READ_BODY", False)
            maxlen = _i("NOTIFY_MAXLEN", 70)
            deny = [d.strip().lower() for d in _s("NOTIFY_DENY", "").split(",") if d.strip()]
            allow = [a.strip().lower() for a in _s("NOTIFY_ALLOW", "").split(",") if a.strip()]

            con = connect()
            try:
                if not primed:  # 起動時の既存通知は読み上げない
                    r = con.execute("SELECT MAX(rec_id) FROM record").fetchone()
                    last_id = (r[0] or 0) if r else 0
                    cnt = con.execute("SELECT COUNT(*) FROM record").fetchone()[0]
                    primed = True
                    print(f"[notify] 監視開始: 既存{cnt}件 max_rec_id={last_id} "
                          f"(以降の新着を読み上げる)", flush=True)
                else:
                    rows = fetch_new(con, last_id)
                    if rows:
                        print(f"[notify] 新着 {len(rows)} 件検出", flush=True)
                    for rec_id, bundle, blob in rows:
                        last_id = rec_id
                        if blob is None:
                            continue
                        b, title, subt, body = extract(blob)
                        bundle = (bundle or b or "")
                        name = app_name(bundle)
                        hay = f"{bundle} {name}".lower()
                        if deny and any(d in hay for d in deny):
                            continue
                        if allow and not any(a in hay for a in allow):
                            continue
                        ttl = title if not subt else f"{title} {subt}".strip()
                        say_body = body if read_body else ""
                        text = phrases.notify(name, ttl[:maxlen], say_body[:maxlen])
                        if text:
                            print(f"[notify] 読上 rec_id={rec_id} app={name}", flush=True)
                            sp.speak(text, switch=SWITCH)
            finally:
                con.close()
            fda_warned = False
        except sqlite3.DatabaseError as e:
            # OperationalError(open不可) と "authorization denied" の両方を一度だけ警告
            if not fda_warned:
                print(f"[notify] DB を読めない(フルディスクアクセス未許可?): {e}", flush=True)
                fda_warned = True
        except Exception as e:
            print(f"[notify] err: {e}", flush=True)
        time.sleep(max(1, poll))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""地震情報トリガー(事後): Wolfx の JMA 地震リストをポーリングして読み上げる。

EEW(揺れる前)とは別。揺れた後の「震源・震度情報」を伝える。
データ源: Wolfx Open API https://api.wolfx.jp/jma_eqlist.json (APIキー不要・無料)。
取得は macOS 標準 curl 経由。switches/quake が無ければ何もしない。

config.env: QUAKE_POLL_SEC / QUAKE_MIN_SHINDO
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import ZundaSpeaker, _i, _s  # noqa: E402

SWITCH = "quake"
URL = "https://api.wolfx.jp/jma_eqlist.json"
ORDER = ["1", "2", "3", "4", "5弱", "5強", "6弱", "6強", "7"]


def norm_shindo(s: str) -> str:
    s = (s or "").strip()
    return {"5-": "5弱", "5+": "5強", "6-": "6弱", "6+": "6強"}.get(s, s)


def rank(s: str) -> int:
    s = norm_shindo(s)
    return ORDER.index(s) if s in ORDER else -1


def fetch():
    try:
        out = subprocess.run(
            ["/usr/bin/curl", "-s", "--max-time", "12", "-A", "curl/8", URL],
            capture_output=True, text=True, timeout=15).stdout
        return json.loads(out) if out.strip() else None
    except Exception:
        return None


def newest_entries(data: dict):
    """No1, No2... を新しい順に (eventid, dict) で返す。"""
    items = []
    for k, v in (data or {}).items():
        if k.startswith("No") and isinstance(v, dict):
            try:
                items.append((int(k[2:]), v))
            except ValueError:
                pass
    items.sort(key=lambda x: x[0])  # No1=最新
    return [v for _, v in items]


def build_text(e: dict, min_rank: int):
    sh = norm_shindo(str(e.get("shindo", "")))
    if rank(sh) < min_rank:
        return None
    loc = e.get("location", "震源不明")
    mag = e.get("magnitude", "")
    parts = [f"地震情報。{loc}で最大震度{sh}"]
    if mag:
        parts.append(f"マグニチュード{mag}")
    text = "、".join(parts) + "なのだ"
    info = str(e.get("info", ""))
    if "心配はありません" in info or "心配はない" in info:
        text += "。津波の心配はないのだ"
    elif "津波" in info:
        text += "。津波に注意なのだ"
    return text


def main() -> None:
    sp = ZundaSpeaker()
    seen = set()
    primed = False

    while True:
        try:
            sp.cfg = type(sp.cfg)()
            if not (Path(__file__).resolve().parent.parent / "switches" / SWITCH).exists():
                time.sleep(5)
                continue
            poll = _i("QUAKE_POLL_SEC", 60)
            min_rank = rank(_s("QUAKE_MIN_SHINDO", "1"))
            if min_rank < 0:
                min_rank = 0

            data = fetch()
            if data:
                entries = newest_entries(data)
                if not primed:  # 初回は既存を既読化(過去分を読み上げない)
                    for e in entries:
                        seen.add(e.get("EventID"))
                    primed = True
                    print(f"[quake] 監視開始: 既存{len(entries)}件を既読化", flush=True)
                else:
                    # 古い順に処理して時系列で読み上げる
                    for e in reversed(entries):
                        eid = e.get("EventID")
                        if eid in seen:
                            continue
                        seen.add(eid)
                        text = build_text(e, min_rank)
                        if text:
                            print(f"[quake] 読上 {eid} {e.get('location')} 震度{e.get('shindo')}",
                                  flush=True)
                            sp.speak(text, switch=SWITCH)
                    if len(seen) > 200:
                        seen = set(list(seen)[-100:])
        except Exception as e:
            print(f"[quake] err: {e}", flush=True)
        time.sleep(max(15, poll))


if __name__ == "__main__":
    main()

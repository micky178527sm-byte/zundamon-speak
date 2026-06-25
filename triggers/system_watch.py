#!/usr/bin/env python3
"""電源/システムトリガー: 充電の開始/終了・低バッテリー・(任意)アプリ起動。

switches/power が無ければ何もしない。
config.env: POWER_WATCH / POWER_LOW_PCT / POWER_POLL_SEC / APP_WATCH / APP_POLL_SEC

権限不要(pmset と ps を読むだけ)。
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import ZundaSpeaker, _b, _i, _s  # noqa: E402
import phrases  # noqa: E402

SWITCH = "power"
APP_RE = re.compile(r"/([^/]+)\.app/Contents/MacOS/")
PCT_RE = re.compile(r"(\d+)%")


def power_state():
    """(on_ac: bool|None, pct: int|None) を返す。"""
    try:
        out = subprocess.run(["/usr/bin/pmset", "-g", "batt"],
                             capture_output=True, text=True, timeout=8).stdout
    except Exception:
        return None, None
    on_ac = None
    if "'AC Power'" in out:
        on_ac = True
    elif "'Battery Power'" in out:
        on_ac = False
    m = PCT_RE.search(out)
    pct = int(m.group(1)) if m else None
    return on_ac, pct


def running_apps():
    try:
        out = subprocess.run(["/bin/ps", "-axww", "-o", "comm="],
                             capture_output=True, text=True, timeout=8).stdout
    except Exception:
        return set()
    return {m.group(1) for line in out.splitlines() if (m := APP_RE.search(line))}


def main() -> None:
    sp = ZundaSpeaker()
    prev_ac, _pct = power_state()
    low_warned = False
    prev_apps = running_apps()
    last_app_poll = time.time()

    while True:
        try:
            sp.cfg = type(sp.cfg)()  # 設定再読込
            poll = _i("POWER_POLL_SEC", 12)
            low_pct = _i("POWER_LOW_PCT", 20)
            app_watch = [w.strip().lower() for w in _s("APP_WATCH", "").split(",") if w.strip()]
            app_poll = _i("APP_POLL_SEC", 5)

            if _b("POWER_WATCH", True):
                ac, pct = power_state()
                if ac is not None and prev_ac is not None and ac != prev_ac:
                    sp.speak(phrases.pick(phrases.CHARGE_START if ac else phrases.CHARGE_STOP),
                             switch=SWITCH)
                if ac is not None:
                    prev_ac = ac
                if pct is not None:
                    if (ac is False) and pct <= low_pct and not low_warned:
                        sp.speak(phrases.low_battery(pct), switch=SWITCH)
                        low_warned = True
                    elif ac is True or pct > low_pct + 5:
                        low_warned = False

            # アプリ起動監視(APP_WATCH が空なら無効)
            if app_watch and (time.time() - last_app_poll) >= app_poll:
                last_app_poll = time.time()
                cur = running_apps()
                for name in cur - prev_apps:
                    if any(w in name.lower() for w in app_watch):
                        sp.speak(phrases.app_launched(name), switch=SWITCH)
                prev_apps = cur
        except Exception as e:
            print(f"[system] err: {e}", flush=True)
        time.sleep(max(2, min(poll, app_poll if app_watch else poll)))


if __name__ == "__main__":
    main()

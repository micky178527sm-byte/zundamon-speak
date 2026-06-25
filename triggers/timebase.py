#!/usr/bin/env python3
"""時刻トリガー: 毎時の時報 + 休憩リマインド。

switches/time が無ければ何もしない(マスタースイッチ enabled も core 側で判定)。
config.env: TIME_HOURLY / TIME_BREAK_MIN
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import ZundaSpeaker, _b, _i  # noqa: E402
import phrases  # noqa: E402

SWITCH = "time"
LOOP = 15  # 秒


def main() -> None:
    sp = ZundaSpeaker()
    last_hour_chimed = -1
    last_break = time.time()
    while True:
        try:
            sp.cfg = type(sp.cfg)()  # config.env を毎周回再読込(設定変更を反映)
            now = datetime.now()
            hourly = _b("TIME_HOURLY", True)
            break_min = _i("TIME_BREAK_MIN", 0)

            if hourly and now.minute == 0 and now.hour != last_hour_chimed:
                last_hour_chimed = now.hour
                sp.speak(phrases.hourly(now.hour), switch=SWITCH)

            if break_min > 0 and (time.time() - last_break) >= break_min * 60:
                last_break = time.time()
                sp.speak(phrases.pick(phrases.BREAK), switch=SWITCH)
        except Exception as e:  # デーモンは落とさない
            print(f"[time] err: {e}", flush=True)
        time.sleep(LOOP)


if __name__ == "__main__":
    main()

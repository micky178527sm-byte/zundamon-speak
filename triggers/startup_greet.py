#!/usr/bin/env python3
"""起動(ログイン)トリガー: ログイン時に一度だけ挨拶する。

LaunchAgent com.zundamon.startup が RunAtLoad で1回だけ実行(KeepAlive 無し)。
ログインのたびに発火する。挨拶文は事前キャッシュ済みなので、起動直後で
エンジンが未準備でも即再生できる(キャッシュが無い場合はエンジン起動を待って合成)。

ゲート: マスター enabled / switches/startup / 静音時間帯 を尊重する。
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import core  # noqa: E402
from core import ZundaSpeaker  # noqa: E402
import phrases  # noqa: E402

SWITCH = "startup"


def main() -> None:
    # ログイン直後はオーディオ/セッションが整うまで少し待つ(ログイン音と被らせない)
    time.sleep(5)
    sp = ZundaSpeaker()

    # 意図的に黙る設定(マスターOFF/スイッチOFF/静音)ならリトライせず終了
    if (not sp.master_enabled()
            or not (core.SWITCH_DIR / SWITCH).exists()
            or sp._in_quiet()):
        return

    text = phrases.startup_greeting(datetime.now().hour)
    # キャッシュ即ヒットが基本。万一エンジン起動待ちで合成できない時は数回リトライ。
    for _ in range(6):  # 最大 ~30 秒
        if sp.speak(text, switch=SWITCH):
            return
        time.sleep(5)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""気象警報・注意報トリガー: 気象庁の公式JSONを見て、新規発表/解除を読み上げる。

データ源: 気象庁 防災情報JSON(APIキー不要・無料)。
  https://www.jma.go.jp/bosai/warning/data/warning/{JMA_AREA}.json
府県内のどこかで新たに出た/解除された 警報・注意報の「種類」をまとめて伝える
(市町村ごとには細かく読まない=うるさくしない)。台風の影響は暴風/波浪/高潮等の
警報として反映される(台風進路そのものの専用追跡は将来課題)。

switches/jmawarn が無ければ何もしない。取得は macOS 標準 curl 経由。
【非公式利用】気象庁は常識的範囲での利用を求めている。ポーリングは控えめに。

config.env: JMA_AREA(府県予報区コード) / JMA_AREA_NAME(読み上げ用) / JMA_WARN_POLL_SEC
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import ZundaSpeaker, _i, _s  # noqa: E402

SWITCH = "jmawarn"

# 警報・注意報コード -> 名称(主要なもの)
WARN_NAME = {
    "02": "暴風雪警報", "03": "大雨警報", "04": "洪水警報", "05": "暴風警報",
    "06": "大雪警報", "07": "波浪警報", "08": "高潮警報",
    "10": "大雨注意報", "12": "大雪注意報", "13": "風雪注意報", "14": "雷注意報",
    "15": "強風注意報", "16": "波浪注意報", "17": "融雪注意報", "18": "洪水注意報",
    "19": "高潮注意報", "20": "濃霧注意報", "21": "乾燥注意報", "22": "なだれ注意報",
    "23": "低温注意報", "24": "霜注意報", "25": "着氷注意報", "26": "着雪注意報",
    "32": "暴風雪特別警報", "33": "大雨特別警報", "35": "暴風特別警報",
    "36": "大雪特別警報", "37": "波浪特別警報", "38": "高潮特別警報",
}
ACTIVE = {"発表", "継続"}


def fetch(area: str):
    url = f"https://www.jma.go.jp/bosai/warning/data/warning/{area}.json"
    try:
        out = subprocess.run(
            ["/usr/bin/curl", "-s", "--max-time", "12", "-A", "curl/8", url],
            capture_output=True, text=True, timeout=15).stdout
        return json.loads(out) if out.strip() else None
    except Exception:
        return None


def active_codes(data: dict) -> set:
    """府県内のどこかで 発表/継続 中の 警報・注意報コード集合。"""
    codes = set()
    for at in (data or {}).get("areaTypes", []):
        for area in at.get("areas", []):
            for w in area.get("warnings", []):
                if w.get("status") in ACTIVE and w.get("code") in WARN_NAME:
                    codes.add(w["code"])
    return codes


def main() -> None:
    sp = ZundaSpeaker()
    prev = None  # 直近のアクティブ集合(None=未取得)

    while True:
        try:
            sp.cfg = type(sp.cfg)()
            if not (Path(__file__).resolve().parent.parent / "switches" / SWITCH).exists():
                time.sleep(5)
                continue
            area = _s("JMA_AREA", "130000")
            area_name = _s("JMA_AREA_NAME", "")
            poll = _i("JMA_WARN_POLL_SEC", 180)

            data = fetch(area)
            if data is not None:
                cur = active_codes(data)
                if prev is None:  # 初回は基準化(既存の警報は読み上げない)
                    prev = cur
                    print(f"[jmawarn] 監視開始 area={area}: 既存{len(cur)}件を基準化",
                          flush=True)
                else:
                    where = (area_name + "に") if area_name else ""
                    for code in cur - prev:  # 新規発表
                        sp.speak(f"{where}{WARN_NAME[code]}が発表されたのだ", switch=SWITCH)
                        print(f"[jmawarn] 発表 {WARN_NAME[code]}", flush=True)
                    for code in prev - cur:  # 解除
                        whose = (area_name + "の") if area_name else ""
                        sp.speak(f"{whose}{WARN_NAME[code]}は解除されたのだ", switch=SWITCH)
                        print(f"[jmawarn] 解除 {WARN_NAME[code]}", flush=True)
                    prev = cur
        except Exception as e:
            print(f"[jmawarn] err: {e}", flush=True)
        time.sleep(max(60, poll))


if __name__ == "__main__":
    main()

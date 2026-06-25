#!/usr/bin/env python3
"""朝の天気ブリーフ・トリガー: 指定時刻に一度だけ、現在地の天気を読み上げる。

データ源: wttr.in (APIキー不要・無料)。?format=j1 の JSON を取得し、
現在地(IP自動判定)の 天気・気温(現在/最高/最低)・湿度・風向風速 を発話する。
最後にユニークな一言を添える。

switches/weather が無ければ何もしない。
config.env: WEATHER_TIME(HH:MM) / WEATHER_LOCATION(空=自動) / WEATHER_POLL_SEC

権限不要(ネットワークのみ)。現在地名はIPから自動判定されるため発話では省略し、
天気そのものに集中する(都市名の不自然な読み上げを避ける)。
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import ZundaSpeaker, _i, _s  # noqa: E402

SWITCH = "weather"

# WWO 天気コード -> 日本語(wttr.in が返す weatherCode)。
WEATHER_CODE = {
    "113": "快晴", "116": "晴れ時々くもり", "119": "くもり", "122": "本曇り",
    "143": "もや", "176": "ところにより雨", "179": "ところにより雪",
    "182": "ところによりみぞれ", "185": "ところにより霧雨", "200": "雷雨のおそれ",
    "227": "地ふぶき", "230": "ふぶき", "248": "霧", "260": "こおる霧",
    "263": "弱い霧雨", "266": "霧雨", "281": "こおる霧雨", "284": "強いこおる霧雨",
    "293": "弱い雨", "296": "弱い雨", "299": "時々強い雨", "302": "強い雨",
    "305": "激しい雨", "308": "激しい雨", "311": "こおる雨", "314": "強いこおる雨",
    "317": "弱いみぞれ", "320": "みぞれ", "323": "弱い雪", "326": "弱い雪",
    "329": "強い雪", "332": "強い雪", "335": "激しい雪", "338": "激しい雪",
    "350": "ひょう", "353": "にわか雨", "356": "強いにわか雨", "359": "激しいにわか雨",
    "362": "みぞれのにわか雨", "365": "強いみぞれのにわか雨", "368": "にわか雪",
    "371": "強いにわか雪", "374": "弱いにわかひょう", "377": "強いにわかひょう",
    "386": "雷をともなう雨", "389": "雷をともなう強い雨", "392": "雷をともなう雪",
    "395": "雷をともなう強い雪",
}

# 16方位(英) -> 日本語
WIND_DIR = {
    "N": "北", "NNE": "北北東", "NE": "北東", "ENE": "東北東", "E": "東",
    "ESE": "東南東", "SE": "南東", "SSE": "南南東", "S": "南", "SSW": "南南西",
    "SW": "南西", "WSW": "西南西", "W": "西", "WNW": "西北西", "NW": "北西",
    "NNW": "北北西",
}


def fetch(location: str):
    """wttr.in から現在地(空)or指定地の天気 JSON を取得。失敗時 None。

    取得は macOS 標準の curl 経由(システムの証明書ストアを使うため、python の
    SSL証明書が未整備な環境でも確実に動く)。UA は curl 風(JSON は UA 非依存だが念のため)。
    """
    loc = urllib.parse.quote(location.strip())
    url = f"https://wttr.in/{loc}?format=j1"
    try:
        out = subprocess.run(
            ["/usr/bin/curl", "-s", "--max-time", "12", "-A", "curl/8", url],
            capture_output=True, text=True, timeout=15).stdout
        return json.loads(out) if out.strip() else None
    except Exception:
        return None


def one_liner(code: str, temp: int, wind_kmph: int, humidity: int) -> str:
    """天気に応じたユニークな一言。条件別プール + ランダムで日替わり感を出す。"""
    rain = code in {"176", "200", "263", "266", "293", "296", "299", "302",
                    "308", "353", "356", "359", "386", "389"}
    snow = code in {"179", "227", "230", "323", "326", "329", "332", "335",
                    "338", "368", "371", "392", "395"}
    pools = []
    if rain:
        pools = ["傘を忘れずに持っていくのだ", "足元がぬれるから気をつけるのだ",
                 "雨音をBGMにのんびりするのもいいのだ"]
    elif snow:
        pools = ["路面がこおるから一歩ずつなのだ", "あたたかくして出かけるのだ",
                 "雪だるま日和なのだ"]
    elif temp >= 28:
        pools = ["水分をこまめにとるのだ", "日かげを選んで歩くのだ", "アイスがおいしい日なのだ"]
    elif temp <= 0:
        pools = ["こおえないように厚着するのだ", "手ぶくろの出番なのだ", "あったかいお茶がしみるのだ"]
    elif wind_kmph >= 30:
        pools = ["風が強いから帽子に注意なのだ", "飛ばされないようにするのだ"]
    else:
        pools = ["今日もいい一日にするのだ", "ずんだもんが応援してるのだ",
                 "深呼吸して始めるといいのだ", "ちいさな目標をひとつ決めるといいのだ",
                 "笑顔でいくのだ"]
    if humidity >= 80:
        pools = pools + ["じめじめするから水分とりすぎ注意なのだ"]
    return random.choice(pools)


def build_text(data: dict):
    """JSON から発話テキストを組み立てる。組み立て不能なら None。"""
    try:
        cur = data["current_condition"][0]
        today = data["weather"][0]
        code = str(cur.get("weatherCode", ""))
        desc = WEATHER_CODE.get(code, "")
        temp = int(cur.get("temp_C", 0))
        hi = int(today.get("maxtempC", temp))
        lo = int(today.get("mintempC", temp))
        hum = int(cur.get("humidity", 0))
        spd = int(cur.get("windspeedKmph", 0))
        wdir = WIND_DIR.get(str(cur.get("winddir16Point", "")), "")
    except Exception:
        return None

    parts = ["おはようなのだ"]
    parts.append(f"今日のお天気は{desc}" if desc else "今日のお天気をお知らせするのだ")
    parts.append(f"気温は今{temp}度、最高{hi}度、最低{lo}度")
    parts.append(f"湿度は{hum}パーセント")
    if wdir:
        parts.append(f"風は{wdir}の時速{spd}キロ")
    else:
        parts.append(f"風は時速{spd}キロ")
    text = "。".join(parts) + "なのだ。" + one_liner(code, temp, spd, hum)
    return text


def main() -> None:
    sp = ZundaSpeaker()
    last_date = ""   # 既に読み上げた日(YYYY-MM-DD)

    while True:
        try:
            sp.cfg = type(sp.cfg)()  # 設定を毎周回再読込
            poll = _i("WEATHER_POLL_SEC", 30)
            location = _s("WEATHER_LOCATION", "")
            hhmm = _s("WEATHER_TIME", "08:30")
            try:
                th, tm = (int(x) for x in hhmm.split(":", 1))
            except Exception:
                th, tm = 8, 30

            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            target = th * 60 + tm
            cur_min = now.hour * 60 + now.minute
            # 指定時刻から5分の窓内で、その日まだ読んでいなければ取得を試みる。
            # 取得失敗時は last_date を更新しないので窓内で次周回に再試行する。
            if last_date != today and 0 <= cur_min - target < 5:
                data = fetch(location)
                if data is not None:
                    text = build_text(data)
                    if text and sp.speak(text, switch=SWITCH):
                        last_date = today
                        print(f"[weather] 読上 ({hhmm}) loc={location or 'auto'}",
                              flush=True)
        except Exception as e:
            print(f"[weather] err: {e}", flush=True)
        time.sleep(max(5, poll))


if __name__ == "__main__":
    main()

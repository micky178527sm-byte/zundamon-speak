#!/usr/bin/env python3
"""zundamon-speak / phrases.py — ずんだもん語尾の台詞集。"""
from __future__ import annotations

import random

GREET = ["ずんだもん、準備OKなのだ", "今日も見守るのだ"]

# 起動(ログイン)時の挨拶。時間帯で変える。全variantを事前キャッシュする(起動直後でも即再生)。
def startup_greeting(hour: int) -> str:
    if 5 <= hour < 11:
        return "おはようなのだ。今日もがんばるのだ"
    if 11 <= hour < 17:
        return "こんにちはなのだ。ずんだもん、準備OKなのだ"
    return "こんばんはなのだ。今日もおつかれなのだ"

# 事前キャッシュ対象(代表時刻: 朝/昼/夜)
STARTUP_ALL = [startup_greeting(8), startup_greeting(14), startup_greeting(20)]

# 時刻
def hourly(h: int) -> str:
    return f"{h}時なのだ"

BREAK = ["そろそろ休憩なのだ", "ちょっと休むといいのだ", "目を休めるのだ"]

# 電源
CHARGE_START = ["充電はじまったのだ", "電源つないだのだ"]
CHARGE_STOP = ["電源がぬけたのだ", "充電やめたのだ"]
CHARGE_FULL = ["満充電なのだ。電源をぬくとバッテリーが長持ちするのだ",
               "充電まんたんなのだ。そろそろ電源ぬいていいのだ"]
def low_battery(pct: int) -> str:
    return f"バッテリーが{pct}パーセントなのだ。そろそろ充電なのだ"

# アプリ起動
def app_launched(name: str) -> str:
    return f"{name}をひらいたのだ"

# 通知
def notify(app: str, title: str = "", body: str = "") -> str:
    parts = []
    if app:
        parts.append(f"{app}から通知なのだ")
    if title:
        parts.append(title)
    if body:
        parts.append(body)
    return "。".join(parts) if parts else "通知が来たのだ"


def pick(seq):
    return random.choice(seq)

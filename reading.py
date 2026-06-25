#!/usr/bin/env python3
"""zundamon-speak / reading.py — 発話テキストの読み正規化。

VOICEVOX(OpenJTalk)は辞書に無いローマ字を綴り読み(「Ayaka」→「えーわいえー
けーえー」)してしまう。通知の送信者名などローマ字の日本語名がこれで不自然に
なるため、発話前に「ローマ字として綺麗に分解できる語」だけ ひらがな へ変換する。

方針(誤変換を出さないことを最優先):
  - トークン(連続するASCII英字)全体が ローマ字音節 に完全分解できる時だけ変換。
    例: Ayaka→あやか / Yuki→ゆき / Takeshi→たけし
  - 分解に失敗する英単語は一切触らない。
    例: Slack(sl で失敗) / GitHub(th で失敗) / Discord(di を持たない) はそのまま。
  - 全大文字の頭字語(NHK/API 等)は変換せず VOICEVOX のアルファベット読みに任せる。
  - READING_MAP の手動指定が最優先(自動が外す/誤る語をユーザーが上書きできる)。

純粋関数のみ。外部依存なし。
"""
from __future__ import annotations

import re

# ローマ字 -> ひらがな。長いキー(3字)から貪欲一致させる。
# 標準ヘボン式を中心に、人名で出る範囲をカバー。あいまいで英単語を巻き込みやすい
# 綴り(di, fi, l/q/v/x 始まり 等)はあえて入れない -> 英単語は分解失敗で素通りする。
_ROMAJI = {
    # 3字(拗音・促音絡み)
    "kya": "きゃ", "kyu": "きゅ", "kyo": "きょ",
    "gya": "ぎゃ", "gyu": "ぎゅ", "gyo": "ぎょ",
    "sha": "しゃ", "shu": "しゅ", "sho": "しょ", "shi": "し",
    "cha": "ちゃ", "chu": "ちゅ", "cho": "ちょ", "chi": "ち",
    "ja": "じゃ", "ju": "じゅ", "jo": "じょ",
    "nya": "にゃ", "nyu": "にゅ", "nyo": "にょ",
    "hya": "ひゃ", "hyu": "ひゅ", "hyo": "ひょ",
    "mya": "みゃ", "myu": "みゅ", "myo": "みょ",
    "rya": "りゃ", "ryu": "りゅ", "ryo": "りょ",
    "bya": "びゃ", "byu": "びゅ", "byo": "びょ",
    "pya": "ぴゃ", "pyu": "ぴゅ", "pyo": "ぴょ",
    "tsu": "つ",
    # 2字
    "ka": "か", "ki": "き", "ku": "く", "ke": "け", "ko": "こ",
    "ga": "が", "gi": "ぎ", "gu": "ぐ", "ge": "げ", "go": "ご",
    "sa": "さ", "su": "す", "se": "せ", "so": "そ",
    "za": "ざ", "zu": "ず", "ze": "ぜ", "zo": "ぞ", "ji": "じ",
    "ta": "た", "te": "て", "to": "と",
    "da": "だ", "de": "で", "do": "ど",
    "na": "な", "ni": "に", "nu": "ぬ", "ne": "ね", "no": "の",
    "ha": "は", "hi": "ひ", "fu": "ふ", "he": "へ", "ho": "ほ",
    "ba": "ば", "bi": "び", "bu": "ぶ", "be": "べ", "bo": "ぼ",
    "pa": "ぱ", "pi": "ぴ", "pu": "ぷ", "pe": "ぺ", "po": "ぽ",
    "ma": "ま", "mi": "み", "mu": "む", "me": "め", "mo": "も",
    "ya": "や", "yu": "ゆ", "yo": "よ",
    "ra": "ら", "ri": "り", "ru": "る", "re": "れ", "ro": "ろ",
    "wa": "わ", "wo": "を",
    # 1字(母音)
    "a": "あ", "i": "い", "u": "う", "e": "え", "o": "お",
}
_CONSONANTS = set("kgsztdnhfbpmyrwcj")


def romaji_to_kana(token: str):
    """token が完全にローマ字分解できれば ひらがな を返す。無理なら None。"""
    s = token.lower()
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        # 促音: 同じ子音の重なり(kk, tt, pp, ss ...) -> っ
        if (c in _CONSONANTS and c != "n" and i + 1 < n
                and s[i + 1] == c):
            out.append("っ")
            i += 1
            continue
        # 撥音: n が 母音/y 以外の前、または語末 -> ん
        if c == "n":
            nxt = s[i + 1] if i + 1 < n else ""
            if nxt == "" or nxt not in "aiueoy":
                out.append("ん")
                i += 1
                continue
        # 3字 -> 2字 -> 1字 の順で貪欲一致
        for ln in (3, 2, 1):
            chunk = s[i:i + ln]
            if chunk in _ROMAJI:
                out.append(_ROMAJI[chunk])
                i += ln
                break
        else:
            return None  # 1音節も取れない = ローマ字ではない -> 変換しない
    return "".join(out)


def parse_reading_map(raw: str) -> dict:
    """READING_MAP 文字列 'Ayaka=あやか;Zoom=ズーム' を dict に。キーは小文字化。"""
    m = {}
    for piece in (raw or "").split(";"):
        piece = piece.strip()
        if not piece or "=" not in piece:
            continue
        k, _, v = piece.partition("=")
        k, v = k.strip(), v.strip()
        if k and v:
            m[k.lower()] = v
    return m


def normalize(text: str, reading_map: dict | None = None,
              auto_romaji: bool = True) -> str:
    """テキスト中の ASCII 英字トークンを読みやすく整える。

    各トークンについて:
      1. reading_map に有れば その読みへ(最優先)。
      2. 全大文字(NHK/API 等)は頭字語とみなし そのまま(アルファベット読み)。
      3. auto_romaji かつ ローマ字として完全分解できれば ひらがな へ。
      4. いずれも該当しなければ そのまま(英単語など)。
    """
    reading_map = reading_map or {}

    def repl(match: re.Match) -> str:
        tok = match.group(0)
        mapped = reading_map.get(tok.lower())
        if mapped is not None:
            return mapped
        if tok.isupper():            # 頭字語はアルファベット読みのまま
            return tok
        if auto_romaji:
            kana = romaji_to_kana(tok)
            if kana is not None:
                return kana
        return tok

    return re.sub(r"[A-Za-z]+", repl, text)

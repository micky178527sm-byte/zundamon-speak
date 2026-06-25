#!/usr/bin/env python3
"""zundamon-speak / core.py

自分の Mac の「随所で」ずんだもん(VOICEVOX)に喋らせるための発話コア。
すべてのトリガー(通知/時刻/電源/ホットキー)と CLI `zundamon` が共有する。

設計:
    - サードパーティ依存ゼロ(標準ライブラリ + macOS 標準コマンドのみ)
        合成 : VOICEVOX Engine (HTTP, urllib)
        再生 : afplay
        代替 : say (FALLBACK_SAY=1 のとき。ずんだもん声では無い)
    - 発話を直列化(fcntl ロック)。複数トリガーが同時でも声が被らない。
      ロック待ちが長い(=バックログ)ときは捨てる -> 喋り続け事故を防ぐ。
    - キャッシュ: 同じ台詞の WAV は再合成せず即再生(エンジン不要)。
    - マスタースイッチ: プロジェクト直下の `enabled` が無ければ完全に黙る。
    - 静音時間帯 / 連続重複抑制。
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

warnings.filterwarnings("ignore")

APP_DIR = Path(__file__).resolve().parent
CACHE_DIR = APP_DIR / ".voice_cache"
STATE_DIR = APP_DIR / ".state"
LOCK_FILE = STATE_DIR / "speak.lock"
LAST_FILE = STATE_DIR / "last_spoken.json"
ENABLED_FILE = APP_DIR / "enabled"          # マスタースイッチ(存在しなければ黙る)
SWITCH_DIR = APP_DIR / "switches"           # 個別トリガー ON/OFF


# ==========================================================================
# 設定
# ==========================================================================
def _load_env() -> None:
    path = APP_DIR / "config.env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.split("#", 1)[0].strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), val)


def _s(k: str, d: str) -> str:
    return os.environ.get(k, d)


def _i(k: str, d: int) -> int:
    try:
        return int(os.environ.get(k, d))
    except (TypeError, ValueError):
        return d


def _f(k: str, d: float) -> float:
    try:
        return float(os.environ.get(k, d))
    except (TypeError, ValueError):
        return d


def _b(k: str, d: bool) -> bool:
    v = os.environ.get(k)
    return d if v is None else v.strip().lower() in ("1", "true", "yes", "on")


class Config:
    def __init__(self) -> None:
        _load_env()
        self.url = _s("VOICEVOX_URL", "http://127.0.0.1:50021").rstrip("/")
        self.speaker = _i("VOICEVOX_SPEAKER", 3)         # 3 = ずんだもん(ノーマル)
        self.speed = _f("VOICEVOX_SPEED", 1.1)
        self.pitch = _f("VOICEVOX_PITCH", 0.0)
        self.volume = _f("VOICEVOX_VOLUME", 1.0)
        self.cache = _b("ENABLE_CACHE", True)
        self.fallback_say = _b("FALLBACK_SAY", False)
        self.quiet_start = _i("QUIET_START", 23)         # -1 で無効
        self.quiet_end = _i("QUIET_END", 8)
        self.lock_timeout = _f("SPEAK_LOCK_TIMEOUT", 8.0)
        self.dedupe_sec = _f("DEDUPE_SEC", 4.0)
        self.maxlen = _i("SPEAK_MAXLEN", 140)            # 長文の安全打ち切り


# ==========================================================================
# スピーカー
# ==========================================================================
class ZundaSpeaker:
    def __init__(self, cfg: Optional[Config] = None) -> None:
        self.cfg = cfg or Config()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_DIR.mkdir(parents=True, exist_ok=True)

    # ---- HTTP (stdlib only) ------------------------------------------------
    def _get(self, path: str, timeout: float = 1.5) -> bytes:
        with urllib.request.urlopen(self.cfg.url + path, timeout=timeout) as r:
            return r.read()

    def _post(self, path: str, params: dict, body: Optional[dict] = None,
              timeout: float = 20.0) -> bytes:
        url = self.cfg.url + path + "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()

    def engine_up(self) -> bool:
        # 高負荷時は /version 応答が遅れるため、短すぎると生きていても NG 表示になる。
        # 5秒まで待って正確に判定する(実発話の synth は別途 20秒許容)。
        try:
            self._get("/version", timeout=5.0)
            return True
        except Exception:
            return False

    # ---- 合成(キャッシュ付き) --------------------------------------------
    def _cache_path(self, text: str) -> Path:
        key = f"{text}|{self.cfg.speaker}|{self.cfg.speed}|{self.cfg.pitch}|{self.cfg.volume}"
        return CACHE_DIR / (hashlib.sha1(key.encode("utf-8")).hexdigest()[:16] + ".wav")

    def synth(self, text: str) -> Optional[Path]:
        out = self._cache_path(text)
        if self.cfg.cache and out.exists() and out.stat().st_size > 0:
            return out
        try:
            q = json.loads(self._post("/audio_query",
                                      {"text": text, "speaker": self.cfg.speaker}))
            q["speedScale"] = self.cfg.speed
            q["pitchScale"] = self.cfg.pitch
            q["volumeScale"] = self.cfg.volume
            wav = self._post("/synthesis", {"speaker": self.cfg.speaker}, body=q)
            tmp = out.with_suffix(".wav.tmp")
            tmp.write_bytes(wav)
            tmp.replace(out)
            return out
        except Exception:
            return None

    # ---- ゲート ------------------------------------------------------------
    @staticmethod
    def master_enabled() -> bool:
        return ENABLED_FILE.exists()

    def _in_quiet(self) -> bool:
        qs, qe = self.cfg.quiet_start, self.cfg.quiet_end
        if qs < 0 or qe < 0 or qs == qe:
            return False
        h = datetime.now().hour
        return (qs <= h < qe) if qs < qe else (h >= qs or h < qe)

    def _is_dup(self, text: str) -> bool:
        if self.cfg.dedupe_sec <= 0:
            return False
        try:
            d = json.loads(LAST_FILE.read_text())
            if d.get("text") == text and (time.time() - d.get("ts", 0)) < self.cfg.dedupe_sec:
                return True
        except Exception:
            pass
        try:
            LAST_FILE.write_text(json.dumps({"text": text, "ts": time.time()}))
        except Exception:
            pass
        return False

    # ---- 再生(直列化) ----------------------------------------------------
    def _play_locked(self, argv: list) -> bool:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_RDWR, 0o644)
        deadline = time.time() + self.cfg.lock_timeout
        got = False
        while time.time() < deadline:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                got = True
                break
            except OSError:
                time.sleep(0.15)
        if not got:
            os.close(fd)
            return False  # バックログ -> 捨てる
        try:
            subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    # ---- 公開 API ----------------------------------------------------------
    def speak(self, text: str, *, force: bool = False, switch: Optional[str] = None) -> bool:
        """text を発話する。

        force=True : マスタースイッチ/静音/個別スイッチを無視(手動テスト用)。
        switch     : 個別トリガー名。switches/<switch> が無ければ黙る。
        """
        text = (text or "").strip()
        if not text:
            return False
        if len(text) > self.cfg.maxlen:
            text = text[: self.cfg.maxlen] + "、以下略なのだ"

        if not force:
            if not self.master_enabled():
                return False
            if switch and not (SWITCH_DIR / switch).exists():
                return False
            if self._in_quiet():
                return False
            if self._is_dup(text):
                return False

        wav = self.synth(text)
        if wav is not None:
            return self._play_locked(["afplay", str(wav)])
        if self.cfg.fallback_say:
            return self._play_locked(["say", text])
        return False


# ==========================================================================
# CLI
# ==========================================================================
def _cli(argv) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="zundamon", description="ずんだもんに喋らせる")
    ap.add_argument("text", nargs="*", help="喋らせるテキスト(省略時は標準入力)")
    ap.add_argument("--force", action="store_true", help="スイッチ/静音を無視して必ず喋る")
    ap.add_argument("--switch", help="個別トリガー名(switches/<name> ゲート)")
    ap.add_argument("--status", action="store_true", help="エンジン疎通/設定を表示")
    ap.add_argument("--test", action="store_true", help="疎通確認して一言喋る")
    a = ap.parse_args(argv)

    sp = ZundaSpeaker()

    if a.status or a.test:
        up = sp.engine_up()
        print(f"VOICEVOX : {sp.cfg.url} -> {'OK' if up else 'NG (エンジン未起動)'}")
        print(f"speaker={sp.cfg.speaker}(3=ずんだもん) speed={sp.cfg.speed} "
              f"cache={sp.cfg.cache} fallback_say={sp.cfg.fallback_say}")
        print(f"master_enabled={sp.master_enabled()} quiet={sp.cfg.quiet_start}-{sp.cfg.quiet_end}")
        if a.test:
            sp.speak("ずんだもん、準備OKなのだ", force=True)
            print("テスト発話したのだ(聞こえた?)")
        return 0 if up else 1

    text = " ".join(a.text).strip()
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if not text:
        ap.print_help()
        return 2

    ok = sp.speak(text, force=a.force, switch=a.switch)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))

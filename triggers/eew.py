#!/usr/bin/env python3
"""緊急地震速報トリガー: Wolfx の JMA EEW を WebSocket で受けて読み上げる。

データ源: Wolfx Open API (https://wolfx.jp/ ・APIキー不要・無料)。
  WebSocket: wss://ws-api.wolfx.jp/jma_eew  (押し付け配信=低遅延・常時ポーリング不要)

標準ライブラリのみで最小の WebSocket(RFC6455) クライアントを実装(依存ゼロ)。
switches/eew が無ければ接続もしない(完全に休眠=サービスに負荷をかけない)。

【重要・免責】Wolfx は JMA 非提携の非公式リレーで、ネット経由のため遅延があり、
人命安全グレードではない。本命の備えは端末内蔵の緊急地震速報。本機能は補助的な
「声のヘッドアップ」と位置づけること。

config.env: EEW_MIN_SHINDO(この最大予測震度以上 or 警報のみ発話) / EEW_WS_URL
"""
from __future__ import annotations

import base64
import json
import os
import socket
import ssl
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import ZundaSpeaker, _s  # noqa: E402

SWITCH = "eew"

# 震度の序列(予測震度の比較・読み上げ用)
SHINDO_ORDER = ["0", "1", "2", "3", "4", "5-", "5+", "6-", "6+", "7"]
SHINDO_WORD = {"5-": "5弱", "5+": "5強", "6-": "6弱", "6+": "6強"}


def shindo_rank(s: str) -> int:
    s = (s or "").strip()
    return SHINDO_ORDER.index(s) if s in SHINDO_ORDER else -1


def shindo_word(s: str) -> str:
    return f"震度{SHINDO_WORD.get(s, s)}"


def _ssl_context() -> ssl.SSLContext:
    # macOS の python は CA 未整備のことがある。システム束→certifi→無検証 の順で確保。
    for ca in ("/etc/ssl/cert.pem", "/private/etc/ssl/cert.pem"):
        if os.path.exists(ca):
            try:
                return ssl.create_default_context(cafile=ca)
            except Exception:
                pass
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl._create_unverified_context()  # 最後の手段(公開フィードなので許容)
        return ctx


class WS:
    """ごく小さな WebSocket クライアント(text 受信 / ping応答 / close 検知)。"""

    def __init__(self, url: str, timeout: float = 60.0):
        assert url.startswith("wss://")
        host_path = url[len("wss://"):]
        self.host, _, path = host_path.partition("/")
        self.path = "/" + path
        self.timeout = timeout
        self.sock = None

    def connect(self) -> None:
        raw = socket.create_connection((self.host, 443), timeout=15)
        self.sock = _ssl_context().wrap_socket(raw, server_hostname=self.host)
        self.sock.settimeout(self.timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "User-Agent: zundamon-speak\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("handshake closed")
            resp += chunk
        if b" 101 " not in resp.split(b"\r\n", 1)[0]:
            raise ConnectionError(f"handshake failed: {resp[:80]!r}")

    def _recv_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("closed")
            buf += chunk
        return buf

    def _send_frame(self, opcode: int, payload: bytes = b"") -> None:
        # クライアント→サーバは必ずマスクする
        b1 = 0x80 | opcode
        ln = len(payload)
        header = bytes([b1])
        if ln < 126:
            header += bytes([0x80 | ln])
        elif ln < 65536:
            header += bytes([0x80 | 126]) + struct.pack("!H", ln)
        else:
            header += bytes([0x80 | 127]) + struct.pack("!Q", ln)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def messages(self):
        """text メッセージ(str)を逐次 yield。ping は自動応答、close で StopIteration。"""
        while True:
            b0, b1 = self._recv_exact(2)
            opcode = b0 & 0x0F
            ln = b1 & 0x7F
            if ln == 126:
                ln = struct.unpack("!H", self._recv_exact(2))[0]
            elif ln == 127:
                ln = struct.unpack("!Q", self._recv_exact(8))[0]
            payload = self._recv_exact(ln) if ln else b""
            if opcode == 0x8:        # close
                return
            if opcode == 0x9:        # ping -> pong
                self._send_frame(0xA, payload)
                continue
            if opcode in (0x1, 0x2):  # text / binary
                try:
                    yield payload.decode("utf-8", "replace")
                except Exception:
                    continue

    def close(self) -> None:
        try:
            if self.sock:
                self._send_frame(0x8)
                self.sock.close()
        except Exception:
            pass
        self.sock = None


def build_text(d: dict, min_rank: int):
    """EEW JSON から発話テキスト。閾値未満かつ非警報なら None。"""
    if not isinstance(d, dict) or "EventID" not in d:
        return None
    if d.get("isCancel"):
        return "さきほどの緊急地震速報はキャンセルされたのだ"
    if d.get("isTraining") or d.get("isAssumption"):
        return None  # 訓練/仮定報は読まない
    is_warn = bool(d.get("isWarn"))
    maxi = str(d.get("MaxIntensity", ""))
    if not is_warn and shindo_rank(maxi) < min_rank:
        return None
    hypo = d.get("Hypocenter", "震源不明")
    mag = d.get("Magunitude", "")  # Wolfx の綴りママ
    head = "緊急地震速報の警報" if is_warn else "緊急地震速報"
    parts = [f"{head}。{hypo}"]
    if maxi:
        parts.append(f"最大{shindo_word(maxi)}")
    if mag != "":
        parts.append(f"マグニチュード{mag}")
    return "、".join(parts) + "なのだ"


def key_of(d: dict):
    return (d.get("EventID"), bool(d.get("isWarn")), bool(d.get("isCancel")))


def main() -> None:
    sp = ZundaSpeaker()
    seen = []  # 直近に発話済みの (EventID, isWarn, isCancel)

    while True:
        try:
            sp.cfg = type(sp.cfg)()
            # スイッチOFFなら接続せず休眠(無接続=サービスに優しい)
            if not (Path(__file__).resolve().parent.parent / "switches" / SWITCH).exists():
                time.sleep(5)
                continue
            min_rank = shindo_rank(_s("EEW_MIN_SHINDO", "3"))
            if min_rank < 0:
                min_rank = SHINDO_ORDER.index("3")
            url = _s("EEW_WS_URL", "wss://ws-api.wolfx.jp/jma_eew")

            ws = WS(url)
            ws.connect()
            print(f"[eew] WS接続: {url} (min_shindo={_s('EEW_MIN_SHINDO','3')})", flush=True)
            for msg in ws.messages():
                try:
                    d = json.loads(msg)
                except Exception:
                    continue
                if not isinstance(d, dict) or d.get("type") == "heartbeat":
                    continue
                k = key_of(d)
                if k in seen:
                    continue
                text = build_text(d, min_rank)
                if text:
                    seen.append(k)
                    seen[:] = seen[-50:]
                    print(f"[eew] 読上 EventID={d.get('EventID')} "
                          f"warn={d.get('isWarn')} maxI={d.get('MaxIntensity')}", flush=True)
                    sp.speak(text, switch=SWITCH)
        except Exception as e:
            print(f"[eew] 切断/エラー: {e} (5秒後に再接続)", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()

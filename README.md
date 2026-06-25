# 🫛 zundamon-speak — Macのあちこちでずんだもんが喋る

あなたのMacの「随所で」ずんだもん（VOICEVOX）が自動でしゃべってくれる常駐ツールです。
**ターミナルが苦手な人でも、コピペ1回とボタンのダブルクリックだけ**で使えます。

ずんだもんが喋ってくれる場面:
- 🟢 **Mac起動（ログイン）時** … 「おはようなのだ。今日もがんばるのだ」（時間帯で挨拶が変わる）
- ⏰ **毎時の時報** … 「14時なのだ」
- 🔌 **充電/電池** … 充電開始・終了、バッテリー残量わずか、**満充電**（電源を抜く合図）
- 🌤 **朝の天気ブリーフ** … 8時30分に現在地の天気・気温・湿度・風（風速）を一言（任意）
- 🔔 **通知の読み上げ** … 来た通知を声で教えてくれる（任意・要設定）
- ⌨️ **好きな言葉** … `zundamon "すきな言葉なのだ"` でいつでも
- 🇯🇵 **日本向け防災**（任意・既定OFF）… 緊急地震速報・地震情報・気象警報（→ 下の専用セクション）

> 通知や名前の読みは賢く調整されます。ローマ字の名前（例 `Ayaka`）は「あやか」と自然に読み、
> 英単語（Slack など）や頭字語（NHK など）はそのまま読みます。

---

## 必要なもの
- Mac（Apple Silicon / Intel どちらもOK）
- macOS 12 以降
- 空き容量 約2.5GB（ずんだもんの声エンジンを入れます）
- 料金は**完全無料**

---

## 🚀 インストール（コピペ1回）

1. **「ターミナル」アプリ**を開きます
   （Launchpad で「ターミナル」と検索 → クリック）
2. 下の1行をコピーして、ターミナルに貼り付け、**Enter** を押すだけ:

   ```sh
   curl -fsSL https://raw.githubusercontent.com/micky178527sm-byte/zundamon-speak/main/install.command | zsh
   ```

3. あとは自動です（声エンジンのダウンロードに数分かかります）。
   - 途中で「開発者ツールをインストール」と出たら**インストール**を押して、終わったらもう一度同じ行を実行してください。
   - 終わると「ボタン」フォルダが開きます。

> これだけで、次回からMac起動時にずんだもんが挨拶してくれます。

---

## 🎛 操作はボタンをダブルクリック

インストールでできた **「ボタン」フォルダ**（`~/zundamon-speak/ボタン/`）の中身:

| ボタン | はたらき |
|---|---|
| ① ずんだもんを始める | 喋るようにする（普段はこれだけ） |
| ② ぜんぶ黙らせる | 一時的に全部だまる（①でまた喋る） |
| ③ 通知の読み上げを止める | 通知だけ読まなくする |
| ④ 通知の読み上げを再開 | 通知の読み上げを戻す |
| ⑤ ちゃんと動くかテスト | 一言しゃべってテスト |

> よく使うボタンは **Dock やデスクトップにドラッグ**しておくと便利です。

---

## 🔔 通知の読み上げを使うには（任意・1回だけ設定）

通知センターを読むには「フルディスクアクセス」の許可が必要です。
インストール後に設定画面が自動で開きます:

1. **「フルディスクアクセス」** を選ぶ
2. **「＋」** を押す → ファイル選択で **`Cmd+Shift+G`** → **`Cmd+V`**（パスはコピー済み）→ Enter
3. 出てきた `python3` を選んで **オン**にする → Touch ID/パスワードで許可
4. ③④のボタンで通知の読み上げを切り替えられます

プライバシー配慮で、**通知はアプリ名とタイトルだけ**読み上げます（本文は読みません）。
パスワード/2段階認証アプリは最初から除外しています。

---

## 🌤 朝の天気ブリーフ（任意）

毎朝 **8時30分**に、現在地（IPから自動判定）の天気を一言で教えてくれます。

> 「おはようなのだ。今日のお天気はくもり。気温は今24度、最高30度、最低16度。湿度は54パーセント。風は南、風速2メートルなのだ。今日もいい一日にするのだ」

- データは [wttr.in](https://wttr.in)（**APIキー不要・無料**）。
- 既定でONです。時刻や地域は `config.env` の `WEATHER_TIME` / `WEATHER_LOCATION` で変更可。
- 止めたいとき: `rm ~/zundamon-speak/switches/weather`

---

## 🇯🇵 日本向け防災トリガー（任意・既定OFF）

日本国内向けに、**緊急地震速報・地震情報・気象警報**を声で知らせます。
いずれも **APIキー不要・無料**。**既定では無効**で、スイッチを作ったときだけ動きます
（作らなければ接続もポーリングもしません）。海外では有効化しないでください。

| 機能 | スイッチ | 内容 | データ源 |
|---|---|---|---|
| 緊急地震速報（揺れる前） | `switches/eew` | 「緊急地震速報。◯◯沖、最大震度3…」 | [Wolfx](https://wolfx.jp/)（WebSocket） |
| 地震情報（揺れた後） | `switches/quake` | 「地震情報。◯◯で最大震度4…」 | Wolfx |
| 気象警報・注意報 | `switches/jmawarn` | 「大雨警報が発表されたのだ」 | 気象庁 公式JSON |

**有効化のしかた**（日本在住の人向け）:
```sh
# 1) 気象警報は自分の地域を設定（config.env を編集）
#    JMA_AREA=130000 (東京) / 270000 (大阪) など。JMA_AREA_NAME=東京都
# 2) 使うものだけスイッチを作る
touch ~/zundamon-speak/switches/eew      # 緊急地震速報
touch ~/zundamon-speak/switches/quake    # 地震情報（事後）
touch ~/zundamon-speak/switches/jmawarn  # 気象警報
```
発話のしきい値も調整可（`config.env`: `EEW_MIN_SHINDO` / `QUAKE_MIN_SHINDO`）。

> ⚠️ **免責（必読）**: 緊急地震速報の Wolfx は気象庁 非提携の**非公式リレー**です。
> ネット経由のため**遅延があり、人命安全グレードではありません**。本命の備えは
> **スマホ内蔵の緊急地震速報**で、本機能はあくまで**補助的な声のヘッドアップ**です。

---

## 🌙 こんな気づかい付き
- **夜（23時〜翌8時）は自動で静か**になります（`config.env` で変更可）
- 声が**重なりません**（1つずつ最後まで喋る）
- よく使う台詞は記録して**すぐ鳴る**（起動直後やMacが重いときでも途切れにくい）

---

## ❓ 困ったとき / やめたいとき
- 全部だまらせたい → ボタン②、または `rm ~/zundamon-speak/enabled`
- 通知だけ止めたい → ボタン③
- 完全にやめる（アンインストール） → `~/zundamon-speak/uninstall.sh` を実行
  （VOICEVOX.app と設定は残ります。声エンジンも消すなら案内が出ます）

---

## 🙏 クレジット
- 音声合成: **VOICEVOX** https://voicevox.hiroshiba.jp/
- キャラクター: **ずんだもん**
- VOICEVOX 本体・音声は本リポジトリに含まれず、導入時に公式から取得します。
  生成音声の利用は VOICEVOX / 各キャラクターの利用規約に従ってください。

---

<details>
<summary>🛠 開発者向け（しくみ・手動操作）</summary>

### 構成（依存ゼロ：標準ライブラリ + macOS標準コマンドのみ）
```
エンジン  VOICEVOX.app 同梱エンジンを headless 常駐 (127.0.0.1:50021)
  ↓
コア     core.py … 合成→キャッシュ→直列再生(afplay)。マスター/静音/重複抑制
  ↓
トリガー  launchd 常駐デーモン
          ├ startup 起動(ログイン)挨拶   triggers/startup_greet.py
          ├ time    時報・休憩            triggers/timebase.py
          ├ system  充電/電池/満充電/アプリ triggers/system_watch.py
          ├ notify  通知の読み上げ ※要FDA  triggers/notify_watch.py
          ├ weather 朝の天気ブリーフ       triggers/weather.py
          ├ eew     緊急地震速報(WS) 🇯🇵    triggers/eew.py     ※既定OFF
          ├ quake   地震情報(事後) 🇯🇵      triggers/quake.py   ※既定OFF
          └ jmawarn 気象警報 🇯🇵           triggers/jmawarn.py ※既定OFF
読み正規化 reading.py … ローマ字名を かな読み に(Ayaka→あやか)。core が発話直前に適用
コマンド  zundamon / zundamon-read / zundamon-ctl
```

### コマンド
```sh
zundamon "好きな言葉なのだ"      # その場で喋らせる
zundamon --status                # エンジン疎通/設定
zundamon-ctl start|stop|notify-on|notify-off|test|status|uninstall
```

### 設定: `config.env`
話者・話速・静音時間帯（`QUIET_START/END`）・通知の対象アプリ（`NOTIFY_ALLOW`/`NOTIFY_DENY`）・
本文読み上げ（`NOTIFY_READ_BODY`）・休憩リマインド（`TIME_BREAK_MIN`）・満充電（`POWER_FULL_PCT`）・
天気（`WEATHER_TIME`/`WEATHER_LOCATION`）・読み辞書（`READING_MAP`/`ROMAJI_TO_KANA`）・
防災（`EEW_MIN_SHINDO`/`QUAKE_MIN_SHINDO`/`JMA_AREA`）など。
変更は常駐デーモンにも**再起動なしで反映**（次回発話時にホットリロード）。

### スイッチ（ファイルの有無で制御）
- `enabled` … マスター（無ければ全部だまる）
- `switches/{startup,time,power,notify,weather}` … 個別ON/OFF（既定ON）
- `switches/{eew,quake,jmawarn}` … 日本向け防災（**既定OFF**。作ると有効）

### しくみメモ
- LaunchAgent は `__ROOT__`/`__PYTHON__` を install 時に実値へ置換（どのユーザーでも動く）
- 通知DB(`group.com.apple.usernoted`)は `mode=rw`+`query_only` で読む（読み取り専用だと
  WAL の最新通知を取りこぼすため）。FDA は **再exec先の実体 python** に付与が必要。
- EEW は標準ライブラリだけの最小 WebSocket クライアント（TLSはmacOSシステム証明書/certifi）。
- ネット取得（天気/地震/警報）は macOS 標準 `curl` 経由（python の SSL証明書が未整備でも動く）。

</details>

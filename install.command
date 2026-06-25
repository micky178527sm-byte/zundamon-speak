#!/bin/zsh
# install.command — ダブルクリック1回で全部入れる導入スクリプト(機械音痴向け)。
#   - 必要なら開発者ツール(python)の導入を案内
#   - VOICEVOX.app を自動ダウンロード&インストール(機種に合わせarm64/x64)
#   - 本体セットアップ(install.sh)
#   - フルディスクアクセスの設定画面を開く + 操作ボタンのフォルダを開く
# リポジトリ内でダブルクリックしても、次の1行(Terminal)で起動してもOK:
#   curl -fsSL https://raw.githubusercontent.com/micky178527sm-byte/zundamon-speak/main/install.command | zsh
REPO_TARBALL="https://github.com/micky178527sm-byte/zundamon-speak/archive/refs/heads/main.tar.gz"

set -e
echo "==================================================="
echo "   ずんだもん speak  かんたんセットアップ"
echo "==================================================="

# 0) 自分がリポジトリ内にあるか? 無ければ取得(curl|zsh 起動に対応)
SELF_DIR="$(cd -P "$(dirname "$0")" 2>/dev/null && pwd || true)"
if [ -n "$SELF_DIR" ] && [ -f "$SELF_DIR/core.py" ]; then
  ROOT="$SELF_DIR"
else
  ROOT="$HOME/zundamon-speak"
  echo "→ 必要ファイルを取得します..."
  mkdir -p "$ROOT"
  curl -fsSL "$REPO_TARBALL" | tar xz -C "$ROOT" --strip-components=1
fi
cd "$ROOT"

# 1) 開発者ツール(python3)の確認。無ければ案内して終了
if ! /usr/bin/python3 -c 'import sys' >/dev/null 2>&1; then
  echo "→ 開発者ツール(Python)が必要です。インストール画面を出します..."
  xcode-select --install 2>/dev/null || true
  osascript -e 'display dialog "最初に「開発者ツール(Python)」のインストールが必要です。\n\n表示された画面で「インストール」を押し、完了したら\nもう一度このインストーラを実行してください。" buttons {"OK"} default button 1 with title "ずんだもん"' >/dev/null 2>&1 || true
  exit 0
fi

# 2) VOICEVOX.app(ずんだもんの声エンジン)を導入
ENGINE="/Applications/VOICEVOX.app/Contents/Resources/vv-engine/run"
if [ -x "$ENGINE" ]; then
  echo "✓ VOICEVOX.app は導入済み"
else
  case "$(uname -m)" in
    arm64) PAT="arm64.dmg"; FB="https://github.com/VOICEVOX/voicevox/releases/download/0.25.2/VOICEVOX.0.25.2-arm64.dmg" ;;
    *)     PAT="x64.dmg";   FB="https://github.com/VOICEVOX/voicevox/releases/download/0.25.2/VOICEVOX.0.25.2-x64.dmg" ;;
  esac
  URL="$(curl -s --max-time 20 https://api.github.com/repos/VOICEVOX/voicevox/releases/latest \
        | grep browser_download_url | grep -i "$PAT" | head -1 | cut -d'"' -f4)"
  [ -z "$URL" ] && URL="$FB"
  echo "→ VOICEVOX.app をダウンロードします（約2GB・回線により数分）..."
  TMP="$(mktemp -d)"; DMG="$TMP/voicevox.dmg"; MNT="$TMP/mnt"
  curl -L --progress-bar -o "$DMG" "$URL"
  echo "→ インストール中..."
  hdiutil attach "$DMG" -nobrowse -noautoopen -mountpoint "$MNT" >/dev/null
  ditto "$MNT/VOICEVOX.app" /Applications/VOICEVOX.app
  hdiutil detach "$MNT" >/dev/null 2>&1 || true
  rm -rf "$TMP"
  echo "✓ VOICEVOX.app 導入完了"
fi

# 3) 本体セットアップ
zsh "$ROOT/install.sh"

# 4) 仕上げ: 操作ボタンを開く / 通知用フルディスクアクセスを案内
PYREAL="$(/usr/bin/python3 -c 'import sys;print(sys.executable)' 2>/dev/null)"
open "$ROOT/ボタン" 2>/dev/null || true
osascript -e 'display dialog "セットアップ完了なのだ！🫛\n\n「ボタン」フォルダが開いたのだ。\n①ずんだもんを始める を押すと喋り始めるのだ。\n\n通知の読み上げも使うなら、次に出る設定画面で\nフルディスクアクセスを許可してね（任意）。" buttons {"OK"} default button 1 with title "ずんだもん"' >/dev/null 2>&1 || true

# 通知読み上げ用 FDA: パスをコピーして設定を開く(任意)
printf '%s' "$PYREAL" | pbcopy 2>/dev/null || true
open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles" 2>/dev/null || true

echo ""
echo "✓ 完了なのだ! 「$ROOT/ボタン」のボタンをダブルクリックで操作できるのだ。"
echo "  (通知読み上げを使う場合) フルディスクアクセスに次を追加→ $PYREAL"
echo "  ※コピー済みなので、設定画面で + を押して貼り付け(Cmd+V)するだけなのだ。"
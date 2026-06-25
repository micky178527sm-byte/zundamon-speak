#!/bin/zsh
# zundamon-speak インストーラ(冪等・どの Mac でも動く)。
# 通常はダブルクリックの install.command から呼ばれる。手動なら: ~/zundamon-speak/install.sh
#   - コマンド(zundamon / zundamon-read / zundamon-ctl)を PATH に
#   - マスター enabled と switches/* を作成
#   - LaunchAgent(engine/time/system/notify/startup)を配置&起動(パスは自動置換)
#   - 起動挨拶を事前キャッシュ / クイックアクション配置 / 操作ボタン生成
set -e
ROOT="$(cd -P "$(dirname "$0")" && pwd)"
LA="$HOME/Library/LaunchAgents"
SVC="$HOME/Library/Services"
DOMAIN="gui/$(id -u)"
KEEPALIVE_AGENTS=(engine time system notify weather eew quake jmawarn)

echo "==> zundamon-speak install (root=$ROOT)"

ENGINE_BIN="/Applications/VOICEVOX.app/Contents/Resources/vv-engine/run"
[ -x "$ENGINE_BIN" ] || echo "   ⚠ VOICEVOX.app 未検出。先に install.command で導入してね。"

# FDA を効かせるため python の実体(再exec先)を解決
PYREAL="$(/usr/bin/python3 -c 'import sys;print(sys.executable)' 2>/dev/null)"
[ -z "$PYREAL" ] && PYREAL=/usr/bin/python3

# 1) コマンド symlink(書込可能な bin を自動選択)
chmod +x "$ROOT"/bin/*(N) "$ROOT"/*.sh(N) "$ROOT"/*.command(N) 2>/dev/null || true
BIN=""
for cand in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin"; do
  if [ -w "$cand" ] || { [ ! -e "$cand" ] && mkdir -p "$cand" 2>/dev/null; }; then BIN="$cand"; break; fi
done
[ -z "$BIN" ] && { mkdir -p "$HOME/.local/bin"; BIN="$HOME/.local/bin"; }
for c in zundamon zundamon-read zundamon-ctl; do ln -sf "$ROOT/bin/$c" "$BIN/$c"; done
echo "   コマンド: $BIN/{zundamon,zundamon-read,zundamon-ctl}"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "   ※ $BIN は PATH 外。~/.zshrc に: export PATH=\"$BIN:\$PATH\"";; esac

# 2) スイッチ(既定: 全部ON)
touch "$ROOT/enabled"
mkdir -p "$ROOT/switches"
touch "$ROOT/switches/time" "$ROOT/switches/power" "$ROOT/switches/notify" \
      "$ROOT/switches/startup" "$ROOT/switches/weather"
echo "   スイッチ: time, power, notify, startup, weather (master ON)"
# 日本向け防災(eew/quake/jmawarn)は既定OFF。日本在住者が手動で有効化する。
echo "   防災(日本向け)は既定OFF。有効化: touch $ROOT/switches/{eew,quake,jmawarn}"

# 3) LaunchAgents 配置&再ロード(__ROOT__/__PYTHON__ を実値に置換)
mkdir -p "$LA" "$ROOT/logs"
pkill -f 'VOICEVOX.app/Contents/Resources/vv-engine/run' 2>/dev/null || true
reload_agent() {  # 1:agent名 2:running確認(yes/no)
  local a="$1" check="$2"
  local dst="$LA/com.zundamon.$a.plist"
  sed -e "s#__ROOT__#$ROOT#g" -e "s#__PYTHON__#$PYREAL#g" \
      "$ROOT/launchd/com.zundamon.$a.plist" > "$dst"
  # bootout は非同期。微小待機(sleep不使用)+リトライで確実に再ロード
  launchctl bootout "$DOMAIN/com.zundamon.$a" 2>/dev/null || true
  perl -e 'select(undef,undef,undef,0.6)' 2>/dev/null || true
  local ok=0 t
  for t in 1 2 3 4 5; do
    launchctl bootstrap "$DOMAIN" "$dst" 2>/dev/null && { ok=1; break; }
    perl -e 'select(undef,undef,undef,0.5)' 2>/dev/null || true
  done
  [ $ok -eq 1 ] || launchctl load -w "$dst" 2>/dev/null || true
  if [ "$check" = "yes" ]; then
    launchctl print "$DOMAIN/com.zundamon.$a" >/dev/null 2>&1 \
      && echo "   起動: com.zundamon.$a" || echo "   !! 失敗: com.zundamon.$a (logs/$a.log)"
  else
    echo "   登録: com.zundamon.$a"
  fi
}
for a in $KEEPALIVE_AGENTS; do reload_agent "$a" yes; done

# 4) 起動挨拶の事前キャッシュ + startup(一回実行エージェント)
printf "   エンジン起動待ち(挨拶の事前キャッシュ用)... "
curl -s --retry 30 --retry-delay 1 --retry-connrefused --max-time 90 \
  http://127.0.0.1:50021/version >/dev/null 2>&1 && echo OK || echo skip
"$PYREAL" -c "import sys; sys.path.insert(0,'$ROOT'); import core,phrases; sp=core.ZundaSpeaker(); [sp.synth(t) for t in phrases.STARTUP_ALL]" 2>/dev/null \
  && echo "   挨拶を事前キャッシュ(朝/昼/夜)" || echo "   事前キャッシュは初回ログイン時に"
reload_agent startup no

# 5) クイックアクション(任意のホットキー読み上げ)
mkdir -p "$SVC"
rm -rf "$SVC/ZundamonRead.workflow"
cp -R "$ROOT/hotkey/ZundamonRead.workflow" "$SVC/ZundamonRead.workflow" 2>/dev/null || true
/System/Library/CoreServices/pbs -update 2>/dev/null || true

# 6) ダブルクリック操作ボタンを生成
"$ROOT/make_buttons.sh" "$ROOT" >/dev/null 2>&1 && echo "   操作ボタン生成: $ROOT/ボタン/" || echo "   ボタン生成スキップ"

echo "   フルディスクアクセス対象(通知用): $PYREAL"
echo "==> 完了なのだ!  操作は $ROOT/ボタン/ の中のボタンをダブルクリック"

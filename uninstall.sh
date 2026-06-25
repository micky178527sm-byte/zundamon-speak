#!/bin/zsh
# zundamon-speak アンインストーラ。常駐とコマンドとサービスを撤去する。
# (VOICEVOX.app 本体とキャッシュは残す。完全削除は最後の行を参照)
ROOT="$(cd -P "$(dirname "$0")" && pwd)"
LA="$HOME/Library/LaunchAgents"
DOMAIN="gui/$(id -u)"
AGENTS=(engine time system notify startup weather)

echo "==> zundamon-speak uninstall"
for a in $AGENTS; do
  launchctl bootout "$DOMAIN/com.zundamon.$a" 2>/dev/null || launchctl unload "$LA/com.zundamon.$a.plist" 2>/dev/null || true
  rm -f "$LA/com.zundamon.$a.plist"
  echo "   removed agent: com.zundamon.$a"
done
pkill -f 'VOICEVOX.app/Contents/Resources/vv-engine/run' 2>/dev/null || true
rm -f /usr/local/bin/zundamon /usr/local/bin/zundamon-read
rm -rf "$HOME/Library/Services/ZundamonRead.workflow"
echo "   removed commands + quick action"
echo "==> 撤去完了。VOICEVOX.app と $ROOT は残してある。"
echo "    完全削除する場合:  rm -rf '$ROOT' && rm -rf /Applications/VOICEVOX.app"

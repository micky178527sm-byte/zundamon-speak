#!/bin/zsh
# make_buttons.sh — ダブルクリックで使える操作ボタン(.app)を生成する。
# osacompile でローカル生成するので、Terminal 窓も Gatekeeper の警告も出ない。
# install.sh から呼ばれる(引数: プロジェクトルート)。
ROOT="${1:-$(cd -P "$(dirname "$0")" && pwd)}"
CTL="$ROOT/bin/zundamon-ctl"
OUT="$ROOT/ボタン"
mkdir -p "$OUT"

mkbtn() {  # 1:ファイル名 2:ctl引数 3:ダイアログ文
  local name="$1" arg="$2" msg="$3"
  local app="$OUT/$name.app"
  local src; src="$(mktemp).applescript"
  # do shell script の中はシングルクォートでパスを囲む(空白対策)
  cat > "$src" <<APPLESCRIPT
do shell script "'$CTL' $arg"
display dialog "$msg" buttons {"OK"} default button 1 with title "ずんだもん" with icon note giving up after 5
APPLESCRIPT
  rm -rf "$app"
  osacompile -o "$app" "$src" 2>/dev/null && echo "  生成: $name.app" || echo "  失敗: $name.app"
  rm -f "$src"
}

mkbtn "① ずんだもんを始める"       start      "ずんだもんが喋り始めるのだ！"
mkbtn "② ぜんぶ黙らせる"           stop       "ずんだもんを黙らせたのだ。「①始める」でまた喋るのだ"
mkbtn "③ 通知の読み上げを止める"     notify-off "通知の読み上げをオフにしたのだ"
mkbtn "④ 通知の読み上げを再開"       notify-on  "通知の読み上げをオンにしたのだ"
mkbtn "⑤ ちゃんと動くかテスト"       test       "テストで一言喋ったのだ。聞こえたのだ？"

# 使い方メモも置く
cat > "$OUT/つかいかた.txt" <<'TXT'
ずんだもん 操作ボタン

このフォルダの中のボタンをダブルクリックするだけで操作できます。

① ずんだもんを始める … 喋るようにする(普段はこれだけでOK)
② ぜんぶ黙らせる     … 一時的に全部黙らせる(①でまた喋る)
③ 通知の読み上げを止める … 通知だけ読まなくする
④ 通知の読み上げを再開   … 通知の読み上げを戻す
⑤ ちゃんと動くかテスト   … 一言喋ってテスト

※ よく使うボタンは Dock やデスクトップにドラッグしておくと便利です。
TXT
echo "  使い方メモ: つかいかた.txt"

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

mkbtn_pick() {  # 地域を選んで気象警報をオンにする専用ボタン(choose from list)
  local name="$1" app="$OUT/$1.app"
  local src; src="$(mktemp).applescript"
  cat > "$src" <<APPLESCRIPT
set theList to paragraphs of (do shell script "'$CTL' pref-list")
set chosen to (choose from list theList with prompt "お住まいの都道府県を選ぶのだ（気象警報の地域）" default items {"東京都"} with title "ずんだもん")
if chosen is false then return
set pref to item 1 of chosen
do shell script "'$CTL' warn-on " & quoted form of pref
display dialog "気象警報をオンにしたのだ（" & pref & "）" buttons {"OK"} default button 1 with title "ずんだもん" with icon note giving up after 5
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
# --- 日本向け防災(任意) ---
mkbtn "⑥ 地震速報を始める"         quake-on   "地震速報をオンにしたのだ（緊急地震速報と地震情報）"
mkbtn "⑦ 地震速報を止める"         quake-off  "地震速報をオフにしたのだ"
mkbtn_pick "⑧ 気象警報を始める（地域を選ぶ）"
mkbtn "⑨ 気象警報を止める"         warn-off   "気象警報をオフにしたのだ"

# 使い方メモも置く
cat > "$OUT/つかいかた.txt" <<'TXT'
ずんだもん 操作ボタン

このフォルダの中のボタンをダブルクリックするだけで操作できます。

① ずんだもんを始める … 喋るようにする(普段はこれだけでOK)
② ぜんぶ黙らせる     … 一時的に全部黙らせる(①でまた喋る)
③ 通知の読み上げを止める … 通知だけ読まなくする
④ 通知の読み上げを再開   … 通知の読み上げを戻す
⑤ ちゃんと動くかテスト   … 一言喋ってテスト

── 日本の防災(使いたい人だけ) ──
⑥ 地震速報を始める … 緊急地震速報＋地震情報を声で知らせる(日本向け)
⑦ 地震速報を止める … ⑥をオフにする
⑧ 気象警報を始める(地域を選ぶ) … メニューから都道府県を選ぶだけ
⑨ 気象警報を止める … ⑧をオフにする
  ※地震速報は非公式の無料サービス経由で遅延あり。本命はスマホ内蔵の緊急地震速報です。

※ よく使うボタンは Dock やデスクトップにドラッグしておくと便利です。
TXT
echo "  使い方メモ: つかいかた.txt"

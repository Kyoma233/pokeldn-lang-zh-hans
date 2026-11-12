#!/usr/bin/env bash
# 针对某个 pokeldn 版本检查未翻译内容，全部译完后才打包签名。
# 用法: tools/release.sh vX.Y.Z [包版本号，默认 <tag去v>-zh.1]
# 需要: git、python3、签名私钥 POKELDN_ZH_KEY（默认 ~/.pokeldn-keys/pokeldn-zh-signing.pem）
# 检查未通过时写入 todo 文件并退出 1，不打包。补译后先跑 merge_todo.py / translate_docs.py，再重新执行本脚本。
# 打包成功后用 tools/publish.sh 提交、推送、发 Release。
set -euo pipefail
cd "$(dirname "$0")"
TAG=${1:?usage: release.sh vX.Y.Z [version]}
VER=${2:-${TAG#v}-zh.1}
KEY=${POKELDN_ZH_KEY:-$HOME/.pokeldn-keys/pokeldn-zh-signing.pem}
ROOT=$(cd .. && pwd)
mkdir -p work
[ -d work/pokeldn/.git ] || git clone -q https://github.com/Decryptu/pokeldn work/pokeldn
git -C work/pokeldn fetch -q --tags origin && git -C work/pokeldn checkout -q -f "$TAG"
[ -x work/venv/bin/python ] || { python3 -m venv work/venv && work/venv/bin/pip -q install pycryptodome; }
if ! work/venv/bin/python check_l10n.py work/pokeldn --write-todo | tee "work/untranslated-$TAG.txt"; then
  echo "还有未完成的翻译，见 tools/todo.toml、todo-messages.toml、todo-docs.txt。"
  echo "文案/标题译完后运行: python3 tools/merge_todo.py"
  echo "文档译完后运行: python3 tools/translate_docs.py"
  echo "然后再执行: tools/release.sh $TAG"
  exit 1
fi
sed -i "s/^version = .*/version = \"$VER\"/" "$ROOT/plugin/plugin.toml"
sed -i "s/适配 pokeldn v[0-9.]*/适配 pokeldn $TAG/" "$ROOT/plugin/plugin.toml"
N=$(work/venv/bin/python -c "import tomllib,pathlib; print(len(tomllib.loads(pathlib.Path(r'$ROOT/plugin/strings.toml').read_text(encoding='utf-8'))))")
sed -i "s/翻译了全部 [0-9]* 条/翻译了全部 $N 条/" "$ROOT/README.md"
sed -i "s/适用版本：pokeldn v[0-9.]*/适用版本：pokeldn $TAG/" "$ROOT/README.md"
OUT="$ROOT/dist/pokeldn-zh-hans-$VER.pokeplugin"
mkdir -p "$ROOT/dist"
(cd work/pokeldn && ../venv/bin/python scripts/pack_plugin.py "$ROOT/plugin" -o "$OUT" --key "$KEY")
cp "$OUT" "${OUT%.pokeplugin}.zip"
(cd work/pokeldn && ../venv/bin/python scripts/plugin_source.py "$OUT" -o "$ROOT/pokeldn-source.json" --name "pokeldn 简体中文" \
   --download "https://github.com/Kyoma233/pokeldn-lang-zh-hans/releases/download/v$VER/{file}")
echo "打包完成: $OUT"
echo "发布: tools/publish.sh $TAG"

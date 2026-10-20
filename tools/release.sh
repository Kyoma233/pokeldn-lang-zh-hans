#!/usr/bin/env bash
# 针对某个 pokeldn 版本检查未翻译字符串，并打包签名的语言包。
# 用法: tools/release.sh v0.34.0 [包版本号，默认 <tag去v>-zh.1]
# 需要: git、python3.13+、签名私钥 POKELDN_ZH_KEY（默认 ~/.pokeldn-keys/pokeldn-zh-signing.pem）
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
work/venv/bin/python check_untranslated.py work/pokeldn --write-todo | tee "work/untranslated-$TAG.txt" | head -30
sed -i "s/^version = .*/version = \"$VER\"/" "$ROOT/plugin/plugin.toml"
sed -i "s/适配 pokeldn v[0-9.]*/适配 pokeldn $TAG/" "$ROOT/plugin/plugin.toml"
OUT="$ROOT/dist/pokeldn-zh-hans-$VER.pokeplugin"
mkdir -p "$ROOT/dist"
(cd work/pokeldn && ../venv/bin/python scripts/pack_plugin.py "$ROOT/plugin" -o "$OUT" --key "$KEY")
cp "$OUT" "${OUT%.pokeplugin}.zip"
(cd work/pokeldn && ../venv/bin/python scripts/plugin_source.py "$OUT" -o "$ROOT/pokeldn-source.json" --name "pokeldn 简体中文" \
   --download "https://github.com/Kyoma233/pokeldn-lang-zh-hans/releases/download/v$VER/{file}")
echo "打包完成: $OUT"
echo "发布: git commit + push，然后 gh release create v$VER $OUT ${OUT%.pokeplugin}.zip"

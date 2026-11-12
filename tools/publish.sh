#!/usr/bin/env bash
# 在 release.sh 打包成功后：提交、推送、创建 GitHub Release，并确认 .pokeplugin 下载返回 200。
# 用法: tools/publish.sh vX.Y.Z [包版本号，默认 <tag去v>-zh.1]
# 不会把文件拷到本机。已存在的同名 Release 不会覆盖。
set -euo pipefail
cd "$(dirname "$0")"
TAG=${1:?usage: publish.sh vX.Y.Z [version]}
VER=${2:-${TAG#v}-zh.1}
ROOT=$(cd .. && pwd)
PY=${ROOT}/tools/work/venv/bin/python
[ -x "$PY" ] || PY=python3
cd "$ROOT"

"$PY" tools/check_l10n.py tools/work/pokeldn

OUT="$ROOT/dist/pokeldn-zh-hans-$VER.pokeplugin"
ZIP="${OUT%.pokeplugin}.zip"
[ -f "$OUT" ] && [ -f "$ZIP" ] || { echo "找不到 $OUT 或 $ZIP，先跑 tools/release.sh $TAG"; exit 1; }

plugin_ver=$(sed -n 's/^version = "\(.*\)"/\1/p' plugin/plugin.toml | head -1)
[ "$plugin_ver" = "$VER" ] || { echo "plugin.toml version=$plugin_ver，与 $VER 不一致"; exit 1; }

git add -- plugin/strings.toml plugin/messages.toml plugin/terms.toml plugin/docs plugin/plugin.toml \
        pokeldn-source.json README.md tools/strings.en.snapshot.toml

if git diff --cached --quiet; then
  echo "没有要提交的文件变更"
else
  git commit -m "适配 pokeldn $TAG"
fi

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" = "HEAD" ]; then
  echo "当前不在分支上，拒绝推送"
  exit 1
fi
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "还有未提交的变更，先处理后再发布"
  git status -sb
  exit 1
fi
git push origin "$branch"

if gh release view "v$VER" --repo Kyoma233/pokeldn-lang-zh-hans >/dev/null 2>&1; then
  echo "Release v$VER 已存在，不覆盖"
else
  gh release create "v$VER" "$OUT" "$ZIP" \
    --repo Kyoma233/pokeldn-lang-zh-hans \
    --title "v$VER" \
    --notes "适配 pokeldn $TAG"
fi

URL="https://github.com/Kyoma233/pokeldn-lang-zh-hans/releases/download/v$VER/pokeldn-zh-hans-$VER.pokeplugin"
code=""
for i in 1 2 3 4 5 6; do
  code=$(curl -sI -L -o /dev/null -w "%{http_code}" "$URL")
  [ "$code" = "200" ] && break
  sleep 2
done
[ "$code" = "200" ] || { echo "下载校验失败: $URL -> HTTP $code"; exit 1; }
echo "已发布: https://github.com/Kyoma233/pokeldn-lang-zh-hans/releases/tag/v$VER"
echo "下载可达: $URL (HTTP 200)"

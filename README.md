# pokeldn 简体中文语言包

[pokeldn](https://github.com/Decryptu/pokeldn) 的简体中文（zh-Hans）语言包插件：界面文案共 1630 条（全部已翻译），另有一份游戏术语表，宝可梦术语采用官方简中译名。宝可梦、招式、道具的名称由 pokeldn 自带的 PKHeX 按简体中文显示。

- 兼容版本：**pokeldn v0.33.0**（插件 API 1.9）。在更新的 pokeldn 上也能用，新增的文案会显示为英文。
- 插件 ID：`pokeldn-zh-hans`，版本 `0.33.0-zh.1`
- 签名指纹：`X4FQ-F3TF-VG5N-LQZG`（以后每次更新都会用同一把密钥签名）

## 安装（桌面版和安卓版步骤相同，用官方 APK 即可，不需要改过的版本）

### 方法一：下载文件安装
1. 从 [Releases](https://github.com/Kyoma233/pokeldn-lang-zh-hans/releases) 下载 `pokeldn-zh-hans-0.33.0-zh.1.pokeplugin`
   （同一个文件也提供了 `.zip` 版本。安卓文件选择器认的是文件扩展名，如果选不到 .zip，就用 .pokeplugin 那个）。
2. 打开 pokeldn → **Plugins**（插件）→ **Add a plugin**（桌面版也可以直接把文件拖进窗口）→ 选择这个文件。
3. 看完风险说明后，勾选确认，点 **Install**。
4. **Settings → App language**（设置 → 应用语言）里选 **简体中文**，然后**重启 pokeldn**。

### 方法二：添加插件源（之后可以在应用里一键更新）
1. Plugins → **Sources** → 输入 `Kyoma233/pokeldn-lang-zh-hans` 并添加。
2. **Browse** → 简体中文 → **Install**，再按上面第 4 步选择语言并重启。

> 语言包不会自动跟随系统语言生效，需要在设置里手动选一次。没翻译的文案会显示英文。

## 维护（上游发布新版本时）
```sh
tools/release.sh v0.34.0            # 拉取上游指定 tag，列出新增/改动的字符串（写入 tools/todo.toml），并打包签名
# 把 tools/todo.toml 里的英文翻成中文（{value0}、{count} 这类占位符要原样保留）
python3 tools/merge_todo.py tools/work/pokeldn
tools/release.sh v0.34.0            # 重新打包，输出 dist/*.pokeplugin、*.zip，同时更新 pokeldn-source.json
git commit -am "zh: v0.34.0" && git push
gh release create v0.34.0-zh.1 dist/pokeldn-zh-hans-0.34.0-zh.1.pokeplugin dist/pokeldn-zh-hans-0.34.0-zh.1.zip
```
签名私钥默认放在 `~/.pokeldn-keys/pokeldn-zh-signing.pem`，也可以用环境变量 `POKELDN_ZH_KEY` 指定。**私钥不要提交到仓库**，丢了就没法给已安装的用户发更新。

## 许可证
AGPL-3.0，与上游 pokeldn 相同。宝可梦相关名称归 Nintendo / Creatures / GAME FREAK 所有。

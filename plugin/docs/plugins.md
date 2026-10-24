---
title: Plugins
---

# 插件

插件会向 pokeldn 添加工具、游戏、电台和对战服务器，并且可以加入或托管自己的 LDN 网络。它是一个 Python 文件文件夹，带有 `plugin.toml`，以一个 `.pokeplugin` 文件发布。pokeldn 不分发、审查或支持第三方插件。

代码：`pokeldn/plugins.py`（加载器和 API）、`pokeldn/app/plugin_store.py`（包）、`pokeldn/ldn/radios.py`（电台查找）、`gui/views/plugins.py`（该页面）。示例：`examples/plugins/hello`（一个工具）和 `examples/plugins/test_kit`（API 的每个部分）。

## 安装插件

在侧边菜单底部的**插件**页面，在**浏览**下按**安装**，或将 `.pokeplugin` 拖到**已安装**上或按**添加插件**；然后接受风险提示界面。其工具会出现在游戏页面，标记为“插件: ...”。每个插件有一张卡片，可以开启和关闭、从文件更新、显示其文件夹和页面，以及移除它（可选连同其保存的数据）。每次安装和更新都会显示风险提示界面；手动复制的插件在首次开启时会弹出该提示。在启动期间关闭或冻结应用的插件会在下次启动时被关闭。

插件作为 Python 在 pokeldn 内运行，可以完全访问文件、密钥、网络和主板。包中的任何内容在安装并开启之前都不会运行。

### 来源

来源是已发布的插件 JSON 列表。**来源**会关注它们；**浏览**会列出它们的插件。`Decryptu/pokeldn-decrypt-plugins` 始终被关注。移除来源会保留其插件。

| 在来源下输入 | 读取的列表 |
|---|---|
| `OWNER/REPO` 或 `https://github.com/OWNER/REPO` | `https://raw.githubusercontent.com/OWNER/REPO/HEAD/pokeldn-source.json` |
| 以 `.json` 结尾的 HTTPS 地址 | 该文件 |
| 任何其他 HTTPS 地址 | 该文件夹中的 `pokeldn-source.json` |

```json
{"schema": 1, "name": "My plugins", "homepage": "https://github.com/me/my-plugins",
 "plugins": [{"id": "my-plugin", "name": "My plugin", "version": "1.0.0", "api": "1.6",
   "description": "...", "author": "me", "download": "https://.../my-plugin-1.0.0.pokeplugin",
   "sha256": "64 hex digits", "size": 46302, "icon": "https://.../icon.png", "homepage": "https://..."}]}
```

缺少 `id`、`version`、HTTPS `download` 或 `sha256` 的条目，或重复 id 的条目会被忽略；`schema` 不是 1 会被拒绝；SHA-256 不匹配的下载会在读取之前被拒绝；包的 id 与条目不同的也会被拒绝。风险提示界面和签名检查仍会运行。来源在启动时（设置，更新开启）和刷新时读取；最后的列表缓存在 `plugins/.source-cache/` 中，关注列表是 `plugins/.sources.json`。插件会从它来自的来源更新；从文件安装的插件，会从第一个列出它的来源更新，否则使用其 `updates`。

```bash
python scripts/plugin_source.py my-plugin-1.0.0.pokeplugin -o pokeldn-source.json --name "My plugins" \
    --download "https://github.com/me/my-plugins/releases/download/{id}-{version}/{file}"
```

已列出更高版本的条目会被保留。

### 护栏

两项检查会阻止明显的危害；两者都不是沙盒。安装屏幕会列出 Python 文件执行的操作：网络、其他程序、删除文件、本机代码（`ctypes`、`cffi`）、运行时代码（`exec`、`eval`、`compile`、`marshal`）、命名 `prod.keys`，或其无法读取的已编译文件。当插件的代码位于调用栈中时，审计钩子（`pokeldn/plugin_guard.py`）会对以下情况引发 `PermissionError`：

| 拒绝 | 允许 |
|---|---|
| 删除、清空、移动或覆盖插件文件夹之外的文件 | 在其文件夹、数据文件夹、库、会话、日志和临时文件夹中执行相同操作 |
| 直接或通过 shell 启动 `rm`、`del`、`rd`、`Remove-Item`、`shred`、`dd`、`format`、`mkfs`、`diskutil`、`diskpart`、`sudo`、`su` 及类似命令，或任何带有 `-delete` 或 `--no-preserve-root` 的命令 | 任何其他程序；在任何位置创建文件 |

插件调用的 pokeldn 代码会被检查；调用栈中没有插件的代码永远不会被检查。

## 制作插件

    my-plugin/
        plugin.toml        what the plugin is
        plugin.py          register(api): what it adds
        hello.py           a tool's script
        icon.png           optional, square, 96 x 96
        mylib_common.py    optional shared module (the folder is on sys.path: use a unique name)

```toml
id = "my-plugin"            # required: lowercase letters, digits, dots, dashes, underscores
name = "My plugin"
version = "1.0.0"           # compared on update
author = "Your name"
description = "Shown on the install screen and the card."
homepage = "https://example.org/my-plugin"   # optional
updates = "https://github.com/you/my-plugin" # optional, see Updates
api = "1.1"                 # required: lowest API needed; 1 means 1.0
icon = "icon.png"           # optional
library = "My files"        # optional (1.7), see A library
library_sort = "name"       # optional (1.8)
module = "plugin"           # optional; the module holding register()
exclude = ["tests"]         # optional; left out by pack_plugin.py
```

`plugin.toml` 或语言包文件如果嵌套深度超过 64 层数组或表，将不会被解析而直接拒绝
（`pokeldn.plugins.toml_loads`）；字符串和注释中的括号不计入。

当插件启用时，`register(api)` 会在应用中以及它启动的每次运行中执行：

```python
from pokeldn.plugins import Field, Game, Tool

def register(api):
    api.add_tool("frlg", Tool(
        "my-hello", "Hello", "hello.py", "Says hello.",       # key, name, script, summary
        ("Nothing to do on the console.", "Press Start."),    # console steps
        fields=(Field("--name", "Your name", default="Red"),),
        fixed=("--trainer", "{ot}"),                          # always passed
    ))
```

### 工具脚本

应用会导入脚本以执行 `build_parser()`（高级标签页），然后将其作为子进程在会话文件夹中运行。
实际工作应放在 `if __name__ == "__main__"` 下；顶层工作会破坏游戏页面。

| 脚本 | 应用 |
|---|---|
| 打印一行 | 显示在输出中 |
| 打印 `[done] trade N complete`（`pokeldn.ldn.show_done()`） | 勾掉一个排队中的交换 |
| 退出码为 0 / 非 0 或抛出异常 | 完成 / 失败并显示回溯 |
| 收到 `KeyboardInterrupt` | 已按下停止；请在 15 秒内退出，否则进程会被结束 |
| `pokeldn.popup`（1.2）、`popup.choose`（1.7） | 在任何页面上弹出弹窗；回答会返回 |
| `pokeldn.progress.show(done, total, title, unit)`（1.7） | 显示带有速率和剩余时间的进度条（[进度](gui.md#progress)） |
| `pokeldn.panel`（1.8） | 状态卡片和资料库备注（[状态卡片](#status-cards-18)） |

弹窗会立即返回其 id；回答稍后以回调形式到达，可在任意线程上触发：

```python
answers = queue.Queue()
popup.set_dispatcher(answers.put)       # run callbacks from the loop below
asked = popup.confirm("Trade the shiny?", "Your partner offers a shiny Gholdengo.", "Trade", "Skip",
                      on_agree=lambda: print("trading"), on_disagree=lambda: print("skipping"),
                      tone="warning")
while not finished():
    try:
        answers.get(timeout=0.5)()
    except queue.Empty:
        pass
popup.cancel(asked)                     # closes it; no callback fires
```

### 插件可以导入的内容

发布版应用自带 Python 3.13，且没有 `pip`：

| 内容 | 来源 |
|---|---|
| 标准库 | 已捆绑，但 `multiprocessing`、`tkinter`、`curses`、`venv`、`ensurepip`、`profile`、`cProfile`、`pstats`、`trace`、`compileall`、`modulefinder`、`pyclbr`、`tabnanny` 以及其他平台的模块除外（`scripts/pack_app.py`、`PLUGIN_STDLIB`） |
| `trio`、`pycryptodome`（`Crypto`）、`zstandard`、`pyserial`（`serial`）、`websockets`、`certifi`、`bleak`、`unicorn`、`flet` | pokeldn 自身的依赖，版本与 `requirements.txt` 一致 |
| `ldn`、`pokeldn` | 仅下表中列出的内容为稳定接口 |
| 纯 Python 模块 | 插件自己的文件夹 |

编译型包（`numpy`、`Pillow`）只在已安装它们的源码运行环境中可用。

### 字段

| `kind` | 输入 | 传递为 |
|---|---|---|
| `text`（默认） | 文本框 | `--flag VALUE` |
| `number` | 数字框 | `--flag VALUE` |
| `choice` | 下拉框，选项为 `choices=((value, label), ...)` | `--flag VALUE` |
| `switch` | 开/关开关 | 开启时传递 `--flag` |
| `file` | 文件选择器，`exts=("bin",)` | `--flag PATH` |

`help=`、`default=` 和 `hidden=True`（高级标签页）适用于任何字段；其余内容见
`pokeldn/app/catalog.py`。`Field.identity`（1.5）是已翻译位置字段的稳定设置键。
`fixed` 可以包含 `{ot}`、`{tid}`、`{sid}`、`{language}`、`{gender}`、`{received}`、`{stamp}` 和
`{keys}`（1.7，设置中的 `prod.keys`；接受 `--keys` 的解析器无论如何都会得到它）。

### 插件保留的内容

更新会替换整个文件夹。需要长期保存的文件应放入 `api.data`，或从脚本中放入
`pokeldn.plugins.data_folder("my-plugin")`：即 `plugin-data/<id>`，仅在卸载时询问后才删除。

### 资料库（1.7）

`library = "My files"` 对应 `Documents/pokeldn/My files`（设置了 `POKELDN_DATA` 时在其下），由
`api.library` 或 `pokeldn.plugins.library_folder("my-plugin")` 返回，并在首次使用时创建。守护规则
允许在其中任意写入，安装页面会显示其名称，移除插件时该文件夹会保留。游戏页面会在该插件的工具
下方列出其文件，玩家可以在那里添加、重命名和删除这些文件；以 `.` 开头或以 `.part` 结尾的名称
会被隐藏（可以先写入这类名称，再重命名）。顺序由玩家选择，否则按 `library_sort`（`name`、
`name-desc`、`date`、`date-desc`、`size`、`size-desc`）排序，再否则按 `date-desc`；名称按自然
顺序排序。名称最多包含 40 个字母、数字、空格、`.`、`-`、`_`；pokeldn 自己的文件夹（`Bank`、
`Saves`、`Received` 等）、Windows 设备名以及另一个插件的资料库会被拒绝。

### 状态卡片（1.8）

`pokeldn.panel` 会打印 `[panel]` 行；应用会在工具页面上绘制卡片，并在资料库文件上添加备注，
将其保存在 `plugin-panels/<id>.json` 中，并随插件一起删除。

```python
panel.show("console", "Pokémon: Let's Go, Pikachu!", ["System version\t23.0.1"],
           image=icon, chips=[("Version", "1.0.2")], tone="ok")
panel.annotate("Game 1.0.2.nsp", state="ok", text="Every signature checks", image=icon)
```

| 调用 | 显示 |
|---|---|
| `panel.show(id, title, lines=(), *, image=None, chips=(), tone="info")` | 显示卡片 `id`，替换上一个；一行可以是文本或 `label<TAB>value`；`tone` 可为 `info`、`ok`、`warning`、`error` |
| `panel.clear(id)` | 移除它 |
| `panel.annotate(name, *, state="ok", text="", image=None)` | 将资料库文件标记为 `ok`、`bad` 或 `checking` |
| `panel.unannotate(name)` | 移除备注 |

限制：id 为 1 到 32 个 `[a-z0-9_-]`；每个插件最多 8 张卡片；标题 80 个字符，12 行每行 200 个
字符，6 个芯片每个 40 个字符；图片为数据文件夹或资料库中的 PNG 或 JPEG，最大 2 MB。备注会跟随
文件名。超出限制会抛出 `ValueError`；无法解析的 `[panel]` 行会显示在输出中。

### 自有游戏

```python
api.add_game(Game("my-game", "My game", "Mine", "", (tool_one, tool_two)), icon="icon.png")
```

`Game(key, name, short, doc, tools)`；`api.add_tool("my-game", tool)` 可继续添加工具。

### 无线模块

`api.add_radio(scheme, install, label)` 会在插件页面的 **Radio** 下列出一个无线模块；运行在首次
无线调用之前会调用 `install(argument, log)`。`install` 需要调用 `ldn.wlan.set_factory(factory)`，
并传入一个异步上下文管理器，该管理器产出 `ldn.wlan.Factory`；参考实现见
`pokeldn/ldn/esp32_wlan.py`。应用通过 `POKELDN_RADIO=myradio:` 运行它；在命令行中，参数跟在
冒号之后。

### LDN 网络（1.7）

`pokeldn.ldn.network` 可以通过无线模块的 IPv4 协议栈（ESP32 板或 ldnrs）加入或主持网络。

```python
with network.join(COMM_ID, keys=args.keys, password=PASSPHRASE, name="My game") as net:
    net.add_protocol(6, lambda src, dst, segment: segments.put((src, segment)))
    while not net.send_ip(6, net.host_ip, first_segment):    # False until ARP resolves
        time.sleep(0.1)
```

| 名称 | 说明 |
|---|---|
| `join(comm_id, *, keys, password, nickname, app_version, name, log, timeout)` | 加入通告 `comm_id` 的网络；无人应答时抛出 `RuntimeError` |
| `host(comm_id, *, keys, password, nickname, application_data, scene_id, app_version, max_participants, channel, protocol, log, timeout)` | 开启一个可供主机加入的网络 |
| `Network.ip`、`.mac`、`.host_ip`、`.broadcast`、`.ssid`、`.comm_id`、`.application_data` | 地址与通告信息 |
| `Network.participants` | 已就座站点：`.index`、`.ip`、`.mac`、`.name` |
| `Network.add_protocol(number, handler)`、`.remove_protocol(number)` | 在无线循环中，对每个重组后的 IPv4 数据包调用 `handler(src_ip, dst_ip, payload)`；UDP（17）仍由协议栈处理；异常会丢弃数据包 |
| `Network.send_ip(protocol, dst_ip, payload)` | 发送一个数据包，按 1500 字节分片；ARP 尚未解析时返回 `False` |
| `Network.udp_socket(port)` | 提供 `sendto`、`recvfrom`、`setblocking`、`settimeout`、`fileno`、`close` |
| `Network.set_application_data(data)` | 发布新通告 |
| `Network.error`、`.close()` | 网络结束的原因；用于离开网络。它是一个上下文管理器 |
| `pokeldn.ldn.radio_lost()` | 无线模块离开的原因，可用于与停止操作区分 |

通过板子的吞吐量约为 0.5 MB/s。

### 对战服务器

对战服务器可以为 `bin/sv_host.py --raid-serve [NAME]` 运行《朱／紫》太晶团体战
（[主持对战](sv_raid.md#serving-the-battle)）。`api.add_battle_server("sv", name, factory, label)`
注册它；`factory(bootstrap, partners)` 在网络循环之外被调用，参数为引导字节和两个伙伴的 0x158
字节记录。

| 成员 | 作用 |
|---|---|
| `start(now)` | 第一帧；返回推动战斗的帧 |
| `run(until)` | 以每秒 30 帧运行到 `until`（至少一帧）；返回相同 |
| `t` | 服务器时钟，单位为秒 |
| `receive(slot, message)` | 来自 `slot` 的 32 字节头部加正文 |
| `sent(slot)` | 自上次调用以来为 `slot` 排队的消息 |

槽位：0 为程序的宝可梦，1 为头目，2 为主机，3 和 4 为伙伴。发生异常会停止主持，主机将自行进行
战斗。

### 提供的宝可梦编辑（1.10）

`api.add_offer_edit(game, edit, label="")` 会对 `game` 的内置启动器从文件准备出的每一只宝可梦
运行 `edit(record) -> record`（`game` 可为 `frlg`、`lgpe`、`swsh`、`bdsp`、`pla`、`sv`、`za`）：
包括交换提供的宝可梦、排队提供的宝可梦、团体战伙伴、为接收者重新制作的神秘礼物宝可梦。记录
就是 PKHeX 读取的文件字节（`pokeldn.pokemon.RECORD_SIZES`，无论是否加密）；
`SERVICE.check(game, path)` 可以读取一只。编辑函数返回要提供的记录。

```python
def rename(record):              # FireRed: the nickname at +0x08 is outside the checksum
    out = bytearray(record)
    out[8:18] = bytes((0xC6, 0xBE, 0xC8)) + b"\xff" * 7      # "LDN"
    return bytes(out)

def register(api):
    api.add_offer_edit("frlg", rename, "Renamer")
```

| 步骤 | |
|---|---|
| 1 | 启动器自身的编辑（提供选项、新 PID、游戏格式） |
| 2 | 按加载顺序执行每个插件的提供编辑；运行日志会记录 `the plugin LABEL edited the offer` |
| 3 | PKHeX 的合法性检查 |

PKHeX 的合法性检查是每次提供的最后一步，并且没有插件可以关闭它：如果 PKHeX 拒绝编辑结果，
运行会以 PKHeX 给出的原因停止。如果编辑函数抛出异常或未返回字节，运行会以插件标签停止。编辑
会在启动器读取文件时运行，并在交换期间神秘礼物宝可梦被重新制作时再次运行。

### 打包、测试、签名和更新

```bash
python scripts/pack_plugin.py my-plugin --key ~/my-plugin-signing.pem
POKELDN_PLUGINS=~/my-plugin python -m pokeldn --plugins            # lists plugins and load errors
POKELDN_PLUGINS=~/my-plugin python -m pokeldn my-hello -- --name Blue
POKELDN_PLUGINS=~/my-plugin python gui/main.py
```

`pack_plugin.py` 会写出 `my-plugin-1.0.0.pokeplugin`，并像应用一样检查它；隐藏文件和 `exclude`
中的内容不会被打包。任何 zip 都可以使用，只要 `plugin.toml` 位于其顶层或某一顶层文件夹中，
路径不得逃逸，也不得包含符号链接。`POKELDN_PLUGINS` 会为该进程及其启动的运行启用某个文件夹。
如果插件在 `register` 中抛出异常、需要应用不提供的 API 或重用了某个键，则不会添加任何内容，
其卡片会显示原因。Python 包也可以通过 `pokeldn.plugins` 入口点组进行注册。

`--key` 使用 Ed25519 密钥（首次使用时创建）签名，并打印指纹（`ABCD-EFGH-IJKL-MNOP`）。
`plugin.sig` 包含公钥以及针对 id、版本和每个文件 SHA-256 的签名。请妥善保管私钥并备份，同时
公布指纹。

| 应用遇到的情况 | 处理 |
|---|---|
| 签名不匹配 | 拒绝该文件 |
| 新的已签名插件 | 显示指纹并按 id 记住密钥 |
| 使用记住的密钥进行更新 | 显示“Signed by the same author” |
| 密钥不同，或已签名后变为未签名 | 用红色警告并要求再次确认 |
| 未签名，且从未签名 | 显示“Not signed” |

| `updates` | 应用会读取 |
|---|---|
| `https://github.com/OWNER/REPO` | 最新 release 的标签（`v1.3.0` 或 `1.3.0`）以及第一个 `.pokeplugin` |
| 任何其他 HTTPS 地址 | `{"version": "1.3.0", "url": "https://.../my-plugin-1.3.0.pokeplugin", "page": "..."}` |

在设置中开启“更新”后，这些地址会在启动和刷新时检查；检测到新版本会显示
**Update to 1.3.0**，点击后会下载并打开安装页面。仅 `127.0.0.1` 和 `localhost` 允许使用 HTTP。

## 语言包（1.5）

语言包是纯数据插件；`name` 会显示在设置、应用语言中，`locale` 是它的标签。

```toml
id = "community-zh-hans"
name = "简体中文"
version = "1.0.0"
api = "1.5"
locale = "zh-Hans"
strings = "strings.toml"
```

`strings.toml` 在带引号的键下保存文本值（`"bank.bank_676c47" = "宝可梦银行"`）。无效的 TOML、非文本值和错误的格式语法会在安装时被拒绝；损坏的语言包会回退到英文。选择语言包会将其打开并需要重新启动。缺少的键会使用其内联的英文默认值。像 `{value0}` 这样的占位符可以移动，但保留名称和规格；`{{` 和 `}}` 是字面大括号；无法成功格式化的翻译会使用英文。

```bash
python scripts/extract_strings.py [--check]     # writes pokeldn/app/data/strings.en.toml
python scripts/pack_plugin.py examples/plugins/pseudo -o pseudo.pokeplugin
python scripts/check_language_pack.py PACK_FOLDER   # what the pack lacks against this release
```

`check_language_pack.py` 会列出未翻译的字符串和工具帮助、该版本不再拥有的键，以及占位符与英文不同的翻译；若存在占位符差异，则退出码为 1。

测试会检查模板是否与源匹配，并拒绝具有两个默认值的键。语言包最初是模板的翻译副本；`examples/plugins/pseudo` 是一个部分伪区域设置。

### 额外资源（1.9）

```toml
api = "1.9"
messages = "messages.toml"
templates = "templates.toml"
terms = "terms.toml"
help = "help.toml"
documents = "docs"
font_family = "Noto Sans CJK SC"
```

| 条目 | 键 | 值 |
|---|---|---|
| `messages` | 模块的英文原文，逐字 | 其翻译 |
| `templates` | `"Could not open {path}: {reason}"` | 带有相同字段的翻译 |
| `terms` | 游戏术语（1 到 200 个字符，最多 10000 条） | 其翻译 |
| `help` | `"TOOL-KEY:--option"` | 该标志在高级选项卡中的描述 |
| `documents` | 按名称包含 `guide.md` 和 `docs/` 页面的文件夹 | |
| `font_family` | 一种字体，最多 100 个字符 | 文本字体；CJK 回退字体保持不变 |

路径保持在插件文件夹内。这些会翻译来自游戏模块、PKHeX 和插件的文本：消息会先在 `messages` 中整体查找，然后是 `templates`，接着逐句查找，最后在词边界处替换 `terms`。模板有 1 到 8 个由字面文本分隔的纯命名字段，最多 2048 个字符，按字面匹配，最长优先，作用于最长 4096 个字符的消息；名为 `term...` 或 `message...` 的字段自身也会被翻译，深度为 4。某个值如果整体是一个种类、招式、特性、性格、属性或精灵球名称，且没有任何术语覆盖，就采用 PKHeX 的名称。PKHeX 名称和合法性报告遵循 `ja`、`fr`、`it`、`de`、`es`、`ko`、`zh-Hans`、`zh-Hant` 的区域设置（`zh` 搭配 `TW`、`HK`、`MO` 时为 `zh-Hant`）。翻译后的页面在标题数量一致时保留英文锚点，否则用 `<a id="NAME"></a>` 设置一个；front-matter 中的 `title` 会在侧边栏中重命名页面。

文件名、宝可梦银行与队列摘要、GTS 列表、设置、会话日志、无线电输出以及 `[done]` 行保持英文。设置中的训练家语言会决定生成的宝可梦的语言。

## 插件测试套件

`examples/plugins/test_kit` 会添加自助测试（检查 API 的每个部分，打印 PASS 或 FAIL，并留下 Last self-test 卡片）、模拟会话（交换步骤和 `[done]` 行）、故意失败、火红／叶绿下的“来自插件的问候”，以及不传输任何内容的 Test Kit 无线电。

## 版本

API 采用 `major.level` 格式；插件的 `api` 是它所需的最低值。新增内容会提升 level（更高的需求会被拒绝，并提示“Update pokeldn”）；移除或含义变更会提升 major。仍受支持的旧 major 会列在 `DEPRECATED` 中并标注其最后发布版本；被放弃的 major 低于 `API_OLDEST` 并会被拒绝。插件自身的 `version` 只用于决定更新、重装或降级。

| API | 新增内容 |
|---|---|
| 1.0 | `add_tool`, `add_game`, `add_radio`, `folder`, `version` |
| 1.1 | `api.data`, `api.level`, `pokeldn.plugins.data_folder(plugin_id)` |
| 1.2 | `pokeldn.popup` |
| 1.3 | 程序接口：构建器、礼物文件、PKHeX 和开发板 |
| 1.4 | 宝可梦银行导入、记录、目标、offer 以及交换完成 |
| 1.5 | 语言包插件和字符串查找 |
| 1.6 | `add_battle_server` |
| 1.7 | `pokeldn.ldn.network`, `pokeldn.ldn.radio_lost`, `library` 和 `api.library`, `pokeldn.popup.choose`, `pokeldn.progress`, `{keys}` 标记 |
| 1.8 | `pokeldn.panel`, `library_sort` |
| 1.9 | 语言包消息、模板、术语、工具帮助、文档和字体偏好 |
| 1.10 | `add_offer_edit` |

## API，版本 1

| 名称 | 作用 |
|---|---|
| `api.add_tool(game, tool)` | 一个 `Tool`，位于 `frlg`、`lgpe`、`swsh`、`bdsp`、`pla`、`sv`、`za` 或插件游戏下 |
| `api.add_game(game, icon="")` | 一个游戏分区 |
| `api.add_radio(scheme, install, label="")` | 一个无线电 |
| `api.add_battle_server(game, name, factory, label="")` | 一个团体战服务器（1.6） |
| `api.add_offer_edit(game, edit, label="")` | 在 PKHeX 检查之前，对内置启动器的每个 offer 所做的编辑（1.10，[Offer 编辑](#offer-edits-110)） |
| `api.folder` | 插件文件夹；对于包则为 None |
| `api.version`, `api.level` | 应用的 API，`1` 和 `10` |
| `api.data` | 保留的数据文件夹（1.1） |
| `api.library`, `pokeldn.plugins.library_folder(plugin_id)` | 库文件夹（1.7，[库](#a-library-17)） |
| `Tool`, `Field`, `Game` | 来自 `pokeldn.plugins` 的目录类型 |
| `pokeldn.ldn.show_done()` | 打印交换完成行 |
| `pokeldn.popup.acknowledge(title, text="", *, id, label="OK", on_ack, tone)` | 单按钮弹窗；返回 id（1.2，[弹窗](gui.md#pop-ups)） |
| `pokeldn.popup.confirm(title, text, agree, disagree, *, id, on_agree, on_disagree, on_dismiss, tone)` | 两个按钮；按 Esc 或点击外部会关闭；返回 id（1.2） |
| `pokeldn.popup.choose(title, text, options, *, id, on_choice, on_dismiss, tone)` | 2 到 8 个选项，`on_choice(index)`；返回 id（1.7） |
| `pokeldn.progress.show(done, total, title, unit="bytes")` | 一个进度条；`unit` 为 `bytes` 或 `items`（1.7） |
| `pokeldn.panel.show(id, title, lines=(), *, image, chips, tone)`, `clear(id)`, `annotate(name, *, state, text, image)`, `unannotate(name)` | 状态卡片（1.8，[状态卡片](#status-cards-18)） |
| `pokeldn.ldn.network` | LDN 网络（1.7，[LDN 网络](#ldn-networks-17)） |
| `pokeldn.ldn.radio_lost()` | 无线电离开的原因，或空字符串（1.7） |
| `pokeldn.popup.cancel(id)`, `available()`, `set_dispatcher(dispatch)` | 关闭弹窗；弹窗是否显示；回调在哪里运行（1.2） |

本表和下一表是受支持的接口；任何其他导入内容都可能在任何版本中更改。

## 程序接口（1.3，宝可梦银行在 1.4 加入，语言包在 1.5 加入）

插件或 pokeldn 检出副本上的独立程序可以使用这些；`tests/test_plugin_surface.py` 会解析每一项。

| 名称 | 作用 |
|---|---|
| `python -m pokeldn --list`, `python -m pokeldn TOOL -- ARGS` | 工具键；使用设置中的训练家运行 |
| `pokeldn.app.i18n.t(key, default, **fmt)`, `select(plugin_id)` | 字符串查找；选择一个语言包，或用 `""` 选择英文（1.5） |
| `pokeldn.app.catalog.GAMES` | 内置游戏及其 `Tool`；应用传递的标志会保留其名称 |
| `pokeldn.pokemon.SERVICE.species(game)`, `.names(game, kind)` | 种类、`moves`、`items`、`bag`、`held`、`balls`，以 `{"id", "name"}` 列表表示 |
| `pokeldn.pokemon.SERVICE.options(game, species, trainer)` | 用于某个 offer 的形态、性格、特性、道具和精灵球 |
| `pokeldn.pokemon.SERVICE.make(game, species, trainer, level, shiny, nickname, version, options)` | 一只合法宝可梦；返回值和 `"file"` |
| `pokeldn.pokemon.SERVICE.paste(game, text, trainer)` | 把 Showdown 配置解析为 `make` 的值并带 `errors` |
| `pokeldn.pokemon.BuilderError` | PKHeX 拒绝或缺失，并附带给玩家的一句话 |
| `pokeldn.pokemon.NATURES` | 按索引排列的 25 个性格名称 |
| `pokeldn.gifts.load(path, game=)`, `pokeldn.gifts.save(path, gift)` | `.pokegift`、`.wc3`、`.wc8`（[神秘礼物文件](gifts.md)） |
| `pokeldn.swsh.gift_builder.KINDS`, `PRESETS`, `PRESET`, `OUTFITS` | 剑／盾礼物类型、预设和服装 |
| `pokeldn.swsh.gift_builder.blank(**changes)`, `record(state)`, `compile(state)`, `describe(state, name)` | 表单状态、720 字节记录、礼物、玩家描述行；`ValueError` 会指出错误字段 |
| `pokeldn.swsh.events.load()`, `by_key()`, `gift(key)` | 官方剑／盾活动卡片 |
| `pokeldn.frlg.gift.builder.KINDS`, `PRESETS`, `PRESET`, `GIVERS`, `CARTRIDGES` | 火红／叶绿的类型、预设、赠送者、卡带 |
| `pokeldn.frlg.gift.builder.blank()`, `compile(state)`, `describe(state, name)` | 对神秘卡片、News 或控制台代码同理；`name` 会根据其卡带 id 取得种类 |
| `gui.board.ports()`, `identify(port, blink=)`, `detect_chip(port)` | 串口以及开发板的 `.firmware`、`.firmware_version`、`.protocol`、`.current` |
| `gui.board.download_firmware(say=)`, `image_for(kind, chip)`, `image_version(path)`, `flash(port, kind=)` | 已检查的发布镜像和刷写 |
| `pokeldn.app.bank.library()` | 默认的宝可梦银行文件夹；列出内容不会创建它（1.4） |
| `pokeldn.app.bank.Entry`, `Imported`, `ImportedPokemon` | 宝可梦银行结果类型（1.4） |
| `pokeldn.app.bank.Imported.count(state)` | 状态中的结果数量（1.4） |
| `pokeldn.app.bank.entries(folder=)`, `find(entry_id, folder=)`, `data(entry)` | 记录按最新在前排列、一个或 `None`、它的字节（1.4） |
| `pokeldn.app.bank.import_file(path, trainers, folder=)` | 导入宝可梦文件或存档；返回 `Imported`（1.4） |
| `pokeldn.app.bank.deposit(game, source, info, folder=)` | 将收到的文件存入宝可梦银行；返回 `Entry`，若已存入则返回 `None`（1.4） |
| `pokeldn.pokemon.SERVICE.check(game, path)` | PKHeX 检查结果，即用于 `deposit` 的 `info`（1.4） |
| `pokeldn.app.bank.destinations(entry, trainer)`, `offer(entry, game, trainer)` | 按游戏给出转换结果；转换后的 offer（1.4） |
| `pokeldn.app.bank.edit(entry, fields)`, `remove(entry_id, folder=)` | 编辑昵称、升级、招式、携带道具；删除一条记录（1.4） |
| `pokeldn.app.bank.TradeSession(offers, folder=)` | 本次运行中按顺序排列的 offer（1.4） |
| `pokeldn.app.bank.TradeSession.advance(count)` | 应用累计交换计数；`.completed` 是曾经见过的最高值（1.4） |
| `pokeldn.app.received.trades_done(line)` | `[done] trade N complete` 行中的计数，没有则为 `None`（1.4） |

要停止启动器运行，先向其 PID 发送 SIGINT，15 秒后再发送 SIGTERM；切勿使用 `pkill -f`。

## 银行集成（1.4）

外部前端使用 `pokeldn.app.bank`，并拥有自己的队列和进程；转换需要 PKHeX 辅助程序（从源码运行 `dotnet build -c Release services/pkhex`）。

| 类型 | 字段 |
|---|---|
| `Entry` | `id`, `path`（原生记录）, `game`, `species_id`, `shiny`, `summary`, `legal`, `tracker`, `created`（Unix 秒）, `origin`, `home_tracker`（`empty`、`made` 或 `""`，[HOME 追踪器设置](gui.md#the-home-tracker-setting)） |
| `Imported` | `name`, `save`, `pokemon` |
| `ImportedPokemon` | `where`, `species`, `species_id`, `shiny`, `state`（`banked`, `already`, `refused`）, `game`, `detail` |
| `destinations` value | 每个游戏：`ok`、`reason`、`home_tracker` |
| `offer` value | `file`, `summary`, `species`, `shiny`, `legal`, `encounter`, `moves`, `report`, `home_tracker`, `bank`（来源 id） |

`trainers` 将游戏键映射到 `{ot, tid, sid, language, gender}`。导入会记住所有曾导入过的记录。一个 offer 会保留 Bank 记录原样；将其 `file` 作为启动器的 `--offer-file` 传入，且不要加 `--fresh-pid`，并保留它直到运行结束。直接运行目录工具的脚本，因为 `python -m pokeldn TOOL` 不接受 offer。

```python
from pokeldn.app import bank, received

trainer = {"ot": "ASH", "tid": 1111, "sid": 2222, "language": 2, "gender": 0}
bank.import_file("main", {g: trainer for g in ("frlg", "lgpe", "swsh", "bdsp", "pla", "sv", "za")},
                 folder="tradebox-bank")
entry = next(iter(bank.entries(folder="tradebox-bank")), None)
if entry is None:
    raise ValueError("No Pokemon available in the Bank.")
if not bank.destinations(entry, trainer)["swsh"]["ok"]:
    raise ValueError("cannot go to Sword/Shield")
session = bank.TradeSession([bank.offer(entry, "swsh", trainer)], folder="tradebox-bank")

def on_launcher_line(line):
    if (count := received.trades_done(line)) is not None:
        session.advance(count)
```

每次运行一个 `TradeSession`，按确切的 offer 顺序，包含已构建的 offer。只向其提供已确认的数量；未完成的记录会保留。`advance` 在计数错误时抛出 `ValueError`，并且在 `OSError` 之后可以重试。文件错误会抛出 `OSError`；PKHeX 失败会抛出 `BuilderError`。`deposit` 信任 `SERVICE.check`；玩家文件通过 `import_file` 进入。`folder` 默认为 `library()`。导入前设置 `POKELDN_DATA` 以隔离所有文件。调用是同步的：请让 PKHeX 远离 UI 线程。每个 Bank 文件夹一个写入者；桌面应用旁的前端使用自己的文件夹。`TradeSession` 只更改 Bank。

---
title: Plugins
---

# 插件

插件为 pokeldn 添加工具、游戏、电台和战斗服务器，并能加入或自行托管一个 LDN 网络。它是一个包含 `plugin.toml` 的 Python 文件夹，以一个 `.pokeplugin` 文件发布。pokeldn 不分发、审核或支持第三方插件。

代码：`pokeldn/plugins.py`（加载器和 API）、`pokeldn/app/plugin_store.py`（包管理）、`pokeldn/ldn/radios.py`（电台查找）、`gui/views/plugins.py`（页面）。示例：`examples/plugins/hello`（一个工具）和 `examples/plugins/test_kit`（完整 API）。

## 安装插件

在**插件**（侧边菜单底部）下，按 **浏览** 下的 **安装**，或将 `.pokeplugin` 文件拖到 **已安装**，或按 **添加插件**；然后接受风险提示。其工具会出现在游戏页面上，标记为"插件：..."。每个插件都有一张卡片，可开启/关闭、从文件更新、显示其文件夹和页面，并移除（可选是否删除保存的数据）。每次安装和更新都会显示风险提示；手动复制的插件在首次开启时会要求确认。插件在启动时关闭或冻结应用的，会在下次启动时自动关闭。

插件以 Python 运行在 pokeldn 内部，可完全访问文件、密钥、网络和棋盘。包中的任何内容在安装并开启前都不会运行。

### 来源

来源是发布的插件 JSON 列表。**来源** 会跟随它们；**浏览** 会列出它们的插件。`Decryptu/pokeldn-decrypt-plugins` 永远会被跟随。移除来源不会删除其插件。

| 在来源下输入 | 读取的列表 |
|---|---|
| `OWNER/REPO` 或 `https://github.com/OWNER/REPO` | `https://raw.githubusercontent.com/OWNER/REPO/HEAD/pokeldn-source.json` |
| 以 `.json` 结尾的 HTTPS 地址 | 该文件 |
| 其他任何 HTTPS 地址 | 该文件夹中的 `pokeldn-source.json` |

```json
{"schema": 1, "name": "My plugins", "homepage": "https://github.com/me/my-plugins",
 "plugins": [{"id": "my-plugin", "name": "My plugin", "version": "1.0.0", "api": "1.6",
   "description": "...", "author": "me", "download": "https://.../my-plugin-1.0.0.pokeplugin",
   "sha256": "64 hex digits", "size": 46302, "icon": "https://.../icon.png", "homepage": "https://..."}]}
```

缺少 `id`、`version`、HTTPS `download` 或 `sha256` 的条目，或重复的 id 会被忽略；`schema` 不是 1 的会被拒绝；SHA-256 不匹配的下载在读取前会被拒绝；id 与条目不符的包会被拒绝。风险提示和签名检查仍会运行。来源在启动时（设置、更新开启）和刷新时读取；最后的列表缓存在 `plugins/.source-cache/`，跟随列表是 `plugins/.sources.json`。插件从其来源更新；从文件安装的插件，从第一个列出它的来源更新，否则从其 `updates` 字段更新。

```bash
python scripts/plugin_source.py my-plugin-1.0.0.pokeplugin -o pokeldn-source.json --name "My plugins" \
    --download "https://github.com/me/my-plugins/releases/download/{id}-{version}/{file}"
```

已以更高版本列出的条目会被保留。

### 安全措施

两种检查会阻止明显的危害；但这不是沙箱。安装屏幕会列出 Python 文件的行为：网络访问、调用其他程序、删除文件、使用原生代码（`ctypes`、`cffi`）、运行时代码（`exec`、`eval`、`compile`、`marshal`）、命名 `prod.keys`，或无法读取的编译文件。在插件代码在调用栈上时，审计钩子（`pokeldn/plugin_guard.py`）会在以下情况引发 `PermissionError`：

| 拒绝 | 允许 |
|---|---|
| 删除、清空、移动或覆盖插件文件夹外的文件 | 在其文件夹、数据文件夹、库、会话、日志和临时文件夹内执行相同操作 |
| 直接或通过 shell 启动 `rm`、`del`、`rd`、`Remove-Item`、`shred`、`dd`、`format`、`mkfs`、`diskutil`、`diskpart`、`sudo`、`su` 等命令，或任何带有 `-delete` 或 `--no-preserve-root` 的命令 | 其他任何程序；在任何地方创建文件 |

插件调用的 pokeldn 代码会被检查；没有插件在调用栈上的代码永远不会被检查。

## 制作插件

    my-plugin/
        plugin.toml        插件是什么
        plugin.py          register(api)：它添加了什么
        hello.py           工具的脚本
        icon.png           可选，正方形，96 x 96
        mylib_common.py    可选共享模块（文件夹在 sys.path 中：使用唯一名称）

```toml
id = "my-plugin"            # 必填：小写字母、数字、点、连字符、下划线
name = "My plugin"
version = "1.0.0"           # 更新时比较
author = "Your name"
description = "Shown on the install screen and the card."
homepage = "https://example.org/my-plugin"   # 可选
updates = "https://github.com/you/my-plugin" # 可选，参见 Updates
api = "1.1"                 # 必填：所需最低 API 版本；1 表示 1.0
icon = "icon.png"           # 可选
library = "My files"        # 可选（1.7），参见 A library
library_sort = "name"       # 可选（1.8）
module = "plugin"           # 可选；包含 register() 的模块
exclude = ["tests"]         # 可选；pack_plugin.py 打包时排除
```

嵌套超过 64 个数组或表格的 `plugin.toml` 或语言包文件会被拒绝不解析（`pokeldn.plugins.toml_loads`）；字符串和注释内的括号不计入。

`register(api)` 在插件开启时运行，包括在应用内以及每次启动的运行中：

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

### 工具的行（1.12）

游戏的列表显示每个活动的一行（参见 [The Games page](gui.md#the-games-page)）。没有 `activity` 的工具独占一行。设置了 `activity` 的工具加入该行，并由其 `variant` 按钮显示：

```python
Tool("my-lan-trade", "Trade over my LAN", "lan.py", "Trades over this computer's network.", (),
     activity="trade", variant=(("role", "host"), ("link", "lan")))
```

| `activity` | 对应的行 |
|---|---|
| `trade`, `gift`, `max-raid`, `lair`, `tera-raid`, `circle` | Trade, Mystery Gift, Max Raid, Dynamax Adventure, Tera Raid, Union Circle |

| axis | options | buttons |
|---|---|---|
| `role` | `host`, `join` | Your console: Joins (pokeldn hosts), Hosts (pokeldn joins) |
| `link` | `board`, `lan`, `online` | Connection: Board, Wi-Fi with no board, Online |
| `mode` | `quests`, `encounters` | Mode |

`pokeldn.app.catalog.AXES` 和 `ACTIVITIES` 是这些列表。`add_tool` 拒绝未知的 activity 或 option，以及另一个工具已占用的变体：应用永远无法显示它。

### 工具的脚本

应用导入脚本以获取 `build_parser()`（高级标签页），然后在会话文件夹中作为子进程运行。工作应放在 `if __name__ == "__main__"` 下；顶层工作会破坏 Games 页面。

| the script | the app |
|---|---|
| prints a line | shows it in the output |
| prints `[done] trade N complete` (`pokeldn.ldn.show_done()`) | ticks one queued trade off |
| exits 0 / non-zero or raises | done / failed with the traceback |
| receives `KeyboardInterrupt` | Stop was pressed; leave within 15 s or the process is ended |
| `pokeldn.popup` (1.2), `popup.choose` (1.7) | a pop-up over any page; the answer comes back |
| `pokeldn.progress.show(done, total, title, unit)` (1.7) | a bar with rate and time left ([Progress](gui.md#progress)) |
| `pokeldn.panel` (1.8) | status cards and library notes ([Status cards](#status-cards-18)) |

弹出窗口立即返回其 id；答案稍后以回调形式返回，可在任意线程上：

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

发布版应用捆绑 Python 3.13，且无 `pip`：

| what | from |
|---|---|
| the standard library | bundled, except `multiprocessing`, `tkinter`, `curses`, `venv`, `ensurepip`, `profile`, `cProfile`, `pstats`, `trace`, `compileall`, `modulefinder`, `pyclbr`, `tabnanny` and other platforms' modules (`scripts/pack_app.py`, `PLUGIN_STDLIB`) |
| `trio`, `pycryptodome` (`Crypto`), `zstandard`, `pyserial` (`serial`), `websockets`, `certifi`, `bleak`, `unicorn`, `flet` | pokeldn's own dependencies, at the versions in `requirements.txt` |
| `ldn`, `pokeldn` | only the tables below are stable |
| pure-Python modules | the plugin's folder |

编译包（`numpy`, `Pillow`）仅在具有它们的源码运行时中可用。

### 字段

| `kind` | the input | passed as |
|---|---|---|
| `text` (default) | a text box | `--flag VALUE` |
| `number` | a number box | `--flag VALUE` |
| `choice` | a dropdown of `choices=((value, label), ...)` | `--flag VALUE` |
| `switch` | an on/off switch | `--flag` when on |
| `file` | a file chooser, `exts=("bin",)` | `--flag PATH` |

`help=`, `default=` 和 `hidden=True`（高级标签页）适用于任意字段；其余内容见 `pokeldn/app/catalog.py`。`Field.identity`（1.5）是翻译后的位置字段的稳定设置键。`fixed` 可包含 `{ot}`, `{tid}`, `{sid}`, `{language}`, `{gender}`, `{received}`, `{stamp}` 和 `{keys}`（1.7，Settings 的 `prod.keys`；接受 `--keys` 的解析器无论如何都会获得它）。

### 插件保留的内容

更新会替换文件夹。持久文件应放在 `api.data` 或从脚本中使用 `pokeldn.plugins.data_folder("my-plugin")`：`plugin-data/<id>`，仅在移除时（如要求）删除。

### 库（1.7）

`library = "My files"` 是 `Documents/pokeldn/My files`（在设置 `POKELDN_DATA` 时位于其下），通过 `api.library` 或 `pokeldn.plugins.library_folder("my-plugin")` 获取，首次使用时创建。 guardrails 允许在其中进行任何写入，安装屏幕会命名它，移除插件时保留它。Games 页面在插件工具下列出其文件，玩家可添加、重命名和删除；以 `.` 开头或以 `.part` 结尾的名称会被隐藏（先写入以 `.part` 结尾的文件，然后重命名）。排序由玩家选择，否则按 `library_sort`（`name`, `name-desc`, `date`, `date-desc`, `size`, `size-desc`）排序，否则按 `date-desc`；名称按自然顺序排序。名称最多 40 个字母、数字、空格、`.`, `-`, `_`；pokeldn 自己的文件夹（`Bank`, `Saves`, `Received`...）、Windows 设备名和其他插件的库文件夹会被拒绝。

### 状态卡片（1.8）

`pokeldn.panel` 输出 `[panel]` 行；应用在工具页面上绘制卡片并在库文件上显示备注，保存在 `plugin-panels/<id>.json` 中，并随插件一起删除。

```python
panel.show("console", "Pokémon: Let's Go, Pikachu!", ["System version\t23.0.1"],
           image=icon, chips=[("Version", "1.0.2")], tone="ok")
panel.annotate("Game 1.0.2.nsp", state="ok", text="Every signature checks", image=icon)
```

| call | shows |
|---|---|
| `panel.show(id, title, lines=(), *, image=None, chips=(), tone="info")` | card `id`, replacing the last; a line is text or `label<TAB>value`; `tone` is `info`, `ok`, `warning`, `error` |
| `panel.clear(id)` | removes it |
| `panel.annotate(name, *, state="ok", text="", image=None)` | marks a library file `ok`, `bad` or `checking` |
| `panel.unannotate(name)` | removes the note |

限制：id 为 1 到 32 个 `[a-z0-9_-]`；每个插件最多 8 张卡片；标题最多 80 字符，12 行每行 200 字符，6 个芯片每个 40 字符；图像为 PNG 或 JPEG，最大 2 MB，位于数据文件夹或库中。备注跟随文件名。超过限制会引发 `ValueError`；无法读取的 `[panel]` 行会显示在输出中。

### 独占游戏

```python
api.add_game(Game("my-game", "My game", "Mine", "", (tool_one, tool_two)), icon="icon.png")
```

`Game(key, name, short, doc, tools)`；`api.add_tool("my-game", tool)` 添加更多工具。

### 电台

`api.add_radio(scheme, install, label)` 在插件下列出电台 **Radio**；运行时在首次无线电调用前调用 `install(argument, log)`。`install` 使用异步上下文管理器调用 `ldn.wlan.set_factory(factory)`，该管理器产出一个 `ldn.wlan.Factory`；`pokeldn/ldn/esp32_wlan.py` 是参考。应用以 `POKELDN_RADIO=myradio:` 运行；在命令行中，参数跟在冒号后。

### LDN 网络（1.7）

`pokeldn.ldn.network` 使用电台的 IPv4 栈（ESP32 板或 ldnrs）加入或主持网络。

```python
with network.join(COMM_ID, keys=args.keys, password=PASSPHRASE, name="My game") as net:
    net.add_protocol(6, lambda src, dst, segment: segments.put((src, segment)))
    while not net.send_ip(6, net.host_ip, first_segment):    # False until ARP resolves
        time.sleep(0.1)
```

| name | what it is |
|---|---|
| `join(comm_id, *, keys, password, nickname, app_version, name, log, timeout)` | joins the network advertising `comm_id`; `RuntimeError` when none answers |
| `host(comm_id, *, keys, password, nickname, application_data, scene_id, app_version, max_participants, channel, protocol, log, timeout)` | opens a network consoles join |
| `Network.ip`, `.mac`, `.host_ip`, `.broadcast`, `.ssid`, `.comm_id`, `.application_data` | addresses and advertisement |
| `Network.participants` | seated stations: `.index`, `.ip`, `.mac`, `.name` |
| `Network.add_protocol(number, handler)`, `.remove_protocol(number)` | `handler(src_ip, dst_ip, payload)` per reassembled IPv4 packet, on the radio loop; UDP (17) stays the stack's; exceptions drop the packet |
| `Network.send_ip(protocol, dst_ip, payload)` | one packet, fragmented at 1500; `False` while ARP is pending |
| `Network.udp_socket(port)` | `sendto`, `recvfrom`, `setblocking`, `settimeout`, `fileno`, `close` |
| `Network.set_application_data(data)` | a new advertisement |
| `Network.error`, `.close()` | why it ended; leaves. A context manager |
| `pokeldn.ldn.radio_lost()` | why the radio left, which tells it apart from Stop |

通过板载连接的吞吐量约为 0.5 MB/s。

### 对战服务器

对战服务器为 `bin/sv_host.py --raid-serve [NAME]` 运行朱 / 紫的团体战战斗（参见 [Serving the battle](sv_raid.md#serving-the-battle)）。`api.add_battle_server("sv", name, factory, label)` 注册它；`factory(bootstrap, partners)` 在网络循环之外用 bootstrap 字节和两个伙伴的 0x158 字节记录调用。

| member | does |
|---|---|
| `start(now)` | first frame; returns frames that moved the battle |
| `run(until)` | frames at 30/s up to `until` (at least one); same return |
| `t` | the server clock, seconds |
| `receive(slot, message)` | a 32-byte header plus body from `slot` |
| `sent(slot)` | messages queued for `slot` since the last call |

插槽：0 为程序的宝可梦，1 为老板，2 为玩家主机，3 和 4 为伙伴。异常会停止服务，玩家主机会与自己的宝可梦对战。

### 礼物编辑（1.10）

`api.add_offer_edit(game, edit, label="")` 对由 `game`（`frlg`, `lgpe`, `swsh`, `bdsp`, `pla`, `sv`, `za`）的内置启动器从文件准备的每个宝可梦运行 `edit(record) -> record`：交易礼物、排队中的礼物、团体战伙伴、为接收者重做的神秘礼物宝可梦。record 是文件中的字节，按照 PKHeX 读取（`pokeldn.pokemon.RECORD_SIZES`，加密或未加密）；`SERVICE.check(game, path)` 读取一个。编辑返回要提供的 record。

```python
def rename(record):              # FireRed: the nickname at +0x08 is outside the checksum
    out = bytearray(record)
    out[8:18] = bytes((0xC6, 0xBE, 0xC8)) + b"\xff" * 7      # "LDN"
    return bytes(out)

def register(api):
    api.add_offer_edit("frlg", rename, "Renamer")
```

| step | |
|---|---|
| 1 | the launcher's own edits (offer options, a fresh PID, a game's format) |
| 2 | each plugin's offer edit, in load order; the run logs `the plugin LABEL edited the offer` |
| 3 | PKHeX's legality check |

PKHeX 的合法性检查是每个礼物的最后一步，且没有插件能关闭它：如果编辑结果被 PKHeX 拒绝，则运行会以 PKHeX 的原因停止。编辑引发异常或返回无字节也会以插件标签停止。编辑在启动器读取文件时运行，并在交易过程中为神秘礼物宝可梦重做时再次运行。

### 打包、测试、签名和更新

```bash
python scripts/pack_plugin.py my-plugin --key ~/my-plugin-signing.pem
POKELDN_PLUGINS=~/my-plugin python -m pokeldn --plugins            # lists plugins and load errors
POKELDN_PLUGINS=~/my-plugin python -m pokeldn my-hello -- --name Blue
POKELDN_PLUGINS=~/my-plugin python gui/main.py
```

`pack_plugin.py` 生成 `my-plugin-1.0.0.pokeplugin` 并像应用一样检查它；隐藏文件和 `exclude` 保持排除。任何 zip 文件都可以使用，只需 `plugin.toml` 位于顶层或一个顶层文件夹中，且无路径逃逸和无符号链接。`POKELDN_PLUGINS` 为该进程及其运行启用一个文件夹。插件在 `register` 中引发异常、需要更高 API 或重复使用 key 都会添加失败，并在其卡片上显示原因。Python 包也可以通过 `pokeldn.plugins` 入口点组注册。

`--key` 使用 Ed25519 密钥（首次使用时创建）签名并打印其指纹（`ABCD-EFGH-IJKL-MNOP`）。`plugin.sig` 保存公钥及对 id、version 和每个文件的 SHA-256 签名。请妥善保管密钥并备份，同时发布指纹。

| the app sees | it |
|---|---|
| a signature that does not match | refuses the file |
| a new signed plugin | shows the fingerprint and remembers the key per id |
| an update with the remembered key | shows "Signed by the same author" |
| another key, or unsigned after signed | warns in red and asks a second acknowledgement |
| unsigned, never signed | shows "Not signed" |

| `updates` | the app reads |
|---|---|
| `https://github.com/OWNER/REPO` | the latest release's tag (`v1.3.0` or `1.3.0`) and first `.pokeplugin` |
| any other HTTPS address | `{"version": "1.3.0", "url": "https://.../my-plugin-1.3.0.pokeplugin", "page": "..."}` |

在 Settings 中开启 Updates 后，这些会在启动和刷新时检查；新版本会显示 **Update to 1.3.0**，下载并打开安装屏幕。仅接受 `127.0.0.1` 和 `localhost` 的 HTTP。

## 语言包（1.5）

语言包是一种仅含数据插件；`name` 显示在设置、应用语言中，而 `locale` 是其标签。

```toml
id = "community-zh-hans"
name = "简体中文"
version = "1.0.0"
api = "1.5"
locale = "zh-Hans"
strings = "strings.toml"
```

`strings.toml` 在引号内的键下保存文本值（`"bank.bank_676c47" = "宝可梦银行"`）。安装时拒绝错误的 TOML、非文本值和错误的格式语法；损坏的包将回退到英文。选择一个包会启用它并需要重启。缺失的键使用其内联英文默认值。占位符如 `{value0}` 可能会移动但保留其名称和规范；`{{` 和 `}}` 是字面大括号；格式化失败的翻译将使用英文。

```bash
python scripts/extract_strings.py [--check]     # 写入 pokeldn/app/data/strings.en.toml
python scripts/pack_plugin.py examples/plugins/pseudo -o pseudo.pokeplugin
python scripts/check_language_pack.py PACK_FOLDER   # 该包相比本次发布缺少的内容
```

`check_language_pack.py` 列出未翻译的字符串和工具帮助、发布版本不再包含的键，以及占位符与英文不同的翻译；在占位符差异时退出代码为 1。

测试会检查模板是否匹配源文件，并拒绝具有两个默认值的键。一个包以翻译后的模板副本开始；`examples/plugins/pseudo` 是一个部分伪语言环境。

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
| `messages` | 某模块的英文文本，逐字 | 其翻译 |
| `templates` | `"Could not open {path}: {reason}"` | 具有相同字段的翻译 |
| `terms` | 游戏术语（1 至 200 字符，最多 10000） | 其翻译 |
| `help` | `"TOOL-KEY:--option"` | 该标志在高级选项卡的描述 |
| `documents` | 包含 `guide.md` 和 `docs/` 页面的文件夹 | |
| `font_family` | 字体，最多 100 字符 | 文本字体；CJK 回退仍保留 |

路径始终位于插件文件夹内。这些翻译来自游戏模块、PKHeX 和插件的文本：一条消息会先在 `messages` 中整体尝试，然后在 `templates` 中尝试，然后按句子尝试，最后在 `terms` 中替换词边界的内容。模板具有 1 至 8 个由字面文本分隔的普通命名字段，最多 2048 字符，按字面匹配，最长优先匹配，适用于最多 4096 字符的消息；名为 `term...` 或 `message...` 的字段本身会被翻译，递归深度为 4。一个值如果整体是某个种属、招式、能力、性格、类型或精球的名称，且没有术语覆盖它，则使用 PKHeX 的名称。PKHeX 的名称和合法性报告会根据 `ja`、`fr`、`it`、`de`、`es`、`ko`、`zh-Hans`、`zh-Hant` 地区设置（`zh` 与 `TW`、`HK`、`MO` 对应 `zh-Hant`）跟随地区。

翻译后的页面在标题数量匹配时保留英文锚点，否则通过 `<a id="NAME"></a>` 设置一个；前置元数据的 `title` 会在侧边栏中重命名页面。

文件名、Bank 和队列摘要、GTS 列表、设置、会话日志、广播输出和 `[done]` 行保持英文。设置中的训练师语言决定所构建宝可梦的语言。

## 插件测试套件

`examples/plugins/test_kit` 添加了自检（检查每个 API 部分，打印 PASS 或 FAIL，留下最后一次自检卡片）、模拟会话（交易步骤和 `[done]` 行）、故意失败、在火红／叶绿下显示 "Hello from a plugin"，以及 Test Kit 广播（不携带任何内容）。

## 版本

API 的格式为 `major.level`；插件的 `api` 是其所需的最低版本。一次添加会提升 level（更高需求将被拒绝并提示 "Update pokeldn"）；一次删除或含义改变会提升 major。仍在服务的旧 major 版本会在 `DEPRECATED` 中列出其最后一次发布；被丢弃的版本将低于 `API_OLDEST` 并被拒绝。插件自身的 `version` 仅决定更新、重新安装或降级。

| API | 添加内容 |
|---|---|
| 1.0 | `add_tool`, `add_game`, `add_radio`, `folder`, `version` |
| 1.1 | `api.data`, `api.level`, `pokeldn.plugins.data_folder(plugin_id)` |
| 1.2 | `pokeldn.popup` |
| 1.3 | 程序表面：构建器、礼物文件、PKHeX 和看板 |
| 1.4 | Bank 导入、记录、目的地、报价和交易完成 |
| 1.5 | 语言包插件和字符串查找 |
| 1.6 | `add_battle_server` |
| 1.7 | `pokeldn.ldn.network`, `pokeldn.ldn.radio_lost`, `library` 和 `api.library`, `pokeldn.popup.choose`, `pokeldn.progress`, `{keys}` 标记 |
| 1.8 | `pokeldn.panel`, `library_sort` |
| 1.9 | 语言包消息、模板、术语、工具帮助、文档和字体偏好 |
| 1.10 | `add_offer_edit` |
| 1.11 | 火红／叶绿 RNG：`lcg`, `rng_countdown.mon_from`, `scan`, `buffer_script.read_rng_trace` |
| 1.12 | `Tool` 的 `activity` 和 `variant`（参见 [A tool's row](#a-tools-row-112)） |

## API 版本 1

| 名称 | 含义 |
|---|---|
| `api.add_tool(game, tool)` | 在 `frlg`、`lgpe`、`swsh`、`bdsp`、`pla`、`sv`、`za` 或插件的游戏下添加一个 `Tool` |
| `api.add_game(game, icon="")` | 游戏分节 |
| `api.add_radio(scheme, install, label="")` | 广播 |
| `api.add_battle_server(game, name, factory, label="")` | 团体战服务器（1.6） |
| `api.add_offer_edit(game, edit, label="")` | 对内置启动器的每个报价进行编辑，在 PKHeX 检查之前（1.10，参见 [Offer edits](#offer-edits-110)） |
| `api.folder` | 插件的文件夹，或打包时为 None |
| `api.version`, `api.level` | 应用的 API，为 `1` 和 `12` |
| `api.data` | 保留的数据文件夹（1.1） |
| `pokeldn.plugins.data_folder(plugin_id)` | 从脚本访问的相同文件夹（1.1） |
| `api.library`, `pokeldn.plugins.library_folder(plugin_id)` | 图书馆文件夹（1.7，参见 [A library](#a-library-17)） |
| `Tool`, `Field`, `Game` | 来自 `pokeldn.plugins` 的目录类型 |
| `pokeldn.ldn.show_done()` | 打印交易完成行 |
| `pokeldn.popup.acknowledge(title, text="", *, id, label="OK", on_ack, tone)` | 单按钮弹窗；返回 id（1.2，参见 [Pop-ups](gui.md#pop-ups)） |
| `pokeldn.popup.confirm(title, text, agree, disagree, *, id, on_agree, on_disagree, on_dismiss, tone)` | 两个按钮；Esc 或点击外部可关闭；返回 id（1.2） |
| `pokeldn.popup.choose(title, text, options, *, id, on_choice, on_dismiss, tone)` | 2 至 8 个选项，`on_choice(index)`；返回 id（1.7） |
| `pokeldn.progress.show(done, total, title, unit="bytes")` | 进度条；`unit` 为 `bytes` 或 `items`（1.7） |
| `pokeldn.panel.show(id, title, lines=(), *, image, chips, tone)`, `clear(id)`, `annotate(name, *, state, text, image)`, `unannotate(name)` | 状态卡片（1.8，参见 [Status cards](#status-cards-18)） |
| `pokeldn.ldn.network` | LDN 网络（1.7，参见 [LDN networks](#ldn-networks-17)） |
| `pokeldn.ldn.radio_lost()` | 广播离开的原因，或空（1.7） |
| `pokeldn.popup.cancel(id)`, `available()`, `set_dispatcher(dispatch)` | 关闭弹窗；弹窗是否显示；回调在何处运行（1.2） |

本表及下一表为支持的接口；任何其他导入都可能在任意发布版本中变更。

## 程序表面（1.3，Bank 于 1.4 添加，语言包于 1.5 添加，RNG 于 1.11 添加）

插件或 pokeldn 检出目录下的独立程序可以使用这些接口；`tests/test_plugin_surface.py` 解析每个接口。

| 名称 | 含义 |
|---|---|
| `python -m pokeldn --list`, `python -m pokeldn TOOL -- ARGS` | 工具键；使用设置中的训练师运行 |
| `pokeldn.app.i18n.t(key, default, **fmt)`, `select(plugin_id)` | 字符串查找；选择一个包，或使用 `""` 时选择英文（1.5） |
| `pokeldn.app.catalog.GAMES` | 内置游戏及其 `Tool`；应用传递的标志保持原名 |
| `pokeldn.pokemon.SERVICE.species(game)`, `.names(game, kind)` | 种属、`moves`、`items`、`bag`、`held`、`balls`，格式为 `{"id", "name"}` 列表 |
| `pokeldn.pokemon.SERVICE.options(game, species, trainer)` | 表单、性格、能力、道具和精球 |
| `pokeldn.pokemon.SERVICE.make(game, species, trainer, level, shiny, nickname, version, options)` | 合法宝可梦；返回值和 `"file"` |
| `pokeldn.pokemon.SERVICE.paste(game, text, trainer)` | Showdown 套装作为 `make` 的值，附带 `errors` |
| `pokeldn.pokemon.BuilderError` | PKHeX 拒绝或缺失，并附带面向玩家的句子 |
| `pokeldn.pokemon.NATURES` | 按索引排序的 25 个性格名称 |
| `pokeldn.gifts.load(path, game=)`, `pokeldn.gifts.save(path, gift)` | `.pokegift`、`.wc3`、`.wc8`（参见 [Mystery Gift files](gifts.md)） |
| `pokeldn.swsh.gift_builder.KINDS`, `PRESETS`, `PRESET`, `OUTFITS` | 剑／盾礼物种类、预设和服装 |
| `pokeldn.swsh.gift_builder.blank(**changes)`, `record(state)`, `compile(state)`, `describe(state, name)` | 表单状态、720 字节记录、礼物、玩家行；`ValueError` 指明错误字段 |
| `pokeldn.swsh.events.load()`, `by_key()`, `gift(key)` | 官方剑／盾事件卡片 |
| `pokeldn.frlg.gift.builder.KINDS`, `PRESETS`, `PRESET`, `GIVERS`, `CARTRIDGES` | 火红／叶绿种类、预设、赠送者、卡带 |
| `pokeldn.frlg.gift.builder.blank()`, `compile(state)`, `describe(state, name)` | 适用于神秘卡片、新闻或控制台代码；`name` 通过卡带 id 获取种属 |
| `gui.board.ports()`, `identify(port, blink=)`, `detect_chip(port)` | 串行端口和板子的 `.firmware`、`.firmware_version`、`.protocol`、`.current` |
| `gui.board.download_firmware(say=)`, `image_for(kind, chip)`, `image_version(path)`, `flash(port, kind=)` | 已检查的发布镜像和刷写 |
| `pokeldn.app.bank.library()` | 默认 Bank 文件夹；列表从不创建它（1.4） |
| `pokeldn.app.bank.Entry`, `Imported`, `ImportedPokemon` | Bank 结果类型（1.4） |
| `pokeldn.app.bank.Imported.count(state)` | 状态中的结果数量（1.4） |
| `pokeldn.app.bank.entries(folder=)`, `find(entry_id, folder=)`, `data(entry)` | 按最新优先排序，一条或 `None`，其字节（1.4） |
| `pokeldn.app.bank.import_file(path, trainers, folder=)` | 导入宝可梦文件或存档；返回 `Imported`（1.4） |
| `pokeldn.app.bank.deposit(game, source, info, folder=)` | 存入收到的文件；返回 `Entry` 或 `None`（如果已存入）（1.4） |
| `pokeldn.pokemon.SERVICE.check(game, path)` | PKHeX 检测，用于 `deposit` 的 `info`（1.4） |
| `pokeldn.app.bank.destinations(entry, trainer)`, `offer(entry, game, trainer)` | 按游戏转换；转换后的报价（1.4） |
| `pokeldn.app.bank.edit(entry, fields)`, `remove(entry_id, folder=)` | 编辑昵称、升级等级、招式、Held 道具；删除记录（1.4） |
| `pokeldn.app.bank.TradeSession(offers, folder=)` | 运行中的有序报价（1.4） |
| `pokeldn.app.bank.TradeSession.advance(count)` | 应用累计交易次数；`.completed` 为已见最大值（1.4） |
| `pokeldn.app.received.trades_done(line)` | `[done] trade N complete` 行中的次数，或 `None`（1.4） |
| `pokeldn.frlg.rom.lcg.step(value)`, `.advance(value, n)`, `.distance(start, target)`, `.draws(value, count)` | 火红／叶绿的 `gRngValue` 生成器：下一个状态、提前 n 步、两个状态间步数、接下来 `count` 个 `Random()` 结果及剩余状态（1.11，参见 [The RNG](frlg_rng.md)） |
| `pokeldn.frlg.rom.lcg.recover_wild_state(personality, ivs, max_gap=)` | 构建宝可梦的状态，IV 按存储顺序（1.11） |
| `pokeldn.frlg.rom.rng_countdown.mon_from(state, tid, sid)`, `.scan(state, tid, sid, frames=, want=)` | 状态构建的脚本 `CreateMon`：`personality`、`ivs`、`nature`、`shiny`；`frames` 范围内的 shiny 按键（1.11） |
| `pokeldn.frlg.rom.buffer_script.read_rng_trace(dump)` | `--buffer-script rng-trace` 会话的 `--dump-file` 样本（1.11） |

通过向其 PID 发送 SIGINT 停止启动器运行，然后在 15 秒后发送 SIGTERM；切勿使用 `pkill -f`。

## Bank 集成（1.4）

外部前端使用 `pokeldn.app.bank` 并拥有自己的队列和进程；转换需要 PKHeX 辅助工具（从源码运行 `dotnet build -c Release services/pkhex`）。

| 类型 | 字段 |
|---|---|
| `Entry` | `id`, `path`（本地记录）, `game`, `species_id`, `shiny`, `summary`, `legal`, `tracker`, `created`（Unix 秒）, `origin`, `home_tracker`（`empty`, `made` 或 `""`, [The HOME tracker setting](gui.md#the-home-tracker-setting)） |
| `Imported` | `name`, `save`, `pokemon` |
| `ImportedPokemon` | `where`, `species`, `species_id`, `shiny`, `state`（`banked`, `already`, `refused`）, `game`, `detail` |
| `destinations` 值 | 按游戏：`ok`, `reason`, `home_tracker` |
| `offer` 值 | `file`, `summary`, `species`, `shiny`, `legal`, `encounter`, `moves`, `report`, `home_tracker`, `bank`（源 id） |

`trainers` 将游戏键映射到 `{ot, tid, sid, language, gender}`。导入会记住曾经导入过的所有记录。Offer 会保留 Bank 记录原位；将其 `file` 作为启动器的 `--offer-file` 传入（不带 `--fresh-pid`），并在运行结束前一直保留。直接运行 catalog 工具的脚本，因为 `python -m pokeldn TOOL` 不接受 offer。

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

每次运行只创建一个 `TradeSession`，按确切的 offer 顺序构建，包含已构建的 offer。只输入已确认的计数；未完成的记录会保留。`advance` 在计数错误时抛出 `ValueError`，可在 `OSError` 后重试。文件错误抛出 `OSError`；PKHeX 失败抛出 `BuilderError`。`deposit` 信任 `SERVICE.check`；玩家文件通过 `import_file` 进入。`folder` 默认为 `library()`。在导入前设置 `POKELDN_DATA` 以隔离所有文件。调用是同步的：请使 PKHeX 不在 UI 线程上运行。每个 Bank 文件夹只允许一个写入者；桌面应用之外的前端使用自己的文件夹。`TradeSession` 仅修改 Bank。

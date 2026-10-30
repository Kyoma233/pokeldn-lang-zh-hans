---
title: Desktop builds
---

# 桌面版构建

桌面应用是 pokeldn 在 macOS、Windows 和 Linux 上的界面。一次发布会打包 PKHeX 和适用于 ESP32、ESP32-S3、ESP32-C3 和 ESP32-C6 的无线固件；用户需提供 `prod.keys`。

1. 设置：选择 `prod.keys`。
2. 主板页面：选择 USB 主板并安装无线固件。安装时会选择芯片自带的镜像；来自文件的镜像会与芯片校验。S3、C3 和 C6 通过原生 USB 串口/JTAG 连接；S2 芯片会被拒绝。
3. 选择游戏和工具，准备宝可梦或文件，按照控制台步骤操作并按 Start。收到的宝可梦会进入设置文件夹，通过 Output 按钮旁的按钮打开。

每个交易工具的宝可梦可留空：Start 时 PKHeX 会为你的训练家构建一个随机合法宝可梦（`command.prepare`），每次运行都会更新。

神秘礼物工具共享一个构建器（预设、自定义构建、`.pokegift`、`.wc8` 在剑/盾）。保存礼物文件导出时无需主板，格式为 `.pokegift`、`.wc3` 或 `.wc8`
([神秘礼物文件](gifts.md#desktop-app))。

## 首次启动

macOS 保留原生窗口按钮；Windows 和 Linux 在应用标题栏中绘制这些按钮，点击可拖动窗口并在双击时最大化。

| 系统 | 步骤 |
|---|---|
| macOS | 未签名：打开一次，关闭警告，然后前往系统设置、隐私与安全性，点击“仍然打开” |
| Windows | 解压 zip 并运行 `pokeldn.exe`，`_internal` 需放在旁边；SmartScreen：更多信息，仍然运行。无 COM 端口：[Windows USB 驱动](#windows-usb-drivers) |
| Linux | 需要 GTK 3 和 libsecret；`sudo usermod -aG dialout $USER`（Arch 系统为 `uucp`），然后重新登录。参见 [Linux 串口](#linux-serial-ports) |

## Android 设置要求

[Android 应用](../examples/android/README.md) 是手机上的本界面。主板页面会在插入、拔出 USB、关闭 USB 提示和从设置返回时重新读取 USB 状态。原生 USB 主板（`303a:1001`）插入时会自动打开应用。

| 检测状态 | 提示 |
|---|---|
| 无兼容 USB 设备 | 检查数据线；显示手机的 USB 主机或 OTG 设置（OnePlus 有 OTG 开关） |
| 缺少或拒绝 USB 权限 | 解释 Android 的提示；提供重试选项 |
| 主板握手失败 | 检查主板和固件；显示错误信息 |
| 主板响应 | 显示主板和固件；继续操作 |
| 主板断开或从设置返回 | 刷新并在就绪时恢复 |

经典 ESP32 仅适配 CP210x 桥（`10c4:ea60`, `UsbStream.java`）；CH34x 和 FTDI 被命名为不支持。PKHeX 在手机上运行。保存和“打开文件夹”（zip 文件）使用 Android 的文件选择器。

## iOS 设置

[iOS 应用](../examples/ios/README.md) 是 iPhone 或 iPad 上的本界面（通过 AltStore 或 SideStore）。它通过蓝牙连接主板：从桌面版主板页面安装蓝牙无线固件（ESP32-C6 对应 `pokeldn-radio-ble-c6.bin`，经典 ESP32 对应 `pokeldn-radio-ble.bin`）；USB 仅供供电。当手机握住主板时，主板会忽略 USB：在其他地方使用前请先关闭 iOS 应用。应用文件位于文件、在我的 iPhone、pokeldn。

## 窗口大小

页面的面板布局由可用宽度决定（窗口变化时实时测量，参见 `gui/theme.py` 中的 `Panes`）。选项列最窄不能小于 440 点，其他面板也如此。

| 面板可用宽度 | 布局 |
|---|---|
| 侧面板全宽加上 440 | 并排显示 |
| 侧面板 88% 加上 440 | 并排显示，侧面板变窄 |
| 最后一个面板为 88% 加上 440（三面板页面） | 前两个在切换器中，最后一个并排 |
| 更少 | 切换器中一次显示一个面板 |

从并排布局缩窄窗口会将选项列提前。宽窗口时，选项列固定为 720 点并居中，尽可能多排在同一行；设置和插件页面固定为 760。调整大小后打开的页面会以其可用宽度启动相应布局。

桌面窗口最小可缩窄到 380 点。低于 760 点时，会实时切换为下方的手机布局，并在扩宽时切换回去；桌面窗口在内容上方保留标题栏。

## 手机版

低于 760 点时，页面以底部标签栏形式显示，面板通过切换器一次显示一个（游戏、选项、会话）。Android 和 iOS 没有控制或更新页面。

## 游戏页面

游戏列表每行显示一个活动：交易、神秘礼物，随后是每种团体战类型和联合环。运行该活动的方式是位于其选项上方的按钮，每行显示一个选项：

| 选项 | 按钮 | 显示位置 |
|---|---|---|
| 你的控制台 | 加入（pokeldn 作为主机）、主持（pokeldn 加入） | 主板或局域网上的交易、团体战、极巨大冒险 |
| 连接方式 | 主板、Wi-Fi（无主板）、在线 | 交易；剑/盾仅支持 Wi-Fi |
| 模式 | 任务、遭遇 | 联合环 |

每种组合对应一个目录工具（`pokeldn/app/catalog.py` 中 `Tool` 的 `activity` 和 `variant`），因此运行、保存的字段和 `python -m pokeldn TOOL` 都保持该工具的键。只有一个选项的选择不会显示：在线交易没有控制台选择。更改一个选择会保留该行上其他最近选择的选项。插件工具以同样的方式加入一行（参见 [工具的行](plugins.md#a-tools-row-112)）。

## 应用语言

设置中的应用语言列出英语和已安装的语言包（参见 [语言包](plugins.md#language-packs-15)）；更改后需重启生效，缺失字符串回退为英语。训练家语言单独设置。自带的 Noto Sans CJK SC 字体支持中文、日文和韩文（`gui/assets/fonts/LICENSE`）。其自带的‘ ’“ ”·…为全宽字符，因此 Noto Sans Punctuation（同字体中上述六个字符的拉丁宽度形式，参见 `scripts/gen_punctuation_font.py`）优先于它；每个语言包的 `font_family` 仍然优先。

## 你的训练家

设置中的你的训练家是应用构建的所有宝可梦的初始训练家：姓名、性别、语言和两个 ID 对（游戏中显示的形式）。一条记录存储一个 16 位 TID 和 16 位 SID，它们是 32 位 ID 的高低两部分。

| 游戏 | 显示的 ID | 秘密 ID | 存储 ID |
|---|---|---|---|
| 火红／叶绿 | TID，0 至 65535 | SID，0 至 65535 | `SID << 16 \| TID` |
| 去吧！皮卡丘／伊布、剑／盾、晶灿钻石／明亮珍珠、传说 阿尔宙斯、朱／紫、传说 Z-A | ID mod 10^6 | ID div 10^6，0 至 4294 | `secret * 10^6 + ID` |

`Settings.ids` 按游戏转换。每个连接控制台的工具都会将此训练家作为其玩家呈现（参见 `tests/test_gui_catalog.py`）。火红／叶绿的姓名被截断为七个第三世代字符；不可编码的姓名变为 `POKELDN`（参见 `Settings.name`）。传说 Z-A 仅在性别、ID 和姓名都匹配时，才会将收到的宝可梦视为玩家自己的（参见 [收到记录的内容](za.md#what-the-trade-writes-into-a-received-record)）；传说 阿尔宙斯的记录会携带性别（参见 [记录](pla.md#the-games-reader-and-the-pre-handler-phase)）。

### 查找你的训练家

“查找我的”会从最近一次从控制台读取的训练家中填充一行的 ID 和秘密 ID，以及姓名、性别和语言。Switch 游戏从不显示秘密 ID；链接会携带它。

| 行 | 什么命名了这个训练家 |
|---|---|
| 火红／叶绿 | 控制台的 LinkPlayer，`trainerId` = `SID << 16 \| TID`，在每次交易、神秘礼物和联盟房间会话中，无论是哪个角色 |
| Switch | 在去吧！皮卡丘／伊布、晶灿钻石／明亮珍珠、传说 阿尔宙斯、朱／紫或传说 Z-A 的交易会话中，控制台的会话数据，无论是哪个角色（参见 [这是谁的存档](gift_simulated.md#whose-save-it-is)）；在剑／盾中，以及在任意标题中，控制台曾交易过且其存档捕获的宝可梦（handler 为 0，游戏自己的版本，非蛋） |

启动器每次打印一次 `[trainer] {json}`（参见 `pokeldn.console_trainer`）；应用会在 `settings.json` 的 `found_trainers` 中按行、并按游戏保留最新的训练家，并在私有日志掩码下记录。Switch 行适用于所有 Switch 游戏，因此会使用最近一次交易的训练家。若未找到任何训练家，“查找我的”会提示进行一次交易。

### 每个游戏的训练家

「每个游戏使用不同训练家」会让每款游戏各自拥有姓名、性别、语言、ID 和秘密 ID，一次编辑一款游戏；ID 按该游戏的显示方式。从未编辑过的游戏继续使用共用训练家。`settings.json` 用 `per_game_trainer` 保存开关，用 `game_trainers` 保存各游戏有差异的字段。`Settings.own(game)` 是某款游戏看到的训练家；`Settings.ids`、`Settings.name`、`Settings.trainer` 以及启动令牌 `{ot}`、`{tid}`、`{sid}`、`{language}`、`{gender}` 都经此读取（`tests/test_gui_catalog.py`）。对某款游戏按「找我的」会取用从该游戏读到的最新训练家。

## Windows USB 驱动

经典 ESP32 的 USB 转串口桥在 Windows 分配 COM 端口前需要驱动（设备管理器问题代码 28）。S3、C3 和 C6 在原生 USB 上不需要驱动。

| 桥接器 | USB ID | 驱动 |
|---|---|---|
| CP210x | `10c4:ea60` | [CP210x VCP 驱动](https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers)：右键点击 `silabser.inf`，安装，重新插入 |
| CH340 | `1a86:7523` | [CH341SER.EXE](https://www.wch-ic.com/downloads/CH341SER_EXE.html)：安装，重新插入 |

无 COM 端口时，主板页面每 2 秒轮询一次 `Win32_PnPEntity`（`ConfigManagerErrorCode <> 0`），并命名一个已知的桥接器（参见 `gui/board.py` 中的 `bridges_without_driver`）。

## Linux 串口

串口需要 `dialout` 用户组（Arch 系统为 `uucp`）；在收到 `EACCES` 错误时，主板页面会显示该组名。

| 服务 | 主板 | 影响 |
|---|---|---|
| brltty 6.4 (Ubuntu 22.04) | CH340 | 占用设备，无 `/dev/ttyUSB*`（参见 [LP 1990357](https://bugs.launchpad.net/bugs/1990357)）；解决方法：`sudo apt remove brltty` |
| brltty 6.6 (Ubuntu 24.04) | CH340 | 仅在 `1a40:0101` 集线器后被占用（参见 [LP 1958224](https://bugs.launchpad.net/bugs/1958224)） |
| ModemManager 1.23 | 全部 | 无忽略规则适用于 `10c4`、`1a86`、`303a` |

无端口时，主板页面读取 `/sys/bus/usb/devices` 并命名一个无 tty 的桥接器（参见 `gui/board.py` 中的 `bridges_without_port`）。

## 本地存储

设置中的存储显示可回收的空间；清除本地文件会在确认后在后台删除，并暂时阻止会话和刷写操作。请先保存任何有助于报告 bug 的文件。

| 被删除 | 被保留 |
|---|---|
| `session/`（捕获、追踪、临时提供）、`logs/`、`pokemon/` 中未使用的生成或导入提供；空文件夹 | 一分钟以内的提供或被保存设置和队列引用的提供；收到的文件、银行、存档、密钥、固件、设置；符号链接；自检查后修改的文件 |

## 你的存档

剑/盾神秘礼物工具的“你的存档”标签页会备份或恢复控制台的存档（参见 [存档备份与恢复](frlg_gift.md#save-backup-and-restore)）。存档位于 `Documents/pokeldn/Saves`（`pokeldn.app.saves`；当设置了 `POKELDN_DATA` 时位于其内部），每个存档对应一个 `.sav` 和一个 `.json`。

| 操作 | 结果 |
|---|---|
| 从 Switch 备份 | 写入 `backup-<run>.sav`；若备份中断，会保存在 `Saves/.partial` 中，下次恢复时继续 |
| 将存档放到 Switch | 传递 `--save-restore`；未选择存档时 Start 被阻止 |
| `+` 或拖入 `.sav` | 复制进去；丢弃 16 字节模拟器页脚，拒绝非 128 KB 的文件 |
| 重命名、导出、删除 | 删除会同时移除本地的两个文件 |
| 查看和编辑 | PKHeX 读取训练家、队伍和箱子 |

在没有完整存档副本或队伍中存在非法宝可梦时，恢复操作会被阻止，直到开启“仍然恢复”。编辑器会修改训练家姓名、性别、金钱、硬币和队伍；“另存为新存档”会通过 PKHeX 写入，重新计算扇区校验和，并作为新条目保存。

## 银行

银行页面保存收到的所有宝可梦，并将一个宝可梦交易到 HOME 将其移动到的任意游戏。
记录存放在 `Documents/pokeldn/Bank`（`pokeldn.app.bank`；在设置 `POKELDN_DATA` 时位于内部）中，
以该游戏的格式保存为 `.json`。

| 步骤 | 具体内容 |
|---|---|
| 交易完成 | 每个收到的文件按其字节内容存入银行一次 |
| 宝可梦被存入银行 | `.json` 保存物种、摘要、判定结果、来源、SHA-256、随机 63 位追踪码、`home_tracker` |
| 目的地 | 辅助程序的 `destinations` 尝试所有七个游戏 |
| 目的地被选中 | `move` 将其转换为该工具的队列，并附带 `"bank": id` |
| 交易 N 完成 | `[done] trade N complete` 将其从银行移除 |
| 运行失败 | 它仍留在银行和队列中 |

一次移动使用 PKHeX 的 HOME 转换（通过 `EntityConverter.ConvertToType` 至 `PKH`）以及目的地的
合法性检查。应用程序的训练家成为处理人（`IHandlerUpdate`，`PB8.UpdateHandler`）；
非法招式获得 PKHeX 建议的招式组；PID、加密常量、OT 和 ID 保留不变，运行时省略 `--fresh-pid`。

| 拒绝原因 | 来源 |
|---|---|
| 无法传回 火红／叶绿 | `EntityConverter.IsConvertibleToFormat` |
| 无法传至 Let's Go | HOME 仅从中接收宝可梦 |
| 蛋；带有物品或 HM 招式的 火红／叶绿 宝可梦 | HOME 的 火红／叶绿 筛选 |
| 物种或表单不存在 | 目的地的个人表 |
| Legends Z-A 记录无法导出 | PKHeX.Core 26.8.26 无对应路由 |

盒子列出所有存入银行的宝可梦，并提供对其摘要的搜索、排序（最新、最旧、图鉴编号、名称）、
过滤（异色、等待交易、不合法）以及选择功能，选择可同时选中多个宝可梦（长按也可触发），
进行批量导出到文件夹、移出交易或移除。精灵图的裁剪与其 SHA-256 一起保存在精灵图缓存的
`index.json` 中，因此盒子在显示过的 PNG 后无需再次解码即可打开。

宝可梦的面板显示其战斗组，从辅助程序的 `check`（`battle`）获取：IV、努力值和属性值，
按 Showdown 顺序显示，并以英文展示其 Showdown 集合，便于复制为 Showdown 集合。
努力值列显示为 Let's Go 的 AV（`IAwakened`）、Legends Arceus 的 GV（如游戏所示，
存储值加上 `GanbaruExtensions.GetBias` 的 IV）以及其他游戏的 EV。

图鉴盒列出银行七个游戏中拥有的每个物种（辅助程序 `species` 的并集），
显示银行的数量、精灵图和每个拥有的物种的异色标记；过滤器可显示拥有的、缺少的，
或尚无异色的物种。拥有的物种会自动在盒子中搜索该物种。

编辑功能遵循游戏允许的范围：昵称、等级提升、招式、携带物品。
辅助程序的 `check` 拒绝会使合法宝可梦变为非法的编辑。
已排队的宝可梦不可编辑。
`tests/test_bank.py` 涵盖招式、拒绝、编辑和导入等内容，通过真实辅助程序测试。

### HOME tracker 设置

PKHeX 会在宝可梦被移动到其他游戏时以及通过 HOME 获得的礼物上标记缺失的 tracker（`TransferTrackerMissing`）。
HOME 3.1.0+ 拒绝其未发行的 tracker（错误代码 10015）。
设置 → 高级 → HOME tracker（`Settings.home_tracker`）会随每个辅助程序请求发送，
并作为 `POKELDN_HOME_TRACKER` 传递给运行。

| 设置 | 写入的 tracker | 合法性 | 警告 |
|---|---|---|---|
| `empty`（默认） | 无 | 带 tracker 时合法则接受 | PKHeX 标记缺失的 HOME tracker |
| `made` | 随机 63 位（银行的） | 不变 | 无法存入 HOME |

在 `empty` 模式下，辅助程序会根据带有 HOME 修改的 tracker 副本判断记录（`ValidWithTracker`），
因为 PKHeX 会在 HOME 游戏之间限制进化，并将 Z-A 的能力调整与 tracker 相关联。
礼物遵循该设置（`MendGift`）；一个 `made` 的 tracker 会附带 HOME 的修改（`HomeSeen`：
在 朱／紫 上显示为高度，Z-A 的高度、重量和 Alpha 标记）。
剑／盾 的神秘礼物卡从不携带 tracker（参见 [Pokemon HOME](swsh_gift.md#pokemon-home)）。

### 导入

加号按钮或拖放文件可导入 PKSM 银行、存档（`SaveUtil.TryGetSaveFile`；
3DS 的存档是一个名为 `main` 的文件）或任意 PKHeX 格式的单条记录（`FileUtil.TryGetPKM`）。
存档会先提取队伍槽位，然后盒子槽位；PKSM 银行则按顺序提取其盒子槽位。

| PKSM 银行（`.bnk`） | 布局（PKSM `common/source/BankFile.cpp`） |
|---|---|
| 文件头 | `PKSMBANK`，u32 版本，u32 盒子数量（版本 1 中缺失，根据长度读取） |
| 条目 | u32 生成标签，后跟用 `0xFF` 填充的解密记录；版本 1 和 2 为 264 字节，版本 3 为 0x150 字节 |
| 插槽 | 每盒 30 个，最多 500 盒 |
| 标签（PKSM-Core `Generation.hpp`） | 0 Gen 4，1 Gen 5，2 Gen 6，3 Gen 7，4 Let's Go，5 Gen 8（PK8），6 Gen 3，7 Gen 1，8 Gen 2；`0xFFFFFFFF` 表示为空 |

Gen 1 或 Gen 2 的条目是包含两个名称的单宝可梦列表：Gen 1 为 59 或 69 字节，Gen 2 为 63 或 73 字节，
日语长度为时最后一字节为 `0x50` 或 0（PKSM `3ds/source/Bank.cpp`，`Bank::pkm`）。
版本高于 3 的将被拒绝。盒子名称位于 PKSM 的 `.json` 中，与银行文件同目录，但不被读取。

| 记录 | 保留方式 |
|---|---|
| 银行游戏的格式 | 原样保留，若合法 |
| 其他格式 | 移除携带物品，忘记 Gen 3/4 的 HM 招式；若合法，移动到第一个接受它的游戏：火红／叶绿、朱／紫、剑／盾、BDSP、Legends Arceus、Legends Z-A |

非法记录、校验和错误、其他游戏的蛋以及不可达物种将被拒绝。
`Bank/.imported` 保存每条导入记录的 SHA-256，因此重新导入存档时仅会导入变更过的记录。

### 未解决问题

- HOME 是否接受 `made` 的 tracker，或在宝可梦跨游戏移动时接受 `empty` 的 tracker。
- HOME 的 火红／叶绿 规则是否超出蛋、携带物品和 HM 招式。
- 哪个字段携带 HOME 的 Switch 火红／叶绿 来源图标；PKHeX 会根据 Pal Park 血统转换 `.pk3`。

## GTS

GTS 页面列出符合物种筛选条件的公开挂单，以及玩家自己的挂单在“Yours”下。
“Shiny only”仅保留提供异色宝可梦的挂单；“My bank can answer”保留合法、未排队的银行宝可梦的挂单。
挂单按最新、结束日期、图鉴编号或等级排序。
异色宝可梦在提供、索要或选择存入时都会带有闪光效果。
存入操作需要一只合法、未排队的银行宝可梳，存放在 `Documents/pokeldn/GTS` 中并挂出，
最多可请求三个物种，每个物种可选是否异色，以及一个等级范围。
应用程序在运行时自动应答挂单（参见 [The GTS](online.md#the-gts)）。

## 主板与固件

主板页面列出所有插入的主板及其固件、版本和“最新”或“可更新”状态。
固件卡（`gui.board.FIRMWARES`）在确认后安装 Wireless 或 Controller 固件；
“从文件安装”接受一个 pokeldn 的 `.bin` 文件。

| 主板 | 发现方式 | 版本来源 |
|---|---|---|
| Wireless | 串口 | HELLO 回复 |
| Controller，经典 ESP32 | 串口 | 状态帧 |
| Controller，ESP32-S3 | USB id `0f0d:0092` | 蓝牙状态 |
| 无 | 串口，无回应 | 无 |

随带版本为 ESP-IDF 应用描述符的 `version`（魔数 `0xABCD5432`，位于合并镜像的 `0x10020`）。
运行 Controller 固件的 S3 主板会通过蓝牙接收下载命令；应用程序等待 20 秒寻找加载器端口，
并使用 `--from-loader` 进行刷写。

作为 [便携信标](hardware_esp32.md#portable-beacon) 的主板显示“Kept gift”及移除按钮。

### 主板详情

主板页面上的“复制主板详情”（无论是否选中主板）以纯文本复制详情并保存为
`logs/board-report-DATE.txt`（位于数据文件夹内；`gui/board_report.py`）。
复制详情会打开所选端口，因此主板可能会重启；在运行时，它仅列出端口。

| 部分 | 包含内容 |
|---|---|
| This computer | 应用版本（打包或源码）、系统、Python、pyserial 和 esptool 版本 |
| USB 串口 | pyserial 列出的每个端口，含 USB id、序列号、位置和 `hwid` |
| Drivers | Windows 桥接缺少驱动，Linux 桥接缺少 tty，控制器主板在 USB 上 |
| Opening the port | 打开端口的错误（含 `errno`/`winerror`），或前 2 秒读取的字节 |
| pokeldn 固件 | HELLO 和 STATUS，或为什么没有主板回应 |
| ESP32 bootloader | esptool 的芯片、描述、特性、晶振、MAC 和 USB-Serial/JTAG 模式 |
| Activity | 页面最近的 80 行日志 |

## 控制器

控制页面通过 Controller 固件（参见 [Controller board](hardware_pad.md)）按下 Switch 按钮并播放宏。
ESP32-S3 插入 Switch 并通过蓝牙低功耗连接；经典 ESP32 留在电脑的 USB 上，
并从“Change Grip/Order”配对。重新安装会清除配对。
当连接断开时，页面会持续搜索直到主板回应或点击“Stop looking”。

| 部分 | 功能 |
|---|---|
| 屏幕控制器 | 按住按钮；摇杆八方向，L3/R3 在中心 |
| 键盘 | 方向键为 D-pad，X 为 A，Z 为 B，S 为 X，A 为 Y，Q 为 L，W 为 R，1 为 ZL，2 为 ZR，Enter 为 +，Backspace 为 -，H 为 HOME，C 为 Capture |
| Record into the macro | 每次按下都会成为一个步骤，包含按住时间和暂停 |
| 宏编辑器 | 按钮、摇杆、等待、嵌套重复；Run once 和 Loop 部分 |
| Play on the board | 主板在其自身时钟上播放宏 |

宏为 `.pokemacro` 文件，存放在 `Documents/pokeldn/Macros` 中
（参见 [Controller board, Macros](hardware_pad.md#macros)）。
页面通过 `127.0.0.1:47800` 与 `pokeldn.pad.service` 通信。
在 macOS 26 中，作为 bundle 主可执行文件的已签名进程不会收到蓝牙发现，
因此打包应用会从 `Contents/Helpers/pokeldn-bluetooth` 运行服务，
这是一个裸签名副本，`_internal` 链接到 `../Frameworks`。

## 宝可梦精灵图

图像按需从 [PokeAPI](https://github.com/PokeAPI/sprites) 获取，缓存于 `sprites/`。
设置 → 宝可梦精灵图 禁用下载并清除缓存。
缺失的图像显示占位图；缺失的异色图会回退为普通图。

## 团体战事件

朱／紫 的 Tera Raid（Host）Raid event 卡从
[EventsGallery](https://github.com/projectpokemon/EventsGallery)
（参见 [Event raids](sv_raid.md#event-raids)）获取团体战，
复制到 `EventsGallery/`（`pokeldn.app.events_gallery`）。
下载获取 `codeload.github.com` 上最近一次修改 `Released/Gen 9/SV/Raid Events` 的提交，
并保留每个事件的最新表格；“检查更新”比较该提交。
复制操作仅在完成后才会替换旧文件；Windows 以 `\\?\` 形式打开长路径。

选择一个事件会将团体战卡限制在其版本、进度和水晶上（`raid_event.constrain`），
并在“Find a raid”中限制到其水晶、Boss 和奖励表
（参见 [Finding a seed](sv_raid.md#finding-a-seed)、[Size marks](sv_raid.md#size-marks)）。
一次只能捕获的 Boss 会提供“Let it be caught again”选项（`--raid-catch-normal`）。
折叠卡片会恢复为标准团体战（“Off: Event”）；
复制中缺失的事件会显示“Missing: Event”，运行时拒绝该事件。

## 主持团体战奖励

奖励卡提供模板（训练道具、蛋蛤、战斗道具、浆果、进化道具、Tera 碎片、Herba Mystica、
秘宝、精球），共享数量为 1 到 999；编辑时切换为自定义奖励，最多 45 行。
团体战自身的奖励会清除覆盖（参见 [Hosting](sv_raid.md#hosting)；`gui/views/rewards.py`）。

## 团体战 NPC 伙伴

团体战 NPC 伙伴卡填充主机留下的空位（参见 [Partners](sv_raid.md#partners)；
`gui/views/raid_partners.py`）；未选择任何伙伴时，主机会像主机一样随机抽取伙伴。
伙伴的进度会传递 `--raid-partner-progress`；
每张卡显示训练家、宝可梦（等级为 Our Pokemon 的四五分之一）、Tera 属性、特性和招式，
而受欢迎的伙伴会带有蓝色或银色条（参见 [Favoured partners](sv_raid.md#favoured-partners)）。
每次点击会按插槽顺序传递 `--raid-partner`；缺少该插槽的选择会被丢弃。
文件名：gui.md
这是第 3/3 段（请仅翻译本段，保持与前后段落标题层级的衔接）。

## 联盟环

《紫罗兰》版本的联盟环工具可根据四位数字的链接代码，将一个控制台加入一个环中
（[联盟环](sv_union_circle.md)）；该字段最初是空的。

- 任务：解锁剩余的 Snacksworth 传奇宝可梦或给予 BP（1 到 9,999,999）；Snacksworth 运行
会绘制一个清除进度条（[progress](#progress)）。
- 遭遇：生成卡（`gui/views/encounter.py`）可设置物种、闪光、形态、等级、太晶类型、
性格、性别、能力、道具、比例和 IV；仅限合法遭遇（默认）限制在 PKHeX 接受的范围内并列出有效的地点。它会传递 `--spawn` 和 `--spawn-*` 参数。

当运行持续时，`[panel]` 卡片（[状态卡](plugins.md#status-cards-18)）会显示在工具的选项上方。`--verbose-circle` 会记录每个环的消息。

## 神秘礼物 - 模拟

在《宝可梦：Let's Go》、《宝可梦：BDSP》、《宝可梦：阿尔宙斯》、《紫罗兰》和《宝可梦：Z-A》的工具卡上，列出了来自 PKHeX 活动表的礼物宝可梦
（[模拟神秘礼物](gift_simulated.md#the-gifts)；
`gui/views/event_gifts.py`），按时间排序，可搜索。点击会为设置训练师排队一份新副本；一次托管会话中最多可交易六份礼物。副本会保留与之一起创建的训练师。

如果礼物指定了接收者的语言，而没有存档达到该语言，则会显示一个非法标记
（[保存一个已达到的卡片](gift_simulated.md#saves-a-card-reached)）。为接收玩家（默认）创建的礼物会为控制台的存档重新创建此类礼物
（[为接收玩家创建](gift_simulated.md#made-for-the-receiving-player)）；当没有排队的礼物符合条件时，开关会被禁用，且没有传递 `--for-receiver` 参数。HOME 礼物以琥珀色突出显示，并采用 [HOME 跟踪器设置](#the-home-tracker-setting)
（[交易提供的副本](gift_simulated.md#the-copy-a-trade-offers)）。

## 私人日志

设置“隐藏日志中的个人信息”（默认启用）会屏蔽显示和复制的日志
（`pokeldn/app/redact.py`）：

| 屏蔽内容 | 显示为 |
|---|---|
| 路径中的主目录 | `~` |
| iOS 应用容器 | `<app>` |
| MAC 地址中的设备一半 | `**:**:**` |
| `ot_name`、`ht_name`、`OT`、`nickname`、`trainer`、`player`、`name` 之后的引号值（除 `POKELDN`、`PKLDN` 外） | `***` |
| `TID`、`SID`、`trainer_id` 之后的值 | `***` |
| 一个已见的训练师名称，以及设置中的一个，作为整个单词 | `***` |

会话记录（`captures/`）不会被屏蔽。链接本地地址保持不变。

## 弹出窗口

运行、子进程和应用可以在任何页面上打开弹出窗口（`pokeldn.popup`，插件 API 1.2）。

| 类型 | 回调 |
|---|---|
| `acknowledge(title, text)` | `on_ack` |
| `confirm(title, text, agree, disagree)` | `on_agree`、`on_disagree`、`on_dismiss` |
| `choose(title, text, options)` (1.7，2 到 8 个选项) | `on_choice(index)`、`on_dismiss` |

选项：`id`（重新打开一个已打开的 id 会替换它并丢弃其回调）和 `tone`（`info`、
`warning`、`error`）。打开返回 id；回调在答案线程上运行，除非设置了 `set_dispatcher(dispatch)`。`cancel(id)` 关闭一个。32 个未回答的弹出窗口会引发 `RuntimeError`。如果没有应用（`available()` 为 false），弹出窗口会是一个 `[pop-up]` 输出行。

`runner.Process(..., popups=app.popups)` 设置 `POKELDN_POPUPS=1`；子进程在 stdout 上写入 `[popup]` 和 JSON，并在 stdin 上读取 `[popup] {"id", "n", "answer"}`（`pokeldn.app.runner.child`）；`n` 使对替换的弹出窗口的晚期答案不会触发任何操作。`pokeldn.app.popups.Manager` 保留它们，`gui.popups.Dialogs` 绘制它们。应用自身的弹出窗口报告更新失败、插件禁用和为设置训练师发送接收者礼物（[交易](gift_simulated.md#the-trade)）。

## 进度

运行会打印 `[progress] DONE TOTAL UNIT TITLE`（`pokeldn.progress.show`，API 1.7；`UNIT` 是 `bytes` 或 `items`），以绘制一个带有数量、30 秒速率和剩余时间的进度条，每个标题每秒最多四行。`[save]` 行绘制相同的进度条。

## 更新

启动时，应用会询问 `api.github.com/repos/Decryptu/pokeldn/releases/latest`（5 秒超时）。如果 `vX.Y.Z` 标签高于 `pokeldn.__version__`，则会添加一个更新条目，提供立即更新或下载。

立即更新（`pokeldn.app.update`）会下载平台存档和 `SHA256SUMS` 到 `update/`，拒绝校验和不匹配，解压缩（`ditto -x -k`，`tarfile` `data` 过滤器，`zipfile`），并启动 `pokeldn --apply-update NEW TARGET PID VERSION`（`gui/updating.py`）。助手等待旧应用退出（在 Windows 上等待其进程），将其重命名为 `.<name>.old`，复制新应用并打开它；任何失败都会恢复旧应用。新应用会读取 `update/outcome.json` 一次。校验和可以检测损坏，但不能验证发布。

| 情况 | 行为 |
|---|---|
| 预发布、草稿、奇数标签 | 不提供 |
| 无网络 | 检查现在说 GitHub 没有回答 |
| 设置中关闭更新 | 没有启动请求 |
| 没有存档或 `SHA256SUMS`、源代码检查、应用转移、不可写文件夹（macOS、Linux） | 仅下载 |
| Windows，`C:\Program Files` | 立即更新在 UAC 后面（`ShellExecuteExW` `runas`） |
| Windows，另一个驱动器的根（`D:\pokeldn`） | 立即更新无 UAC：交换仅在应用旁边添加文件夹，这允许用户在卷的根下操作。0.34.0 之前的版本会用文件探测根，在那里请求 UAC，标准用户的更新会在“Windows 没有给予 pokeldn 更改 D:\ 的权限”时停止；从此类版本中，下一版本需要手动下载一次 |
| Windows，映射或 `subst` 驱动器 | 保留驱动器号；助手在两种拼写下找到旧应用的进程；在 UAC 后面，助手获取字母所代表的文件夹，因为在用户会话中映射的字母在提升的进程中是看不见的 |
| 一个会话、闪存或清理正在运行 | 要求先完成 |

`scripts/check_update.py ARCHIVE FOLDER` 测试打包应用的更新是否与 127.0.0.1 兼容；
`POKELDN_UPDATE_URL` 替换端点（`tests/test_app_update.py`）。macOS 是否在 `/Applications` 中请求应用管理权限没有被测量。

## 文件拖放

| 目标 | 接受 |
|---|---|
| 交易的宝可梦 | 宝可梦文件或 Showdown `.txt`；额外内容会填满下一个交易 |
| 添加交易 | 每个文件一个交易 |
| 礼物卡 | `.pokegift`、`.wc8`、`.wc3` |
| 板级固件卡 | pokeldn `.bin` |
| 任何路径字段 | 文件，或其文件夹 |

Flet 1.0.2 的客户端不接受拖放；`scripts/build_client.py` 使用 `gui/flet_drop`（[desktop_drop](https://pub.dev/packages/desktop_drop)）构建 Flet 客户端，进入 `gui/client/<platform>`，使用 Flutter 版本 `python -m flet_cli.cli --version --json`，macOS 部署目标为 12.0。如果没有它，`gui/main.py` 会运行 Flet 自己的客户端，没有拖放功能。

## 文档页面

文档页面显示应用指南和此网站上的每个可导航页面；搜索匹配章节，每个单词都必需，标题匹配第一个（`gui/views/docs.py`）。

## 未发布的标题

一个标题在 Switch 发布之前显示，只在游戏、银行和文档中显示，来自源代码检查（`pokeldn/app/preview.py`）。`POKELDN_PREVIEW=1` 会在任何地方显示它，`0` 会隐藏它。它的文档页面设置 `nav_exclude` 和 `search_exclude`。

## 从源代码运行

安装 Python 3.13 和 .NET 10 SDK：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r gui/requirements.txt
dotnet build -c Release services/pkhex -warnaserror
python scripts/build_client.py    # 可选：文件拖放；需要 Flutter
python gui/main.py
```

Raspberry Pi OS 添加 piwheels 作为包索引，piwheels 的 `flet_web-1.0.2-py3-none-any.whl`（25 KB）缺少 PyPI 的 wheel（27 MB）中携带的 `flet_web/web` 客户端；应用然后会回答 `RuntimeError: Web root path not found`。单独从 PyPI 安装该包：
`python -m pip install --force-reinstall --no-cache-dir --index-url https://pypi.org/simple flet-web==1.0.2`。
没有 Linux arm64 发布；Raspberry Pi 从源代码运行应用。

源代码检查没有固件镜像。下载固件在板级页面会从最新版本获取所有镜像，使用 `SHA256SUMS`，并仅在所有镜像匹配时写入。

## 构建桌面应用

在激活 ESP-IDF v6.1 的情况下，将每个镜像构建到 `gui/firmware`，然后打包：

```sh
mkdir -p gui/firmware
OUT="$PWD/gui/firmware"
cd firmware/esp32
for t in esp32:radio esp32s3:radio-s3 esp32c3:radio-c3 esp32c6:radio-c6; do
  chip=${t%%:*}; name=${t#*:}
  idf.py -B build/$chip -D SDKCONFIG="$PWD/build/$chip/sdkconfig" set-target $chip
  idf.py -B build/$chip -D SDKCONFIG="$PWD/build/$chip/sdkconfig" build
  idf.py -B build/$chip merge-bin -o "$OUT/pokeldn-$name.bin"
done
export POKELDN_BLE=1   # Bluetooth images for the iOS app (hardware_esp32.md, Bluetooth)
DEF="sdkconfig.defaults;sdkconfig.defaults.ble"
for t in esp32:ble esp32c6:ble-c6; do
  chip=${t%%:*}; name=${t#*:}
  idf.py -B build/$name -D SDKCONFIG="$PWD/build/$name/sdkconfig" -D SDKCONFIG_DEFAULTS="$DEF" set-target $chip
  idf.py -B build/$name -D SDKCONFIG="$PWD/build/$name/sdkconfig" -D SDKCONFIG_DEFAULTS="$DEF" build
  idf.py -B build/$name merge-bin -o "$OUT/pokeldn-radio-$name.bin"
done
unset POKELDN_BLE
cd ../pad
idf.py -B build -D SDKCONFIG="$PWD/build/sdkconfig" set-target esp32s3
idf.py -B build -D SDKCONFIG="$PWD/build/sdkconfig" build
idf.py -B build merge-bin -o "$OUT/pokeldn-pad-s3.bin"
cd ../..
python scripts/build_client.py
python scripts/build_unicorn.py   # 需要 CMake
python scripts/pack_app.py
```

冻结应用检查验证每个镜像，`flet_drop` 客户端和 Unicorn 被捆绑。版本是 `pokeldn.__version__`，通过 `.github/release-notes.md` 增加，其第一行必须是 `# pokeldn X.Y.Z`（`tests/test_release.py`）。`v*` 标签发布九个文件和 `SHA256SUMS`；只有带连字符的标签是预发布版本。

应用是 PyInstaller 的单文件夹构建（`pokeldn.app`；一个 `pokeldn` 文件夹，`_internal` 在其他地方）：在 M4 上，游戏页面在 0.7 秒内打开，运行在 0.08 秒内启动。`scripts/pack_app.py` 在 Flet 的 `--onefile` 之后传递 `--onedir`，并设置 `LSBackgroundOnly`，这样只有查看器才有 Dock 图标。

| 部分 | 大小 | 保持小巧的方法 |
|---|---|---|
| Flet 查看器 | 31 MB（macOS 上 9.4 MB xz） | 没有可选扩展，一个架构，`--split-debug-info` |
| Unicorn | 3 MB | 仅 ARM 和 ARM64 引擎 |
| PKHeX 助手 | 16 MB | 完全修剪 |
| Python | 8 MB | 排除 web、image、test 和语法模块；macOS 上 `strip -x` |

打包陷阱：

- 修剪禁用反射 JSON；`JsonSerializerIsReflectionEnabledByDefault` 恢复它。`DynamicDependency` 保留 PKHeX.Core 的 Gen 3 活动表。
- macOS 查看器存档是 xz 命名 `flet-macos.tar.gz`；`gui/flet_client.py` 以压缩检测打开它，并删除标记为 `pokeldn-drop` 的过时 `~/.flet/client` 文件夹。
- 永远不要修剪可执行文件或 PKHeX 助手：两者在 Mach-O 图像之后都携带一个存档。
- `scripts/pack_flet.py` 保留查看器的权限；如果没有 `com.apple.security.files.user-selected.read-write`，选择 `prod.keys` 会引发 `ENTITLEMENT_NOT_FOUND`。
- 在 Linux 上，`pokeldn/app/paths.py` 恢复用户的 `LD_LIBRARY_PATH`（捆绑的 `libstdc++` 会破坏 Fedora 的 EGL），并设置 `FLET_LINUX_DISTRO`。
- Unicorn 在 Control Flow Guard 下会中止，错误代码为 `0xC0000409`
（[unicorn#2281](https://github.com/unicorn-engine/unicorn/issues/2281)）；打包器清除 `pokeldn.exe` 中的 `GUARD_CF`（`0xC160` 到 `0x8160`）。永远不要在冻结检查中启用 `faulthandler`。

### 应用图标

`gui/AppIcon.icon` 是一个 Icon Composer 文档，是 macOS 和 iOS 图标的唯一源。`actool`（Xcode 26）将其编译成 `Assets.car` 和 `AppIcon.icns`；`scripts/pack_app.py` 将两者放入 `pokeldn.app` 和 Flet 查看器中，并设置 `CFBundleIconName`。macOS 26 从目录中绘制分层图标；macOS 12 到 15 绘制其平铺版本，这些版本位于苹果的图标网格上（瓦片跨度 102 个 128 像素）。Windows 采用 `gui/assets/icon.ico`，Linux 采用 `gui/assets/icon.png`，两者都是全出血：这两个平台都不在图标中添加内边距。

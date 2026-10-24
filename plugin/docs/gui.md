---
title: Desktop builds
---

# 桌面版构建

桌面应用是 pokeldn 面向 macOS、Windows 和 Linux 的界面。一个发布包捆绑 PKHeX 以及适用于 ESP32、ESP32-S3、ESP32-C3 和 ESP32-C6 的无线固件；用户提供 `prod.keys`。

1. 设置：选择 `prod.keys`。
2. 开发板页面：选择 USB 开发板并安装 Wireless 固件。安装会选择该芯片捆绑的镜像；来自文件的镜像会与芯片进行校验。S3、C3 和 C6 通过原生 USB Serial/JTAG 连接；S2 芯片会被拒绝。
3. 选择游戏和工具，准备一只宝可梦或一个文件，按照主机步骤操作并按下 Start。收到的宝可梦会保存到设置文件夹，可通过 Output 旁的按钮打开。

神秘礼物工具共用一个构建器（预设、自建、`.pokegift`、剑／盾上的 `.wc8`）。
在没有开发板的情况下，将礼物文件导出保存为 `.pokegift`、`.wc3` 或 `.wc8`
（[神秘礼物文件](gifts.md#desktop-app)）。

## 首次启动

macOS 保留系统原生窗口按钮；Windows 和 Linux 会在应用头部绘制窗口按钮，双击头部可最大化窗口。

| 系统 | 步骤 |
|---|---|
| macOS | 未签名：打开一次，关闭警告，然后前往“系统设置” > “隐私与安全性” > “仍要打开” |
| Windows | 解压 zip 并运行 `pokeldn.exe`，`_internal` 位于其旁边；SmartScreen：更多信息 > 仍要运行。没有 COM 端口：请参阅 [Windows USB 驱动](#windows-usb-drivers) |
| Linux | GTK 3 和 libsecret；`sudo usermod -aG dialout $USER`（Arch 上为 `uucp`），然后重新登录。参见 [Linux 串口](#linux-serial-ports) |

## Android 配置要求

[Android 应用](../examples/android/README.md) 是手机上的此界面。开发板页面会在插入、拔出、USB 提示关闭及从 Settings 返回时重新读取 USB 状态。原生 USB 开发板（`303a:1001`）在插入时会打开应用。

| 检测到的状态 | 引导 |
|---|---|
| 没有兼容的 USB 设备 | 检查数据线；显示手机的 USB 主机或 OTG 设置（OnePlus 有 OTG 开关） |
| 缺少或被拒绝 USB 权限 | 解释 Android 的提示；提供重试 |
| 开发板握手失败 | 检查开发板和固件；显示错误 |
| 开发板有响应 | 显示开发板和固件；继续 |
| 开发板断开，或从 Settings 返回 | 刷新并在就绪后继续 |

经典 ESP32 只能在 CP210x 桥接器（`10c4:ea60`，`UsbStream.java`）上工作；CH34x 和 FTDI 被列为不受支持。PKHeX 在手机上运行。保存和“打开文件夹”（一个 zip）使用 Android 的文件选择器。

## iOS 设置

[iOS 应用](../examples/ios/README.md) 是 iPhone 或 iPad（AltStore 或 SideStore）上的此界面。它通过蓝牙连接到开发板：从桌面开发板页面安装蓝牙无线固件（ESP32-C6 使用 `pokeldn-radio-ble-c6.bin`，经典 ESP32 使用 `pokeldn-radio-ble.bin`）；USB 仅用于供电。当手机占用开发板时，开发板会忽略 USB：在其他地方使用前请关闭 iOS 应用。应用文件位于“文件” > 我的 iPhone > pokeldn 下。

## 窗口尺寸

页面的面板按它们拥有的宽度进行布局，该宽度随窗口变化而测量
（`gui/theme.py` `Panes`）。选项列在其他列旁边时永远不会窄于 440 点。

| 留给面板的宽度 | 布局 |
|---|---|
| 侧栏面板在全宽加 440 点 | 并排显示 |
| 侧栏面板在 88% 加 440 点 | 并排显示，侧栏面板变窄 |
| 最后一个面板在 88% 加 440 点（三栏页面） | 前两个放在切换器上，最后一个在它们旁边 |
| 更小 | 每次在切换器上显示一个面板 |

从并排显示收窄窗口时，选项列会前移。在宽窗口中，选项列保持在 720 点、居中，字段每行尽可能多地排列。

## 手机

宽度低于 760 点时，页面位于底部标签栏中，面板在切换器上一次显示一个
（Games、Options、Session）。Android 和 iOS 没有 Control 或 Update 页面。

## 应用语言

“设置”中的“应用语言”列出英语和已安装的语言包
（[语言包](plugins.md#language-packs-15)）；更改会在重启后生效，缺失的字符串回退到英语。训练家语言独立设置。捆绑的 Noto Sans CJK SC 字体覆盖中文、日文和韩文（`gui/assets/fonts/LICENSE`）。它自身的 ‘ ’ “ ” · … 是全角形式，因此 Noto Sans Punctuation（同一字体中同样六个字符的拉丁宽度形式，`scripts/gen_punctuation_font.py`）会排在它前面；语言包中的 `font_family` 仍然优先。

## 你的训练家

“设置”中的“你的训练家”是本应用生成的所有宝可梦的初训家：名字、性别、语言和两组 ID，与游戏中显示一致。一条记录存储一个 16 位 TID 和一个 16 位 SID，它们是一个 32 位 id 的两半。

| 游戏 | 显示的 ID | 秘密 ID | 存储的 id |
|---|---|---|---|
| 火红／叶绿 | TID，0 到 65535 | SID，0 到 65535 | `SID << 16 \| TID` |
| 去吧！皮卡丘／去吧！伊布、剑／盾、晶灿钻石／明亮珍珠、传说 阿尔宙斯、朱／紫、传说 Z-A | id mod 10^6 | id div 10^6，0 到 4294 | `secret * 10^6 + ID` |

`Settings.ids` 会按游戏进行转换。每个主机连接工具都会将这位训练家作为其玩家展示
（`tests/test_gui_catalog.py`）。火红／叶绿的名字会被截断为七个 Gen III 字符；无法编码的名字会变为 `POKELDN`（`Settings.name`）。传说 Z-A 仅在性别、ID 和名字都匹配时将收到的宝可梦视为玩家自己的
（[收到的记录](za.md#what-the-trade-writes-into-a-received-record)）；传说 阿尔宙斯的记录携带性别（[记录](pla.md#the-games-reader-and-the-pre-handler-phase)）。

## Windows USB 驱动

经典 ESP32 的 USB 转串口桥接器在 Windows 提供 COM 端口之前需要驱动程序（设备管理器问题代码 28）。原生 USB 上的 S3、C3 和 C6 不需要。

| 桥接器 | USB id | 驱动 |
|---|---|---|
| CP210x | `10c4:ea60` | [CP210x VCP 驱动](https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers)：右键 `silabser.inf`，安装，重新插拔 |
| CH340 | `1a86:7523` | [CH341SER.EXE](https://www.wch-ic.com/downloads/CH341SER_EXE.html)：安装，重新插拔 |

没有 COM 端口时，开发板页面每 2 秒轮询 `Win32_PnPEntity`（`ConfigManagerErrorCode <> 0`），并指出已知桥接器（`gui/board.py` `bridges_without_driver`）。

## Linux 串口

串口需要 `dialout` 组（Arch 上为 `uucp`）；在 `EACCES` 时开发板页面会指出组名。

| 服务 | 开发板 | 影响 |
|---|---|---|
| brltty 6.4（Ubuntu 22.04） | CH340 | 占用它，没有 `/dev/ttyUSB*`（[LP 1990357](https://bugs.launchpad.net/bugs/1990357)）；修复：`sudo apt remove brltty` |
| brltty 6.6（Ubuntu 24.04） | CH340 | 仅在一个 `1a40:0101` 集线器后占用（[LP 1958224](https://bugs.launchpad.net/bugs/1958224)） |
| ModemManager 1.23 | 所有 | 没有针对 `10c4`、`1a86`、`303a` 的忽略规则 |

没有端口时，开发板页面读取 `/sys/bus/usb/devices`，并指出没有 tty 的桥接器
（`gui/board.py` `bridges_without_port`）。

## 本地存储

“设置”中的“存储”显示可回收的空间；清除本地文件会在确认后在后台删除，并在此期间暂停会话和刷写。请先保存任何用于错误报告所需的内容。

| 移除 | 保留 |
|---|---|
| `session/`（捕获、跟踪、临时提供）、`logs/`、`pokemon/` 中未使用的已生成或导入的提供、空文件夹 | 生成不到一分钟或被已保存设置和队列引用的提供；收到的文件、银行、存档、密钥、固件、设置；符号链接；检查后有改动的文件 |

## 你的存档

火红／叶绿神秘礼物工具的“你的存档”标签页会备份或恢复主机的存档
（[存档备份与恢复](frlg_gift.md#save-backup-and-restore)）。存档位于
`Documents/pokeldn/Saves`（`pokeldn.app.saves`；设置了 `POKELDN_DATA` 时位于其中），每个存档有一个 `.sav` 和一个 `.json`。

| 操作 | 发生什么 |
|---|---|
| 从 Switch 备份 | 写入 `backup-<run>.sav`；被截断的备份保留在 `Saves/.partial` 中，下一次会继续 |
| 将存档放到 Switch 上 | 传入 `--save-restore`；在选择存档之前 Start 会被阻止 |
| `+` 或拖入一个 `.sav` | 复制进来；16 字节模拟器尾缀会被丢弃，其他非 128 KB 的大小会被拒绝 |
| 重命名、导出、删除 | 删除会移除两边的本地文件 |
| 查看和编辑 | PKHeX 读取训练家、队伍和箱子 |

在没有完整存档副本或存在非法的队伍宝可梦时，恢复会被阻止，除非打开“仍要恢复”。编辑器会更改训练家姓名、性别、金钱、代币和队伍；“保留为新存档”会通过 PKHeX 写出新条目，并重新计算扇区校验和。

## 银行

银行页面会保留每只收到的宝可梦，并将其中一只交换到 HOME 会将其转移到的任何游戏。记录以对应游戏的格式和 `.json` 文件保存在 `Documents/pokeldn/Bank`（`pokeldn.app.bank`；设置 `POKELDN_DATA` 后在其内）中。

| 步骤 | 发生什么 |
|---|---|
| 一次交换完成 | 每个收到的文件按字节存入银行一次 |
| 宝可梦存入银行 | `.json` 保存物种、摘要、判定、来源、SHA-256、随机 63 位跟踪器、`home_tracker` |
| 目的地 | 助手的 `destinations` 会尝试全部七个游戏 |
| 选定目的地后 | `move` 会将其转换为该工具队列中的记录，并带 `"bank": id` |
| 第 N 次交换完成 | `[done] trade N complete` 会将其从银行移除 |
| 运行失败 | 它会留在银行和队列中 |

转移会使用 PKHeX 的 HOME 转换（通过 `PKH` 调用 `EntityConverter.ConvertToType`）和目的地的合法性检查。应用的训练家会成为处理者（`IHandlerUpdate`、`PB8.UpdateHandler`）；不合法的招式会采用 PKHeX 建议的招式组；PID、加密常数、初训家和 ID 会保留，并且运行会省略 `--fresh-pid`。

| 拒绝原因 | 来源 |
|---|---|
| 没有可回传火红／叶绿的宝可梦 | `EntityConverter.IsConvertibleToFormat` |
| 没有可传送到去吧！皮卡丘／去吧！伊布的宝可梦 | HOME 只会从它那里取走 |
| 蛋；携带道具或秘传招式的火红／叶绿宝可梦 | HOME 的火红／叶绿界面 |
| 目的地不存在该物种或形态 | 目的地的个人表 |
| 传说 Z-A 的记录无法转移 | PKHeX.Core 26.8.26 没有路线 |

编辑允许游戏允许的内容：昵称、提升等级、招式、携带物品。助手的 `check` 会拒绝会使合法宝可梦变为不合法的编辑。已排队的宝可梦不可编辑。`tests/test_bank.py` 通过真实助手覆盖转移、拒绝、编辑和导入。

### HOME 跟踪器设置

PKHeX 会在移入其他游戏的宝可梦以及通过 HOME 获得的礼物上标记缺失跟踪器（`TransferTrackerMissing`）。HOME 3.1.0+ 会拒绝并非它发放的跟踪器（错误 10015）。设置、高级、HOME 跟踪器（`Settings.home_tracker`）会随每次助手请求发送，并作为 `POKELDN_HOME_TRACKER` 传给运行。

| 设置 | 写入的跟踪器 | 合法性 | 警告 |
|---|---|---|---|
| `empty`（默认） | 无 | 在带跟踪器且合法时被接受 | PKHeX 会标记缺失的 HOME 跟踪器 |
| `made` | 随机 63 位（银行的） | 不变 | 无法存入 HOME |

在 `empty` 下，助手会以带跟踪器的副本及 HOME 的改动来判断记录（`ValidWithTracker`），因为 PKHeX 对跨 HOME 游戏的进化以及 Z-A 重新对齐的特性都取决于跟踪器。礼物遵循该设置（`MendGift`）；自制跟踪器会带有 HOME 的改动（`HomeSeen`：在朱／紫中 scale 作为身高，Z-A 中身高、体重和头目证章）。剑／盾神秘礼物卡片从不带跟踪器（[Pokémon HOME](swsh_gift.md#pokemon-home)）。

### 导入

加号按钮或拖入文件可导入存档（`SaveUtil.TryGetSaveFile`；3DS 存档是一个名为 `main` 的文件）或任意 PKHeX 格式的单条记录（`FileUtil.TryGetPKM`）。存档会先产出队伍槽位，再产出盒子槽位。

| 记录 | 保留方式 |
|---|---|
| 银行支持游戏的格式 | 合法时按原样保留 |
| 任何其他格式 | 移除携带物品，遗忘第 3/4 世代的秘传招式；若合法，则转移到第一个接受它的游戏：火红／叶绿、朱／紫、剑／盾、晶灿钻石／明亮珍珠、传说 阿尔宙斯、传说 Z-A |

非法的记录、校验和错误、其他游戏的蛋以及无法到达的物种会被拒绝。`Bank/.imported` 会保存每条导入记录的 SHA-256，因此重新导入存档只会带入有变化的记录。

### 未解决问题

- HOME 是否会接受自制跟踪器，或接受空跟踪器用于跨游戏移动的宝可梦。
- HOME 的火红／叶绿规则是否不止蛋、携带物品和秘传招式。
- 哪个字段承载 HOME 的 Switch 火红／叶绿来源图标；PKHeX 会通过宝可梦公园谱系转换 `.pk3`。

## GTS

GTS 页面会按物种列出公开的挂单，并在“你的”下显示玩家自己的挂单。存入会取走一只合法、未排队且已存入银行的宝可梦，挂单期间保存在 `Documents/pokeldn/GTS`。应用在运行时随时回应交换请求（[GTS](online.md#the-gts)）。

## 开发板与固件

开发板页面会列出每块已插入的开发板，并显示其固件、版本以及“最新”或“可更新”。固件卡片（`gui.board.FIRMWARES`）会在确认后安装 Wireless 或 Controller；从文件安装会接受一个 pokeldn `.bin` 文件。

| 开发板 | 发现方式 | 版本来源 |
|---|---|---|
| Wireless | 串口 | HELLO 回复 |
| Controller，经典 ESP32 | 串口 | 状态帧 |
| Controller，ESP32-S3 | USB ID `0f0d:0092` | 蓝牙状态 |
| 无 | 串口，无应答 | 无 |

随附版本是 ESP-IDF 应用描述符的 `version`（魔数 `0xABCD5432`，在合并映像中的 `0x10020` 处）。运行 Controller 固件的 S3 会通过蓝牙接收下载命令；应用会等待 20 秒加载器端口，并使用 `--from-loader` 刷写。

作为[便携信标](hardware_esp32.md#portable-beacon)保留的开发板会显示“保留的礼物”和“移除”。

### 开发板详情

在开发板页面，无论是否选择了开发板，“复制开发板详情”都会将详情复制为纯文本，并将其保存到数据文件夹中的 `logs/board-report-DATE.txt`（`gui/board_report.py`）。复制详情会打开所选端口，因此开发板可能会重新启动；在运行期间它只会列出端口。

| 部分 | 包含内容 |
|---|---|
| 此计算机 | 应用版本、打包或源码、系统、Python、pyserial 和 esptool 版本 |
| USB 串口 | pyserial 列出的每个端口，包括其 USB ID、序列号、位置和 `hwid` |
| 驱动程序 | 无驱动的 Windows 桥接器、无 tty 的 Linux 桥接器、USB 上的控制器开发板 |
| 打开端口 | 打开时的错误及 `errno`/`winerror`，或前 2 秒读取到的字节 |
| pokeldn 固件 | HELLO 和 STATUS，或为何无响应 |
| ESP32 引导加载程序 | esptool 的芯片、描述、特性、晶振、MAC 和 USB-Serial/JTAG 模式 |
| 活动 | 页面最后 80 行 |

## 控制器

控制页面会通过 Controller 固件按下 Switch 的按键（[控制器开发板](hardware_pad.md)）并播放宏。ESP32-S3 插入 Switch，并通过蓝牙 LE 连接；经典 ESP32 则保留在电脑 USB 上，并从“更改握法/顺序”配对。重新安装会清除配对。当连接断开时，页面会不断搜索，直到开发板应答或点击“停止寻找”。

| 部分 | 作用 |
|---|---|
| 屏幕控制器 | 按住按钮；摇杆可向八个方向，L3/R3 在中心 |
| 键盘 | 方向键 D-pad，X A，Z B，S X，A Y，Q L，W R，1 ZL，2 ZR，Enter +，Backspace -，H HOME，C 截图 |
| 录制到宏 | 每次按压会成为带有按住时间和暂停的一步 |
| 宏编辑器 | 按钮、摇杆、等待、嵌套重复；运行一次和循环部分 |
| 在开发板上播放 | 开发板会按自己的时钟播放宏 |

宏是 `Documents/pokeldn/Macros` 中的 `.pokemacro` 文件（[控制器开发板，宏](hardware_pad.md#macros)）。该页面与 `127.0.0.1:47800` 上的 `pokeldn.pad.service` 通信。在 macOS 26 上，以 bundle 主可执行文件签名的进程无法发现蓝牙，因此打包后的应用会从 `Contents/Helpers/pokeldn-bluetooth` 运行该服务，这是一个以裸签名方式签名的副本，其 `_internal` 链接到 `../Frameworks`。

## 宝可梦精灵图

图片按需来自 [PokeAPI](https://github.com/PokeAPI/sprites)，并缓存在 `sprites/` 中。设置、宝可梦精灵图会禁用下载并清空缓存。缺失的图片会显示占位图；缺失的异色图片会回退到普通图片。

## 团体战活动

朱／紫太晶团体战（主办）的团体战活动卡片会主持来自 [EventsGallery](https://github.com/projectpokemon/EventsGallery)（[活动团体战](sv_raid.md#event-raids)）的团体战，这些文件会复制到 `EventsGallery/`（`pokeldn.app.events_gallery`）中。下载会从 `codeload.github.com` 获取触碰 `Released/Gen 9/SV/Raid Events` 的最新提交，并保留每个活动的最新表；检查更新会比较该提交。副本只有在完整复制后才会替换旧副本；Windows 会以 `\\?\` 打开长路径。

选择某个活动后，团体战卡片会限制为其版本、进度和结晶（`raid_event.constrain`），而查找团体战会限制为其结晶、头目和奖励表（[寻找种子](sv_raid.md#finding-a-seed)、[体型证章](sv_raid.md#size-marks)）。只能捕捉一次的头目会提供“让它再次被捕捉”（`--raid-catch-normal`）。折叠卡片会恢复为普通团体战（“关闭：活动”）；副本中缺失的活动会显示“缺失：活动”，运行会拒绝它。

## 主持团体战奖励

奖励卡片会提供模板（训练道具、薄荷、对战道具、树果、进化道具、太晶碎块、秘传调味料、宝物、球），共享数量从 1 到 999；编辑会切换到自定义奖励，最多 45 行。团体战自身奖励会清除覆盖（[主持](sv_raid.md#hosting)；`gui/views/rewards.py`）。

## 团体战 NPC 队友

团体战 NPC 队友卡片会填补主机空出的位置（[队友](sv_raid.md#partners)；`gui/views/raid_partners.py`）；未选择任何内容时，主机会像主机一样随机抽取队友。队友的进度会传递 `--raid-partner-progress`；每张卡片会显示训练家、宝可梦（等级为我方宝可梦的五分之四）、太晶属性、特性和招式，偏爱的队友带有蓝色或银色条带（[偏爱的队友](sv_raid.md#favoured-partners)）。每次点击会按位置顺序传递 `--raid-partner`；舞台缺少的选项会被丢弃。

## 联合环

朱／紫的联合环工具会通过四位数字的密语加入主机的圈子（[联合环](sv_union_circle.md)）；该字段初始为空。

- 任务：解锁剩余的 Snacksworth 传说宝可梦或给予 BP（1 到 9,999,999）；Snacksworth 运行会绘制清除次数的[进度](#progress)条。
- 遭遇：生成卡片（`gui/views/encounter.py`）可设置物种、异色、形态、等级、太晶属性、性格、性别、特性、携带物品、体型和个体值；仅合法遭遇（默认）会将其限制为 PKHeX 接受的内容，并列出有效位置。它会传递 `--spawn` 和 `--spawn-*`。

运行期间，`[panel]` 卡片（[状态卡片](plugins.md#status-cards-18)）会显示在工具选项上方。`--verbose-circle` 会记录每条联合环消息。

## 神秘礼物 - 模拟

工具在去吧！皮卡丘／去吧！伊布、晶灿钻石／明亮珍珠、传说 阿尔宙斯、朱／紫和传说 Z-A 上的卡片会列出 PKHeX 事件表中的礼物宝可梦（[模拟神秘礼物](gift_simulated.md#the-gifts)；`gui/views/event_gifts.py`），最新的排在最前，可搜索。点击会为设置中的训练家排队一份新副本；一次主持会话最多可交换六份礼物。副本会保留其创建时的训练家。

如果礼物指定的接收者语言没有任何存档到达，则会显示非法图块（[卡片到达的存档](gift_simulated.md#saves-a-card-reached)）。为接收玩家制作（默认开启）会针对主机的存档重新制作此类礼物（[为接收玩家制作](gift_simulated.md#made-for-the-receiving-player)）；当没有符合条件的排队礼物时，该开关会被禁用，且不会传递 `--for-receiver`。HOME 礼物会以琥珀色描边，并采用 [HOME 跟踪器设置](#the-home-tracker-setting)（[交换提供的副本](gift_simulated.md#the-copy-a-trade-offers)）。

## 隐私日志

设置、在日志中隐藏个人详细信息（默认开启）会遮盖显示和复制的日志（`pokeldn/app/redact.py`）：

| 被遮盖内容 | 显示为 |
|---|---|
| 路径中的主文件夹 | `~` |
| iOS 应用容器 | `<app>` |
| MAC 地址的设备部分 | `**:**:**` |
| `ot_name`、`ht_name`、`OT`、`nickname`、`trainer`、`player`、`name` 后面的引号值（`POKELDN`、`PKLDN` 除外） | `***` |
| `TID`、`SID`、`trainer_id` 后面的值 | `***` |
| 见过的训练家名称，以及设置中的那个，作为完整单词 | `***` |

会话记录（`captures/`）不会被遮盖。链路本地地址会保留。

## 弹窗

运行、子进程和应用可在任何页面打开弹窗（`pokeldn.popup`，插件 API 1.2）。

| kind | callback |
|---|---|
| `acknowledge(title, text)` | `on_ack` |
| `confirm(title, text, agree, disagree)` | `on_agree`, `on_disagree`, `on_dismiss` |
| `choose(title, text, options)` (1.7, 2 to 8 options) | `on_choice(index)`, `on_dismiss` |

选项：`id`（重新打开一个已打开的 id 会替换它并丢弃其回调）和 `tone`（`info`、`warning`、`error`）。打开会返回 id；回调在应答线程上运行，除非设置了 `set_dispatcher(dispatch)`。`cancel(id)` 关闭一个。32 个未应答弹窗会引发 `RuntimeError`。没有应用（`available()` 为 false）时，弹窗是一行 `[pop-up]` 输出。

`runner.Process(..., popups=app.popups)` 设置 `POKELDN_POPUPS=1`；子进程在 stdout 写入 `[popup]` 和 JSON，并在 stdin 读取 `[popup] {"id", "n", "answer"}`（`pokeldn.app.runner.child`）；`n` 使对被替换弹窗的迟到应答不触发任何东西。`pokeldn.app.popups.Manager` 保存它们，`gui.popups.Dialogs` 绘制它们。应用自身的弹窗会报告更新失败、插件被禁用，以及通过 Settings 训练家发送的接收者礼物（[交换](gift_simulated.md#the-trade)）。

## 进度

一次运行会打印 `[progress] DONE TOTAL UNIT TITLE`（`pokeldn.progress.show`，API 1.7；`UNIT` 为 `bytes` 或 `items`）来绘制一个带有总量、30 秒速率和剩余时间的进度条，每个标题每秒最多四行。`[save]` 行绘制相同的进度条。

## 更新

启动时，应用会请求 `api.github.com/repos/Decryptu/pokeldn/releases/latest`（5 秒超时）。高于 `pokeldn.__version__` 的 `vX.Y.Z` 标签会添加一个带有“立即更新”或“下载”的更新条目。

立即更新（`pokeldn.app.update`）会将平台归档文件和 `SHA256SUMS` 下载到 `update/`，拒绝校验和不匹配，解包（`ditto -x -k`、`tarfile` 的 `data` 过滤器、`zipfile`），然后启动 `pokeldn --apply-update NEW TARGET PID VERSION`（`gui/updating.py`）。辅助程序等待旧应用退出（在 Windows 上还要等待其进程），将其重命名为 `.<name>.old`，复制新应用并打开；任何失败都会恢复旧应用。新应用只读取一次 `update/outcome.json`。校验和可检测损坏，但不会验证发布来源。

| 情况 | 行为 |
|---|---|
| 预发布、草稿、异常标签 | 不提供 |
| 无网络 | “立即检查”显示 GitHub 未响应 |
| Settings 中关闭更新 | 不发起请求 |
| 没有归档文件或 `SHA256SUMS`、源码检出、App Translocation、文件夹不可写（macOS、Linux） | 仅下载 |
| Windows，`C:\Program Files` | “立即更新”需要 UAC（`ShellExecuteExW` `runas`） |
| Windows，另一个驱动器的根目录（`D:\pokeldn`） | “立即更新”无需 UAC：交换只会在应用旁边添加文件夹，这是卷根目录允许用户进行的操作。0.34.0 之前的版本会用文件探测根目录并在那里请求 UAC，标准用户的更新会在“Windows did not give pokeldn permission to change D:\”处停止；从这样的版本开始，下一个版本只能手动下载一次 |
| Windows，映射或 `subst` 驱动器 | 驱动器盘符会保留；辅助程序会以两种拼写找到旧应用的进程；在 UAC 后，辅助程序会获取该盘符所指的文件夹，因为提升的进程看不到用户会话中映射的盘符 |
| 有会话、烧录或清理正在运行 | 要求先完成 |

`scripts/check_update.py ARCHIVE FOLDER` 针对 127.0.0.1 测试打包应用的更新；`POKELDN_UPDATE_URL` 可替换端点（`tests/test_app_update.py`）。macOS 是否会请求 `/Applications` 中的 App Management 权限尚未测量。

## 文件拖放

| 目标 | 接受 |
|---|---|
| 一个交换的宝可梦 | 一个宝可梦文件或 Showdown `.txt`；多余文件会填充后续交换 |
| 添加交换 | 每个文件一个交换 |
| 礼物卡片 | `.pokegift`、`.wc8`、`.wc3` |
| Board 固件卡片 | 一个 pokeldn `.bin` |
| 任何路径字段 | 文件或其文件夹 |

Flet 1.0.2 的客户端不支持拖放；`scripts/build_client.py` 会使用 `gui/flet_drop`（[desktop_drop](https://pub.dev/packages/desktop_drop)）构建 Flet 客户端到 `gui/client/<platform>`，使用 `python -m flet_cli.cli --version --json` 命名的 Flutter 版本，macOS 部署目标为 12.0。没有它，`gui/main.py` 会运行 Flet 自带的客户端，不支持拖放。

## 文档页面

Docs 页面显示应用指南和本站的每个可导航页面；搜索匹配章节，要求每个词都匹配，标题优先（`gui/views/docs.py`）。

## 未发售游戏标题

在其 Switch 发售前提前推出的游戏标题仅会从源码检出中显示在 Games、Bank 和 Docs 中（`pokeldn/app/preview.py`）。`POKELDN_PREVIEW=1` 会在任何地方显示它，`0` 会隐藏它。其文档页面会设置 `nav_exclude` 和 `search_exclude`。

## 从源码运行

安装 Python 3.13 和 .NET 10 SDK：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r gui/requirements.txt
dotnet build -c Release services/pkhex -warnaserror
python scripts/build_client.py    # optional: file drops; needs Flutter
python gui/main.py
```

Raspberry Pi OS 会将 piwheels 添加为软件包索引，而 piwheels 的 `flet_web-1.0.2-py3-none-any.whl`（25 KB）缺少 PyPI wheel（27 MB）所带的 `flet_web/web` 客户端；应用随后会报 `RuntimeError: Web root path not found`。请仅从 PyPI 安装该软件包：`python -m pip install --force-reinstall --no-cache-dir --index-url https://pypi.org/simple flet-web==1.0.2`。没有 Linux arm64 发布版；Raspberry Pi 从源码运行应用。

源码检出没有固件镜像。在 Board 页面下载固件会从最新版本获取所有镜像及其 `SHA256SUMS`，并且仅在所有都匹配时才写入。

## 构建桌面应用

在 ESP-IDF v6.1 激活的情况下，将每个镜像构建到 `gui/firmware`，然后打包：

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
python scripts/build_unicorn.py   # needs CMake
python scripts/pack_app.py
```

冻结应用检查会验证每个镜像、`flet_drop` 客户端和 Unicorn 都已打包。版本为 `pokeldn.__version__`，通过与 `.github/release-notes.md` 一同更新，其首行必须为 `# pokeldn X.Y.Z`（`tests/test_release.py`）。`v*` 标签会发布九个文件和 `SHA256SUMS`；只有带连字符的标签才是预发布版。

这些应用是单文件夹 PyInstaller 构建（`pokeldn.app`；一个 `pokeldn` 文件夹，`_internal` 在其他位置）：在 M4 上，Games 页面 0.7 秒打开，运行 0.08 秒启动。`scripts/pack_app.py` 在 Flet 的 `--onefile` 之后传入 `--onedir`，并设置 `LSBackgroundOnly`，因此只有查看器有 Dock 图标。

| 部分 | 大小 | 保持小巧的方法 |
|---|---|---|
| Flet 查看器 | 31 MB（macOS 上 xz 为 9.4 MB） | 无扩展组件、单一架构、`--split-debug-info` |
| Unicorn | 3 MB | 仅 ARM 和 ARM64 引擎 |
| PKHeX 辅助程序 | 16 MB | 完全裁剪 |
| Python | 8 MB | 排除 web、image、test 和 syntax 模块；macOS 上 `strip -x` |

打包陷阱：

- 裁剪会禁用反射 JSON；`JsonSerializerIsReflectionEnabledByDefault` 可恢复它。`DynamicDependency` 会保留 PKHeX.Core 的 Gen 3 事件表。
- macOS 查看器归档文件是名为 `flet-macos.tar.gz` 的 xz；`gui/flet_client.py` 会通过压缩检测打开它，并移除标记为 `pokeldn-drop` 的过期 `~/.flet/client` 文件夹。
- 切勿对可执行文件或 PKHeX 辅助程序执行 strip：两者都携带 Mach-O 映像之后的归档文件。
- `scripts/pack_flet.py` 会保留查看器的 entitlements；如果没有 `com.apple.security.files.user-selected.read-write`，选择 `prod.keys` 会引发 `ENTITLEMENT_NOT_FOUND`。
- 在 Linux 上，`pokeldn/app/paths.py` 会恢复用户的 `LD_LIBRARY_PATH`（捆绑的 `libstdc++` 会破坏 Fedora 的 EGL）并设置 `FLET_LINUX_DISTRO`。
- 在 Control Flow Guard 下，Unicorn 会以 `0xC0000409` 中止（[unicorn#2281](https://github.com/unicorn-engine/unicorn/issues/2281)）；打包器会清除 `pokeldn.exe` 中的 `GUARD_CF`（从 `0xC160` 改为 `0x8160`）。切勿在冻结检查中启用 `faulthandler`。

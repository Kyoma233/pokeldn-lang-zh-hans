---
title: The Switch build
parent: Ruby, Sapphire and Emerald
nav_order: 3
nav_exclude: true
search_exclude: true
app_exclude: true
---

# 面向 Switch 火红应用的绿宝石

Switch 构建是把 pokefirered 中 `REVISION >= 0xA` 的改动移植到 pret/pokeemerald，并链接成让火红／叶绿应用的载入期补丁落在绿宝石无线驱动上的版本。它替代火红卡带运行：在模拟控制台上可以存档、接收神秘礼物、交换，并与 pokeldn 主机使用联盟房间。`tools/rse/pokeemerald_switch.patch` 是相对 pret 提交 `731ad5bf` 的移植；`tools/rse/emerald_switch_build.py` 负责应用并构建。

## 应用对卡带的要求

英文 Switch 火红 ROM 就是 pret/pokefirered 的 `make compare_firered_switch`
（[ROM 映射](frlg_rom_map.md#the-cartridge-image)）；移植内容是该构建相对 REVISION 1 的差异，应用到绿宝石中相同文件的副本上。

- **系统调用。** 应用提供 `swi 0x40..0x62`（Sloop 调用，
  [主机上的代码](frlg_rom.md)）。`src/sloopsvc.c` 与 pokefirered 相同、未改动：无线适配器调用（`0x42..0x53`）、`WriteSector`（`0x48`）、`ReplaceSector`（`0x56`）、`FinishSave`（`0x4C`）、家长控制（`0x54`）、敏感词过滤（`0x4D`）、`SetSaveBlock2`（`0x55`）、`SetStarter`（`0x57`）、`SetActivity`（`0x61`）与 `IncrementLinkError`（`0x62`）。
- **存档。** 应用仅在 `svc_FinishSave` 时把闪存镜像写入存储。构建通过 `svc_WriteSector`／`svc_ReplaceSector` 写扇区，并在 pokefirered 同样的位置调用 `svc_FinishSave`：`HandleSavingData` 结束、特殊存档扇区、最后一块链路存档扇区。
- **固定地址上的驱动。** 载入时应用会在卡带自身的 `Sio32IDMain + 0x12E`、`IntrSIO32 + 8` 与 `IntrSIO32 + 0x71C` 处打三处指令补丁
  （[断点钩子](frlg_rom.md#the-breakpoint-hooks)）。`ld_script_switch.ld` 把 `librfu_sio32id.o` 与 `librfu_intr.o`（`+0x30C`）放进位于卡带地址的 `sloop_rfu` 节；代码字节与火红相同，仅字面量指针与 `bl` 偏移不同。

| cartridge | `librfu_sio32id.o` | | cartridge | `librfu_sio32id.o` |
|---|---|---|---|---|
| BPRE | `0x081E2814` | | BPGE | `0x081E27F0` |
| BPRF | `0x081E1568` | | BPGF | `0x081E1544` |
| BPRD | `0x081E702C` | | BPGD | `0x081E7008` |
| BPRI | `0x081E0200` | | BPGI | `0x081E01DC` |
| BPRS | `0x081E28C8` | | BPGS | `0x081E28A4` |
| BPRJ | `0x081C66EC` | | BPGJ | `0x081C66C8` |

日文地址落在绿宝石的 `.text` 内；那两张卡带不构建。

## 补丁改动了什么

每处改动都放在 `#if REVISION >= 0xA` 下，因此 `make compare` 仍与 pret 的 ROM 一致。

| 区域 | 文件 |
|---|---|
| 构建 | `Makefile`（`REVISION`、`SWITCH_CART`、地址表、`make emerald_switch`）、`ld_script_switch.ld`、`sym_common.txt` |
| 系统调用 | `include/sloopsvc.h`、`src/sloopsvc.c` |
| 适配器库与链路管理器 | `librfu.h`（版本 1028）、`librfu_rfu.c`、`AgbRfu_LinkManager.{c,h}`：svc 调用、更长周期、关闭链路恢复 |
| 链路层 | `link_rfu_2.c`（rev10 超时、重新播种、重载以及 `svc_51` 上的软复位）、`link_rfu_3.c`（ASCII 表）、`link.c`（错误屏幕、`HandleLinkConnection`） |
| 联盟房间 | `union_room.c`（队长与加入组状态机、活动报告、家长控制）、`union_room_chat.c` 与 `naming_screen.c`（敏感词过滤）、`union_room_player_avatar.c`、`union_room_battle.c` |
| 存档 | `save.c`、`load_save.c`、`main.c`（`svc_SetSaveBlock2`、黑色背景、软复位时不等待适配器） |
| 时钟 | `rtc.c`（未附加 GPIO 端口时的软件时钟，[实时时钟](#the-real-time-clock)） |
| 护栏 | `cable_club.c`、`trade.c`、`field_screen_effect.c`、`menu.c`、`task.c`、`wireless_communication_status_screen.c`、`mystery_gift_menu.c`、`battle_setup.c`（`svc_SetStarter`） |

未纳入：pokefirered 的开场配色、状态屏幕计数、链路测试移除、名人堂船票、树果修复、中毒闪烁速度、多选项默认值与 `NDEBUG`。交换仍保留绿宝石的五轮交换后待机（[交换](rse_link.md#trade)）。

## 构建

需要 pret/agbcc、arm-none-eabi binutils 与 C 预处理器。

    ./.venv/bin/python tools/rse/emerald_switch_build.py --tree ~/pokeemerald_switch --agbcc ~/agbcc \
        --cart BPRE --cpp /opt/homebrew/bin/cpp-16 --compare

`--tree` 若不存在则克隆并检出到基线提交。`--agbcc` 在树内运行 agbcc 的 `install.sh`。`--compare` 还会构建 REVISION 0 并运行 pret 的 sha1 检查。工具会拒绝把 `librfu_sio32id.o` 放到卡带地址以外的 ROM 映射。Homebrew 不附带 `arm-none-eabi-cpp`；用 `--cpp` 指定另一个。

全新克隆下，BPRE 构建的 sha1 为 `a1de677b211ba967b721233ef6096de0e1507c6b`，REVISION 0 构建通过 `pokeemerald.gba: OK`。

## 运行

应用每次启动都从 RomFS 加载 ROM（[ROM 映射](frlg_rom_map.md)），因此覆盖该路径的 LayeredFS 文件会替换卡带直到被移除。`tools/rse/rom_mod.py` 可将其安装到模拟器的 mod 文件夹或 Atmosphere SD 卡上：

    ./.venv/bin/python tools/rse/rom_mod.py install pokeemerald_switch_BPRE.gba --title 0100554023408000 --data FOLDER
    ./.venv/bin/python tools/rse/rom_mod.py install pokeemerald_switch_BPRE.gba --title 0100554023408000 --sd /Volumes/SWITCH
    ./.venv/bin/python tools/rse/rom_mod.py remove --title 0100554023408000 --data FOLDER

ROM 必须匹配标题的卡带：英文火红（`0100554023408000`）用 BPRE，法文火红（`01004B3023412000`）用 BPRF。游戏沿用标题的存档文件名（`FireRed_e.sav`）；绿宝石存档与火红存档不能共用，因此先备份火红存档。

在模拟控制台（英文火红，BPRE 构建）上，绿宝石以 60 FPS 启动，不显示电池耗尽消息，可以存档，并在重新启动后加载存档。把模拟器的 LDN 指向 Mac 后，主机的 `--over-ip` 可为其服务（[交换与联盟房间](rse_link.md)、[神秘礼物](rse_gift.md)）。

## 测试存档

链路功能受剧情标志控制。`tools/rse/emerald_save.py` 编辑游戏加载的槽位并重算校验和（[存档](rse.md#the-save)）：

    ./.venv/bin/python tools/rse/emerald_save.py FireRed_e.sav --link-ready --copy-party-mon 0

| 标志 | 开启内容 |
|---|---|
| `FLAG_SYS_POKEDEX_GET` `0x861` | 宝可梦中心 2 楼接待员 |
| `FLAG_SYS_MYSTERY_GIFT_ENABLE` `0x8DB` | 标题菜单上的 MYSTERY GIFT |

`--link-ready` 设置二者，并把继续传送点设为古鲁鲁镇宝可梦中心 2 楼（地图组 2、地图 3、x 5、y 4）。`--copy-party-mon N` 以新 PID 追加队伍槽位 N 的副本，让只有一只宝可梦的存档也能交换。图鉴标志会显示 POKeDEX 菜单，但没有遇见或捕获条目。

绿宝石会按火红存档文件中的样子加载整份零售绿宝石存档：在模拟控制台上，一份设置了 `FLAG_SYS_MYSTERY_GIFT_ENABLE` 的 128 KB 存档显示了其训练家、MYSTERY GIFT 条目及其菜单，CONTINUE 加载了野外。软件时钟未弹出电池消息。

## 不经 Atmosphere 的交付

运行 Atmosphere 的控制台把 ROM 当作 LayeredFS 文件（[运行](#running-it)）。原版控制台只读取标题已签名的 RomFS，因此 ROM 必须在每次启动时，从游戏内部、经与存档传输相同的神秘礼物原生代码路径写入正在运行的 ROM 副本（[存档备份与恢复](frlg_gift.md#save-backup-and-restore)）。

已测得并支撑该设计的三种机制：

- `swi 0x48` 配合 `r0 = 0xFA000 + n`（n 在 0..0xFFF）把来自客户源的 4 KB 写入 ROM 副本的 `0x08000000 + n * 0x1000`，覆盖全部 16 MB（[闪存扇区路径](frlg_rom.md#the-flash-sector-path)）。
- 这样写入的代码可以运行：复制到 `0x083FF000` 的例程在分支过去后执行
  [frlg_rom.md](frlg_rom.md#the-flash-sector-path)。
- 存档传输把压缩数据跨多条神秘礼物消息流入常驻 EWRAM 块，每次解压 `0x800` 字节并写入各扇区，大约每条消息 1 KB 令牌
  （[存档备份与恢复](frlg_gift.md#save-backup-and-restore)）。

ROM 传输就是把写入目标从闪存扇区（0..13）改成 ROM 折叠（`0xFA000 + n`）、并在结束时启动而不是存档的同一条流水线。每次启动都要重做流，因为 ROM 副本在每次应用启动时都会从 RomFS 重新加载。

### ROM 传输

`bin/frlg_mg_host.py --rom-transfer ROM` 运行它（`pokeldn.frlg.gift.rom_transfer`、
`asm/rom-transfer.s`；`--rom-no-boot` 在检查后停止）。一次会话：

1. 安装载荷，并停止 m4a 引擎（将 `gSoundInfo.ident` 与 `SOUNDCNT_X` 清零）：否则音乐会从正在被替换的 ROM 读取歌曲与波形数据；
2. 对 ROM 副本的全部 4096 个块做哈希（`h = rotl(h, 1) ^ word`，每帧 32 块）；
3. 写入哈希与镜像不同的每个块，每 62 条消息确认一次，每个块通过 ROM 窗口回读；连续相同单字节的块作为最多八块的填充消息发送；
4. 再次哈希所有块并比较；
5. 发送启动操作：在关闭 `IME` 与四个 DMA 通道后，把暂存块就位，镜像之后的块变成 `0xFF`，然后 `swi 0x00`。

哈希过程使一次中断的会话可在同一次应用启动内恢复：下一会话只写入仍不同的块。

在模拟英文火红上经 IP 主机测得：一张把三处标题屏幕调色板改色的火红镜像（块 `0xEAB`、`0xEAD`、`0xEAE`）就地写入那 3 块，在 `0xEB1` 暂存 151 个活动块，检查通过，启动操作后控制台经开场重启到改色后的标题屏幕。

面向 BPRE 的整份绿宝石构建已在模拟英文火红上流式传输并启动：3073 块就位、157 个活动块暂存于 `0xE3D`，4268 条消息中共 3,691,122 字节 LZMA（`--block-repeat 1 --inter-block-gap-frames 8`，消息在 10 帧解码处截断），检查整段通过，启动操作在 3 小时 12 分发出，随后在火红应用中出现绿宝石开场及其标题屏幕。过了标题后绿宝石打印 “The internal battery has run dry. The game can be played.” 与 “However, clock-based events will no longer occur.”，然后主菜单在火红存档上提供 CONTINUE（读回玩家名与游戏时间，0 枚徽章）。经 LayeredFS 在启动时加载的绿宝石不显示电池消息（[实时时钟](#the-real-time-clock)）。

当控制台丢失一条消息的第一个数据块时，流会结束。控制台只有在读完前一块后才接受下一块 [link_rfu_2.c:1146]，而下一条消息的头可能在它仍在解码上一条时到达。在模拟控制台上，传到 2240 块时，控制台发给主机的帧有四次在 0.6 秒内相隔 0.07 到 0.12 秒，同时主机仍在发送。客户端接收缓冲区随后在偏移 0 到 756 持有该消息的块 1 到 4，并在 1008 持有下一条消息的头。CRC 失败，`LinkRfu_FatalError` 运行，`sLinkErrorBuffer` 读作 `0x90000000`（[模拟器可以自行关闭链路](frlg_link.md#the-emulator-can-close-the-link-on-its-own)）。断开帧在该头之后 0.3 秒出现。主机现在按收到的控制台帧计间隙，并在繁忙消息之后的头后留下 24 帧（`HEADER_GAP_FRAMES`）。两者兼用时，3645／3645 块在 3 小时 13 分内全部通过且无中断，检查整段通过，绿宝石经开场启动到标题与主菜单且无电池消息，存档上显示 CONTINUE（POKELDN，137:40，0 枚徽章）。单独用其中一项是否足够尚未测量。

主机在应用的子进程中编码（`pokeldn.frlg.gift.rom_transfer`，`--module`），因为打包应用没有 `multiprocessing`；在手机上则用线程。使用 `--rom-base none` 时主机没有卡带，流是不命名控制台副本任何块的 LZMA：BPRE 构建为 6,349,961 字节，同一编码器下相对卡带为 3,350,357，未压缩为 11,842,749。

解码器自身负载已被排除：unicorn 下整条 BPRE 流（`tools/rse/rom_stream_cost.py`）峰值每次调用 96,715 条指令，且没有消息超过其静默帧。

绿宝石存档在流之前、同一次应用启动中用 `--save-restore-emerald FILE` 写入。它把文件的最新副本以下一计数器写到芯片最新副本旁边，外加槽位之后的四个扇区（19 个扇区，模拟控制台上约 7 到 9 分钟），逐个回读后停止。跳过火红的加载：其校验和在绿宝石块上失败，且其存档会覆盖该副本。绿宝石的块比火红更长，火红扇区尾部为零，因此绿宝石会接受火红副本并取更高计数器；火红拒绝绿宝石副本并继续加载自己的。

应用把闪存保存在内存中，模拟控制台的存档文件在写入后、离开神秘礼物后或模拟器关闭时都没有变化。若在游戏存档前重新启动，写入的副本会丢失，因此流必须在同一次启动中跟进。经 GDB，闪存在计数器 195 持有文件副本、在 194 持有火红副本；把该镜像当作存档文件、并在启动时加载绿宝石，会显示文件的训练家与 MYSTERY GIFT 条目，CONTINUE 加载野外。存档写入后的完整流尚未运行。

同一顺序已在零售 Switch Lite 上、英文火红、经固件 1.9.3 的 XIAO ESP32S3 跑通：存档备份、`--save-restore-emerald`（19 个扇区共 390 秒），然后 `--block-repeat 1 --inter-block-gap-frames 8` 的流在 3 小时 18 分写入 3645／3645 块且无丢包。绿宝石启动、加载绿宝石存档并在游戏中存档。控制台自动休眠会在距上次按键约 10 分钟后以错误 2318-0314 结束流，且没有 RFU 断开帧；游戏撑过了这一点，回到标题并保留块与已写入存档，火红在加载自己的副本前打印存档损坏，下一会话恢复流。

### 回到火红

重新启动应用会从 RomFS 重新加载火红，但存档文件可能仍保留绿宝石的扇区。火红随后会打印 “The save file is corrupted.” / “The previous save file will be loaded.”，并在另一槽完整时加载该槽；两个槽都不完整时只提供 NEW GAME，此时神秘礼物会话无法到达控制台。

若控制台仍在运行绿宝石，`tools/rse/emerald_save_restore.py` 会从绿宝石的神秘礼物执行存档恢复。它用 FinishSave 桩构建 `asm/save-restore.s`：`swi 0x4C` 把整份 128 KiB 闪存镜像提交到 `save:/`，桩返回 0 而不是 `SAVE_STATUS_OK`，因此神秘礼物菜单以失败结束，正在运行的游戏不会把恢复后的镜像再存回去。载荷读取绿宝石的 `gSaveCounter`（BPRE 与 BPRF 构建中为 0x03006320），主机以绿宝石身份通告。在模拟法文火红上测得：一个 VBlank 钩子经 `swi 0x48` 把扇区 30 写成 `0x5A`，然后调用 `swi 0x4C`；存档文件发生了变化，扇区 30 读回 `0x5A`；同样的写入若没有 `0x4C`，则只留在内存中的闪存镜像里。在运行绿宝石 BPRE 构建的零售英文火红 Lite 上，该绿宝石构建的神秘礼物 → 神秘卡片 → 朋友界面变成黑屏：控制台已关联到主机的 Wi-Fi，但从未发送其 LinkPlayer 块，因此零售机上的 FinishSave 路径尚未验证。

控制台现已回到火红，并带有一份全新存档。旧存档是 `scratchpad/lite/lite_backup.sav`（GURVAN，TID 57189，SID 58811，156h30m）。一旦在火红上解锁神秘礼物，普通恢复会写入、加载并保存它：

    bin/frlg_mg_host.py --save-restore scratchpad/lite/lite_backup.sav --live ...

ROM 副本携带应用的三处 librfu 补丁（[断点钩子](frlg_rom.md#the-breakpoint-hooks)），卡带文件没有它们。镜像写入时在卡带的 `librfu_sio32id.o` 处应用相同补丁（`builds.SIO32ID`，偏移 `+0x12E`、`+0x314`、`+0xA28`；十二张卡带上均核验过那里的字节）。若那里的字节不是卡带指令则拒绝：补丁会落到别的代码上。

### LZMA 流

当 `--rom-base` 命名控制台自己的卡带 ROM 时，块以 LZMA（lc 0、lp 0、pb 2，`pokeldn.frlg.gift.rom_lzma`）发送，而不是游程与字面量令牌。字典就是控制台副本本身：低于 16 MB 的虚拟位置是副本字节，超过则是流的输出。从 0 到仍需写入的最高块，每个块都会发出，主机写入顺序先写 ROM 块 `0xFFD` 与 `0xFFE`：一次无可用性限制的扫描记录每个块从哪些副本块复制，若某块从另一副本块取走 8 字节或更多，则该块排在那一副本块之前（拓扑排序，最高块优先）。匹配只在该块仍持有扫描所见内容时命名副本字节：尚未被流、活动块或未触碰块覆盖。匹配在可能不可读的块前停止，匹配后的字面量按控制台在该处持有的字节编码。

解码器（`asm/rom-lzma.c`，clang 构建的 1768 字节 Thumb）从 ROM 块 `0xFFF` 运行，主机先写入它，启动填充会连同顺序表一并清掉。其状态（含 5.2 KB 概率共 6.9 KB）位于 `gDecompressionBuffer + 0x2000`。它大约每帧解码一千字节（unicorn 下每次调用最多 98,000 条指令），并在消息耗尽前返回 0，因此客户端下一帧会再次调用。完成的块用 `swi 0x48` 写入并回读。主机在工作进程中编码，同时用单块扫描保持链路忙碌。

控制台在仍运行上一条消息时到达的链路块会被丢弃。编码器按流字节记录解码器开销（符号 6 单位、复制字节 1、每帧 1000 单位）；符号只有在解码器持有其 20 字节前瞻（比编码器计数多 25 字节）时才解码，因此其工作落在带来这些字节的消息上。每条数据消息携带它所导致的解码帧数再加 6 帧；下一条消息的头块可在解码期间到达，第二块只能之后到达。几字节的流若对应长段 `0xFF`，解码可能超过一百帧。

| 面向 BPRE 的绿宝石编码 | 字节 |
|---|---|
| 游程与字面量 | 11,667,649 |
| 游程与字面量，外加仍持有的任意 ROM 字节的复制令牌（离线） | 9,073,120 |
| 相对控制台副本的 LZMA，降序（57 段，编码 26 秒） | 3,691,122 |
| 参考顺序下的相同结果（离线） | 3,206,459 |
| 无可用性限制的贪婪 LZMA（离线上界） | 3,027,095 |

### 活动块

会话运行的是它正在覆盖的副本中火红自己的链路与神秘礼物代码。那些块最后写入：新字节先到两份镜像之后的暂存块（BPRE 上为 `0xEB1` 到 `0xFFF`，335 块），启动操作再移动它们。

英文火红（BPRE）的集合是 157 块，见 `pokeldn/frlg/data/rom_live_blocks.json`：模拟会话执行的函数（传输期间 2.16 亿次主机侧 GBA `pc` 采样落入 327 个函数与 53 块）、其直接被调用者，以及其字面量池命名的数据。在把副本其余每个块填成 `0xFF` 后，模拟英文火红会话跑完了写入与检查并打印结束消息。若进一步沿数据指针关闭，几乎覆盖整份 ROM（两层共 3380 块）。其余十一张卡带没有测得的集合，一律拒绝。

### 速率

模拟英文火红经 IP 主机：完整哈希过程需 120 秒（每 32 块应答 0.6 秒）；1 KB 数据消息需 6.3 秒（160 B/s）；2077 块作为填充消息耗时 400 秒。默认节奏下，252 字节链路块大约花费 80 帧：21 个片段发送两次（`block_repeat`）加 36 帧间隙（`inter_block_gap_frames`），链路上则是每帧一个片段。

绿宝石（BPRE）在其 `0xFF` 尾之前为 14,929,764 字节，共 3645 个 4 KB 扇区，且每一个都与同偏移处的火红 Switch 镜像扇区不同，因此不能跳过任何扇区。一条消息携带 1012 令牌字节（1 KiB 链路缓冲区减去 12 字节头）：

| 编码 | 流 | 消息 | 解码器 |
|---|---|---|---|
| 存档传输的游程与字面量 | 11,667,649 字节 | 14,566 | 在 GBA 侧，已测 |
| 无熵编码的复制／字面量格式，相对整份火红镜像与绿宝石自身输出匹配，字节对齐令牌 | 8,470,154 字节 | 8370 | 尚未编写 |
| LZMA2，64 KB 窗口 | 6,169,577 字节 | 6097 | 尚未编写 |
| LZMA2，无界窗口 | 5,747,728 字节 | 5680 | 尚未编写 |
| 以火红镜像为字典的 LZMA2 | 2,561,046 字节 | 2531 | 尚未编写 |

DEFLATE 的 32 KiB 窗口看不到两份 ROM 共约 15 MB 的共享库与引擎代码，因此 `zlib` 下的火红字典几乎无帮助（6,991,630 字节，相对无字典的 6,975,681）：字典收益专属于 ROM 大小的窗口。解码器复杂度不必随窗口增长：复制令牌可以零额外开销命名任意 32 位源地址，因此无界窗口匹配器需要的分派与 memcpy 解码器与现有存档传输相同，只多第三种令牌类型。相对哈希链匹配器（6 个候选、5 字节键）在火红镜像与绿宝石自身输出上的测量，该格式仍落后 LZMA2 约 3.3 MB：LZMA2 超出窗口大小的大部分收益来自把短匹配与字面量装进不足一字节的范围编码器，字节对齐格式做不到。要达到 LZMA2 数字，需要 GBA 侧真正的熵编码器，而不只是更大窗口。`tools/rse/emerald_switch_build.py` 已携带面向该精确目标的可用 agbcc／arm-none-eabi 工具链，因此该解码器更适合从现有小型 LZMA 或 LZMA2 参考 C 解码器改编并交叉编译，而不是从零手写汇编；目前尚不存在。

经板子的零售恢复大约每秒移动 150 令牌字节，外加每扇区约 3.5 秒：19 个扇区对 6182 令牌字节用了 107 秒、对 27,421 用了 249 秒，两点拟合，未经第三次确认。按该速率，流在存档传输编码下约 22 小时，无熵编码格式约 16 小时，LZMA2 约 11 小时，火红字典约 5 小时；3645 个扇区按 3.5 秒再加 3.5 小时，若每个扇区仍保留恢复的一确认一轮往返。恢复现在每确认最多发送 62 条数据消息（[恢复](frlg_gift.md#restore)），ROM 传输使用相同批次。目前测得最长会话持续 269 秒。

启动写入 GBA SoftReset 标志并运行 `swi 0x00`：BIOS 跳到 `0x08000000` 的 ROM 复位向量且 RAM 已清零，因此绿宝石自己的 `AgbMain` 从刚写入的字节初始化。BIOS SoftReset 在核内完成，不是应用启动，因此对 ROM 副本的写入会在它之后保留。rom-reset-probe 载荷（`asm/rom-reset-probe.s`）把 `word[i] = 0x454D4552 + i` 写到 ROM 副本块 0xF00（0x08F00000，位于火红的 `0xFF` 尾），运行 `swi 0x00`，重启后第二次神秘礼物会话转储 0x08F00000：全部 16 个字原样读回（英文火红，模拟控制台，经 IP 主机）。RomFS 重载发生在应用启动而非软复位，因此写入的 ROM 会在启动进入新游戏后继续存在。

### 实时时钟

应用模拟卡带 GPIO 端口与 S-3511 时钟，且仅当启动时加载的 ROM 不是火红或叶绿时才附加它们。附加钩子（`main + 0x056DD8`，Sloop 组件虚表 `main + 0x1C3878` 的槽 `+0x40`）从组件的头副本读取游戏代码的第三个字母：`G` 或 `R` 跳过端口，其他则构建它。

| 内容 | 位置 |
|---|---|
| 头副本：`0xAC` 到组件 `+0x55`，`0xBC` 到 `+0x5D` | `main + 0x05593C` 到 `main + 0x055950` |
| 第三个字母测试，`0x47` 与 `0x52` | `main + 0x056DF4` |
| 端口区域仅安装在区域 `0x08` 上，ROM 指针、大小与掩码从普通对象复制 | `main + 0x056E20` 到 `main + 0x056E64` |
| 区域虚表 | `main + 0x1C3978` |
| 读 16 位：`0xC8` 使能、`0xC6` 方向、`0xC4` 数据，仅在使能为 1 时提供 | `main + 0x05610C` |
| 写 16 位：同样三个偏移 | `main + 0x05620C` |
| 时钟串行协议：位 0 时钟、位 1 数据、位 2 片选，命令前缀 `0x60` | `main + 0x0351CC` |
| 日期来源：`nn::time` 日历，BCD 写入时钟寄存器 | `main + 0x05EB90`、`main + 0x034CA8` |

BIOS 软复位在客户中运行，因此没有主机代码查看新头。以游戏代码 `BPEE` 构建并在启动时加载的绿宝石会得到端口；流进 `BPRE` 会话则不会。其 GPIO 存储随后是普通卡带存储，读取返回 ROM 字节，因此 `SiiRtcProbe` 会按那些字节成功，而 `RtcCheckInfo` 会标记日期（`month == 0` 为 `RTC_ERR_INVALID_MONTH` [rtc.c:174]），`RTC_ERR_FLAG_MASK` 将其变成电池耗尽消息 [main_menu.c:717]。读取尚未在调试器下观察。仅把头中的游戏代码改成 `BPRE`、并在启动时加载的绿宝石，在模拟控制台上也会显示电池耗尽消息，且不涉及流。

日期只到达时钟设备：`main + 0x05EB90` 有五个调用者，四个在设备内部，一个在其设置（`main + 0x054A9C`）。`0x40` 到 `0x62` 之间没有系统调用调用它，因此流式 ROM 无法读取控制台时间。

构建为该情况保留软件时钟（`src/rtc.c`，在 `REVISION >= 0xA` 下）。`RtcInit` 在使能后读取 `0x080000C8`：端口读回 1，普通 ROM 读回自身的 0。没有端口时，原始日期是 2001 年 1 月 1 日加上存档的游戏时间，因此它活在存档里、无需新字段，并随旧存档回去。一个游戏日是 24 小时游戏时间。时钟停在游戏时间停止处：999:59:59，即 2001 年 2 月 11 日。附加端口时，构建仍像以前一样读取应用的时钟。

| 模拟控制台上启动时加载的绿宝石 | 主菜单 |
|---|---|
| 游戏代码 `BPEE`，无软件时钟 | 无消息 |
| 游戏代码 `BPRE`，无软件时钟 | 电池耗尽消息 |
| 游戏代码 `BPRE`，有软件时钟 | 无消息 |

在 unicorn 下，从构建 ROM 调用 `RtcGetRawInfo` 在七个游戏时间返回了预期日期，且每次 `RtcCheckInfo` 返回 0。此构建的流尚未运行。

## 未解决

- 绿宝石继续火红存档时会做什么。
- 绿宝石存档两次后，火红在重新启动时显示什么：按 [save.c] 两份副本都通不过校验和，且没有神秘礼物条目时主机无法到达控制台。
- 零售绿宝石构建的神秘礼物 → 神秘卡片 → 朋友界面会在 LinkPlayer 块之前变成黑屏（[回到火红](#returning-to-firered)）；FinishSave 恢复尚未在零售机上运行。
- 错误路径的活动块。模拟流进行到 2816 块发生链路错误后，在错误屏幕按 A 得到黑屏：回到标题的路径运行在被覆盖的块上，因此中断的流要从重新启动恢复。
- 其余十一张卡带的活动块。
- 面向日文卡带的构建。

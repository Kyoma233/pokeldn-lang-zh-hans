---
title: Mystery Gift
parent: FireRed and LeafGreen
nav_order: 2
---

# 神秘礼物

火红／叶绿的神秘礼物（好友模式）可接收神秘卡片、投递脚本、神秘新闻、来访的对战塔训练家，以及直接进入队伍的宝可梦，无需宝可梦中心。神秘事件 VM 与原生 ARM 代码位于 [主机上的代码](frlg_rom.md)。

## 会话流程

主机端客户端以 `{CLI_RECV, MG_LINKID_CLIENT_SCRIPT}, {CLI_COPY_RECV}` 启动 [mystery_gift_scripts.c:15]，并执行接收到的任意 `MysteryGiftClientCmd` 数组 [mystery_gift_client.c:87]。

    主机加入  ->  SEND_PLAYER_IDS  ->  LinkPlayer 区块交换  ->  一个待机屏障
      服务端 -> CLIENT_SCRIPT (sClientScript_SendGameData, 32 B)
      客户端 -> GAME_DATA     (MysteryGiftLinkGameData, 96 B)   -- 校验通过，比对卡片标志
      服务端 -> CLIENT_SCRIPT (sClientScript_SaveCard, 48 B)
      服务端 -> CARD          (struct WonderCard, 332 B)
      服务端 -> RAM_SCRIPT    (1024 B：投递字节码，零填充)
      客户端 -> READY_END     (1024 B)
    关闭链路握手  ->  断开连接

### 帧规则

- 大小为 0 表示 1024 [mystery_gift_link.c:55]；`SVR_COPY_SAVED_RAM_SCRIPT` 从不设置 `ramScriptSize` [mystery_gift_server.c:275]，因此 RAM 脚本与 READY_END 均为完整的 1024 字节消息。CRC 覆盖填充后的缓冲区。
- 区块传输无确认：除非接收端槽位为 `RECV_STATE_READY`，否则 `SEND_BLOCK_INIT` 被忽略 [link_rfu_2.c:1146]。`MysteryGiftTiming.inter_block_gap_frames` 为 36；区块丢失会导致主机永久等待。客户端跨多帧处理的载荷会占用槽位那么久：服务端发送此类消息时带上 `after`，即主机发完最后一个区块后仍保持忙碌的帧数。下一条消息的头部区块可能落在该时段内；宿主会扣住第二个区块，直到主机空闲。
- 主机发送时的停顿遵循 [镜像规则](frlg_link.md#row-one-of-the-parents-table-is-the-consoles-own-command-mirrored-back)。

### 模块

除另有说明外，均位于 `pokeldn/frlg/gift/`：

| 文件 | 职责 |
|---|---|
| `mg_link.py` | 成帧：6 字节 `{ident, crc, size}` 头部区块 + ≤252 字节分片 |
| `mg_script.py` | 客户端脚本汇编器、反编译项目的内置脚本、`MysteryGiftLinkGameData` 读取器 |
| `mg_server.py` | 服务端脚本解释器 (`SVR_*`) |
| `host_mystery_gift.py` | 主机引擎：`tick()` → 父级 `gSendCmd`，`feed_child_slot()` ← 子级行 |
| `host_mg_app.py` | 基于主机运行时的应用钩子 |
| `wonder_card.py` | 逐字节精确的时拉比与三圣兽卡片／RAM 脚本构建器 |
| `stamp_rally.py` | 集印卡、印章、激活封装、投递脚本 |
| `gift_composer.py` | 动作定义、光标状态校验、RAM 脚本编译器 |
| `gift_registry.py` | 目录 |
| `gift_to_bin.py` | 面向外部第三世代神秘礼物工具的 `.bin` 导出器 |
| `pokeldn/frlg/save/save_inject.py` | 带卡片、RAM 脚本与扇区校验和的存档礼物写入 |
| `bin/frlg_mg_host.py` | CLI 入口 |

## 运行方法

    (对方) 神秘礼物 -> 神秘卡片 (接收) -> 好友 (Ami)，停留在搜索画面
    (你)  POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --phy auto \
               --keys PROD_KEYS --gift beast-cutscene --flag-id 1005
    (对方) 主机出现时加入；若出现替换卡片提示则选 YES

无线电设置：[ESP32 无线电](hardware_esp32.md)。每次运行一台主机；主机离开 LDN 即停止 ([主机实现](frlg_host.md))。`tests/test_mystery_gift_flow.py` 与 `tests/test_mystery_gift_end_to_end.py` 建模了主机的接收路径。

`--save-to-board` 将礼物存入 ESP32 开发板并退出；板子由任意 USB 充电器供电，随后为每台加入的主机单独重放该会话，使用各卡带自带的字节 ([主机镜像](hardware_esp32.md#a-host-image))。

    (你)  POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live \
               --keys PROD_KEYS --gift celebi --save-to-board

## 链路可携带的内容

22 条客户端指令 [include/mystery_gift_client.h:18] 中有三条会执行实体操作：

| 指令 | 主机行为 |
|---|---|
| `CLI_SAVE_RAM_SCRIPT` (17) | 存储一个字段脚本；下次 NPC 交互时运行 |
| `CLI_RUN_MEVENT_SCRIPT` (15) | 运行神秘事件字节码脚本 (17 操作码 VM) |
| `CLI_RUN_BUFFER_SCRIPT` (21) | `func = (void *)gDecompressionBuffer; func(&param, gSaveBlock2Ptr, gSaveBlock1Ptr)`；最多 1024 字节 ARM 代码 |

## 仅有的一个 RAM 脚本槽位

主机只能持有神秘卡片或绑定的 RAM 脚本，二者不可兼得。`ValidateSavedWonderCard` 最终调用 `ValidateRamScript` [mystery_gift.c:186]，要求具备 `RAM_SCRIPT_MAGIC`、地图为 `MAP_UNDEFINED` 且 `objectId == 0xFF` [script.c:538]；字段脚本仅在与该对象交谈的坐标处运行 [field_control_avatar.c:458]。`CLI_SAVE_RAM_SCRIPT` 写入 MAP_UNDEFINED/0xFF [script.c:578]；神秘事件 VM 的 `initramscript` 写入真实坐标。绑定脚本时卡片仍留在存档，但菜单隐藏它，且 GameData 上报 `flagId` 为 0 [mystery_gift.c:349]。

下一张神秘卡片会重新绑定槽位，卡片随之重现；缓冲脚本则不改动槽位。卡片重写 SaveBlock1 +0x32E0 (卡片) 与 +0x361C (RAM 脚本)，共一个扇区，不涉及 SaveBlock2。

存档本身也可携带同一对数据：`pokeldn/frlg/save/save_inject.py` 将有效卡片与 RamScript 写入原始存档 (`inject_gift`、`build_ram_script_struct`)，因此通过神秘卡片导入的存档无需实时主机即可在其 NPC 处运行脚本。脚本的 `callnative` 操作码可调用客体 ARM，`resident-save` 礼物即利用此机制绑定妈妈的加载器。

`ramScript.checksum` 为 1000 字节上的 `CalcCRC16WithTable`，即 999 字节声明数据加一字节零填充 [script.c:500] (`CalculateRamScriptChecksum` `0x0806D43C` BPRE, `0x0806D5A0` BPRF)。CRC 覆盖 999 字节的槽位，在首次与其对象交谈时会被清空 [script.c:526]。

## 礼物目录

`--gift NAME`；`--help` 列出标志 ID（1000..1019）。只有持有的卡片才重要：相同的 ID 意味着「已持有此卡片」（`MysteryGift_CompareCardFlags`）。已持有该卡片的主机会直接接收神秘事件礼物，不再弹出提示。

| 礼物 | 作用 |
|---|---|
| `beast-cutscene-share` | 可重复的传说三兽过场动画；默认演示卡片 |
| `celebi` | 合成的 50 级时拉比卡片 |
| `porygon-tm-gift` | 一张多边兽卡片、一段皮皮动画、TM29 念力然后 TM46 偷窃 |
| `solrock-stamp` / `lunatone-stamp` | 同一枚印章拉力卡片的两半 |
| `altering-cave` | 官方更改洞穴活动，移植版 |
| `wish-egg`, `pokepark-egg`, `pc-japan-egg` | 官方分发蛋 |
| `event-pokemon` | 一只第三世代分发宝可梦，直接进入队伍 |
| `starter-egg` | 九只初始伙伴之一的蛋，由 `random` 抽取 |
| `rare-berries` | 一颗谜之果、一颗岚沙果、一颗星星果，各一枚 |
| `national-dex` | `EnableNationalPokedex`（特殊 367），除非 `FLAG_SYS_NATIONAL_DEX`（`0x840`）已置位 |
| `rare-candy` | 五颗升级糖果 |
| `box-swablu`, `box-zigzagoon`, `box-skitty`, `surf-pichu` | 宝可梦 Box 红宝石＆蓝宝石赠送蛋 |
| `nature-mint`, `pc-anywhere` 及另外 42 张 | GB-Link Team 卡片 |
| `battle-count-card` | 官方对战计数卡片 |
| `visiting-trainer` | 一位对战塔训练家，识别码 26（仅火红） |
| `mystery-event-probe` | `givenationaldex; setstatus 42; checksum`，虚拟机自检 |
| `mystery-event-celebi` | `givepokemon`：一只 30 级时拉比携带邮件，直接进入队伍 |
| `mystery-event-npc` | `initramscript`：将一个场地脚本绑定到真新镇的胖大叔 |
| `rng-seed-reader`, `rng-rate-probe`, `rng-shiny-hunt`, `rng-mon-hunt`, `rng-mon-hunt-both`, `rng-mon-hunt-log` | 见 [RNG](frlg_rng.md) |

### 传说三兽

送货员赠送岚沙果、躁躁果和一颗大师球，随后发起一场可重复的 65 级战斗：妙蛙种子存档对应水君，杰尼龟存档对应炎帝，小火龙存档对应雷公。

### 多边兽 TM 礼物

一张多边兽图标卡片和玩家右侧三格处的皮皮精灵，在两个独立检查点分别给予 TM29 然后 TM46。默认标志 ID 1007；查看器显示 `flag_id % 100`。

### 印章拉力

两个活动共享一张 `SUN AND MOON RALLY` 卡片（奈克洛兹玛图标、两个印章槽、标志 ID 1006），顺序不限。每个印章给予一只 30 级太阳岩或月亮岩；集齐两者给予一只 50 级时拉比。

| 状态 | 含义 |
|---|---|
| `VAR_MYSTERY_GIFT_1` | 时拉比完成光标 |
| `VAR_MYSTERY_GIFT_2 = 0/1/2` | 太阳岩缺失／进行中／已领取 |
| `VAR_MYSTERY_GIFT_3 = 0/1/2` | 月亮岩缺失／进行中／已领取 |
| `FLAG_MYSTERY_GIFT_DONE` | 拉力完成 |

```text
matching = 存档标志 ID == 分发标志 ID 且 最大印章数 == 2 且 图标物种 == CLAYDOL
if no card:                安装共享卡片 + 送货脚本 + 选定印章，运行激活
else if not matching:      提供丢弃提示；接受后，按上述安装
else if 印章物种或 ID 已存在:   HAS_STAMP
else if 两个槽位均非空:           NO_ROOM_STAMPS
else:                      保存印章，运行激活，STAMP_RECEIVED
```

激活是一个神秘事件包装器。`IsStampInMetadata` [mystery_gift.c:272] 拒绝冲突印章；`CLI_SAVE_STAMP` 仅写入 `cardMetadata.stampData` [mystery_gift.c:307]。

### 更改洞穴

官方脚本 [data/mystery_event_msg.s:325] 将 `VAR_ALTERING_CAVE_WILD_SET`（0x4024，SaveBlock1 + 0x1048）加 1，在 10 处回绕；值 9 及以上读取表 0 [wild_encounter.c:192]。

| 变量 | 物种 | | 变量 | 物种 |
|---|---|---|---|---|
| 0 | 超音蝠 | | 5 | 长尾怪手 |
| 1 | 咩利羊 | | 6 | 坚果哑铃 |
| 2 | 铁甲蛹 | | 7 | 惊角鹿 |
| 3 | 黑暗鸦 | | 8 | 图图犬 |
| 4 | 熊宝宝 | | | |

### 分发蛋

三个日本分发，来自 GB-Link-Switch-LDN 的 `web/js/gift/official.js`。卡片用 `random` [scrcmd.c:455] 抽取一枚蛋；该蛋获得分发的招命中之缘标记和遇见地点 0xFF。队伍满员会在抽取前拒绝。

| 卡片 | 蛋 |
|---|---|
| `wish-egg`（纽约宝可梦中心） | 幸运蛋、睡睡蛋、蛋蛋、大葱鸭、袋兽、舌舔；均知晓许愿 |
| `pokepark-egg`（宝可梦公园市场幻想） | 沙奈朵、龙虾小兵、太阳珊瑚、波波、帕奇利兹、皮丘、帕奇利兹、可达鸭、尾立、旋转球、跳跳猪、蓝蓝路、尾立、吼吼鲸、 Wynaut |
| `pc-japan-egg`（日本宝可梦中心） | 喇叭芽（摇摆舞）、喵喵（花瓣舞）、走路草（吸取种子）、蚊香蝌蚪（甜甜之吻） |

### 所有 GBA 版本共享的卡片

`wonder_card_events.gba_cards(rules)` 构建火红、叶绿和绿宝石共同提供的卡片：`master-ball`、`rare-candy`、三个分发蛋、`starter-egg`、`rare-berries`、`national-dex`、`battle-count-card` 和四个宝可梦 Box 蛋。对战计数和全国图鉴卡片从 `rules`（`GameRules`）获取特殊指令和标志编号；其余卡片在任一版本的编号下均可编译。`pokeldn.frlg.gift.builder.GBA_CARDS` 和 `EVENT_PRESETS` 是应用程序的预设，[绿宝石的礼物](rse_gift.md)也列出了它们。

| 宝可梦 Box 蛋 | 招式 [PKHeX EncountersWC3] |
|---|---|
| 蓝天飞龙 | 啄击、咆哮、气合斩 |
| 之字斑马 | 撞击、咆哮、摇尾巴、极速移动 |
| 向尾喵 | 咆哮、撞击、摇尾巴、金钱攻击 |
| 皮丘 | 电击、魅惑、冲浪 |

每枚蛋均为命中之缘，遇见地点 `0xFF`，由 `GiveEgg` 写入。

### 活动宝可梦

`--gift event-pokemon --event-pokemon NAME` 发送一只由 PKHeX.Core 制作、合法性检查通过的第三世代分发宝可梦，在卡片保存时通过神秘事件 `givepokemon` 送达。队伍满员返回状态 3，卡片可再次接收。默认为 WISHMKR 基拉祈。

`NAME` 为 `EncounterGift3` 中的训练家名和物种（非蛋、非日本、按其 PID/IV 方法）：`WISHMKR Jirachi`、`CHANNEL Jirachi`、`RUBY Zigzagoon`、`SAPHIRE Zigzagoon`、`Aura Mew`、`MYSTRY Mew`、`DOEL Deoxys`、`SPACE C Deoxys`、`ROCKS Metang`、所有 `10 ANIV` 物种，以及欧版 `10ANNIV`、`10JAHRE`、`10ANNI` 和 `10ANIV` 发布；`--language` 选择语言。可转移到 GBA 的 GameCube 礼物来自 PKHeX 的斗技场和 XD 表，按物种查找：`MATTLE Ho-Oh`、`DUKING Plusle`、`Colosseum Pikachu`、`AGETO Celebi`（均为日版）、`XD Eevee`、`XD Chikorita`、`XD Cyndaquil`、`XD Totodile` 和 `XD Lugia`。

两个 PKHeX 生成陷阱，在 `services/pkhex` 中处理：

- `SAPHIRE Zigzagoon`（`BACD_RBCD`）从 `RUBY` 的固定种子 `0x00D5` 生成，失败 `PIDTypeMismatch`；辅助程序扫描 256 个八位种子，其中 103 个有效。
- 随机训练家 ID 和隐藏 ID 约 37% 概率导致 XD 礼物失败（「无法从任何 RNG 种子获得」）；辅助程序从两个连续的 `XDRNG` 步骤抽取，模拟 XD 建立存档。

卡片与构建无关；`tests/test_frlg_english_cartridges.py` 在每个卡带的 `RunMysteryEventScript` 中运行它。

### GB-Link Team 卡片

GB-Link Team 的自制卡片（GB-Link-Switch-LDN `cards/`，GPL-3.0）是一张神秘卡片加一个 RAM 脚本，通过 `callnative` 调用 THUMB 代码。源码在 `vendor/gblink-cards/`；`scripts/gen_team_cards.py` 构建 `pokeldn/frlg/data/team_cards.json`，逐字节复现其所有 44 个 `BPRE 1.10` 载荷，`team_cards.py` 注册每个 ID（不带 `custom-` 前缀）。`starter-egg`、`rare-berries`（道具 173-175）和 `national-dex`（`FLAG_SYS_NATIONAL_DEX` 0x840）由合成器重建。

| 分组 | 卡片 |
|---|---|
| 修改宝可梦 | `nature-mint`、`ability-capsule`、`poke-ball-changer`、`pokemon-gender`、`nickname`、`stat-judge`、`hidden-power`、`hidden-power-type`、`ev-training`、`friendship`、`pp-max`、`max-conditions`、`pokerus`、`unown-letters`、`trade-evolution`、`espeon-umbreon`、`move-tutor` |
| 每帧钩子 | `speed-2`、`speed-3`、`speed-4`、`speed-0-75`、`speed-0-5`、`fast-text`、`travel-anywhere`、`pc-anywhere`、`hm-moves`、`reusable-tms`、`physical-special-split`、`exp-share`、`shiny-hunting`、`roamer` |
| 其他 | `no-encounters`、`legendary-respawn`、`instant-eggs`、`gift-box`、`pocket-casino`、`gift-ribbons`、`trainer-ids`、`gender-swap`、`rival-name` |
| 活动宝可梦 | `box-eggs`、`colosseum-pikachu`、`ageto-celebi`、`mattle-ho-oh`（仅命令行；应用列出共享宝可梦 Box 蛋和 PKHeX 的活动副本） |

与其构建的差异：

- 所有十二个版本 `0x0A` 卡带：`vendor/gblink-cards/symbols.json` 保存每个 ROM 的 167 个地址，`tests/test_team_cards.py` 校验，每个脚本检查头部的游戏、语言和版本（[卡带映射](frlg_rom_map.md#the-international-revision-0x0a-cartridges)）。
- 重定位脚本（996 字节）和菜单列表（80 字节）位于 `0x0203F768` 和 `0x0203FB50`，低于 `0x0203FC00` 的常驻钩子（[载荷可驻留位置](frlg_rom.md#where-a-payload-can-live)）。
- 钩子安装器链接到 `VBlankIntr`，存储于 `0x0203FBFC`，因此钩子卡片和游戏加速互相替换。其状态在 `0x0203FF60`。
- 1019 以上的 ID 没有 `sReceivedGiftFlags` 位；注册表发送 1000 + id mod 20。
- `hm-moves` 和 `physical-special-split` 文本缩短以适应 995 字节。

每张卡片在 mGBA 上绑定妈妈，在所有十二个卡带上运行。在另一版本卡带上，载荷回应「This gift doesn't work with this version of the game.」（日版显示「Wrong game.」）。`colosseum-pikachu` 和 `ageto-celebi` 携带日文训练家名，在欧版卡带上显示为点。

### 对战计数卡片

`MysteryEventScript_BattleCard` [data/mystery_event_msg.s:162] 在恰好三次 `GET_CARD_BATTLES_WON`（特殊 390）时给予一瓶伤药；移植版以自己的变量为门控，因此可重复。计数器仅在 96 字节训练家卡片后的 u16 等于持有卡片的标志 ID 时递增 [union_room.c:1777]（`frlg_trade_host.py --card-flag-id N`）。

| 递增内容 | 位置 | 规则 |
|---|---|---|
| `numTrades` | 完成一次交换 [trade_scene.c:2609] | 卡片未计数过的训练家 ID |
| `battlesWon` / `battlesLost` | 通信对战 [cable_club.c:792] | 同上，每项统计 5 个 ID |

联盟房间对战不计数；仅 [斗技场](frlg_link.md#the-cable-club-colosseum) 计数。计数器位于 SaveBlock1 + 0x3434，无 CRC [mystery_gift.c:490]：

    0x3434: 0000 0000 0100 2300     交换 1，图标 35 (CARD_TYPE_LINK_STAT)

`CARD_TYPE_GIFT` 卡片即使运行特殊指令也保持为零。

### 来访训练家

`CLI_RECV_EREADER_TRAINER`（18，识别码 26）将缓冲区复制到 `gSaveBlock2Ptr->battleTower.ereaderTrainer` [mystery_gift_client.c:233]。结构体 188 字节 [global.h:286]：

    0x00 u8  unk0                  0x10 u16 greeting[6]            0x34 BattleTowerPokemon party[3]
    0x01 u8  trainerClass          0x1C u16 farewellPlayerLost[6]  0xB8 u32 checksum
    0x02 u16 winStreak             0x28 u16 farewellPlayerWon[6]
    0x04 u8  name[8]
    0x0C u8  trainerId[4]

前 46 字不全为零且 u32 为其和时有效 [battle_tower.c:1354, :1384]。`SevenIsland_House_Room1` 的老奶奶随后提供可重复的 3v3，由 `CreateBattleTowerMon` [battle_tower.c:928] 生成；无等级限制或禁用名单。火红叶绿显示五字节名字 [battle_tower.c:1343]。`--gift visiting-trainer` 同时发送卡片、RAM 脚本和训练家；持有相同卡片时仅发送训练家。

## 神秘新闻

`struct WonderNews` [global.h:646] 大小为 444 字节：

| 偏移 | 大小 | 字段 | 备注 |
|---|---|---|---|
| 0x000 | 2 | `id` | 不得为 0，唯一检查 [mystery_gift.c:113] |
| 0x002 | 1 | `sendType` | `SEND_TYPE_DISALLOWED` 隐藏“发送” [mystery_gift.c:120] |
| 0x003 | 1 | `bgType` | `>= NUM_WONDER_BGS` 读为 0 [mystery_gift_show_news.c:110] |
| 0x004 | 40 | `titleText` | 在 224 像素窗口中居中 |
| 0x02C | 400 | `bodyText[10][40]` | 屏幕显示八行；超过索引 7 的行会开启滚动指示器 [:346] |

`IsWonderNewsSameAsSaved` 比较全部 444 字节 [mystery_gift.c:140]（`--news-id N` 让新闻变为新）。新闻与卡片互不置换。

- `build_wonder_news_app_data` 宣告活动 22 [src/data/union_room.h:406]。
- 主机回复 `MG_LINKID_RESPONSE`（ident 19）：`FALSE` 已保存，`TRUE` 已持有 [mystery_gift_client.c:210; mystery_gift_scripts.c:126]。
- 来自好友的新闻会在 `ITEM_RAZZ_BERRY` 到 `ITEM_NOMEL_BERRY` 之间随机一种树果，由 `CeruleanCity_House4` 的男子赠送，最多五颗，之后需 500 步 [mystery_gift_menu.c:1367, wonder_news.c:21]。四颗树果的奖励需要关闭无线通信路径。

`--news` (`--news berry`, `--news-id N`)。消息顺序（约 18 秒）：

    ident 16  sClientScript_SendGameData
    ident 17  MysteryGiftLinkGameData
    ident 16  sClientScript_SaveNews
    ident 23  MG_LINKID_NEWS - 444 字节分三块
    ident 19  MG_LINKID_RESPONSE - FALSE：主机已保存
    ident 16  sClientScript_NewsReceived
    ident 20  READY_END                              -> SVR_MSG_NEWS_SENT

## 问卷作为密码关卡

`SVR_CHECK_QUESTIONNAIRE` 对比四个宝可梦商店问卷词汇 [mystery_gift.c:422]；`mg_server.gate_on_questionnaire(script)` 在游戏数据前缀后插入它：

    bin/frlg_mg_host.py --gift ... --questionnaire species:55,FEELINGS/60,move:177,why

一个词可以是英文名、`species:N`、`move:N`、`GROUP/INDEX` 或原始 id。错误的短语会收到主机的 64 字节消息（`CLIENT_SCRIPT_DYNAMIC_ERROR`），且不发送任何内容。每个会话都会记录主机从 GameData 看到的主机四个词 [mystery_gift.c:361]：

    questionnaire: POKEMON/55  done [FEELINGS/60]  MOVE_1/177  why [MISC/37]

`EC_GROUP_POKEMON` 按物种索引，`EC_GROUP_MOVE_1` 按招式 id 索引；参见[法语简易聊天词汇表](frlg_rom_map.md#the-french-easy-chat-vocabulary)。

## 主机主动上报的自身信息

GameData 携带简易聊天档案与卡片统计 [mystery_gift.c:361]。`--game-data-log PATH`（`game_data_log.py`）将每个会话追加到 JSONL 账本，并打印自该主机上次以来的变化；`tools/frlg/game_data_read.py PATH` 读取它。计数器仅作为同一卡片标志 id 上的差值作为证据。

## 存档备份与恢复

神秘卡片、好友会话会将主机的整个 128 KiB 存档芯片复制到主机，或将 `.sav` 写入芯片并让游戏加载并保存它；不发送卡片。`asm/save-backup.s` 和 `asm/save-restore.s` 移植自 GB-Link Team 的 `cards/savebackup.s` 和 `cards/saverestore.s` (GPL-3.0)；主机端为 `pokeldn.frlg.gift.save_transfer`（`--save-backup FILE`、`--save-restore FILE`），应用端为 Your save 标签页（[Your saves](gui.md#your-saves)）。两者均在所有十二个卡带上运行（[存档备份与恢复](frlg_rom_map.md#save-backup-and-restore)）。

### 令牌编码

字节 `n < 0x80` 后跟 `n + 1` 个原文字节；`n >= 0x80` 后跟一个字节，重复 `n - 0x80 + 3` 次（连续 3 到 130，原文最多 128）。

### 备份

客户端脚本重复 `CLI_LOAD_TOSS_RESPONSE, CLI_RUN_BUFFER_SCRIPT, CLI_SEND_LOADED`，每个脚本最多 32 次。每轮发送最多 1 KiB 令牌，对应至多 8 KiB 芯片数据，绝不跨越 64 KiB bank 边界；芯片偏移为 `client->param = 0x5A << 24 | offset` [mystery_gift_client.c:276]，不带 `0x5A` 的 `param` 从 `first` 开始。

| 载荷字 | 偏移 | 值 |
|---|---|---|
| `first` | `0x004` | 第一轮开始的芯片偏移 |
| `send_queue` | `0x008` | `&gRfu.sendQueue.count` |

一轮在一帧内将 `0x800` 字节暂存到 `gDecompressionBuffer + 0x800`，压缩到 `+ 0x400`，并设置 `link.sendBuffer`（`param + 0x3C`）和 `link.sendSize`（`param + 0x34`）。等待 `gRfu.sendQueue.count` 变零。会话在 `CLI_MSG_BUFFER_FAILURE` 附带消息结束，因此主机不保存 [mystery_gift_menu.c:1379]。中断的备份可按游戏代码与训练家 id 恢复。

### 恢复

1. 第一条消息为 636 字节镜像；`install` 将其复制到 `gDecompressionBuffer + 0x400`，并回复 28 个扇区的 12 字节尾部（id、校验和、签名、位于 `+0xFF4` 的计数器），随后是游戏的 `gSaveCounter`。
2. 主机按 `GetSaveValidStatus` 的方式找到最新的完整扇区，将文件副本写入另一扇区，计数器为 `newest + 1`，再按文件内容写入扇区 28 到 31。
3. 先擦除目标扇区的 id-0 扇区，最后写入新的 id 0，这样芯片自身的副本会一直加载，直到新副面完整。
4. 后续消息以 `b RESIDENT + 4`（`0xEA0000FF`）开头，随后是操作码。`OP_DATA` (1) 携带扇区、写入标志、u16 偏移、u16 令牌长度与令牌，写入 4 KiB 缓冲区；扇区的最后一条消息用 `swi 0x48` 写入并校验，不匹配则置失败掩码位。一个客户端脚本最多承载 62 条数据消息、若干扇区，主机在脚本结束时一次性上报累积失败掩码。新的 id 0 单独开启一批，因此仅在其扇区其余部分读回完整后才发送。
5. `OP_FINISH` (2) 若无失败则调用 `LoadGameSave(SAVE_NORMAL)` [save.c:803]。`SAVE_STATUS_OK` 时会话以 `CLI_MSG_BUFFER_SUCCESS` 结束，主机保存加载后的游戏；否则以 `CLI_MSG_BUFFER_FAILURE` 结束，旧存档保留。

| 载荷字 | 偏移 | 值 |
|---|---|---|
| `b install` | `0x000` | 第一条消息的入口 |
| `b entry` | `0x004` | 后续每条消息的入口，位于 `gDecompressionBuffer + 0x404` |
| `load_game_save` | `0x008` | `LoadGameSave \| 1` |

主机拒绝加载副本不完整或布局不同的存档：日版 SaveBlock1 短 40 字节，从训练家自有宝可梦的语言字节（`+0x12`）读取。

`tests/test_save_transfer.py` 覆盖备份、续传、恢复与中断恢复，对脚本化主机验证。实机上，备份在法版与英版火红可用，恢复在英版火红可用（含法版存档）。主机下一次保存与文件在扇区 1 到 7 不同，这些扇区承载 `LoadGameSave` 重新生成的加密密钥。

## 编写礼物

`pokeldn.frlg.gift.gift_composer` 从 `WonderGift` 定义构建卡片与投递脚本：

```python
MEWTWO_GIFT = WonderGift(
    slug="mewtwo-encounter",
    card=WonderCardSpec(icon_species=150, title="MYSTERIOUS ENCOUNTER",
                        body=("Visit the deliveryman.",), default_flag_id=1008),
    intro_message="A powerful presence is waiting!",
    event=GiftSpec(shareable="once"),          # 或 StampRallySpec(...)
    delivery=DeliveryPlan(delivery=(
        DeliveryStage(Message("Take this."), GiveItem(1)),  # Master Ball
        DeliveryStage(ShowSprite(0, RelativeToPlayer(dx=1)), BattleLegendary(150, level=70)),
    )),
    completed_message="That mysterious encounter is over.",
)
```

`WonderGift.delivery` 使用 `delivery`；`StampSlot.delivery` 与 `StampRallySpec.completion` 使用 `pre_stages` 与 `post_stages`。编译器从 `VAR_MYSTERY_GIFT_1` 恢复阶段，成功时设置 `FLAG_MYSTERY_GIFT_DONE` 与领取标志；`GiftSpec(repeatable=True)` 重置游标。

### 阶段与条件

每个 `DeliveryStage` 是一个检查点；切勿在同一阶段放两个可能失败的奖励（`GiveItem`、`GivePokemon`、`GiveEgg`）。携带招式的 `GiveEgg` 需要队伍空位。`GiveRandomEgg(eggs)` 通过跳转表随机选取一个（十五个四招式蛋放入 944 字节）。`condition=`（`VarEquals`、`FlagSet`、`Not`、`AllOf`、`AnyOf`）跳过阶段但推进游标；`RequireSpecialResult(...)` 失败即停止，不推进游标。

```python
DeliveryStage(ShowSprite(142, RelativeToPlayer(dx=1)),
              condition=VarEquals(0x4031, 0))  # VAR_STARTER_MON == 妙蛙种子
DeliveryStage(RequireSpecialResult(SPECIAL_HAS_ALL_KANTO_MONS, 1, "Finish the KANTO POKEDEX first."),
              GivePokemon(251, level=50))
```

`SetVar`（`setvar` 0x16）与 `AddVar`（`addvar` 0x17）接受存档变量 0x4000..0x40FF 与特殊变量 0x8000..0x8011。

### 对战

`BattleLegendary` 发出 `setwildbattle`、`special StartLegendaryBattle`、`end`，无 `waitstate`（[RAM 脚本可能无法从对战返回](frlg_rng.md#a-ram-script-may-not-come-back-from-a-battle)）；`BattlePokemon` 发出 `dowildbattle`。两者均结束其阶段。印章槽路径中拒绝对战，除非作为条件终止的替代分支。

### 分享

`GiftSpec.shareable` 设置卡片的 `sendType`："never"、"once"（接收者的副本变为不可分享）或 "always"。

### 宿命相遇标记

`GivePokemon(..., fateful_encounter=True)`（及 `GiveEgg`）发出 `setmonmodernfatefulencounter`（`0xCD`）与 `setmonmetlocation`（`0xD2`，0xFF）[data/mystery_event_msg.s:71]。首条指令不检查索引越界 [scrcmd.c:2239]；索引为赠送前的队伍人数，队伍满时跳转到失败标签。摘要行仅来自遇见地点 [pokemon_summary_screen.c:2665, 2799]；`modernFatefulEncounter` 为 Misc+0x08 的第 31 位 [include/pokemon.h:40-82]。

### `initramscript` 在编译器中

`gift_composer.build_bound_script(actions)` 与 `build_mevent_npc_script(actions=...)` 将动作编译为 `initramscript` 绑定的野外脚本。它没有阶段游标且整体重跑，因此一次性效果需要自带 `SetVar` 或条件。

### 注册与验证

```python
from pokeldn.frlg.gift.gift_registry import GIFT_REGISTRY
GIFT_REGISTRY.register_definition(MEWTWO_GIFT)
```

注册会验证并编译：卡片文本与标志、计划结构、动作范围、游标边界、唯一印章、对战位置、指针与 995 字节 RAM 脚本限制，错误会给出路径（`example-rally.event.slots[1].delivery.post_stages[0].actions[1]: ...`）。

## 静态工具

```bash
./.venv/bin/python -m pokeldn.frlg.gift.gift_to_bin --gift beast-cutscene --flag-id 1005 --out-dir exported-gift
./.venv/bin/python -m pokeldn.frlg.save.save_inject game.sav --gift beast-cutscene --flag-id 1005
```

`gift_to_bin` 输出 336 字节神秘卡片与 1004 字节 RAM 脚本，供 `pokemon-gen3-mysterygift-tool` 使用。`save_inject` 将两者写入活动扇区，修正卡片、RAM 脚本与扇区校验和，并保存为 `<save>.gift.sav`（`--in-place` 覆盖；`--make-artifact` 在 `artifacts/` 下生成 `.ram.lst` 清单）。

## 封闭路径

### 无线通信

无线路径在 RFU 序列号关卡处被拦截：

| | 好友 | 无线通信 |
|---|---|---|
| 监听器 | `Task_ListenForCompatiblePartners` [union_room.c:3757] | `Task_ListenForWonderDistributor` [union_room.c:3799] |
| 接受的 RFU 序列号 | `{0x0002, 0x7F7D}` | `== 0x7F7D` only [link_rfu_3.c:920] |
| 选择方式 | 玩家从列表中选择 | 自动连接 |
| 可从 Switch 到达 | 是 | 否 |

`Task_CardOrNewsOverWireless` [union_room.c:2415] 仅在候选 0 的 `serialNo` 为 `0x7F7D` 时保留它，随后检查生成状态、`hasCard` 位（失败时 SE_BOO）并重新连接。Switch 桥报告 `0x0002`，且广播包无序列号字段；`svc_47` [sloopsvc.c:34] 接收 24 字节且无序列号。原生广播包：

```
50 10 | c1 cc bf bf c8 ff 00 00 | 65 ac | 00 00 00 00 | 84 15 | 00 00 00 00 00 00
TID   | uname                   | parent| 未解释       | search| 未解释
```

`record[16:18]` 处的搜索字为
`activity:7 | bit7 | version:3 | language:3 | hasCard?:1 | startedActivity:1`。

未尝试的广播包变体（场景 ID、应用版本、每个空闲偏移填 `0x7F7D`、activity、`hasCard`、bit 7）均未能从无线路径引出认证。未测试：`local_communication_id`、场景暴力枚举、组合尝试。

### e-Reader 本身

训练家塔 e-Reader 卡组通过 GBA 串口链路使用 `LINKTYPE_EREADER_FRLG`（`ereader_screen.c`），而非无线适配器。

### 极光票与神秘票

Switch 版在首次进入殿堂时 [post_battle_event_funcs.c:52, `REVISION >= 0xA`] 同时授予两张票及其 `FLAG_RECEIVED_*` 标志，因此之后收到票卡片无任何效果。卡片的 `iconSpecies` 若非 `SPECIES_NONE` 会绘制图标；超出 `SPECIES_UNOWN_B - 1` 则绘制问号 [mystery_gift_show_card.c:466, pokemon_icon.c:1102]。旧海图仅限绿宝石 [mystery_gift.c:30]。

## 陷阱

- `charmap.encode` 会丢弃未知字符（含换行）。换行符为 0xFE；`mg_server` 拒绝第三行或宽度超过 31 字符的行 [strings.c:1291]（窗口 28 格 × 4 行，[mystery_gift_menu.c:97,524]）。
- 新载荷会进入 `buffer_script.py` 的 `DUMP_SCRIPTS` 与 `DECODED_SCRIPTS` 以及启动器的 `--dump-file` 行。

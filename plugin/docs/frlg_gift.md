---
title: Mystery Gift
parent: FireRed and LeafGreen
nav_order: 2
---

# 神秘礼物

火红／叶绿版的神秘礼物通过好友接受神秘卡片、递送脚本、神秘新闻、拜访战塔训练师以及宝可梦，直接放入队伍，无需宝可梦中心。神秘事件 VM 和本地 ARM 代码位于[控制台上的代码](frlg_rom.md)。

## 本次会话

控制台的客户端以 `{CLI_RECV, MG_LINKID_CLIENT_SCRIPT}, {CLI_COPY_RECV}` 启动[mystery_gift_scripts.c:15]，并执行收到的任意 `MysteryGiftClientCmd` 数组[mystery_gift_client.c:87]。

    控制台加入  ->  SEND_PLAYER_IDS  ->  LinkPlayer 块交换  ->  一次待机屏障
      服务器 -> CLIENT_SCRIPT (sClientScript_SendGameData, 32 B)
      客户端 -> GAME_DATA     (MysteryGiftLinkGameData, 96 B)   -- 已验证，卡标志比较
      服务器 -> CLIENT_SCRIPT (sClientScript_SaveCard, 48 B)
      服务器 -> CARD          (struct WonderCard, 332 B)
      服务器 -> RAM_SCRIPT    (1024 B: 递送字节码，零填充)
      客户端 -> READY_END     (1024 B)
    关闭链接握手  ->  断开连接

### 帧格式规则

- 大小 0 表示 1024 [mystery_gift_link.c:55]；`SVR_COPY_SAVED_RAM_SCRIPT` 永远不会设置 `ramScriptSize` [mystery_gift_server.c:275]，因此 RAM 脚本和 READY_END 都是完整的 1024 字节消息。CRC 覆盖填充后的缓冲区。
- 块 pacing 没有确认：除非接收方的槽位是 `RECV_STATE_READY` [link_rfu_2.c:1146]，否则 `SEND_BLOCK_INIT` 会被忽略。`MysteryGiftTiming.inter_block_gap_frames` 是 36；丢失一个块会导致控制台永远等待。
- 当控制台发送时，遵循[镜像规则](frlg_link.md#row-one-of-the-parents-table-is-the-consoles-own-command-mirrored-back)。

### 模块

在 `pokeldn/frlg/gift/` 下，除非另有说明：

| 文件 | 角色 |
|---|---|
| `mg_link.py` | 帧格式：6 字节 `{ident, crc, size}` 头块 + ≤252 字节分块 |
| `mg_script.py` | 客户端脚本汇编器、反编译器的固件脚本、`MysteryGiftLinkGameData` 读取器 |
| `mg_server.py` | 服务器脚本解释器 (`SVR_*`) |
| `host_mystery_gift.py` | 领导引擎：`tick()` → 父 gSendCmd，`feed_child_slot()` ← 子行 |
| `host_mg_app.py` | 主机运行时的应用程序钩子 |
| `wonder_card.py` | 字节精确的 Celebi 和传说野兽卡/RAM 脚本构建器 |
| `stamp_rally.py` | 盖章集卡、盖章、激活包装、递送脚本 |
| `gift_composer.py` | 操作定义、光标状态验证、RAM 脚本编译器 |
| `gift_registry.py` | 礼物目录 |
| `gift_to_bin.py` | 面向外部第 3 世代神秘礼物工具的 `.bin` 导出器 |
| `pokeldn/frlg/save/save_inject.py` | 带卡、RAM 脚本和扇区校验和的存档礼物写入 |
| `bin/frlg_mg_host.py` | CLI |

## 运行方法

    (他们) 神秘礼物 -> 神秘卡片 (接收者) -> 好友 (Ami)，在搜索屏幕等待
    (你)  POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --phy auto \
               --keys PROD_KEYS --gift beast-cutscene --flag-id 1005
    (他们) 当主机出现时加入；如果出现替换卡提示则选择 YES

Radio 设置：[ESP32 收音机](hardware_esp32.md)。每次运行一个控制台；主机一旦离开 LDN 就会停止([主机实现](frlg_host.md))。`tests/test_mystery_gift_flow.py` 和 `tests/test_mystery_gift_end_to_end.py` 模拟控制台的接收路径。

`--save-to-board` 将礼物存储在 ESP32 板上而不是本地，然后退出；从任何 USB 充电器供电后，板子本身就会为每个加入的控制台播放本次会话，一次一个，每个卡带使用自己的字节([主机镜像](hardware_esp32.md#a-host-image))。

    (你)  POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live \
               --keys PROD_KEYS --gift celebi --save-to-board

## 链接能承载的内容

22 个客户端指令中，有 3 个[include/mystery_gift_client.h:18]会执行某些操作：

| 指令 | 控制台执行的操作 |
|---|---|
| `CLI_SAVE_RAM_SCRIPT` (17) | 存储一个字段脚本；在下一次 NPC 交互时运行 |
| `CLI_RUN_MEVENT_SCRIPT` (15) | 运行神秘事件字节码脚本（17 操作码 VM） |
| `CLI_RUN_BUFFER_SCRIPT` (21) | `func = (void *)gDecompressionBuffer; func(&param, gSaveBlock2Ptr, gSaveBlock1Ptr)`；最多 1024 字节 ARM |

## 唯一的 RAM 脚本槽

控制台持有神秘卡片或绑定的 RAM 脚本，但不同时拥有两者。`ValidateSavedWonderCard` 以 `ValidateRamScript` 结尾[mystery_gift.c:186]，该函数要求 `RAM_SCRIPT_MAGIC`、地图 `MAP_UNDEFINED` 和 `objectId == 0xFF`[script.c:538]；字段脚本仅在与 NPC 交互的坐标处运行一次[field_control_avatar.c:458]。`CLI_SAVE_RAM_SCRIPT` 写入 `MAP_UNDEFINED/0xFF`[script.c:578]；神秘事件 VM 的 `initramscript` 写入真实坐标。带绑定脚本时，卡片仍保留在存档中，但菜单隐藏它，GameData 报告 `flagId` 为 0[mystery_gift.c:349]。

下一次神秘卡片会重新绑定槽位，卡片恢复显示；缓冲脚本不会影响槽位。卡片重写 SaveBlock1 +0x32E0（卡片）和 +0x361C（RAM 脚本），仅一个扇区，SaveBlock2 中无内容。

`ramScript.checksum` 是对 1000 字节的 `CalcCRC16WithTable`，即 999 字节声明内容和一个零填充字节[script.c:500]（`CalculateRamScriptChecksum` 在 BPRE 为 `0x0806D43C`，BPRF 为 `0x0806D5A0`）。CRC 覆盖 999 字节的槽位，在其对象首次被对话时被擦除[script.c:526]。
文件名: frlg_gift.md
这是第 2/3 段（请只翻译本段，保持与前后段衔接的标题层级）。

## 礼物目录

`--gift NAME`；`--help` 列出标志 ID（1000..1019）。只有持有的卡片才重要：相同的 ID 表示“已拥有此卡片”（`MysteryGift_CompareCardFlags`）。已持有卡片的游戏机只能接受 Mystery Event 礼物，无需提示。

| 礼物 | 功能 |
|---|---|
| `beast-cutscene-share` | 可重复播放的传奇野兽场景；默认演示卡 |
| `celebi` | 合成的等级 50 Celebi 卡片 |
| `porygon-tm-gift` | 一张 Porygon 卡片，一个 Clefairy 场景，TM29 精神力然后 TM46 偷盗 |
| `solrock-stamp` / `lunatone-stamp` | 一张 Stamp Rally 卡片的两个部分 |
| `altering-cave` | 官方 Altering Cave 事件，已移植 |
| `wish-egg`、`pokepark-egg`、`pc-japan-egg` | 官方发行的三个蛋 |
| `event-pokemon` | 一个 Gen 3 发行的宝可梦，直接进入队伍 |
| `starter-egg` | 九只初始伙伴之一的一个蛋，由 `random` 决定 |
| `rare-berries` | 一个 Enigma、一个 Lansat 和一个 Starf 浆果，每个阶段一个 |
| `national-dex` | `EnableNationalPokedex`（特殊 367）除非 `IsNationalPokedexEnabled`（403）返回 1 |
| `nature-mint`、`pc-anywhere` 和 42 张更多 | GB-Link 团队卡片 |
| `battle-count-card` | 官方的 Battle Count 卡片 |
| `visiting-trainer` | 一个 Battle Tower 训练员，标识 26（仅限 FireRed） |
| `mystery-event-probe` | `givenationaldex; setstatus 42; checksum`，VM 的自检 |
| `mystery-event-celebi` | `givepokemon`：一个 Lv30 Celebi 持有邮件，直接进入队伍 |
| `mystery-event-npc` | `initramscript`：将一个场地脚本绑定到 Pallet Town 的胖老头 |
| `rng-seed-reader`、`rng-rate-probe`、`rng-shiny-hunt`、`rng-mon-hunt`、`rng-mon-hunt-both`、`rng-mon-hunt-log` | 见 [RNG](frlg_rng.md) |

### 传奇野兽

一名送货员会给予 Lansat 和 Liechi 浆果以及一个 Master Ball，然后开始一个可重复的等级 65 对战：Suicune 对 Bulbasaur 存档，Entei 对 Squirtle，Raikou 对 Charmander。

### Porygon TM 礼物

一张 Porygon 图标卡片和一个 Clefairy 精灵（在玩家右侧三个格子）会分别在不同的检查点给予 TM29 然后 TM46。默认标志 ID 为 1007；查看器显示 `flag_id % 100`。

### Stamp Rally

两个事件共享一张 `SUN AND MOON RALLY` 卡片（Claydol 图标，两个印章槽，标志 ID 为 1006），顺序不限。每个印章都会给予一个等级 30 的 Solrock 或 Lunatone；两个印章都会给予一个等级 50 的 Celebi。

| 状态 | 含义 |
|---|---|
| `VAR_MYSTERY_GIFT_1` | Celebi 完成光标 |
| `VAR_MYSTERY_GIFT_2 = 0/1/2` | Solrock 缺失/激活/已获得 |
| `VAR_MYSTERY_GIFT_3 = 0/1/2` | Lunatone 缺失/激活/已获得 |
| `FLAG_MYSTERY_GIFT_DONE` | 集齐印章 |

```text
matching = saved flag ID == distribution flag ID and max stamps == 2 and icon species == CLAYDOL
if no card:                install shared card + delivery script + selected stamp, run activation
else if not matching:      offer the toss prompt; on accept, install as above
else if stamp species or ID already exists:   HAS_STAMP
else if neither slot empty:                   NO_ROOM_STAMPS
else:                      save the stamp, run activation, STAMP_RECEIVED
```

激活是一个 Mystery Event 包装器。`IsStampInMetadata` [mystery_gift.c:272] 会拒绝冲突的印章；`CLI_SAVE_STAMP` 只写入 `cardMetadata.stampData` [mystery_gift.c:307]。

### Altering Cave

官方脚本 [data/mystery_event_msg.s:325] 会将 `VAR_ALTERING_CAVE_WILD_SET`（0x4024，SaveBlock1 + 0x1048）加 1，达到 10 后循环；值 9 和以上的值会读取表 0 [wild_encounter.c:192]。

| 变量 | 物种 | | 变量 | 物种 |
|---|---|---|---|---|
| 0 | Zubat | | 5 | Aipom |
| 1 | Mareep | | 6 | Shuckle |
| 2 | Pineco | | 7 | Stantler |
| 3 | Houndour | | 8 | Smeargle |
| 4 | Teddiursa | | | |

### 发行蛋

三个日本发行，来自 GB-Link-Switch-LDN 的 `web/js/gift/official.js`。卡片会用 `random` 选择一个蛋 [scrcmd.c:455]；它会获得发行的招式、宿命遭遇标志和遇敌地点 0xFF。如果队伍已满，则在抽取前拒绝。

| 卡片 | 蛋 |
|---|---|
| `wish-egg`（Pokemon Center New York） | Chansey、Drowzee、Exeggcute、Farfetch'd、Kangaskhan、Lickitung；每个都学会 Wish |
| `pokepark-egg`（PokePark Market Fantasia） | Cacnea、Corphish、Corsola、Igglybuff、Minun、Pichu、Plusle、Psyduck、Skitty、Spinda、Spoink、Surskit、Taillow、Whismur、Wynaut |
| `pc-japan-egg`（Pokemon Center Japan） | Bellsprout（Teeter Dance）、Meowth（Petal Dance）、Oddish（Leech Seed）、Poliwag（Sweet Kiss） |

### 活动宝可梦

`--gift event-pokemon --event-pokemon NAME` 会发送一个由 PKHeX.Core 生成的 Gen 3 发行宝可梦（非蛋、非日本发行），通过其 PID/IV 方法进行合法性检查，当卡片被保存时通过 Mystery Event `givepokemon` 发送。默认是 WISHMKR Jirachi。如果队伍已满，则会返回状态 3，卡片可以再次被接收。

`NAME` 是训练员名称和物种：`WISHMKR Jirachi`、`CHANNEL Jirachi`、`Aura Mew`、`MYSTRY Mew`、`DOEL Deoxys`、`SPACE C Deoxys`、`ROCKS Metang`、每个 `10 ANIV` 物种，以及欧洲的 `10ANNIV`、`10JAHRE`、`10ANNI` 和 `10ANIV` 发行；`--language` 可以选择语言。

该卡片是独立于构建的；`tests/test_frlg_english_cartridges.py` 会通过每个卡带的 `RunMysteryEventScript` 运行它。

### GB-Link 团队卡片

GB-Link 团队的自定义卡片（GB-Link-Switch-LDN `cards/`，GPL-3.0）包括一张 Wonder Card 和一个 RAM 脚本，该脚本通过 `callnative` 调用 THUMB 代码。源代码在 `vendor/gblink-cards/` 中；`scripts/gen_team_cards.py` 构建 `pokeldn/frlg/data/team_cards.json`，逐字节复制所有 44 个他们的 `BPRE 1.10` 负载，并且 `team_cards.py` 注册每个没有 `custom-` 的 ID。`starter-egg`、`rare-berries`（物品 173-175）和 `national-dex`（`FLAG_SYS_NATIONAL_DEX` 0x840）是由合成器重建的。

| 组 | 卡片 |
|---|---|
| 改变宝可梦 | `nature-mint`、`ability-capsule`、`poke-ball-changer`、`pokemon-gender`、`nickname`、`stat-judge`、`hidden-power`、`hidden-power-type`、`ev-training`、`friendship`、`pp-max`、`max-conditions`、`pokerus`、`unown-letters`、`trade-evolution`、`espeon-umbreon`、`move-tutor` |
| 每帧钩子 | `speed-2`、`speed-3`、`speed-4`、`speed-0-75`、`speed-0-5`、`fast-text`、`travel-anywhere`、`pc-anywhere`、`hm-moves`、`reusable-tms`、`physical-special-split`、`exp-share`、`shiny-hunting`、`roamer` |
| 其他 | `no-encounters`、`legendary-respawn`、`instant-eggs`、`gift-box`、`pocket-casino`、`gift-ribbons`、`trainer-ids`、`gender-swap`、`rival-name` |
| 活动宝可梦 | `box-eggs`、`colosseum-pikachu`、`ageto-celebi`、`mattle-ho-oh` |

与他们的构建版本的差异：

- 所有十二个修订版 `0x0A` 卡带：`vendor/gblink-cards/symbols.json` 包含每个 ROM 的 167 个地址，`tests/test_team_cards.py` 检查它们，并且每个脚本检查头部的游戏、语言和修订版本（[卡带映射](frlg_rom_map.md#the-international-revision-0x0a-cartridges)）。
- 重新定位的脚本（996 字节）和菜单列表（80 字节）位于 `0x0203F768` 和 `0x0203FB50`，低于驻留钩子 `0x0203FC00`（[负载可以存在的位置](frlg_rom.md#where-a-payload-can-live)）。
- 钩子安装器链到 `VBlankIntr`，存储在 `0x0203FBFC`，因此一个钩子卡和一个游戏加速器可以相互替换。它们的状态位于 `0x0203FF60`。
- ID 大于 1019 没有 `sReceivedGiftFlags` 位；注册表发送 1000 + id mod 20。
- `hm-moves` 和 `physical-special-split` 的文本被缩短以适应 995 字节。

每张卡片在 Mom 绑定下在所有十二个卡带上运行 mGBA。在其他游戏的卡带上，负载会回答“This gift doesn't work with this version of the game.”（日语中为“Wrong game.”）。`colosseum-pikachu` 和 `ageto-celebi` 携带日语训练员名称，在欧洲卡带上绘制为点。

### Battle Count 卡片

`MysteryEventScript_BattleCard` [data/mystery_event_msg.s:162] 会给予一个 POTION，当 `GET_CARD_BATTLES_WON`（特殊 390）恰好等于三时；端口依赖于其自己的变量，因此可以重复。计数器只有在 u16 之后等于持有的卡片的标志 ID 时才会增加 [union_room.c:1777]（`frlg_trade_host.py --card-flag-id N`）。

| 什么增加 | 位置 | 规则 |
|---|---|---|
| `numTrades` | 一个已完成的交易 [trade_scene.c:2609] | 一个卡片没有统计的训练员 ID |
| `battlesWon` / `battlesLost` | 一个有线俱乐部对战 [cable_club.c:792] | 相同，5 个 ID 每个状态 |

联盟房间对战不计入；只有 [有线俱乐部 Colosseum](frlg_link.md#the-cable-club-colosseum) 才计入。计数器位于 SaveBlock1 + 0x3434，没有 CRC [mystery_gift.c:490]：

    0x3434: 0000 0000 0100 2300     交易 1，图标 35 (CARD_TYPE_LINK_STAT)

一个 `CARD_TYPE_GIFT` 卡片即使在特殊脚本运行时也会保持为零。

### 访问训练员

`CLI_RECV_EREADER_TRAINER`（18，标识 26）会将缓冲区复制到 `gSaveBlock2Ptr->battleTower.ereaderTrainer` [mystery_gift_client.c:233]。该结构体是 188 字节 [global.h:286]：

    0x00 u8  unk0                  0x10 u16 greeting[6]            0x34 BattleTowerPokemon party[3]
    0x01 u8  trainerClass          0x1C u16 farewellPlayerLost[6]  0xB8 u32 checksum
    0x02 u16 winStreak             0x28 u16 farewellPlayerWon[6]
    0x04 u8  name[8]
    0x0C u8  trainerId[4]

当前 46 个字不是全零并且 u32 是它们的和时有效 [battle_tower.c:1354, :1384]。`SevenIsland_House_Room1` 中的老妇人会提供一个可重复的 3v3 对战，由 `CreateBattleTowerMon` [battle_tower.c:928] 构建；没有等级规则或禁止列表适用。FRLG 显示五个名称字节 [battle_tower.c:1343]。`--gift visiting-trainer` 会发送卡片、RAM 脚本和训练员；如果已经持有相同的卡片，则只发送训练员。

## Wonder News

`struct WonderNews` [global.h:646] 是 444 字节：

| 偏移量 | 大小 | 字段 | 备注 |
|---|---|---|---|
| 0x000 | 2 | `id` | 必须不为 0，这是唯一的检查 [mystery_gift.c:113] |
| 0x002 | 1 | `sendType` | `SEND_TYPE_DISALLOWED` 隐藏“发送” [mystery_gift.c:120] |
| 0x003 | 1 | `bgType` | `>= NUM_WONDER_BGS` 读取 0 [mystery_gift_show_news.c:110] |
| 0x004 | 40 | `titleText` | 居中在一个 224 像素的窗口中 |
| 0x02C | 400 | `bodyText[10][40]` | 八行显示屏幕；一行超过索引 7 会打开滚动指示器 [:346] |

`IsWonderNewsSameAsSaved` 比较所有 444 字节 [mystery_gift.c:140]（`--news-id N` 会使新闻更新）。新闻和卡片互不影响。

- `build_wonder_news_app_data` 宣传活动 22 [src/data/union_room.h:406]。
- 游戏机回答 `MG_LINKID_RESPONSE`（标识 19）：`FALSE` 已保存，`TRUE` 已经持有 [mystery_gift_client.c:210; mystery_gift_scripts.c:126]。
- 来自朋友的新闻会滚动一个浆果，从 `ITEM_RAZZ_BERRY` 到 `ITEM_NOMEL_BERRY`，由 CeruleanCity_House4 中的男子给予，最多五个，然后是 500 步 [mystery_gift_menu.c:1367, wonder_news.c:21]。四种浆果的奖励需要关闭的无线路径。

`--news`（`--news berry`、`--news-id N`）。消息顺序（约 18 秒）：

    标识 16  sClientScript_SendGameData
    标识 17  MysteryGiftLinkGameData
    标识 16  sClientScript_SaveNews
    标识 23  MG_LINKID_NEWS - 444 字节，分三块
    标识 19  MG_LINKID_RESPONSE - FALSE：游戏机已保存
    标识 16  sClientScript_NewsReceived
    标识 20  READY_END                              -> SVR_MSG_NEWS_SENT

## 问卷作为密码门

`SVR_CHECK_QUESTIONNAIRE` 会比较四个 Poke Mart 问卷单词 [mystery_gift.c:422]；`mg_server.gate_on_questionnaire(script)` 会将其拼接到游戏数据前缀之后：

    bin/frlg_mg_host.py --gift ... --questionnaire species:55,FEELINGS/60,move:177,why

一个单词是一个英文名称、`species:N`、`move:N`、`GROUP/INDEX` 或一个原始 ID。错误的短语会得到主机的 64 字节消息（`CLIENT_SCRIPT_DYNAMIC_ERROR`），并且不会发送任何东西。每个会话都会记录游戏数据中的控制台的四个单词 [mystery_gift.c:361]：

    questionnaire: POKEMON/55  done [FEELINGS/60]  MOVE_1/177  why [MISC/37]

`EC_GROUP_POKEMON` 按物种索引，`EC_GROUP_MOVE_1` 按移动 ID 索引；见 [法国易聊词汇表](frlg_rom_map.md#the-french-easy-chat-vocabulary)。

## 控制台自报的信息

GameData 携带 Easy Chat 资料及卡片统计数据 [mystery_gift.c:361]。`--game-data-log PATH`（`game_data_log.py`）将每个会话追加到 JSONL 账本，并打印自该控制台上次以来所移动的数据；`tools/frlg/game_data_read.py PATH` 读取它。计数器仅作为同一卡片标志 id 的差值才有证据价值。

## 保存备份与恢复

Wonder Card、Friend 会话将控制台整个 128 KiB 保存芯片复制到主机，或将 `.sav` 写入其中并让游戏加载和保存它；不会发送任何卡片。`asm/save-backup.s` 和 `asm/save-restore.s` 移植自 GB-Link Team 的 `cards/savebackup.s` 和 `cards/saverestore.s`（GPL-3.0）；主机端为 `pokeldn.frlg.gift.save_transfer`（`--save-backup FILE`，`--save-restore FILE`），以及应用的「你的保存」标签页（参见 [Your saves](gui.md#your-saves)）。二者均适配十二种卡带（参见 [Save backup and restore](frlg_rom_map.md#save-backup-and-restore)）。

### 令牌编码

字节 `n < 0x80` 后跟 `n + 1` 个字面字节；`n >= 0x80` 后跟一个重复 `n - 0x80 + 3` 次的字节（重复次数 3 至 130，字面量最长 128）。

### 备份

客户端脚本重复执行 `CLI_LOAD_TOSS_RESPONSE, CLI_RUN_BUFFER_SCRIPT, CLI_SEND_LOADED`，每个脚本最多 32 次。每次传递最多发送 1 KiB 令牌，对应芯片上最多 8 KiB 数据，且绝不跨越 64 KiB 银行边界；芯片偏移为 `client->param = 0x5A << 24 | offset` [mystery_gift_client.c:276]，而不带 `0x5A` 的 `param` 从 `first` 开始。

| payload 字 | 偏移 | 值 |
|---|---|---|
| `first` | `0x004` | 第一轮开始的芯片偏移 |
| `send_queue` | `0x008` | `&gRfu.sendQueue.count` |

每轮在 `gDecompressionBuffer + 0x800` 中暂存 0x800 字节数据，一帧压缩至 `+ 0x400`，并设置 `link.sendBuffer`（`param + 0x3C`）和 `link.sendSize`（`param + 0x34`）。它会等待直到 `gRfu.sendQueue.count` 为零。会话在 `CLI_MSG_BUFFER_FAILURE` 带消息时结束，因此控制台不会保存 [mystery_gift_menu.c:1379]。中断的备份可通过游戏代码和训练家 ID 恢复。

### 恢复

1. 第一条消息是 620 字节镜像；`install` 将其复制到 `gDecompressionBuffer + 0x400`，并回复 28 个槽位的 12 字节页脚（id、校验和、签名、计数器位于 `+0xFF4`）。
2. 主机像 `GetSaveValidStatus` 一样找到最新的完整槽位，并将文件副本写入另一个槽位，计数器为 `newest + 1`，然后按文件内容写入槽位 28 至 31。
3. 它先擦除目标槽位的 id-0 扇区，再最后写入新的 id 0，因此芯片自己的副本会一直加载，直到新副本完整。
4. 后续消息以 `b RESIDENT + 4`（`0xEA0000FF`）开头，后跟一个操作。`OP_DATA`（1）将扇区、写标志、u16 偏移、u16 令牌长度及令牌载入 4 KiB 缓冲区；该扇区的最后一条消息通过 `swi 0x48` 写入并验证，校验失败时设置失败掩码位。
5. `OP_FINISH`（2）在未发生失败时调用 `LoadGameSave(SAVE_NORMAL)` [save.c:803]。若返回 `SAVE_STATUS_OK`，会话在 `CLI_MSG_BUFFER_SUCCESS` 结束，控制台保存已加载的游戏；否则在 `CLI_MSG_BUFFER_FAILURE` 结束，旧存档保留。

| payload 字 | 偏移 | 值 |
|---|---|---|
| `b install` | `0x000` | 第一条消息的入口 |
| `b entry` | `0x004` | 每条后续消息的入口，位于 `gDecompressionBuffer + 0x404` |
| `load_game_save` | `0x008` | `LoadGameSave \| 1` |

主机拒绝加载副本不完整或布局不一致的存档：日文 SaveBlock1 短 40 字节，从训练家自身宝可梦的语言字节（`+0x12`）处读取。

`tests/test_save_transfer.py` 覆盖备份、恢复、中断恢复及脚本控制台下的中断恢复测试。在真机上，备份适用于法语和英文版火红，恢复适用于英文版火红及一份法文存档。控制台下一次保存与文件在槽位 1 至 7 不同，这些槽位携带 `LoadGameSave` 重新生成的加密密钥。

## 礼物创作

`pokeldn.frlg.gift.gift_composer` 根据 `WonderGift` 定义构建卡片和投送脚本：

```python
MEWTWO_GIFT = WonderGift(
    slug="mewtwo-encounter",
    card=WonderCardSpec(icon_species=150, title="MYSTERIOUS ENCOUNTER",
                        body=("Visit the deliveryman.",), default_flag_id=1008),
    intro_message="A powerful presence is waiting!",
    event=GiftSpec(shareable="once"),          # or StampRallySpec(...)
    delivery=DeliveryPlan(delivery=(
        DeliveryStage(Message("Take this."), GiveItem(1)),  # Master Ball
        DeliveryStage(ShowSprite(0, RelativeToPlayer(dx=1)), BattleLegendary(150, level=70)),
    )),
    completed_message="That mysterious encounter is over.",
)
```

`WonderGift.delivery` 使用 `delivery`；`StampSlot.delivery` 和 `StampRallySpec.completion` 使用 `pre_stages` 和 `post_stages`。编译器从 `VAR_MYSTERY_GIFT_1` 继续执行阶段，并在成功时设置 `FLAG_MYSTERY_GIFT_DONE` 和收据标志；`GiftSpec(repeatable=True)` 重置游标。

### 阶段与条件

每个 `DeliveryStage` 是一个检查点；切勿在同一阶段中放入两个可能失败的奖励（`GiveItem`、`GivePokemon`、`GiveEgg`）。携带招数的 `GiveEgg` 需要一个队伍槽位。`GiveRandomEgg(eggs)` 通过跳转表随机选择一个（十五只四招蛋 fits in 944 字节）。`condition=`（`VarEquals`、`FlagSet`、`Not`、`AllOf`、`AnyOf`）跳过阶段但仍推进游标；`RequireSpecialResult(...)` 在失败时停止且不推进游标。

```python
DeliveryStage(ShowSprite(142, RelativeToPlayer(dx=1)),
              condition=VarEquals(0x4031, 0))  # VAR_STARTER_MON == Bulbasaur
DeliveryStage(RequireSpecialResult(SPECIAL_HAS_ALL_KANTO_MONS, 1, "Finish the KANTO POKEDEX first."),
              GivePokemon(251, level=50))
```

`SetVar`（`setvar` 0x16）和 `AddVar`（`addvar` 0x17）接受保存变量 0x4000..0x40FF 和特殊变量 0x8000..0x8011。

### 战斗

`BattleLegendary` 发出 `setwildbattle`、`special StartLegendaryBattle`、`end`，且不带 `waitstate`（参见 [a RAM script may not come back from a battle](frlg_rng.md#a-ram-script-may-not-come-back-from-a-battle)）；`BattlePokemon` 发出 `dowildbattle`。二者均以该阶段结束。战斦在邮票槽路径中除非作为条件性终结替代方案外均被拒绝。

### 分享

`GiftSpec.shareable` 设置卡片的 `sendType`：`"never"`、`"once"`（接收者的副本将变为不可分享）或 `"always"`。

### 命中标记

`GivePokemon(..., fateful_encounter=True)`（及 `GiveEgg`）会发出 `setmonmodernfatefulencounter`（`0xCD`）和 `setmonmetlocation`（`0xD2`、0xFF） [data/mystery_event_msg.s:71]。第一条指令不检查索引越界 [scrcmd.c:2239]；索引为赠送前的队伍数，满队时跳转至失败标签。总结行仅来自相遇位置 [pokemon_summary_screen.c:2665, 2799]；`modernFatefulEncounter` 是 Misc+0x08 的第 31 位 [include/pokemon.h:40-82]。

### 作曲家中的 `initramscript`

`gift_composer.build_bound_script(actions)` 和 `build_mevent_npc_script(actions=...)` 将动作编译为 `initramscript` 绑定的字段脚本。它没有阶段游标且整体重跑，因此一次性效果需自备 `SetVar` 或条件。

### 注册与验证

```python
from pokeldn.frlg.gift.gift_registry import GIFT_REGISTRY
GIFT_REGISTRY.register_definition(MEWTWO_GIFT)
```

注册会验证并编译：卡片文本与标志、计划结构、动作范围、游标边界、唯一邮票、战斗放置、指针及 995 字节 RAM 脚本限制，错误信息中会命名路径（如 `example-rally.event.slots[1].delivery.post_stages[0].actions[1]: ...`）。

## 静态工具

```bash
./.venv/bin/python -m pokeldn.frlg.gift.gift_to_bin --gift beast-cutscene --flag-id 1005 --out-dir exported-gift
./.venv/bin/python -m pokeldn.frlg.save.save_inject game.sav --gift beast-cutscene --flag-id 1005
```

`gift_to_bin` 输出 336 字节 Wonder Card 和 1004 字节 RAM 脚本，供 `pokemon-gen3-mysterygift-tool` 使用。`save_inject` 将二者写入当前槽位，修复卡片、RAM 脚本及扇区校验和，并保存为 `<save>.gift.sav`（`--in-place` 覆盖；`--make-artifact` 在 `artifacts/` 下写入 `.ram.lst` 列表）。

## 封闭路径

### 无线通信（JoySpot）

无线路径在 RFU 序列号关卡被阻塞：

| | Friend | Wireless Communication |
|---|---|---|
| 监听 | `Task_ListenForCompatiblePartners` [union_room.c:3757] | `Task_ListenForWonderDistributor` [union_room.c:3799] |
| 接受 RFU 序列号 | `{0x0002, 0x7F7D}` | 仅 `== 0x7F7D` [link_rfu_3.c:920] |
| 选择 | 玩家从列表中选择 | 自动连接 |
| 可从 Switch 到达 | 是 | 否 |

`Task_CardOrNewsOverWireless` [union_room.c:2415] 仅在候选 0 的 `serialNo` 为 `0x7F7D` 时保留它，然后检查生成状态、`hasCard` 位（失败时 SE_BOO）并重连。Switch 桥报告 `0x0002`，广告中不含序列号字段；`svc_47` [sloopsvc.c:34] 接收 24 字节且不含序列号。一条原生广告：

```
50 10 | c1 cc bf bf c8 ff 00 00 | 65 ac | 00 00 00 00 | 84 15 | 00 00 00 00 00 00
TID   | uname                   | parent| unexplained | search| unexplained
```

位于 `record[16:18]` 的搜索字为 `activity:7 | bit7 | version:3 | language:3 | hasCard?:1 | startedActivity:1`。

没有尝试过的广告变体（场景 id、应用版本、在每个空闲偏移处放置 `0x7F7D`、活动、`hasCard`、bit 7）能引发无线路径的认证。未测试：`local_communication_id`、场景暴力破解、组合方式。

### e-Reader 本身

Trainer Tower 的 e-Reader 使用通过 GBA 串行链路（`ereader_screen.c`）的 `LINKTYPE_EREADER_FRLG`，而非无线适配器。

### Aurora 和 Mystic 票

Switch 版本在首次 Hall of Fame 记录时授予双票及其 `FLAG_RECEIVED_*` 标志 [post_battle_event_funcs.c:52，`REVISION >= 0xA`]，因此之后的票卡赠送毫无效果。卡片的 `iconSpecies` 非 `SPECIES_NONE` 时会绘制图标；超过 `SPECIES_UNOWN_B - 1` 时绘制问号 [mystery_gift_show_card.c:466, pokemon_icon.c:1102]。Old Sea Map 仅限绿宝石 [mystery_gift.c:30]。

## 陷阱

- `charmap.encode` 会丢弃未知字符，连换行符也不例外。换行符为 0xFE；`mg_server` 拒绝第三行或宽度超过 31 字符的内容 [strings.c:1291]（窗口为 28 瓦片 × 4，参见 [mystery_gift_menu.c:97,524]）。
- 新载荷需放入 `buffer_script.py` 中的 `DUMP_SCRIPTS` 和 `DECODED_SCRIPTS`，以及启动器的 `--dump-file` 行。

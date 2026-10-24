---
title: Mystery Gift
parent: FireRed and LeafGreen
nav_order: 2
---

# 神秘礼物

火红／叶绿中通过“朋友”的神秘礼物会接收一张神秘卡片、一个传递脚本、神秘新闻、一位来访的对战塔训练家，以及直接进入同行队伍的宝可梦，无需宝可梦中心。神秘事件 VM 和原生 ARM 代码位于[游戏机上的代码](frlg_rom.md)。

## 会话

游戏机的客户端以 `{CLI_RECV, MG_LINKID_CLIENT_SCRIPT}, {CLI_COPY_RECV}` 启动 [mystery_gift_scripts.c:15]，并执行它接收到的任何 `MysteryGiftClientCmd` 数组 [mystery_gift_client.c:87]。

    console joins  ->  SEND_PLAYER_IDS  ->  LinkPlayer block exchange  ->  one standby barrier
      server -> CLIENT_SCRIPT (sClientScript_SendGameData, 32 B)
      client -> GAME_DATA     (MysteryGiftLinkGameData, 96 B)   -- validated, card flag compared
      server -> CLIENT_SCRIPT (sClientScript_SaveCard, 48 B)
      server -> CARD          (struct WonderCard, 332 B)
      server -> RAM_SCRIPT    (1024 B: the delivery bytecode, zero-padded)
      client -> READY_END     (1024 B)
    close-link handshake  ->  disconnect

### 分帧规则

- 大小为 0 表示 1024 [mystery_gift_link.c:55]；`SVR_COPY_SAVED_RAM_SCRIPT` 从不设置 `ramScriptSize` [mystery_gift_server.c:275]，因此 RAM 脚本和 READY_END 是完整的 1024 字节消息。CRC 覆盖填充后的缓冲区。
- 块节奏没有确认：除非接收方槽位为 `RECV_STATE_READY`，否则 `SEND_BLOCK_INIT` 会被忽略 [link_rfu_2.c:1146]。`MysteryGiftTiming.inter_block_gap_frames` 为 36；被丢弃的块会让游戏机永远等待下去。
- 游戏机发送时的停顿遵循[镜像规则](frlg_link.md#row-one-of-the-parents-table-is-the-consoles-own-command-mirrored-back)。

### 模块

除非另有说明，均位于 `pokeldn/frlg/gift/`：

| 文件 | 作用 |
|---|---|
| `mg_link.py` | 分帧：6 字节 `{ident, crc, size}` 头块 + ≤252 字节分块 |
| `mg_script.py` | 客户端脚本汇编器、反编译的固定脚本、`MysteryGiftLinkGameData` 读取器 |
| `mg_server.py` | 服务器脚本解释器（`SVR_*`） |
| `host_mystery_gift.py` | 主导引擎：`tick()` → 父级 gSendCmd，`feed_child_slot()` ← 子行 |
| `host_mg_app.py` | 宿主运行时上的应用钩子 |
| `wonder_card.py` | 字节精确的时拉比与传说野兽卡片/RAM 脚本构建器 |
| `stamp_rally.py` | 集章拉力赛卡片、印章、激活包装器、传递脚本 |
| `gift_composer.py` | 动作定义、光标状态验证、RAM 脚本编译器 |
| `gift_registry.py` | 目录 |
| `gift_to_bin.py` | 供外部第三代神秘礼物工具使用的 `.bin` 导出器 |
| `pokeldn/frlg/save/save_inject.py` | 带卡片、RAM 脚本和扇区校验和的存档礼物写入 |
| `bin/frlg_mg_host.py` | 命令行工具 |

## 运行方式

    (them) Mystery Gift -> Wonder Cards (Recevoir) -> Friend (Ami), wait on the search screen
    (you)  POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --phy auto \
               --keys PROD_KEYS --gift beast-cutscene --flag-id 1005
    (them) join the host when it appears; YES on the replace-card prompt if one shows

无线电设置：[ESP32 无线电](hardware_esp32.md)。每次运行一台游戏机；主机一旦离开 LDN 即停止（[主机实现](frlg_host.md)）。`tests/test_mystery_gift_flow.py` 和 `tests/test_mystery_gift_end_to_end.py` 模拟游戏机的接收路径。

## 链路能承载的内容

22 条客户端指令中有 3 条 [include/mystery_gift_client.h:18] 会执行某些操作：

| 指令 | 游戏机所做的操作 |
|---|---|
| `CLI_SAVE_RAM_SCRIPT` (17) | 存储一个场景脚本；它会在下次与 NPC 互动时运行 |
| `CLI_RUN_MEVENT_SCRIPT` (15) | 运行神秘事件字节码脚本（17 操作码 VM） |
| `CLI_RUN_BUFFER_SCRIPT` (21) | `func = (void *)gDecompressionBuffer; func(&param, gSaveBlock2Ptr, gSaveBlock1Ptr)`；最多 1024 字节的 ARM 代码 |

## 唯一的 RAM 脚本槽

游戏机要么持有神秘卡片，要么持有绑定的 RAM 脚本，绝不会同时持有两者。`ValidateSavedWonderCard` 以 `ValidateRamScript` 结尾 [mystery_gift.c:186]，这要求 `RAM_SCRIPT_MAGIC`、地图为 `MAP_UNDEFINED` 且 `objectId == 0xFF` [script.c:538]；场景只会在所对话对象的坐标处运行一个 [field_control_avatar.c:458]。`CLI_SAVE_RAM_SCRIPT` 会写入 MAP_UNDEFINED/0xFF [script.c:578]；神秘事件 VM 的 `initramscript` 会写入真实坐标。绑定脚本时，卡片仍保留在存档中，但菜单会隐藏它，并且 GameData 报告 `flagId` 为 0 [mystery_gift.c:349]。

下一张神秘卡片会重新绑定该槽位，卡片随之恢复；缓冲区脚本则不会动该槽位。卡片会重写 SaveBlock1 +0x32E0（卡片）和 +0x361C（RAM 脚本），仅一个扇区，不写 SaveBlock2。

`ramScript.checksum` 是对 1000 字节（声明的 999 字节和 1 个置零填充字节）计算 `CalcCRC16WithTable` 得到的 [script.c:500]（`CalculateRamScriptChecksum` `0x0806D43C` BPRE，`0x0806D5A0` BPRF）。如果某个槽位的 CRC 覆盖 999 字节，则在其对象第一次被对话时会被清除 [script.c:526]。

## 礼物目录

`--gift NAME`；`--help` 会列出旗标 ID（1000..1019）。只有持有的卡片重要：同一 ID 表示“已持有此卡片”（`MysteryGift_CompareCardFlags`）。已经持有该卡片的主机会直接收下神秘活动礼物，不会有提示。

| gift | what it does |
|---|---|
| `beast-cutscene-share` | 可重复的传说宝可梦过场动画；默认演示卡片 |
| `celebi` | 组合好的 50 级雪拉比卡片 |
| `porygon-tm-gift` | 一张多边兽卡片、皮皮的过场动画，先给 TM29 精神强念，再给 TM46 小偷 |
| `solrock-stamp` / `lunatone-stamp` | 同一张集章拉力赛卡片的两半 |
| `altering-cave` | 官方变化洞窟活动，已移植 |
| `wish-egg`、`pokepark-egg`、`pc-japan-egg` | 官方配送的蛋 |
| `event-pokemon` | 一只第三代配送宝可梦，直接进入同行队伍 |
| `starter-egg` | 九只第一伙伴之一所产的蛋，由 `random` 抽取 |
| `rare-berries` | 谜芝果、兰萨果和星桃果，每种一个阶段 |
| `national-dex` | 启用全国图鉴（特殊 367），除非 `IsNationalPokedexEnabled`（403）返回 1 |
| `nature-mint`、`pc-anywhere` 以及另外 42 张 | GB-Link 团队的卡片 |
| `battle-count-card` | 官方对战计数卡 |
| `visiting-trainer` | 一个作为 ident 26 的对战塔训练家（仅火红） |
| `mystery-event-probe` | `givenationaldex; setstatus 42; checksum`，VM 的自检 |
| `mystery-event-celebi` | `givepokemon`：一只 30 级携带邮件的雪拉比，直接进入同行队伍 |
| `mystery-event-npc` | `initramscript`：将场景脚本绑定到真新镇的胖男人 |
| `rng-seed-reader`、`rng-rate-probe`、`rng-shiny-hunt`、`rng-mon-hunt`、`rng-mon-hunt-both`、`rng-mon-hunt-log` | 参见[随机数系统](frlg_rng.md) |

### 传说中的宝可梦

配送员送出兰萨果和枝荔果以及一个大师球，然后开始一场可重复触发的 65 级战斗：妙蛙种子存档对应水君，杰尼龟对应炎帝，小火龙对应雷公。

### 多边兽 TM 礼物

一张多边兽图标卡片和玩家右侧三格处的皮皮精灵会在不同的检查点分别给予 TM29 和 TM46。默认旗标 ID 为 1007；查看器显示 `flag_id % 100`。

### 集章拉力赛

两个活动共用一张 `SUN AND MOON RALLY` 卡片（念力土偶图标、两个集章槽、旗标 ID 1006），先后顺序任意。每个印章给一只 30 级的太阳岩或月石；两个都集齐给一只 50 级的雪拉比。

| 状态 | 含义 |
|---|---|
| `VAR_MYSTERY_GIFT_1` | 雪拉比完成游标 |
| `VAR_MYSTERY_GIFT_2 = 0/1/2` | 太阳岩未获得 / 已激活 / 已领取 |
| `VAR_MYSTERY_GIFT_3 = 0/1/2` | 月石未获得 / 已激活 / 已领取 |
| `FLAG_MYSTERY_GIFT_DONE` | 集章完成 |

```text
matching = saved flag ID == distribution flag ID and max stamps == 2 and icon species == CLAYDOL
if no card:                install shared card + delivery script + selected stamp, run activation
else if not matching:      offer the toss prompt; on accept, install as above
else if stamp species or ID already exists:   HAS_STAMP
else if neither slot empty:                   NO_ROOM_STAMPS
else:                      save the stamp, run activation, STAMP_RECEIVED
```

激活过程是一个神秘活动包装器。`IsStampInMetadata` [mystery_gift.c:272] 会拒绝冲突的印章；`CLI_SAVE_STAMP` 只写入 `cardMetadata.stampData` [mystery_gift.c:307]。

### 变化洞窟

官方脚本 [data/mystery_event_msg.s:325] 会给 `VAR_ALTERING_CAVE_WILD_SET`（0x4024，SaveBlock1 + 0x1048）加 1，到 10 时回绕；值 9 及以上读取表 0 [wild_encounter.c:192]。

| 变量 | 宝可梦 | | 变量 | 宝可梦 |
|---|---|---|---|---|
| 0 | 超音蝠 | | 5 | 长尾怪手 |
| 1 | 咩利羊 | | 6 | 壶壶 |
| 2 | 榛果球 | | 7 | 惊角鹿 |
| 3 | 戴鲁比 | | 8 | 图图犬 |
| 4 | 熊宝宝 | | | |

### 配送的蛋

三个日本配信，来自 GB-Link-Switch-LDN 的 `web/js/gift/official.js`。卡片用 `random` [scrcmd.c:455] 抽取一个蛋；蛋会获得该配信的招式、命运邂逅标志位和相遇地点 0xFF。同行队伍已满时会在抽取前拒绝。

| 卡片 | 蛋 |
|---|---|
| `wish-egg`（Pokemon Center New York） | 吉利蛋、催眠貘、蛋蛋、大葱鸭、袋兽、大舌头；每只都会祈愿 |
| `pokepark-egg`（PokePark Market Fantasia） | 刺球仙人掌、龙虾小兵、太阳珊瑚、宝宝丁、负电拍拍、皮丘、正电拍拍、可达鸭、向尾喵、晃晃斑、跳跳猪、溜溜糖球、傲骨燕、咕妞妞、小果然 |
| `pc-japan-egg`（Pokemon Center Japan） | 喇叭芽（摇晃舞）、喵喵（花瓣舞）、走路草（寄生种子）、蚊香蝌蚪（天使之吻） |

### 活动宝可梦

`--gift event-pokemon --event-pokemon NAME` 会在保存卡片时，通过神秘活动 `givepokemon` 发送一只由 PKHeX.Core 根据 `EncounterGift3`（非蛋、非日文）按 PID/IV 方法生成并通过合法性检查的第三代配信宝可梦。同行队伍已满时会回应状态 3，卡片可以再次接收。默认是 WISHMKR 基拉祈。

`NAME` 是训练家名称和宝可梦种类：`WISHMKR Jirachi`、`CHANNEL Jirachi`、`Aura Mew`、`MYSTRY Mew`、`DOEL Deoxys`、`SPACE C Deoxys`、`ROCKS Metang`、所有 `10 ANIV` 种类，以及欧洲的 `10ANNIV`、`10JAHRE`、`10ANNI` 和 `10ANIV` 配信；`--language` 在其中选择语言。

该卡片与构建无关；`tests/test_frlg_english_cartridges.py` 会在每个卡带的 `RunMysteryEventScript` 中运行它。

### GB-Link 团队的卡片

GB-Link 团队的自制卡片（GB-Link-Switch-LDN `cards/`，GPL-3.0）是一张神秘卡片加上一段通过 `callnative` 调用 THUMB 代码的 RAM 脚本。源代码位于 `vendor/gblink-cards/`；`scripts/gen_team_cards.py` 构建 `pokeldn/frlg/data/team_cards.json`，逐字节复现全部 44 个 `BPRE 1.10` 载荷，`team_cards.py` 注册每个不带 `custom-` 前缀的 ID。`starter-egg`、`rare-berries`（道具 173-175）和 `national-dex`（`FLAG_SYS_NATIONAL_DEX` 0x840）用 composer 重建。

| 组 | 卡片 |
|---|---|
| 改变宝可梦 | `nature-mint`、`ability-capsule`、`poke-ball-changer`、`pokemon-gender`、`nickname`、`stat-judge`、`hidden-power`、`hidden-power-type`、`ev-training`、`friendship`、`pp-max`、`max-conditions`、`pokerus`、`unown-letters`、`trade-evolution`、`espeon-umbreon`、`move-tutor` |
| 逐帧钩子 | `speed-2`、`speed-3`、`speed-4`、`speed-0-75`、`speed-0-5`、`fast-text`、`travel-anywhere`、`pc-anywhere`、`hm-moves`、`reusable-tms`、`physical-special-split`、`exp-share`、`shiny-hunting`、`roamer` |
| 其他 | `no-encounters`、`legendary-respawn`、`instant-eggs`、`gift-box`、`pocket-casino`、`gift-ribbons`、`trainer-ids`、`gender-swap`、`rival-name` |
| 活动宝可梦 | `box-eggs`、`colosseum-pikachu`、`ageto-celebi`、`mattle-ho-oh` |

与原版构建的差异：

- 全部十二个修订 `0x0A` 卡带：`vendor/gblink-cards/symbols.json` 保存每个 ROM 的 167 个地址，`tests/test_team_cards.py` 检查这些地址，每个脚本检查头中的游戏、语言和修订（[卡带映射](frlg_rom_map.md#the-international-revision-0x0a-cartridges)）。
- 重定位后的脚本（996 字节）和菜单列表（80 字节）位于 `0x0203F768` 和 `0x0203FB50`，在常驻钩子 `0x0203FC00` 之下（[载荷可存放的位置](frlg_rom.md#where-a-payload-can-live)）。
- 钩子安装器链接到存储于 `0x0203FBFC` 的 `VBlankIntr`，因此钩子卡片和游戏加速会相互替换。它们的状态位于 `0x0203FF60`。
- 高于 1019 的 ID 没有 `sReceivedGiftFlags` 位；注册表发送 1000 + id mod 20。
- `hm-moves` 和 `physical-special-split` 文本被缩短以适配 995 字节。

在 mGBA 下，每张卡片都在全部十二个卡带上绑定妈妈运行。在另一个游戏的卡带上，载荷会回答“This gift doesn't work with this version of the game.”（日文为“Wrong game.”）。`colosseum-pikachu` 和 `ageto-celebi` 带有日文训练家名称，在欧洲卡带上显示为点。

### 对战计数卡

`MysteryEventScript_BattleCard` [data/mystery_event_msg.s:162] 在恰好三次 `GET_CARD_BATTLES_WON`（特殊 390）时给予一个伤药；此移植版本以自身变量为门控，因此可重复触发。仅当 96 字节训练家卡片之后的 u16 等于所持卡片的旗标 ID 时，计数器才会推进 [union_room.c:1777]（`frlg_trade_host.py --card-flag-id N`）。

| 递增项 | 位置 | 规则 |
|---|---|---|
| `numTrades` | 完成的连接交换 [trade_scene.c:2609] | 一个该卡片尚未计数的训练家 ID |
| `battlesWon` / `battlesLost` | 连线俱乐部对战 [cable_club.c:792] | 同上，每个统计 5 个 ID |

联盟房间对战不计入任何内容；只有[竞技场](frlg_link.md#the-cable-club-colosseum)才计入。计数器位于 SaveBlock1 + 0x3434，无 CRC [mystery_gift.c:490]：

    0x3434: 0000 0000 0100 2300     trades 1, icon 35 (CARD_TYPE_LINK_STAT)

`CARD_TYPE_GIFT` 卡片即使在执行该特殊时也保持为零。

### 来访训练家

`CLI_RECV_EREADER_TRAINER`（18，ident 26）将缓冲区复制到 `gSaveBlock2Ptr->battleTower.ereaderTrainer` [mystery_gift_client.c:233]。结构体为 188 字节 [global.h:286]：

    0x00 u8  unk0                  0x10 u16 greeting[6]            0x34 BattleTowerPokemon party[3]
    0x01 u8  trainerClass          0x1C u16 farewellPlayerLost[6]  0xB8 u32 checksum
    0x02 u16 winStreak             0x28 u16 farewellPlayerWon[6]
    0x04 u8  name[8]
    0x0C u8  trainerId[4]

当前 46 个字不全部为零且 u32 为其总和时有效 [battle_tower.c:1354, :1384]。随后 `SevenIsland_House_Room1` 中的老妇人会提供一场由 `CreateBattleTowerMon` [battle_tower.c:928] 构建的可重复 3v3；没有等级规则或禁用列表限制。FRLG 显示五个名称字节 [battle_tower.c:1343]。`--gift visiting-trainer` 会同时发送卡片、RAM 脚本和训练家；若已持有同一卡片，则只发送训练家。

## 神秘新闻

`struct WonderNews` [global.h:646] 为 444 字节：

| 偏移量 | 大小 | 字段 | 备注 |
|---|---|---|---|
| 0x000 | 2 | `id` | 不得为 0，这是唯一的检查 [mystery_gift.c:113] |
| 0x002 | 1 | `sendType` | `SEND_TYPE_DISALLOWED` 会隐藏“Send” [mystery_gift.c:120] |
| 0x003 | 1 | `bgType` | `>= NUM_WONDER_BGS` 时读作 0 [mystery_gift_show_news.c:110] |
| 0x004 | 40 | `titleText` | 在 224 px 窗口中居中 |
| 0x02C | 400 | `bodyText[10][40]` | 屏幕显示八行；行索引超过 7 时打开滚动指示器 [:346] |

`IsWonderNewsSameAsSaved` 比较全部 444 字节 [mystery_gift.c:140]（`--news-id N` 会让新闻被视为新新闻）。新闻与卡片永远不会相互取代。

- `build_wonder_news_app_data` 通告活动 22 [src/data/union_room.h:406]。
- 主机回应 `MG_LINKID_RESPONSE`（ident 19）：`FALSE` 已保存，`TRUE` 已持有 [mystery_gift_client.c:210; mystery_gift_scripts.c:126]。
- 来自朋友的新闻会在 `ITEM_RAZZ_BERRY` 到 `ITEM_NOMEL_BERRY` 之间掷出一个树果，由 `CeruleanCity_House4` 中的男人送出，最多五个，然后需要 500 步 [mystery_gift_menu.c:1367, wonder_news.c:21]。四个树果的奖励需要闭合的无线路径。

`--news`（`--news berry`、`--news-id N`）。消息顺序（约 18 秒）：

    ident 16  sClientScript_SendGameData
    ident 17  MysteryGiftLinkGameData
    ident 16  sClientScript_SaveNews
    ident 23  MG_LINKID_NEWS - 444 bytes in three blocks
    ident 19  MG_LINKID_RESPONSE - FALSE: the console saved it
    ident 16  sClientScript_NewsReceived
    ident 20  READY_END                              -> SVR_MSG_NEWS_SENT

## 作为密码关卡的问卷调查

`SVR_CHECK_QUESTIONNAIRE` 会比较四个友好商店问卷词语 [mystery_gift.c:422]；`mg_server.gate_on_questionnaire(script)` 将其拼接到游戏数据前缀之后：

    bin/frlg_mg_host.py --gift ... --questionnaire species:55,FEELINGS/60,move:177,why

一个词语可以是英文名称、`species:N`、`move:N`、`GROUP/INDEX` 或原始 ID。错误短语会收到主机的 64 字节消息（`CLIENT_SCRIPT_DYNAMIC_ERROR`），并且不会发送任何内容。每个会话都会从 GameData 记录主机的四个词语 [mystery_gift.c:361]：

    questionnaire: POKEMON/55  done [FEELINGS/60]  MOVE_1/177  why [MISC/37]

`EC_GROUP_POKEMON` 按宝可梦种类索引，`EC_GROUP_MOVE_1` 按招式 ID 索引；参见[法语易聊词汇表](frlg_rom_map.md#the-french-easy-chat-vocabulary)。

## 主机自愿提供的信息

GameData 携带 Easy Chat 个人资料和卡片统计信息 [mystery_gift.c:361]。`--game-data-log PATH`（`game_data_log.py`）会把每次会话追加到 JSONL 台账，并打印自该主机上次会话以来发生变化的内容；`tools/frlg/game_data_read.py PATH` 读取它。计数器只有在同一卡片标志 ID 上出现差异时才算证据。

## 保存备份与恢复

神秘卡片、朋友会话会把主机的整个 128 KiB 存档芯片复制到宿主机，或者把一个 `.sav` 写入其中并让游戏加载并保存它；不会发送任何卡片。`asm/save-backup.s` 和 `asm/save-restore.s` 移植自 GB-Link Team 的 `cards/savebackup.s` 和 `cards/saverestore.s`（GPL-3.0）；宿主机端为 `pokeldn.frlg.gift.save_transfer`（`--save-backup FILE`、`--save-restore FILE`），以及应用的“你的保存”标签页（[你的保存](gui.md#your-saves)）。两者都能在所有十二种卡带上运行（[保存备份与恢复](frlg_rom_map.md#save-backup-and-restore)）。

### 令牌编码

一个字节 `n < 0x80` 后面跟着 `n + 1` 个字面字节；`n >= 0x80` 后面跟着一个重复 `n - 0x80 + 3` 次的字节（行程长度 3 到 130，字面量最多 128）。

### 备份

客户端脚本在每个脚本中最多重复 `CLI_LOAD_TOSS_RESPONSE, CLI_RUN_BUFFER_SCRIPT, CLI_SEND_LOADED` 32 次。每一轮最多发送 1 KiB 的令牌，对应芯片最多 8 KiB，绝不跨越 64 KiB 存储体边界；芯片偏移量为 `client->param = 0x5A << 24 | offset` [mystery_gift_client.c:276]，不带 `0x5A` 的 `param` 从 `first` 开始。

| 载荷字 | 偏移 | 值 |
|---|---|---|
| `first` | `0x004` | 第一轮开始时所在的芯片偏移 |
| `send_queue` | `0x008` | `&gRfu.sendQueue.count` |

每一轮每帧把 `0x800` 字节暂存到 `gDecompressionBuffer + 0x800`，压缩到 `+ 0x400`，并设置 `link.sendBuffer`（`param + 0x3C`）和 `link.sendSize`（`param + 0x34`）。当 `gRfu.sendQueue.count` 不为零时它会等待。会话会在 `CLI_MSG_BUFFER_FAILURE` 时结束并给出消息，因此主机不会保存 [mystery_gift_menu.c:1379]。被中断的备份会按游戏代码和训练家 ID 续传。

### 恢复

1. 第一条消息是 620 字节的映像；`install` 将其复制到 `gDecompressionBuffer + 0x400`，并用 28 个槽位扇区的 12 字节页脚（id、校验和、签名、计数器位于 `+0xFF4`）应答。
2. 宿主机按 `GetSaveValidStatus` 的方式找到最新的完整槽位，把文件的副本写入另一个槽位，计数器设为 `newest + 1`，然后按文件内容写入扇区 28 到 31。
3. 它先擦除目标槽位的 id-0 扇区，最后写入新 id 0，这样在新存档完整之前，芯片自身的副本会继续加载。
4. 后续消息以 `b RESIDENT + 4`（`0xEA0000FF`）开头，然后是一个操作。`OP_DATA`（1）将扇区、写入标志、u16 偏移、u16 令牌长度和令牌传入 4 KiB 缓冲区；该扇区的最后一条消息用 `swi 0x48` 写入并验证，不匹配时设置失败掩码位。
5. `OP_FINISH`（2）在没有任何失败时调用 `LoadGameSave(SAVE_NORMAL)` [save.c:803]。在 `SAVE_STATUS_OK` 时，会话以 `CLI_MSG_BUFFER_SUCCESS` 结束，主机保存已加载的游戏；否则以 `CLI_MSG_BUFFER_FAILURE` 结束，旧存档保留。

| 载荷字 | 偏移 | 值 |
|---|---|---|
| `b install` | `0x000` | 第一条消息的入口 |
| `b entry` | `0x004` | 后续每条消息的入口，位于 `gDecompressionBuffer + 0x404` |
| `load_game_save` | `0x008` | `LoadGameSave \| 1` |

宿主机拒绝已加载副本不完整或布局不同的存档：日文版的 SaveBlock1 短 40 字节，可从训练家自己的宝可梦的语言字节（`+0x12`）读取。

`tests/test_save_transfer.py` 针对脚本化主机覆盖了备份、续传、恢复以及一次被中断的恢复。在实机上，备份在法语和英语火红上可用，恢复在英语火红上可用，包括一个法语存档。主机下一次保存与文件在扇区 1 到 7 上不同，这些扇区携带 `LoadGameSave` 重新生成的加密密钥。

## 制作礼物

`pokeldn.frlg.gift.gift_composer` 根据 `WonderGift` 定义构建卡片和发放脚本：

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

`WonderGift.delivery` 使用 `delivery`；`StampSlot.delivery` 和 `StampRallySpec.completion` 使用 `pre_stages` 和 `post_stages`。编译器从 `VAR_MYSTERY_GIFT_1` 继续阶段，并在成功时设置 `FLAG_MYSTERY_GIFT_DONE` 和领取标志；`GiftSpec(repeatable=True)` 会重置游标。

### 阶段与条件

每个 `DeliveryStage` 都是一个检查点；绝不要把两个可能失败的发奖操作（`GiveItem`、`GivePokemon`、`GiveEgg`）放在同一个阶段。携带招式的 `GiveEgg` 需要一个队伍空位。`GiveRandomEgg(eggs)` 通过跳转表挑选一个（十五个四招式蛋在 944 字节内即可容纳）。`condition=`（`VarEquals`、`FlagSet`、`Not`、`AllOf`、`AnyOf`）会跳过一个阶段，但仍推进游标；`RequireSpecialResult(...)` 在失败时停止且不推进。

```python
DeliveryStage(ShowSprite(142, RelativeToPlayer(dx=1)),
              condition=VarEquals(0x4031, 0))  # VAR_STARTER_MON == Bulbasaur
DeliveryStage(RequireSpecialResult(SPECIAL_HAS_ALL_KANTO_MONS, 1, "Finish the KANTO POKEDEX first."),
              GivePokemon(251, level=50))
```

`SetVar`（`setvar` 0x16）和 `AddVar`（`addvar` 0x17）接受保存变量 0x4000..0x40FF 和特殊变量 0x8000..0x8011。

### 战斗

`BattleLegendary` 会生成 `setwildbattle`、`special StartLegendaryBattle`、`end`，没有 `waitstate`（[RAM 脚本可能无法从战斗中返回](frlg_rng.md#a-ram-script-may-not-come-back-from-a-battle)）；`BattlePokemon` 会生成 `dowildbattle`。两者都会结束其阶段。在盖章槽路径中，战斗会被拒绝，除非作为有条件的终局替代项。

### 共享

`GiftSpec.shareable` 设置卡片的 `sendType`：`"never"`、`"once"`（接收者的副本变得不可共享）或 `"always"`。

### 命运邂逅标记

`GivePokemon(..., fateful_encounter=True)`（以及 `GiveEgg`）会生成 `setmonmodernfatefulencounter`（`0xCD`）和 `setmonmetlocation`（`0xD2`、0xFF）[data/mystery_event_msg.s:71]。第一条命令不检查索引边界 [scrcmd.c:2239]；索引是给予前的队伍数量，队伍已满时会跳转到失败标签。摘要行仅来自相遇地点 [pokemon_summary_screen.c:2665, 2799]；`modernFatefulEncounter` 是 Misc+0x08 的第 31 位 [include/pokemon.h:40-82]。

### 合成器中的 `initramscript`

`gift_composer.build_bound_script(actions)` 和 `build_mevent_npc_script(actions=...)` 将动作编译成 `initramscript` 绑定的场景脚本。它没有阶段游标，并且会整体重新运行，因此一次性效果需要自己的 `SetVar` 或条件。

### 注册与验证

```python
from pokeldn.frlg.gift.gift_registry import GIFT_REGISTRY
GIFT_REGISTRY.register_definition(MEWTWO_GIFT)
```

注册会进行验证和编译：卡片文本与标志、计划结构、动作范围、游标边界、唯一盖章、战斗位置、指针以及 995 字节 RAM 脚本限制，错误会指明路径（`example-rally.event.slots[1].delivery.post_stages[0].actions[1]: ...`）。

## 静态工具

```bash
./.venv/bin/python -m pokeldn.frlg.gift.gift_to_bin --gift beast-cutscene --flag-id 1005 --out-dir exported-gift
./.venv/bin/python -m pokeldn.frlg.save.save_inject game.sav --gift beast-cutscene --flag-id 1005
```

`gift_to_bin` 会为 `pokemon-gen3-mysterygift-tool` 写出一个 336 字节的 Wonder Card 和一个 1004 字节的 RAM 脚本。`save_inject` 将两者写入活动槽位，修复卡片、RAM 脚本和扇区校验和，并保存为 `<save>.gift.sav`（`--in-place` 会覆盖；`--make-artifact` 会在 `artifacts/` 下写出一份 `.ram.lst` 列表）。

## 已关闭的路径

### 无线通信（JoySpot）

无线路径在 RFU 序列号关口被阻断：

| | 朋友 | 无线通信 |
|---|---|---|
| 监听器 | `Task_ListenForCompatiblePartners` [union_room.c:3757] | `Task_ListenForWonderDistributor` [union_room.c:3799] |
| 接受 RFU 序列号 | `{0x0002, 0x7F7D}` | 仅 `== 0x7F7D` [link_rfu_3.c:920] |
| 选择 | 玩家从列表中选择 | 自动连接 |
| 可从 Switch 到达 | 是 | 否 |

`Task_CardOrNewsOverWireless` [union_room.c:2415] 仅当候选 0 的 `serialNo` 为 `0x7F7D` 时才保留它，然后检查生成状态、`hasCard` 位（失败时返回 SE_BOO）并重新连接。Switch 桥报告 `0x0002`，而广告没有序列号字段；`svc_47` [sloopsvc.c:34] 接收 24 字节且没有序列号。一个原生广告：

```
50 10 | c1 cc bf bf c8 ff 00 00 | 65 ac | 00 00 00 00 | 84 15 | 00 00 00 00 00 00
TID   | uname                   | parent| unexplained | search| unexplained
```

`record[16:18]` 处的搜索字是 `activity:7 | bit7 | version:3 | language:3 | hasCard?:1 | startedActivity:1`。

尝试过的广告变体（场景 id、应用版本、每个空闲偏移处的 `0x7F7D`、活动、`hasCard`、位 7）都没有从无线路径引出认证。未测试：`local_communication_id`、场景暴力破解、组合。

### e-Reader 本身

训练家之塔 e-Reader 套装使用 GBA 串行链接上的 `LINKTYPE_EREADER_FRLG`（`ereader_screen.c`），而非无线适配器。

### 极光船票与神秘船票

Switch 版本在第一次进入名人堂时授予两张船票及其 `FLAG_RECEIVED_*` 标志 [post_battle_event_funcs.c:52, `REVISION >= 0xA`]，所以在那之后船票卡片不会给出任何东西。卡片的 `iconSpecies` 如果不是 `SPECIES_NONE`，会绘制图标；超过 `SPECIES_UNOWN_B - 1` 时，会绘制问号 [mystery_gift_show_card.c:466, pokemon_icon.c:1102]。古老海图是绿宝石独占 [mystery_gift.c:30]。

## 陷阱

- `charmap.encode` 会丢弃未知字符，包括换行符。换行符是 0xFE；`mg_server` 拒绝第三行或宽度超过 31 个字符的行 [strings.c:1291]（窗口为 28 个图块乘 4，[mystery_gift_menu.c:97,524]）。
- 新负载会进入 `buffer_script.py` 中的 `DUMP_SCRIPTS` 和 `DECODED_SCRIPTS`，以及启动器的 `--dump-file` 行。

---
title: Ruby, Sapphire and Emerald
nav_order: 11
nav_exclude: true
search_exclude: true
---

# 红宝石／蓝宝石／绿宝石

红宝石／蓝宝石／绿宝石没有 Switch 版本；pokeldn 携带的支持是从
[pret/pokeemerald](https://github.com/pret/pokeemerald) 和 [pret/pokeruby](https://github.com/pret/pokeruby)
准备的，用于与火红／叶绿相同的 GBA 应用。这里没有任何内容在真机上测量，所有地址都是 GBA 英文构建版的地址。应用仅在从源码检出时显示标题
（[未发布标题](gui.md#unreleased-titles)）。

GBA 应用已经为全部五个第三代游戏代码保存了游玩报告表，其中包括 `AXV?`、
`AXP?` 和 `BPE?`（[主机上的代码](frlg_rom.md)），并且全部十二个火红／叶绿标题共用第一个本地通信 ID
`0x01006fa0233f8000`（[ROM 地图](frlg_rom_map.md)）。

## 各游戏可通过链接做什么

| | 红宝石／蓝宝石 | 绿宝石 |
|---|---|---|
| 无线适配器（RFU）代码 | 无：仅限 SIO 多人连接线 | 火红的 `link_rfu_2.c` |
| 连接交换 | 连接线 | 交流角和联盟房间，与火红相同 |
| 神秘礼物（神秘卡片、神秘新闻） | 无 | 火红的协议和结构体 |
| 神秘事件 | 通过连接线的 e-Reader，由“MYSTERY EVENT IS EXCITING”启用 | 标题菜单中无 |

启动器使用无线适配器协议通信，因此只能连接绿宝石。在链接之上，RS 连接线协议共享
`LinkPlayer` 记录、块大小 200、200、100、220 和 40、链接命令字以及交换块
[pokeruby link.c, trade.c]。RS 将 11 字节的名称写到火红和绿宝石作为进度标志读取的那些字节上，因此两者都会为 RS 伙伴将这些标志清零。

## 标识符

| 字段 | 红宝石 | 蓝宝石 | 绿宝石 |
|---|---|---|---|
| 游戏代码 | `AXV` + 语言 | `AXP` + 语言 | `BPE` + 语言 |
| 头部标题 | `POKEMON RUBY` | `POKEMON SAPP` | `POKEMON EMER` |
| `gGameVersion` | 2 | 1 | 3 |
| `LinkPlayer.version` | `0x4002` | `0x4001` | `0x4003` |

语言字母为 `E`、`F`、`D`、`I`、`S` 或 `J` [include/constants/global.h:8-12]。

## 加入主机

广播记录和 `RfuGameData` 与火红相同 [include/link_rfu.h:80-113]。绿宝石会将版本不是 3 的主机列为“未就绪”，除非玩家是冠军且该主机广播了 `canLinkNationally` [union_room.c:1266-1283; trade.c:2514-2521]。`--version emerald`（或 `ruby`、`sapphire`）广播该版本，并根据配置文件设置 `canLinkNationally`、`hasNationalDex` 和 `gameClear`（`[16:20]` 处字的第 16、17 和 24 位；`RfuGameData` 的第 7、8、9 位）。火红／叶绿保持这些位为 0。

## 连接交换

线路与火红相同（训练家卡上的神秘卡片 ID 位于 `0x60`），但有两处不同：

- 没有全国图鉴时，绿宝石会拒绝蛋或非丰缘物种，并在按下 A 后发送 `READY_CANCEL_TRADE` [trade.c:1585-1589]；`LinkPlayer.progressFlags & 0xF` 报告图鉴情况。`pokeldn.rse.constants` 保存了 202 个条目的丰缘图鉴，主机会记录被拒绝的提议。
- GBA 绿宝石在交换后运行五轮待机；Switch 火红运行六轮，最后一轮后跟 `svc_FinishSave`。`--save-rounds N` 设置该次数（默认 6）。

版本 3 的绿宝石会绘制主机的训练家卡，其中 `0x3A` 处为对战开拓区符号，`0x3C` 处为对战点数。它的接收队列有 32 个槽位（火红为 20），并且除了 `0x0002` 和 `0x7F7D` 外还接受序列号 `0x0000`。

## 神秘礼物

传输、脚本、332 字节的 `WonderCard`、444 字节的 `WonderNews` 和 `MysteryGiftSave`（`0x36C`）与火红相同。GameData 的 `+0x0C` 和 `+0x10` 对卡片携带 4 和 `0x200`，对新闻携带 5 和 `0x201`，而火红发送 1 及其版本代码 [mystery_gift.c:346-363]；绿宝石的检查要求卡片有第 2 位和 `0x380` [mystery_gift.c:390]。主机会应用主机游戏代码所对应游戏的规则。绿宝石的字段操作码仅在 `0xC7..0xCC`、`0xD0`、`0xD3..0xD5` 处不同，并延伸到 `0xE3`。

| | 火红／叶绿 | 绿宝石 |
|---|---|---|
| 卡片 flagId 1000（`sReceivedGiftFlags[0]`） | `0x2A7` | `0x13A` |
| `FLAG_MYSTERY_GIFT_DONE` | `0x3D8` | `0x1E4` |
| 礼物光标变量 | `0x40B6..0x40BC` | `0x40DE..0x40E4` |
| 最后道具 | 374 | 376（`ITEM_OLD_SEA_MAP`） |
| `StartLegendaryBattle` / `GetMysteryGiftCardStat` | 312 / 390 | 314 / 392 |
| `special` 索引检查 | 受 `gSpecialsEnd` 限制 [scrcmd.c:101] | 无：527 个 special [scrcmd.c:119] |
| SaveBlock1 中的 RamScript | `0x361C` | `0x3728` |

`gift_composer` 接受一个 `GameRules` 表；`pokeldn.rse.constants.EMERALD_RULES` 在绿宝石的编号下编译。主机会在发送前拒绝其他游戏的游戏机。绿宝石的神秘新闻没有奖励。

### 礼物

`pokeldn.rse.gifts` 用 pokeldn 的文本逐操作码重建了 pokeemerald 的四个官方礼物脚本（`tests/test_rse.py` 会比较字节码）。宝可梦中心 2F 的神秘礼物人会运行保存的脚本。

| 预设 | card flagId | 作用 |
|---|---|---|
| 极光船票 | 1000 | 船票及 `FLAG_ENABLE_SHIP_BIRTH_ISLAND` |
| 神秘船票 | 1001 | 船票及 `FLAG_ENABLE_SHIP_NAVEL_ROCK` |
| 古代海图 | 1002 | 海图及 `FLAG_ENABLE_SHIP_FARAWAY_ISLAND` |
| 变化洞窟传闻 | 1003 | 洞窟九张野生宝可梦表中的下一张 |
| 无限船票 | 1007 | 游戏自有的分发 [cable_club.inc:33]：船票和 `FLAG_ENABLE_SHIP_SOUTHERN_ISLAND` |
| 大师球、神奇糖果 ×5、冲浪皮丘的蛋 | 1004..1006 | 在 `EMERALD_RULES` 下组合 |

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --version emerald \
        --gift-file old-sea-map.pokegift --keys "$HOME/Documents/Switch/23.0.0 keys/prod.keys"

绿宝石礼物文件只有一个变体 `emerald`（[神秘礼物文件](gifts.md)）。原生代码、存档备份和火红预设对绿宝石会被拒绝。

## 存档

flash 布局、签名 `0x08012025` 和校验和与火红相同 [save.c]。SaveBlock1 为 `0x3D88` 字节，SaveBlock2 为 `0xF2C`。队伍数量 `0x234`，队伍 `0x238`，金钱 `0x490`（与 SaveBlock2 `+0xAC` 异或），标志 `0x1270`，变量 `0x139C`，游戏统计 `0x159C`，神秘礼物 `0x322C`。SaveBlock2 没有 `filler_B20`。

## pokeldn 缺少的绿宝石链接功能

记录混合、树果混合器、华丽大赛、对战塔连接多人对战、树果粉碎、宝可梦跳跃和嘟嘟利摘树果（链接组 12 至 21，活动 14 以及 23 至 29）。

## 未解决的问题

- Switch 版本是否存在，以及其标题 ID、游戏代码和软件版本。
- 是否保留火红应用的通信 ID、场景 ID 和广播打包。
- Switch 版本如何承载红宝石和蓝宝石的连接线链接。
- Switch 绿宝石交换后的待机轮数。
- Switch 绿宝石的每个 ROM 和 RAM 地址。
- 日版绿宝石神秘礼物活动和卡片大小。
- Switch 是否保留绿宝石的神秘礼物菜单门槛（`FLAG_SYS_MYSTERY_GIFT_ENABLE`，由“LINK TOGETHER WITH ALL”设置 [easy_chat.c:693]）。

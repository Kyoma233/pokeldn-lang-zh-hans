---
title: Emerald Mystery Gift
parent: Ruby, Sapphire and Emerald
nav_order: 2
nav_exclude: true
search_exclude: true
---

# 绿宝石神秘礼物

绿宝石的神秘礼物就是火红的神秘礼物（[神秘礼物](frlg_gift.md)），只是数字换成绿宝石的。启动器为
`bin/frlg_mg_host.py --version emerald`。

## 菜单闸门

标题菜单在设置了 `FLAG_SYS_MYSTERY_GIFT_ENABLE`（`0x8DB`）后才会列出 MYSTERY GIFT。宝可梦中心柜台的问卷在玩家持有图鉴后，会为 LINK TOGETHER WITH ALL 设置该标志
[questionnaire.inc:30-37; easy_chat.c:693]。之后路径为神秘礼物、神秘卡片、朋友。

## 协议

传输、脚本、332 字节的 `WonderCard`、444 字节的 `WonderNews` 以及 `MysteryGiftSave`（`0x36C`）
都与火红相同。GameData `+0x0C` 与 `+0x10` 对卡片携带 4 和 `0x200`，对新闻携带 5 和 `0x201`，
而火红发送的是 1 及其版本代码 [mystery_gift.c:346-363]；绿宝石的检查要求卡片具备位 2 与
`0x380` [mystery_gift.c:390]。主机按控制台游戏代码所命名的游戏规则应用。绿宝石的野外操作码仅在
`0xC7..0xCC`、`0xD0`、`0xD3..0xD5` 处不同，并延伸到 `0xE3`。

| | 火红／叶绿 | 绿宝石 |
|---|---|---|
| 卡片 flagId 1000（`sReceivedGiftFlags[0]`） | `0x2A7` | `0x13A` |
| `FLAG_MYSTERY_GIFT_DONE` | `0x3D8` | `0x1E4` |
| 礼物游标变量 | `0x40B6..0x40BC` | `0x40DE..0x40E4` |
| 最后道具 | 374 | 376（`ITEM_OLD_SEA_MAP`） |
| `StartLegendaryBattle`／`GetMysteryGiftCardStat` | 312／390 | 314／392 |
| `special` 索引检查 | 受 `gSpecialsEnd` 约束 [scrcmd.c:101] | 无：527 个 special [scrcmd.c:119] |
| SaveBlock1 中的 RamScript | `0x361C` | `0x3728` |

`gift_composer` 接受一张 `GameRules` 表；`pokeldn.rse.constants.EMERALD_RULES` 按绿宝石的数字编译。
主机在发送前会拒绝其他游戏的控制台。绿宝石的神秘新闻没有奖励。

在模拟控制台上，[Switch 构建](rse_switch_build.md) 会在朋友搜索中列出 POKELDN，将自身识别为未持有卡片的绿宝石，收下远海地图卡片并正常关闭 LDN；随后宝可梦中心 2 楼的配送员会按保存的脚本交出远海地图。

## 礼物

`pokeldn.rse.gifts` 用 pokeldn 的文本按操作码重建 pokeemerald 的四个官方礼物脚本
（`tests/test_rse.py` 比对字节码）。宝可梦中心 2 楼的神秘礼物员会运行保存的脚本。

| 预设 | 卡片 flagId | 作用 |
|---|---|---|
| Aurora Ticket | 1000 | 船票与 `FLAG_ENABLE_SHIP_BIRTH_ISLAND` |
| Mystic Ticket | 1001 | 船票与 `FLAG_ENABLE_SHIP_NAVEL_ROCK` |
| Old Sea Map | 1002 | 地图与 `FLAG_ENABLE_SHIP_FARAWAY_ISLAND` |
| Altering Cave rumor | 1003 | 洞穴九张野生表中的下一张 |
| Eon Ticket | 1007 | 游戏自身发放 [cable_club.inc:33]：船票与 `FLAG_ENABLE_SHIP_SOUTHERN_ISLAND` |
| Master Ball、Rare Candy x5、冲浪皮丘蛋 | 1004..1006 | 按 `EMERALD_RULES` 合成 |

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --version emerald \
        --gift-file old-sea-map.pokegift --keys "$HOME/Documents/Switch/23.0.0 keys/prod.keys"

预设可用 `pokeldn.gifts.save(PATH, pokeldn.rse.gift_builder.compile(PRESET[key].state))` 写成文件。
绿宝石礼物文件只有一个变体 `emerald`（[神秘礼物文件](gifts.md)）。原生代码、存档备份以及火红预设对绿宝石一律拒绝。

## 未解决

- 日文绿宝石神秘礼物活动与卡片大小。
- Switch 正式版是否保留菜单闸门。

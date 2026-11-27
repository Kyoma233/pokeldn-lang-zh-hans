---
title: Emerald Mystery Gift
parent: Ruby, Sapphire and Emerald
nav_order: 2
nav_exclude: true
search_exclude: true
---

# 绿宝石神秘礼物

绿宝石的神秘礼物是火红版的（[神秘礼物](frlg_gift.md)）套用绿宝石的数值。启动器为 `bin/frlg_mg_host.py --version emerald`。

## 菜单入口

标题菜单会在设置 `FLAG_SYS_MYSTERY_GIFT_ENABLE` (`0x8DB`) 后显示 MYSTERY GIFT。宝可梦商店柜台的问卷会在玩家持有图鉴后为“与所有人连接”设置该标志 [questionnaire.inc:30-37; easy_chat.c:693]。随后路径为 Mystery Gift、Wonder Cards、Friend。

## 协议

传输层、脚本、332 字节的 `WonderCard`、444 字节的 `WonderNews` 以及 `MysteryGiftSave` (`0x36C`) 均沿用火红版。`GameData +0x0C` 与 `+0x10` 对卡片分别填 4 和 `0x200`，对新闻填 5 和 `0x201`，而火红版发送 1 及其版本代码 [mystery_gift.c:346-363]；绿宝石的检查要求卡片的 bit 2 与 `0x380` [mystery_gift.c:390]。主机端按主机游戏代码所指明的游戏应用规则。绿宝石的字段操作码仅在 `0xC7..0xCC`、`0xD0`、`0xD3..0xD5` 处不同，并延伸至 `0xE3`。

| | 火红／叶绿 | 绿宝石 |
|---|---|---|
| card flagId 1000 (`sReceivedGiftFlags[0]`) | `0x2A7` | `0x13A` |
| `FLAG_MYSTERY_GIFT_DONE` | `0x3D8` | `0x1E4` |
| 礼物光标变量 | `0x40B6..0x40BC` | `0x40DE..0x40E4` |
| 最后一个道具 | 374 | 376 (`ITEM_OLD_SEA_MAP`) |
| `StartLegendaryBattle` / `GetMysteryGiftCardStat` | 312 / 390 | 314 / 392 |
| `special` 索引检查 | 受 `gSpecialsEnd` 限制 [scrcmd.c:101] | 无：527 个 special [scrcmd.c:119] |
| SaveBlock1 中的 RamScript | `0x361C` | `0x3728` |

`gift_composer` 接受一个 `GameRules` 表；`pokeldn.rse.constants.EMERALD_RULES` 在绿宝石的数值下编译。主机在发送前会拒绝非本游戏的主机。绿宝石的神秘新闻无奖励。

在模拟主机上，[Switch 版本](rse_switch_build.md)会在好友搜索中列出 POKELDN，识别为持有无卡片的绿宝石，接收 Old Sea Map 卡片并正常关闭 LDN；宝可梦中心 2F 的送货员随后会根据保存的脚本交付 OLD SEA MAP。

## 礼物

`pokeldn.rse.gifts` 逐条重建 pokeemerald 的四个官方礼物脚本，使用 pokeldn 的文本（`tests/test_rse.py` 对比字节码）。宝可梦中心 2F 的神秘礼物男子会运行保存的脚本。

| 预设 | 卡片 flagId | 功能 |
|---|---|---|
| 极光票 | 1000 | 该票与 `FLAG_ENABLE_SHIP_BIRTH_ISLAND` |
| 秘密票 | 1001 | 该票与 `FLAG_ENABLE_SHIP_NAVEL_ROCK` |
| 旧海图 | 1002 | 该图与 `FLAG_ENABLE_SHIP_FARAWAY_ISLAND` |
| 灵台票 | 1007 | 游戏自带的发放 [cable_club.inc:33]：该票与 `FLAG_ENABLE_SHIP_SOUTHERN_ISLAND` |
| 变化山洞传闻 | 1003 | 山洞的九张野生表中的下一张 |

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --version emerald \
        --gift-file old-sea-map.pokegift --keys "$HOME/Documents/Switch/23.0.0 keys/prod.keys"

其他预设为火红版提供的神秘卡片与活动宝可梦（[火红版的礼物](frlg_gift.md#cards-every-gba-title-shares)），在 `EMERALD_RULES` 下编译：`wonder_card_events.gba_cards(EMERALD_RULES)` 替入绿宝石的卡片统计 special（392）、`EnableNationalPokedex`（499）与 `FLAG_SYS_NATIONAL_DEX`（`0x896`）。

三张票的接收标志为 `sReceivedGiftFlags[0..2]` [mystery_gift.c:229]，灵台票发放读取 flagId 1007 的标志。合成卡片在首次对话时清除接收标志并在结束时设置，因此 `pokeldn.rse.gifts.composed` 拒绝 flagIds 1000、1001、1002 和 1007。

## 活动宝可梦

`--gift event-pokemon --event-pokemon NAME` 在绿宝石数值下发送火红版的活动卡片（[活动宝可梦](frlg_gift.md#event-pokemon)）。绿宝石的神秘事件 VM（`CLI_RUN_MEVENT_SCRIPT`）运行相同的 `givepokemon`，偏移量相对于接收缓冲区，因此单一 `emerald` 变体适用于所有绿宝石卡带。

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --version emerald \
        --gift event-pokemon --event-pokemon "WISHMKR Jirachi" --keys "$HOME/Documents/Switch/23.0.0 keys/prod.keys"

编译后的预设通过 `pokeldn.gifts.save(PATH, pokeldn.rse.gift_builder.compile(PRESET[key].state))` 成为文件；活动预设可用 `--export-gift PATH` 导出。绿宝石礼物文件仅有一个变体 `emerald`（[神秘礼物文件](gifts.md)），包含 `card`、`ram_script` 与可选的 `mevent`。原生代码、存档备份、神秘新闻、问卷及火红版的其他预设均被绿宝石拒绝。

## 待解决

- 日版绿宝石神秘礼物的活动与卡片大小。
- Switch 版本是否保留菜单入口。

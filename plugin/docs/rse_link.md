---
title: Trade and the Union Room
parent: Ruby, Sapphire and Emerald
nav_order: 1
nav_exclude: true
search_exclude: true
---

# 绿宝石交换与联盟房间

绿宝石的无线链路就是火红的（[连接](frlg_link.md)）；本页列出绿宝石不同之处。启动器为
`bin/frlg_trade_host.py` 与 `bin/frlg_trade_join.py`，并带 `--version emerald`。测量对照模拟控制台上的
[Switch 构建](rse_switch_build.md)。

## 加入主机

通告记录与 `RfuGameData` 与火红相同 [include/link_rfu.h:80-113]。绿宝石会把版本不是 3 的主机列为
“未准备好”，除非玩家是冠军且主机通告了 `canLinkNationally`
[union_room.c:1266-1283; trade.c:2514-2521]。`--version emerald`（或 `ruby`、`sapphire`）会通告该版本，
并根据档案设置 `canLinkNationally`、`hasNationalDex` 与 `gameClear`
（`[16:20]` 处字的第 16、17、24 位；`RfuGameData` 的位 7、8、9）。火红与叶绿保持这些位清零。

宝可梦中心 2 楼的每位接待员在设置 `FLAG_SYS_POKEDEX_GET`（`0x861`）之前都会回答“正在调整中”
[cable_club.inc:803, 885, 901, 1152]。

## 交换

线路与火红相同（训练家卡片神秘卡片 id 在 `0x60`），有两处差异：

- 没有全国图鉴时，绿宝石会拒绝来自伙伴的蛋或非丰缘种属
  [trade.c:1584-1589]：交换画面显示 “The other TRAINER's POKeMON can't be traded now”，按 A 后控制台发送
  `READY_CANCEL_TRADE`。`LinkPlayer.progressFlags & 0xF` 报告图鉴状态。`pokeldn.rse.constants.HOENN_DEX`
  保存 202 个条目，主机会记录被拒绝的报价。
- 绿宝石在交换后运行五轮待机 [trade.c:4686-4797]；Switch 火红运行六轮，最后一轮后跟
  `svc_FinishSave`。Switch 构建保留五轮：控制台发送 `READY_EXIT_STANDBY` 5 到 9，并在主机期待第六轮时停在
  “communication standby”。`--version emerald` 让主机跑五轮；`--save-rounds N` 可覆盖。

版本为 3 时，绿宝石会在 `0x3A` 绘制主机训练家卡片上的对战开拓区标记，在 `0x3C` 绘制对战点数。其接收队列有
32 个槽位（火红为 20），并在 `0x0002` 与 `0x7F7D` 之外还接受序列号 `0x0000`。

在模拟控制台上，Switch 构建能与主机完成一次交流角交换：LinkPlayer、训练家卡片、座位路线、队伍、邮件与缎带块、交换、五轮待机、`READY_CLOSE_LINK`、RFU 断开帧与 Pia 离开，然后将存档写入模拟器存储。

## 联盟房间

房间、活动菜单与交换板与火红相同（[联盟房间](frlg_link.md#the-union-room)）。
`--union-room --union-room-keepalive 120` 会生成 POKELDN 的形象，控制台玩家与其对话时连接。与 POKELDN
对话会显示 GREETINGS、BATTLE、CHAT 与 EXIT；绿宝石该菜单不提供交换。

| 活动 | 标志 | 在模拟控制台上测得 |
|---|---|---|
| GREETINGS | `--union-room` | 双方训练家卡片、待机屏障，回到房间 |
| EXIT | `--union-room` | `READY_CLOSE_LINK` 与正常断开 |
| 交换板 | `--union-room --board-type TYPE` | 控制台选取 POKELDN 的条目，宝可梦与邮件块交叉，交换与存档完成，链路关闭 |
| CHAT | `--union-room-chat` | 未运行 |
| BATTLE | `--union-room-battle` | 未运行 |

主机服务于控制台从 POKELDN 条目发起的板面交换；它不会向控制台自己的条目请求交换。`--board-type`
指定主机要求回报的类型，控制台只会提供该类型的宝可梦。

使用 `--union-room-keepalive 600` 时，双方训练家卡片块交叉后，控制台停在 “Communicating with POKELDN...”
且从不显示菜单；120 则到达菜单。

## 未解决

- Switch 绿宝石正式版的交换后待机轮数。
- 针对绿宝石的联盟房间聊天与对战。

---
title: Simulated Mystery Gifts
---

# 模拟神秘礼物

模拟神秘礼物通过本地无线将官方礼物宝可梦带给一款无法接收神秘礼物卡片的游戏：该游戏的交换主持人提供一份全新的合法副本，身份是收到该礼物的训练家；主机的玩家交换回一只宝可梦，该宝可梦进入接收盒。指定接收者的礼物会为主机自身的存档生成（[为接收玩家制作](#made-for-the-receiving-player)）。

| 游戏 | 工具 | 它所担任的交换主持 | 提供选项 |
|---|---|---|---|
| 去吧！皮卡丘／去吧！伊布 | `lgpe-gift-host` | Trade (Host), `bin/lgpe_host.py` | `--offer` |
| 晶灿钻石／明亮珍珠 | `bdsp-gift-host` | Trade (Host), `bin/bdsp_host.py` | `--offer` |
| 传说 阿尔宙斯 | `pla-gift-host` | Trade (Host), `bin/pla_host.py` | `--trade-box-record` |
| 朱／紫 | `sv-gift-host` | Trade (Host), `bin/sv_host.py`（[为主机托管](sv.md#hosting-for-a-console)） | `--trade-offer` |
| 传说 Z-A | `za-gift-host` | Trade (Host), `bin/za_host.py` | `--trade-offer` |

每个工具都是对应游戏的 Trade (Host)，按交换顺序最多可提供六只活动宝可梦（`catalog.simulated_gift`）；主持人在交换之间保持会话。

## 礼物

PKHeX.Core 内置了其合法性检查所知晓的全部分发，每个游戏一张表；不会下载任何内容。PKHeX 服务的 `gift_events` 列出表中的宝可梦卡片（蛋和道具卡被排除），按 `EncounterServerDate.GetDistributionWindow` 从新到旧排序，无日期卡片排在最后。PKHeX.Core 26.8.26 收录：

| 游戏 | 表 | 礼物宝可梦 | 开放日期 | HOME 的 | 你的初训家 |
|---|---|---:|---|---|---:|
| 去吧！皮卡丘／去吧！伊布 | `MGDB_G7GG` | 15 | 无日期，但 HOME 的美录坦（2025 年 2 月 11 日） | 美录坦 (9028) | 3 |
| 晶灿钻石／明亮珍珠 | `MGDB_G8B` | 9 | 2022 年 5 月 18 日至 2025 年 1 月 27 日，5 个无日期 | 草苗龟、小火焰猴、波加曼 (9015 至 9017)、玛纳霏 (9026) | 3 |
| 传说 阿尔宙斯 | `MGDB_G8A` | 11 | 2022 年 1 月 27 日至 2025 年 1 月 27 日 | 木木枭、火球鼠、水水獭 (9018 至 9020)、眷恋云 (9027) | 3 |
| 朱／紫 | `MGDB_G9` | 106 | 2022 年 11 月 17 日至 2026 年 6 月 5 日 | 新叶喵、呆火鳄、润水鸭 (9021 至 9023)、美洛耶塔 (9024)、烈咬陆鲨 (9035) | 29 |
| 传说 Z-A | `MGDB_G9A` | 8 | 2025 年 10 月 14 日至 2026 年 4 月 26 日 | 菊草叶、暖暖猪、小锯鳄 (9031 至 9033)、波尔凯尼恩 (9034) | 5 |

礼物的键是 `card-species-form`，在朱／紫中还要加上太晶属性（`0503-964-0-10` 是盖文的波普海豚）。朱／紫的卡片 1521 包含十八只梦幻，每种太晶属性一只。

工具会以 Settings 训练家接收礼物时的形态列出每个礼物（PKHeX 的 `ConvertToPKM`）：卡片固定初训家和语言时使用卡片的初训家和语言，否则使用你的初训家，并带有等级、太晶属性、异色、携带物品和开放日期（[神秘礼物 - 模拟](gui.md#mystery-gift---simulated)）。在 Settings 训练家语言下从未到达过对应存档的你的初训家卡片会被标记为不合法。

### 卡片到达过的存档

你的初训家副本会将接收存档的初训家设为其初训家，因此它必须是该卡片到达过的存档。`gift_event` 回复 `refused` 并带上原因，允许时为空（`services/pkhex/Program.cs`）：

- 语言：副本使用存档的语言。当卡片固定了其他语言时，由 PKHeX 的 `CanHaveLanguage` 决定（`InTrainerLanguage`）。
- 版本：在 `"only_version"` 条件下，卡片会拒绝它从未到达过的版本（`ReachedVersion`）。HOME 的卡片（编号 9000 及以上）到达过两个版本；其他固定了来源的卡片只到达过那个版本；否则由 `RestrictVersion`（去吧！皮卡丘／去吧！伊布的 `IRestrictVersion`）决定。

具有自己训练家的卡片永远不会被拒绝：它的副本是一只交换来的宝可梦。在 PKHeX.Core 26.8.26 中，唯一被拒绝的你的初训家卡片是去吧！皮卡丘／去吧！伊布的美录坦和美录梅塔（1501、1502），它们仅在简体中文中合法（`WB7.IsMainlandChinaGift`）。

### HOME 的礼物

PKHeX 的 HOME 卡片还原了 HOME 发放的内容：

| OT | 图库 | 卡片 | 为接收玩家制作 |
|---|---|---|---|
| HOME | “模拟 HOME” | 去吧！皮卡丘／去吧！伊布的美录坦 (9028)、玛纳霏 (9026)、眷恋云 (9027)、美洛耶塔 (9024)、波尔凯尼恩 (9034) | 否：按制作好的样子发放 |
| 接收训练家的 | “模拟（训练家）” | 草苗龟、小火焰猴、波加曼 (9015 至 9017)；木木枭、火球鼠、水水獭 (9018 至 9020) | 是 |
| 接收训练家的，带有处理者 | “模拟（训练家）” | 新叶喵、呆火鳄、润水鸭 (9021 至 9023)；菊草叶、暖暖猪、小锯鳄 (9031 至 9033) | 否：携带来自 Settings 的训练家 |
| PJCS26，日语 | “模拟 PJCS26” | 朱／紫的烈咬陆鲨 (9035) | 否：按制作好的样子发放 |

在去吧！皮卡丘／去吧！伊布之外，HOME 礼物带有 HOME 追踪器，由 [HOME 追踪器设置](gui.md#the-home-tracker-setting) 设置：在 `empty` 下为无（PKHeX 唯一会抱怨、但可接受的情况），在 `made` 下为已生成（Pokemon HOME 会拒绝）。每次回复都会为它命名（`home_tracker`）；列表会用琥珀色标出此类礼物，并且主持会继承该设置（`POKELDN_HOME_TRACKER`）。

两个 HOME 礼物需要在 `services/pkhex/Program.cs` 中进行修正：

- 去吧！皮卡丘／去吧！伊布的美录坦（9028）保留 HOME 的身高和体重（`WB7.IsHeightWeightFixed`、`ResetSizes`）。
- 传说 Z-A 的菊草叶、暖暖猪和小锯鳄（9031 至 9033）获得 HOME 的个体值：三项满值，其余为 20（`WA9.HomeBaseIV`、`SetHomeIVs`）。

## 交换提供的副本

`gift_event` 会为该游戏的每个版本为 Settings 训练家生成一个全新的副本，直到有一个合法为止。生成时不合法的副本会得到处理者 POKELDN。招式绝不会被重新调整，被拒绝的 PID 在每个版本上最多重新随机八次。主持会将副本作为交换提供再次检查；在卡片随机生成它们的地方，每次运行 New PID 都会给出新的 PID 和加密常数。每个礼物在任一 HOME 追踪器设置下都能通过（`tests/test_pokemon_service.py`）。

主机接收的内容包括：

- 在卡片固定训练家和语言时，使用卡片的训练家和语言；
- 否则如果开启 [为接收玩家制作](#made-for-the-receiving-player)，使用主机自身的存档作为训练家；关闭时则使用 Settings 训练家；
- 无论使用卡片的训练家还是 Settings 训练家，主机的玩家都会作为处理者。

## 为接收方玩家制作

`--for-receiver`（在应用中默认开启）会在交换过程中为主机自身的存档生成一个“你的 OT”礼物。自带初训家的礼物按原样发送。只有在带有处理者（`handled`：HOME 的 Sprigatito、Fuecoco、Quaxly、Chikorita、Tepig、Totodile）时才合法的礼物将使用设置中的训练家，因为收到自己 OT 的存档会清除处理者，随后 PKHeX 会拒绝它（[一次交换会改写什么](sv.md#what-a-trade-rewrites)）。应用将每个提供作为 `--gift-event KEY`（`command._args`）传递。

在启动时，服务端会在探测训练家 `receiver_gift.PROBE` 下向 `gift_event` 询问卡片，这会告知卡片是否命名其接收者（`your_ot`）并启动服务。五个服务端共享 `pokeldn.receiver_gift`，其 `ReceiverGift` 位于在线伙伴本应出现的位置（[在启动器中](online.md#in-a-launcher)）。

### 这是谁的存档

当提供的宝可梦由该存档捕获时，它会命名该存档：初训家（handler 0）、游戏的其中一个版本，且不是蛋。它给出 OT 名称、16 位 TID 和 SID、性别、语言和版本（`receiver_gift.own_trainer`），在工作者线程上读取（`Service.owner`；朱／紫为 Python 版，`receiver_gift.sv_owner`）。

| 游戏 | 你的 OT 卡片 | 主机的提供 | 版本 |
|---|---|---|---|
| 去吧！皮卡丘／去吧！伊布 | Meltan（1501）、Melmetal（1502），两者均仅适用于简体中文存档；Mew（2001） | kind 2 + 2r in trade r，一个加密的 232 字节 PB7 | 42 皮卡丘，43 伊布 |
| 晶灿钻石／明亮珍珠 | HOME 的 Turtwig、Chimchar、Piplup（9015 至 9017） | 0x13，一个加密的 328 字节 PB8 | 48 晶灿钻石，49 明亮珍珠 |
| 传说 阿尔宙斯 | HOME 的 Rowlet、Cyndaquil、Oshawott（9018 至 9020） | selector 4，一个加密的 376 字节 PA8 | 47 |
| 朱／紫 | 9 张卡片，其中包括 Mew（1521）和 Pikachu（1501） | `80 00 02 00` 的 348 字节主体（[交换消息携带的记录](sv.md#the-record-a-trade-message-carries)） | 50 朱，51 紫 |
| 传说 Z-A | Charizard（1607）、Ralts（1601） | 354 字节的 pick | 52 |

否则，主机会话会在任何宝可梦之前命名该存档（`receiver_gift.hear`）：

| 游戏 | 主机的消息 | 它命名的内容 |
|---|---|---|
| 去吧！皮卡丘／去吧！伊布 | kind 1，存档的 MyStatus 块（[Kind 1](lgpe_session.md#the-games-messages-on-the-reliable-protocol)，`pb7.first_trainer`） | id 对、版本、性别、语言、名称 |
| 晶灿钻石／明亮珍珠 | 0x24 `TradeTranerData`，当交换开始时（[宝可梦](bdsp_trade.md#the-pokemon)，`room.traner_trainer`） | id 对、版本、语言、名称 |
| 传说 阿尔宙斯 | 其 0x81 数据交换记录，存档的 MyStatus 块（[游戏的读取器](pla.md#the-games-reader-and-the-pre-handler-phase)，`data_exchange.read_trainer`） | id 对、版本、性别、语言、名称 |
| 朱／紫 | 其身份块的第 1 条记录，在其站点索引的 0x81 端口上（[记录](sv.md#the-records)，`sv_host.identity_chunk`，`reference.identity_trainer`） | id 对、版本、性别、语言、名称 |
| 传说 Z-A | 1400 身份（[游戏自身的交换](za.md#the-games-own-exchange)，`reference.identity_trainer`） | id 对、性别、语言、名称 |

晶灿钻石／明亮珍珠的会话从不命名性别（[模型](bdsp_protocol.md#the-model)）；提供的宝可梦会，无论是作为初训家，还是作为游戏写入每一只接收到的宝可梦的处理者（[主机对接收到的宝可梦做了什么](bdsp_trade.md#what-the-console-does-to-a-received-pokemon)）。会话缺失的字段会来自提供的宝可梦，当它的初训家（handler 0）或处理者（handler 1）与会话的名称和 id 对匹配时；否则来自设置。日志会列出每个这样的字段（`[gift] the console's Pokemon ... cannot name the save`）。传说 阿尔宙斯和传说 Z-A 只有一个版本。在后续交换中提供的已捕获宝可梦优先于会话，并且会重新制作副本。

`gift_event` 仅根据存档的版本制作卡片（`"only_version"`），并拒绝任何没有该版本存档收到过的卡片（[卡片到达的存档](#saves-a-card-reached)）。HOME 的 Turtwig、Chimchar 和 Piplup 属于晶灿钻石。

### 交换

交换以在线方式进行（[在线](online.md)）：

1. 主机首先提供。
2. 如果宝可梦和会话都没有命名该存档，则礼物会归入设置中的训练家；服务端会记录原因，并针对每个原因弹出一次弹窗（[弹窗](gui.md#pop-ups)）。
3. `gift_event` 为该存档制作卡片，然后在工作者线程上，副本通过服务端的提供检查（`pokemon.prepare_offer`，受 HOME tracker 设置影响）及其加载器。
4. 该副本在主机的提供之后发出，并持续到交换结束。
5. 服务端在主机确认后确认。

| 游戏 | 加载器 | 它检查的内容 |
|---|---|---|
| 去吧！皮卡丘／去吧！伊布 | `lgpe_host.boxed` | 一个加密的 232 字节盒子结构，其校验和与健全字有效 |
| 晶灿钻石／明亮珍珠 | `bdsp.pokemon.build_from` | 加密的 PB8 |
| 传说 阿尔宙斯 | 交换盒的 `box_offer` | 它的编辑，然后是 PKHeX 对加密记录的检查（`pokemon.validate`） |
| 朱／紫 | `trade.load_offer` | 交换消息携带的 348 字节主体 |
| 传说 Z-A | `za_host.gift_offer` | 一个可解密的 354 字节提供；礼物绝不会以坏蛋的形式发送 |

PKHeX 无法制作或未通过检查的副本会按应用制作的方式发送；日志（`[gift] could not be made ...`）和弹窗会指出存档和阶段（`receiver_gift.maker`）：

| 位置 | 原因内容 |
|---|---|
| 卡片 | 该存档不可能收到过该卡片：卡片 1502 仅以简体中文发放，从未发给英文存档 |
| PKHeX | PKHeX 从卡片……生成了非法的……：其检查的发现 |
| 提供检查 | 副本未通过服务端的提供检查：…… |
| 加载器 | 服务端无法发送该副本：…… |

朱／紫、传说 阿尔宙斯和传说 Z-A 每台主机保留一个 `ReceiverGift`；去吧！皮卡丘／去吧！伊布和晶灿钻石／明亮珍珠的服务端只连接一台主机。同一席位中的后续交换会在前一次完成后立即进行；最后一份礼物将服务于所有后续交换。

在所有五款游戏的零售版主机上，无论主机提供的是已捕获还是已交换的宝可梦，礼物都会以该存档自己的训练家身份到达。被交换回主机的礼物会以 handler 0 的身份到达，即存档自己的捕获（[一次交换会改写什么](sv.md#what-a-trade-rewrites)）。

## 其他游戏

火红／叶绿通过它们自己的神秘礼物接收活动宝可梦（[活动宝可梦](frlg_gift.md#event-pokemon)）。剑／盾通过本地无线接收真实卡片（[官方活动卡片](swsh_gift.md#official-event-cards)）。

---
title: Simulated Mystery Gifts
---

# 模拟神秘礼物

模拟神秘礼物将官方赠送宝可梦带入无需通过本地无线接收神秘礼物卡片的游戏中：游戏的交换主机以接收过礼物的训练家身份提供一份全新的合法副本，主机玩家则交换回一只宝可梦，该宝可梦会进入「已接收」。指定接收者的礼物会为主机自己的存档制作（[为接收玩家制作](#made-for-the-receiving-player)）。

| 游戏 | 工具 | 所作为的主机 | 赠送标志 |
|---|---|---|---|
| 去吧！皮卡丘／去吧！伊布 | `lgpe-gift-host` | 交换（主机），`bin/lgpe_host.py` | `--offer` |
| 晶灿钻石／明亮珍珠 | `bdsp-gift-host` | 交换（主机），`bin/bdsp_host.py` | `--offer` |
| 传说 阿尔宙斯 | `pla-gift-host` | 交换（主机），`bin/pla_host.py` | `--trade-box-record` |
| 朱／紫 | `sv-gift-host` | 交换（主机），`bin/sv_host.py` ([为主机托管](sv.md#hosting-for-a-console)) | `--trade-offer` |
| 传说 Z-A | `za-gift-host` | 交换（主机），`bin/za_host.py` | `--trade-offer` |

每个工具都是该游戏的「交换（主机）」，最多包含六只按交换顺序排列的活动宝可梦（`catalog.simulated_gift`）；主机在交换之间保持会话。

## 礼物

PKHeX.Core 内置其合法性检查已知的所有分发，每个游戏一张表；无需下载。PKHeX 服务的 `gift_events` 列出表中的宝可梦卡片（不含蛋卡和道具卡），按 `EncounterServerDate.GetDistributionWindow` 从新到旧排序，无日期的卡片排在最后。PKHeX.Core 26.10.18 包含：

| 游戏 | 表 | 礼物宝可梦 | 已开放 | HOME 的 | Your OT |
|---|---|---:|---|---|---:|
| 去吧！皮卡丘／去吧！伊布 | `MGDB_G7GG` | 15 | 无日期，但 HOME 的美录坦除外 (2025-02-11) | 美录坦 (9028) | 3 |
| 晶灿钻石／明亮珍珠 | `MGDB_G8B` | 9 | 2022-05-18 至 2025-01-27，5 个无日期 | 木守宫、火稚鸡、水跃鱼 (9015 到 9017)、玛纳霏 (9026) | 3 |
| 传说 阿尔宙斯 | `MGDB_G8A` | 11 | 2022-01-27 至 2025-01-27 | 木木枭、火球鼠、海獭 (9018 到 9020)、爱纽萝 (9027) | 3 |
| 朱／紫 | `MGDB_G9` | 106 | 2022-11-17 至 2026-06-05 | 尼亚奥哈、呆火鳄、夸夸誇 (9021 到 9023)、美洛耶塔 (9024)、烈咬陆鲨 (9035) | 29 |
| 传说 Z-A | `MGDB_G9A` | 9 | 2025-10-14 至 2026-08-28 | 菊草叶、火稚鸡、小锯鳄 (9031 到 9033)、波尔凯尼恩 (9034) | 5 |

礼物的键为 `card-species-form`，在朱／紫上额外加上太晶属性（`0503-964-0-10` 是伽文的超能海豚）。朱／紫的卡片 1521 包含十八只梦幻，每种太晶属性一只。

工具按设置训练家接收礼物的方式列出每个礼物（PKHeX 的 `ConvertToPKM`）：卡片固定的原训练家和语言，否则为 Your OT，附带等级、太晶属性、异色、携带道具和开启日期（[神秘礼物 - 模拟](gui.md#mystery-gift---simulated)）。从未以设置训练家语言进入存档的 Your OT 卡片会被标记为非法。

### 卡片到达的存档

Your OT 副本将接收存档作为其原训练家，因此必须是该卡片到达过的存档。`gift_event` 回复 `refused` 并附带原因，允许时为空（`services/pkhex/Program.cs`）：

- 语言：副本使用存档的语言。卡片固定其他语言时，由 PKHeX 的 `CanHaveLanguage` 决定（`InTrainerLanguage`）。
- 版本：在 `\"only_version\"` 下，卡片拒绝其从未到达的版本（`ReachedVersion`）。HOME 的卡片（9000 起）到达过任一版本；另一张固定产地的卡片仅到达该版本；否则由 `RestrictVersion`（去吧！皮卡丘／去吧！伊布的 `IRestrictVersion`）决定。

自带训练家的卡片永不被拒绝：其副本视为交换来的宝可梦。在 PKHeX.Core 26.10.18 中，唯一被拒绝的 Your OT 卡片是去吧！皮卡丘／去吧！伊布的美录坦和美录梅塔（1501、1502），仅在简体中文下合法（`WB7.IsMainlandChinaGift`）。

### HOME 的礼物

PKHeX 的 HOME 卡片重建 HOME 分发的内容：

| 原训练家 | 图库 | 卡片 | 为接收玩家制作 |
|---|---|---|---|
| HOME | "Simulated HOME" | 去吧！皮卡丘／去吧！伊布的美录坦 (9028)、玛纳霏 (9026)、爱纽萝 (9027)、美洛耶塔 (9024)、波尔凯尼恩 (9034) | 否：按原样赠送 |
| 接收训练家的 | "Simulated (Trainer)" | 木守宫、火稚鸡、水跃鱼 (9015 到 9017)；木木枭、火球鼠、海獭 (9018 到 9020) | 是 |
| 接收训练家的，带管理员 | "Simulated (Trainer)" | 尼亚奥哈、呆火鳄、夸夸誇 (9021 到 9023)；菊草叶、火稚鸡、小锯鳄 (9031 到 9033) | 否：随设置中的训练家赠送 |
| PJCS26，日文 | "Simulated PJCS26" | 朱／紫的烈咬陆鲨 (9035) | 否：按原样赠送 |

除去吧！皮卡丘／去吧！伊布外，HOME 礼物携带 HOME 追踪器，由 [HOME 追踪器设置](gui.md#the-home-tracker-setting)决定：`empty` 下为无（仅 PKHeX 报警，但被接受），`made` 下为已制作（宝可梦 HOME 会拒绝）。每个回复都会标注它（`home_tracker`）；列表以琥珀色勾勒此类礼物，主机继承该设置（`POKELDN_HOME_TRACKER`）。

两个 HOME 礼物需要在 `services/pkhex/Program.cs` 中修复：

- 去吧！皮卡丘／去吧！伊布的美录坦 (9028) 保留 HOME 的身高体重（`WB7.IsHeightWeightFixed`、`ResetSizes`）。
- 传说 Z-A 的菊草叶、火稚鸡、小锯鳄 (9031 到 9033) 获得 HOME 的个体值，三项完美其余为 20（`WA9.HomeBaseIV`、`SetHomeIVs`）。

## 交换提供的副本

`gift_event` 为设置训练家在游戏的每个版本上制作全新副本，直到某个合法。制作出的非法副本会获得管理员 POKELDN。招式从不重新适配，被拒绝的 PID 每版本最多重新生成八次。主机再次将副本作为赠送物检查；每次运行新 PID 会在卡片生成 PID 和加密常量的地方给出新的 PID 和加密常量。每个礼物在任一 HOME 追踪器设置下均能通过（`tests/test_pokemon_service.py`）。

主机接收：

- 卡片固定的原训练家和语言；
- 否则以主机自己的存档作为原训练家（[为接收玩家制作](#made-for-the-receiving-player)），或关闭该项时使用设置训练家；
- 无论卡片还是设置训练家，主机玩家均作为管理员。

## 为接收方制作

`--for-receiver`（应用中默认开启）会在交换过程中为主机自身的存档制作一份「你是 OT」的礼物。自带训练家的礼物按原样制作。仅凭处理者（`handled`：HOME 的尼亚奥哈、呆火鳄、夸克海豚、菊草叶、火稚鸡、小锯鳄）合法的礼物，会改用设置中的训练家，因为接收自己 OT 的存档会清除处理者，随后 PKHeX 会拒绝该数据（见[交换会重写什么](sv.md#what-a-trade-rewrites)）。应用将每份礼物作为 `--gift-event KEY`（`command._args`）传递。

启动时，主机向 `gift_event` 请求探针训练家 `for_receiver.PROBE` 下的卡片，以判断该卡片是否指定了接收方（`your_ot`），并启动服务。五个主机共享 `pokeldn.for_receiver`，其 `ReceiverGift` 处于在线伙伴的位置（见[在启动器中](online.md#in-a-launcher)）。同一个 `ReceiverGift` 还会制作一份交换提议，将玩家指定为原始训练家（见[原始训练家](gui.md#original-trainer)），并在礼物从卡片再次生成时重新训练该提议本身。

### 存档归属

当存档捕获宝可梦时，该宝可梦会标记存档归属：原始训练家（处理者 0）、游戏版本之一、非蛋。它提供 OT 名称、16 位 TID 与 SID、性别、语言和版本（`for_receiver.own_trainer`），在工作线程中读取（`Service.owner`；朱／紫在 Python 中，`for_receiver.sv_owner`）。

| 游戏 | 你是 OT 的卡片 | 主机的提议 | 版本 |
|---|---|---|---|
| 去吧！皮卡丘／去吧！伊布 | 超梦（1501）、超梦X（1502），仅限简体中文存档；梦幻（2001） | 种类 2 + 2r（交换 r），一个加密的 232 字节 PB7 | 42 皮卡丘，43 伊布 |
| 晶灿钻石／明亮珍珠 | HOME 的草苗龟、火球鼠、波加曼（9015 到 9017） | 0x13，一个加密的 328 字节 PB8 | 48 晶灿钻石，49 明亮珍珠 |
| 传说 阿尔宙斯 | HOME 的木木枭、火球鼠、水水獭（9018 到 9020） | 选择器 4，一个加密的 376 字节 PA8 | 47 |
| 朱／紫 | 9 张卡片，含梦幻（1521）和皮卡丘（1501） | `80 00 02 00` 的 348 字节正文（见[交换消息携带的记录](sv.md#the-record-a-trade-message-carries)） | 50 朱，51 紫 |
| 传说 Z-A | 喷火龙（1607）、拉鲁拉丝（1601） | 354 字节的 pick | 52 |

否则，主机会话会在任何宝可梦之前标记存档归属（`for_receiver.hear`）：

| 游戏 | 主机的消息 | 标记的内容 |
|---|---|---|
| 去吧！皮卡丘／去吧！伊布 | 种类 1，存档的 MyStatus 块（见[种类 1](lgpe_session.md#the-games-messages-on-the-reliable-protocol)，`pb7.first_trainer`) | ID 对、版本、性别、语言、名称 |
| 晶灿钻石／明亮珍珠 | 0x24 `TradeTranerData`，交换开始时（见[宝可梦](bdsp_trade.md#the-pokemon)，`room.traner_trainer`) | ID 对、版本、语言、名称 |
| 传说 阿尔宙斯 | 其 0x81 数据交换记录，存档的 MyStatus 块（见[游戏的读取器](pla.md#the-games-reader-and-the-pre-handler-phase)，`data_exchange.read_trainer`) | ID 对、版本、性别、语言、名称 |
| 朱／紫 | 身份块的记录 1，在其站点索引的 0x81 端口（见[记录](sv.md#the-records)，`sv_host.identity_chunk`、`reference.identity_trainer`) | ID 对、版本、性别、语言、名称 |
| 传说 Z-A | 1400 身份（见[游戏自身的交换](za.md#the-games-own-exchange)，`reference.identity_trainer`) | ID 对、性别、语言、名称 |

晶灿钻石／明亮珍珠的会话从不标记性别（见[模型](bdsp_protocol.md#the-model)）；提议的宝可梦会标记，作为原始训练家或作为游戏在每次接收宝可梦时写入的处理者（见[主机对接收宝可梦的处理](bdsp_trade.md#what-the-console-does-to-a-received-pokemon)）。会话缺失的字段，若提议宝可梦的原始训练家（处理者 0）或处理者（处理者 1）与会话的名称和 ID 对匹配，则取自该宝可梦；否则取自设置。日志会记录每个此类字段（`[gift] the console's Pokemon ... cannot name the save`）。传说 阿尔宙斯和传说 Z-A 只有一个版本。后续交换中提议的捕获宝可梦优先于会话，副本会被重新制作。

`gift_event` 仅在存档的版本上制作卡片（`"only_version"`），并拒绝无此类存档接收的卡片（见[卡片到达的存档](#saves-a-card-reached)）。HOME 的草苗龟、火球鼠、波加曼属于晶灿钻石。

### 交换

交换按在线模式运行（见[在线](online.md)）：

1. 主机先提议。
2. 若宝可梦和会话均未标记存档，礼物将使用设置中的训练家；主机记录原因并弹出提示（见[弹窗](gui.md#pop-ups)），每种原因仅提示一次。
3. `gift_event` 为存档制作卡片，随后在工作线程中，副本通过主机的提议检查（`pokemon.prepare_offer`，在 HOME 追踪设置下）及其加载器。
4. 副本在主机提议后上场，并保留至交换结束。
5. 主机在主机确认后确认。

| 游戏 | 加载器 | 检查内容 |
|---|---|---|
| 去吧！皮卡丘／去吧！伊布 | `lgpe_host.boxed` | 校验和与完整性字均有效的加密 232 字节箱子结构 |
| 晶灿钻石／明亮珍珠 | `bdsp.pokemon.build_from` | 加密的 PB8 |
| 传说 阿尔宙斯 | 交换箱子的 `box_offer` | 其编辑，随后 PKHeX 对加密记录的检查（`pokemon.validate`） |
| 朱／紫 | `trade.load_offer` | 交换消息携带的 348 字节正文 |
| 传说 Z-A | `za_host.gift_offer` | 可解密的 354 字节提议；礼物绝不作为坏蛋发送 |

PKHeX 无法制作或未通过检查的副本，将按应用制作的原样发送；日志（`[gift] could not be made ...`）和弹窗会标明存档和阶段（`for_receiver.maker`）：

| 位置 | 原因显示为 |
|---|---|
| 卡片 | 存档无法接收该卡片：卡片 1502 仅在简体中文下赠送，从未赠送给英文存档 |
| PKHeX | PKHeX 从卡片 ... 制作出非法 ...：其检查的发现 |
| 提议检查 | 副本未通过主机的提议检查：... |
| 加载器 | 主机无法发送副本：... |

朱／紫、传说 阿尔宙斯和传说 Z-A 每台主机保留一个 `ReceiverGift`；去吧！皮卡丘／去吧！伊布和晶灿钻石／明亮珍珠一台主机对应一台主机。同一席位的后续交换在前一次完成后立即制作；最后一份礼物服务于之后的所有交换。

在所有五款游戏的零售主机上，礼物均以存档自身的训练家身份到达，无论主机提议的是捕获还是交换来的宝可梦。交换回主机的礼物以处理者 0 到达，视为存档自身的捕获（见[交换会重写什么](sv.md#what-a-trade-rewrites))。

## 其他游戏

火红／叶绿通过自身的神秘礼物接收活动宝可梦（见[活动宝可梦](frlg_gift.md#event-pokemon)）。剑／盾通过本地无线接收真实卡片（见[官方活动卡片](swsh_gift.md#official-event-cards)）。

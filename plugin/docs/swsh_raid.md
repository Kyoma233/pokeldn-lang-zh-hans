---
title: Max Raid Battles
parent: Sword and Shield
nav_order: 5
---

# 极巨团体战

一条本地的极巨团体战是一场剑／盾会话，最多支持 4 个站点，位于 LDN 场景 60006。主机从一个洞穴中选择「邀请他人」打开；访客在 Y-Comm 列表中找到并点击主机名称选择「开始对战」。大厅使用可靠广播协议 0x80，战斗使用 0x7C。`bin/swsh_connect.py --preset raid` 让一个访客加入控制台大厅，准备并与选定的宝可梦（`--offer-file`）和招式（`--raid-move`）战斗；应用的「Max Raid（加入）」工具运行它。

## 网络

| 字段 | 值 |
|---|---|
| LDN 场景 ID | 60006（野外为 65535） |
| 参与者 | 1/4 于开启时 |
| 广告数据字节 `0x97` | `0x11` |
| Pia 会话最大值 | 4 (`0x0110e5e0`，从洞穴大厅处 `0x01031c74` 调用) |
| 广告 `0xb0` 和 `0xd4` | boss 和 den 记录（参见 [The den record](#the-den-record)） |

洞穴大厅的代码位于 `0x0102aba4..0x010370cc`（`View_NestHole`、`StateGuestReady`、`StateHostReady`）。访客的 Y-Comm 列表会排除广告中包含访客自身设备 ID 和账户 UID 的极巨团体战。

## 大厅消息

每条大厅消息的 ID 为 2000，对应 `net_contents.nesthole.protocol_buffers.NestholeAsyncDataHolder`（在 `main` 中的描述符 `0x1bfde43`、`0x20677b0`）。每个字段都是一个持有者，包含一个 `bytes` 字段 1。

| 字段 | 名称 | 大小 | 内容 |
|---|---|---|---|
| 1 | NestholeTimeLimit | 4 | u32 剩余秒数；主机每秒发送 3 次 |
| 2 | NestholePlayerInfo | 40 | 8 个零字节，u32（0x11 零售剑，0x12 模拟盾），13 个字符的 UTF-16 名称，`00 03` |
| 3 | NestholeBattleReady | 16 | 第 8 字节为 1 表示玩家已准备；第 12 字节为 1 表示战斗开始 |
| 4 | NestholeSelectPokemon | 352 | 8 个零字节，随后为选定宝可梦的加密 party PK8（0x158） |
| 5 | NestholeBattleStart | 32 | 参与者的 Pia 常量 ID 作为四个 u64，主机在前，未使用的槽位为零 |
| 6 | NestholeBossPokemon | 364 | 19 个零字节和 `ff`，随后为 boss 的加密 party PK8 |
| 7 | NestholeRewards | 120 | 十五对 u32：物品 ID、数量；未使用的对为零 |
| 8 | NestholeBattleSeed | 16 | u64 seed，随后为 `00 ff ff ff 1e 00 03 00` |

PlayerInfo 使用 4 KB 窗口的 zlib 压缩（标头 `48 4b`），可靠标志 0x10；其它字段原样发送。`pokeldn/swsh/raid.py` 构建所有字段。boss 记录携带完整的 boss；BattleSeed 提供的数据未被读取（对其应用 den 的极巨团体战生成器既不能得到 boss 的加密常量也不能得到其 PID）。

## 访客的流程

在 0x84 上进行快照交换（主机在前）；PlayerInfo、BattleReady 和 SelectPokemon 在端口 0 的 0x80 上发送；BattleReady 在准备就绪时设置第 8 字节。一旦所有玩家准备就绪，主机发送 BattleStart、SelectPokemon、BossPokemon、Rewards、BattleSeed 和 BattleReady（第 8 和第 12 字节均设为 1）；访客回复其 SelectPokemon 和相同的 BattleReady，战斗在 0x7C 开始（端口 0 上 ping 为 80，框架 40000 在端口 1，然后每个回合 10000 和 20000）。访客在 BattleReady（第 8 字节设为 1）后停止，会使零售剑主机卡在「Connexion en cours」，最终报错 2-ALZAA-0016。

## 战斗

主机运行战斗；访客在 0x7C 回复（`pokeldn/swsh/raid_battle.py`）。从 mesh 加入后，访客运行 SyncClockProtocol 0x1C（每秒一次请求）并发送一个 ClockProtocol 0x77 请求（`00` x16 然后 `00 6f`），两者均发往目标位图 1。

| 端口 | 消息 | 访客 |
|---|---|---|
| 0 | sync 80：ping、pingReply、pingSynced | 用 ping 回答 ping，用 pingReply 回答 pingReply，用 pingSynced 回答 pingSynced |
| 1 | 40000，content 0 的框架：字段 2 基准（10000 或 20000，0 时缺失），3 站点常量 ID，4 时钟，5 身体 | 在其 pingSynced 后发送三对基准-10000/基准-20000（身体 `00000000`、`000018fc`），然后镜像每个主机基准-20000身体在其自身站点 ID 下 |
| 0 | 10000，字段 3 {1 站点、2 槽位、3 版本} | 当主机列出自己的座位时发送（基准 0，16 字节身体：常量 ID、槽位、版本字节 0x6e） |
| 0 | 10000，字段 1 为空 | 在主机的基准-8 消息（24 字节身体，战斗的 seed）后发送 |
| 0 | 20000，字段 1 {1 发送者、2 槽位、3 计数器、4 数据} | 回答每个主机命令 |
| 0 | 20000，字段 3 {1 状态、2 槽位} | 在其动作前发送 {1: 2, 2: 槽位} |

主机命令的数据以四个 u16 开头：serial、type、length、tag。访客回复相同的 serial、type 和 tag，length 为 4，四个零字节，除了 type 0x02（状态消息，随后其动作：serial、0x02、0x58、tag、88 字节）和 type 0x21（结束：发送者 1，数据 `0000 1e00 0000 2f00`）。主机类型包括：0x01、0x0d、0x07、0x0e、0x02、0x10、0x09（回合日志，zlib）、0x04、0x11、0x0a、0x21。

### 哪个站点提供服务

服务器是每个控制台保留的 ServerVersion 记录获胜的站点。ServerVersion 是 `btl.net.protocol_buffers.BtlDataHolder`（id 10000）字段 3：站点 ID u64、客户端 ID u32、版本 u32（版本 `0x6e`）。八个 {站点、客户端 ID、版本、有效} 槽位位于战斗网络对象 `+0x190 + 16 * i`；`0x8b4030` 选择第一个有效槽位中版本最高的，`0x8b1990`（IsServer）比较其客户端 ID 与控制台自身。控制台的客户端 ID 是其在 BattleStart 中的位置（`0x1025120`）。提供服务的站点将槽位发布为 40000 框架对象 0 至 7。

### 动作

88 字节的动作是十一个 8 字节条目。条目 2 作为小端 u24 是 `move id << 13 | target << 8 | 0xc1`。

| 招式 | 条目 2 | 目标 |
|---|---|---|
| 磨牙 (1) | `c1 28 00` | 8 |
| 缠住 (20) | `c1 88 02` | 8 |
| 生气 (45) | `c1 a2 05` | 2 |
| 水枪 (55) | `c1 e8 06` | 8 |

生气击中所有敌方并携带目标 2；单目标招式携带 8。访客无法行动的回合会发送条目 2 为零。`raid_battle.action(move, target)` 构建它；`--raid-move N` 选择招式槽位。0x7C 确认携带 32 个槽位；只有槽位 0 跟踪访客的流，因此基于最大槽位的重发从不重发。

## den 记录

den 主机的广告描述其极巨团体战；访客的 Y-Comm 条目构建器（`0x00fa1560`）读取它。

| 偏移 | 内容 |
|---|---|
| `0x5F` 位 1 | 主机版本：清除 Sword，设置 Shield |
| `0xAF` | 活动类型：等级 0 时为 `0x11`，等级 1 以上为 `0x13 + 2 (rank - 1)`；`0xFF` 永远不列出 |
| `0xB0` | 显示的 boss：u16 种属（位 0 至 9）和形态（位 10 至 15），一个字节其第 4 和第 5 位为 1 正常，2 超极巨化，u32 加密常量 |
| `0xD4` | den 记录，相同的八字节布局 |
| `0xDC` | 高半字节：星级排名，0 至 4 |
| `0xDD` | 位 3 至 5：den 类型，0 为普通 den |
| `0xDE`、`0xE0` | u16 遇见表，计入主机版本的表中，u16 槽位 |
| `0xE6` 至 `0xED` | `bin/archive/field/resident/data_table.gfpak` 中文件 8、6、7、9 的 CRC16 |

当 `0xD4` 处的种属非零时，访客仅在其自身的表 CRC 匹配、den 类型为 0、主机版本的表 `0xDE` 槽位 `0xE0` 包含该种属、形态和超极巨化标志（`0x00ea5160`）时才列出极巨团体战。种属为 0 时跳过这些检查。排名不能超过访客自身的排名（来自徽章数量），当 `0x02510b2c` 处的字节为 1 或 2 且主机不是好友时。`0xB0` 处的记录仅进行范围检查。访客会丢弃设备 ID 和账户 UID（`0x1F` 至 `0x3E`）同时等于自身的站点（`0x0111b160`）。`pokeldn/swsh/data/nest_slots.json` 保存 1.3.2 的槽位（`scripts/gen_swsh_nest_data.py`）；`raid.den_advert` 将 den 记录指向包含 boss 的槽位，或将其清零。

### boss 记录

访客在发送已开始的 BattleReady 之前检查 BossPokemon 和 Rewards（`0x01030d14`）；检查失败会导致 2-ALZAA-0016。

| 检查 | 代码 | 通过条件 |
|---|---|---|
| boss | `0x01032270` | 种属、形态和 party `+0x156`（1 正常，2 超极巨化）等于 den 记录命名的条目：类型 0 为基础表 `0xDE`，广告版本的槽位 `0xE0`；类型 1 至 3 为访客自身保存的事件遇见，槽位 `0xE0`；类型 4 为其保存的水晶遇见 |
| rewards | `0x01032570` | 每对带有物品和数量的都是槽位奖励表在广告排名下恰好其数量的奖励行，或是 drop 表中物品以该排名有概率（数量自由） |

等级、招式、IV、PID、能力、异色和训练师字段不进行比较。零 den 记录命名类型 0，表 0，槽位 0（Tyrogue）。在零售剑访客上观察到：带有训练师数据的 boss 记录、party 极巨化类型为 0，或是零 den 记录用于 boss 基础 den 不持有的 boss（Mew、事件的超极巨化 Toxtricity）会导致 2-ALZAA-0016，尽管极巨团体战已被列出；仅更改种属的 den boss 记录和由 `raid.boss_record` 构建的 boss 会被接受。基础 den 不持有任何传说或神话宝可梦，因此主办的 boss 是 `nest_slots.json` 列出的种属、形态和超极巨化状态；`raid.den_advert` 在仅另一方持有 boss 时切换广告版本，并将事件 boss 显示为持有其种属的基础 den 槽位。`bin/swsh_host.py` 和应用的极巨团体战主持工具会拒绝基础 den 不持有的头目。

`raid.boss_record` 保留 den 头目的 TID 28222 和 SID 36500。异色判定是 PID 对上这两个 ID，因此 `raid.same_shine` 会移动 PID 的高半部分，以保留头目文件中相对其训练家的方形、星形或普通异色；若把头目改成玩家异色却原样发送 PID，则会抽成普通色。`raid.reward_choices` 列出槽位在某个排名下允许的内容；`raid.den_rewards` 构建槽位自己的行。

在 den boss 中，party HP 统计和当前 HP 是普通 HP 统计乘以 `(150 + 5 * Dynamax 等级) / 100`，向下取整；其他统计为普通值。Dynamax 等级位于 `+0x90`，能力槽位比特位于 `+0x16` 位 0 至 2，经验值是等级的最低位。

## Hosting

`bin/swsh_host.py --raid-boss PK8 --raid-console-serves` 主持一个宝可梦盾版.den 房间，由控制台从其 Y-Comm 列表加入 (`pokeldn/swsh/raid_host.py`)。广告和快照是模拟的盾版.den 主机的，带有全新的站点配置文件、团体名称和无账户 ID (`pokeldn/swsh/data/raid_advert.bin`, `raid_snapshot.bin`; `--advert` 和 `--snapshot` 替换它们)。`--raid-boss` 接受任意 PK8 并传入 `raid.boss_record`。主机的快照在客机之前发出。`--raid-reward ITEM:COUNT` 填充 Rewards，`--raid-seed` 填充 BattleSeed；主机拒绝广告.den 插槽在其等级下不提供的行，并打印该插槽提供的内容。

该应用的 Max Raid (Host) 工具使用这些标志配合一个 boss（或基础.den 所持的 Wild Area Event boss，`raid_event.hostable`），玩家的宝可梦和最多 15 个奖励行；若无行，则主机提供.den 插槽自己的奖励。其奖励编辑器仅提供 boss 所广告.den 插槽的物品 (`raid.boss_den`, `pokeldn.app.raid_rewards.swsh_den`)，并固定 bonus 物品的数量。

使用 `--raid-console-serves` 时，加入的控制台承担战斗，主机作为客户端 1 应答 (`raid_battle.Master`)：

| step | the host |
|---|---|
| BattleStart | lists the console first, so the console's client id is 0 |
| 0x7C port 0 | sends ping; answers the console's ping and pingSynced |
| framework objects | publishes object 0 = the console's ServerVersion record, object 1 = its own |
| 0x7C port 0 | sends its own ServerVersion (client id 1) |
| base 20000 | publishes the counter and its own body, 0000 / 00000100, then 0100 / 01000100, 01000200, 0200 / 02000200, each once the console mirrors the last body |
| object 8 | the console publish it (24 bytes, a seed); the host answers EmptyCommand (10000 field 1) |
| battle commands | answered as a guest answers them, the action naming the host's Pokemon's first move |

一位零售剑版通过这种方式完成了整个团体战，赢得了胜利并收到了主机的 Rewards，然后发送了 mesh 离开请求。

我们自己的记录以版本 `0x6d` 发出，低于控制台的 `0x6e`，因此控制台的记录是无论每个插槽最终落在哪里，唯一一个最高版本的记录。在 LAN 模式下，零售剑版将 session 主机的记录存入插槽 0（主机的 Pia 站点索引），因此在版本相同时，它选择了我们的主机，发布了我们的记录作为 object 0，发送了 EmptyCommand 并在黑屏上等待一个从未开始的服务器；在 `0x6d` 时，它承担了战斗并加载了画面。

### Several consoles

最多三台控制台共享一个主持的房间 (`raid_host.RaidParty`)。主机在所有加入的控制台准备就绪后开始战斗；BattleStart 按加入顺序列出控制台，然后是主机。第一台控制台承担战斗。主机发布 framework object k 作为第 k 台控制台的 ServerVersion 记录及其自己的最后一条记录，并在每台控制台镜像其 body 后推进 base-20000 屏障。

第二台控制台需要从 Pia 主机处获取：发送给它的 session 更新（在 loopback 上每个站点都有自己的副本）；mesh 加入响应字节 8，active station 最大值，超过已坐下的站点（否则返回结果 1 和错误 2618-0502）；以及发送者 stream 端口上的 ack（主机为 0，第一位加入者为 1，第二位为 2），因为未被确认的 stream 会无休止重复。

客机之间直接连接：站点连接请求、彼此的快照在 0x84 上，以及 0x80 上的 lobby 消息，分别发给主机和另一位客机。

## Event raids

Wild Area Event 是一次 BCAT 递送，包含.den 遭遇和奖励表，每次递送有一个编号索引。Project Pokemon 的 EventsGallery 将每个事件保存在 `Released/Gen 8/SwSh/Wild Area Events/Index NNN/` 下。`pokeldn/swsh/raid_event.py` 读取其中一个；`pokeldn.app.events_gallery` 在游戏 `swsh` 下保留一份副本。

| file | content |
|---|---|
| `normal_encount` | the Wild Area dens' event encounters |
| `normal_encount_rigel1`, `normal_encount_rigel2` | the Isle of Armor's and the Crown Tundra's (in Index 080 and 117, not in 010) |
| `drop_rewards`, `bonus_rewards` | the delivery's reward tables |
| `dai_encount` | the Dynamax crystal encounters [pkNX `NestHoleCrystalEncounterArchive`]; unread |

每个文件以 0x20 字节的 header 开头：0 偏移处为 u8 BCAT 索引；4 偏移处为 `ff ff ff ff`；8 偏移处为 u32 `0x20`；`0x10` 偏移处为 u32 文件大小减 4。FlatBuffer 从 `0x20` 运行到末尾前四个字节，后者保存 CRC [pkNX `GameDumperSWSH.GetDistributionContents`]。

遭遇文件是一组表的向量（字段 0）：TableID u64，GameVersion u32（1 Sword，2 Shield）和 Entries（字段 4）。Entry 字段：0 索引；1、2、3 种属、形态、等级；4 Dynamax 等级；11 能力（0、1、2 第一、第二、隐藏；3 第一或第二个；4 任意）；12 Gigantamax；13、14 drop 和 bonus 表 ID（u64）；15 五个 rank 概率（百分比，每 version 各 rank 总和为 100）；16 性别（0 随机，否则性别 + 1）；17 完美 IV 数量；18 shiny（0 随机，1 从不，2 总是）；21 性格（25 随机）；23 至 26 四个招式；30 shield 和 31 至 36 两个额外招式，按 PyNXBot 的 schema。

其他字段未被读取。Index 010 解码为 Wild Area Event #7：rank 3 至 5 的 Gigantamax Toxtricity，各 rank 的 Gigantamax Milcery，剑版的 Kingler 和 Grimmsnarl，盾版的 Orbeetle 和 Hatterene；其 rank-5 Toxtricity 等于 PKHeX 的 `encounter_sw_dist.pkl` 中 index 10 的记录。

递送奖励文件是一组表的向量（字段 0）：TableID u64 和 Entries（字段 1），每个 entry 包含五个 u8 值代表 rank 1 至 5（字段 0 至 4）和一个 u16 物品（字段 5）。游戏自己的表，`data_table.gfpak` 文件 7（drops）和 6（bonus），保存 TableID，随后是 u32 entry 索引、u32 物品和 u32 五个值的向量 (`pokeldn/swsh/data/nest_rewards.json`, `scripts/gen_swsh_nest_data.py`)。遭遇通过 id 命名其表，在两者之间，游戏的第一个 [pkNX `NestHoleDistributionEncounterTable`]。bonus 值为数量，drop 值为概率。1-star.den 的 Rewards (`raid.DEN_REWARDS`) 以 rank 1 的 bonus 表 `0xf966212316b78eb6` 的行作为开头，按数量（Exp. Candy XS x5，S x1，Dynamax Candy x1），然后是两个物品，各一个。`raid_event.rewards` 构建 bonus 行，然后每 drop 一行，滚动每个 drop 的概率或保留全部。

`raid_event.boss_pk8` 在 `raid.boss_record` 上构建 boss：表中的种属、形态、等级、招式、Gigantamax 和 Dynamax 等级，以及表允许的能力、IVs、性格、性别和 PID，party 统计来自 `pokeldn/swsh/data/species.json` (`scripts/gen_swsh_species_data.py`)。

    bin/swsh_host.py --raid-event "FOLDER/Index 010" --raid-stars 5 --raid-event-boss 4 --raid-console-serves

若不带 `--raid-stars` 或 `--raid-event-boss`，主机会列出它需要的内容。`--raid-version` 选择表的版本（默认为广告的版本），`--raid-area` 选择.den 区域，`--raid-event-drops all` 选择所有 drop；`--raid-reward` 行替换 event 的奖励。

## 极巨大冒险

一次极巨大冒险（Max Lair，二进制文件中称为 `chika`）通过本地通信匹配，当每个玩家都选择在 Max Lair 邀请他人时：第一个玩家打开网络，其他玩家扫描并连接。Y-Comm 永远不会列出它：主机广告活动类型为 0xFF。该网络使用本地通信 id `0x0100abf008968000`，场景 50000，最大节点数 4（Pia 最大值从 `0x00bd9b30` 调用，在 `ChikaMatchingState*` `0x00bd1978..0x00bda158` 中）。主机从 3:00 开始倒计时，显示为“通讯中”；如果没有客人加入，则取消冒险。冒险开始后，电脑伙伴填充空位。

在可靠端口 0 的 0x80 端口上运行两个消息持有者，每个字段都是一个持有一个字段 1 的持有者：

- id 7000，`net_contents.chika.protocol_buffers.ChikaAsyncDataHolder`（描述符 `0x1c3adb5`，`0x2066654`），为大厅；
- id 8000，`net_contents.underground.protocol_buffers.UndergroundAsyncDataHolder`（描述符 `0x1c36fab`，`0x20681cc`），用于战斗之间。

发送到 Max Lair 大厅的 Den 消息（id 2000）会被确认但无法入座。战斗运行在 0x7C 端口上，与 Den 团体战相同，但有两个区别：

- 操作为条目 1 `01 ff ff ff ff ff ff ff`，条目 2 为移动，与 Den 团体战中的移动相同，其他九个条目为 `0xff`；条目 2 的第 3 字节在极巨回合中为 `0x80`，并且在此之前的状态消息则携带状态 1 而非 2；
- 在客人宝可梦昏厥后，主机发送类型 0x04，数据为 `01 00 ff ff ff ff`；客人回复一个 88 字节的操作，其中条目 2 为零。

`pokeldn/swsh/lair.py` 是两个持有者的客人端；`bin/swsh_connect.py --preset lair`（应用程序的极巨大冒险（加入））作为玩家 1 入座，并选择主机留下的第一个可用位置（租借宝可梦按顺序排列，主机的租借宝可梦在第一位）。由 `lair.rental_pk8` 构建的租借宝可梦是记录租借宝可梦的记录，包含该行的种类、形态、等级 65 和招式、四个 IV 为 31，其他随机，随机性格、能力槽 1 或 2、性别、PID 和加密常量；OT 为 Scientist，精灵球，等级 65 时遇到，队伍统计无极巨加成。一位零售剑主机接受了它。

### 大厅持有者，id 7000

以玩家名字命名的记录以其 Pia 常量 id（u64）和玩家索引字节开头；电脑伙伴具有零 id 和索引 2 和 3。

| 字段 | 名称 | 大小 | 内容 |
|---|---|---|---|
| 1 | ChikaTimeLimit | uint32 | 剩余秒数，来自主机 |
| 2 | ChikaPlayerInfo | 48 | 12 个零字节，13 个字符的 UTF-16 名称，然后 `02 00 00 00 00 2d 00 00 00`；zlib 压缩（可靠标志 0x10） |
| 3 | ChikaBattleReady | 16 | 第 8 字节为 1 表示玩家已准备；第 12 字节为 1 表示冒险已开始 |
| 4 | ChikaSelectPokemon | 360 | 8 个零字节，u32 租借宝可梦在共享报价中的位置，加密队伍 PK8 形式的租借宝可梦，4 个零字节 |
| 5 | ChikaBattleStart | 32 | 人类玩家的常量 id，客人的第一个 |
| 8 | ChikaBattleSeed | uint64 | 来自主机；为租借报价和遭遇播种（参见[冒险种子](#the-adventure-seed)） |
| 9 | ChikaRentalPokemonSeed | uint64 | 来自主机，在租借选择之前 |
| 11 | ChikaPlayerNumber | 40 | 四个常量 id（主机、客人、零、零），然后玩家索引 `00 01 02 03` |
| 12 | ChikaBigBoss | 16 | 第 12 字节为 1；每个玩家发送自己的 PlayerInfo |
| 13 | ChikaBigBossFixed | 4 | u32 冒险传说宝可梦的种类 |

字段 6、7 和 10 不发送。顺序：加入时每个玩家发送 PlayerInfo、BattleReady 和 BigBoss；BattleReady 带有第 8 字节置位；来自主机的 BattleStart、BattleSeed、RentalPokemonSeed、PlayerNumber、BattleReady 带有第 12 字节置位和 BigBossFixed；然后是每个玩家的 SelectPokemon。

### 冒险持有者，id 8000

| 字段 | 名称 | 大小 | 内容 |
|---|---|---|---|
| 1 | UndergroundWaySelect | 16 | 常量 id、玩家索引、选择的路径 |
| 3 | UndergroundWayResult | 1 | 所选路径，来自主机 |
| 4 | UndergroundTradeWant | 16 | 常量 id、玩家索引、1 表示交换为捕获的宝可梦 |
| 6 | UndergroundTradeResult | 360 | 交换玩家的常量 id、索引、两个字节、然后加密队伍 PK8 形式的新宝可梦在 +11 |
| 10 | UndergroundRaidCapture | 16 | 常量 id、玩家索引、第 9 字节 |
| 11 | UndergroundRaidWant | 16 | 常量 id、玩家索引、1 表示获取捕获的宝可梦 |
| 12 | UndergroundRaidResult | 360 | 8 个零字节、获取玩家的索引（无则为 `ff`）、一个字节、然后加密队伍 PK8 形式的宝可梦在 +10 |
| 14 | UndergroundTimeLimit | 8 | u32 剩余秒数、u32 阶段，来自主机，每秒发送三次 |

字段 2、5、7、8、9 和 13 不发送。每个客人发送自己的 WaySelect、TradeWant、RaidCapture 和 RaidWant；主机回复自己的以及每个电脑伙伴的，然后是结果。

### 主持一次冒险

`bin/swsh_host.py --lair-legendary SPECIES [--lair-seed N]`（`pokeldn/swsh/lair_host.py`）从模拟的盾主机广告（场景 50000）开始，像连接交换一样交换快照，然后发送大厅：PlayerInfo、BattleReady 和 BigBoss，时间限制每秒发送三次，准备就绪；一旦客人准备就绪，发送 BattleStart、BattleSeed、RentalPokemonSeed 和 PlayerNumber；一旦客人确认开始，发送 BattleReady（已开始）和 BigBossFixed。5 秒后，它像主机离开那样离开（参见[离开](swsh_session.md#leaving)）：MIGRATION_START `44 00 01`，带有其主机迁移字节的更新会话，START_HOST_MIGRATION 每 0.33 秒一次，一旦控制台离开或 10 秒后关闭网络。

应用程序的极巨大冒险（主持）工具运行以下标志：传说宝可梦、可选的链接代码和种子。它的种子选择器显示 `lair.adventure` 为该种子提供的三个租借宝可梦和十个遭遇，绘制一个新种子，并搜索具有特定租借宝可梦的种子（约 1/75 的种子提供给定的租借宝可梦）。地图末尾的传说宝可梦是 BigBossFixed 命名的种类；客人的 BigBoss 全为零。租借宝可梦按顺序选择，主机的租借宝可梦在第一位，离开的玩家座位由电脑伙伴接替。

Max Lair 链接代码在接待员处设置。广告携带代码十进制值的 CRC32，前导零省略（`7777` 对应 0000 7777）；使用不同代码或无代码的搜索永远不会列出大厅。带代码时，主机在未发送 MIGRATION_START 的情况下关闭网络，客人会在租借屏幕上收到错误 2618-0006；而有了移交，客人在 MIGRATION_START 后 0.1 秒内离开，其冒险继续进行。

### 冒险种子

冒险的宝可梦是 RomFS `bin/appli/chika/data_table/underground_exploration_poke.bin` 中的行，一个包含 273 行的 FlatBuffer：226 个租借宝可梦和遭遇在等级 65，随后 47 个传说宝可梦在等级 70（Boss 标志已设置）。每行包含种类、形态、等级和四个招式。

ChikaBattleSeed 决定六个租借宝可梦报价和遭遇；`lair.adventure(seed)` 计算它们。Xoroshiro128+ 用 u64 和 `0x82A2B175229D6A5B` 播种。每次选择用下一个 32 位输出播种 MT19937，洗牌 273 个行索引（索引 i 与 i 加上 0 到 272 - i 的抽取交换，掩码为 `0x1ff`，超过则重新抽取），并取第一个不是传说也未被选中的行。四次选择，然后在接下来的两次选择前各抽取一次 0 到 2，还有一次更多，每次当多于 2、1 和 0 个电脑伙伴就座时；然后抽取 0 到 2 和 0 到 9，接着十次遭遇选择，每次当该行有两种类型时再抽取一次输出。有三个电脑伙伴时，首先抽取一次 0 到 27。

租借屏幕显示报价位置 0 到 2。每个座位按顺序选择，主机的租借宝可梦在第一位，所取的位置用下一个未使用的位置（3、然后 4、然后 5）填充。电脑伙伴在玩家之后选择，从不通过网络：每个电脑伙伴取其 0 到 2 抽取所对应的屏幕位置，第一个电脑伙伴取第一个抽取。`lair.partner_places(seed, taken)` 计算它；它在三次记录的冒险中命名两个伙伴的租借宝可梦（一次模拟主机和客人，一次我们的客人对模拟主机，一次对零售剑主机），这些记录从主机的类型 0x10 命令中读取每个战斗位置使用的招式。该规则仅需要 ChikaBattleSeed。哪些遭遇在一条路径上相遇尚不清楚。

作为零售剑主机的客人，`swsh_connect.py --preset lair` 遵循了三次遭遇和传说宝可梦（Raikou）的所有路径和捕获选择，其租借宝可梦在每次战斗中使用其第一个招式；主机的玩家输掉了最后一场战斗，整个会话结束时没有错误。

## 离开

一旦玩家离开奖励屏幕，零售剑主机通过每 0.33 秒发送 START_HOST_MIGRATION 10 秒，像连接交换后离开那样（参见[离开](swsh_session.md#leaving)）。不离开的客人会让主机的玩家在野外冻结直到超时；`--leave-with-host` 在第一次时离开。

### 中途离开

在本地 Den 团体战中离开的站点不会结束其他人的战斗。战斗的离开服务（由 `0x8b7830` 构建，保存在 btl-net `+0x3b8`）在处理程序 `0x8c4570` 中收听 Pia 会话的站点离开事件（`0x6b4850`，类型 1）。在本地 Den 团体战中（设置 `+4` = 2，`+0x3b8` = 1，由 `0x7e7c50` 在 `nn::pia::local` 模式中设置），它保持座位连接 30 秒（`0x7530`），然后移除站点（`0x8c3f70`，`0x8b4140`）并重新运行服务器选择；服务控制台将座位的备用客户端（`main+0x1c0 + 8 * i`，`0x8dfcb0`）放入其中（`0x7f8450`）。丢失的会话（类型 3）通过 `0x10f8e30` 提升错误（2,4）。

在模拟盾 1.3.2 上测量，战斗中途杀死进程且未发送任何内容：

| 控制板 | 控制台所做的 |
|---|---|
| 控制台的 Den 大厅中的客人 | 战斗继续进行，没有错误；下回合的菜单出现 |
| 主机，控制台在服务中（`--raid-console-serves`） | 战斗暂停约一分钟，然后继续进行，没有错误；Boss 在下回合受到伤害 |

在零售剑主机上通过 ESP32 控制板，战斗 10 秒后杀死进程，两种角色都得到相同的结果：没有错误，战斗继续进行。

一次干净的移交（战斗 5 秒后 MIGRATION_START，然后关闭网络）会让控制台在 0x18 端口 0 上回复 `48 01`，0.1 秒后离开网络并显示 2618-0006，之后其战斗离线继续进行。主机在战斗开始前离开会让控制台停留在“Connexion en cours”（参见[客人的顺序](#the-guests-sequence)）。

## 未解决

- 是否非 Pia 主机的控制台会发布框架对象 0 到 7。
- 备用客户端为已离开玩家的座位选择什么。
- 一局托管大厅中有多个控制台在零售硬件上；仅在模拟盾上测量。
- PlayerInfo 的 u32 和末尾字节的含义。
- 操作的其他十个条目、极巨化和目标代码 8 和 2 之外的内容。原样重放一条记录的水枪操作会让任何客人宝可梦使用水枪，甚至在零售剑主机上也一样。
- 极巨大冒险：三个电脑伙伴时的伙伴顺序；一个电脑伙伴在租借屏幕上接替离开的主机时，`partner_places` 给出的是位置 2，但它拿到了位置 1。
- 极巨大冒险：PlayerInfo 的末尾字节、BigBoss、RaidCapture 中玩家索引后的字节和结果记录，以及两个持有者的未发送字段。
- 零售客人是否会从 Den 广告中获取事件 Boss（Den 记录为零），以及零售事件 Den 主机在 Den 类型位和 Den 记录中写入什么。

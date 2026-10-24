---
title: Max Raid Battles
parent: Sword and Shield
nav_order: 5
---

# 极巨团体战

本地极巨团体战是一场剑／盾会话，最多四台主机，使用 LDN 场景 60006。主机从巢穴以“邀请其他人”开启；访客在其 Y-Comm 列表中找到它，并在主机名字上选择“开始对战”加入。大厅使用可靠广播协议 0x80，战斗使用 0x7C。`bin/swsh_connect.py --preset raid` 会在主机的大厅中占一个访客席位，准备并用所选宝可梦（`--offer-file`）和招式（`--raid-move`）战斗；应用的“极巨团体战（加入）”工具会运行它。

## 网络

| 字段 | 值 |
|---|---|
| LDN 场景 ID | 60006（旷野地带为 65535） |
| 参与者 | 开启时为 4 人中的 1 人 |
| 广播数据字节 `0x97` | `0x11` |
| Pia 会话上限 | 4（`0x0110e5e0`，从巢穴大厅 `0x01031c74` 调用） |
| 广播 `0xb0` 和 `0xd4` | 头目和巢穴记录（[巢穴记录](#the-den-record)） |

巢穴大厅的代码位于 `0x0102aba4..0x010370cc`（`View_NestHole`、`StateGuestReady`、`StateHostReady`）。访客的 Y-Comm 列表会排除广播中带有该访客自身设备 ID 和账户 UID 的极巨团体战。

## 大厅消息

每条大厅消息的 id 都是 2000，`net_contents.nesthole.protocol_buffers.NestholeAsyncDataHolder`（描述符 `0x1bfde43`、`0x20677b0` 位于 `main` 中）。每个字段是一个带有一个 `bytes` 字段 1 的 holder。

| 字段 | 名称 | 大小 | 内容 |
|---|---|---|---|
| 1 | NestholeTimeLimit | 4 | u32 剩余秒数；主机每秒发送三次 |
| 2 | NestholePlayerInfo | 40 | 8 个零字节、u32（零售版剑为 0x11，模拟版盾为 0x12）、13 个字符的 UTF-16 名称、`00 03` |
| 3 | NestholeBattleReady | 16 | 玩家按下准备后字节 8 为 1；战斗开始后字节 12 为 1 |
| 4 | NestholeSelectPokemon | 352 | 8 个零字节，然后是所选宝可梦的加密队伍 PK8（0x158） |
| 5 | NestholeBattleStart | 32 | 参与者的 Pia 常量 ID 作为四个 u64，主机的排第一，未使用槽位为零 |
| 6 | NestholeBossPokemon | 364 | 19 个零字节和 `ff`，然后是作为加密队伍 PK8 的头目 |
| 7 | NestholeRewards | 120 | 十五对 u32：道具 ID、数量；未使用对为零 |
| 8 | NestholeBattleSeed | 16 | u64 种子，然后 `00 ff ff ff 1e 00 03 00` |

PlayerInfo 以 zlib 压缩、4 KB 窗口（头 `48 4b`）在可靠标志 0x10 下发出；其他消息以明文发出。`pokeldn/swsh/raid.py` 构建每个字段。头目记录包含完整头目；BattleSeed 馈入的内容未被读取（对其应用巢穴的极巨团体战生成器既得不到头目的加密常量，也得不到其 PID）。

## 访客的流程

快照交换在 0x84 上进行（主机先发送）；PlayerInfo、BattleReady 和 SelectPokemon 在 0x80 端口 0 上进行；准备就绪时发送字节 8 置位的 BattleReady。一旦所有玩家准备就绪，主机会发送 BattleStart、SelectPokemon、BossPokemon、Rewards、BattleSeed 以及字节 8 和 12 均置位的 BattleReady；访客以自己的 SelectPokemon 和相同的 BattleReady 回应，然后战斗在 0x7C 上开始（端口 0 上 ping 80，端口 1 上框架 40000，随后每回合 10000 和 20000）。在发送字节 8 置位的 BattleReady 后停止的访客会让零售版剑主机停留在“Connexion en cours”，最终报错 2-ALZAA-0016。

## 战斗

战斗由主机运行；访客在 0x7C 上回应（`pokeldn/swsh/raid_battle.py`）。从 mesh 加入后，访客运行 SyncClockProtocol 0x1C（每秒一个请求）并发送一个 ClockProtocol 0x77 请求（`00` x16 然后 `00 6f`），两者都发往目标位图 1。

| 端口 | 消息 | 访客 |
|---|---|---|
| 0 | 同步 80：ping、pingReply、pingSynced | 以 ping 和 pingReply 回应 ping，以 pingSynced 回应 pingSynced |
| 1 | 40000，content 0 的框架：字段 2 base（10000 或 20000，0 时不存在）、3 主机常量 ID、4 时钟、5 消息体 | 在其 pingSynced 后发送三个 base-10000 / base-20000 对（消息体 `00000000`、`000018fc`），然后以自己的主机 ID 镜像每个主机 base-20000 消息体 |
| 0 | 10000，字段 3 {1 主机、2 槽位、3 版本} | 一旦主机列出自己的座位后发送（base 0，16 字节消息体：常量 ID、槽位、版本字节 0x6e） |
| 0 | 10000，字段 1 空 | 在主机 base-8 消息后发送（24 字节消息体，战斗的种子） |
| 0 | 20000，字段 1 {1 发送者、2 槽位、3 计数器、4 数据} | 回应每条主机命令 |
| 0 | 20000，字段 3 {1 状态、2 槽位} | 在动作前发送 {1: 2, 2: 槽位} |

主机命令的数据以四个 u16 开头：序列号、类型、长度、一个标记。访客以相同的序列号、类型和标记回应，长度 4 和四个零字节，除了类型 0x02（状态消息，然后是它的动作：序列号、0x02、0x58、标记、88 字节）和类型 0x21（结束：发送者 1，数据 `0000 1e00 0000 2f00`）。观察到的主机类型：0x01、0x0d、0x07、0x0e、0x02、0x10、0x09（该回合的日志，zlib）、0x04、0x11、0x0a、0x21。

### 哪台主机作为服务器

服务器是其 ServerVersion 记录在各主机维护的表中胜出的那台主机。ServerVersion 是 `btl.net.protocol_buffers.BtlDataHolder`（id 10000）字段 3：主机 ID u64、客户端 ID u32、版本 u32（版本 `0x6e`）。八个 {主机、客户端 ID、版本、有效} 槽位位于战斗网络对象 `+0x190 + 16 * i`；`0x8b4030` 选择具有最高版本的第一个有效槽位，`0x8b1990`（IsServer）将其客户端 ID 与主机自身的客户端 ID 比较。主机的客户端 ID 是它在 BattleStart 中的位置（`0x1025120`）。进行收集的主机将这些槽位作为 40000 框架对象 0 到 7 发布。

### 动作

88 字节的动作是十一个 8 字节条目。条目 2 作为小端 u24 为 `move id << 13 | target << 8 | 0xc1`。

| 招式 | entry 2 | 目标 |
|---|---|---|
| 拍击（1） | `c1 28 00` | 8 |
| 绑紧（20） | `c1 88 02` | 8 |
| 叫声（45） | `c1 a2 05` | 2 |
| 水枪（55） | `c1 e8 06` | 8 |

叫声命中所有对手并携带目标 2；单体招式携带 8。访客无法行动的回合会将条目 2 设为零。`raid_battle.action(move, target)` 构建它；`--raid-move N` 选择招式槽位。0x7C 确认携带 32 个槽位；只有槽位 0 跟踪访客的流，因此以所有槽位最大值作为条件的重发永远不会触发。

## 巢穴记录

巢穴主机的广播描述其极巨团体战；访客的 Y-Comm 条目构建器（`0x00fa1560`）读取它。

| 偏移 | 内容 |
|---|---|
| `0x5F` 位 1 | 主机版本：清零为剑，置位为盾 |
| `0xAF` | 活动类型：0 级时为 `0x11`，更高级为 `0x13 + 2 (rank - 1)`；`0xFF` 永远不会列出 |
| `0xB0` | 显示的头目：u16 物种（位 0 到 9）和形态（10 到 15）、一个字节（位 4 和 5 为 1 普通，2 超极巨化）、u32 加密常量 |
| `0xD4` | 巢穴记录，同样的 8 字节布局 |
| `0xDC` | 高半字节：星数等级，0 到 4 |
| `0xDD` | 位 3 到 5：巢穴类型，0 表示普通巢穴 |
| `0xDE`、`0xE0` | u16 遇敌表（按主机版本的表计数）和 u16 槽位 |
| `0xE6` 到 `0xED` | `bin/archive/field/resident/data_table.gfpak` 中文件 8、6、7 和 9 的 CRC16 |

当 `0xD4` 处的物种非零时，访客只有在自身表 CRC 匹配、巢穴类型为 0，并且主机版本表 `0xDE` 槽位 `0xE0` 中具有该物种、形态和超极巨化标志（`0x00ea5160`）时才会列出该极巨团体战。物种为 0 会跳过这些检查。当 `0x02510b2c` 处的字节为 1 或 2 且主机不是好友时，等级不得超过访客自身由徽章数决定的等级。`0xB0` 处的记录仅做范围检查。访客会忽略设备 ID 和账户 UID（`0x1F` 到 `0x3E`）都与自身（`0x0111b160`）相同的主机。`pokeldn/swsh/data/nest_slots.json` 保存 1.3.2 槽位（`scripts/gen_swsh_nest_data.py`）；`raid.den_advert` 将巢穴记录指向包含头目的槽位，或将其清零。

### 头目记录

访客在发送其已开始的 BattleReady 之前检查 BossPokemon 和 Rewards（`0x01030d14`）；检查失败会以 2-ALZAA-0016 离开。

| 检查 | 代码 | 通过条件 |
|---|---|---|
| 头目 | `0x01032270` | 物种、形态和队伍 `+0x156`（1 普通，2 超极巨化）等于巢穴记录所指定的条目：类型 0 为所广播版本的基础表 `0xDE` 槽位 `0xE0`；类型 1 到 3 为访客自己保存的事件遇敌记录，槽位 `0xE0`；类型 4 为其保存的结晶遇敌记录 |
| 奖励 | `0x01032570` | 每个带有道具和数量的对都必须是指定等级下该槽位奖励表中恰好为该数量的奖励行，或者是该等级有概率掉落的掉落表道具（数量不限） |

等级、招式、个体值、PID、特性、异色和训练家字段不会被比较。零巢穴记录表示类型 0、表 0、槽位 0（无畏小子）。在零售版剑访客上观察到：带训练家数据的头目记录、队伍极巨化类型为 0，或为基础巢穴中不存在的头目（梦幻、活动中的超极巨化颤弦蝾螈）使用零巢穴记录，虽然极巨团体战会被列出，但会以 2-ALZAA-0016 离开；只改了物种的巢穴头目记录，以及由 `raid.boss_record` 构建的头目，则会被接受。基础巢穴中没有传说或幻之宝可梦，因此主持的头目是 `nest_slots.json` 中列出的物种、形态和超极巨化状态；`raid.den_advert` 会在只有另一个版本持有该头目时切换广播版本，并将活动头目显示为基础巢穴中持有该物种的槽位。`raid.reward_choices` 列出某等级下槽位允许的内容；`raid.den_rewards` 构建槽位自身的行。

在巢穴头目中，队伍 HP 能力值和当前 HP 是普通 HP 能力值乘以 `(150 + 5 * Dynamax level) / 100`，向下取整；其他能力值为普通值。极巨化等级位于 `+0x90`，特性槽位在 `+0x16` 的位 0 到 2，经验值为该等级的最小值。

## 托管

`bin/swsh_host.py --raid-boss PK8 --raid-console-serves` 托管一个巢穴大厅，游戏机从其
Y-Comm 列表加入（`pokeldn/swsh/raid_host.py`）。广告和快照是一个模拟的盾版巢穴
主机的，带有全新站点资料、公告板名称且无账号 ID
（`pokeldn/swsh/data/raid_advert.bin`、`raid_snapshot.bin`；`--advert` 和 `--snapshot` 可替换
它们）。`--raid-boss` 通过 `raid.boss_record` 接受任意 PK8。主机的快照在客人的快照之前发出。
`--raid-reward ITEM:COUNT` 填充奖励，`--raid-seed` 填充 BattleSeed；如果广告的巢穴槽位在该等级
不提供某行，主机会拒绝该行并打印该槽位实际提供的内容。

应用程序的极巨团体战（主机）工具使用这些标志，配合一个头目（或基础巢穴持有的旷野地带活动头目，
`raid_event.hostable`）、玩家的宝可梦以及最多 15 行奖励；没有行时，主机会给予巢穴槽位自身的奖励。
其奖励编辑器只提供头目被广告来源的巢穴槽位的物品（`raid.boss_den`、
`pokeldn.app.raid_rewards.swsh_den`），并固定奖励物品的数量。

使用 `--raid-console-serves` 时，加入的游戏机主持对战，主机作为客户端 1 应答
（`raid_battle.Master`）：

| step | the host |
|---|---|
| BattleStart | 先列出游戏机，所以游戏机的客户端 ID 为 0 |
| 0x7C port 0 | 发送 ping；应答游戏机的 ping 和 pingSynced |
| framework objects | 发布对象 0 = 游戏机的 ServerVersion 记录，对象 1 = 自己的记录 |
| 0x7C port 0 | 发送自己的 ServerVersion（客户端 ID 1） |
| base 20000 | 发布计数器和自己的身体，0000 / 00000100，然后 0100 / 01000100、01000200、0200 / 02000200，每次在游戏机镜像了上一个身体后发送 |
| object 8 | 游戏机发布它（24 字节，一个种子）；主机应答 EmptyCommand（10000 字段 1） |
| battle commands | 像客人一样应答，动作命名为主机的宝可梦的第一个招式 |

一台零售版《剑》以这种方式主持了一整场极巨团体战，获胜并收到了主机的奖励，然后发送了
网状网络离开请求。

### 多台游戏机

最多三台游戏机共享一个托管大厅（`raid_host.RaidParty`）。每台加入的游戏机就绪后，主机开始
对战；BattleStart 按加入顺序列出游戏机，然后是主机。第一台游戏机主持。主机将框架对象 k
发布为游戏机 k 的 ServerVersion 记录，自己的记录最后发布，并在每台游戏机镜像其身体后推进
base-20000 屏障。

第二台游戏机需要从 Pia 主机获得：传递给它的会话更新（在回环上每个站点获取自己的副本）；
mesh 加入响应字节 8，即活动站点上限，要高于已经入座的站点（否则结果 1 和错误
2618-0502）；以及在发送方流的端口上的确认（主机 0、第一个加入者 1、第二个加入者 2），
因为未确认的流会无限重复。

客人们直接相互连接：站点连接请求、在 0x84 上相互的快照，以及在 0x80 上发给主机和
另一个客人的大厅消息。

## 活动极巨团体战

旷野地带活动是一次 BCAT 分发，包含巢穴遭遇和奖励表，每次分发有一个编号索引。Project
Pokemon 的 EventsGallery 将每个活动保存在
`Released/Gen 8/SwSh/Wild Area Events/Index NNN/` 下。`pokeldn/swsh/raid_event.py` 读取其中一个；
`pokeldn.app.events_gallery` 在 game `swsh` 下保存一份副本。

| file | content |
|---|---|
| `normal_encount` | 旷野地带各巢穴的活动遭遇 |
| `normal_encount_rigel1`, `normal_encount_rigel2` | 铠岛和王冠雪原的（在索引 080 和 117 中，不在 010 中） |
| `drop_rewards`, `bonus_rewards` | 分发的奖励表 |
| `dai_encount` | 极巨化水晶遭遇 [pkNX `NestHoleCrystalEncounterArchive`]；未读取 |

每个文件以 0x20 字节的头部开始：偏移 0 处是 u8 BCAT 索引，偏移 4 处是 `ff ff ff ff`，偏移 8 处
是 u32 `0x20`，偏移 `0x10` 处是 u32 文件大小减 4。FlatBuffer 从 `0x20` 一直延伸到文件末尾前四个
字节，那里保存着 CRC [pkNX `GameDumperSWSH.GetDistributionContents`]。

遭遇文件是表的向量（字段 0）：TableID u64、GameVersion u32（1 为剑，2 为盾）和 Entries
（字段 4）。条目字段：0 索引；1、2、3 为物种、形态、等级；4 为极巨化等级；11 为特性
（0、1、2 分别为第一、第二、隐藏特性；3 为前两种之一；4 为任意）；12 为超极巨化；13、14 为
掉落和奖励表 ID（u64）；15 为五个等级的概率百分比（每个版本每个等级总和为 100）；16 为性别
（0 为随机，否则为性别 + 1）；17 为完美个体值数量；18 为异色（0 为随机，1 为从不，2 为必定）；
21 为性格（25 为随机）；23 到 26 为四个招式；30 为护盾，31 到 36 为两个额外招式，按
PyNXBot 的模式。

其他字段未读取。索引 010 解码为旷野地带活动 #7：在等级 3 至 5 出现超极巨化颤弦蝾螈，
每个等级都有超极巨化霜奶仙，剑版有巨钳蟹和长毛巨魔，盾版有以欧路普和布莉姆温；
其等级 5 的颤弦蝾螈等于 PKHeX 的 `encounter_sw_dist.pkl` 中索引 10 的记录。

分发奖励文件是表的向量（字段 0）：TableID u64 和 Entries（字段 1），每个条目为等级 1 至 5 的
五个 u8 值（字段 0 到 4）和一个 u16 道具（字段 5）。游戏自身的表，
`data_table.gfpak` 文件 7（掉落）和 6（奖励），保存 TableID，然后是 u32 条目索引、u32 道具和
五个值的 u32 向量（`pokeldn/swsh/data/nest_rewards.json`、
`scripts/gen_swsh_nest_data.py`）。遭遇通过 ID 在这两类表中命名其表，游戏优先使用
[pkNX `NestHoleDistributionEncounterTable`]。奖励值是一个数量，掉落值是一个百分比概率。
1 星巢穴的奖励（`raid.DEN_REWARDS`）以奖励表 `0xf966212316b78eb6` 在等级 1 按其数量提供的行
开始（经验糖果 XS x5、经验糖果 S x1、极巨糖果 x1），然后是两件道具，各一行。
`raid_event.rewards` 构建奖励行，然后为每个掉落构建一行，掷出每个掉落的概率或全部保留。

`raid_event.boss_pk8` 在 `raid.boss_record` 上构建头目：表的物种、形态、等级、招式、超极巨化和
极巨化等级，以及表允许的特性、个体值、性格、性别和 PID，使用来自
`pokeldn/swsh/data/species.json` 的队伍属性（`scripts/gen_swsh_species_data.py`）。

    bin/swsh_host.py --raid-event "FOLDER/Index 010" --raid-stars 5 --raid-event-boss 4 --raid-console-serves

如果没有 `--raid-stars` 或 `--raid-event-boss`，主机会列出它接受的参数。`--raid-version` 选择
表的版本（默认是广告的版本），`--raid-area` 选择巢穴区域，`--raid-event-drops all` 选择所有
掉落；`--raid-reward` 行替换活动的奖励。

## 极巨大冒险

极巨大冒险（Max Lair，二进制中为 `chika`）通过本地通信匹配，当每位玩家在极巨巢穴选择“邀请其他人”时：第一个玩家开启网络，其他人扫描并连接。Y-Comm 从不列出它：主机宣告的活动类型为 0xFF。网络携带本地通信 ID `0x0100abf008968000`，场景 50000，NodeCountMax 4（Pia 最大值，从 `0x00bd9b30` 调用，位于 `ChikaMatchingState*` `0x00bd1978..0x00bda158`）。主机在“通信中”倒计时 3:00；没有来宾时会取消冒险。冒险开始后，电脑伙伴填满空位。

两个消息持有者运行在可靠 0x80 端口 0 上，每个字段是一个含有一个字段 1 的持有者：

- id 7000，`net_contents.chika.protocol_buffers.ChikaAsyncDataHolder`（描述符 `0x1c3adb5`、`0x2066654`），即大厅；
- id 8000，`net_contents.underground.protocol_buffers.UndergroundAsyncDataHolder`（描述符 `0x1c36fab`、`0x20681cc`），用于战斗之间。

发送到极巨巢穴大厅的巢穴消息（id 2000）会被确认，但不会让任何人入座。战斗在 0x7C 上运行，方式与极巨团体战的巢穴一致，但有两个区别：

- 动作是条目 1 `01 ff ff ff ff ff ff ff`，条目 2 为与巢穴战斗相同的招式，其余九个条目为 `0xff`；在极巨化回合，条目 2 的字节 3 为 `0x80`，并且其前的状态消息携带状态 1 而非 2；
- 来宾的宝可梦昏厥后，主机发送类型 0x04，数据为 `01 00 ff ff ff ff`；来宾回复一个 88 字节的动作，其条目 2 为零。

`pokeldn/swsh/lair.py` 是这两个持有者的来宾侧；`bin/swsh_connect.py --preset lair`（应用中的极巨大冒险（加入））以玩家 1 入座，并取主机留下的第一个提供位置（租用按回合进行，主机优先）。由 `lair.rental_pk8` 构建的租用宝可梦，使用记录的租用记录，具有该行的物种、形态、等级 65 和招式，四项个体值为 31、其余随机，随机性格，特性栏位 1 或 2，性别、PID 和加密常数；原始训练家为“科学家”，精灵球，在 65 级相遇，队伍状态没有极巨化加成。零售版剑主机接受了它。

### 大厅持有者，id 7000

命名玩家的记录以其 Pia 常量 ID（u64）及其玩家索引字节开头；电脑伙伴的 ID 为零，索引为 2 和 3。

| 字段 | 名称 | 大小 | 内容 |
|---|---|---|---|
| 1 | ChikaTimeLimit | uint32 | 剩余秒数，来自主机 |
| 2 | ChikaPlayerInfo | 48 | 12 个零字节、13 个字符的 UTF-16 名称，然后是 `02 00 00 00 00 2d 00 00 00`；zlib 压缩（可靠标志 0x10） |
| 3 | ChikaBattleReady | 16 | 玩家按下准备后字节 8 为 1；冒险开始后字节 12 为 1 |
| 4 | ChikaSelectPokemon | 360 | 8 个零字节、u32 表示该租用宝可梦在共享提供中的位置、作为加密队伍 PK8 的租用宝可梦、四个零字节 |
| 5 | ChikaBattleStart | 32 | 人类玩家的常量 ID，来宾的在前 |
| 8 | ChikaBattleSeed | uint64 | 来自主机；为租用提供和遭遇设定种子（[冒险种子](#the-adventure-seed)） |
| 9 | ChikaRentalPokemonSeed | uint64 | 来自主机，在租用选择之前 |
| 11 | ChikaPlayerNumber | 40 | 四个常量 ID（主机、来宾、零、零），然后是玩家索引 `00 01 02 03` |
| 12 | ChikaBigBoss | 16 | 字节 12 为 1；每个玩家随 PlayerInfo 发送自己的 |
| 13 | ChikaBigBossFixed | 4 | u32 表示冒险中传说宝可梦的物种 |

字段 6、7 和 10 未发送。顺序：加入时每个玩家的 PlayerInfo、BattleReady 和 BigBoss；字节 8 置位的 BattleReady；来自主机的 BattleStart、BattleSeed、RentalPokemonSeed、PlayerNumber、字节 12 置位的 BattleReady 和 BigBossFixed；然后每个玩家的 SelectPokemon。

### 冒险持有者，id 8000

| 字段 | 名称 | 大小 | 内容 |
|---|---|---|---|
| 1 | UndergroundWaySelect | 16 | 常量 ID、玩家索引、选择的路径 |
| 3 | UndergroundWayResult | 1 | 已选择的路径，来自主机 |
| 4 | UndergroundTradeWant | 16 | 常量 ID、玩家索引、1 表示交换获得的宝可梦 |
| 6 | UndergroundTradeResult | 360 | 交换玩家的常量 ID、索引、两个字节，然后在 +11 处作为加密队伍 PK8 的新宝可梦 |
| 10 | UndergroundRaidCapture | 16 | 常量 ID、玩家索引、字节 9 |
| 11 | UndergroundRaidWant | 16 | 常量 ID、玩家索引、1 表示取走捕获的宝可梦 |
| 12 | UndergroundRaidResult | 360 | 8 个零字节、取走玩家的索引（无则为 `ff`）、一个字节，然后在 +10 处作为加密队伍 PK8 的宝可梦 |
| 14 | UndergroundTimeLimit | 8 | u32 剩余秒数、u32 阶段，来自主机，每秒三次 |

字段 2、5、7、8、9 和 13 未发送。每个来宾发送自己的 WaySelect、TradeWant、RaidCapture 和 RaidWant；主机以自己以及每个电脑伙伴各一个回应，然后给出结果。

### 举办冒险

`bin/swsh_host.py --lair-legendary SPECIES [--lair-seed N]`（`pokeldn/swsh/lair_host.py`）根据模拟的盾版主机通告（场景 50000）宣告极巨巢穴网络，像连接交换一样交换快照，然后发送大厅：PlayerInfo、BattleReady 和 BigBoss，时间限制每秒三次，准备；一旦来宾准备，发送 BattleStart、BattleSeed、RentalPokemonSeed 和 PlayerNumber；一旦来宾回应已开始，发送字节 12 置位的 BattleReady 和 BigBossFixed。五秒后它像举办中的剑版主机一样离开（[离开](swsh_session.md#leaving)）：MIGRATION_START `44 00 01`，带主机迁移字节的更新会话，START_HOST_MIGRATION 每 0.33 秒一次，并在一旦游戏机离开或 10 秒后关闭网络。

应用的极巨大冒险（举办）工具运行这些标志：传说宝可梦、可选的连接密码和种子。它的种子选择器显示 `lair.adventure` 针对某个种子给出的三个租用宝可梦和十个遭遇，可抽选新种子，并可搜索种子以找到选定的租用宝可梦（大约每 75 个种子会提供一个给定宝可梦）。地图尽头的传说宝可梦就是 BigBossFixed 指定的物种；来宾自己的 BigBoss 全为零。租用宝可梦按回合选择，主机优先，电脑伙伴会接替已离开玩家的座位。

极巨巢穴的连接密码在前台用 + 设置。通告携带代码十进制值的 CRC32，去掉前导零（0000 7777 为 `7777`）；使用不同代码或不使用代码搜索时，永远不会列出该大厅。在有代码的情况下，若主机未发送 MIGRATION_START 就关闭网络，来宾会在租用画面卡在错误 2618-0006；进行交接后，来宾在 MIGRATION_START 后 0.1 秒离开，冒险继续进行。

### 冒险种子

冒险中的宝可梦来自 RomFS `bin/appli/chika/data_table/underground_exploration_poke.bin` 中的行，这是一个包含 273 行的 FlatBuffer：226 个 65 级的租用宝可梦和遭遇，然后是 47 个 70 级的传说宝可梦（首领标志置位）。每行包含物种、形态、等级和四个招式。

ChikaBattleSeed 设置六个租用提供和遭遇；`lair.adventure(seed)` 计算它们。Xoroshiro128+ 用 u64 和 `0x82A2B175229D6A5B` 播种。每次选取用下一个 32 位输出播种 MT19937，洗牌 273 个行索引（索引 i 与 i 加上一个最多 272 - i 的抽取交换，按 `0x1ff` 掩码，超出则重新抽取），然后取第一个不是传说宝可梦且尚未被选取的行。先选取四次，然后在接下来两次选取以及最后一次之前各抽取一个 0 到 2 的数，分别在就座的电脑伙伴数多于 2、1 和 0 时进行；然后各抽取一次 0 到 2 和 0 到 9；然后十次遭遇选取，每当该行有两种属性时后面再输出一个。有三名电脑伙伴时，先抽取一个 0 到 27 的数。

租用画面显示提供位置 0 到 2。每个座位依次选择，主机优先，它选择的位置由下一个未使用的位置（3，然后 4，然后 5）补充。电脑伙伴在玩家之后选择，从不通过线上：每个伙伴占据其 0 到 2 抽取所给出的画面位置，第一个伙伴使用第一次抽取。`lair.partner_places(seed, taken)` 计算它；它在三次记录的冒险（一次模拟主机和来宾，我们的来宾对模拟主机，以及对零售版剑主机）中命名了两个伙伴的租用宝可梦，这些是从主机在 0x10 类型命令中每个战斗位置使用的招式读取的。该规则只需要 ChikaBattleSeed。路径会遇见哪些遭遇尚不清楚。

## 离开

一旦其玩家离开奖励画面，零售版剑主机会以每 0.33 秒一次 START_HOST_MIGRATION 关闭网络，持续 10 秒，与连接交换之后一样（[离开](swsh_session.md#leaving)）。未离开的来宾会让主机玩家在大地图中冻结，直到超时；`--leave-with-host` 会在第一次时离开。

## 未解决的问题

- 非 Pia 主机的游戏机是否会发布框架对象 0 到 7。
- 在零售硬件上，一个举办大厅中有多台游戏机；目前仅在模拟的盾版上测量过。
- PlayerInfo 的 u32 和最后几个字节的含义。
- 动作的其余十个条目、极巨化，以及 8 和 2 之外的目标代码。原样重放时，一个记录的水枪动作会让任何来宾宝可梦使用水枪，在零售版剑主机上也是如此。
- 极巨大冒险：有三名电脑伙伴时伙伴的顺序；在租用画面接替已离开主机座位的伙伴占据了位置 1，而 `partner_places` 给出的是位置 2。
- 极巨大冒险：PlayerInfo 的尾部字节、BigBoss、RaidCapture 中玩家索引之后的字节以及结果记录，以及两个持有者未发送的字段。
- 零售版来宾是否会从巢穴记录为零的巢穴通告中接受活动首领，以及零售版活动巢穴主机在巢穴种类位和巢穴记录中写入什么。

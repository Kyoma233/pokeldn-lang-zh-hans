---
title: Scarlet and Violet
nav_order: 9
has_children: true
---

# 朱／紫

宝可梦 朱（`0100a3d008c5c000`）与 紫（`01008f6008c5e000`）是原生 Switch 游戏，Pia 链接进 `main`。两个版本在与零售主机交换时均可承担两种角色：`bin/sv_host.py` 为主机的离线连接交换搜索充当主机，`bin/sv_join.py` 加入主机的网络。一台零售紫会加入一个广播朱的本地通信 id 的主机，它自己的搜索网络也广播朱的 id（`0x0100a3d008c5c000`，应用版本 21，场景 4）。

这两个启动器还可在任一角色下运行本地太晶团体战（[太晶团体战](sv_raid.md)），并且主机可向一台零售主机交换官方礼物宝可梦（[模拟神秘礼物](gift_simulated.md)）。[联合环](sv_union_circle.md) 以来宾身份加入主机的环，向环主报告蓝莓任务完成情况，并在主机玩家周围生成用户自制的野生宝可梦。

地址是更新 4.0.0 解压后的 `main` 中的偏移（`tools/switch/nso_read.py`）：text `0x0..0x343fc90`，rodata 从 `0x3440000` 起，data 从 `0x4383000` 起。

## 无线层

| | 值 |
|---|---|
| Pia 头版本 | 11，传说 阿尔宙斯频段；`pokeldn.ldn.pia6` 使用该版本 |
| 头部大小 | 0x1C，GCM 标签 8 字节 |
| LDN 口令 | `W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL`，data `0x44dfd0a` |
| Pia 游戏密钥 | `p1frXqxmeCZWFv0X`，data `0x44dfcfe`，紧挨在口令之前 |
| LDN 本地通信 id | 两个版本上均为朱的 `0x0100a3d008c5c000`（这两个 id 都不是该镜像中的常量；NACP 中列出了两者） |

口令和游戏密钥与剑／盾和传说 阿尔宙斯相同。

## 搜索中的主机所广播的内容

连接交换搜索会在主持（每次使用新 SSID）与扫描之间交替，并在信道 1、6 和 11 之间跳转；一个主持阶段约为五秒。

    local_communication_id  0x0100a3d008c5c000, Scarlet's, on both versions
    ldn protocol            1            advertisement version 4
    scene_id                4            app_version 21
    security_mode           1            accept_policy ALL
    participants            1/2
    application_data        132 bytes

应用数据为 0x5C 的 Pia 系统属性块和 40 游戏字节：

| 字段 | 值 |
|---|---|
| 系统通信版本 | 0x15 |
| 应用通信版本 | 0x15 |
| 用户密码 | 十六个零字节且无连接码 |
| 玩家上限启用 | 1，玩家数为 1，有站点就座后变为 2 |
| 玩家名 | 一个字节，一个空格，UTF-8 |
| 40 游戏字节 | 为零，或游戏 `+0x21` 处为非零值（曾见到 `fb149700`），每隔几秒交替；第二台主机在任一情况下均可关联 |

`pokeldn.sv.build_advertise_data` 逐字节复现两种信标。

## 游戏运行的协议

对实机配对的被动抓包显示 Net、RTT、0x80 和 0x81，全部发往会话 `/24` 的广播地址，明文尾部带有接收方的 variable id。其他六个协议为单播（两台 Switch 2 主机之间的 802.11ax），抓包中不存在。

游戏的初始化 `0x17ff030` 按顺序创建：端口 0 上的 Reliable `0x7C` 和 BroadcastReliable `0x80`，端口 1 和 2 上的 Unreliable `0x68`、Reliable 和 BroadcastReliable，`[0x44dfcd0]` StreamBroadcastReliable `0x81` 端口（线上八个），Clone Clock `0x77` 和 Clone Atomic `0x74`。Pia 会添加 Net、RTT、Session `0x98` 和 MonitoringData `0xA4`；NatTraversalResult `0xA0` 仅在网络工厂启用 NAT 穿越（`0x6d3138`）时添加，本地网络不会启用。

| id | 协议 | 版本 |
|---|---|---|
| `0x2C` | Net | 0 |
| `0x58` | RTT | 3 |
| `0x68` | Unreliable | 1 |
| `0x74` | Clone Atomic | 0 |
| `0x77` | Clone Clock | 0 |
| `0x7C` | Reliable | 2 |
| `0x80` | BroadcastReliable | 3 |
| `0x81` | StreamBroadcastReliable | 3 |
| `0x98` | Session | 0 |
| `0xA4` | MonitoringData | 0 |

《传说 阿尔宙斯》列出了相同的十个版本。实机配对的开场：

    +0.00   the joiner associates
    +0.06   host: Net 0x11 (station list), 0.12 s later Net 0x50
    +0.14   host: acks all eleven streams, opens two
    +0.89   joiner: RTT request, acks all eleven, opens two
    +0.97   host: first records on 0x81 port 0
    +1.26   joiner: first records on 0x81 port 1

### Net 0x11，站点列表

布局与《传说 阿尔宙斯》相同，有四个各 21 字节的站点槽：

    01 11 0054          version 1, type 0x11, payload size 0x54
    00000002            sequence id
    9141                host variable id, fresh every session
    eb9b2220f1480000    host constant id, the LDN MAC reordered
    0000000097392e8a    network id, the low four bytes crc32(ssid[1:16])
    01                  is network open
    0004                station slots
    00                  is migrating host
    ...                 four stations: migration state, ranking (host 0, joiner 1, empty 0xff),
                        one byte, 16 address bytes, big-endian u16 port (12345)

`01 40 00 00` 是一个裸的 NetStartHostMigration，由交接角色的主机发送。从搜索开始主持的实机《朱》会在交给加入者的座位上重复它（[座位如何决定](#what-decides-a-seat)）。

主机写入四个站点槽，这是 Pia 的数量；游戏的上限是两个。有两个槽时，加入方不发送任何内容，用 ICMP 端口 12345 不可达回应 Net 0x11，并在关联后 5 秒断开连接（49 次加入中 4.98 到 5.01 秒）；有四个槽时，它会回应 Net 0x12 并发送其 Session 加入请求。

### 十一条流

    0x80  BroadcastReliable         ports 0, 1, 2
    0x81  StreamBroadcastReliable   ports 0 to 7

两个站点大约每秒一次用 `pokeldn.ldn.reliable5` 的批量确认来确认全部 11 条流：四个条目，站点字节为零，条目 *k* 是站点 *k* 最高序号之后的一个，destination-bit 计数为 3，位图中包含对端的位。站点用 11 字节的 INITIALIZED 消息打开两条流，并在其站点索引端口上发送记录（与 `pokeldn.pla.data_exchange` 一致）。

| 站点 | 打开 | 发送记录到 |
|---|---|---|
| 主机，索引 0 | 0x81 端口 1 和 5 | 0x81 端口 0 |
| 加入者，索引 1 | 0x81 端口 0 和 4 | 0x81 端口 1 |

端口 0 和 1 上的打开负载为 `0000000000f38800000000`，端口 4 和 5 上为 `00 <port> 00 00 0ff0 0800000000`：StreamData 类型 0 表示接收 0xF388（传输 0）或 0xFF008（4 和 5）。0xFF008 传输在交换中从不发送。
`pokeldn.sv.streams` 构建所有内容；`tests/test_sv.py` 将其固定为实机字节。

### Pia 消息标志

两个实机站点都发送（未使用《阿尔宙斯》主机的建立标志）：

| 消息 | 标志 |
|---|---|
| RTT、打开流、记录首次传输 | 0x00 |
| 记录再次发送 | 0x40 |
| 批量确认 | 0xA0 |
| 主机的 Net 0x11 和 0x50 | 0x31 |
| NetStartHostMigration | 0x11 |

消息目标字段始终为零。标志 0x40 是来自 `ReliableSlidingWindow` 发送循环 `0x6f0638` 的 `w4 = 1`（当发送计数 `[slot+0x14]` 为零时为 0，`0x6f0908`；重发 `0x6f0a9c` 或提前发送 `0x6f0c38` 时为 1），由 `0x6e7250` 存储为数据包写入器选项块的第 0 字节。

### RTT

11 字节：类型、大端 u64 时钟、大端 u16 目标。请求类型为 0，目标为 0；应答类型为 1，时钟相同，并包含请求方的 variable id，实机在 20 ms 内完成。

RttProtocol（虚表 `0x43e5a28`）在每个站点保持一个 0x40 字节的记录，地址为 `[proto+0x60] + index*0x40`：样本计数 `+0`，环形头 `+4`，容量 9 在 `+0x10`，环形缓冲区紧随其后，中位数缓存于 `+0x3c`，对应计数 `+0x38`。样本是当前时钟减去回显时钟（`0x6f34b4`）；小于等于零的样本被丢弃（`0x6f34e0`）。请求以间隔 `[0x46d1528]` 发送，直到每个环形缓冲区填满，然后按 `[0x46d1520]` = 500（由 `0x6f2fcc` 和游戏在 `0x1e7c2bc` 写入）。站点事件 0 或 1 清除该站点的记录（vfunc11 `0x6f3bd8`）：新座位没有样本。

GetRtt（`0x6f4498`；带计数 *n* 的 `0x6f44bc`）在没有样本时返回 -1，否则返回最后 min(count, *n*) 个样本的中位数；min `0x6f44e4`、max `0x6f4508` 和样本计数 `0x6f452c` 位于旁边。唯一的调用者是 SessionTransportAnalyzer 的监控副本（`0x6f9ab0`..`0x6f9ad4`）和 `ReliableSlidingWindow` 的重传截止时间 `0x6f0d14`，从发送循环 `0x6f073c` 调用：

    deadline = now + [window+0x80] + 1.4 * (max over the destinations of GetRtt(count))

没有样本时，`0x6f0d14` 返回未调度标记 `[window+0x5c]`：消息入队时发送一次（`0x6f1bbc`..`0x6f1bd4`），并在 `0x6f0a18` 处跳过，直到样本重新武装它（`0x6f09f4`..`0x6f0a08`）。没有 RTT 样本的窗口永远不会重传。

构造函数 `0x6eeea8`（调用者 `0x6e69f8`、`0x1800038`）将 `[window+0x80]` 设为 `ticks_per_second * 33 / 1000`（`0x6eef34`..`0x6eef74`；633,600 tick，19.2 MHz 下为 33.0 ms），标记 `[+0x5c]` 为 0，基础序列 `[+0x30]` 为 1，自身索引 `[+0x10]` 为 0xfd，压缩 `[+0xa4]` 为 1，提前发送限制 `[+0x88]`、`[+0x89]` 为 0。之后唯一的写入者是 vfunc17 `0x6f1f98` 中的 `0x6f1fc8`（来自 `ReliableProtocol::vfunc17` `0x6eebbc` 和 `BroadcastReliableProtocol::vfunc17` `0x6e6818`，没有已知调用者）。发送循环每 16.7 ms 帧运行一次，因此重发会在 `33 + int(1.4 * RTT)` ms 后的第一帧发出：RTT 为 34 ms 时为 83 ms，358 ms 时为 550 ms。

### 记录

一条记录是一条带有 ZLIB 标志的可靠消息，是带有 4 KB 窗口（`484b`）的 zlib 流，解压后为 1395 字节，`[window+0x70]`：Pia 的 StreamData 头下的 0x81 传输的一个块（[协议 0x81](pia.md#protocol-0x81-the-stream-broadcast-reliable-transfer-pia-6)）：

    +0x00  1   StreamData kind: 1 the first chunk of the block, 2 a later chunk
    +0x01  1   transfer id, 0
    +0x02  1   percent of the block delivered after this chunk
    +0x03  4   zero, the capacity field of a kind 0
    +0x07  4   big-endian u32 0x00000568, the 1384 bytes that follow

一个站点的块为 0xF388 (62,344) 字节：45 个 1384 字节的块和一个 64 字节的块，id 从 1 到 46，百分比字节为 `floor(k * 1384 * 100 / 62344)`（第 2、4、6、8、0x0b、...、25 时为 0x37、37 时为 0x52、46 时为 0x64）。第一个块携带屏幕上显示的伙伴：

    +0x0b  4   trainer id, then secret id
    +0x0f  1   version: 50 Scarlet, 51 Violet
    +0x10  1   gender
    +0x11  1   language
    +0x12  1   ball-throw style, 1 the original
    +0x13  26  the player name, UTF-16 little-endian, NUL-padded; --trainer-name on both launchers
    +0x2d  22  the account identifier, ASCII, `u-` and twenty characters
    +0x53  8   story progress, little-endian: 1 the main story cleared, 4 The Indigo Disk cleared

该块在栈上构建，地址为 `0xa52f88`..`0xa530a0`：训练家来自存档，然后是来自另一个存档块的投球风格（`0xa53054`），然后是账户标识符（`0x1a61a00`），最后是进度字，它是游戏保存在 `0x473a040` 处的脚本函数的返回值（在 `0xa5309c` 调用）。原生 `f20A702BD`（`0x877560`）安装它；在 3.0.1 脚本转储中，`BattleNetworkNetReceiver` 传入一个函数，从 0 开始，当 `FSYS_SCENARIO_GAME_CLEAR` 设置时置 1，当 `FSYS_SCENARIO_GAME_CLEAR_SU2` 设置时或入 4。`pokeldn.sv.reference` 发送 1；账户标识符全为零的实机《紫》发送 0。

游戏的脚本通过按此顺序注册的原生 getter 读取站点的玩家：`PlayerId`、`RomCode`、`Sex`、`LanguageId`、投球风格、`NameStrBuf`（`RegisterPlayerData` 和 3.0.1 脚本转储中的战斗设置；投球风格是存档自己的 `ballThrowId` 填充的槽）。在实机存档中，id 对、版本、语言和名称是存档自己捕捉的宝可梦的，无论它提供什么宝可梦。为接收方玩家制作的礼物会读取它们（`reference.identity_trainer`，[为接收方玩家制作](gift_simulated.md#made-for-the-receiving-player)）。

第 2 到 24 个块是高熵的；第 25 到 46 个块是零。站点一次发送整套，通常第一包发送 id 1、25、26 到 36 和 46，第二包发送 2、37 和 38 到 45，然后 3 到 24 逐个包发送（48 套实机中有 41 套），52 次中有 46 次在 0.19 秒内完成。相同的零块在 presence 字节为 0x00 的后面传输，所有头字段被继承（[消息分帧](pia.md#message-framing)）。`pokeldn.sv.streams.decompress` 读取它们。

`pokeldn.sv.reference` 在 0x7C 端口 0 上发送一个站点的 44 条记录和其两个身份片段，记录来自一个模拟的《朱》，其玩家名为 `Player`，账户标识符未设置。`bin/sv_host.py` 和 `bin/sv_join.py` 会发送它们，除非给出 `--record-set`、`--send-on-open` 或 `--no-identity`。

### 实机确认与重传洪流

实机站点确认对端的记录流时，ack id 为连续序列之后的一个，字段 0x50 等于它，掩码中第 *k* 字节的第 *b* 位表示 id `ack_id + 1 + 8k + b`：持有 id 1 到 4 和 7 到 38 的主机发送 `0005 0005 feffffff01`。低于对端自身 `lowest_pending` 的 id 视为已持有。`pokeldn.sv.streams.ack_position` 构建它；`bin/sv_join.py --ack-highest` 改为发送所见最高 id 之后的一个。

主机每轮重发所有未确认的记录，标志 0x40，最低 id 优先，每包一轮。轮间隔为 `[window+0x80] + 1.4 x RTT` 向上取整到帧：RTT 0.015 秒时为 0.065 秒，0.36 秒时为 0.53 秒。在小 RTT 下，这是每秒数百条记录，足以填满开发板的串行线路（[串行上限](hardware_esp32.md#the-serial-ceiling)）。主机的 `lowest_pending` 在集合之后约 0.5 到 1.0 秒离开 1，无论 ack 延迟如何，因此在此之前的 RTT 应答会使它重发加入者已持有的记录。`--rtt-delay 0.3` 将 RTT 延迟 0.3 秒应答，使轮间隔保持在该延迟以上并停止重发。

`--leave-on-migration N` 在 Session 类型 7 之后 N 秒结束一个座位，`--announce-timeout SECONDS` 离开一个未公告的座位；两者都会再次扫描。`bin/sv_join.py` 对新记录立即确认，对重复记录每条流最多每 50 ms 确认一次（`--repeat-ack-gap`）。

没有 RTT 样本时，0x81 流从不重传（[协议 0x81](pia.md#protocol-0x81-the-stream-broadcast-reliable-transfer-pia-6)）：丢失的记录保持待处理，对端永远不会被公告。公告作业没有 RTT 门槛。缺失的身份记录会使 BoxTrade 作业保持在状态 1（`+0xb8`），完成槽计数 `0x1e51ae8` 为 1，对照 2。两个启动器都会重试待处理的身份记录（[5 和 6 处的最低待处理与间隙](#lowest-pending-and-the-gap-at-5-and-6)）；`tests/test_sv_identity_loss.py` 覆盖此情况。

### 抓包中的 A-MSDU 帧

两台主机都将多个 MSDU 打包为一个 A-MSDU 帧。被动抓包必须解包子帧，否则会丢失大部分 Pia 数据包（一次抓包中，不解包可读 313 个，解包后为 3667 个）。

## 连接码

连接码在广播中携带两次；场景 ID 保持为 4。用户密码即该码，以 NUL 填充到 16 字节，再与 `e5ab19ed742b6d40885998bf968aa166`（同一游戏密钥下的传说 阿尔宙斯掩码）进行异或（[docs/pla.md](pla.md)）。游戏字节在 +0x00 处明文携带该码，并在 +0x24 处以 u32 保存其长度。`pokeldn.sv.build_advertise_data(code=...)` 逐字节复现了一台正在使用 12345678 搜索的零售版主机。

正在搜索的主机只会加入广播了相同码的主机（`bin/sv_host.py --code`）。一台使用码作为主机的零售版主机接受了一个未广播任何码的加入者。`bin/sv_join.py --code` 只会加入使用该码搜索的主机。

只有正在搜索的主机会在它扫描的网络上检查码。它的选择器 `0x26e955c`（在加入前从 `0x272d838` 调用）在使用码搜索时会跳过没有密码的网络（`0x26e95f4`），并在没有使用码搜索时会跳过有密码的网络（`0x26e960c`）。然后它对从 +0x00 到第一个 NUL 的游戏字节以及自己的码进行 FNV-1a 64 哈希（质数 `0x100000001b3`，偏移基准 `0xcbf29ce484222645` 从 `0x26e96c8` 加载，不是标准基准），如果两者不相等就跳过该网络（`0x26e972c`）。它既不读取密码的值，也不读取 +0x24 处的长度。

主机不会比较加入者发送的任何内容。LDN 关联使用固定口令，Session 加入请求没有密码字段。Pia 在连接站上的密码检查（Net 0x32 处理器 `0x69ec50` 中的结果 7，`0x69ee5c`、`0x69ee70`）需要 Net 0x32，而它唯一的发送者 `0x69d42c` 受协议 vfunc 48 限制：在 `LdnProtocol` 中为 0（`0x6a2fac`），在 `LanProtocol` 中为 1（`0x6ba278`）。在加入方，LDN 连接运行 Pia 的网络检查 `0x6a22c4`，但其密码比较（`0x6a24a4`）被关闭（`0x6b0d90`）。

已加入的主机不会再次检查码。Net 0x50 处理器 `0x69ea3c` 验证系统属性大小（0x5c）、应用数据大小（至多 0x124）以及四个 Pia 身份字段（`0x69d9d8`），将这些字节复制到网络属性（`0x69d8a4`）并用 Net 0x51 确认；它不会比较系统属性或游戏字节中的任何字节。在 LDN 上，该副本落入缓存的广播数据，下一次 `nn::ldn::GetNetworkInfo`（`0x6b30d4`）会覆盖它。游戏只在选择器和 UpdateSessionSetting（`0x26e63b8`）中读取会话的前 0x28 个游戏字节，后者会重写自己的会话；另外两个读取者（`0x268e988`、`0x268e9bc`）只读取 +0x28 之后的内容。加入方主机保留自己的码作为它自己的 Pia 站点密码（加入对象 vfunc `0x274bdb8`，setter `0x6a208c`），只有在它作为主机时才会广播该密码。连接交换的端口 2 类型 1 来自 BoxTrade 任务的状态 2（`0x1e51b68`）：种类 1、静态空名称 `[0x46d3e30]`、无数据。

## 连接码的位置

RTTI 名称来自二进制文件的 type_info 记录（`tools/switch/rtti_names.py`，208 个 `nn::pia` 类）。

| 地址 | 说明 |
|---|---|
| `0x697134` | Pia 头初始化器：魔数 `0x32AB9864` 位于 `+8`，版本 `0x0b` 位于 `+0xc`，头大小 0x1c 位于 `+0x5f8` |
| `0x696f10` | 头解析器，按版本 11 的顺序排列字段 |
| `0x697034` | 载荷上限：长度超过 0x5a3 时返回 null |
| `0x3c0c8c0`, `0x44dfcfe` | 口令（rodata）和游戏密钥（data） |
| `0x6b43a8` | `LdnConnectionStatus::vfunc20`：将 `GetNetworkInfo` 参与者映射到站点地址 |
| `0x6b45e0`..`0x6b4754` | 它遍历八个 0x40 字节的参与者槽（地址 `+0x108`，存在字节 `+0x113`），与对象 `+0x30` 处的站点数组、`+0x38` 处的计数相对照 |
| `0x6b3090` | `LdnProtocol::vfunc104`，另一个 `GetNetworkInfo` 读取者 |
| `0x046ca878` | `nn::ldn::GetNetworkInfo` 的 GOT 槽，六个调用点 |
| `0x475ea68`, `0x475ea6c`, `0x475ea70` | Reliable 0x7C 句柄，端口 0、1、2 |
| `0x475ea74`, `0x475ea78`, `0x475ea7c` | BroadcastReliable 0x80 句柄，端口 0、1、2 |
| `0xe45e9c` | 0x80 端口 2 上的唯一发送：通过 `0xe21488` 解析协议，将缓冲区交给 `0x107e060` |
| `0xe2246c` | 其下的 0x5a0 字节应用发送，进入 `BroadcastReliableProtocol::vfunc12` `0x6e6344` |
| `0xe457cc`, `0xe45740`, `0xe460bc`, `0xe454ec`, `0xe46148`, `0xe461d4`, `0xe46260` | 消息类型 6、7、8、9、0x0A、0x0B、0x0C 的构造器，每个都会调用 `0xe45e9c` |
| `0xe45e1c`, `0xe46034` | 类型 7 和类型 8 的字段序列化器（`0xb9` 标记） |
| `0x46d6ca0`, `0x46d6ca8` | drain `0xe44cf0` 的单例，在 `0xe44ac0` 处设置 |
| `0x1e685a4` | 交易频道端口 0 的接收器：种类（带标签整数）、步骤，然后通过表 `0x3c5bb82` 处理种类 0 到 5；1 身份（`0x1e6864c`，解析到 `+0xae0`），2 报价（`0x1e686cc`：由 `0x1db949c` 解析的 344 字节块，由 `0xeee8fc` 和 `0xe13ad8` 包装，由 `0x1e684fc` 存储到 `+0xb8`，状态 `+0xc4` = 3），3 确认（`0x1e68768`，与 `+0xe2` 比较步骤），4 取消（`0x1e68678`），5 提交（`0x1e68780`，状态 `+0xc0` 掩码到 4） |

## Session 协议

`nn::pia::session::SessionProtocol`（id vfunc `0x6d9f3c` 返回 0x98）紧挨着 `JoinMeshJob`、`CreateMeshJob`、`LeaveMeshJob`、`JoinSessionJob` 和 `SessionPacketReader`/`Writer`；mesh 加入是传说 阿尔宙斯中的那套。Session 消息在包头部携带对端的 variable id，并且没有尾部，因此它走单播。加入者在加入请求的源 location id 中声明自己的 variable id；主机在关联后 0.14 秒将其命名。

### Session 加入请求

写入器 `0x6d5464`..`0x6d58b0`，主机解析器 `0x6d5aa4`。布局是零售版传说 阿尔宙斯的（`docs/pla.md`，Session 加入请求；在 `tests/test_pla_session_v11.py` 中为 115 字节），由 `pokeldn.ldn.pia6.build_session_join` 构建：

    +0    1    type 0
    +1    1    protocol count, ten
    +2    2n   (id, version) pairs, walked from the protocol manager's list
    +22   4    random, xorshift128 seeded from the system tick (`0x6c70a8`, `0x6c7184`)
    +26   12   source location id: u64 constant id, two zero bytes, u16 variable id, big-endian
    +38   1    NAT mapping, two bits
    +39   1    private-IPv6 flag
    +40   32   identification token
    +72   1    address kind, 0 for IPv4 (1 puts an 18-byte IPv6 address in place of the six bytes)
    +73   4    source IPv4 address
    +77   2    source port, big-endian
    +79   12   destination location id, the host's
    +91   1    player count
    +92   1    a flag the job sets to 1
    +93   ..   player records: a 16-byte id (`1` then `0` as two big-endian u64), a big-endian u32
               name length, a kind byte (1), the name

零售版加入者的一个玩家名称是一个空格。数据包头部携带目标 variable id 0 和加入者的 id 作为源；每次重复发送的消息标志为 `0x01`（跳过源检查）。主机按以下顺序检查：

1. 协议计数与自己的相等；否则不发送任何内容。
2. 每个版本都与主机的相等（`0x6ed1b8`）；否则以状态 3 回应，并附带该 id 和主机的版本。
3. 目标 location id 是主机的 constant id 和 variable id；否则丢弃。
4. 源 constant id 和地址不是主机的。
5. 已知的 constant id 会再次触发状态 1；已关闭的会话返回状态 5；主机侧的监听者可以用状态 4 拒绝。

加入响应（类型 2，43 字节，`0x6d6390`）是阿尔宙斯布局：类型、协议 id、版本、状态、一个大端 u32、四个随机字节、两个 location id、路由字节 A 和 B、站点索引、加入顺序、站点更新必须达到的序列 id。加入者用 13 字节的类型 6（`0x6d80a4`）回应类型 5 更新：类型、constant id、两个零字节、已应用的序列（`pokeldn.ldn.pia_connect`）。

## 席位，以及它上面的身份洪泛

一台零售版朱主机在 16 毫秒内接受加入请求，发送一个 41 字节的加入响应（状态 1，无路由字节）和一个无路由的站点更新，并在 0x81 端口 0 上流式发送其身份。不认可加入者确认的主机会重新发送每条记录，直到席位结束，零售机上大约每秒 350 条记录。主机也可以改发 Session 类型 7，将其角色交给加入者（[什么决定席位](#what-decides-a-seat)）。

### 让主机将一条确认计数的标志

带有标志位第 5 位 ZLIB（`[msg+0x29]`、`0x6efc80`）的消息会在站点解析之前于 `0x6e9984`（`0x69804c`、zlib inflate `0x2801d0`）中被解压；失败会返回 0x2C03（`0x6efd5c`）。在标志 0xA0 下的普通批量确认会在那里失败（模拟主机上 600 条中 600 条都失败）。零售版 0xA0 确认带有解压后为 99 字节的 zlib 体（记录的 4 KB 窗口、5 级 sync-flush 帧）。在标志 0x00 下，同样的 99 字节也会被计入：主机每条记录只发送一次（每秒 6.3 条，然后不再发送，对比普通 0xA0 下每秒 115 到 257 条）。两个零售站点都将批量确认标志设为 0xA0，并将其发送到它们所在 /24 的 LDN 广播；`bin/sv_join.py` 在设置第 5 位时会压缩正文（`--ack-flags`、`--ack-entries`、`--ack-dest-bits`、`--ack-sweep`）。

### 流上的第一条记录携带 INITIALIZED

站点的第一条记录携带 INITIALIZED，以及 START、END 和 ZLIB，标志为 0x1F；后续记录标志为 0x17。以 0x17 发送的第一条记录永远不会被确认。主机随后将该集合确认到 47（掩码 `feffffffff01`），发送一次自己的记录，并发出一个列出两个站点的类型 5 站点更新。

## 主机托管

除了 Net 0x11 中的四个席位槽之外，主机还必须发送：

| 主机发送的内容 | 必须是什么 |
|---|---|
| Session 加入响应 | 41 字节：无路由字节，席位索引 1，加入顺序 1，序列 ID 0，+8 处四个随机字节（Arceus 的 43 字节形式会作为对照被重传） |
| Session 类型 1 加入确认 | 无需发送；一台零售主机曾发送过一次并在两秒内离开 |
| Session 类型 5 席位列表 | 两次：第一次与加入响应一起在序列 ID 0 下发送，然后在下一个 ID 下发送（零售主机：1.5 到 2 秒后） |
| 该列表中的每个席位 | 79 字节：位置 ID、地址和端口、席位索引、大端 u16 加入顺序、NAT 字节、IPv6 标志、32 字节令牌、计数、玩家记录。无路由字节（Arceus 的是 81 字节） |
| 其中的玩家名称 | 一个空格（0x20） |
| 每个 Session 回复的消息标志 | 0x00 |
| Reliable 0x7C 上的确认 | 单条目形式，无目标位图；若未确认，主机将无休止地重发频道表（实测九十秒内上千次） |
| Reliable 0x7C 上的每条数据消息 | 九字节头，destination_bits 为 0，无位图 |
| Net 0x11 | 发送一次；重复发送会被视为在已入座席位上的新连接请求 |
| Net 0x50，更新属性 | 在 0x11 之后 0.2 秒发送，每 500 毫秒一次，直到席位的 0x51，+0x82 处携带四十个游戏广播字节 |
| RTT | 除应答外还要主动发起自身请求（双人主机：每 410 毫秒一次） |
| 开场流程 | 加入响应、第一份席位列表、频道表、两条流打开、时钟应答、入座后立即发送 Net 0x50 和全部 44 条记录（零售主机：0.3 秒内）；key-0x80 打开要在主机交易画面绘制前完成（[打开频道](#opening-the-channel)） |

四十个游戏广播字节每次会话都不同：为零，或在 +0x21 处为非零值（已观察到 `648cf4`、`8170f0` 和 `fb149700`）。使用 `--channel 6`、`--player-name RyuPlayer` 和 `--host-player-id 00000000000000010000000000000000` 时，除会话 ID 外，NetworkInfo 与模拟的《朱》主机一致。在入座之后失败的会话会引发重复加入（实测 16 到 57 次）。

### 最低待处理与 5 和 6 处的缺口

席位 ID 5 和 6 从不发送（线路上有 44 条记录），其余记录乱序发送（双人主机：1、2、3、46、4、7、8、19、9、15、10、16……）。每条记录声明 `lowest_pending` 为 1，目标位为 3，位图 `[2]`，流 ID 为 0。该缺口由发送方在同一条流上的下一次批量确认关闭，其 `lowest_pending` 从 1 步进到 47；对端随后以空掩码将集合确认到 47。若保持为 1，对端会以 `ack_id` 5、掩码 `feffffffff01`、全会话进行应答。无缺口的 ID 1 到 44 也会被接受；没有零售发送方使用它们。

发送方只能将 `lowest_pending` 推进到已确认记录之后。在初始突发后直接推进到 47 可能掩盖丢失的身份块：对端确认了 47，但 StreamData 块仍不完整，席位永远不会被公布。

两个 SV 启动器都为身份集合维护一个 `reliable5.SendWindow`。对应的批量确认条目会释放其 `ack_id` 以下的记录以及其选择性掩码指定的记录。每 250 毫秒，未确认的记录会以其原始序列 ID 和 Pia 消息标志 `0x40` 重新发送。出站数据和批量确认头会声明仍待处理的最低记录；当集合被完全确认时则为 47。这样既保留了故意留下的 5 和 6 空缺，又能反映实际丢失。

如果第一条 INITIALIZED 记录丢失，全部 44 条记录都会处于未确认状态，需要重试整个集合。中间某条记录缺失时单独重试即可。

## 游戏自身的协议，来自一对实例

通过两个互相进行过交换的模拟《朱》4.0.0 实例测得，每个实例记录它发出的每个数据报。
交换运行在 Reliable 0x7C 上；广播流仅承载身份交换。

### 端口 2：公告、加入与应答

Reliable 0x7C 的端口 2（一个站点）和 BroadcastReliable 0x80（每个站点）承载游戏的会话消息。轮询器 `0x1954978` 将 `[0x475ea70]`（`0x19549e4`）和 `[0x475ea7c]`（`0x1954a54`）读入分派器 `0x1954aec`：第一个字节，类型 1 到 0xD，表 `0x3c68988`。有三种类型会开启一次交换：

| 时间 | 站点 | 线上 | 类型 | 字节 |
|---|---|---|---|---|
| 0.00 | 主机 | 0x80 端口 2，zlib | 7 | 167 膨胀后：`07b901b905b906010200bc09`，九个零字节，`bc8080`，128 个零字节，`000000b90183`，主机的站点 ID，`00` |
| 0.09 | 加入者 | 0x7C 端口 2 | 3 | `03b90200bc09` 和九个零字节 |
| 0.15 | 主机 | 0x80 端口 2 | 9 | `09b9030000b90183` 和加入者的站点 ID |

编码是通道表（`pokeldn.ldn.channel_table`）的编码加上标签 `0xbc`，即字节串：标签、整数形式的长度、字节。类型 7 是一个含一个五元素元组的元组（写入器 `0xe464fc`）：

    b9 06 ...   the type-1 body as a tuple of six: kind, capacity, a zero byte, the name as a
                nine-byte string, the data as a 128-byte string, the data length
    key         body +0x8e, the relay's counter +0x1c4 before it steps
    index       body +0x8f, the relay's counter +0x1c0 masked to seven bits, before it steps
    b9 01 ...   a tuple of one u64, the station id of the type 1's sender
    0           body +0x98

类型 9 是加入方的槽密钥、一个结果字节和一个含一个 u64 的元组。

类型 7 是转发的类型 1：类型 1 处理程序 `0x18ceb70` 无条件复制 0x8e 字节的主体，盖上密钥和索引，步进两个计数器，附加发送方的站点 ID，并将其排入类型 7 组装器的队列（队列 `+0x200`，步幅 0xa8）。`0x18d5a58` 向一个站点发送端口 2 消息，当目标是自己时通过 `0x1954aec` 分派，因此主机会中继自己的类型 1。

类型 1 主体（`0x18ab760`）：

    +0x00  kind
    +0x01  the slot's capacity: 2 for kinds 1 to 3, 4 for kinds 4 to 8 and 12, 0 for kinds 9 to 11
    +0x02  zero
    +0x03  a name of up to eight characters, NUL-terminated in nine bytes
    +0x0c  up to 128 bytes of data
    +0x8c  the data length

一次交换的类型 1 为种类 1、容量 2、名称为空、无数据。槽位将主体保存在槽位 `+0xd0` 处（构造函数 `0x18b73a0`），因此其密钥 `0x12fcabc`（槽位 `+0x15e`）就是主体 `+0x8e`。每个转发的类型 1——无论是自己的还是对端的——都会步进密钥；只有 `0x12fbef0` 会清零计数器。命名密钥 0 的加入，如 `03b90200bc09` 所做的，只匹配自计数器清零以来的第一个公告。

类型 3 处理程序 `0x1981e94` 将加入方的第一个字段与槽密钥进行比较（`0x1981ed4`），并在接受时将类型 9（`+0x270`）排入队列；否则将一个类型 0x0D、`0d b9 01` 和一个代码排入 `+0x350`：

| 代码 | 拒绝原因 |
|---|---|
| 1 | 没有槽位具有加入方的密钥（`0x1981ffc`），或 `0x279c8fc` 拒绝 |
| 2 | 槽位已满：`0x18f80c8` 对照 `0x1e64914` 读取的容量，或 `0x279c9a0` 返回 0xfd |
| 3 | 加入方名称的 FNV-1a 64 哈希与槽位的不同（`0x1e648a0`） |
| 4 | 槽位已关闭（`0x1e64924`，槽位 `+0x160`，在槽位创建时清零） |

类型 0x0D 进入 `0x1954f3c`，它要求 `0xb9`，解码一个单元素元组（`0x279c0e8`）并调用接收器 `0x279c1ac`（`0x1954f78`）：

    0x279c1b8  ldr  x8, [x0, #0xb8]     the pending request
    0x279c1bc  cbz  x8, ret             none: nothing happens
    0x279c1d0  strb w9, [x8, #0x43]     result = the code
    0x279c1d8  strb #1, [x8, #0x42]     done
    0x279c1dc  bl   0xc8e6c4            wakes the request's waiter at +0x48

它既不检查请求类型 `+0x40` 也不检查完成字节，因此来自加入方的 0x0D 会用其代码完成本机所持有的任何请求。类型 9 接收器 `0x18b65c8` 通过槽字节选择一个对象，应用该消息，并且仅当 u64 是站点自己的 id `[[0x46d0a08]] + 0xb8` 时才不丢弃它。

站点 id 是 Pia 常量 id，以 big-endian u64 表示（对于 MAC `02:00:7f:00:00:02` 为 `7f00020000020000`）；针对零售主机，类型 9 携带来自其 Session 加入请求的常量 id。`pokeldn.sv.port2` 构建这三种消息（在 `tests/test_sv.py` 中固定）；`bin/sv_host.py --announce` 在席位之后发送类型 7，并用类型 9 应答类型 3。

### 发送公告的交换任务

连接交换在 `0x1e2ea54` 创建任务：配置 `BoxTrade`（`0x3aefac8`），工厂 `0x1e2f3d4`，模式 4，需求 2。两个脚本绑定会到达这里：`0x1e2e9bc`（GOT `0x46d6608`，由 `0x1b9c8c4` 存储到 `0x4717068`，尾调用）和 `0x1e2ec84`（GOT `0x46d6610`，在 `0x1e2ee40` 处 `bl`）。任务（构造函数 `0x1e3bd10`，vtable `0x44568a8`，Update `0x1e51a04`）：结果 `+0x40`，状态 `+0xb8`，会话句柄 `+0xc0`，模式和需求作为 u16 位于 `+0xc8` 和 `+0xca`，槽位对象 `+0xd0`，请求句柄 `+0xf8`。

| 状态 | 地址 | 行为 |
|---|---|---|
| 1 | `0x1e51a84` | 如果站点数 `[[0x46d0a08]]+0xe0` 低于需求，则结果 3；如果 `0x18ab520` 拒绝模式（0、5、8 以上），则结果 1；否则等待（无超时）`need` 个已完成身份块（`0x1e52004` 遍历 `[[job+0xd0]+0x10] - 0x28`），然后在主端上进入状态 2（`0x1639910`：自身 id `+0xb8` 等于主端 id `+0xc0`），在客户端上进入状态 4 |
| 2，主端 | `0x1e51b2c` | 种类 `0x18ab550(mode)`（模式 1 到 8 给出 2、3、4、1、0、5、5、8），然后请求 `0x18ab658`；空则结果 8 结束 |
| 3，主端 | `0x1e51ca8` | 等待请求，无超时；结果 0 进入状态 6，否则任务通过 `0x1e5086c` 结束 |
| 4、5，客户端 | `0x1e51b8c`、`0x1e51c74` | 相同的等待，但有 15 秒限制 |

| 结果 | 含义 |
|---|---|
| 1 | 成功，或模式被拒绝 |
| 2 | 会话处于状态 3 |
| 3 | 站点数少于需求 |
| 4 | 客户端的 15 秒超时 |
| 8 | 无会话，或请求被拒绝 |

请求 `0x18ab658` 构建类型 1 主体并通过 `0x18ab83c` 发送；当中继的挂起请求 `[relay+0xb8]` 的完成字节 `+0x42` 仍为 0（`0x18ab860`、`0x18ab8e8`）或发送失败时，`0x18ab83c` 返回 null。否则它清除 `+0xb8`（`0x18ab894`），存储一个新请求（`0x18ab8a8`；`0x18abec0`：`+0x40` 类型，公告为 0，`+0x42` 完成，`+0x43` 结果），并将类型 1 发送到主端 id（`0x18d58b8`），在主端上就是它自己；发送失败会清除 `+0xb8`（`0x18ab900`）。

`0x18ab658` 有四个调用者：`0x1e51b68`（BoxTrade 状态 2）、`0x18ab34c`（同级任务中的相同函数，vtable `0x4456490`）、`0xa188f0`（vtable `0x4452e68`）和 `0x1d99568`（vtable `0x44536d8`）。只有这四个请求创建者才会写入 `+0xb8`；当有请求挂起时，`0x18ab83c` 和 `0x2799b10` 会拒绝：

| 创建者 | 请求类型 | 存储位置 | 唯一调用者 |
|---|---|---|---|
| `0x18ab83c` | 0，公告 | `0x18ab8a8` | `0x18ab6bc`，位于 `0x18ab658` 中 |
| `0x2799b10` | 2，客户端的加入 | `0x2799bd8`（防护 `0x2799b2c`..`0x2799b40`） | `0x1e635fc` |
| `0x2799c44` | | `0x2799cfc` | `0x1e639ec` |
| `0x2799d6c` | | `0x2799e30` | `0x1e63c88` |

最后三个调用者各自位于一个函数中，这些函数的唯一调用者都在 `0x1d98xxx`（`0x1d986d8`、`0x1d98990`、`0x1d98c20`）内。

在连接交换中，类型 2 创建者从 BoxTrade 状态 4（`0x1e51c40`）经 `0x1d986d8` 和 `0x1e635fc` 到达。它仅在主端的槽位出现后运行于客户端（`0x1d999f4`、`0x18c7a40`），将请求保留在任务 `+0xf8` 处，并进入状态 5。`0x1d98698` 的其他调用者属于其他任务类。

排空器 `0xe44cf0` 按顺序遍历队列 `+0x1c8`、`+0x200`、`+0x238`、`+0x270`、`+0x2a8`、`+0x2e0`、`+0x318`、`+0x350`；组装器返回 false 会结束该帧的排空，因此卡住的类型 7 会将其后面的类型 9 和 0x0D 挡住。

类型 7 组装器 `0xe45740` 在站点数为 1 时仅本地分派；否则它询问 `BroadcastReliableProtocol::vfunc20`（`0x6e6638`）0x80 端口 2 是否可以发送，用 `0x107e060` 发送，并且仅当两者都成功时才在本地分派。当目标列表 `[window+0x40]` 中没有任何条目被设置时（`0x6efb98`），vfunc20 以 0x2c27 拒绝；当窗口没有空间容纳分片时（`0x6f1ef8`）以 0x4c0d 拒绝；没有会话或窗口时以 0x10408 拒绝。Pia 在站点加入事件时填充目标列表（[窗口发送给谁](pia.md#who-a-window-sends-to-pia-6)）。

类型 7 接收器 `0x18b566c` 创建并应用槽位，并且对于挂起的类型 0 请求以及本机自己的站点 ID（主体 `+0x90`），以结果 0 完成它：主端会一直停留在状态 3，直到它自己的类型 7 已经发送到线上。中继和线上之间没有任何东西读取 RTT 或定时器。

0x81 身份是每个站点一个块，放在其索引对应的端口上（句柄 `0x475ea48 + 4*index`），由流发送 API `0xe22188` 和接收 API `0xe22458` 为具有同一种布局的三个对象移动：

| 对象：Update，vtable | 发送 | 接收 | 块 |
|---|---|---|---|
| `0xe21104`，`0x4455ec0` 的槽位 13 | `0xe21a44`，在 `0xe21dc4` 处 `bl`，`w2 = 0xf388` 在 `0xe21db8` | `0xe2150c`、`0xe2170c`，`w3 = 0xf388` 在 `0xe21708` | 0xF388 = 62,344 |
| | `0xa62c5c`，`w2 = 0xff008` | `0xa64ddc`，`w3 = 0xff008` | 0xFF008 = 1,044,488 |
| `0x1e5f87c`，`0x4458698` 的槽位 13 | `0x1e617a8`、`0x1e61980`，`w2 = 0x97e08` | `0x1e61a74`、`0x1e61c0c`，`w3 = 0x97e08` | 0x97E08 = 622,088 |

在交换中只有 0xF388 块会出现在线上，因此任务的 `+0xd0` 对象属于该类（实例未追踪；通过 `0x1e34b6c` -> `0x1e35e88` 构建）。

`0x1e52004` 统计位于 `+0xd0 + 0x30*k`（四个）处、持有对端指针且字节 `+0xd8` 已设置的槽位。本机自己的槽位在 `0xe21154` 中获得该设置（`memcpy(slot, [+0x90], 0xf388)` 在 `0xe21248`，`+0xd8 = 1` 在 `0xe21258`；从 `0xa536e0`、`0xd6dc88`、`0xe21128`、`0x195160c` 调用）。对端槽位在 `0xe212b8` 中获得该设置（从 `0xa536f0`、`0xd6dc98`、`0xe21138` 调用），仅当向对端的发送（`+0xda`）和从对端的接收（`+0xd9`）已开始，自己的 0x81 流处于状态 3（`0xe2144c`，每个自己的块都已确认）且对端的处于状态 6（`0xe21404`，每个对端块都已接收）；状态 7 会清除一个标志（[协议 0x81](pia.md#protocol-0x81-the-stream-broadcast-reliable-transfer-pia-6)）。0x97E08 类具有相同的一对函数，`0x1e60284` 和 `0x1e615e8`。

在线上，类型 7 通常会在 0.11 秒内紧跟本机自己集合的最后一条记录。

中继是一个 0x388 字节的对象（vtable `0x44e56f8`），单例 `[0x46da9c0]` = `0x4739430`，仅当不存在时由 `0x165a200` 从 `0x1659b70` 创建（`0x1659b18`）。它的站点事件处理程序是 `0x12fbb90`，通过 thunk `0x2b71650`：

| 事件 | 效果 |
|---|---|
| 0，站点加入，在主端上 | `0x12fbf8c` 将当前槽位发送给它，除非它是主端 |
| 1，自身 id | 未完成的挂起请求以结果 5 完成（`+0x42` 处的 `0x501`），然后 `0x12fbef0` |
| 1，主端 id | `0x12fbef0` |
| 1，任意站点，在主端上 | 然后 `0x12fcebc` 丢弃它所中继的元素 |

`0x12fbef0` 通过 `0x12fc644` 移除每个槽位（完成密钥匹配的挂起类型 1 请求），清空七个队列（除 `+0x1c8` 之外的所有队列），并将 `+0x1c0` 和 `+0x1c4` 清零；它保留 `+0xb8` 处的请求。类型 0 请求仅由类型 7 接收器、类型 0x0D 接收器和自身离开事件完成；类型 2 由类型 9 接收器 `0x18b6710` 完成，类型 3 由类型 0xA 接收器 `0x1945404` 完成，类型 4 由类型 0xB 接收器 `0x279be18` 完成。
The own-leave path `0x12fbc3c..0x12fbc4c` 以结果 5 完成客户端的待处理类型 2 请求（`+0x40..+0x43 = 02 00 01 05`），因此下一个创建者可替换它。仅针对 master 的 id 的离开事件只会调用 `0x12fbef0`。客户端的 BoxTrade 作业在 15 秒时以结果 4 结束（状态 5 的时钟测试 `0x1e51c74`，基址 `+0x108`），但它的超时路径 `0x1e51d50` 和析构函数 `0x1e51740` 都不触及中继的请求：请求在 `+0xb8` 保持待处理，`0x2799b10` 和 `0x18ab83c` 拒绝，直到类型 9、类型 0x0D 或客户端自身的离开事件完成它。

中继一直存活到应用程序退出，因此 `+0xb8` 处待处理的请求会存活过每个席位、搜索和菜单，直到某个完成器运行。其持有者 `0x4739430`（GOT `0x46da9c0`）仅由创建者（`0x165a2b4`）、从中继自身的销毁槽（`0x279d5ac`、`0x2b71660`）到达的重置 `0x279d610` 以及静态析构函数 `0xa15f74` 写入。Vtable `0x44e56f8`：槽 0 `0x279a7b0`、3 `0x279d5ac`、4 `0x12fbb90`；接口 `+0x28` 为监听器 thunk `0x2b71650`。创建者在终结器列表 `0x4763a18` 中用 `0xf0ba9c` 注册它，该列表仅在应用程序 finalize（`0x20e9c78`，最终进入 `nn::account::CloseUser`）时遍历。

### 打开通道

| 时间 | 站点 | 端口 | 字节 | |
|---|---|---|---|---|
| 0.29 | 主机端 | 1 | 31，INITIALIZED | `b90104b902b9027b0001b902b902320101b902b902320201b902b902320301` |
| 1.84 | 加入方 | 1 | 31，INITIALIZED | 相同的 31 字节 |
| 2.43 | 加入方 | 2 | 15，INITIALIZED | `03b90200bc09000000000000000000` |
| 9.00 | 主机端 | 1 | 11 | `b90101b902b90280800001`，加入方发回相同内容 |

端口 1 是通道表（阿尔宙斯机制）：站点只有在对等方已宣告某个键后才会在该键上发送。加入方的表与主机方的表逐字节相同；在它到达之前，主机方停留在搜索画面。主机方的键 0x80 打开必须先发生：交易画面先于它绘制的加入方永远不会发送其第一条游戏消息，对宝可梦按 A 也不会出现菜单。0x7C 可靠头为九个字节，无位图，sequence 和 lowest pending 都是消息自身的值；打开的标志为 0x0F，之后更新为 0x07。

稍后打开会让模拟的《朱》4.0.0 交易箱没有选择光标。截止时间取决于对等方：对于在座位绘制菜单后 9.15 秒打开自己的键 0x80 的零售主机，主机方在 6.0 秒打开可接受，在 11.0 秒打开则不行。

### 交易

端口 0 承载游戏：四字节头部和正文。

| 时间 | 站点 | 正文 | |
|---|---|---|---|
| 9.15 | 加入方 | `80000100`，两个 zlib 片段 | 第一条游戏消息 |
| 9.31 | 主机端 | 相同的消息 | |
| 58.2 | 主机端 | `80000200` + 348 字节 | 提供的宝可梦 |
| 67.6 | 加入方 | `80000200` + 348 字节 | |
| | 任一方 | `8000040100` | 取消（接收方 `0x1e68678`）：玩家退出了等待 |
| 112.7 | 主机端 | `80000300` | |
| 116.0 | 加入方 | `80000300` | |
| 117.5 | 加入方 | `80000500` | |
| 117.5 | 主机端 | `80000500` | |
| 117.6 | 双方 | 端口 1，`b90101b902b90280800101` | 打开下一个键的表更新 |
| 117.7 | 双方 | `80010103`，`80010203` | |
| 117.8 | 双方 | `80010106`，`80010206` | |
| 118.2 | 双方 | `8001010b`，`8001020b` | |
| 118.9 | 双方 | `8001010e`，`8001020e` | |
| 119.2 | 双方 | 端口 1，`b90101b902b90280800100` | 关闭它的表更新 |

主机端只有在站点宣告键 0x80 之后才会发送其第一条游戏消息四次（两个片段，然后在接下来的两个 id 下再次发送，标志 `0x1b`、`0x15`、`0x13`、`0x15`）。如果在此之前发送，端口 0 上不会分发任何内容；如果作为两条发送（如同配对中的主机端发送给其克隆体那样），站点会回复 `ack_id` 5、`lowest_pending` 5（配对中的加入方：4 和 3），游戏永远不会看到下一条消息，游戏机停留在“等待回应”（`--send-on-open`）。

主机端在 0x7C 上的 ack 的 `lowest_pending` 字段携带其自己的下一个序号，与 0x81 上一样。比站点最后序号大 1 的值反而会让站点等待该序号，并在 `0x6f03cc` 丢弃主机端发送的下一条、更小的消息（[接收方静默丢弃的内容](pia.md#what-the-receiver-discards-in-silence)）；编号在提交处分叉，站点先提交。`8001` 步骤成对运行，01 和 02 在第四个字节按 03、06、0B、0E 步进；交易在它们之上进行，两个画面都返回交易菜单。

在 `bin/sv_host.py` 下，主机端的交易流消息编号为 5（提供）、6（确认）、7（提交）、8 至 15（步骤）；游戏机的为 5、6、7 和 8 至 11，其键 0x180 打开和关闭对应其端口 1 的消息 3 和 4；它对主机端提供的 ack 显示 `ack_id` 6、`lowest_pending` 5。两个完全相同的训练家也可以交易。

### 在站点自己的提供之前发送的确认

当提供 `80000200` 仍在排队时，绝不要发送确认 `80000300`：按该顺序收到它们的零售主机会因系统错误而崩溃。在两个启动器上都使用 `--offer-after-open` 会让提供挂在对等方的键 0x80 宣告上，并且两者都不会把一条交易消息排在已经为同一站点和端口排队的消息之前。

### 同一次入座中的多笔交易

键 0x0080 保持打开；键 0x0180 每次交易打开和关闭。第二次交易重复该循环，序号继续递增（主机端提供 16、确认 17、提交 18、步骤 19 至 26），没有新的关联、Session 交换或身份。`TradeStage` 和 `JoinerTradeStage` 接受记录列表，每次交易一条；`--trade-offer` 可重复。席位是否能在游戏机请求主机迁移后存续尚不清楚。

### 第一条游戏消息及其携带内容

`80 00 01 00` 和 2557 字节，分为两个可靠片段，先 START 后 END（来自配对主机端 238 个压缩字节，来自零售主机 195 个），每个片段都是自己的 zlib 流（`484b`）；消息是两个解压结果连接而成：

    b9 02          a tuple of two fields
    bc 81 f6 09    a blob, 0x9f6 = 2550 bytes
    ...            2550 bytes
    04

该 blob 是 850 个小端三字节值，大多为 1，其余为位掩码（`0x0fffff`、`0x0002ff`、`0x00003f`、0），按站点区分（零售主机与配对主机端之间有 38 项不同；第 36 项：`0x040000` 对 `0x0fffff`）。该索引计数的是什么尚不清楚。它不携带任何训练家字段：零售主机的消息中既不出现 ID 对也不出现名字。配对主机端的四个片段，重放后会被零售主机接受。

### 交易消息携带的记录

`80 00 02 00` 消息的 348 字节正文是常量 `bc 81 58 01` 加上第八世代加密（`pokeldn/gen8.py`）下的 344 字节第九世代同行记录（PKHeX 的 PK9）：从 0x08 开始的四个 0x50 字节块按 `(EC >> 13) & 31` 置换，对 16 位字进行的 LCG `seed = seed * 0x41C64E6D + 0x6073`，以及解密正文到 0x148 为止的 16 位校验和。0x148 处的同行尾部在置换和校验和之外，并用加密常量重新播种 LCG。

    0x000  u32  encryption constant, in the clear
    0x004  u16  sanity, 0 on every record measured
    0x006  u16  checksum, in the clear
    0x008       four 0x50-byte blocks, encrypted and permuted        -> 0x148
    0x148       level, a pad byte and the six stats, encrypted       -> 0x158

字段映射为 PK9 的 [`PKHeX.Core/PKM/PK9.cs`]；`pokeldn/gen9.py` 读写它。

| 偏移 | 字段 | | 偏移 | 字段 |
|---|---|---|---|---|
| 0x08 | 物种，内部索引 | | 0x8A | 当前 HP |
| 0x0A | 携带物品 | | 0x8C | 六个 5 位个体值，然后是蛋与昵称位 |
| 0x0C | 训练家 ID、秘密 ID | | 0x90 | 异常状态 |
| 0x10 | 经验值 | | 0x94 | 太晶属性，原始与覆盖 |
| 0x14 | 特性，其次数在 0x16 的位 0-2 | | 0xA8 | 现训练家姓名，26 字节 |
| 0x18 | 标记 | | 0xC2 | 现训练家性别、语言，当前现训练家在 0xC4 |
| 0x1C | 性格值 | | 0xC6 | 现训练家 ID、亲密度、回忆 |
| 0x20 | 性格，能力性格 | | 0xCE | 版本、对战版本 |
| 0x22 | 位 0 为命中注定，位 1-2 为性别 | | 0xD0 | 形态参数 |
| 0x24 | 形态 | | 0xD4 | 附着的奖章，语言在 0xD5 |
| 0x26 | 六个努力值，HP 攻击 防御 速度 特攻 特防 | | 0xF8 | 初训家姓名，26 字节 |
| 0x2C | 六个华丽大赛数值 | | 0x112 | 训练家亲密度和回忆 |
| 0x32 | 宝可病毒 | | 0x119 | 蛋日期，相遇日期在 0x11C，服从等级在 0x11F |
| 0x34 | 奖章和证章标志 | | 0x120 | 蛋地点，相遇地点 |
| 0x48 | 身高标度、体重标度、尺寸 | | 0x124 | 球种 |
| 0x4B | DLC 招式记录标志 | | 0x125 | 相遇等级在位 0-6，训练家性别在位 7 |
| 0x58 | 昵称，26 字节 UTF-16LE | | 0x126 | 极限特训标志 |
| 0x72 | 四个招式，PP 在 0x7A，PP 提升在 0x7E | | 0x127 | HOME 追踪器 |
| 0x82 | 四个回忆招式 | | 0x12F | 基础游戏招式记录标志 |

从 344 个零字节和 `read` 报告的字段重建的记录可以逐字节一致还原（`tests/test_sv_pokemon.py`）。物种是内部索引，在 917 处与全国图鉴分道扬镳 [`PKHeX.Core/PKM/Util/Conversion/SpeciesConverter.cs:92`]。错误的块顺序仍能通过校验和；读起来像一只连贯宝可梦的记录可确定它。`bin/sv_host.py` 打印双方的提供，`--offer-out FILE` 写入游戏机的提供（第一条之后的第 N 条提供用 `-N` 写入 `FILE`，放在扩展名前），`--trade-offer` 接受 344 字节记录（明文或加密）、348 字节正文或 352 字节消息。

### 组合记录

通过 `pokemon.build` 从零字节组合的记录，或用 `bin/sv_host.py --offer-set`（昵称、昵称标志、性格值、个体值）编辑的记录，交易进零售《朱》存档后每个摘要字段都与组合时一致。交易画面绘制组合记录时不做合法性检查；主机端写入校验和。摘要中的训练家 ID 为 `(TID16 | SID16 << 16) % 1000000`（12345 和 54321 显示为 993401，8131 和 64817 显示为 855043）；特征描述行来自加密常量和个体值。

等级跟随经验值：0x148 字节为 100 且经验值为 0 时到达为等级 1，1,000,000 经验值为等级 100。六条成长曲线（`PKHeX.Core/PKM/Util/Experience.cs`）在等级 100 时需要 1,000,000、600,000、1,640,000、1,059,860、800,000 和 1,250,000。物种表 `personal_sv`（每个物种和形态 0x50 字节，`PersonalInfo9SV.cs`）在 0x00 保存种族值，0x0C 为性别比例，0x0F 为成长曲线，0x12 为三个特性（物种 132：曲线 0，特性 7、7、150）。接收方游戏重新计算同行能力值：

    HP    = (2 * base + IV + EV/4) * level / 100 + level + 10
    other = ((2 * base + IV + EV/4) * level / 100 + 5) * nature

一只个体值完美、无努力值、性格无修正的百变怪在等级 1 时从零状态字段显示 12 和 6 x5，在等级 100 时显示 237 和 132 x5；等级 1 发送的 HP 99/99 到达后为 12。

### 加入方按顺序发送的内容

配对中的加入方在游戏的第一条消息之前，来自一次捕获的时间：

| 时间 | 消息 |
|---|---|
| 0.04 | Session 加入请求 |
| 0.17 | Net 0x12，回显主机端 0x11 的序号 |
| 0.38 | Net 0x51，回显主机端 0x50 的序号 |
| 1.63 | Session 类型 6，确认站点更新 |
| 1.68 | 十一个批量确认，以及 0x81 端口 0 和 4 上的流打开 |
| 1.68 | 0x7C 端口 1 上的通道表 |
| 1.82 | Clone Clock 0x77，十八个零字节；主机端回复 1、十六个字节、一个尾部字节 |
| 2.03 | 它自己在 0x81 端口 1 上的 44 条记录 |
| 2.43 | 0x7C 端口 2 上的打开 |

未得到应答时，游戏机会重复 Net 0x11 和 0x50；0x12 和 0x51 会停止它们（没有它们时一次入座有 212 条 Net 消息，有它们时为 2 条）。

### 交易中加入方一侧

配对加入方的整个 0x7C 脚本，每条消息的序号在其端口上：
| 端口 | 序号 | 消息 |
|---|---|---|
| 1 | 1 | 频道表、主机的四把密钥、INITIALIZED |
| 2 | 1 | 类型 3 加入、`03b90200bc09` 和九个零字节 |
| 0 | 1 到 4 | 第一条游戏消息，重复两次 |
| 1 | 2 | `b90101b902b90280800001`，密钥 0x80 打开，在第四个片段之后 |
| 0 | 5 | 提供的宝可梦 |
| 0 | 6 | 确认 |
| 0 | 7 | 提交，先发送 |
| 1 | 3 | `b90101b902b90280800101`，密钥 0x0180 打开，在主机自己的之后 |
| 0 | 8 到 11 | 每一步 `8001 01 SS` 的回显（03、06、0B、0E）；`8001 02 SS` 没有 |
| 1 | 4 | `b90101b902b90280800100`，关闭 |

身份消息在主机密钥 0x80 打开后 0.15 秒发出，加入者自己的打开则在那之后 0.21 秒。

`lowest_pending` 规则同样约束加入者：它自己的 0x7C 上的下一个序号，以及其 0x81 批量确认中比最高记录 id 大一的那个序号。来自主机编号的一个数字会让主机的接收基准越过加入者稍后的消息，这些消息在 `0x6f03cc` 处被丢弃。

`pokeldn.sv.trade.JoinerTradeStage` 是这一侧的状态机，由 `bin/sv_join.py --trade-offer` 运行（`--send-on-open` 用于在密钥 0x80 打开时才发送身份片段）。`tests/test_sv.py` 用成对消息中主机的那一半驱动它，并钉住加入者那一半。

### 一次交换会改写什么

一条组合记录被交换到零售机上再被提供回来时，有 27 个字节、七个字段不同：

| 字段 | 发送时 | 返回时 |
|---|---|---|
| `current_handler` | 0 | 1 |
| `ht_name` | 空 | 该主机玩家的名字 |
| `ht_language` | 0 | 接收主机的语言（3，法语） |
| `ht_friendship` | 0 | 50 |
| `nickname` | 空 | 该主机语言下的物种名 |
| `current_hp` | 0 | 计算出的最大 HP（237，一只 100 级百变怪） |
| `stats` | 零 | 游戏计算出的六项 |

其他所有内容都按发送时原样保留。空名字返回时会变成物种名，与《剑》神秘礼物记录（`docs/swsh_gift.md`）中的情况一样。

如果一条记录的初训家是接收存档的玩家，则会保持 handler 为 0 且没有 handler 名字，就像在传说 Z-A 中一样（[交换写入接收记录的内容](za.md#what-the-trade-writes-into-a-received-record)）。为零售《紫》的玩家制作的神秘礼物宝可梦，来自该存档捕获的宝可梦（[为接收玩家制作](gift_simulated.md#made-for-the-receiving-player)），从该机返回时也是如此。

### 加入正在搜索的主机：一次交换，以及席位由什么决定

`bin/sv_join.py` 与一台正在其连接交换搜索中做主机、并作为双人加入者编号的零售《朱》进行交换。它把站点更新当作席位，用类型 3 加入回应主机的公告，在主机打开密钥 0x80 后发送四条身份消息，并应用上面的 `lowest_pending` 规则。

#### 什么决定席位

一台从其搜索发起主机的零售主机，要么运行游戏，要么把主机角色交给它的加入者。游戏在 3 到 7 次浏览尝试后主持一次（`RandomMatchingSeq` `0x26e182c`，计数器 `rand%5+4`），并等待一名成员 3000 + rand%1000 毫秒，每有一名成员加入再加 5000 毫秒（WaitMember，`0x26df898`）。超时的等待会以 JoinRandomRecover `0x26f507c` 结束，后者通过 `LeaveMeshWithHostMigrationJob`（[离开](#leaving)）离开会话，把角色交给 Net 排名最低的站点（`0x6a012c`）。在 WaitMember 内被接受的加入会让游戏运行；在它之后被接受的加入则得到类型 7。主机玩家在公告后退出也会发送类型 7。

交出角色的主机会销毁自己的网络并再次浏览。`--take-host`（默认）会让 `bin/sv_join.py` 在公告之前收到类型 7 时，在席位的频道和代码上以应用的主机标志运行 `bin/sv_host.py`，就像 `bin/pla_join.py` 对传说 阿尔宙斯所做的那样。

在运行游戏时，该主机会按顺序发送：

| | |
|---|---|
| 席位 | 一条命名加入者变量 id 和其请求所声明玩家 id 的类型 5 站点更新，然后是 41 字节的加入响应 |
| 它的开场 | 所有 11 条流上的批量确认，0x81 端口 1 上的一条 11 字节记录和端口 5 上的另一条 |
| 它的身份 | 0x81 端口 0 上的 46 条记录，并且它确认加入者的 44 到 47 条 |
| 它的频道表 | 0x7C 端口 1 上，密钥 `0x007b`、`0x0132`、`0x0232`、`0x0332` |
| `0db90101` | 0x7C 端口 2 上，代码 1，仅用于回应在公告之前发送的类型 3 加入 |
| 公告 | 0x80 端口 2 上，zlib，解压后 167 字节：一个类型 7，kind 1，容量 2，以及该主机的站点 id |

加入者用类型 3 加入回应公告（`--port2-now` 改为随频道表一起发送它）。单凭站点更新就是席位：绝不要等待加入响应。

## 离开

退出座位的主机按角色运行两个 Pia 作业之一。每个作业都会等待对端，并在计时器超时后放弃。

加入的主机运行 `LeaveMeshJob`。`SendLeaveRequest` `0x6db590` 发送 Session 类型 3 离开请求（布局见 [docs/pla.md](pla.md#leaving)）并设置 500 毫秒期限（`0x6db6a0`）；`WaitLeaveResponse` `0x6db7b0` 在到期时重发，并在第四次发送后（`[job+0x6c]` 超过 2，`0x6db8e8`）或 `[job+0x69]` 一置位即完成。Session 派发器（`0x6d4960`、表 `0x3c0cd3b`、类型 0 到 0xA）将类型 4 交给 `0x6d7b10`，后者会针对一条 17 字节消息置位 `[job+0x69]`，该消息的字节 5 至 16 是该站点自身的定位 ID：

    04 | u32 random | location id (12), copied from the request

主机的类型 3 处理器 `0x6d7894` 在按常量 ID 和变量 ID 找到该站点后，会写入完全相同的消息（类型字节位于 `0x6d7a50`，从 `0x6c70a8` 新取一次 xorshift 随机数，并在 `0x6d7ad8` 发送）。未收到应答时，零售主机大约每 0.5 秒发送一次离开请求，并在第一次发送后约 2 秒解除认证；收到应答时，则在应答后约 0.04 秒解除认证。`bin/sv_host.py` 会应答第一个请求（`--no-leave-response` 会让它保持未应答）；`tests/test_sv_departure.py` 在 unicorn 下将应答送入 `0x6d7b10` 运行。

从搜索开始主持的主机会把主机角色传递下去。`LeaveMeshWithHostMigrationJob` 向下一个主机发送 Session 类型 7，并每隔一秒重发（`0x6df050`），直到类型 8 指定该站点（`0x6ded94`），5 秒后放弃（`0x6defb8`）。类型 7（写入器 `0x6d8de0`）为 34 字节：

    07 | host location id (12) | 00 | host IPv4, port | next host's location id (12) | u16

最后一个 u16 是该作业的 `+0xe0`（`0x6d8ea8`）。然后，`NetDestroyNetworkJob` 以其主机迁移形式等待，直到每个客户端都收到连接状态更新（最多 4 秒，`0x6ac68c`），每 300 毫秒（`0x6aca98`）发送 NetStartHostMigration `01400000`（仅由 `0x69d310` 写入，且仅从 `0x6aca54` 调用），直到网络的站点计数为 1（`0x6acaf4`）或超过期限（4 秒；当更新等待超时时为 2 秒，`0x6ac984`），然后销毁 LDN 网络。在线路上，该更新是 Net 0x11 且 is-migrating 置位；在加入方发送 Net 0x12 后，第一个 NetStartHostMigration 在 45 毫秒后出现。客户端在 NetStartHostMigration 时启动哪个作业尚未追踪；`NetHostMigrationJob` 以 DisconnectNetwork 或 EmulateDisconnection（`0x6a93c4`）开始。

持有座位的加入方会在约 4 秒内收到 NetStartHostMigration。`bin/sv_join.py` 在收到第一个时离开（`--stay-on-host-migration` 会保持座位）。

交换完成后，当主机离开时两个启动器都会退出。未完成任何交换的座位会让 `bin/sv_join.py` 恢复扫描（[结束一次运行](architecture.md#ending-a-run)）。

## 未解决的问题

- 哪个门控拦住了一台已加入 `bin/sv_host.py`、确认了公告却没有发送端口 2 加入的主机。该加入只由 BoxTrade 状态 4（`0x1e51c40`）产生。在此之前，状态 1 无定时地等待两个完成的身份块（`0x1e51ae4`），状态 4 最长等待 15 秒，等待只有类型 7 才会创建的种类 1 中继槽位（`0x1e51c10`）；主控端或主机自身 ID 的离开事件会清空该槽位（`0x12fbc68`、`0x12fbc84`）。0x80 窗口在游戏轮询器读取公告之前就确认公告，因此该确认无法区分两者。`bin/sv_host.py --announce` 会在公告 20 秒后仍未收到 `0x7c` 端口 2 消息时指出该门控：以 `the state-1 gate` 结尾的一行会列出仍未被确认的身份记录（[流上的第一条记录携带 INITIALIZED](#the-first-record-on-a-stream-carries-initialized)），以 `the state-4 gate` 结尾的一行则表示这些记录全部已被确认；捕获会将其保存为 `port2_gate` 行。
- 主机在其玩家退出到其第一条离开消息之间做了什么：所有捕获都没有标出按钮按下。在一个加入者座位中，取消 `8000040100` 比类型 7 早 1.5 秒出现。

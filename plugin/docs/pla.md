---
title: Legends Arceus
nav_order: 8
has_children: true
---

# 传说 阿尔宙斯

宝可梦传说 阿尔宙斯（title id `01001f5010dfa000`）是一款原生 Switch 游戏，Pia 6.16-6.23 静态链接到 `main` 中。地址是更新 1.1.1 解压后的 `main` 中的偏移，布局由 `tools/switch/nso_read.py` 确定（text `0x0..0x32a5690`，rodata 从 `0x32a6000` 起，data 从 `0x401a000` 起）。

## 无线层

| | 值 |
|---|---|
| Pia 头版本 | 11（剑 4、BDSP 9、GBA 应用 15/16） |
| 头大小 | 0x1C |
| 线上的 GCM tag | 8 字节，从 16 字节截断 |
| LDN 口令 | 剑／盾的，`HGhG` 拼写（wiki 的 `HGHG` 行有误）；rodata `0x3985319` |
| Pia 游戏密钥 | `p1frXqxmeCZWFv0X`，同剑／盾和朱／紫；rodata `0x3985308` |
| LDN 本地通信 id | `0x01001f5010dfa000`，即 title id |

LDN 设置 `0x2c1e684` 在 `x3` 中接收本地通信 id（在 `0x264082c` 构造），并在 `0x2c1e880` 安装游戏密钥。头部初始化器 `0x6f0744` 把 magic 存储到对象 `+8` 处，并把 `0x0b` 存到 `+0xc`；校验器 `0x6f07d0` 检查 magic、`(byte & 0x7f) == 11` 以及长度减 0x1C 后小于 0x5a5。数据包缓冲区位于 `+0x30`（容量 0x5c0），长度位于 `+0x5f8`；字段大小来自复制赋值 `0x6f0878`：

    wire  object  size  field
    0x00  +0x08   4     magic 0x32AB9864, big-endian
    0x04  +0x0c   1     0x80 (encrypted) | version (0x7F) = 11
    0x05  +0x0e   2     destination variable id
    0x07  +0x10   2     source variable id
    0x09  +0x12   2     packet id
    0x0b  +0x14   1     footer size
    0x0c  +0x15   8     AES-GCM nonce
    0x14  +0x1d   8     AES-GCM tag, truncated from the 16 the object holds
    0x1c                ciphertext, then the plaintext footer

加密路径 `0x6f09f4` 减去 footer、用 0xFF 填充到块大小、从缓冲区 `+0x4c` 加密、通过 GCM 入口 `0x6e68d0` 写入 tag 长度为 8 的 tag（`0x6f0b24`），然后把 `0x80` 按位或进版本。

断点：socket read `0x6ff6d8`、validator `0x6f07d0`、decrypt `0x6f0b84`（在这里失败说明 key、IV 或 tag 有误）、`LdnBackgroundProcessJob::WaitConnected` `0x7015b4`。

分发依据是数据包的源 variable id：来自注册表中缺失站点的消息会被跳过，而且 variable id 每个会话都会重新随机生成。消息标志 `0x01` 会跳过源 variable id 检查；`bin/pla_host.py` 会在两个探测包上都设置该标志。

## 数据包加密

| | |
|---|---|
| 会话密钥 | 对网络 SSID 的一个块执行 `AES-128-ECB(game key)` |
| 网络 id | `ssid[1:16]` 的 CRC-32 |
| GCM IV | `u32be(network id XOR source IP)` 再拼接头部的 8 字节 nonce |
| 头部 nonce | 每个数据包一个大端序计数器 |
| tag | GCM tag 的前 8 字节 |

`0x70d61c` 派生会话密钥；`LocalOutputStream::vfunc3`（`0x711710`）构造 IV。`pokeldn/ldn/crypto.py` 覆盖 6.16 到 6.42。

## 数据包之上的协议

Pia 6.16 到 6.30 保留了会话层以下的 5.29 到 5.45 id，并用一个 Session Protocol 替换了 station 和 mesh 协议：

| 协议 | 5.29-5.45 | 6.16-6.30 | 6.32-6.40 |
|---|---|---|---|
| Net | 无 | 0x2C | 1 |
| RTT | 0x58 | 0x58 | 3 |
| Unreliable | 0x68 | 0x68 | 5 |
| Clone、atomic to clock | 0x74-0x77 | 0x74-0x77 | 6-9 |
| Reliable | 0x7C | 0x7C | 10 |
| Broadcast reliable | 0x80 | 0x80 | 11 |
| Session | 0x94 | 0x98 | 13 |
| Monitoring data | 0xA4 | 0xA4 | 15 |
| Station、mesh、sync clock、local | 0x14, 0x18, 0x1C, 0x24 | 无 | 无 |

`pia_connect.py` 适配这个频段，并对 id 重新编号。主机的 join request 列出的内容：

    Net 0x2c v0   RTT 0x58 v3   Unreliable 0x68 v1   Clone 0x74 v0   Clock 0x77 v0
    Reliable 0x7c v2   BroadcastReliable 0x80 v3   0x81 v3   Session 0x98 v0   Monitoring 0xa4 v0

消息在其载荷结束处结束；这个频段不会把消息对齐到 4 字节（5.27-5.45 会）。每一层的填充字节都是 0xFF：消息遍历会把存在字节 0x00 当作继承上一条消息字段的单字节头，因此零填充会使数据包失败（`0x74419c`）。主机会在 `0x6f0af8` 用 0xFF 预填其加密缓冲区；`0x6e6cb0` 把块大小设为 16。`pokeldn/ldn/pia6.py` 使用版本 11，`pia5.parse_messages` 读取分帧。`tests/test_pia6.py` 固定了布局、密钥派生、两个捕获的 advertisement 以及从 `main` 中读出的每个常量。

| 协议 | 头部 destination | footer |
|---|---|---|
| Session、Clone Clock、Reliable | 对方的 variable id | 无 |
| RTT、Stream Broadcast Reliable | mesh 目标 0x0001 | 接收者的 variable id，明文 |

头部中目标为对方 variable id 的 0x81 消息永远不会到达游戏。

### Net 协议

托管自身网络的主机会以 `NetUpdateNetworkConnectionStatusMessage`（0x2C 类型 0x11）开始，即 wiki 的 6.16 到 6.39 布局：

```
01 11 002a          header version 1, type 0x11, payload size 0x2a
00000002            sequence id
eb6f                host variable id, fresh every session
ac56011000020000    host constant id, ldn_constant_id of 02:00:ac:10:56:01
000000004f264487    network id, the low four bytes crc32(ssid[1:16])
01                  is network open
0002                number of stations
00                  is migrating host
...                 NetStation entries, 21 bytes each (6.39 has 22)

    NetStation  +0x00 1 migration state   +0x01 1 migration ranking
                +0x02 1 one byte where 6.39 has two (disconnection candidate, kicking)
                +0x03 18 16-byte address then big-endian u16 port (12345)
```

### Session 加入请求

一个 115 字节的 Session 类型 0：类型字节、协议数量、十个 `(id, version)` 对，然后是：

    +22  4   random, fresh on every repeat (docs/sv.md, The Session join request)
    +26  8   source constant id
    +34  2   zero
    +36  2   source variable id, fresh per session
    +38  1   NAT mapping
    +39  1   private-IPv6 flag
    +40  32  identification token, zero on a codeless join
    +72  1   address kind, 0 for IPv4
    +73  4   source IPv4 address
    +77  2   source port, 12345
    +79  8   destination constant id
    +87  2   zero
    +89  2   destination variable id
    +91  1   player count, 1
    +92  1   a flag, 1
    +93  22  one player record: id (two big-endian u64, 1 and 0), big-endian u32 name length 1,
             kind byte 1, the name, a single space

location id 为 12 字节：大端序 u64 constant id、两个零字节、大端序 u16 variable id。消息标志为 `0x01`。`pokeldn.ldn.pia6.build_session_join` 再现了它（`tests/test_pla_session_v11.py`）。

主机的 `ClusterPacketReader` 门 `0x744644`（vfunc `0x98`，在 `0x743ec0` 调用）会在其站点中查找单播数据包的源 variable id（`0x744718`），没有匹配时将其丢弃（`0x7447a8`）；目标为 0 或 1 且没有 footer 的包，或源 variable id 为 0 的包会跳过查找。join request 必须发往头部目标 0；发往主机 variable id 的 join request 在解密后会被丢弃。

### Session 加入回复

加入方在 `0x737534` 解析 ack，在 `0x7379c0` 解析 join response，这些从 `0x7353a0` 通过类型表 `0x3973f19` 分发。每个处理都会丢弃四个 id 不匹配的消息：主机的 id 是请求的 destination id，加入方的 id 则是其 source id。

ack 是类型 1，25 字节：类型、主机 location id、加入方 location id。它会设置 `JoinMeshJob+0x69` 并把截止时间 `+0x80` 延长 8000 毫秒。join response 是类型 2，43 字节：

    +0x00  1   02
    +0x01  2   protocol id 0x98 and Session version, read only when status is 3
    +0x03  1   status, 1 accepts
    +0x04  8   unread on accept
    +0x0c  12  host location id
    +0x18  12  console location id
    +0x24  2   route bytes, to self station +0x90, +0x91
    +0x26  1   station index
    +0x27  2   join order, big-endian
    +0x29  2   sequence id, big-endian

assignment 字段不校验（第一个加入方会得到路由 `00 01`、索引 1、顺序 1）。状态 1 会停止重发。当到达 `+0x29` 序列的类型 5 更新被应用时，加入完成；加入方会回复一个 13 字节的类型 6：类型、自己的 constant id、两个零字节、序列号。

### 类型 5 站点列表更新

`0x7404a8` 在 `0x73897c` 读取之前重新组装它。分片头部为 7 字节：类型、大端序 u16 序列号、数量、索引、大端序 u16 偏移（单个分片时为 3）。主体：

    +0x00  1   05
    +0x01  2   sequence id
    +0x03  8   host constant id
    +0x0b  4   host variable id as [0000, u16]
    +0x0f  1   station count, at most 0x18
    +0x10  n   IPv6 bitmap, (count + 31) / 32 * 4 bytes, little-endian words
       ...     station entries (0x739050), IPv4 form:
    +0x00  8   constant id         +0x15  2   join order
    +0x08  4   [0000, u16] var id  +0x17  1   NAT mapping
    +0x0c  4   IPv4 address        +0x18  1   private-IPv6 flag
    +0x10  2   port                +0x19  32  identification token
    +0x12  1   route byte A        +0x39  1   player count
    +0x13  1   route byte B        +0x3a  1   participant count
    +0x14  1   station index       +0x3b  ..  player records (16-byte id, u32 name length,
                                              encoding byte, name)

IPv6 站点用 18 字节地址代替 6 字节。主机为路由 `00 00`、索引 0、顺序 0。`0x738bc0` 按 constant id 更新或创建每个站点。加入后的主机会接着运行 RTT、Clone Clock 和 Stream Broadcast Reliable 流。

### 主机迁移

| 加入方 | 主机 |
|---|---|
| 用 0x12 回复 0x11 | 再次 0x11，`is migrating host` 置 1，然后大约每秒两次 `01 40 00 00`（`NetStartHostMigrationMessage`） |
| 发送 join request，从不回复 0x11 | 每 0.5 秒 0x11，然后 migrating，再 0x40，然后网络断开 |
| 回复 `NetUpdateNetworkHostMessage` | 继续重复 0x40 |

托管网络的主机离开时总是迁移（`NetProtocol+0x248`，由其构造函数置 1）：`NetDestroyNetworkJob`（`0x7069d0`）发送 migrating 0x11，等待最多 4000 毫秒接收每个 0x12，每 300 毫秒发送 0x40 持续 4000 毫秒（在未确认的 0x11 之后再过 2000 毫秒），然后销毁网络。`LeaveMeshWithHostMigrationJob`（`0x73eee4`）先轮询最多 8000 毫秒以寻找下一台主机；路由字节位于 0xfd 的站点永远不符合条件。

当主机的 WaitMember 在 join 被接受之前结束时，会出现指定接班人的类型 7，如同《朱》（[docs/sv.md](sv.md#what-decides-a-seat)）中一样；`bin/pla_join.py --join-delay 4.5` 会引出它。主机会每秒重发一次，直到收到类型 8。类型 8 处理函数 `0x739b08` 只接受第二个 location id 是本主机 location id 的 25 字节消息；当第一个 location id 等于 `+0x68` 处的目标时，`0x73f0a8` 会设置任务的完成标志 `+0xb0`：

    08 | joiner location id (12) | host location id (12)

新主机通过在同一网络代码上创建网络来完成迁移；原主机会以加入方身份加入并进行连接交换。`bin/pla_join.py` 会在收到第一个 0x40 时离开座位，并在同一网络代码和频道上运行 `bin/pla_host.py`，或使用 `--ip-join`（`--take-host`，默认开启）通过 IP 运行。

## 静默站点检查

每次 Session 更新（`0x73564c`）都会列出静默时间超过 `SessionProtocol+0xd8` 的站点，即 10000 毫秒（来自启动设置 `+0x28c`，无下限；传说 Z-A 设有 4000 毫秒下限）。再过 3000 毫秒后，主机会踢掉每个站点（`KickoutManageJob`），加入方也会将被列出的主机视为已离开。盒子画面中静默的主机大约 13 秒后会弹出同伴离开的提示。

## 游戏的读取器与前置处理阶段

游戏在 `main+0x2ca4f30`（`0x741494`）处轮询其读取器：在共享一个处理程序表的 0x7C 和 0x80 上循环。消息的前八个字节是一个由两个 u32 组成的处理程序键；匹配的处理程序接收剩余数据，未匹配的键被丢弃。0x81 上的主机数据永远不会到达这里。游戏的九个 Pia 调用点只解析 0x68、0x7C 和 0x80；0x77 时钟流量由 Pia 自身处理。

在搜索界面，表为空，每条消息都在未读状态下被清空；处理程序在流程步骤 0x1e（`0x2ca5264`）注册。

交换流程是 `0x13d5bfc`（步骤 `[flow+0xa4]`，表 `0x397c118`）。步骤 0x17 构建匹配序列（`0x26bdcac`）；步骤 0x18 轮询它和网络菜单的页面结果（`0x13de870`）。该序列的步骤：

    LoginRelayServer     looked up before the sequence is built; missing returns false
    Matching             from TradeMatchmakingConfig (0x26be354)
    DataExchangeStart    the two-round data exchange, 10.0 s deadline (0x26be3f0)
    OnCancelDataExchange
    OnSuccess            the trade scene (0x26d5f64)
    OnFailure            event 8, flow step 0x23 (table 0x397c134), the leave
    OnCancel
    Cleanup

DataExchangeStart（`0x26c5288`）在已建立的会话上启动，并在至少两个站点的记录到达后完成；超过 10.0 秒（`0x26c6a94`）后，它会以 `net_contents::p2p::ErrorLeaveAnyone`（vtable `0x416c628`，`0x26c6d30`）失败。失败会执行 `0x13d654c -> 0x13d6384 -> 0x2c43d78 -> 0x2ca0a10 -> Session::LeaveAsync (0x72a6dc)`，然后显示错误 7 对话框；主机会随迁移离开。

`Error::Timeout` 的唯一生产者是监视器 `0x2bdb754`，它在匹配的另外两个 WaitMember 步骤中被武装：25000 毫秒（`0x2bda24c`）和 `3000 + rand % 1000` 毫秒（`0x2c491b8`，目标是匹配记录的 `+0x22` 半字，在代码 00000000 下为 2）。当成员计数（`[Session+0xe0]`，Pia 会话成员列表）达到目标时，WaitMember 完成；没有任何东西会延长计时器。该列表包含本地站点和每个已接受的会话加入（在加入方上，每个类型 5 的站点）一个条目；单独的 LDN 关联或 Net 0x11 不被计入。没有成员的搜索会在该计时器上重新主持，每 2.4 到 4.3 秒创建一个带有新会话 ID 的新网络，因此加入方只有当前网络计时器的剩余时间可被计入。

### 数据交换

DataExchangeStart 等待在 Stream Broadcast Reliable（0x81）的端口 0 和 1 上进行两轮交换：每个站点用一条类型 0x0f 的消息打开流，用标志 0xa0 下的 44 字节 `0000002c ffff` 消息进行确认，并发送一条 74 字节的类型 0x1f 记录，其中携带以 `484b6264` 开头的 64 字节有效负载。该步骤在对端的第二轮记录上完成。加入方主机未经提示打开其流，并在主机之后发送其记录；主持方主机在加入方打开后首先发送。响应加入方主机打开的主持方主机会将端口 0 上的记录和端口 1 上自己的打开捆绑在一个数据包中；`bin/pla_host.py` 每次加入发送一次，若在无线传输中丢失则会以错误 7 结束。

64 字节的有效负载是 139 字节记录（`pokeldn.pla.data_exchange`）的 zlib（4 KB 窗口，级别 5）压缩结果，位于 Pia 的 StreamData 头（[协议 0x81](pia.md#protocol-0x81-the-stream-broadcast-reliable-transfer-pia-6)）下的一个块：

    +0x00  1   StreamData kind, 1: first chunk
    +0x01  1   transfer id, 0
    +0x02  1   percent delivered, 0x64
    +0x03  4   zero
    +0x07  4   big-endian u32 0x80
    +0x0b  128 the MyStatus block (PKHeX MyStatus8a): trainer id pair +0x1b, version +0x1f (47),
               gender +0x20, language +0x22, UTF-16LE name +0x2b

游戏仅将块交给 Pia（`0x753554` 位于 `0x26bfd28`）。为接收玩家制作的礼物会读取主机的训练家（`data_exchange.read_trainer`，[为接收玩家制作](gift_simulated.md#made-for-the-receiving-player)）。

块 +0x3c 是玩家的外貌，即开场 4x2 `grid_player` 的列号 + 4 × 行号（设置器 `0x1023f94`），列 2 和 3 为女性；它必须与 +0x15 处的性别一致。`data_exchange.build_record` 根据 `--gender` 发送 5（男性）或 7（女性）。块 +0x50 为 1，由初始化器 `0x10230e4` 写入。

## 维持网状网络

RTT（0x58）为 11 字节：类型、八字节时间戳、两字节目标；类型为 1 且目标为 0 的回显会被接受。

Stream Broadcast Reliable（0x81）承载 `pokeldn/ldn/reliable5.py` 窗口：9 或 13 字节的头，然后是数据，或者当数据标志清除时，为 `2 + 21 * count` 字节的批量确认（类型字节，位 0 读取；条目包含站点字节、u16 确认 ID、u16、16 字节掩码）。消费者（vf13 `0x742730`）读取自己站点索引处的条目，并要求其站点字节等于发送方的索引：例如，一个确认索引 1 处加入方的主机发送两个站点字节为 0 的条目。该 ID 通过 `0x74f0ec` 应用。主机的 0x81 消息携带序列号 1，因此主机确认 `ack_id 2`。

主机用 INITIALIZED 消息（标志 `0x0f`，序列号 1）打开其流；主机数据需要主机站点索引的目标位图位（位 1，计数 2）。

## 游戏的可靠频道

交换后，流程到达 `0x13d5cac`，它测试 `[net+0xb8] > 1`：状态 0 到 1 通过 `0x26d9170`，1 到 2 取决于 `[net+0x78]`，后者由接收处理程序 `0x26da310` 在 selector 1（`0x26da3a4`）上设置。

调度器 `0x2ca4a88` 将消息键与每个频道的 `+0x6c` 进行匹配。存在两个频道：键 `00 00 00 00 00 00 00 00` 用于交换盒（`0x26d8c2c`），`01 00 00 00 00 00 00 00` 用于阶段协议（`0x26d7aa0`）。0x7c 的端口 0 和 1 是两个 Reliable 实例；端口 1 是频道表。

两个端口都用 `reliable5` 流打开（无位图，发送到对端的可变 ID，序列号 1，以及 start、end 和 initialized 标志）；每一侧都会确认并送回相同内容：

    port 0    key eight zero bytes      body 0100        the host opens it
    port 1    b9 01 01 b9 02 b9 02 00 00 01              the joiner announces the zero key open

### 确认

`ReliableSlidingWindow`（vtable `0xc5b4d98`）在 vf12 `0x74ee1c` 中构建其确认：ID 为接收窗口的 `+0x50`，在 16 字节掩码（`0x74ef18..0x74efb8`）中，每个保留条目对应一位；当 `[window+0x54]` 被设置时为空。vf13 `0x74efbc` 解析它（`0x742da0`），要求 `2 + 21 * count` 字节且条目的流字节等于 `+0x36`，并调用 `0x74f0ec(window, station, ack_id, mask)`。发送条目为 0x5d0 字节，序列号 `+0x24`，按站点的待处理位图 `+0x2c`：

| entry sequence | pending bit |
|---|---|
| below `ack_id` | cleared (`0x74f274`) |
| equal | kept |
| above | cleared when mask bit `seq - ack_id - 1` is set, offsets up to 0x7f (`0x74f280..0x74f2a8`) |

| `ack_id` | effect |
|---|---|
| 0 | nothing (`0x74f0fc`) |
| below the base | sets `[window+0x4b8]` (`0x74f17c`, `0x74f2d0`) |
| `base + count` (`[window+0x32]`) | releases everything |
| beyond | vf6 `0x74f2e8`, a bare `ret`: ignored |
| `0xffff` | applies the whole window (`0x74f104`) |

该 ID 是累积的；掩码是 128 位小端整数的第 n 位（`pokeldn.ldn.reliable5.build_mask`）。

接收方根据每条消息的最低待处理字段（包括确认）移动其窗口基值（`0x74c250`）。切勿声明超过未确认消息的最低待处理值：其重传会落在基值以下被丢弃。

`bin/pla_host.py` 和 `pokeldn.pla.joiner` 使用 `reliable5`（`SendWindow`、`ReceiveWindow`）：保留每条 0x7c 消息直到被确认，0.4 秒后以相同序列号和一个新的 nonce 重发，最多声明自己的最低未确认序列号，确认连续运行之后的一个，按顺序传递一次。加入方的 0x81 消息每 1 秒重发一次。主机在某端口上的第一条 0x7c 消息携带序列号 1（66 中的 66）。

主机会同样地每 33 毫秒 + 1.4 × 最大往返时间（`0x74d06c`）重发 0x7c 和 0x81（`0x74c9c8`），没有重试上限，直到收到窗口内的确认或站点离开。

## 端口 1 上的频道表

0x7c 的端口 1 承载频道表：每个站点通告其已打开的处理程序键，且站点只有在对端通告该键已打开后才在该键上发送。

表对象（`0x2ca36f0`，vtable `0x41997d8`）保存自己的频道（`+0xa0`）和对端已通告的频道（`+0xd8`），每个条目为八字节键和站点掩码；帧轮询 `0x2ca82d0` 负责发送和接收。

发送方将现有频道通告为打开，将已销毁的频道通告为关闭。接收方（`0x2ca9800`）在打开时将发送方的位 OR 到对端条目中，在关闭时清除该位，并为未知键追加条目；收集器会清除零掩码条目，离开站点的位会在各处被清除（`0x2ca90e0`）。创建的频道（`0x2bcb8c8 -> 0x2ca5264 -> 0x2ca3024`）在 `+0xb8` 处保留表的接口。每个频道发送方都会询问接口槽 3（`0x2ca92e0`，通过 `0x2ca9360`）对端是否通告了其键，并且仅在得到肯定回答时才发送：如果主机在端口 1 上保持沉默，交换界面就会一直等待。

消息是游戏的带标记序列化：小于 0x80 的整数是它自身的一个字节；0x80 到 0x83 作为前缀，后跟小端 1、2、4、8 字节值（写入器 `0x2661ec4`、`0x26619cc`、`0x2661f78`）。大小表 `0x397dfcc` 为 0x84 到 0x87 分配相同宽度，0x88 四字节，0x89 八字节，0xb5 到 0xbf 一字节。0xb9 打开一个元组，后面跟着字段计数。

    b9 01  NN  { b9 02  b9 02 LO HI  01|00 }    list of NN (key as two u32, open 1 / closed 0)

| message | meaning | when |
|---|---|---|
| `b9 01 01 b9 02 b9 02 00 00 01` | trade box key open | with the port-1 open, at the trade step |
| `b9 01 01 b9 02 b9 02 01 00 01` | phase key open | after the confirmation, when `0x26d7aa0` creates it |
| `b9 01 01 b9 02 b9 02 01 00 00` | phase key closed | once the trade is written |

`pokeldn.ldn.channel_table` 构建并解析这些内容。主机对每个键的每次打开只响应一次，并让关闭消息不被回应，因此其常设条目可为下一次交换服务。

## 交换盒

在端口 0 的零键之后，处理程序 `0x26da310` 读取一个选择器和一个计数器，通过 `0x397e388` 进行切换，丢弃任何大于 7 的值，并且除非其第四个参数等于 `[net+0x88]`（即伙伴）否则中止。

    1   ready                0x26da3a4   sets [net+0x78]; the port-0 open body 01 00, once a session
    2   showing a Pokemon    0x26da3f0   stored at [net+0x98] by 0x26da1d8
    3   showing no record    0x26da430   -> 0x26d93c8
    4   offering a Pokemon   0x26da3b0   stored at [net+0xb0] by 0x26da23c, phase 0xbc := 3
    5   confirmed            0x26da43c   counter check, -> 0x26da2c0
    6   withdrawn            0x26da458   state 4|5 := 3, phase 0xbc := 2, counters moved
    7                        0x26da49c   counter check, phase 0xbc := 5

`0x26d9458` 发送选择器 2，并携带光标下的记录（来自 `0x2b65514` 的 0x178 字节），或发送选择器 3，不带正文表示空槽（`03 00`）。选择器 2 和 4 携带相同的正文；只有 4 会推进阶段。主机必须以提议回应提议：如果用显示回应提议，主机就会显示一个空的伙伴六边形。

选择器 6 撤回一个提议或确认（发送方 `0x26d9898`，计数器 `[net+0xf8] + 1`）。接收端将状态返回为 3 且不发送任何内容：被回显的 6 会取消主机的确认。

正文（`0x26dac6c`、`0x26662fc`、`0x26dacbc`）：

    0x00  1   selector
    0x01  1   counter, 0 on both record-carrying selectors
    0x02  1   0xbc
    0x03  1   0x81
    0x04  2   record length, 0x178
    0x06  376 the record

390 字节位于九字节头之下，标志 0x07，序列号 2。它只取决于存档，因此一次捕获可以重放。

该记录是第八世代实体（`pokeldn.gen8` 头、LCG、块置换、16 位校验和），具有 0x58 字节的块：0x168 存储，0x178 在队伍中。解密时按原样应用 `gen8.BLOCK_ORDER[(ec >> 13) & 31]`，加密时反转；校验和无法区分两者，但名称可以（昵称在 0x60，训练家名称在 0x110）。0x0c 处的训练家 ID 和训练家名称正是数据交换所携带的内容。

## 确认交换

交换会发送选择器 5 和 `[net+0xf8]`。发送方 `0x26d9770` 要求状态为 3 并设为 4。消费方 `0x26da2c0` 设置阶段 4，并且当状态已经是 4 时分配 `[net+0xc8]`：第二台确认的站点继续。选择器 5 和 7 将计数器降到 `[net+0xfa]` 以下（`0x26da440`、`0x26da4a0`）。然后本机在端口 1 上宣告阶段键打开，并停在阶段 5 等待，直到主机也宣告它。

`0x26d9094` 的滴答会移动 `[net+0xb8]`：

    0     if [net+0x90] is set, 0x26d9170 -> 1
    1     once [net+0x78] is set, one store of 0x200000002: state 2, phase [net+0xbc] 2
    3, 4  while [net+0xc0]: past 1.5 s on [net+0xc8] with phase 4 or 5, 0x26d9254 sends
          selector 7, state 5
    5     finished; the save is untouched until the job below

## 执行交换的任务

该任务（`0x26d9a90`，虚表 `0x416c8f8`，更新 `0x26dc71c`，执行器 `[job+0x130]`）携带提供的记录 `[net+0xb0]`。

| 状态 | 行为 |
|---|---|
| 1 | 发送阶段 3（`0x26d7d8c`）；仅在发送成功时进入状态 2 |
| 2 | 等待主机的 `02 03`（`0x26d7e5c`） |
| 3 | 设置并保存交换限制（vf `+0x50` `0x26dd910`） |
| 4, 5 | 发送阶段 6，等待 `02 06` |
| 6 | 应用交换，清除限制（vf `+0x58`） |
| 7 至 10 | 发送 `0x0b`（在状态 9 中随机等待 2 到 302 帧后），等待 `02 0b` |
| 11, 12 | 提交存档（`nn::fs::Commit`），发送 `0x0e` |
| 13 | 等待 `02 0e` |
| 14 | 成功（`[net+0xb8] = 6`）或失败（7） |

发送闸门失败的任务会在下一次更新时重试；处于状态 1 或 2 的任务没有超时，并显示 `msg_ui_box_p2ptrd_09`“正在通信。请稍候……”。它仅会因取消请求 `0x26dc640` 而结束，该请求来自场景监视器 `0x1109d00`（当发生会话错误或伙伴离开且站点数低于 2 时），或者来自模式 9。本机在等待期间没有未完成的事项：主机会重新发送其在空中丢失的十一个应答中的任意一个（端口 0 打开、两个通道打开、展示、提供、选择器 5 和 7、四个阶段）。

在状态 `0x3ff7 >> state & 1`（0 到 2、4 到 13）中接受取消。在阶段 2 到 4 取消时，执行器会先完成保存；只有设置了 `[executor+0xb0]` 时，vf `+0x48` `0x26dd5f8` 才会写入，并在状态 6 完成。在状态 1 或 2 取消的任务不写入任何内容。

## 交换限制

限制是存档块 `0x96993D83` 中位于 `[game manager+0x2b8]`（虚表 `0x40f2048`）的对象字段 `+0x70` 处的一个 u64 分钟计数。块 `0x24E0D195`（字段 `+0x78`，0x2F2 字节）保存一个标志字节，然后是最近交换进来的记录。

`+0x78` 字节标记尚未放置的收到记录：在任务状态 6 时设置（`0x10251c8`，记录位于 `+0x79`，进化形态位于 `+0x1f1`），由 `0x26dcc74` 清除——后者放置记录、将其登记到图鉴并保存。

| 位置 | 调用者 | 值 | 时机 |
|---|---|---|---|
| `0x26dd9a0` | vf `+0x50`，任务状态 3 | 10 | 在伙伴的 `02 03` 之后，两条记录中的任意一个移动之前 |
| `0x26ddaf0` | vf `+0x58`，任务状态 6 | 0 | 交换被应用时 |
| `0x26dd704` | vf `+0x48`，取消 | 10 | 仅在 `[executor+0xb0]` 设置时 |
| `0x26bd5d0` | 计时器 `0x26bd434` | 减 1 | 每 60 秒 |

状态 3 在设置 10 之后保存。在状态 3 之前停止的交换不会产生限制；在状态 3 之后、状态 6 后的保存之前停止则会在存档中留下 10。

计时器（`0x26bd434`）每 60.0 秒的 OS 滴答（`0x26bd5b4`）递减一次：游戏运行十分钟可将其清零。时钟设置不起作用，游戏关闭时的时间不计算在内。

当计数非零时，连接交换的伙伴菜单（`0x13d55fc`、`0x13d56ac`）会显示 `common/net` 的 `matching_win_03`（上次连接中断）而不是警告 `matching_win_06`。

## 阶段协议

任务在键 `01 00 00 00 00 00 00 00` 上宣告阶段，该键在任务创建时注册。宣告对象保存三个标志/半字对：

    [obj+0x94] / [obj+0x96]   own announced phase, written by 0x26d7d8c (selector 1)
    [obj+0x98] / [obj+0x9a]   the peer's, on receiving selector 1
    [obj+0x90] / [obj+0x92]   written by 0x26d7e84 (selector 2), and on receiving selector 2

接收处理程序 `0x26d7f90` 镜像发送方的行为；选择器 0 中止。消息由选择器和阶段组成。`0x26d7e5c(obj, n)` 返回 `[obj+0x92] == n` 且 `+0x90` 已设置。

选择器 2 由主机发送：只有满足 `[obj+0x78]` 后才能到达 `0x26d7e84`，而 `[obj+0x78]` 在任务创建时由 `0x26d7aa0` 设置——当该站点是会话的主机时。加入者的任务只有在主机的选择器 2 之后才会离开状态 2；只镜像选择器 1 的主机会让交换界面一直等待。

一个站点在端口上发出的每条消息（包括镜像）都占用自己的下一个序列 id；重新使用对方 id 的镜像会被确认，但一旦计数出现偏差就会被丢弃。

## 交换完成

本机宣告 3、6、0xb 和 0xe；主机各自用选择器 2 和相同阶段来应答：

    <-  0x7c p0  01 03      ->  01 03   the mirror     ->  02 03   the host's
    <-  0x7c p0  01 06      ->  02 06
    <-  0x7c p0  01 0b      ->  02 0b
    <-  0x7c p0  01 0e      ->  02 0e

动画结束后，盒子将主机玩家称为原始伙伴。八个存档文件发生变化：两个槽位中的 `main`、`main2`、`backup`，以及两个 ExtraData 文件。然后本机发送一个全新的选择器 2，主机用一个展示来应答，然后阶段键关闭，不进行回应。

## 同一会话中的第二次交换

在完成一次交换后，场景会重置交换对象（`0x26d8fd0`，位于 `0x110aa04`）：释放任务输入和记录、释放任务、状态和阶段设为 2、计数器 `[net+0xf8]` 清零。`[net+0x78]` 和 `[net+0x88]` 被保留：下一轮从状态 2 开始，不发送新的选择器 1。
场景（更新 `0x1109a68`，模式 `[scene+0xb0]`：0 盒子，5 交换，6 伙伴离开，7 和 8 会话错误，9 离开）在会话保持的情况下返回模式 0。`0x10fb178` 清除盒子控制器的有效标志，因此盒子会发送新的展示；否则只有光标移动时才发送一个。

下一个任务再次使用键 1 创建其阶段通道并使用相同阶段。第二次交换逐字节重复 `05 00`、`07 00`、阶段以及阶段键打开；只有序列 id 不同，所以按消息体去重的对端不会应答其中任何一条。应答了本机关闭的主机会让第二条 `01 03` 留在闸门中：任务处于状态 1，没有超时，没有限制。

## 交换改写的内容

收到的记录与发送的记录在以下字段上有所不同（对于以 70 级队伍尾部发送的 50 级记录，共有 23 字节）：

    0x006  2   checksum
    0x092  1   current HP
    0x0b8  26  handling trainer's name, the receiver's own
    0x0d3  1   handling trainer's language (3 French, 2 English)
    0x0d4  1   current handler, 1
    0x0d8  1   handling trainer's friendship, the species' base friendship
    0x16a  12  the six party stats, recomputed

高于等级的相遇等级得以保留。块起始地址是 `pokeldn.gen8` 的起始地址加上每个前置块的八个字节：昵称 0x60、处理训练家姓名 0xb8、训练家姓名 0x110、队伍尾部 0x168。第一个块除招式（0x54，PP 0x5c）外与第八世代相同；第二个加 8，第三个加 0x10，第四个加 0x18，并将球放在相遇日期之后。`pokeldn/pla/trade_box.py` 和 `pokemon.py` 可以逐字节再现本机的数据。

## 选择要提供的内容

游戏读取 PKHeX 的 PA8：

| 偏移 | 字段 | 偏移 | 字段 |
|---|---|---|---|
| 0x08 | 物种 | 0x92 | 当前 HP |
| 0x0a | 携带物品 | 0x94 | 打包的个体值 |
| 0x0c | 训练家 ID，32 位（显示时模 1000000） | 0xa4 | 成长值 |
| 0x10 | 经验值 | 0xac, 0xb0 | 绝对身高、体重（浮点数） |
| 0x14 | 特性 | 0xb8 | 处理训练家 |
| 0x16 | 头目位 | 0xee | 版本 |
| 0x1c | 性格值 | 0xf2 | 语言 |
| 0x20 | 性格（9 是悠闲） | 0x110 | 训练家姓名 |
| 0x24 | 形态 | 0x134 | 相遇日期 |
| 0x26 | 努力值 | 0x137 | 球种 |
| 0x3e | 头目招式 | 0x138, 0x13a | 蛋和相遇地点 |
| 0x50, 0x51, 0x52 | 身高缩放、体重缩放、体型 | 0x13d | 相遇等级和训练家性别 |
| 0x54, 0x5c | 招式、PP | 0x159 | 已购买招式记录 |
| 0x60 | 昵称 | 0x15d | 精通招式位图 |
| 0x8a | 回忆招式 | 0x168, 0x16a | 等级、六项能力值 |

在 47 条捕获记录中，头目在 0x50 到 0x52 处携带 0xff，体型等于身高缩放，0x94 的蛋和昵称位为清除状态，每条记录都带有版本 47、语言 2、健全性 0 和固定缎带 0xff。`pokemon.build` 在 376 个零字节和校验和之上写入给定字段。组合出的记录（异色、头目、有昵称、存档从未拥有过的物种）可以交换进入并如发送时一样显示。存档已经持有其加密常数和 PID 的记录会被存储（盒子块 `0x47E1CEAB`）；`--fresh-pid` 会重新随机生成两者。

`bin/pla_host.py` 会按顺序一次性处理每个 `(port, sequence id)`，并重发未确认的应答；取消的提供会以 `04 01` 重新提供。它会在两次提供之间重新读取其提供文件。

### 精通招式

0x15d 处的八个字节是游戏 61 个招式精通列表上的位图；一个物种只能精通其个人条目允许的招式（0xa8 处的 u64）。“更改招式”界面允许精通等级（`mastery_la`）等于或低于当前等级、或者对应位被置位的招式。

### 游戏计算的能力值

`pokeldn/pla/stats.py` 可以复现它们。每项能力值包含一个成长项，公式为 `(sqrt(base) * multiplier + level) / 2.5` 并四舍五入，再加上一个基础项：HP 为 `((level / 100 + 1) * base)` 截断后加上等级；其余能力值为 `((level / 50 + 1) * base / 1.5)` 截断，并按性格取 110% 或 90%。乘数由成长值加上个体值偏差（31 及以上为 3，26 为 2，20 为 1）读取，上限为 10。已在 12 个主机数字上验证，68 级、性格 14、耿鬼：273/210/199/322/345/220（个体值 31，成长 10）和 239/136/121/322/304/133。

0xac 和 0xb0 处的身高和体重是物种平均值乘以 `(scalar / 255) * 0.40000004 + 0.8`（每个缩放值，体重使用两个缩放值），以 32 位浮点数表示（缩放值 111、221，平均值 150、405 得到 146.11766052246094 和 452.38031005859375）。表格来自 PKHeX：`personal_la`（每条 0xB0 字节；0x21 位 6 标记游戏中的 264 个物种）、`lvlmove_la.pkl`、`MoveInfo8a`、`Experience`。

## 克隆时钟与原子协议

克隆时钟（0x77）消息为 18 字节：类型、序列、大端 u64 起始滴答、大端 u64 应答方时钟（以毫秒为单位）。类型 0 是请求（除非是主设备，否则忽略）；类型 1 是应答，推进 ClockProtocol 的 `+0x5c`（0 复位，1 请求中，2 已同步，3 主设备，4 驻留）。加入的本机驻留在 4 并发送请求；类型 1 的应答回显序列和滴答以及主设备的时钟，使其同步。

克隆原子（0x74）消息为 14 字节：类型（0 宣告，1 提交，2 确认）、世代、大端 u32 元素索引（小于 33）、大端 u64 值。只有交换场景创建元素；主机类型 0 宣告会收到类型 2 回显，但不填充任何槽位。

## 主持

`bin/pla_host.py` 会广播标题、口令、场景 ID 和链接码；`pokeldn.pla.build_advertise_data(code)` 可以逐字节重建零售版广播（`app_version` 0，`security_mode` 1）。

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/pla_host.py --keys PROD_KEYS \
        --code 00000000 --seconds 240

搜索界面上的本机以约五秒的周期交替以站点身份进行扫描和以新的 SSID 进行主持。关联的加入者会保持静默，直到主机每 500 ms 发送一次 Net 0x2C 连接请求（`--no-net-probe` 会阻止该请求）。

## 加入游戏机的网络

`pokeldn.pla.joiner` 应答作为主机的游戏机：

| 主机发送 | 加入方应答 |
|---|---|
| Net 0x11 | Net 0x12 回显该序号，标志 `0x11`，头部目的地址 0；第一次时会发送 Session 加入请求，标志 `0x01`，目的地址 0 |
| Net 0x50 | Net 0x51 回显该序号，目的地址 0 |
| Session 类型 7 为加入方命名 | 类型 8 |
| Session 类型 5 | 类型 6 |
| 第一个类型 5 | 0x81 流在端口 0 上打开，`0f00000b 0001 0001 01 00000001 0000000000008000000000` |
| 它在端口 0 上的 0x81 记录 | ack，它在端口 1 上的自己记录（标志 `0x1f`，序号 1，位图 `0x01`），然后在 0x7c 端口 1 上打开零号密钥 |
| 0x7c 端口 0 上打开 `0000000000000000 0100` | 相同内容回传，序号 1 |
| 一次展示或一个提议 | 它自己的，相同选择器和计数器 |
| 选择器 5 和 7 | 相同；在 7 之后，打开相位密钥 |
| 相位密钥打开 | 阶段 3、6、11、14（选择器 1），每个都在主机应答之后，然后密钥关闭 |
| RTT 类型 0 | 类型 1，回显时间戳，请求者的 variable id 最后 |

一个零售加入方会向目的地址 0（108 个中的第 108 个）发送它的 0x12；发往主机 variable id 的会被读取器门丢弃。一台零售游戏机作为主机时，会在加入方之后 0.02 到 0.04 秒用选择器 2 应答每个阶段。切勿在该游戏机自己的 `01 0e` 上关闭相位密钥：`02 0e` 永远不会到来，游戏机离开时会显示 2-AW7KA-0007 并保持限制。`bin/pla_join.py` 会在 `02 0e` 上关闭它，保持座位直到玩家退出或 `--hold` 结束（`--hold-after-trade N` 会在最后一次排队交换后等待 N 秒离开），并在每次交换后忘记已应答的步骤。它大约每秒在端口 0 和 1 上重复一次 0x81 确认：

    0000002c ffff 0002 01 00000001       header: size 0x2c, lowest pending 2, bitmap 1
    00 02                                type 0 the first time, then 1; two entries
    00 0002 0001 00*16                   the host's stream
    00 0001 0001 00*16                   its own stream

## 在游戏机上进入本地交换

    title screen, A -> Jubilife Village, the trading post -> talk to Simona (Trado in French), A
    -> "echanger des pokemon !" -> local -> the restriction warning -> an eight-digit code
    -> "Echange en reseau ! Recherche d'un partenaire en cours..."

`0x397e1b8` 处的分钟表（`30 30 60 60 ... 2160 2160`）是遗失书包的（`0x2686a0c`，基于网络时钟），与交换无关。

## 广播

| | |
|---|---|
| 本地通信 id | `0x01001f5010dfa000` |
| LDN 协议 | 1：AES-CTR 广播，如同《剑》 |
| 场景 id | 1 |
| 广播帧版本 | 4（GBA 应用 3，剑 2） |
| 接受策略 | 全部 |
| 参与者 | 2 人中的 1 人 |
| SSID | 16 字节，会话密钥的输入 |
| 应用数据 | 112 字节 |

应用数据是 0x5C 系统属性块（`docs/ldn.md`，6.16 到 6.41：系统通信版本 21，应用版本 0，一个 16 字节用户密码，玩家限制开启，一个玩家，名称为单个空格），然后是明文代码：16 字节 ASCII NUL 填充，然后是其长度以小端 u32 表示（`0000 0000` 得到 `3030303030303030`、八个 NUL、8）。

### 广播中的链接码

用户密码是由 Pia 的设置器 `0x6fc454` 加密后的代码：在加密开启（session `+0x230`）且处于模式 1（`+0x234`）时，它会用 0xFE 填充 16 字节，将 NUL 填充后的代码复制到其上，并用 `0x6e68d0` 原地加密：在游戏密钥（session `+0x238`，通过 `0x6fc8a4` 设置）下使用 AES-128-GCM，无附加数据，丢弃标签，IV 为 `key[1] key[8] key[7] key[2]`（`0x6fc4e4..0x6fc4fc`），此处为 `1emf`：

    password  = KEYSTREAM XOR (the code's ASCII, NUL-padded to 16)
    KEYSTREAM = AES-128-GCM(key = p1frXqxmeCZWFv0X, iv = 1emf).encrypt(16 zero bytes)
              = e5ab19ed742b6d40885998bf968aa166

密钥流是固定的。`pokeldn.pla` 有 `link_code_keystream`、`user_password`、`link_code` 和 `parse_advertise_data`。该设置器是 Pia 的，因此这一代中的每个游戏都以此方式加密（[无线层](ldn.md)）。

如果某台游戏机上面的主机（host）重启了，该游戏机在下一次搜索时会显示错误 2318-0006；离开交换菜单并再次搜索即可清除该错误。

## 离开

退出的游戏机运行 `nn::pia::session::LeaveMeshJob`：它发送 Session 类型 3 的离开请求，等待 500 毫秒的类型 4 响应，最多发送四次，然后离开网络。步骤：SendLeaveRequest `0x73b898`（写入器 `0x737ee8`，截止时间在 `0x73b9a8`），WaitLeaveResponse `0x73bab8`（计数器 `[job+0x6c]`，在 `0x73bbf0` 处超过 3 后放弃），CompleteProcess `0x73ba54`。

    03 | u32 random | location id (12) | address kind | IPv4 (4) | port big-endian (2)
    04 | u32 random | location id (12)                          the response, 17 bytes

随机字在每次发送时都不同。类型 3 处理器 `0x738000` 应答 `04`：一个全新的随机字以及请求的第 5 到 16 字节，然后移除该站；类型 4 处理器 `0x738280` 只接受离开者自身的 id。

如果没有应答，游戏机会在四次请求（约 2 秒）后离开；如果有应答，则在一次之后离开。`bin/pla_host.py` 应答每个类型 3（`tests/test_pla_host_loss.py`，应答在 unicorn 下通过 `0x738280` 运行）。

退出、搭档离开消息以及会话错误会进入场景模式 9（`0x110b72c`）：它会放置一条待处理的接收记录，启动离开（`0x26be890`），取消作业，并等待至少 3.0 秒（`0x110b7d8`）以完成离开和作业，因此无论主机是否应答，场景画面在退出后约 3.7 秒返回。`Session::LeaveAsync` 的唯一调用者是游戏的离开请求 `0x2ca0a10`；在第一个类型 3 之前没有任何 Pia 定时器（[pia.md](pia.md)，离开会话）。

接收到离开请求不会改变屏幕上的任何内容。当游戏机处于盒子屏幕时：

| 主机（host） | 游戏机（console） |
|---|---|
| 网络断开 | 一秒内显示 "code d'erreur 2318-0006" |
| 网络开启且静默（`--leave-sends 0`） | 约 13 秒后显示 "Your trade partner chose not to continue trading"，然后 Communicating，然后 `DisconnectedByUser`，无错误代码 |

`--leave-after SECONDS` 会向每个已加入的站发送离开请求并结束运行；`--stay-after-leave` 会保持网络开启且静默。

## 未解决的问题

- 是什么填充了场景析构函数与屏幕上场景画面之间 0.4 秒的时间。
- 盒子代码中的哪些流程调用了 `0x26dcc74`（`0xc17ce0`、`0xc17e8c`）。

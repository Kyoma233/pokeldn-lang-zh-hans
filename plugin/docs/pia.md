---
title: The Pia layer
parent: The wireless layer
nav_order: 1
---

# Pia 层

Pia 是任天堂的点对点会话中间件，在所检查的所有游戏中使用 UDP 端口 12345。每个数据报都以魔数 `32 AB 98 64` 开头。Pia 版本决定头部布局：

| | 火红／叶绿（GBA 应用） | 晶灿钻石／明亮珍珠 | 剑／盾 |
|---|---|---|---|
| Pia 版本字节 | 15/16 (6.32+) | 9 (5.27-5.45) | 4 |
| 头部大小 | 0x1D | 0x20 | 0x20 |
| 变量 ID | 每项 2 字节 | 每项 4 字节 | 1 字节 + 一个半字 |
| 传输中的 GCM 标签 | | 8，从 16 截断 | 全部 16 |
| 模块 | `pokeldn/ldn/pia_connect.py` | `pokeldn/ldn/pia5.py` | `pokeldn/ldn/pia4.py` |

除非某节注明其他版本，`0x01...` 地址是《剑》1.3.2 解压缩后的 `main`（按 `tools/switch/nso_read.py` 的布局），而 `main.bin 0x01...` 地址是 BDSP 1.3.0 的。

## 数据包头部

### 版本 9（Pia 5.27-5.45）

来自 `nn::pia::common::Packet::Header`：

    0x00  4  magic 0x32AB9864, big-endian
    0x04  1  0x80 (encrypted) | version (0x7F)
    0x05  4  destination variable id, big-endian   (0 = broadcast to the mesh)
    0x09  4  source variable id, big-endian
    0x0d  2  packet id, big-endian
    0x0f  1  footer size
    0x10  8  AES-GCM nonce, a monotonic counter
    0x18  8  AES-GCM tag, truncated from 16
    0x20     ciphertext: the plaintext padded to a multiple of 16

### 版本 4

来自反序列化器 `0x01774730`（需要超过 0x1f 字节）：

    0x00  4  magic 0x32AB9864, big-endian
    0x04  1  0x80 (encrypted) | version (0x7F) = 4
    0x05  1  connection id
    0x06  2  packet id, big-endian
    0x08  8  AES-GCM nonce, a monotonic counter
    0x10  16 AES-GCM tag, not truncated
    0x20     ciphertext

这两个小字段都按目标站点区分，在发送给所有站点的数据包中为 0；零售版《剑》在这两个字段中都发送 0，因此能通过所有接收路径。

- 连接 ID：接收方（`0x017bdbd0`）会丢弃与其所持有的 ID 不相等、等于或大于 2 的 ID；0 和 1 会通过。
- 数据包 ID：接收方（`0x0185dd20`）将 0 视为无序传递，并丢弃来自相同站点的、不高于上一个 ID 的非零 ID。

在头部以下，版本 4 与版本 9 共用会话密钥、IV 和分帧。

### 版本 11：接收方会丢弃什么（朱 4.0.0）

`0x6e9744` 在任何协议读取之前接受或丢弃整个数据包。设 `st` 为源地址处的站点，`V` 为接收方的变量 ID，`D` 为头部目标，`S` 为源：

| 检查 | 丢弃条件 |
|---|---|
| 发送方 | `st` 被标记（`+0x78`）或处于状态 3 |
| 目标 | `D >= 2` 且 `D != V` |
| 源 ID | `S != 0` 指定了不存在的站点，当 `D == V` 时，或当 `D` 为 0 或 1 且带有页脚时 |
| 数据包 ID，`D == 1` | 不比来自 `st` 在其目标 1 计数器（`st+0x60`）上的上一个新 |
| 数据包 ID，其他 `D` | 不比来自 `st` 在其另一个计数器（`st+0x48`）上的上一个新 |

数据包 ID 0 始终通过且不存储任何内容；否则要求 `(int16)(id - last) >= 1`，因此在相同 ID 下的重发会被丢弃。当源地址处没有站点（加入）时，不检查任何数据包 ID。零售版发送方从一个计数器为目标 1 数据包编号，并从每个接收方计数器发送单播；两者都跳过 0。

## 消息分帧

Pia 载荷携带一条或多条消息，每条消息以一个存在字节开头，说明后续有哪些头部字段。省略的字段从数据包中的前一条消息继承（`0x01853050`）。遍历在 `0xFF` 处停止，其他值不会停止：`0x00` 是一个合法的一字节头部，继承所有字段。

| 头部版本 | 读取的游戏 | 读取器 | 下一条消息开始位置 |
|---|---|---|---|
| 4 | 剑 | `0x01852da0` | 四字节倍数处 |
| 9 (5.27-5.45) | 明亮珍珠 1.3.0 | `0x159b980` | 四字节倍数处 |
| 11 (6.16-6.30) | 传说 阿尔宙斯 1.1.1 | `0x7484cc` | 载荷结束处 |
| 11 | 朱 4.0.0 | `0x6ed2d0` | 载荷结束处 |
| 16 (6.39-7.2) | 传说 Z-A | `0x256e088`；没有 `0xFF` 停止，数据包头部声明其填充 | 载荷结束处 |

站点将相同大小的消息批量打包在存在字节 0x00 之后（《朱》的零填充记录块、《明亮珍珠》的可靠消息、《阿尔宙斯》的第二个 24 字节记录）。绝对不要在 0x00 处停止遍历。`tests/test_pia_bundled.py` 固定了每个游戏的一个数据包。

版本 3（去吧！皮卡丘／去吧！伊布 1.0.2）没有存在字节：固定的 0x16 字节头部，其第二个字节必须为 1（`0x5ae7d0`），遍历在 `0xFF` 处停止。

版本 4 的头部是一个字节加上五个条件字段：

    bit 0x01  +1  message flags
    bit 0x02  +2  payload size, big-endian
    bit 0x04  +4  protocol id and a 3-byte port
    bit 0x08  +8  destination
    bit 0x10  +8  the sender's station constant id

存在字节 0x7F 给出 24 字节（版本 9：16）；位 0x20/0x40 不增加任何内容。常量 ID 是发送方 MAC 上计算的 `station_protocol.ldn_constant_id`，在这里为大端，在 Local Protocol 主体中为小端。

版本 16（Z-A）对 flags、protocol（0x04）、port（0x08）和位 0x10 各占一个字节，大小占两个字节；位 0x10 字节位于 protocol 和 port 之间（`0x256df54`）。大小为 0x590 或更大时会被拒绝。`pokeldn.ldn.reliable.parse_messages` 可读取它。

在版本 4 和 9 中，每条消息都会填充到四字节的倍数；数据包尾部为 `0xFF`。`pia4.parse_packet()` 解析继承，`pia4.parse_messages()` 按发送原样返回每个头部。当已消耗字节加上 `0xFF` 填充占满整个明文时，遍历即为正确。

### 压缩

载荷可能是 zlib 流，通过消息标志中的标记指示：5.27-5.45 中为 0x20，版本 4 中为 0x10。版本 5 的可靠头部有自己的 zlib 标志 0x10，BDSP 在某些游戏消息上设置该标志（[BDSP 的协议](bdsp_protocol.md)）。BDSP 在会话中途切换压缩。zlib 流的前两个字节作为大端半字读取，是 31 的倍数。

### 页脚

发送给多台主机的数据包会携带页脚：每个接收方一个大端半字，为其变量 ID 的低半部分，长度在头部字节 0x0f 中。GCM 标签不覆盖它：密文是 `data[0x20 : len(data) - footer_size]`（`pia5.ciphertext()`）。留下的页脚会导致认证失败，且没有其他症状。

## 会话密钥

| 网络类型 | 类 | 派生方式 |
|---|---|---|
| LDN（本地无线） | `nn::pia::local::LocalProtocol` | 在游戏密钥下使用 AES-128-ECB，对来自 xorshift128（以会话值为种子）的 16 字节进行加密 |
| LAN | `nn::pia::lan::LanProtocol` | HMAC-SHA256(游戏密钥, 一个 32 字节参数，其最后一个字节递增) 的前 16 字节 |
| NEX（互联网） | `nn::pia::nex::*` | 来自匹配服务器的会话密钥 |

### 游戏密钥

    key = cryptoKeyDataSeed                     the game's own 16-byte constant
    key[1]  = (version >> 8) & 0xFF
    key[3]  = (version >> 4) & 0xFF             version = the local communication version,
    key[7]  = (version >> 1) & 0xFF                       which the advertisement carries
    key[12] = (version >> 0) & 0xFF

`ldn_game_key()` 计算它。《剑／盾》的密钥是一个 16 字节的 ASCII 字面量，原样使用，不涉及种子和版本替换。

### LDN 会话密钥

对于 Pia 5.9-5.45：

    rnd = four SEAD draws, seeded with the session parameter from the advertisement (+0x0c),
          packed little-endian into 16 bytes
    session key = AES-128-ECB(game key).encrypt(rnd)

SEAD 用 `s[i] = (prev ^ (prev >> 30)) * 0x6C078965 + i` 进行种子初始化，并运行移位为 11、8 和 19 的 xorshift128（`pokeldn/ldn/sead.py`；`pia5.ldn_session_key()`）。对于 Pia 6.16+，会话密钥是在游戏密钥下对 SSID 进行 AES 加密（[无线层](ldn.md#hosting-for-an-emulator)）。

### AES-GCM IV

对于 Pia 5.27-5.45 和版本 4（`ldn_nonce_crc()`、`gcm_iv()`）：

    IV[0..2]  = first three bytes of crc32( network id (little-endian) || source MAC address )
    IV[3]     = source variable id & 0xFF        from the packet header
    IV[4..11] = the packet's 8-byte header nonce

明文中的 `0xFF` 填充是已知明文，可以在一个 AES 块中测试候选密钥。

## 协议

来自 `GetProtocolId`（每个 `nn::pia` 协议对象上的 vfunc4）：

| ID | 类 | 说明 |
|---|---|---|
| 0x14 | MeshStationProtocol | 连接握手；所有网格确认 |
| 0x18 | MeshProtocol | 加入、更新网格、主机迁移 |
| 0x1c | SyncClockProtocol | |
| 0x24 | LocalProtocol | 主机重新广播的更新会话 |
| 0x54 | BandwidthCheckProtocol | |
| 0x58 | RttProtocol | 往返计时 |
| 0x68 | UnreliableProtocol | |
| 0x77 | ClockProtocol | |
| 0x7c | ReliableProtocol | 可靠的滑动窗口 |
| 0x80 | BroadcastReliableProtocol | |
| 0x84 | ReliableBroadcastProtocol | 与 0x80 不同的类 |
| 0x94 | SessionProtocol | |
| 0xa4 | MonitoringDataProtocol | |

BDSP 注册了九个：0x14 v2、0x18 v3、0x1c v0、0x24 v0、0x58 v3、0x68 v1、0x7c v3、0x94 v1、0xa4 v0，这将其库固定到 Pia 5.31-5.43。

### 加入网格

站点依次通过更新会话（0x24）、连接请求（0x14）和加入请求（0x18）加入；每条消息每 500 毫秒重传一次，直到被确认。

网格消息在 0x14 上用八字节类型 5 确认进行确认，即 `05 00 00 00` 和以大端表示的确认 ID；确认 ID 是消息的最后四个字节（`mesh_protocol.ack_for()`）。主机在发送加入响应之前确认加入请求；接收方确认每个副本。

### 离开会话（Pia 6）

`Session::LeaveAsync` 运行 `LeaveSessionJob`，其 LeaveMesh 步骤在非主机上启动 `LeaveMeshJob`（在主机上是 `LeaveMeshWithHostMigrationJob`）。其 SendLeaveRequest 步骤发送 Session 类型 3 离开请求，并等待 500 毫秒以接收主机的类型 4 响应，最多发送四次。第一次类型 3 之前的任何延迟由游戏决定。

| | 传说 阿尔宙斯 1.1.1 | GBA 应用（Pia 6.39） |
|---|---|---|
| `Session::LeaveAsync` | `0x72a6dc` | `0xb1060` |
| SendLeaveRequest | `0x73b898` | `0xcacf4` |

## Local 协议（0x24）

主机大约每 100 毫秒广播一次更新会话（类型 0x11），直到每个站点都确认它：

    local message header  version 1, type 0x11, size 73
    sequence id
    network id            random, not the advertisement's network id
    host variable id      the packet header's source variable id
    host constant id
    allow participating
    node 0..7             address:port and a ranking byte each
    host migration state

Pia 消息头部为大端，这些字段为小端，其中的本地地址为大端。`pokeldn/ldn/local_protocol.py` 解析它以及版本 4 的。

### 确认

确认（类型 0x21）为 20 字节（`LocalAckMessage::Serialize`，`main.bin 0x016bc0f4`）：偏移 0 处为 `1`，偏移 1 处为类型，偏移 2 处为载荷大小半字，六个零字节，偏移 0x0C 处为序列 ID，四个零字节。它的分帧方式与更新会话相同：存在字节 `0x7F`、标志 `0x11`、协议 36、端口 0、目标 0。客户端广播它；重新广播停止即为通过信号。

主机根据发送方的地址和端口（`0x016aec94`）归属确认。客户端的变量 ID 参与 IV 计算，因此它必须在一次运行内保持稳定且非零。

## 网格站点协议（0x14）

字节 0 是类型：1 连接请求，2 响应，3 和 4 断开请求和响应，5 ack，6 和 7 中继连接请求和响应（分发器：版本 4 `0x017c5f50`，BDSP `0x0154e848`）。

### 版本 9 连接请求

按顺序检查：

| 偏移 | 字段 | 失败时给出 |
|---|---|---|
| | 大小 15..949 | 丢弃 |
| 0x0 | 消息类型、连接结果、平台 id | 丢弃 |
| 0x3 | 目标固定 id，大端 u64，主机自己的 | 静默 |
| 0xB | 目标可变 id，大端 u32，主机自己的 | 静默 |
| 0xF | 协议数量，主机自己的计数 | 静默 |
| 0x10 | 这么多对 (id, version) | 版本低 → 结果 2，高 → 结果 3 |
| | 站点位置大小，大端 u16，0x20..0x40 | 丢弃 |
| | 站点位置 | 丢弃 |

协议 id 从不检查。站点位置的地址大小字节必须是 2、6 或 18；格式错误的位置读取为可变 id 0。

结果码（`0x0154f5e8`）：

| 结果 | 含义 |
|---|---|
| 2 | 请求方版本过低 |
| 3 | 过高 |
| 7 | 每个版本都匹配且第二阶段拒绝，或可变 id 已经是主机的站点之一（站点离开时清除，或由新 id 清除） |

大小：ack 8 字节，拒绝 15，断开响应 1。

### 版本 4 连接请求

处理函数 `0x017c62a0`：

    [0]     message type            1
    [1]     nat flags
    [2]     platform id             must be 9
    [3]     0 or 1; 1 means the request also names a target variable id
    [4]     target constant id      big-endian u64, the console's own
    [0xC]   target variable id      big-endian u32, checked only when [3] is 1
    [0x10]  nat location / protocol count
    [0x11]  the sender's station location (deserializer `0x0185ee20`)

没有协议列表。当 [3] = 1 时主机不回复。平台错误会回复 `02 02 09 00` 和 13 个零字节（结果 2）；之后的检查保持静默。

握手（[3] 清零）：

    ->   the console's connection request
    <-   the joiner's connection response, result 0, carrying the console's constant and variable ids
    ->   a type-5 ack
    ->   its own connection response, ~600 bytes, carrying the joiner's ids and the player's name,
         repeated until acknowledged

发送主机请求的类型 5 ack 会停止其重传（`--ack-request`）；没有它响应也会被接受。

### 连接响应要被读取必须满足的条件

类型 2 和 7 会到达 `0x017c6e70`。结果不是 2 的响应会被静默丢弃，除非：

| 字段 | 要求 |
|---|---|
| `[5]` 大端 u64 | 接收方自己的固定 id |
| `[0xD]` 大端 u32 | 接收方自己的可变 id |
| 站点位置 | 解析为它认识的站点 |
| `[0x37]`，仅结果 0 时 | 小于 5 |
| 站点状态 | 4，在发送 ack 后检查；接受时为 5 |

主机在 `[0x37]` 检查之后会 ack 响应：从未被 ack 的响应在 id、位置或 `[0x37]` 上失败。17 字节的响应会把 `[0x37]` 留在其末尾之后的陈旧缓冲区字节中；
`station4.build_connection_response(..., min_size=ACCEPTED_RESPONSE_SIZE)` 填充到 0x38 并在那里写入 1。这一层的接受不会启动其上的游戏层
（[到达游戏层](swsh_session.md#reaching-the-game-layer)）。

主机自己的连接响应就是接受；其请求每 500 ms 以相同尾部计数器重传则是拒绝；仅静默既不是接受也不是拒绝。

## 网格协议（0x18）

字节 0 减一作为 129 项表的索引（版本 4：`0x017c0c80`）；版本 4 缺少 BDSP 的 0x22 DUMMY_MESSAGE 和 0x23 DUMMY_ACK。

加入请求是六个字节：类型 1、站点索引 253（“尚未在网格中”）、一个 ack id。Pia 会重传大约十秒。

加入响应头是十六字节。拒绝是 `[1] == 0`、`[2] == [3] == 0xFF`，原因在 [4]；否则 [1] 是站点数，0xC 是大端更新计数器。站点条目：

| 版本 | 条目 | 布局 |
|---|---|---|
| 5.31-5.45 | 68 字节 | 64 字节站点位置、站点索引、大端加入顺序 |
| 4 | 64 字节 | 索引在 0x3E，没有加入顺序，最多 32 个站点 |

版本 4 在未分片时遍历 `stations` 条目，在分片时把 [6] 个条目写入槽 [7]；
5.31-5.45 在两种情况下都取 [6]。`parse_join_response(version4=True)` 遵循两条路径。

UPDATE_MESH (0x20) 大约每秒一次，列出网格中有谁；BDSP 总是发送 556 字节，未使用的席位清零，因此请遍历 `entries` 字节（`mesh_protocol.parse_update_mesh()`）。

### 主机迁移

0x18 端口 1 上的网格消息在可靠头部下到达。被指定为下一主机的站点必须应答。

| 消息 | 字节 | 处理函数要求 |
|---|---|---|
| MIGRATION_START (0x44) | `[0x44, host index, new host index]` | 大小 3，[1] 网格的主机索引，[2] <= 0x1F 且不是主机索引（`0x017c1f00`） |
| MIGRATION_RESPONSE (0x48) | `[0x48, own station index]` | 大小 2（`0x017c10ac`） |
| MIGRATION_FINISH (0x41) | `[0x41, host index, flag & 1]` | 大小 3，[1] 主机索引（`0x017c0fb0`） |

响应发往新主机，新主机广播 MIGRATION_FINISH。`pokeldn/ldn/mesh_protocol.py` 构建并解析全部三种。

## RTT 协议（0x58）

主机从每个站点进入网格时开始计时。版本 9 的消息是十三字节：

    u8   kind        0 = request, 1 = response
    u64  timestamp   big-endian, the sender's own clock
    u32  target      big-endian, whose reply this is; zero is accepted by everyone

版本 4 读取平坦的十六字节，并忽略十三字节的应答；
`rtt_protocol.response_for_v4()` 回显请求并只设置 kind。

站点用回显的时间戳应答 kind 1。主机为每个站点维护一个九样本环形缓冲区，其中位数为 RTT；BDSP 的时间戳大约以 31.36 MHz 运行。静默的站点不会被丢弃，只是不再采样。BDSP 在未收到应答时每 410 ms 请求一次，当每个环形缓冲区满后每 508 ms 请求一次（`0x015ace54`）；可靠重传间隔跟随 RTT。

## 可靠滑动窗口（0x7c）

### 版本 9（Pia 5.29-5.43）

    0x0  1  flags     1 application data, 2 message start, 4 message end, 8 is initialized,
                      16 zlib, 32 reset, 64 reset ack
    0x1  1  stream id
    0x2  2  payload size, big-endian
    0x4  2  sequence id, big-endian
    0x6  2  lowest sequence id pending ack, big-endian
    0x8  1  number of destination bits (N)
    0x9  4 * ceil(N / 32)  destination bitmap words, big-endian
            payload

N 为 0x20 或更大，以及负载为 0x5a1 或更大时会被拒绝。

当应用数据标志清零时，负载是批量确认：

    0x0  1   a bitfield, 0 in every captured ack
    0x1  1   entry count, refused at 0x21 or more
    0x2  21 * n  entries: u8 stream id, u16be ack id, u16be `ack id - 1`, 16-byte ack mask

零售主机对序列 0 和 1 的 ack：

    00 00 0017 ffff 0003 00   00 01   00 0002 0001  00 * 16

控制消息的序列 id 为 0xFFFF。`ack id` 比已接收的最高序列大 1。
`reliable5.build_ack_message()` 逐字节重现它。序列 0 的数据消息不会引起 ack；序列 1 会。

### 接收方静默丢弃的内容

接收路径（朱 4.0.0 `0x006f0330`，BDSP 1.3.0 `0x159fb98`）会丢弃消息并且仍返回成功，当：

| 消息在此情况下被丢弃 | 朱 | 仍发送 ack |
|---|---|---|
| 窗口未初始化且标志缺少 `is initialized` | `0x6f037c` | 否 |
| 序列 id 低于窗口基点 | `0x6f03cc` | 是 |
| 目标计数非零且位图缺少接收方的位 | `0x6f0430` | 否 |
| 流 id 与初始化时锁定的不同 | `0x6f0454` | 否 |
| 环形槽已被占用 | `0x6f0540` | 是 |

被 ack 的两种情况让发送方读到一个应用程序从未收到的消息的 ack。超出窗口末端的序列返回 `0x4c0d`，重组超过 `0x5a1` 字节返回 `0x10407`，无法解压的 zlib 负载返回 `0x2c03`。

流上的第一条消息将其基点设为自身的序列 id。接收方也会将其基点推进到发送方的 `lowest pending`（朱 `0x6eff24`）。发送方声明的 `lowest pending` 高于其下一个序列，会使对端丢弃这些消息并发送 ack，在朱和 BDSP 上均如此。
一个 ack 在头部和条目的第二个半字中携带发送方自身的最低未确认序列。BDSP 会在定时器上以及随数据一起，向每个活跃的对端发送所欠的 ack。

### 窗口发送给谁（Pia 6）

`ReliableSlidingWindow` 的目的地是按站点索引排列的站点指针，由 Pia 在站点加入和离开事件中填充，没有游戏代码参与（朱 4.0.0：注册 `0x6ef588`）。站点不在列表中只可能在其加入事件之前、离开之后、协议具有站点索引 0xfd 时，或注册拒绝它时（索引已被占用，或该站点已注册）。批量 ack 组合器 `0x6f2138` 读取同一个列表：ack 中的一位表明窗口注册了该站点，与发送给它的消息无关。

### 版本 4

一个头部类服务于 0x7C 和 0x80（`ReliableSlidingWindow::MessageHeader`，反序列化
`0x0184e390`）：

    0x0  1  flags
    0x1  1  stream id
    0x2  2  payload size, big-endian    refused at 0x589 and above
    0x4  2  sequence id, big-endian
    0x6  2  lowest sequence id pending ack, big-endian
    0x8  1  destination count           refused at 0x20 and above
    0x9  8 * count  station constant ids, big-endian

两个版本在计数为 0 时一致，也就是任一方发送的每条 0x7C 消息都是如此。

接收路径（`0x01859338`）会静默拒绝以下情况：负载超过 `0x57F - 8 * count`，消息长度不等于 `9 + 8 * count + size`，流 id 与该站点的窗口不同，目的地列表中没有接收方，以及第一条消息没有 FLAG_IS_INITIALIZED。标志位 5 是 RESET，位 6 是 RESET_ACK，位 0 是 APPLICATION_DATA；其他任何情况都是 ack。

主机在其第一条消息中发送标志 0x0F，之后发送 0x07。
`reliable4.build_data_message(bytes.fromhex("610000000a00"))` 重现了主机的序列 1：
`0f0000060001000100610000000a00`。

ack 负载正好是 0x260 字节，32 个 19 字节的条目：u8 流 id、u16be ack id、16 字节掩码（处理函数 `0x01859a84`；其他大小都会回复 0x2c03）。`reliable4.build_ack_payload` 用同一个条目填满每个槽。盾主机未使用的槽中保留陈旧字节：只读取被 ack 的流的条目，否则发送方会使主机的窗口溢出，从而停止 ack。

在固定的 `lowest_pending` 上不断增长的序列 id 意味着不断增长的积压。

一条消息太长无法放入一个负载时，会按连续序列 id 拆分，第一条的标志为 0x02，最后一条为 0x04，每个独立压缩的分片标志为 0x10。盾主机的对战回合日志（2074 到 2657 字节）分为两条：标志 0x03 加未更改的 1407 字节，然后标志 0x15 加作为 zlib 流的其余部分；消息是第一个主体后跟第二个解压后的内容。在模拟回环中，11 条分片消息中有 3 条的结束分片先于其开始分片到达：请按序列顺序重组，绝不要按到达顺序重组。

## 协议 0x80，广播可靠窗口

`nn::pia::transport::BroadcastReliableProtocol`。其消息是压缩的（版本 4 标志 0x10）：
带有目的地计数 1 的可靠头部和一个站点固定 id，后跟 0x260 字节的 ack 负载，解压后为 625 字节。ack 对每个站点索引有一个槽：主机填充 0..7，并让 8..31 保持零，其中 8 是加入响应中的 `max_total`。

## 协议 0x81，流广播可靠传输（Pia 6）

`StreamBroadcastReliableProtocol` 以分块方式将一个固定大小的块从某个站点传送到每个请求它的站点（朱 4.0.0，更新 `0x6f5360`）。它按与 0x7C 和 0x80 相同的截止时间重传，并且绝不会在任何目标没有 RTT 样本时进行重传。

每条消息都带有一个 11 字节的 StreamData 头（`0x6f60e8`）：

    +0  1  kind: 0 a receive posted, 1 the first chunk, 2 a later chunk, 3 to 6 control
    +1  1  transfer id
    +2  1  percent of the block delivered after this chunk
    +3  4  big-endian u32: the receive capacity in a kind 0, zero in a chunk
    +7  4  big-endian u32: the length of the data that follows
    +11    the data

一个已提交的接收会发送携带自身容量的 kind 0；已提交容量中的最小值界定了发送 API 可接受的块大小。对于超过该大小、id 为 0xff 或没有站点为该 id 提交过接收的情况，发送将被拒绝。分块大小为 `[window+0x70] - 11` 字节。

| kind | 接收方的操作 |
|---|---|
| 0, receive posted | 记录发送方的 id 和容量，或忙时用 kind 3 应答 |
| 1, first chunk | 重置已接收计数，然后按 kind 2 处理 |
| 2, chunk | 如果放得下就复制数据；接收在百分比为 100 时完成 |
| 3, busy sender refuses a receive | 重置传输 |
| 4, sender cancels | 重置传输 |
| 5, receiver cancels | 丢弃该接收方；发送方用 kind 6 应答 |
| 6, sender acks the cancel | 重置 |

控制类 kind 携带 id 0xff。当每个目标的窗口都确认最后一个分块时，发送完成。

## 协议 0x84，可靠广播传输

`nn::pia::transport::ReliableBroadcastProtocol` 承载剑／盾的交换快照：

| kind | 含义 |
|---|---|
| 0x11 / 0x12 | 一个数据分片；位于 [4] 的计数器与位于 [10] 的容量 |
| 0x19 | 传输完成 |
| 0x21 | 一个确认，携带连续基准与提前到达内容的位掩码 |
| 0x28 | 对 0x19 的应答 |

从不应答的接收方永远收不到最后三个，而发送方会持续重传。`pokeldn/ldn/broadcast4.py`。一台主机在端口 0 发送自己的传输，并在端口 1 确认对方的传输。

## 未解决的问题

- 零售版《剑》在 17 字节连接响应的 `[0x37]` 处读取、但发送方未写入的字节是什么。
- 是什么写入了版本 4 连接请求中 [1] 处的 nat-flags 字节；该字节在不同连接之间会变化。
- 实际拒绝会向等待上下文（`0x01769720`）传递哪个错误代码。

## 致谢

头部版本表、会话密钥派生与 nonce 布局来自 [NintendoClients wiki](https://github.com/kinnay/NintendoClients/wiki/Pia-Protocol)（[逆向一款 Switch 游戏](switch_re.md) 介绍了检索它的方法）。哪个派生对应哪个网络类型、`cryptoKeyDataSeed` 值及版本规则是从零售版游戏自身的代码中读出的。

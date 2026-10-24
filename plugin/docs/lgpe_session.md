---
title: The Let's Go cartridge and session
parent: Let's Go Pikachu and Eevee
nav_order: 1
---

# 去吧！卡带与会话

本页涵盖去吧！皮卡丘／去吧！伊布从卡带密钥到交换提交的内容。地址是去吧！皮卡丘 1.0.2 解压后的 `main` 中的偏移，按 `tools/switch/nso_read.py` 的布局：text `0..0xd32ba8`，rodata 从 `0xd33000` 开始，data 从 `0x1527000` 开始。

## 标题由什么构建

更新 NSP 携带 Program NCA `2b7730a9e56498bbafac2002d4908c6b`（title `010003f003a34000`，rights id `010003f003a348000000000000000007`，密钥生成 6）。每个 `nn::pia` 和 `gflnet3` 引用都在其 exefs `main` 中。

    ./.venv/bin/python tools/switch/xci_read.py "<the .nsp>" --keys prod.keys \
        --nca 2b7730a9e56498bbafac2002d4908c6b --exefs 0 --extract main
    ./.venv/bin/python tools/switch/nso_read.py main main.bin
    ./.venv/bin/python tools/switch/rtti_names.py main.bin 0xd32ba8

Pia 是静态链接的：269 个 `nn::pia` 类，2112 个命名虚方法，`nn::pia::local` 包含 `LdnCreateNetworkJob`、`LdnCreateSessionSetting`、`LdnJoinSessionSetting` 和 `LocalProtocol`。`nn::ldn` 从 nnSdk 导入，GOT 槽位 `0x15fa1e0..0x15fa2a8`。在 Pia 之上，`gflnet3` 捆绑了协议缓冲区。

## LDN 口令

    W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL

`0xf73a50` 处的 64 字节，直接使用，与剑／盾相同。`0x004db6b4` 以长度 `0x40` 将其传给 `LdnCreateSessionSetting` setter `0x5c0fb0`，`0x004dbba4` 传给 `LdnJoinSessionSetting` setter `0x5c1280`。`LdnCreateNetworkJob`（`0x5ce640`）将其存储在 +0xC4，其长度存储在 +0x104，并在 `nn::ldn::CreateNetwork` 之前构建 `nn::ldn::SecurityConfig`（`0x5ce988`，PLT 桩 `0xd31c78`）。

## Pia 游戏密钥

    p1frXqxmeCZWFv0X

`0xefd659` 处的 16 个 ASCII 字节，是剑／盾、传说 阿尔宙斯和朱／紫的密钥。当模式字段 `[x19+0x98]` 为 0 或 2 时，`0x0011a364..0x0011a384` 将其存储在 crypto setting +0x24c 处。

## Pia 头部

版本 3（wiki 的 Pia 5.11-5.17）。初始化器 `0xd122d4` 写入 `0x00000003_32AB9864`；校验器 `0xd12400` 检查 magic 和 `(byte & 0x7f) == 3`。布局为剑的版本 4，仅版本字节不同（`pokeldn/ldn/pia4.py`）：

    0x00  4  magic 0x32AB9864, big-endian
    0x04  1  0x80 (encrypted) | version = 3
    0x05  1  connection id
    0x06  2  packet id
    0x08  8  AES-GCM nonce
    0x10  16 AES-GCM tag
    0x20     ciphertext

## 消息成帧

固定 22 字节消息头（Pia 5.11-5.12；反序列化器 `0x5ae870`，写入器 `0x5aeb00`），`pokeldn/ldn/pia3.py`：

    0x00  1  flags: 1 destination is a bitmap, 2 relay needed, 4 relayed, 8 unbundled
    0x01  1  version, 1
    0x02  2  payload size, big-endian
    0x04  1  protocol type
    0x05  1  protocol port
    0x06  8  destination, big-endian: a constant id, or a station bitmap under flag 1
    0x0E  8  source constant id, big-endian
    0x16     payload, padded to a multiple of 4

## 会话密钥

`LocalProtocol` 的派生 `0x5cd560` 是晶灿钻石／明亮珍珠和剑的：一个 SEAD xorshift128，从会话参数（`0x57cfc0`）播种，四次抽取，在游戏密钥下于 `LocalProtocol+0x49c` 进行 AES-128-ECB。`pokeldn.ldn.pia5.ldn_session_key`。IV 是 pia4 的：`crc32(network id little-endian || host MAC)` 的三个字节，一个 source-id 字节 0，头部 nonce。

通告的应用数据以一个 24 字节头部开头：

    0x00  4  network id, random per session
    0x04  4  CRC32 of the user password, 0
    0x08  1  system communication version, 4
    0x09  1  header size, 0x18
    0x0C  4  session param, the key seed
    0x18     the game's application data

## 链接代码

链接代码是 NetworkInfo 场景 id，`1000a + 100b + 10c + 1`，每个选择是选择器中的索引（皮卡丘 0，伊布 1，妙蛙种子 2，小火龙 3，杰尼龟 4，波波 5，绿毛虫 6，小拉达 7，胖丁 8，地鼠 9）；SSID 保持为 `01000000000000000000000000000000`。`0x891580` 折叠这些选择，`0x978080` 计算 `10 * number + mode`（mode 1 表示交换），会话构造函数 `0x4db1e0` 将其放入 `LdnCreateSessionSetting+0x60`（`0x4db6ac`），Pia 将其复制到 `NetworkConfig.intentId.sceneId`。

同一个构造函数选择搜索方主机所使用的频道：`{1, 6, 11}[scene % 3]`，表 `0xf73a44`；`pokeldn.lgpe.search_channel(code)`。皮卡丘 x3 是场景 1，频道 6；妙蛙种子、小火龙、杰尼龟是 2341，频道 6；皮卡丘、皮卡丘、妙蛙种子是 21，频道 1。

搜索方只有在网络在它自己的频道上通告其场景 id 时才会加入该网络。`bin/lgpe_host.py --code NAMES` 在该频道上作为主机（`--channel auto` 会扫描主机所在网络）。`bin/lgpe_join.py` 不发送代码。

## 本地协议

会话状态通过协议 0x24、端口 0 发出：wiki 的 5.7-5.45 update-session 消息（`pokeldn.ldn.local_protocol.parse_update_session`），本地头版本 1，类型 0x11，八个节点：主机 `169.254.105.1` 排名 0，加入者 `169.254.105.2` 排名 1，其余为 255。消息体以小端携带主机常量 id（MAC `48:f1:eb:20:9b:22` 对应 `000048f120229beb`）；消息头以大端携带它。

## 站点协议，用于网格加入

在协议 0x14 上的连接请求，然后在 0x18 上进行网格加入。处理器 `0x5b8800` 读取 wiki 的 5.10-5.18 布局，站点协议版本 9：

    [0]     message type            1
    [1]     connection id
    [2]     version number          must be 9 (0x5b8848)
    [3]     is inverse connection request; rejected above 1
    [4]     target constant id      big-endian u64, the console's own (0x5b6830)
    [0xC]   target variable id      big-endian u32, checked only when [3] is 1
    [0x10]  inverse connection id
    [0x11]  station location        36 bytes for a joiner: no public address, zero NAT fields
    [...]   ack id                  u32, the message size minus four

零售主机运行包含逆向请求的完整序列：

    ->  connection request (is_inverse 0)
    <-  ack; inverse connection request (is_inverse 1) with the host's location
    ->  ack; connection response (type 2, result 0, padded to 0x38)
    <-  connection response, 840 bytes, repeated until acknowledged
    ->  ack

### 站点发送的连接响应

0x348 字节（解析器 `0x5b9270` 接受 0x3C）：

    0x00  1  message type 2
    0x01  1  result
    0x02  1  version 9
    0x03  1  platform 4
    0x05  8  the receiver's constant id, big-endian
    0x0D  4  the receiver's variable id, big-endian
    0x31  4  the network id, big-endian
    0x35  2  01 01
    0x37  0xC3  a PlayerInfo (`station_protocol.player_info`); its first byte must be below 5
    0x344 4  the ack id

`station9.build_connection_response`；`bin/lgpe_join.py --player-name NAME`。被给予 0x3C 字节响应的主机永远不会发送其克隆数据并离开克隆会话。

## 加入网格

在 0x18 上发送网格加入请求（`mesh_protocol.build_join_request`，本地站点索引 253）会收到 148 字节的加入响应（主机索引 0，加入者索引 1，最大活跃 2，最大总数 8），在 0x14 上确认，然后是 update mesh（类型 0x20）。随后主机持续发送 update session（0x24，以 0x21 确认）、RTT（0x58）、Sync Clock（0x1C）和 Clone（0x73）。Keep-alive 是协议 0x08，无消息体，以同样方式应答。

## RTT 协议（0x58），版本 3

共 16 字节：kind 为 [0] 处的大端 u32，发送方的 19.2 MHz tick 为 [8] 处的 u64；响应复制该 tick，kind 为 1。`rtt_protocol.build_v3`；`--no-rtt` 将其关闭。

## Sync Clock 协议（0x1C）

由主机控制的网格时钟。请求：[0] u64 tick，[8] 为零。回复：[0] 返回该 tick，[8] u64 为以毫秒为单位的网格时钟。站点从加入响应起每两秒请求一次，并加上往返时间的一半。Clone Protocol 时钟就是该时钟；被给予基于加入者自身运行时间的 clone 时钟的主机会释放 clone 并离开。`pokeldn.ldn.sync_clock`。

## Reliable 协议（0x7C），游戏数据所在之处

Pia 5.11 的头部为 24 字节；序列 id 从 0xFFFFF82F 开始。

    0x00  1  flags
    0x01  1  stream id, 3 for the game, 0 on an acknowledgement
    0x02  2  payload size, big-endian
    0x08  4  sequence id, big-endian
    0x0C  4  the next sequence id expected from the peer
    0x18     the payload

确认只是头部本身。`pokeldn.ldn.reliable3`。

## 克隆协议（0x73）

`nn::pia::clone::CloneProtocol` (`PiaCommon-5_11_4`) 承载对等方同步。每条消息以版本 3、一个类型字节（高半字节为结构，低半字节为变体）以及发送方的帧计数器（大端 u16）开头。

### 时钟同步，前两秒

双方大约每秒发送 5 次时钟请求（类型 0x11，18 字节，`0x51f9b0`），并用回复（类型 0x21，22 字节，`0x51fab0`）应答：

    clock request                              clock reply
    [4]   4  sender message count              [4]   4  sender message count
    [8]   2  destination bitmap                [8]   2  destination bitmap
    [0xA] 8  sender system tick                [0xA] 4  sender clone clock, ms
                                               [0xE] 8  the request's tick, echoed

消息计数从 1 开始，涵盖发送方的请求、回复与参与消息。位图是 `1 << 站点索引`。克隆时钟为 0 的回复会让零售机继续请求。

### 参与

在十个请求得到应答后，加入方发送参与消息（类型 0x31，10 字节，位图 0x0003）；主机回复 0x33 并发送自己的参与消息，加入方再回复 0x33。此后时钟回复变为 0x22，时钟请求停止。

### 克隆元素

克隆由克隆类型（1 到 4）、所属站点（0xFD 表示无）以及 u32 克隆 ID 作为键。双方都会发布自己的副本。

    every command message   [4] u8 clone type, [5] u8 owning station, [8] u32 clone id
    types 0x81 to 0xc4      [0xC] u32 message count, [0x10] u16 destination bitmap, then fields
    types 0xd1 to 0xf4      [0xC] the data

低半字节是命令标记加一：1 通告，2 请求，3 结束，4 锁定。`0x51c110` 通过表 `0xf769c4` 分派高半字节：

| 类型 | 附加内容 | 长度 |
|---|---|---|
| 0x8N | 无 | 0x12 |
| 0x9N | 位于 [0x12] 的 u32 时钟（毫秒） | 0x16 |
| 0xaN | 时钟以及位于 [0x16] 的 u8 计数 | 0x1a |
| 0xbN | 时钟以及位于 [0x16] 的 u32 参与者位图 | 0x1a |
| 0xcN | 时钟、计数以及位于 [0x1A] 的位图 | 0x1e |
| 0xeN | 位于 [0xD] 的 zlib 流 | 确认状态 |
| 0xfN | 位于 [0xD] 的字节，位于 [0xE] 的 zlib 流 | 带数据的状态 |

zlib 流展开为一条记录，标记 0x20：

    0x20 0x06 u16 clone id  0x01  0x00                               empty copy
    0x20 len  u16 clone id  0x03  u8 station  u16 0  u16 participants  u32 clock  data
    0x20 0x0A u16 clone id  0x05  u8 the station acknowledged  u32 clock

`clone.pack_record` 重现每一条捕获到的流（一次压缩、一次同步 flush、一个最终空块）。

| 交换 | 消息 |
|---|---|
| 所有者通告 | 0xa1 和 0xb1；对方在数据之前回复 0xa2 和 0xc1 |
| 接管 | 对方用 0x91 回复 0xa1 |
| 数据 | 所有者的 0xf3；对方用相同时钟的 0xe3 |
| 释放 | 0x83；0x84 确认 |
| 离开克隆会话 | 0x32；0x41 应答 |

0xa2 携带网状时钟和计数：克隆类型 4 上为 1，克隆类型 2 上为 0。0xaN 的字节 `0x17..0x19` 是栈残留，接收方不会读取（`01 2808ab`）。克隆类型 3 和 4 的 0xa1 处理器（`0x522a60`）用 0xa2、0x91 或什么都不回复；针对未知克隆的 0xa1 会引来 0x91。`0x51c110` 在目标不符、消息计数不高于发送方的上一条（`0x51c1e0`）、长度与类型范围不符时静默丢弃。当协议的待处理掩码 `+0xc0` 清空时，参与握手完成。

### 克隆 0 对

克隆类型 3 上克隆 0 的所有者用 0xa1 和 0xb1 通告它，并且只有在对方的 0xa2 和 0xc1 之后才发布。应答丢失的主机会让主机停留在“vous allez bientôt être connecté”；`bin/lgpe_host.py` 每 110 ms 重复这对消息，最多 20 次，直到收到 0xa2、0xc1 或 0x91。

### 通告的目标字段决定什么

首次通告某个克隆的 0x81 携带整个网状网络（0x0003）；其后的 0xa1 只携带对等方（0x0001）。由于 0x81 上的对等方位图如此，对等方不会回复 0xa2，门 `0x11b080` 永远不会通过。

### 游戏在可靠协议上的消息

`0x7c` 上的每条消息都是一个 16 字节头部和一个主体：

```
+0x00  4  kind: the channel id
+0x04  4  body length: 0x168 kind 1, 0xe8 kinds 2 and 4, 4 kind 3
+0x08  4  step, counting every message a station sends from 1
+0x0c  1  tag, 0 on every trade message
+0x0d  1  destination station index, 0xff for every station
+0x10     the body
```

`0x116f30` 构建头部；交换发送方经过 `0x4d94e0`。接收函数 `0x1171d0` 取队列中第一条 step 等于本站下一条的消息，丢弃发往他处或未注册类别的消息，并让其他类别或标记的消息留在队列中，阻塞其后的一切。

类别是来自每会话 u32 计数器（从 1 开始，`0x116e80`）的通道 ID，同时最多注册 16 个活动通道。一次交换注册 1（交换会话）、2（提供）、3（提交）和 4（交换后保存重新创建的提供对象）。每次注册都会通告一个克隆集合，因此克隆 ID 与通道 ID 不同。已死的通道每帧压缩，因此一个席位可容纳约四个，并可无限连续交换。

类别 1，主体 0x168，身份信息：存档的 MyStatus 块（PKHeX `MyStatus7b`，名称 UTF-16LE），由双方在收到任何内容之前发送：

```
+0x00  4  trainer id, then secret id
+0x04  1  version: 42 Pikachu, 43 Eevee
+0x05  1  gender
+0x35  1  language
+0x38 26  trainer name; --trainer-name on both launchers
+0x52 16  Pokemon name
+0x90  4  the trade lock
```

为接收玩家制作的礼物会在这里读取训练家（[为接收玩家制作](gift_simulated.md#made-for-the-receiving-player)）。`pokeldn.lgpe.reference` 附带一个训练家为 `POKELDN` 的示例；`--our-trainer` 会替换其 ID 对。

类别 2，主体 0xe8，提供消息，在站点的已发布状态字达到 2 时发送，并在其玩家每次更改选择时以新的 step 再次发送。新的 step 会被应答；重复的 step 是重传。用全新 step 而不是自己的 step 应答提供会开启无休止的新一轮。发送方是队伍提供对象（`0x349bf0`，位于 `mgr+0x68`），当交换状态允许时，`0x34a3d0` 会在每次选择变化时重新填充它。

类别 3，主体 4，提交（[提交与交换锁](#the-commit-and-the-trade-lock)）：每个站点发送 1，其中一方在收到对等方的 1 后发送 2。收到 2 即提交；在 1 之后的任何其他主体都会被忽略。

类别 4，主体 0xe8，搭载在常规保存在其保存后 3000 ms 重新创建的提供对象上，并在交换演示之后发送：先是站点的第一个栏位，然后每个选择发送一个。它开启下一次交换。

| step | kind | body |
|---|---|---|
| 1 | 1 | identity |
| 2 | 2 | the offer, again per selection |
| 5 | 3 | commit, 1 |
| 6 | 3 | commit, 2 |
| 7 | 4 | the first slot, again per selection |

从 0 开始计数的第 r 次交换在类别 2 + 2r 上提供，在 3 + 2r 上提交，在 4 + 2r 上结束。其队伍克隆为 2 + 3r 和 3 + 3r，其提交克隆为 4 + 3r。

| 启动器 | 连续交换 |
|---|---|
| `bin/lgpe_host.py --next-offer` | 用下一条记录回答每次后续交换的选择 |
| `bin/lgpe_join.py --offer ...` | 用下一条记录回答主机方的类别 4；最后一条之后不再回答 |
| `bin/lgpe_host.py --lead` | 为 `bin/lgpe_join.py` 扮演主机方；`tests/test_esp32.py` |

两个启动器在交换 2 时写入收到的记录；被撤回的提供不写入任何内容。

类别 2 和 4 的主体是一个 232 字节的盒子结构：采用第 6 代加密的第 7 代布局，从 +0x08 开始的四个 56 字节块按 `((ec >> 13) & 0x1F) % 24` 排列，并与以加密常量作为种子的 LCRNG 流异或。`pokeldn.lgpe.pb7`。主机不做检查地保存它：一只异色、100 级、隐藏特性、所有 IV 31 和所有 AV 200 的百变怪在摘要中显示不变。

### 什么门控游戏自身的第一条消息

连接交换对象的状态机是 `0x349200`（跳转表 `0xf4e994` 位于 +0x68）。

| 状态 | 作用 |
|---|---|
| 3 | 通告克隆 1 的集合（`0x11aec0`），将状态设为 4 |
| 4 | 等待门 `0x11b080` |
| 6 | 在没有网络输入的情况下发送类别 1 |
| 7 | 计数类别 1 消息，包括自己的环回；计到 2 时进入 8 |
| 8 | 终止；屏幕显示已找到玩家 |

当 +0x90 的 SendClone 和 +0x1258 的 SharingClone 的已确认集合 `clone+0xA8` 中包含每个参与站点，每个队伍克隆的完成字节 `+0x110` 都已设置，并且 +0x1430 处的站点索引不是 0xFD 时，门通过。某个站点的位只有通过该站点在克隆类型 2 上发来的 0xa2 才能进入 `clone+0xA8`。

`0x11aec0` 在一帧内通告站点的克隆集合：克隆类型 2 上的 `0x81`，类型 4 上的 `0xa1` 以及类型 1 上的 `0xa1`。克隆 ID 2 和 3 在 ID 1 之后大约 3.2 秒由交换调度器 `0x886530` 产生，该调度器仅在模式字 `+0x8C` 为 3 时发布；写入这个 3 的代码未知。

### 将零售主机引导至其交换屏幕

- 本地协议主体以小端序携带主机的常量 ID；若为大端序，零售机无法解析发送方，会在状态 7 等待。
- 更新会话在会话变化时发出，并在其后再次发出，从不按定时器发出。
- 主机在发布克隆 0 的同一帧通告克隆 1；零售机大约 31 ms 后通告自己的，而等待的主机会失去竞争，角色互换。
- 应答对等方对主机所有克隆的通告的 `0xa2` 携带对等方 `0xa1` 的时钟；若使用主机自己的时钟，零售机会永远重新通告。
- 双方都会用自己的副本来应答每个克隆类型 2 的发布。
- 主机必须在克隆类型 4 和 1 上发布克隆数据，否则加入方主机会停留在其搜索屏幕。

### 接管必须携带的序列

`0x520c30` 在通告时分配一个序列到 `+0x10C`；完成函数 `0x520ce0`（一个 `0xa2`）只有在值等于 `+0x10C` 时才设置 `+0x110`，而 `0x520d30`（一个 `0x91`）会取消链接但不设置它。该值是另一站点对该克隆的最新 `0xa1` 的时钟。从加入方自己的时钟构建的 `0xa2` 会错过，状态字永远不会离开 4。入站的 `0x82` 也会分配序列，因此用 `0x82` 突发应答每次重新通告会无休止地铸造序列。

### 加入方对每个克隆运行一次的接管交换

一次接管会取消对等方的通告，并在加入方自己的时钟下通告该克隆：

```
+0 ms   host    0x81 clone 2, 0x81 clone 3, dest 0x0003
        host    0xa1 x2 per clone                        clock 0x197e, the host's
+5 ms   joiner  0x82, 0x91 x2, 0x82, 0x91 x2, 0x84 x2    echoing 0x197e
+75 ms  joiner  0x81 clone 2, 0x81 clone 3, 0xa1 x2 each clock 0x19c1, the joiner's own
+102 ms host    0xa2 per clone                           clock 0x19c1
        host    0xa1 per clone                           clock 0x19e2, the host's own
+141 ms joiner  0xa2 per clone                           clock 0x19e2
```

加入方对每个克隆只接管一次。之后的每次重新通告都会收到一个携带该通告时钟的 `0xa2`，在加入方站点的克隆类型 2 上，负载为 `<clock> 00 00 00 02`；第二次接管会让对等方无限制地重新通告。

仅对等方的重新通告会引来对等方在克隆类型 1 上的 `0x82`，这又会引来主机的类型 4 副本，零售机用 `1 1 1` 应答。如果主机没有收到针对提交克隆的 `0x82`，就会停留在确认屏幕并保存交换锁；`pokeldn.ldn.clone` 每 100 ms 重发仅对等方的 `0x81`，最多 20 次，直到收到 `0x82`。

### 一次交换所走的两个克隆记录

克隆类型 2 副本的 20 字节数据：

```
+0x00  4  state: 1 a vote, 2 a vote withdrawn, 4 a forced leave
+0x04  4  argument, 1 on selection and 2 on confirmation
+0x08  4  a counter, incremented on each call
+0x0c  4  the station's own step
+0x10  4  the trailing word
```
The clone type 4 copy's 32-byte data is the session host's (the authority's) view:

```
+0x00  4  A, the agreed argument
+0x04  4  B
+0x08 16  per station index: the counter of the vote it last saw withdrawn
+0x18  4  the station's step
+0x1c  4  the trailing word
```

权威方 `0x11b6c0` 仅当每个站点在当前尾随字上发布带参数 X 的状态 1 时，才将 A 移到 X，同时发布 A 和尾随字加一；状态 4 会立即移动 A。对于处于状态 2 且参数与 A 不同的站点，它会记录计数器并将尾随字前移。仅当时钟严格更新时，记录才会替换副本；`pokeldn.ldn.clone.Participant.record_clock` 保持每条记录的时钟高于上一条。在类型 4 上发布 32 个零的主机会使主机停留在“communication en cours”界面。

交换界面的状态（`0x34a300`）来自 A 和本地状态：

| A | local state 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| 0 | 0 | 1 | 1 | 0 | 0 |
| 1 | 2 | 3 | 3 | 0 | 2 |
| 2 | 4 | 4 | 4 | 4 | 4 |
| 3 | 5 | 5 | 5 | 5 | 5 |

状态 4 开始同步保存，状态 2 返回选择界面，5 表示对方离开。

提供的同行宝可梦克隆步进为 `1 1 1`，尾随字 1，然后是 `x 2 2`，尾随字 2。提交克隆（id 高一位）先取前两个，再取一个零：

```
+0 ms     type 4 data, 32 zeros, with the announcement
          the peer publishes 1 1 1 step 0 once its player has confirmed
          1 1 1 step 0                 the host's own confirmation
+30 ms    1 1 1 step 1                 type 4 data 1, zeros, step, 1
+8 ms     the peer answers 0 1 1 step 1
+27 ms    0 1 1 step+1 1               the offered clone goes 0 2 2 step+1 2,
                                       and the kind 3 carrying 1 goes under that step
+3 ms     the peer's kind 3 carrying 1
+63 ms    kind 3 carrying 2 under the next step, every copy republished under it
after the trade demo and the normal save:
          two more clones announced, 32 zeros on type 4; the peer publishes 0 0 0 on each
then      kind 4 under the next step
```

对方仅在类型 4 副本的第一个字为 1 时回应尾随字 1。主机方控制台宣布每个克隆并率先投票；加入方接管每个克隆，并在自己的状态字下重新发布主机方的前三个字和尾随字，即可完成交换。

在确认界面再次按下 A 会撤回投票：`1 2 2` 之后为 `2 2 3`。用 A 2 回答它会提交交换锁但不完成交换（[未解决](lgpe.md#unresolved)）。回答 `1 0 0 3 0 0 step T+1` 会使主机返回选择界面；在 A 为 0 时，已撤回的选择 `2 1 4` 采用 `0 0 0 4 0 0 step T+1`。`bin/lgpe_host.py` 如此回答；`tests/test_lgpe_host_withdraw.py` 在游戏代码中运行这两种情况。

### 交换动画

主机在步骤 `0e` 之后播放交换动画，期间不发送交换载荷。从该步骤起：动画约在 1.7 秒开始，收到的宝可梦约在 15.3 秒出现，主机的类型 4 载荷（248 字节）在 27.0 秒到达，玩家约在 28.8 秒恢复控制。

### 提交与交换锁

交换锁是 MyStatus `+0x90`（`savedata.bin` `0x1090`；设置器 `0x1c9d40`）处的 u32 秒倒计时。一次交换的同步保存会将其设为 600，并在提交交换之前提交该值；交换完成后再将其提交回 0。连接菜单的检查 `0x9765f4` 会在其非零时拒绝交换（`0x976634`，消息 `0x0248810f825b1fee`）。该锁仅随游戏处于焦点时的计费游玩时间倒计时，每秒一秒，每次更新至多一秒。

`0x347190` 构建三种保存序列之一：普通保存、同步保存、致命错误。交换使用同步保存（更新 `0x838070`，跳转表 `0xf867c4`）：

| 状态 | 作用 |
|---|---|
| 0 | 等待 `SaveThread`（600 已提交），决定本站是否发送 2（`0x838660`），应用收到的宝可梦并在内存中将锁清零（`0x838800`），启动 `FirstSaveThread` |
| 1 | 等待 `FirstSaveThread` 写入，然后随机延迟 `2000 + r % 6000` 毫秒 |
| 2 | 注册提交通道 |
| 3 | 在提交克隆上投 1，等待通道的门控 |
| 4 | 发送携带 1 的 kind 3 |
| 5 | 接收对方的 kind 3；主体不是 1 则中止；发送方发送 2 |
| 6 | 收到 2 表示提交；任何其他主体被忽略 |
| 7 | 等待 `FirstSaveThread` 提交 |

所有状态都没有超时。在状态 0 结束到收到 2 之间记录的任何网络错误都会中止：`FirstSaveThread` 不提交，保存保持 600，调度器推入致命错误 `error_fatal_save`（“An error occurred. You couldn't trade Pokémon. Press the HOME Button to end the game.”，标签 id `0x191615296121e064`，位于 `common/message_error.dat`），游戏从此无法返回。对方在提交期间离开网状网络会记录此类错误。

| 对方情况 | 后果 |
|---|---|
| 权威方发布 A 2 | 主机提交 600；权威方有义务完成整个提交交换 |
| 第一个 kind 3 携带的不是 1 | 中止，锁已设置 |
| 在接收方注册提交通道之前发送的 kind 3 | 丢弃；状态 3 的投票会保持它，直到双方都已注册 |

`0x838660` 决定谁发送 2：用急冻鸟、闪电鸟、火焰鸟、超梦、梦幻、美录坦或美录梅塔交换任意其他宝可梦的一方会发送它，反过来则不发送；否则由会话开始时作为会话主机的站点（`mgr+0x128c`）发送。

`0x838800` 将收到的宝可梦写入自己提供的盒子槽位，并应用交换的副作用：宝可梦图鉴登记、交换进化（方法 5 始终生效，方法 6 需携带道具；方法 7，小嘴蜗与盖盖虫，永远不匹配，因为到达的副本被同时作为两只宝可梦传入；方法 6、19、20 会清空携带道具），以及游戏记录 476（本地交换）或 477（互联网连接开启时的交换）。

### 交换调度器

`0x886530` 运行从菜单到退出的连接，通过 `0xf87bc4` 根据 `[obj+0x68]` 切换：

| 状态 | 作用 |
|---|---|
| 0 | 设置；连接菜单进程写入模式字 `+0x8c` |
| 1 | 模式 1 或 2 开始连接对战，然后进入 6；模式 3 等待同行宝可梦提供对象准备好；网络错误进入 8 |
| 2 | `[obj+0x100]` 5，交换 UI 的继续，启动同步保存；其他情况进入 8 |
| 3 | 等待同步保存；结果 2 推入致命错误；否则销毁提供对象并开始交换演示 |
| 4 | 释放演示，状态 5 |
| 5 | 将收到的宝可梦写入盒子槽位，启动普通保存，状态 7 |
| 6 | 状态 8 |
| 7 | 等待保存；结果 1 进入 8，其他结果进入 1 |
| 8 | 销毁提供对象并离开 |

保存进程会在 `obj+0x178` 处获得一个块：

```
+0x00  save type: 0 sync save, 1 normal save, 2 or 3 fatal error
+0x04  result: 0 done, 2 aborted, 1 the link ends
+0x08  box index of the own offered Pokemon
+0x10  the received Pokemon
```

普通保存在其 `SaveThread` 之后等待 3000 毫秒，然后在新通道上重新创建同行宝可梦提供对象。调度器从状态 7 返回状态 1，因此一个座位可以接连进行多次交换。连接菜单的选项 1（交换）存储模式 3；选项 2 和 3 存储 1 和 2，即单打和双打连接对战，它们用标签 1 和 3 注册自己的通道，并计入 `local_btl_single_cnt` 和 `local_btl_double_cnt`。一次交换会计入 `local_trade_cnt`（`0x1dc`）或 `net_trade_cnt`（`0x1dd`）。

### 加入方离开

使用 Retour 退出的控制台会在已提供克隆上发布状态 4，参数先为 0 再为 3；主机方对每个的回应是：前三个字为零，尾随字加一，并将参数作为类型 4 副本的第一个字。双方会释放各自的克隆（0x83，回应为 0x84）。一旦其克隆协议空闲（[离开前的等待](#the-wait-before-leaving)），控制台会在网状协议可靠端口上发送网状网络离开请求 `04 01`。

它应当收到可靠确认，以及不可靠端口上的离开响应 `08 00`（网状网络主机的索引）。`LeaveMeshJob` 每 40 毫秒重传请求，最长 5000 毫秒。收到 `08 00` 回应后，控制台会发送自己的断开连接请求并在 0.1 秒内解除认证；未收到回应，则在 5.0 秒时解除认证。Retour 之后，主机方会发送站点断开连接请求（类型 3）；该控制台回应类型 4。

主机方控制台会对加入方的离开请求回应两次 `08 00`，然后每 0.3 秒重复一次本地协议启动主机迁移（类型 0x13）。加入方的断开连接请求会使主机方玩家返回菜单。`bin/lgpe_join.py --leave-after SECONDS` 执行退出（`pokeldn.lgpe.leave`）；`--stall-leave`（默认 5）会在任何 kind 3 之前投票尚未达成一致时执行退出。退出不会解除交换锁。

### 主机方离开

玩家退出的主机方控制台会发布状态 4，参数 3，释放其克隆，并在空闲后发送网状网络迁移启动 `44 00 01`（主机索引、下一主机索引），每 45 毫秒重传一次，最长 5000 毫秒，直到每个站点回应 `48 <index>`。然后它会广播一个携带主机迁移状态 1 的更新会话，并每 301 毫秒重复启动主机迁移（类型 0x13），直到没有其他站点连接或经过 10000 毫秒，然后销毁网络（八个 LDN 断开连接帧，原因 3）。`bin/lgpe_join.py` 会回应 ack 和 `48 01`，并在第一个 0x13 时离开（`pokeldn.lgpe.leave.host_departure`）。

### 离开前的等待

拆解步骤 `0x116bc0` 会在克隆协议空闲时立即结束克隆会话并离开；否则会等待 150 次调用，约 2.5 秒。一旦没有克隆存在未确认数据，且每个站点都用 0x41 回应了其 0x32，协议即达到空闲。在释放克隆 0 之后，控制台大约每 100 毫秒继续发布克隆类型 2 副本；对方在克隆类型 1、站点 0xFD 上用 0xe3 回应每个副本，并携带发布方的站点和时钟，可让它在 0.3 秒内进入空闲并离开。对方用自己的副本回应会使其等待完整时长。`pokeldn.ldn.clone.Participant` 会在对方释放克隆 0 之后进行确认。

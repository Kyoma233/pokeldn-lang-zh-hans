---
title: The Let's Go cartridge and session
parent: Let's Go Pikachu and Eevee
nav_order: 1
---

# 去吧！卡带与会话

本页涵盖从卡带密钥到交易提交的 Let's Go Pikachu／Eevee。地址为 `tools/switch/nso_read.py` 所布局的 Let's Go Pikachu 1.0.2 解压后 `main` 的偏移量：文本 `0..0xd32ba8`，rodata 从 `0xd33000`，data 从 `0x1527000`。

## 游戏标题的构成

更新 NSP 包含 Program NCA `2b7730a9e56498bbafac2002d4908c6b`（标题 `010003f003a34000`，权利 id `010003f003a348000000000000000007`，密钥生成 6）。所有 `nn::pia` 和 `gflnet3` 引用都位于其 exefs `main` 中。

    ./.venv/bin/python tools/switch/xci_read.py "<the .nsp>" --keys prod.keys \
        --nca 2b7730a9e56498bbafac2002d4908c6b --exefs 0 --extract main
    ./.venv/bin/python tools/switch/nso_read.py main main.bin
    ./.venv/bin/python tools/switch/rtti_names.py main.bin 0xd32ba8

Pia 是静态链接的：269 个 `nn::pia` 类，2112 个命名虚方法，`nn::pia::local` 包含 `LdnCreateNetworkJob`、`LdnCreateSessionSetting`、`LdnJoinSessionSetting` 和 `LocalProtocol`。`nn::ldn` 从 nnSdk 导入，GOT 槽 `0x15fa1e0..0x15fa2a8`。Pia 之上，`gflnet3` 打包了协议缓冲。

## LDN 密码

    W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL

位于 `0xf73a50` 的 64 字节，原样使用，与剑／盾相同。`0x004db6b4` 以长度为 `0x40` 传递给 `LdnCreateSessionSetting` setter `0x5c0fb0`，`0x004dbba4` 传递给 `LdnJoinSessionSetting` setter `0x5c1280`。`LdnCreateNetworkJob`（`0x5ce640`）在 +0xC4 处保存它，长度在 +0x104，并在 `nn::ldn::CreateNetwork`（`0x5ce988`，PLT stub `0xd31c78`）之前构建 `nn::ldn::SecurityConfig`。

## Pia 游戏密钥

    p1frXqxmeCZWFv0X

位于 `0xefd659` 的 16 个 ASCII 字节，剑／盾、传说 阿尔宙斯 和朱／紫的密钥。`0x0011a364..0x0011a384` 在模式字段 `[x19+0x98]` 为 0 或 2 时，存储在 crypto 设置 +0x24c。

## Pia 头

版本 3（wiki 的 Pia 5.11-5.17）。初始化函数 `0xd122d4` 写入 `0x00000003_32AB9864`；验证函数 `0xd12400` 检查魔数和 `(byte & 0x7f) == 3`。布局是剑的版本 4，但版本字节除外（`pokeldn/ldn/pia4.py`）：

    0x00  4  magic 0x32AB9864，big-endian
    0x04  1  0x80 (encrypted) | version = 3
    0x05  1  connection id
    0x06  2  packet id
    0x08  8  AES-GCM nonce
    0x10  16 AES-GCM tag
    0x20     ciphertext

## 消息封装

固定 22 字节消息头（Pia 5.11-5.12；反序列化函数 `0x5ae870`，写入函数 `0x5aeb00`），`pokeldn/ldn/pia3.py`：

    0x00  1  flags: 1 destination is a bitmap, 2 relay needed, 4 relayed, 8 unbundled
    0x01  1  version, 1
    0x02  2  payload size, big-endian
    0x04  1  protocol type
    0x05  1  protocol port
    0x06  8  destination, big-endian: a constant id, or a station bitmap under flag 1
    0x0E  8  source constant id, big-endian
    0x16     payload, padded to a multiple of 4

## 会话密钥

`LocalProtocol` 的派生函数 `0x5cd560` 与 BDSP 的和剑的相同：一个 SEAD xorshift128，从会话参数（`0x57cfc0`）播种，四次抽取，AES-128-ECB 使用游戏密钥在 `LocalProtocol+0x49c`。`pokeldn.ldn.pia5.ldn_session_key`。IV 是 pia4 的：三个字节的 `crc32(network id little-endian || host MAC)`，一个源 id 字节 0，头 nonce。

广告的应用数据以 24 字节头开始：

    0x00  4  network id, random per session
    0x04  4  CRC32 of the user password, 0
    0x08  1  system communication version, 4
    0x09  1  header size, 0x18
    0x0C  4  session param, the key seed
    0x18     the game's application data

## LAN 模式

Let's Go 1.0.2 有一个代码从不走的 LAN 路径。网络设置函数 `0x5dabb0` 为模式 0 构建本地工厂，模式 1 为 Nex，模式 2 为 Lan 工厂（`0x5ddaf0`，LanNetworkFactory 构造函数 `0xd14a20`），对应的启动函数 `0x4da710` 接受 1 或 2。每个写入模式的地方都传入 0 或 1：`0x115818` 传入 1，session 对象的构造函数在 `+0xa4` 处将其清零，其唯一 setter `0x348eb0` 存储 0 或 1。英文本选项、匹配、菜单和错误消息不包含 LAN 文本。

## 链接码

链接码是 NetworkInfo 场景 id，`1000a + 100b + 10c + 1`，每个选择在选择器中的索引（皮卡丘 0，伊布 1，妙蛙种子 2，小火龙 3，杰尼龟 4，比比鸟 5，毛球虫 6，尾立 7，咪立 8，地面鼠 9）；SSID 保持 `01000000000000000000000000000000`。`0x891580` 折叠选择，`0x978080` 计算 `10 * number + mode`（模式 1 为交易），session 构造函数 `0x4db1e0` 将其放入 `LdnCreateSessionSetting+0x60`（`0x4db6ac`），Pia 将其复制到 `NetworkConfig.intentId.sceneId`。

同一个构造函数为搜索中的主机选择频道：`{1, 6, 11}[scene % 3]`，表 `0xf73a44`；`pokeldn.lgpe.search_channel(code)`。皮卡丘×3 是场景 1，频道 6；妙蛙种子、小火龙、杰尼龟是 2341，频道 6；皮卡丘、皮卡丘、妙蛙种子是 21，频道 1。

搜索中的主机只在其广告包含该主机的场景 id 且在该主机自己的频道上时加入网络。`bin/lgpe_host.py --code NAMES` 在该频道上主机（`--channel auto` 扫描主机的网络）。`bin/lgpe_join.py` 不发送码。

## 本地协议

会话状态通过协议 0x24，端口 0 发送：wiki 的 5.7-5.45 更新会话消息（`pokeldn.ldn.local_protocol.parse_update_session`），本地头版本 1，类型 0x11，八个节点：主机 `169.254.105.1` 排名 0，加入者 `169.254.105.2` 排名 1，其余 255。正文携带主机常量 id 小端（MAC `48:f1:eb:20:9b:22` 对应 `000048f120229beb`）；消息头以大端发送。

## 站点协议，用于网格加入

在协议 0x14 上发送连接请求，然后在 0x18 上进行网格加入。处理函数 `0x5b8800` 读取 wiki 的 5.10-5.18 布局，站点协议版本 9：

    [0]     message type            1
    [1]     connection id
    [2]     version number          must be 9 (0x5b8848)
    [3]     is inverse connection request; rejected above 1
    [4]     target constant id      big-endian u64, the console's own (0x5b6830)
    [0xC]   target variable id      big-endian u32, checked only when [3] is 1
    [0x10]  inverse connection id
    [0x11]  station location        36 bytes for a joiner: no public address, zero NAT fields
    [...]   ack id                  u32, the message size minus four

零售主机运行完整序列，包括反向请求：

    ->  connection request (is_inverse 0)
    <-  ack; inverse connection request (is_inverse 1) with the host's location
    ->  ack; connection response (type 2, result 0, padded to 0x38)
    <-  connection response, 840 bytes, repeated until acknowledged
    ->  ack

### 站点发送的连接响应

0x348 字节（解析函数 `0x5b9270` 接受 0x3C）：

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

`station9.build_connection_response`；`bin/lgpe_join.py --player-name NAME`。收到 0x3C 字节响应的主机从不发送其克隆数据并离开克隆会话。

## 加入网格

在 0x18 上发送网格加入请求（`mesh_protocol.build_join_request`，本地站点索引 253），收到 148 字节网格加入响应（主机索引 0，加入者索引 1，最大活动 2，最大总数 8），在 0x14 上确认，然后发送更新网格（类型 0x20）。主机随后流式传输更新会话（0x24，用 0x21 确认）、RTT（0x58）、Sync Clock（0x1C）和 Clone（0x73）。保持活动是协议 0x08，无正文，应答类似。

## RTT 协议（0x58），版本 3

16 字节：kind 是 [0] 的 big-endian u32，发送者的 19.2 MHz 时钟计数是 [8] 的 u64；响应复制时钟计数并带 kind 1。`rtt_protocol.build_v3`；`--no-rtt` 关闭。

## Sync Clock 协议（0x1C）

主机控制的网格时钟。请求：[0] u64 时钟计数，[8] 零。回复：[0] 时钟计数返回，[8] u64 毫秒网格时钟。站点每两秒从加入响应中请求一次，并加上往返时间的一半。Clone 协议时钟即为此时钟；主机收到加入者自身运行时间的克隆时钟后释放克隆并离开。`pokeldn.ldn.sync_clock`。

## 可靠协议（0x7C），游戏数据所在

Pia 5.11 的头是 24 字节；序列号从 0xFFFFF82F 开始。

    0x00  1  flags
    0x01  1  stream id, 3 for the game, 0 on an acknowledgement
    0x02  2  payload size, big-endian
    0x08  4  sequence id, big-endian
    0x0C  4  the next sequence id expected from the peer
    0x18     the payload

确认仅为头本身。`pokeldn.ldn.reliable3`。

## 克隆协议 (0x73)

`nn::pia::clone::CloneProtocol` (`PiaCommon-5_11_4`) 承载伙伴同步。每条消息以版本 3、类型字节（高半字节为结构，低半字节为变体）和发送方的帧计数器（大端 u16）开头。

### 时钟同步，前两秒

双方发送时钟请求（类型 0x11，18 字节，`0x51f9b0`），大约每秒 5 次，并用回复（类型 0x21，22 字节，`0x51fab0`）响应：

    时钟请求                              时钟回复
    [4]   4  发送方消息计数              [4]   4  发送方消息计数
    [8]   2  目标位图                  [8]   2  目标位图
    [0xA] 8  发送方系统时钟              [0xA] 4  发送方克隆时钟，毫秒
                                               [0xE] 8  请求的时钟，回显

消息计数从 1 开始，遍历发送方的请求、回复和参与。位图为 `1 << 站点索引`。克隆时钟为 0 的回复会使零售控制台保持请求状态。

### 参与

在十次已答复的请求后，加入方发送参与（类型 0x31，10 字节，位图 0x0003）；主机答复 0x33 并发送自己的参与，加入方再答复 0x33。随后时钟回复变为 0x22，时钟请求停止。

### 克隆元素

克隆由克隆类型（1 至 4）、所属站点（0xFD 表示无）和 u32 克隆 ID 键控。双方发布各自的副本。

    每条命令消息   [4] u8 克隆类型, [5] u8 所属站点, [8] u32 克隆 ID
    类型 0x81 至 0xc4  [0xC] u32 消息计数, [0x10] u16 目标位图, 然后是字段
    类型 0xd1 至 0xf4  [0xC] 数据

低半字节是命令令牌加一：1 公告，2 请求，3 结束，4 锁定。`0x51c110` 通过表 `0xf769c4` 分发高半字节：

| 类型 | 添加 | 长度 |
|---|---|---|
| 0x8N | 无 | 0x12 |
| 0x9N | 在 [0x12] 处 u32 毫秒时钟 | 0x16 |
| 0xaN | 时钟，在 [0x16] 处 u8 计数 | 0x1a |
| 0xbN | 时钟，在 [0x16] 处 u32 参与者位图 | 0x1a |
| 0xcN | 时钟，计数，在 [0x1A] 处位图 | 0x1e |
| 0xeN | 在 [0xD] 处 zlib 流 | 确认状态 |
| 0xfN | 在 [0xD] 处一个字节，在 [0xE] 处 zlib 流 | 带数据的状态 |

zlib 流解压为记录，标签 0x20：

    0x20 0x06 u16 克隆 ID  0x01  0x00                               空副本
    0x20 len  u16 克隆 ID  0x03  u8 站点  u16 0  u16 参与者  u32 时钟  数据
    0x20 0x0A u16 克隆 ID  0x05  u8 确认的站点  u32 时钟

`clone.pack_record` 重现每个捕获的流（一次压缩，一次同步刷新，一个最终空块）。

| 交换 | 消息 |
|---|---|
| 所有者公告 | 0xa1 和 0xb1；另一方在数据之前答复 0xa2 和 0xc1 |
| 接管 | 另一方用 0x91 答复一个 0xa1 |
| 数据 | 所有者的 0xf3；另一方的 0xe3 带相同时钟 |
| 释放 | 0x83；0x84 确认 |
| 离开克隆会话 | 0x32；0x41 答复 |

0xa2 携带网格时钟和计数，克隆类型 4 为 1，克隆类型 2 为 0。0xaN 的字节 `0x17..0x19` 是接收方不读取的栈残留（`01 2808ab`）。克隆类型 3 和 4 的 0xa1 处理程序 (`0x522a60`) 答复 0xa2、0x91 或无响应；未知克隆的 0xa1 引发 0x91。`0x51c110` 在目标、消息计数未超过发送方最后值 (`0x51c1e0`)、长度和类型范围时静默丢弃。参与握手在协议的待处理掩码 `+0xc0` 清空时完成。

### 克隆 0 对

克隆类型 3 的克隆 0 的所有者用 0xa1 和 0xb1 公告它，并在另一方的 0xa2 和 0xc1 之后才发布。主机若其答复丢失，控制台会停留在“vous allez bientôt être connecté”画面；`bin/lgpe_host.py` 每隔 110 毫秒重复该对，最多 20 次，直到收到 0xa2、0xc1 或 0x91。

### 公告的目标字段决定什么

首次公告克隆的 0x81 携带整个网格 (0x0003)；其后的 0xa1s 只携带对等方 (0x0001)。给定 0x81 上的对等位图，对等方既不答复 0xa2，门 `0x11b080` 永远不会放行。

### 游戏在可靠协议上的消息

`0x7c` 上的每条消息是一个 16 字节的头部和一个主体：

```
+0x00  4  类型：通道 ID
+0x04  4  主体长度：0x168 类型 1，0xe8 类型 2 和 4，4 类型 3
+0x08  4  步进，计数每个站点从 1 开始发送的消息
+0x0c  1  标签，0 在每个交易消息上
+0x0d  1  目标站点索引，0xff 表示所有站点
+0x10     主体
```

`0x116f30` 构建头部；交易发送方通过 `0x4d94e0`。接收 `0x1171d0` 取出队列中步进等于其站点下一步的第一条消息，丢弃寻址到其他地方或未注册类型的消息，并留下另一种类型或标签的消息排队，阻塞其后所有消息。

类型是来自每会话 u32 计数器从 1 开始的通道 ID (`0x116e80`)，最多同时注册 16 个活跃。一次交易注册 1 (交易会话)、2 (报价)、3 (提交) 和 4 (交易后保存重新创建的报价对象)。每次注册都会公布一个克隆集合，因此克隆 ID 与通道 ID 不同。死信通道每帧压缩一次，因此一个座位大约能容纳四个，并无限链式交易。

类型 1，主体 0x168，身份：保存的 MyStatus 块 (PKHeX `MyStatus7b`，名称为 UTF-16LE)，由双方在任一方收到任何消息之前发送：

```
+0x00  4  训练师 ID，然后是秘密 ID
+0x04  1  版本：42 皮卡丘，43 伊布
+0x05  1  性别
+0x35  1  语言
+0x38 26  训练师名称；--trainer-name 在两个启动器上
+0x52 16  宝可梦名称
+0x90  4  交易锁
```

为接收玩家制作的礼物在此读取训练师信息
([为接收玩家制作](gift_simulated.md#made-for-the-receiving-player))。
`pokeldn.lgpe.reference` 附带一个训练师为 `POKELDN` 的礼物；`--our-trainer` 替换其 ID 对。

类型 2，主体 0xe8，报价，在站点的发布状态字达到 2 时发送，并在每次玩家更改选择时以新步进再次发送。新步进会被答复；重复步进为重传。答复一个新步进的报价而非自己的，会开启一个无终止的新轮次。发送方是 party-offer 对象 (`0x349bf0`，位于 `mgr+0x68`)，`0x34a3d0` 在每次选择变更且交易状态允许时用它填充。

类型 3，主体 4，提交 ([提交与交易锁](#the-commit-and-the-trade-lock))：每个站点发送一个 1，对方的 1 到达时发送 2。收到 2 则提交；1 之后的任何其他主体都被忽略。

类型 4，主体 0xe8，搭载正常保存 3000 毫秒后重新创建的报价对象，交易演示之后：首先是站点的第一槽，然后每次选择一次。它会开启下一个交易。

| 步进 | 类型 | 主体 |
|---|---|---|
| 1 | 1 | 身份 |
| 2 | 2 | 报价，每次选择重复 |
| 5 | 3 | 提交，1 |
| 6 | 3 | 提交，2 |
| 7 | 4 | 第一槽，每次选择重复 |

交易 r (从 0 计数)，在类型 2 + 2r 上报价，在 3 + 2r 上提交，在 4 + 2r 上结束。其 party 克隆为 2 + 3r 和 3 + 3r，提交克隆为 4 + 3r。

| 启动器 | 链式交易 |
|---|---|
| `bin/lgpe_host.py --next-offer` | 用下一个记录答复每个后续交易的选择 |
| `bin/lgpe_join.py --offer ...` | 用下一个记录答复主机的类型 4；在最后一次后不再答复 |
| `bin/lgpe_host.py --lead` | 为 `bin/lgpe_join.py` 拼演主机角色；`tests/test_esp32.py` |

交换 2 时，双方写入收到的记录；撤回的报价写入空。

类型 2 和 4 的主体是一个 232 字节的箱结构：第 6 代加密下的第 7 代布局，从 +0x08 的四个 56 字节块通过 `((ec >> 13) & 0x1F) % 24` 排列并异或 LCRNG 流 (以加密常数为种子)。`pokeldn.lgpe.pb7`。控制台保存时不检查：一个异色 100 级 Ditto，隐藏能力，全 IV 31 和全 AV 200，在总结画面上保持不变。

### 什么门控游戏自己的第一条消息

链接交易对象的状态机是 `0x349200` (跳转表 `0xf4e994` 在 +0x68)。

| 状态 | 做什么 |
|---|---|
| 3 | 公布克隆 1 的集合 (`0x11aec0`)，设置 4 |
| 4 | 等待门 `0x11b080` |
| 6 | 发送类型 1，无网络输入 |
| 7 | 计数类型 1 消息，包括自己的回环；在收到两个时进入 8 |
| 8 | 终态；画面显示已找到玩家 |

门在 SendClone (+0x90) 和 SharingClone (+0x1258) 的已确认集合 `clone+0xA8` 中拥有所有参与站点时放行，每个 party 克隆的完成字节 `+0x110` 都被设置，且 +0x1430 的站点索引不是 0xFD。站点的位只通过克隆类型 2 的 0xa2 从该站点进入 `clone+0xA8`。

`0x11aec0` 在一帧内公布站点的克隆集合：克隆类型 2 的 0x81，类型 4 的 0xa1 和类型 1 的 0xa1。克隆 ID 2 和 3 在 ID 1 之后约 3.2 秒由交易调度器 `0x886530` 生成，该调度器仅在模式字 `+0x8C` 为 3 时发布；设置该 3 的写入方未知。

### 托管零售控制台至其交易画面

- 本地协议主体以小端传输主机的固定 ID；若为大端，控制台无法解析发送方并停留在状态 7。
- 更新会话在会话变更时发送一次，以及在其后再发送一次，从不按定时器。
- 主机在发布克隆 0 的帧中公布克隆 1；控制台约 31 毫秒后公布自己的，主机若等待就会输掉比赛，角色互换。
- 答复主机拥有的克隆公告的 0xa2 携带对等方的 0xa1 时钟；主机若用自己的时钟，控制台会永远重新公布。
- 双方答复每个克隆类型 2 的发布带上自己的副本。
- 主机必须在克隆类型 4 和 1 上发布克隆数据，否则加入的控制台停留在搜索画面。

### 一个接管必须承载的序列

`0x520c30` 在公布时为 `+0x10C` 分配一个序列；完成 `0x520ce0` (一个 0xa2) 仅在值等于 `+0x10C` 时设置 `+0x110`，而 `0x520d30` (一个 0x91) 在不设置的情况下取消链接。该值是另一站点最新 0xa1 的时钟。由加入方自己的时钟构建的 0xa2 会错失，状态字永远停留在 4。一个入站 0x82 也会分配，因此每次回复重新公布会用 0x82 爆发创建无限序列。

### 一个加入方在每个克隆上运行的接管交换

接管取消对等方的公告并在加入方自己的时钟下公布克隆：

```
+0 ms   主机    克隆 2 的 0x81，克隆 3 的 0x81，目标 0x0003
        主机    每克隆 2 个 0xa1                        时钟 0x197e，主机的
+5 ms   加入方  0x82，2 个 0x91，0x82，2 个 0x91，2 个 0x84    回显 0x197e
+75 ms  加入方  克隆 2 的 0x81，克隆 3 的 0x81，每克隆 2 个 0xa1 时钟 0x19c1，加入方自己的
+102 ms 主机    每克隆 0xa2                           时钟 0x19c1
        主机    每克隆 0xa1                           时钟 0x19e2，主机自己的
+141 ms 加入方  每克隆 0xa2                           时钟 0x19e2
```

加入方对每个克隆只接管一次。所有后续重新公布都会收到一个 0xa2，携带该公布的时钟，在加入方的站点上的克隆类型 2，载荷 `<时钟> 00 00 00 02`；第二次接管会使对等方永远重新公布。

仅对等方的重新公布会引发对等方在克隆类型 1 上的 0x82，进而引发主机的类型 4 副本，控制台用 `1 1 1` 答复。主机若未收到提交克隆的 0x82，会停留在确认画面并保存交易锁；`pokeldn.ldn.clone` 每隔 100 毫秒重发对等方的 0x81，最多 20 次，直到 0x82 到达。

### 交易遍历的两个克隆记录

克隆类型 2 副本的 20 字节数据：

```
+0x00  4  状态：1 一票，2 一票撤回，4 强制离开
+0x04  4  参数，1 表示选择，2 表示确认
+0x08  4  计数器，每次调用递增
+0x0c  4  站点的自己的步进
+0x10  4  末尾字
```

### 克隆类型 4 拷贝的 32 字节数据是会话主机（权限者）的视图：

```
+0x00  4  A，即约定的参数
+0x04  4  B
+0x08 16  按站点索引：它最后看见撤销的投票计数
+0x18  4  站点的步骤
+0x1c  4  末尾字
```

权限者 `0x11b6c0` 仅当每个站点在当前末尾字上发布带参数 X 的状态 1 时，才将 A 移动到 X，同时发布 A 和末尾字加一；状态 4 立即移动 A。对于参数与 A 不同的状态 2 站点，记录计数并推进末尾字。拷贝仅被更严格更新时钟的记录替换；`pokeldn.ldn.clone.Participant.record_clock` 保持每条记录的时钟高于上一条。主机在类型 4 上发布 32 个零会使控制台停留在“communication en cours”。

### 交易屏幕的状态 (`0x34a300`) 来自 A 和本地状态：

| A | 本地状态 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| 0 | 0 | 1 | 1 | 0 | 0 |
| 1 | 2 | 3 | 3 | 0 | 2 |
| 2 | 4 | 4 | 4 | 4 | 4 |
| 3 | 5 | 5 | 5 | 5 | 5 |

状态 4 开始同步保存，状态 2 返回选择，状态 5 是伙伴离开。

### 提供的团队克隆行走 `1 1 1`，末尾字 1，然后 `x 2 2`，末尾字 2。提交克隆（ID 高一位）取前两个然后一个零：

```
+0 ms     类型 4 数据，32 个零，附带公告
          对等方在其玩家确认后发布 `1 1 1` 步 0 一次
          `1 1 1` 步 0                 主机自己的确认
+30 ms    `1 1 1` 步 1                 类型 4 数据 1，零，步，1
+8 ms     对等方回答 `0 1 1` 步 1
+27 ms    `0 1 1` 步+1 1               提供的克隆变为 `0 2 2` 步+1 2，
                                       带 1 的类型 3 放在该步下
+3 ms     对等方的类型 3 带 1
+63 ms    下一步下的类型 3 带 2，所有拷贝在其下重新发布
交易演示和正常保存后：
          两个更多的克隆被公告，类型 4 上 32 个零；对等方在每个上发布 `0 0 0`
然后      下一步下的类型 4
```

### 对等方仅当类型 4 拷贝的第一个字为 1 时才回答末尾字 1。控制台主机公告每个克隆并首先投票；一个接管每个克隆并重新发布主机前三个字和末尾字在其自身状态字下的加入者完成交易。

在确认上再次按 A 撤销投票：`1 2 2` 后为 `2 2 3`。用 A 2 回答会在不完成交换的情况下提交交易锁（参见 [Unresolved](lgpe.md#unresolved)）。回答 `1 0 0 3 0 0` 步 T+1 会将控制台返回选择；在 A 0 下撤销的选择 `2 1 4` 对应 `0 0 0 4 0 0` 步 T+1。`bin/lgpe_host.py` 这样回答；`tests/test_lgpe_host_withdraw.py` 将两者都运行到游戏代码中。

### 交易动画

控制台在其步骤 `0e` 后播放交易动画期间不发送任何交易负载。从该步骤开始：动画在约 1.7 秒开始，收到的宝可梦在约 15.3 秒出现，控制台的类型 4 负载（248 字节）在 27.0 秒到达，玩家在约 28.8 秒获得控制权。

### 提交和交易锁

交易锁是 MyStatus `+0x90` 处的 u32 倒计时（以秒为单位）（`savedata.bin` `0x1090`；设置器 `0x1c9d40`）。交易的同步保存将其设为 600 并在提交交换之前提交；交换完成后提交回 0。链接菜单的检查 `0x9765f4` 在其非零时拒绝交易（`0x976634`，消息 `0x0248810f825b1fee`）。锁仅在游戏聚焦时倒计时，一次更新最多倒一秒。

`0x347190` 构建三种保存序列之一：正常保存、同步保存、致命错误。交易使用同步保存（更新 `0x838070`，跳转表 `0xf867c4`）：

| 状态 | 做什么 |
|---|---|
| 0 | 等待 `SaveThread`（已提交 600），决定本站是否发送 2（`0x838660`），应用收到的宝可梦并清零内存中的锁（`0x838800`），启动 `FirstSaveThread` |
| 1 | 等待 `FirstSaveThread` 写入，然后随机延迟 `2000 + r % 6000` 毫秒 |
| 2 | 注册提交通道 |
| 3 | 在提交克隆上投票 1，等待通道的门 |
| 4 | 发送带 1 的类型 3 |
| 5 | 接收对等方的类型 3；身体不是 1 则中止；发送站点发送 2 |
| 6 | 接收到的 2 信号提交；任何其他身体被忽略 |
| 7 | 等待 `FirstSaveThread` 提交 |

没有状态有超时。在状态 0 结束和 2 之间记录的任何网络错误都会导致中止：`FirstSaveThread` 不提交，保存保持 600，调度器推送致命错误 `error_fatal_save`（"An error occurred. You couldn't trade Pokémon. Press the HOME Button to end the game."，标签 ID `0x191615296121e064` 在 `common/message_error.dat` 中），游戏从此无法返回。伙伴在提交过程中离开网格会记录这样的错误。

| 对于对等方 | 后果 |
|---|---|
| 权限者发布 A 2 | 控制台提交 600；权限者欠下整个提交交换 |
| 第一个带非 1 的类型 3 | 中止，锁被设置 |
| 在接收方注册提交通道之前发送的类型 3 | 被丢弃；状态 3 的投票将其挂起，直到双方都注册 |

`0x838660` 决定谁发送 2：给出 Articuno、Zapdos、Moltres、Mewtwo、Mew、Meltan 或 Melmetal 用于任何其他宝可梦的站点发送它，反之则不发送，否则在会话开始时作为会话主机的站点（`mgr+0x128c`）发送。

`0x838800` 将收到的宝可梦写入自己的提供箱槽并应用交易的副作用：宝可梦图鉴注册、交易进化（方法 5 始终，方法 6 带 Held Item；方法 7，Shelmet 与 Karrablast，从不匹配，因为到达的拷贝作为两个宝可梦传递；对方法 6、19、20 清除 Held Item），以及游戏记录 476（本地交易）或 477（互联网连接时交易）。

### 交易调度器

`0x886530` 运行从菜单到退出的链接，切换在 `[obj+0x68]` 上通过 `0xf87bc4`：

| 状态 | 做什么 |
|---|---|
| 0 | 设置；链接菜单进程写入模式字 `+0x8c` |
| 1 | 模式 1 或 2 开始链接战斗，然后 6；模式 3 等待团队提供对象就绪；网络错误跳转到 8 |
| 2 | `[obj+0x100]` 5，交易 UI 的继续，开始同步保存；其他情况跳转到 8 |
| 3 | 等待同步保存；结果 2 推送致命错误；否则销毁提供对象并开始交易演示 |
| 4 | 释放演示，进入状态 5 |
| 5 | 将收到的宝可梦写入箱槽，开始正常保存，进入状态 7 |
| 6 | 进入状态 8 |
| 7 | 等待保存；结果 1 跳转到 8，其他情况跳转到 1 |
| 8 | 销毁提供对象并离开 |

保存过程在 `obj+0x178` 获取一个块：

```
+0x00  保存类型：0 同步保存，1 正常保存，2 或 3 致命错误
+0x04  结果：0 完成，2 中止，1 链接结束
+0x08  自己的提供宝可梦的箱索引
+0x10  收到的宝可梦
```

正常保存等待其 `SaveThread` 后 3000 毫秒，然后在新通道上重新创建团队提供对象。调度器从状态 7 返回到状态 1，因此一个座位可以连续进行一次交易。链接菜单的选择 1（交易）存储模式 3；选择 2 和 3 存储 1 和 2，单人和双人链接战斗，分别注册带标签 1 和 3 的通道，并计入 `local_btl_single_cnt` 和 `local_btl_double_cnt`。交易计入 `local_trade_cnt`（`0x1dc`）或 `net_trade_cnt`（`0x1dd`）。

### 一个加入者离开

一个按 Retour 退出的控制台在提供的克隆上发布状态 4，参数 0 然后 3；主机用前三个字的零、末尾字加一和参数作为类型 4 拷贝的第一个字回答每个。双方都释放它们的克隆（0x83，由 0x84 回答）。一旦其克隆协议空闲（参见 [The wait before leaving](#the-wait-before-leaving)），控制台发送网格离开请求 `04 01` 在网格协议的可靠端口上。

它欠下可靠的确认和来自不可靠端口的离开响应 `08 00`（网格主机的索引）。`LeaveMeshJob` 每 40 毫秒重传请求，最多 5000 毫秒。收到 `08 00` 回答，控制台发送自己的断开请求并在 0.1 秒内去认证；未收到回答，则在 5.0 秒后去认证。Retour 后，主机发送站点断开请求，类型 3；控制台回答类型 4。

一个控制台主机用 `08 00` 回答加入者的离开请求两次，然后重复本地协议开始主机迁移（类型 0x13）每 0.3 秒。加入者的断开请求将主机的玩家返回菜单。`bin/lgpe_join.py --leave-after SECONDS` 运行退出（`pokeldn.lgpe.leave`）；`--stall-leave`（默认 5）在投票悬而未决且未收到任何类型 3 之前运行退出。退出不会解除交易锁。

### 一个主机离开

一个按 Retour 退出的控制台主机发布状态 4，参数 3，释放其克隆，并在空闲后发送网格迁移开始 `44 00 01`（主机索引，下一个主机的索引），每 45 毫秒重传一次，最多 5000 毫秒，直到每个站点回答 `48 <index>`。然后它广播一个携带主机迁移状态 1 的更新会话，并重复开始主机迁移（类型 0x13）每 301 毫秒，直到没有其他站点连接或 10000 毫秒已过，然后销毁网络（八个 LDN 断开帧，原因 3）。`bin/lgpe_join.py` 回答确认和 `48 01` 并在第一个 0x13 上离开（`pokeldn.lgpe.leave.host_departure`）。

### 离开前的等待

拆卸步骤 `0x116bc0` 在克隆协议空闲时结束克隆会话并立即离开；否则等待 150 次调用，约 2.5 秒。协议在没有克隆有未确认的数据且每个站点都用 0x41 回答其 0x32 时达到空闲。克隆 0 释放后，一个控制台保持发布克隆类型 2 拷贝约每 100 毫秒；一个对等方用 0xe3 回答每个，在克隆类型 1、站点 0xFD 上，携带发布者的站点和时钟，让它空闲并在 0.3 秒内离开。一个对等方用自己的拷贝回答则将其保持到完整的等待。`pokeldn.ldn.clone.Participant` 在对等方的克隆 0 释放后应答。

---
title: Legends Z-A
nav_order: 10
has_children: false
---

# 传说 Z-A

宝可梦传说 Z-A（title id `0100f43008c44000`）是一款原生 Switch 游戏，Pia 静态链接进 `main`。它的数据包头部是版本 16，即 `pokeldn.ldn.crypto` 为 GBA 应用写入的那个版本。

## 转储

基础应用 `v0`（4.3 GB），更新 `0100f43008c44800` `v393216`（2.1 GB），Mega Dimension DLC `0100f43008c45002`。

| NCA | id | container offset | section key |
|---|---|---|---|
| Program (update) | `4a70b3ff963bfe412681185cea68bf55` | `0x2085d0` | `b9de1a0334576634f8fdafdd703f7f9a` |
| Control | `3e7ba1cd223145fa4f299a8f4cafd4cb` | `0xbd0` | `a8cb59338ce785237048d52452eb6adf` |

Program NCA 在 section 0 中有 exeFS，在 section 1 中有 BKTR RomFS。exeFS 包含 `main`（33,970,422 字节）、`main.npdm`（1,700）、`rtld`（8,550）和 `sdk`（6,247,676），没有 `subsdk0`。解压后，`main` 的 text 是 `0..0x3163f70`，rodata 从 `0x3164000` 开始，data 从 `0x3bc2000` 开始；本页中的地址是该映像内的偏移。Control RomFS 数据位于 NCA `+0x14c00`，section counter `0000000000000005`；`control.nacp` 显示版本 2.0.2 和八个本地通信 id，在 `+0x30b0` 处，全部为 `0100f43008c44000`。

## 无线层

| value | | where |
|---|---|---|
| LDN passphrase | `BM7cXkadR9ugiXdHiurkiyhrQwcR3rMgCM5BF47dranKXWAGpGEA9z3ncXRnPjCX` | rodata `0x33391fc`, data `0x3eeda1f` |
| Pia game key | `p3bwdaSsywFXUkDu` | data `0x3eeda0e` |

两者都与 [NintendoClients wiki](https://github.com/kinnay/NintendoClients/wiki/Pia-Game-Keys) 相符。

## 数据包头部

头部版本 16，在 wiki 表格中对应 Pia 6.39 至 7.2。布局为 `pokeldn.ldn.crypto.PiaHeader`（29 字节，魔数 `32AB9864`，加密时版本字节带 `0x80`；参见 [Pia](pia.md)）。

    0x24fadbc   initializer: magic at object +0x08, 0x10 at +0x0c, memsets nonce +0x15 (8), tag +0x1d (16)
    0x24faefc   validator: magic, (version & 0x7f) == 0x10, (length - 0x1d) >> 6 below 0x71
    0x24fb1e0   receive path, branches on bit 7 of the version byte
    0x24fb4b0   send path, writes 0x10 back to +0x0c when it seals nothing
    0x24fb46c   padding-size setter: ORs into bits 4..7 of object +0x0d (wire byte 0x05)

该对象将 nonce 和 tag 保存在其线上偏移上方八字节处，正如传说 阿尔宙斯的版本 11 头部在 `pokeldn.ldn.pia6` 中所做的那样。

## 广播

处于本地搜索界面的主机托管一个网络并广播 112 字节：0x5C 的 Pia 系统属性块和 20 个游戏字节。不随链接代码变化的字段：

| field | value |
|---|---|
| local communication id | `0100f43008c44000` |
| LDN protocol | 1 |
| advertisement version | 4 |
| scene id | 1 |
| application version | 6 |
| security mode | 1 |
| accept policy | ALL |
| participants | 1/2 |
| system / application communication version | 22 / 6 |
| player name | 一个字节、一个空格、UTF-8 |

SSID 和信道按会话变化。游戏字节是链接代码的 ASCII，用 NUL 填充到 16 字节，然后是其长度的小端 `u32`。布局和密码字段与传说 阿尔宙斯相同（[pla.md](pla.md)，广播中的链接代码）；Z-A 的游戏密钥给出的掩码为 `1068a742ac3a8787ab6066a161f5d5e1`。`pokeldn.za.build_advertise_data(code)` 仅凭链接代码即可复现每条广播；`tests/test_za.py` 对两者均有固定校验。

## 席位

正在搜索的主机一旦接受一个站点就会立即通过 Pia 通信：第一个数据报（109 字节）在 0.02 秒发出。数据包使用 `AES_ECB(game_key, ssid)` 进行认证，网络 id 为 `CRC32(ssid[1:16])`（32 个数据包中有 32 个解密成功）。若未收到应答，它会通过协议 1（Net）从其 variable id 向目标 0 发送：

| message | |
|---|---|
| `01 11 ...`, 118 字节 | 连接状态，序列 id 2 和 3，每秒两次 |
| `01 40 00 00` | 开始主机迁移，一旦状态未收到应答 |

连接状态就是 `pokeldn.ldn.pia_connect.parse_net_conn_request` 所读取的布局：四个槽位，填了两个，都在端口 12345，主机 `169.254.x.1`，加入方 `169.254.x.2`。它大约 14 秒后停止，并使站点保持就座状态。

| | |
|---|---|
| first packet | 主机发出的，109 字节，关联后 48 ms；加入方以 45 字节应答，然后是 125 字节 |
| header nonce | 每个站点的计数器，基于随机 64 位基础值，每发送一个数据包加 1 |
| joiner's first packet | 源 0，目标 0，数据包 id 0，无尾部，未压缩 |
| joiner's second packet | 其自身的源 id，zstd 压缩 |
| host's next packet | 发往该 id，带有两字节接收方尾部 |

如果加入方在网络上 LDN 连接成功但没有 Pia 主机，则会在 7.94 秒后断开连接，该时间等于 Net 连接截止时间 8000 ms 减去 LDN 连接耗时：

0x251b1bc   LdnProtocol 虚表 0x3c8aef8 槽 0x1d8：mov w0, #0x1f40
    0x2513520   NetBackgroundProcessJob StartConnectNetwork：job+0xa0 = now + ticks_per_ms * 8000
    0x25141c4   WaitConnected 步骤 0x25140bc，当主机未知时：相对 now 的截止时间
    0x25143a0   到期：结果 0x647a，状态字节 +0x100 = 5，一个 5000 ms 截止时间（槽 0x1e8），
                然后 StartDisconnectNetwork

LdnProtocol 的定时槽 0x1b0 至 0x1f8 返回 6000、1000、500、10500、4500、8000、20000、5000、5000 和 10000 ms；目前仅识别出 0x1d8 和 0x1e8 的含义。

## 零售主机上的会话

发送参考加入方的 Session 加入消息的站点会立即被接纳。主机发送的内容：

| from the seat | what the console sends |
|---|---|
| 0.02 s | Net 连接状态，118 字节 |
| 0.05 s | Session 加入响应，类型 2，37 字节，发往加入方的 variable id |
| 0.06 s | Reliable（协议 10），106 字节，以及两个 Broadcast Reliable（协议 11） |
| 0.08 s | Net 更新属性，类型 0x50，150 字节 |
| from 0.5 s | RTT 请求，大约每秒三次 |
| 1.12 s，重复 | Session 更新会话，类型 5，185 字节 |

在 Net 确认之外，加入还需要：十个协议（`1:0 3:5 5:1 6:0 9:1 10:3 11:4 12:4 13:7 15:0`）、应用通信版本 6、一个 identification token `0x06` 后跟零，以及一个名称为一个空格的 PlayerInfo。若加入方应答所有 Net、Session、RTT 和 Reliable 消息且不应答游戏消息（不带 `--game` 的 `bin/za_join.py`），则它会一直占据零售搜索的席位，直到离开（实测 150 秒）。

| join | console's answer |
|---|---|
| 协议数量与主机不同 | 被类型 0 处理器 `0x254a030`（`0x254a090`，对比 `0x256c9f0`）直接丢弃，无应答，无站点 |
| 协议或应用版本错误 | 37 字节的类型 2，结果 3（`0x254a2e4`）或 4（`0x254a290`） |
| GBA 应用的六个协议，或十个中的九个 | 无 Session 消息；入座后 8 到 12 秒发送 Net 0x40，然后在新 SSID 下建立新网络，并继续搜索 |
| 十个协议，但没有 RTT 应答或来自其 variable id 的其他流量 | 被踢出（[踢出](#the-kick)），入座后约 27 秒显示“未找到伙伴” |

8 到 12 秒的路径来自主机的 WaitMember，时长为 3000 ± 999 ms（随机 u64 被按有符号数读取）；到期时，加入方仍在 Net 层但不在会话中，LeaveMeshWithHostMigration 会轮询 8000 ms 寻找下一主机（`0x255a520`），然后发送 Net 0x11 序列 3 和 Net 0x40。踢出序列为：从 14 秒起发送 Session 类型 13，每 0.5 秒一次共九次；从 19 秒起每 0.5 秒发送 Net 0x11 序列 3；从 23 秒起每 0.3 秒发送 Net 0x40。

## 游戏自身的交换

在 Pia 之上，游戏运行在 Reliable（协议 10）和 Broadcast Reliable（协议 11）上，子头部 `pokeldn.ldn.reliable` 会解析。一次交换携带以下应用负载（在一次参考捕获中有二十个不同的负载），每个都会重发直到被确认，除站点 id 外，两个站点发送的集合相同。按消息 id，以首次出现顺序排列：

| id | 字节数 | 携带内容 |
|---|---|---|
| `1400` | 106 | 站点的身份，玩家名称以 UTF-16 编码 |
| `1403` | 9 | 身份的校验和（SyncDataSet），如下 |
| `0100` | 1211 | 选择界面所依据的记录 |
| `0101` | 354 | 提供：九字节头部、344 字节宝可梦记录、一个尾随字节 |
| `0102`、`0104` | 5 | 步骤消息 |
| `0200` | 5 | 确认步骤，最后一个字节为 3、6、0x0b、0x0e |

`pokeldn.za.reference` 提供身份、其后续消息、协议 11 的开场和选择记录，这些来自玩家为 `Player` 的模拟配对；`bin/za_join.py` 和 `bin/za_host.py` 发送它们（`--game-dir` 指定另一组）。

身份是一个两元素的 `b9` 元组：一个 u32，然后是一个包含 0x5d 字节 `bc` blob 的单元素元组。该 blob 是一个六元素元组。其前四个成员是存档的训练家 id（高半部分为秘密 id）、性别、语言和玩家名称。随后是一个 32 字节的全零字段及其余部分。

游戏从存档的训练家区块（PKHeX 的 `MyStatus9a`，位于玩家状态对象的 +0x40 处）填充这四个成员：

| 成员 | 区块偏移 | 获取器 |
|---|---|---|
| 训练家 id | +0x00 | `0x824b2c` |
| 性别 | +0x05 | `0x505c24` |
| 语言 | +0x07 | `0x23c398` |
| 名称，13 个字符 | +0x10 | 由 `0xc90ce4` 复制 |

构建器是 `0xc90b04`；它将值存储在 GOT 在 `0x3ec7638` 处的名称条目下。

接收主机按相同顺序解码成员（`0x9131ec`）。其名称框 `T_pname_%02d`（`0xb13fd4`）根据游戏语言表（`0x33a308c`）检查语言是否为 1 到 11；11 是拉丁美洲西班牙语。它将性别与名称一起传给文本（`0x6b9fb8`）。

记录的身份是女性、英语存档：`0x378913cf`（5071 和 14217，参考会话中宝可梦的训练家），1 和 2。为接收方玩家制作的礼物读取全部四个（`reference.identity_trainer`，[为接收方玩家制作](gift_simulated.md#made-for-the-receiving-player)）。

    1400 b902 82<u32> b901 bc5d b906 82<u32> 01 02 bc1a <name> bc20 <32 bytes> ...

名称是 26 字节，UTF-16LE，NUL 填充：最多十二个字符，位于协议 10 消息的偏移 0x18 处（在协议 11 站点前缀后 0x1c 处）。用记录的 `Player` 进行测试时，零售主机显示其交换伙伴为 `Player`。两个启动器都会将 `--trainer-name`（默认 `POKELDN`）写入其中（`pokeldn.za.reference.named`）。

通道 0x14 承载一个键值存储，游戏在站点之间保持同步（`gfa::network::p2p`，在 `0x7796a0` 构建；消息 id 为 `0x1400 | index`）：1400 是 UpdateValue（`0xc1bdf4`），1402 是 DeleteAllValues，1403 是 SyncDataSet（`0xc4b1b4`）。身份的外部 u32 `0x2abe85e2` 是值的键，是 `0xdf1b30` 处的常量：`UserData` 的 FNV-1a 32 位，游戏以该名称存储身份。1403 携带一个 u32，它由发送方按键排序的值计算：从 `h = 0` 开始，`h = crc32(le32(fnv1a32(value) + h))`（`0xc4b270`，FNV-1a 在 `0xc4b31c`，标准 CRC-32 在 `0xc4b420`）；对于身份来说，该值是 `bc5d` 后的 0x5d 字节。接收方重新计算，并且只有在每个站点都匹配时才继续（`0xb8c724`、`0xb8c660`）。记录的 `Player` 身份给出 `1403b9018269fb308f`，即记录的消息。发送改名后的身份并携带那个过期的 1403 会让零售主机停留在搜索屏幕：它会发送自己的 1400 和 1403，但从不发送 0100。`pokeldn.za.reference.sync_message` 为发送的身份构建 1403。

### 交换命令

交换会话设置 `0xca2928` 在会话的命令通道（session+0xc8）上订阅五种命令类型（由 ctti 字符串命名）。id 为 `0x100 | index`，即类型在通道列表 +0x60 处的位置（`0x96129c`，一次 `strcmp` 遍历）。每个负载都是一个以 u16 轮次开头的 `b9` 结构体。

| id | 命令 | 处理器 | 处理器读取的负载 | 处理器行为 |
|---|---|---|---|---|
| `0100` | CommandReady | `0x2dc4c7c` | 轮次，1200 字节 | 将 1200 字节复制到 session+0x604，设置 session+0xf0 |
| `0101` | CommandSelectPokemon | `0xb2a44c` | 轮次，344 字节记录，一个字节 | 加载记录（被提供的宝可梦）；该字节的位 0 清除时表示选择 |
| `0102` | CommandConfirmTrade | `0xc8dda0` | 轮次 | 当 session+0x152 高于该轮次时忽略；否则伙伴状态 +0x134 = 4 |
| `0103` | CommandCancelTrade | `0x2dc51ac` | 轮次，u32 原因 | +0xab4 = 原因（1 和 2 互换），否则 0；+0x152 = 轮次；+0x150 += 1；然后 `0x2dc41f8` |
| `0104` | CommandFinalAgreement | `0x2dc52b4` | 轮次 | 当 +0x152 高于该轮次或自身状态 +0x130 不是 4 或 5 时忽略；否则伙伴状态 5 |

取消发送器 `0x964a60` 在自身状态 +0x130 为 2 或 5 时不发送任何内容；否则它发送轮次 +0x150 + 1，将 +0x130 设为 2，使 +0x150 和 +0x152 递增，并将伙伴状态从 3..5 降至 2（当原因值为 0 时降至 3）。处理器只拒绝严格低于 +0x152 的轮次，因此取消后过期的 ConfirmTrade 或 FinalAgreement 会被忽略，而更高的轮次会被接受。SelectPokemon 不读取轮次。

会话对象（0xab8 字节，由 `0xca2704` 构建，虚表 `0x3e3a6e8`）将 +0x150..+0xab7 清零，因此两个轮次都从 0 开始，会话的第一个 `0102` 和 `0104` 是 `b90100`。交换完成后 `0x964568`（自身状态 6）清除两个提供，将两个状态设为 2 并将两个轮次清零，因此该席位上的下一次交换从轮次 0 开始。`pokeldn.za.host` 在每次交换时重置其轮次。

| 自身状态 | 写入者 | 时机 |
|---|---|---|
| 5 | 会话更新 `0x95f600`（`0x95f680`） | 自身状态 3 或 4，字节 +0x148 设置，定时器 +0x138 至少 1.5 秒，伙伴状态 4 或 5，`0x963710` 为真 |
| 6 | 委托调用 `0xdfda8c`，在 `0x964e78` 填充 | 交换工作器的状态 6 委托 |
| 7 | `0x2dc4b94`，由 `0x964f0c` 安装 | 工作器的状态 7 委托；在 2.0.2 中不可达 |

在自身状态 5 时，`0x9610a4` 调用交换对象（session+0x48，由 `0xc8ad1c` 构建，虚表 `0x3d8a0d0`），并在 +0xd0 处构建交换工作器（`0x966af0`，0xb0 字节），带有状态 6 和状态 7 委托（`0x9649e0`、`0x964a20`）。

工作器的启动 `0x965660` 将主机测试 `0x9157d0` 存储在 +0x14，清除 +0x15，将 `0x34f2b0(rng, 0x12c) + 2`（2..302）存储在 +0x18，将 +0xc 和 +0x10 清零，设置 +9 为 1。其更新 `0x960c20`（只有一个调用者 `0x95f750`）通过表 `0x33a360d` 对 +9 进行分支。`0x962ac0(peer, step)` 将 `0x100 | step` 存储在 peer+0x48 并发送；等待会比较伙伴在 +0x70 处的步骤，当 +0x71 设置时有效。

| +9 | 处理器 | 行为 | 下一状态 |
|---|---|---|---|
| 1 | `0x960d20` | 交换对象虚函数 +0x68；结果 1：+0x15 = (+0x14 != 0)，结果 0：+0x15 = 1（`0x960e50`、`0x960e90`），否则 +0x15 = 0；发送步骤 3 | 2 |
| 2 | `0x960cc0` | 等待伙伴的 3 | 3 |
| 3 | `0x960d64` | 交换对象虚函数 +0x78；为假：状态 4，发送步骤 6 | 5 |
| 5 | `0x960ce0` | 等待伙伴的 6 | 6 |
| 6 | `0x960da0` | `0x9628e8`：交换对象 +0x40 = 1，然后虚函数 +0x80（`0xcbc68c`，即“交换写入接收记录的内容”中的处理器更新） | 7 |
| 7 | `0x960c84` | 等待交换对象 +0x40 == 3；+0x15 设置：发送 0xb | 8，否则 9 |
| 9 | `0x960c40` | 每次更新将 +0x18 减一，然后发送 0xb | 10 |
| 8, 10 | `0x960ca0` | 等待伙伴的 0xb | 11 |
| 11 | `0x960db0` | 交换对象 +0x40 = 4（`0x961098`） | 12 |
| 12 | `0x960dc0` | 等待交换对象 +0x40 == 5（`0x9626e4`），发送 0xe | 13 |
| 13 | `0x960d00` | 等待伙伴的 0xe | 14 |
| 14 | `0x960de8` | +0x10 == 0：状态 6 委托（`0x963810`）；否则状态 7 委托（`0x9a0b00`）；然后 `0x9637b8` | 0x10 |

自身状态 6 表示交换完成，此时两个站点都已通过 `0200b901XX` 步骤 3、6、0x0b 和 0x0e。处理器 14 在工作器的错误字 +0x10 非零时选择状态 7 委托，而 2.0.2 中没有任何代码会在那里写入非零值：它只在构造函数 `0x966ba4`（`0x966bcc`）和启动 `0x965660`（`0x9656a0`）中将它清零。工作器的中止阶段 +0xc 由会话滴答 `0x95f6e4`（`0x95f738`）读取：1 要求交换对象取消（`0x9636f8` 将交换对象 +0x44 设为 1）并将工作器停在步骤 0xf；2 等待交换对象 +0x44 == 3，然后设置步骤 14 和阶段 3（`0x95f7e0`）。没有代码存储 1，因此没有任何路径能够通过工作器到达自身状态 7。每个通过工作器指针的存储（在 `0x95f608`、`0x95fc80`、`0x9610c8`、`0x961130`、`0x961a74`、`0x9645cc`、构造函数、处理器及其被调用者中对 session+0xd0 的读取）都落在 +0x09、+0x0c、+0x14、+0x15、+0x18、+0xa0、+0xa8 或委托的存储处（管理器 `0x965f54`、`0x4177c8`）；没有经过计算地址。+0x15 清除的站点会在其 0x0b 之前等待随机的 2..302 次更新。`0xdd07cc` 返回什么以及存储的半字如何映射到 `b901XX` 字节尚不清楚。

在交换提示上选择取消的《传说 Z-A》会发送 `0103b9020100`（轮次 1，原因 0）；一旦其玩家再次选择，它会用主机先前的提供重绘提示，并用 `0102b90101` 和 `0104b90101` 确认。轮次低于 0 的应答会被忽略，并让主机停留在“正在通信”画面。`pokeldn.za.host` 会从主机自己的 `0102`、`0103` 和 `0104` 中获取轮次。

### 加入者在该流上的义务

根据参考配对和模拟主机确认的测量：

- 协议 10 发送到主机的可变 id，协议 11 发送到网格 id 0x0001；两者都在两字节接收方页脚中携带主机的可变 id；
- 每个游戏数据包都经过 zstd 压缩；
- 纯确认使用流的基址 0xfff0 和消息标志 0x40；推进序列的确认被读取为后面有空洞的数据。应用数据不携带消息标志；
- 协议 11 上的确认是 74 字节：站点的四个字节、一个流字节、一个计数四，然后是四个条目，每个包含一个下一个期望的半字和一个十六字节掩码，最后一个被截短。条目 1 是加入者的流；主机在其他三个中报告空闲基址 0xfff0；
- 身份在 INIT 下发出，选择记录紧随其后，然后在一个新序列下重复发送，每次都是相同的 1211 字节（测量：约 0.5 秒后，然后约每秒四次）；
- 子头部中的接收方计数在协议 11 上为三，在协议 10 上为零；
- 在协议 11 上，子头部长度计数的是四字节站点前缀之后的负载，因此每帧携带的字节数比声明的多四：开头是 `00000001` 和 `1402 b900`，身份是前缀加上整个协议 10 身份，九字节消息是 `1403b9018269fb308f`，确认是前缀加上四个完整的 18 字节条目。被裁剪到声明长度的帧会被丢弃（主机约每秒十次重新发送其开头）；最后四个字节错误的帧虽然被确认，但会让主机停留在搜索屏幕。

LDN NodeInfo 本地通信版本（0x40 字节的 +0x2E）在参考站点上为 6；0 被同样对待。

### 踢出

主机会踢出一个站点，如果该站点自己的可变 id 在 10 秒内没有发出任何数据包，无论其玩家屏幕是什么：它到该站点的 RTT 停止，并且每 501 毫秒重复发送会话类型 13（0x0d，其八字节常量 id 大端序，长度十，原因字节为 1），由 `0x25512b4` 中的 `0x2551320` 组成，其两个调用者 `0x255bad4` 和 `0x255bd70` 位于 `nn::pia::session::KickoutManageJob`（`vfunc6` `0x255bda0`）中。0x0001 只是目的地；从它发送的加入者不会被任何人听到。在踢出的捕获中，它在席位后 18 到 25 秒出现。

    0x2547700   来自 SessionProtocol 虚函数 10 (0x2547170)，当本地站点的字节 +0x48 为 2
                且 +0x1b0 非零时：对每个状态为 2 的站点，通过 0x2547dd0（映射在
                session+0x1048）发送原因 1，当 now > last_heard(+0xb8) + ticks_per_ms * (s32)[+0x1b0]
    0x24f5f08   ticks per ms: GetSystemTickFrequency() / 1000，只计算一次
    0x25504c8   写入 +0x1b0 到 session+0x18，对象 0x24f11f0 的 +0x338 返回
    0x253d9d4   会话启动 0x253d4f0：max([setting+0x28c], 4000) 传给 0x25504c8
                (0x253d9cc ldr x0,[x20,#0x18])，[setting+0x290] 在之前传给 0x257d12c
    0x199eb48   设置构造函数将 (+0x28c, +0x290) = (10000, 1000) 作为一个 u64 存储；还有
                0x199edf0、0x199f07c、0x199f2f8、0x19a0494、0x19a0a4c，以及 Pia 的默认 0x251a4c8
    0x255c990   一次性表 [0x3ee51d8][station id]，读取并清除：也用原因 1 踢出
    0x2548b60   将映射排空到 0x255b4a0，后者在 KickoutManageJob 的 24 条目表中占用一个槽位
                并发送第一个类型 13；该工作的更新 0x255bc10 每 501 毫秒重发一次
    0x2567280   为掩码中位（字节 +0x30）为 1 的每个站点刷新 last-heard
                0x2566740 从接收数据映射构建，以头部源 id 为键

session+0x18 是 `SessionProtocol`（0xd8e8 字节，虚表 `0x3c8db18`，协议类型 0xd）。

### 保活

设置的 +0x290 是发送静默限制，以毫秒为单位（`0x257d12c` -> `0x256a238`；0 变为 1000）。`SessionPacketWriter` 虚函数 7 `0x2544004` 在发送时于 +0xb0 处为每个就座站点打时间戳，并通过 `0x256a2d0` 向任何在限制内未发送的站点发送一个额外数据包：一个 Pia 消息，协议 0，中间字节 0xfd，端口 0，空负载（头部字节 `04 00`）。没有协议具有 id 0；读取器在下一次接收通开始时会回收未读消息（`0x2566030`），因此此类消息不会累积。字节 +0xa0 标记一个正在被踢出的站点（`0x2577094`）。

### 数据包标识

数据包标识在每个发送方上使用两个计数器：一个用于目的地 0x0001，一个用于所有其他目的地（0 和主机的可变 id 共享后者）。`nn::pia::session::SessionPacketReader::vfunc11` `0x2566920` 在任何协议之前检查：未知源或没有站点会被接受；否则目的地选择一个控制器（0x0001 为 station+0x78，否则为 station+0x50），并且 `0x2576ad0` 检查数据包标识（线上 0x0a）和大端序 nonce（线上 0x0d）：

    id == 0                                         接受，不记录
    last id == 0                                    last id = id - 1
    last nonce == 0 and nonce != 0                  last nonce = nonce - 1
    (s16)(id - last id) < 1                         拒绝
    nonce != 0 and (s64)(nonce - last nonce) < 1    拒绝
    否则                                            last id = id，last nonce = nonce（若非零）

被拒绝的数据包会进入 `0x25655d8` 并被丢弃：重复的 id，或者领先 0x8000 或更多的 id。为目的地 0 使用单独计数器的加入者，其每个 Net 0x51 都会被丢弃，直到它超过主机 id 计数器；主机会重复其 Net 0x50，直到有一个通过（约 10 秒，测量），其更新序列 1 被延迟。Net 0x51 处理器 `0x2504100` 不读取任何头部字段。

### 加入的其余部分

- Net：连接状态 0x11 用 0x12 应答，更新属性 0x50 用 0x51 应答。
- Session：类型 5 的更新会话用十五个字节应答：类型、站点的 LDN 常量 id、更新序列（大端序 u32）和 0x0001。GBA 应用程序的应答（原始 MAC，无序列）会让传说 Z-A 主机无限期地每两秒重复一次其更新。

接受更新序列 1 的主机约在 50 毫秒后发送其选择记录（测量为席位后 1.2 和 1.25 秒），并移动到其交换盒。

### 协议 10 上的交换

在选择记录之后，每一方都会发送一个 354 字节的 `0101`（测量为约 2.5 秒后）。提供的最后一个字节在站点主动发送的预览中为 1（零售主机每次光标在交换盒上移动时都会发送一个），在玩家选择时为 0；主机会依据该字节，而不是计数。以 1 发送的选择会被确认但不会显示，伙伴会在“正在通信”画面等待空槽位。

加入者用自己的选择回应主机的选择，并用 `0102b90100` 确认；主机同样确认，两者都发送 `0104b90100`（主机在加入者的 `0102` 后 1.5 秒），然后加入者发送四个 `0200b901XX` 步骤，03 和 06 立即发送，0b 和 0e 在交换动画和交换工作器的随机等待之后发送（[交换命令](#the-trade-commands)）。主机在协议 11 上发送 `0000000202`，并在其前缀下用 `0201b901XX` 回应每个步骤。`bin/za_join.py --trade-offer` 运行加入者。

## 提供的宝可梦

提供方的记录是第八、第九世代的实体：四个 0x50 字节块由加密常数打乱，存储 0x148 字节，加上队伍尾部为 0x158 字节，校验和覆盖存储体。`pokeldn.gen9.decrypt` 和 `read` 原样处理它；示例提供方读取的是一只异色嗡蝠，等级 44，完美个体值，球 22，特性 151，招式 542、103、403 和 162。来自三次参考会话的九条记录都读取到版本 52、语言 10、相遇地点 200 至 212、相遇日期在 2025 年 10 月、训练家 ID 5071、秘密 ID 14217、初训家“XS”、身高和体重标量为零；只有当设置了当前训练家时，现训练家名称才读取为“Player”。

由 `pokeldn.gen9.build` 从 344 个零字节组合（或用 `pokeldn.za.pokemon.build_offer` 编辑）的记录会交换并被保留：

| 字段 | 接收方游戏的行为 |
|---|---|
| 昵称 0x58、昵称位 0x8F 第 7 位、个体值 0x8C | 保留，朱的布局 |
| 物种 0x08 | 917 以下为全国图鉴编号，917 起为第九世代内部索引（`pokeldn.gen9.internal_index`、`national`） |
| 招式 0x72、四个 u16 | 按发送值保留（446、328、103、784 分别到达为隐形岩、流沙地狱、刺耳声、广域破坏） |
| 等级 | 根据 0x10 处的经验值：一只大岩蛇拥有 1,000,000 经验、队伍等级字节为 44，到达时等级为 100 |
| 能力、当前 HP | 根据物种重新计算；留零则会被填上 |
| 性格、球、携带物品、异色 | 保留 |
| 训练家 ID 12345、秘密 ID 54321 | 显示为 993401，即 `54321 << 16 | 12345` 的六位数字形式 |
| 相遇地点 202 | Wild Zone 18 |
| 特性 | 摘要中不显示 |

组合出的冰伊布（经验值 125,000、语言 3、相遇日期 2025-10-16、尺寸 128）显示等级 50、出生地为法国、体型等级 M。存档已持有的记录会再次交换，在新的加密常数和 PID 下但保持相同的 `hi ^ lo`（`--fresh-pid`）。

### 内存中的记录

每个字段访问器在 `x0` 中接收记录的访问器对象：

| 偏移 | 内容 |
|---|---|
| +0x08 | 指向 0x10 字节队伍尾部数据；对于存储的记录为 null |
| +0x10 | 指向 0x148 字节核心 |
| +0x18 | 核心加密时为 1 |
| +0x19 | 快速模式：为 1 时在访问器调用之间保持核心解密 |
| +0x1c | `nn::os::LightEventType`，当计数到等待者时释放信号 |
| +0x1e | 自旋锁所有者字节，空闲时为 0x5f |
| +0x1f | 等待者计数 |

    0xe5d810             16-bit word sum over the 0x140 bytes at core+8; checksum at core+6
    0xe5d8c0, 0xe5d940   crypt: seed = seed * 0x41c64e6d + 0x6073, XOR with seed >> 16, seeded by the
                         encryption constant at core+0 over core+8..+0x147, re-seeded over the tail
    0x3303ab0            block order: 32 rows of four bytes indexed by (EC >> 13) & 31, byte k for
                         block k; rows 0..23 are PKHeX's BlockPosition, rows 24..31 repeat 0..7

访问器（`0xe48000..0xe5d000`）会加锁；当 +0x18 置位时进行解密；校验和不匹配时重新计算校验和并设置坏蛋标志位（core+4 的第 2 位，在加密范围之外）；除非快速模式开启，否则之后会重写校验和并重新加密。坏蛋上的 getter 会从位于 `0x3f7eda0` 的默认记录读取。序列化器 `0xe47a20`（0x158 字节）和 `0xe47c60`（0x148）写出加密、乱序后的形式。

### main 2.0.2 读写的字段

偏移量位于解密、未乱序的记录中。代码未显示的名称是 PKHeX 的（`PKM/PA9.cs`）。

| 偏移 | 大小 | 读取函数 | 写入函数 | 字段 |
|---|---|---|---|---|
| 0x00 | 4 | every accessor | `0xe514d0` | 加密常数 |
| 0x04 | 2 | `0xe485f0` | `0xe51698` | 标志；第 2 位 坏蛋 |
| 0x06 | 2 | load path | `0xe48250` | 校验和 |
| 0x08 | 2 | `0xe49940` | `0xe52aa0` | 物种：917 以下为全国图鉴编号，917 起为第九世代内部索引 |
| 0x0a | 2 | `0xe49b40` | `0xe52cc0` | 携带物品 |
| 0x0c | 4 | `0xe49d50` | `0xe52ee0` | 训练家 ID 和秘密 ID，合为一个 u32 |
| 0x10 | 4 | `0xe49f60` | `0xe53100` | 经验值；等级 = `0xe5ce70(species, form, exp)` |
| 0x14 | 2 | `0xe4a3c0` | `0xe535b0` | 特性 |
| 0x16 | 2 | `0xe4d7c0` 第 1 位，`0xe4d9d0` 第 2 位 | `0xe56ad0..0xe57130` | 特性槽：第 2 位隐藏，第 1 位第二 |
| 0x18 | 2 | `0xe4a5d0` | `0xe537d0` | 标记 |
| 0x1c | 4 | `0xe4dbe0` | `0xe57350` | PID |
| 0x20 | 1 | `0xe4d3a0` | `0xe56690` | 性格 |
| 0x21 | 1 | `0xe4d5b0` | `0xe568b0` | 能力性格，能力例程读取的那个 |
| 0x22 | 1 | `0xe4cd70` 第 0 位，`0xe4cf80` 第 1-2 位 | `0xe56030`、`0xe56250` | 命运的相遇、性别 |
| 0x23 | 1 | `0xe5bcf0` | `0xe5bf00` | PKHeX 中的 IsAlpha（见下文） |
| 0x24 | 2 | `0xe4d190` | `0xe56470` | 形态 |
| 0x26..0x2b | 6 | `0xe4aa30..0xe4b480` | `0xe53c10..0xe546b0` | 努力值 |
| 0x48, 0x49 | 2 | none | `0xe5a7e0`、`0xe5aa00` | 身高和体重标量，仅写入 |
| 0x4a | 1 | `0xe512c0` | `0xe5ac20` | 尺寸 |
| 0x4b | 1 | `0xe5c120` | `0xe5c330` | 等级加成，PKHeX 中的 LevelBoost（见下文） |
| 0x58..0x71 | 26 | `0xe4ddf0` | `0xe57570` | 昵称，13 个 UTF-16 单元 |
| 0x72..0x79 | 8 | `0xe4b690(i)` | `0xe548d0(i)` | 四个招式 |
| 0x7a..0x7d | 4 | `0xe4b8b0(i)` | `0xe54b10(i)` | PP |
| 0x7e..0x81 | 4 | `0xe4bad0(i)` | `0xe54d50(i)` | PP 提升 |
| 0x8a | 2 | `0xe48820` | `0xe51ec0` | 当前 HP |
| 0x8c | 4 | `0xe4bcf0..0xe4cb60` | `0xe54f90..0xe55e10` | 六个 5 位个体值从第 0 位起，第 30 位蛋，第 31 位昵称 |
| 0x90 | 4 | `0xe48600` | `0xe516c0` | 状态异常 |
| 0x94..0x9f | 12 | `0xe5cb00(i)` | `0xe5c550(i)` | 逐招式标志 264..359 |
| 0xa8..0xc1 | 26 | `0xe50840`、`0xe50a70` | `0xe5a190` | 现训练家名称 |
| 0xc2 | 1 | `0xe50ca0` | `0xe5a3a0` | 现训练家性别 |
| 0xc3 | 1 | `0xe50eb0` | `0xe5a5c0` | 现训练家语言 |
| 0xc4 | 1 | `0xe4f780`，作为 `!= 0` | `0xe58a70` | 当前训练家 |
| 0xc6 | 2 | `0xe4f990` | none | 现训练家 ID（PKHeX 中为“未使用？”） |
| 0xc8 | 1 | `0xe4fdb0` | `0xe58eb0` | 现训练家的亲密度；`0xe4a170` 当 0xc4 为 1 时返回它，否则为 0x112 |
| 0xc9..0xcd | 5 | none | `0xe59910`、`0xe59b30`、`0xe59f70`、`0xe59d50`（0xcc 处的 u16） | 现训练家的回忆，仅写入 |
| 0xce | 1 | `0xe4e2a0` | `0xe57780` | 版本 |
| 0xd0 | 4 | `0xe5b280` | `0xe5b060` | 形态参数 |
| 0xd4 | 1 | none | `0xe5ae40` | 附加奖章，仅写入 |
| 0xd5 | 1 | `0xe4a7e0` | `0xe539f0` | 语言 |
| 0xd6..0xf6 | 33 | `0xe5cb00(i)` | `0xe5c550(i)` | 逐招式标志 0..263 |
| 0xf8..0x111 | 26 | `0xe4e4b0` | `0xe579a0` | 初训家名称 |
| 0x112 | 1 | `0xe4fba0` | `0xe58c90` | 初训家亲密度 |
| 0x113..0x118 | 6 | `0xe590d0`、`0xe592e0`、`0xe594f0`、`0xe59700` | `0xe4ffc0`、`0xe501e0`、`0xe50400`、`0xe50620` | 初训家的回忆：0x113、0x114、位于 0x116 的 u16、0x118 |
| 0x11c..0x11e | 3 | `0xe4e910`、`0xe4eb20`、`0xe4ed30` | `0xe57bb0..0xe57ff0` | 相遇日期 |
| 0x11f | 1 | `0xe5bae0` | `0xe5b8c0` | 服从等级 |
| 0x122 | 2 | `0xe4ef40` | `0xe58210` | 相遇地点 |
| 0x124 | 1 | `0xe4f150` | `0xe58430` | 球 |
| 0x125 | 1 | `0xe4f360` 第 0-6 位，`0xe4f570` 第 7 位 | `0xe58650`、`0xe58860` | 相遇等级、初训家性别 |
| 0x126 | 1 | `0xe5b6b0` | `0xe5b490` | 极限特训位 |
| 0x148 | 1 | `0xe49760` | `0xe518f0` | 等级，队伍尾部 |
| 0x14a..0x155 | 12 | `0xe48a40` 及另外五个 | `0xe51ae0..0xe528b0` | 最大 HP 和五项能力 |
| 0x156 | 2 | `0xe48c20` | `0xe51cd0` | 有符号最大 HP 偏移 |

访问器范围内没有任何函数触及这些字节，并且它们在每份主机生成的记录上都为零：

    0x1a..0x1b  0x2c..0x47  0x4c..0x57  0x82..0x89  0xa0..0xa7  0xc5  0xcf  0xf7
    0x115  0x119..0x11b  0x120..0x121  0x127..0x147

在朱的布局中（PA9.cs 保留）它们存放华丽大赛状态、宝可病毒、奖章和标记（0x2c..0x47）、回忆招式（0x82）、对战版本（0xcf）、蛋日期和地点、HOME 追踪器（0x127）以及 TM 记录（0x12f）。PA9.cs 将 0x4b..0x57 映射为 DLC TM 记录；main 只读取 0x4b。

| 字节 | 用途 |
|---|---|
| 0x4b | 能力等级 = `level + [0x4b]`，上限 200（`0x10f558`） |
| 0x156（s16，PA9.cs 未映射） | `0xe4163c` 使用 `max(1, maxhp + (s16)[0x156])`；加载路径从不写入它，因此组合值会保留 |
| 0x23 | 模型描述符 `0x106a48` 在 +0x13 存储 `[0x23] != 0`（`0x106ba0`），旁边的 +0x12 为蛋或坏蛋，以及尺寸为 `(scale / 255) * 2 - 1`；仅从 `0xe3f140` 调用 setter。在两个主机生成的记录（尺寸 255 的罗丝雷朵 407、冰伊布 471）上正好为 1。 |

0x4b 和 0x156 在每份主机生成的记录上都为零。

#### 逐招式标志

PA9.cs 的 plus 招式记录：360 位，当 k < 264 时位 k 位于 0xd6 + k/8，当 k >= 264 时位于 0x94 + (k - 264)/8（朱的太晶属性在 0x94/0x95 处，这里是标志 264..279）。招式的索引是其在 rodata `0x3303fb0` 处 340 个 u16 招式 ID 中的位置，由线性搜索 `0xe669e0` 查找（缺失时为 -1；每个调用者随后跳过该标志）。`0x631834` 设置一个标志，`0x673448` 清除一个，`0xe438e4` 清空数组，`0xe43068` 读取一个。拥有招式 446、328、103、784 的大岩蛇标志为 33 38 88 91 103 106 157 174 225 231 328 444 446 457 784。招式 58、103、162、247、328、403、423、446、542、573 和 784 在此列表中。

`0xe343a0(species, form, move)` 读取个人数据条目（vtable +0x36，经由 `0xe3cb88` 和 `0xe36850`）的字段 25，这是一个 {u16 招式, u8 等级, u8 解锁等级} 的向量，并返回匹配的解锁等级或 0。学习等级为 1..100、253 或 254。在 2.0.2 表中：

| 学习等级 | 解锁等级 |
|---|---|
| 1（4,803 项） | 10 |
| 3..100（14,717） | 学习等级 + 3；例外：99 为 100（6 个）和 102（1 个），33 为 37（2 个） |
| 254，当前物种 | 10（274 个中的 266 个）；其余为 19、20 或 22 |
| 253 | 10（192 个中的 48 个）；其余为 39、15、12、33、38 等 |

具有 vtable `0x3e28e58` 的 PokemonParam 包装器（321 个槽位，每个都是指向 +0x50 处 PokemonParam 的 thunk）以三种方式使用它：

| 槽位 | 函数 | 行为 |
|---|---|---|
| 135 | `0x6a30b0` | 列出解锁等级非零且与其等级参数相等的招式 |
| 145 | `0x631834` | 设置招式的标志，跳过 `0xe669e0` 找不到的招式 |
| 150 | `0x699308` | 当解锁等级非零且等级（`0xe49760`，或存储记录上根据经验值由 `0xe5ce70` 得出）达到它时为 true；否则为标志 |

标志可以使等级规则不允许的招式解锁；一个所有标志为零的记录仍然使其每个达到或低于其等级的可学招式解锁。位写入器 `0xe5c550` 仅从 `0x631864`（设置）和 `0x673478`（清除）进入。主机在某个等级上为槽位 135 列出的每个招式设置标志（`0x52fff0`、`0x824eb0`、`0x28eec70`），并且构造例程 `0x656060` 在字节 0x23 置位时写入并标记一个每物种招式到槽位 0（`0x6568c4`）。

接收或加载的记录会整体带来其标志；接收路径上没有任何内容读取该数组。

摘要画面 `0x8d0610` 根据槽位 150（`0x8d1a18`）将每个招式标记为“/plus_on”或“/plus_off”，当游戏标志 `flag_megaevo_disable` 置位时交换（`0x393b8`，具名标志读取，位于 `0x8d1438`；键记录 `0x3db5548`，FNV-1a-64 哈希 `0x5d0f3c74b46a0ff5`）。

主机生成的记录带有其等级及以下所有可学招式的标志，再加上物种通过进化在学习等级 253 或 254 获得的任何招式以及字节 0x23 的招式。

#### 特性

朱的 0x14 处 u16，0x16 处槽位位。GetAbility `0xe43bec` 在存储值低于 299（0x12b）时返回它，否则从个人表返回 `0xe5d368(species, form, bit 2 ? 2 : bit 1)`。0x14 的其他读取者只有属性 getter `0x99c84` 和 `0xa4354`（特性 121 的物种 493 和特性 225 的 773 从携带物品获取属性，`0xe5d528`、`0xe5d5a0`）。创建例程 `0xe3eb34` 和 `0xbb8f04` 从 `0xe5d368` 写入它。主机生成的记录存储 5、30、38、81、151、187。

没有任何画面显示存储的特性。`0xe43bec` 仅从 `0x288d894` 进入，这是引擎组件的槽位 42（vtable `0x3d1a7c8`）；七个 PokemonParam 包装器 vtable 使槽位 42 返回 0（`0x2d6fd88`），而对战特性窗口 `0x2d52468` 读取该槽位。

### 加载接收到的记录会检查什么
A partner's `0101` reaches `0xb2a44c`, registered for CommandSelectPokemon (`0xca33d8`, called
from `0xca2928`). The deserializer `0xb4e248` requires tag 0xb9 with three members (`0xb4e33c`),
reads the first as a u16 (`0xa91178`), requires the second to be tag 0xbc of exactly 0x158 bytes
(`0xb4e4b8`) and keeps the third at struct+0x15a; on any error the handler is not called
(`0xb4e1c8`). The handler allocates a PokemonParam (`0x82713c`) and loads the 344 bytes with
`0x270994`:





### 对收到的宝可梦进行名字检查

`0xad2c68` 对空记录返回（IsEmpty `0x13778`），否则运行 `0x89f250`（其他调用方
`0x89de34`）：它将一个 `nn::ngc::ProfanityFilter` 打开到全局 `0x612d3d0` 中，并使用 0x20000 字节的
缓冲区（`0x912e10`），用 `0x9138d4(str, len, language)` 检查三个名称，然后执行完成操作
（`0x912d80`）。

| name | language passed | on failure |
|---|---|---|
| nickname, 0x58 | the record's, 0xd5 | `0x8a0370` writes the species name in that language (`0xe33ca0`) and clears the nicknamed bit (0x8c bit 31) |
| original trainer's, 0xf8 | the record's, 0xd5 | `0x3d8a248[language]`, written with `0xe579a0` |
| handler's, 0xa8 | the handler's, 0xc3 | `0x3d8a248[language]`, written with `0xe5a190` |

语言为 12 或更大时，将该表索引为 0。`0x8a0370` 在 `[0x3f0784()]+0x380` 和 accessor+0x1a 均为 0 时，对蛋或坏蛋（`0xe4c950`、`0xe485f0`）不写入任何内容。替换表 `0x3d8a248` 保存十二个 UTF-16 字符串：0、1、6 `ゼット.`；2 `Z`；3 `Zed`；4、7、11 `Zeta`；5 `Zett`；8 `제트.`；9、10 `Z.`。

`0x9138d4` fails a name when:

- its length is 0 or its first unit is 0;
- it is 7 units or longer and any unit is in 0x3041..0x3090, 0x30a1..0x30fa, 0x4e00..0x9fcc or
  0xac00..0xd7a3 (lanes at `0x3308840`, `0x33087b8`);
- the language is 1..5, 7 or 11 and any unit before the first 0 is in 0x4e00..0x9fa0 other than
  0x4edd;
- L (from `0x444330`) is 0, 6 or above 11;
- the filter's vfunc +0x28, called by `0x913ad0` as `(&result, pattern, &str, 1)` with pattern
  `0x339f650[L - 1]`, leaves a non-zero result.

长度扫描 `0x913a80`（跳过 0x10 标记的运行）在没有过滤器的情况下测得为 0 次通过，返回错误的过滤器调用（`0x913b08`）也是如此。处理者名称为空且处理者语言为 0 时会变成 `ゼット.`，而原始训练家名称为空时会变成记录语言的字符串；完成交换后则会覆盖处理者的名称。PKLDN 和参考名称通过。

L，游戏文本语言，是单例 `0x6131800` 的字节 +0x14（GOT `0x3ec7800`；一旦 +0x80 标记其已构造，则由 `0x444330` 经 `0x410a20` 读取）。它被编号为记录的语言字节，并索引消息目录表 `0x3e278b8`（步长 0x18，`0x940dd8`）：0、1、6 为 "jpn"，2 为 "English"，3 为 "French"，4 为 "Italian"，5 为 "German"，7 为 "Spanish"，8 为 "Korean"，9 为 "Simp_Chinese"，10 为 "Trad_Chinese"，11 为 "Latam"，12 为 "item"。加载器 `0x410a30` 在其语言参数为 0（`0x410a68`）时使用 L。

启动时，L 来自 `nn::oe::GetDesiredLanguage()`，经由 `0x17d6368` 和表 `0x330f728`（1..5 或 7..11）。setter `0x17d62ec` 是它的唯一写入者；它的其他调用方包括语言选择视图（该视图只存储它列出的十个值）、带训练家记录 +0x47 的 `0xbb9d30`，以及一个没有任何已附带 Lua 包名称的脚本绑定 `0x1673170`。

The pattern `0x339f650[L - 1]` is a set of `nn::ngc` word lists, so the receiving console's
language picks them, whatever the record's language:

| L | pattern | lists |
|---|---|---|
| 1 Japanese | 0x13 | Japanese, American and British English |
| 2 English | 0x12 | American and British English |
| 3 French | 0x36 | American and British English, Canadian French, French |
| 4 Italian | 0x92 | American and British English, Italian |
| 5 German | 0x52 | American and British English, German |
| 6 | 0 | none; the name has already failed |
| 7 Spanish, 11 Latin American Spanish | 0x11a | American and British English, Latin American Spanish, Spanish |
| 8 Korean | 0x412 | American and British English, Korean |
| 9, 10 Chinese | 0x8813 | Japanese, American and British English, Chinese, Taiwanese |

### 交换写入接收记录的内容

Step 6 of the exchange calls trade object vfunc +0x80, `0xcbc68c`, which calls `0xcbc7fc`. Unless
`0xcbc9e8` returns null (`0xcbc854`, skipping the update), it fills a struct from the player's
trainer record (`0x505c30` on the singleton from GOT `0x3ec28d8`) with `0x882104`: u32 +0x40 (trainer
id and secret id), gender +0x45, language +0x47, 13 units of name from +0x50. It wraps the partner's
PokemonParam (trade object +0x78) with `0x825358` and calls wrapper slot 167 (`0xcbc888`, +0x538;
`0xcebfe0` in both wrapper vtables), a thunk to `0xcebfe8`:

- original trainer's gender (`0xe4f570`, 0x125 bit 7), u32 0x0c (`0xe49d50`) and name (`0xe510c0`)
  all match the struct: 0xc4 = 0 (`0xe58a70`), call `0xe3f900`, return 1;
- otherwise 0xc4 = 1, the struct's name (`0xe5a190`), gender to 0xc2 (`0xe5a3a0`) and language to
  0xc3 (`0xe5a5c0`), 0 to the handler's memory 0xc9, 0xca, 0xcb and u16 0xcc (`0xe59910`, `0xe59b30`,
  `0xe59f70`, `0xe59d50`), `0xe340ac(species, form)` to friendship 0xc8 (`0xe58eb0`), call
  `0xe3f900`, return 0.

接收到的宝可梦会将接收方玩家作为 handler，除非该玩家是其初训家。每个 setter 会对仍标记为已加密（+0x18）的记录重新计算校验和（`0xe5d810`），并在校验和不匹配时设置坏蛋位（`0xe58b60..0xe58b80`）；对于坏蛋，它会写入 `0x3f7ef98` 处的一个接收点（`0xe58bcc`）。

### personal 表

`0xe380c0` loads `personal_array.bin` from the directory `0x7961b0` configures as "avalon/data"
(`[[0x3f7f038]]`), as it does `waza_array.bin`, `tokusei_array.bin` and `growTable.bin`:

| | |
|---|---|
| `/arc/data.trpfd` | 9,877,520 bytes: 238,546 file hashes, 13,181 packs |
| `/arc/data.trpfs` | 4,753,821,072 bytes, magic `ONEPACK` |
| name hash | FNV-1a 64, basis `0xcbf29ce484222645` (`0xe38438`) |
| `avalon/data/personal_array.bin` | hash `0x68ab38e2cf1281ed`, file index 97074 |
| its pack | 169, `arc/avalondatatokusei_array.bin.trpak`, trpfs `+0x4bc1840`, 131,488 bytes, 4 files |
| its entry | compression type 3, 110,132 bytes, 384,260 decompressed by `OodleLZ_Decompress` `0x1a9c9e0` |

一个包含 1445 个表的 FlatBuffers 向量，1445 个不同键。字段 0 以物种和形态半字开头，由映射构建器 `0xe36170` 以 `species * 10000 + form` 作为键（键 0 位于 map+0x80）。物种范围为 0..1010，全部存在，434 个条目的形态大于 0；从 917 开始的键是第 9 世代内部索引。字段 1 在 364 个物种的 594 个（物种，形态）对中为 1，在其余 851 个中缺失。这 594 个组合与 PKHeX 的 `personal_za` 存在列表截至 1010 一致；PKHeX 的 1011..1016（14 对）没有条目，会以坏蛋形式出现。Mega Dimension DLC 不附带个人表（其唯一一个 PublicData NCA，101,376 字节，包含一个 692 字节的 RomFS）。物种 95、333、407、471、707、714 和 716 以形态 0 存在。

No refusal of a Bad Egg was found on the boxing or exchange path. `0x962388` boxes only a Pokemon
neither empty (IsEmpty `0x13778`) nor egg-or-bad (IsEgg `0x18e4c`), but the live trade path
`0x95f8f4` boxes the pick through `0x961964` (`0x960000`) directly. On the exchange the egg and Bad
Egg tests only skip work: the PP clamp `0xe42584` and the stat recomputation `0xe41750` (skipped by
`0xc34b5c`).

## 与零售版主机交换

零售版 Z-A 在连接交换搜索中与 `bin/za_join.py` 交换，并保留一条合成记录。交换后主机会返回到同一位上的交换盒，并且可以再次交换：`0x964568` 会将两个状态重置为 2，并将两个轮次重置为 0（[交换命令](#the-trade-commands)）。重复的 `--trade-offer` 会在两种角色中按顺序交换队列：第四步后 2.7 秒预览下一条记录，并在主机在回合 0 下的下一次选择时被选中（`tests/test_za_host.py`）。

交换动画在第四步之后运行，不携带消息。从该步起：动画在 1.1 秒时出现，收到的宝可梦约在 26 秒时显示在屏幕上，主机的下一次预览（`0101`，354 字节）在 30.2 秒时出现，玩家控制约在 31.7 秒时恢复。

在主机的主持阶段较晚形成的席位会被移交：关联后约 1.4 秒收到第一个数据报，之后没有更新序列 1，并且主机会每秒重复一次 Session 类型 9，直到它重启其 Net（测得 6.5 秒）。Wiki 将此类型编号为开始主机迁移和踢出 12，而 Z-A 使用 13。其背后的代码未被追踪。

## 主持

正在搜索的主机也会扫描，并加入一个带有本作广告及其链接码的网络。`bin/za_host.py` 主持一个；`pokeldn.za.host` 已针对一对模拟交换进行逐字节固定。

| 从席位来看 | 主机发送的内容 |
|---|---|
| 0 秒起，每 0.46 秒一次直到获得应答 | 网络连接状态 0x11：序列 2，四个槽位，主机与加入者在 12345 |
| 在 Session 加入时 | 向加入者 id 发送加入响应（类型 2，37 字节），将会话更新（类型 5，序列 0）发送到 0x0001 |
| 同时 | 在 INIT 下通过协议 10 发送身份；在协议 11 上捆绑发送身份和 `1403b9018269fb308f`，前缀为 `00000002` |
| 同时 | 网络更新属性 0x50，每 0.5 秒一次直到 0x51 |
| 从 0.2 秒起 | 向 0x0001 发送 RTT 请求，约每秒三次；对加入者的每个请求作出响应 |
| 更新 0 被确认后 1.15 秒 | 更新会话序列 1 |
| 更新 1 被确认后 | 发送 1211 字节的选择记录两次，间隔 60 毫秒 |
| 2.7 秒后 | 预览 `0101` |

与 GBA 应用程序的主机不同：

- 更新会话中主机的站点条目带有标识令牌 `0x06`；
- 更新的序列会被写入两次，位于 +1 和 +21 处；
- 属性更新在场景 id 之后携带 `02`，而 GBA 应用程序写入的是 `01`（CloseParticipation，见下文）；
- 广播确认在条目 1 中报告加入者的流，在其他三个条目中报告 0xfff0。

零售版 Z-A 会加入 `bin/za_host.py`，并在任意链接码（`--code`）下进行交换。主机在第四个交换步骤之后保持会话，并在主机用 B 键离开时关闭。`--hold-after-trade` 会启用定时关闭，从交换后主机的第一次预览开始计时；总的 `--seconds` 限制仍然适用。在定时关闭、`--seconds` 限制和 Ctrl-C 时，主机会先将会话交给已入席的主机（[主机离开](#a-host-leaving)）；之后处于盒子界面的主机会显示“你的交换对手选择退出交换。连接交换现在结束。”并返回到连接游玩。

陷阱：在交换保存后无移交就关闭网络，或在交换动画期间发送移交，会在主机上显示“错误编号：6”（交换已保存）。

交换后返回盒子时，主机会预览光标下的宝可梦，因此 `--offer-out` 只保留选取项。

### 属性更新

网络更新属性（类型 0x50）由 `0x2502960` 构建（序列位于 NetProtocol+0x160，经 `0x250f5d0`），并由 `0x250e414` 以大端序序列化。相对于 0x26 字节网络消息起始处的偏移：

| 线路 | 大小 | 字段 |
|---|---|---|
| 0x04 | 4 | 序列 id，NetProtocol+0x160 |
| 0x08 | 8 | 网络 id，会话属性 +0x90 |
| 0x10 | 2 | 参与者数量（`0x25050dc`） |
| 0x12 | 2 | 站点槽位，NetProtocol+0x1216 |
| 0x14 | 8 | 会话属性值（`vfunc +0x10`）；LDN 属性将场景 id 保存在 NetworkInfo +0x0a 处，偏移为 +0x98 |
| 0x1c | 1 | 接受状态（`0x2505ec0`） |
| 0x1d | 1 | 会话属性 `vfunc +0x80`，第 0 位 |
| 0x1e | 4 | 系统属性大小（`0x24fe4dc`） |
| 0x22 | 4 | 游戏数据大小（`vfunc +0x50`） |

`0x2505ec0` 在主机地址（+0x1280）和本站点自身地址（+0x1260）已设置后，或 +0x12d0 非零时，返回 NetProtocol+0x340 处的字节；否则返回 0。其写入者：

| 写入者 | 值 |
|---|---|
| 网络创建和自动连接作业（`0x2511b94`、`0x2511658`）以及第三个作业点 `0x2515714` | 当会话属性字节 +0xa6 被设置时为 1，清除时为 2 |
| `0x2515434`，来自作业字节 +0xc0（由 `0x2515220` 存储） | 通过 `0x250758c`（`NetFacade` vfunc 17）为 1，通过 `0x2507828`（vfunc 19）为 2 |
| 主机迁移 `0x250b060` | 当该字节为 1 时重新执行 1 路径，否则执行 2 路径 |
| 设置器 `0x2500a9c` | 来自 `0x25fdc90` 和 `0x25fe1ec` 时为 1 |
| 接收 0x50 的站点（`0x25035bc`） | 消息的字节；`0x2502e70` 将自身 +0xa6 设置为 `byte != 2` |

LDN 会话属性将 +0xa6 设置为 `stationAcceptPolicy == 0`（NetworkInfo +0x62，`0x25234b8`）。1 表示全部接受；2 表示该标志被清除。

2 路径，自顶向下：

0x1a25454   游戏任务槽 13（虚表 0x3c17cc0，构造函数 0x1a25390）：仅调用 0x253e744
                当会话在 +0xe0/+0xe8 的 (u64, u16) 非零且等于 +0xf0/+0xf8 时，
                主机测试 0x9157d0 成立；当 0x253da70 发现状态对象为 1 时返回
    0x253e744   -> 0x253e780 -> 0x253e7bc（当状态 +0xd0 读取为 1 或字节 +0x528 为 0 时为 0x10408）
                -> 0x2546fe8(0)，关闭 -> 0x255c118，OpenCloseParticipationJob（外观会话+0x30
                位于 job+0xc8）：OpenParticipation 0x255c264 调用外观索引 17，CloseParticipation
                0x255c404 调用索引 19（0x255c484）
    0x25183bc   外观索引 19（Net、Local、Lan、Wan、Nplnd 外观）：通过 0x2507828 进行操作 0xa；
                索引 17（0x251826c）：通过 0x250758c 进行操作 9
    0x2515220   0x250758c 传递 1，0x2507828 传递 2；当 [[job+0xe0]+0x344] 为 1 且 0x2513c0c
                返回 0 时，将其存储到 job+0xc0（0x25152c0），否则以 0x10408 失败
    0x2513c0c   将其存储到 LdnBackgroundProcessJob+0x9b（0x2513c6c，唯一写入者），调度
                vfunc 37 0x2513ccc：当 +0x9b 为 1 时 LDN 协议索引 23，否则为 24（0x2513d1c）
    0x2515434   将 job+0xc0 复制到接受状态（0x2500a9c），构建 Net 0x50（0x2502960）

`nn::ldn::SetStationAcceptPolicy`（PLT `0x3163b60`）由 LdnProtocol 索引 23（0，全部接受）、24（1，拒绝）和 21（3，白名单）调用。游戏关闭参与，并且仅在它是会话主机时，从 CloseSession 任务的更新 `0x1a25454` 开始，策略 1 才会跟随。

任务构建器 `0x1a228f0` 在两个会话驱动上以 "CloseSession"（哈希 `0x0dd344f64c81e84d`）调用。网络管理器（vtable `0x3c16978`）将其驱动保存在 +0x38；其设置器 `0x199e850` 按模式安装：0 无，1 本地驱动（`0x199eaa0`），2 互联网驱动（`0x199ecc0`，用于排位对战），3 LAN 驱动（`0x199ef70`）。模式来自 "InitializePia" 任务，由到本地序列（连接交换、私人对战）以 1 构建，由到互联网序列以 2 构建；没有调用以 3 构建它，因此在 2.0.2 中 LAN 驱动从未被安装。

| 构建器 | 驱动，槽位 | 游戏功能 |
|---|---|---|
| `0x19d7a70` | 本地，13（RandomMatchingSeq 的 CloseSession 步骤） | 连接交换搜索 |
| `0x19a7590` | 本地，19 | 私人对战 |

槽位 13 在 `0xc8a224` 处被调用一次，来自连接交换（`0xc9f8ec`，会话 "BoxTrade"）和排位对战。连接交换搜索运行本地驱动的槽位 13（`0x19a1310`），第四个参数为常量 1（`0xc8a194` 处的 `mov w3, #1`），因此其 CloseSession 步骤会构建该任务。槽位 19 的调用者仅来自私人对战页面。

在零售版连接交换搜索中，广告在席位持有策略 0；Pia 玩家计数（广告数据 +0x16，`e1 01 01 00` 到 `e1 01 02 00`）在 0.6 秒内变为 2，然后正当主机唯一的 Net 0x50（150 字节，序列 1，接受状态 `02`）之前广告策略 1，并在会话期间保持为 1。之前没有主机迁移，因此 `02` 来自 CloseParticipation，来自槽位 13 的步骤 `0x19d7a70`。有 2 个参与者中的 2 个时，该策略不会拒绝任何容量未拒绝的内容。

## 离开

站点通过两个 `nn::pia::session` 作业之一离开，每个作业都等待另一个站点的回复。调度器 `0x2547490` 读取的会话类型（表 `0x336a9b7`，类型 0 到 17）：

| 类型 | 大小 | 发送方 | 消息 |
|---|---|---|---|
| 3 | 22 | 离开的加入者 | 离开请求：类型、随机 u32、其 constant id（8，大端序）、其 variable id（2）、地址类型 0、其 IPv4、端口 |
| 4 | 15 | 主机 | 离开响应：类型、随机 u32、从请求中复制的离开者 constant 与 variable id |
| 9 | 30 | 离开的主机 | 开始主机迁移：类型、主机 constant 与 variable id、0、主机 IPv4 与端口、下一台主机的 constant 与 variable id、`00 01` |
| 10 | 21 | 类型 9 所指的站点 | 其确认：类型、它自己的 constant 与 variable id，然后是主机的 |

`pokeldn.za` 构建全部四种（`build_leave_request`、`build_leave_response`、`build_migration_ack`）。

### 加入者离开

`LeaveMeshJob::SendLeaveRequest`（`0x2557e54`）向主机发送类型 3，并设置 500 ms 截止时间；`WaitLeaveResponse`（`0x2558098`）在收到类型 4 时完成，并在每个截止时间重新发送，总共发送四次（计数器 +0x9c，`cmp w8, #2; b.gt` 位于 `0x25581e0`），然后在没有收到的情况下也完成。`0x25474f8` 仅在 15 字节且字节 5 到 14 是该站点自己的 id（+0x1b8、+0x1c0）时才接受类型 4；它会设置作业的字节 +0x99。主机的类型 3 处理器 `0x254c5ac`（22 或 34 字节，仅主机）在 `0x254c740` 写入类型 4，并移除该站点（`0x2548500`）。

如果主机不发送类型 4，零售版 Z-A 会发送四次类型 3，间隔约 0.5 秒，并在第一次发送 2.0 秒后解除认证。`bin/za_host.py` 对每个类型 3 都回复类型 4；`bin/za_join.py` 在 `--hold` 或 `--hold-after-trade` 离开时发送自己的类型 3，并在收到类型 4 或完成第四次发送后退出。

### 主机离开

`LeaveMeshWithHostMigrationJob` 指定下一台主机（`CalcNextHost` `0x255a6fc`），然后 `SendStartHostMigrationMessage`（`0x255a91c`）每秒发送一次类型 9，直到 5000 ms 截止时间（`0x255a8c8`），之后作业以 `0x6c0e` 失败。`WaitStartHostMigrationAck`（`0x255abb4`）在字节 +0xe0 被设置后立即完成。类型 10 读取器 `0x2550a64` 仅在主机上接受 21 字节消息，且仅当字节 11 到 20 是主机自己的 id 时，并在字节 1 到 10 是被指定的下一台主机的 id 时通过 `0x255a630` 设置 +0xe0。

| 加入者的回应 | 零售主机在其类型 9 之后的行为 |
|---|---|
| 无 | 五个类型 9，间隔一秒；Net 0x11 序列 3 每 0.5 秒一次持续 4 秒；Net 0x40 持续 2 秒；10.8 秒时静默；11.3 秒时网络断开 |
| 类型 10，然后 0x12 `0112000000000003` | 0x11 在 0.04 秒发出；Net 0x40（`01 40 00 00`，源 0）每 0.3 秒一次持续 4 秒，直至加入者保持 |

加入者的类型 10 与 0x12 发出时带有头标志 2、目的地址 0、数据包 id 0 且无尾部。

Net 0x11 是离开主机在 `NetDestroyNetworkJob`（`0x2516444`，标志位于 job+0xd8，在断开站为主机时设置，`0x2503c44`）的迁移形式中的连接状态：`0x2501930` 递增序列（NetProtocol+0x15c）；字节 29（is-migrating 字节）在 NetHostMigration 状态 NetProtocol+0x12d0 为 1 时为 1（`0x250f084`）。它向每个客户端请求该序列的 Net 0x12；客户端存储序列、设置 NetProtocol+0x308 并回复（`0x2503164`、`0x25035c0`）。主机等待每个 0x12 最多 4000 ms，然后每 300 ms 发送 0x40，持续 4000 ms（若等待超时则持续 2000 ms），直到只剩它自己，并销毁其网络（`0x251693c`、`0x25169f8`）。

迁移形式与开头的 0x11 在三处不同：序列、字节 26（开头形式为 1，迁移形式为 2；含义未读）和字节 29。零售与模拟主机从源 0、目的地址 0、数据包 id 0、头标志 `0x3`（建立中、压缩）且无尾部发送它；0x40 以相同方式发出，但标志为 2。类型 9 从主机发送到被指定站点的 variable id，带有尾部。

0x40 在非主机站点上启动主机迁移（`0x2503d44` -> `0x25099a4`、`NetHostMigrationJob` `0x2509da0`）：下一台主机打开网络并等待其他站点 6000 ms；客户端等待 1000 ms 并重新连接。

连接交换在交接时结束：类型 9 处理器 `0x2550684` 移除离开主机的站点，交换场景更新 `0x95f398` 在会话的站点计数（session+0x110）为 1 时以原因 3（`0x95f508`）结束交换。

在两台坐在交换箱中的模拟 Z-A 2.0.2 游戏机之间，主机玩家退出（按 B，然后选择“是”）会依次执行类型 9、类型 10、字节 29 置位的 Net 0x11 序列 3、0x12，然后在类型 9 之后 0.12 秒发送 0x40；另一站点在 0x40 之后 4 ms 离开网络，不创建网络，并显示“Your trading partner chose to quit trading. The Link Trade will now end.”

`bin/za_join.py` 对指定它的类型 9 回复类型 10，对其后的 Net 0x11 回复 0x12，并在第一个 Net 0x40（或主机静默一秒后）离开网络。

`pokeldn.za.host.HostSession.leave` 以相同的时间执行相同的离开；`tests/test_za_host.py` 固定了类型 9 和两条 Net 消息。

## 神秘礼物

2.0.2 中的神秘礼物提供“通过互联网接收”“使用代码／密码接收”和“查看神秘礼物”；没有本地无线路径。

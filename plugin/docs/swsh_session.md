---
title: The cartridge and the session
parent: Sword and Shield
nav_order: 1
---

# 卡带与会话

`main` 静态链接了全部 Pia（252 个 `nn::pia` 类，2036 个虚方法），并导入了 `nn::ldn`。在 Pia 之上，游戏使用 protocol buffers：`main` 为 78 个 P2P 消息集（`gflnet.p2p.framework.pb`、`.block.pb`、`.sync.pb`，每个内容一个包：交换、对战、露营、团体战）都携带了一个 `FileDescriptorProto`。

## LDN 密码短语

    W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL

64 字节，原始（两份，`0x203ff04` 和 `0x203ff45`）；与 NintendoClients wiki 的朱／紫行相同，与传说 阿尔宙斯差一个字符（此处 `HGhG`，彼处 `HGHG`）。setter 调用位于 `0x006c3ec8`，长度为 `0x40`。`nn::pia::local::LdnCreateNetworkJob` 在 +0xC4 保存密码短语，+0x104 保存长度，+0xB8 保存本地通信 id；它在 `nn::ldn::CreateNetwork`（`0x017972bc`）之前将密码短语复制到 `SecurityConfig+4`。`LdnBackgroundProcessJob` 要求长度为 16..64。

## Pia 游戏密钥

    p1frXqxmeCZWFv0X

位于 `0x01c3dc87` 的十六个 ASCII 字节，被三个调用点原样使用（wiki 的剑／盾行）；创建／加入调用是 `0x183fd10`，来自 `0x006ca914..0x006ca93c`。

## 读取卡带

    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --keys prod.keys --type Program
    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --nca 87e41bc8 --exefs 0 --extract main
    ./.venv/bin/python tools/switch/nso_read.py main
    ./.venv/bin/python tools/switch/rtti_names.py main.bin 0x1900fc0 --rodata 0x1901000:0x24da168

`main` 的 text 为 0..0x1900fc0，rodata 到 0x24da168，data 到 0x2635f38。方法：[逆向一个 Switch 游戏](switch_re.md)。

`/bin/message/<Language>/common/*.dat` 使用第六／第七／第八世代消息容器：第 *n* 行的键起始于 `0x7C89 + n * 0x2983`，每个字符左移 3 位（每行以 `0x0000` 结尾）。`.tbl` 是一个 `AHTB` 索引，条目 *i* 对应第 *i* 行。

## Pia 4

Pia 头携带版本 4，这一形态与 [Pia 层](pia.md)中的两个频段都不同；其下是 5.27 的 LDN 家族（相同的密钥、IV、帧格式，外加一个字段）。`pokeldn/ldn/pia4.py` 实现了它。`pokeldn.swsh.session_keys` 是 BDSP 的派生，不做版本替换：

    session key   = ldn_session_key(GAME_KEY, application_data[12:16] little-endian)
    IV            = crc32(application_data[0:4] || the sender's MAC)[0:3] || source id || nonce
    tag           = sixteen bytes, checked in full

484 个零售包全部通过认证，每个包的 source id 均为 0。第二条路径 `0x0179bff0` -> `0x01774f40` 使用会话的两个 64 位值作为 AES-GCM 的种子；本地交换只需要广播。

## 入座

    POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_join.py --keys PROD_KEYS --scan-only

扫描一个正在主持的屏幕，并将每个广播写入 `scratchpad/swsh_net_facts.json`。

| 画面 | 本地通信 id | 版本 | 场景 | 应用版本 |
|---|---|---|---|---|
| 连接交换 | `0x0100ABF008968000`（剑的） | 4 | 60001 | 7 |
| 本地无线神秘礼物 | 相同 | 4 | 65535 | |

盾使用剑的 id；其 `control.nacp` 中列出 `LocalCommunicationId[0] = 0x0100ABF008968000`、`[1..7] = 0x01008DB008C2C000`。

应用数据的 384 字节：

    0x00  4  network id, random per session
    0x04  4  CRC32 of the Link Code's ASCII digits, LE; 0 with no code (12345678 -> 0x9AE0DAAF)
    0x08  1  system communication version, 5
    0x09  1  header size, 0x18
    0x0A  2  padding
    0x0C  4  session param, random per session
    0x10  8  zero
    0x18  2  CRC16 over 0x1A..0x180 (`0x0065dcb0`, `pokeldn.swsh.beacon.crc16`)
    0x1A  2  network version word, 12 bits, 0x0D70 (`0x006c17c0` from `0x02068848`)
    0x1C  1  bit 0 from `0x006b5c10`; set is refused
    0x1D  1  payload type, 0 for station info
    0x1E  1  page byte, 1 and 2 in turn every third publish (`0x0111aac0`)
    0x1F 266 the player profile, as in the trade snapshot at 0xAEC
             ([the protocol page](swsh_protocol.md#the-player-profile)); zero to the end

`Connect failed with status code 1` 表示关联被拒绝；在同一次搜索上的下一次尝试可以关联。正在搜索的剑会在一个 comm id 下广播两个网络：它的 Y-Comm 信标（场景 65535），以及在第二条消息之后，它的匹配网络（场景 60001）。信标上的一个站点在 16 次加入中有 0 次到达交换箱；`bin/swsh_connect.py` 只加入场景 60001，并不断重新扫描直到它出现。关联后，主机向 `169.254.x.255:12345` 广播 Pia（大约每秒十个包）。一个已加入站点离开后是什么结束主机的广播，这一点尚未解读。

## 正在搜索的剑如何找到伙伴

在 Y-Comm 画面上，每台主机都在场景 65535 主持一个信标网络，并且大约每秒浏览一次（`0x006c3630`：主持 `0x006c3840`，浏览 `0x006c3770`，条件来自 `0x006c4550`、`0x0183fac0`，仅基于 comm id 和网络类型）。通过 CRC 和版本关卡（`0x006c1be0`）的记录到达附近玩家注册表（`0x0110f270`），后者丢弃自己的记录（广播 0x1F 处的设备 id 和 0x2F 处的账户 uid，`0x0111b160`）以及任何没有网络 id 和场景配对的记录（`0x0110f2d4`）。这里没有任何东西加入。

连接交换，然后是普通交换，会显示两条消息，每条都在等待按 A。第二条之后，`0x00fba940` 调用 `SetMode(comm, 2)`（`0x01096d10`）；`0x01095f10` 依次经历状态 0、5、3、4、6，状态 6 调用 `StartRandomMatching`（`0x010fcff0`）并传入场景 60001（`0x01096730`）。停留在第一条消息的主机永远不会调用 `SetMode(comm, 2)`，也永远不会匹配。

匹配层加入一个网络（`0x006c9e70`、`0x006cb8e0`，加入 `0x006ca1c0`），条件是：

    scene 60001, equal to its own
    node count 1, below its maximum of 2; network type 2; node count maximum 8 or less
    advertise 0x04 zero: a search without a link code refuses a password
    advertise 0x00, a u32, greater than the searcher's own
    advertise 0x00 not among ids whose join failed this search (0x80 entries)

连接密码只会改变 0x04。`bin/swsh_connect.py`（无密码）加入一台设置了密码的主机并进行交换；`bin/swsh_host.py --code 12345678` 会被设置了密码的搜索加入，而没有密码时永远不会。较大的 id 担任主机，所以两台正在搜索的主机只能单向配对；主机会广播一个接近 0xFFFFFFFF 的 id。

## 主机首先说的话

Pia 本地协议 0x24，与 BDSP 中相同（`pokeldn.ldn.local_protocol`）：版本 1，类型 0x11，0x30 个固定字节，八个九字节座位，主机迁移字节。`allow_participating` 为 true，所以主机在说 Pia 之前将加入者列入表中：站点 0 是位于 `169.254.14.1:12345` 的主机，站点 1 是位于 `169.254.14.2:12345` 的座位。

主机会重复更新会话，直到每个站点确认（0x21）。只有携带其 sequence id 的确认才会停止重新广播（13 毫秒内）。头字节 0x05 和 IV 的 source id 为 0。

## Pia 会话对象

`[[0x02616a30]]`（也是 `[0x02630f40]`），交换代码在此读取站点 id，是 Pia 的会话对象：0x270 字节，无 vtable，由 `0x0183ddb0` 从 `0x006a8644` 分配一次。在 LDN 上，网络工厂是 `LdnNetworkFactory`，其槽 73（`0x01791080`）构建一个 0x7220 字节的 `LdnMatchmakeSession`。

| 字段 | 写入者 | 值 |
|---|---|---|
| `+0xf0` | `0x018418a0` (`0x01841918`) | 这台主机自己的站点 id |
| `+0xf8` | `0x018418a0` (`0x01841990`) | mesh 主机索引（`[[0x0262f7b0]]+0xab`）处的站点 id；当 `[obj+0xd4] == 4` 时跳过 |
| `+0xf8` | `MeshEventListener` slot 2 (`0x01843580`), event 1 | 离场主机上的后端槽 30 |
| `+0xf8` | event 2 | 来自 `0x017d6080` 的 id（模式 2），或后端槽 30（仅模式 4） |
| `+0xf8`, `+0x100` | event 3 | 当 `[obj+0xd4] != 3` 时为零 |

`0x018418a0` 在创建（`0x018394d8`）和加入（`0x0183d9b0`）时运行。对于普通 LDN 创建和加入，模式 `+0xd4` 为 2；只有在 `LanMatchJointSessionJob` 和 `NexMatchJointSessionJob`（`0x01839cc0`、`0x0183a040`）中才为 3 或 4，当 `w8 - 6 < 3`（`0x0183a2b8`）时为 4。

事件 1 的槽 30 存储要求离开的 id 等于 `+0xf8` 且不同于 `+0x100`，`0x01840b90(obj)` true（本地 mesh 控制器的 `+0x281` 和 `+0x234`，均在创建时设置），`+0xd8 == 1`，`[mesh+0x64] == 0`，以及一个来自 `0x0184a4b0` 的映射，其字非零且与 `obj+0x180+4*[obj+0x162]` 处的字不同。事件 2 只有在 `[obj+0xd8] - 2` 至少为 6 且 `0x01841350` 与 `0x01769ec0([obj+0x38])` 均为 false 时，才会到达主机 id 存储。

当 `[this+0x18]` 为空时，`LdnMatchmakeSession` 槽 30（`0x017a23d0`）返回 `0xff`，否则返回 `[[this+0x18]+0x18]+0x2c0+8` 处 16 字节地址的 `0x017672d0`：当所有字节为零时为 0，当最后十二个字节为零时为其前四个字节，否则错误 `0x10c07`。槽 28（`0x017a23b0`）是 `0x018407f0` 所做的调用。

当 `+0xf0` 非零、等于 `+0xf8` 且后端槽 28 一致时，`0x018407f0` 为 true：即主持 Pia 的 mesh 的主机。主持交换的主机会根据命令爬上确认阶梯；加入了 pokeldn 主机的主机则跟随共享值（[泵](swsh_trade.md#the-pump)）。

## 到达游戏层

游戏之下的每一层都可以双向工作（[Pia 层](pia.md)）：本地协议 0x24、站点握手 0x14、mesh 加入 0x18、RTT 0x58、可靠窗口 0x7C 和 0x80。

加入者的 0x14 连接响应必须是剑发送的 840 字节形式（`host4.build_host_response`：账户 id 在 0x11，玩家名在 0x88，尾部在 0xB1，令牌在 0xBC）；`bin/swsh_connect.py --respond` 会发送它。模拟的盾 1.3.2 主机在 56 字节响应之后不会发送任何游戏消息。零售剑在 17 字节响应后即可完成交换（[Pia 层](pia.md#what-a-connection-response-must-satisfy-to-be-read)）。

如果不加干预，主机会重复 `61 00 00 00 0a 00`，这是一个 ping（大约每秒四次）；0x80 每秒询问一次 ack id 1，0x7C 保持沉默。`bin/swsh_connect.py --send-data HEX --send-protocol 0x7c` 发送应用数据（`reliable4.build_data_message`；五次静默接收检查：[版本 4](pia.md#version-4)）。通过信号：0x80 的 ack id 从 1 移开，或者 0x7C 有任何 ack。

## ping 握手

有效负载是一个四字节小端消息 id 和一个 protobuf 主体。握手携带以下五条消息（`gflnet.p2p.sync.ping.pb`、`gflnet.p2p.block.pb`）：

    0x7C  61000000 0a00      97 SyncPingDataHolder, field 1 ping {}
    0x7C  61000000 1200      97, field 2 pingReply {}
    0x7C  61000000 1a00      97, field 3 pingSynced {}
    0x7C  60ea0000 0a00      60000 BlockDataHolder, field 1 result {}  (Result { bool isBlocking })
    0x80  60ea0000 12020801  60000, field 2 imReady { isReady: true }

回答会按五个步骤推进游戏：

    1  answer the ping continuously   --send-data 610000000a00 --send-mirror --send-count N
    2  ack every reliable window      0x7C, 0x18 port 1, 0x80; one unacked window kills the mesh
    3  answer `result{}` on 0x7C      the mirror is per protocol
    4  answer imReady on 0x80         --send2-data 60ea000012020801
    5  the console sends its party on 0x84

- 单个 ping 应答只会引出一个 `pingReply`，然后游戏恢复到 ping 状态。
- 在主机请求之前发送的 `pingReply` 会停止其心跳。
- 在 0x7C 上发送 `imReady` 不会引出 0x84；它应在 0x80 上发送。
- 延迟确认的消息会被重发，并且可能在其后继之后到达。只有高于最新序号的消息才会替换当前消息。

`bin/swsh_connect.py --sync-answers` 在它有规则的地方回答 `trade.SYNC_ANSWERS`，在其他地方按协议回显，并打印每个没有规则的负载。

## 离开

剑版离开交换会话时会发送 box 命令 3，并在约 0.77 s 后开始按其角色执行 Pia 离开。每一步都等待回复，若没有回复则超时后继续执行。

作为加入方离开主机的剑版：

| 步骤 | 剑版发送 | 主机应回复 | 未应答 |
|---|---|---|---|
| mesh 离开 | LEAVE_REQUEST `04 <own index>`，0x18 端口 1，可靠，一次 | LEAVE_RESPONSE `08 <host index>` | 5.0 s |
| 站点断开 | 0x14 上的 `03`，每 0.5 s | `04` | 8 次请求，3.6 s |
| LDN | 离开网络 | | |

若两者均未应答，剑版会在 LEAVE_REQUEST 后 9.0 至 9.1 s 离开 LDN 网络；若两者均得到应答，则在 0.14 s 后离开。版本 4 主机处理程序 `0x017c19a0` 通过 `0x017c2450` 发送 `08` 和自身索引（两份不可靠副本）并断开站点；0x14 处理程序 `0x017c6110` 向发送方回复 `04`。`pokeldn/ldn/host4.py` 会回复这两者。

作为主机离开客户端的剑版（它是 LDN 接入点）：

| 步骤 | 剑版发送 | 客户端应回复 | 未应答 |
|---|---|---|---|
| mesh 迁移 | MIGRATION_START `44 00 01`（[主机迁移](swsh_trade.md#host-migration)） | MIGRATION_FINISH 和一条 UPDATE_MESH 声明自己为主机 | 5.0 s |
| 本地会话 | 它的更新会话（0x24 类型 0x11，主机迁移字节 1，新序列 ID），约每 0.11 s | 该序列 ID 的 0x21 ack | 10.0 s |
| 销毁网络 | START_HOST_MIGRATION `01 13 00..`（16 字节），每 0.33 s | 离开 LDN 网络 | 10.0 s |

在收到 MIGRATION_FINISH、以主机身份发送 UPDATE_MESH、收到 ack 并离开后，零售版剑的最后一个数据包在 MIGRATION_START 后 0.17 s 出现；若完全不回应，它会持续发送 25.0 s。

- `LocalDestroyNetworkJob::WaitUntilAllClientsDisconnection` (`0x017acd70`) 会在仅剩主机时或 `0x2710` ms 后销毁网络，并每 `0x12d` ms 重发 START_HOST_MIGRATION（`0x017acbd0`、`0x017a8bb0`）。
- ack（处理程序 `0x017a9250`，本地类型 0x21）只有在自身序列 ID 与消息的序列 ID 相等时才会清除发送方的位（`0x017aed10`）。限制 10.0 s 本地会话步骤的原因尚未解读。
- START_HOST_MIGRATION 不携带序列号（`0x017abc60` 在 0xC 处写入 0），也没有任何内容对其确认。

`bin/swsh_connect.py --answer-migration --update-mesh --leave-with-host`（在 `--preset trade` 中）会完成上述三项应答。

## 操作注意事项

- 在实际运行中切勿使用 `--verbose`；请改用 `--capture FILE`。
- 主机的信道会在会话之间变化（曾观察到 1 和 6）；扫描会保留最繁忙的信道（[信道](ldn.md#channels)）。
- `0x2D0`（在 `0x006a970c`、`0x006a9740` 处分配）是会话单例的大小（`0x006b4410`，全局 `main+0x02616758`），这是一个 720 字节的结构，与神秘卡片无关。

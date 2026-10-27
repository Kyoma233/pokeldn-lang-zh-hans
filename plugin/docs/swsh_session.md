---
title: The cartridge and the session
parent: Sword and Shield
nav_order: 1
---

# 卡带、密钥与入席

`main` 静态链接全部 Pia（252 个 `nn::pia` 类，2036 个虚方法）并导入 `nn::ldn`。Pia 之上，游戏使用协议缓冲区：`main` 包含 78 个 P2P 消息集的 `FileDescriptorProto`（`gflnet.p2p.framework.pb`、`.block.pb`、`.sync.pb`，每个内容类型一个包：交易、对战、营地、团体战）。

## LDN 密码

    W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL

64 字节，原始格式（两份副本，`0x203ff04` 和 `0x203ff45`）；与 NintendoClients 维基 Scarlet/Violet 行一致，与 Legends: Arceus 相差一个字符（此处为 `HGhG`，彼处为 `HGHG`）。设置调用位于 `0x006c3ec8`，长度为 `0x40`。`nn::pia::local::LdnCreateNetworkJob` 在 +0xC4 处保存密码，+0x104 处保存长度，+0xB8 处保存本地通信 ID；在调用 `nn::ldn::CreateNetwork`（`0x017972bc`）之前将密码复制到 `SecurityConfig+4`。`LdnBackgroundProcessJob` 要求长度为 16..64。

## Pia 游戏密钥

    p1frXqxmeCZWFv0X

十六个 ASCII 字节，位于 `0x01c3dc87`，被三个调用站点原样使用（维基的 Sword/Shield 行）；创建/加入调用为 `0x183fd10`，来自 `0x006ca914..0x006ca93c`。

## 读取卡带

    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --keys prod.keys --type Program
    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --nca 87e41bc8 --exefs 0 --extract main
    ./.venv/bin/python tools/switch/nso_read.py main
    ./.venv/bin/python tools/switch/rtti_names.py main.bin 0x1900fc0 --rodata 0x1901000:0x24da168

`main` 的文本段为 0..0x1900fc0，rodata 段到 0x24da168，data 段到 0x2635f38。方法：[逆向工程 Switch 标题](switch_re.md)。

`/bin/message/<Language>/common/*.dat` 使用第 6/7/8 代消息容器：第 *n* 行的键从 `0x7C89 + n * 0x2983` 开始，每字符左旋 3 位（每行以 `0x0000` 结尾）。`.tbl` 是一个 `AHTB` 索引，第 *i* 个条目对应第 *i* 行。

## Pia 4

Pia 头携带版本 4，形状与[The Pia layer](pia.md)中的两个频段均不同；其下为 5.27 的 LDN 家族（相同密钥、IV、帧格式加一个字段）。`pokeldn/ldn/pia4.py` 实现了它。`pokeldn.swsh.session_keys` 是 BDSP 的派生公式，无版本替换：

    session key   = ldn_session_key(GAME_KEY, application_data[12:16] little-endian)
    IV            = crc32(application_data[0:4] || the sender's MAC)[0:3] || source id || nonce
    tag           = 十六字节，全部校验

484/484 个零售数据包通过认证，每个数据包的源 ID 为 0。另一条路径 `0x0179bff0` -> `0x01774f40` 用会话的两个 64 位值作为 AES-GCM 的种子；一次本地交易只需要广告包。

## 入席

    POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_join.py --keys PROD_KEYS --scan-only

扫描主持屏幕并将每个广告写入 `scratchpad/swsh_net_facts.json`。

| screen | local communication id | version | scene | app version |
|---|---|---|---|---|
| Link Trade | `0x0100ABF008968000` (Sword's) | 4 | 60001 | 7 |
| Mystery Gift local wireless | same | 4 | 65535 | |

Shield 使用 Sword 的 ID；其 `control.nacp` 列出 `LocalCommunicationId[0] = 0x0100ABF008968000`，`[1..7] = 0x01008DB008C2C000`。

384 字节的应用数据：

    0x00  4  network id，每会话随机
    0x04  4  Link Code ASCII 数字的 CRC32，LE；无代码时为 0（12345678 -> 0x9AE0DAAF）
    0x08  1  system communication version，5
    0x09  1  header size，0x18
    0x0A  2  padding
    0x0C  4  session param，每会话随机
    0x10  8  zero
    0x18  2  CRC16 over 0x1A..0x180 (`0x0065dcb0`，`pokeldn.swsh.beacon.crc16`)
    0x1A  2  network version word，12 位，0x0D70 (`0x006c17c0` 来自 `0x02068848`)
    0x1C  1  来自 `0x006b5c10` 的 bit 0；设置时拒绝
    0x1D  1  payload type，0 表示站点信息
    0x1E  1  page byte，每第三个发布时依次为 1 和 2 (`0x0111aac0`)
    0x1F 266 玩家资料，同交易快照中 0xAEC 处
             ([协议页](swsh_protocol.md#the-player-profile))；至末尾为零

`Connect failed with status code 1` 是一次被拒绝的关联；在同一搜索中重试可以建立关联。搜索中的 Sword 在一个通信 ID 下广告两个网络：其 Y-Comm 信标在 scene 65535，以及在第二个消息之后，其匹配网络在 scene 60001。信标上的一个站点在 16 次加入中 0 次到达交易框；`bin/swsh_connect.py` 仅加入 scene 60001 并重新扫描直到出现。关联后，控制台向 `169.254.x.255:12345` 广播 Pia（约每秒十个数据包）。什么结束了已加入站点离开后的控制台广告，尚未阅读。

## 搜索中的 Sword 如何找到伙伴

在 Y-Comm 屏幕上，每个控制台在 scene 65535 上主持一个信标网络并大约每秒浏览一次（`0x006c3630`：主持 `0x006c3840`，浏览 `0x006c3770`，依据来自 `0x006c4550`、`0x0183fac0`，仅依通信 ID 和网络类型）。通过 CRC 和版本门控（`0x006c1be0`）的记录到达附近玩家注册表（`0x0110f270`），该注册表丢弃自己的记录（设备 ID 在广告 0x1F，账户 UID 在 0x2F，`0x0111b160`）以及缺少 network id 和 scene 对的记录（`0x0110f2d4`）。这里没有任何加入行为。

Link Trade，然后是普通交易，显示两条消息，每条等待按 A。第二条之后，`0x00fba940` 调用 `SetMode(comm, 2)`（`0x01096d10`）；`0x01095f10` 遍历状态 0、5、3、4、6，其中状态 6 调用 `StartRandomMatching`（`0x010fcff0`）并传入 scene 60001（`0x01096730`）。留在第一条消息的控制台永远不会调用 `SetMode(comm, 2)`，也永远不会匹配。

匹配层以如下条件加入一个网络（`0x006c9e70`、`0x006cb8e0`，加入 `0x006ca1c0`）：

    scene 60001，等于自身
    node count 1，低于其最大 2；network type 2；node count maximum 8 或更少
    advertise 0x04 为零：无链接码的搜索拒绝密码
    advertise 0x00，u32，大于搜索者自身
    advertise 0x00 不在本次搜索中失败的 ID 列表中（0x80 条目）

Link Code 仅改变 0x04。`bin/swsh_connect.py`（无代码）加入有码控制台并交易；`bin/swsh_host.py --code 12345678` 被有码搜索加入，绝不在无码情况下加入。较大的 ID 作为主机，因此两个搜索控制台只能单向配对；主机广告的 ID 接近 0xFFFFFFFF。

## 控制台说的第一句

Pia Local Protocol 0x24，如 BDSP 中所示（`pokeldn.ldn.local_protocol`）：版本 1，类型 0x11，0x30 固定字节，八个九字节座位，主机迁移字节。`allow_participating` 为 true，因此控制台在说 Pia 之前就把加入者记入名单：座位 0 是 `169.254.14.1:12345` 的控制台，座位 1 是 `169.254.14.2:12345` 的座位。

主机重复发送更新会话直到每个座位确认（0x21）。只有携带其序列 ID 的确认会停止重新广播（在 13 毫秒内）。头字节 0x05 和 IV 的源 ID 均为 0。

## Pia 会话对象

`[[0x02616a30]]`（也有 `[0x02630f40]`），交易代码读取站点 ID 的地方，是 Pia 的会话对象：0x270 字节，无虚表，由 `0x0183ddb0` 从 `0x006a8644` 分配一次。LDN 上的网络工厂是 `LdnNetworkFactory`，其槽 73（`0x01791080`）构建一个 0x7220 字节的 `LdnMatchmakeSession`。

| field | written by | value |
|---|---|---|
| `+0xf0` | `0x018418a0` (`0x01841918`) | 本控制台自己的站点 ID |
| `+0xf8` | `0x018418a0` (`0x01841990`) | mesh 主机索引处的站点 ID (`[[0x0262f7b0]]+0xab`)；当 `[obj+0xd4] == 4` 时跳过 |
| `+0xf8` | MeshEventListener 槽 2 (`0x01843580`)，event 1 | 后端槽 30，主机离开时 |
| `+0xf8` | event 2 | 来自 `0x017d6080` 的 ID（模式 2），或后端槽 30（仅模式 4） |
| `+0xf8`, `+0x100` | event 3 | 零，当 `[obj+0xd4] != 3` |

`0x018418a0` 在创建（`0x018394d8`）和加入（`0x0183d9b0`）时运行。模式 `+0xd4` 对于普通 LDN 创建和加入为 2；仅在 `LanMatchJointSessionJob` 和 `NexMatchJointSessionJob`（`0x01839cc0`、`0x0183a040`）中为 3 或 4，其中 4 当 `w8 - 6 < 3`（`0x0183a2b8`）。

event 1 的槽 30 存储要求离开的 ID 等于 `+0xf8` 且不同于 `+0x100`，`0x01840b90(obj)` 为真（本地 mesh 控制器的 `+0x281` 和 `+0x234`，二者均在创建时设置），`+0xd8 == 1`，`[mesh+0x64] == 0`，以及来自 `0x0184a4b0` 的映射其字非零且不同于 `obj+0x180+4*[obj+0x162]` 处的字。event 2 仅当 `[obj+0xd8] - 2` 至少为 6 且 `0x01841350` 和 `0x01769ec0([obj+0x38])` 均为假时到达主机 ID 存储。

`LdnMatchmakeSession` 槽 30（`0x017a23d0`）当 `[this+0x18]` 为空时返回 `0xff`，否则对 `[[this+0x18]+0x18]+0x2c0+8` 处的 16 字节地址调用 `0x017672d0`：全零时为 0，最后十二字节为零时为其前四字节，错误 `0x10c07` 其他情况。槽 28（`0x017a23b0`）是 `0x018407f0` 发起的调用。

`0x018407f0` 为真当 `+0xf0` 非零、等于 `+0xf8`、且后端槽 28 同意：即控制台主持 Pia mesh。主持交易的控制台在命令上爬升确认阶梯；加入 pokeldn 主机的控制台则遵循共享值（[the pump](swsh_trade.md#the-pump)）。

## 到达游戏层

以下所有层双向工作（[The Pia layer](pia.md)）：Local Protocol 0x24，站点握手 0x14，mesh 加入 0x18，RTT 0x58，可靠窗口 0x7C 和 0x80。

加入者的 0x14 连接响应必须是 Sword 发送的 840 字节形式（`host4.build_host_response`：账户 ID 在 0x11，玩家名称在 0x88，尾部在 0xB1，令牌在 0xBC）；`bin/swsh_connect.py --respond` 发送它。模拟的 Shield 1.3.2 主机在 56 字节响应后不发送任何游戏消息。零售 Sword 在 17 字节响应后完成交易（[The Pia layer](pia.md#what-a-connection-response-must-satisfy-to-be-read)）。

闲置时，控制台重复发送 `61 00 00 00 0a 00`，即 ping（约每秒四次）；0x80 每秒请求 ack id 1，0x7C 保持静默。`bin/swsh_connect.py --send-data HEX --send-protocol 0x7c` 发送应用数据（`reliable4.build_data_message`；五次静默接收检查：[version 4](pia.md#version-4)）。信号传递：0x80 ack id 离开 1，或 0x7C 确认任何。

## ping 握手

负载是四字节小端消息 ID 和一个 protobuf 主体。握手携带五条消息（`gflnet.p2p.sync.ping.pb`、`gflnet.p2p.block.pb`）：

    0x7C  61000000 0a00      97 SyncPingDataHolder, field 1 ping {}
    0x7C  61000000 1200      97, field 2 pingReply {}
    0x7C  61000000 1a00      97, field 3 pingSynced {}
    0x7C  60ea0000 0a00      60000 BlockDataHolder, field 1 result {}  (Result { bool isBlocking })
    0x80  60ea0000 12020801  60000, field 2 imReady { isReady: true }

回答遍历游戏五步：

    1  answer the ping continuously   --send-data 610000000a00 --send-mirror --send-count N
    2  ack every reliable window      0x7C, 0x18 port 1, 0x80; one unacked window kills the mesh
    3  answer `result{}` on 0x7C      the mirror is per protocol
    4  answer imReady on 0x80         --send2-data 60ea000012020801
    5  the console sends its party on 0x84

- 单个 ping 回答会引发一条 `pingReply`，游戏返回 ping。
- 在控制台请求之前发送 `pingReply` 会停止其心跳。
- 在 0x7C 上发送 `imReady` 不会引发 0x84；它在 0x80 上。
- 晚确认的消息会被重发，可能在其后续消息之后到达。只有序列高于当前最新值的消息才会替换当前消息。

`bin/swsh_connect.py --sync-answers` 回答 `trade.SYNC_ANSWERS`（在其有规则时），在其他地方按协议回显，并打印每个无规则的负载。

## 离开

剑离开一个交易会话时，发送箱子命令 3，然后大约 0.77 秒后为其角色启动 Pia 离开流程。每一步都等待回复，并在超时时落空退出。

一个已加入的剑离开主机：

| 步骤 | 剑发送的内容 | 主机应当发送的内容 | 无回答时 |
|---|---|---|---|
| 网格离开 | LEAVE_REQUEST `04 <自己的索引>`，0x18 端口 1，可靠，一次性 | LEAVE_RESPONSE `08 <主机索引>` | 5.0 秒 |
| 站点断开 | `03` 在 0x14，每 0.5 秒一次 | `04` | 8 次请求，3.6 秒 |
| LDN | 离开网络 | | |

如果两者都无回答，剑在 LEAVE_REQUEST 后 9.0 到 9.1 秒内离开 LDN 网络；如果两者都有回答，则在其后 0.14 秒内离开。版本 4 的主机处理程序 `0x017c19a0` 发送 `08` 和自己的索引通过 `0x017c2450`（两份不可靠的副本），并丢弃站点；0x14 处理程序 `0x017c6110` 向发送方回复 `04`。`pokeldn/ldn/host4.py` 回复两者。

一个主持的剑离开其客户端（它是 LDN 接入点）：

| 步骤 | 剑发送的内容 | 客户端应当发送的内容 | 无回答时 |
|---|---|---|---|
| 网格迁移 | MIGRATION_START `44 00 01`（[主机迁移](swsh_trade.md#host-migration)） | MIGRATION_FINISH 和一个 UPDATE_MESH 声明自己为主机 | 5.0 秒 |
| 本地会话 | 自己的更新会话（0x24 类型 0x11，主机迁移字节 1，新的序列号），大约每 0.11 秒一次 | 该序列号的 0x21 ack | 10.0 秒 |
| 销毁网络 | START_HOST_MIGRATION `01 13 00..`（16 字节），每 0.33 秒一次 | 离开 LDN 网络 | 10.0 秒 |

在收到 MIGRATION_FINISH、UPDATE_MESH 声明为主机、ack 和离开后，零售版剑的最后一个数据包在 MIGRATION_START 后 0.17 秒内到达；如果不回答任何内容，则会持续发送 25.0 秒。

- `LocalDestroyNetworkJob::WaitUntilAllClientsDisconnection`（`0x017acd70`）在仅剩主机时销毁网络，或在 `0x2710` 毫秒后，重新发送 START_HOST_MIGRATION 每 `0x12d` 毫秒（`0x017acbd0`、`0x017a8bb0`）。
- 一个 ack（处理程序 `0x017a9250`，本地类型 0x21）仅当其序列号等于消息的序列号时（`0x017aed10`），才会清除发送方的位。限制本地会话步骤 10.0 秒的因素尚不明确。
- START_HOST_MIGRATION 不携带序列号（`0x017abc60` 在 0xC 处写入 0），且没有任何 ack。

`bin/swsh_connect.py --answer-migration --update-mesh --leave-with-host`（在 `--preset trade` 中）完成所有三个回答。

## LAN 模式

按下选项、L、R 和左摇杆一起，开启剑的 LAN 模式；游戏显示“Mode réseau local activé”，并警告只有极巨团体战是有保障的。Pia 随后通过控制台的 IP 网络运行（[LAN 模式](pia.md#lan-mode)），Y-Comm 的连接交换搜索在其上工作。

传输选择器 `0x6a8550`（Shield 1.3.2）为模式 0 构建 Ldn 工厂（`0x6a90b0`），为模式 2 构建 Nex 工厂（`0x6a8f80`），为模式 3 构建 Lan 工厂（`0x6a9210`）。

| 在模拟的 Shield 1.3.2 上测量 | 值 |
|---|---|
| 一个连接交换搜索所主持的会话 | 游戏模式 60001，最大人数 2，版本 7 和 7，无应用程序数据，无属性 |
| 搜索开始时的浏览 | 五次请求，游戏模式 0，标志 0x2，最大参与者 4..4，结果大小 1 |
| 一个主持的剑离开其加入者 | MULTI_MIGRATION_START（0x49）在网格端口 1，然后 5.2 秒后静默 |

一个连接交换搜索的自身会话与它开始时发送的浏览不匹配。
`bin/swsh_connect.py --lan auto`（应用程序的 Trade (LAN Join)）使用 `--preset trade` 的标志浏览每个本地 /24 子网，并与一台 Switch 2 上的零售剑和模拟控制台完成了一次交易；它将控制台的静默作为其离开（`--lan-quiet`，默认 3 秒），这结束了零售运行 3.1 秒后玩家退出。`bin/swsh_host.py --lan`（应用程序的 Trade (LAN Host)）主持一个零售剑从其连接交换搜索加入并交易的会话，在 Switch 2 上通过 Wi-Fi。没有 `--our-ip` 在具有多个地址的计算机上（VPN 占用默认路由），它会等待控制台的第一个浏览并在该子网上主持。

LAN 模式下的一个连接交换搜索发送两种浏览：

| 浏览 | 构建位置 | 条件 |
|---|---|---|
| Y-Comm 附近玩家注册表 | `0x006c46a0` | 最大参与者 4..4，仅开启且空缺，结果大小 1 |
| 交易搜索的随机匹配（`Session::JoinRandomSession`，`0x0183f860`） | `0x006bb120` | 游戏模式 60001，最大参与者 2..2，仅开启且空缺，结果大小 8 |

第二个加入它所听到的第一个匹配会话，或如果没有，则主持自己的 2 人会话（[LAN 模式](pia.md#lan-mode)）。一个 2 人会话仅匹配第二个。

一个大厅的应用程序数据在 LAN 和 LDN 之间相同：0x168 游戏字节。LDN 广告是 Pia 的 0x18 字节标头后跟它们。LAN 匹配对象将它们保存在 +0x284，最多 0x168 字节（`0x006b98c0`，通过 `0x006b5bcc` 从团伙大厅设置），浏览结果通过与 LDN 扫描相同的解析器（`0x006c2360`，从 `0x006bb9c0` 用于 LAN 和 `0x006ca0b0` 用于 LDN）读取回 0x168 字节到 Y-Comm 列表中。因此，一个团伙战的记录位于广告偏移 `0xB0`，即应用程序数据 `0x98`。

| 在模拟的 Shield 1.3.2 上测量（LAN 模式） | 值 |
|---|---|
| 一个团伙主的会话（“Combat à plusieurs”） | 游戏模式 60006，最大人数 4 |
| Y-Comm 的浏览 | 游戏模式 0，标志 0x2，最大参与者 4..4，仅开启且空缺，结果大小 1；它通过应用程序数据列出团伙会话 |
| 一个极巨巢穴邀请他人且无链接码（零售剑） | 开始时一次浏览：游戏模式 50000，最大人数 4..4，标志 0x712，属性 2 = `0xfffffffe`，3 = `0x33d39298`，4 = `0x253cad29`；如果无回答，则主持游戏模式 50000，最大人数 4 |
| 加入一个列出的团伙战（“Participer”，然后“Commencer le combat”） | 一个新的浏览使用开放范围，一个明文保持连接，然后会话请求（类型 5）发送到子网广播，端口 49152 到 49155，之前没有主机请求 |

`bin/swsh_host.py --lan` 与 `--raid-boss`、`--raid-event` 或 `--lair-legendary` 一起使用，主持一个 4 人座位的会话，携带团伙的字节，并在其站点端口监听子网广播；模拟的 Shield 和一台 Switch 2 上的零售剑通过 Wi-Fi 列出它，加入并参与团伙战，控制台提供服务（[哪个站点提供服务](swsh_raid.md#which-station-serves)）。`bin/swsh_connect.py --lan` 与 `--preset raid` 或 `--preset lair` 一起使用，浏览一个 4 人座位的会话，场景 60006 或 50000；它加入了模拟 Shield 的团伙大厅和零售剑的团伙大厅，战斗开始，并加入了一个零售剑的冒险，其租借宝可梦已被选择且第一场战斗已加载。

一个浏览的属性条件是六个最多 20 个 u32 的列表，位于条件 `0x1A + 0x50 k`，计数作为 u8 位于 `0x1FA + k`，搜索标志 `0x40 << k` 开启属性 k。一个极巨巢穴搜索会跳过属性不符合其值的会话。三个值所编码的内容未知；一个控制台的两次搜索携带相同的值。LAN 主机将搜索的属性值复制到自己的游戏模式会话信息中（`pia_lan.criteria_attributes`）；然后一个零售剑加入 `bin/swsh_host.py --lan --lair-legendary`，其冒险开始。

### LAN 模式下的链接码

`SetMode(comm, mode, code)`（`0x01096d10`）将场景保存在 comm+0x70，链接码保存在 comm+0x74，为一个可选的 u32（一个存在的字节，然后是值）。`StartRandomMatching` 的参数将其携带到匹配对象 +0x278 的 +0x88（LAN 为 `0x006b83ec`）。LDN 加入（`0x006ca1c0`）和 NEX 随机加入（`0x006c6b7c`）使用 `%u` 格式化它并作为会话密码传递。LAN 匹配类（`0x006b6000`..`0x006bc000`，在 `0x006ba480` 构造）中没有代码读取 +0x278，其创建、浏览和随机加入设置不携带密码。一个带链接码的连接交换搜索在 LAN 模式下发送与无链接码的相同浏览（在零售版上测量），并加入任何匹配的会话，无论其链接码为何：LAN 主机和加入者同时服务带链接码和无链接码的搜索。

## 操作说明

- 永远不要在现场使用 `--verbose`；使用 `--capture FILE`。
- 控制台的信道在会话之间变化（已观察到 1 和 6）；扫描会保持最忙的信道（[信道](ldn.md#channels)）。
- `0x2D0`（分配在 `0x006a970c`、`0x006a9740`）是会话单例的大小（`0x006b4410`，全局 `main+0x02616758`），一个与神秘卡片无关的 720 字节结构体。

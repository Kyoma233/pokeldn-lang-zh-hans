---
title: Joining and the Pia layer
parent: Brilliant Diamond and Shining Pearl
nav_order: 1
---

# 加入与 Pia 层

本页涵盖《晶灿钻石》／《明亮珍珠》联盟房间会话，从 LDN 广告到 Pia 网格：密钥、本地协议、加入、主持和离开。地址为 1.3.0 `main`。

## 广告

    local_communication_id  0100000011d90000
    scene_id                4352 (0x1100) Union Room; 5120 (0x1400) Union Room with a password;
                            12608 (0x3140) Grand Underground
    version                 4
    accept_policy           ALL, 1/8
    application_data        17 bytes: Pia's 16-byte LDN header (ldn.md), then one byte

通信 ID 是晶灿钻石的 title id，与明亮珍珠共享（`010018e011d92000`）。该广告仅用 `prod.keys` 即可解密（`tools/ldn/ldn_scan.py`）。

头部的 CRC32 字段（+0x04）在普通房间中为 0。密码房间在此处携带密码 ASCII 数字的 CRC32，小端序（00000000 -> `0xC0088D03`），scene id 为 5120。主机在扫描时通过 scene id 过滤，跳过保护方式与自身不匹配的房间，并在 `nn::ldn::Connect` 之前将输入的密码的 CRC 与 +0x04 比较（参见 `0x16b8890`，错误 0x6c51）。没有任何消息把加入者的 CRC 发送给主机：密码错误时主机不会收到任何东西。超过八个字符的密码会保留八个给 Pia，其余部分移到 `INL1` 后面的应用数据中。`bin/bdsp_host.py --password 00000000` 主持一个密码房间；`bin/bdsp_connect.py` 无需修改即可加入。

## 口令

    WirelessStrongCryptoKey2021

直接使用原始形式，27 字节，既不填充也不哈希（LDN 接受 16 到 64 字节并带显式长度），作为 `nn::ldn::SecurityConfig` 的口令；它永远不会到达 Pia 的加密部分。

## 入座

`bin/bdsp_join.py` 扫描、关联并报告参与者表；主机分配 IP。联盟房间的八个座位就是 LDN 的 `max_participants`。一个 LDN 座位在屏幕上不显示任何内容。

- `Connect failed with status code 1` 表示关联失败；从 ESP32 板子上大约每两次尝试就会失败一次。诊断前请重试。
- 重新进入房间会打开一个新网络（新频道、SSID 和会话参数）。
- LDN 接口上的接收方必须过滤自己的源 IP：广播会回环。
- 未经认证的 Pia 会被静默丢弃，座位不会丢失。

### 随机匹配

一台主机独自在自己的联盟房间会话中，会关闭会话并重新匹配，屏幕上没有任何变化，直到它独自一人足够长时间。`INL1.IlcaNetSession$$GameState_GameFrontBefore_LocalRandom` [0x02740640] 在每次会话更新时运行，每渲染一帧一次，每秒 30 帧。只有一个站点时，它会在 `25 + (0x7F & r)` 次更新后关闭会话（0.83 到 5.07 秒，`r` 每次尝试随机），直到累计独处 270 次更新（9.0 秒），然后保留网络。这些常量来自 `IlcaNetSessionSetting` 构造函数 [0x01f46fc0]。更新链：`Sequencer$$SubscribeUpdate` 调用 [0x0202da38] -> `_orderableList` [0x01a8fed0] -> `Sequencer$$Update` [0x01a906d8..0x01a9071c] -> `NetworkManager$$OnUpdate` [0x02253190] -> `IlcaNetSession$$Update` [0x02030a38]；`targetFrameRate` 30 [0x01a8ed68]，并且唯一画质级别（`Ultra`）的 `vSyncCount` 为 2（在 60 Hz 下 30 fps）。

## 线路上的内容

在站点确认之前，主持主机每 100 ms 向其更新会话广播到 `169.254.x.255:12345`，`dst_var = 0`，176 字节：

    32ab9864 89 00000000 11bac90d 0000 00 f5a83bd383ce712d 59baa5cbc320cb56 <144 bytes>
    magic    v  dst=0    src      pid  f  nonce (a counter) tag              ciphertext

版本 9，已加密：Pia 5.31-5.43。头部和传输协议见 [Pia 层](pia.md)；`pokeldn/ldn/pia5.py` 能逐字节一致地往返处理捕获的数据包。

## 密钥层级

    cryptoKeyDataSeed  9918bd0fdcfa65779918bd0fdcfa6577    from global-metadata.dat
    game key           9900bd0cdcfa65639918bd0fc7fa6577    = seed derived with version 199
    session param      0x36dee059                          advertisement +0x0c, little-endian
    session key        7b182cb087eeabd228a2efd91a8be147    = AES-ECB(game key) over 16 SEAD bytes
    network id         b4c85cf8                            advertisement +0x00, little-endian
    source MAC         48:f1:eb:20:9b:22
    crc32(netid||MAC)  0xda291352
    IV (first packet)  da29130df5a83bd383ce712d

### 种子所在的位置

`INL1.IlcaNetSessionSetting` 的构造函数从 `global-metadata.dat` 中的字段默认 blob（`<PrivateImplementationDetails>.33F804682DF9E210AABDC4D939CBCD380EC7517F`）填充 `cryptoKeyDataSeed`；该方法见 [逆向工程一个 Switch 游戏](switch_re.md)。

### 发布的密钥是派生自种子

游戏根据本地通信版本覆盖种子的字节 1、3、7 和 12，1.3.0 版本为 199（广告中的 `app_version`）；`ldn_game_key(seed, 199)` 给出游戏密钥。

### 会话密钥

    seed  = the session parameter (LocalProtocol+0x5b0)
    state = for i in 1..4:  prev = ((prev ^ (prev >> 30)) * 0x6C078965 + i)
    rnd   = four xorshift128 draws (shifts 11, 8, 19) -> 16 bytes, little-endian
    key   = AES-128-ECB(game key).encrypt(rnd)

`pokeldn/ldn/sead.py` 实现了 SEAD 的 RNG。

### GCM nonce

由 `nn::pia::local::LdnOutputStream::vfunc3` `0x16b39c4` 构建：

    IV[0..3]  = u32be( crc32(network id LE || source MAC) )
    IV[3]     = overwritten with (packet.source_variable_id & 0xFF)
    IV[4..11] = the eight-byte header nonce

CRC 是普通 CRC32。源 MAC 来自站点记录；数据包本身不携带它。

## 本地协议，解码

更新会话（本地协议 0x24，类型 0x11），每 100 ms 重新广播，直到每个站点都确认它：

    local message header  version 1, type 0x11, size 73
    sequence id           4
    network id            8b4a3b22        random, unrelated to the advertisement's
    host variable id      11bac90d        the packet header's source variable id
    host constant id      0000 48f1 2022 9beb
    allow participating   1
    node 0..7             nine bytes each (ip, port, ranking); empty slots 0xff
    host migration state  0

主机常量 ID 以小端序读取，按 LDN 规则（`mac[2] << 56 | mac[4] << 48 | mac[5] << 40 | mac[3] << 32 | mac[1] << 24 | mac[0] << 16`）解包为主机 MAC。Pia 消息头为大端序，本地协议字段为小端序，其中的地址为大端序。

### 确认

20 字节的确认见 [Pia 层](pia.md#the-local-protocol-0x24)，以 `dst_var` 0 和目的地 0 作为广播发送。第一个确认会停止更新。

## 加入网格

握手过程见 [Pia 层](pia.md#joining-a-mesh)。BDSP 的地址：

| 内容 | 地址 |
|---|---|
| 站点协议接收分发器 | `0x0154e848`，表 `0x3e6b38f` |
| 连接请求反序列化器 | `0x0154ebd0` |
| 内部错误到结果的映射 | `0x0154f5e8` |
| 按 ID 查询协议版本 | `0x0159b850`，未注册 ID 为 0 |
| 读取网格消息的 ack ID | `0x01542db8`（`size - 4`，大端序） |
| 发送 ack（8 字节，在 0x14 上） | `0x01550324`，MeshStationProtocol 位于 `session + 0xa0` |
| 主机侧的加入 REQUEST 处理器 | `0x0154b790`、`0x0154b868` |
| 加入 RESPONSE 处理器 | `0x0154b984`、`0x0154b9a4`；指针存储在 `MeshProtocol + 0x128`（`0x0154e5c4`） |

主机注册了九个协议（[实测](#measurement-methods)）：

    0x14 Station v2   0x18 Mesh v3      0x1c SyncClock v0
    0x24 Local v0     0x58 RTT v3       0x68 Unreliable v1
    0x7c Reliable v3  0x94 Session v1   0xa4 MonitoringData v0

加入响应列出两个站点，主机索引 0，加入者索引 1，`max_active` 8。结果 7 表示变量 ID 已经是其站点之一。会话协议（0x94）在 LDN 上是惰性的：其处理器（分发器 `0x15820b8`，跳转表 `0x3e6b986`）因 session+0x70 为空而直接返回：`LdnNetworkFactory` 槽 61 [`0x16b30ac`] 不构建联合会话任务。它在 `0x157c66c` 处构建（当 GOT `0x4c4b850` 后面的 +0x38 被设置时跳过），存储在 session+0xC8，每个站点有一个 `ReliableSlidingWindow` [`0x1581938`；构造函数 `0x159dab4`；`0x159de54(window, 2, 2, 0x94000001)`；接收槽 10 `0x1581c98`]。有效的可靠 0x94 会被确认，然后丢弃。

## 主持

进入联盟房间的主机会先加入任何有空位的房间，然后才开启自己的房间。`bin/bdsp_host.py`（`pokeldn/bdsp/host.py`）主持一个 scene id 为 0x1100、`app_version` 为 199、全新网络 ID 和会话参数的房间。它发送的内容，每一条都从零售主机的字节逐一重建（`tests/test_bdsp_host.py`）：

| 步骤 | 消息 | 帧格式 |
|---|---|---|
| 站点关联 | 每 100 ms 更新会话直到确认，加入者作为节点 1 | 广播，`dst_var` 0 |
| 其连接请求 | 接受的连接响应，949 字节 | `dst_var` 0，标志 0x01 |
| 其网格加入请求 | 站点 ack，然后是加入响应 | `dst_var` 0 |
| 加入响应被确认 | `NetJoinData`，可靠序列 1 | `dst_var` 为加入者的 |
| 此后 | 每秒更新网格，RTT 请求，0x68 上的 `NetCharacterStateData{0, 0}` | `dst_var` 1 |

主机必须用请求的 tick 和以毫秒为单位的网格时钟来应答加入者的 Sync Clock（0x1C）请求。未收到应答的加入者大约十秒后解除认证并重新关联，此时屏幕显示“communication en cours”。一旦应答，房间是对称的，[交换](bdsp_trade.md) 保持不变。

## 离开

两种离开都在网格可靠窗口（0x18 端口 1，序列 1）上开始，并等待在端口 0 上以不可靠方式发送的应答，零售版 Pia 会发送两次。网格分发器 `0x0154ac94`。

| 主机 | 发送 | 应收到 |
|---|---|---|
| 加入者 | `04 <自身索引>`，然后在 0x14 上发送站点断开 `03` | `08 <主机索引>`，然后是 `04` |
| 主机 | 向每个站点发送 `44 <主机索引> <新主机索引>` | 从每个站点收到 `48 <站点索引>` |

收到应答后，加入者在 0.2 秒内解除认证，主机会在 0.5 秒内关闭网络。未收到应答时，加入者会重试约 5 秒，约 9 秒后离开；主机会运行迁移约 25 秒，最后以每 0.3 秒发送本地协议 0x13，最多持续 10 秒（`LocalDestroyNetworkJob::WaitUntilAllClientsDisconnection` `0x016b95b8`），此时有站点离开会立即结束。其步骤：301 ms 后重发（`job+0x68`）；向 `WaitForCancel` `0x016b9330` 发送取消字节；一个站点已离开（计数 `0x016b014c`，测试 `0x016b9614`）或自 `WaitUntilAllClientsReceiveUpdateSessionMessage` `0x016b936c` 起过去 10000 ms（`job+0x70`，测试 `0x016b9644`）到 `StartDestroyNetwork` `0x016b950c`；前一个状态在 `[[protocol+0x4f0]+0x5c]`（`0x016b0888`）或 10001 ms 后结束。离开处理器：主机的离开请求 `0x0154b9e0`（通过 `0x0154c860` 应答）、加入者的响应 `0x0154baf8`、迁移响应 `0x0154b068`；`WaitLeaveResponse` `0x0155fd2c`、`WaitMigrationResponse` `0x015607bc`。

`pokeldn.bdsp.session.answer_departure` 构建两种应答；`bin/bdsp_host.py` 应答离开的加入者，`bin/bdsp_connect.py` 应答迁移开始并在 0x13 上离开网络（`--no-leave-on-host-migration` 会保持）。离开交换箱时不会发送任何离开消息，只在一个数据包中发送 `NetDataCurrentFlowCancelData{0}`（0x25）和 `NetCharacterStateData{0}`。

## 测量方法

- 主机只有在协议数量与自身匹配时才应答连接请求；遍历数量可得到 9。未注册的协议期望版本为 0，因此二分版本即可读取任何协议的版本。
- 信号必须是回复；沉默往往同样可能是丢包。可靠窗口会确认它接受的数据，因此发送数据并只遍历序列 ID。

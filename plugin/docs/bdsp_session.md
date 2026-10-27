---
title: Joining and the Pia layer
parent: Brilliant Diamond and Shining Pearl
nav_order: 1
---

# 加入 BDSP 会话及其加密下的内容

本页涵盖了《宝可梦 辉晶壁／闪晶壁》联盟房间会话，从 LDN 广告到 Pia 网格：密钥、本地协议、加入、主持和离开。地址基于 1.3.0 `main`。

## 广告

    local_communication_id  0100000011d90000
    scene_id                4352 (0x1100) Union Room; 5120 (0x1400) Union Room with a password;
                            12608 (0x3140) Grand Underground
    version                 4
    accept_policy           ALL, 1/8
    application_data        17 bytes: Pia's 16-byte LDN header (ldn.md), then one byte

通信 ID 是辉晶壁的标题 ID，同时也是闪晶壁（`010018e011d92000`）共享的。广告仅用 `prod.keys` 解密（`tools/ldn/ldn_scan.py`）。

标头的 CRC32 字段（+0x04）在普通房间中为 0。密码房在该字段中存放密码 ASCII 数字的 CRC32，小端序（00000000 -> `0xC0088D03`），场景 ID 为 5120。控制台在扫描时按场景 ID 过滤，跳过保护方式不匹配自己的房间，并在 `nn::ldn::Connect` 之前将其输入密码的 CRC 与 +0x04 比较（检查 `0x16b8890`，错误码 0x6c51）。没有任何消息将加入者的 CRC 传给主机：密码错误时主机收不到任何内容。超过八个字符的密码，Pia 仅保留八个，余下的移入 `INL1` 之后的应用数据。`bin/bdsp_host.py --password 00000000` 主持一个密码房间；`bin/bdsp_connect.py` 原样加入。

## 密码

    WirelessStrongCryptoKey2021

原样使用，27 字节，不填充也不哈希（LDN 接受 16 到 64 字节的显式长度），作为 `nn::ldn::SecurityConfig` 的密码；它永远不会到达 Pia 的加密层。

## 加入会话

`bin/bdsp_join.py` 扫描、关联并报告参与者表；控制台分配 IP。联盟房间的八个座位即为 LDN 的 `max_participants`。LDN 座位在屏幕上不显示任何内容。

- `Connect failed with status code 1` 是一次失败的关联；从 ESP32 板子来看，大约有一半尝试失败。请在诊断前重试。
- 重新进入房间会开启一个新网络（新信道、SSID 和会话参数）。
- 在 LDN 接口上运行的接收器必须过滤自己的源 IP：广播会回环。
- 未经认证的 Pia 会被静默丢弃，不会丢失座位。

### 随机匹配

一个孤身一人的控制台会关闭自己的联盟房间会话并重新匹配，屏幕上没有任何变化，直到它独自呆够足够长的时间。`INL1.IlcaNetSession$$GameState_GameFrontBefore_LocalRandom` [0x02740640] 在每个会话更新时运行，即每秒渲染 30 帧。单机时，关闭会话需等待 `25 + (0x7F & r)` 次更新（0.83 至 5.07 秒，每次尝试 `r` 随机），直到累计 270 次独自更新（9.0 秒），然后保留其网络。这些常量来自 `IlcaNetSessionSetting` 构造函数 [0x01f46fc0]。更新链：`Sequencer$$SubscribeUpdate` 调用 [0x0202da38] -> `_orderableList` [0x01a8fed0] -> `Sequencer$$Update` [0x01a906d8..0x01a9071c] -> `NetworkManager$$OnUpdate` [0x02253190] -> `IlcaNetSession$$Update` [0x02030a38]；`targetFrameRate` 30 [0x01a8ed68]，唯一的质量等级（Ultra）有 `vSyncCount` 2（在 60 Hz 下为 30 帧）。

## 网络上的内容

在一台主机收到确认之前，它会每 100 毫秒向 `169.254.x.255:12345` 广播一次更新会话，`dst_var = 0`，176 字节：

    32ab9864 89 00000000 11bac90d 0000 00 f5a83bd383ce712d 59baa5cbc320cb56 <144 bytes>
    magic    v  dst=0    src      pid  f  nonce (a counter) tag              ciphertext

版本 9，已加密：Pia 5.31-5.43。标头和传输协议详见 [The Pia layer](pia.md)；`pokeldn/ldn/pia5.py` 可以原样往返传输捕获的数据包。

## 密钥层次结构

    cryptoKeyDataSeed  9918bd0fdcfa65779918bd0fdcfa6577    from global-metadata.dat
    game key           9900bd0cdcfa65639918bd0fc7fa6577    = seed derived with version 199
    session param      0x36dee059                          advertisement +0x0c, little-endian
    session key        7b182cb087eeabd228a2efd91a8be147    = AES-ECB(game key) over 16 SEAD bytes
    network id         b4c85cf8                            advertisement +0x00, little-endian
    source MAC         48:f1:eb:20:9b:22
    crc32(netid||MAC)  0xda291352
    IV (first packet)  da29130df5a83bd383ce712d

### 种子的存储位置

`INL1.IlcaNetSessionSetting` 的构造函数从 `global-metadata.dat` 中的一个字段默认 blob 填充 `cryptoKeyDataSeed`（`<PrivateImplementationDetails>.33F804682DF9E210AABDC4D939CBCD380EC7517F`）；该方法详见 [Reverse-engineering a Switch title](switch_re.md)。

### 公开的密钥是从种子派生的

游戏用本地通信版本覆盖种子的第 1、3、7 和 12 字节，1.3.0 版本为 199（广告的 `app_version`）；`ldn_game_key(seed, 199)` 得到游戏密钥。

### 会话密钥

    seed  = the session parameter (LocalProtocol+0x5b0)
    state = for i in 1..4:  prev = ((prev ^ (prev >> 30)) * 0x6C078965 + i)
    rnd   = four xorshift128 draws (shifts 11, 8, 19) -> 16 bytes, little-endian
    key   = AES-128-ECB(game key).encrypt(rnd)

`pokeldn/ldn/sead.py` 实现了 SEAD 的 RNG。

### GCM Nonce

由 `nn::pia::local::LdnOutputStream::vfunc3` `0x16b39c4` 构建：

    IV[0..3]  = u32be( crc32(network id LE || source MAC) )
    IV[3]     = overwritten with (packet.source_variable_id & 0xFF)
    IV[4..11] = the eight-byte header nonce

CRC 是普通的 CRC32。源 MAC 来自站点记录，数据包本身不携带。

## 本地协议解析

更新会话（本地协议 0x24，类型 0x11），每 100 毫秒广播一次，直到每个站点确认为止：

    local message header  version 1, type 0x11, size 73
    sequence id           4
    network id            8b4a3b22        random, unrelated to the advertisement's
    host variable id      11bac90d        the packet header's source variable id
    host constant id      0000 48f1 2022 9beb
    allow participating   1
    node 0..7             nine bytes each (ip, port, ranking); empty slots 0xff
    host migration state  0

主机常量 ID 按小端序读取，按 LDN 规则（`mac[2] << 56 | mac[4] << 48 | mac[5] << 40 | mac[3] << 32 | mac[1] << 24 | mac[0] << 16`）解包为主机 MAC。Pia 消息标头是大端序，本地协议的字段是小端序，字段内部的地址是大端序。

### 确认

20 字节的确认在 [The Pia layer](pia.md#the-local-protocol-0x24) 中，作为广播发送，`dst_var` 为 0，目标为 0。第一个确认会停止更新。

## 加入网格

握手详见 [The Pia layer](pia.md#joining-a-mesh)。BDSP 的地址：

| 内容 | 位置 |
|---|---|
| 站点协议接收分发 | `0x0154e848`，表 `0x3e6b38f` |
| 连接请求反序列化 | `0x0154ebd0` |
| 内部错误结果映射 | `0x0154f5e8` |
| 按 ID 查找协议版本 | `0x0159b850`，未注册 ID 返回 0 |
| 读取网格消息的确认 ID | `0x01542db8`（`size - 4`，大端序） |
| 发送确认（8 字节，在 0x14） | `0x01550324`，`MeshStationProtocol` 位于 `session + 0xa0` |
| 加入 REQUEST 处理（主机侧） | `0x0154b790`, `0x0154b868` |
| 加入 RESPONSE 处理 | `0x0154b984`, `0x0154b9a4`；指针存储在 `MeshProtocol + 0x128`（`0x0154e5c4`） |

控制台注册九种协议（[测量方法](#measurement-methods)）：

    0x14 Station v2   0x18 Mesh v3      0x1c SyncClock v0
    0x24 Local v0     0x58 RTT v3       0x68 Unreliable v1
    0x7c Reliable v3  0x94 Session v1   0xa4 MonitoringData v0

加入响应列出两个站点，主机索引 0，加入者索引 1，`max_active` 8。结果 7 表示变量 ID 已是其站点之一。会话协议（0x94）在 LDN 上是空操作：其处理程序（分发 `0x15820b8`，跳转表 `0x3e6b986`）返回是因为 session+0x70 为 null：`LdnNetworkFactory` 槽 61 [`0x16b30ac`] 不构建联合会话任务。它在 `0x157c66c` 处构建（当 GOT `0x4c4b850` 后的 +0x38 被设置时跳过），存储在 session+0xC8，每个站点有一个 `ReliableSlidingWindow` [`0x1581938`；构造函数 `0x159dab4`；`0x159de54(window, 2, 2, 0x94000001)`；接收槽 10 `0x1581c98`]。有效的可靠 0x94 会被确认，然后丢弃。

## 主持

进入联盟房间的控制台会在开启自己的房间之前加入任何有空位的房间。`bin/bdsp_host.py`（`pokeldn/bdsp/host.py`）主持一个场景 ID 为 0x1100、`app_version` 199、全新的网络 ID 和会话参数的房间。它发送的内容，每个都从零售主机的捕获中逐字节重建（`tests/test_bdsp_host.py`）：

| 步骤 | 消息 | 框架 |
|---|---|---|
| 站点关联 | 每 100 毫秒发送一次更新会话，直到收到确认，加入者作为节点 1 | 广播，`dst_var` 0 |
| 其连接请求 | 一个被接受的连接响应，949 字节 | `dst_var` 0，标志 0x01 |
| 其网格加入请求 | 站点确认，然后加入响应 | `dst_var` 0 |
| 加入响应被确认 | `NetJoinData`，可靠序列 1 | `dst_var` 为加入者的 |
| 从此之后 | 每秒更新网格，RTT 请求，`NetCharacterStateData{0, 0}` 在 0x68 | `dst_var` 1 |

主机必须用请求的 tick 和网格毫秒时间响应加入者的同步时钟（0x1C）请求。未得到响应的加入者大约在 10 秒后去认证并重新关联，同时屏幕显示“communication en cours”。一旦得到响应，房间变为对称的，[交易](bdsp_trade.md) 即可原样运行。

## 离开

双方的离开都在网格可靠窗口（0x18 端口 1，序列 1）上进行，并等待通过不可靠方式在端口 0 上发送的响应，零售 Pia 发送两次。网格分发 `0x0154ac94`。

| 控制台 | 发送 | 应收 |
|---|---|---|
| 加入者 | `04 <own index>`，然后在 0x14 上的站点断开 `03` | `08 <host index>`，然后 `04` |
| 主机 | `44 <host index> <new host index>` 至每个站点 | `48 <station index>` 来自每个站点 |

得到响应后，加入者在 0.2 秒内去认证，主机在 0.5 秒内关闭其网络。未收到响应时，加入者重试约 5 秒后离开；主机运行其迁移约 25 秒，结束时每 0.3 秒发送一次本地协议 0x13，持续最多 10 秒（`LocalDestroyNetworkJob::WaitUntilAllClientsDisconnection` `0x016b95b8`），这会立即结束一个正在离开的站点。其步骤：301 毫秒后重发（`job+0x68`）；取消字节发送至 `WaitForCancel` `0x016b9330`；仅剩一个站点（计数 `0x016b014c`，测试 `0x016b9614`）或自 `WaitUntilAllClientsReceiveUpdateSessionMessage` `0x016b936c`（`job+0x70`，测试 `0x016b9644`）起 10000 毫秒后，进入 `StartDestroyNetwork` `0x016b950c`；之前的状态在 `[[protocol+0x4f0]+0x5c]`（`0x016b0888`）或 10001 毫秒后结束。离开处理程序：主机的离开请求 `0x0154b9e0`（通过 `0x0154c860` 回答），加入者的响应 `0x0154baf8`，迁移响应 `0x0154b068`；`WaitLeaveResponse` `0x0155fd2c`，`WaitMigrationResponse` `0x015607bc`。

`pokeldn.bdsp.session.answer_departure` 构建两个应答；`bin/bdsp_host.py` 回答一个正在离开的加入者，`bin/bdsp_connect.py` 回答迁移开始并在收到 0x13 时离开网络（`--no-leave-on-host-migration` 保持）。离开交易框时不发送离开消息，仅发送 `NetDataCurrentFlowCancelData{0}`（0x25）和 `NetCharacterStateData{0}` 在一个数据包中。

## LAN 模式

BDSP 1.3.0 从不设置 LAN 模式。它的 Pia 通过 Nintendo 的 Unity 插件传入，其框架初始化（约 `0x16886d0`）为 LAN 模式构建 Lan 工厂（构造函数 `0x169fdcc`），需要注册的 LAN 设置。`INL1.IlcaNetBase.PlatformInitialize` 注册互联网设置（`0x1e13800`），`PlatformInitialize2` 注册本地设置（`0x1e139dc`）；没有任何调用 `PiaPlugin.RegisterInitializeLanSetting`（`0x227caf0`）或其本地版本 `0x227cac0`。`global-metadata.dat` 中没有任何 C# 名称提及 LAN。

## 测量方法

- 主机仅在协议计数与自身匹配时响应连接请求；扫描计数得到 9。未注册的协议期望版本为 0，因此二分版本号可读取任意协议。
- 信号必须为回复；静默通常意味着丢包。可靠窗口会确认其接受的数据，因此发送数据并仅扫描序列号。

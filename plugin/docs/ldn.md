---
title: The wireless layer
nav_order: 2
has_children: true
---

# 无线层

**LDN** 是 Switch 的本地无线；任天堂的点对点中间件 [Pia](pia.md) 运行在它之上。

## 两个秘密

LDN 口令（16-64 字节，原样使用）用于验证 802.11 关联。16 字节的 Pia 游戏密钥为每个数据报派生会话密钥。

| 标题 | LDN 口令 | Pia 游戏密钥 |
|---|---|---|
| 晶灿钻石／明亮珍珠 | `WirelessStrongCryptoKey2021`（27 字节） | 来自 `cryptoKeyDataSeed`（[BDSP](bdsp_session.md)） |
| 剑／盾、朱／紫、传说 阿尔宙斯 | `W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL`（64 字节） | `p1frXqxmeCZWFv0X` |

## 发现

`tools/ldn/ldn_scan.py` 仅凭 `prod.keys` 就能读取任何通告。一个游戏只能看到自己 LDN 协议的通告，因此主机要复制该协议（`HostTransport(protocol=...)`）。

| 标题 | 协议 | 通告格式 |
|---|---|---|
| GBA 应用，通信 ID `0x01006fa0233f8000` | 3（AES-GCM，`master_key_12`） | 3 |
| 剑 神秘礼物界面，`0x0100abf008968000` | 1（AES-CTR，`master_key_00`） | 2 |
| 传说 阿尔宙斯 本地交换，`0x01001f5010dfa000` | 1 | 4 |

信标以 11 Mbit/s DSSS 发出，通告 action 帧以 HT MCS 3（OFDM）发出；仅支持 DSSS 的接收器会错过通告。

## 通告中的应用数据

Pia 5（明亮珍珠）：

    +0x00  4  network id                     每会话随机
    +0x04  4  用户密码的 CRC32               无密码时为 0
    +0x08  1  系统通信版本
    +0x09  1  头部大小                       16
    +0x0c  4  会话参数                       为 Pia 会话密钥提供种子
    +0x10     应用数据

一次捕获只能用其自身会话的通告来解密。

Pia 6.16 到 6.41 从 SSID 派生会话密钥和网络 ID：

    +0x00  2  系统属性数据大小               0x5C
    +0x02  1  系统通信版本                   6.16-6.30 为 21，6.39-6.41 为 22
    +0x03  2  应用通信版本
    +0x05  16 用户密码                       以 0xFE 填充，在游戏密钥下进行 AES-128-GCM，丢弃标签
    +0x15  1  是否启用玩家限制
    +0x16  1  玩家数量
    +0x17  4  玩家名长度
    +0x1b  1  玩家名编码                     1 = UTF-8，2 = UTF-16
    +0x1c  64 玩家名
    +0x5c     应用数据

密码的 IV 是 `key[1] key[8] key[7] key[2]`（阿尔宙斯 1.1.1 `0x6fac70`，[设置器](pla.md#the-link-code-in-the-advertisement)）；仅凭游戏密钥即可读取。

## 为模拟器提供主机

ldn_mitm 模式下的模拟器通过 11452 端口关联，并在局域网上运行 Pia，无需无线电，也无需 `prod.keys`。`pokeldn/ldn/ldn_mitm.py` 加入；`ldn_mitm_host.py` 通过 `IpHostTransport` 提供主机（`NEEDS_RADIO = False`）。

    UDP  主机 -> 模拟器:11452   Scan          仅头部
    UDP  模拟器 -> 主机         ScanResp      NetworkInfo，0x480
    TCP  模拟器 -> 主机:11452   Connect       NodeInfo，0x40
    TCP  主机 -> 模拟器         SyncNetwork   带模拟器就座的 NetworkInfo，保持打开

`nn::ldn::NetworkInfo`，0x480 字节：

    +0x000  NetworkId          IntentId 0x10（u64 localCommunicationId，u16，u16 sceneId，u32）接着 SessionId 0x10
    +0x020  CommonNetworkInfo  MAC 6，Ssid 0x22（长度字节后跟 0x21），s16 channel，u8 linkLevel，u8 networkType，u32
    +0x050  LdnNetworkInfo     SecurityParameter 0x10，u16 securityMode，u8 acceptPolicy，...
    +0x066                     u8 nodeCountMax，u8 nodeCount
    +0x068                     NodeInfo[8]，每个 0x40：u32 IPv4 LE，MAC 6，u8 nodeId，
                               u8 isConnected，0x0C 处 0x20 名称，0x2E 处 u16 localCommunicationVersion
    +0x26A                     u16 advertiseDataSize，随后 0x180 字节通告数据
    +0x478                     u64 authenticationId

节点 0 的地址必须是可达的局域网地址：主机向那里发送 Pia。节点的 MAC 从其地址派生（172.16.86.1 对应 `02:00:ac:10:56:01`）。游戏的节点在 +0x2E 处携带 88。火红的扫描过滤仅比较 `localCommunicationId` 和 `networkType`。

16 字节的会话 ID 是 `NetworkId.SessionId`、十六进制 `Ssid` 文本以及 Pia 会话密钥的明文 `AES(game_key).encrypt(ssid)`；网络 ID 是 `crc32(ssid[1:16])` [`pokeldn/ldn/crypto.py`:114]。陷阱：不匹配时会关联成功，之后主机静默丢弃所有数据报。

## 工作站的广播

加入的主机发送不带 DS 位的广播和组播（CCMP 组密钥，密钥 ID 1），以及到 DS 的单播（成对密钥，密钥 ID 0）。火红以对主机的 ARP 开场；不回应它的主机会被以原因 3 取消认证。标准接入点会丢弃这些帧；[ESP32](hardware_esp32.md) 会原样转发。

## 信道

LDN 还允许 5 GHz 信道 36-48，ESP32 无法到达这些信道；火红／叶绿仅使用 2.4 GHz。板子也能听到相邻信道上的主机；在那里加入会在主机的下一次通告时被丢弃，因此扫描报告最繁忙的信道：

    POKELDN_RADIO=esp32:auto ./.venv/bin/python tools/ldn/ldn_scan.py --keys PROD_KEYS --dwell 2.5

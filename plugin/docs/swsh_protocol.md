---
title: The sync framework
parent: Sword and Shield
nav_order: 2
---

# 同步框架

Pia 之上的发布／订阅框架。一条消息由小端 u16 id、一个鉴别字节、一个零字节和一个 protobuf 正文组成。

## 消息 id 的来源

低 id 来自 `0x01BBFFA0` 处 838 条 24 字节记录组成的表，格式为 `{u64 handler slot, u32 0x402, u32 id, u64 0}`，id 范围 1..880。高 id 为基础值加偏移量。

## 内容与持有者

每个内容注册三个持有者（注册器 `0x010ccd90` 对应内容 30、`0x010da7d0` 对应 40、`0x010d5150` 对应 50），将基础值加到其偏移量 `ldrh [content+0x372]` 上，并把每个传给 `0x006daeb0(manager, &holder, flag)`：

| id | holder | flag |
|---|---|---|
| 10000 + offset | `0x010dd910` | 1 |
| 20000 + offset | `0x010d85f0` | 0 |
| 30000 + offset | `0x010d0980` | 0 |

40000 族在更下一层被铸造（`ldrb w20,[x0,#0x28]`、`add w24,w20,#-0x63c0`、`strh w24,[x20,#0x160]`）：40030 / 40040 / 40050。

没有监听器的持有者会静默丢弃（`0x010d81d0`）。没有任何内容会到达内容 40 或 50 的 20000 基础持有者：20040 和 20050 是惰性的。

### 30000 持有者

30000+offset 持有者（`0x010d0980`，vtable GOT `0x02618620` = `0x02528100`，无 RTTI）携带 `gflnet.p2p.framework.pb.SequenceDataHolder`：

    SequenceDataHolder    oneof message {
                            1 CancelAccepted        cancelAccepted
                            2 RequestCancel         requestCancel
                            3 RequestCancelAll      requestCancelAll
                            4 RequestForcedProceed  requestForcedProceed }
    CancelAccepted        { 1 int32 currentSeqNo; 2 bool  isForced    }
    RequestCancel         { 1 int32 currentSeqNo }
    RequestCancelAll      { 1 int32 currentSeqNo }
    RequestForcedProceed  { 1 int32 currentSeqNo; 2 int32 targetSeqNo }

解析器 `0x006a7580`；接收（槽 8 `0x008b9590`）调用 `[holder+0x168]` 的监听器槽（case - 1）。《盾》1.3.2 只构建 CancelAccepted（`0x006a3db0`，从发送包装器 `0x008b7420` 以及十个同步内容中每个内容的两个回复作业调用）。零售版交换从不携带 case 2 到 4；主机仍会处理它们（[内容 40](swsh_trade.md#the-cancel-and-proceed-messages)）。

内容 40 的实例 30040，端口 0：

    RequestForcedProceed{c, c+1}   58750000 2204 08<c> 10<c+1>     c=0: 58750000 2204 0800 1001

### 三个连接交换内容

`0x010c9280` 构建会话：内容 30（盒子交换）在 `+0x120`，内容 40（SyncSaveDataHolder）在 `+0x148`，内容 50（PokemonTradeDataHolder）在 `+0x2b0`；自己的宝可梦 `+0x68`，对方的 `+0x70`；交换状态（1..10）`+0x140`，错误码 `+0x144`；`+0x418` 在第一帧发送命令 3，`+0x419` 是抑制其发送的角色位。内容 50 以状态 1 初始化，内容 40 以状态 6 初始化。

## 路由路径

    0x006a9a20   the sync pump, from the trade session update
    0x006db3b0   the poll: per registered entry, drain both streams of its kind (byte +8)
    0x006a8490   stream A: mesh port [pia+0xd0+kind*4], Pia protocol 0x7C
    0x006a84f0   stream B: mesh port [pia+0xd8+kind*4], Pia protocol 0x80
    0x006db9c0   drain: slot 0x78 fills (sender*, length) and the buffer at manager+0xf0
    0x006db620   dispatch: match the entry, call the holder's slot 8
    0x010d81d0   content 50's 10000-base holder: parse, call the listener's slot 0
    0x010d5e40   the listener: sender to station index, memcpy 0x158, invoke

### 应用头

有效载荷是 `struct.pack("<HBB", id, discriminator, 0)` 后接正文，由 `0x006db840` 构建并由 `0x006db620` 解析。鉴别字节是一个世代计数器（`[content+0x370]`，+1 模 255，`0x008b6670`），被压入 `[manager+0x480f0]`；强制的 CancelAccepted 会在内容 40 上推进它（`0x006db470`），注册器会将其归零（`0x010d53a0`）。没有强制 CancelAccepted 的交换全程携带零。

### 实时读取注册项

    manager = read_u64(read_u64(main + 0x02616750))     0x006a9a70, the poll's caller
    count   = read_u64(manager + 0xD8)                  0x006db3dc
    array   = read_u64(manager + 0xD0)                  0x006db3e0
    entry i = array + i * 0x10                          0x006db3e4
    id      = holder's vtable slot 7, called at 0x006db740 (`ldr x8, [x8, #0x38]`)

槽 7 返回 `[holder+0x160]`。空闲画面上列表为空；已入座的连接交换会增加两个条目；神秘礼物不会增加任何条目。

### 分派门控、端口与发送方

一个条目为 16 字节：持有者、+8 处为 kind、+9 处为标志（仅 10000+offset 为 1）：

    id == holder->slot7()
    entry[8] == the drain's kind
    entry[9] ? header[2] == [manager+0x480f0] : no check

kind 是网格端口：内容持有者（20030、10050、ping）为 0，40000 族为 1（`0x006daf40(manager, &holder, 1, 0)`）。发送方是由 `0x006b5850` 解析出的传输指针（`mesh->GetStationIndex`，失败时为 0xfd）；环回传递 `[[0x2616a30]]+0xf0`。`Data.ownerId` 在 10050 上不起作用。

## `Data` 封套

`gflnet.p2p.sync.pb`、`data.proto`：

    1  uint32  syncId        the content offset       30 / 40 / 50
    2  uint32  elementId     the base                 10000 / 20000
    3  uint64  ownerId       the sender
    4  uint64  clock
    5  bytes   body          four bytes in a pair; a 344-byte PK8 in a 40050

40000 持有者的监听器是 `element+0x18`；其槽 0 `0x006d59f0` 路由：

    [Data+0x14] == [listener+0x10]        syncId, the element's offset
    walk [listener+0x28] .. [+0x30]       sub-elements, 0x90 bytes each
      [Data+0x18] == [sub+0x62]           elementId, u16
      [Data+0x20] == [sub+0x68]           ownerId, u64
    sub->vtable at 0x48 (sub, body, len, [Data+0x28])     body and clock
    otherwise: ret                        dropped silently

### 子元素种类

| 种类 | 构造函数 | vtable | 出生时 `+0x88` | 槽 9，接收：大小检查，存储到 `+0x88` |
|---|---|---|---|---|
| 32 位 | `0x006d5c00` | `0x2512bc8` | 0 | `0x006d5f20`：4 字节 |
| 配对（阶段） | `0x006d6160` | `0x2512c90` | `0xfc18fc18` | `0x006d6490`：4 字节 |
| 16 位 | `0x006d66d0` | `0x2512d58` | 0 | `0x006d69f0`：2 字节 |

一次接收随后设置 `[sub+0x78] = clock`，并执行 `strh 0x0100 -> [sub+0x60]`（就绪字节 `+0x61`）；槽 7（哈希值）返回时钟。构造函数接收元素 `x0`（`+0x80`）、elementId `w1`（`+0x62`）、ownerId `x2`（`+0x68`）、标志 `w3`（`+0x70`）。

同步元素（`0x006d3f80`）按同步内容构建一次（内容 30 在 `0x010ce604`，50 在 `0x010d6904`，40 在 `0x010dc264`）。vtable 来自 `0x2512b28`：

| 偏移量 | vtable | 角色 |
|---|---|---|
| `+0x00` | `0x2512b38` | 主接口，6 个槽；2、3、4 是 w3 = 1 的三个构造函数 |
| `+0x08` | `0x2512b78` | 接口 A：32 位种类 |
| `+0x10` | `0x2512b90` | 接口 B：配对、16 位种类 |
| `+0x18` | `0x2512bb0` | 路由监听器，槽 0 = `0x006d59f0` |

铸造器 `0x006d44e0` 构建四个通道：`+0xd0` 为每个站点保存一个 32 位子元素，elementId 为 10000（quorum 哈希）；`+0xf0` 在 `+0x38` 保存一个 16 位子元素，elementId 为 20000，所有者为 0（[共享值](swsh_trade.md#the-phase-is-the-elements-field)），并为每个站点保存一个 elementId 为 20000 的配对；`+0x110` 是 quorum 哈希遍历的列表。

### quorum 哈希

elementId 10000 上的四个字节由 `0x006d7b40` 在 `element+0xa8` 构建：

    h = 0
    for sub in subs:
        if (!sub[+0x61]) { h = 0; break }        any station not ready -> zero
        h = crc32(le32(h + sub->slot7()))        slot 7 is the clock

非零意味着每个站点都已就绪。`0x0065de30` 是 `zlib.crc32`；`0x0065df04`（多项式 `0x8005`）是 CRC-16。被遍历的列表 `element+0x110` 是 `0x006d48b0` 对 `+0x40` 的拷贝，只保留 `+0x68` 为零的条目。

该链覆盖发送方的 elementId 0 和 1（无所有者），然后是发送方自身的 elementId 20000。作为主机的《剑》的非零哈希匹配，例如内容 50：

    elementId 0, no owner      clock 2304   the host's own Pokemon (344 bytes)
    elementId 1, no owner      clock 2313   the partner's Pokemon, sent back
    elementId 20000, host      clock 2278   then 2338 after its pair moved
    crc32 chain                8ffa0f2e     then b3615e90

加入方如果回显主机的哈希，就能完成与作为主机的《剑》的交换。

## 0x84 协议上的队伍负载

`ReliableBroadcastProtocol` 以三个分片携带 3456 字节交换快照，直到被确认；
第三个分片为 zlib（Pia 标志 0x10）：原始 1404 + 1404 + 157，最后一片解压后为 648。
`trade_payload.py` 会拒绝任何其他总长度。布局（同 `kwsch/PokePiaSWSH`、
`lincoln-lm/swsh-lan-client`）：

    0x000  six PK8 records, party form, 0x158 each          -> 0x810
    0x810  u32   party count
    0x814  MyStatus, 272 bytes      TID/SID at 0xA0, trainer name at 0xB0
    0x924  TrainerCard, 456 bytes   trainer name at 0x00, save start date at 0x170
    0xAEC  the player profile, 266 bytes                     -> 0xBF6
    0xBF6  392 bytes, the Battle Stadium block; zero for Link Trade
    0xD7E  2 bytes of padding                                -> 0xD80 = 3456

MyStatus 和 TrainerCard 是 PKHeX 的存档块（`Saves/Substructures/Gen8/SWSH/`）。构建者为
`0x0110c180`，接收者为 `0x0110cff0`。连接交换（`0x010967f0`）和密码匹配
（`0x00bd80f4`）不传递对战竞技场块；对战竞技场（`0x00b2d7d0`）会传递一个。

### 对战竞技场块

0x180 字节数据，后跟一个 u64 长度；读取器 `0x00b2d9fc` 要求长度为 0x118。生产者
`0x00b2eb60`。从 0xBF6 开始：

    0x000  u32    CRC-16 (0x8005) of the 0x22fc-byte regulation core (0x008ff9e0;
                  regulation_preset_core_%d.bin)
    0x004  0x100  the team's signature: +0x36 of the 0x136-byte team descriptor at match+0x98
    0x104  4      zero
    0x108  u64    the manager's optional (value +0x1ab8, flag +0x1ab0), zero unless match type 3
    0x110  u8     the manager's byte +0x191c when 0x00adb920 yields an object and 0x00b1ce10(0) == 2
    0x111  u32, u16, u8   team descriptor +0, +4, +6
    0x118  0x68   zero
    0x180  u64    length, 0x118

接收器 `0x00b2e590` 将对方的 CRC 与自己的（`0x00b2e760`）比较；双方都持有时结果为 9，否则为 10。

队伍描述符位于 match+0x70 处可选项的 match+0x98，仅由对战竞技场匹配更新 `0x00ad5750` 中的
`0x00ad9cf0` 写入。队伍下载任务（`0x014f7fd0`）填充它：
`+0x00..+0x2f` 从结果持有者的 `+0x38` 取六个 u64，`+0x30..+0x35` 从 `+0x68` 取六个字节，
`+0x36..+0x135` 从 `+0x6e` 取，然后被 `v1/validate` 签名覆盖。持有者从队伍列表
（`0x0150320c`）中取得键与所选键匹配的 0x158 字节条目：

| key | entry |
|---|---|
| (1, team) | 一个存档对战队伍：六个 u64 `box \| slot << 32`，来自 `save+0x525 + team*12 + i*2`；名字在 `save+0x4a0 + team*0x16` |
| (2, i) | 一条存储记录：0x87f 字节记录（`0x01430670`）的字节 0x26..0x15b |

签名为 RSA-2048、PKCS#1 v1.5、SHA-256，由 `0x011aedf0(team, v, sig)` 验证；该函数是
`nn::crypto::detail::BigNum::ModExp` 的唯一调用者（PLT `0x018fff50`）。被签名的消息是
队伍存储的 0x148 字节 PK8、密钥版本 `v` 作为大端 u16，然后是 `00 01`。主机只持有
公钥；镜像名称为 `https://v3-lp1.vp.n.srv.nintendo.net/v1/public_key` 和
`.../v1/validate`，因此大概由任天堂服务器签名。连接交换永远不会到达该检查。

`v1/validate`（`0x011a2a70`）发送一个 NUL 结尾字符串（`v1/public_key` 主体）、密钥版本
作为大端 u16、主机版本 `0x2D`（盾）作为大端 u16、`00 01`、一个大端计数和 0x148 字节记录。
回复解析器 `0x011a2870`：字节 0 是状态（2：密钥过期，需重新获取），字节 5-6 是钳制到 6 的
大端计数 n，接着 n 个大端 u32，状态为 0 时还有一个 0x100 字节签名。

匹配类型是虚表 `0x2538238`、`0x2538358`、`0x2538478` 的槽 8：1 休闲、2 排位、3 在线
竞赛。它们由 `0x00adcfb0(obj, mode)` 从 `StateBtlSpotTop`（`0x00b23080`）构建。
块 `+0x108` 由 `0x00adc8b0` 从 `StateBtlSpotCompTop` 写入，所用的是存档块 `0x88F6D6AE`
（0x33D0 字节；前一个键 `0xEEE5A3F8` 是 PKHeX 的 `KOfficialCompetition`）中 0x33C0 处的 u64。

### 玩家资料

0xAEC 处 266 字节，也是信标在 0x1F 的记录（[session](swsh_session.md#taking-a-seat)）。
`0x01111970` 从单例 `[0x2610958]`（+0x310 到 +0x564）复制它；`0x01125080` 打包所有组或全
不打；位打包组按 LSB 优先。`trade_payload.read_tail` 将其解码。

    0x00  16  nn::oe::GetPseudoDeviceId
    0x10  16  nn::account::GetUserId, the account Uid
    0x20   8  nn::account::GetNetworkServiceAccountId, or zero
    0x28  24  trainer name, UTF-16, from MyStatus+0xB0; stale bytes after the terminator
    0x40  25  appearance, bit-packed:
                bit 0      MyStatus+0xA5 (gender) != 0
                bit 1      set by 0x0111cfec; 0 in every capture
                bits 2-5   MyStatus+0xA7, the language (3, French)
                bits 6-7   zero
                8 bits     MyStatus+0xCC
                17 x 10    the model 0x0111dd60 unpacks from the MyStatus bitfield at +0x00
                2, 2, 10   the last three of that unpacking
    0x59  55  position samples, bit-packed:
                2, 2 bits  `a` and `b`, below
                8 bits     generation: random at ring reset (0x00eb98a8), +1 per re-seed
                8 bits     player object byte +0x136 (7 in every capture)
                3 x 17     at 0x5C, 0x6D, 0x7E, newest first: 5-bit counter (+1 per push);
                           3-bit state (+0x1c8, below); x, y, z floats; yaw in radians.
                           0x00ebf590 pushes at most once a second from the field object's
                           +0x60 (position) and +0x50 (rotation)
                8 bits     at 0x8F: player object byte +0x140 (1 in every capture)
    0x90  37  activity, bit-packed: an 8-bit kind (13 in trade), an optional 28-byte part,
              a 24-byte field, a u16 at 0xB2, a bool; only kind and u16 non-zero. The u16 is the
              location, the line of `script/place_name.dat`, PKHeX's met-location id
              (170 Challenge Beach)
    0xB5  37  two more groups, zero in every capture
    0xDA  32  sixteen u16 records (`0x010f5060`): Record8 indexes 6, 32, 0, 33, 17, 27, 34, 24,
              12, 3, 10, 35, 38, 7, 36, 37, each clamped to 0xFFFF (PKHeX `RecordList_8`)
    0xFA   8  an optional u64, zero in every capture
    0x102  8  zero

接收器（`0x00dd5e24`）将位置存储在 +0xB0，将偏航以四元数存储在 +0xA0。

采样状态（`[[0x261bd18]]` 的 `+0x1c8`，由 `0x00ebf570` 设置）为 0，直到场景设置它；为 0 时
推送会立即返回。状态 1 和 2 是场景动作，3 和 4 是宝可梦露营访问和会话画面，6 是极巨团体战
匹配（`0x01466d30`）。`a` 为 1、2 或 3 时分别对应区域 `wr0101`、`wr0201`（铠之孤岛，捕获
位置为 170）和 `wr0301`，否则为 0，来自 FNV-1a 64 位区域键；`b` 来自虚表 `0x259add8` 的
槽 8 和 11。

0x90 处的活动记录为 `0x49` 字节，由 `0x0111b660(rec, kind)` 设置；连接交换设置
通信模式 2（`SetMode` `0x01096d10`，
[session](swsh_session.md#how-a-searching-sword-finds-a-partner)），通过 `0x2066c40` 处的表
映射为类型 13。

训练家名字出现四次（MyStatus、训练家卡片、队伍记录、资料）；
`pokeldn/swsh/trade_payload.rewrite` 会移动全部四次，交换画面会显示该训练家的名字。空队伍槽
为全零；0x810 处的计数与此一致。

## PK8

与 BDSP 在 `pokeldn/gen8.py` 中共享（PKHeX 的 `PK8` 和 `PB8` 都是 `G8PKM`）。剑发送 0x158
队伍形态（`pokeldn/swsh/pokemon.py`），BDSP 发送 0x148 存储形态。

    0x00  u32  encryption constant, in the clear. Seeds the cipher and the block order
    0x06  u16  checksum, in the clear, over the decrypted body only
    0x08       four 80-byte blocks, LCG-encrypted and permuted by (EC >> 13) & 31
    0x148      the party stats, LCG-encrypted with the stream restarted, never permuted

陷阱：

- 队伍状态重新启动 LCG（`PokeCrypto.Decrypt8` 从 EC 两次为 `CryptArray` 播种）；连续流会给
  出看似合理的垃圾数据，例如等级 110。
- `BLOCK_ORDER[sv]` 命名的是变成块 *i* 的块：应用它，不要反转它。32 个 `sv` 值中有 16 个
  自逆，且校验和忽略顺序。PKHeX 的 `BlockPosition` 条目 24-31 与 0-7 重复。

解码后队伍的检查：昵称与物种匹配；等级与经验匹配；0x126 处的极限特训与 IV 字 0x8C 匹配；
MyStatus 的训练家 ID 与每个 PK8 的匹配。

## 交换消息

`net_contents.trade.common.pokemon_trade.protocol_buffers`：

    Pokemon                  { 1 bytes   serializePokemonParam }
    PokemonTradeDataHolder   { 1 Pokemon pokemon }

一个 offer 在 10050 上携带 344 字节的 PK8（`trade.py` `pokemon_offer`）。解析器 `0x010d81d0`
构建一条 0x28 字节消息，调用 `ParseFromArray`（`0x0070c180`）；`MergePartialFromCodedStream`
（`0x010d9ee0`）只接受标签 0x0a。监听器将 `[Pokemon+0x18]` 读作 libc++ 的
`std::string`，复制 0x158 字节。

### 接收处理器的两次静默丢弃

`0x010d5e40`：

    w0 = 0x006b5850(senderPointer)                            0xfd on failure
    if (w0 == 0xfd) { [content+0x1a4] = 1; return; }          silent
    memcpy(stack, body, 0x158)
    subscriber = [content + 0x30 + index*8]
    if (subscriber == null || its refcount is 0) return       silent
    ... invoke it, then content 50's send 0x010d6000

内容 50 的初始化只填充 `+0x30` 和 `+0x38`，所以站点索引大于 1 时会直接返回；内容 40 的
`0x010dbc90` 在 `+0x38`/`+0x40` 处进行相同的把关。主机立即用自己的 10050 回应；没有收到
10050 返回意味着该 offer 从未到达 `0x010d5e40`。内容 30 的槽（`0x010ce080`）只拒绝自己的
id：无主的 offer 会通过盒子阶段，然后在内容 50 处失败。

### 内容 40 的消息

`net_contents.trade.common.sync_save.protocol_buffers`：

    SyncSaveDataHolder { 1 SyncCommand syncCommand }
    SyncCommand        { 1 int32       data       }

解析 `0x010ddb20`；`0x010df6d0` 只接受标签 0x0a，子消息解析器 `0x010debc0` 只接受标签 0x08
。`trade.sync_command` 构建它。

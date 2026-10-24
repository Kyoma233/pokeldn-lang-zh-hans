---
title: The Link Trade
parent: Sword and Shield
nav_order: 3
---

# 连接交换

剑盾的连接交换，从快照交换到存档。帧构建、内容注册和 PK8 参见[同步框架](swsh_protocol.md)。

## 序列

    1  主机在协议 0x84，端口 0 上广播其 3456 字节快照
    2  客户端确认分片（0x21）和传输（0x19 / 0x28）
    3  客户端在 0x84 端口 1 上发送自己的快照并报告完成
    4  交换画面开启
    5  主机在 0x7C 端口 1 上每秒多次发送 40030 RPC 对
    6  客户端应答该对并在 20030 上发送 `imReady`
    7  主机在 20030 上提供一只宝可梦；客户端在 10050 上提供一只
    8  玩家接受（盒子命令 4）
    9  在内容 40 上进行确认阶梯
    10 主机写入其存档

作为主机的主机不确认加入方在端口 0 上发送的快照；加入方的快照在端口 1 上。在其 0x84 得到应答之前，该主机不发送其他内容，并无限重传。`pokeldn/ldn/broadcast4.py` 实现了全部四种。

## 交换 RPC

ping、分块消息和提供使用端口 0，40030 对使用端口 1；在错误端口上的应答不会被读取。

    id 40030 = 40000 + 30
      1  offset      30
      2  base        10000，另一成员中为 20000
      3  station id  发送方的，等于席位记录的 host_constant
      4  clock       在消息之间递增的计数器
      5  bytes(4)    10000 成员为 00000000，20000 成员为 000018fc

`000018fc` 是哨兵 `0xfc18`（[步骤体](#the-step-body)）。`3e4e000012020801` 是承载 `imReady{isReady:true}` 的 20030；由加入客户端发送。这些消息可以根据解析字段逐字节重建（`pokeldn/swsh/trade.py`）。

- 每个应答只发送一次（`--answer-once`）；在定时器上重新推导应答会重新发送提供。
- 读取器在不是交换消息的消息上返回 `None`。一个可靠窗口（`44 00 01`，[主机迁移](#host-migration)）上的网状消息若引发异常，会结束接收任务和交换。

## 主机迁移

离会的《剑》主机会在协议 0x18 端口 1 上请求主机迁移（`nn::pia::mesh::LeaveWithHostMigrationJob`）：可靠头 `0f 00 00 03 00 01 00 01`，然后是网状消息 `44 00 01`，MIGRATION_START `[0x44, host index 0, new host index 1]`。被指定的客户端必须在网状端口 1 的可靠窗口上广播 `MIGRATION_FINISH`（[Pia 层](pia.md#host-migration)）。`--answer-migration --update-mesh` 会发送完成，并在新主机索引下发布网状更新。交接后保留会话尚未经过验证。

一部零售《剑》主机会在两种情况下发送一次 MIGRATION_START：

| 时间 | 条件 |
|---|---|
| 其盒子命令 3 后 0.8 秒 | 一场已完成的交换之后 |
| 玩家接受后的几秒钟，在主机以 `2-ALZAA-0016` 拆除之前 | 在阶梯之前失败的交换，加入方未发送确认命令 |

`bin/swsh_host.py --migrate` 会以盒子命令 3 和 MIGRATION_START 结束其主持的交换。默认情况下主机会保留会话。

## 主持一场交换

`bin/swsh_host.py` 负责主持，`pokeldn/swsh/host_trade.py` 则像作为主机的《剑》一样进行引导。一部零售法文版《剑》1.3.2 和一部模拟的《盾》1.3.2 各自加入并交换。

主机会使用新的网络 id、设备 id 和账户 uid 构建站点通告。在 0x84 上，它确认加入方的三个快照分片，用其训练家身份和 `--offer-file` PK8 重写该实时快照，然后在端口 0 上发送结果。主机提供的 PK8 会被写入 `--received`。`--advert FILE` 和 `--snapshot FILE` 则改用已保存的记录。

站点握手双向得到确认，主机的请求在 [0x10] 处携带加入方的随机字节；未确认时，加入方会重复其请求。主机应答加入方的 Sync Clock（0x1C，每两秒一次）和 Clone Clock（0x77）。

在双向 [ping 握手](swsh_session.md) 之后，应用层：

    0x84  每一方在其站点索引端口上的快照（加入方 1，主机 0），每个都在同一端口上得到确认；
          零售主机先发送，`host_trade.py` 后发送
    110   加入方在其交换画面出现后先 ping；主机用自己的 ping 和回复应答
          （该画面之前的主机 ping 会被确认并丢弃）
    30    主机打开内容 30；每一方在 20030 上提供并发送盒子命令 1；每次接受都是盒子命令 4
    130   加入方先 ping
    50    主机将其宝可梦发布为元素 0，并将加入方的 10050 中继为元素 1
    120   主机先 ping
    40    阶梯：主机命令作为元素 0，加入方的 10040 作为元素 1，阶段 0 到 4

## 交换动画

主机在其最后一个 syncCommand 40（`3`）之后播放交换动画，期间没有任何交换消息。加入 `bin/swsh_host.py` 的一部零售《剑》在那条 syncCommand 之后 1.2 秒开始播放动画，并在约 24 秒时将控制权交给玩家。

## 同一会话中的连续交换

一个会话可以连续进行多场交换：交换状态 9 会发送事件 7（成功）或 8（失败），写回状态 0，玩家则回到盒子里。内容 30 和 ping 110 在整个会话期间存在（设置 `0x010c9280`）；内容 50 与 ping 130（交换状态 1，`0x010d5440`）以及内容 40 与 ping 120（状态 6，`0x010dabc0`）会为每一场交换重建，每个元素都用新的 SyncPing 铸造。已经达到 synced 的 SyncPing 永远不会被就地重置，因此当一台主机没有内容 50 时发送的 ping 130 不会抵达任何持有者。

盒子画面的步骤机（`0x00aa5160`，表 `0x2059218`）读取由监听器 `0x00c8d900` 设置的搭档盒子命令标志。在第 3 步中，当搭档的标志 1（其提供）出现时，它会同时清除标志 1 和 4（`0x00aa5688..0x00aa569c`）；第 7 步等待标志 4（`0x00aa5628`），并且只有第 10 步才会发出动作 6，从而启动交换状态 1。与提供在同一突发中发送的盒子命令 4 会被擦除，主机则在第 7 步中带着“En attente d'une réponse（等待回应）”等待。搭档的 4 必须在主机处理其提供之后到达：`pokeldn.swsh.host_trade` 只有在加入方的 4 之后才发送自己的 4，而加入方启动器会在回应主机的 4 时发送自己的 4。

第 7 步只有在玩家按下 B 键（没有计时器）时才会结束：按下会清除搭档的标志，发送盒子命令 5（接受被撤回）并离开序列（`0x00aa57d0`）；在第 3 步中它会发送盒子命令 2。在那条盒子命令 5 之前发送的搭档提供和盒子命令 1 会与其标志一起被清除，因此 `pokeldn.swsh.host_trade` 和 `bin/swsh_connect.py` 会在盒子命令 5 之后重新发送它们的提供和盒子命令 1。如果没有第二次发送，主机就会停留在“En attente d'une réponse（等待回应）”上。

之后的每一场交换都会重复交换自身的部分：双方提供和盒子命令 1，按该顺序的两个盒子命令 4，ping 130（加入方先 ping），处于阶段 0 的新内容 50，ping 120，从阶段 0 到 4 的新内容 40。两场交换之间不会有 0x84 快照、ping 97 或 110、盒子命令 3 或内容 30 发布。`bin/swsh_host.py` 和 `bin/swsh_connect.py` 使用重复的 `--offer-file`，在同一个会话上分别与一部零售《剑》加入方和主机，每场交换各处理一条排队记录；当对方离开时，主机关闭。

`bin/swsh_connect.py` 会在已完成的阶梯（40040 上的阶段 4）之后把主机的提供视为下一场交换，并清除其每场交换的状态；40030 对和 ping 应答会继续沿用。
`bin/swsh_host.py --accept-first --lead SECONDS` 会扮演主机玩家的操作（先接受，在交换后提供其下一条排队记录）；这两个启动器在模拟板（`tests/test_esp32.py`）上的同一会话中双向各交换两条记录。

当零售加入方的玩家在盒子里按下 B 键时，该主机会发送盒子命令 2 和 3 以及网状消息 `0401`，并无错误地解除认证；其下一次搜索可以加入同一个托管网络。正在搜索的主机会加入任何通过[匹配规则](swsh_session.md#how-a-searching-sword-finds-a-partner)的网络。

## 盒子状态机

内容 30 承载从交换画面到提供的一切。`onBoxSyncStateCommand` `0x010ce180` 会丢弃线上命令 0 以及 7 及以上的命令，并用事件 *N* 通知每个监听器，对应线上命令 *N*（跳转表 `0x2067bec`）。监听器 `0x00c8d900` 会设置 `[owner + 0x218 + code] = 1`；1 表示提供，2 撤回提供；4 确认，5 撤回一个 4。发送器 `0x010cda70(content, command)` 由场景跳转表 `0x00a96d10` 根据其动作 `+0x78` 驱动：

    action 1  ->  command 3
    action 2  ->  the Pokemon (0x010ca430), then command 1
    action 3  ->  command 2
    action 4  ->  command 5
    action 5  ->  command 4
    action 6  ->  0x010ca640, which stores its Pokemon and sets the trade state to 1

命令会保存在 `[content+0x48]` 中，直到通道就绪字节 `[content+0x4c]` 被置位；在此期间到达的不同命令会置位错误字节 `[content+0x4d]`，并且不发送任何内容。

命令 3 恰好由一侧发送：设置 `0x010c9280` 会设置 `[session+0x419] = 0x00dceea0() & 1`（来自玩家列表），而每帧更新 `0x010c9bb0` 会在该字节清零时发送它。`--box-open` 会在 0x84 确认时发送盒子命令。

## 交换状态机

`[session+0x140]`，范围 1..10，表 `0x2067b68`：1 启动内容 50 并发送其宝可梦（`0x010ca0a0`），2 等待，3 是宝可梦交换（`0x010d54b0`），4 做决定（`0x01109320`），6 安装四个委托并启动内容 40（`0x010ca1ac`），8 释放它（`0x010dac90`），9 是终止状态（`[+0x144]` 置位表示失败；监听器收到事件 8）。盒子回调 `0x010ca800` 在状态非 0 时会丢弃事件。状态 2 在委托 `0x010cc380` 中结束：搭档的宝可梦被写入 `session+0x70`，一个 0x60 字节记录（`0x010f5cc0`）。当内容 50 的初始化 `0x010d4d90` 失败时，调用方会设置 `[session+0x144] = 1`，状态 9：通信中断消息。

## 确认阶梯

Content 40 是一道屏障，每条命令对应一级梯级。

### 阶段到状态映射

状态是 `delegate+0x5c`。机器 `0x010dae70` 将 `state - 1` 分派到表 `0x2067ed0`；状态 2、4、7、9 只能通过 `0x010dbf40` 离开，该函数会忽略大于 4 的 u16，否则索引表 `0x2067f4c`：

    phase 0  -> state 1              -> send(0), announcing 1     0x010db308
    phase 1  -> state 3              -> send(1), announcing 2     0x010db0b0
    phase 2  -> state 5 -> 6 or 8    -> send(2), announcing 3     0x010db0dc / 0x010db104
    phase 3  -> state 10 or 11 -> 12 -> send(3), announcing 4     0x010db16c
    phase 4  -> state 13 -> 14       -> 0x010db970 tears down, content+0x84 = 0xfc18; no send

`[delegate+0x58]`（`0x110e620(...) & 1`）是角色：状态 7 立即发送 2，状态 9 在倒计时 `[delegate+0x60]`（一个 2..302 的 xorshift 抽取值）之后发送。初始化将 delegate 安装为 10040 持有者的监听器（`0x010da6d0`），并在 `[content+0x2c0]` 安装其第二接口（`0x010da6bc`）。

### 泵

`0x010db3e0` 由内容 40 的 tick 在机器之前运行，是 `[content+0x80]` 上的一个 17 状态机器，带有一个共享尾部。尾部通过 `0x010de310` 提交内容的阶段 `[content+0x17c]`（该函数丢弃挂起的消息体并清空作业队列 `content+0x310`），并在阶段等于已宣告的阶段时调用 delegate 的状态设置器，然后运行排队作业 `0x010ddf40` 和元素更新 `0x006d4b80(content+0xd0)`。

| 字段 | 含义 |
|---|---|
| `+0x84` | 已提交的阶段；构造函数设为 `0xfc18` |
| `+0x86` | 随最后一条命令宣告的阶段，在所有五个发送点 (`0x010dbab0`) 处为 `data + 1` |
| `+0x17c` | 阶段，即 `element+0xac` |

当阶段达到 `+0x86` 时，梯子攀升。泵状态（表 `0x2067f08`；`[+0x1c0]` 是元素的 `+0xf0` 通道）：

    1   element ready -> 2; delegate slot 0 with the phase (command 0, announcing 1)
    2   a pending body at +0x88 -> 3
    3   all ready, every pair's low half == phase: send the body -> 4
    4   0x006d3690 publishes the high half; the master goes to 8, others to 7
    8   every station has sent a command -> 9
    9   no resend byte set -> 10
    10  every high half == announced: the master writes shared value = announced -> 7
    11  clears every flag (a station left); [+0x374] ? 12 : 2
    14  the gated commit

状态 8 到 10 仅在主机上运行（`0x018407f0`）；其他站点跟随共享值。内容 40 的注册器在 `[+0x374]` 存储 1：有站点离开时进入 11、12，并结束梯子（`0x010dc720`）。

### 阶段就是元素的字段

阶段是 `element+0xac`（`0xd0 + 0xac = 0x17c`）：注册器用 `0x006d44e0(element, 0)` 在 `content+0xd0` 处铸造 40040 元素，而 `0x010c0000..0x010e0000` 范围内没有任何代码会写入它。

它只在 `0x006d4ca0`（元素更新 `0x006d4b80` 的尾部）中推进：一旦共享值 `0x006d3260([element+0xf0])`（无值时为 `0xfc18`）被发布为本站自己的低半部分，阶段就变成该共享值，并通知内容。

`0x018407f0` 在承载 Pia 网格的控制台上为真（[会话](swsh_session.md#the-pia-session-object)）。只有它会初始化共享值——`+0xf0` 通道的 16 位子元素（[子元素种类](swsh_protocol.md#sub-element-kinds)）；每个站点都会采用该值。内容发送的其他形态见[下文](#shapes-the-confirmation-content-also-sends)：

    0x006d3260  read            ready [sub+0x61] ? [sub+0x88] : 0xfc18
    0x006d33b0  write(v)        0x006d3570 when not ready or body != v
    0x006d3570  publish         body [sub+0x88] = v and queue it per station
    0x006d3060  all high == v   every pair's [sub+0x8a] == v

写入不会触碰 ready 字节（只有接收函数 `0x006d6a08` 会存储 `+0x60`），因此读取会返回 `0xfc18`，直到有消息到达；在主机上，那条消息就是它自己的消息。

### 步骤消息体

内容 40 的 elementId 20000 上的四字节消息体：低半部分是阶段，高半部分是最后宣告的值：

    0x006d3980(channel, v)   body = <u16 v><u16 [sub+0x8a]>    low; from the element update
    0x006d3690(channel, v)   body = <u16 [sub+0x88]><u16 v>    high; from pump state 4, [content+0x86]

观察到的梯子：

    000018fc   phase 0, announced 0xfc18   the birth sentinel
    00000100   phase 0, announced 1        the cue; command 0 already sent
    01000100   phase 1, announced 1        caught up, committed
    01000200   phase 1, announced 2        state 3 sent command 1
    02000200   phase 2, announced 2        caught up
    02000300   phase 2, announced 3        committed, sent command 2
    04000400   phase 4                     the teardown rung

`trade.parse_sync_step`、`SYNC_LADDER` 和 `sync_announced_phase` 会解码它。

### 命令

`SyncSaveDataHolder{syncCommand{data:N}}` 位于 10040，可靠端口 0。处理函数 `0x010dbc90` 会丢弃 `0x006b5850` 无法解析的发送方（`0xfd`），将 `[arg1+0x14]` 处的 int32 传给中继 `0x010dbe20`，然后总是对 `[content+0x2a0]` 调用 `0x006a24a0(obj, sender, 1)`（`0x010dbdf8..0x010dbe08`）：梯子从不读取该值，所以任何命令都会推进一级。状态只通过 `0x010dbf40` 移动，该函数由泵以自己的阶段调用。

`[content+0x2a0]` 是每站点标志位图（`0x006a24a0` 设置，`0x006a2840` 在列出的每个站点都已设置时为 1，`0x006a2760` 清除）；状态 8 等待它和提交，状态 11 清除它。该标志在网络更新的排空阶段 `0x006db3b0` 中设置，帧函数 `0x00f1df30` 会在游戏更新前后各运行一次它。内容 40 的命令 tick `0x010dae70` 在两次排空之间运行。

一级需要一条命令在上一次提交之后到达主机。在第 0 级，任何命令都算数，包括 cue `00000100` 上的那条；之后，cue 上的命令（`01000200`、`02000300`、`03000400`）会在提交之前到达并被清除，而 caught-up 消息体上的命令（`01000100`、`02000200`、`03000300`）算数：

| 命令，每个新消息体一条 | 最后的消息体 |
|---|---|
| 1，在 `00000100` 上 | `01000200`：第 0 级 |
| 4，`000018fc` 到 `01000200` | `02000300`：第 0 和第 1 级 |
| 9，`000018fc` 到 `04000400` | `04000400`：交换 |

`--confirm-commands 0,1,2,3,0,1,2,3,0,1,2,3` 会在每个新消息体（包括 `000018fc`）弹出一个；队列不能耗尽。`answer_rpc` 会回显消息体且两半都不移动；`--confirm-phase N` 写入低半部分。

### 取消和继续消息

30040，即 `SequenceDataHolder`（[协议页](swsh_protocol.md#the-30000-holder)），存储在 `[content+0x2b8]`，监听器为 `content+0x68`（vtable `0x02580030`）：

| 分支 | 消息 | 处理函数 |
|---|---|---|
| 1 | CancelAccepted | `0x010dce70` |
| 2 | RequestCancel | `0x010dc920` |
| 3 | RequestCancelAll | `0x010dcaa0` |
| 4 | RequestForcedProceed | `0x010dc7b0` |

每个动作仅在 `currentSeqNo` 等于已提交阶段 `(s16)[content+0x84]` 时生效。RequestCancel 用 `CancelAccepted{[+0x84], isForced: 0}` 回应发送方并清除其标志；RequestCancelAll 用 `isForced: 1` 回应列出的每个站点并清除每个标志。CancelAccepted 重新运行状态 2 到 4 并保留阶段。RequestForcedProceed（作业 `0x010dd040`）写入 `0x006d33b0([content+0x1c0], targetSeqNo)`，这是状态 10 的写入，但没有状态 8 和 9，也没有主机测试。

RequestForcedProceed 会在没有 `syncCommand` 的情况下推进共享阶段（模拟《盾》）。后继命令为这些请求的梯子会在保存前停在 “Communicating”。

### 确认内容也会发送的形态

40040 信封没有 `ownerId`，消息体也不是四字节：

    elementId 20000, no owner, 2 bytes   0000   then   0100
    elementId 1,     no owner, 4 bytes   00000000        after a syncCommand{data:0}
    no elementId,    no owner, 4 bytes   00000000  then  01000000

配对的接收函数 `0x006d6490` 会丢弃两字节的那些（`cmp x2,#4`）；它们就是共享值（[阶段就是元素的字段](#the-phase-is-the-elements-field)）。

## 联盟卡

交换完成后，每台主机都会询问是否保留对方的联盟卡，即其快照 0x924 处的 TrainerCard（[协议](swsh_protocol.md#the-party-payload-on-protocol-0x84)）；回答不会发送任何内容。

Oui 将其原样存入存档块 `0x28e707f5`：从 `album+0x230` 开始的 300 个大小为 0x1d0 的槽位，在 `+0x1c8` 非零时为空闲（`0x013fbab0` 填充第一个空闲槽；`0x013fbc00` 在所有槽位都已使用时返回 1）。

`0x013fbc40(album, card)` 会在某个已用槽位与卡片 0x1C 处的 u32 以及 0x1A8 处的八个字节匹配时跳过提问。0x1C 是 PKHeX 的 `TrainerCard8.TrainerID`，即 `(SID << 16 | TID) mod 10**6`；0x1A8 是 `TimestampPrinted`，一个 Unix 时间。面对模拟的《盾》时，更改训练家 ID 或更改 0x1A8 处的某个字节会再次询问并存下第二个槽位；更改宝可梦图鉴计数或名称则不会。`pokeldn.swsh.league_card` 会映射一个 u32；`trade_payload.rewrite` 设置训练家 ID。

零售版《剑》会绘制接收日期、`game`（0x24）的标志、0x39 处的三个 ASCII 字节、`dex_complete`（0x30）时的洛托姆图鉴王冠，以及七个星格中的 `count + 1` 个，其中 `count = card[0x177] + (card[0x1b6] != 0) + (card[0x1b7] != 0)`。构建器 `0x0158eef0` 从存档填写 0x177（`DesignLevel`：有 `FSYS_GAME_CLEAR` 时为 4，否则徽章数 > 6、> 3、> 0、0 时分别为 3、2、1、0）、0x1B1（`FSYS_SEED_CHALLENGE`）、0x1B3（`FSYS_INPUT_SHIRT_NUMBER`）以及星星 0x1B6、0x1B7（`FSYS_R1_GAME_CLEAR`、`FSYS_R2_GAME_CLEAR`）；标志键是名称的 FNV-1a 64 位（[协议](swsh_protocol.md#the-player-profile)）。

`0x0158f5e0` 会拒绝一张卡片（DesignLevel 5、language 6、GlossIndex 9），该卡片会被替换为默认卡。`bin/swsh_host.py --card-set FIELD=VALUE` 编辑发送的卡片（`pokeldn.swsh.league_card` 字段）；全新的 `trainer_id` 会让主机再次询问。

## 提供的记录

在 20030 上提供的记录是快照的队伍槽位 `--offer-slot`，在原位编辑，因此显示的队伍与提供内容一致；身份重写首先运行，`party_matches_trainer` 成立。`pokeldn.swsh.pokemon.build_from` 会重写校验和，在新的加密常量下重新打乱，并保留每个未命名字节。一只构建的皮卡丘交换到零售版《剑》再换回后，等级、性格、特性、性别、球种、携带物品、个体值和基础点数均保持不变，并通过 PKHeX 合法性检查。

法语版《剑》1.3.2 在四次交换中接受了其存档已经持有的记录（相同 PID 和 EC）。《盾》1.3.2 在读取路径上没有重复检查：PID 和加密常量 getter 不会走到盒子遍历，盒子代码只读取物种和蛋标志。晶灿钻石在 PK8 字节 0x52 的非法标志没有访问器读取（[BDSP 交换页面](bdsp_trade.md#duplicate-detection)）。
在 `bin/swsh_host.py` 和 `bin/swsh_connect.py` 上的 `--fresh-pid` 会生成新的加密常量和 PID。

    --offer-slot 1 --offer-nickname POKELDN --offer-ivs 31,31,31,31,31,31

| 标志 | 效果 |
|---|---|
| `--offer-nickname`, `--offer-ot` | 26 字节 UTF-16 字段，最多 12 个字符；昵称会设置昵称标志，否则将采用物种名称 |
| `--offer-species` | 仅物种字；其他一切保持模板不变 |
| `--offer-ability ID`, `--offer-moves A,B,C,D` | 这两个字段；PP 和回忆招式保持不变 |
| `--offer-level N` | 位于 0x148 的等级字节 |
| `--offer-experience N` | 位于 0x10 的经验值字 |
| `--offer-ivs` | 六项个体值 |
| `--offer-file FILE` | 四种形态中的任意一种 `.pk8`（存储或队伍、加密或 PKHeX 解密导出，通过头部校验和区分）；初训家名称和 ID 移到快照的训练家 |
| `--offer-file-as-is` | 保留文件中的初训家 |
| `--save-offer FILE` | 在操作无线电之前写入构建的记录 |

法语版《剑》1.3.2 不检查特性或招式是否与物种匹配，会从经验值字（0x10）取等级，并根据个体值、基础点数、性格和极限特训（0x126）重建能力值；将初训家 ID 显示为 `(SID << 16 | TID) mod 1000000`，不将任何初训家 ID 与 MyStatus 比较，并将 PID 高半部分 `low ^ TID ^ SID` 显示为异色。没有数据的物种（152）会以皮卡丘的模型、黑色精灵球图标和零基础种族值存储。

尚未解决：其他缺失物种会显示什么，以及名称是来自名称字段还是一次失败的查找。

## 已完成交换的命令行

`swsh_connect.py --preset trade` 带有交换所需的标志；在其后给出的标志会覆盖预设。当主机正在搜索本地连接交换时（Y-Comm、连接交换、本地，两条消息都按 A）：

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/swsh_connect.py --keys PROD_KEYS \
        --preset trade --save-offered offered.pk8 --capture trade.jsonl

发回的快照是同一会话中主机自己的快照（`--send-snapshot live`，预设默认值）：三个 0x84 片段被重新组装，训练家名称、TID 和 SID 被重写为 `--snapshot-name/-tid/-sid`，并在主机的快照重新组装完成后发出。`--send-snapshot FILE` 改为发送已保存的 3456 字节载荷（`--preset capture`，然后运行 `tools/switch/swsh_snapshot.py` 写出一个）。

`--offer-file FILE` 将一个 `.pk8` 放入提供的队伍槽位。重复使用时，它会在会话中为每次交换排队一条记录；最后一条会用于之后每次交换，在 `--fresh-pid` 下使用新 PID，并且第 N 次交换会用 `-N` 写出 `--save-offered`。若主机已提供某次交换且其阶梯尚未结束，会话最多会在 `--hold` 之后再保持 `--grace` 秒（300）。没有队伍能力值的存储格式记录可以交换；主机会根据经验值计算等级。

## 惩罚，以及干净地结束一次运行

链接仍活动时交换超时属于失败的交换，并会锁定主机，使其无法再进行交换（`msg_ui_live_comm_app_alert_00`，`/bin/message/French/common/live_comm.dat` 的第 331 行）；锁定的时长无法读取。在保存期间于 `04000400` 之后 15 秒切断链接，会显示通信错误 `2-ALZAA-0016`，不会触发交换锁定，并会立即开始新的本地搜索。

`bin/swsh_connect.py --abort-on-stall SECONDS` 会在阶梯已开始且经过 SECONDS 秒仍没有新正文时断开链接。它会在第 4 阶段（静默拆除梯级）退出（`stall_abort()`、`final_phase_seen`、`LADDER_FINAL_PHASE`），因此链接绝不会在保存期间被切断。

## 验证已完成的交换

收到的宝可梦在 0xC4 处带有 `CurrentHandler` 1，并在 0xA8 处的 `HandlingTrainerName` 中带有接收者名称，覆盖发送者的原训练家。`--offer-echo` 会将主机自己的记录返回，因此只有物种不同才能证明发生了转移。

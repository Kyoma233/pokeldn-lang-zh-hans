---
title: The Link Trade
parent: Sword and Shield
nav_order: 3
---

# 连接交换

剑／盾的连接交换，从快照交换到存档写入。帧结构、内容注册与 PK8 详见 [同步框架](swsh_protocol.md)。

## 交换序列

    1  主机在协议 0x84、端口 0 广播其 3456 字节快照
    2  客户端确认片段 (0x21) 与传输 (0x19 / 0x28)
    3  客户端在 0x84 端口 1 发送自己的快照并报告完成
    4  交换画面打开
    5  主机在 0x7C 端口 1 每秒多次发送 40030 RPC 对
    6  客户端应答该对并在 20030 发送 `imReady`
    7  主机在 20030 提供宝可梦；客户端在 10050 提供宝可梦
    8  玩家确认（盒子命令 4）
    9  内容 40 上运行确认阶梯
    10 主机写入存档

主机不确认加入者在端口 0 发送的快照；加入者的快照走端口 1。在其 0x84 得到应答前，主机不发送任何其他内容并无限重传。`pokeldn/ldn/broadcast4.py` 实现了全部四种情况。

## 交换 RPC

心跳、区块消息与提供使用端口 0，40030 对使用端口 1；错误端口上的应答不被读取。

    id 40030 = 40000 + 30
      1  offset      30
      2  base        10000，另一成员为 20000
      3  station id  发送者的，等于座位记录的 host_constant
      4  clock       消息间递增的计数器
      5  bytes(4)    10000 成员为 00000000，20000 成员为 000018fc

`000018fc` 是哨兵 `0xfc18`（[步骤主体](#the-step-body)）。`3e4e000012020801` 是携带 `imReady{isReady:true}` 的 20030；加入客户端发送它。消息从解析字段逐字节重建（`pokeldn/swsh/trade.py`）。

- 每个应答仅发送一次 (`--answer-once`)；定时器上重新派生应答会重发提供。
- 读取器对非交换消息返回 `None`。可靠窗口上的网格消息 (`44 00 01`，[主机迁移](#host-migration)) 抛出异常将结束接收任务与交换。

## 主机迁移

离开会话的主机剑请求主机迁移，使用协议 0x18 端口 1 (`nn::pia::mesh::LeaveWithHostMigrationJob`)：可靠头 `0f 00 00 03 00 01 00 01` 随后是网格消息 `44 00 01`，MIGRATION_START `[0x44, host index 0, new host index 1]`。被指名的客户端必须在网格端口 1 的可靠窗口广播 `MIGRATION_FINISH`（[Pia 层](pia.md#host-migration)）。`--answer-migration --update-mesh` 发送 finish 并在新主机索引下发布网格更新。迁移后保留会话未经验证。

主机零售剑在两种情况下各发送一次 MIGRATION_START：

| 时机 | 条件 |
|---|---|
| 其盒子命令 3 后 0.8 s | 已完成的交换后 |
| 玩家确认后数秒，主机在 `2-ALZAA-0016` 中拆解前 | 阶梯前失败的交换，加入者未发送确认命令 |

`bin/swsh_host.py --migrate` 以盒子命令 3 和 MIGRATION_START 结束其主持的交换。默认主机保留会话。

## 主持交换

`bin/swsh_host.py` 主持，`pokeldn/swsh/host_trade.py` 按主机剑的方式引导。零售法版剑 1.3.2 与模拟盾 1.3.2 均可加入并交换。

主机用全新的 network id、device id 与 account uid 构建站点广播。在 0x84 上确认加入者的三个快照片段，用其训练家身份与 `--offer-file` PK8 重写该实时快照，然后在端口 0 发送结果。主机提供的 PK8 写入 `--received`。`--advert FILE` 与 `--snapshot FILE` 使用保存的记录。

站点握手双向确认，主机请求携带加入者的随机字节（位于 [0x10]）；未确认时加入者重复请求。主机应答加入者的 Sync Clock (0x1C，每两秒) 与 Clone Clock (0x77)。

应用层在双向 [心跳握手](swsh_session.md) 后：

    0x84  双方快照各自在其站点索引端口上（加入者 1，主机 0），各在同端口确认；零售主机先发，`host_trade.py` 后发
    110   加入者在交换画面就绪后先心跳一次；主机以自己的心跳与回复应答（画面前的主机心跳被确认并丢弃）
    30    主机打开内容 30；双方在 20030 提供并发送盒子命令 1；每次确认均为盒子命令 4
    130   加入者先心跳
    50    主机将自己的宝可梦作为元素 0 发布，并将加入者的 10050 作为元素 1 中转
    120   主机先心跳
    40    阶梯：主机命令为元素 0，加入者的 10040 为元素 1，阶段 0 至 4

## 交换动画

主机在其最后一个 syncCommand 40 (`3`) 后播放交换动画，期间无交换消息。加入 `bin/swsh_host.py` 的零售剑在该 syncCommand 后 1.2 s 开始动画，约 24 s 后将控制权交给玩家。

## 同一会话上的连续交换

一个会话承载接连的交换：交换状态 9 发送事件 7（成功）或 8（失败），写入状态 0，玩家回到盒子。内容 30 与心跳 110 存续于会话（设置 `0x010c9280`）；内容 50 与心跳 130（交换状态 1，`0x010d5440`）以及内容 40 与心跳 120（状态 6，`0x010dabc0`）在每次交换时重建，每个元素伴随新的 SyncPing 铸造。已达 synced 的 SyncPing 不会原地复位，因此在主机无内容 50 时发送的心跳 130 将无持有者接收。

盒子画面的步骤机 (`0x00aa5160`，表 `0x2059218`) 读取监听器 `0x00c8d900` 设置的伙伴盒子命令标志。步骤 3 中，遇伙伴标志 1（其提供），清除标志 1 与 4 (`0x00aa5688..0x00aa569c`)；步骤 7 等待标志 4 (`0x00aa5628`)，仅步骤 10 发出动作 6，启动交换状态 1。与提供同一突发发送的盒子命令 4 被擦除，主机停留在步骤 7 显示 "En attente d'une réponse"。伙伴的 4 必须在主机处理完其提供后到达：`pokeldn.swsh.host_trade` 在加入者的 4 之后才发送自己的 4，加入者启动器在应答主机时发送其 4。

步骤 7 仅在玩家按 B 结束（无计时器）：按下清除伙伴标志，发送盒子命令 5（撤回确认）并离开序列 (`0x00aa57d0`)；步骤 3 中发送盒子命令 2。在该盒子命令 5 前发送的伙伴提供与盒子命令 1 随其标志一同清除，因此 `pokeldn.swsh.host_trade` 与 `bin/swsh_connect.py` 在盒子命令 5 后再次发送提供与盒子命令 1。缺少第二次发送会导致主机停留在 "En attente d'une réponse"。

此后每次交换重复交换自身部分：双方提供与盒子命令 1，两个盒子命令 4 依序，心跳 130（加入者先心跳），新内容 50 从阶段 0 开始，心跳 120，新内容 40 从阶段 0 至 4。交换间无 0x84 快照、心跳 97 或 110、盒子命令 3 或内容 30 发布。`bin/swsh_host.py` 与 `bin/swsh_connect.py` 配合重复的 `--offer-file`，在单会话上分别让零售剑加入者与主机各交换一条排队记录；主机在主机离开时关闭。

`bin/swsh_connect.py` 在完成的阶梯后（40040 上阶段 4）将主机的提供视为下一次交换并清除其逐交换状态；40030 对与心跳应答延续。`bin/swsh_host.py --accept-first --lead SECONDS` 扮演主机玩家（先确认，交换后提供下一条排队记录）；两启动器在模拟板上单会话双向各交换两条记录（`tests/test_esp32.py`）。

当零售加入者玩家在盒子中按 B，主机发送盒子命令 2 与 3 及网格 `0401` 并取消认证且无错误；其下一次搜索可加入同一主持网络。搜索中的主机加入任何通过 [匹配规则](swsh_session.md#how-a-searching-sword-finds-a-partner) 的网络。

## 盒子状态机

内容 30 承载从交换画面到提供的一切。`onBoxSyncStateCommand` `0x010ce180` 丢弃线命令 0 与 7 以上，并以事件 *N* 通知每个监听器（跳转表 `0x2067bec`）。监听器 `0x00c8d900` 置 `[owner + 0x218 + code] = 1`；1 提供，2 撤回提供；4 确认，5 撤回 4。发送器 `0x010cda70(content, command)` 由场景跳转表 `0x00a96d10` 在其动作 `+0x78` 上驱动：

    动作 1  ->  命令 3
    动作 2  ->  宝可梦 (0x010ca430)，然后命令 1
    动作 3  ->  命令 2
    动作 4  ->  命令 5
    动作 5  ->  命令 4
    动作 6  ->  0x010ca640，存储其宝可梦并将交换状态置 1

命令保存在 `[content+0x48]` 直到通道就绪字节 `[content+0x4c]` 被置位；期间到达不同命令则置错误字节 `[content+0x4d]` 且不发送。

命令 3 仅由一方发送：设置 `0x010c9280` 根据玩家列表令 `[session+0x419] = 0x00dceea0() & 1`，逐帧更新 `0x010c9bb0` 在该字节为 0 时发送。`--box-open` 在 0x84 确认时发送盒子命令。

## 交换状态机

`[session+0x140]`，范围 1..10，表 `0x2067b68`：1 启动内容 50 并发送其宝可梦 (`0x010ca0a0`)，2 等待，3 为宝可梦交换 (`0x010d54b0`)，4 决定 (`0x01109320`)，6 安装四个委托并启动内容 40 (`0x010ca1ac`)，8 释放它 (`0x010dac90`)，9 为终态（`[+0x144]` 置位表示失败；监听器收到事件 8）。盒子回调 `0x010ca800` 在状态非 0 时丢弃事件。状态 2 在委托 `0x010cc380` 结束：伙伴宝可梦进入 `session+0x70`，一条 0x60 字节记录 (`0x010f5cc0`)。当内容 50 的初始化 `0x010d4d90` 失败，调用者置 `[session+0x144] = 1`，状态 9：中断通信消息。

## 确认阶梯

Content 40 是一道屏障，每个命令对应一级阶梯。

### 阶段到状态的映射

状态位于 `delegate+0x5c`。状态机 `0x010dae70` 将 `state - 1` 分发到表 `0x2067ed0`；
状态 2、4、7、9 仅通过 `0x010dbf40` 离开，该函数忽略高于 4 的 u16，否则索引表 `0x2067f4c`：

    phase 0  -> state 1              -> send(0), announcing 1     0x010db308
    phase 1  -> state 3              -> send(1), announcing 2     0x010db0b0
    phase 2  -> state 5 -> 6 or 8    -> send(2), announcing 3     0x010db0dc / 0x010db104
    phase 3  -> state 10 or 11 -> 12 -> send(3), announcing 4     0x010db16c
    phase 4  -> state 13 -> 14       -> 0x010db970 拆除，content+0x84 = 0xfc18；不发送

`[delegate+0x58]` (`0x110e620(...) & 1`) 为角色：状态 7 一次性发送 2，状态 9 在倒计时 `[delegate+0x60]` 后发送，该倒计时为 2..302 的 xorshift 随机数。初始化将 delegate 安装为 10040 持有者的监听器 (`0x010da6d0`) 及其在 `[content+0x2c0]` 的第二个接口 (`0x010da6bc`)。

### 交换中的传说宝可梦

状态 1 (`0x010daf3c`) 通过两次物种检查，从 `[delegate+0x48]` 和 `[delegate+0x50]` 处的两只宝可梦重新计算角色：`0x008fc280(species, form)` 和 `0x008fc310(species)`。
`0x008fc280` 对物种 150、151 和 249 到 251，以及跳转表 `0x02052aec`（382 到 494）和 `0x02052cb0`（643 及以上）中的条目返回真。角色为 0 时，状态 6 转至状态 8，其倒计时会延迟主机的命令 2。

在模拟 盾 1.3.2 主机上测试，`bin/swsh_connect.py` 加入：

| 提出的宝可梦 | 角色字节 | `02000200` 后主机行为 |
|---|---|---|
| 水箭龟、皮卡丘 | 1 | 0.6 秒后发送命令 2 和 `02000300` |
| 勒克猫、赞乃，对方回复一次 | 0 | 53 秒无命令，content 40 处于状态 9 且泵处于状态 3 (`0x010db48c`，其发送 `0x010de080` 未完成)，随后提示 "L'échange de Pokémon n'a pas pu être effectué" |
| 勒克猫，对方每秒重发一次 | 0 | `02000200` 后 2.4 秒收到 `02000300`；交换完成 |

重发的对携带主机的上一帧时钟加上经过的时间，以每秒 60 帧的速率（捕获中信封时钟的速率）；`--ladder-refresh` 设置周期。主机方向（`bin/swsh_host.py`，主机加入）无需更改即可完成 勒克猫 交换：其主机从自身的帧时钟发布。泵状态 3 中哪个检查读取加入方的时钟尚未确定。

### 泵

`0x010db3e0` 在机器之前由 content 40 的 tick 运行，是一个基于 `[content+0x80]` 的 17 状态机，带有共享尾部。尾部通过 `0x010de310` 提交 content 的阶段 `[content+0x17c]`（该函数丢弃待处理的 body 并清空作业队列 `content+0x310`），当阶段等于宣布的阶段时调用 delegate 的状态设置器，随后运行队列作业 `0x010ddf40` 和元素更新 `0x006d4b80(content+0xd0)`。

| 字段 | 含义 |
|---|---|
| `+0x84` | 已提交的阶段；构造函数设为 `0xfc18` |
| `+0x86` | 最后一次命令宣布的阶段，所有五个发送点均为 `data + 1` (`0x010dbab0`) |
| `+0x17c` | 阶段，`element+0xac` |

当阶段达到 `+0x86` 时阶梯上升。泵状态（表 `0x2067f08`；`[+0x1c0]` 为元素的 `+0xf0` 通道）：

    1   元素就绪 -> 2；delegate slot 0 带阶段（命令 0，宣布 1）
    2   +0x88 有待处理 body -> 3
    3   全部就绪，每对的低半字 == 阶段：发送 body -> 4
    4   0x006d3690 发布高半字；主机去 8，其他去 7
    8   每个站点都已发送命令 -> 9
    9   未设置重发字节 -> 10
    10  每个高半字 == 宣布：主机写共享值 = 宣布 -> 7
    11  清除所有标志（有站点离开）；[+0x374] ? 12 : 2
    14  受控提交

状态 8 到 10 仅在主机 (`0x018407f0`) 上运行；其他站点跟随共享值。Content 40 的注册器在 `[+0x374]` 存储 1：站点离开会经 11、12 结束阶梯 (`0x010dc720`)。

### 阶段即元素的字段

阶段为 `element+0xac`（`0xd0 + 0xac = 0x17c`）：注册器在 `content+0xd0` 以 `0x006d44e0(element, 0)` 创建 40040 元素，`0x010c0000..0x010e0000` 内无指令写入该字段。

阶段仅在 `0x006d4ca0`（元素更新 `0x006d4b80` 的尾部）推进：一旦共享值 `0x006d3260([element+0xf0])`（无值时为 `0xfc18`）作为站点自身的低半字被发布，阶段即变为该共享值，并通知 content。

`0x018407f0` 在主机 Pia 的 mesh（[会话](swsh_session.md#the-pia-session-object)）上为真。只有它播种共享值，即 `+0xf0` 通道的 16 位子元素（[子元素种类](swsh_protocol.md#sub-element-kinds)）；每个站点采纳它。content 发送的其他形状见[下文](#shapes-the-confirmation-content-also-sends)：

    0x006d3260  读取            ready [sub+0x61] ? [sub+0x88] : 0xfc18
    0x006d33b0  写入(v)         未就绪或 body != v 时调用 0x006d3570
    0x006d3570  发布            body [sub+0x88] = v 并按站点入队
    0x006d3060  全部高半字 == v  每对的 [sub+0x8a] == v

写入不改动 ready 字节（仅接收 `0x006d6a08` 写 `+0x60`），因此收到消息前读取返回 `0xfc18`；对主机而言该消息即自身发出的。

### 步骤体

content 40 的 elementId 20000 上的四字节 body，低半字为阶段，高半字为上次宣布：

    0x006d3980(channel, v)   body = <u16 v><u16 [sub+0x88]>    低半字；来自元素更新
    0x006d3690(channel, v)   body = <u16 [sub+0x88]><u16 v>    高半字；来自泵状态 4，[content+0x86]

观测到的阶梯：

    000018fc   phase 0, announced 0xfc18   出生哨兵
    00000100   phase 0, announced 1        提示；命令 0 已发送
    01000100   phase 1, announced 1        追上，已提交
    01000200   phase 1, announced 2        状态 3 发送命令 1
    02000200   phase 2, announced 2        追上
    02000300   phase 2, announced 3        已提交，发送命令 2
    04000400   phase 4                     拆除阶梯

`trade.parse_sync_step`、`SYNC_LADDER` 和 `sync_announced_phase` 可解码它。

### 命令

10040 上的 `SyncSaveDataHolder{syncCommand{data:N}}`，可靠端口 0。处理器 `0x010dbc90` 丢弃 `0x006b5850` 无法解析的发送者 (`0xfd`)，将 `[arg1+0x14]` 处的 int32 传给中继 `0x010dbe20`，随后总在 `[content+0x2a0]` (`0x010dbdf8..0x010dbe08`) 上调用 `0x006a24a0(obj, sender, 1)`：该值从未被阶梯读取，因此任何命令都能推进一级。状态仅通过 `0x010dbf40` 移动，由泵以自身阶段调用。

`[content+0x2a0]` 为每站点标志图（`0x006a24a0` 置位，`0x006a2840` 在所有列出站点均置位时为 1，`0x006a2760` 清除）；状态 8 等待它与提交，状态 11 清除它。标志在网络更新的排空 `0x006db3b0` 中置位，帧 `0x00f1df30` 在游戏更新前后各运行一次排空。Content 40 的命令 tick `0x010dae70` 运行于两次排空之间。

一级阶梯需一个命令在上次提交后到达主机。第 0 级任何命令均计数，包括提示 `00000100` 上的命令；后续提示上的命令（`01000200`、`02000300`、`03000400`）在提交前到达并被清除，追上 body 上的命令（`01000100`、`02000200`、`03000300`）计数：

| 每个新 body 的命令 | 最后的 body |
|---|---|
| 1，在 `00000100` 上 | `01000200`：第 0 级 |
| 4，`000018fc` 到 `01000200` | `02000300`：第 0、1 级 |
| 9，`000018fc` 到 `04000400` | `04000400`：完成交换 |

`--confirm-commands 0,1,2,3,0,1,2,3,0,1,2,3` 每个新 body 弹出一个，包含 `000018fc`；队列不得耗尽。`answer_rpc` 回显 body 且不移动任何半字；`--confirm-phase N` 写入低半字。

### 取消与继续消息

30040，即 `SequenceDataHolder`（[协议页](swsh_protocol.md#the-30000-holder)），存储于 `[content+0x2b8]`，监听器为 `content+0x68`（vtable `0x02580030`）：

| case | 消息 | 处理器 |
|---|---|---|
| 1 | CancelAccepted | `0x010dce70` |
| 2 | RequestCancel | `0x010dc920` |
| 3 | RequestCancelAll | `0x010dcaa0` |
| 4 | RequestForcedProceed | `0x010dc7b0` |

仅当 `currentSeqNo` 等于已提交阶段 `(s16)[content+0x84]` 时生效。RequestCancel 向发送者回复 `CancelAccepted{[+0x84], isForced: 0}` 并清除其标志；RequestCancelAll 向所有列出站点回复 `isForced: 1` 并清除所有标志。CancelAccepted 重跑状态 2 到 4 并保留阶段。RequestForcedProceed（作业 `0x010dd040`）写入 `0x006d33b0([content+0x1c0], targetSeqNo)`，即状态 10 的写入，但无状态 8、9 及主机测试。

RequestForcedProceed 无需 `syncCommand` 即可推进共享阶段（模拟 盾）。后续命令均为此请求的阶梯会在存档前停留于 "Communicating"。

### 确认内容同时发送的形状

无 ownerId 且 body 非四字节的 40040 信封：

    elementId 20000, 无 owner, 2 字节   0000   然后   0100
    elementId 1,     无 owner, 4 字节   00000000        在 syncCommand{data:0} 后
    无 elementId,    无 owner, 4 字节   00000000  然后  01000000

对对的接收 `0x006d6490` 丢弃两字节体（`cmp x2,#4`）；它们即共享值（[阶段即元素的字段](#the-phase-is-the-elements-field)）。

## 联盟卡

交换后每台主机询问是否保留对方的联盟卡，即其快照 0x924 处的 TrainerCard（[协议](swsh_protocol.md#the-party-payload-on-protocol-0x84)）；回答不发送任何内容。

选择“是”将其原样存入存档块 `0x28e707f5`：从 `album+0x230` 开始共 300 个槽位，每槽 `0x1d0`，`+0x1c8` 非零时为空闲（`0x013fbab0` 填入首个空闲槽；`0x013fbc00` 全用时返回 1）。

`0x013fbc40(album, card)` 在已用槽位匹配卡片 0x1C 处的 u32 与 0x1A8 处的八字节时跳过询问。0x1C 为 PKHeX `TrainerCard8.TrainerID`，即 `(SID << 16 | TID) mod 10**6`；0x1A8 为 `TimestampPrinted`，Unix 时间。对模拟 盾，更改训练师 ID 或 0x1A8 处字节会再次询问并占用第二个槽位；更改图鉴计数或姓名则不会。
`pokeldn.swsh.league_card` 映射一个 u32；`trade_payload.rewrite` 设置训练师 ID。

零售 会绘制接收日期、`game`（0x24）的徽标、0x39 处的三个 ASCII 字节、`dex_complete`（0x30）对应的洛托姆图鉴皇冠，以及 `count + 1` 个七星窗格，其中 `count = card[0x177] + (card[0x1b6] != 0) + (card[0x1b7] != 0)`。构建器 `0x0158eef0` 从存档填充 0x177（`DesignLevel`：有 `FSYS_GAME_CLEAR` 则为 4，否则按徽章 >6、>3、>0、0 分别为 3、2、1、0）、0x1B1（`FSYS_SEED_CHALLENGE`）、0x1B3（`FSYS_INPUT_SHIRT_NUMBER`）及星星 0x1B6、0x1B7（`FSYS_R1_GAME_CLEAR`、`FSYS_R2_GAME_CLEAR`）；标志键为名称的 FNV-1a 64（[协议](swsh_protocol.md#the-player-profile)）。

`0x0158f5e0` 拒绝卡片（DesignLevel 5、language 6、GlossIndex 9），并用默认卡替换。`bin/swsh_host.py --card-set FIELD=VALUE` 编辑发送的卡（`pokeldn.swsh.league_card` 字段）；全新的 `trainer_id` 会让主机再次询问。

## 提供的记录

20030 上的提供是快照的队伍栏位 `--offer-slot`，原地编辑，因此显示的队伍与提供一致；身份重写先运行且 `party_matches_trainer` 成立。
`pokeldn.swsh.pokemon.build_from` 重写校验和，在新加密常数下重新打乱，并保留所有未命名字节。构建的皮卡丘经零售版《剑》交换再交回，等级、性格、特性、性别、球、携带道具、个体值和努力值均保留，并通过 PKHeX 合法性检查。

法语版《剑》 1.3.2 在四次交换中均接受其存档已持有的记录（相同 PID 与 EC）。
《盾》 1.3.2 在读取路径上无重复检查：PID 与加密常数取值器未遍历箱子，箱子代码仅读取种类与蛋标志。《晶灿钻石》 PK8 字节 0x52 的非法标志未被任何访问器读取（见 [BDSP 交换页](bdsp_trade.md#duplicate-detection)）。
`bin/swsh_host.py` 与 `bin/swsh_connect.py` 上的 `--fresh-pid` 抽取新的加密常数与 PID。

    --offer-slot 1 --offer-nickname POKELDN --offer-ivs 31,31,31,31,31,31

| 标志 | 作用 |
|---|---|
| `--offer-nickname`, `--offer-ot` | 26 字节 UTF-16 字段，最多 12 字符；昵称设置 nicknamed 标志，否则使用种类名 |
| `--offer-species` | 仅种类字；其余保留模板值 |
| `--offer-ability ID`, `--offer-moves A,B,C,D` | 两字段；PP 与回忆招式保留 |
| `--offer-level N` | 0x148 处的等级字节 |
| `--offer-experience N` | 0x10 处的经验值字 |
| `--offer-ivs` | 六个个体值 |
| `--offer-file FILE` | 任意四种形态之一的 `.pk8`（存放格式或队伍格式、加密或 PKHeX 解密导出，按头部校验和区分），自带原训练家 |
| `--receiver-owns N` | 第 N 个 `--offer-file` 置于主机实时快照的训练家名下（[原训练家](gui.md#original-trainer)） |
| `--save-offer FILE` | 在触碰无线电前写出构建好的记录 |

法语版《剑》 1.3.2 不校验特性或招式与种类的对应，从经验值字（0x10）取等级并按个体值、努力值、性格与超级训练（0x126）重算能力值，显示 OT ID 为 `(SID << 16 | TID) mod 1000000`，不与 MyStatus 比对任何 OT ID，以 `low ^ TID ^ SID` 的 PID 高半部判定异色。无数据的种类（152）以皮卡丘模型、黑色精灵球图标与零基础点存储。

未决：其他缺失种类会绘制什么，以及名称是名称字段还是查找失败的结果。

## 完成交换的命令行

`swsh_connect.py --preset trade` 携带交换所需标志；其后给出的标志覆盖预设。在主机搜索本地连接交换（Y-Comm、连接交换、本地、两边均按 A 确认）时：

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/swsh_connect.py --keys PROD_KEYS \
        --preset trade --save-offered offered.pk8 --capture trade.jsonl

回传的快照为主机同一会话的自身快照（`--send-snapshot live`，预设默认）：三个 0x84 片段重组，训练家名、TID 与 SID 改写为 `--snapshot-name/-tid/-sid`，在主机快照重组完成后发出一次。
`--send-snapshot FILE` 改为发送已保存的 3456 字节载荷（`--preset capture`，再经 `tools/switch/swsh_snapshot.py` 写出）。

`--offer-file FILE` 将一条 `.pk8` 放入提供队伍栏位。重复使用时，按会话为每次交换排队一条记录；最后一条服务于此后所有交换，配合 `--fresh-pid` 使用新 PID，交换 N 在其阶梯结束后将 `--save-offered` 带 `-N` 写出；主机撤回的提供不写入文件。主机已提供但阶梯未结束的交换，将挂起会话至 `--hold` 后最多 `--grace` 秒（300 秒）。任一启动器上的 `--hold-after-trade SECONDS` 在最后一笔排队交换后延长运行该秒数（[离开](swsh_session.md#leaving)）。无队伍能力值的存放格式记录可交换；主机按经验值计算等级。

## 惩罚，与干净地结束运行

链路存活时交换超时视为失败交换，主机被锁定无法交易（`msg_ui_live_comm_app_alert_00`，`/bin/message/French/common/live_comm.dat` 第 331 行）；锁定时长不可读。
在 `04000400` 后 15 秒、存档过程中切断链路，显示通信错误 `2-ALZAA-0016`，不触发交易锁定，并立即开始新的本地搜索。

`bin/swsh_connect.py --abort-on-stall SECONDS` 在阶梯启动后若 SECONDS 秒内无新主体则切断链路。它在第 4 阶段（静默拆除阶、`stall_abort()`、`final_phase_seen`、`LADDER_FINAL_PHASE`）退让，因此链路绝不在存档期间被切断。

## 验证完成的交换

接收到的宝可梦在 0xC4 携带 `CurrentHandler` 1，在 0xA8 的 `HandlingTrainerName` 中记录接收方姓名，覆盖发送方的原训练家。`--offer-echo` 将主机自身记录回传，因此仅当种类不同才能证明发生了转移。

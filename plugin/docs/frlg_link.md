---
title: The link protocol
parent: FireRed and LeafGreen
nav_order: 1
---

# 连接协议

本页说明火红／叶绿在 Pia 之上的链路层：RFU 组帧、座位屏障、联盟房间、对战与竞技场。引用来自 [pret/pokefirered](https://github.com/pret/pokefirered)。

# RFU 链路层

## 每个父设备轮询对应一个子设备槽位

`RfuMain2_Parent` 每次轮询保留一个子设备槽位，并检查其滚动 `childSendCmdId` 标签是否为上一次 `+1 mod 8` [link_rfu_2.c:876-892]。标签错误会使 `numChildRecvErrors[i]` 加一；连续超过四次就调用 `RfuSetErrorParams` 并断开链路。同一次轮询内出现第二个槽位即为标签被丢弃。子设备若自由运行或每次轮询发出两个槽位，会在房间行走的 0.3 秒内被丢弃；每次轮询一个槽位时所有标签都按序。该规则在每个阶段都成立，包括座位行走。

## 父设备表的第一行是掌机自己的命令，回显回来

这条规则支配着掌机发送时的每一次停顿。

`MGL_Send` 以 252 字节分块，并在每个块之前和最后等待 `MGL_HasReceived(link->sendPlayerId)`，也就是它自己的 id 1 [mystery_gift_link.c:176,205; mystery_gift_client.c:33]：它一直等到自己的块通过父设备 `gRecvCmds` 的第一行完整返回，而该行由主机回显 [link_rfu_2.c:970,1125]。`HandleBlockSend` 在回显前保持 INIT，`SendLastBlock` 重复最后一段直到回显，然后镜像位掩码中缺失的每一段都会被重新入队 [link_rfu_2.c:1366-1416]。

`rfu_leader.ChildEcho`：

- 从不丢弃任何不同命令；一个片段丢失会导致整块重发，第二次丢失会结束链路；
- 合并仍在等待中的重发（`SendLastBlock` 每帧重新发送）；在镜像已经发出之后到达的重发会得到应答。

子设备对每个接收到的父设备帧发送一条命令 [link_rfu_2.c:600]，因此镜像队列不会自行增长。

## 一步地格恰好是 16 次链路更新

`FacingHandler_DpadMovement` 将 `directionSequenceIndex` 设为 16，每次链路更新减一 [overworld.c:3432-3470]。经过 N 个方向键后，脚本化行走的间隙需要 `16 - (N mod 16)` 次更新。

## 玩家的输入并不总会传输

`UpdateHeldKeyCode` 在 `GetLinkSendQueueLength() > 1` 时，将 EMPTY、方向键码、START 和 A 重写为 `LINK_KEY_CODE_NULL` [overworld.c:2786-2810]。`LINK_KEY_CODE_READY`（0x16）不受影响：门控条件是 0x16，而不是没有方向键码。

## 座位是双方共同屏障

`Task_EnterCableClubSeat` 调用 `SetInCableClubSeat()`（下一次发出的按键为 READY），并在 `GetCableClubPartnersReady()` 上自旋 [cable_club.c:827-869]；只有所有玩家都 READY 时它才为真 [overworld.c:2988-2999]。随后 `Task_StartWirelessTrade` 运行 `SetLinkStandbyCallback()` [cable_club.c:910-943]。只有在两名玩家都 READY 之后才驱动待机轮次；在处于 `CABLE_SEAT_WAITING` 的掌机上驱动它们会导致其座位状态机出错。

## 真实子设备端到端发送的内容

一台零售法文火红子设备；IDLE 计数来自一次交换：

```
IDLE x8
SEND_BLOCK_INIT w1=0x0011 x4   + 17 fragments      (LinkPlayer)
IDLE x31
SEND_BLOCK_INIT w1=0x0009 x4   + 9 fragments       (trainer card)
IDLE x262   READY_EXIT_STANDBY w1=0x0000 x1
IDLE x72    READY_EXIT_STANDBY w1=0x0001 x1
IDLE x45    <room: SEND_HELD_KEYS 0x1b x24, EMPTY, 0x1a once, the walk, READY, then EMPTY x13>
IDLE x22    READY_EXIT_STANDBY w1=0x0002 x1
IDLE x28    READY_EXIT_STANDBY w1=0x0003 x1
IDLE x75    -> the host pulls the party
```

- 每个待机轮次是一帧，由 Pia Reliable 重传直到成功送达。
- 轮次之间，子设备发送全零的 IDLE。leader 在队伍交换前的静默帧计数器只会在完全空闲的槽位上推进；EMPTY keepalive 会使其死锁。
- `LINK_KEY_CODE_IDLE`（0x1a）将对端的链路状态设为 IDLE [overworld.c:2755]；地格脚本只对处于该状态的玩家运行。

## 双方只有在收到对端消息后才会推进

`CB1_UpdateLinkState` 只有在某个 `gRecvCmds` 条目非零时才运行 `UpdateAllLinkPlayers` [link_rfu_2.c:787-800]；这个循环会稳定为每次往返一次交换。主机 `SEND_HELD_KEYS` 的高字节是 `heldKeyCount`，每个已准备好的命令对应一个。

## 入座后的待机门控与离场

双方坐下后，掌机在回显主机的 `READY_EXIT_STANDBY` 之后，在 mpId 0 广播自己的 count=2。它只在子设备的 count 与自己相等时接受该 count [link_rfu_2.c:1577-1591]。以主机自己的 mp0 count=2 为门控，重发 count=3，其间隔须超过 `HostTradeTiming.entry_final_standby_quiet_frames`（75 个槽位，长于子设备 60 帧的重发 [link_rfu_2.c:1529]）。

离场过程：主机发出 `LINK_KEY_CODE_EXIT_ROOM`（0x17），并阻塞直到每个玩家都处于 EXITING_ROOM [overworld.c:2962-2981]；子设备在 held-keys 流上以自己的 0x17 应答。

## 离开房间

在坐下前或对战后走出交换中心的掌机会发送 held key 0x17，并在“请稍候”中等待每个玩家 [overworld.c:2977]。主机在 `H_ENTRY_SEAT`、`H_RETURN_FIELD` 和对战状态（`host_trade._child_send_held_keys`）中以自己的 0x17 应答。

### 静默门控

当掌机持续 `QUIET_GATE_SECONDS`（0.25 秒）没有发送任何内容时，除每 `QUIET_RETRANSMIT_SECONDS`（1 秒）一次外，主机会丢弃自己的重传（`tests/test_host_quiet_gate.py`）。

## 交换后的取消

`BufferTradeParties` 在礼物缎带交换之后、菜单命令被读取之前清除已接收块标志 [trade.c:1549]，因此在此期间完成的取消可能会丢失 [1593-1633]。`bin/frlg_trade_join.py` 在选择 Cancel 后，当 leader 的请求到达时重新发送 `REQUEST_CANCEL`（`0xEEAA`）（`trade.py`，`_on_linkcmd`）。跟随者在 YES 之后发送 `REQUEST_CANCEL`，并空闲等待直到 `BOTH_CANCEL_TRADE` [trade.c:2049, 1643]；主机会立即应答掌机的 `REQUEST_CANCEL`。

## 单方面取消会让双方返回菜单

`PLAYER_CANCEL_TRADE` / `PARTNER_CANCEL_TRADE` 返回 `CB_MAIN_MENU` [trade.c:2094-2113]；只有 `BOTH_CANCEL_TRADE` 才会结束会话 [1715-1722]。用 `PARTNER_CANCEL_TRADE` 应答 `REQUEST_CANCEL` 会让掌机一直显示“votre ami veut échanger des Pokémon”；`bin/frlg_trade_host.py` 用 `BOTH_CANCEL_TRADE` 应答。leader 自己的选择不会发送任何内容 [trade.c:1811-1828]。先发送了 `READY_TO_TRADE` 的加入者会在 leader 第一次 Cancel 时触发 `PLAYER_CANCEL_TRADE`；随后 `bin/frlg_trade_join.py` 在菜单处取消。

## 链路上的版本与语言

`IsTryingToTradeAcrossVersionTooSoon` [union_room.c:1499] 只会针对既不是火红也不是叶绿的伙伴触发。`ConvertInternationalString` 会特别处理日文名字；法文火红能接受英文神秘卡片。联盟房间搜索会跳过日文候选者 [union_room.c:3726]；神秘礼物的 `Task_ListenForCompatiblePartners` 不会。日文卡带使用其他的神秘卡片和 News 活动编号（[日文布局](frlg_rom_map.md#japanese-layout)）。在神秘礼物好友列表中，掌机会在 GameData 中发送自己的 ROM 游戏代码，主机在投递前选择该卡带的地址。

## 模拟器可以自行关闭链路

`HandleLinkConnection` 在 Switch 构建中调用 `svc_51` [link.c:1654]；返回非零意味着 `CloseLink()`，然后在神秘礼物下软复位或 `RfuReloadSave()` [link.c:1674]：Switch 错误 2318-0006。主机在 RFU 层仍正常时出现崩溃，则指向 LDN/Pia。

| SVC | 调用来源 | 作用 |
|---|---|---|
| `swi 0x45` | librfu_rfu.c:667,749 | 将 `gRfuLinkStatus` 交给模拟器 |
| `swi 0x49` | AgbRfu_LinkManager.c:657 | 非零期间，在 SEARCH_CHILD 中保持 `connect_period` 开放 |
| `swi 0x4a` | AgbRfu_LinkManager.c:720 | 同上，但在 SEARCH_PARENT 中 |
| `swi 0x4b` | link_rfu_2.c:2114, union_room_player_avatar.c:518 | `SVC4B_EXIT_EARLY` 退出 SpawnGroupLeader；`SVC4B_RESEED_RNG` 根据主机的训练家 ID 重新播种 |
| `swi 0x51` | link.c:1654 | 立即关闭链路（在神秘礼物下软复位） |
| `swi 0x53` | wireless_communication_status_screen.c:328 | 由模拟器驱动从状态屏幕退出 |

# 本游戏实际使用的无线层

## 通告速率集

缺少 6、9 和 12 Mbit/s 的关联响应会让掌机在关联后 2.9 到 3.9 秒离开 LDN，此时 Pia 会话已经完成：76 次此类关联中有 42 次离开；带有这些速率的 284 次关联中有 0 次离开。信标和掌机的请求速率集都不重要。掌机究竟需要其中哪些速率尚不清楚。ESP32 softAP 携带全部十二个（[hardware_esp32.md](hardware_esp32.md)）。

主机通告 Switch 速率集（1B 2B 5.5B 11B 6 9 12 18，扩展 24 36 48 54）。信标头部携带元素 0、1 和 3（41 字节）；Switch 的其他元素是可选的。带 WMM 的信标会让掌机发送 QoS 数据帧，其 TID 会进入 CCMP nonce 和 AAD。在隐私能力下没有 RSN 的探测响应会让掌机的关联请求得不到应答。`host_pia` 单播 type 5 Update Session。

## 作为 Pia 子设备的掌机

- 子设备掌机需要 type 2 Join Response：如果只有 type 5，它会每 0.5 秒重发自己的加入请求，并在加入后 3.05-3.20 秒离开。
- 一台主持神秘礼物的掌机会在 50-66 毫秒内用 type 5 应答子设备掌机；它却以“没有 type 2，并且 2.0 秒后才给 type 5”应答 `bin/frlg_mg_client.py`，原因不明。一台主持交换的掌机会在 34 毫秒内发送 type 5 和 type 2。

一台主持神秘礼物的掌机，面向接收客户端，从它的 Net 0x11 开始：

    0.000  Net 0x11 (once)
    0.006  client: Net 0x12 + Session join
    0.252  RTT request, then every 316ms
    2.038  Session type 5, no type 2
    2.040  client: type 6 (finalize); 2.159 reliable open
    4.63   host's own NI (the player's YES)
    6.82   SEND_PLAYER_IDS, 6.87 BLOCK_REQ
    8.15   Net 0x50 property update every ~0.5s, acked 0x51

## 离开 Pia 会话

子设备掌机在其 RFU `D` 帧之后离开：一次暂停、Session type-3 离开请求，然后是它的 LDN 解除认证（reason 3）。在没有 type-4 应答时：

| 间隔 | 实测值 |
|---|---|
| `D` to the first type 3 | 1.97-2.02 s |
| type 3 to type 3, four sends | 0.48-0.54 s |
| first type 3 to the LDN leave | 2.03-2.08 s |

    type 3, 22 bytes:  03 | random u32 | constant id (8) | variable id (2) | kind 0 | IPv4 | port
    type 4, 15 bytes:  04 | random u32 | the request's constant id and variable id

GBA 应用 `main` 中的偏移：`LeaveMeshJob` 在 `0xcacf4` 发送请求，截止时间 500 毫秒；`WaitLeaveResponse`（`0xcaf38`）在响应标志 `+0x99` 时结束，或最多重发四次（`0xcb06c`..`0xcb08c`）。type-4 情况（`0xba028`，表 `0x180fc9`）会为携带该站点自身 ID 的 15 字节消息设置标志。主机的 type-3 处理器（`0xbf2d4`）接受 22 或 34 字节，并用请求的第 5 到第 14 字节应答 type 4（`0xbf454`..`0xbf4e4`）。`HostPeerProtocol` 对每个 type 3 都这样应答，单播，头为 `(console variable, 0x00C6)`，并按发往该掌机的单播计数器编号；编号低于该计数器的 type 4 会被忽略。掌机为每个目的地保留一个计数器。

这个暂停是固定的 120 tick 倒计时（每秒 60 tick，`0x4ff64`）。`TryDisconnectRfu` 和 `LinkRfu_Shutdown` 发出 `swi 0x44` [link_rfu_2.c:1446-1455, 625]；处理器 `0x58b0c` 投递断开请求 1（`0x53d98` -> `0x4f0ec`，`+0x730`），tick `0x4ee34` 设置 `+0x734 = 0x78`（`0x4ef00`）并在归零时调用槽位 `0x78`（`0x4ef60`），而 `Session::LeaveAsync`（`0xb1060`，来自 `0x537e0`）发送 type 3（[pia.md](pia.md)，离开会话）。任何接收到的内容都不会缩短它；只有请求 2 或 3（`swi 0x42`，或带 PID 0 的 `swi 0x43`）或设置 `+0x277c` 的 Pia 错误才会缩短它。

## 802.11 行为

- 作为站点（station）的掌机：无省电，每个数据帧前都发 RTS，离开时发一次解除认证。
- Switch 主机以 11M 发送信标，并以 48-54M 发送数据。

## Pia 报头 nonce 是游戏机强制递增的计数器

游戏机会丢弃任何数据报，只要其 8 字节报头 nonce 不严格大于该通道上最近接受的值。`Sim._next_nonce` 和宿主都在计数。

## 前向携带

每个可靠帧都会在接下来的 4 个数据报中重复。空口丢失为 1-2% 且呈突发性；一个空洞会挡住其后的每一个时隙，直到其重传，随后重传会填满游戏机深度为 8 的 RFU 接收队列。没有前向携带时，一个丢失时隙就会使游戏机断开。宿主按序号去重。

## 游戏机的确认滞后是一个 512 ms 节拍器

游戏机的累计 ack 位于 CTRL 帧载荷中（`parse_bulk_ack`）；可靠报头中的 `ack` 是发送方最低待确认序号。每隔 16 或 17 个 512 ms 时隙（相位锁定到 LDN 加入），游戏机会停顿 50-70 ms，重传其最后几帧，然后其 ack 跳进若干帧。在负载下，停顿正好发生在发送窗口已满时。具体是模拟器还是 Pia/LDN 定时器驱动，目前未知。

## ident-25 停顿：空洞加上无界积压

当一个空洞在无界积压之后闭合时，游戏机会立即投递所有被保持的帧，其深度为 8 的 RFU 队列会丢弃 ident-25（`MG_LINKID_RAM_SCRIPT`）片段，并在链路保持的情况下停留在“Transmission...”。父块永远不会被反映，因此这种丢失在捕获中不可见。`HostSession` 在 `HOST_OUTSTANDING_MAX`（6）个帧未被确认时会保留新帧，而 `--ram-script-block-repeat 3` 会发送 ident 25 三次。到底是空口丢失还是游戏机的交递丢弃了该片段，目前未知。

## 卡片之后的传输阶段断开

在 ack 停顿之后每个 tick 重发所有未确认帧会杀死会话。默认开启的检查项：

- `HOST_RTX_LIMIT` 限制每个 VBlank 中 Reliable 重传的数量。
- `FRLG_ECHO_MAX` 限制子方数据块时隙的 FIFO 回显。
- 发送套接字是非阻塞的，`FRLG_QUIET_GATE_MS` 会在游戏机静默（接收卡片后约 0.5 秒，即其 flash 保存期间）时暂停重传。

## 套接字与空口之间滞留的数据报

宿主数据报在进入空口之前被滞留 0.1-1.1 秒，会让游戏显示“erreur de connexion, rapprochez-vous”[link_rfu_2.c:2312, link.c:1521]。在 ESP32 开发板上测得的最长等待为 265 ms（[ESP32 radio](hardware_esp32.md)，TX_DONE）。

# 联盟房间

## 被列出：广播的活动字节

搜索中的游戏机仅当候选方的 activity 位于其链接组的接受列表中时才会保留该候选方 [`IsPartnerActivityAcceptable`，union_room.c:1590；src/data/union_room.h:398-456]。在联盟房间中，游戏机搜索 `{ACTIVITY_SEARCH, 0xFF}`，然后搜索 `IN_UNION_ROOM | activity`（`IN_UNION_ROOM = 1 << 6`）[union_room.c:2664]。记录字节 16 是 activity：21 会在神秘卡片屏幕上将宿主列出，22 则会列在神秘新闻上。

## 连接：IN_UNION_ROOM，必须正好且单独存在

`IsPartnerActivityIncompatible` 要求 `partner->activity == IN_UNION_ROOM` 精确匹配 [link_rfu_2.c:2933]。0x44 会生成头像，但连接被拒绝（“le DRESSEUR est occupé”）；0x40 会连接，交易意图在链路建立后协商。

## 没有父 NI，以及五帧规则

联盟房间子方设置的是 TYPE_UNI 接收缓冲，而不是 TYPE_NI [link_rfu_2.c:2526, 533]。父 NI 载荷是致命的：它会以 ERR_RECV_BUFF_OVER 失败 [librfu_rfu.c:2300]，并以“erreur de connexion”结束 [link_rfu_2.c:2585]。`RFULeader(skip_parent_ni=True)`（`--union-room`）会跳过它。

游戏机会在第五个未应答的父帧时断开（`maxMFrame = 4` [link_rfu_2.c:128]）。`--union-room-keepalive N`（120 可行）会在 UNI 之前将第一个 NI_START 重新呈现 N 个 VBlank。游戏机随后会等待约八秒：在 NI_START 待处理期间，`rfu_UNI_setSendData` 会以 ERR_SUBFRAME_SIZE 失败 [librfu_rfu.c:2262, 1449]，直到 `NI_failCounter_limit`，即最后一个 NI_START 之后 480 帧 [link_rfu_2.c:139, AgbRfu_LinkManager.c:1328]。

## 连接后游戏机做什么

一旦链接，游戏机会交换训练家卡片 [union_room.c:2858-2879]，并显示 Salut / Combat / Tchat / Retour。每个选项都会发送一个 `SEND_PACKET` 并等待 [union_room.c:3151]：

| 游戏机发送 | activity | 宿主回应 |
|---|---|---|
| 0x48 | CARD (Salut) | 0x51 ACCEPT |
| 0x44 | TRADE (trading board) | 0x51 ACCEPT |
| 0x41 | BATTLE (Combat) | 0x51 ACCEPT |
| 0x45 | CHAT (Tchat) | 0x51 ACCEPT |
| 0x40 | EXIT (Retour) | 视为游戏机关闭 |

每个活动之后双方都会 `SetLinkStandbyCallback` [union_room.c:2995, :3012]。接受方受 `svc_CommsAllowedByParentalControls()` 限制 [union_room.c:3159, :3037]。Retour 发送 0x40，然后发送 READY_CLOSE_LINK 并正常断开。

## 交换板

交换板读取记录字节 18（`type << 2`）、19（`gameClear | level << 1`，[广告记录](frlg_rom.md#the-advertisement-record)）以及 22:24（`tradeSpecies:10`）[union_room.c:3400; include/link_rfu.h:107]。

交换板上每次链接只进行一次交换：`Task_StartUnionRoomTrade` 保存 `CB2_ReturnToField` [union_room.c:1744]，而 `CB2_SaveAndEndTrade` 仅为交换中心的回调保持链接 [trade_scene.c:2722-2725]。顺序：游戏机的宝可梦块（count 9）、宿主的、其邮件块（count 19）、宿主的、动画、READY_FINISH、CONFIRM_FINISH、保存屏障、双方 READY_CLOSE_LINK、断开。没有队伍交换、菜单或房间路线。

## 聊天

聊天通过 `SendBlock(0, buf, 0x28)`（count 4），主动发送，没有 `BLOCK_REQ` [union_room_chat.c:429, :823]：

    [0]      command: 0 NULL, 1 CHAT, 2 JOIN, 3 LEAVE, 4 DROP, 5 DISBAND
    [1..8]   player name, EOS-terminated
    [9]      multiplayer id            (JOIN / LEAVE / DROP / DISBAND)
    [9..39]  message text, EOS-terminated (CHAT)

[union_room_chat.c:1256-1283]。对 0x45 的 ACCEPT 会保持链路 [union_room.c:1938]；两名成员进入时都会发送 JOIN。一行可容纳 15 条记录 [union_room_chat.c:21]；接收方会在屏幕外绘制更多内容，而宿主会在启动时拒绝过长行（`uroom_chat.entry_count`）。在 LEAVE 时，领队必须断开链路 [union_room_chat.c:596-660]：宿主会在 0.1 秒后发送 DROP 并关闭。追加到 `--chat-file` 的行约在写入后 1.7 秒到达游戏机。

## 链接对战（UR_BATTLE 0x41）

`HasAtLeastTwoMonsOfLevel30OrLower` [union_room.c:4565] 要求双方各有两只非蛋的等级不高于 30 的同行宝可梦，并在提议和接受时均检查 [union_room.c:2923, 3176]。

双方各选两只后，每方发送一个从 0x51 开始的 0x20 字节块（若取消则为 0x52），其余为零（`CB2_UnionRoomBattle`）；任何其他内容都会关闭链接。Switch 路径会添加两个链接任务等待，并在其间加入一个待机（case 50-52）。`StartUnionRoomBattle(BATTLE_TYPE_LINK | BATTLE_TYPE_TRAINER)` [union_room.c:1811] 会设置 `linkType = 0x2211` [link.h:92; battle_controllers.c:520]。然后 [battle_main.c:934]：

    state 1  SendBlock struct LinkBattlerHeader {versionSignatureLo, versionSignatureHi,
             vsScreenHealthFlagsLo, vsScreenHealthFlagsHi, struct BattleEnigmaBerry}
    state 3  SendBlock gPlayerParty[0..1]   200 bytes      state 4  recv -> gEnemyParty
    state 7  SendBlock gPlayerParty[2..3]   200 bytes      state 8  recv
    state 11 SendBlock gPlayerParty[4..5]   200 bytes      state 12 recv
    state 15 InitBattleControllers

### 主控方选举

只有 `BATTLE_TYPE_IS_MASTER` 一侧运行回合解析、伤害和 RNG [battle_controllers.c:141, :45]；宿主作为非主控方是一个战斗控制器。`LinkBattleComputeBattleTypeFlags` [battle_main.c:886]：如果 `gBlockRecvBuffer[0][0] == 0x100` 或双方签名相等，则玩家 0 为主控，否则由最高版本决定。宿主发送 0x200，使游戏机成为主控。

### 链路缓冲协议

每个控制器命令都是一个带 8 字节头的 SendBlock [battle_controllers.c:401-435]：`BUFFER_ID, ACTIVE_BATTLER, ATTACKER, TARGET, SIZE_LO, SIZE_HI, ABSENT_BATTLER_FLAGS, EFFECT_BATTLER`，载荷按 `size - size % 4 + 4` 存储。`bufferId` 0 = BUFFER_A（命令），1 = BUFFER_B（回复），2 = 携带发送方 multiplayer id 的执行标志清除 [:566-594]。Battler 0 属于主控方。

`MarkBattlerForControllerExec` 设置位 `28+battler`；命令的返回块设置每个玩家的半字节，而每个玩家用 bufferId 2 清除自己的半字节 [battle_util.c:185-201]。主控只有在 `gBattleControllerExecFlags == 0` 时才会推进。

需要超出 ack 的命令 [battle_controller_player.c]：

    CONTROLLER_GETMONDATA    -> EmitDataTransfer(BUFFER_B, size, data)   [player.c:1515]
    CONTROLLER_CHOOSEACTION  -> EmitTwoReturnValues(1, B_ACTION_*, 0)    [player.c:232-241]
    CONTROLLER_CHOOSEMOVE    -> EmitTwoReturnValues(1, 10, move | target << 8) [player.c:342]
    CONTROLLER_CHOOSEPOKEMON -> EmitChosenMonReturnValue(1, partyId, order)    [player.c:1316]
    CONTROLLER_OPENBAG       -> EmitOneReturnValue(1, itemId)            [player.c:1340]
    CONTROLLER_EXPUPDATE     -> EmitTwoReturnValues(1, RET_VALUE_LEVELED_UP, exp) [player.c:1051]
    CONTROLLER_ENDLINKBATTLE -> gBattleOutcome = payload[1], then ack     [player.c:2876]

`B_ACTION_USE_MOVE` 0, `USE_ITEM` 1, `SWITCH` 2, `RUN` 3 [battle.h:34]。第一个 `GETMONDATA` 以 0x58 字节的 `struct BattlePokemon` 应答 [pokemon.h:170]；重新计算的字段可能为零。battler 0 的 BUFFER_B 回复可能被跳过 [link_opponent.c:444]。链接战斗者可以在最高回合顺序下逃跑 [battle_main.c:3239, 3548-3560]。

### 反编译中不可见的两条规则

- 对战中状态路由的是块，而不是其大小：每个 ack 和短命令都是 16 字节、两个片段组成的记录。
- ack 绝不能超越它所确认的数据块的回显。迟到的回显会再次设置 exec 位 [battle_util.c:193]，游戏机便会永远等待 `gBattleControllerExecFlags == 0` [battle_script_commands.c:2041]。`HostTradeEngine._echo_owed` 会在子命令等待其镜像时保持新数据块，而 `rfu_leader.echo_blocks` 会让 ack 等待回显中 0..count-1 的每个片段。

### 节奏就是 RFU VBlank 预算

对战步骤大约需要一秒：命令块以每 `HOST_VBLANK_SECONDS = 1/59.727` 一个 RFU 时隙的速率跨越约二十帧，再加返程。连续的 `bufferA` 命令间隔中位数为 800 ms。

## 两台真机在空口上发送的内容

一台通过 Direct Corner 主持的火红以 25.5 帧/秒向叶绿发送，并以 161.8 帧/秒向宿主发送。它在 `application_data` 偏移 0x11 处以 ASCII 携带 Switch 个人资料名称，而不是训练家名称。

## 宿主 tick 频率与游戏机输出速率

`--tick-hz` 设置宿主的 RFU 时隙每秒数量；默认是每个 VBlank 一个。在 20 Hz 时，一次交换大约需要两倍时间，游戏机发送的数据报多出 80%。

# 线缆俱乐部竞技场

`frlg_trade_host.py --colosseum` 主持宝可梦中心 2F、第三个 NPC、竞技场、单打对战、JOIN。只有 `CB2_ReturnFromCableClubBattle` 会递增神秘卡片的 `battlesWon` [cable_club.c:792]。

`Task_StartActivity` 将 `ACTIVITY_BATTLE_SINGLE` 视同 `ACTIVITY_TRADE` [union_room.c:1903]，除了地图（(6, 8) 处的 `MAP_BATTLE_COLOSSEUM_2P`）和 `HealPlayerParty()`。与交换路径的差异：

1. `LINK_GROUP_SINGLE_BATTLE` 接受 `{ACTIVITY_BATTLE_SINGLE, 0xFF}` [src/data/union_room.h:398]；`build_colosseum_app_data` 只改那个字节。
2. 2P 座位脚本没有队伍检查 [data/scripts/cable_club.inc:576]。
3. `Task_StartWirelessCableClubBattle` case 2 会从双方主动发送裸的 28 字节 `struct LinkPlayer` [cable_club.c:701]，然后 case 4-6 在 `CB2_InitBattle` 之前加入待机。
4. 整个队伍都会参战 [union_room_battle.c:47]。

从 `CB2_InitBattle` 开始，它就是联盟房间对战，但没有 0x51 选择块。座位只需要 READY 键，且没有落座后的待机回合；游戏机停在 case 3，发送 `SEND_BLOCK_INIT` count 3 以及 `04 40 00 80 65 df | bb c8 ff 00 11 00 | 01 00 03 00 00 00`，其到达即完成入场。对战后宿主需要补上退出键 [overworld.c:2977]。

## 决定竞技场对战是否被计数的因素

认输算作另一方的胜利：`HandleAction_Run` 设置 `B_OUTCOME_WON` 并带有
`B_OUTCOME_LINK_BATTLE_RAN` [battle_main.c:4300]，在返回前清除 [:3734]。被计数的 id 是
伙伴的 28 字节记录训练家 ID [cable_club.c:794]，每个 id 各计一次，每项统计五次
[mystery_gift.c:630]。用三个 `--id` 值进行三次认输即可获得对战计数卡的伤药：

    save 0x3434:  0100 0000 0000 2300    battlesWon 1, lost 0, trades 0, icon 35 CARD_TYPE_LINK_STAT

## 两个主机端约束

- 关闭计时器在 `activity.tick()` 内运行，而 `HostSession.tick` 在 hole guard 持有期间会跳过它，
  因此停止确认的主机会使其停顿；一旦主机在确认退出后离开 LDN，运行时就会停止。
- 全零的 `easyChatProfile` 会在训练家卡片上显示“??? ???” [easy_chat.c:166-171]。一个词为
  `(group & 0x7F) << 9 | (index & 0x1FF)` [easy_chat.h:1089]，每张卡片四个词；用
  `EC_WORD_UNDEFINED` (0xFFFF) 填充。

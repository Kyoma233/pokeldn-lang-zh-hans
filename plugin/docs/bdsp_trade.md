---
title: The Union Room trade
parent: Brilliant Diamond and Shining Pearl
nav_order: 3
---

# 联盟房间交换

一次 BDSP 联盟房间交换通过五条消息在两台主机之间交换一只宝可梦，然后运行一个写入存档的安全阶段。接近与问候部分见[游戏协议](bdsp_protocol.md)。地址均来自 1.3.0 `main`。

## 消息序列

    NetDataTransitionData{transitionType: 18}     entering the trade
    NetDataTradeTranerData        32 B            who they are
    NetTradePokeData             328 B            the Pokemon
    NetDataTradePokeCheckOkData    1 B, value 1   "yours is fine"
    NetDataTradeReadyOkData        2 B            the last message before the exchange

每条消息都由客户端以自己的同类型消息应答。主机的 check-ok 始终为 1；它从不通过此消息拒绝宝可梦。

在本地无线中，主机只针对存档的非法标志检查玩家自己选择的宝可梦（[重复检测](#duplicate-detection)）。`SS_box_182`（"Un problème avec votre Pokémon rend
tout échange impossible."）会拒绝被标记的所选宝可梦。仅当设置 `UnionFrontDeskStateController.isGlobal` 时，服务器验证才会运行：`NetworkManager$$RequestValidateTrade` [0x02251cb0] 会以 0x148 字节的请求发送每个 `CoreParam`（`IlcaNetServerValidate.CheckRequestAutoAsync` [0x027318c0]）；应答中的 `ValidateResultID` 为 None、InvalidData、SignatureError 或 ProcessError，后两者会弹出错误对话框。`SS_box_181` 拒绝对方的已标记宝可梦。

## 交换状态机

`UnionTradeManager.currentState`（+0x80）为 `TradeFlowState {NONE 0, SELECT_WINDOW 1, SECURIY_TRADE 2, PLAY_DEMO 3, END 4}`。仅在 SELECT_WINDOW 中才会取走宝可梦。ready-ok（0x21）在 SELECT_WINDOW 中进入 `TradeSelectPokeModel$$ReciveReadyOk` [0x1c27d40]，在 SECURIY_TRADE 中进入 `TradeSecurityController$$ReciveState`，在其他状态则被丢弃。

当主机自己和对端的 `tradeState`（0x21 的第二个字节）都为 2（`WAIT`）时，主机离开 SELECT_WINDOW，然后发送自己 `tradeState` 为 0 的 0x21。只有对端的 0x21 能让它离开。

### 盒子阶段与重置一轮的消息

`BoxWindow.NetTradePhase`：

    None 0, WaitSave 1, PlayerSelecting 2, WaitSend 3, OtherPokeConfirm 4, WaitOtherDecide 5,
    LastConfirm 6, WaitTrading 7, Complete 8, WaitClose 9, CancelOther 10, Error 11

重置（`TradeSelectPokeModel$$ReciveReturnSelectPoke` [0x1c27f00]）会清空双方宝可梦和双方交换状态；从阶段 3 起，盒子回到阶段 2 并显示 `SS_box_588`（"L'autre joueur a
choisi d'annuler l'échange."）。收到 `NetDataReturnSelectData{1}` 时会以 `{0}` 应答。

| 来自对端的消息 | 盒子阶段 | 主机执行的操作 |
|---|---|---|
| check-ok (0x46) | 低于 6 | 记录对端的 check |
| check-ok (0x46) | 6 `LastConfirm` 或之后 | 重置 |
| ready-ok (0x21)，SELECT_WINDOW | 阶段 5 或以下 | 重置 |
| ready-ok (0x21)，SELECT_WINDOW | 阶段 6 或之后 | 记录对端状态；之后重复的副本被丢弃 |
| return-select (0x45)，任意值 | 任意阶段，PLAY_DEMO 之外 | 重置 |

锁存（+0x71，`<isLoadingBox>k__BackingField`；清除点 [0x1c342e4]，设置点 [0x1c3435c]）由 `Init`、`WaitBoxWindowComplete`、`Cancel`、`RecivePokeData` 和 `ReciveCancelData` 清除；其设置器 [0x1c33040] 没有调用者。重置会将 `UnionWork` +0x50（`boxState`）设为 6 `CANCEL_SELECT` [0x1c28030]，由 `BoxWindow$$UpdateNetworkTrade` [0x2121628] 在 [0x2121c64] 消费。

当玩家退出时（`onCancelSelect`、`b__54_5` 0x1c28620；发送点在 [0x1c286a4]），主机发送 `{1}` 并等待新的 `NetTradePokeData`；对端的 `{0}` 不会将其释放。

- 每条主机 check-ok 只应答一次；在 `LastConfirm` 之后被应答的重复副本会重置本轮。接收方会丢弃已经交付的可靠 id（`pokeldn.ldn.reliable5.Reassembler`）。
- 用 `45 0001 00` 应答 `45 0001 01`。在替换宝可梦发出后或主机重新选择后，绝不要发送 0x45：它会清除本轮。
- 在选择窗口中，主机最终确认前出现的 0x21 是取消。在主机可能回到选择窗口之前，停止安全阶段状态重复器。

## 安全阶段

`TradeStateModel` 拥有存档：

    NONE 0, INIT 1, WAIT 2, SEND_POKE 3, WAIT_POKE 4,
    SEND_READYOK 5, WAIT_READYOK 6, START_WRITE_SAVE 7, WRITEING_SAVE 8

在此阶段，对端的宝可梦消息只会触发下一步：主机使用玩家在全屏视图中确认的宝可梦，且在该确认之前 `WAIT_POKE` 永远不会结束。

### 由谁主导：更稀有的宝可梦

角色（PARENT 或 CHILD）在对端的宝可梦到达时，根据每个物种的稀有度设置（`TradeSecurityController$$CheckPokeRarity` [0x1c25060]）：

| rarity | species |
|---|---|
| 3 | 151, 251, 385, 386, 489, 490, 491, 492, 493（幻之宝可梦） |
| 2 | 150, 249, 250, 382, 383, 384, 483, 484, 487（盒子封面传说宝可梦） |
| 1 | 144, 145, 146, 243, 244, 245, 377-381, 480, 481, 482, 485, 486, 488 |
| 0 | 其他 |

`Dpr.SubContents.Utils$$GetPokeRarityNum` [0x1cbe560] 会遍历三个 `MonsNo[]` 列表（稀有度 3 在 0x1cbe614，2 在 0x1cbe698，1 在 0x1cbe71c，无稀有度 0x1cbe730），这些列表由 `Utils$$.cctor` [0x1cbe9a0] 从 `global-metadata.dat` 的 `0x666aa6`、`0x666b06`、`0x667c39`（静态字段 +0x78、+0x80、+0x88）填充。更稀有的一方为 PARENT；平局时发起招募方为 PARENT。用帝牙卢卡交换主机的梦幻时，主机为 PARENT。

`TradeParentStateModel$$StateProc` [0x1c23350]，表 0x3d80f2f，以及 `TradeSecurityController$$ReciveState` [0x1c24f10]，表 0x3d80f39，驱动该过程：

    2 WAIT            peer at WAIT                           -> 3
    3 SEND_POKE       send the Pokemon                       -> 4
    4 WAIT_POKE       peer Pokemon confirmed                 -> 5
    5 SEND_READYOK    PARENT sends its state; CHILD waits for a peer 5 or 6   -> 6
    6 WAIT_READYOK    one more peer message                  -> 7
    7 START_WRITE_SAVE, 8 WRITEING_SAVE

处于 SEND_READYOK 的 CHILD 主机会静默等待，因此回显 WAIT_POKE 的客户端会使其死锁。`room.mirror_trade_state` 用 SEND_READYOK 应答 WAIT_POKE，该做法在两种角色下都有效（`tests/test_bdsp_trade_states.py` 在随机延迟下对两个函数建模）。

每个可靠序列 id 只发送一条消息：同一 id 下的后续消息会被视为重传并被丢弃。

## 完成交换

先显示主机状态，再显示客户端应答：

    their READY-OK {tradeState 2}  ->  the client's READY-OK
    INIT          ->  WAIT
    WAIT          ->  WAIT
    SEND_POKE     ->  SEND_POKE, and its Pokemon
    WAIT_POKE     ->  WAIT_POKE
    SEND_READYOK  ->  SEND_READYOK
    WAIT_READYOK  ->  SEND_READYOK

之后主机写入存档、播放动画，并且只发送 `NetCharacterStateData`。客户端每秒重复一次自己的状态，直到主机的 SEND_READYOK（`room.repeats_trade_state`）；之后出现的 0x21 会落到下一个选择窗口并重置本轮。端点不得在此窗口离开：掉线会让主机落在 `FirstSave` 与 `SecondSave` 之间（[断线惩罚](#the-disconnect-penalty)）。

动画在 `tradeState` 6 后约 2.7 秒开始，收到的宝可梦约在 18.6 秒出现，玩家约在 29 秒恢复控制。完成交换不会以任何消息结束；下一轮以主机的下一条 `NetTradePokeData` 开始。交换可以在两种角色下于同一个关联中连续进行。

## 宝可梦

`NetTradePokeData` 携带 328 字节，是[剑／盾页面](swsh_protocol.md#the-pk8)上格式的加密 PB8（`pokeldn/gen8.py`、`pokeldn/bdsp/pokemon.py`）。0x06 处的校验和无法检测错误的块顺序。

`NetDataTradeTranerData`（[组帧](bdsp_protocol.md#framing)）：

    0x00  26  tranerName, UTF-16LE, NUL-terminated
    0x1a   4  tranerId, the full 32-bit id, secret id in its high half
    0x1e   1  cassetVersion, the save's version (49)
    0x1f   1  langId, the save's language (3)

主机在任何宝可梦之前发送它；为接收玩家制作的礼物会读取它（`room.traner_trainer`，[为接收玩家制作](gift_simulated.md#made-for-the-receiving-player)）。它不携带性别。交换屏幕用其命名对方；问候语使用 Pia 玩家名称（[协议页](bdsp_protocol.md#the-name-in-the-greeting)）。名称结束符后的 10 个字节是堆残留；`room.build_trade_traner` 会复制主机自己的数据。

提供的是一只真实宝可梦，仅修改了指定字段（`pokemon.build_from`）。

## 主机对收到的宝可梦做了什么

`TradeStateModel$$ReplacePoke` [0x1c29120] 将宝可梦的 OT 性别、32 位 id 和 OT 名称与接收方存档进行比较（`CoreParam$$UpdateOwnerInfo` [0x2495920]）：

| 比较 | 效果 |
|---|---|
| 三项全部匹配 | 清除 handler 标志；当名称不同于物种名时设置 `IsNicknamed`（0x08F 第 7 位） |
| 否则 | 从存档设置 handler：名称 0x0A8，性别 0xC2，语言 0x0C3，`CurrentHandler` 0x0C4 = 1，亲密度 0x0C8 = 物种基础值，回忆归零 |

随后更新校验和。`ot_name` 和 0xC6 不会被修改。GTS、游戏内交换和神秘礼物以同样方式写入 handler。游戏中不包含 Pokémon HOME 代码。

### 重复检测

`PokeDupeChecker`（1.3.0）会给重复宝可梦打上标志：解密后 PB8 字节 0x52 的第 0 位，即 PKHeX 的 `PB8.IsDprIllegal`。被标记的宝可梦无法用于交换，且该标志永远不会被清除。

检查（`UpdateIllegalFlagAll` [`0x01de5860`]）在存档加载时以及交换盒中每次选取时，按顺序遍历队伍、1 到 40 号盒子和寄放屋；收到交换时不会运行。它涵盖晶灿钻石／明亮珍珠中非蛋、非游戏内交换的宝可梦。当后一个副本与先前某只的以下所有字段都匹配时，会将其标记：

| 字段 | 访问器 | PB8 偏移 |
|---|---|---|
| 加密常数 | `GetPersonalRnd` | 0x00 |
| PID | `GetColorRnd` | 0x1C |
| 训练家 id（TID16、SID16） | `GetID` | 0x0C |
| 性格 | `GetSeikaku` | 0x20 |
| 六项个体值 | `GetTalentHp` .. | 0x8C |

比较：`IsDuplicatedPokemonParam` [`0x01de62f0`]，每只宝可梦的 `CheckDuplicate` [`0x01de59d0`]；游戏内交换测试 `IsLocalKoukanPokemonParam` [`0x01de66d0`]；极限特训检查 `UpdateIllegalSpecialTraining` [`0x01de6830`]；交换盒调用 [`0x01c28310`]；标志设置器 `CoreDataBlockA.set_dpr_illegal_flag` `0x027bb040`。

铁面忍者（291）和脱壳忍者（292）这一对永远不会被视为重复。等级 99 或以下且设置了任意极限特训位的 BDSP 宝可梦也会被标记。

绝不要提供加密常数、PID、训练家 id、性格和个体值都与接收方存档中某只宝可梦完全匹配的 BDSP 记录。`bin/bdsp_host.py --fresh-pid` 会生成新的加密常数和 PID，同时保留异色状态。

## 断线惩罚

端点若在 `FirstSave`（惩罚计数器 30，存储时间）与 `SecondSave`（计数器 0）之间掉线，会使主机拒绝新的本地交换，并显示 "vous ne pouvez pas faire d'echange en
reseau pour le moment"（`UnionFrontDeskStateController$$CheckPenarty` 0x1fcc400）。出现惩罚意味着主机已写入存档。

惩罚时钟（`UnionWork$$CheckDateTime` [0x1dd3e30]，`SetPenartyTime` [0x1dd32d0]；`FirstSave` 0x1cd4fc0，`SecondSave` 0x1cd5030）采用未加权和 `Year + Month + Day + Hour + Minute + Second`，一旦它超过存储的和 30，惩罚就清除。当分钟或小时回绕时，该和会下降 58，所以在某一小时较晚时触发的惩罚可能持续到第二天或更久。

绝不要通过更改主机时钟或系统设置来清除惩罚：BDSP 会检测到更改，并将基于时间的功能锁定一天。把时钟拨回会恢复惩罚；只有 `SecondSave` 会将计数器清零。

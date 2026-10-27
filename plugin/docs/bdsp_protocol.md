---
title: The game protocol
parent: Brilliant Diamond and Shining Pearl
nav_order: 2
---

# 游戏协议

BDSP 在其 Pia 负载中携载一种类型化消息协议。`TeamLumi/opendpr` 中解编译的 C# 复现版 `Dpr.NetworkUtils.NetDataParser` 列出了每一条消息：一个以一个字节 `DataID` 环绕普通结构体 `T` 的 `ANetData<T>`。标记为 1.3.0 main 的地址位于 Shining Pearl 的镜像中。

## 帧结构

    0x0  1  数据 ID
    0x1  2  负载长度，大端序
    0x3  .  结构体，小端序，紧凑排列

`JoinData`（`byte, byte, byte, short, Vector3`）在线上占 17 字节。

`NetDataParser` 注册了 65 条消息，全部位于 `pokeldn/bdsp/netdata.py` 中（由 `scripts/gen_bdsp_netdata.py` 生成）。源码固定了 53 个布局；十二个携带 C# 字符串、数组或列表（`netdata.OPAQUE`），二进制文件也固定了它们：负载是已封送的结构体（`ANetData<T>.ConvertStructToBytes` [main.bin 0x27bb0e0]），字符串和数组作为固定大小的字段，由 `Il2CppTypeDefinitionSizes` 和 `fieldMarshaledSizes` 确定大小，由 `CodeRegistration.interopData` 中的 `marshalToNative` 写入 [1.3.0 main 0x4acd0c8]。捕获的负载匹配（`room.NATIVE_SIZES`，`room.MEASURED`）。

| id | payload | bytes | layout |
|---|---|---|---|
| 0x02 | `PosListData` | 72 | 12 x `PosData` (ushort posX, ushort posZ, short rotY) |
| 0x13 | `TradePokeData` | 328 | 一个加密的 PB8，存储大小 |
| 0x14 | `NetRecodeData` | 694 | `RECORD` 120, `RANDOM_SEED` 132, `TvRecodeData` 204, 4 x `TV_STR_DATA` 36, `RECORD_HEAD` 48, 十个 int, 六个字节 |
| 0x15 | `BallDecoData` | 143 | affixSealCount, Is3DEditMode, IsAppliedTemplate, 然后是 20 x `SealParam{short x, y, z; byte id}` |
| 0x18, 0x54 | `UgSecretBase` | 616 | short zoneID, posX, posY; byte direction, expansionStatus; int goodCount; 30 x `UgStoneStatue` 20; bool isEnable (4) |
| 0x22 | `StanbyListData` | 20 | 5 x `StandbyData` (isAddPlayer, hostIndex, myIndex, langId) |
| 0x24 | `TradeTranerData` | 32 | 13 个 UTF-16 字符, uint tranerId, byte cassetVersion, byte langId |
| 0x29, 0x61 | `UgStationID_to_DigFossilIDList` | 8 | `byte DigFossilIDs[8]`, 0..7 的一个排列 |
| 0x38 | `BattleMatchingPokeData` | 481 | 一个 328 字节的 PB8, 20 x `SealParam` 7, uint attachPokemonId, uint attachPersonalRnd, byte index, num, is3DEditMode, isAppliedTemplate, affixSealCount |
| 0x42 | `NetPlayerName` | 28 | 13 个 UTF-16 字符, byte genderid, byte languageId |

`SendStandbyPlayerData` [1.3.0 main 0x01e52fa0] 从 `unionMatchWaitDataList` 填充 0x22；空列表是二十个零字节。一个站点通过 `NetDataStandbyWaitData`（0x59，相同的四个字节，`isAddPlayer = 0` 移除它）添加自身：在 `59 0004 01 00 01 03` 之后，下一个 0x22 是 `22 0014 01 00 01 03` 和十六个零。屏幕不会改变。

封送程序不会清除其缓冲区：一个固定字段会携带其值之外的堆残留（参见[交易页面](bdsp_trade.md)）。

## 曾经在空中出现的消息

一个孤身一人的控制台发送 `NetJoinData`（0x01，可靠，17 字节）、`NetPosData`（0x02，不可靠，72 字节）、`NetRequestData`（0x12，1 字节）和 `NetDataIsMatchWaitData`（0x23，可靠，1 字节）。在请求时，它还会发送 0x09 和 0x22；在活动时，0x14 和 0x15。交易消息在[交易页面](bdsp_trade.md)上。一个 0x23 可以位于存在字节 0x00 之后；一次行走必须把 0x00 当作一条消息处理（参见[消息帧结构](pia.md#message-framing)）。

## 控制台重复发送的消息

`NetJoinData` 就是整个 `JoinData`：

| offset | size | field |
|---|---|---|
| 0x00 | 1 | `avatarId` ([The model](#the-model)) |
| 0x01 | 1 | `colorId`, 0 |
| 0x02 | 1 | `cassetVersion`, 0x31 |
| 0x03 | 2 | `InitRotY`, 度，小端序，未对齐 |
| 0x05 | 12 | `InitPos`, 三个小端序浮点数 x, y, z |

`NetRequestData` 是一个字节，请求的 ID。控制台重复请求 0x23，直到客户端确认其可靠窗口；并在创建角色时请求 `NetCharacterStateData`（0x04）：一次 0x04 请求意味着一个角色已存在，`bin/bdsp_connect.py` 将其打印为判定结果。

`UnionRoomManager$$SetNetData` [1.3.0 main 0x01e50700] 回应六个 ID 的请求并忽略其余：

| requested | the console sends |
|---|---|
| 0x01 `NetJoinData` | its join record |
| 0x04 `NetCharacterStateData` | its character state |
| 0x09 `NetDataBattleTypeData` | its battle rule |
| 0x13 `NetTradePokeData` | its offered Pokémon; nothing when none is selected |
| 0x22 `NetDataStandbyWaitListData` | its standby list |
| 0x23 `NetDataIsMatchWaitData` | whether it waits to be matched |

回应在 30 到 130 毫秒内通过可靠流发送给一个房间内有角色的站点。

### 压缩

可靠标头标志 0x10 标记整个游戏消息（含标头）的 zlib 流。`ReliableSlidingWindow` 的推送 [1.3.0 main `0x15a10d0`] 在窗口的开关 (+0x7ac)开启时进行 deflate，并在结果未变小时发送原始数据 (`0x159a5b0`)。这些字节等于 Python 的 `zlib.compressobj(5, zlib.DEFLATED, 12, 5)`，先同步刷新再完成。加入消息发送原始数据；记录（0x14）、胶囊（0x15）和全零的 0x22 会变小。`bin/bdsp_connect.py` 在标志位上进行 inflate。

### 其他不透明消息的发送者

| id | class | sent by |
|---|---|---|
| 0x14 | `NetDataRecodeData` | `RecodeMatching$$SendRecodeData`, `UnionStateController$$SendRecodeData` |
| 0x15 | `NetDataAttachSealNetData` | `BallDecoMatching$$SendBallDecoData` |
| 0x18 | `NetSecretBaseData` | `UgNetworkManager$$SendMySecretBaseData`; on request |
| 0x61 | `NetDigTableData` | on request |
| 0x38 | `NetDataBattleMatchingSelectPokemon` | `BattleMatchingManager$$SendSelectPokemonData` |
| 0x42 | `NetPlayerNameData` | `UgNetworkManager$$SendOnJoinNewPlayer`, `SendPlayerNameData` |
| 0x54 | `NetSecretBaseUpdate` | no reliable sender |

### 不可靠流

| bytes | message |
|---|---|
| `04 0002 00 00` | `NetCharacterStateData{NONE, 0}`, every two seconds |
| `12 0001 04` | `NetRequestData` for 0x04 |
| `02 0048 <72 B>` | `NetPosData` while the avatar walks |

`room.build_state()` 和 `room.build_match_wait(False)` 构建状态和 0x23 的回答。控制台以每秒五次的频率重传可靠消息，直到收到确认；确认序号超过其最后一个序号的两个时将被忽略。

## 发送游戏会响应的消息

可靠序号 ID 与控制台的发送共享；低于已确认 ID 的消息将被静默丢弃。在每次发送之前立即读取 ID。一台零售版的 Shining Pearl 会响应其自身最后一条消息 ID 之下的回复并丢弃更低 ID 的消息：在其状态消息（27）和宝可梦（28）之后，一个 ID 为 27 的返回宝可梦会被确认但从未检查。一个在已确认序号上的加入会被响应；`--room-pattern fixed` 在第一个 0x04 请求处停止，`--join-wait` 间隔为秒数（默认 1.0）。

`UnionOpcManager` 在每次加入时调用 `CreateCharacter(joinData)`：四十次加入就是四十次到达。一个没有会话支持的角色会跟随玩家穿过地图，直到游戏重启。`OpcManager$$RemoveCharacter` [0x02279ee4] 接受一个站点索引。

## 角色记录

`OpcManager.CharaData` 是 `{int stationIndex, string assetName, int colorId, int avatarId, int sexId, int cassetVersion}`，以站点为键。

### 模型

    NetJoinData.avatarId  ->  CreateCharaData  ->  CharaData.avatarId
                          ->  UnionCharacterTable.SheetSheet1{ID, AssetName}
                          ->  OpLoadCharacter("persons/field/" + assetName)

`CreateCharaData` [1.3.0 main 0x022796b0] 设置 `sexId = avatarId > 7 && avatarId != 16`：8 到 15 为女孩，0 到 7 和 16 为男孩。8 是一个女孩，0 是一个戴蓝帽的男孩（`--join-avatar N`）。

一个控制台自己的加入携带工作 360（`GetAvaterId` [0x01e54030]）。一个新存档持有 0。外观计数器（`ev_union_character_select_*`）存储 16 或 1 到 7 给男孩，8 到 15 给女孩；否则，当工作 360 为 0 时，`ev_traner_other_see_random` 将其设为 1 + 随机值小于 16，任一性别。因此，加入仅在计数器使用后才命名存档的性别。

`NetDataTranerCardData`（0x05，75 字节）在联盟房间中不绘制任何内容。

### 状态字节

`StateData` 是 `{byte state, byte isRecruiment}`，`state` 是 `OpcState.OnlineState`：

| value | name | value | name |
|---|---|---|---|
| 0 | `NONE` | 5 | `RECRUITMENT_RECORD` |
| 1 | `DIG_FOSILL` | 6 | `RECRUITMENT_GREETINGS` |
| 2 | `SECRETBASE_ACTION` | 7 | `RECRUITMENT_BALL_DECORATION` |
| 3 | `RECRUITMENT_BATTLE` | 8 | `COMMUNICATE` |
| 4 | `RECRUITMENT_TRADE` | | |

17 到 21 是 `NOW_*` 状态（参见[talkstate and the value that crashes the game](#talkstate-and-the-value-that-crashes-the-game)）。`RECRUITMENT_*` 值会显示一个对话气泡：`StateData{RECRUITMENT_TRADE, 1}` 显示一个交易气泡。

收到的 0x04 抵达 `UnionOpcController$$SetNetData` [1.3.0 main 0x01e48c50]（当站点没有角色时丢弃），它设置状态，根据 `isRecruiment` 选择主持人或普通表情，并为非零状态播放动画 0。远程角色的状态仅在其自身站点的 0x04 或移除时改变。在角色的 `Start` 运行之前，设置器会丢弃该值 [0x02277c50]，并且 0x04 请求会在此之前发出 [0x01e49854]：每隔两秒重复一次状态，就像控制台所做的那样。

`OnlinePlayerCharacter$$IsCanTalkState` [0x02277af0]：状态 1、3 到 8 和 17 到 21 可以对话。

### 行走

控制台自己的 `NetPosData` 每隔 0.410 秒发送一次，跨度为 0.935 单位（`room.POS_PERIOD`，`room.POS_STRIDE`）。`pos = (-posX * 0.05, posZ * 0.05)`。远程角色会与墙壁碰撞；玩家不会与它碰撞。`--room-walk-steps 8` 停留在房间内；交易不需要行走（`--room-walk-steps 0`，交易路径的默认值）。

## 被对话

玩家站起表情动作时保持静止，状态非零时 A 按键无效。交易表情动作是 `NetCharacterStateData{4, 1}`，由 `{0, 0}` 清除。门控在 `isRecruiment` 上：状态 18 表示已在交易中的控制台。

接近操作是 `NetDataTalkReserveData`（0x63），`63 00 01 00`（`bin/bdsp_connect.py --initiate-talk`；`bin/bdsp_host.py --approach-delay`）。控制台接近客户端：

    cli ->  64 0003 00 01 04      NetDataTalkReserveResultData{IsCanTalk, IsRecruitment, emoticonStateType}
    con ->  06 0005 00 01000000   NetDataTalkData{talkOpcSexId: 0, talkState: GREETING}
    con ->  10 0002 01 04         NetDataTalkCancelEndData{IsRecruitment: 1, emoticonStateType: 4}

若无 0x64，玩家保持冻结。`IsCanTalk` 为 0 时运行问候并停留在“1 秒钟！”；为 1 时显示“抱歉，我有其他计划”。释放站点会释放停留的问候。

### 控制台接近

`UnionRoomManager$$MyUpdate` [1.3.0 main 0x01e49fb0] 仅在玩家状态为 0、无对话或窗口打开且玩家位于所有 `EnterCollision` 外部时处理 A 按键。在 10.0 单位范围内最近的字符：

| 字符的状态 | A 按键作用 |
|---|---|
| 0, 2, 9 至 16 | 无作用 |
| 8, 17 至 21 | `StartTalk(opc, 0, 0, 0)` [0x01e4c2d0] |
| 4 | `CheckErrorMessageTrade`，然后执行最后一行 |
| 7 | `CheckBallDeco`，然后执行最后一行 |
| 1, 3, 5, 6 | 发送 0x63，存储状态于 `nowTalkReserveState` (+0x188)，`CreateSelectStateModel(state, 1)` |

控制台读取 0x64 [0x01e50dec] 时，除非 `emoticonStateType` 等于 `nowTalkReserveState`，否则发送 `NetDataTalkCancelEndData{0, 0}`；否则清除状态。因此，广告为 `{4, 1}` 的字符会以 `64 0003 00 01 04` 回应，且每次 0x63 仅一次，忽略 retransmitted 副本。

以控制台作为对话方时，客户端角色为招募者。招募者的“是”是 `NetDataTransitionData{18, 0}`，即 `07 0002 12 00`（参见[交易页面](bdsp_trade.md#the-message-sequence)）。在 0x64 之后发送，它在对话控制台上启动交易，无需其玩家按 A（`SwitchTransitionMessage` [0x01e53bf0] -> `TransitionTradePoke` [0x01e5c1c0]）：控制台发送其 0x24 并打开交易框。`SwitchTransitionMessage` 读取类型模型时不进行空指针检查；向自进入以来未在交易招募者上按 A 的控制台发送 0x07 会导致空指针解引用。

### 问候中的名称

问候通过站点的 Pia 玩家名称命名字符（`NetworkManager$$GetGamerData` [1.3.0 main 0x02250e50]），从 PlayerInfo 中以 UTF-8 解码。`Utils$$CheckNGTrainerName` [0x01cbdc30] 在名称为空（由 `CheckNgWords` 标记）或 UTF-16 单位长度超过语言限制时，替换为版本名称：

| `lang` | 限制 |
|---|---|
| 1, 8, 9, 10 | 6 |
| 其他任何正值 | 12 |
| 0 或以下 | UI 当前语言决定 |

PlayerInfo 长 195 字节（解析器 [0x0154f044..0x0154f5e0]）：

| 偏移 | 字段 |
|---|---|
| 0x00 | 名称编码：2 表示 20 个 UTF-16 单位，其他情况为 80 字节 |
| 0x01..0x50 | 名称 |
| 0x51 | 第二个字符串的编码 |
| 0x52..0x79 | 第二个字符串，40 字节 |
| 0x7A | 语言，为 `MsgLangId` |
| 0x7B..0xBA | 64 字节 |
| 0xBB..0xC2 | u64 |

    MsgLangId  JPN 1, USA 2, FRA 3, ITA 4, DEU 5, ESP 7, KOR 8, SCH 9, TCH 10

控制台在 0x7A 发送其游戏文本语言（存档 `CONFIG.msg_lang_id`，`get_msgLangID` [0x0237e100]），在 0x01..0x50 发送其检查后的名称，编码为 1。站点协议的写入器将其放置于 [0x01550e98]。`bin/bdsp_connect.py` 和 `bin/bdsp_host.py` 通过 `pokeldn/bdsp/host.py` 中的 `player_info` 构建 PlayerInfo，并发送 `--language`，默认为 3；桌面应用传递其训练家语言。在语言 3 下，11 字符名称完整显示。在语言 1 下，一台零售版法语闪晶珍珠将 11 字符名称显示为“Perlo.”，问候为“Konnichiwa!”。

替换依赖于被对话字符的 `NetJoinData` 字节 2：`dp_characters` 中的标签 247 对应 0x31，标签 206 对应其他情况，加一个句号：

| bundle | 0x31（闪晶珍珠） | 其他情况 |
|---|---|---|
| english | `Pearl.` | `Diamond.` |
| french | `Perlo.` | `Diamant.` |
| german | `Perl.` | `Diamant.` |
| italian | `Perl.` | `Diaman.` |
| spanish | `Perla.` | `Diamant.` |
| jpn, jpn_kanji | `パール。` | `ダイヤ。` |
| korean | `펄.` | `다이아몬드.` |
| simp_chinese | `帕尔.` | `戴亚.` |
| trad_chinese | `帕爾.` | `戴亞.` |

### talkState 以及会导致游戏崩溃的值

`TalkState` 为 `{CHECK = 0, GREETING = 1, NONE = 2}`。CHECK 状态会使 `UnionStateController$$SwitchSpokenStateMine` 在无空指针保护的情况下解引用 `msgWindow`（0x1fd5ec0）；站立时有表情动作的玩家没有该窗口，因此 CHECK 会导致游戏崩溃。`pokeldn/bdsp/room.py` 拒绝发送它。

`NetDataTransitionData{transitionType, isRecruitment}`（0x07）将停留的问候推进为活动。它作为尾调用发送，对仅扫描 BL 的调用者不可见（参见[查找调用者](switch_re.md#finding-callers)）。`SwitchTransition` [1.3.0 main 0x01e5ba70] 对其分发：

| transitionType | 活动 | 通过以下进入 | `UnionStateController` + 的模型 |
|---|---|---|---|
| 3, 17 | battle | `TransitionBattle` | 0x38 或 0x40，由 `isRecruitment` 决定 |
| 4, 18 | trade | `TransitionTradePoke` | 0x50 |
| 5, 19 | record mixing | `RecodeMatching$$Open` | 0x60 |
| 6, 20 | trainer card | `TransitionShowTrainerCard` | 0x70 |
| 7, 21 | ball capsules | `BallDecoMatching$$Open` | 0x80 |
| 8 至 16 | none | | |

`RecodeMatching$$Open` 和 `BallDecoMatching$$Open` 立即发送控制台自己的记录并等待；仅伙伴的写入会写入存档。

### 记录混合

控制台以“Échanger des données”（状态 5）招募。在其玩家按“是”后发送 `NetDataTransitionData{5, 0}`，然后发送其 694 字节的 `NetDataRecodeData`（zlib），并在状态 19 等待。若无回应，约 44 秒后返回房间。`room.parse` 返回记录的头部作为 `recode`：

    RECORD.record[30]        由 RECORD_ID 索引的 30 个 uint 计数器
    RANDOM_SEED              group_name（16 字符）、name（32 字符）、int sex、int region_code、
                             ulong seed、ulong random、long time_stmp（FILETIME）、int user_id
    TvRecodeData             五个电视记录，每个为 `bool isEmpty`（4 字节）、ints、一个 TV_STR_DATA
    4 x TV_STR_DATA          {16 字符 value、byte language、genderId、两个保留字段}
    RECORD_HEAD              13 字符用户名、int language、byte sex、int body_type、uint uniqueID
    ten ints、six bytes      每-TV 分支值、myVersion（0x31）、五个 *IsNotEmpty 标志

未写入的字段保存堆指针。`RECORD_HEAD.sex` 和 `RANDOM_SEED.sex` 可能不一致。

### 对战阶梯

对战（招募时状态 3）运行一个阶梯；招募控制台在每个台阶等待加入者：

| 加入者发送 | 控制台执行 |
|---|---|
| `NetDataTalkData{GREETING}` | 显示“Un combat ? OK !”并等待 |
| `NetDataSelectData{0}`（0x08） | 显示“... est en train de choisir quoi faire...”并等待 |
| `NetDataBattleTypeData{0}`（0x09，Single） | 询问其玩家；玩家按“是”后发送 `NetDataTransitionData{17, 0}` 并打开大厅 |
| `NetDataBattleMatchingJoin`（0x30） `{uint id, byte stationIndex, index, language, colorId, avatarId, sexId, cassetVersion}` | 用自己的加入回应并转发加入者的加入；加入者出现在第二个槽位 |
| `NetDataBattleMatchingReady`（0x32，空） | `NetDataBattleMatchingState{0, 6}`（0x33，`SelectBattleTeam`） |
| 无 | 在队伍选择后，六次 0x38，然后“en attente d'autres personnes” |

每个 0x38 包含一个加密的 PB8（按顺序选择的队伍），残留密封通过 `affixSealCount` 0、`index` 0 至 5、`num` 6。未找到对 0x30 `id` 的检查。`MatchingState`：None 0、Initialize 1、Load 2、RecruitmentMember 3、SelectTeamMember 4、SelectRule 5、SelectBattleTeam 6、SelectPokemon 7、GoBattle 8、Result 9、Resume 10、Closing 11、LeavedOtherMembers 12。

`NetDataSelectData`（0x08）为 `{byte index}`；其接收器 [0x01e52a30] 忽略该索引并将 `UnionStateController+0x38`（对战招募模型）驱动为 `BATTLE_RULE_SELECT_WAIT`，无论何种对话处于打开状态，且不进行空指针检查。该模型仅在玩家招募对战时设置，且每次访问联盟房间时在 `UnionRoomManager` 被销毁时初始化为 null（`NetUseManager.OnZoneChange` [0x026cfef0]）。由此推断，向自本次访问以来未招募过对战的控制台发送 0x08 会写入地址 0x18 [0x023e2604]。一台零售版闪晶珍珠在交易框和训练家卡交换时均确认收到了 `08 00 01 00`，但屏幕未发生变化；是否执行了接收器逻辑未知。除非控制台自身的 0x04 显示状态 3 且 `isRecruiment` 为 1，否则切勿发送 0x08。

### 大地深处

大地深处广告相同的 `local_communication_id`，位于场景 id 12608 下；相同的会话行关联，但无加入记录（`--room-walk 0`）。在站点到达时，`UgNetworkManager` 发送：

| id | 类 | 字节 | 内容 |
|---|---|---|---|
| 0x17 | `NetZoneData` | 16 | `Vector3 pos`、`int zoneID` |
| 0x42 | `NetPlayerNameData` | 28 | 13 个 UTF-16 字符、byte genderid、byte languageId |
| 0x50 | `NetKousekiCount` | 4 | `int Value` |
| 0x41 | `NetSecretBaseInfo` | 16 | 在秘密基地内替代 0x17：`Vector3 pos`、`int zoneID` 入口 |

命名了玩家所在区域的 `NetUgJoinData`（0x16，18 字节：`byte avatarId, colorId; short zoneID, InitRotY; Vector3 InitPos`）会在玩家旁放置一个角色；控制台请求其 0x04 和 `NetNaminoriData`（0x55），并每 0.41 秒发送 `NetPosData`（`--ug-join --room-walk-steps N`）。

`UgNetworkManager$$OnReceiveRequestData` [1.3.0 main 0x01f7c050] 在控制台的窗口已携带内容后，回应对 0x01、0x04、0x18、0x19、0x54、0x55 和 0x61 的请求：

| 请求内容 | 字节 | 内容 |
|---|---|---|
| 0x18, 0x54 | 616 | 玩家自己的 `UgSecretBase`；当其 `zoneID` 为 0 时无内容 |
| 0x61 `NetDigTableData` | 8 | 挖掘化石表，即 0..7 的排列，仅当就绪时发送 |

非主机站点在加入时请求 0x61。`OnReceiveDigTableData` [0x01f7dad0] 采用第一个到达的 0x61，当其表标志 (+0xA8) 为 0 时，从任意站点且未检查；重建挖掘点并设置标志；后续到达的忽略。`CreateDigPoints` 通过 `MyStationIndex` 索引表并查找该组 ID，无空指针检查：仅发送 0..7 的排列，否则较大字节会导致控制台崩溃。每个 `UgFieldManager` 会话构建新的 `UgNetworkManager`，因此每个都会重新采用一张表。0x29 `NetDigGroupIdData` 没有发送端和接收分支。

`bin/bdsp_connect.py --inject-file PATH` 可靠发送文件中每一行新的 `ID:HEX`。

### 球胶囊

控制台以“Déco Capsule”（状态 7）招募。它发送 `NetDataTransitionData{7, 0}`，进入状态 21，并发送其 143 字节的 `NetDataAttachSealNetData`（zlib）。若无回应，约 45 秒后返回房间。以 143 字节回应（`bin/bdsp_connect.py --answer-with 0x15:FILE`），它会应用这些并返回房间。从自己的任务发送回应：从接收器内部发送，等待的 ack 永远不会被读取。

`BallDecoMatching$$ReceiveBallDecoData`（`0x021ca5e0`）在第一个空槽中写入无密封的内容，或当所有槽均有密封时写入无内容。`BallDecoWork$$CopyTradeCapsuleData`（`0x01f23eb0`）清除槽并放置每个密封于 `(x, y, z) / 100`，当存档中有库存时使用并消费，否则丢弃。当所有密封均放置时，关闭消息为 `DLP_net_union_room_090`，否则为 `_114`。计数超过 20 或密封 ID 超过等于 200 会抛出异常。

位置是球胶囊半径的百分之一。3D 模式绘制每个密封所在的位置。2D 模式仅在网格单元的 `BallDecoWork$$Convert2DPosition`（`0x01f24da0`）绘制密封：半径 1，行和列在正面（+z）间隔 28 度，背面间隔 25 度，每个分量四舍五入到 0.01。网格（正面和背面）是 7×7 方格减去 `(|x|, |y|)` 在 `{(3, 2), (2, 3), (3, 3)}` 内的部分（`Capsule2DViewController$$Initialize` `0x01e909b0`，在零售版 1280×720 缩放下）：

    row  3   columns -1..1
    row  2   columns -2..2
    row  1   columns -3..3
    row  0   columns -3..3
    row -1   columns -3..3
    row -2   columns -2..2
    row -3   columns -1..1

离网格的 2D 设计会填充一个标记为已装饰的槽，但绘制无内容。

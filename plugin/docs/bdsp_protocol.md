---
title: The game protocol
parent: Brilliant Diamond and Shining Pearl
nav_order: 2
---

# 游戏协议

《晶灿钻石／明亮珍珠》（BDSP）在其 Pia 载荷中承载一套带类型的消息协议。`TeamLumi/opendpr`（一个反编译 C# 重建项目）中的 `Dpr.NetworkUtils.NetDataParser` 列出了每条消息：一个 `ANetData<T>`，带一字节 `DataID`，包裹普通结构体 `T`。标记为 1.3.0 main 的地址来自《明亮珍珠》映像。

## 帧结构

    0x0  1  data id
    0x1  2  payload length, big-endian
    0x3  .  the struct, little-endian, packed

`JoinData`（`byte, byte, byte, short, Vector3`）在线路上为 17 字节。

`NetDataParser` 注册了 65 条消息，全部在 `pokeldn/bdsp/netdata.py`（由 `scripts/gen_bdsp_netdata.py` 生成）。源代码确定了 53 种布局；十二种携带 C# 字符串、数组或列表（`netdata.OPAQUE`），由二进制确定其布局：载荷就是被封送的结构体（`ANetData<T>.ConvertStructToBytes` [main.bin 0x27bb0e0]），字符串和数组作为定长字段，大小由 `Il2CppTypeDefinitionSizes` 和 `fieldMarshaledSizes` 决定，并由 `CodeRegistration.interopData` 中的 `marshalToNative` 写入 [1.3.0 main 0x4acd0c8]。捕获到的载荷与之匹配（`room.NATIVE_SIZES`、`room.MEASURED`）。

| id | 载荷 | 字节数 | 布局 |
|---|---|---|---|
| 0x02 | `PosListData` | 72 | 12 x `PosData` (ushort posX, ushort posZ, short rotY) |
| 0x13 | `TradePokeData` | 328 | one encrypted PB8 at stored size |
| 0x14 | `NetRecodeData` | 694 | `RECORD` 120, `RANDOM_SEED` 132, `TvRecodeData` 204, 4 x `TV_STR_DATA` 36, `RECORD_HEAD` 48, ten ints, six bytes |
| 0x15 | `BallDecoData` | 143 | affixSealCount, Is3DEditMode, IsAppliedTemplate, then 20 x `SealParam{short x, y, z; byte id}` |
| 0x18, 0x54 | `UgSecretBase` | 616 | short zoneID, posX, posY; byte direction, expansionStatus; int goodCount; 30 x `UgStoneStatue` 20; bool isEnable (4) |
| 0x22 | `StanbyListData` | 20 | 5 x `StandbyData` (isAddPlayer, hostIndex, myIndex, langId) |
| 0x24 | `TradeTranerData` | 32 | 13 UTF-16 chars, uint tranerId, byte cassetVersion, byte langId |
| 0x29, 0x61 | `UgStationID_to_DigFossilIDList` | 8 | `byte DigFossilIDs[8]`, a permutation of 0..7 |
| 0x38 | `BattleMatchingPokeData` | 481 | a 328-byte PB8, 20 x `SealParam` 7, uint attachPokemonId, uint attachPersonalRnd, byte index, num, is3DEditMode, isAppliedTemplate, affixSealCount |
| 0x42 | `NetPlayerName` | 28 | 13 UTF-16 chars, byte genderid, byte languageId |

`SendStandbyPlayerData` [1.3.0 main 0x01e52fa0] 从 `unionMatchWaitDataList` 填充 0x22；空列表为二十个零字节。站点用 `NetDataStandbyWaitData`（0x59，同样四个字节，`isAddPlayer = 0` 表示移除）将自己加入：在 `59 0004 01 00 01 03` 之后，接下来的 0x22 是 `22 0014 01 00 01 03` 加十六个零。画面不会改变。

封送器不会清空缓冲区：定长字段会携带其值之后的堆残留数据（[交换页面](bdsp_trade.md)）。

## 线路上出现过的消息

房间里单独一台主机发送 `NetJoinData`（0x01，可靠，17 字节）、`NetPosData`（0x02，不可靠，72）、`NetRequestData`（0x12，1）和 `NetDataIsMatchWaitData`（0x23，可靠，1）。收到请求时它还会发送 0x09 和 0x22；进行活动时发送 0x14 和 0x15。交换消息见[交换页面](bdsp_trade.md)。0x23 可能位于存在性字节 0x00 之后；行走处理必须把 0x00 当作一条消息（[消息帧](pia.md#message-framing)）。

## 主机重复发送的消息

`NetJoinData` 就是整个 `JoinData`：

| 偏移 | 大小 | 字段 |
|---|---|---|
| 0x00 | 1 | `avatarId`（[模型](#the-model)） |
| 0x01 | 1 | `colorId`，0 |
| 0x02 | 1 | `cassetVersion`，0x31 |
| 0x03 | 2 | `InitRotY`，度数，小端序，不要求对齐 |
| 0x05 | 12 | `InitPos`，三个小端序浮点数 x、y、z |

`NetRequestData` 是一个字节，表示所请求的 id。主机会反复请求 0x23，直到客户端确认其可靠窗口；当它创建角色时会请求 `NetCharacterStateData`（0x04）：出现 0x04 请求意味着存在角色，`bin/bdsp_connect.py` 会将其作为判断结果打印出来。

`UnionRoomManager$$SetNetData` [1.3.0 main 0x01e50700] 会应答其中六个 id 的请求，并忽略其余请求：

| 请求 | 主机发送 |
|---|---|
| 0x01 `NetJoinData` | 其加入记录 |
| 0x04 `NetCharacterStateData` | 其角色状态 |
| 0x09 `NetDataBattleTypeData` | 其战斗规则 |
| 0x13 `NetTradePokeData` | 其提供的宝可梦；未选择时无内容 |
| 0x22 `NetDataStandbyWaitListData` | 其待机列表 |
| 0x23 `NetDataIsMatchWaitData` | 是否正在等待匹配 |

应答在 30 到 130 毫秒内通过可靠流返回给房间里拥有角色的站点。

### 压缩

可靠头标志 0x10 表示整个游戏消息（含头）是一条 zlib 流。`ReliableSlidingWindow` 的 push [1.3.0 main `0x15a10d0`] 在窗口开关（+0x7ac）打开时进行压缩，当结果没有更小时发送原始数据（`0x159a5b0`）。这些字节等同于 Python 的 `zlib.compressobj(5, zlib.DEFLATED, 12, 5)`，先同步冲刷再完成。加入消息以原始形式发送；记录（0x14）、胶囊（0x15）和全零 0x22 会缩小。`bin/bdsp_connect.py` 会按该标志解压。

### 其他不透明消息的发送者

| id | 类 | 发送者 |
|---|---|---|
| 0x14 | `NetDataRecodeData` | `RecodeMatching$$SendRecodeData`、`UnionStateController$$SendRecodeData` |
| 0x15 | `NetDataAttachSealNetData` | `BallDecoMatching$$SendBallDecoData` |
| 0x18 | `NetSecretBaseData` | `UgNetworkManager$$SendMySecretBaseData`；收到请求时发送 |
| 0x61 | `NetDigTableData` | 收到请求时发送 |
| 0x38 | `NetDataBattleMatchingSelectPokemon` | `BattleMatchingManager$$SendSelectPokemonData` |
| 0x42 | `NetPlayerNameData` | `UgNetworkManager$$SendOnJoinNewPlayer`、`SendPlayerNameData` |
| 0x54 | `NetSecretBaseUpdate` | 无可靠发送者 |

### 不可靠流

| 字节 | 消息 |
|---|---|
| `04 0002 00 00` | `NetCharacterStateData{NONE, 0}`，每两秒一次 |
| `12 0001 04` | 请求 0x04 的 `NetRequestData` |
| `02 0048 <72 B>` | 角色行走时的 `NetPosData` |

`room.build_state()` 和 `room.build_match_wait(False)` 构建状态和 0x23 应答。主机会以每秒五次重传可靠消息，直到收到确认；超出其最后序号两个的确认会被忽略。

## 发送游戏会实际处理的消息

可靠序号 id 与主机的发送共享；低于已确认 id 的消息会被静默丢弃。每次发送前立即读取该 id。在已确认序号处的加入消息会被处理；`--room-pattern fixed` 会在第一个 0x04 请求处停止，`--join-wait` 间隔以秒为单位（默认 1.0）。

`UnionOpcManager` 在每次加入时调用 `CreateCharacter(joinData)`：四十次加入就是四十次到达。背后没有会话的角色会跟随玩家跨地图存在，直到游戏重新启动。`OpcManager$$RemoveCharacter` [0x02279ee4] 接受一个站点索引。

## 角色记录

`OpcManager.CharaData` 为 `{int stationIndex, string assetName, int colorId, int avatarId, int sexId, int cassetVersion}`，按站点索引键控。

### 模型

    NetJoinData.avatarId  ->  CreateCharaData  ->  CharaData.avatarId
                          ->  UnionCharacterTable.SheetSheet1{ID, AssetName}
                          ->  OpLoadCharacter("persons/field/" + assetName)

`CreateCharaData` [1.3.0 main 0x022796b0] 设置 `sexId = avatarId > 7 && avatarId != 16`：8 到 15 是女孩，0 到 7 以及 16 是男孩。8 是女孩，0 是戴蓝帽子的男孩（`--join-avatar N`）。

主机自己加入时带有 work 360（`GetAvaterId` [0x01e54030]）。新存档保存为 0。外观计数器（`ev_union_character_select_*`）为男孩存储 16 或 1 到 7，为女孩存储 8 到 15；否则，当 work 360 为 0 时，`ev_traner_other_see_random` 会将其设为 1 加上一个小于 16 的随机值，性别任意。因此，只有在计数器被使用之后，加入消息才会体现存档性别。

`NetDataTranerCardData`（0x05，75 字节）在联盟房间里不绘制任何内容。

### 状态字节

`StateData` 为 `{byte state, byte isRecruiment}`，`state` 是 `OpcState.OnlineState`：

| 值 | 名称 | 值 | 名称 |
|---|---|---|---|
| 0 | `NONE` | 5 | `RECRUITMENT_RECORD` |
| 1 | `DIG_FOSILL` | 6 | `RECRUITMENT_GREETINGS` |
| 2 | `SECRETBASE_ACTION` | 7 | `RECRUITMENT_BALL_DECORATION` |
| 3 | `RECRUITMENT_BATTLE` | 8 | `COMMUNICATE` |
| 4 | `RECRUITMENT_TRADE` | | |

17 到 21 是 `NOW_*` 状态（[transitionType 表](#talkstate-and-the-value-that-crashes-the-game)）。`RECRUITMENT_*` 值会弹出对话气泡：`StateData{RECRUITMENT_TRADE, 1}` 显示交换气泡。

接收到的 0x04 到达 `UnionOpcController$$SetNetData` [1.3.0 main 0x01e48c50]（当该站点没有角色时丢弃），它会设置状态，根据 `isRecruiment` 选择主机或普通表情图标，并对非零状态播放动画 0。远程角色的状态只有在其所属站点发来 0x04 或被移除时才会改变。在角色 `Start` 运行之前，设置器会丢弃该值 [0x02277c50]，而 0x04 请求在此之前就已发出 [0x01e49854]：要像主机那样每两秒重复发送一次状态。

`OnlinePlayerCharacter$$IsCanTalkState` [0x02277af0]：状态 1、3 到 8 以及 17 到 21 可以被交谈。

### 行走

主机自身的 `NetPosData` 每 0.410 秒来一次，跨过 0.935 个单位（`room.POS_PERIOD`、`room.POS_STRIDE`）。`pos = (-posX * 0.05, posZ * 0.05)`。远程角色会与墙壁碰撞；玩家不会与它碰撞。`--room-walk-steps 8` 会留在房间内；交换不需要行走（`--room-walk-steps 0`，交换路径的默认值）。

## 被搭话

摆出表情的玩家会停在原地直到有人接近，在其状态非零时按 A 键没有任何效果。交换表情是 `NetCharacterStateData{4, 1}`，由 `{0, 0}` 清除。以 `isRecruiment` 为条件：状态 18 表示主机已在交换中。

接近动作是 `NetDataTalkReserveData`（0x63），`63 00 01 00`（`bin/bdsp_connect.py --initiate-talk`；`bin/bdsp_host.py --approach-delay`）。接近客户端的主机：

    cli ->  64 0003 00 01 04      NetDataTalkReserveResultData{IsCanTalk, IsRecruitment, emoticonStateType}
    con ->  06 0005 00 01000000   NetDataTalkData{talkOpcSexId: 0, talkState: GREETING}
    con ->  10 0002 01 04         NetDataTalkCancelEndData{IsRecruitment: 1, emoticonStateType: 4}

没有 0x64，玩家会保持冻结。`IsCanTalk` 为 0 会播放问候语并在“请稍等！”处停住；为 1 则显示“抱歉，我另有安排”。断开站点会释放停住的问候语。

### 主机接近时

`UnionRoomManager$$MyUpdate` [1.3.0 main 0x01e49fb0] 仅在玩家状态为 0、没有对话或窗口打开、玩家位于所有 `EnterCollision` 之外时处理 A 键。对于 10.0 单位内最近的角色：

| 角色的状态 | 按 A 键的效果 |
|---|---|
| 0、2、9 到 16 | 无 |
| 8、17 到 21 | `StartTalk(opc, 0, 0, 0)` [0x01e4c2d0] |
| 4 | `CheckErrorMessageTrade`，然后按最后一行处理 |
| 7 | `CheckBallDeco`，然后按最后一行处理 |
| 1、3、5、6 | 发送 0x63，将状态存储到 `nowTalkReserveState`（+0x188），调用 `CreateSelectStateModel(state, 1)` |

主机读取 0x64 [0x01e50dec] 后会发送 `NetDataTalkCancelEndData{0, 0}`，除非 `emoticonStateType` 等于 `nowTalkReserveState`，此时它会将其清除；因此，一个广告 `{4, 1}` 的角色会回复 `64 0003 00 01 04`，每次 0x63 回复一次，忽略重传的副本。

当主机作为搭话方时，客户端的角色是招募者。招募者的“是”是 `NetDataTransitionData{18, 0}`，即 `07 0002 12 00`（[交换页面](bdsp_trade.md#the-message-sequence)）。在 0x64 之后发送它，会在搭话主机上直接开始交换，无需其玩家确认（`SwitchTransitionMessage` [0x01e53bf0] -> `TransitionTradePoke` [0x01e5c1c0]）：主机会发送其 0x24 并打开交换框。`SwitchTransitionMessage` 读取类型对应的模型时没有空值检查；向一台自进入后尚未对交换招募者按过 A 的主机发送 0x07 会读取空值。

### 问候语中的名字

问候语按角色站点的 Pia 玩家名来称呼该角色（`NetworkManager$$GetGamerData` [1.3.0 main 0x02250e50]），从 PlayerInfo 以 UTF-8 解码。`Utils$$CheckNGTrainerName` [0x01cbdc30] 会在名称为空、被 `CheckNgWords` 标记、或按 UTF-16 单元计算超过该语言限制时，替换为一个版本名：

| `lang` | 限制 |
|---|---|
| 1、8、9、10 | 6 |
| 任何其他正值 | 12 |
| 0 或以下 | 由 UI 当前语言决定 |

PlayerInfo 为 195 字节（解析器 [0x0154f044..0x0154f5e0]）：

| 偏移 | 字段 |
|---|---|
| 0x00 | 名称编码：2 表示 20 个 UTF-16 单元，其他值表示 80 字节 |
| 0x01..0x50 | 名称 |
| 0x51 | 第二个字符串的编码 |
| 0x52..0x79 | 第二个字符串，40 字节 |
| 0x7A | 语言，一个 `MsgLangId` |
| 0x7B..0xBA | 64 字节 |
| 0xBB..0xC2 | u64 |

    MsgLangId  JPN 1, USA 2, FRA 3, ITA 4, DEU 5, ESP 7, KOR 8, SCH 9, TCH 10

主机会在 0x7A 处发送其游戏文本语言（存档 `CONFIG.msg_lang_id`，`get_msgLangID` [0x0237e100]），并发送其检查后的名称，编码为 1。站点协议的写入器将其放在 [0x01550e98] 处。`bin/bdsp_connect.py` 和 `bin/bdsp_host.py` 使用 `pokeldn/bdsp/host.py` 的 `player_info` 构建 PlayerInfo，并发送 `--language`，默认值为 3；桌面应用传递其训练家语言。在 3 下，11 个字符的名称会完整显示。

替换名取决于被搭话角色的 `NetJoinData` 的字节 2：0x31 时为 `dp_characters` 中的标签 247，否则为标签 206，外加一个句号：

| 语言包 | 0x31（明亮珍珠） | 其他值 |
|---|---|---|
| 英语 | `Pearl.` | `Diamond.` |
| 法语 | `Perlo.` | `Diamant.` |
| 德语 | `Perl.` | `Diamant.` |
| 意大利语 | `Perl.` | `Diaman.` |
| 西班牙语 | `Perla.` | `Diamant.` |
| 日语、日语汉字 | `パール.` | `ダイヤ.` |
| 韩语 | `펄.` | `다이아몬드.` |
| 简体中文 | `帕尔.` | `戴亚.` |
| 繁体中文 | `帕爾.` | `戴亞.` |

### talkState，以及会导致游戏崩溃的值

`TalkState` 为 `{CHECK = 0, GREETING = 1, NONE = 2}`。CHECK 会让 `UnionStateController$$SwitchSpokenStateMine` 在没有空值保护的情况下解引用 `msgWindow`（0x1fd5ec0）；摆出表情站立的玩家没有这个窗口，所以 CHECK 会导致游戏崩溃。`pokeldn/bdsp/room.py` 拒绝发送它。

`NetDataTransitionData{transitionType, isRecruitment}`（0x07）会将停住的问候推进到某项活动。它通过尾调用发送，对仅扫描 BL 的调用者查找不可见（[查找调用者](switch_re.md#finding-callers)）。`SwitchTransition` [1.3.0 main 0x01e5ba70] 根据它进行分发：

| transitionType | 活动 | 进入方式 | `UnionStateController` + 处的模型 |
|---|---|---|---|
| 3、17 | 对战 | `TransitionBattle` | 由 `isRecruitment` 决定 0x38 或 0x40 |
| 4、18 | 交换 | `TransitionTradePoke` | 0x50 |
| 5、19 | 记录混合 | `RecodeMatching$$Open` | 0x60 |
| 6、20 | 训练家卡片 | `TransitionShowTrainerCard` | 0x70 |
| 7、21 | 球壳装饰 | `BallDecoMatching$$Open` | 0x80 |
| 8 到 16 | 无 | | |

`RecodeMatching$$Open` 和 `BallDecoMatching$$Open` 会立即发送主机自己的记录并等待；只有对方的记录会写入存档。

### 记录混合

主机以“Échanger des données”（状态 5）招募。其玩家确认后，会发送 `NetDataTransitionData{5, 0}`，然后是 694 字节的 `NetDataRecodeData`（zlib），并在状态 19 等待。若无应答，约 44 秒后返回房间。`room.parse` 将记录头部返回为 `recode`：

    RECORD.record[30]        thirty uint counters indexed by RECORD_ID
    RANDOM_SEED              group_name (16 chars), name (32 chars), int sex, int region_code,
                             ulong seed, ulong random, long time_stmp (FILETIME), int user_id
    TvRecodeData             five TV records, each `bool isEmpty` (4 bytes), ints, a TV_STR_DATA
    4 x TV_STR_DATA          {16-char value, byte language, genderId, two reserved}
    RECORD_HEAD              13-char username, int language, byte sex, int body_type, uint uniqueID
    ten ints, six bytes      per-TV branch values, myVersion (0x31), five *IsNotEmpty flags

未写入的字段持有堆指针。`RECORD_HEAD.sex` 和 `RANDOM_SEED.sex` 可能不一致。

### 对战阶梯

对战（招募时状态 3）会运行一个阶梯流程；招募方主机在每一级都会等待加入者：

| 加入者发送的内容 | 主机的行为 |
|---|---|
| `NetDataTalkData{GREETING}` | 显示“Un combat ? OK !”并等待 |
| `NetDataSelectData{0}`（0x08） | 显示“... est en train de choisir quoi faire...”并等待 |
| `NetDataBattleTypeData{0}`（0x09，单打） | 询问其玩家；确认后发送 `NetDataTransitionData{17, 0}` 并打开大厅 |
| `NetDataBattleMatchingJoin`（0x30）`{uint id, byte stationIndex, index, language, colorId, avatarId, sexId, cassetVersion}` | 以自己的加入数据回应并转发加入者的数据；加入者出现在第二个槽位 |
| `NetDataBattleMatchingReady`（0x32，空） | `NetDataBattleMatchingState{0, 6}`（0x33，`SelectBattleTeam`） |
| 无 | 在选择队伍时，发送六个 0x38，然后显示“en attente d'autres personnes” |

每个 0x38 持有一个加密的 PB8（按顺序选定的队伍），剩余贴纸数据的 `affixSealCount` 为 0，`index` 为 0 到 5，`num` 为 6。未找到对 0x30 `id` 的检查。`MatchingState`：None 0、Initialize 1、Load 2、RecruitmentMember 3、SelectTeamMember 4、SelectRule 5、SelectBattleTeam 6、SelectPokemon 7、GoBattle 8、Result 9、Resume 10、Closing 11、LeavedOtherMembers 12。

`NetDataSelectData`（0x08）为 `{byte index}`；其接收器 [0x01e52a30] 会忽略索引，并在没有任何空值检查的情况下将 `UnionStateController+0x38`（对战招募模型）驱动到 `BATTLE_RULE_SELECT_WAIT`，无论当前打开的是什么对话。该模型仅在玩家招募对战时才设置，并且在每次进入联盟房间时都从 null 开始（`UnionRoomManager` 在离开房间区域时被销毁，`NetUseManager.OnZoneChange` [0x026cfef0]）。向本次进入后尚未招募过对战的主机发送 0x08，会向地址 0x18 [0x023e2604] 写入并触发故障。除非主机自己的 0x04 表明状态为 3 且 `isRecruiment` 为 1，否则永远不要发送 0x08。

### 地下大洞窟

地下大洞窟在场景 id 12608 下通告相同的 `local_communication_id`；同一条会话线会关联，但没有加入记录（`--room-walk 0`）。站点到达时，`UgNetworkManager` 会发送：

| id | 类 | 字节数 | 内容 |
|---|---|---|---|
| 0x17 | `NetZoneData` | 16 | `Vector3 pos`、`int zoneID` |
| 0x42 | `NetPlayerNameData` | 28 | 13 个 UTF-16 字符，byte genderid、byte languageId |
| 0x50 | `NetKousekiCount` | 4 | `int Value` |
| 0x41 | `NetSecretBaseInfo` | 16 | 在秘密基地内代替 0x17：入口的 `Vector3 pos`、`int zoneID` |

指定玩家区域的 `NetUgJoinData`（0x16，18 字节：`byte avatarId, colorId; short zoneID, InitRotY; Vector3 InitPos`）会在玩家旁边放置一个角色；主机会请求其 0x04 和 `NetNaminoriData`（0x55），并每 0.41 秒发送一次 `NetPosData`（`--ug-join --room-walk-steps N`）。

`UgNetworkManager$$OnReceiveRequestData` [1.3.0 main 0x01f7c050] 会在主机窗口已携带某些内容后，应答对 0x01、0x04、0x18、0x19、0x54、0x55 和 0x61 的请求：

| 请求 | 字节数 | 内容 |
|---|---|---|
| 0x18、0x54 | 616 | 玩家自己的 `UgSecretBase`；当其 `zoneID` 为 0 时无内容 |
| 0x61 `NetDigTableData` | 8 | 挖掘化石表，0..7 的一个排列，准备就绪后返回 |

非主机站点在加入时会请求 0x61。`OnReceiveDigTableData` [0x01f7dad0] 会采用其表标志（+0xA8）为 0 时到达的第一个 0x61，来自任何站点且未经检查，重建挖掘点并设置该标志；之后的则被忽略。`CreateDigPoints` 按 `MyStationIndex` 索引该表，并在没有空值检查的情况下查找对应的组 ID：只发送 0..7 的排列，因为更大的字节会使主机触发故障。每个 `UgFieldManager` 会话都会构建新的 `UgNetworkManager`，因此每个都会重新采用一个表。0x29 `NetDigGroupIdData` 没有发送方分支，也没有接收方分支。

`bin/bdsp_connect.py --inject-file PATH` 会可靠地发送文件中每一行新的 `ID:HEX`。

### 球壳装饰

主机以“Déco Capsule”（状态 7）招募。它会发送 `NetDataTransitionData{7, 0}`，进入状态 21，并发送其 143 字节的 `NetDataAttachSealNetData`（zlib）。若无应答，约 45 秒后返回房间。若以 143 字节应答（`bin/bdsp_connect.py --answer-with 0x15:FILE`），它会应用这些数据并返回房间。请从自己的任务发送应答：如果从接收器内部发送，它等待的确认将永远不会被读取。

`BallDecoMatching$$ReceiveBallDecoData`（`0x021ca5e0`）会写入 99 个球壳槽位中第一个没有贴纸的槽位，如果所有槽位都有贴纸则什么都不写。`BallDecoWork$$CopyTradeCapsuleData`（`0x01f23eb0`）会清空该槽位，并在存档中拥有对应贴纸时，将每个贴纸放置在 `(x, y, z) / 100` 处并消耗它，否则丢弃。当所有贴纸都成功放置时，关闭消息是 `DLP_net_union_room_090`，否则是 `_114`。数量超过 20 或贴纸 id 为 200 或以上会抛出异常。

位置是球壳半径的百分之一。3D 模式会在每个贴纸所在位置绘制它。2D 模式只在网格单元格的 `BallDecoWork$$Convert2DPosition`（`0x01f24da0`）处绘制贴纸：半径为 1，正面（+z）的行和列相隔 28 度，背面相隔 25 度，每个分量四舍五入到 0.01。正面和背面的网格是 7×7 方块减去 `(|x|, |y|)` 属于 `{(3, 2), (2, 3), (3, 3)}` 的位置（`Capsule2DViewController$$Initialize` `0x01e909b0`，在零售版 1280×720 缩放比例下）：

    row  3   columns -1..1
    row  2   columns -2..2
    row  1   columns -3..3
    row  0   columns -3..3
    row -1   columns -3..3
    row -2   columns -2..2
    row -3   columns -1..1

网格外的 2D 设计会填充一个标记为已装饰的槽位，但不会绘制任何内容。

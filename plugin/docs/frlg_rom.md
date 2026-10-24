---
title: Code on the console
parent: FireRed and LeafGreen
nav_order: 3
---

# 主机上的代码

神秘礼物客户端通过两个解释器运行发送给它的代码：`CLI_RUN_MEVENT_SCRIPT`（操作码 15）将字节交给神秘事件虚拟机，`CLI_RUN_BUFFER_SCRIPT`（操作码 21）交给 CPU。两者都不需要故障、准备好的存档或任何设置；主机停留在神秘礼物菜单上。

本页地址对应法语版火红，卡带 BPRF，软件版本 0x0A。叶绿版地址在 [叶绿](frlg_leafgreen.md)；表格在 [ROM 地图](frlg_rom_map.md)。

# 神秘事件虚拟机

一个独立的解释器 [src/mystery_event_script.c]，拥有自己的 17 条命令表 [data/mystery_event_script_cmd_table.s]，与神秘卡片的配送脚本编译到的场景脚本虚拟机不同。`pokeldn/frlg/rom/mystery_event.py` 汇编每条命令（`MysteryEventScript.blob()` 保存数据，汇编器解析指针）。每条操作码都在零售硬件上验证过。

## 命令表

| # | 命令 | 操作码字节后的操作数 | 返回 | 效果 |
|---|---|---|---|---|
| 0 | `nop` |  | FALSE | 无 |
| 1 | `checkcompat` | u32 base, u16, u32, u16, u32 | TRUE | 兼容性门控 |
| 2 | `end` |  | TRUE | `StopScript` |
| 3 | `setmsg` | u8 selector, ptr | FALSE | 当选择器为 `0xFF` 或等于状态时，执行 `StringExpandPlaceholders(gStringVar4, str)` |
| 4 | `setstatus` | u8 | FALSE | `ctx->data[2] = value` |
| 5 | `runscript` | ptr | FALSE | 在场景脚本上执行 `RunScriptImmediately` |
| 6 | `initramscript` | u8 group, u8 map, u8 object, ptr, ptr | FALSE | 将 `InitRamScript` 绑定到任意地图和对象 |
| 7 | `setenigmaberry` | ptr | FALSE | 写入 `gSaveBlock1Ptr->enigmaBerry` |
| 8 | `giveribbon` | u8 index, u8 ribbonId | FALSE | 将礼物奖章赋予每只非蛋的同行宝可梦 |
| 9 | `givenationaldex` |  | FALSE | `EnableNationalPokedex()` |
| 10 | `addrareword` | u8 | FALSE | `EnableRareWord`（一种轻松聊天流行语） |
| 11 | `setrecordmixinggift` |  | TRUE | 失效：`SetIncompatible` |
| 12 | `givepokemon` | ptr | FALSE | 将完整的 `struct Pokemon` 以及附加的邮件放入队伍 |
| 13 | `addtrainer` | ptr | FALSE | 一个 188 字节的 `BattleTowerEReaderTrainer` |
| 14 | `enableresetrtc` |  | TRUE | 失效：`SetIncompatible` |
| 15 | `checksum` | u32, ptr, ptr | TRUE | 如果范围内 `CalcByteArraySum` 不匹配，则状态为 1 |
| 16 | `crc` | u32, ptr, ptr | TRUE | 与 `CalcCRC16` 相同 |

## `checkcompat` 是可选的

`checkcompat` 会开启每一份官方脚本，并对语言和版本掩码进行门控（反编译的 `LANGUAGE_MASK` 是英语）。脚本可以跳过它：

```c
bool32 RunMysteryEventScriptCommand(struct ScriptContext *ctx)
{
    if (RunScriptCommand(ctx) && ctx->data[3])   // data[3] is set only by checkcompat
        return TRUE;
    return FALSE;
}
...
while (MEventScript_Run(&ret));
```

`RunScriptCommand` [script.c:107] 在一次调用内循环，直到某条命令返回 TRUE。没有 `checkcompat` 时，`data[3]` 保持为 0：脚本运行到第一条返回 TRUE 的命令（通常是 `end`），外层 `while` 停止。掩码永远不会起作用，指针会按照 `operand - ctx->data[1] + ctx->data[0]` 重新定位，其中 `data[1]` 为 0（仅由 `checkcompat` 设置），`data[0]` 是主机的 1024 字节 `client->recvBuffer`：操作数 N 表示发送内容的第 N 个字节。`checkcompat` 是汇编器允许在其后出现代码的唯一命令。

## 返回通道

`MEventScript_Run` 将状态写入 `client->param` [mystery_event_script.c:75]；`CLI_LOAD_TOSS_RESPONSE` 将其加载到 `MG_LINKID_RESPONSE` [mystery_gift_client.c:204]。以下四个客户端命令返回脚本选择的 u32：

    CLI_RECV MG_LINKID_RAM_SCRIPT
    CLI_RUN_MEVENT_SCRIPT
    CLI_LOAD_TOSS_RESPONSE
    CLI_SEND_LOADED

`setstatus` 可设置任意值。内置状态：

| 状态 | 含义 |
|---|---|
| 0 | 没有命令设置状态 |
| 1 | `setenigmaberry` 无法验证树果，或 `checksum`/`crc` 不匹配 |
| 2 | 成功；每条完成工作的操作码都会设置此值 |
| 3 | `SetIncompatible`，或 `givepokemon` 发现队伍已满 |

`CLI_COPY_RECV_IF` 和 `CLI_COPY_RECV_IF_N` 可以根据它分支客户端脚本 [mystery_gift_client.c:170]（未使用）。

菜单从 `CLI_RETURN` [`GetClientResultMessage`, mystery_gift_menu.c:884] 打印结果，因此这里的 `setmsg` 不可见。只有成功消息才能到达 `MG_STATE_SAVE_LOAD_GIFT` [:1379]，否则事件写入的数据会在重置时丢失；因此 `CLIENT_SCRIPT_MEVENT_DONE` 即使没有卡片也返回 `CLI_MSG_CARD_RECEIVED`。`CLI_MSG_BUFFER_SUCCESS`（13）是另一个成功出口，打印压入的 64 字节 `CLI_COPY_MSG`。

### 自检脚本

`--gift mystery-event-probe` 是无害的：一旦全国图鉴开启，`givenationaldex` 就是空操作，而 `checksum` 只读取。

    givenationaldex; setstatus 42; checksum 1026, 16, 31

| 状态 | 含义 |
|---|---|
| 42 | 链运行到末尾，指针操作数是发送缓冲区内的偏移量 |
| 1 | 链已运行，但重定位后的指针没有落在测试字节上 |
| 2 | `givenationaldex` 运行了，其后没有命令执行 |
| 0 | 虚拟机已进入，但没有命令执行 |
| 无 | 客户端脚本结构有误，不是虚拟机的问题 |

`checksum` 是终止性的，在匹配时保留之前的状态。零售火红会返回 42。

## `givepokemon`

`pokeldn/frlg/save/mevent_pokemon.py` 构建有效载荷：100 字节加密的同行宝可梦，然后是主机在 `pointer + sizeof(struct Pokemon)` 处读取的 34 字节 `struct Mail`。`--gift mystery-event-celebi` 会提供一个。与场景脚本的 `givemon` 不同，它：

- 附加邮件。`ItemIsMail` 作为门控，因此携带物品必须是十二种邮件物品之一 [mail_data.c:167]；`GiveMailToMon2` 将整个结构（文字、发件人姓名、训练家 ID、物种、物品）复制到 `gSaveBlock1Ptr->mail` [:100]；
- 在全国图鉴编号上设置 `FLAG_SET_SEEN` 和 `FLAG_SET_CAUGHT`；
- 落到神秘礼物菜单：菜单关闭时宝可梦已在队伍中。

状态 2 为成功，3 为队伍已满且未写入任何内容。切勿在它之后放置 `setstatus`。

构建器强制避免的陷阱：

- 宝可梦的 `mail` 字节必须为 `MAIL_NONE`（0xFF）；0 是邮件槽 0，会被读取为真实邮件；
- `personality == otId` 会使加密密钥为 0，因此宝可梦无论是否经过洗牌都能通过验证，未洗牌的可能会被发送；
- 队伍尾部是派生值；尾部为零时会读回为等级 0；
- 携带物品与邮件的 `itemId` 必须一致：`GiveMailToMon2` 会根据邮件设置携带物品。

## `initramscript`

`initramscript 3, 0, 2` 将场景脚本绑定到组 3、地图 0、对象 2，即真新镇南边的胖男人。重启后他会说出脚本的台词，并展开 `{PLAYER}`。

`CLI_SAVE_RAM_SCRIPT` 使用 `InitRamScript_NoObjectEvent`（MAP_UNDEFINED，对象 0xFF）[script.c:578]，只有配送员的 `GetSavedRamScriptIfValid` [:554] 会读取它，并且仅在持有有效神秘卡片时。真实坐标会到达 `GetRamScript(gSpecialVar_LastTalked, script)` [:514, field_control_avatar.c:458]，它会代替对象自身的脚本运行该脚本，并忽略卡片。`gSpecialVar_LastTalked` 是对象的本地 ID，按 `map.json` 顺序从 1 开始。

它会消耗神秘卡片（[唯一的 RAM 脚本槽位](frlg_gift.md#the-one-ram-script-slot)）；会话会记录“未持有神秘卡片”，直到下一张普通卡片收回该槽位。被绑定时，对象会失去自己的脚本：绑定到静态遭遇对象时，该脚本会取代遭遇。

## 陷阱

- `setenigmaberry` 无法设置道具效果。`struct ReceivedEnigmaBerry` [berry.c:944] 有 1322 字节：`Berry2`（28 字节）、`u8 unk_001C[0x4FA]`，然后是 `itemEffect[18]`、`holdEffect` 和 `holdEffectParam`，位于 0x516，超出了 1024 字节缓冲区；尾部是堆上 `recvBuffer` 之后的内容（`build_enigma_berry_blob`；模拟器报告 `read_past_buffer`）。
- `struct Berry2` 中的两个 ROM 描述指针必须从卡带读取，并原样发回：树果袋会永久从存档中解引用它们。
- `giveribbon` 索引 7..10：`GiveGiftRibbonToParty` [pokemon_size_record.c:193] 接受 `index < 11`，但 `sGiftRibbonsMonDataIds` 有七个条目复制到 `u8[8]` 中，因此 7..10 会 `SetMonData` 一个来自未初始化堆栈的字段 ID。汇编器会拒绝任何大于 6 的值。FRLG 没有奖章界面；奖章只能在转移后显示。
- 没有终止命令的脚本会把缓冲区其余填零的部分当作操作码解码。`assemble()` 和服务器会拒绝这样的脚本。
- `setrecordmixinggift` 和 `enableresetrtc` 各调用一次 `SetIncompatible`，并停止链 [mystery_event_script.c:227, :291]。作曲器会拒绝它们。
- `addrareword` 和 `setenigmaberry` 在游戏中不可见；从存档中读取它们：`additionalPhrases`（SaveBlock1 + 0x2F10，多一个轻松聊天词语）和 `enigmaBerry`（+0x30EC）。它设置的 `VAR_ENIGMA_BERRY_AVAILABLE` 在 FRLG 中没有其他地方读取。

## 接线方式

- `pokeldn/frlg/rom/mystery_event.py`：操作码、汇编器、反汇编器（`describe`）以及 `run()`，即离线客户端使用的模拟器。
- `pokeldn/frlg/gift/mg_script.py`：`CLIENT_SCRIPT_SAVE_CARD_AND_MEVENT`（未持有卡片：卡片、配送脚本、事件）、`CLIENT_SCRIPT_RUN_MEVENT`（已持有卡片：仅事件，不丢弃任何东西）、`CLIENT_SCRIPT_MEVENT_DONE`（共享的成功结尾）。
- `pokeldn/frlg/gift/mg_server.py`：`SCRIPT_SEND_MYSTERY_EVENT` 带 `SVR_LOAD_MEVENT` 和 `SVR_READ_MEVENT_STATUS`；状态会落到 `server.mevent_status` 和主机日志中。
- `pokeldn/frlg/gift/gift_composer.py`：`WonderGift.mevent` 验证汇编后的字节。

# 原生 ARM 代码

```c
case CLI_RUN_BUFFER_SCRIPT:
    memcpy(gDecompressionBuffer, client->recvBuffer, MG_LINK_BUFFER_SIZE);
    client->funcId = FUNC_RUN_BUFFER;
    ...
static u32 Client_RunBufferScript(struct MysteryGiftClient * client)
{
    u32 (*func)(u32 *, struct SaveBlock2 *, struct SaveBlock1 *) = (void *)gDecompressionBuffer;
    if (func(&client->param, gSaveBlock2Ptr, gSaveBlock1Ptr) == 1)
```

[mystery_gift_client.c:237,276]。每个有效载荷都基于五个事实：

- 无论发送什么，都会复制 1024 字节（`MG_LINK_BUFFER_SIZE`），因此有效载荷运行时其后面是上一次接收的尾部，必须自包含。
- `r0 = &client->param`、`r1 = gSaveBlock2Ptr`、`r2 = gSaveBlock1Ptr`：两个存档块均可读可写。
- `client->param` 正是 `CLI_LOAD_TOSS_RESPONSE` 作为 `MG_LINKID_RESPONSE` 发回的内容 [:204]。
- 每帧调用一次，直到返回 1；始终不返回 1 的有效载荷会让神秘礼物菜单挂起且无法退出。`memcpy` 在 `CLI_RUN_BUFFER_SCRIPT` [:239] 处运行一次，因此有效载荷可以在帧之间保持状态。
- ARM 状态：调用者通过 `bx` 到达字对齐的地址。

`gDecompressionBuffer` 位于 0x0201C000（由 `anchors` 测量）。有效载荷是位置无关的。

## 构建

本应用的神秘礼物构建器使用同一工具链
（`pokeldn/frlg/rom/custom_code.py`）汇编 ARM 源码，或直接获取原始 `.bin`，并在发送前于模拟控制台上运行。`.pokegift` 文件包含编译后的 ARM 字节码、卡带目标和响应设置。[神秘礼物文件](gifts.md#console-code)说明了打包与分享方式。

- `asm/*.s`，每个负载一个 ARM 源文件，由 `scripts/gen_buffer_scripts.py` 汇编到已提交的
  `pokeldn/frlg/rom/buffer_payloads.py`；`tests/test_buffer_script.py` 会在安装了
  `arm-none-eabi-as` 时重新汇编并比较。
- `pokeldn/frlg/rom/buffer_script.py`：注册表、校验，以及 `emulate()` / `emulate_repeating`，
  它们在 unicorn 下按 GBA 内存映射运行负载，并传入控制台的三个参数；发生错误或从不返回 1 的
  负载永远不会发送出去。
- `pokeldn/frlg/gift/mg_script.py`：`CLIENT_SCRIPT_RUN_BUFFER`（接收、运行、加载返回通道、
  发送、接收下一个脚本）和 `CLIENT_SCRIPT_BUFFER_SUCCESS`。
- `pokeldn/frlg/gift/mg_server.py`：`SCRIPT_RUN_BUFFER_SCRIPT`。没有卡片提示，也没有丢弃提示；
  已持有的神秘卡片会保留。
- 两个模拟控制台均独立依据反编译编写，并以逐帧重入的方式执行负载：
  `pokeldn/frlg/gift/mg_client.py` 和 `tests/test_mystery_gift_flow.py` 中的
  `ConsoleClientModel`。

每次都先离线：

    ./.venv/bin/python -m pytest tests/test_buffer_script.py -q
    ./.venv/bin/python scratchpad/mg_client_harness.py --buffer-script -v

在硬件上，控制台会等待神秘礼物 -> 神秘卡片 -> 朋友，然后加入主机。在下面的运行命令中，`HOST`
代表
`POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS --dump-file DUMP.bin`，
`IP_HOST` 代表 `./.venv/bin/python -u bin/frlg_mg_host.py --over-ip --dump-file DUMP.bin`，后者
通过局域网提供模拟控制台，不使用无线电也不需要密钥。在 `DUMP.bin` 存在之前，绝不要向主机发送
SIGTERM；它会在显示 `Buffer script dump: N bytes` 数秒后写出：

    until ls DUMP.bin >/dev/null 2>&1; do sleep 2; done

## 负载可存放的位置

缓冲脚本每一帧都会被重新复制，因此它写入自身映像的任何内容都不会保留。生命周期超过菜单的代码
要放在游戏从不写入的位置：

    0x0203FC00 .. 0x02040000    1024 bytes, above every symbol the game links

尺寸最大的 EWRAM 符号结束于 0x0203FBAC（[EWRAM 在两个构建中的地址相同](frlg_rom_map.md)）。
根据反编译命名（`gHeap` 的 114688 字节在符号表中没有大小），这是唯一未被占用的 EWRAM 区间；
其余的是三字节和八字节的对齐空洞。

    0x0203F768 .. 0x0203FBAC    1092 bytes, newlib's malloc state

`__malloc_av_` 以及其后的 malloc 计数器只能从 newlib 的 stdio 到达，而调用 stdio 的只有
`AGBPrintf`，后者在发布版本中未使用（pokefirered_switch.elf：对 `_malloc_r`、`_calloc_r`
和 `_free_r` 的唯一 `bl` 均位于 libc 内部）。在 mGBA 下的法语版火红中，在那里填充 0xA5 后经过
菜单、行走和一整场野生对战仍然保留。GB-Link 团队卡片将其重定位后的脚本保存在那里
（[frlg_gift.md](frlg_gift.md#gb-link-team-cards)）。`scratchpad/ewram_symbol.py ADDR LEN`
可检查某个地址。

绝不要因为某个地址读数为零就选择它。0x0202B280、0x020185C4 和 0x0203B0E9 会读出几十 KB 的零，
它们分别是对战和盒子缓冲区、`gDecompressionBuffer` 之前的一段区域以及分配器簿记；0x02012304
位于 `gHeap` 中。0x0202B280 位于 `gPokemonStorage` 内部：在那里写入可能会落到某只存放在盒子中
的宝可梦的校验和上，此后存档就会留下一个坏蛋。

软复位会清除 EWRAM 两次：`DoSoftReset` 调用 `SoftReset(RESET_ALL & ~RESET_SIO_REGS)`
[main.c:488]（先 `svc 0x1` 再 `svc 0` [libagbsyscall.s:69]），然后 `AgbMain` 调用
`RegisterRamReset(RESET_ALL)` [main.c:134]；0xFF 的第 0 位就是 `RESET_EWRAM`
[include/gba/syscall.h:4,12]。Switch 封装还会重启模拟控制台，因此 `AgbMain` 会运行两次：
`gIntrTable` 和 `INTR_VECTOR`（0x03007FFC）每次启动都会被清除并重建两次，条目 1、2、7 在两次
之间取得无线通信值（以每秒 328000 次采样：33.3 ms，之后到第二次清除为 133.6 ms，到重建为
33.6 ms）。启动过程不会重建 0x0203B0E8 以上的任何内容。两次启动之间不会有任何内容写入
0x0203FC00..0x02040000：放在那里的标记在标题画面、重新加载、菜单、存档、地图切换、对战和
电脑盒之后仍会存在，而软复位（A+B+START+SELECT）会将其清除。

## 每帧钩子

`gIntrTable` 位于法语卡带的 0x03002720；第 4 项，即 V 空白处理程序，保存着 `VBlankIntr`
（0x0800071D）。它是由 `InitIntrHandlers` 从 `gIntrTableTemplate` [main.c:339] 一次性写好的十四个函数指针，BIOS 通过 `IntrMain` 到达这里，而 `IntrMain` 的地址由 0x03007FFC 处的向量保存。替换第 4 项就能让代码在每个游戏状态的每一帧得到一次调用；每当菜单或战斗开始时，`gMain.vblankCallback` 和 `gMain.callback2` 都会被重写。

位于主机的 IWRAM 中：`IntrMain_Buffer` 为 0x03002760（英文版为 0x03002810），`gSaveBlock1Ptr` 为 0x03004228（英文版为 0x030042D8），因此卡带版 IWRAM 在这些地址上比英文版低 0xB0。IWRAM 不像 EWRAM 那样会在构建之间转移。

| 入口 | 卡带版 | 英文版 | |
|---|---|---|---|
| 0 VCount | 0x08000805 | 0x0800081C | `VCountIntr` |
| 1 Serial | 0x03004B34 | | 连接建立时的一个 IWRAM 处理程序 |
| 2 Timer3 | 0x08005AE1 | | `Timer3Intr`，不同的 ROM 段和差值 |
| 3 HBlank | 0x080007D5 | 0x080007EC | `HBlankIntr` |
| 4 VBlank | 0x0800071D | 0x08000734 | `VBlankIntr` |
| 5, 6, 8-13 | 0x08000885 | 0x0800089C | `IntrDummy`，八次 |
| 7 | 0x081E0D35 | | RFU 定时器处理程序，`sTimerIntrFunc = gIntrTable + 0x7` [main.c:85] |

入口 1 和 7 在无线运行时与反编译预测的模板不同；会话结束后、直到重置前，入口 1 和 2 会一直保留它们的无线值。游戏只在 `InitIntrHandlers` 中写入入口 4，而该函数仅在软重置时重新运行。

### 会话结束后仍然存活的代码

暂存区中的一个二十字节 stub，安装到入口 4 中，在会话关闭后的每个游戏状态、每一帧都会运行。`asm/resident/vblank-hook.s`：

```arm
    ldr     r0, .Lcounter
    ldr     r1, [r0]
    add     r1, #1
    str     r1, [r0]
    ldr     r0, .Loriginal
    bx      r0                      @ tail branch: lr still points at intr_return
```

`IntrMain` 以 SYS 模式进入处理程序，`lr` 指向 `intr_return`，并允许它覆盖 r0-r3 [crt0.s, `jump_intr`]，因此被替换的处理程序通过自己的 `bx lr` 返回。两个字面量都在发送前打好补丁。

一条 `call-chain` 安装它：先写五个字，最后写入口 4，每次写入都读回验证。

    read32  [0x03002730]                gIntrTable[4], 0x0800071D
    write32 [0x0203FC00] = 0x68014802   the stub
    write32 [0x0203FC04] = 0x60013101
    write32 [0x0203FC08] = 0x47004801
    write32 [0x0203FC0C] = 0x0203FC40   the counter's address
    write32 [0x0203FC10] = 0x0800071D   the handler being replaced
    write32 [0x03002730] = 0x0203FC01   the hook, THUMB bit set
    read32  [0x0203FC40]                the counter

这个钩子在每个游戏状态的每一帧运行一次：在 19995 帧内，它在菜单、标题画面、大地图、队伍菜单、野生战斗以及游戏内重启期间每秒计得 59.0 到 63.3 次调用。软重置会终止它：`InitIntrHandlers` 会重写入口 4 [main.c:339]（`gIntrTable[4]` 先读为零，然后为 0x0800071D）。神秘礼物只有在开机后才能到达，而开机会清空 EWRAM，所以如果某个 payload 必须在没有新会话的情况下保持存在，就需要把它的安装器放在存档中。

### 重置后再次安装它

`--gift resident-hook` 会发送一张神秘卡片，其神秘事件脚本通过 `initramscript` 把一个场地脚本绑定到玩家的妈妈身上。这个绑定保存在存档中，能在断电重启后继续存在（[那个唯一的 RAM 脚本槽](frlg_gift.md#the-one-ram-script-slot)）；在任何一次开机后与她对话就会安装该钩子，无需连接也无需主机。

`asm/field/install-vblank-hook.s`，68 字节，用 `setptr` 按每六个脚本字节一组暂存，并用 `callnative` 运行：占用 RAM 脚本体 995 字节中的 418 字节。

    read  gIntrTable[4]
    if it already names the stub: return, writing nothing
    write the five words of the V-blank stub to the staging area
    write the handler just read into the stub's fifth word
    zero the counter
    write the staging area, Thumb bit set, into gIntrTable[4], last

尾部跳转目标来自表格，所以这个钩子会链接到那里已有的任何处理程序。顶部的检查是必需的：安装两次会让 stub 尾部跳转到自身，从而在中断处理程序内死循环，并冻结大地图。

位于 `SaveBlock1 + 0x32E0` 的脚本块在重新掷出的指针下经过软重置仍能存活（已在模拟器上验证）。

每次安装时脚本都会重建代码，因此代码受限于一个脚本体：暂存 162 字节，或者约 755 字节附加在最后一条命令之后，并通过跳板到达。

### 大于脚本体的 payload

`asm/field/save-loader.s`，64 字节，是 RAM 脚本暂存的全部内容，无论 payload 有多大：它重新读取 `gSaveBlock2Ptr`，加上 0xB20，把 N 个字复制到暂存区，检查第一个字是否与某个魔数相匹配（一个从未写入过的存档，或者后来的卡片到达过的某个区域），然后跳入。它只使用 r0-r3，从不压栈，因此 payload 会直接返回到 `ScrCmd_callnative` 的调用者。

这个 blob 是 936 字节，正好一次 `save-write`（`MAX_SAVE_WRITE_BYTES`，即 1024 字节接收缓冲区减去写入器）：

    +0x000  magic 0x444C4B50
    +0x004  installer
    +0x054  the V-blank hook
    +0x068  filler
    +0x3A4  checksum over the filler

除非 filler 校验和正确，否则安装器不会安装任何内容（[证明其大小](frlg_rng.md#proving-the-size-rather-than-the-jump)）。

存档副本中钩子的尾部目标必须是测量到的 `VBlankIntr`，绝不能为零：加载器会覆盖一个可能正在运行的钩子，而且第二次访问时安装器发现钩子已安装，就不会打任何补丁。那里若是零，会在第二次对话后让主机崩溃成黑屏。

RAM 脚本占 995 字节中的 394 字节，无论 payload 是什么。`filler_B20` 保存 1024 字节，存档中其他未使用区域约 700 字节。更大的 blob 会在一次会话中按每份 936 字节、每次一个 payload 分块写入（[`save-write`](#save-write)）。在完整的 1024 字节下，blob 会到达 EWRAM 顶端，计数器会移入暂存区下方 84 字节。暂存副本除了钩子的第五个字之外与存档完全相同，而且每次安装暂存的字节都相同（已在模拟器上验证，计数器以每秒 60.0 次运行）。

### 调用封装器

GBA 代码通过 Sloop 系统调用到达 Switch 模拟器：在 `swi 0x40` 到 `swi 0x62` 之间有 23 个，其中 0x46、0x4E、0x52 以及 0x58 到 0x60 为空缺 [src/sloopsvc.c]。常驻 payload 可以发出其中任何一个：构建器会把一个 `swi N ; bx lr` 的 thunk 汇编进 blob，并把编号打上补丁。标记会在调用之前写入，因为一个不返回的系统调用不会留下任何其他可读内容：

    +0x00  0xB0B00001   the call was reached
    +0x04  the syscall number
    +0x08  0xB0B00002   it returned, and zero until it does
    +0x0C  r0, r1, r2, r3 as the syscall left them

`swi 0x54`，即 `svc_CommsAllowedByParentalControls` [sloopsvc.c:182]，在没有家长控制的主机上返回非零值。

#### 分派器及其跳转表

分派器位于 `main + 0x057014`，其跳转表位于 `main + 0x17D7F6`。它接受范围在 0x40..0x62 的 `N`：

    cmp   w2, #0x2b ; b.lo default       below 0x2B, the BIOS syscalls
    sub   w9, w19, #0x40 ; cmp w9, #0x22 ; b.hi default
    ldrh  w12, [table, w9, lsl #1]       a u16 word-offset from 0x05706C
    br    base + offset * 4

三十五个表项，二十三个不同的处理程序。`sloopsvc.c` 中命名的每个编号都有自己的处理程序。0x46、0x4E 和 0x58 到 0x60 共用默认处理程序，正好是反编译中的空缺。0x48 和 0x56 共用一个处理程序（`WriteSector`、`ReplaceSector`）；0x40 和 0x41 共用一个根据编号进行分支的处理程序。分派器的 `x0` 是 CPU 对象，`w2` 是编号，`x3` 是其处理程序读取的寄存器上下文：客户机的 `r0` 在 `+0x48`，`r1` 在 `+0x4C`（`0x52` 处理程序在 `mov x20, x3` 之后的 `ldp w1, w22, [x20, #0x48]`）。

默认处理程序是 `cmp w19, #0x2a ; cset w0, hi ; ret`。那个 `w0` 是封装器自己的“已处理”布尔值，而不是客户机的 r0，因此未实现的编号是惰性的（不会挂起），并且不会改动任何客户机寄存器。一个传入零并读取零的测试什么也没测到。

绝不要在 r0 未选定的情况下步进 0x40..0x62：0x48 和 0x56 需要扇区号和指针，0x4C 会完成保存，0x55 会交出 SaveBlock2 指针，而 0x43、0x57、0x61 和 0x62 需要参数。r0 中的标记会变成垃圾闪存源。

payload 在每次调用前重写自己的 `swi`（没有指令缓存），先写入编号，这样挂起时能自行指明是哪个编号，并在七个头字之后按编号记录 `r0`（35 个结果，140 字节）。`p_probe_num_step` 步进编号；`p_probe_a0_step` 在编号步进为零时步进 `r0`。

| 编号 | r0 输入 | r0 输出 |
| --- | --- | --- |
| `swi 0x52` | `0xA5A00052` | `0` |
| `swi 0x53` | `0xA5C00052` | `1` |
| `swi 0x54` | `0xA5E00052` | `1` |
| `swi 0x55` | `0xA6000052` | `0xA6000052`，不变 |
| `swi 0x56` | `0xA6200052` | 封装器发生故障 |

`swi 0x56`（`ReplaceSector`）在目标被区域表拒绝（r0 中是标记）时，会在 `0xFF8`（`main+0x573F8`）处使模拟器发生故障，且存档不受影响：

    Invalid memory access at virtual address 0x0000000000000FF8
    PC  = main+0x573F8     LR = main+0x573EC
    x19 = 0x56                  the syscall number
    x22 = 0xA6200052            the guest's r0
    x13 = 0x0203FFC2            the guest's PC, the halfword after the thunk's `swi`
    x03 = 0x655DB09BE8          0x2D0 above the object 0x52's index 45 resolves to

日志把 `0x0855D3F8` 标记为 `gba-app:0x573f8`，由此可知 `main` 基地址为 0x08506000。

#### `swi 0x52` 和 `swi 0x55`：内存总线

0x52 有一个反编译中缺少的处理程序，位于 `main + 0x05728C`：

    ldp   w1, w22, [x20, #0x48]     guest r0 into w1, guest r1 into w22
    lsr   x9, x1, #0x15             r0 >> 21
    ldr   x8, [x21, #0xe0]!         the region table
    and   x9, x9, #0x7f8            bits 3..10, so x9 is a BYTE OFFSET, not an index
    add   x8, x8, x9
    ldr   x0, [x8, #0x50]           the object for this selector
    ldr   x8, [x0]                  its vtable
    ldr   x8, [x8, #0x48]           slot 9
    blr   x8
    mov   x0, x20 ; mov w1, wzr ; mov w2, wzr ; b 0x0855D584

返回值会被丢弃：`main + 0x057584` 处的写回收到的是 `w1 = wzr`，所以客户机读到的 r0 始终为 0，r1 到 r3 不变。从大地图中，在 selector 45 到 54 范围内（`r0` 按 `1 << 21` 步进），`swi 0x52` 返回 r0 = 0，并且不改变 r1 到 r3 以及存档。`main + 0x057304` 处的 `swi 0x55` 用同样的移位索引同一张表，调用 slot 9，并通过 `main + 0x057588` 退出，后者跳过写回；这就是它返回 r0 不变的原因。

要读取对象和目标，在 `blr x8` 处停下，即 `main + 0x0572AC`（虚拟地址 `0x0855D2AC`）：`x0` 是对象，`x8` 是 slot 9 的目标，`w1` 是客户机 r0。再过一条指令，返回值仍在 `x0` 中。要遍历全部 256 个表项，在 `ldr x8, [x0]` 处停下，即 `main + 0x0572A4`，此时尚未解引用任何内容：空对象或未映射对象会在这里发生故障。

`0x7f8` 在一条指令中同时完成掩码和缩放：

    entry = (r0 >> 24) & 0xFF        and the byte offset is entry * 8

把它读作 `(r0 >> 21) & 0xFF` 会让每个表项变成正确值的八倍。`r0` 是 GBA 地址，而这张表就是内存总线：最高字节选择区域，slot 9 是它的地址折叠。
| entry | region | object | slot 9 |
| --- | --- | --- | --- |
| 0x00 | BIOS | 自身 | `and w0, w1, #0xffffff` |
| 0x01 | 未映射 | 默认 | `and w0, w1, #0xffffff` |
| 0x02 | EWRAM，256 KB | 自身 | `and w0, w1, #0x3ffff` |
| 0x03 | IWRAM，32 KB | 自身 | `and w0, w1, #0x7fff` |
| 0x04 | I/O | 自身 | |
| 0x05 | 调色板，1 KB | 自身 | `and w0, w1, #0x3ff` |
| 0x06 | VRAM，96 KB | 自身 | `and w8, w1, #0x1ffff`, then `0x18000..0x1FFFF` folded down by `0x8000` |
| 0x07 | OAM，1 KB | 自身 | `and w0, w1, #0x3ff` |
| 0x08, 0x09 | ROM 等待状态 0 | 一个对象覆盖两者 | `ldr w8, [x0, #0x34] ; and w0, w8, w1`, the cartridge's size mask |
| 0x0A, 0x0B | ROM 等待状态 1 | 一个对象覆盖两者 | same vtable |
| 0x0C | ROM 等待状态 2 | 自身 | same vtable |
| 0x0D | 等待状态 2 顶部，EEPROM 所在处 | 自身 | the default vtable |
| 0x0E | SRAM | 分配时与其他所有区域对象隔离 | |
| 0x0F | SRAM 镜像 | 自身 | |
| 0x10 到 0xFF | 未映射 | 默认 | `and w0, w1, #0xffffff` |

条目 0 到 15 给出 14 个对象和 11 个 vtable。VRAM 折叠就是硬件镜像（`0x18000` 读取 `0x10000`，`0x1FFFF` 读取 `0x17FFF`）。默认对象是 `0x655DB09918`，vtable 为 `main + 0x1C1FB0`，slot 9 为 `main + 0x01F7D8`；其 slot 10 为 `mov x0, xzr ; ret`，11 为裸 `ret`，2 为两次存储的 setter。每个 vtable 在 `-0x08` 处都有空 typeinfo 指针：没有 RTTI，也没有类名。

EWRAM 的 vtable `main + 0x1C21A0`（`x0` 为区域对象，`x1` 为周期计数器，`x2` 为地址，`x3` 为值）：

| slot | 作用 |
| --- | --- |
| 2 | 将两个字存储到对象的 `+0x24` 和 `+0x2C` |
| 3、4、5 | 读取 16、32 和 8 位 |
| 6、7、8 | 写入 16、32 和 8 位 |
| 9 | 将地址折叠进该区域 |
| 10、11 | 返回 null，以及一个空操作 |

访问器会先计入周期计数器（半字或字节为三，字为六），然后索引位于 `+0x10` 的主机后备指针。大小在 `+0x20`，ROM 大小掩码在 `+0x34`。

七个 syscall 会到达该表（0x45、0x47、0x48 与 0x56、0x4D、0x52、0x55、0x62），并且每个都只调用 slot 9；读写访问器属于模拟器的 CPU 核心。`swi 0x62` 是四条递增计数器的指令。

处理例程的边界应按其自身控制流来界定：若干处理例程在最后一个表项之后带有线外延续代码，若以下一个处理例程的起始地址来界定，就会将其错误归属。

### Flash 扇区路径

`swi 0x48` 和 `swi 0x56` 共享位于 `main + 0x057084` 的处理例程，延续代码位于 `main + 0x057364`。客户机 `r0` 是 4 KB 扇区号，客户机 `r1` 是源：

    source      = r1, resolved through the region table and folded
    destination = 0x0E000000 + r0 * 0x1000, resolved the same way

目标地址按 32 位算术形成 [main + 0x05737C]：`0x0E000000 + ((r0 & 0xFFFFF) << 12)`，区域条目是该地址的最高字节 [main + 0x057384]：`0x0E + ((r0 & 0xFFFFF) >> 12)` mod 256，因此 `r0` 选择区域。位于 EWRAM、IWRAM 或卡带缓冲区中的目标会通过两项边界检查（`fold < size`、`size - fold >= 0x1000`）；当 `r0 = 0xFA000 + n` 时，目标会折叠到 ROM 副本中 `n * 0x1000` 处的 4 KB（`n` 为 0..0xFFF），且可来自任意源区域。

ROM 目标是写入卡带缓冲区的一次实时写入；这是在模拟主机通过 IP 主机连接、并使用打过补丁的 Ryubing 构建测得的（未接触实机）：当 `r0 = 0xFA3FF`（`dest` 为 0x083FF000，`n` = 0x3FF，区域条目 0x08）且 EWRAM 源为（`r1` 0x0201C400，fold 0x1C400，mask 0x3ffff）时，两处边界检查都通过，复制落地：卡带缓冲区中 0x3FF000 处的字节精确地变为源自身的 0x1000 字节（所选模式的前 200 个字位于 0x3FF000..0x3FF31F，随后源在 0x3FF320+ 处的尾部字节被一并带入，例如第 200 个字在两处均为 0x11111000）。随后客户机在 0x083FF000 处的加载会通过折叠后的 ROM 窗口读取到该模式。主机会话保持：载荷返回 1，`client->param` 携带该模式自身的第一个字，主机打印成功消息并干净地关闭连接。

以同样方式复制的代码可以执行。当源的第 0 个字是两条指令的 THUMB 例程（`0x47706001`：`str r1,[r0]; bx lr`）、第 1..199 个字是模式时，复制完成后载荷读回折叠处（`0x47706001`，该例程），并以 `r1` 中的 nonce 和 `r0` 中自身结果字的地址分支到 `0x083FF001`：主机的应答携带该 nonce，因此包装器的指令取指读取的是该 syscall 写入的同一片实时后备存储，复制的字节通过正常取指路径作为代码运行。会话以成功消息结束，游戏已保存。

该写入在软复位后仍然存在。按 A+B+START+SELECT 后，通过调试器读回折叠处 0x3FF000 的同一 4 KB，字节完全相同（4096 字节中 0 个变化），而 EWRAM 源暂存区已被清除。复位后打开的第二个会话读取 0x083FF000（`0x47706001`），并以新的 nonce 分支到 0x083FF001；驻留例程返回该 nonce。完整重启应用程序会从模拟器的 ROM 文件恢复字节：新进程在该折叠处持有文件的原始字节。该写入的生存期就是模拟器进程的生存期。

如果区域在 `+0x10` 的后备指针为 null、折叠偏移达到或超过 `+0x20` 处的大小、或剩余字节少于 `0x1000`，则任一侧都会被拒绝（指针置为 null）。在复制 `0x1000` 字节之前，两侧都会先完成解析。随后 `swi 0x56` 在目标 `+0xFF8` 处存储 `0xFF`，且没有 null 检查：

    cmp   w19, #0x56
    b.ne  exit
    mov   w8, #0xff
    strb  w8, [x21, #0xff8]

`+0xFF8` 是扇区签名 [pokeldn/frlg/save/save_inject.py]：`0x08012025` 变为 `0x080120FF`，该扇区即作废。`ReplaceSector` 会写入并作废，`WriteSector` 只写入。被拒绝的目标会让 `x21` 保持 null，因此 `swi 0x56` 会在 `0xFF8` 处出错，即上述 abort。

在模拟主机上用 `swi 0x48` 测得：

| 调用 | 结果 |
| --- | --- |
| `r0` 为超出 flash 大小的扇区，`r1` 为未映射区域 | 未写入任何内容，flash 逐字节相同，无错误，无冻结 |
| `r0 = 30`，`r1 = 0x08000000`（ROM 头） | 扇区 30 变为卡带的前 4 KB，4096/4096 字节，相邻扇区未受影响 |
| `r0 = 30`，`r1` 为载荷填充的 EWRAM 缓冲区 | 扇区 30 变为那些字节；缓冲区读回不变 |
| `r0 = 0xFA3FF`（dest 0x083FF000），`r1` 为 EWRAM 缓冲区 | 复制落在卡带缓冲区：其折叠处 0x3FF000 的字节逐字节变为源的 4 KB；在 0x083FF000 的客户机读取返回该模式；会话干净结束 |
| 同一次复制，源的第 0 个字为 THUMB 例程，然后以 `r1` 中的 nonce 分支到 `0x083FF001` | 复制的例程返回该 nonce；主机显示成功、保存并干净关闭 |
| 软复位后，调试器读取同一折叠处 | 4 KB 逐字节匹配（4096 字节中 0 个不同），而 EWRAM 源暂存已被清除 |
| 复位后，第二个会话读取该例程，然后分支到 `0x083FF001` | 驻留例程返回新的 nonce，并在一个进程内跨复位保持可调用 |
| 完整重启应用程序后，调试器读取同一折叠处 | 折叠处恢复为 ROM 文件的原始字节；该写入的生存期是进程生存期 |

它不修改任何客户机寄存器，也不返回状态：只有一次 flash 读取才能区分被接受的调用与被拒绝的调用。

模拟器仅在游戏保存时提交其 128 KiB 的 flash 映像，并会连同外来扇区一起写入。syscall 写入后若强行终止，主机文件保持不变。来自神秘礼物会话内部的写入，在会话以成功消息结束（这会触发保存 [mystery_gift_menu.c:1379]）后才会持久化；在任何其他结果之后，以及来自驻留钩子的写入，都会等待下一次保存。

### 断点钩子

包装器的 GBA CPU 对象在 `cpu + 0x170` 处有 256 个钩子槽，每个 `bkpt` 立即数对应一个。ARM 解码在 `main + 0x01FCE4` 处测试 `(insn & 0xFFF000FF) == 0xE1200070`，THUMB 解码测试 `(insn & 0xFF00) == 0xBE00`；位于 `main + 0x01EFC0` 的 THUMB 处理例程通过 `main + 0x01F820` 调用 `imm8` 槽中钩子的 vtable slot 2（参数为 hook、`&insn`、`bkpt` 的地址、CPU）。钩子返回 1 时，核心会执行存储在 `insn` 中的指令；返回 0 或空槽时，`bkpt` 成为空操作。`main + 0x022A2C` 注册钩子并拒绝已占用的槽。有两个槽被填：

| slot | 属主 | 钩子 | 作用 |
| --- | --- | --- | --- |
| `bkpt #0x52` | Sloop 组件，vtable `main + 0x1C3878` | `main + 0x05499C` -> `main + 0x056368` -> `main + 0x03E850` | 下方的 librfu 补丁 |
| `bkpt #0xFF` | 应用程序对象，vtable `main + 0x1B4078` | `main + 0x001140` | 以参数 1 发布事件 `0x82EF0054`，从而退出应用程序 |

加载时，包装器会向客户机的 ROM 副本写入三个补丁；在 v0 和 1.0.1 上一样，这是 `0x08000000..0x09000000` 范围内与卡带仅有差异的十个字节（通过神秘礼物客户端对块校验和及一次读取验证，实机与模拟均如此）：

| 地址 | 卡带 | 客户机 |
| --- | --- | --- |
| `0x081E1696` | THUMB `mov ip, r1` (`468c`) | `bkpt #0x52` (`be52`) |
| `0x081E187C` | ARM `ldr r3, [pc, #0x50]` (`e59f3050`) | `bkpt #0x52` (`e1200572`) |
| `0x081E1F90` | ARM `mov lr, r0, lsr #14` (`e1a0e720`) | `b 0x081E1FB8` (`ea000008`) |

第三个补丁移除了一个等待循环。位于 `0x081E1F74` 的函数会根据调用者的 `r0`（`r0` 掩码为 u16，`lr = r0 >> 14`）轮询 `REG_SIOCNT`（`0x04000128`）的第 2 位，并在 `[*(0x03000030) + 0x10]` 处的字节为 1 时提前返回，将其清零并应答 1。在模拟中该轮询永不匹配，因此包装器将函数体替换为 `mov r0, #0; return`：该等待会立即应答 0。

`bkpt #0x52` 以地址为键：其钩子在 `+0x120` 和 `+0x148` 处持有两条记录 `{u32 pc, u32 original insn, ..., u32 hits at +0x0C}`，`main + 0x0546C0` 匹配地址并返回原始指令。在 `Sio32IDMain` 补丁（`0x081E1696`）处，它解析客户机 `r0`（`&gRfuSIO32Id`）并将 `0x8001` 存储到 `+0x0A`，即 `AgbRFU_checkID` 等待的适配器 id [librfu_sio32id.c]。在任何其他地址处的 `bkpt #0x52` 会将会话剩余时间内第二条记录（`0x081E187C` 补丁）重新指向该地址本身。

#### 记录解析器（`main + 0x03E850`）

钩子 `main + 0x05499C` 将 `bkpt` 本身写入 `insn`，然后以 `x0 - 0x60` 作为 `this` 调用 `[[x0 - 0x60] + 0x98]` 处的虚函数（反汇编见 `main + 0x549c4`-`0x549cc`）；对于 Sloop 组件，这会解析到 `main + 0x056368`，该函数推导出记录持有者 `[component + 0x40] -> [+0xA8] + 0x68`，并以它、`&insn`、`bkpt` 的地址和 CPU 作为参数尾调用解析器 `main + 0x03E850`（`0x3e850` 在映像中只有一个调用者，即 `0x56378`）。客户机 `r0` 的最高字节只在稍后选择区域，即下方解析器的 Sio32ID 仿真内部。解析器：
- 匹配记录 1（holder 位于 `+0x120`）直到 `main + 0x0546C0`：匹配会使 `+0x0C` 处的命中计数加 1，并把 `+0x4` 处的原始指令复制到 `insn` 中，随后由核心执行；
- 在记录 1 匹配时，继续进入 Sio32ID 仿真：guest 的 `r0` 通过区域表进行折叠，折叠后的偏移仅按 `offset < region size`（`+0x20`）做边界检查，并且当 holder `+0x108` 处的标志字节被设置时，`strh` 会将 `0x8001` 存储到 `backing + offset + 0xA`，而 `main + 0x2209C` 会把 `backing + offset + 1` 处的字节写入 guest 的 `r1`（`str w2, [regfile + 4 + 0x48]`）。边界检查没有覆盖 `+0xA`，因此如果 offset 位于某个区域的最后 `0xA` 个字节内，写入会越过该区域 backing 分配的末尾，最多超出其末尾 11 个字节；当标志设置且 offset 越界时，backing 指针为空，wrapper 会在读取地址 `0x1` 时出错。标志清零时，解析器直接返回而不进行写入。Holder `+0x108` 是 `[+0xA8] + 0x170`（holder 是 `[+0xA8] + 0x68`），与下面适配器电源开关是同一个字节：在主机自己的神秘礼物搜索期间，通过 `main + 0x03E850` 的三次实时读取每次都发现它为 `0x1`，所以仅 `swi 0x40` 就打开了写入路径。
- 在记录 1 不匹配时，重新指向记录 2（holder `+0x148`）：`record2.pc := the bkpt address`，然后匹配它，因此核心执行记录 2 的原始指令，而这个原始指令从未被更新：即陈旧的 `0x081E187C` 处的原始 `e59f3050`（`ldr r3, [pc, #0x50]`），在 guest 执行 `bkpt #0x52` 的任意地址、任意 CPU 模式下都会执行。在主机自己的神秘礼物搜索中，每次分派都会通过这条路径重新指向：三次实时读取中，记录 2 的命中计数（holder `+0x154`）每 0.33 秒大约增加 20，而记录 1 的命中计数没有变化，因此搜索画面每帧运行的是 STWI 驱动在 `0x081E187C` 的运行时 IWRAM 副本中的 `bkpt #0x52`，而不是 `Sio32IDMain` ROM 地址。
- 在记录 2 匹配且 `+0x108` 标志设置时，进入 `main + 0x03E954`：它折叠存储在 holder `+0x170` 处的地址，在折叠后的地址处读取一个字，并将该字的最高字节用作区域选择器，将该字本身用作再次折叠的地址，进行边界检查，同时递减 holder `+0x42B8 + 0x7C` 处的计数器。
- 在记录 2 匹配且 `+0x108` 标志清零时，进入 `main + 0x03E960`：它折叠存储在 holder `+0x170` 处的地址，在那里读取一个字，并将其第 15 到 26 位与 `0x600` 比较。如果匹配，则将该字的低 24 位通过同一个区域表折叠，进行边界检查，并递减 holder `+0x42B8 + 0x7C` 处的计数器；如果不匹配，则不执行任何操作。

guest 控制着整个触发过程：选择一个 `r0` 并跳转到 `0x081E1696`（补丁位置，THUMB）的载荷会让 wrapper 在 `fold(r0) + 0xA` 处写入 `0x8001`，并将 `r1` 设置为 `fold(r0) + 1` 处的字节；在其他任何地方执行 `bkpt #0x52` 的载荷则会在那里执行陈旧的 `e59f3050`。两者都是相对 guest 的；`+0xA` 写入是唯一一条离开 guest 区域的路径：它可以将两个固定字节 `0x8001` 写到任何区域 backing 分配末尾之后最多 11 个字节处，包括 16 MB ROM 副本的 backing。

#### ROM 缓冲区之后：Sloop 组件

ROM 对象的掩码（`+0x34`）为 `0x1ffffff`，而卡带占用 `0x1000000` 字节，因此折叠 `0xFFFFF6..0xFFFFFF` 会通过边界检查，并将写入放到紧跟 ROM 缓冲区之后的十个字节上。那里的对象是 Sloop 组件（[断点钩子](#the-breakpoint-hooks)）：其第一个字是 vtable 指针 `main + 0x1C3878`，`+8` 为 `0x000004bf`，`+0xC` 为 `0x0A828400`，`+0x18` 和 `+0x20` 为 `main + 0x16EB83`，`+0x28` 是一个 `0x655db` 堆指针，`+0x60` 和 `+0x88` 是另外两个 vtable（`main + 0x1C3948`、`main + 0x1C3978`），`+0xE0` 是 CPU 总线对象。

邻居对象在每次启动之间会发生变化：某次启动时 ROM 的邻居是一个对象，其第一个字是 vtable `main + 0x1C36D8`，其 `+0x60` 是 vtable `main + 0x1C3790`。构造函数 `main + 0x547CC` 写入的正是这一对值，它读取 `main + 0x86D67E8` 处的静态指针（加数为 `main + 0x1C36C8` [main_relocs.json]）。该类的字段由其自己的构造函数和自己的代码写入；guest 会话中的任何存储操作都无法到达这些字段。

在补丁位置，卡带自己的代码会暂存自己的 `r0`（`ldr r0, [pc, #0x10]` 加载 `0x0300744A`，即它自己的 `&gRfuSIO32Id`，位于 IWRAM），因此游戏自身的分派总是折叠到游戏自身的结构体：wrapper 的 `0x8001` 存储就是到达 `gRfuSIO32Id.lastId` 的适配器 ID（`RFU_ID = 0x8001` [librfu.h]），也就是 `AgbRFU_checkID` 等待的值。直接跳转到 `0x081E1696` 的载荷会跳过那次加载并暂存自己的 `r0`，这就是使存储位置发生移动的原因。

在 `strh` 本身（`main + 0x3E928`）及其后续路径上进行插桩：使用直接跳转且 `r0 = 0x08FFFFF6` 时，store 的 `x8` 为 `backing + 0xFFFFF6`（`0x66209f9ff6`，其后的尾部 `ff` 填充），而存储前后的转储显示 `0x66209fa000` 在存储之前为 `78 98 6c 08 ...`，之后为 `01 80 6c 08 ...`：两次存储相隔约 90 毫秒（一次来自载荷的触发，另一次是通过同一位置、使用暂存的 `r0` 进行的第二次分派）。

覆盖组件前两个字节的写入会把 vtable 指针替换为 `0x086C8001`，随后分派器 `main + 0x1F820` 会从该处读取钩子槽 19（偏移 `+0x98`）：`main + 0x1C2099` 处的八个字节是 `f7 01 00 00 00 00 00 00`，因此 wrapper 的下一次虚调用会在 guest PC `0x1F7` 处执行，这是一个任何 guest 路径都无法到达的未映射地址。在模拟器上，这会使进程中止（`Unhandled guest exception InstructionAbortLowerEl`）；而当折叠位于某个区域内时，同一个触发只会以本地折叠写入结束会话，不会发生这样的分派。该位置卡带自己的代码排除了另一个候选：`mov ip, r1` 将 `ip` 作为值存储（`mov r0, ip; strh r0, [r4]`），从未被跳转调用。

钩子仅在 `[component + 0x40] -> [+0xA8] + 0x170` 处的字节被设置时起作用：这是虚拟适配器的电源开关。`swi 0x40` 将其设置，`swi 0x41` 将其清零（处理函数 `main + 0x05706C` 存储 `number == 0x40`；[sloopsvc.c:23] 中的“未引用标志设置器”）。在神秘礼物菜单中执行 `swi 0x41` 会停止 RFU 帧：游戏会触发链接错误并离开 LDN。适配器在软复位后保持关闭状态，因此下一个无线菜单会报告 "L'adaptateur sans fil GBA n'est pas connecté"。该字节在软复位后仍然存在；重新启动游戏或执行 `swi 0x40` 可以将其恢复。它每帧都会被读取：在同一个载荷中先执行 `swi 0x41` 再执行 `swi 0x40` 是无害的。

#### 从 bkpt 到解析器的链

NSO 的 vtable 槽在文件中保存的是未重定位的加数；加载器会加上映像基址（`main` 位于 `0x8506000`）。应用该基址后，guest 的 `bkpt #0x52` 会执行以下链：

- 两条解码路径（THUMB 的 `main + 0x1EFE0`，ARM 的 `main + 0x1B7B8`）都会以 `(CPU, bkpt address, immediate, &insn)` 的形式调用分派器 `main + 0x1F820`；
- 分派器取出 hook = `[CPU + (imm & 0xff) * 8 + 0x170]`；对于 `bkpt #0x52`，这就是 `component + 0x60`，即该组件的一个子对象（该组件就是 GBA CPU 对象：`+0x84` 是当前 pc，`+0x170` 是钩子表，`+0x960` 是第二个总线表，`+0xE0` 是总线对象）。它读取钩子自身的 vtable（`main + 0x1C3948`）的 `+0x10` 槽，并以 `f(hook, &insn, bkpt address, CPU)` 的形式调用它。槽 `+0x10` 直接就是 `main + 0x5499C`；
- `main + 0x5499C` 将 `0xE1200572` 写入 `insn`，然后加载 `[component]` 并以 `(component, &insn, bkpt address, CPU)` 尾调用 `[该指针 + 0x98]` 处的虚函数：`main + 0x1C3878` 的 `+0x98` 槽是 `main + 0x56368`，后者会派生记录持有者并到达解析器 `main + 0x03E850`。

因此，覆盖组件前十个字节的存储会在 `+0x98` 槽处被消费；`+0x10` 的读取发生在钩子子对象上，在那十个字节之外。解析器的写入目标是 `buffer_data + fold + 0xA`，其中 fold 是所选区域的槽 9（[`swi 0x52` 和 `swi 0x55`：内存总线](#swi-0x52-and-swi-0x55-the-memory-bus)）。

#### 跨区域边界的写入会做什么

当 `fold = size - 0xB`（在范围内）时，写入对为 `(size-1, size)`：区域的最后一个字节得到 `0x01`，相邻分配的第一个字节得到 `0x80`。当 `fold = size - 0xA` 时，写入对为 `(size, size+1)`：`0x01 0x80` 写到邻居的前两个字节上。一次神秘礼物会话每次访问只允许选择一个 fold。

该位置后面的函数体通过一个五字的栈帧返回：它在 `0x081E177C` 处的尾声是 `movs r0,#0 ; pop {r4,r5,r6,r7} ; pop {r1} ; bx r1`。跳转到该位置的载荷会跳过函数序言，必须自己压入这个栈帧，并将 `lr` 设置为某个继续地址；然后函数体会返回载荷，载荷可以继续运行更多代码并正常结束会话。压入其他任何栈帧的载荷则会通过其调用者的栈展开返回，而且实测运行中会以同一个暂存的 `r0` 重新进入该位置。

窗口 4，也就是 GBA IO 寄存器，映射到一个 0x400 字节的区域对象，该对象紧邻其自己的 backing 分配之后：backing 位于 bus `+0x14C0`，对象位于 bus `+0x18C0`，按键中断子对象嵌入在对象 `+0x88` 处。因此，写入会落在总线每次 IO 访问都要经过的那个对象上。映像的 CPU 核中有 210 个访问器形态的调用点（[`swi 0x52` 和 `swi 0x55`：内存总线](#swi-0x52-and-swi-0x55-the-memory-bus)）。

在模拟输出的主机上：

| 写入 | 读取位置 | 结果 |
| --- | --- | --- |
| 组件字节对 `01 80`（`0x086C8001`） | 在 `main + 0x1C2099` 处读取的 `+0x98` 槽，未重定位，`0x1f7`（[上文](#what-follows-the-rom-buffer-the-sloop-component)） | |
| 组件字节 0 `0x80`（`0x086C9880`） | `main + 0x5492C`，同一个方法但没有 `-0x60` | 它会在仍被改写的组件上再次读取 `[x0] + 0x98` 并递归调用自身；线程栈耗尽，进程因数据中止（`InvalidMemoryRegionException`）而终止 |
| IO 对象字节 0 `0x80`（`0x086C8480`） | 总线的存储槽 `+0x38`/`+0x40`，被替换的目标是原始的 `0xffffffffffffe5e0` 和 `0` | 写入后的第一个 IO 存储会在约 30 毫秒内使进程中止；加载目标（`main + 0x30EAC`、`main + 0x31114`、`main + 0x36D54`）永远不会运行 |
| name-hash 块字节 0（`0x80`） | 该块是一个 SDK binder/surface 描述符对象（`android.gui.IGraphicBufferProducer` 等是 SDK 映像中的静态字符串），而不是被分派的对象 | 没有反应；游戏一直运行到自己干净退出 |

写入 `0x086C8080`（字节为 `80 80`：之后每个 `bkpt #0x52` 都会运行纯计数器 getter `main + 0x1F7F0`，因此每个 bkpt 都变成空操作）需要两次写入，且中间不能有分派；一次会话只允许一次写入，而途中的两个单写入状态都会终止进程。如果改为通过调试器写入，该指针会保持五分钟，游戏运行且进程存活。映像中没有任何代码位置会在初始化之后写入 wrapper 对象的头部。

#### 单次写入能形成的每种放置

单次写入会在邻居上留下两种字节模式之一：`80` 写在其第一个字节上（区域自己的最后一个字节得到 `01`），或者 `01 80` 写在第 `k` 和 `k+1` 个字节上，其中 `k` 在 0..9 之间。邻居的前八个字节是其 vtable 指针，因此使用者随后读取的指针会相对于文件映像及其重定位进行解析。有四种放置会读取活动的主内存：

| 对象 | 写入的字节 | 被改写的指针 | 使用方 |
| --- | --- | --- | --- |
| 组件（vtable `main + 0x1C3878`） | `80` 在 +0 | `0x086C9880` | `bkpt #0x52` 链的 `[P + 0x98]` = `main + 0x1C3918` = `main + 0x5492C` |
| 组件 | `01 80` 在 +0..1 | `0x086C8001` | `[P + 0x98]` = `main + 0x1C2099` = 原始 `0x1F7` |
| IO 对象（vtable `main + 0x1C2408`） | `80` 在 +0 | `0x086C8480` | 总线访问器槽，见下文 |
| IO 对象 | `01 80` 在 +0..1 | `0x086C8001` | 总线访问器槽：`0x1F7`、零、原始加数 |
其他放置解析到镜像之外。`01 80` 在 +1 处给出 `0x08800178`（组件）和 `0x08800108`（IO 对象），位于 main 的 bss 内。零填充的 bss 模型预测此处为一次空调用；仅凭文件镜像无法确定实时会话期间的内容。`01 80` 在 +2 到 +7 处会移动字节 2 或字节 3，因此消费者的读取本身会出错。在 +8 和 +9 处，这对字节落在 `+8` 处的字段上（组件的 `0x000004BF` 在 +8 处变为 `0x00008001`，在 +9 处变为 `0x008001BF`），而 vtable 指针保持原位，因此分派使用的是对象自身的方法。

当两次站点访问之间没有 `0x04` 访问时，它们可以在 IO 对象上组合各自的字节对；载荷从 ROM 或 EWRAM 取指本身不会访问该对象。重复同一放置是幂等的，并且在 +8 或 +9 处写入不会改变 vtable 指针。仅涉及字节 0 和字节 1 的不同放置仍可能留下上述某个镜像内指针；改变更高指针字节的组合需要单独分析。

在组件上，下一个 `bkpt #0x52` 会消耗当前写入。在链路开启时，STWI 驱动每秒产生约 60 次此类调用，但仅凭该速率并不能确定每次载荷访问之间都有调用介入。

按总线槽位列出的 IO 对象重写块。访问类别来自调用者的结果掩码（16 位加载使用 `main + 0x18378` 处的 `and #0xffff`，32 位加载使用 `main + 0xBDB8` 处的字旋转，8 位加载使用 `main + 0xD914` 处的 `and #0xff`）。

| bus slot | access | rewritten target | with the IO object as `this` |
| --- | --- | --- | --- |
| `+0x18` | 16 位加载 | `main + 0x30EAC` | 按键处理器的默认分支：`w2` 是完整的 `0x04xxxxxx` 地址，高于处理器所切换的所有寄存器 id，因此它将 `w3 & 0xffff` 存储到 `[x1]`；`main + 0x18330` 处的调用点传入 `x1 = CPU + 0x20` 和 `w3 = 1`，访客的加载返回处理器遗留的 `w0` |
| `+0x20` | 32 位加载 | `main + 0x31114` | 以 `(x1 来自站点，IO + 0x20)` 调用 `main + 0x3580C`，然后以 `x0 = [[IO + 8] + 0x90]` 尾调用 `main + 0x22404` |
| `+0x28` | 8 位加载 | `main + 0x36D54` | 一个 0x76000 字节对象的清理族：`[x0 + 0x76C70]`、`+0x76C30`、`+0x76C00`、`[x0 + 0x4E68]` |
| `+0x30` | 存储 | `main + 0x36E40` | `x0 -= 0x1A10`，然后 `main + 0x3664C`，在重定位后的指针上使用同一清理族 |
| `+0x38` | 存储 | 原始 `0xFFFFFFFFFFFFE5E0` | 调用出错 |
| `+0x40` | 存储 | `0` | 空调用 |
| `+0x48` | | `main + 0x36E4C` | 在 `+0x76C60`、`+0x76C20`、`+0x76BF0`、`[x0 + 0x4E58]` 处的清理族 |
| `+0x68` | | `main + 0x310A8` | `x0 -= 0x10`，然后 `main + 0x30EAC` |

以上放置均未到达由访客内存提供的分派目标：四个位于 main 内的放置读取 main 自己的数据，而 IO 对象的块以总线的参数调用 main 自己的处理器。

在零售机上（Switch Lite，英文火红，载荷由 XIAO ESP32S3 无线电通过 LDN 投递），组件写入与范围内写入是由链路拆除行为区分的，而不是通过屏幕。每次运行在脚本执行约两秒后返回 HOME，并显示“The software was closed because an error occurred”，因此该消息是通用提示；而优雅的 Pia 离开（`Session type 3`）则不是：

- 当折叠位置越过卡带缓冲区一个单位时（组件，`r0 = 0x08FFFFF6`），主机离开 LDN 时没有 `Session type 3`（标签 `pl01`、`pl04`）——即模拟器分派所显示的突然中止，如今发生在硬件上；
- 当折叠位置在范围内时（`r0 = 0x08FFFFF0`，标签 `pl03`，写入缓冲区 `+0xFFFFFA`）以及当 EWRAM 末尾越界落到 VRAM 时（`r0 = 0x0203FFF6`，标签 `pl02`），主机发送了 `Session type 3` 并优雅离开；普通卡带会话（`scratchpad/re1_host.log`、`rt02`..`rt04`）也是如此。

因此，当折叠位置越过 ROM 缓冲区末尾时，记录解析器的存储会在零售机上触及一个活跃的包装器对象，应用在此处中止；而同样的存储若停留在访客可见内存中则不会。将主体帧压栈的载荷在零售机上也会从该站点返回。

写入后的分派是应用的下一个 `bkpt #0x52`。游戏从两个地方产生这些断点：STWI 驱动的 IWRAM 副本（链路开启时约每秒 60 次，来自对其命中计数的实时读取），以及它在站点处对 `Sio32IDMain` 的自身调用（对记录 1 的实时读取中有 12 次命中）。当 vtable 的低字节为 `0x80` 时，该分派到达 `main + 0x5492C`，它会在重写后的指针上重新读取 `[component] + 0x98`，并递归直到线程栈离开其区域；主机返回 HOME 且没有 `Session type 3`。一个载荷将卡带自身的指令放回 IWRAM 副本的 `bkpt #0x52` 之上，并还原卡带副本的两处加载时补丁（通过 `swi 0x48` 覆盖包含两个站点的 4 KB 块），就移除了这两个来源：主机随后显示游戏自身的通信错误，以 `Session type 3` 离开 LDN，提交网络报告并继续运行。在该状态下，被写入的指针是惰性的，不会被修复：没有任何代码位置会恢复 vtable。还原后的卡带副本同样具有进程生命周期状态：无线菜单随后报告适配器未连接，而完全重启会重新应用包装器的加载时补丁。

### 覆盖范围

本页映射的访客路径包含一次越过区域后备存储的存储：解析器在 `fold + 0xA` 处的 `0x8001` strh；重写指针的读取者从 `main` 自身数据在静态地址处获取其目标（[单次写入能形成的每种放置](#every-placement-a-single-write-can-make)）。读取活跃内存的四种放置以及所有其他放置所留下的内容都列在那里；在低字节 `80` 写入后的会话期间，组件的消费者是 `main + 0x5492C`，来自 `bkpt #0x52` 钩子链。单次写入调查未发现由访客字节提供的调用目标；它并未覆盖所有写入序列。移除链条的两个访客来源后，观察到的分派停止了。系统调用对组件的存储及其读取者位于[其余系统调用](#the-remaining-syscalls)中；`main + 0x1C36C8` 类的字段由其自身的构造函数和自身代码写入（[ROM 缓冲区之后是什么：sloop 组件](#what-follows-the-rom-buffer-the-sloop-component)）。第三处加载时补丁替换了一个等待循环。坏词过滤器的两个缓冲区在分派器自身的帧内进行了长度限制（[坏词过滤器](#the-bad-word-filter)）；闪存扇区路径的边界见[闪存扇区路径](#the-flash-sector-path)。

Pia 一侧的两端都已解码：访客的 `RfuGameData` 和用户名被重新打包进广播记录并进行 base85 编码（[广播记录](#the-advertisement-record)）；对端的 `NetworkInfo` 字节原样到达候选列表（[包装器自己的扫描管线](#the-wrappers-own-scan-pipeline)）；对端的会话消息在处理器读取之前通过了按类型区分的边界检查（[Pia 会话消息分派器](#the-pia-session-message-dispatcher)）。接下来的[线路解析小节](#the-pia-librarys-own-wire-parsing)追踪静态链接的 `PiaCommon-6_42_1` 路径，从 UDP 套接字到会话队列；该追踪只映射路径，并未覆盖其中的每项长度检查和消息处理器。

#### 其余系统调用

处理器地址为 `main + 0x05706C + entry * 4`，取自 `main + 0x17D7F6` 处的跳转表。最后一列是神秘礼物客户端在使用 `sloop-svc` 时某一次问题所显示的内容。
| swi | handler、callee | 作用 | 单次执行观察结果 |
| --- | --- | --- | --- |
| 0x40, 0x41 | `main + 0x05706C` | 适配器电源开关：将 `r0 == 0x40` 存储到 `[component + 0x40] -> [+0xA8] + 0x170` | 从神秘礼物菜单发起 swi 0x41 会引发链接错误并退出 LDN（[上文](#what-follows-the-rom-buffer-the-sloop-component)） |
| 0x42 | 模式切换 `main + 0x0588A0` | `rfu_REQ_startSearchChild` [sloopsvc.c:49]；将网络管理器设为模式 2 | 以链接错误结束会话；未打开接入点 |
| 0x43 | `main + 0x0570EC` -> `main + 0x058AD0` | `rfu_REQ_startConnectParent`，`r0` 中为 16 位 PID [sloopsvc.c:91]；相同的模式切换 | 缓冲脚本应答，然后在关闭时显示 `"Erreur de connexion"` |
| 0x44 | `main + 0x057100` -> `main + 0x058B0C` | `rfu_REQ_stopMode`，无参数 [sloopsvc.c:102] | 在 0x43 之后，无可观察变化 |
| 0x45 | `main + 0x057110` -> `main + 0x058900` | `rfu_REQ_startSearchParent`，`rfu_STC_readParentCandidateList` 使用 `&gRfuLinkStatus` [sloopsvc.c:67-75]；将包装器的扫描结果通过区域表复制到 `struct RfuLinkStatus`，`findParentCount` [include/librfu.h] 先位于偏移 8 | 220 个清零字节保持为零（在礼物会话中没有父搜索） |
| 0x46 | 跳转表项 `0x147` | 落入分派器的退出：该系统调用什么也不做 | |
| 0x47 | `main + 0x05715C` -> `main + 0x058680` | `rfu_REQ_configGameData`，`r0` 指向 `struct RfuGameData`（16 字节）和用户名（8，`RFU_USER_NAME_LENGTH`）[sloopsvc.c:34-46; include/link_rfu.h:103-115,232]；若发生变化，将所有 24 字节复制到 `component + 0x6050D8`，并将 `activity`（第二个 64 位字的第 16–22 位）复制到 `component + 0x605360` | `activity` 0x30 逐字节落在两处 |
| 0x48, 0x56 | `main + 0x057084` | 闪存扇区复制：目标扇区为 guest `r0`，源为通过同一区域表折叠的 `fold(guest r1)`，并对区域大小进行边界检查，最多 4 KB | [闪存扇区路径](#the-flash-sector-path) |
| 0x49 | `main + 0x0571A8` -> `main + 0x0588D0` | 在 `component + 0xD0` 对象上调用 `main + 0x0588D0`；不接受 guest 参数 | 返回 0 |
| 0x4A | `main + 0x0571B8` -> `main + 0x058AB8` | 在 `component + 0xD0` 上的相同形状 | 返回 0 |
| 0x4B | `main + 0x0572C4` | 无参数；位 1 使 `RfuMain1` 从 `gHostRfuGameData->compatibility.playerTrainerId` 重新播种 RNG，位 0 清零使 `SpawnGroupLeaderAndMembers` 对队长提前退出 [sloopsvc.c:132-145] | 0 |
| 0x4C | `main + 0x0571CC` | 在 `[component + 0xE8] + 0xA0` 上调用 `main + 0x05D930`，当其应答为 0 时在全局指针上调用 `main + 0x049D28`；guest 数据不会到达这两者 | 返回 0 |
| 0x4D | `main + 0x0571FC` | 脏话过滤器：解析 `r0` 并最多读取 256 字节于 `fold(r0)`，[下文](#the-bad-word-filter) | |
| 0x4E | 跳转表项 `0x147` | 落入分派器的退出：该系统调用什么也不做 | |
| 0x4F | `main + 0x057248` -> `main + 0x058B54` | 在其栈上构建 `{u16 tag 0x4757; u32 value = r0}`；带标签属性分派器 `main + 0x4EBD0` 和设置器 `main + 0x058BB4` 将未验证的值存储到 `component + 0x6052A0` | 写入 3 和 `0x7FFFFFFF`，各自后跟 0x49 和 0x4A，无可观察变化 |
| 0x50 | getter `main + 0x058BA4` | 读回同一个 4 字节计数 | |
| 0x51 | `main + 0x057270` -> `main + 0x0511BC` | 将 `component + 0x3404` 读入输出参数并清零；输出参数始终是分派器自身的栈槽 | |
| 0x52 | `main + 0x05728C` | 通过总线对象的区域表（`[component + 0xE0] + 0x50`）折叠 guest `r0`，并调用区域的 `+0x48` 折叠。非零 guest `r1` 还会运行指针解析器 `main + 0x562CC`：它读取 `[[bus] + 0x50 + (r1 >> 24) * 8]`，索引无界 0..255，调用值的 `+0x48` 作为虚方法，然后在 `offset < size` 时返回 `backing + offset`。该处理程序是解析器的唯一调用者，丢弃其结果并返回 `r0 = 0`，因此 guest `r1` 读回 0。读到的 256 个活动条目是 main 自身的方法指针、负值和零，没有一个具有 `+0x48` 方法的对象 | |
| 0x53 | `main + 0x0572D4` | 应答 `component + 0x2770 == 0`（通过 `[component + 0xD0]`） | |
| 0x54 | `main + 0x0572EC` | `svc_CommsAllowedByParentalControls` [sloopsvc.c:182] | 返回 1 |
| 0x55 | `main + 0x057304` | 将 `r0` 存储到 `component + 0xE1BC`，将存储的字通过区域表折叠并读回一个字节（[游玩报告由哪些内容构建](#what-the-play-reports-are-built-from)） | |
| 0x57 | `main + 0x057330` | `MonsSelect` 到 `component + 0x140` 处的报告副本 | |
| 0x58 至 0x60 | 跳转表项 `0x147` | 落入分派器的退出：该系统调用什么也不做 | |
| 0x61 | `main + 0x057340` -> `main + 0x058B2C` | `svc_SetActivity`；仅对 0x41 到 0x48 的 Union Room 活动代码将 `r0` 写入 `component + 0x605360` | 0x45：在 callee 的 `ret`（`main + 0x058B50`）处断点读取 `w1` 和字段为 0x45；正常关闭 |
| 0x62 | `main + 0x057354` | 将 `component + 0xE1B0` 加 1，即下一份报告的 `CommsError` | |

应答通过 `main + 0x2209C` 返回：当编号大于 0x2A 时，guest `r0` = 1；guest `r1` = 处理程序的应答字。没有任何处理程序的应答携带包装器地址。

`component + 0x6052A0` 占 16 字节：一个 4 字节计数、4 字节未使用、一个指向 `main` 的 8 字节指针。刚启动时：计数为 1，指针为 `main + 0x1E8D20`，是一个指针数组，已填充的槽位后跟两个空值。

带标签属性分派器 `main + 0x4EBD0` 遍历组件上的监听器列表：条目大小为 `0xd0`，位于 `component + 0x10`；计数位于 `+0x688`；启用字节位于 `+0x690`；对于第一个字为 2 的每个条目，它调用组件 vtable 槽 `+0x50`，传入 `entry - 8` 处的 8 字节和带标签条目。设置器 `main + 0x058BB4` 是 `0x4757` 监听器。`main + 0x50618` 处的 `0x59` 监听器将 `[tagged entry + 4]` 处的值写入 `component + 0x3324 + index * 4`，索引从 `[x2]` 读取并由 `main + 0x4DB0C` 限制在 0..7。没有任何系统调用构建 `0x59` 条目或提供该第三参数，分派器的十二次调用都由包装器内部字段构建条目。`0x4757` 监听器存储在 `component + 0x6052A0` 的计数只有 getter `main + 0x058BA4`（`swi 0x50`）读取：映像中构成偏移 `0x6052A0` 或 `0x6052A8` 的每个其他代码位置都在初始化时写入它或旁边的指针。`0x4F` 调用者提供的值是惰性的。

控制台自身的神秘礼物搜索在任何缓冲脚本之前发出 `swi 0x47`，通告 `activity` 0x15（`ACTIVITY_WONDER_CARD` [include/constants/union_room.h:46]）；载荷的调用会覆盖它。`main + 0x0586B4` 处的断点通过 `x8 + 0x280` 读取 `component + 0x605360`。游戏数据对象（vtable `main + 0x1C3B30`）是 CPU/总线对象 `bkpt #0x52` 的钩子表解析出的同级对象（vtable `main + 0x1C3878`、区域表、系统调用 0x45、0x48、0x52、0x55、0x62）；实际地址相差 `0x100000000`。

0x45 写入的每个候选者布局尚未确定：复制循环的字节数与 `sizeof(struct RfuTgtData)` 不匹配；依赖它之前请实时读取。

`component + 0x6050D8` 是 `swi 0x47` 复制的 24 字节（[main + 0x058694]，来自 guest `r0` 缓冲区的预索引存储），同一处理程序会读回它，并将其重新打包到广播记录中。`component + 0x605360` 的读取者是活动差异 `main + 0x058698`（通过 `component + 0x6050E0`）和 `svc_SetActivity` 的设置器 `main + 0x058B40`；两者都比较或存储活动代码。

#### 广播记录

`swi 0x47` 处理程序根据 guest 自身的 `RfuGameData`（16 字节）和 `gHostRfuUsername`（8 字节）[include/link_rfu.h:103-115, src/sloopsvc.c:34-46] 组装广播所携带的 24 字节 RFU 记录：

| record | source |
| --- | --- |
| `[0:2]` | `RfuGameData[2:4]`，训练家 ID（`compatibility.playerTrainerId`） |
| `[2:10]` | 用户名 |
| `[10:12]` | 包装器的 RFU 会话 ID，`main + 0x3F2E0([component + 0x6050D0])` |
| `[12:16]` | `RfuGameData[4:8]`，`partnerInfo` |
| `[16:20]` | 搜索字，由 `RfuGameData[0:2]` 和 `[8:12]` 打包而成 |
| `[22:24]` | `RfuGameData[8:10]`，`tradeSpecies` |

搜索字的位来自两个源字：第 0–6 位为 activity（`RfuGameData` 第 16–22 位），第 7 位为性别（第 24 位），第 8–10 位为版本（`RfuGameData[0:2]` 第 10–12 位），第 11–14 位为语言（第 0–3 位），第 15 位为 `startedActivity`（第 23 位），第 16 位为 `canLinkNationally`（第 7 位），第 17 位为 `hasNationalDex`（第 8 位），第 18–23 位为 `tradeType`（第 10–15 位），第 24 位为 `gameClear`（第 9 位），第 25–31 位为 `tradeLevel`（第 25–31 位）。`hasNews` 和 `hasCard`（第 4 和第 5 位）不会被复制。`[20:22]` 处的两个字节保留帧中的原样。

编码器 `main + 0x2A90` 每 4 字节组写入五个字符，低数字优先，使用从 `0x23` 向上的字母表，跳过 `0x5C`，并在输出会超出给定容量时拒绝。处理程序以 `0x20` 的容量为 24 字节调用它，因此 30 个字符可以放下，并将文本存储到 `component + 0x6C0`，其 `strlen` 存储在 `component + 0x700`（`main + 0x15FAE0` 和 `main + 0x15FB20`，`strlen`/`memcpy` PLT 存根）。

主机信标克隆的捕获应用数据（`pokeldn/frlg/link/host_beacon.py`）为 122 字节：`0x5C` 的 Pia 系统头部和 30 个字符，读回为训练家 ID `0x1050`、名称 `GREEN`、RFU 会话 ID `0xac65` 和搜索字 `0x1584`（activity 4、版本 5、语言 2、第 7 位置位）。

记录文本进入一个广播数据构建器，该构建器由处理程序为这种场合构建（类 vtable `main + 0x1CB8C8`，构造函数 `main + 0x87514`）：一个 `0x180` 字节的 Pia 广播区域位于 `+0x1C`，已用大小位于 `+0x18`，从 `0x5C` 头部开始；应用数据指针 `main + 0xA2C70` = `+0x78`；应用数据大小 `main + 0xA2C90` = 已用大小减去 `0x5C`，限制为 `0x124`（槽 `+0x28`，`main + 0x875AC`；头部偏移 `0x5C` 是槽 `+0x30`，`main + 0x875A4`）。`main + 0xA3480` 通过其持有在 `+8` 的缓冲对象在应用数据偏移处追加这 30 个字符（其容量是缓冲对象的 vtable 槽 `+0x28`，已用大小位于缓冲对象的 `+0x18`，追加设置缓冲对象 `+8` 的第 1 位）；它唯一的调用者是处理程序（`main + 0x58838`）。然后处理程序在 `main + 0x58854` 交付构建器：`x0 = [component + 0x3528]`，`main + 0xB1304`。该方法调用 `[session + 0xD0]` 上的一个方法，将其作为参数传递，清零 `+0xD8` 处的 u32，并调用 `main + 0xD4DD0(x0 = [session + 0x70], x1 = [session + 0xD0], x2 = [session + 0x30], x3 = 构建器)`。交付取 `X = [session + 0x30]` 并以 `(X, [session + 0x70] + 0x90, builder)` 调用 `X` 的 vtable 槽 `+0xA8`，此前要经过 `X` 的槽 `+0xD8`（必须返回 true）和 `+0xE8`（必须返回 false）的门控。会话的 `+0x30` 由 `main + 0xAF760` 从 `[[session + 8] + 0xB8]`（会话所有者的 `+0xB8`）设置。

`X` 具有外观类的形态：`nn::pia::local::LocalFacade`（vtable `main + 0x1CB548`）和 `nn::pia::net::NetFacade`（`main + 0x1CBE60`）共享实现，它们的槽位是 `+0xA8` = `main + 0x8D4AC`，`+0xD8` = `main + 0x8D84C`（当外观的 `+0x28` 已设置且其 `+0x30` 非空时为 true），`+0xE8` = `main + 0x8D920`（当 `[[facade + 0x30] + 0x12D8]` 非零时为 true）。外观的 `main + 0x8D4AC` 通过 `main + 0x8C6FC` 验证，锁定管理器（`[facade + 0x30] + 0x2B8` 通过 `main + 0x94B78`，因此外观将管理器持有在 `+0x30`），取出构建器 `+8` 处的值（`main + 0xA3710`）并将其交给管理器的 `main + 0x99C3C`，然后在 `[facade + 0x48]` 记录传输并在 `[facade + 0x40]` 记录状态 8。管理器将缓冲区传递给作业的接收半部分（下文），作业的发布半部分通过管理器的 blob 构建器到达 `nn::ldn::SetAdvertiseData`。
组件保存在 `[component + 0x3528]` 的对象是 `nn::pia::session::Session`：这一类的成员函数占据 `main + 0xAF4E0` 到 `0xB23xx`（主虚表在 `main + 0x1CE300`，另一个在 `main + 0x1CE330`，构造函数 `main + 0xAF4E0`，它初始化从 `+0x10` 开始的字段，并把 `+0xD8` 当作 u32）。其方法会设置 `+0x30`（`main + 0xAF760`）、`+0x70`（由 `main + 0xAF9F0` 设置；实际运行时它保存 `UpdateSessionPropertyJob` 单例，setter 维护其 `+0x10` 的 u16）和 `+0xD0`（`main + 0xAFA94`），并在 `main + 0xAFB44` 清除它们；投递调用方读取 `+0x150`、`+0x528`、`+0x70`、`+0x30`、`+0xD0` 和 `+0xD8`，它们都是 Session 字段。组件在 `main + 0x528F8` 从它内嵌在 `+0x34A0` 的对象（其第一个字）或从重定位槽 `main + 0x1D1AB0` 的全局量（指向映像外，即 `0x41FB1C8`）取出它，并用 `main + 0xB14E0` 打开它，后者把回调 `main + 0x52BB4` 存到 `+0x88`，把组件存到 `+0x90`。Session 的构造函数在映像内没有调用者，且其虚表指针槽只由该构造函数和析构函数加载，因此实例来自本模块之外。运行形态（模拟的法语火红，神秘礼物会话；同一个 `main` 二进制）：该层是一组 bss 单例：`Session` 在 `main + 0x1029950`，`SessionProtocol` 在 `main + 0x1032000`，owner 在 `main + 0x9E1798`，`LocalFacade` 在 `main + 0x9E15B8`，还有三个会话作业单例在 `main + 0x103FBB0`、`+0x103FCE8` 和 `+0x1040180`（`LeaveMeshWithHostMigrationJob`、`ProcessHostMigrationJob`、`KickoutManageJob`）。在活动会话期间，`[component + 0x3528]` 就是那个 `Session`，其中 component = `[session + 0x90]`，即系统调用分发器接收到的对象（其 `+0x6050D8` 处的 RFU 影子保存最后一条记录：活动 `0x15`、用户名字节）。`[session + 8]`（owner；对每个协议也是 `[protocol + 8]`，对 `[reader + 0x60]` 也是）没有虚表：`+0xB8` 保存 facade 对象，`+0xC8` 保存协议管理器。`[session + 0x30]` = `LocalFacade`（经 typeinfo 验证）。会话作业的 `+0x80` 是 `[SessionProtocol + 0x130]` = Session，它们的 `+0x88` 是 SessionProtocol（其构造函数 `main + 0xCB0D0`：`stp x9, x19, [x20, #0x80]`，`x9 = [x19 + 0x130]`）。

广播机制属于另一个对象，即 `nn::pia::local::LdnBackgroundProcessJob`（类虚表 `main + 0x1CAC48`，`0xA60` 字节，工厂函数 `main + 0x7EED8` = 管理器的虚表槽 `+0x278`，构造函数 `main + 0x83A88`），它派生自 `nn::pia::net::NetBackgroundProcessJob`（虚表 `main + 0x1CB928`），并在 `+0xD8` 处内嵌一个 `nn::pia::common::StepSequenceJob::Step`（虚表 `main + 0x1C9770`），在 `+0x320` 处内嵌一个 `nn::pia::local::LocalConnectNetworkSetting`（虚表 `main + 0x1CA2D0`）。其基类构造函数 `main + 0x875BC` 把网络管理器存到 `+0xA8` 并构建子对象；其构造函数构建 `+0x8C0` 处的广播数据构建器（`main + 0x87514`）。作业的方法 `main + 0x84260`（虚表槽 `+0x60`）是接收半部分：它锁定管理器（`+0x2B8`），触碰 holder（`main + 0x87374`，作用于 `[manager + 0x200] + 0xA8` 和 `[manager + 0x2D8]`），通过 `main + 0x8885C` 验证传入缓冲区（缓冲区大小在 `main + 0xA2C90` 的管理器槽 `+0x100` 限制内，缓冲区的 `+0x8` 位 1 置位，`[manager + 0x12D8]` 为零，`main + 0x879C0` 检查其中 `w2 = 8`，时间戳位于 `[job + 0xA0]`），将缓冲区的 `0x180` 字节广播区域（`+0x1C`）复制到作业在 `+0x8C0` 的构建器中（`main + 0x87578`），并把作业的下一步设为槽 `0x130`。它通过作业的虚表到达：管理器的 `main + 0x99C3C` 把缓冲区交给它保存在 `+0x250` 的对象（一个 `StepSequenceJob::Step` 派生的委托，构造函数 `main + 0xA2824`，`0x98` 字节，`+0x88` 处有一个 `0x38` 字节的 helper，管理器在 `+0x90`），该对象的 `main + 0xA28E4` 以 `(job, helper, buffer)` 调用作业的槽 `+0x60`。发布半部分是作业的 `+0x130`（`main + 0x84360`），它在 `main + 0x8445C` 将作业的构建器 `+0x8C0` 传给管理器的槽 `+0xD0`。Pia 自身会话作业的步骤中有八处（`main + 0xCB0CC`-`0xCC738`；`nn::pia::session::LeaveMeshWithHostMigrationJob`，虚表 `main + 0x1CEB70`；`nn::pia::session::ProcessHostMigrationJob`，`main + 0x1CEBA0`；`nn::pia::session::KickoutManageJob`，以及构造槽 `main + 0x1D26F8`-`0x1D2728` 处的类），每处都由作业在 `+0x90` 的状态字节控制，读取 `+0x80` 处的 holder（它是 `[SessionProtocol + 0x130]`，即 `Session`；运行中已验证），并调用 `[holder + 0x30]` 的虚表槽 `+0x130`；`[holder + 0x30]` 是 `LocalFacade`（运行中 typeinfo），其 `+0x130` 项为 `main + 0x8E0B4`。

这条链受包装器的网络状态控制，并且是主机（leader）侧路径。`swi 0x47` 主体只有在会话非空、`component + 0x690` 处的字节置位、`component + 0x2770` 至少为 10 且会话谓词 `main + 0xB06BC` 返回假（`main + 0x5879C`-`0x587DC`）时才会投递。`+0x690` 处的字节是监听列表的启用标志：它只在 `[component + 0x6A0] == [component + 0x6A4]`（包装器的扫描和加入对）时于 `main + 0x53A58` 处被置位，并被带标签属性分发器的遍历（`main + 0x4EBB0`，模式 `-2`）以及向两者写入 `-1` 的拆卸过程清除。投递自身的门随后比较管理器中的两个 Pia 地址结构体：`X` 的槽 `+0xD8` 随后进入 `main + 0x95C90`，它要求 `[manager + 0x1268]` 和 `[manager + 0x1288]` 都通过 `main + 0x74BE0`（有效地址）并在 `main + 0x74C18` 中比较相等（先比较 `+0x18` 处的 u16，再比较 `+8` 处的 0x10 字节）；槽 `+0xE8` 要求 `[manager + 0x12D8]` 为零。这两个结构体保存包装器的本地地址（模拟器上为 `127.0.0.1`）和对端地址（主机的 IP），因此该链仅在控制台是所在网络的主机时运行。加入方控制台的记录留在影子中；其游戏数据仍通过会话到达父端。

已在模拟器上在一帧内实际确认，全部八跳，使用一个携带版本 5、语言 2、训练家 ID `0x1234`、活动 `0x45` 和用户名 `PKLDNTST` 的 `swi 0x47`：处理程序的影子接受了这 24 字节；在把门字节和地址对强制改为相等后，会话的 `main + 0xB1304` 运行，facade 的 `main + 0x8D4AC` 获取栈构建器（其应用数据携带 30 字符记录文本 ``Z8J4;Vk.+>`.uN;#####<P?>######``），管理器的 `main + 0x99C3C` 及其 `+0x250` 委托的 `main + 0xA28E4` 传递它，作业的 `+0x60` 验证它并把 `0x180` 字节区域复制到作业在 `+0x8C0` 的构建器中（`main + 0x87578`），作业的 `+0x130` 从状态机运行，管理器的 blob 构建器 `main + 0x80C3C` 收到带相同记录文本的作业构建器。作业本身作为状态机运行：其 `+0x38`/`+0x40` 保存当前步骤（带一位虚拟标志的虚表槽，或直接函数），基类方法 `main + 0x6EAA0`（“ExecuteCore”，作业的槽 `+0x20`）分发它；观察到的步骤有虚表槽 `0xB8`、`0xC8`、`0xD8`、`0xE8`、`0xF8`、`0x108`、`0x118`、`0x138`、`0x148` 以及直接函数，如 `main + 0x891F0`。

管理器类（`nn::pia::local::LdnProtocol`；虚表 `main + 0x1CA5B0`，指针在 `main + 0x7E244` 由重定位槽 `main + 0x1D1E98` 生成）在 `[manager + 0x2D8] + 0xB8` 保存自己的 `NetworkInfo`：广播大小是 `NetworkInfo + 0x26A`（`+0x322`），blob 是 `NetworkInfo + 0x26C`（`+0x324`），`NetworkInfo + 0x282` 在 `+0x33A`。其方法 `main + 0x80C3C`（构建器应用数据的唯一消费者；`main + 0xA2C70` 只有这一个调用者）清零 `+0x380`（`NetworkInfo + 0x2C8`），把应用数据复制到那里，在 `+0x322` 把大小设为应用数据加 `0x5C`，用 holder 自己的方法（其虚表槽 `+0x68`）在 `+0x324` 写入 `0x5C` 字节的 Pia 系统头，并调用 `nn::ldn::SetAdvertiseData(holder + 0x324, size)`（PLT `main + 0x160A90`，GOT `0x1d3800`）。另外两个管理器方法广播第二个对象的数据（`main + 0x7F990`、`0x81140`：`[object + 0x18]`，大小为其虚表槽 `+0x38` 加 `main + 0x8AC20`），`main + 0x80EBC` 在广播前从 `[manager + 0x128]` 重建 holder。

`component + 0x2770`（通过 `[component + 0xD0]`）由 `swi 0x53`（一个布尔值）以及 `main + 0x0511CC` 和 `main + 0x0511F4` 读取，后两者没有任何系统调用到达。`main + 0x0511F4` 将其与 10 比较，在达到或超过 10 时原子加载 `component + 0x2790` 处的标志；标志置位则进入 `main + 0x057250` 的续体，后者测试第三个参数是否为空。其调用者尚未识别。

`bkpt #0x52` 组件还拥有分发器（其虚表槽 21）和 2324 个物种名称，每个名称有六种语言，使用 djb2 哈希（`main + 0x056540`，字符串在 `main + 0x1C4470`）。分发器的栈帧由所有处理程序共享，为 `0x40` 字节的保存寄存器加 `0x310`。

来自 payload 的 `bkpt #0xFF` 会关闭游戏：包装器提交会话的游戏报告，终结 LDN，停止音频，提交由存档构建的报告，提交存档并退出。不会有回复到达主机。Ryujinx 的 `prepo` 打印的报告如下：

| room | fields |
| --- | --- |
| `network`，每个连接会话一条 | `Flavor` 66、`Trainer`（32 位训练家 ID）、`Zone`（连接活动，神秘礼物为 21 `ACTIVITY_WONDER_CARD`）、`Duration`、`Players`、`Slot`、`Rtt` |
| `game`，退出时 | `Flavor`、`TimeStamp`、`Trainer`、`Gender`、`Duration`、`Badges`（位掩码）、`TotalBadges`、`HallOfFame`、`TotalHallOfFame`、`CompleteRegionalPokedex`、`RegionalPokedexCnt`、`RegionalPokedexCap`、`CompleteNationalPokedex`、`NationalPokedexCnt`、`NationalPokedexCap`、`Distributed`、`LinkExchange`、`LinkBattle`、`MonsNo1..5` 和 `MonsNoNLevel`、`Money`、`CommsError` |

### 游戏报告的构建来源

游戏报告从 flash 映像解析。`main + 0x05A280` 通过扇区尾部（签名 `0x08012025`）找到最新槽，将其 14 个扇区（0xE000 字节）复制到 `component + 0x140 + 0x70`，然后 `main + 0x05A370` 用按游戏区分的描述表遍历它：徽章标志位、名人堂和图鉴标志、与存档密钥异或的金钱。每个偏移和位索引都来自静态表；复制出的存档提供的唯一计数 `playerPartyCount`（一个字节）限制 `main + 0x05AAE0` 处的队伍遍历，255 个 0x64 字节条目保持在 0xE000 副本内。`swi 0x57` 填充 `MonsSelect`（初始宝可梦，通过 `main + 0x17DA8C` 的内部到全国图鉴表）；打印的 JSON 携带表的固定子集，并省略 `MonsSelect`。`swi 0x62` 递增 `component + 0xE1B0`，它成为 `CommsError`：每次调用都会在 Ryujinx 的 `ServicePrepo ProcessPlayReport` 打印到主机日志的下一个报告中给 `CommsError` 加一。`swi 0x55` 存储在 `component + 0xE1BC` 的 SaveBlock2 指针的唯一读取者是 `main + 0x0577D8`，它测试 `optionsButtonMode == 2`（L=A）。存储点是处理程序本身 `main + 0x057308`：分发器在 `main + 0x057058` 设置 `x8 = component + 0xE1B0`，处理程序将原始 guest `r0` 存到 `[x8 + 0xC]`。读取器将存储的字按区域表折叠，进行边界检查，并读取一个字节，即折叠区域的 `+0x13` 处：两者都是 guest 相对且经过边界检查。

`main + 0x059CE4` 按游戏代码选择表；应用程序携带全部五个：

| game code | table | `Flavor` base |
| --- | --- | --- |
| `AXV?` | 红宝石 | 0x10 |
| `AXP?` | 蓝宝石 | 0x20 |
| `BPE?` | 绿宝石 | 0x30 |
| `BPR?` | 火红 | 0x40 |
| `BPG?` | 叶绿 | 0x50 |

`Flavor` 再加上语言在 `JEFIDS` 中的索引，因此法语火红报告 `0x42`（66）。

该表按 ID 顺序寻址 14 个扇区，每个 0x1000：字节偏移 `o` 的 SaveBlock1 偏移为 `((o >> 12) - 1) * 0xF80 + (o & 0xFFF)`。一个标志是 `(bit, byte)` 对；位大于 7 表示不存在。已对照三个反编译项目解码：
| 字段 | 红宝石／蓝宝石 | 绿宝石 | 火红／叶绿 |
| --- | --- | --- | --- |
| 徽章，8 个标志来自 | 字节 `0x23A0` 第 7 位，`FLAG_BADGE01_GET` 0x807 | `0x23FC` 第 7 位，0x867 | `0x2064` 第 0 位，0x820 |
| `HallOfFame` | `0x23A0` 第 4 位，`FLAG_SYS_GAME_CLEAR` 0x804 | `0x23FC` 第 4 位，0x864 | `0x2065` 第 4 位，0x82C |
| `Money` | `0x1490`（SaveBlock1 + 0x490），无密钥 | `0x1490`，XOR `0x00AC`（SaveBlock2 `encryptionKey`） | `0x1290`（+0x290），XOR `0x0F20` |
| 队伍数量，队伍 | `0x1234`，`0x1238` | `0x1234`，`0x1238` | `0x1034`，`0x1038` |
| `TotalHallOfFame` | `0x25E8`，`GAME_STAT_ENTERED_HOF` | `0x2644` | `0x22A8` |
| `LinkExchange` | `0x2614`，`GAME_STAT_POKEMON_TRADES` | `0x2670` | `0x22D4` |
| `LinkBattle`，各项之和 | `0x261C..0x2624`，连接胜、负、平 | `0x2678..0x2680` | `0x22DC..0x22E4` |
| 地区宝可梦图鉴大小 | 202 | 202 | 151 |

在有金钱密钥的游戏中，游戏统计数据会与该密钥异或。

`Distributed` 是四位，每位是开启前往仅限船票岛屿的渡轮的标志：

| 位 | 标志 | 红宝石／蓝宝石 | 绿宝石 | 火红／叶绿 |
| --- | --- | --- | --- | --- |
| 0 | 肚脐岩（神秘船票） | 无 | `0x240C` 第 0 位，`FLAG_ENABLE_SHIP_NAVEL_ROCK` 0x8E0 | `0x2069` 第 2 位，0x84A |
| 1 | 诞生之岛（极光船票） | 无 | 无 | `0x2069` 第 3 位，0x84B |
| 2 | 南方之岛（无限船票） | `0x23AA` 第 3 位，`FLAG_SYS_HAS_EON_TICKET` 0x853 | `0x2406` 第 3 位，`FLAG_ENABLE_SHIP_SOUTHERN_ISLAND` 0x8B3 | 无 |
| 3 | 遥远之岛（古代海图） | 无 | `0x240A` 第 6 位，`FLAG_ENABLE_SHIP_FARAWAY_ISLAND` 0x8D6 | 无 |

在火红／叶绿中，两个标志都由船票的神秘事件脚本 [mystery_event_msg.s:222,281] 以及 Switch 版本的名人堂授予 [post_battle_event_funcs.c:58] 设置；已进入名人堂的存档继承过来时会报告 0。

### 禁词过滤器

`swi 0x4D` 的处理程序 `main + 0x0571FC`，将 `r0` 解析为 GBA 地址，需要其后 256 字节，将 ASCII 字符串转换为 UTF-16 并运行平台的不当言论检查，原地重写字符串。`r1` 非零会选择游戏从不使用的第二种模式（`r1` = 1 以相同方式掩码）。游戏通过 `svc_BadWordCheck` 调用它，将名称转换为 ASCII 再转回来 [sloopsvc.c:211]。命名界面仅在它返回 0 时才保存输入的名称 [naming_screen.c:686]。

| 发送的字符串 | `r0` | 之后的字符串 |
| --- | --- | --- |
| `hello world` | 0 | `hello world` |
| `hello fuck` | 1 | `hello ` 后跟四个 `0xA1` 字节 |
| `POKELDN` | 0 | 未改变 |
| `ASSASSIN` | 0 | 未改变 |
| `NINTENDO` | 0 | 未改变 |

路径 [main + 0x0571FC -> main + 0x057458]：处理程序折叠 `r0`，要求折叠后地址之后有 `0x100` 字节，并将字符串复制到帧偏移 `-0x100` 处的 `0x100` 字节栈缓冲区（`main + 0x85645F0` 处的复制受其 `w1 = 0x100` 实参限制）。UTF-16 转换从该缓冲区运行到 `sp + 0x10` 处的 `0x200` 字节缓冲区（[main + 0x855F100]，`w2 = 0x200`），不当言论检查通过全局指针运行（[main + 0x574AC，被调方 `main + 0x86664C0`]），掩码后的字符串被复制回访客折叠地址。两个缓冲区都结束于调度器自身的 `0x310` 字节帧内（`sp + 0x210` 和 `sp + 0x310`）；复制既不会到达保存的寄存器，也不会越出帧。替换字节是常量 `0xA1`。

### 包装器自身的扫描管线

包装器通过其自身的 PLT（`main + 0x160B70`；`ScanPrivate` 在 `main + 0x160B60`）用 `nn::ldn::Scan` 扫描网络，调用点 `main + 0x80944`/`0x8095C` 处来自管理器对象 `x23`，`w2 = 0x18` 个网络，写入 `manager + 0x14C0` 处的内联数组，24 项 x `0x480`（初始化时一次性清零，`main + 0x7E290`）。模拟器自身的 ldn 服务将线上 `ScanResponse` 主体直接转换为 `NetworkInfo`，不做长度检查，因此对侧座席的字段值会原样到达包装器。

消费循环（`main + 0x80A20..0x80B9C`）遍历该数组：它清零 `sp + 0x128` 处的 `0x480` 字节记录（`main + 0x874A0`），将条目转换到其中（`main + 0x87374`：一次将整个 `0x480` 块 memcpy 到 `record + 0xB8`，然后逐位精确读取字段：源 `+0xA`、`+0x11`（一个 15 字节整数解析，`main + 0xA9830`，支持十六进制/八进制/十进制/二进制，带 `b`/`x` 前缀，每次前进都做边界检查）、`+0x26A`（广播数据大小）、`+0x281`/`+0x282`、`+0x11A..0x11F`；存储到记录 `+0x90`、`+0xA0`、`+0xA2`、`+0xA4`、`+0xA6`、`+0xB0`），然后将记录依次通过过滤虚函数和接受虚函数（`main + 0x80A88..0x80A94`）。

被接受的网络落入父候选列表：`owner + 0x6050F2` 处的 16 个槽位 x `0x1A` 字节，写索引在 `owner + 0x605294` 封顶为 15（`cmp w8, #0xf; b.le` [main + 0x58C3C]）；数组结束于 `+0x605292`，紧贴索引。填充是所有者类（vtable `main + 0x1C3B30`）的槽位 `+0xA0`，`main + 0x58BF8`，由 `main + 0x536A4` 按扫描结果站点调用；站点名称长度来自站点自身的虚函数 [槽位 `+0x50`]，并且 `sub w8, w0, #1; cmp w8, #0x3f; b.hi` [main + 0x5364C] 在调用前丢弃 `x6 > 0x40` 的值。在填充内部，`sp + 7` 处的 `0x41` 字节栈缓冲区接收 `memcpy(sp + 7, x5, x6)`，当 `x6 > 0x40` 时跳过尾部清零的 memset [main + 0x58C68]：对于 `x6 > 0x40`，复制会到达帧的保存 `x29`/`x30`（缓冲区偏移 `0x59`/`0x61`）。解码的唯一调用方先进行了钳制，因此通过它的长度最多为 `0x40`；在映像的八个加载类槽位 `+0xA0` 的站点中，`main + 0x536A4` 是确认会对此类进行分派的那个。

在模拟主机上测量，一个主机广播：计数 1，槽位 0 = 主机的广播逐字节一致：16 字节游戏数据（活动 `0x15`）、8 字节显示名称、父 ID u16（`0x59f1`）。

在 `main` 中，列表仅通过填充系列（`main + 0x58BB4`、`0x58BE4`、`0x58BF8`）写入，全部为虚函数；映像中每个其他基于组件锚点的访问都是读取。所有者类的 vtable 指针 `main + 0x1C3B30` 是在 `main` 中通过加载重定位槽位 `main + 0x1D1B38`（值 `main + 0x1C3B20`）并加上 `0x10` 形成的：`main + 0x58558` 在清零 `component + 0x6050F0` 处的候选列表时存储它，`main + 0x58FD8`/`0x59054` 在两个组件初始化器中也存储它。同样的惯用法形成管理器类的指针（槽位 `main + 0x1D1E98`；`main + 0x7E244`、`0x7E4D0`）和会话类的指针（槽位 `main + 0x1D2770`；`main + 0xB7D24`、`0xB7E78`）。

### Pia 会话消息分发器

包装器的原生 Pia 会话接收是 `main + 0xB9FC0` 处的类型开关。遍历节点链：`[node + 0x10]` 是消息体，其首字节是类型，而节点自身开头的三个字节是作为队列键的协议地址。当管理器对象的 `[x0 + 0xA0]` 非零且类型至多为 `0x11` 时分发节点，开关是 `adr x8, main + 0xB9FD0`（`main + 0xB9FCC`）、`ldrb w9, [main + 0x180FC9 + type]`（`main + 0xB9FC4`；`adr x27, main + 0x180FC9` 在 `main + 0xB9EFC`）、`add x8, x8, w9, lsl #2`、`br x8`。`main + 0x180FC9` 处的字节表每个类型一个条目；十八个 case 块位于 `main + 0xB9FD0 + index * 4`，每个都以无条件 `b main + 0xB9F80` 结束，并各自调用其处理程序（`main + 0xBCB60`、`main + 0xBE438`、`main + 0xBE8BC`……）。

每个处理程序在接触消息前都会对照消息限制其读取：类型 1 处理程序 `main + 0xBE438` 开头是 `cmp w2, #0x15; b.ne`（只有 `0x15` 字节的消息会到达复制处），审计解码出的按类型测试为：类型 2 `>= 4`，类型 3 `== 0x16 或 0x22`，类型 4 `== 0xf`，类型 6 `>= 0xf`，类型 9 `== 0x1e 或 0x2a`，类型 10 和 12 `== 0x15`，类型 11 `>= 0xe`，类型 13 `== 0xa`，类型 14 `>= 0x4d`，类型 17 `>= 0xd`。变长读取器 `main + 0xC0D90` 从位计数推导字节数，与声明的长度比较，若过短则拒绝。未发现该集合中有处理程序将消息控制的长度复制到固定缓冲区。

类型是 Pia 会话协议自身的消息类型；主机的会话层（`pokeldn/ldn/pia_connect.py`）将其编号为 0 加入请求、1 加入确认、2 加入响应、3 离开请求、4 离开响应、5 更新、6 更新确认、7 开始主机迁移、8 迁移确认。类型 1 处理程序 `main + 0xBE438` 将 21 字节消息读作 `[0]` 类型、`[1:9]` 和 `[9:0xB]` 源站点的常量 ID 和变量 ID、`[0xB:0x13]` 和 `[0x13:0x15]` 目的地的，并拒绝，除非目的地对与传输自身的匹配（[transport + 0x1B8]、`+0x1C0`），然后查找源站点并对它调用 `main + 0xC9B4C`。类型 2 处理程序 `main + 0xBE8BC` 接受 4 字节或更多，以管理器的状态字节（`+0x30 == 0xFD`）为门控，并对消息字节 3 在 3 到 0x10 之间进行开关。

接收路径的所有者是会话类（`nn::pia::session::SessionProtocol`；vtable 基址 `main + 0x1CE8E0`；其 vtable 指针在 `main + 0xB7D24`/`0xB7E78` 处由重定位槽位 `main + 0x1D2770` 形成，构造函数是 `main + 0xB7E70`）。泵是该类的 vtable 槽位 `+0x50`，`main + 0xB9CA0`，它调用遍历器 `main + 0xB9DB0`；链挂在 `[protocol + 0xF8]` 处的对象上（会话包读取器，由协议管理器挂接），位于其 `+0x70` 表（`main + 0xD6D68` 返回该地址）。消息对象由 `main + 0xD4430` 构造（其 vtable 指针来自重定位槽位 `main + 0x1D27B0`）。Pia 库本身静态链接在 `main` 中（映像带有 `SDK MW+Nintendo+PiaCommon-6_42_1-Release` 和会话作业名）。

### Pia 库自身的线上数据解析

`main` 链接了整个 Pia 6.42.1 协议栈（映像带有 `SDK MW+Nintendo+...` 的发布字符串，包括 `PiaCommon`、`PiaLocal`、`PiaNet`、`PiaSession`、`PiaTransport` 和 `Pia_ZStandard`，以及修饰类名）。上文中仅通过 vtable 描述的类如下：

| 早先的措辞 | 类（vtable 的 typeinfo 处的修饰名） | vtable |
| --- | --- | --- |
| 网络管理器 | `nn::pia::local::LdnProtocol` | `main + 0x1CA5B0` |
| 会话对象（构建器在 `+0x8C0`） | `nn::pia::local::LdnBackgroundProcessJob` | `main + 0x1CAC48` |
| 会话类（接收路径） | `nn::pia::session::SessionProtocol` | `main + 0x1CE8E0` |
| 包对象 | `nn::pia::common::Packet::Header` | `main + 0x1CA100` |
| 本地接收流 | `nn::pia::local::LocalInputStream` | `main + 0x1CA540` |
| 网络接收流 | `nn::pia::net::NetInputStream` | `main + 0x1CC1D0` |

传输类的 vtable 为 `PacketReader` `main + 0x1CF1A8`（第二个在 `main + 0x1CE7E8`）、`PacketWriter` `main + 0x1CF258`、`ProtocolManager` `main + 0x1CF3A0`、`ProtocolMessageReader` `main + 0x1CF458`、`ProtocolMessageWriter` `main + 0x1CF490`、`ReliableProtocol` `main + 0x1CF4C8`、`Station` `main + 0x1CF8C8`、`StationManager` `main + 0x1CF938`、`ReceiveThreadStream` `main + 0x1CFB20`、`SendThreadStream` `main + 0x1CFB68`；会话类的为 `Session` `main + 0x1CE300`、`SessionPacketReader` `main + 0x1CE748`、`SessionPacketWriter` `main + 0x1CE7F8`、`SessionStation` `main + 0x1CED20`；本地类的为 `LocalProtocol` `main + 0x1CA9B0`、`LocalService` `main + 0x1CB460`、`LocalFacade` `main + 0x1CB548`。

**数据包。** 包对象为 `0x1D18` 字节：解析后的头部在 `+8` 到 `+0x24`，数据报缓冲区在 `+0x30`（容量 `0x1C5C`，追加辅助函数中的上限 `main + 0x75664` 和 `main + 0x75694`，第二个会在 `+0x14` 记录页脚大小），接收大小在 `+0x1C90`（本地接收路径在 `main + 0x7DE40` 存储它，在此之前有 `0x5AC` 字节的接收并检查该上限）。其解析（`main + 0x752D4`，vtable 槽位 `+0x18`；入口 `main + 0x752C8` 提供对象自身的缓冲区和常量 `0x1C5C`）要求超过 `0x1C` 字节并读取 `0x1D` 字节的头部：
| 偏移 | 大小 | 含义 | 落点 |
| --- | --- | --- | --- |
| 0x00 | 4 | 魔数 `0x32AB9864`，大端序 | `+0x08` |
| 0x04 | 1 | 位 0-6 为版本，`0x80` 为加密标志 | `+0x0C` |
| 0x05 | 1 | 一字节，按发送原样保留 | `+0x0D` |
| 0x06 | 2 | 目标变量 id，大端序 | `+0x0E` |
| 0x08 | 2 | 源变量 id，大端序 | `+0x10` |
| 0x0A | 2 | 包 id，大端序 | `+0x12` |
| 0x0C | 1 | 尾部大小 | `+0x14` |
| 0x0D | 8 | nonce，按发送原样 | `+0x15` |
| 0x15 | 8 | GCM 标签，按发送原样 | `+0x1D` |

本应用使用的版本为 `0x10`（16）：有效性检查 `main + 0x75610` 要求魔数、`([+0xC] & 0x7F) == 0x10` 且 `size - 0x1D < 0x1C40`。载荷指针为 `+0x4D`（位于头部之后的缓冲区，`main + 0x75474`）；`main + 0x75458` 返回 `buffer + t`，其中 `t = (n + 0x1D)`（32 位算术），或当 `(t >> 2) > 0x716` 时返回 null。此容量检查允许 `t` 达到 `0x1C5B`；消息遍历器会另行对照接收大小减去头部和尾部后的大小进行检查（`main + 0xDE278`）。

**套接字与接收流。** 套接字是一个小型持有者（构造函数 `main + 0x6D93C`：`+0` 处 fd 为 `-1`，`+4` 处为计数，`+8` 处为地址族，`+0xC` 处为协议）；`main + 0x6D95C` 打开它（`nn::socket::Socket`，PLT `main + 0x160940`），`main + 0x6DBF4` 关闭它（`main + 0x160950`），`main + 0x6DCD0` 绑定它（`main + 0x160960`），`main + 0x6DE6C`、`0x6DF44`、`0x6E00C`、`0x6E0F0` 设置选项（`main + 0x160970`）。数据报调用为 `main + 0x6E1D0`（`nn::socket::RecvFrom`，PLT `main + 0x160980`，标志 `0x80`，源地址由 `main + 0x6E9D0` 转换回来）和 `main + 0x6E538`（`nn::socket::SendTo`，`main + 0x160990`）。本地接收流（变量 id 位于 `+0x88`，锁位于 `+0x68`，套接字持有者指针位于 `+0x18`）运行泵 `main + 0x7DD10`（vtable 槽 `+0x10`）：它接收进一个包的缓冲区，并把头部解析进其中（`main + 0x7DDEC`；`main + 0x6E1C8` 是 thunk）；包过滤器 `main + 0x91280`（槽 `+0x20`）首先要求有效包。当版本至少为 7、尾部非空且目标变量 id 至多为 1 时，尾部必须至少包含两个字节，并且流自身的 id（`+0x88`）必须非零并出现在其大端序 u16 接收者 id（`footer_size >> 1` 项）中。另外，当 `([+0xC] & 0x7E) >= 6` 且目标为 2 或以上时，它必须等于流自身的 `+0x88`。

过滤器将接收者指针构成为 `packet + (size - footer) + 0x30`，在 `main + 0x912EC` 处执行 `sub w8, w8, w9` 之后；消息遍历器 `main + 0xD6460` 和解析器 `main + 0xDE278` 将遍历边界构成为 `size - footer - 0x1d`（`main + 0xD651C`、`main + 0xDE298`）。这两处减法都没有把尾部大小适配数据报作为前提。尾部大小字节在数据报偏移 12，位于明文头部中，因此对端可以任意设置。尾部大小大于数据报大小并不会使过滤器出错：在模拟器上测量到，六个 31 字节、尾部为 `0x40` 的数据报到达套接字后会话仍继续运行。

**线程。** 传输层的接收和发送循环是名为 "Pia ReceiveThreadStream"（在 `main + 0xE9020` 处启动，名称通过 `main + 0xE9034` 处的 `adr`）和 "Pia SendThreadStream"（`main + 0xEA758`）的 `nn::os` 线程，通过 `main + 0xF6010` 创建（`nn::os::CreateThread`，PLT `main + 0x15FDF0`，以及 `StartThread`，`main + 0x15FE00`）。

**从线路到会话处理器。** 接收到的会话消息由会话包读取器解析，并留在每个地址的表中，会话协议在每次更新时遍历该表。

`nn::pia::session::SessionPacketReader`（vtable `main + 0x1CE748`）继承自 `nn::pia::transport::PacketReader`（vtable `main + 0x1CF1A8`）。读取器的 `+0x30` 方法（`main + 0xD5DE0`）处理接收到的包，并调用 `main + 0xD6460(reader, packet)` 来遍历其中的消息。遍历器从数据报偏移 `0x1D` 开始，在 `packet_size - footer_size` 之前停止（`main + 0xDE278`、`0xD6510`-`0xD6538`）；尾部跟在载荷之后。它用 `main + 0x74EA8` 解析每条消息，并通过读取器的 `+0x78` 虚函数取得用作队列键的协议地址（`main + 0xD6D0C`：消息 `+0x2C` 处的 u16，`+0x2E` 处的字节作为其高位部分），然后调用 `main + 0xD6944(table, address, message)`。

该表内嵌在 `reader + 0x70`：`+0` 处为 u32 桶计数，`+8` 处为指向桶数组的指针（每桶 0x18 字节，链头位于 `+0`，链尾位于 `+8`），可选哈希回调位于 `+0x40`。`main + 0xD6944` 先加载数组指针，再添加 `index * 0x18`；桶并不是内联在表中的。桶索引为 `callback(address) % count`，未设置回调时为 `(address[0] + address[1] + address[2]) % count`。`main + 0xD71F0(bucket, address, message)` 取一个节点，将消息复制进去（三个地址字节位于 `+0`，主体指针位于 `+0x10`，id 位于 `+0x18`，更多字段位于 `+0x20` 到 `+0x30`，其余部分通过 `main + 0x74C54`），并将其追加到桶的双向链表（next 位于 `+0x78`，previous 位于 `+0x80`）。

协议侧：`nn::pia::session::SessionProtocol` 的 `+0x50` 虚函数（`main + 0xB9CA0`）在每次更新时运行 `main + 0xB9DB0`。它读取 `[protocol + 0xF8]`（读取器，如下文所附加），取读取器 `+0x70` 处的表，为协议自身的三字节地址计算桶（`+0x120` 处的 u16，以及 `+0x122` 处的字节，由 `+0x18` 虚函数 `main + 0x828E4` 读取；该对是 `nn::pia::transport::Protocol` 的字段，由 `main + 0xDA614` 设置），遍历链并通过跳转表按 `[node + 0x10]` 处主体的第一个字节将每个节点分派给处理器（`main + 0xBCB60`、`main + 0xBE438`、`main + 0xBE8BC`、`main + 0xBF2D4` 等），传递 `(protocol, node, id)`。

附加过程：协议管理器（内嵌在其所有者的 `+0xC8`，其协议表位于 `+0x18`）遍历自己的表，并根据其所有者的 `+0xF8` 和 `+0x100` 设置每个协议的 `+0xF0` 与 `+0xF8`（设置器为 `main + 0xDA8C8` 和 `main + 0xDA8D0`，广播为 `main + 0xDB740`，在 `main + 0xEC0E4` 处以该对调用；任一参数为零则拒绝）。`+0xF8` 对象是读取器，因此遍历器的表就是读取器的 `+0x70`。

实际运行时，管理器位于 `[session + 8] + 0xC8`（即上文的所有者），其表位于 `[manager + 0x18]`，`+0` 处为 u32 桶计数，`+8` 处为桶数组指针。每个桶为 `0x18` 字节：`+0` 是节点，节点的 `+8` 是协议，节点的 `+0x30` 链接下一个节点。在模拟会话中，该表的计数为 `19`，并且正好有六种协议，每种一个，以协议地址为键（u16；`+0x122` 处的字节为零，每个协议的 `+0x108` 保存网络的 Pia var，`0x8fa2`/`0x0766`）：`0xfd01` `nn::pia::local::LdnProtocol`，`0xfd03` `nn::pia::transport::RttProtocol`，`0xfd05` `nn::pia::transport::UnreliableProtocol`，`0xfd0a` `nn::pia::transport::ReliableProtocol`，`0xfd0d` `nn::pia::session::SessionProtocol`，`0xfd0f` `nn::pia::transport::MonitoringDataProtocol`。协议是每种一个，而不是每个站点一个：`SessionProtocol` 的泵在 8 次中 8 次追踪到同一个实例，读取器表节点也归入协议地址（`0xfd0a`，消息 id `0x60`）下。实例由 `main + 0xB1F60` 创建并注册（通过 `main + 0xDB114` 分配 `0xD8E8` 字节，构造函数 `main + 0xB7D0C`，插入管理器的以地址对为键的映射中）；Session 的构造函数调用一次，并将返回地址存储在 `+0x12`/`+0x14`。

`nn::pia::transport::Protocol` 基类（vtable `main + 0x1CF308`，构造函数 `main + 0xDA548`，vtable 指针来自重定位槽 `main + 0x1D2808`）在 `+0x120`/`+0x122` 处携带三字节地址，在 `+0xC8` 处有锁，在 `+0xF0`/`+0xF8` 处有附加对，在 `+0x100`/`+0x108` 和 `+0x110`/`+0x118` 处有两个配置的 8 字节加 u16 值，在 `+0x123` 处有状态字节，在 `+0xD8` 处有标志。

## 重定向主机的出站消息

`r0` 是 `&client->param`，因此 `struct MysteryGiftClient` [include/mystery_gift_client.h:71] 位于相对于它的固定偏移处：

| 字段 | 相对 `r0` 的偏移 |
| --- | --- |
| `client->sendBuffer` | 0x10 |
| `client->link.sendSize` | 0x34 |
| `client->link.sendBuffer` | 0x3C |

`MysteryGiftLink_InitSend` 会保存传入的指针 [mystery_gift_link.c:59]；CRC 在发送时对 `link->sendBuffer` 的 `link->sendSize` 字节计算 [:166]。在 InitSend 与发送之间运行的有效载荷会将主机的出站消息指向任意地址：

    CLI_RECV -> CLI_LOAD_TOSS_RESPONSE -> CLI_RUN_BUFFER_SCRIPT -> CLI_SEND_LOADED

如果顺序相反，InitSend 会覆盖有效载荷的补丁。

切勿转储在 CRC 帧与发送帧之间发生变化的区域：

```c
case 0:  header.crc = CalcCRC16WithTable(link->sendBuffer, link->sendSize);   // one frame
case 1:  SendBlock(0, link->sendBuffer + blocksize, ...);                     // the next
case 2:  if (CalcCRC16WithTable(...) != link->sendCRC) LinkRfu_FatalError();  // the one after
```

[mystery_gift_link.c:155]。`gRngValue`（0x03004220）每帧前进两步；对它进行转储会使正文 CRC 失败，主机会报告“erreur de connexion”。`buffer_script.build_memory_dump` 会拒绝任何与之重叠的范围；请绕开它进行转储，或使用 `rng-trace`，后者会通过 4 字节通道返回它。任何其他易变区域也必须以同样方式发现。

## 载荷

### `trainer-id-probe`

24 字节，只读。游戏机在数秒前已经通过 `MysteryGiftLinkGameData` 发送了它的 `playerTrainerId` [mystery_gift.c:337]，因此答案是已知的。

```arm
    ldrh    r3, [r1, #0x0A]         @ SaveBlock2.playerTrainerId[0..1]
    ldrh    ip, [r1, #0x0C]         @ SaveBlock2.playerTrainerId[2..3]
    orr     r3, r3, ip, lsl #16
    str     r3, [r0]                @ *param
    mov     r0, #1
    bx      lr
```

匹配意味着它在 ARM 状态下以反编译项目的参数针对真实 `gSaveBlock2Ptr` 运行并返回 1；值不同意味着参数或偏移错误；没有 `Buffer script status:` 行意味着客户端脚本形态错误，或者调用从未到达。7 个字符的玩家名称的终止符会覆盖游戏数据中的 `playerTrainerId[0]` [mystery_gift.c:364]；随后主机会比较前三个字节。

### `save-dump` 与 `memory-dump`

`memory-dump` 接受一个绝对地址。`save-dump` 可在任何构建上通过 r1 和 r2 读取任一存档块的任意偏移。每次最多 1024 字节；`MGL_Receive` 会拒绝更多 [mystery_gift_link.c:102]。

    HOST --buffer-script save-dump --dump-block sav2 --dump-size 256 --version firered
    HOST --buffer-script memory-dump --dump-address 0x0201C000 --version firered

它们能够到达 0x0038 的 `SaveBlock1.playerParty`、0x0290 与 0xF20 的 `SaveBlock2.encryptionKey` 异或的 `money`、背包、标志和变量，以及 IWRAM（`gRngValue`）。

### `memory-dump-multi` 与 `memory-dump-scatter`

`MG_LINK_BUFFER_SIZE` 限制单条消息，而不是整个会话。客户端从其 1024 字节接收缓冲区运行命令脚本 [mystery_gift_client.c:140]，而转储三重指令

    CLI_LOAD_TOSS_RESPONSE -> CLI_RUN_BUFFER_SCRIPT -> CLI_SEND_LOADED

会尽可能多地重复：每条命令 8 字节，循环前后有三个固定命令，每轮可执行 41 遍。`mg_script.MAX_DUMP_BLOCKS` 将其限制在 32，因为中途死掉的会话会丢失所有块。通过 ESP32 无线电进行 16 KB 转储大约需要 57 秒，块间隔约 2.5 秒。

`CLI_RUN_BUFFER_SCRIPT` 每一遍都会重新复制映像 [:238]，因此游标保存在 `client->param` 中：每一遍发送 `base + index * 1024` 并传递下一个索引。高半部分没有 `0x5A5A0000` 的 `param` 表示第零遍。

`memory-dump-scatter` 改为索引一个基址表：

    adr     r3, .Ltable
    ldr     r3, [r3, r1, lsl #2]    @ this block's own base
    str     r3, [r0, #0x3C]         @ client->link.sendBuffer

`adr` 是 PC 相对的。所有 32 个槽位都被填满，未使用的槽位填入最后一个地址，因此额外的一遍会重新发送已持有的块，而不是把消息指向 0。分散的块每次加入能捕获的短函数体数量约为连续块的四倍；对于分布在 1 MB 上的一组 166 个未读函数体：

| 一次加入，16 KB 通信量 | 捕获的函数体数 |
|---|---|
| `memory-dump-multi`，在最佳基址的十六个连续块 | 22 |
| `memory-dump-scatter`，密度最高的十六个千字节 | 83 |
| `memory-dump-scatter`，32 个块 | 166 个中的 119 个 |

可读性检查会覆盖每个分散块。这些块首尾相连地到达一个文件中；`--dump-scatter A,B,C` 允许 `script_read.dumps` 将每个块放置在其基址处，并标记为 `<run>[0]`、`<run>[1]`……`--dump-blocks 1` 返回 `CLIENT_SCRIPT_DUMP_MEMORY` 的逐字节内容。

### `anchors`

将十一个字写入 `client->sendBuffer`，并将 `link->sendSize` 扩大到 44；不需要重新指向，因为 `CLI_LOAD_TOSS_RESPONSE` 已经让 `link->sendBuffer` 指向那里 [`MysteryGiftClient_InitSendWord`, mystery_gift_client.c:91]。

| 字 | 含义 | 一次启动 |
| --- | --- | --- |
| 0 | `sub ip, pc, #8`：游戏机放置代码的位置 | 0x0201C000 |
| 1 | `lr`：调用后的 ROM 地址 [mystery_gift_client.c:276]，位 0 置 1，因为调用方是 THUMB | 0x08148C75 |
| 2 | `sp` | 0x03007DB8 |
| 3 | `r0` = `&client->param`，即 `AllocZeroed` 在 `gHeap` 中放置客户端的位置 | 0x020020D4 |
| 4-5 | gSaveBlock2Ptr、gSaveBlock1Ptr | 0x02024598、0x0202553C |
| 6-9 | 四个 AllocZeroed 缓冲区：send、recv、script、msg | 0x02006510 .. 0x02007140 |
| 10 | `link->sendBuffer`，InitSend 留下的值；必须等于第 6 个字 | 0x02006510 |

第 4-5 个字在每场战斗和读档后都会改变 [load_save.c:75]；第 3 和 6-9 个字取决于堆状态。第 1 个字锚定了一个反编译调用点；第 10 个字与第 6 个字相等则确认了结构体偏移。这些缓冲区相隔 0x410（1024 字节加上 16 字节块头），如 `malloc.c` 所述。`buffer_script.describe_anchors` 会打印全部十一个字及其一致性检查。

### `save-write`

将其载荷尾部复制到块中，然后将 `link->sendBuffer` 指向目标位置，因此应答就是存档当前持有的内容。会话以 `CLI_MSG_BUFFER_SUCCESS` 结束，该状态会到达 `MG_STATE_SAVE_LOAD_GIFT` 并将写入提交到闪存；从标题画面重新载入后它仍然存在。

    HOST --buffer-script save-write --dump-block sav2 --dump-offset 0xB20 \
        --write-text "some text" --version firered

一个载荷携带 936 字节。更长的数据会以 936 字节为单位分段写入，每段都是自己的载荷，在会话中依次运行；客户端按照其命令列表接收并运行它们 [mystery_gift_client.c:145, 236]。应答是最后一段写入后存档持有的内容。

`build_save_write` 会拒绝 `struct SaveBlock2` 中 0x090 的 `filler_90[8]` 与 0xB20 的 `filler_B20[0x400]` 之外的任何范围 [global.h:345,357]，而 `src/` 中没有任何代码引用它们。`filler_B20` 之后四个字节就是 `encryptionKey`，金钱会与之异或。`--write-unsafe` 可以覆盖此限制。块落在闪存中的位置会轮换（[id 位于何处以及哪个扇区承载插槽计数器](#where-an-id-lives-and-which-sector-carries-the-slots-counter)）。

一次 `save-write` 只会更改它指定的范围：一次 256 字节写入更改了 SaveBlock2 的 196 字节，全部在该范围内，而 SaveBlock1 没有变化。游戏中没有任何内容写入 `filler_B20`：写入那里的数据会在存档（十代，已测量）、神秘事件、神秘卡片、软复位和游玩过程中持续存在（在一分钟游玩中，SaveBlock1 变动了 1456 字节，而这 256 字节保持不变）。

### `memory-scan`

接受一个 32 位目标值和一个范围。每次调用会扫描其预算内的 32 字节块，将游标写回其映像并返回 0；到达末尾的调用会将 `link->sendBuffer` 重新指向结果并返回 1。映像开头是一条跳过其参数的跳转指令：

| 偏移 | |
|---|---|
| 0x000 | `b .Lcode` |
| 0x004 | 游标：起始地址，由载荷推进 |
| 0x008 | 结束地址 |
| 0x00C | 目标值 |
| 0x010 | 每次调用的块数 |
| 0x014 | max_calls，看门狗 |
| 0x018 | 结果：找到的匹配数、最终游标、已用调用次数、已存储匹配数 |
| 0x028 | 结果：64 ×（地址，值） |
| 0x228 | 代码 |

预算保护了需要帧的 RFU 链路。内层循环是对八个字执行一次 `ldmia` 和八个串联的 `cmpne`，每八个字约 14 条指令；在 unicorn 下默认 512 个块为每次调用 7703 条指令，约为每帧 280896 个周期中的 60000 个，这些周期来自 EWRAM（16 位总线，每次 ARM 取指约 6 个周期）。16 MB 卡带需要 1024 次调用，约 17 秒。`--scan-blocks` 可设置它；主机全程每秒读取约 60 个子帧。

`max_calls` 默认为范围所需次数加两次；看门狗停止时会以短游标应答，指出从何处继续。应答始终为 528 字节，因此 `len(dump) == buffer_dump_size` 可以证明发生了重新指向。`found` 统计每个匹配，`hits` 保存前 64 个。`ldmia` 只能看到字对齐的匹配：对于真实步长，目标值永远不会字对齐，因此返回零。

### `table-scan`

按形状查找表：每个最大连续运行都由 `runlen` 个字组成，每个字恰好比其前驱大 `delta`，应答为该运行的起始位置和第一个值。`gSpecialVars` [data/event_scripts.s:51] 列出了 `gSpecialVar_0x8000` 到 `0x800B`，即十二个连续的 `u16` [event_data.c:16]，因此其前十二个字以 2 为步长递增，第一个值为 `&gSpecialVar_0x8000`。

    HOST --buffer-script table-scan --table-delta 2 --table-runlen 12 \
        --table-start 0x08140000 --table-end 0x08400000 --version firered

第 12 项是 `gSpecialVar_Facing`，声明在 `Result` 和 `LastTalked` 之后，比第 11 项大 6，因此该运行恰好为十二个，第 13 个什么也找不到。

形状测试每个字约 7 条指令，而值测试约 1.75 条，因此 `TABLE_SCAN_DEFAULT_BLOCKS` 为 192 个 16 字节块，负载与 `memory-scan` 的 512 个 32 字节块相同。`run`、`runstart` 和 `expect` 位于游标旁边的 0x22C..0x234，并在每次让出时保存，因为一次运行可能会跨越 `ldmia` 和帧结尾。`expect` 初始值为 0，因此第一个字为零会被记入一个 `runstart` 尚未写入的运行；`read_table_scan` 会丢弃范围外的命中。

同样的形状可以找到活跃的 `struct ScriptContext`：`InitScriptContext` 在 +0x5C 和 +0x60 处存储命令表及其末尾 [include/script.h]，对于 17 项表两者相距 68 字节，因此在 EWRAM 上使用 `--table-delta 0x44 --table-runlen 2` 会返回上下文地址和表地址。在脚本运行之前该上下文为零，因此扫描必须在同一次启动中的神秘事件礼物之后进行。`--table-delta 0x358`（214 项）可以找到字段脚本上下文，其 `cmdTable` 就是已知的 `gScriptCmdTable`。

### `rom-checksum`

对一个范围求和，最多 128 个块，每块一个和，这样主机就能指出卡带中与其 ROM 映像不同的块；之后可以在一个块上以更小的块进行第二次运行来缩小范围。帧循环、预算、看门狗和重新指向的发送都来自 `memory-scan`。每个块从 0 开始按升序对其字求和：

    acc = w + ror(acc, 31)          每个字一条 `add r0, rN, r0, ror #31`，模 2^32

`rom_checksum_reference` 从 ROM 文件计算相同的内容。异或会相互抵消（重复的字求和为 0；相差 32 个字的相等变化会抵消）。参考范围末尾之后的块会按其特征和命名：零填充、0xFF 填充、开放总线（每个半字是其自身地址的一半）、镜像或 CONTENT。

| 偏移 | |
|---|---|
| 0x000 | `b .Lcode` |
| 0x004 | 游标：起始地址，由载荷推进 |
| 0x008 | 结束地址 |
| 0x00C | 起始地址 |
| 0x010 | 每次调用的 32 字节块数 |
| 0x014 | max_calls，看门狗 |
| 0x018 | shift：块大小的 log2，5 到 25 |
| 0x01C | 正在进行的块的运行和，跨调用携带 |
| 0x020 | 结果：最终游标、已用调用次数、已存储和数、回显的 shift |
| 0x030 | 结果：128 × u32 块和 |
| 0x230 | 代码 |

应答从 0x020 起为 528 字节。构建器会拒绝未按块对齐的起始地址、不是整块数倍数的范围、超过 128 个块，以及不是从 32 字节开始的 2 的幂的块。每八个字 13 条指令；512 个块为每次调用 6688 条指令。默认在 0x08000000..0x09000000 上以 128 KiB 块进行，共 1024 次调用，约 17 秒。

    HOST --buffer-script rom-checksum --version firered
    HOST --buffer-script rom-checksum --sum-start 0x08120000 --sum-end 0x08140000 \
        --sum-block 0x400 --version firered

主机会记录每个块的范围、两个和以及 `SAME` 或 `DIFF`，然后输出 `rom-checksum: N of M blocks differ from <image>`。映像是 `config.REFERENCE_ROMS[game code]`，或者用 `--sum-reference` 适用于所有构建。超出映像的块会被列出但不计数。

### `rng-trace`

每帧采样一个字，并在每个样本的两次读取之间调用一个 ROM 函数（`--trace-call 0` 会让它变成普通采样器）。

    HOST --buffer-script rng-trace --trace-address 0x03004220 --trace-call 0x080486B1 \
        --trace-samples 96 --version firered

该调用是 `mov lr, pc; bx r2`：pc 读取为 `bx` 之后的指令，位 0 清零，因此被调用方返回到 ARM 状态。在零售版火红中，`Random` 跟踪的每个样本都遵循 LCG（实测跟踪中 96 个里 96 个）。结果见 [RNG](frlg_rng.md)。

### `string-gather`

给定第一个指针的地址、步长和计数，将每个指向的字符串（直到并包括 0xFF 终止符）复制到一个应答中，并报告下一次运行从何处继续。
HOST --buffer-script string-gather --gather-address 0x083E0D54 --gather-count 69 \
        --gather-stride 12 --version firered

`--gather-stride` 对于 `struct EasyChatWordInfo`（`text` 在偏移 0）为 12，对于 `const u8 *` 数组为 4。答案为 776 字节：四个头部字，最多 760 字节字符串。它从不截断：放不下的字符串会结束运行并由 `next` 指出。`--gather-maxlen`（默认 64）限制不是字符串的指针。

### `create-mon`

```c
void CreateMon(struct Pokemon *mon, u16 species, u8 level, u8 fixedIV,
               u8 hasFixedPersonality, u32 fixedPersonality, u8 otIdType, u32 fixedOtId)
```

四个参数在 `r0..r3`，四个在栈上。`asm/create-mon.s` 遵循主机的函数序言：

    08041150  push {r4,r5,r6,r7,lr}    ; sp -= 20
    08041152  mov  r7, r8
    08041154  push {r7}                ; sp -= 4
    08041156  sub  sp, #28             ; sp -= 28, so entry sp is now sp + 52
    0804115c  ldr  r4, [sp, #52]       -> entry sp +  0   hasFixedPersonality  (masked to u8)
    0804115e  ldr  r7, [sp, #56]       -> entry sp +  4   fixedPersonality     (NOT masked: u32)
    08041160  ldr  r5, [sp, #60]       -> entry sp +  8   otIdType             (masked to u8)
    08041184  ldr  r0, [sp, #64]       -> entry sp + 12   fixedOtId            (u32)

这四个参数作为完整字放在 `sp+0..sp+12`，由 payload 自己弹出。生成的宝可梦构建在 payload 映像内部，代码前有 32 字节填充；`--create-mon-destination ADDR` 将其复制到目标地址，并需要 `--write-unsafe`。

    HOST --buffer-script create-mon \
        --create-mon-species 151 --create-mon-level 30 --create-mon-iv 31 \
        --create-mon-personality 0x3ADE0000 --version firered

`--create-mon-call` 默认来自 `rom_map.py` 中的 `CreateMon | 1`；`0` 不调用任何函数并返回清零缓冲区。答案为 116 字节（四个头部字，100 字节的 `struct Pokemon`），且 `*param` 是性格值。

子结构用 `personality ^ otId` 加密并进行校验和，因此有效的校验和可以证明这两个字。`check_create_mon` 检查物种、等级和个体值；`scratchpad/verify_create_mon.py` 预测十三个派生字段：经验值来自 `gExperienceTables[growthRate][level]`，亲密度和特性槽来自 `gSpeciesInfo`，招式与 PP 来自升级技能表，六项能力来自 `CalculateMonStats`。昵称来自 `gSpeciesNames` [pokemon.c:1810]，即卡带的法语表，只读取从不预测。三个字段用于衡量主机：

| field | value | what it says |
| --- | --- | --- |
| `language` | 3 | `gGameLanguage` 为 LANGUAGE_FRENCH [global.h:22] |
| `metGame` | 4 | `gGameVersion` 为 VERSION_FIRE_RED [global.h:11] |
| `metLocation` | 91 | `GetCurrentRegionMapSectionId()` [overworld.c:1265]，即玩家当时站的位置 |

`buffer_script.shiny_personality(tid, sid)` 给出异色的 `fixedPersonality`。`CreateMon` 的离线桩：`CREATE_MON_ARG_MODEL` 将八个参数写入目标，`create_mon_copy_model(source)` 复制 100 个准备好的字节。

#### `--create-mon-append`

它写入 `gPlayerParty`，而不是存档块中的队伍：

```c
void SavePlayerParty(void)
{
    gSaveBlock1Ptr->playerPartyCount = gPlayerPartyCount;
    for (i = 0; i < PARTY_SIZE; i++)
        gSaveBlock1Ptr->playerParty[i] = gPlayerParty[i];
}
```

追加到存档块会报告成功，但在下一次保存时会丢失 [load_save.c:160,196]。它在 `slot == playerPartyCount` 处写入并增加计数，就像捕捉那样；已占用的槽位永远不会被触碰，队伍已满时什么都不写入。第五个答案字报告 `countBefore | slot << 8 | status << 16`（0 未请求，1 已追加，2 队伍已满，3 试运行）。使用绝对 `--create-mon-destination` 的追加，或使用 `--create-mon-call 0` 的追加，会被拒绝。

    # dry run first: the same code with the two stores left out
    HOST --buffer-script create-mon --create-mon-append-dry-run \
        --create-mon-species 59 --create-mon-level 30 --version firered
    HOST --buffer-script create-mon --create-mon-append \
        --write-unsafe --create-mon-species 59 --create-mon-level 30 --version firered

试运行会报告数量、目标地址以及该槽位当前的 100 字节，从而发现 `playerPartyCount` 与队伍不一致的情况。空槽位并非全零：`ZeroMonData` 以 `SetMonData(mon, MON_DATA_MAIL, &MAIL_NONE)` [pokemon.c:1737] 结束，因此偏移 0x55 是 `0xFF`（`buffer_script.EMPTY_PARTY_SLOT`、`is_empty_party_slot`）。

| | 是否移动？ | 所以 |
| --- | --- | --- |
| `gSaveBlock1Ptr` | 会，每次战斗和加载时都会重新随机生成一个 4 对齐偏移 [`SetSaveBlocksPointers`, load_save.c:75] | 每次调用从 `r1`/`r2` 获取 |
| `gPlayerParty` | 不会，链接期 EWRAM 全局变量 | 地址是合法的 |

`gPlayerParty` 为 0x02024280，`gPlayerPartyCount` 为 0x02024025：EWRAM 转储中唯一一个可作为带校验和的 `struct Pokemon` 解码的 4 对齐窗口。

### `call`

一个地址，最多八个参数字，返回的 `r0`，以及调用两侧各读取一次的一个地址。

    HOST --buffer-script call \
        --call-address 0x080486D1 --call-arg 0xC0DE --call-watch 0x03004220 --version firered

    0x000  b .Lcode
    0x004  function    THUMB pointer (bit 0 set), or 0 to call nothing
    0x008  argc        how many of the eight words below are meant
    0x00C  args[0..7]  r0, r1, r2, r3, then [sp+0], [sp+4], [sp+8], [sp+12]
    0x02C  watch       a word to read before and after the call, or 0
    0x030  result      calls used, function, argc, r0, *watch before, *watch after

`asm/call.s` 总是压入十六个栈字节；被调用方从不弹出它们。`SeedRng` 不返回任何值（`gRngValue = seed` [random.c:15]），因此监视字就是证据。只能调用已经作为代码读取过的地址。`tests/test_buffer_script.py` 在 unicorn 下通过 payload 运行主机自己的 `SeedRng` 字节，并用 2 的幂测试八参数路径。

### `flash-write`

在 EWRAM 中组成一个 4 KB 扇区，并用 [`swi 0x48`](#the-flash-sector-path) 写入闪存，而不是通过游戏的保存代码。暂存区为 `gDecompressionBuffer + 0x400`，即 payload 自身映像上方 0x400 处。

    --flash-sector N            the sector, 0..31; 0..27 are the save bands and need --write-unsafe
    --flash-fill-base WORD      word[i] = base + i * step, the data pattern
    --flash-footer              compose a well-formed sector instead of a raw pattern
    --flash-id N                the sector id at +0xFF4
    --flash-derive              read the save globals and place it where that id actually lives
    --flash-position N          aim at band position N and derive the id from it instead
    --flash-counter-bias N      added to gSaveCounter for the footer

`--flash-footer` 会像游戏一样将模式结束到 `+0xFF4` 之间的区域清零，计算游戏的校验和，并写入 id、校验和、签名和计数器。状态字为物理扇区（高半部分）和校验和（低半部分）。`--flash-derive` 在写入时读取 `gLastWrittenSector` 和 `gSaveCounter`：两者在每次保存时都会递增，而以成功消息结束的礼物会话会保存 [mystery_gift_menu.c:1379]。

### `sloop-svc`

在一个会话中最多执行八个 Sloop 系统调用，操作数由主机选择，并通过结果块应答。

    IP_HOST --buffer-script sloop-svc --svc-number 0x4d --svc-text "hello fuck" \
        --svc-data-in r0 --version firered

    0x000  b .Lcode
    0x004  flags       bit 0: r0 = &copy, bit 1: r1 = &copy
    0x008  r0..r3
    0x018  scratch     gDecompressionBuffer + 0x400
    0x01C  length      of the data, at most 256
    0x020  thunk       swi N ; bx lr (THUMB), or bkpt N ; bx lr with --svc-bkpt
    0x024  count       1..8
    0x028  numbers     eight bytes, one per call
    0x030  data

每次调用前，payload 会重新复制数据，并将系统调用号写入 thunk 的低字节。结果块：标记 `0x53565331`、计数、标记 `0x53565332`、长度、八条 20 字节记录（thunk 字，之后的 `r0..r3`），以及最后一次调用留下时的数据。仅值型号码（0x46、0x49..0x4B、0x4D、0x4E、0x50..0x54、0x58..0x60）按原样执行；0x48、0x56、0x4C 和 0x55 被拒绝；其余号码以及 `--svc-bkpt` 需要 `--write-unsafe`；`--svc-bkpt` 拒绝 `#0x52`。

### `install-resident`

将常驻 THUMB 钩子复制到 `0x0203FC00`，并在一个会话内将其安装到 `gIntrTable[4]`。它每帧运行，贯穿 CONTINUER 和主世界，直到软复位。

    IP_HOST --buffer-script install-resident --resident turbo \
        --resident-param extra=4 --resident-param field=1 --resident-param battle=1 \
        --resident-param overlay=0x03004220 --resident-param hold=0x100 \
        --resident-param budget=228 --write-unsafe --version firered

    0x000  b .Lcode
    0x004  dest          0x0203FC00
    0x008  length        of the hook, whole words
    0x00C  table         &gIntrTable[4], 0x03002730
    0x010  entry_off     the hook's entry inside it
    0x014  original_off  its p_original word
    0x018  blob_off      where the hook starts in this image, after the installer's code

THUMB 安装器为 148 字节，剩余 876 字节给钩子，其数据（`p_frames`、`p_ring`、`p_state`）不得与其代码重叠，也不得越过 `0x02040000`。复制和表写入期间会清除 REG_IME。首次安装会将被替换的处理程序保留在 `0x0203FBFC`；后续安装会链接到该字，当其为空时以 `0xBAD0BAD0` 拒绝。答案就是找到的处理程序：干净安装时为 `0x0800071D`。一次只有一个钩子常驻；所有钩子共享 `0x0203FC00` 处的 1 KB。

#### `turbo`

`asm/resident/turbo.s` 运行 `VBlankIntr`，然后在空闲帧中额外运行主世界的 `field` 次回调，额外运行战斗的 `battle` 次回调，以及额外运行 `extra` 次 `RunTextPrinters`（`0x08002D51`）。一次额外执行只在 `callback1`/`callback2` 恰好为 `CB1_Overworld`（`0x08059E49`）/ `CB2_Overworld`（`0x08059EC9`）或 `BattleMainCB1`（`0x08015B6D`，由 `0x08013FDE` 处的战斗初始化存储）/ `BattleMainCB2`（`0x08014889`）时运行，并在两次调用之间重新检查。`newKeys` 和 `newAndRepeatedKeys` 会先被清除，因此一次按键只处理一次。

当 `gPaletteFade.active`（`0x02037AB4`）被置位时不会运行任何额外执行：硬件淡出在 `UpdatePaletteFade` 设置一位的 `hardwareFadeFinishing` 且下一个 V-blank 看到它时结束 [palette.c:701, 743]；一帧内的第二次更新会将此位回绕为 0，然后 `CompleteWhenChoseItem` 会在战斗中选择道具后背包关闭时永远等待。还有两个门控：

- `gMain.intrCheck`（`0x030022EC`）位 0 清零，在 `VBlankIntr` 之前读取：主循环停在 `WaitForVBlank` [main.c:462]。置位表示滞后帧，保持原样。
- `sTextPrinters`（`0x02020034`，32 个 0x24 字节）中没有处于原点（`currentX == x`、`currentY == y`）的活动打印机：野外消息会在其框绘制前添加打印机 [field_message_box.c:44]，而在框绘制前进行额外执行会把文本打印到随后被框清除的窗口中。

在模拟器上测量：每秒 60 帧，97% 空闲，文本每帧五个字形；`field=1` 使主世界速度翻倍，`battle=1` 使战斗及其菜单速度翻倍。

`hold=MASK` 仅在 `gMain.heldKeys`（`gMain + 0x2C`）按住掩码中的每个按键时才运行回调额外执行；文本额外执行始终运行。当 `hold=0x100`（R）时，钩子每帧将 1 存储到 `gHelpSystemToggleWithRButtonDisabled`（`0x0203F171`，即 `RunHelpSystemCallback`（`0x0813F65C`）中 `0x0813F6FC` 处的字面量），因此 R 不会打开帮助系统 [help_system_util.c:50]；L 仍然会。

`budget=LINES` 按时间限制额外执行。Switch 模拟器在一帧代码运行时推进 `REG_VCOUNT`（0 到 227，V-blank 从 160 开始）；只有当自 V-blank 以来的行数加上上次额外执行消耗的两倍不超过 `LINES` 时才会开始额外执行。上次消耗在计数器 `+0x0C` 处，被扣住的额外执行在 `+0x10` 处计数；每次被扣住的执行会使保留的消耗缩减八分之一。

在模拟器上测量：
| 设置，按住 R 时 | 每帧额外 pass 数 | 备注 |
|---|---|---|
| `field=2 battle=2` | 2 中的 1.70 到 1.90 | 约 2.9 倍，无明显延迟 |
| `field=3 battle=3` | 3 中最多 2.38 | 约四分之一帧延迟；可见卡顿 |
| `field=3 battle=3 budget=228` | 最多 2.48 | 流畅；一次 pass 行走时占 36 到 42 个扫描行，对战中占 100 到 108 个扫描行 |

`overlay=ADDRESS` 将 `ADDRESS` 处的字以八位十六进制数字显示在主世界右上角
（`0x03004220` 为 `gRngValue`）。这些条目写入 `gMain.oamBuffer[120..127]`（`0x030026C8`），两种颜色
写入 `gPlttBufferFaded`（`0x020375F4`）和 `gPlttBufferUnfaded`
（`0x020371F4`）的 OBJ 调色板 15，位于 `VBlankIntr` 的 `LoadOam` 与 `TransferPlttBuffer` 之前
（若在其后，顶部各行会滞后一帧）。一个 128 字节的 1bpp 字体（16 个 3x5 数字，取第 1 至 5 行的
第 2 至 4 像素，`asm/resident/overlay.inc`）在两个哨兵字不同时展开到 OBJ tile 1008 到 1023。
该 overlay 会覆盖游戏保存在调色板 15 和这些 tile 中的任何内容。

`ring=ADDRESS`（140 字节；`0x0203FF74` 结束于 EWRAM 顶部）按 `VBlankIntr`
读取到的值保存 `gRngValue`，每帧一个字，共 32 帧，并在 `watch`（`gEnemyParty[0]` 的性格值，
`0x02024028`）改变时冻结。草丛遭遇的性格值可由每一个保存的种子推得。在模拟器上于草丛中
行走时测得：每帧两次 `Random` 调用；从前一帧的种子起，性格掷骰是第五次调用
（`VBlankIntr` 的 [main.c:412]，本帧自身那次、槽位、等级、性格）。

#### `shiny`、`ivs`、`noencounter`

`shiny`（`asm/resident/shiny.s`）倒计时到下一次野生异色掷骰。`VBlankIntr` 每帧调用一次
`Random` [main.c:412]；野生宝可梦为性格掷出 `Random() % 25`，然后抽取
`Random() | Random() << 16`，直到性格匹配 [wild_encounter.c:233, pokemon.c:1864]；
`method=1` 取第一对（脚本化的 `CreateMon`）。异色条件为 `TID ^ SID ^ high ^ low < 8`，
TID 和 SID 取自 `gSaveBlock2Ptr`（`0x0300422C`）`+0x0A`。该钩子逐帧跟踪 `gRngValue`
（最多 64 步，否则重新开始），每个空闲帧搜索 `search` 个候选，并以十进制显示目标性格以及
`target - current - offset`（`offset=4`，即草丛情形），或显示 `FF` 和搜索距离。
当按住 `slow`（R）时，它每帧多等待 `slow_frames` 个 V-blank：`IntrMain` 会在处理函数中
让 VCount 保持启用 [crt0.s]，因此 `m4aSoundVSync` 会运行；该钩子每等待一个 V-blank
就调用一次 `m4aSoundMain`（`0x081DF53D`；`gPcmDmaCounter` `0x03002F68`，来自
`gSoundInfo` `0x03005F80`），并在 `REG_IF` 中清除它。状态位于 `0x0203FF80`，占 36 字节。

`ivs`（`asm/resident/ivs.s`）在两行中显示队首宝可梦的个体值（`OVERLAY_TWO_ROWS`，
第二行在 `gMain.oamBuffer[112..117]`，y 为 10）：HP、攻击、防御、速度，然后是特攻、特防和
`personality % 25`。`GetMonData(mon, MON_DATA_IVS)`（66，`0x080432E5`）返回六个 5 位个体值，
HP 位于最低位 [pokemon.c:3250]；`GetBoxMonData` 会原地解密并重新加密
[pokemon.c:2992, 3327]，因此该调用只会在主世界的空闲帧中进行。

`noencounter`（`asm/resident/noencounter.s`）每帧向 `sWildEncountersDisabled`
（`0x020386D8`）写入 1，`StandardWildEncounter`（`0x08086528`）会首先测试该值
[wild_encounter.c:360]；`DisableWildEncounters`（`0x08085FAC`）是唯一其他写入者。
草丛、水面和游走遭遇都会停止；垂钓和甜甜香气走各自的路径。

#### `noclip`

`noclip`（`asm/resident/noclip.s`，304 字节）在按住 `hold` 中的按键（默认 `0x100`，即 R）期间，
让玩家可以穿墙行走。在主世界的每个空闲帧（`gMain.intrCheck` 位 0 清零，`callback2` 为
`CB2_Overworld`），它重写地图网格 `VMap.map`（`gBackupMapData`，`0x02031DF8`）中玩家
`currentCoords` 周围的四个地块，将碰撞改为 0、高度改为 15，同时保留 metatile id。
`VMap` 在 `0x03004260`（法语版）或 `0x03004310`（英文版）处是
`{s32 Xsize, s32 Ysize, u16 *map}`，即 `MapGridGetCollisionAt` 中的字面量。一个地块的
编码是 `metatile | collision << 10 | elevation << 12` [global.fieldmap.h:7]；
`GetCollisionAtCoords` 会先按碰撞位阻挡，再按 `IsElevationMismatchAt` 阻挡；后者会传入高度 15，
而 `ObjectEventUpdateElevation` 在高度为 15 的 tile 上会保持玩家自身高度不变
[event_object_movement.c:4830, 8346, 8400]。

下一个空闲帧会将每个地块还原，但仅在 `gMapHeader.mapLayout`（`0x02036DF8`）仍是它修改时的
布局、且该地块仍保留其 metatile id 并带有高度 15 和碰撞 0 时进行：若发生传送或游戏改写了
该 metatile，则保留新的地块。等于 `MAPGRID_UNDEFINED`（`0x3FF`）的地块会保持原样，
否则玩家可能会离开地图。对象事件仍会阻挡（`DoesObjectCollideWithObjectAt`），台阶仍可跳跃，
玩家旁边游荡的对象事件可能走到被打开的 tile 上。按住 R 会打开帮助系统，因此该钩子每帧向
`0x0203F171` 写入 1（参见 `turbo`）。状态位于 `0x0203FF80`，占 24 字节：布局、一个计数，
以及四个 `{u16 index, u16 block}`。

`tests/test_noclip.py` 通过每个卡带自身的客户端安装它，并用该卡带自身的
`MapGridGetCollisionAt` 和 `MapGridGetElevationAt` 读取结果。在 mGBA 上使用法语版卡带
于真新镇测得：向南走时，未按 R 玩家会停在栅栏前，按住 R 则穿过栅栏走过六个 tile；
对象事件仍会阻挡玩家。

#### `follower`

`asm/resident/follower.s` 让队首宝可梦作为真实对象事件跟在玩家身后一个 tile，由游戏自身的
移动动作驱动，因此游戏会绘制它的步伐、奔跑、台阶跳跃（弧线、阴影、落地灰尘）、门淡入淡出
和精灵优先级。设计参考 GB-Link 的 `cards/follow.s`（GPL-3.0）。它长 984 字节，超出了一次
`install-resident` 会话的容量，因此从存档安装
（[保存在存档中的驻留钩子](#a-resident-hook-kept-in-the-save)）。

在主世界的每个空闲帧（`gMain.intrCheck` 位 0 清零，`callback2` 为 `CB2_Overworld`），
于 `VBlankIntr` 之后：

| 步骤 | 钩子的行为 |
| --- | --- |
| 找到它 | 本地 id 为 `0xF0` 的活动对象事件；`0xF0` 是任何地图都不使用的本地 id；地图加载后尚无此事件 |
| 生成 | 在玩家所在 tile 上调用 `SpawnSpecialObjectEventParameterized(gfx, MOVEMENT_TYPE_NONE, 0xF0, x, y, elevation)`，在玩家迈出第一步前保持隐藏 |
| 每帧 | 将其当前高度设为 14（任何 tile 都没有该高度）：玩家走回它身上时不会受阻，也没有任何对象会与它对话 [event_object_movement.c:4899]；在场地锁定期间设置 `fixedPriority`，这样地图加载后仍保持该高度 |
| 玩家迈步 | 玩家离开的 tile 成为其目标；相距一个 tile 时，它获得玩家自身的动作族（奔跑会变为 `WALK_FAST`）；不在一条线上时，用 `MoveObjectEventToMapCoords` 直接把它移到那里 |
| 台阶 | 玩家的 `JUMP_2` 会使它的坐标移动两次：第一次把它带到台阶边缘，第二次让它留在那里；玩家下一步时它自己执行 `JUMP_2`，跨两个 tile；若与玩家在同一直线上相距两个 tile 且没有待处理的台阶，它会用 `WALK_FASTER`（0x35）一次一个 tile 地跟上 |
| 菜单 | 当 `sGlobalScriptContextStatus`（`0x03000FA8`）为 `CONTEXT_SHUTDOWN` 时设置 `sLockFieldControls`（`0x0300109C`）：执行 `RemoveObjectEvent`，因此存档中绝不会保存它；之后会重新生成 |
| 自行车、冲浪、潜水 | 隐藏在玩家所在 tile 上 |
| 新队首 | 移除并重新生成 |
| 碰撞 | 玩家在高度为 0 的 tile 上撞到它时，会把它放到玩家所在 tile |

| 队首 | 对象 |
| --- | --- |
| 拥有主世界精灵图的 42 个物种之一（`OBJ_EVENT_GFX_SNORLAX` 109 到 `DEOXYS_N`；代欧奇希斯为对应版本的形态，由构建器的 `deoxys=` 决定） | 其自身的 graphics id |
| 任何其他物种、蛋、按字母区分的未知图腾 | 卡比兽的 32x32 帧（109，`sAnimTable_Standard`）；其精灵的 `images` 指向 `0x0203FBB4` 处的九个 `SpriteFrameImage`（站立 0..2：图标帧 0；行走 3..8：帧 1；每个 0x200 字节，来自 `GetMonIconPtr`），使用 OBJ 调色板 15 |

每个空闲帧，图标调色板都会写入 `gPlttBufferUnfaded` 的 OBJ 调色板 15（`0x020375D4`）；
仅当混合值 `y`（`gPaletteFade + 4`，位 6..10）为 0 时才写入 `gPlttBufferFaded`
（`0x020379D4`）。门淡出会运行 `BeginNormalPaletteFade` 将 `y` 设为 16，然后在屏幕仍为
黑色时清除 `active` [field_weather.c:740, palette.c]；在 mGBA 上走进门时测得，`active`
保持置位 21 帧，然后 `y` 为 16 且 `active` 清除，再过四帧 `callback2` 才离开主世界。

在主世界中，当玩家面前的 tile 是跟随者且场地未锁定时按 A（游戏自身的 A、脚本或菜单会
优先取得该帧）：将 `gSelectedObjectEvent` 设置为它并运行 `ScriptContext_SetupScript`，
同时写入物种（对于没有叫声的 `SPECIES_EGG`，412，则写入 none）：

    6A                lock
    A1 SPEC 0000      playmoncry SPECIES, CRY_MODE_NORMAL
    5A                faceplayer
    4F F000 PTR       applymovement 0xF0: 66 FE (MOVEMENT_ACTION_EMOTE_SMILE, step_end)
    51 0000           waitmovement 0
    C5                waitmoncry
    7F 00 0000        bufferpartymonnick STR_VAR_1, 0
    67 PTR            message: "{STR_VAR_1} saute\nde joie !" (French), "{STR_VAR_1} jumps\nfor joy!" (English)
    66 6D 6C 02       waitmessage, waitbuttonpress, release, end

状态位于 `0x0203FFDC`，占 17 字节（`state=`）：`+0` 其对象事件或 `0xFF`；`+1` 是否有
待处理的迈步；`+2` 是否显示图标；`+3` 移动动作族；`+4` 最近看到的玩家坐标；`+8` 其目标；
`+12` 队首的物种；`+14` 生成它时对应的物种；`+16` 是否有待处理的台阶。图标帧表位于
`0x0203FBB4`（`images=`），占 72 字节，在安装器保留于 `0x0203FBFC` 的处理程序下方。

| 卡带 | `SpawnSpecialObjectEventParameterized` | `ObjectEventSetHeldMovement` | `ObjectEventClearHeldMovement` | `MoveObjectEventToMapCoords` | `RemoveObjectEvent` | `ScriptContext_SetupScript` | `gSelectedObjectEvent` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BPRF, BPGF | `0x08062130` | `0x080675A4` | `0x08067634` | `0x08063024` | `0x08061DB4` | `0x0806D3D4` | `0x03004294` |
| BPRE, BPGE | `0x08061FD4` | `0x08067448` | `0x080674D8` | `0x08062EC8` | `0x08061C58` | `0x0806D270` | `0x03004344` |

| 卡带 | `gMonIconPaletteIndices` | `gMonIconPalettes` | `GetMonIconPtr` |
| --- | --- | --- | --- |
| BPRF | `0x083CBEE8` | `0x083CB7A8` | `0x0809AA74` |
| BPGF | `0x083CBD24` | `0x083CB5E4` | `0x0809AA48` |
| BPRE | `0x083D197C` | `0x083D123C` | `0x0809A7B8` |
| BPGE | `0x083D17B8` | `0x083D1078` | `0x0809A78C` |

英文版数值来自 `pokefirered_switch.elf`；法语版数值则是在各映像中找到的相同字节。
`tests/test_follower.py` 按照 `install-kept` 在各映像上的安装方式运行该钩子；对象函数
用替身代替：生成、行走、图标帧与调色板、台阶等待与单次跳跃、对话脚本、菜单下的移除。

`AddSpritesToOamBuffer` 仅用 `gDummyOamData` 填充到 `gOamLimit` 为止的未使用 OAM 条目
[sprite.c:487]；`ResetSpriteData` 将 `gOamLimit` 设为 64 [sprite.c:297]，在主世界中该值
读数为 64（`0x02021B44`）：钩子写入的超过 64 的条目会一直留在屏幕上，直到某次屏幕
重置其精灵。

#### 已验证
| hook | 零售版法语火红，ESP32 无线电（每次安装应答 `0x0800071D`） | 模拟器 |
| --- | --- | --- |
| `turbo` `extra=4 field=3 battle=3 hold=0x100 budget=228` | 按住 R 快进 | |
| `overlay` | 绘制八个数字，每帧变化 | 在 CONTINUER 之后的回顾期间绘制 |
| `shiny` | 在草丛中倒计时；按 R 减速 | 跟踪的种子与 `gRngValue` 匹配；Python 模型对异色判断一致 |
| `ivs` | 队首的 IV 字和 `personality % 25` 与 `SaveBlock1 + 0x34` 的 `save-dump` 匹配 | 与 `gPlayerParty` (`0x02024280`) 匹配 |
| `noencounter` | 在草丛中行走时不会遇到野生宝可梦 | 无；软复位后遇敌恢复 |
| `turbo-lite+noclip+noencounter`、`turbo-lite.field=2 battle=2 hold=0x2`、`noclip.hold=0x100` | 一次会话应答 `0x0800071D`；按住 B 快进，按住 R 穿墙，草丛不遇敌，同时按住两键快速穿墙 | |
| `follower` | 走在身后一格，在台阶边缘等待，在玩家离开落点格子后跳下，带有游戏的阴影和尘土；奔跑以及跑过台阶时无闪烁；面朝它按 A：叫声、微笑、台词；开始菜单和门；一次会话将其写入存档并安装 | 在 mGBA 上相同，使用吉利蛋的精灵和水箭龟的图标 |

未解决：在模拟器上，overlay 在 CONTINUER 之后的回顾期间绘制，但在交互游玩中不绘制，而 `field` 仍会加速游戏。

每个 hook 在叶绿上运行只需改一个地址：`m4aSoundMain` 为 `0x081DF518`（其 `VBlankIntr` 中 `0x08000772` 的 `bl`）；其他所有常量通过火红自身的引用完全对应。`follower` 还会读取 ROM 表以及会移动的函数，列在其章节中。构建器接受 `version=`，主机端 `--version leafgreen`。在模拟的叶绿上验证：turbo 和 `shiny`，音乐完好。

### 一次使用多个 hook

每个 hook 以函数方式调用它所替换的处理器（`bl` 到 `p_original` 上的 `bx r3`），并通过自己压栈的 `lr` 返回，因此一个 hook 的 `p_original` 可以指向另一个 hook。`--resident turbo-lite+noclip+noencounter` 将 hook 从 `0x0203FC00` 起背靠背排列，把每个 hook 的 `p_original` 写成下一个 hook 的入口（Thumb 位置位），并交给安装器一个 blob，其入口是第一个 hook 的，`p_original` 是最后一个 hook 的。`install-resident`、`install-kept` 和 MOM 的加载器不变。设置项用其 hook 命名：`--resident-param turbo-lite.hold=2`。

| 规则 | 原因 |
|---|---|
| 顺序为 turbo、noclip、shiny、ivs、noencounter | turbo 的回调会在其他 hook 处理完该帧后运行 |
| 每个 hook 的数据放在 `0x0203FBB4..0x0203FBFC`，然后在代码上方 | 默认值重叠：`shiny`、`ivs` 和 `noclip` 都在 `0x0203FF80` 保存状态 |
| `shiny`、`ivs` 和 turbo 的 `overlay` 最多同时使用一个 | 每个都在 `gMain.oamBuffer[120..127]` 和 OBJ 调色板 15 中绘制 |
| `follower` 单独运行 | 984 字节：与任何其他 hook 一起会超过存档可容纳的 1004 字节 |
| 代码适合 `0x0203FC00..0x02040000` | 1024 字节；超过 876 字节后整套要经过存档，超过 1004 字节无处可放 |

`turbo-lite`（`asm/resident/turbo-lite.s`）是设置 `TURBO_LITE` 后汇编的 `turbo.s`：相同的 passes、gates、hold 和 budget，但没有 overlay 和 RNG 历史，356 字节对 696 字节。每个 turbo 帧测试都在它上面运行（`tests/test_turbo_lite.py`）；通过链的一帧会运行每个 hook 和 `VBlankIntr` 各一次（`tests/test_resident_chain.py`）。

### `install-kept`

`asm/install-kept.s`，192 字节，像 `install-resident` 安装自己的 hook 一样安装保存在 `filler_B20` 中的 hook：它读取 `gSaveBlock2Ptr`（该块每次加载都会移动），检查魔数、使校验和留在 `filler_B20` 内的长度以及总和，然后清除 REG_IME，将游戏处理器保留在 `0x0203FBFC`，复制 hook，写入其 `p_original`，并将 `gIntrTable[4]` 指向它。应答是表中找到的处理器；若未安装任何内容则为 `0xBAD0BAD0`。+0 处的 ARM 入口是缓冲脚本的；MOM 的 RAM 脚本运行 +8 处的 THUMB 入口，它将应答指向映像中的某个字。最后两个字按卡带修补：`&gSaveBlock2Ptr` 和 `&gIntrTable[4]`。

    IP_HOST --buffer-script install-kept --version firered

### 保存在存档中的常驻 hook

任何常驻 hook 都可以放在 `filler_B20` 中，并在启动后与 MOM 交谈再次安装，无需连接或主机。两个礼物会话进行设置：

    IP_HOST --buffer-script save-write --resident follower --version firered
    IP_HOST --gift resident-save --version firered

第一个会话将以下 blob 写到 `SaveBlock2 + 0xB20`，并在同一会话中从中安装 hook：

    +0x00  magic     0x32524B50, "PKR2"
    +0x04  length    the hook's bytes, whole words
    +0x08  dest      0x0203FC00
    +0x0C  entry     u16 offset of the hook's entry
    +0x0E  original  u16 offset of its p_original word
    +0x10  the hook
    +len   checksum  the sum of every word before it

超过一次 `save-write` 容量（936 字节）的 blob 由两次写入。该会话运行每次写入，然后运行 [`install-kept`](#install-kept)，每个都是各自的载荷：客户端按照其命令列表 [mystery_gift_client.c:145, 236] 依次接收并运行缓冲脚本，只有最后一个应答返回。

    client  RECV RUN  RECV RUN  RECV RUN LOAD_TOSS_RESPONSE SEND_LOADED  RECV COPY_RECV
    host    script    write 1   write 2  install-kept   <- the handler found

会话以 `CLI_MSG_BUFFER_SUCCESS` 结束，该消息会保存，因此 `filler_B20` 写入闪存。

第二个会话将 RAM 脚本绑定到 MOM，该脚本暂存 36 字节的 [ram-jump 跳板](#a-payload-larger-than-a-script-body) 并分支到 `install-kept` 的 THUMB 入口，该入口在脚本主体中逐字节携带（995 字节中的 428 字节）。与 MOM 交谈安装 hook；第二次访问会链接到保留的处理器，软复位会移除 hook，直到再次与 MOM 交谈。

| hook | blob | `save-write` 载荷数 |
| --- | --- | --- |
| `noencounter` | 48 | 1 |
| `ivs` | 520 | 1 |
| `turbo-lite` | 376 | 1 |
| `turbo` | 716 | 1 |
| `shiny` | 888 | 1 |
| `follower` | 1004 | 2 |

`tests/test_resident_save.py` 在主机和模拟客户端之间运行整个会话，并在启动的控制台上运行 MOM 的主体脚本：翻转一个字节、缺少第二次写入、长度超过 `filler_B20` 都不会安装任何内容。零售版火红从其 `PKR2` blob 安装 follower。

新的神秘卡片会解除绑定：`SaveWonderCard` 调用 `ClearSavedWonderCardAndRelated`，后者调用 `ClearRamScript` [mystery_gift.c:172, 160]。`filler_B20` 保持写入状态。

### `call-chain`

一帧内最多按顺序执行十六步，每一步一个应答字。

    HOST --buffer-script call-chain \
        --chain-step call:FlagGet,0x828 \
        --chain-step call:FlagSet,0x828 \
        --chain-step call:FlagGet,0x828 --version firered

一步为 24 字节（op、目标、四个参数），写作 `OP:TARGET[,ARG]...`，操作包括 `call`、`read32/16/8`、`write32/16/8`。调用目标可以是 `rom_map.CALLABLE` 名称（绝不能用反编译地址）。

一步可以从上一个结果 `prev` 获取其目标或第一个参数：

    --chain-step call:GetVarPointer,0x4024      prev = the address the GAME computed
    --chain-step read16+keep:prev               the value before, prev untouched
    --chain-step write16:prev,7                 the store, read back by the payload itself
    --chain-step read16:prev                    the value after

`ScrCmd_setvar` 通过 `GetVarPointer` 的返回值写入 [scrcmd.c:472]；没有 ScrCmd worker 是 `VarSet`（[ROM 地图](frlg_rom_map.md)）。写入永远不会成为 `prev`；读取会成为 `prev`，除非带有 `+keep`。每次写入都会将自身读回应答。

    0x000  b .Lcode
    0x004  count       how many steps are meant, 0..16
    0x010  steps[16]   {op, target, a0, a1, a2, a3}, 24 bytes each
    0x190  result      calls, count, steps executed, the op word that stopped it
    0x1A0  values[16]  one word per step, in order

未知操作码会停止运行并在应答中指明；ARM 端也会限制步数。构建器拒绝空链、超过十六步、调用 ARM 指针或卡带外部、来自 `prev` 的调用目标（错误的目标会使菜单挂起）、未对齐或不可达的读取、超过四个参数，以及任何没有 `--write-unsafe` 的写入（之后主机会提交存档）。

    call GetVarPointer(0x4024)   -> 0x020265B4
    read16 [prev] keep           -> 0
    write16 [prev] = 3           -> 3        the store, read back by the payload
    read16 [prev]                -> 3
    call VarGet(0x4024)          -> 3        the game's own reader, same frame

`gSaveBlock1Ptr` 改变基址后，该变量仍读为 3。金钱是 `*moneyPtr ^ gSaveBlock2Ptr->encryptionKey` [money.c:14]：

    read32 [0x03004228]              -> 0x02025554     gSaveBlock1Ptr
    read32 [prev + 0x290] keep       -> 0x5A5A198C     the ciphertext, before
    call GetMoney(prev + 0x290) keep -> 0x00000BB8     3000, the plaintext
    call AddMoney(prev + 0x290, 1234) keep
    call GetMoney(prev + 0x290) keep -> 0x0000108A     4234, exactly +1234
    read32 [prev + 0x290]            -> 0x5A5A02BE     the ciphertext, after

（示例值。）两对异或给出密钥，此处为 0x5A5A1234，即 SaveBlock2 + 0xF20 处的字（`rom_map.SAV1_MONEY`、`SAV2_ENCRYPTION_KEY`）。特殊功能从特殊变量读取其操作数：将 `gSpecialVar_Result` 设为 `GET_CARD_BATTLES_WON` 后，特殊功能 390 会应答卡片的 `battlesWon`，即 `SaveBlock1 + 0x3434` 在同一帧保存的值。

切勿从缓冲脚本调用传送或消息 worker：神秘礼物菜单没有主世界。它们属于 [字段存根](frlg_rng.md#the-payload-in-the-script-body)。

## 写入游戏将要加载的扇区

以下内容均在模拟器上测得。

### 校验和覆盖 id 的区块

`CalculateChecksum(data, size)` 将 `size` 字节按小端 u32 字求和，并把 `(sum >> 16) + sum` 折叠为 u16 [decomp:src/save.c]。`size` 是 `sSaveSlotLayout` 中 id 自己的区块大小，该布局在法语卡带上位于 `0x083F58C4`，由 14 个 {u16 offset, u16 size} 条目组成：

| id | size | id | size |
| --- | --- | --- | --- |
| 0 | 3876 | 4 | 3816 |
| 1-3 | 3968 | 5-12 | 3968 |
| 13 | 2000 | | |

`HandleWriteSector` 在复制区块前会将整个扇区缓冲区清零 [save.c:181-183]，因此游戏写入的扇区在其区块之后为零，对所有 3968 字节求和会得到相同校验和；而区块之后还有数据的合成扇区会被拒绝。只填充区块。当 id 在主机上确定时，最多填充 2000 字节，即最小的区块：这样一个校验和对任何 id 都有效。

### id 位于何处，以及哪个扇区承载槽的计数器

一个槽是 14 个扇区；游戏在两个槽之间交替并轮换 id [decomp:src/save.c:174]：

    physical = ((gLastWrittenSector + id) % 14) + 14 * (gSaveCounter % 2)

`gLastWrittenSector` 在每次完整保存时增加 1，到 14 后回绕 [:147]。在正常游戏中它与计数器一致，但当写入被标记为损坏时会分离：游戏从 `gLastKnownGoodSector` 恢复它 [save.c:159]，而 `Save_ResetSaveCounters` [:104] 会独立重置它。`gLastKnownGoodSector` 和 `gLastSaveCounter` 会在它前进之前取当前这一对，因此它们准确描述了上一代。通过解析页脚来查找扇区，绝不要依赖固定的文件偏移。

当扇区签名为 `0x08012025`，且对 `locations[id].size` 计算的校验和匹配时，`GetSaveValidStatus` 会将其计入，id 取自它自己的页脚：

- 只有当全部 14 个 id 都存在且有效时，一个槽才是正常的；槽内的计数器不需要一致；
- `slotNsaveCounter` 会按物理顺序在每个有效扇区上被赋值，因此它保存最后一个有效扇区的计数器。

因此，最后一个扇区携带较高计数器的完整带区会胜过所有扇区都携带较低计数器的带区（十三个 129 和一个 131 胜过十四个 130）。

| 地址 | 符号 | 宽度 |
| --- | --- | --- |
| `0x030045A0` | `gLastWrittenSector` | u16 |
| `0x030045A4` | `gLastSaveCounter` | u32 |
| `0x030045A8` | `gLastKnownGoodSector` | u16 |
| `0x030045AC` | `gDamagedSaveSectors` | u32 |
| `0x030045B0` | `gSaveCounter` | u32 |

IWRAM，法语版本。加载后，`gLastWrittenSector` 会描述被采用的槽。

### 本次会话自身保存不会写入的带区

完整保存会记录前一对，使 `gLastWrittenSector` 和 `gSaveCounter` 前进，然后写入递增后计数器所选择的带区 [save.c:144-153]。以成功消息结束的礼物会话会保存 [mystery_gift_menu.c:1379]；以任何其他结果结束的会话会返回菜单而不保存。当会话将以成功结束时，现在写入 `gSaveCounter % 2` 所选择的带区：会话的保存会写入另一个。要被采用，扇区需位于带区位置 13，计数器为 `gSaveCounter + 2`，即比会话的 `gSaveCounter + 1` 高 1。位置 13 的 id 是 `(13 - gLastWrittenSector) % 14`，在主机上计算得出。

### 从 RAM 快照合成扇区

保存例程在保存时才进行序列化，因此 SaveBlock2 的实时内容与它实际会写入的内容不同。在以下两种情况下，每个校验和都会通过，且 `gDamagedSaveSectors` 保持为 0：

- 加密密钥在加载时重新生成。`LoadGameSave` 恢复各块，生成新密钥，将其应用于 RAM 中每个加密字段，并存储到 SaveBlock2 [decomp:src/load_save.c:126-128]。由 RAM 合成且未改动 SaveBlock1 的 SaveBlock2 读取金钱时会得到 `raw ^ flash_key ^ ram_key`。加密集合 [ApplyNewEncryptionKeyToAllEncryptedData]：SaveBlock2 中的训练家塔时间、游戏统计、背包数量和树果粉末，以及金钱和硬币。
- 已保存的地图视图，位于 SaveBlock2 `+0x898` 的 420 字节（210 个 u16 元图块 id，空白为 `0x03FF`），只在保存时填充，在 RAM 中为零；合成的扇区会把野外地图绘制成空白网格。

正常保存会一次性写入全部十四个扇区，因此密钥和密文一起移动；部分写入必须保持这一点。

### 读取闪存：128 KiB 芯片上的 64 KiB 窗口

`swi 0x48` 线性寻址芯片。guest 加载会在 `0x0E000000` 看到 64 KiB 窗口，而 1 Mbit 芯片通过两个 bank 访问：

    sector N is bank N / 16 at 0x0E000000 + (N % 16) * 0x1000

窗口之上的地址会发生别名：`0x0E01E000`（扇区 30）会读取 `0x0E00E000`，即当前所选 bank 的扇区 14，通常为零。根据扇区计算 bank 和窗口。选择 bank 是游戏自身的四次写入 [decomp:src/agb_flash.c SwitchFlashBank，`0x081E0C74`，七条指令，无循环，无 `REG_WAITCNT`]，已被内联，因此 payload 不进行 ROM 调用：

    strb 0xAA -> 0x0E005555 ; strb 0x55 -> 0x0E002AAA ; strb 0xB0 -> 0x0E005555 ; strb bank -> 0x0E000000

读取按字节宽度进行；闪存总线为 8 位。

`ReadFlash` 唯一的持久效果——将 `REG_WAITCNT` 的 SRAM 字段设为 3（`WAITCNT_SRAM_8` [decomp:src/agb_flash.c:149]）——在启动后已经就位：`AgbMain` 会清除它 [main.c:143]，启动时的存档加载会调用 `ReadFlash` [intro.c:1006]，并且每个闪存例程都会写入 3（`gFlash->wait[0]` [agb_flash_mx.c:28, agb_flash_le.c:28]）。

绝不要让待发送的消息指向闪存。消息头和消息体以不同宽度读取窗口：

| 步骤 | 代码 | 加载 | 读到的内容 |
|---|---|---|---|
| 头 CRC | `CalcCRC16WithTable` [mystery_gift_link.c:166] | `ldrb` | flash：`0xDEC2` 是物理 `0x1BC00..0x1BFFF` 的 CRC，`0x5907` 是 `0x1E000..0x1E0FB`（已选 bank 1）的 CRC |
| 体 | `Rfu_InitBlockSend` 用 `memcpy` `0x081E44F4` 将每个不超过 252 字节的块复制到 `gBlockSendBuffer` [link_rfu_2.c:1357] | `ldm`，当源和目的字对齐且剩余 16 字节或更多时一次取一个字 | 其他字节：字节对 `01 cb`、`10 3a` 和 `04 3a` 的连续串，对 `0x0E01BC00` 和 `0x0E01E000` 完全相同 |

消息体 CRC 失败，主机会丢弃它，并且礼物菜单会卡在 RFU 链接开启状态。消息体字节的来源未知。`build_memory_dump` 及其两个同类会拒绝任何触及 `0x0E000000..0x0FFFFFFF` 的范围。`flash-read` 使用 `ldrb` 将扇区复制到 EWRAM 并发送该副本，这样可以准确返回该扇区。

### 修改真实存档中的一个字段

`flash-patch` 读取真实存档写入的扇区，修改一个字段并写回，因此密钥和地图视图保持一致。一次编辑涉及两个扇区：

    A   目标 id 的扇区：修改字段，对 id 自己的区块重新计算校验和，
        将计数器设为 gSaveCounter + 2
    B   带区位置 13 的扇区：将其计数器设为 gSaveCounter + 2，不修改其他内容，
        甚至不修改校验和，因为 +0xFFC 在校验和数据区之外

加载器采用该带区（十二个扇区为旧计数器，两个为新计数器），因为全部十四个 id 都有效，且最后一个有效扇区携带较高计数器。对玩家名字进行 `flash-patch` 只会修改扇区 A 的字段和校验和以及扇区 B 的计数器；加载会采用该带区，没有错误校验和，金钱和野外地图保持不变，密钥副本和地图视图都是游戏写入的内容。

### 完整链路

在模拟主机上测得：缓冲区脚本根据实时全局变量合成一个扇区，`swi 0x48` 写入它，游戏下一次保存提交该映像，下一次加载采用此带区，且 `gDamagedSaveSectors` 干净。所交付的模式（与加载器的预测试模式不同，后者不会出现在任何地方）在 EWRAM 中读回，两个位置各连续读取 500 个字。

# 读取存档

神秘礼物会话会读取实时存档：秘密 ID，以及每只队伍宝可梦的 PID、IV 和性格。不会写入任何内容，也不会有卡片易手。主机的日志通过 `pokeldn.frlg.save.readout` 解码从偏移 0 开始的 SaveBlock2 `save-dump`（名字、性别、TID、SID、游戏时间）或覆盖 0x38 的 SaveBlock1（每只队伍宝可梦的性格、IV 和 EV），并将 `trainer-id-probe` 的应答解码为 TID 和 SID。

## 训练家 ID 和秘密 ID

SaveBlock2 偏移 0 保存玩家名字、性别、32 位训练家 ID 和游戏时间 [global.h:327]。低半部分是训练家卡片上的 TID；高半部分是秘密 ID，不会显示在任何地方，也不会在任何链接消息中发送。

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS \
        --buffer-script save-dump --dump-block sav2 --dump-size 64 --dump-file dump.bin

    ./.venv/bin/python tools/frlg/dump_read.py dump.bin --block sav2

    dump.bin: 64 bytes from sav2 + 0x0
      playerName    'PLAYER'
      gender        boy
      trainerId     0x12345678  TID 22136  SID 4660
      playTime      12h 34m 56s

与训练家卡片不一致的 TID 表示读取有误。

## 队伍

SaveBlock1 0x34 是 `playerPartyCount`，然后是位于 0x38 的 `playerParty[6]`，每个 100 字节 [global.h:772]：六只共 604 字节。

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS \
        --buffer-script save-dump --dump-block sav1 --dump-offset 0x34 \
        --dump-size 608 --dump-file party.bin

    ./.venv/bin/python tools/frlg/dump_read.py party.bin --block sav1 --offset 0x34

    party.bin: 608 bytes from sav1 + 0x34
      playerPartyCount 5
      slot 1: PIKACHU   Lv25 nick='PIKACHU' OT='PLAYER' PID=0x00000019 Hardy   IVs=[10,20,30,15,5,25] checksum ok
      slot 2: ...

（示例值。）

IV 按 HP、ATK、DEF、SPE、SPA、SPD 读取。异色列会将每只宝可梦的 PID 与它自己的 OTID 比较。每个槽都 `checksum ok` 表示这是真实队伍。队伍宝可梦按 `.pk3`/`.ek3` 的存储方式存储（`pokeldn.frlg.save.mon`）：0x20 处的 48 字节与 `PID ^ OTID` 异或，四个子结构按 `PID % 24` 排序。

SaveBlock1 保存的是上次保存时的队伍（`SavePlayerParty` [load_save.c:160]，参见 `--create-mon-append`）。对于实时队伍转储 `gPlayerParty`，在两个被测卡带上的地址均为 0x02024280：

    --buffer-script memory-dump --dump-address 0x02024280 --dump-size 600

绝不要在多次运行之间沿用绝对的存档块地址；`save-dump` 会重新获取指针。IWRAM 和 `gRngValue` 的内容见[随机数生成器](frlg_rng.md)。

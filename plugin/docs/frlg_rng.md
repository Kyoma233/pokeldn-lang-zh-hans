---
title: The random number generator
parent: FireRed and LeafGreen
nav_order: 5
---

# gRngValue：读取、预测与瞄准

火红版的 `gRngValue` 可以被读取、从宝可梦预测出来，并通过一个野外存根瞄准，使得下一个剧本 encounter 成为异色宝可梦，具有指定的性格与 IV。地址为法语火红版（BPRF，0x0A）。

## 随机数生成器

```c
u16 Random(void) { gRngValue = 1103515245 * gRngValue + 24691; return gRngValue >> 16; }
void SeedRng(u16 seed) { gRngValue = seed; }
```

[src/random.c, include/random.h:18]

| 符号 | 地址 |
|---|---|
| `gRngValue` | `0x03004220` |
| `Random` | `0x080486B0` |
| `SeedRng` | `0x080486D0` |
| `gSpecialVar_0x8000` | `0x020370B4` |

`pokeldn/frlg/rom/lcg.py` 实现了相关运算；`distance(a, b)` 通过 baby-step/giant-step 算法精确计算。该映射排列所有 2<sup>32</sup> 个状态，因此距离值仅在较小时才具有证据意义（概率为 N / 2<sup>32</sup>）。`gRngValue` 和 `gSpecialVar_0x8000` 永远不会改变；存档块在每次战斗后移动，并加载 [load_save.c:75]。

## 速率：恰好每帧 2 次推进

状态每帧恰好推进 2 次：`--gift rng-rate-probe`（读取，`delay` N 帧 [scrcmd.c:651]，再次读取）测量出 `2N + 2` 次推进，其中 +2 来自 `delay` 周围的一帧。状态在读取后 n 帧的位置为 `advance(S, 2n)`。一次推进约为 8 毫秒。

## 种子的来源及为何无法携带

`SeedRngAndSetTrainerId` [main.c:264] 在标题屏幕的 START 按键按下时，从定时器 1（`REG_TM1CNT_L`）中获取种子 [title_screen.c:735]，共 65536 个可能值；读取存在亚帧抖动，因此无法通过精确按压 START 来选择种子。从 Mystery Gift 返回标题屏幕 [mystery_gift_menu.c:463]，因此在链接过程中设置的种子无法到达野外地图。

| `SeedRng` 调用位置 | 何时 |
|---|---|
| `SeedRngAndSetTrainerId` [title_screen.c:735] | 标题屏幕 |
| `LinkTestScreen` [link.c:318] | 未使用的调试画面 |
| `Debug_RfuIdle` [link_rfu_2.c:2670] | 未使用的调试画面 |
| `RfuMain1` [link_rfu_2.c:2116] | 仅限 Switch，受 `svc_4b() & SVC4B_RESEED_RNG` 控制，从主机广播的 `playerTrainerId` 中获取种子 |

没有任何已测量的状态来源于 `RfuMain1` 的重新播种；其比特何时被设置仍未知。

## 从宝可梦读取回生成它的状态

野生宝可梦需要四次抽取：个性值低位、个性值高位、HP/攻击/防御、特攻/特防/速度 [wild_encounter.c:233]。IV 增加了 30 位的校验，因此 `lcg.recover_wild_state` 能找到唯一一个状态。可能存在的抽取可能位于 IV 抽取之前或之间；其来源未知，因此搜索这两个间隙：

| 方法 | IV 之前的间隙 | IV 之间的间隙 |
|---|---|---|
| 1 | 0 | 0 |
| 2 | 1 | 0 |
| 4 | 0 | 1 |

在进行任何 RNG 推断之前，请将宝可梦的 PID 和 IV 与其六个统计值进行核对。

## 剧本战斗

```
setptr b0..b3 -> 0x03004220      gRngValue = seed          (opcode 0x11)
setwildbattle <species> <level>  CreateMon rolls PID, PID, IV, IV   (0xB6)
dowildbattle                     the battle starts          (0xB7)
```

`setwildbattle` 调用 `CreateMon(..., 32, 0, 0, OT_ID_PLAYER_ID, 0)` [script_pokemon_util.c:128]：普通的四抽取方法 1，无草丛或 encounter roll。两个命令都返回 FALSE，因此写入和生成在同一帧内执行；不能有任何可能 yield 的操作在它们之间（测试断言了这一点）。RAM 脚本由 `initramscript` 绑定，并以 `end`（0x02）结束，而非 `endram`，因此会重新触发。一个预测的异色 50 级 Ditto 精确匹配了 PID、性格与 IV。

读取实时状态并生成宝可梦，四次抽取从读取的状态开始；宝可梦消耗 4 次推进 (`Random32()` 2 次，IV 2 次 [pokemon.c:1796,1836,1845])，加上一个野外帧的 2 次推进。

## 种子读取 NPC

`--gift rng-seed-reader`，标志 ID 1015，一个绑定的 RAM 脚本：

```
copybyte gSpecialVar_0x8000+0, 0x03004220      (opcode 0x15)
copybyte gSpecialVar_0x8000+1, 0x03004221
copybyte gSpecialVar_0x8001+0, 0x03004222
copybyte gSpecialVar_0x8001+1, 0x03004223
buffernumberstring 0, VAR_0x8000               (0x83)
msgbox                                          the NPC prints the value
```

`rng_script.seed_from_printed(low, high)` 重新组合成一个字，并使用 `rng_script.check_two_readings` 对两次读取进行评分。

- 所有六个命令都返回 FALSE 并在同一帧内执行，因此读取不会撕裂。
- 文本指针是相对的：`setvaddress` (0xB8) 和 `vmessage` (0xBD) [scrcmd.c:171] 将操作数作为脚本体的偏移量，随存档块一起移动。
- `buffernumberstring` 打印一个 `u16` [scrcmd.c:1678]：两个变量，两行。

绑定到玩家母亲（组 4，地图 0，对象 1，`MOVEMENT_TYPE_FACE_LEFT`，从不隐藏）。Pallet Town 的对象事件会走走停停。

## 人类按 A 的精确程度

一位玩家在 30 秒前瞄准目标，经过一个固定偏移后落在标准差 4.5 帧范围内，因此按键大约有 9% 的概率命中目标帧；异色帧每隔约 8192 帧出现一次。`pokeldn/frlg/rom/rng_countdown.py` 是倒计时器；`--aimed-at STATE` 测量偏差（以帧为单位）。当 RAM 脚本槽位持有 Wonder Card 时，这是可行的路径。

在脚本的按钮等待时，钩子可以代替按下按钮，在确切的帧上按下且不写入 `gRngValue`：[shiny-press](frlg_rom.md#shiny-shiny-press-ivs-noencounter)，即本应用的 Shiny 传说。

## 执行搜索的存根

`--gift rng-shiny-hunt`，`pokeldn/frlg/rom/native_script.py`，`asm/field/`。所有四个存根都能在零售版上运行：

| 存根 | 礼物 |
|---|---|
| `shiny-seek.s` | `rng-shiny-hunt` |
| `mon-seek.s` | `rng-mon-hunt` |
| `mon-seek-far.s` | `rng-mon-hunt-far` |
| `mon-seek-both.s` | `rng-mon-hunt-both` |

```c
bool8 ScrCmd_setptr(struct ScriptContext * ctx)          // 0x11
{ u8 value = ScriptReadByte(ctx); *(u8 *)ScriptReadWord(ctx) = value; }
bool8 ScrCmd_callnative(struct ScriptContext * ctx)      // 0x23
{ void (*func)(void) = ((void (*)(void))ScriptReadWord(ctx)); func(); return FALSE; }
```

[scrcmd.c:300, :120]。`setptr` 将代码加载到 EWRAM，`callnative` 在野外地图中执行它，`CLI_RUN_BUFFER_SCRIPT` 无法到达（`notblisy/RUBYSAPPHIREDLC` 在红宝石／蓝宝石上做了同样的事）。`CreateScriptedWildMon` 没有固定的个性值，`OT_ID_PLAYER_ID` 不会抽取任何值，因此异色性是存根留下的状态之后的前两个抽取。

存根读取 `playerTrainerId` 位于 `gSaveBlock2Ptr + 0x0A`，并仅写入 `gRngValue`。搜索是有界的；在耗尽时，encounter 恢复为普通。每个存根在暂存之前都会在 unicorn 中运行一次（`tests/test_native_script.py`）。

### 战斗后 RAM 脚本可能无法返回

`CB2_InitBattle` 和 `InitOverworldBgs` 调用 `MoveSaveBlocks_ResetHeap` [battle_main.c:614, overworld.c:1337]，将 `gSaveBlock1` 按 4 的倍数移动 0..124 [load_save.c:75]，同时引擎保持其指针指向 `ramScript.data.script` [script.c:514]。`dowildbattle` 之后的任何内容都无法到达：恢复时可能会落在一个 stray battle、zero fill，或一个冻结野外地图的命令上。

战斗从存档块外部开始 [`rng_script.battle_and_exit`]：

    setvar 0x8000, 0x02B7      ->  0x020370B4: B7 02  =  dowildbattle ; end
    goto   0x020370B4

没有任何代码在战斗中写入 `gSpecialVar_0x8000`，`end` 返回控制权 [script.c:335]。没有 RAM 脚本可以依赖于战斗或地图加载后的存档块地址。

## 选择性格与 IV

`--gift rng-mon-hunt`，`asm/field/mon-seek.s`，标志 ID 1019，测试异色性、性格 (`personality % 25` [pokemon.c:5020]) 和 IV 楼层（抽取 3 和 4 [pokemon.c:1836]）：

    --hunt-nature adamant,jolly   --hunt-iv speed=31 --hunt-iv attack=20   --hunt-cap N

| 请求内容 | 1 状态中 | 典型冻结时间 | 达到上限时最坏情况 |
|---|---|---|---|
| 异色 | 8,192 | 0.02 秒 | 0.10 秒 |
| 异色 + 一个性格 | 204,800 | 0.55 秒 | 2.5 秒 |
| 异色 + 性格 + 一个 IV >= 20 | 546,133 | 1.5 秒 | 6.7 秒 |
| 异色 + 两个 IV = 31 | 8,388,608 | 22 秒 | 拒绝 |

`native_script.search_cost` 计算这些数据；主机拒绝超过 `--hunt-freeze-frames`（默认 900）的最坏情况。玩家看到的是静帧与音乐。`mon-seek.s` 是 160 字节的 163 字节暂存预算。

## 脚本体中的有效载荷

`setptr` 每个代码字节消耗 6 个脚本字节。引擎原地运行 995 字节的 RAM 脚本体，并且从不读取超过最后一个命令 [script.c:514]，因此最后一个命令之后的字节以每个字节 1 字节的存储空间存在。`&gSaveBlock1Ptr` (0x03004228) 提供该帧的脚本体地址；`asm/field/ram-jump.s` (36 字节) 是唯一暂存的部分：

    setptr x36    the trampoline, into gDecompressionBuffer        216 bytes
    callnative    -> trampoline -> payload -> back                   5
    setwildbattle / setvar / goto                                   16
    pad to a multiple of four                                        3
    payload                                                        755

trampoline 使用尾调用 (`bx r0`)，因此 payload 的 `pop {r4-r7, pc}` 返回到 `ScrCmd_callnative` 的调用者。它仅在 `ramScript.data.magic` 为 51 时才执行 [script.c:12]。

### 四字节对齐

THUMB 的 `ldr rN, [pc, #imm]` 使用 `Align(PC, 4)`。脚本体是字对齐的：存档块偏移量为 `& 0x7C` [load_save.c:75]，`RAMSCRIPT_BODY_OFFSET` 为 0x3624。`native_script.emulate_body_script` 遍历真实的脚本字节以检测错位。

### 证明大小而非跳转

`asm/field/mon-seek-far.s` 后跟非零填充至字节 995；仅当填充校验和正确时，存根才会执行搜索。`InitRamScript` 用零填充其余部分 [script.c:495]，因此短交付会留下 `gRngValue` 不变。`--gift rng-mon-hunt-far` 包含 196 字节的存根和 559 字节的填充。

## 搜索时 stray draw 无法影响结果

`asm/field/mon-seek-both.s` (232 字节, `--gift rng-mon-hunt-both`, 标志 ID 1001) 在两个位置测试楼层。使用 d3, d4, d5，个性值后的抽取：

| 方法 | 第一个三元组 (HP/攻击/防御) | 第二个三元组 (特攻/特防/速度) |
|---|---|---|
| 1 (干净) | d3 | d4 |
| 2 | d4 | d5 |
| 4 | d3 | d5 |

要求同时满足 `d3 | d4<<15` 和 `d4 | d5<<15`，覆盖所有三种方法。异色 + Jolly + SPEED >= 20 变为 1/1,456,000，约 4 秒典型；上限为 95%。

## 搜索报告的写入位置

`asm/field/mon-seek-log.s` (288 字节, `--gift rng-mon-hunt-log`, 标志 ID 1002) 将 `{marker, start, found, iterations, cap}` 写入 `gSaveBlock1Ptr + 0x348C`，即 `u8 unused_348C[400]` [include/global.h]，该区域没有任何代码写入。它能在战斗后存活并在存档时写入闪存；耗尽的搜索写入 `found` 为 0。

    --buffer-script save-dump --dump-block sav1 --dump-offset 0x348C --dump-size 32

`native_script.decode_hunt_log` 读取它。一次记录的搜索，603,745 次迭代，精确匹配 `lcg.distance(start, found)`，耗时 2-3 秒，3.7-5.6 个周期每条指令，相比模型的 `CYCLES_PER_INSTRUCTION_FROM_EWRAM`（3）稍慢。

## LeafGreen

这些存根无需修改即可运行：每个字面量都是一个链接时 IWRAM 字或常量，`TID ^ SID` 在运行时读取。参见 [LeafGreen](frlg_leafgreen.md)。

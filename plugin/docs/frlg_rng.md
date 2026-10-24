---
title: The random number generator
parent: FireRed and LeafGreen
nav_order: 5
---

# 随机数生成器

火红的 `gRngValue` 可以被读取、从一只宝可梦反推，并通过一个野外桩瞄准，使下一场脚本遭遇的宝可梦为异色，且性格与个体值符合选定要求。地址为法语火红（BPRF，0x0A）。

## 生成器

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

`pokeldn/frlg/rom/lcg.py` 是相关算术；`distance(a, b)` 通过小步／大步精确计算。该映射会置换全部 2<sup>32</sup> 个状态，因此距离仅在很小时才作为证据（概率 N / 2<sup>32</sup>）。`gRngValue` 和 `gSpecialVar_0x8000` 从不移动；保存块在每场战斗和加载时移动 [load_save.c:75]。

## 速率：每帧恰好 2 步

状态每帧恰好推进 2 步：`--gift rng-rate-probe`（读取、`delay` N 帧 [scrcmd.c:651]、再读取）测得 `2N + 2` 步，多出的 +2 是围绕 `delay` 的一帧。一次读取后 n 帧的状态为 `advance(S, 2n)`。一步约为 8 毫秒。

## 种子从何而来，以及为什么它无法被携带

`SeedRngAndSetTrainerId` [main.c:264] 在标题画面按下 START 时 [title_screen.c:735] 从定时器 1（`REG_TM1CNT_L`）取种子，共 65536 个值；该读取具有亚帧抖动，因此掐准 START 时机无法选定种子。从神秘礼物退出会返回标题画面 [mystery_gift_menu.c:463]，所以联机期间设置的种子永远不会到达主世界。

| `SeedRng` 调用位置 | 时机 |
|---|---|
| `SeedRngAndSetTrainerId` [title_screen.c:735] | 标题画面 |
| `LinkTestScreen` [link.c:318] | 未使用的调试画面 |
| `Debug_RfuIdle` [link_rfu_2.c:2670] | 未使用的调试画面 |
| `RfuMain1` [link_rfu_2.c:2116] | 仅限切换，以 `svc_4b() & SVC4B_RESEED_RNG` 为门槛，从主机广播的 `playerTrainerId` 取种子 |

没有任何测得的状态来源于 `RfuMain1` 重新播种；该位何时被设置未知。

## 从宝可梦反推生成它的状态

一只野生宝可梦对应四次抽取：性格低位、性格高位、HP／攻击／防御、速度／特攻／特防 [wild_encounter.c:233]。个体值增加了 30 位校验，因此 `lcg.recover_wild_state` 会找到唯一一个状态。一次多余抽取可能出现在个体值抽取之前或之间；其来源未知，因此两个间隔都会被搜索：

| 方法 | 个体值前间隔 | 个体值之间间隔 |
|---|---|---|
| 1 | 0 | 0 |
| 2 | 1 | 0 |
| 4 | 0 | 1 |

在做出任何 RNG 断言之前，请用宝可梦的 PID 和个体值对照其六项摘要能力值进行核对。

## 脚本战斗

```
setptr b0..b3 -> 0x03004220      gRngValue = seed          (opcode 0x11)
setwildbattle <species> <level>  CreateMon rolls PID, PID, IV, IV   (0xB6)
dowildbattle                     the battle starts          (0xB7)
```

`setwildbattle` 会调用 `CreateMon(..., 32, 0, 0, OT_ID_PLAYER_ID, 0)` [script_pokemon_util.c:128]：普通的四次抽取方法 1，没有草丛或遭遇判定。两条命令都返回 FALSE，因此写入和生成在同一帧内运行；任何会让出执行的内容都不能夹在它们之间（有一项测试断言了这一点）。RAM 脚本由 `initramscript` 绑定，并以 `end`（0x02）结尾，而不是 `endram`，因此它会重新触发。预测出的异色 Lv50 百变怪在 PID、性格和个体值上完全匹配。

读取实时状态并生成宝可梦时，四次抽取从读取到的状态开始；生成该宝可梦消耗 4 步（`Random32()` 2 步、个体值 2 步 [pokemon.c:1796,1836,1845]），一个主世界帧再增加 2 步。

## 读取种子的 NPC

`--gift rng-seed-reader`，标志 id 1015，一个绑定的 RAM 脚本：

```
copybyte gSpecialVar_0x8000+0, 0x03004220      (opcode 0x15)
copybyte gSpecialVar_0x8000+1, 0x03004221
copybyte gSpecialVar_0x8001+0, 0x03004222
copybyte gSpecialVar_0x8001+1, 0x03004223
buffernumberstring 0, VAR_0x8000               (0x83)
msgbox                                          the NPC prints the value
```

`rng_script.seed_from_printed(low, high)` 会重新拼装该字，`rng_script.check_two_readings` 会对两次读取进行评分。

- 全部六条命令都返回 FALSE，并且在同一帧内运行，因此读取不会撕裂。
- 文本指针是相对的：`setvaddress`（0xB8）和 `vmessage`（0xBD）[scrcmd.c:171] 会让操作数成为脚本体内的偏移，而脚本体会随保存块移动。
- `buffernumberstring` 打印一个 `u16` [scrcmd.c:1678]：两个变量，两行。

绑定到主角的母亲（组 4、地图 0、对象 1、`MOVEMENT_TYPE_FACE_LEFT`、从未隐藏）。真新镇的对象事件会四处走动。

## 人类按 A 能有多精确

瞄准 30 秒后的玩家在扣除固定偏移后，落点标准差为 4.5 帧，因此一次按键命中某一选定帧的概率约为 9%；而异色帧大约每 ~8192 帧出现一次。`pokeldn/frlg/rom/rng_countdown.py` 是倒计时；`--aimed-at STATE` 会以帧为单位测量偏差。当 RAM 脚本槽位存放的是神秘卡片时，就走这条路线。

## 执行搜索的桩

`--gift rng-shiny-hunt`、`pokeldn/frlg/rom/native_script.py`、`asm/field/`。四个桩都可在零售版上工作：

| stub | gift |
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

[scrcmd.c:300, :120]。`setptr` 会把代码暂存到 EWRAM 中，`callnative` 会在主世界运行它，而这是 `CLI_RUN_BUFFER_SCRIPT` 无法到达的（`notblisy/RUBYSAPPHIREDLC` 在红宝石／蓝宝石上也做了同样的事）。`CreateScriptedWildMon` 没有固定性格，且 `OT_ID_PLAYER_ID` 不进行抽取，因此异色判定是桩所留下状态之后的前两次抽取。

该桩会从 `gSaveBlock2Ptr + 0x0A` 读取 `playerTrainerId`，并且只写入 `gRngValue`。搜索是有界的；耗尽时遭遇就是普通遭遇。每个桩在暂存前都会在 unicorn 下运行（`tests/test_native_script.py`）。

### RAM 脚本可能无法从战斗中返回

`CB2_InitBattle` 和 `InitOverworldBgs` 会调用 `MoveSaveBlocks_ResetHeap` [battle_main.c:614, overworld.c:1337]，把 `gSaveBlock1` 移动 0..124 中 4 的倍数 [load_save.c:75]，而引擎仍保留其指向 `ramScript.data.script` 的指针 [script.c:514]。`dowildbattle` 之后没有任何内容可达：恢复执行会落在一场多余的战斗、零填充或一条冻结主世界的命令上。

战斗从保存块之外开始 [`rng_script.battle_and_exit`]：

```
    setvar 0x8000, 0x02B7      ->  0x020370B4: B7 02  =  dowildbattle ; end
    goto   0x020370B4
```

战斗中没有任何内容会写入 `gSpecialVar_0x8000`，并且 `end` 会返回控制权 [script.c:335]。任何 RAM 脚本都不得在跨战斗或地图加载时依赖保存块地址。

## 选择性格与个体值

`--gift rng-mon-hunt`、`asm/field/mon-seek.s`、标志 id 1019，会测试异色、性格（`personality % 25` [pokemon.c:5020]）和个体值下限（第 3 和第 4 次抽取 [pokemon.c:1836]）：

```
    --hunt-nature adamant,jolly   --hunt-iv speed=31 --hunt-iv attack=20   --hunt-cap N
```

| 要求 | 出现一次所需状态数 | 典型冻结 | 达到上限时最差 |
|---|---|---|---|
| 异色 | 8,192 | 0.02 s | 0.10 s |
| 异色 + 一种性格 | 204,800 | 0.55 s | 2.5 s |
| 异色 + 性格 + 一项个体值 >= 20 | 546,133 | 1.5 s | 6.7 s |
| 异色 + 两项个体值 = 31 | 8,388,608 | 22 s | 拒绝 |

`native_script.search_cost` 会计算此表；宿主会拒绝最差情况超过 `--hunt-freeze-frames`（默认 900）的搜索。玩家会看到画面静止但音乐继续。`mon-seek.s` 为 160 字节，处于 163 字节的暂存预算内。

## 脚本体中的载荷

`setptr` 每暂存一个代码字节要消耗六个脚本字节。引擎会就地运行 995 字节的 RAM 脚本体，并且从不越过最后一条命令读取 [script.c:514]，因此其后的字节都是每字节一个的存储空间。`&gSaveBlock1Ptr`（0x03004228）给出该帧的脚本体地址；`asm/field/ram-jump.s`（36 字节）是唯一被暂存的部分：

```
    setptr x36    the trampoline, into gDecompressionBuffer        216 bytes
    callnative    -> trampoline -> payload -> back                   5
    setwildbattle / setvar / goto                                   16
    pad to a multiple of four                                        3
    payload                                                        755
```

蹦床会尾分支（`bx r0`），因此载荷的 `pop {r4-r7, pc}` 会返回到 `ScrCmd_callnative` 的调用者。除非 `ramScript.data.magic` 为 51 [script.c:12]，否则它会提前返回。

### 对齐到四个字节

THUMB 的 `ldr rN, [pc, #imm]` 使用 `Align(PC, 4)`。脚本体按字对齐：保存块偏移为 `& 0x7C` [load_save.c:75]，且 `RAMSCRIPT_BODY_OFFSET` 为 0x3624。`native_script.emulate_body_script` 会遍历真实脚本字节以捕获未对齐。

### 证明尺寸而非跳转

`asm/field/mon-seek-far.s` 后跟非零填充直到第 995 字节；只有当填充校验和正确时，桩才会搜索。`InitRamScript` 会将其余部分填零 [script.c:495]，因此短投递不会动 `gRngValue`。`--gift rng-mon-hunt-far` 携带 196 字节桩和 559 字节填充。

## 搜索以避开多余抽取的影响

`asm/field/mon-seek-both.s`（232 字节，`--gift rng-mon-hunt-both`，标志 id 1001）会在两个位置上测试下限。设 d3、d4、d5 为性格之后的抽取：

| 方法 | 第一组三项（HP／攻击／防御） | 第二组三项（速度／特攻／特防） |
|---|---|---|
| 1（干净） | d3 | d4 |
| 2 | d4 | d5 |
| 4 | d3 | d5 |

同时要求 `d3 | d4<<15` 和 `d4 | d5<<15` 这两个字，就能覆盖全部三种方法。异色 + 爽朗 + 速度 >= 20 变为每 1,456,000 个状态出现一次，约 4 秒典型耗时；上限为 95%。

## 搜索报告的写入位置

`asm/field/mon-seek-log.s`（288 字节，`--gift rng-mon-hunt-log`，标志 id 1002）会把 `{marker, start, found, iterations, cap}` 写到 `gSaveBlock1Ptr + 0x348C`，即 `u8 unused_348C[400]` [include/global.h]，而没有任何代码会写这里。该数据能在战斗后存活，并在保存时写入闪存；耗尽搜索会写入 `found` 为 0。

```
    --buffer-script save-dump --dump-block sav1 --dump-offset 0x348C --dump-size 32
```

`native_script.decode_hunt_log` 会读取它。一次记录下 603,745 次迭代的搜索与 `lcg.distance(start, found)` 完全吻合，耗时 2-3 秒，每条指令 3.7-5.6 个周期，而模型中 `CYCLES_PER_INSTRUCTION_FROM_EWRAM` 为 3。

## 叶绿

这些桩无需移植即可运行：每个字面量都是链接期的 IWRAM 字或常量，并且 `TID ^ SID` 在运行时读取。参见 [叶绿](frlg_leafgreen.md)。

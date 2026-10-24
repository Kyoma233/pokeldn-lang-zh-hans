---
title: Sword and Shield
nav_order: 6
has_children: true
---

# 剑／盾

宝可梦剑／盾通过直接跑在 Pia 上的发布／订阅框架交换协议缓冲消息。

静态阅读来自盾 1.3.2 欧版镜像（`01008db008c2c000`，更新 NCA，SDK 7.7.0.0）；测量对照法文剑 1.3.2。两者共用网络代码。

| 页面 | 内容 |
|---|---|
| [卡带与会话](swsh_session.md) | 密钥、镜像、Pia 4、从关联到首个应用数据 |
| [同步框架](swsh_protocol.md) | 消息 id、内容、持有者、路由、队伍载荷 |
| [交换](swsh_trade.md) | 交换画面、盒子状态机、确认阶梯 |
| [神秘礼物](swsh_gift.md) | 神秘礼物菜单的本地无线分支 |
| [极巨团体战](swsh_raid.md) | 巢穴大厅、广播、托管一或多台主机加入的团体战、客人参战、极巨冒险、离开 |

## 来源

除非某节点名客户端，id、偏移与地址来自盾的 `main` 或空中流量。`pokeldn/swsh/trade.py` 中的 `SYNC_ANSWERS` 来自 `andyjusa/nxldn-lab` 对主机对主机抓包的解读（消息 97 与 60000 与 pokeldn 逐字节一致）。`kwsch/PokePiaSWSH`、`lincoln-lm/swsh-lan-client`、`andyjusa/nxldn-lab` 与 `Slashcash/PSD` 从 Pia 站点握手起覆盖 LAN 模式；均未覆盖 LDN 或主机迁移。

## 野外脚本

`bin/script/amx/*.amx`（1.3.2 中共 953 个）是带 64 位单元的 Pawn 3.x：魔数 `0xF1E1`，版本 10，标志 `0x1C`（紧凑代码、可休眠、无检查）。紧凑编码：每字节 7 位，高组在前，符号在首字节第 6 位。非分支单参数操作码也打包为 `(param << 32) | op`，按 3.x 顺序自 162 起编号（`LOAD.pri` 162、`LOAD.S.pri` 164、`PUSH.C` 188、`PUSH.S` 190、`STACK` 191、`ADD.C` 197、`ZERO.S` 200、`EQ.C.pri` 201、`INC.S` 204、`HALT` 210、`PUSH.ADR` 212）；偏移 0 处的 `halt 0` 可作锚点。

原生函数十二字节：`u64 0` 与一个 `u32` 名称哈希，由 `amx_Register`（`0x0066d970`）解析：

    h = 0; for each byte c: h = (h * 0x83) ^ c        (32-bit)

绑定表是 `.data` 中各模块的 `(name, function)` 对（如 getter `0x014aea00`）：777 个名字，513 个哈希中用了 512 个。道具：`ItemAdd`（`0x014acea0`）、`ItemSub`（`0x014acf40`）、`ItemGetNum`、`ItemAddCheck`、`ItemGetCategory`、`GetPocketNumberFromItemNumber_`。变量：`WorkGet`／`WorkSet`（哈希 64 位键）、`TempWorkGet`／`TempWorkSet`（UI 在脚本恢复前填入的索引）。调用为按参数从右到左 `PUSH`，再 `SYSREQ.N native, bytes`。

## 未解决

- [玩家资料](swsh_protocol.md#the-player-profile)：宝可梦营地会话中角色采样状态 3 与 4 代表什么（`StateCreateSession`、`StateConnect`）。把 `a_wr0301` 当作冠之雪原野外区域仅来自编号推断。
- [对战体育馆](swsh_protocol.md#the-battle-stadium-block)：`0x01430670` 为已存队伍记录读取哪个存档块，以及存档队伍描述符在 `+0x30..+0x135` 于 `v1/validate` 签名替换 `+0x36` 前保存什么（`0x015039f0` 之后 `[sp+0x28]` 处的条目）。
- 剑对盾：二进制阅读来自盾，主机是剑；[会话常量](swsh_session.md#taking-a-seat)在两者间成立。剑测试卡片版本掩码第 0 位，是从盾的代码推断的——测试为 `1 << (v == 0x2D)`，`0x007d4270` 的 31 处调用中有十一处同时比较 `0x2C` 与 `0x2D`——以及 PKHeX `RestrictVersion`（1 剑、2 盾、3 两者）；两份零售剑快照在 MyStatus `+0xA4` 带有 `0x2C`。剑自己的 `0x007d4270` 及其通信 id 字面量尚未阅读。
- [神秘礼物](swsh_gift.md#what-the-menu-refuses)：零售主机是否像模拟盾那样，把游戏中不存在物种的 kind-1 礼物收成名为「Egg」的坏蛋；以及这种蛋在孵化或交换时会怎样。

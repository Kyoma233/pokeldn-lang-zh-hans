---
title: FireRed and LeafGreen
nav_order: 4
has_children: true
---

# 火红／叶绿

Switch 版火红／叶绿是在模拟器中运行的原版 GBA ROM，叠有两层连接：

| 层 | 归属 | 文档位置 |
|---|---|---|
| LDN 与 Pia | 模拟器侧，与所有 Switch 作品共用 | [无线层](ldn.md) |
| GBA 连接：RFU 帧、席位、块发送 | ROM 侧 | 本系列页面 |

[pret/pokefirered](https://github.com/pret/pokefirered) 在 `REVISION >= 0xA` 时是游戏层协议的权威来源。法文卡带回报软件版本 `0x0A`，游戏代码为 `BPRF`（火红）与 `BPGF`（叶绿）。主机端还携带英、德、意、西、日五组卡带的 ROM／RAM 地址，共十二种卡带；玩家在朋友列表中选中 pokeldn 后，神秘礼物会根据游戏代码选用其一。覆盖范围见 [零售验证](frlg_rom_map.md#retail-verification) 与 [卡带映射](frlg_rom_map.md#the-international-revision-0x0a-cartridges)。

若主机在关联后约三秒离开，且 Pia 会话已完成，则收到的是不含 6、9、12 Mbit/s 的关联响应（见 [frlg_link.md](frlg_link.md)「广播的速率集」）。缺少 Pia 类型 2 加入响应会出现同样症状。

## 已可用

在零售硬件上，两种卡带均可：主机双向提供神秘礼物、作为主机或加入方交换、联盟房间完整连接对战、奇妙新闻、缆线俱乐部斗技场，以及来访的对战塔训练家。

通过礼物连接的两套解释器，主机可向游戏发送代码：读写内存、按构建把 ROM 映射为具名函数并带八个参数调用，以及用游戏自己的 `CreateMon` 把主机选定的宝可梦写入队伍。RNG 可端到端预测；瞄准闪光遭遇每次尝试只需按一次 A。

访客与封装层的接口见 [主机上的代码](frlg_rom.md#coverage)，封装层扫描管线到第一阶段见 [封装层自己的扫描管线](frlg_rom.md#the-wrappers-own-scan-pipeline)。

## 页面

| 页面 | 内容 |
|---|---|
| [连接协议](frlg_link.md) | RFU 连接层、席位屏障、联盟房间、聊天、连接对战、缆线俱乐部斗技场 |
| [神秘礼物](frlg_gift.md) | 礼物会话、制作礼物、奇妙新闻、来访训练家、被屏蔽的无线通信路径 |
| [主机上的代码](frlg_rom.md) | 神秘事件 VM、原生 ARM 载荷、实时存档 |
| [ROM 映射](frlg_rom_map.md) | 地址来源、四张函数表、物种表、法文 Easy Chat 词表 |
| [随机数生成器](frlg_rng.md) | 读取与预测 `gRngValue`、瞄准遭遇的野外桩 |
| [叶绿](frlg_leafgreen.md) | 相对火红的偏移图、以英文构建作测量仪器 |
| [主机端实现](frlg_host.md) | 交换与神秘礼物主机的组成 |

## 规则

- 叶绿在分段常数偏移上运行同一套代码（[叶绿](frlg_leafgreen.md)）。切勿跨未界定区间预测地址。
- 反编译的链接顺序是证据；其地址需在卡带上实测。`pokeldn/frlg/rom/rom_map.py` 记录每个地址如何取得。
- 载荷在发送前先用 unicorn 离线运行（`buffer_script.emulate`、`emulate_repeating`，两台模拟主机）。出错或永不返回 1 的载荷会挂起神秘礼物菜单；死循环的野外桩会冻结野外。

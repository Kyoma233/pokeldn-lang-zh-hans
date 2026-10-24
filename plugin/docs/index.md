---
title: Home
nav_order: 1
---

# pokeldn

pokeldn 实现了任天堂 Switch 本地无线（LDN），通过 ESP32 开发板作为无线电，与零售 Switch 主机上的宝可梦游戏通信；可用 USB 串口连接电脑或 Android 手机，也可通过蓝牙连接 iPhone。这些页面用反编译引用、反汇编地址和硬件测量记录协议细节。

从[应用设置](gui.md)或[命令行用法](usage.md)开始。

## 支持目标

七款游戏共用同一套 LDN 与 Pia 层：

| | FRLG | LGPE | SwSh | BDSP | PLA | SV | PLZA |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 交换 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 神秘礼物 | ✓ | ∅ | ✓ | ∅ | ∅ | ∅ | ∅ |
| 活动宝可梦 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 连接对战 | ✓ | ✗ | ✗ | ✗ | ∅ | ✗ | ✗ |
| 主机上的代码、存档读写 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

✓ 在零售主机上可用 · ✗ 尚未实现 · ∅ 该游戏在本地无线上无此功能
FRLG 火红／叶绿 · LGPE 去吧！皮卡丘／伊布 · SwSh 剑／盾 · BDSP 晶灿钻石／明亮珍珠 · PLA 传说 阿尔宙斯 · SV 朱／紫 · PLZA 传说 Z-A

火红／叶绿在 Switch 模拟器内运行 GBA ROM，因此 ROM 的 GBA 连接协议叠在 LDN 与 Pia 之上。另外六款游戏把各自代码直接放在 Pia 上：BDSP 使用 Unity/IL2CPP，剑／盾与去吧！通过 `gflnet3` 使用带协议缓冲的 C++，传说 阿尔宙斯、朱／紫与传说 Z-A 则静态链接 Pia。

## 章节

| 章节 | 内容 |
|---|---|
| [无线层](ldn.md) | LDN 与 Pia：广播、关联、各版本数据包格式、会话密钥派生。 |
| [逆向分析 Switch 游戏](switch_re.md) | 就地阅读零售游戏代码：NCA/RomFS 提取、IL2CPP 元数据、C++ RTTI。 |
| [火红／叶绿](frlg.md) | GBA 连接、神秘礼物、代码执行、RNG、卡带。 |
| [晶灿钻石／明亮珍珠](bdsp.md) | Pia 5.27–5.45、联盟房间与交换流程。 |
| [剑／盾](swsh.md) | Pia 4、同步框架、交换、极巨团体战、极巨冒险、神秘礼物。 |
| [去吧！皮卡丘／伊布](lgpe.md) | Pia 3、连接暗号与交换流程。 |
| [传说 阿尔宙斯](pla.md) | Pia 头版本 11、交换流程、合成记录。 |
| [朱／紫](sv.md) | Pia 头版本 11、可靠流、交换、太晶团体战、联合环。 |
| [传说 Z-A](za.md) | Pia 头版本 16 与二十种交换消息。 |
| [模拟神秘礼物](gift_simulated.md) | 由主机向没有本地神秘礼物的作品交换官方礼物宝可梦。 |
| [命令行用法](usage.md) | 各游戏的源码设置与命令。 |
| [桌面应用](gui.md) | 设置、银行、手柄、构建；Android 与 iOS。 |
| [代码组织](architecture.md) | 共享模块、宝可梦准备与校验。 |
| [硬件与设置](hardware.md) | ESP32 无线电、Switch 密钥，以及旧式 Linux Wi-Fi 网卡。 |
| [代码签名策略](code_signing.md) | Windows 发行版签什么、团队角色与隐私政策。 |

## 致谢

基于 [kinnay 的 LDN 库](https://github.com/kinnay/LDN) 与 [NintendoClients wiki](https://github.com/kinnay/NintendoClients/wiki)，并对照火红／叶绿反编译 [pret/pokefirered](https://github.com/pret/pokefirered) 阅读。

---
title: Adapters
parent: Hardware and setup
nav_order: 3
---

# Wi-Fi 适配器

Linux 主机可直接以 root 驱动一块支持 AP 的 Wi-Fi 网卡，代替 [ESP32 无线电](hardware_esp32.md)。此路径为旧方案。

| 症状 | 原因 |
|---|---|
| AP 启动时出现虚拟机式 USB 断开 | USB 模式切换（见下） |
| 静默主机 | 未设置 `accept_decrypted_ccmp` |
| `dmesg` 中 `failed to get tx report from firmware` | 主机自身拆卸 |

## 经 ldnrs 在 Windows 上使用 USB Wi-Fi

Windows 可通过 [ldnrs 0.0.3](https://github.com/unlimitedcoder2/ldnrs/releases/tag/0.0.3) 使用外置 USB Wi-Fi 适配器。请单独安装 ldnrs、完成适配器向导并保持守护进程运行。在 pokeldn 中打开**插件**，在**无线电**下选择 **USB Wi-Fi（Windows，ldnrs）**。Switch 密钥仍来自 pokeldn 的「设置」。

ldnrs 向导把适配器绑定到 WinUSB 并下载所需 Linux 驱动固件；在设备管理器恢复原驱动前，该适配器不再提供 Windows Wi-Fi。兼容性取决于 ldnrs；下方 Linux 网卡结果不适用于 Windows。

在 PowerShell 中，运行任意游戏启动器前先选择后端：

```powershell
$env:POKELDN_RADIO = 'ldnrs:'
python bin/swsh_gift_host.py --keys C:\Switch\prod.keys --species 25 --level 25
```

空参数选用本地管道 `\\.\pipe\ldnd`；冒号后可跟其它管道名。守护进程经该管道接收密钥。它拥有无线电、LDN 关联与加密；pokeldn 经既有用户态 IPv4 栈传递以太网帧。扫描、加入、主机与广播更新使用 [守护协议 7](https://github.com/unlimitedcoder2/ldnrs/blob/0.0.3/docs/daemon-protocol.md)。缺少守护进程、适配器未就绪或协议版本不同会报错失败。

守护进程侧关联允许 70 秒，启动器至少 90 秒：上游 [RTL8822BU 测量](https://github.com/unlimitedcoder2/ldnrs/blob/0.0.3/clients/python/ldnd/compat.py) 显示两次驱动重配置各约 14.5 秒。游戏握手在关联之后开始。一个守护进程同时只承载一个会话。会话结束时 pokeldn 关闭原始通道与网络，但留下外部守护进程运行。抓包保留游戏 UDP 流量；ESP32 计数器与捆绑库的 Wi-Fi 管理钩子不适用。

离线测试对照 ldnrs 0.0.3 Python 客户端的向量比较扫描／加入／主机请求，并与脚本化守护进程交换 UDP。带零售主机的 Windows 适配器在此后端尚未测试。

## 已测网卡

| 型号 | 类型 | 驱动 | 在测试主机上的结果 |
|---|---|---|---|
| TP-Link Archer T3U（`2357:012d`） | 外置 USB | `rtw88_8822bu` | 可靠；参考适配器 |
| ALFA AWUS036ACHM | 外置 USB | `mt76x0u` | 可靠 |
| Realtek RTL8821CE | 内置 PCIe | `rtw88_8821ce` | 可靠 |
| AMD RZ616 | 内置 M.2 | `mt7921e` | 约一半速度，有时退出前死锁 |
| MT7601U | 外置 USB | `mt7601u` | 原版驱动无 AP 模式；需钉住的 `mt7601u-ap` DKMS 模块（[树莓派主机](hardware_raspberry_pi.md)） |
| Intel AX200 | 内置 M.2 | `iwlwifi` | 失败：无法分配 IP |
| Atheros AR9271 | 外置 USB | `ath9k_htc` | 失败：通常无法分配 IP |

## 主机模式

`--skip-encryption` 跳过 LDN 的 Python CCMP 步骤，改由 mac80211 或硬件应用一次 CCMP；空中流量仍加密。Archer T3U（`config/host.toml` 中 `skip_encryption = true`）与 ALFA AWUS036ACHM 需要它。

`--accept-decrypted-ccmp` 用于在硬件解密明文周围仍保留 CCMP 头与 MIC 的监听驱动，如 Archer T3U 的 `rtw88_8822bu`；转发明文到 `ldn-tap` 前会剥掉 MIC。ALFA 交付标准帧，请保持关闭。

| 适配器 | 主机配置 |
|---|---|
| TP-Link Archer T3U | 跟踪的 `config/host.toml` 配置；无 Wi-Fi 标志 |
| ALFA AWUS036ACHM | `--phy phyN --skip-encryption --no-accept-decrypted-ccmp` |

`phy = "auto"` 仅解析单个 `rtw88_8822bu` USB `2357:012d` 设备，零个或多个都会失败。显式 `--phy phyN` 始终优先；仅用于一次性调试，因为每次重新枚举编号会变。启动会打印检测到的配置、收发模式，以及标志与已验证配置不符时的警告。

## TP-Link Archer T3U

`rtw88_8822bu` 自内核 6.11 起进入主线并列出此 USB id。确认内核已绑定：

```bash
modinfo rtw88_8822bu | grep -i 2357
lsusb | grep -i 2357
iw dev
```

### 让 NetworkManager 别管适配器本身

NetworkManager 会占用热插拔接口（`wlx...`）并开始后台扫描；信道切换会在接口出现后不久关掉无线电（测得约 11 秒）：

```text
rtw88_8822bu 3-1:1.0: write register 0x81c failed with -71
usb 3-1: USB disconnect, device number 2
```

排除适配器与 LDN 接口：

```text
# /etc/NetworkManager/conf.d/zz-ldn-unmanaged.conf
[keyfile]
unmanaged-devices=interface-name:ldnclient;interface-name:ldn;interface-name:ldn-mon;interface-name:ldn-tap;interface-name:wlx*;interface-name:wlan*
```

文件名须排在最后（`zz-`）：有的发行版会有更后的文件设 `unmanaged-devices=none`。重载 NetworkManager；`nmcli device status` 须显示适配器为 `unmanaged`，`NetworkManager --print-config | grep unmanaged` 须含该列表。若不含 `ldnclient`，NetworkManager 会抢走加入时创建的接口、把 wpa_supplicant 指过去，加入以 `[Errno 114] Match already configured` 失败。

更多 USB 3 模式切换与其它陷阱见上游英文原文。

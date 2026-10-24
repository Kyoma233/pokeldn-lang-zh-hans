---
title: ESP32 radio
parent: Hardware and setup
nav_order: 1
---

# ESP32 无线电

ESP32 板子通过 USB 串口作为无线电。它运行 `firmware/esp32/`，承载 LDN 的厂商 action 帧和以太网帧；广播加密、LDN 认证、IP 和 Pia 留在主机上，[便携信标](#portable-beacon)除外。`pokeldn.ldn.esp32_wlan` 为 LDN 库提供一个由该板子支撑的工厂，因此 `ldn.scan`、`ldn.connect` 和 `ldn.create_network` 无需更改即可运行，主机也无需 Wi-Fi 驱动。

## 支持的板子

| 芯片 | 主机连接 | 合并镜像 |
|---|---|---|
| 经典 ESP32（ESP32-D0WD，WROOM-32E） | 通过 USB 串口桥接器的 UART0 | `pokeldn-radio.bin` |
| ESP32-S3 | 原生 USB Serial/JTAG | `pokeldn-radio-s3.bin` |
| ESP32-C3 | 原生 USB Serial/JTAG | `pokeldn-radio-c3.bin` |
| ESP32-C6 | 原生 USB Serial/JTAG | `pokeldn-radio-c6.bin` |
| 经典 ESP32，ESP32-C6 | 低功耗蓝牙（iOS 应用），以及如上所述的 USB | `pokeldn-radio-ble.bin`、`pokeldn-radio-ble-c6.bin` |

所有目标都使用 2.4 GHz；不支持 ESP32-S2。具有独立 UART 和原生 USB 插座的 S3、C3 或 C6 必须使用原生插座（S3 GPIO19/20，C3 GPIO18/19）；通过 UART 插座时固件从不响应。当通过 USB 串口桥接器没有固件响应时，桌面应用从 ROM 引导加载程序（esptool `detect_chip`）读取芯片，并把 S3、C3 或 C6 识别为插入了错误的插座。`303a:1001` 被多个芯片共用；烧录时用 esptool 检测芯片。

| 板子 | 天线 | BOOT | 用户 LED | CPU，任务核心 | 空闲堆 | 通过原生 USB 的 BENCH，macOS |
|---|---|---|---|---|---|---|
| XIAO ESP32C3 rev 0.4 | 提供的外部天线，必需 | GPIO9 | 无（仅充电指示灯） | 160 MHz，核心 0 | 152656 | 880.1 KB/s |
| XIAO ESP32C6 rev 0.2（C6FH4，4 MB） | 陶瓷天线，由固件选择 | GPIO9 | 黄色，GPIO15，低电平点亮 | 160 MHz，核心 0 | 255196 | 824.6 KB/s |
| XIAO ESP32S3 rev 0.2（8 MB flash，8 MB PSRAM） | 提供的外部天线，必需 | GPIO0 | 黄色，GPIO21，低电平点亮 | 240 MHz，核心 1 | 212416 | 883 KB/s |

BENCH 无损耗；主机的波特率设置不会改变 USB 速度。较大的 S3 板（N8R2、N16R8）带有板载天线。板子指南：[XIAO ESP32C3](https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/)、[XIAO ESP32C6](https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/)。

XIAO ESP32C6 在 GPIO3 为低电平时为其射频开关供电；GPIO14 低电平选择陶瓷天线。C6 固件在 Wi-Fi 启动前将两者拉低；在 ESP32-C6-DevKitC-1 上这些引脚只连接到排针，因此一个镜像适用于所有 C6 板子。C6 站点被限制为 11b/g/n。其接收头没有 `sig_mode`、`mcs` 或 `cwb`：固件从 `cur_bb_format` 推导 `sig_mode`，从 `he_siga1` 推导 HT MCS，其速率字节是 OFDM 帧的 L-SIG 速率码。

每块板子完成的交换记录见[按板子划分的交换](#trades-by-board)。

### 复位后的 USB 链路（C6、S3）

打开端口会复位 C6 或 S3。在 ESP-IDF 默认的 `CONFIG_ESP_SYSTEM_BBPLL_RECALIB=y` 下，启动会停止为 USB Serial/JTAG 提供时钟的 BBPLL（`recalib_bbpll()`，`esp_system/port/soc/esp32c6/clk.c`），链路可能一直保持乱码，直到重新插拔板子（SOF 帧号冻结，`USB_SERIAL_JTAG_INT_RAW` `0000b5b2`，正常为 `0000b50a`）。C6 和 S3 构建将其设置为 `n`（需要 v5.2+ 引导加载程序；每个合并镜像都自带）：900 次 C6 打开中有 900 次应答，300 次 S3 打开中有 300 次应答。C3 没有此选项，也没有此故障。

C6 和 S3 构建带有 USB 监视器（`usbwatch.c`）：SOF 帧号停滞 2 秒会重启芯片，下一次 HELLO 将 USB 和时钟寄存器作为 LOG 行携带。它在第一个 SOF 帧或从电缆读取到第一个主机字节时启动，并且在蓝牙主机已链接时绝不重启：接在充电器上的板子看不到 SOF 帧，而直到固件 1.7.0，蓝牙主机的字节会触发它，因此接在充电器上的 C6 在 iPhone 应用下每 2 到 3 秒重启一次。使用 `POKELDN_USB_BEACON=1` 构建时，两种镜像还会将这些寄存器以每秒一次的速度作为厂商 action 帧广播到 `03:55:53:42:57:00`（布局见 `usbwatch.c`），`esp32_sniff.py --mac 03:55:53:42:57:00` 在 USB 失效期间会持续接收。

## 角色

| 角色 | 板子做什么 |
|---|---|
| idle | 在一个信道上处于混杂模式；每个带有任天堂 LDN 前缀 `7f 00 22 aa` 的 action 帧都发送给主机 |
| station | 使用主机派生出的 CCMP 密钥，按 BSSID 加入游戏机的网络 |
| access point | 在主机 BSSID 上的隐藏 SSID WPA2 网络，以相同方式设置密钥 |

游戏机的网络没有 4 次握手：两端都从广播的服务器随机数导出 CCMP 密钥。固件替换 ESP-IDF 私有 `struct wpa_funcs` 表中的四个条目（`esp_wifi_driver.h`）。其布局是 v6.1 blob 的 ABI；固件拒绝针对其他版本构建。

| 条目 | 替换内容 |
|---|---|
| `wpa_sta_connect` | 在标准回调周围安装 Switch 站点的 RSN 元素（CCMP、PSK、能力 `0x000c`） |
| `wpa_sta_rx_eapol` | 丢弃 EAPOL；一旦看到关联响应，就用 `esp_wifi_set_sta_key_internal` 放入密钥，然后 `esp_wifi_auth_done_internal` 打开端口 |
| `wpa_ap_join` | 添加站点并发送关联响应（`esp_send_assoc_resp`），无 EAPOL-Key 消息 1（`AP_START` 标志位 0 保持标准加入）；主循环安装成对密钥（`esp_wifi_set_ap_key_internal(CCMP, mac, 0, key)`）并打开端口（`esp_wifi_wpa_ptk_init_done_internal(mac)`），即 hostapd 的 `PTKINITDONE` 顺序（`wpa_auth.c:2290-2332`）；组密钥在 `WIFI_EVENT_AP_START` 时以索引 1 放入 |

陷阱：绝不要等待 `WIFI_EVENT_AP_STACONNECTED` 来安装密钥。只有 `esp_wifi_wpa_ptk_init_done_internal` 会发布它，因此没有 4 次握手时它永远不会到来，游戏机的第一个加密帧会被丢弃。

## 接入点的帧

softAP 的信标、探测响应和关联响应在闭源的 `libnet80211.a`（v6.1 `ieee80211_output.o` 偏移）中构建，与 `vendor/LDN` 的接入点发送的内容进行比较：

| 字段 | Switch 形式 | ESP32 softAP | 可设置 |
|---|---|---|---|
| 隐藏 SSID 元素 | 32 个零字节 | 长度为 0（`ieee80211_beacon_construct` 0xc4） | 否 |
| 支持速率 | `82 84 8B 96 0C 12 18 24` | `8B 96 82 84 0C 18 30 60` | 否；同样的十二个速率和基本位，9 和 18 在扩展中 |
| 扩展速率 | `30 48 60 6C` | `6C 12 24 48` | 否 |
| 能力，信标 | `0x0511` | `0x0431`（短前导码常量，`ieee80211_getcapinfo` 0x7b） | 否 |
| HT 元素 | 无 | 在 11b/g/n 中存在 | 已移除：固件设置为 11b/g |
| RSN 能力 | `0x000c` | hostapd 自己的 | 可设置：`wpa_ap_get_wpa_ie` 返回 Switch 的元素 |
| WMM | 无 | 在 11g 中存在 | 仅纯 11b 会移除它 |

隐藏的 softAP 只响应定向探测。没有配置 SSID 的关联请求会被丢弃（0x9c6）。`esp_wifi_80211_tx` 拒绝关联响应（`ieee80211_raw_frame_sanity_check` 0xf9），而且 blob 自身的信标无法停止。

## 串口协议

一个帧为 `COBS(type | payload | crc32-le(type | payload))` 后接 `0x00`；CRC 为 CRC-32/ISO-HDLC（`zlib.crc32`）。经典 ESP32 以 115200 波特启动；`BAUD` 会切换两端，板子保持该速率直到复位。在 S3 上，`BAUD` 会被确认，但不会改变 USB 传输速率。任何 `0x00` 之前的内容，包括 ROM 的启动文本在内，校验失败并被丢弃。

| type | direction | payload |
|---|---|---|
| `0x01` HELLO | 主机 | 无；以 CREDIT 0 应答，然后是 INFO。主机先发送 `0x00` 以结束任何不完整帧 |
| `0x02` BAUD | 主机 | u32 波特率；以旧速率返回 RESULT，等 UART 排空后（最长 3 s）切换；`open_serial` 以新速率重试首个 HELLO |
| `0x03` CHANNEL | 主机 | u8 信道；仅空闲时 |
| `0x04` STA_JOIN | 主机 | u8 信道、6 BSSID、32 SSID（LDN SSID 的十六进制文本）、16 密钥、6 站点 MAC（零 = 随机）；可选：u8 固定数据速率（AP_START 位 3..5 表）、u8 最大 TX 功率（每个单位 0.25 dBm，`esp_wifi_set_max_tx_power`，8 到 84，驱动将其上限设为 61）、u8 标志：1 每帧前发送 RTS，2 重试前不发送 RTS（`esp_wifi_internal_set_rts`） |
| `0x05` STOP | 主机 | 无；回到空闲，密钥被清除 |
| `0x06` AP_START | 主机 | u8 信道、6 BSSID、32 SSID、16 密钥、u8 最大站点数、u8 标志：1 原厂关联和四次握手，2 对站点不启用 QoS，4 不复制每个站点数据帧的 40 字节，位 3..5 为固定数据速率，`0x40` 每 1000 TU 发送一个信标，`0x80` 关闭混杂接收；可选第二个标志字节：1 关闭驱动的噪声底检查，2 检查间隔为 250，4 在每个 40 字节副本头部包含接收时间，8 重试上限为 7 和 4，`0x10` 对除本站点正常数据帧之外的每个帧发送 RX_CENSUS；然后可选最大 TX 功率（每个单位 0.25 dBm） |
| `0x07` AP_KICK | 主机 | 6 MAC、u16 原因码；解除认证 |
| `0x08` ETH_TX | 主机 | 一个以太网帧，由驱动使用站点密钥或组密钥加密。驱动队列满时每 1 ms 重试一次，最长 100 ms；发往已离开站点的帧会以 `0x3015` 失败。站点的以太网源地址必须是 LINK 中的 MAC，否则帧永远不会被确认 |
| `0x09` RAW_TX | 主机 | 一个不含 FCS 的 802.11 帧（`esp_wifi_80211_tx`）；用于通告 |
| `0x0A` SNIFF | 主机 | u8 信道、6 MAC；发往或来自它的每个管理帧和数据帧，以及信道上的每个 action 帧（LDN 通告是主机要切换到的网络的关键帧），均作为 RX_SNIFF 完整上报；MAC 为 ff:ff:ff:ff:ff:ff 时，将信道上的每个帧作为 RX_CENSUS 发送 |
| `0x0B` STATUS | 主机 | 无；以 STATUS 应答 |
| `0x0C` BENCH | 主机 | u32 字节数、u16 消息大小（8 到 1600）；先返回 RESULT，然后以 UART 能接受的速度发送 BENCH 消息 |
| `0x0D` LED | 主机 | u8 灯效模式、u8 峰值亮度、u16 周期毫秒（0：该灯效的默认值）、u16 持续时间毫秒（0：直到下一条 LED 命令）；返回 RESULT |
| `0x0E` DISPLAY | 主机 | 一条屏幕命令（[屏幕](#the-screen)）；无屏幕时返回 RESULT `0x105` |
| `0x0F` ALIVE | 主机 | 无，无回复；布防[主机看门狗](#the-host-watchdog)；仅发送到固件 1.4.0 及更高版本 |
| `0x10` BEACON | 主机 | u8 操作：0 WRITE 将 u32 偏移和字节写入暂存缓冲区，1 COMMIT u16 长度（校验并存储暂存映像），2 ERASE，3 START，4 QUERY（以 BEACON 应答）；其余操作返回 RESULT。固件 1.8.0 及更高版本（[便携式信标](#portable-beacon)） |
| `0x81` INFO | 板子 | u8 协议版本（1）、6 站点 MAC、6 AP MAC、u8 芯片修订、文本 |
| `0x82` RESULT | 板子 | u8 命令、i32 `esp_err_t` |
| `0x83` LOG | 板子 | 文本 |
| `0x84` RX_MGMT | 板子 | u8 信道、i8 RSSI、一个不含 FCS 的帧：LDN action 帧；作为主机时，还包含发往板子 BSSID 的管理帧、发往它的数据帧的前 40 字节，以及站点的 no-DS 广播完整帧 |
| `0x85` RX_ETH | 板子 | 驱动解密后的以太网帧 |
| `0x86` LINK | 板子 | u8 连接状态、u16 原因、6 MAC；原因 `0xFFFF` 表示 15 s 内未关联，`0xFFFE` 表示密钥被拒绝 |
| `0x87` STA_JOINED | 板子 | 6 MAC、u8 AID、i8 密钥安装结果、u8 端口已打开 |
| `0x88` STA_LEFT | 板子 | 6 MAC、u16 原因 |
| `0x89` STATUS | 板子 | 文本计数器（见下）；作为主机时每 2 s 主动发送一次；如果主机正在写跟踪，则每 5 s 轮询一次 |
| `0x8A` BENCH | 板子 | u32 序号和负载字节；最后一条的序号为 `0xFFFFFFFF`，并携带板子花费的 u32 微秒数 |
| `0x8B` CREDIT | 板子 | 自上次 HELLO 以来主机读取并处理的 u32 字节数，从分隔符后的字节开始计数；在 HELLO 时、每 1024 字节时、线路空闲时以及空闲期间每 100 ms 发送，且位于任何排队消息之前 |
| `0x8C` RX_SNIFF | 板子 | u8 信道、i8 RSSI、u8 `sig_mode`（0 传统，1 HT）、u8 传统速率码（`wifi_phy_rate_t`）、u8 HT MCS（位 7 表示 40 MHz）、一个不含 FCS 的帧；还有信道上的每个 10 字节 ACK |
| `0x8D` TX_DONE | 板子 | 驱动对一帧的 TX 完成通知，站点或接入点：u32 板子时间（µs）、u32 自其完成的 ETH_TX 以来经过的 µs（若没有则为全 1）、u8 是否被对端无线电确认、u8 接口、u16 长度、帧的前 24 字节（其 802.11 头） |
| `0x8E` BUTTON | 板子 | 一次 BOOT 按下，经 30 ms 去抖：u32 板子时间（µs）、u16 自启动以来的按下次数；主机打印 `BOOT button, mark N`，跟踪中保留该记录 |
| `0x8F` RX_CENSUS | 板子 | 每个接收到的帧，包括 FCS 失败帧和控制帧：u32 接收时间（µs）、i8 RSSI、i8 噪声底、u8 `rx_state`（0 良好）、u8 包类型（0 管理、1 控制、2 数据、3 其他）、u8 `sig_mode`、u8 速率码、u8 MCS（位 7 表示 40 MHz）、u16 `sig_len`（含 FCS）、帧的前 16 字节 |
| `0x90` BEACON | 板子 | u8 是否存储了映像、u8 是否正在运行、u8 分片数、u16 映像长度、u32 映像 CRC-32（整个映像的 `zlib.crc32`） |

`rx_state` 98 表示双流 HT（MCS 8 到 15），单流 ESP32 从不解码此类帧；65 表示任何其他调制方式下的损坏帧。

| STATUS 计数器 | 统计内容 |
|---|---|
| `tx_acked`, `tx_unacked` | 驱动的 TX 完成结果 |
| `tx_eth`, `tx_eth_failed`, `tx_eth_retried` | ETH_TX 已发送、失败，以及发现驱动队列已满的调用 |
| `tx_queued_max_us`, `_total_us`, `_n`, `_pending` | 从 ETH_TX 到 TX 完成，在匹配的 TX_DONE 上统计 |
| `wire_dropped`, `wire_rx_bad` | 丢弃的板到主机消息；主机命令的 COBS 或 CRC 失败 |
| `uart_fifo_ovf`, `uart_buffer_full`, `uart_overflow` | 128 字节硬件 FIFO 和 16 KB 环形缓冲区溢出，及其总和 |
| `uart_frame_err`, `uart_events_full` | 帧错误、奇偶校验错误和断点事件；UART 事件队列满时的滴答数（这些计数器可能少计） |
| `read_max_us`, `write_max_us`, `handler_max_us`, `handler_max_type` | 最长的主机链路读取回合（含 20 ms 超时）、写入器等待时间，以及命令及其类型 |
| `heap_min`, `queue_max`, `refused_heap`, `refused_queue` | 最小可用堆、出站队列最深深度、在堆下限时拒绝的消息数，以及在队列已满时拒绝的消息数 |
| `tx_eth_max_us`, `tx_eth_total_us`, `tx_eth_slow` | `esp_wifi_internal_tx` 中的 ETH_TX，含重试：最长、总和、超过 5 ms 的次数 |

EtherType 为 `0x88B7` 的帧是 LDN 认证帧；`esp32_wlan` 将其转换为 LDN 库的 `CustomFrameEvent`。其他以太网帧进入一个 L2 端口，端口由 `POKELDN_L2=tap|userspace` 选择：

| 端口 | 位置 | 启动器的套接字 |
|---|---|---|
| `userspace_ip` 协议栈 | 默认，所有平台 | `userspace_ip.udp_socket` 和 `packet_socket` |
| 以内核接口命名的 kernel TAP | 仅 Linux，`POKELDN_L2=tap` | 内核套接字，`SO_BINDTODEVICE` 和 `AF_PACKET` 保持不变 |
| `MemoryPort` | 测试 | 无 |

创建 TAP 需要 `CAP_NET_ADMIN`。

### 主机看门狗

主机对固件 1.4.0 及更高版本每秒发送一次 ALIVE（`esp32.ALIVE_EVERY`）。HELLO 之后的第一个 ALIVE 布防看门狗；HELLO 会解除布防，因此从不发送 ALIVE 的主机永远不会被监视。布防后，一块不在空闲状态的板子如果在 5 s（`HOST_SILENT_US`）内没有读到主机命令，就会执行 STOP 的拆除流程：接入点停止发送信标，其站点断开；作为站点时则断开连接。之后它会丢弃所有发往主机的消息且不计入统计，直到主机再次发送命令；否则每条排队消息会耗费一次 500 ms 的写入、一次 `wire_dropped` 和 LED 上持续的 `flash3`。如果主机在火红交换房间期间被杀掉，主机上将显示 2318-0006，之后的 JOIN 搜索也列不出该主机。

## 便携式信标

从固件 1.8.0 起，板子在 NVS 中存储一个 LDN 通告周期，并可在无主机时发送它。存储了映像且通电后 3 s 内没有主机命令时，它会启动映像的接入点，重放最多四条屏幕命令，并每隔 `interval_ms`（100）发送一次通告，每过 `dwell_ms`（500）移到下一个分片。HELLO、CHANNEL、SNIFF、STA_JOIN、STOP 和 AP_START 会结束它；被看门狗判定已消失的主机则会让它继续运行。`pokeldn.ldn.portable` 会从 `ldn.create_network` 将创建的网络构建映像；`bin/swsh_gift_host.py --save-to-board` 会存储剑／盾神秘礼物（[剑／盾神秘礼物](swsh_gift.md)）。

板子像主机一样构建每个帧（`firmware/esp32/main/advert.c`，PSA SHA-256、AES-CTR 和 AES-GCM）：使用存储的头、分片的负载，以及一个 nonce——它在每次启动时从随机值开始，每处理一个分片加一，就像主机上 `set_application_data` 增加它那样。`tests/test_esp32_beacon.py` 编译 `advert.c`，并将其帧与 LDN 库的帧逐字节比较，针对协议 1 和 3。

| 偏移 | 大小 | 字段（小端序） |
|---|---|---|
| 0 | 4 | `PKSA` |
| 4 | 1 | layout，1 |
| 5 | 1 | kind，1（一个通告周期） |
| 6 | 2 | 映像长度，含 CRC |
| 8 | 1 | 信道 |
| 9 | 6 | BSSID |
| 15 | 32 | SSID，按 AP_START 接受的形式 |
| 47 | 16 | 数据密钥 |
| 63 | 1 | 最大站点数 |
| 64 | 16 | 通告密钥 |
| 80 | 40 | 通告头：网络 ID、版本、格式、u16 大端大小、u32 大端 nonce |
| 120 | 2 | `interval_ms`，20 到 1000 |
| 122 | 2 | `dwell_ms`，至少为 `interval_ms` |
| 124 | 1 | 分片数，1 到 8 |
| 125 | 1 | 屏幕命令数，0 到 4 |
| 126 | 2 | 零 |
| 128 | | 每个分片的 u16 长度和通告明文；每条屏幕命令的 u16 长度和一个 DISPLAY 负载 |
| end | 4 | 之前所有内容的 `zlib.crc32` |

映像保存的是为其单一网络推导出的通告密钥和数据密钥，绝不包含 `prod.keys`。映像最大为 12288 字节。板子插在电脑 USB 上且没有打开任何应用时，会像在充电器上一样启动信标。

## 串口上限

经典 ESP32 UART 在 921600 波特下以 92.16 KB/s 从板子向主机传输；Pia 载荷是密文且不压缩。作为主机的板子还会发送每个站点数据帧的 48 字节 RX_MGMT 副本，除非设置了 AP 标志 4（`POKELDN_ESP32_AP_FLAGS=4`）；每个附近的 LDN 网络每秒增加约十条通告。

出站队列容纳 384 条消息，并在可用堆低于 64 KB 时拒绝消息；在线路速率下的控制台环境中，堆下限会在队列填满之前拒绝 RX_ETH。

### 波特率

`POKELDN_ESP32_BAUD` 设置 `open_serial` 切换到的速率，默认 921600；USB 桥接器决定上限。在 macOS 上 ELEGOO 板子的 CP2102 上，1500000 传输 149.1 KB/s 且无丢失，而 2000000 和 3000000 从不回应 HELLO。`tools/ldn/esp32_bench.py --port PORT --bauds LIST` 在每个速率下流式发送 BENCH。

### 主机到板子的命令丢失与 CREDIT

在控制台的洪泛下，板子可能在到达处理程序之前丢失主机命令。固件的对策，每项都针对其缺失情况进行了衡量：

| 原因 | 固件对策 |
|---|---|
| UART 中断在核心 0 上与 Wi-Fi 任务一起 | 从读取任务安装驱动，核心 1 |
| 阻塞的 ETH_TX 让 16 KB 环形缓冲区和 128 字节 FIFO 溢出 | CREDIT 流量控制 |
| FIFO 在 120 字节时排空，在 1500000 下距满 53 µs | 阈值 32（`uart_set_rx_full_threshold`），640 µs |
| `uart_read_bytes`（IDF 6.1 `uart.c:1738`）等待每个环形项的超时 | 等待一个字节，然后取 `uart_get_buffered_data_len` |
| `uart_write_bytes` 在 TX 环形缓冲区满时忙循环，饿死读取任务 | 写入者睡眠直到帧能容纳（`uart_get_tx_buffer_free_size`） |
| `UART_DATA` 事件填满携带溢出事件的 64 项队列 | 读取任务上方的一个任务每 tick 排空它；`uart_events_full` |

一旦板子发送了 CREDIT，主机的写入线程会保持已写入且未报告的字节数低于 8 KB（`esp32.FLOW_WINDOW`）；启动器的 trio 循环只入队，超过 512 个排队帧的 ETH_TX 和 RAW_TX 会被丢弃（`Radio.tx_dropped`）。在窗口关闭期间，某个计数在 0.3 秒内保持不变意味着字节已丢失，主机会重新打开窗口（`Radio.flow_resyncs`）。绝不要仅因静默而重新同步：繁忙的读取任务可能保持长达 0.7 秒，此时重新同步会让 16 KB 在途数据面对 16 KB 环形缓冲区。板子每 1024 字节记一次 CREDIT（`wire.c` `CREDIT_STEP`），因此主机将 CREDIT 与已写字节加上线路上的帧相抵。没有 CREDIT 的板子会被无节流地写入。板子记录超过 50 ms 的命令（`slow command`）和超过 100 ms 的读取任务轮次（`reader held`）。

HELLO 会重启两个计数，因此主机一直持有它直到没有任何在途数据，并保持窗口关闭直到板子发出 CREDIT 0（`tests/test_esp32.py::test_a_hello_mid_session_does_not_open_the_window`）。
`tools/ldn/esp32_cmd_loss.py TRACE` 会核对跟踪：将 ETH_TX 写入与 `tx_eth + tx_eth_failed` 核对，将自 HELLO 以来写入的字节与最后的 CREDIT 核对。

### 发送时序

ETH_TX 在驱动程序中耗时约 0.1 ms，等待 TX 完成的中位数约为 1 ms。在洪泛下，TX_DONE 到达主机最长可延迟 0.6 s。陷阱：嗅探板自己的线路在突发中积压，因此要按对端的确认来计时；接入点洪泛以 1 Mbit/s 广播，在每秒约 90 帧之后占满空中。

## 保持与接收遗漏

在火红交换中，以板子作为接入点时，一帧通常约 1 ms 完成；偶尔有一帧主机尚未确认，会保持 100 到 260 ms，而其后的帧则突发完成，此时板子既听不到主机的数据也听不到它的 ACK。信道决定了保持：在共享的繁忙接入点信道上，大多数交换会保持；在 11 信道上则没有。`config/host.local.toml` 接受 `[host] channel`；主机在信道 1、6 或 11 上加入一个主机。240 MHz CPU 和固定速率（AP 标志位 3..5：1、11、6、12、24、36、54 Mbit/s 对应 1 到 7）并不能消除保持。`tools/ldn/esp32_hold.py CAPTURE TRACE` 将每次等待拆分为阶段，`tools/ldn/esp32_hold_air.py` 列出嗅探器看到的内容，`tools/ldn/esp32_rx_copies.py` 将主机的重试与板子的接收遗漏匹配。

### 两块板的接收遗漏

作为接入点时，板子会遗漏某站点 OFDM 首份副本的 1% 到 22%；1 Mbit/s 的 DSSS 几乎从不遗漏。`tools/ldn/esp32_pair_bench.py AP STA --flood 0 --burst N --send R` 统计它们。
遗漏集中在紧跟板子自身发送之后的帧，例如在其 6 Mbit/s CTS 之后 60 µs 的数据帧。在安静信道上（在 3 到 9 信道上为 0.8% 到 2.3%）、在每个站点帧前有 RTS（STA_JOIN 标志 1）时以及在站点满功率下，遗漏更低。

信标间隔、混杂接收、噪声底限检查、接收缓冲区、CPU 时钟、IRAM 优化、接入点功率，以及 ESP-IDF v5.5.5 相对 v6.1，均未带来变化。大多数遗漏在接入点处不留任何痕迹，甚至没有 FCS 失败。

站点在每次重试前都发送 RTS（`lmacConfMib` +42，阈值在 +22；`esp_wifi_internal_get_rts`/`_set_rts`）。`lmacRetryTxFrame` 按照 `lmacConfMib` 限制重发（短重试 +21，长重试 +20，默认 32；`esp_wifi_internal_set_retry_counter`）。ACK 和 CTS 速率表位于 `0x3ff73400`..`0x3ff7341c`。

## 用户空间协议栈

`pokeldn.ldn.userspace_ip` 在主机进程内承载 IPv4、UDP 和 ARP。栈以接口名注册（加入者为 `ldnclient`，接入点为 `ldn-tap`）；`userspace_ip.lookup(name)` 对内核接口返回 None，每个启动器都以此选择自己的路径。地址和邻居来自 LDN 库的 `add_address` 和 `add_neighbor` 以及接收到的帧；没有邻居的单播目的地会发送 ARP 请求并丢弃数据报；`.255` 发往广播。超过 1472 字节的数据报会被分片，分片在 5 秒内重组。`udp_socket(port)` 和 `packet_socket()` 充当已绑定 UDP 套接字和 `AF_PACKET` 套接字的替身，每个都由一个套接字对支撑，每个排队数据报对应一个字节，因此 `select` 和 `trio.lowlevel.wait_readable` 可在所有平台上工作。

陷阱：板子的帧通过启动器自己的 trio 循环中的 trio 任务到达协议栈。切勿在该循环内阻塞于 `select`；应在 `trio.move_on_after` 下用 `trio.lowlevel.wait_readable` 等待。

## 板载 LED 与按键

LED 在经典 ESP32 上为 GPIO2，在 S3 上为反相 GPIO21，在 C6 上为反相 GPIO15；C3 固件不驱动 LED 引脚。BOOT 在经典 ESP32 和 S3 上为 GPIO0，在 C3 和 C6 上为 GPIO9；每次按下会发送 BUTTON（`0x8E`），闪烁 LED 并唤醒屏幕。在 ELEGOO ESP-32 Type-C 板（CP2102、ESP32-D0WD-V3、无品牌 PCB 天线模组）上，红色 LED 是电源指示，蓝色 LED 是 GPIO2。GPIO2 和 GPIO0 是启动配置引脚；固件仅在启动后驱动 GPIO2。

LED 使用 LEDC PWM（13 位，5 kHz）每 10 ms 运行一次，带有 2.2 伽马值和 150 ms 交叉淡变。

| 模式 | id | 默认周期 | 形状 |
|---|---|---|---|
| auto | 0 | | 该模式的样式，见下文 |
| off, on | 1, 2 | | |
| breathe | 3 | 3000 ms | 升余弦 |
| blink | 4 | 1000 ms | 半个周期内点亮 |
| flash3 | 5 | 1000 ms | 周期前 60% 内闪三次 |
| ramp-up, ramp-down, pulse | 6, 7, 8 | 1000, 1000, 1200 ms | 一次 |

自动样式：启动时一次脉冲，空闲时 4 秒暗淡呼吸，加入时 250 ms 闪烁，作为接入点且无站点时 1.5 秒较亮呼吸，已连接时暗淡常亮，嗅探时熄灭。

每帧都会叠加一次 LED 闪烁。加入失败、密钥被拒绝、板到主机消息被丢弃或主机命令丢失时，会播放 1.5 秒 flash3。交换或神秘礼物完成时会渐亮至全亮（`pokeldn.ldn.show_done`）。`tools/ldn/esp32_led.py --port PORT PATTERN` 设置样式；`--demo` 显示每种样式。

## 屏幕

I2C 上的 SSD1306 128x64 OLED 是可选件（SSD1315 和 SSD1309 模块也可用）。固件先探测 0x3C，再探测 0x3D；有屏幕时以 400 kHz 每 50 ms 绘制一帧。

| target | SDA | SCL | 板载引脚 |
|---|---|---|---|
| ESP32 | GPIO21 | GPIO22 | DevKit V1 D21, D22 |
| ESP32-S3 | GPIO8 | GPIO9 | |
| ESP32-C3 | GPIO6 | GPIO7 | XIAO D4, D5 |
| ESP32-C3 | GPIO5 | GPIO6 | 0.42 英寸 OLED 板自带的 72x40 屏幕，第二次探测 |
| ESP32-C6 | GPIO22 | GPIO23 | XIAO D4, D5 |

常见的四针模块自带稳压器和上拉电阻；其地址电阻选择 0x3C（丝印 0x78）或 0x3D（0x7A）。固件设置段重映射（`A1`）、反向 COM 扫描（`C8`）和备用 COM 引脚（`DA 12`）。ESP32-C3 0.42 英寸 OLED 板的 72x40 面板显示帧的第 30..101 列、第 24..63 行；这些引脚上的屏幕会得到紧凑场景（一行 12 个字符、半尺寸精灵图），由 `tools/ldn/screen_preview.py --panel 72x40` 离线渲染。

没有主机命令时，屏幕显示无线电状态：空闲、正在加入或主持、已连接，并统计每个方向的帧数。当无线电处于活动状态或动画播放时，屏幕为全亮度；在最后一次 DISPLAY、HELLO 或 BOOT 按下后 60 秒内也保持全亮度。之后亮度降至对比度 1，并设置预充电 `22`（`81 01 D9 22`）；600 秒后关闭（`AE`）。更低的预充电会闪烁。空闲画面每 60 秒移动 2 像素以防烧屏。`tests/test_esp32_screen.py` 保存了这些计时。

DISPLAY（`0x0E`）携带一个操作：

| op | layout |
|---|---|
| `0` SHOW | u8 show，u16 保持秒数（0：直到下一次显示），title，NUL，line，NUL；每个文本最多 21 个 ASCII 字符 |
| `1` SPRITE | u8 槽位（0 我方，1 对方，2 礼物），u8 宽度 <= 64，u8 高度 <= 64，每行 `(width + 7) / 8` 字节，MSB 在前；宽度为 0 时清空该槽位 |
| `2` LOBBY | u8 星星（0..7，0：无），u8 joined，u8 seats（1..3，至少为 joined），title，NUL，name，NUL，Link Code，NUL；开始大厅显示 |
| `3` JOINED | u8 joined，最多为大厅的 seats；没有大厅显示时拒绝 |

| show | id | drawn |
|---|---|---|
| auto | 0 | 无线电状态 |
| trade | 1 | 槽位 0 显示“offering”和该行 |
| traded | 2 | 槽位 0 随精灵球离开（2.1 秒），数据包持续传输直到保持时间结束，一个球到达并打开（1.6 秒），然后槽位 1 显示“received”10 秒 |
| gift | 3 | 一张神秘卡片持有槽位 2 |
| gifted | 4 | 卡片离开，然后显示“delivered!” |
| arrived | 5 | 仍在等待的 traded 显示现在带入它的球 |
| lobby | LOBBY | 槽位 0、标题、名称、星星、“joined/seats”和连接密码 |

一个显示会等待正在播放的 traded 或 gifted 显示；当无线电恢复空闲时显示结束。

`pokeldn.app.screen` 是启动器一侧：`offer`、`received`、`arrived`、`gift`、`delivered`、`lobby` 和 `joined` 立即返回，并在一个线程上按顺序运行。主持的团体战会显示一个大厅。每个启动器在交换最后一步调用 `received`，保持时间为下表时间减去 2.5 秒，以便精灵球与主机的动画同时打开：

| 标题 | 来自 | 主机端收到的宝可梦 | 动画后第一条消息 |
|---|---|---|---|
| 火红／叶绿 | START_TRADE | 22.7 s | READY_FINISH_TRADE（[火红链接](frlg_link.md)） |
| Let's Go | 步骤 `0e` | 15.3 s | type 4 payload（[Let's Go 会话](lgpe_session.md#the-trade-animation)） |
| 剑／盾 | 最后一个 syncCommand 40 | 15.0 s | 无（[剑／盾交换](swsh_trade.md#the-trade-animation)） |
| BD/SP | `tradeState` 5 | 18.6 s | 无（[BDSP 交换](bdsp_trade.md#the-completed-trade)） |
| 传说 阿尔宙斯 | `01 0e` | 28.5 s | 箱消息 `00 02`（[传说 阿尔宙斯](pla.md#the-completed-trade)） |
| 朱／紫 | `8001010e` | 19.8 s | 无（[朱／紫](sv.md#the-trade)） |
| 传说 Z-A | 第四步 | 26.2 s | 下一条 `01 01` 预览（[传说 Z-A](za.md#a-trade-with-a-retail-console)） |

时间由人工标注（最多迟到 2 秒）。启动器在动画后的消息处调用 `arrived`。精灵图使用 PokeAPI 的火红／叶绿图案，直到 386 号物种，之后使用默认图案；经过裁剪、缩放至最多 64（卡片上为 40），并阈值化为 1 位，保持内部线条为暗色。`tools/ldn/esp32_screen.py --port PORT` 在板上播放一次交换和一次礼物；`tools/ldn/screen_preview.py OUT.gif` 离线渲染脚本化会话。

### E32R40T 开发板

E32R40T（常被标为 4.0 英寸 ESP32-32E 显示屏）是一块经典 ESP32，配有 SPI 接口的 480x320 ST7796S 面板。其固件是单独构建：在 `idf.py` 环境变量中设置 `POKELDN_DISPLAY=E32R40T`（默认值为 `OLED`）；发布镜像均为 OLED 构建。

| 信号 | GPIO |
|---|---|
| CS, DC, SCK, MOSI | 15, 2, 14, 13 |
| 背光，高电平点亮 | 27 |
| RGB LED，低电平点亮：红、绿、蓝 | 22, 16, 17 |

该面板以 3 倍（384x192）显示 128x64 帧，白底黑字，SPI 频率 40 MHz。GPIO2 是面板的 DC，因此板载 LED 是 GPIO17 上的蓝色 LED。背光在 OLED 屏幕会关闭时也熄灭。

## 构建与烧录

固件版本（`firmware/esp32/version.txt`，`major.minor.patch`，所有目标共享）在 INFO 中报告为 `version=...`；未打版本的构建显示 `version unknown`，只要其串口协议匹配也可工作。协议号是独立的，仅在线上协议变更时改变。

ESP-IDF v6.1（标签 `v6.1`，提交 `fff9895c82d744c7237be8847347bdd1b07c6643`）可构建全部四个目标。使用 `install.sh esp32,esp32s3,esp32c3,esp32c6` 安装其工具，然后激活 IDF 环境。

    cd firmware/esp32
    idf.py set-target esp32   # esp32s3, esp32c3 or esp32c6 for those chips
    idf.py build
    idf.py -p <port> flash

控制台输出关闭；在经典 ESP32 上，固件自行分配 UART0 的 GPIO1 和 GPIO3（`uart_set_pin`）。桌面应用使用 esptool 检测芯片，并在写入前校验合并镜像在芯片 flash 偏移处的引导加载程序（ESP32 为 `0x1000`，其他为 `0x0`）：当镜像以填充字节开头时，esptool 5.4.0 的 `write_flash` 可以跳过芯片检查。切勿依据 USB 桥接 ID 选择固件。[桌面构建](gui.md) 涵盖打包全部四个镜像。

### 蓝牙

使用 `POKELDN_BLE=1` 的构建还会通过蓝牙低功耗承载主机链路，供无法打开 USB 串口设备的 iOS 应用使用；此时开发板只需要 USB 供电。

    POKELDN_BLE=1 idf.py -B ../../scratchpad/esp/build-ble \
        -D SDKCONFIG=../../scratchpad/esp/build-ble/sdkconfig \
        -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.ble" build

该板只广播自己的名称 `POKELDN-RADIO`；iOS 应用扫描时不使用服务过滤器。服务 UUID 为 `7a1e0101-5d2c-4c3e-9f4b-504f4b454c44`：主机将 COBS 流写入 `...0102`（无响应写入），开发板在 `...0103` 上通知。当中央设备订阅 `...0103` 时，线上流量走该通道，USB 线保持静默。分帧、CRC 和 CREDIT 不变。HELLO 文本以 `link=ble` 结尾，Board 页面将其显示为蓝牙无线固件。`POKELDN_RADIO=esp32:ble`（或 `esp32:ble:NAME`）可从任何启动器打开（`pokeldn/ldn/esp32_ble.py`、bleak）。

BLE 构建使用仅 BLE 控制器、10 个静态 Wi-Fi RX 缓冲区和一个 10 KB 接收缓冲区，并释放经典蓝牙内存：双模控制器留下的空闲堆低于线上所需的 64 KB 下限。通过 BLE 时，开发板不发送 TX_DONE，并将排队帧合并到一条通知中。它请求 15 ms 间隔（中央设备订阅后再次请求；STATUS 中为 `ble_itvl_us`）、2M PHY、247 字节 MTU 和数据长度扩展；在 30 ms 间隔下火红房间会变得非常慢。

经典 ESP32（蓝牙 4.2，无 2M PHY）基准速度为 28.1 KB/s，可以完成火红主机端交换，但对火红加入方（2318-0013）太慢。XIAO ESP32C6 基准速度为 33.6 KB/s，可以完成火红加入方交换。所有无线构建都采用 ESP-IDF 的单应用大分区表（1500 KB 工厂应用位于 0x10000；nvs 位于 0x9000，phy_init 位于 0xf000，与之前一致）；C6 BLE 镜像（0xfd000 字节）还剩 488 KB。

在 macOS 上，如果进程所属应用没有蓝牙授权，bleak 会中止（SIGABRT）；用 `open -n -a Terminal FILE.command` 启动的脚本运行在 Terminal 的授权下。

### USB 主机链路

S3、C3 和 C6 通过 USB Serial/JTAG 使用相同的 COBS、CRC 和 CREDIT 协议，具有 16 KB 环形缓冲区。写入方在 `usb_serial_jtag_write_bytes` 被拒绝时每 20 ms 重试一次，500 ms 后计为一条丢弃消息。接收中断在 RX 环已满时会丢弃一个 64 字节包，且不计数（`usb_serial_jtag.c:144`）；CREDIT 可防止环被填满。这条路径上 UART 计数器保持为零，`POKELDN_ESP32_BAUD` 只改变经典 ESP32 的速率。在 USB 目标上，读取方以优先级 21 运行，高于写入方（20）：若低于写入方，全速率流下写入方会使读取方饿死。

主机设置 1 秒写入超时；写入失败或写入过短会将会话终止为开发板丢失。HELLO 之后，若 1 秒内没有有效帧，会排队一个 STATUS 探测；静默 3 秒会以 USB 错误结束会话，提示用户重新插拔开发板。

在没有控制台的情况下进行两小时主机到开发板浸泡测试（一个波特率值；原生 USB 会忽略它）：

```sh
./.venv/bin/python tools/ldn/esp32_bench.py --port COM5 --bauds 921600 \
    --soak 7200 --size 1400 --rate 460000
```

它每 5 秒打印帧、字节、credit 和 STATUS，出现 USB 故障或帧计数不匹配时以非零码退出。它既不模拟主机的确认，也不模拟其 Wi-Fi 负载。

## 运行

`POKELDN_RADIO=esp32:<port>` 会把所有启动器的 `ldn` 调用放到开发板上。`esp32:auto` 使用唯一存在的 USB 串口，若存在多个则拒绝选择，因为打开某个端口可能复位其开发板。每个进程打开端口一次，DTR 和 RTS 均释放；macOS 上的 CP2102 开发板无论如何都会在打开时复位。不复位的开发板会保持之前的 `BAUD`，因此主机会依次尝试 115200、`POKELDN_ESP32_BAUD`、921600 和 1500000 的 HELLO，然后再切换到请求的速率。在 Windows 上，COM 端口以独占方式打开（`PermissionError(13, 'Access is denied.')`），因此启动器会在重试前关闭无响应开发板的端口；运行中拔掉开发板会使会话以 `[esp32] The board disconnected from USB` 结束。使用 CP2102 时，仅断言 RTS 会保持 EN 为低电平，开发板保持静默。处于 ROM 下载模式的开发板永远不会应答 HELLO。

在开发板上，启动器跳过所有 nl80211 步骤（`--phy auto` 解析为 `esp32`），无需 root，也不注入信标；加入方的 `--mac` 会成为开发板站点地址。无法连接在 5 GHz 上主持的主机。

`POKELDN_ESP32_TRACE=FILE` 会追加每条串口消息，每行一条：Unix 时间、`>`（主机）或 `<`（开发板）、类型和十六进制载荷。

`tools/ldn/esp32_first_contact.py` 检查新开发板（`--flash` 写入构建，然后执行 HELLO、STATUS、按信道统计 LDN 动作帧的空闲扫描，加 `--keys` 时执行解密扫描）；`tools/ldn/esp32_sniff.py` 用第二块开发板作为嗅探器；`tests/test_esp32.py` 在两个模拟开发板（`pokeldn.ldn.esp32_sim`）上运行 LDN 主机和站点。CH9102 或 CH343 桥接器会枚举为 CDC ACM（`/dev/ttyACM0`、`/dev/cu.usbmodem*`）。

### 无法解码 OFDM 的开发板

主机的通告是 HT MCS 3（[发现](ldn.md#discovery)），因此无法解调 OFDM 的开发板听不到任何通告：`esp32_first_contact.py` 在每个信道上统计到 0 个 LDN 动作帧，而关联和 ping 在 DSSS 下仍可工作。在繁忙接入点旁运行 `tools/ldn/esp32_census.py` 可以分辨：正常开发板会列出 `OFDM` 和 `HT` 良好帧，而听障开发板只列出 `DSSS`，OFDM 帧在 `rx_state` 65 处失败。一块通用 ESP32-WROOM-32 DevKit（ESP32-D0WD-V3 rev 3.1，CP2102）是听障的；使用相同芯片的 WROOM-32E 开发板正常（[issue 1](https://github.com/Decryptu/pokeldn/issues/1)）。

## 各板子的交换

ELEGOO 板（ESP32-D0WD-V3 rev 3.1、CP2102、921600 baud）以站点和接入点身份在每款游戏中与零售 Switch 2 主机交换，并发送《火红》和《剑》的神秘礼物。XIAO ESP32C3、ESP32C6（陶瓷天线）和 ESP32S3 都能以两种角色完成《火红》交换，并能完成《剑》主机交换，C6 还能完成《朱》主机交换；Windows 上的 ESP32-S3 完成了一次《火红》加入方交换（[PR 2](https://github.com/Decryptu/pokeldn/pull/2)）。[Android 应用](../examples/android/README.md)一旦其 Python 线程被固定到一个性能核，就会通过 XIAO ESP32C6 以每秒 51.1 个父槽位的速率主持《火红》交换。

加入板子接入点的《火红》主机接受其零长度隐藏 SSID、速率顺序、能力值 `0x0431` 和 WMM 元素，并发送一个关联请求：监听间隔 10、SSID 为 32 个十六进制字符、速率 `02 04 0b 16 0c 12 18 24` 和 `30 48 60 6c`、功率能力 `00 14`、RSN 能力 `0x0000`、一个 WMM 信息元素、厂商元素 `00 22 aa 10 01 02`。它的首批广播需要固件转发（[站点的广播](ldn.md#a-stations-broadcasts)）。

### 加入

`STA_JOIN` 进行一次关联尝试：在信道和 BSSID 上进行快速扫描，然后进行开放认证和关联；`LINK` 在 0.23 到 0.34 秒后连通。零售《剑》的网络可能在其通告仍可被听到时使一次尝试失败（`LINK` 断开，原因 `0xc9` 或 `0x2`），而新的尝试随后会关联，因此主机会最多发送 `STA_JOIN` 三次（`pokeldn.ldn.esp32_wlan.JOIN_ATTEMPTS`）。一次尝试为何失败尚不清楚。

## 未解决的问题

- softAP 会协商 WMM，而 Switch 主机不会；无论是否协商 WMM，交换都能完成（`POKELDN_ESP32_AP_FLAGS=2`、`AP_FLAG_NO_QOS` 会清除站点的 QoS 标志）。
- 接入点接收路径中究竟是什么导致站点的 OFDM 首个副本被遗漏尚不清楚（[两块板子上的接收遗漏](#receive-misses-on-two-boards)）。
- ESP32-WROOM-32E 模块是否比 ELEGOO 板上的无品牌模块漏掉更少的帧，尚未测量。有用户报告称较老的 ESP32-WROOM-32 无法可靠交换；一块 WROOM-32 DevKit 没有解码出任何 OFDM（[一块不解码 OFDM 的板子](#a-board-that-decodes-no-ofdm)）。
- 加入板子接入点的《朱》主机可以确认通告，但不发送端口 2 加入（[朱／紫](sv.md#unresolved)）。

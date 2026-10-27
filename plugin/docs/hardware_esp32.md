---
title: ESP32 radio
parent: Hardware and setup
nav_order: 1
---

# ESP32 无线电

通过 USB 串口连接的 ESP32 板子作为无线电。它运行 `firmware/esp32/`，承载 LDN 的厂商动作帧和以太网帧；广告加密、LDN 认证、IP 和 Pia 保持在主机上，仅在 [便携信标](#portable-beacon) 中除外。`pokeldn.ldn.esp32_wlan` 为 LDN 库提供一个基于板子的工厂，因此 `ldn.scan`、`ldn.connect` 和 `ldn.create_network` 无需修改即可运行，主机无需 Wi-Fi 驱动。

## 支持的板子

| 芯片 | 主机连接 | 合并镜像 |
|---|---|---|
| 经典 ESP32（ESP32-D0WD，WROOM-32E） | 通过 USB 串口桥接的 UART0 | `pokeldn-radio.bin` |
| ESP32-S3 | 原生 USB 串口/JTAG | `pokeldn-radio-s3.bin` |
| ESP32-C3 | 原生 USB 串口/JTAG | `pokeldn-radio-c3.bin` |
| ESP32-C6 | 原生 USB 串口/JTAG | `pokeldn-radio-c6.bin` |
| 经典 ESP32，ESP32-C6 | 蓝牙 LE（iOS 应用），以及如上 USB | `pokeldn-radio-ble.bin`，`pokeldn-radio-ble-c6.bin` |

所有目标均使用 2.4 GHz 频段；ESP32-S2 不受支持。具有独立 UART 和原生 USB 接口的 S3、C3 或 C6 板子必须使用原生接口（S3 GPIO19/20，C3 GPIO18/19）；通过 UART 接口时固件不会响应。当通过 USB 串口桥接没有固件响应时，桌面应用会从 ROM 引导加载器读取芯片信息（esptool `detect_chip`），并将 S3、C3 或 C6 识别为插入了错误的接口。`303a:1001` 被多个芯片共享；刷写时通过 esptool 检测芯片。

| 板子 | 天线 | BOOT | 用户 LED | CPU，任务核心 | 空闲可用堆 | BENCH 通过原生 USB，macOS |
|---|---|---|---|---|---|---|
| XIAO ESP32C3 rev 0.4 | 外置天线，必需 | GPIO9 | 无（仅充电指示） | 160 MHz，核心 0 | 152656 | 880.1 KB/s |
| XIAO ESP32C6 rev 0.2（C6FH4，4 MB） | 陶瓷，由固件选择 | GPIO9 | 黄色，GPIO15，低电平亮 | 160 MHz，核心 0 | 255196 | 824.6 KB/s |
| XIAO ESP32S3 rev 0.2（8 MB flash，8 MB PSRAM） | 外置天线，必需 | GPIO0 | 黄色，GPIO21，低电平亮 | 240 MHz，核心 1 | 212416 | 883 KB/s |

BENCH 不会丢失任何性能；主机的波特率设置不会改变 USB 速度。更大的 S3 板子（N8R2，N16R8）具有板载天线。板子指南：[XIAO ESP32C3](https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/)、[XIAO ESP32C6](https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/)。

XIAO ESP32C6 在 GPIO3 低电平时供电 RF 开关；GPIO14 低电平选择陶瓷天线。C6 固件在 Wi-Fi 启动前将这两个引脚设为低电平；在 ESP32-C6-DevKitC-1 上这些引脚仅到达引脚排针，因此一张镜像适用于所有 C6 板子。C6 站点被限制为 11b/g/n。其接收报头中没有 `sig_mode`、`mcs` 或 `cwb`：固件从 `cur_bb_format` 派生 `sig_mode`，从 `he_siga1` 派生 HT MCS，其速率字节是 OFDM 帧的 L-SIG 速率码。

各板子完成的交易记录见 [按板子统计的交易](#trades-by-board)。

### 重置后的 USB 连接（C6，S3）

打开端口会重置 C6 或 S3。使用 ESP-IDF 默认的 `CONFIG_ESP_SYSTEM_BBPLL_RECALIB=y`，启动时会停止时钟 USB 串口/JTAG 的 BBPLL（`recalib_bbpll()`，`esp_system/port/soc/esp32c6/clk.c`），连接可能会保持乱码状态直到拔掉电源（SOF 帧号冻结，`USB_SERIAL_JTAG_INT_RAW` 显示 `0000b5b2` 对比健康状态下的 `0000b50a`）。C6 和 S3 构建将其设置为 `n`（使用 v5.2+ 引导加载器时允许；每个合并镜像都自带）：900/900 次 C6 打开和 300/300 次 S3 打开均得到响应。C3 没有此选项且无故障。

C6 和 S3 构建包含一个 USB 监视器（`usbwatch.c`）：如果 SOF 帧号停滞 2 秒，则重启芯片，下一个 HELLO 将 USB 和时钟寄存器作为 LOG 行输出。它在第一个 SOF 帧或第一个从电缆读取的主机字节时 armed，且当蓝牙主机已连接时绝不会重启：插在充电器上的板子看不到 SOF 帧，并且在固件 1.7.0 之前，蓝牙主机的字节会将其 armed，因此在 iPhone 应用下 C6 在充电器上每 2 到 3 秒重启一次。使用 `POKELDN_USB_BEACON=1` 构建时，任一镜像还会每秒将这些寄存器作为厂商动作帧广播到 `03:55:53:42:57:00`（布局见 `usbwatch.c`），`esp32_sniff.py --mac 03:55:53:42:57:00` 会在 USB 失效时保持接收。

## 角色

| 角色 | 板子的功能 |
|---|---|
| idle | 在一个信道上处于混杂模式；所有带有 Nintendo LDN 前缀 `7f 00 22 aa` 的动作帧转发给主机 |
| station | 使用主机派生的 CCMP 密钥通过 BSSID 加入控制台的网络 |
| access point | 主机 BSSID 上的隐藏 SSID WPA2 网络，使用相同密钥 |

控制台的网络没有 4 次握手：双方从广告的服务器随机数派生 CCMP 密钥。固件替换了 ESP-IDF 私有 `struct wpa_funcs` 表中的四个条目（`esp_wifi_driver.h`）。布局是 v6.1 blob 的 ABI；固件拒绝使用其他版本构建。

| 条目 | 替换 |
|---|---|
| `wpa_sta_connect` | 在库存回调周围安装 Switch 站点的 RSN 元素（CCMP，PSK，能力 `0x000c`） |
| `wpa_sta_rx_eapol` | 丢弃 EAPOL；密钥通过 `esp_wifi_set_sta_key_internal` 传入，一旦看到关联响应，然后 `esp_wifi_auth_done_internal` 打开端口 |
| `wpa_ap_join` | 添加站点并发送关联响应（`esp_send_assoc_resp`），不发送 EAPOL-Key message 1（`AP_START` 标志位 0 保持库存加入）；主循环安装成对密钥（`esp_wifi_set_ap_key_internal(CCMP, mac, 0, key)`）并打开端口（`esp_wifi_wpa_ptk_init_done_internal(mac)`），hostapd 的 `PTKINITDONE` 顺序（`wpa_auth.c:2290-2332`）；组密钥在 `WIFI_EVENT_AP_START` 时以索引 1 加入 |

陷阱：永远不要等待 `WIFI_EVENT_AP_STACONNECTED` 来安装密钥。只有 `esp_wifi_wpa_ptk_init_done_internal` 会发布它，因此在没有 4 次握手的情况下它永远不会到来，控制台的第一帧加密帧将被丢弃。

## Access Point 的帧

softAP 的信标、探测响应和关联响应是在封闭的 `libnet80211.a` 中构建的（v6.1 `ieee80211_output.o` 偏移量），与 `vendor/LDN` 的 access point 发送的内容进行比较：

| 字段 | Switch 形式 | ESP32 softAP | 可设置 |
|---|---|---|---|
| 隐藏 SSID 元素 | 32 个零字节 | 长度为 0（`ieee80211_beacon_construct` 0xc4） | 否 |
| 支持速率 | `82 84 8B 96 0C 12 18 24` | `8B 96 82 84 0C 18 30 60` | 否；相同的十二种速率和基本位，9 和 18 在扩展中 |
| 扩展速率 | `30 48 60 6C` | `6C 12 24 48` | 否 |
| 能力，信标 | `0x0511` | `0x0431`（短前导常量，`ieee80211_getcapinfo` 0x7b） | 否 |
| HT 元素 | 无 | 存在于 11b/g/n | 已移除：固件设置 11b/g |
| RSN 能力 | `0x000c` | hostapd 自己的 | 可设置：`wpa_ap_get_wpa_ie` 返回 Switch 的元素 |
| WMM | 无 | 存在于 11g | 仅 11b-only 移除它 |

隐藏的 softAP 只响应定向探测。没有配置 SSID 的关联请求会被丢弃（0x9c6）。`esp_wifi_80211_tx` 拒绝关联响应（`ieee80211_raw_frame_sanity_check` 0xf9），并且 blob 自己的信标无法停止。

## 串口协议

一帧为 `COBS(type | payload | crc32-le(type | payload))` 后跟 `0x00`；CRC 为 CRC-32/ISO-HDLC（`zlib.crc32`）。经典 ESP32 启动波特率为 115200；`BAUD` 同时切换两端波特率，板子保持该速率直到复位。在 S3 上，`BAUD` 会被确认但不改变 USB 传输速率。任何在 `0x00` 之前的内容（包括 ROM 的启动文本）都将校验失败并被丢弃。

| type | 方向 | payload |
|---|---|---|
| `0x01` HELLO | host | 无；回复 CREDIT 0，然后 INFO。host 首先发送一个 `0x00` 以结束任何不完整的帧 |
| `0x02` BAUD | host | u32 波特率；在旧速率下回复 RESULT，然后在 UART 排空后切换（最多 3 秒）；`open_serial` 在新速率下重试第一个 HELLO |
| `0x03` CHANNEL | host | u8 信道；仅空闲 |
| `0x04` STA_JOIN | host | u8 信道，6 字节 BSSID，32 字节 SSID（LDN SSID 的十六进制文本），16 字节密钥，6 字节站点 MAC（0 表示随机）；可选：u8 固定数据速率（AP_START 位 3..5 表格），u8 最大 TX 功率（单位 0.25 dBm，`esp_wifi_set_max_tx_power`，范围 8 到 84，驱动会将其限制在 61），u8 标志位：1 每帧前发送 RTS，2 重试前不发送 RTS（`esp_wifi_internal_set_rts`） |
| `0x05` STOP | host | 无；回到空闲，密钥清除 |
| `0x06` AP_START | host | u8 信道，6 字节 BSSID，32 字节 SSID，16 字节密钥，u8 最大站点数，u8 标志位：1 使用库存关联和 4 次握手，2 站点不使用 QoS，4 不复制每个站点数据帧的 40 字节，位 3..5 固定数据速率，`0x40` 每 1000 TU 发送信标，`0x80` 不进入混杂接收；可选的第二个标志字节：1 关闭驱动的噪声地面检查，2 其间隔为 250，4 在每个 40 字节复制的头部接收时间，8 重试限制 7 和 4，`0x10` 对除其站点良好数据帧外的每帧进行 RX_CENSUS；之后可选的最大 TX 功率（单位 0.25 dBm） |
| `0x07` AP_KICK | host | 6 字节 MAC，u16 原因；去认证 |
| `0x08` ETH_TX | host | 一个以太网帧，由驱动使用站点密钥或群组密钥加密。驱动队列满时每 1 毫秒重试一次，最多 100 毫秒；发送到已离开站点的帧失败并返回 `0x3015`。站点的以太网源地址必须是 LINK 中的 MAC，否则帧永远不会被确认 |
| `0x09` RAW_TX | host | 一个无 FCS 的 802.11 帧（`esp_wifi_80211_tx`）；广告 |
| `0x0A` SNIFF | host | u8 信道，6 字节 MAC；与其相关的所有管理和数据帧，以及信道上的所有动作帧（LDN 广告将网络键入控制台移动到的网络），完整地作为 RX_SNIFF；MAC ff:ff:ff:ff:ff:ff 将信道上的所有帧作为 RX_CENSUS 发送 |
| `0x0B` STATUS | host | 无；回复 STATUS |
| `0x0C` BENCH | host | u32 字节数，u16 消息大小（8 到 1600）；RESULT，然后尽可能快发送 BENCH 消息 |
| `0x0D` LED | host | u8 模式，u8 峰值亮度，u16 周期毫秒（0：模式默认），u16 持续时间毫秒（0：直到下一个 LED）；RESULT |
| `0x0E` DISPLAY | host | 一个屏幕命令（参见 [The screen](#the-screen)）；RESULT `0x105` 表示无屏幕 |
| `0x0F` ALIVE | host | 无，无回复；使能 [the host watchdog](#the-host-watchdog)；仅发送到固件 1.4.0 及更高版本 |
| `0x10` BEACON | host | u8 操作：0 WRITE 将 u32 偏移量和字节写入暂存缓冲区，1 COMMIT u16 长度（检查并存储暂存的镜像），2 ERASE，3 START，4 QUERY（回复 BEACON）；其他操作回复 RESULT。固件 1.8.0 及更高版本（参见 [Portable beacon](#portable-beacon)） |
| `0x81` INFO | board | u8 协议版本（1），6 字节站点 MAC，6 字节 AP MAC，u8 芯片修订号，文本 |
| `0x82` RESULT | board | u8 命令，i32 `esp_err_t` |
| `0x83` LOG | board | 文本 |
| `0x84` RX_MGMT | board | u8 信道，i8 RSSI，一个无 FCS 的帧：一个 LDN 动作帧；在主机时，还包括一个管理帧到板子的 BSSID，一个数据帧到它的前 40 字节，以及一个站点的无 DS 广播帧 |
| `0x85` RX_ETH | board | 驱动解密的以太网帧 |
| `0x86` LINK | board | u8 是否连接，u16 原因，6 字节 MAC；原因 `0xFFFF` 表示 15 秒内无关联，`0xFFFE` 表示密钥被拒绝 |
| `0x87` STA_JOINED | board | 6 字节 MAC，u8 AID，i8 密钥安装结果，u8 端口已打开 |
| `0x88` STA_LEFT | board | 6 字节 MAC，u16 原因 |
| `0x89` STATUS | board | 文本计数器（见下文）；在主机时无需请求，每 2 秒发送一次，由主机每 5 秒轮询一次以写入跟踪 |
| `0x8A` BENCH | board | u32 序列号和负载字节数；最后一个携带序列号 `0xFFFFFFFF` 和板子花费的 u32 微秒数 |
| `0x8B` CREDIT | board | u32 自上一个 HELLO 之后 host 读取并处理的字节数，从分隔符后的字节开始计数；在 HELLO 时发送，每 1024 字节发送一次，线路空闲时和空闲期间每 100 毫秒发送一次，位于任何排队消息之前 |
| `0x8C` RX_SNIFF | board | u8 信道，i8 RSSI，u8 `sig_mode`（0 旧式，1 HT），u8 旧式速率码（`wifi_phy_rate_t`），u8 HT MCS，第 7 位表示 40 MHz，一个无 FCS 的帧；同时发送信道上的每个 10 字节 ACK |
| `0x8D` TX_DONE | board | 驱动发送一帧的 TX 完成，站点或接入点：u32 板子时间微秒，u32 自 ETH_TX 完成以来微秒（如果没有则为全 1），u8 被对等方无线电确认，u8 接口，u16 长度，帧的前 24 字节（其 802.11 头） |
| `0x8E` BUTTON | board | 一个 BOOT 按下，去抖动 30 毫秒：u32 板子时间微秒，u16 自启动以来按下次数；host 打印 `BOOT button, mark N`，跟踪记录它 |
| `0x8F` RX_CENSUS | board | 每接收到的帧，包括 FCS 失败和控制帧：u32 接收时间微秒，i8 RSSI，i8 噪声地面，u8 `rx_state`（0 表示良好），u8 数据包类型（0 管理，1 控制，2 数据，3 其他），u8 `sig_mode`，u8 速率码，u8 MCS，第 7 位表示 40 MHz，u16 `sig_len`（含 FCS），帧的前 16 字节 |
| `0x90` BEACON | board | u8 镜像已存储，u8 正在运行，u8 分片数，u16 镜像长度，u32 镜像 CRC-32（`zlib.crc32` 计算整个镜像） |

`rx_state` 98 表示双流 HT（MCS 8 到 15），单流 ESP32 永远不会解码；65 表示任何其他调制方式的损坏帧。

| STATUS 计数器 | 计数内容 |
|---|---|
| `tx_acked`, `tx_unacked` | 驱动的 TX 完成结果 |
| `tx_eth`, `tx_eth_failed`, `tx_eth_retried` | ETH_TX 发送、失败和发现驱动队列满的调用次数 |
| `tx_queued_max_us`, `_total_us`, `_n`, `_pending` | ETH_TX 到 TX 完成，匹配 TX_DONE |
| `wire_dropped`, `wire_rx_bad` | 板到 host 的消息丢弃；host 命令 COBS 或 CRC 校验失败 |
| `uart_fifo_ovf`, `uart_buffer_full`, `uart_overflow` | 128 字节硬件 FIFO 和 16 KB 环溢出，以及它们的总和 |
| `uart_frame_err`, `uart_events_full` | 帧格式、奇偶校验和中断事件；UART 事件队列满的 tick 数（计数器可能低估） |
| `read_max_us`, `write_max_us`, `handler_max_us`, `handler_max_type` | 最长 host-link 读取周期（含 20 毫秒超时），写入器等待，以及带其类型的命令 |
| `heap_min`, `queue_max`, `refused_heap`, `refused_queue` | 最小剩余堆，最深的发送队列，在堆底和满队列时拒绝的消息 |
| `tx_eth_max_us`, `tx_eth_total_us`, `tx_eth_slow` | `esp_wifi_internal_tx` 中的 ETH_TX，包括重试：最长时间、总和、超过 5 毫秒的计数 |

以太网类型 `0x88B7` 的帧是 LDN 认证；`esp32_wlan` 将它们转换为 LDN 库的 `CustomFrameEvent`。所有其他以太网帧都发送到 L2 端口，由 `POKELDN_L2=tap|userspace` 选择：

| 端口 | 位置 | 发射器的套接字 |
|---|---|---|
| `userspace_ip` 栈 | 默认，所有平台 | `userspace_ip.udp_socket` 和 `packet_socket` |
| 内核 TAP，命名为接口 | Linux，仅 `POKELDN_L2=tap` | 内核套接字，`SO_BINDTODEVICE` 和 `AF_PACKET` 不变 |
| `MemoryPort` | 测试 | 无 |

创建 TAP 需要 `CAP_NET_ADMIN`。

### The host watchdog

host 每秒发送一次 ALIVE（`esp32.ALIVE_EVERY`）到固件 1.4.0 及更高版本。第一个在 HELLO 之后的 ALIVE 使能看门狗；HELLO 关闭它，因此从不发送 ALIVE 的 host 永远不会被监视。已使能后，5 秒内（`HOST_SILENT_US`）未读取到 host 命令的非空闲板子将执行 STOP 的清理操作：接入点停止信标广播，其站点断开；然后它会丢弃所有发往 host 的消息，未被计数，直到 host 再次发送命令；否则每个排队的消息都会花费 500 毫秒的写入时间，一次 `wire_dropped` 和一次恒定的 `flash3` 点亮 LED。在 FireRed 交易房间中杀死 host 时，控制台显示 2318-0006，后续的 JOIN 搜索列出没有 host。

## 便携信标

从固件 1.8.0 开始，板子在 NVS 中存储一个 LDN 广告周期，并在无主机的情况下发送它。
如果上电后 3 秒内有图像存储但无主机命令，则启动该图像的接入点，回放最多四个屏幕命令，
并每隔 `interval_ms`（100）发送一次广告，在每个 `dwell_ms`（500）后切换到下一个分片。
HELLO、CHANNEL、SNIFF、STA_JOIN、STOP 和 AP_START 会结束它；被看门狗判断为已离开的主机
则让它继续运行。`pokeldn.ldn.portable` 从网络 `ldn.create_network` 将要创建的图像构建图像；
`bin/swsh_gift_host.py --save-to-board` 存储一张剑／盾神秘礼物（[剑／盾神秘礼物](swsh_gift.md)）。

板子以与主机相同的方式构建每一帧（`firmware/esp32/main/advert.c`，PSA SHA-256、AES-CTR
和 AES-GCM）：存储的头部、分片的负载，以及从每次启动时的随机值开始、每分片递增一次的 nonce，
就像 `set_application_data` 在主机上所做的那样。
`tests/test_esp32_beacon.py` 编译 `advert.c` 并逐字节比较其帧与 LDN 库的帧，
适用于协议 1 和 3。

| 偏移 | 大小 | 字段（小端） |
|---|---|---|
| 0 | 4 | `PKSA` |
| 4 | 1 | layout，1 |
| 5 | 1 | kind，1（一次广告周期） |
| 6 | 2 | 图像长度，含 CRC |
| 8 | 1 | channel |
| 9 | 6 | BSSID |
| 15 | 32 | SSID，如 AP_START 所取 |
| 47 | 16 | data key |
| 63 | 1 | max stations |
| 64 | 16 | advertise key |
| 80 | 40 | 广告头部：network id、version、format、u16 BE size、u32 BE nonce |
| 120 | 2 | `interval_ms`，20 至 1000 |
| 122 | 2 | `dwell_ms`，至少为 `interval_ms` |
| 124 | 1 | fragments，1 至 8 |
| 125 | 1 | screen commands，0 至 4 |
| 126 | 2 | zero |
| 128 | | 每分片 u16 长度及广告的明文；每屏幕命令 u16 长度及 DISPLAY payload |
| end | 4 | `zlib.crc32` 先于它的所有内容 |

图像保存为其单一网络派生的 advertise 和 data keys，绝不保存 `prod.keys`。
图像最大为 12288 字节。固件 1.9.1 上的 XIAO ESP32S3，在上电后独自运行，
将一张剑神秘礼物宝可梦发送给零售剑版。从固件 1.9.1 开始，
存储的图像在板子响应其第一条命令之前从 NVS 中读取；
1.9.0 在端口打开后立即收到 BEACON QUERY 时回答“none stored”。
一块插在电脑 USB 上但没有打开应用程序的板子，会像在充电器上一样启动信标。

### 主机图像

从固件 1.9.0 开始，kind 为 2 的图像让板子自己响应每个控制台的加入，
并播放 `bin/frlg_mg_host.py` 播放的会话，因此一台 FireRed 或 LeafGreen
可以从独立的板子收到一次 Mystery Gift。
`bin/frlg_mg_host.py --save-to-board`（应用程序的“Keep it on the board”）
存储一个；`pokeldn.frlg.gift.portable` 通过构建启动器将要运行的主机应用程序
并保留主机在控制台加入前所计算的内容来构建它。
Wonder Card、Wonder News、Stamp Rally 印章、访客训练家和 Mystery Event 脚本
适合 2 至 4 KB；缓冲脚本和存档备份或恢复则在计算机上读取其响应并被拒绝。

Kind 2 没有分片（字节 124 为 0），只有 AES-GCM 头部。在屏幕命令之后是记录到 CRC，
每个记录由 u8 标签、u16 长度和字节组成（`firmware/esp32/main/gift.h`）：

| 标签 | 记录 | 写入者 |
|---|---|---|
| 1 | LDN：广告明文直到主机的 48 字节站点条目，认证头部的 network id（小端），
  16 字节的 key 用于解密认证密钥，32 字节的 challenge key，u64 challenge、
  u64 device id、version、platform | `pokeldn.ldn.portable.ldn_record` |
| 2 | Pia：会话密钥 `AES(game key, SSID)`，u32 network id，主机的 IPv4 地址、
  player id 和 name | `portable.pia_record` |
| 16, 17 | 控制台的 LinkPlayer 块之前和之后的应用程序数据 | `pokeldn.frlg.gift.portable` |
| 18 | 主机的 200 字节 LinkPlayer 块和 RFU 父 id | |
| 19 | `MysteryGiftTiming` 的八个字段、flags（1 native nonces、
  2 join response first、4 trust Pia）、u32 protocol tick µs | |
| 20 | 游戏家族（0 FireRed/LeafGreen、1 Emerald）、期望的控制台（0 any） | |
| 21 | 编译为字节码的服务器脚本：每个 `SVR_LOAD_*` 都变成一个槽 | |
| 22 | payload：u8 ident、u16 size（0 为 1024 字节缓冲）、bytes；每个不同消息一条 | |
| 23 | 提供的卡带：game code（四个零代表任意）、card flag id、icon、stamp 字段、
  每槽一个 payload | |

认证密钥为 `AES-ECB-decrypt(K, SHA-256(client random)[:16])`，
其中 `K` 是源 `f1e7018419a84f711da714c2cf919c9c` 的 `KeyDerivation._derive_key`
第三步派生的密钥，适用于 LDN 协议 3。除最后一个外的每个屏幕命令在开始时播放；
最后一个是传递后的场景，在会话传递后播放，然后再次播放开始的屏幕命令。

引擎是纯 C，逐行移植一个 Python 模块，每层一个：

| 文件 | 移植自 |
|---|---|
| `gift_ldn.c` | `ldn.APNetwork` 的认证和 challenge 回复、站点坐下时的广告、
  `userspace_ip` 的 ARP 和 IPv4/UDP、`host_app.py` 的运行循环 |
| `gift_pia.c` | `crypto.PiaCrypto`、`reliable.parse_messages`、
  `pia_connect` 的 Net、Session 和 RTT 编解码器、`host_pia.HostPeerProtocol` |
| `gift_link.c` | `reliable.HostReliableSession`、`ni.py`、
  `rfu_leader.RFULeader`、`host_session.HostSession` |
| `gift_mg.c` | `host_mystery_gift.HostMysteryGiftEngine`、
  `block.BlockSender` 和 `RecvBlock`、`mg_link`、服务器脚本 |
| `gift_zstd.c` | zstd 1.5.6 的解码器（`vendor/zstd`） |

信标任务运行它：驱动的帧和关联通过队列传递给它，
它在返回的截止时间运行定时器，并每隔 `interval_ms` 重建广告，
每次变化时 nonce 递增一次。站点的广播（首先是其对主机的 ARP）
在组密钥下没有 DS 位，这些接入点会丢弃它们：
引擎从混杂回调中原封不动地接收它们并自己解密，
使用 LDN 库的 nonce 和 AAD 上的 8 字节 MIC 进行 AES-CCM，
无论是否有 QoS（[站点的广播](ldn.md#a-stations-broadcasts)）。
零售 ESP32-S3 在安装的组密钥下已经解密后交给它们，
Protected 位、CCMP 头部和 MIC 保留（FireRed ARP 为 76 字节）；
从固件 1.9.1 开始，紧跟在 CCMP 头部之后以 SNAP 头部开头的主体
被当作明文处理，就像主机的 `accept_decrypted_ccmp` 所做的那样。
固件 1.9.0 会丢弃它们，控制台在认证后出现通信错误并离开。
控制台压缩其数据报的大部分（在一次 Wonder Card 会话中为 1056/1363）；
解码器上下文为 38464 字节，带有 1 KB 字面缓冲。
主机压缩的数据报作为 zstd 帧的一个原始块发出。
引擎的状态约为 41 KB，从堆中在开始时分配，连同解码器一起。

板子一次只容纳一个控制台，并以状态 1 拒绝另一个控制台的认证。
游戏代码未被任何卡带记录命名的控制台，或其游戏数据被脚本拒绝的控制台，
将被断开连接，且在游戏数据请求之后不发送任何内容。
静默 60 秒的控制台，或在 RFU 关闭后仍然连接 30 秒的控制台，
将被断开连接。当控制台离开后，经过 2 秒的稳定期（在其确认关闭后），
板子在同一网络和密钥上为下一个控制台服务。

`tests/test_esp32_gift.py` 编译引擎和 zstd，并在模拟板子上运行，
使用 `bin/frlg_mg_client.py` 充当控制台的位置，它用 ARP 解析主机并在自己的
Session 类型 6 上打开 Reliable 流，就像零售 FireRed 所做的那样；
其广播由 LDN 库加密，没有 DS 位。Wonder Card、已持有的卡片、
被拒绝的替换、印章和 Wonder News 每个都以 `MysteryGiftServer` 发送给该控制台的消息结束，
逐字节匹配；第二个控制台在第一个之后被服务；
图像不提供的卡带被拒绝。固件 1.9.1 上的 XIAO ESP32S3，
上电后无主机，将一张 Wonder Card 发送给零售法语 FireRed，
并再次为持有它的控制台提供服务。

## 串口天花板

经典 ESP32 UART 在 921600 波特率下承载 92.16 KB/s 的板到主机通信；
Pia payload 是密文且不可压缩。托管板子还会发送每个站点数据帧的 48 字节 RX_MGMT 副本，
除非设置了 AP 标志 4（`POKELDN_ESP32_AP_FLAGS=4`）；
每个附近的 LDN 网络大约会增加十个广告每秒。

发出队列最多保存 384 条消息，低于 64 KB 可用堆时拒绝。
在控制台的速率下，堆底会在队列填满之前拒绝 RX_ETH。

### 波特率

`POKELDN_ESP32_BAUD` 设置 `open_serial` 切换到的速率，默认为 921600；
USB 桥设置限制。在 ELEGOO 板的 CP2102 上 macOS，1500000 承载 149.1 KB/s 无丢失，
2000000 和 3000000 从不响应 HELLO。
`tools/ldn/esp32_bench.py --port PORT --bauds LIST` 在每个速率下流式发送 BENCH。

### 主机到板的命令丢失与 CREDIT

在控制台的洪水下，板子可能会在处理程序之前丢失主机命令。
固件的对策，每种都与其缺失进行比较：

| 原因 | 固件 |
|---|---|
| 核心 0 上的 UART 中断与 Wi-Fi 任务 | 从 reader 任务安装驱动，核心 1 |
| 阻塞的 ETH_TX 让 16 KB 环和 128 字节 FIFO 溢出 | CREDIT 流控制 |
| FIFO 在 1500000 下 53 µs 从满到 120 字节 | 阈值 32（`uart_set_rx_full_threshold`），640 µs |
| `uart_read_bytes`（IDF 6.1 `uart.c:1738`）每次环形项等待超时 | 等待一个字节，然后取 `uart_get_buffered_data_len` |
| `uart_write_bytes` 在满 TX 环上忙循环，饿死 reader | 写入线程睡眠直到帧适合（`uart_get_tx_buffer_free_size`） |
| `UART_DATA` 事件填满承载溢出事件的 64 项队列 | reader 上方的任务每 tick 排空它；`uart_events_full` |

一旦板子发送了 CREDIT，主机的写入线程保持在 8 KB 写入且未报告（`esp32.FLOW_WINDOW`）；
启动器的三重循环只排队，ETH_TX 和 RAW_TX 超过 512 排队帧会被丢弃（`Radio.tx_dropped`）。
窗口关闭时 0.3 秒内重复次数不变意味着字节丢失，
主机重新打开窗口（`Radio.flow_resyncs`）。
切勿仅因静默而重新同步：忙碌的 reader 最多会拖延 0.7 秒，
此时重新同步会在 16 KB 环上放入 16 KB。
板子每 1024 字节发送一次 CREDIT（`wire.c` 中的 `CREDIT_STEP`），
因此主机将 CREDIT 抵消于写入的字节数加上线上的帧。
没有 CREDIT 的板子会被写入不受限制。
板子记录超过 50 ms 的命令（`slow command`）和超过 100 ms 的 reader 回合（`reader held`）。

HELLO 重启这两个计数，因此主机会保持它直到没有在途的数据，
并保持窗口关闭直到板子的 CREDIT 0（`tests/test_esp32.py::test_a_hello_mid_session_does_not_open_the_window`）。
`tools/ldn/esp32_cmd_loss.py TRACE` 核对跟踪：
写入的 ETH_TX 与 `tx_eth + tx_eth_failed` 进行对比，
自 HELLO 后写入的字节数与上一次 CREDIT 进行对比。

### 发送时序

ETH_TX 在驱动中花费约 0.1 ms，中位数等待约 1 ms 直到 TX 完成。
在洪水下，TX_DONE 最多会晚达主机 0.6 秒。陷阱：
嗅探板自己的线在突发时会阻塞，因此通过对等方的确认来衡量传递时间；
接入点洪水以 1 Mbit/s 广播，超过大约 90 帧每秒会填满空气。

## 保持与接收丢失

在 FireRed 交易中将板子作为接入点时，一个帧通常在约 1 毫秒内完成；偶尔，控制台会有 100 到 260 毫秒未确认保持，而其后的帧会在突发中完成，板子既听不到控制台的数据也听不到其 ACK。信道决定保持：在与繁忙接入点共享的信道上，大多数交易都保持；在信道 11 上则没有任何保持。`config/host.local.toml` 接受一个 `[host] channel`；控制台加入主机的信道为 1、6 或 11。240 MHz CPU 和固定速率（AP 标志位 3..5：1、11、6、12、24、36、54 Mbit/s 对应 1 到 7）并不能消除保持。`tools/ldn/esp32_hold.py CAPTURE TRACE` 将每次等待划分为多个阶段，`tools/ldn/esp32_hold_air.py` 列出嗅探器看到的内容，`tools/ldn/esp32_rx_copies.py` 将控制台的重试与板子的接收丢失匹配起来。

### 两个板子上的接收丢失

作为接入点时，板子会错失站点 1% 到 22% 的 OFDM 首次副本；DSSS 在 1 Mbit/s 时几乎从不丢失。`tools/ldn/esp32_pair_bench.py AP STA --flood 0 --burst N --send R` 统计这些丢失。丢失集中在板子自身传输之后的帧，例如其 6 Mbit/s CTS 之后 60 µs 的数据。在较安静的信道上（3 到 9 上为 0.8% 到 2.3%），每帧站点传输前都有 RTS（STA_JOIN 标志 1），以及满功率站点时丢失较少。

信标间隔、混杂接收、噪声楼检查、接收缓冲区、CPU 时钟、IRAM 优化、接入点功率或 ESP-IDF v5.5.5 与 v6.1 之间均无变化。大多数丢失在接入点上没有任何痕迹，甚至没有 FCS 失败。

站点在 RTS 后发送每个重试（`lmacConfMib` +42，阈值在 +22；`esp_wifi_internal_get_rts`/`_set_rts`）。`lmacRetryTxFrame` 重发最多达 `lmacConfMib` 限制（短 +21，长 +20，默认 32；`esp_wifi_internal_set_retry_counter`）。ACK 和 CTS 速率表位于 `0x3ff73400`..`0x3ff7341c`。

## 用户态协议栈

`pokeldn.ldn.userspace_ip` 在主机进程内部承载 IPv4、UDP 和 ARP。栈注册在接口名称下（加入者为 `ldnclient`，接入点为 `ldn-tap`）；`userspace_ip.lookup(name)` 对内核接口返回 None，正是每个启动器选择路径的方式。地址和邻居来自 LDN 库的 `add_address` 和 `add_neighbor`，以及接收到的帧；没有邻居的单播目的地会发送 ARP 请求并丢弃数据报；`.255` 发送到广播。超过 1472 字节的数据报会被分片，分片在 5 秒内重新组装。`udp_socket(port)` 和 `packet_socket()` 分别充当绑定的 UDP 套接字和 `AF_PACKET` 套接字的替代品，每个都由一个套接字对支持，每个排队数据报占一个字节，因此 `select` 和 `trio.lowlevel.wait_readable` 在每个平台上都能正常工作。

陷阱：板子的帧通过启动器自身的 trio 循环中的 trio 任务到达栈。永远不要在该循环中阻塞 `select`；应在 `trio.move_on_after` 下使用 `trio.lowlevel.wait_readable` 等待。

## 板子的 LED 和按钮

LED 在经典 ESP32 为 GPIO2，在 S3 为 GPIO21（反相），在 C6 为 GPIO15（反相）；C3 固件不触动 LED 引脚。BOOT 在经典 ESP32 和 S3 为 GPIO0，在 C3 和 C6 为 GPIO9；每次按下都会发送 BUTTON（`0x8E`）、闪烁 LED 并唤醒屏幕。在 ELEGOO ESP-32 Type-C 板（CP2102、ESP32-D0WD-V3、非品牌 PCB 天线模块）上，红色 LED 是电源轨，蓝色的是 GPIO2。GPIO2 和 GPIO0 是strapping 引脚；固件仅在启动后才驱动 GPIO2。

LED 使用 LEDC PWM（13 位，5 kHz）每 10 毫秒运行一次，伽马 2.2，150 毫秒交叉淡化。

| pattern | id | default period | shape |
|---|---|---|---|
| auto | 0 | | 模式的外观，如下 |
| off, on | 1, 2 | | |
| breathe | 3 | 3000 ms | 余弦曲线 |
| blink | 4 | 1000 ms | 在周期的一半时间内亮起 |
| flash3 | 5 | 1000 ms | 在周期的前 60% 中闪烁三次 |
| ramp-up, ramp-down, pulse | 6, 7, 8 | 1000, 1000, 1200 ms | 一次性 |

自动外观：启动时一次脉冲，4 秒的低亮度 breathe 空闲，加入时 250 毫秒的 blink，托管无站点时 1.5 秒的更亮 breathe，链接时变暗，嗅探时熄灭。

每个帧都会使 LED 在顶部闪烁。失败的加入、拒绝的密钥、丢失的板到主机消息或丢失的主机命令会播放 1.5 秒的 flash3。完成的交易或神秘礼物会渐亮到最大（`pokeldn.ldn.show_done`）。`tools/ldn/esp32_led.py --port PORT PATTERN` 设置外观；`--demo` 显示每个。

## 屏幕

SSD1306 128x64 OLED 可选，I2C 接口（SSD1315 和 SSD1309 模块也可用）。固件先探测 0x3C，然后 0x3D，有屏幕时以 400 kHz 频率每 50 毫秒绘制一帧。

| target | SDA | SCL | board pins |
|---|---|---|---|
| ESP32 | GPIO21 | GPIO22 | DevKit V1 D21, D22 |
| ESP32-S3 | GPIO8 | GPIO9 | |
| ESP32-C3 | GPIO6 | GPIO7 | XIAO D4, D5 |
| ESP32-C3 | GPIO5 | GPIO6 | 0.42 英寸 OLED 板自带的 72x40 屏幕，第二个探测 |
| ESP32-C6 | GPIO22 | GPIO23 | XIAO D4, D5 |

常见的四针模块自带电压调节器和上拉电阻；其地址电阻选择 0x3C（丝印 0x78）或 0x3D（0x7A）。固件设置段重映射（`A1`）、反转 COM 扫描（`C8`）和替代 COM 引脚（`DA 12`）。ESP32-C3 0.42 英寸 OLED 板的 72x40 面板显示帧的列 30..101 和行 24..63；在这些引脚上的屏幕会显示紧凑场景（一行最多 12 个字符，半尺寸精灵），由 `tools/ldn/screen_preview.py --panel 72x40` 离线渲染。

没有主机命令时，屏幕显示收音机状态：空闲、加入中或托管中、已链接，并统计每个方向的帧数。在收音机活动或动画播放时，以及最后一次 DISPLAY、HELLO 或 BOOT 按下后 60 秒内，屏幕处于最大亮度；之后调暗到对比度 1，预充 `22`（`81 01 D9 22`），600 秒后关闭（`AE`）。较低的预充会导致闪烁。空闲场景每 60 秒移动 2 像素以防止烧屏。`tests/test_esp32_screen.py` 保存这些计时。

DISPLAY（`0x0E`）携带一个操作：

| op | layout |
|---|---|
| `0` SHOW | u8 show, u16 hold s (0: 直到下一次 show), title, NUL, line, NUL; 每个文本最多 21 个 ASCII 字符 |
| `1` SPRITE | u8 slot (0 ours, 1 theirs, 2 gift), u8 width <= 64, u8 height <= 64, 行数据 `(width + 7) / 8` 字节，MSB 在前；宽度 0 清空插槽 |
| `2` LOBBY | u8 stars (0..7, 0: none), u8 joined, u8 seats (1..3, at least joined), title, NUL, name, NUL, Link Code, NUL; 开始大厅显示 |
| `3` JOINED | u8 joined, at most the lobby's seats; refused without a lobby show |

| show | id | drawn |
|---|---|---|
| auto | 0 | 收音机的状态 |
| trade | 1 | 插槽 0，显示 "offering" 和 line |
| traded | 2 | 插槽 0 离开其球（2.1 秒），数据包交叉直到保持，一个球到达并打开（1.6 秒），然后插槽 1 "received" 10 秒 |
| gift | 3 |  holding 插槽 2 的 Wonder Card |
| gifted | 4 | 卡片离开，然后 "delivered!" |
| arrived | 5 | 等待的 traded 或 gifted show 带其球进来 |
| lobby | LOBBY | 插槽 0, title, name, stars, "joined/seats" 和 code |

show 等待 playing traded 或 gifted show；show 在收音机返回空闲时结束。

`pokeldn.app.screen` 是启动器端：`offer`、`received`、`arrived`、`gift`、`delivered`、`lobby` 和 `joined` 立即返回并按顺序在一个线程上运行。托管的团体战会显示大厅。每个启动器在交易的最后一步调用 `received`，保持时间为以下时间减去 2.5 秒，因此球与控制台同时打开：

| title | from | received Pokémon on the console | first message after the animation |
|---|---|---|---|
| FireRed/LeafGreen | START_TRADE | 22.7 s | READY_FINISH_TRADE ([FireRed link](frlg_link.md)) |
| Let's Go | step `0e` | 15.3 s | type 4 payload ([Let's Go session](lgpe_session.md#the-trade-animation)) |
| Sword/Shield | the last syncCommand 40 | 15.0 s | none ([Sword trade](swsh_trade.md#the-trade-animation)) |
| BD/SP | `tradeState` 5 | 18.6 s | none ([BDSP trade](bdsp_trade.md#the-completed-trade)) |
| Legends Arceus | `01 0e` | 28.5 s | box message `00 02` ([Legends Arceus](pla.md#the-completed-trade)) |
| Scarlet/Violet | `8001010e` | 19.8 s | none ([Scarlet and Violet](sv.md#the-trade)) |
| Legends Z-A | the fourth step | 26.2 s | the next `01 01` preview ([Legends Z-A](za.md#a-trade-with-a-retail-console)) |

时间是手动标记的（最多晚 2 秒）。启动器在动画后的消息调用 `arrived`。精灵是 PokeAPI 的 FireRed/LeafGreen 版本，种族编号在 386 之前使用 FireRed/LeafGreen 版本，之后使用默认版本，裁剪、缩放到最多 64（卡片上为 40）并阈值为单色，保留内部线条为暗色。`tools/ldn/esp32_screen.py --port PORT` 在板子上播放交易和礼物；`tools/ldn/screen_preview.py OUT.gif` 离线渲染脚本会话。

### E32R40T 板

E32R40T（作为 4.0 英寸 ESP32-32E 显示器出售）是一块经典 ESP32，配备 480x320 ST7796S 面板通过 SPI。其固件是独立构建的，`POKELDN_DISPLAY=E32R40T` 在 `idf.py` 的环境中（默认为 `OLED`）；发布镜像为 OLED 构建。

| signal | GPIO |
|---|---|
| CS, DC, SCK, MOSI | 15, 2, 14, 13 |
| backlight, lit while high | 27 |
| RGB LED, lit while low: red, green, blue | 22, 16, 17 |

面板以 3 倍显示 128x64 帧（384x192），黑白反色，SPI 频率 40 MHz。GPIO2 是面板的 DC，因此板子的 LED 是 GPIO17 上的蓝色。背光在 OLED 关闭时也会关闭。

## 构建与烧录

固件版本（`firmware/esp32/version.txt`，格式为 `major.minor.patch`，所有目标共享）会在 INFO 中报告为 `version=...`；未版本化的构建显示为 `version unknown`，只要其串口协议匹配即可正常工作。协议号是独立的，仅在通信协议变更时修改。

ESP-IDF v6.1（标签 `v6.1`，提交 `fff9895c82d744c7237be8847347bdd1b07c6643`）构建所有四个目标。使用 `install.sh esp32,esp32s3,esp32c3,esp32c6` 安装其工具，然后激活 IDF 环境。

    cd firmware/esp32
    idf.py set-target esp32   # esp32s3, esp32c3 或 esp32c6 对应不同芯片
    idf.py build
    idf.py -p <port> flash

控制台输出关闭；在经典 ESP32 上，固件自行分配 UART0 的 GPIO1 和 GPIO3（`uart_set_pin`）。桌面应用使用 esptool 检测芯片，并在写入前验证合并镜像的 bootloader 在芯片的 flash 偏移处（ESP32 为 `0x1000`，其他为 `0x0`）：esptool 5.4.0 的 `write_flash` 在镜像以填充字节开头时可能会跳过其芯片检查。切勿从 USB 桥接器 ID 选择固件。
esptool 根据端口的 USB ID 选择复位方式，但 esp-pylib 1.1.5 拒绝为 URL 端口（如 Android 的 `android://board`）查找 ID；没有 ID 时，它会向 ESP32-S3、C3 或 C6 发送经典的 DTR/RTS 复位，芯片永远无法进入其 ROM 加载器，日志显示 `Failed to get VID/PID`。Android 应用从板子自己的 USB ID 响应查找（`pokeldn/app/android.py`）。一旦 ID 已知，Linux 或 Android 上的 CP210x 板子通过 `ioctl` 操作端口的 `fileno()` 同时写入 DTR 和 RTS 信号进行复位；Android 端口没有文件描述符，改为通过一次 CDC `SET_CONTROL_LINE_STATE` 发送两条信号线。
[桌面构建](gui.md) 涵盖了打包所有四个镜像。

### 蓝牙

带有 `POKELDN_BLE=1` 的构建还通过蓝牙低功耗携带主机链接，适用于无法打开 USB 串口设备的 iOS 应用；此时板子仅需 USB 供电。

    POKELDN_BLE=1 idf.py -B ../../scratchpad/esp/build-ble \
        -D SDKCONFIG=../../scratchpad/esp/build-ble/sdkconfig \
        -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.ble" build

板子仅广告其名称 `POKELDN-RADIO`；iOS 应用以无服务过滤扫描。服务 UUID 为 `7a1e0101-5d2c-4c3e-9f4b-504f4b454c44`：主机将 COBS 流写入 `...0102`（无响应写入），板子则在 `...0103` 通知。当一个中心设备订阅 `...0103` 时，通信走该路径，电缆保持静默。帧格式、CRC 和 CREDIT 保持不变。HELLO 文本以 `link=ble` 结尾，Board 页面显示为蓝牙无线固件。
`POKELDN_RADIO=esp32:ble`（或 `esp32:ble:NAME`）从任何启动器打开它（`pokeldn/ldn/esp32_ble.py`，bleak）。

BLE 构建采用 BLE 专用控制器、10 个静态 Wi-Fi RX 缓冲区和 10 KB 接收缓冲区，并释放经典蓝牙内存：双模控制器使可用堆内存低于通信协议的 64 KB 楼层。通过 BLE，板子不发送 TX_DONE，并将排队的帧合并到一次通知中。它请求 15 ms 间隔（同样在中心订阅后；`ble_itvl_us` 在 STATUS 中）、2M PHY、247 字节 MTU 和数据长度扩展；在 30 ms 间隔下，FireRed 房间爬行。

经典 ESP32（蓝牙 4.2，无 2M PHY）基准为 28.1 KB/s，能完成 FireRed 主机交易，但对于 FireRed 加入者交易（2318-0013）速度过慢。XIAO ESP32C6 基准为 33.6 KB/s，能完成 FireRed 加入者交易。每个无线构建都采用 ESP-IDF 的单应用大表（1500 KB 工厂应用位于 0x10000；nvs 位于 0x9000，phy_init 位于 0xf000，不变）；C6 BLE 镜像（0xfd000 字节）在其中留出 488 KB。

在 macOS 上，bleak 在负责应用没有蓝牙权限的进程中崩溃（SIGABRT）；通过 `open -n -a Terminal FILE.command` 启动的脚本则在 Terminal 的权限下运行。

### USB 主机链接

S3、C3 和 C6 使用相同的 COBS、CRC 和 CREDIT 协议，通过 USB Serial/JTAG 与 16 KB 环形缓冲区通信。写入器每 20 ms 重试一次被拒绝的 `usb_serial_jtag_write_bytes`，并在 500 ms 后计数丢弃的消息。接收中断在 RX 环满时丢弃一个 64 字节的数据包且不计数（`usb_serial_jtag.c:144`）；CREDIT 防止环形缓冲区溢满。在此路径上 UART 计数器保持为零，`POKELDN_ESP32_BAUD` 仅改变经典 ESP32 的速率。在 USB 目标上，读取器优先级为 21，高于写入器（20）：低于它，写入器会在满速数据流下饿死读取器。

主机设置 1 秒写入超时；一次失败或短写入会以板子丢失结束会话。在 HELLO 之后，1 秒内无有效帧会触发 STATUS 探测，3 秒静默会以 USB 错误结束会话，提示用户重新插入板子。

一次无控制台的主机到板子的长达两小时浸泡测试（一种波特率值；原生 USB 忽略它）：

```sh
./.venv/bin/python tools/ldn/esp32_bench.py --port COM5 --bauds 921600 \
    --soak 7200 --size 1400 --rate 460000
```

它每 5 秒打印帧、字节、信用和 STATUS，并在 USB 故障或帧计数不匹配时以非零状态退出。它无法复现控制台的确认机制或其 Wi-Fi 负载。

## 运行

`POKELDN_RADIO=esp32:<port>` 将每个启动器的 `ldn` 调用路由到板子。`esp32:auto` 选择唯一存在的 USB 串口端口，并拒绝在多个端口间选择（因为打开端口可能会重置板子）。每个进程只打开一次端口，释放 DTR 和 RTS 信号；macOS 上的 CP2102 板子在打开时会重置，无论如何。一个不会重置的板子会保留之前的 `BAUD`，因此主机会依次尝试 115200、`POKELDN_ESP32_BAUD`、921600 和 1500000 波特率后，再切换到请求的速率。
在 Windows 上，COM 端口独占打开（`PermissionError(13, 'Access is denied.')`），因此启动器会在重试前关闭静默板子的端口，中途拔掉板子会以 `[esp32] The board disconnected from USB` 结束。使用 CP2102，仅断言 RTS 会使 EN 保持低电平，板子保持静默。处于 ROM 下载模式的板子永远不会响应 HELLO。

在板子上，启动器跳过所有 nl80211 步骤（`--phy auto` 解析为 `esp32`），不需要 root 权限，也不注入信标；加入者的 `--mac` 成为板子站点的地址。托管在 5 GHz 的控制台无法被到达。

`POKELDN_ESP32_TRACE=FILE` 追加每条串口消息，一行一条：Unix 时间、`>`（主机）或 `<`（板子）、类型和十六进制负载。

`tools/ldn/esp32_first_contact.py` 检查新板子（`--flash` 写入构建，然后 HELLO、STATUS、一次空闲扫描统计每个信道的 LDN 动作帧，以及 `--keys` 的解密扫描）；`tools/ldn/esp32_sniff.py` 运行第二个板子作为嗅探器；`tests/test_esp32.py` 在两个模拟板子上运行 LDN 主机和站点（`pokeldn.ldn.esp32_sim`）。CH9102 或 CH343 桥接器枚举为 CDC ACM（`/dev/ttyACM0`，`/dev/cu.usbmodem*`）。

### 无法解调 OFDM 的板子

控制台的广告为 HT MCS 3（参见 [Discovery](ldn.md#discovery)），因此无法解调 OFDM 的板子听不到广告：`esp32_first_contact.py` 在每个信道上计数为 0 个 LDN 动作帧，而关联和 ping 仍可在 DSSS 下工作。`tools/ldn/esp32_census.py` 在繁忙的接入点旁边将其区分开：工作的板子列出 `OFDM` 和 `HT` 的良好帧，聪明的板子只列出 `DSSS`，OFDM 帧在 `rx_state` 65 处失败。一个通用 ESP32-WROOM-32 DevKit（ESP32-D0WD-V3 rev 3.1，CP2102）是聪明的；带有相同芯片的 WROOM-32E 板子则能正常工作（参见 [issue 1](https://github.com/Decryptu/pokeldn/issues/1)）。

## 按板子的交易

ELEGOO 板子（ESP32-D0WD-V3 rev 3.1，CP2102，921600 波特率）能与零售 Switch 2 主机在所有游戏中交易，无论是作为站点还是接入点，并能发送 FireRed 和 Sword 的神秘礼物。XIAO ESP32C3、ESP32C6（陶瓷天线）和 ESP32S3 能完成 FireRed 交易（两种角色）和 Sword 主机交易，C6 也能完成 Scarlet 主机交易；Windows 上的 ESP32-S3 能完成 FireRed 加入者交易（参见 [PR 2](https://github.com/Decryptu/pokeldn/pull/2)）。[Android 应用](../examples/android/README.md) 通过 XIAO ESP32C6 在 51.1 个父槽位托管 FireRed，前提是将其 Python 线程绑定到一个性能核心。

加入板子接入点的 FireRed 主机接受其零长度隐藏 SSID、速率顺序、能力字段 `0x0431` 和 WMM 元素，并发送一次关联请求：监听间隔 10，SSID 作为 32 个十六进制字符，速率 `02 04 0b 16 0c 12 18 24` 和 `30 48 60 6c`，功率能力 `00 14`，RSN 能力 `0x0000`，WMM 信息元素，厂商元素 `00 22 aa 10 01 02`。其首次广播需要固件的转发（参见 [A station's broadcasts](ldn.md#a-stations-broadcasts)）。

### 加入

`STA_JOIN` 进行一次关联尝试：快速扫描指定信道和 BSSID，然后进行开放认证和关联；`LINK` 在 0.23 到 0.34 秒后建立。零售 Sword 的网络可能会失败一次尝试（`LINK` 断开，原因 `0xc9` 或 `0x2`），同时其广告仍可被听到，之后新的尝试会重新关联，因此主机会发送最多三次 `STA_JOIN`（`pokeldn.ldn.esp32_wlan.JOIN_ATTEMPTS`）。一次尝试失败的原因尚不清楚。

## 未解决

- softAP 协商 WMM，而 Switch 主机不会；交易在有或没有 WMM 时均可完成（`POKELDN_ESP32_AP_FLAGS=2`，`AP_FLAG_NO_QOS`，清除站点的 QoS 标志）。
- 接入点接收路径中，什么原因导致错过站点的 OFDM 首拷贝尚不清楚（参见 [Receive misses on two boards](#receive-misses-on-two-boards)）。
- ESP32-WROOM-32E 模块是否比 ELEGOO 板的无品牌模块少丢失帧尚未测量。用户报告称较旧的 ESP32-WROOM-32 不可靠；一个 WROOM-32 DevKit 无法解调 OFDM（参见 [A board that decodes no OFDM](#a-board-that-decodes-no-ofdm)）。
- 加入板子接入点的 Scarlet 主机可以确认公告但发送无端口 2 的加入（参见 [Scarlet and Violet](sv.md#unresolved)）。

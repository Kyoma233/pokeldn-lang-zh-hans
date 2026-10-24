---
title: Controller board
parent: Hardware and setup
nav_order: 5
---

# 手柄板

手柄板是一块 ESP32-S3，Switch 将其作为 USB-C 端口上的有线控制器使用；或者是一块经典 ESP32，通过经典蓝牙与 Switch 配对为 Pro 手柄。上位机按下游戏机的按键并加载宏，由手柄板按自己的时钟播放。固件 `firmware/pad`，上位机侧 `pokeldn.pad`，应用页面 [控制器](gui.md#the-controller)，命令行 `tools/switch/pad.py`。

## 适用板子

| 芯片 | 控制器 | 原因 |
|---|---|---|
| ESP32-S3 | 有线，通过 USB | 它的 USB-OTG 模块可以作为任意 USB 设备 |
| classic ESP32 | 无线 Pro 手柄，经典蓝牙；上位机通过其 USB 转串口端口 | 本身没有 USB 设备；它具备经典蓝牙，这是 Pro 手柄的传输方式 |
| ESP32-C3、ESP32-C6 | 无 | USB Serial/JTAG 功能固定，且它们的蓝牙仅支持 LE |

## USB 侧

手柄板枚举为 HORI Pokken 控制器，`0f0d:0092`，一个 HID 接口，带有中断 IN 和中断 OUT 端点。Switch 将此 ID 接受为普通 HID 游戏手柄，无需 Pro 手柄握手；固件 23.0.1 的零售版 Switch Lite 无需更改任何设置即可在 HOME 菜单中使用它。

输入报告为 8 字节，在上位机准备好接收时每毫秒发送一次：

| 偏移 | 大小 | 字段 |
|---|---|---|
| 0 | 2 | 按键，小端序 |
| 2 | 1 | 方向键：0 为上，然后顺时针到 7 为左上；8 为居中 |
| 3 | 4 | LX、LY、RX、RY；128 为居中，0 为左或上 |
| 7 | 1 | 厂商字节；固件将其蓝牙状态放在此处 |

| 位 | 按键 | 位 | 按键 |
|---|---|---|---|
| 0x0001 | Y | 0x0100 | Minus |
| 0x0002 | B | 0x0200 | Plus |
| 0x0004 | A | 0x0400 | 左摇杆按下 |
| 0x0008 | X | 0x0800 | 右摇杆按下 |
| 0x0010 | L | 0x1000 | HOME |
| 0x0020 | R | 0x2000 | Capture |
| 0x0040 | ZL | | |
| 0x0080 | ZR | | |

厂商字节：1 表示已同步，2 表示广播中，3 表示已连接；当某步骤失败时为 `0x80 | step`。

## 接线

使用 USB-C 转 USB-C 线缆从手柄板连接到游戏机。游戏机作为电源和 USB 主机；手柄板从它取电。当上位机已配置设备时，XIAO ESP32S3 的 LED（GPIO21）会亮起。

Switch Lite 连接 Mac 的 USB-A 端口，并打开“通过 USB 连接复制到电脑”时，枚举为 `057e:201d`：一个 MTP 接口，只读的“相册”存储，十个只读操作（`0x1001`-`0x100a`）。

## 蓝牙侧

手柄板以 `POKELDN-PAD` 广播，提供一个服务 `7a1e0001-5d2c-4c3e-9f4b-504f4b454c44`：

| 特征 | 访问方式 | 内容 |
|---|---|---|
| `...0002` | 写入、无响应写入 | 8 字节输入报告，原样发送；播放宏时忽略 |
| `...0003` | 读取 | 状态，见下文 |
| `...0004` | 写入 | 命令，见下文 |

状态，小端序：已挂载 u8，报告写入计数 u32，播放中 u8，已完成循环数 u32，条目索引 u16，条目计数 u16，固件版本作为文本，然后是 NUL，复位原因 u8（`esp_reset_reason`），上次启动到达的阶段 u8，以及上电以来的启动次数 u16。1.0.0 之前的固件只发送前五个字节。

| 命令 | 正文 | 作用 |
|---|---|---|
| `0x10` load | count u16, loop start u16, loops u32 | 停止宏并为程序设定大小；loops 为 0 表示播放直到停止 |
| `0x11` data | first entry u16, then entries | 每个条目是一个报告和保持时间 u16（单位 ms），共 10 字节 |
| `0x12` play | | 启动程序 |
| `0x13` stop | | 停止程序并释放所有按键 |
| `0xB0` download | | 将芯片重启进入 ROM 加载器 |

程序可容纳 8192 个条目。循环开始之前的条目只播放一次；其余条目重复。播放器使用 `vTaskDelayUntil` 在 1 kHz 节拍上等待，因此保持时间累加而不会漂移。

陷阱：在 macOS 上通过 bleak 进行无响应写入时，当 CoreBluetooth 队列已满，写入会丢失，而且 bleak 从不读取 `canSendWriteWithoutResponse`（300 个连续报告只有 67 个到达）。`pokeldn.pad.link` 在每次报告写入前等待该标志（每个报告 2.4 ms，无丢失），并在标志不存在或持续一秒为假时使用带响应写入，每个 60 ms。

断开连接会将报告恢复为中立状态，因此上位机消失时不会留下任何按住的按键；正在播放的宏会继续。

## 串口侧

经典 ESP32 一直连接在电脑的 USB 上：UART0 以 921600 波特率双向传输帧（`firmware/pad/main/uart_link.c`、`pokeldn/pad/serial_link.py`），并且控制台输出关闭。控制台关闭时，没有任何东西将 UART0 路由到 GPIO1 和 GPIO3，因此固件自行设置引脚；没有它，手柄板不会应答任何请求。

    A5 5A | length u16 (type and payload) | type u8 | payload | sum of type and payload mod 256

| 类型 | 方向 | 负载 |
|---|---|---|
| `0x01` | 到板 | 8 字节报告；用 `0x81` 应答 |
| `0x02` | 到板 | 无；用 `0x82` 和状态记录应答 |
| `0x03` | 到板 | 命令，与控制特征上的相同；用 `0x81` 应答 |
| `0x81` | 到上位机 | 结果 i8：0，-1 长度错误，-2 拒绝 |
| `0x82` | 到上位机 | 状态记录；mounted 表示 Switch 设置了玩家灯 |

上位机以 DTR 和 RTS 低电平打开端口。DevKit 的 CP2102 在 macOS 上打开端口时仍会重启手柄板，启动期间发送的请求会丢失；上位机在最多 3 秒内重复状态请求。服务在扫描低功耗蓝牙之前，会尝试每个不是 S3 原生 USB 的 USB 串口。请用一个进程独占端口：每次新打开都会重启手柄板并断开其蓝牙链接。

## 经典蓝牙侧

`firmware/pad/main/bt_esp32.c` 注册了一个 Bluedroid HID 设备：170 字节的 Pro 手柄报告描述符，服务名“Wireless Gamepad”，提供商“Nintendo”，子类 0x08，设备类别 0x002508，名称“Pro Controller”，SSP 无输入无输出，调制解调器睡眠关闭。它按 ID 应答 0x01 子命令：0x02 设备信息（固件 4.00，类型 0x03，其蓝牙地址），0x10 SPI 读取，0x03 报告模式，0x04 触发时间，0x21 MCU 配置，其余仅以普通 ACK 应答；0x30（玩家灯）将控制器标记为已被占用。任何 0x30 之前都会先发送一条回复。

0x30 报告在按键或摇杆变化时立即发送，否则从链路打开时起每 100 ms 发送一次；只要手柄板不发送，Switch 就不会开始握手。手柄板在链路打开后等待 1 s，在切换为嗅探模式后等待 250 ms，在发送因拥塞被拒绝（原因 8）后等待 45 ms：这是 friendmaker 的 Switch Lite 数值（`classic_bt_controller_transport.cpp`，`SWITCH_LITE`）。陷阱：每 15 ms 发送一次 0x30 会使链路拥塞，Switch 会在玩家灯亮起后 20 秒内断开连接（HCI 0x13）。

Switch 的握手顺序为：0x02、0x08、0x10 在 0x6000 和 0x6050、0x03（0x30）、0x04、0x10 在 0x6080、0x6098、0x8010、0x603D、0x6020、0x40、0x30（0）、0x48、0x21、0x30（玩家 1）。

已绑定的手柄板会在启动时重新连接到其 Switch。刷写合并镜像会覆盖 NVS 分区以及其中的绑定：请从“更改握法/顺序”重新配对。

`pro_report.c` 将共享报告映射到 Pro 手柄的字节（dekuNukem `bluetooth_hid_notes.md`）：摇杆静止时为 0x800，两个方向为 0x700，与它在 0x603D 返回的出厂校准一致；序列号和用户校准使用空白闪存（0xFF）。`tests/test_pad_pro.py` 在上位机上编译它，并检查每个按钮位和校准。

## 宏

宏是一个扩展名为 `.pokemacro` 的 JSON 文件（`pokeldn.pad.macro`）：

```json
{
  "format": "pokeldn-macro", "version": 1,
  "name": "Soft reset", "description": "", "author": "", "game": "",
  "press_ms": 100, "gap_ms": 150,
  "setup": [{"press": "HOME"}, {"wait": 1000}],
  "loop": [
    {"press": ["A", "B"], "ms": 500, "after": 2000, "note": "skip the intro"},
    {"repeat": 3, "steps": [{"press": "A"}]},
    {"press": [], "left": [0, 1], "ms": 300},
    {"wait": 5000}
  ],
  "loops": 0
}
```

| 字段 | 含义 |
|---|---|
| `press_ms`、`gap_ms` | 当步骤未指定时，步骤保持其输入的时长，以及之后的暂停 |
| `setup` | 只运行一次的步骤 |
| `loop` | 重复 `loops` 次的步骤；0 表示重复直到停止 |
| 按键步骤 | `press`：一个按键名称或同时按住的一组按键（`A B X Y L R ZL ZR PLUS MINUS LSTICK RSTICK HOME CAPTURE UP DOWN LEFT RIGHT UPLEFT UPRIGHT DOWNLEFT DOWNRIGHT`）；`left` 和 `right`：摇杆 `[x, y]`，范围从 -1 到 1，上为正；`ms` 保持；`after` 暂停；`note` |
| 等待步骤 | `wait`：所有按键释放的毫秒数 |
| 重复步骤 | `repeat`：对 `steps` 重复 1 到 10000 次，最多嵌套 8 层 |

编译器会展开重复内容，合并相邻具有相同报告的条目，并将超过 65535 ms 的保持时间分割。展开后超过 8192 个条目的宏将被拒绝。两个相同按键之间的 `after: 0` 会将它们合并为一次保持。`version` 比读取器版本新的文件会被拒绝。

## 上位机侧

`pokeldn.pad.service` 保持蓝牙链路，并在 `127.0.0.1:47800` 上每行接收一个 JSON 请求：`status`、`connect`、`send`、`tap`、`play`、`stop`、`download`、`scan`、`disconnect`。应用将其作为自己的子进程启动；当没有服务运行时，`tools/switch/pad.py` 会在自己的进程中启动它。

在 macOS 上，当链路打开时手柄板断电（例如从 Switch 上拔下），CoreBluetooth 可能会使读取或写入处于挂起状态且没有错误。服务会在限制时间内应答每个请求（`status` 5 s，`play` 120 s，`scan` 20 s，其余包括 connect 为 40 s）。超过限制后，服务会关闭链路，让手柄板重新广播，并回复错误。应用的客户端会在 150 s 后停止等待。

    ./.venv/bin/python tools/switch/pad.py A
    ./.venv/bin/python tools/switch/pad.py HOME wait:1 'RIGHT*3' A
    ./.venv/bin/python tools/switch/pad.py hold:B:2 stick:L:-1:0:0.5
    ./.venv/bin/python tools/switch/pad.py --play soft_reset.pokemacro
    ./.venv/bin/python tools/switch/pad.py --stop --status

macOS 会在负责的应用未声明 `NSBluetoothAlwaysUsageDescription` 时终止打开蓝牙的进程，这种情况发生在嵌入其他应用的终端中。`pad.py --make-app PATH` 会写出一个运行该服务的小应用；用 `open` 打开一次并允许蓝牙，之后 `pad.py` 调用和源码检出中的应用就可以使用它。

## 重新刷写

手柄板占用了 USB 端口，因此 esptool 无法将其复位到加载器。下载命令、开发板页面的安装以及 `pad.py --download` 通过蓝牙完成这一操作；在插入手柄板时按住 BOOT 也可以在没有固件的情况下进入加载器。

| 陷阱 | 固件或上位机侧 |
|---|---|
| `RTC_CNTL_USB_CONF` 在复位后仍然存在；如果保留在 USB-OTG 上，加载器为 `303a:0009`，esptool 只有一半时间能访问到 | 停止 NimBLE 和 TinyUSB，将 PHY 交还 USB Serial/JTAG，并设置 `RTC_CNTL_FORCE_DOWNLOAD_BOOT`；加载器随后为 `303a:1001` |
| 蓝牙和 USB 开启时调用 `esp_restart()` 可能挂起 | 不以该方式调用 |
| 在 macOS 上首次打开全新的加载器端口读取不到任何内容，且 esptool 会锁定端口 | `gui/board.py` 等待 8 s，然后在不复位的情况下连接 |
| 从强制加载器刷写后，USB 复位仍停留在加载器中 | `--after watchdog-reset` |

`python -m gui.board --kind pad|radio` 可刷写任一固件覆盖另一个；`--from-loader` 可刷写已被下载命令放入加载器的手柄板。

陷阱：在 FreeRTOS 默认 100 Hz 下，USB 循环的延迟为零个节拍，导致 NimBLE 饥饿；固件以 1000 Hz 构建。

## 构建

    . scratchpad/esp/env.sh
    cd firmware/pad && idf.py -B BUILD_DIR -D SDKCONFIG=SDKCONFIG_PATH build

TinyUSB 来自组件管理器（`espressif/esp_tinyusb` 2.4.0）。发布版本会在 radio 镜像旁边构建 `pokeldn-pad-s3.bin`。

## 未解决

- 尚未测量 Switch 2 是否能与经典 ESP32 固件配对，或是否接受 HORI ID；只测量过 Switch Lite。

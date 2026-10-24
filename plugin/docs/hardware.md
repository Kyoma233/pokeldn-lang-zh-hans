---
title: Hardware and setup
nav_order: 9
has_children: true
---

# 硬件与设置

无线电是一块通过 USB 串口运行 `firmware/esp32` 的 ESP32 开发板；LDN、Pia 与游戏逻辑在主机上的 Python 中运行，无需 root，也无需 Wi-Fi 驱动。所有作品都通过它交换。Linux 主机也可直接驱动一块支持 AP 的 Wi-Fi 网卡；该路径为旧方案。

## 页面

- [ESP32 无线电](hardware_esp32.md)：开发板、固件、串口协议与测量。
- [Switch 密钥](hardware_switch_keys.md)：安全安装 `prod.keys`。
- [适配器](hardware_adapters.md)：Linux Wi-Fi 网卡、配置与失败模式。
- [手柄板](hardware_pad.md)：ESP32-S3 可被主机认作有线手柄（经蓝牙 LE 驱动），或经典 ESP32 可配对为 Pro 手柄（经 USB 串口驱动）。
- [树莓派主机](hardware_raspberry_pi.md)：Linux 部署与受监督的神秘礼物运行器。

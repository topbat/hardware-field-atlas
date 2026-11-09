# ESP32-S3-DevKitC-1 研发档案的资料来源

资料核对日期为 2026 年 11 月 9 日。此处的 v1.0 和 v1.1 是乐鑫参考板版号。采购型号、板版和 ESP-IDF 版本分别记录。以板上丝印识别手中的 PCB 版本，再选对应的文档和固件引脚。[v1.0 手册](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.0.html) · [v1.1 手册](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html)

## 板版、采购型号和电压

| 板版 | 手册订购信息中的代表 SKU | 模组 | Flash / PSRAM |
| --- | --- | --- | --- |
| v1.0 | ESP32-S3-DevKitC-1-N8R8 | ESP32-S3-WROOM-1-N8R8 | 8 MB Quad SPI / 8 MB Octal SPI |
| v1.0 | ESP32-S3-DevKitC-1U-N8R8 | ESP32-S3-WROOM-1U-N8R8 | 8 MB Quad SPI / 8 MB Octal SPI |
| v1.1 | ESP32-S3-DevKitC-1-N16R8 | ESP32-S3-WROOM-1 | 16 MB / 8 MB |
| v1.1 | ESP32-S3-DevKitC-1U-N16R8 | ESP32-S3-WROOM-1U | 16 MB / 8 MB |
| v1.0、v1.1 | ESP32-S3-DevKitC-1-N32R16V | ESP32-S3-WROOM-2-N32R16V | 32 MB Octal SPI / 16 MB Octal SPI |

两版手册的订购表各有适用范围。v1.1 的订购表还保留若干已停止供应的 N8、N8R2 型号。N32R16V 同时出现在两版订购表，单靠 SKU 无法判断该板的 RGB 引脚。[v1.0 订购信息](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.0.html#ordering-information) · [v1.1 订购信息](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html#ordering-information)

开发板手册将 USB 供电、排针 5V 与 GND、排针 3V3 与 GND 列为三类互斥供电方式。排针 3V3 对应板级 3.3 V。N32R16V 的 1.8 V 标注对应模组内部 SPI 存储电压域，排针供电仍依据板卡手册。带 Octal SPI 存储的适用模组占用 GPIO35、GPIO36 和 GPIO37。[板级供电](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html#power-supply-options) · [WROOM-2 模组数据手册](https://documentation.espressif.com/esp32-s3-wroom-2_datasheet_en.html)

## 引脚与可复现固件

| 功能 | v1.0 | v1.1 |
| --- | --- | --- |
| 板载可寻址 RGB LED D6 | GPIO48，J3.16 | GPIO38，J3.10 |
| 3.3 V 排针 | J1.1、J1.2 | J1.1、J1.2 |
| 5 V 排针 | J1.21 | J1.21 |
| UART0 TX / RX | J3.2 / J3.3，GPIO43 / GPIO44 | J3.2 / J3.3，GPIO43 / GPIO44 |
| 原生 USB D+ / D− | J3.19 / J3.20，GPIO20 / GPIO19 | J3.19 / J3.20，GPIO20 / GPIO19 |

排针表和原理图一起用于关联 J1、J3 与板载器件。RGB LED 由两版原理图中的 D6 对应。[v1.0 排针](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.0.html#header-block) · [v1.1 排针](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html#header-block)

ESP-IDF v5.4.4 的 Blink 是开发示例。它为 esp32s3 预设 LED strip 和 GPIO48。复现时以 esp32s3 为构建目标，在 Example Configuration 中选择 LED strip，v1.0 使用 GPIO48，v1.1 显式改为 GPIO38。这里只核验了仓库示例与图纸引脚的对应关系，构建、烧录和板上运行仍待实测。[v5.4.4 Blink 目录](https://github.com/espressif/esp-idf/tree/v5.4.4/examples/get-started/blink) · [固定提交的 esp32s3 配置](https://github.com/espressif/esp-idf/blob/296b6eab9445fd720e71aecab961e2d3fbca9944/examples/get-started/blink/sdkconfig.defaults.esp32s3)

## 原厂文件与位号映射

| 板版 | 原理图 | PCB 布局 | 外形尺寸源文件 |
| --- | --- | --- | --- |
| v1.0 | [原理图 PDF](https://dl.espressif.com/dl/SCH_ESP32-S3-DEVKITC-1_V1_20210312C.pdf) | [布局 PDF](https://dl.espressif.com/dl/PCB_ESP32-S3-DevKitC-1_V1_20210312CB.pdf) | [尺寸 DXF](https://dl.espressif.com/dl/DXF_ESP32-S3-DevKitC-1_V1_20210312CB.dxf) |
| v1.1 | [原理图 PDF](https://dl.espressif.com/dl/schematics/SCH_ESP32-S3-DevKitC-1_V1.1_20221130.pdf) | [布局 PDF](https://dl.espressif.com/dl/schematics/PCB_ESP32-S3-DevKitC-1_V1.1_20220429.pdf) | [尺寸 DXF](https://dl.espressif.com/dl/schematics/esp_idf/DXF_ESP32-S3-DevKitC-1_V1.1_20220429.dxf) |

两版均按布局图中的 25.40 × 62.74 mm 板框显示。正面视图以板框左上角为原点。底面查看时水平镜像，使观察方向与底面装配图一致。

- **v1.0** 的定位点取自原厂布局 PDF 第一页的位号文字框中心。正面装配图和反面视图用于核对朝向，J1、J3 归到底面。网页物料表关联从对应原理图核录的位号子集。图纸投影保留导航用途，未记录原始贴装角度。[v1.0 布局图](https://dl.espressif.com/dl/PCB_ESP32-S3-DevKitC-1_V1_20210312CB.pdf)
- **v1.1** 的物料和贴装坐标分别来自参考设计包的 `05_BOM` 和 `06_Placement`。贴装表有 48 个位号，其中 46 个在正面，J1、J3 在底面。横坐标沿用原厂毫米值，纵坐标用板高减去原厂毫米值，保留原厂角度。图中标记对应贴装基准点，基准点可位于器件焊脚或封装边缘。BOM 的 44 个已列装位号均可关联坐标，PCB 裸板行没有贴装坐标。C13、C14、C15 和 R14 出现在贴装表中，原理图标记为 NC。[v1.1 参考设计 ZIP](https://documentation.espressif.com/api/resource/doc/file/0wyBg1eV/FILE/ESP32-S3-DevKitC-1_Reference_Design.zip)

v1.1 设计包包含原理图 DSN、PCB 和 ASC、Gerber、加工要求、BOM V0.3、贴装 HTML 和装配 PDF。乐鑫文档中心的文件编号为 `TCD000001079`，发布记录为 2026 年 6 月 17 日。核对的 ZIP 大小为 3,368,834 字节，SHA-256 为 `25b16b894c4e104ad62640ceaf60ba7ead356105567f9471da4ce3c66ddb871a`。[乐鑫开发板文档下载中心](https://www.espressif.com/en/support/download/documents/development-board) · [原始 ZIP](https://documentation.espressif.com/api/resource/doc/file/0wyBg1eV/FILE/ESP32-S3-DevKitC-1_Reference_Design.zip)

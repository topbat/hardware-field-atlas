# 家庭、出行与边缘设备调研

核验日期为 2026 年 11 月 9 日。以普通消费者实际要完成的任务组织品类，同时保留可供研发对照的设备版本、传感器、推理位置和证据。样本以中国品牌为主，标明资料适用地区。

## 如何判断用户依赖

- 清洁是本组最适合优先扩充的重复任务。IDC 的 2025 年全球出货追踪记录了 2,412 万台扫地机器人、199 万台割草机器人和 237 万台擦窗机器人。割草机器人同比增长 63.8%，但绝对出货量约为扫地机器人的十二分之一。首页可优先展示室内清洁，庭院作为独立场景。出货量反映产品供给和采用规模，使用频率与停用损失仍需行为数据或访谈验证。[IDC Worldwide Cleaning Robot Trackers](https://www.idc.com/resource-center/blog/global-home-cleaning-robot-market-2025/)
- 出行有较大的设备存量。国家统计局记录 2025 年末中国新能源汽车保有量为 4,397 万辆。这一数字涵盖不同品牌和配置。驾驶辅助的启用率、使用条件及真实依赖程度需要独立证据。[国家统计局《中华人民共和国 2025 年国民经济和社会发展统计公报》](https://www.stats.gov.cn/sj/zxfb/202602/t20260228_1962662.html)
- 安防与宠物照护的体验常由少数关键时刻决定。选型时关注断网或断电后本机是否继续检测、记录或执行计划，以及外出时能否收到通知。厂商资料能证明支持的功能，缺少可比较的依赖率时按场景收录，不作普及排名。[Aqara G5 Pro PoE 帮助中心](https://store-support.aqara.com/products/camera-hub-g5-pro) · [PETKIT D4SH-2 手册](https://instructions.petkit.com/App%20Manual/D4sh-2/D4SH-2_User%20Manual_EN_V1.0_20251024_%20.pdf)
- 对内容创作者，机身能否保持单人构图、跟踪有哪些模式限制，比泛称「AI 相机」更可核对。边缘盒子面向另一类任务，主要用于原型搭建和推理部署，单独放进研发入口。[DJI 官方问答](https://www.dji.com/osmo-pocket-3/faq) · [Seeed J30/40 开发文档](https://wiki.seeedstudio.com/reComputer_J30_40_with_Jetson_getting_start/)

## 本轮入库样本

| 场景 | 代表型号 | 选择理由和核对点 |
| --- | --- | --- |
| 室内清洁 | 石头 Saros 10R | 可对照深度测距、RGB 识别、低机身和基站条件。保留与 Saros 10 的导航方案差异。[官方产品页](https://global.roborock.com/pages/roborock-saros-10r) |
| 家居安防 | Aqara Camera Hub G5 Pro PoE | 适合讲清端侧识别、局域网 RTSP、远程功能和 PoE 供电。规格按 CH-C03E / CH-C03D 行记录。[官方规格](https://www.aqara.com/en/product/camera-hub-g5-pro-specs/) · [PoE 帮助中心](https://store-support.aqara.com/products/camera-hub-g5-pro) |
| 智能出行 | 新一代小米 SU7 标准版 | 公开披露激光雷达、车端辅助驾驶算力与 Xiaomi HAD。配置、OTA 和功能适用条件分开记录。[车型配置](https://www.xiaomiev.com/xiaomi/car-config) · [辅助驾驶技术](https://www.xiaomiev.com/pilot) |
| 影像创作 | DJI Osmo Pocket 3 | 可用「相机画面 → 主体跟踪 → 云台动作」解释感知和执行。把首次激活、支持模式和本机存储分别列出。[官方产品页](https://www.dji.com/osmo-pocket-3) · [官方问答](https://www.dji.com/osmo-pocket-3/faq) |
| 庭院维护 | Segway Navimow i105E | RTK 与视觉定位、辅助建图和避障各有用途，适合比较安装条件和复杂地形。标明欧洲版。[官方产品页](https://navimow.segway.com/products/navimow-i105?variant=52466691572017) |
| 宠物照护 | PETKIT YumShare Dual-hopper 2 | 将定时或手动出粮与多猫识别分列，后续可按电源、网络和服务条件逐项验证。记录 D4SH-2 型号。[官方产品页](https://www.petkit.com/products/yumshare-dual-hopper-2-automatic-feeder-with-camera) · [设备手册](https://instructions.petkit.com/App%20Manual/D4sh-2/D4SH-2_User%20Manual_EN_V1.0_20251024_%20.pdf) |
| 研发与复现 | Seeed reComputer J3010 | 对照 Classic 4 GB 版本的模组、载板、CSI 接口和固件，提供可复现实验步骤。[官方商品页](https://www.seeedstudio.com/reComputer-J3010-p-5589.html) · [开发文档](https://wiki.seeedstudio.com/reComputer_J30_40_with_Jetson_getting_start/) |

## 把目录扩成可用的选型与研发工具

1. 入口以任务分组。家庭清洁、照护、安防、出行和创作各自呈现一张用途明确的首图，场景内保留品类、设备、配件和版本。新增擦窗、泳池清洁等细分项时沿用同一分组，型号仍可通过全局搜索直达。
2. 详情先回答用途、前置条件和可用范围。第一屏优先放整机外观、场景和两三个关键规格。下一屏展示传感器、接口、部件特写或结构图，图片旁标记原厂图、实物拆解或重绘证据。若只有原厂产品页，保留来源入口并标注图像覆盖范围。
3. 比较页沿「感知 → 推理 → 执行」展开。记录输入传感器、处理位置、订阅或账号、局域网可用性、断网或断电后的退化行为。规格字段保留 SKU、地区、固件、测试条件、出处与日期，以便解释同名版本差异。
4. 研发入口提供部件料号反查、接口条件、BOM 与公开资料跳转。复现实验记录模型版本、功耗模式、环境、输入分辨率、时延、故障表现和测量方法。采用厂商规格的标称值与社区实测分开显示。交互式电路板可参考从器件表定位焊盘和网络的做法，维修文档可参考将拆卸路径、工具和配件来源放在同一任务中。[Interactive HTML BOM](https://github.com/openscopeproject/InteractiveHtmlBom) · [iFixit 可维修性指南](https://www.ifixit.com/repairability)

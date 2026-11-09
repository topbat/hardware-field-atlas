# 数据与接口契约

所有业务接口位于 `/api`。本地 FastAPI 端口 8765，Vite 端口 5173。错误使用 HTTP 状态及 JSON 的 `detail`。GET 数据由应用读取，不要求登录。

## 目录文件

`data/catalog.json` 为 UTF-8 对象 `{ "products": [Product, ...] }`。产品字段如下。未采集的值用空数组、null 或有说明的状态，保留出处，禁止猜值。

    Product = {
      id: string, name: string, brand: string, category: Category,
      kind: "commercial"|"open"|"reference"|"module", origin: string,
      tagline: string, description: string, aliases: string[], tags: string[],
      revision: string, checkedAt: string,
      specs: [{ key: string, label: string, value: string, sourceIds: string[] }],
      abilities: [{ name: string, input: string, compute: "device"|"phone"|"lan"|"cloud"|"mixed"|"unknown",
                    output: string, offline: string, sourceIds: string[] }],
      parts: [{ id: string, name: string, role: string, mpn: string|null, manufacturer: string|null,
                quantity: string, status: "confirmed"|"observed"|"inferred"|"unknown",
                sample: string|null, sourceIds: string[] }],
      sources: [{ id: string, title: string, url: string, type: "official"|"teardown"|"open"|"manual"|"other",
                  locator?: string, note?: string }],
      model: null | { url: string, type: "reconstruction"|"concept"|"official"|"scan", note: string },
      image?: Photo,
      photos?: Photo[],
      cutaway?: { url: string, alt: string, type: "concept"|"reconstruction", note: string, sourceIds: string[] },
      illustration?: { url: string, technical: "teardown"|"functional", exterior: "reference"|"concept", sourceIds: string[],
                       panels?: { overview: string, detail: string, specs: string, angles: string },
                       breakdown?: { details: VisualCard[], angles: VisualCard[] } },
      engineering?: EngineeringArchive,
      build?: { repo: string, steps: string[], note: string, stepSourceIds?: string[][] }
    }

    Category = "toy"|"glasses"|"speaker"|"mirror"|"cabinet"|"desk"|"phone"|"tablet"|"computer"
             |"wearable"|"earbuds"|"recorder"|"education"|"vacuum"|"security"|"vehicle"
             |"edge"|"imaging"|"outdoor"|"pet"|"fabrication"|"xr"

    Photo = { url: string, alt: string, type: "concept"|"official"|"retail"|"photo"|"teardown", sourceId?: string }

图解中的 `VisualCard` 含 `url`、`title`、`caption`、`sourceIds` 和可选的 `partId`。每个图卡 URL 对应一张带中文说明的独立图。

实物图片必须关联原商品页、原厂文档或原作者来源。剖视插图是依据这些资料整理出的解释性视图，独立记录来源与近似说明。

Product ID 稳定，部件 ID 在产品内部唯一。给同一位置的替代样机证据不同部件 ID（例如 `storage-a`、`storage-b`）。规格 key 尽量对齐，例如 `weight`、`battery`、`connectivity`。3D 模型有 `part_id` extras，部件 ID 保留短横线。组件可同组多个对象。产品没有模型时 UI 可用部件清单和来源作为结构视图。三种模型 URL 与产品 id 对应。

## 目录查询

- `GET /api/health` → `{status:"ok"}`
- `GET /api/catalog?q=&category=&kind=&compute=&model=&limit=100&offset=0` → `{products:Product[], total:number, parts:[{productId, productName, part:Part}], categories:[{id,label,count}]}`。关键词可用型号、别名、厂商料号、零件、品牌、标签。未输入 q 时 parts 为空。model=true 筛有模型。
- `GET /api/products/{id}` → Product，响应 `ETag` 可用于条件写入。
- `GET /api/compare?ids=foo,bar` → `{products:Product[]}`，按照 ids 顺序返回 2–4 个唯一产品。
- `GET /api/products/{id}/bom.csv` → UTF-8 BOM CSV。
- `POST /api/corrections` 接收 `{productId, field, message, url?}`，返回 `{id,status:"pending"}`。
- 管理接口使用环境变量 `ATLAS_ADMIN_TOKEN` 作为 Bearer Token。GET /api/admin/corrections、PATCH /api/admin/corrections/{id} 接收 `{status:"accepted"|"dismissed"}`。PUT /api/admin/products/{id} 接受已存在产品的完整 Product 对象并写入持久覆盖，保留每次修改快照。带 `If-Match` 条件时在事务内核对版本，冲突返回 412。GET /api/admin/products/{id}/revisions 可查看快照。

## 研究室接口

浏览器使用 `crypto.randomUUID()` 生成随机工作区密钥（可以用安全随机字节加长），仅保留在本地存储，使用 `Authorization: Bearer <token>`。服务器按密钥哈希隔离记录。所有除 config 之外的 /research 请求都用此凭证。

- `GET /api/research/config` → `{modelEnabled:boolean,visionEnabled:boolean}`。
- `POST /api/research/run` → 输入 `{workflow:"search"|"evidence"|"compare"|"build",query:string,productIds:string[],partId?:string,useMemory:boolean,image?:string,allowImageTransfer?:boolean}`。image 为 jpeg/png/webp 的 Base64 data URL，先在客户端缩小到 2 MB 内。query 或 image 至少有一个。
- 返回 `{id, mode:"catalog"|"model", answer:string, steps:[{name,status,detail}], citations:[{id,title,url,productId,locator?}], productIds:string[], createdAt:string, warning?:string}`。answer 为安全纯文本或 Markdown 文本，前端不要注入 HTML。引用 ID 可显示为文本。
- `GET /api/research/history` → `{runs:Run[]}`；`DELETE /api/research/history` → 204。
- `GET /api/research/notes` → `{notes:[{id,text,createdAt}]}`；`POST /api/research/notes` 接收 `{text}` 返回新 Note；`DELETE /api/research/notes/{id}` → 204。记忆由用户主动加入；仅在 useMemory 为真时可用。

图片不会落盘。模型不可用时以目录证据继续工作并标明模式。模型接口地址只可由部署环境配置。

## 版本化部件档案

产品的可选字段 engineering 由 skus 与 revisions 组成。SKU 包含订货码、模组、Flash、PSRAM 和可选的模块 SPI 电压。各板版分别记录适用 skuIds、板级电源 rails、引脚 pins、固件 firmware、文件 files、BOM bom 和可选的 PCB board。与产品的普通 parts 及 BOM CSV 并存。公网体验版随目录快照发布同一份档案。

- 固件 fileId 指向本版的固件文件，pinIds 指向本版引脚。引脚可按 railId 和 ref 追到本版电源和 BOM。
- board.placements 按 ref 关联本版 BOM。x、y 是正面视角下从左上角起算的毫米坐标，背面展示时横向镜像。coordinateSource 区分原厂贴装参考点和 PDF 位号投影，未核验的旋转角留空。
- 每份技术资料通过 sourceIds 引用产品来源，文件可附 SHA-256。fit 区分参考装配、不装配和未列出。选定 SKU 的实际物料仍以对应原厂资料为准。

# 硬件志 · Hardware Atlas

面向极客的中文 AI 硬件研究库。目录优先收录国内整机、开源项目和参考模组。通过型号、厂商或料号查找设备，按证据比较规格和运行方式，并在拆解台关联模型、BOM 和来源。

## 本地运行

需要 Python 3.12、uv 和 Node.js 22.12+。在本项目目录运行以下命令。Windows PowerShell 可把 npm 写成 npm.cmd。

```sh
uv sync --locked --python 3.12
npm --prefix web ci
npm --prefix web run build
uv run --no-sync uvicorn atlas.main:create_app --factory --app-dir server --host 127.0.0.1 --port 8765
```

浏览器打开 http://127.0.0.1:8765 。API 文档位于 http://127.0.0.1:8765/api/docs 。

Windows 也可以运行 `pwsh -File scripts/start.ps1 -Build`，之后省略 `-Build` 可复用构建结果。

前端开发时保留后端进程，再运行 `npm --prefix web run dev`。Vite 将 /api 转给本地后端。生产构建由 FastAPI 同源提供。

## 配置和数据

- 无模型凭据时，研究室使用本地目录、分步检索和可核对的证据。配置 `ATLAS_AI_BASE_URL`（含 /v1）、`ATLAS_AI_KEY`、`ATLAS_AI_MODEL` 后可接入兼容 Chat Completions 的模型，按需配置 `ATLAS_AI_VISION_MODEL` 启用图片检索。图片仅在用户明确同意后传给服务，应用不落盘。
- 本地配置可将 .env.example 复制为 .env，再用 `uv run --no-sync --env-file .env uvicorn atlas.main:create_app --factory --app-dir server --host 127.0.0.1 --port 8765` 启动。模型调用会向所配置服务发送本次任务必要的目录和上下文。
- 研究历史和主动记忆按浏览器随机凭证隔离。同一浏览器的站点存储需要保留，清除站点存储后原凭证无法从应用找回。工作区提供独立删除操作。
- 使用 `ATLAS_ADMIN_TOKEN` 启用内容审核页 /admin 和审核 API。目录种子由 data/catalog.json 管理，线上产品修订、纠错和研究记录保存在 `ATLAS_DATA_DIR`（默认 runtime/）下的 SQLite 数据库。备份时使用 SQLite 在线备份，或停止应用后复制整个目录。
- 三个 Blender 原件在 assets/blender，网页 GLB 和二维图在 web/public/assets。模型以近似结构或概念标注。脚本可用 Blender 5.2 运行 `blender --background --python-exit-code 1 --python scripts/build_models.py` 重建。
- 实物、原厂及电商图在目录和照片图库标明来源。受限的拆解图保留原文入口。三张 ImageGen 剖视图按公开资料重绘，位于 web/public/assets/cutaways；建模的主要证据见 [旗舰视觉依据](docs/flagship-visual-evidence.md)。
- 档案中的「AI 图解」使用 Codex 内置 ImageGen 生成，位于 web/public/assets/illustrations。图版包含产品介绍、两个补充视角和拆解或功能示意，标注参考来源。没有核实的内部装配只画功能关系，没有核实的外壳标为概念示意。[逐款生图约束与参考素材](docs/illustration-briefs.json)
- 首页概念图由 Codex ImageGen 生成。提示词指定通用深色 AI 摄像眼镜、分离的镜腿、电池和电路板、米白工程工作台和无品牌字样。商品样机信息以档案中的原始出处为准。

## 单机部署

```sh
docker compose up -d --build
```

默认端口绑定到主机回环地址。对外部署时由已有的 HTTPS 入口转发，并设置请求限流及模型费用配额。若启用代理传递真实客户端地址，仅信任实际反向代理的地址。部署与备份以单节点、同机持久卷为边界。

## 验证与设计依据

- `uv run --locked pytest` 验证目录、审核和研究工作流。
- `npm --prefix web run build` 验证前端生产构建。
- `python scripts/verify_assets.py` 核对目录、三维部件与二维图编号。
- [数据与接口](docs/api.md) · [原型体验调研](docs/research-experience.md) · [国产样本](docs/research-catalog.md) · [研究工作流](docs/research-intelligence.md)

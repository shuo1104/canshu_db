# 售后参数搜索工具

把用户上传的 Excel 文件按“一个文件中的一个 sheet = 一个数据库子表”的方式导入 MySQL，并通过 **FastAPI + React** 提供关键词搜索和数据导入界面。后端同时暴露 JSON API，可供小程序或其他客户端调用。

## 技术栈

- **后端**：Python + FastAPI + PyMySQL
- **前端**：React + TypeScript + Vite
- **数据库**：MySQL 8
- **部署**：Docker Compose

## 快速启动

推荐使用 Docker Compose 启动完整环境：

```bash
cp .env.example .env
docker compose up --build
```

启动后访问：

```text
http://localhost:4573
```

Compose 会启动两个服务：

- `mysql`：MySQL 8 数据库，数据持久化在 `mysql_data` volume。
- `app`：FastAPI 后端 + React 前端构建产物，监听 `4573` 端口。

## 配置

`.env` 中可配置端口和数据库账号：

```env
APP_PORT=4573
MYSQL_PORT=3306
MYSQL_ROOT_PASSWORD=change_me_root_password
APS_DB_NAME=aftersales
APS_DB_USER=aftersales
APS_DB_PASSWORD=change_me_app_password
APS_DB_CHARSET=utf8mb4
```

应用容器内使用以下连接变量：

- `APS_DB_HOST`
- `APS_DB_PORT`
- `APS_DB_NAME`
- `APS_DB_USER`
- `APS_DB_PASSWORD`
- `APS_DB_CHARSET`

## 开发模式

如果不用 Docker，需要分别启动后端和前端，并先准备一个可访问的 MySQL。

启动后端：

```bash
uv run uvicorn src.api:app --reload --host 0.0.0.0 --port 4573
```

启动前端（Vite dev server 会把 `/api` 代理到 `http://localhost:4573`）：

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器默认运行在 `http://localhost:5173`。

## 导入数据

### Web 导入

1. 打开 `http://localhost:4573`（或开发时的 `http://localhost:5173`）。
2. 点击导航栏「数据导入」。
3. 上传一个 `.xls` 或 `.xlsx` 文件。
4. 如果文件里有多个 sheet，选择其中一个作为本次导入的子表。
5. 输入数据表名称。
6. 查看前三行预览，选择哪一行作为数据库字段。
7. 点击「创建数据表并导入」。

如果同名数据表已存在，可以勾选「如果同名数据表已存在，则替换它」后重新导入。

### CLI 导入

需要自动化时，可以在 app 环境中显式指定文件、sheet、表名和字段行；这种方式可继续使用挂载到容器内的 `数据库_副本/`：

```bash
docker compose exec app uv run python scripts/import_data.py \
  --file 数据库_副本/设备参数信息汇总.xls \
  --sheet Sheet1 \
  --table-name 设备参数 \
  --header-row 0
```

`--header-row` 使用从 0 开始的行号：`0` 表示第一行，`1` 表示第二行，`2` 表示第三行。加 `--replace` 可替换同名数据表。

## 搜索数据

在首页「搜索」中：

- 输入「关键词 1」。
- 系统会先用关键词 1 搜索，并从命中结果的完整行里提取字段名候选。
- 可以手动输入「关键词 2」，也可以点击字段候选把它填入关键词 2。
- 每个关键词只要出现在同一行的任意字段名或单元格内容中，就返回整行信息。
- 同时输入两个关键词时，两个关键词是 AND 关系：同一行必须同时命中关键词 1 和关键词 2。

搜索结果会显示数据表名称、来源文件、sheet 名称、命中字段和完整行内容，并高亮命中的字段名和内容片段。

## API 接口

后端同时暴露 JSON API：

| 接口 | 方法 | 用途 |
|---|---|---|
| `GET /api/health` | - | 健康检查 |
| `GET /api/search` | `keyword1`, `keyword2`, `mode`, `limit` | 搜索 |
| `GET /api/search/candidates` | `keyword1`, `max_candidates` | 关键词 2 候选字段 |
| `POST /api/import/analyze` | `file` | 获取 Excel 的 sheet 列表 |
| `POST /api/import/preview` | `file`, `sheet_name` | 获取指定 sheet 前三行 |
| `POST /api/import` | `file`, `sheet_name`, `display_name`, `header_row_index`, `replace_existing` | 执行导入 |

完整接口文档可在启动后访问：

```text
http://localhost:4573/docs
```

## 运行测试

后端测试：

```bash
uv run pytest tests/ -v
```

前端构建检查：

```bash
cd frontend
npm run build
```

## 项目结构

```text
.
├── 数据库_副本/             # 可选 CLI Excel 数据源目录
├── docker-compose.yml      # MySQL + FastAPI 应用编排
├── Dockerfile              # 多阶段构建：前端 + 后端
├── frontend/               # React 前端
│   ├── src/
│   │   ├── api.ts          # 后端 API 客户端
│   │   ├── App.tsx         # 路由与导航
│   │   ├── main.tsx        # 入口
│   │   ├── components/     # 可复用组件
│   │   └── pages/          # 搜索页、导入页
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   ├── spec.md             # 当前设计规格
│   ├── plans.md            # 当前执行计划
│   ├── references.md       # 参考文档
│   └── ops.md              # 运维更新说明
├── scripts/
│   └── import_data.py      # 可选的显式参数 CLI 导入
├── src/
│   ├── config.py           # 数据源和 MySQL 配置
│   ├── db.py               # MySQL 元数据和动态子表操作
│   ├── importer.py         # Excel 预览和导入
│   ├── search.py           # 跨子表搜索
│   └── api.py              # FastAPI 应用入口
└── tests/
    ├── test_search.py
    └── test_api.py
```

# 参考文档

## React
- 用于构建用户界面的 JavaScript 库，本项目用它实现搜索页和导入页。
- 官方文档：https://react.dev/
- 关键概念：
  - 函数组件与 Hooks（`useState`、`useEffect`）
  - 受控组件处理表单输入
  - 条件渲染与列表渲染
- 本项目前端将使用 React 18 + TypeScript。

## Vite
- 下一代前端构建工具，提供极快的开发服务器和热更新。
- 官方文档：https://vitejs.dev/
- 关键配置（来自 Context7 /vitejs/vite）：
  - `server.proxy`：开发时把 `/api` 代理到后端 `http://localhost:4573`
  - `build.outDir`：构建输出目录，默认 `dist`
  - `npm run dev`：启动开发服务器
  - `npm run build`：生产构建
- 创建项目命令参考：
  ```bash
  npm create vite@latest frontend -- --template react-ts
  ```

## FastAPI / Uvicorn
- 用于构建高性能 JSON API 的 Python Web 框架，基于 Starlette 和 Pydantic。
- 官方文档：
  - FastAPI：https://fastapi.tiangolo.com/
  - Uvicorn：https://www.uvicorn.org/
- 关键 API：
  - `FastAPI()`：创建应用实例
  - `@app.get("/path")` / `@app.post("/path")`：定义路由
  - `fastapi.middleware.cors.CORSMiddleware`：跨域配置
  - `fastapi.testclient.TestClient`：同步接口测试
  - `fastapi.staticfiles.StaticFiles`：托管前端构建产物
- 运行方式：
  - 开发：`uvicorn src.api:app --reload --host 0.0.0.0 --port 4573`
  - 生产：`uvicorn src.api:app --host 0.0.0.0 --port 4573`
- 静态文件与 SPA fallback：
  - 先注册所有 `/api/*` 路由，再托管 `frontend/dist/assets` 和 dist 根目录静态文件。
  - React Router 深链接需要显式 fallback：非 API 且未命中静态文件时返回 `frontend/dist/index.html`。

## React Router
- 单页应用路由库，用于在前端切换搜索页和导入页。
- 官方文档：https://reactrouter.com/
- 关键 API：
  - `BrowserRouter` / `Routes` / `Route`
  - `useNavigate` / `Link`

## MySQL 动态子表
- 当前主流程使用 MySQL 8，运行在 Docker Compose 的 `mysql` 服务中。
- 官方文档：https://dev.mysql.com/doc/refman/8.4/en/create-table.html
- 关键约定：
  - `data_tables` 记录用户可见表名、内部安全表名、来源文件、sheet、字段行和字段映射。
  - 子表使用系统生成的内部表名和列名，避免把用户输入直接拼进 SQL 标识符。
  - 搜索时读取 `data_tables.column_mapping_json`，扫描每个登记子表，并把内部列名还原为原始 Excel 字段名展示。
  - 模糊搜索使用 `LIKE '%关键词%'`；精确搜索使用单元格等值匹配。
  - MySQL 标识符使用反引号引用，所有内部标识符仍需先通过 `^[A-Za-z_][A-Za-z0-9_]*$` 校验。

## MySQL + Docker Compose
- 目标架构：MySQL 8 + FastAPI 后端 + React 前端，通过 Docker Compose 同时启动。
- 官方文档：
  - Docker Compose services / `depends_on` / `healthcheck`: https://docs.docker.com/reference/compose-file/services/
  - MySQL Docker Official Image: https://hub.docker.com/_/mysql
  - SQLAlchemy MySQL dialect / PyMySQL URL form: https://docs.sqlalchemy.org/en/20/dialects/mysql.html
- 关键约定：
  - Compose 中使用 `mysql:8.4` 或同一主版本的 MySQL 官方镜像，配置 `MYSQL_ROOT_PASSWORD`、`MYSQL_DATABASE`、`MYSQL_USER`、`MYSQL_PASSWORD` 初始化数据库。
  - `mysql` 服务提供 `healthcheck`，`app` 服务通过 `depends_on: condition: service_healthy` 等数据库可用后启动。
  - Python 侧继续使用 `pymysql.cursors.DictCursor`，参数占位符为 MySQL 的 `%s`。
  - 动态表名和列名仍必须使用内部生成的安全标识符；MySQL 标识符使用反引号包裹，禁止直接使用用户输入。
  - 中文数据和 Excel 字段名使用 `utf8mb4` 字符集与 `utf8mb4_unicode_ci` 或 MySQL 8 默认 utf8mb4 collation。

## uv
- Python 包和环境管理工具，替代 pip/conda。
- 官方文档：https://docs.astral.sh/uv/
- 关键命令：
  - `uv sync`：按 `pyproject.toml` 安装依赖
  - `uv run <command>`：在虚拟环境中运行命令
  - `uv export`：导出 `requirements.txt` 用于离线部署
  - `uv add fastapi[standard]`：添加 FastAPI 并锁定

# 项目历史

## 2026-06-12 Web 上传导入与关键词 2 字段候选

- **Spec summary**: 将 Web 导入入口从服务器/容器内目录选择改为上传 `.xls` / `.xlsx` 文件；搜索时用户输入关键词 1 后，从关键词 1 命中的多表完整行中提取字段名候选，点击候选可填入关键词 2 并继续按同一行 AND 关系搜索。
- **Key decisions**: 上传文件不写入代码目录，直接以 file-like 对象交给 pandas；Web 导入不再列出 `DATA_DIR` 文件，CLI 路径导入保留给自动化；关键词 2 候选来自关键词 1 搜索结果中的 `row` 字段名，按出现频率和首次出现顺序排序；使用 Streamlit 原生按钮区实现候选点击，不引入自定义前端组件。
- **Plan outcome**: fully completed。更新了 `src/importer.py` 的路径/file-like 兼容读取与上传文件名解析，`src/app.py` 的上传导入和关键词 2 候选交互，`src/search.py` 的字段候选提取 helper，补充了 file-like Excel 与候选排序测试，并更新 README、ops、architecture 文档。
- **Verification evidence**: `uv run pytest tests/ -v` 通过，13 个测试全部 pass；`docker compose config` 通过；`docker compose up --build -d` 成功重建并启动；`docker compose ps` 显示 `mysql` healthy 且 `app` running；`curl -I http://127.0.0.1:8501` 返回 HTTP 200；容器内 `extract_field_candidates` smoke 返回 `['型号', '光强']`；浏览器 DOM 检查确认页面标题为「售后参数搜索」，上传入口「上传 Excel 文件」、模式「数据导入 / 搜索」和搜索输入「关键词 1 / 关键词 2」均渲染。
- **Related commits**: not a git repository in this workspace.

## 2026-06-12 MySQL 与 Docker 部署迁移

- **Spec summary**: 将售后参数搜索工具从 SQLite 文件数据库迁移到 MySQL 8，并通过 Docker Compose 部署 Streamlit app 与 MySQL 服务。动态子表、Excel 导入、字段名/内容搜索、双关键词和高亮规则保持不变。
- **Key decisions**: 使用 `pymysql` 保持轻量 DB helper，不引入 ORM；运行时配置改为 `APS_DB_HOST`、`APS_DB_PORT`、`APS_DB_NAME`、`APS_DB_USER`、`APS_DB_PASSWORD`、`APS_DB_CHARSET`；Docker Compose 管理 `mysql` 与 `app` 两个服务，MySQL 数据放入 `mysql_data` volume；不迁移旧 `database.db`，部署后从 Excel 源文件重新导入。
- **Plan outcome**: fully completed。实现了 MySQL 配置和 DB helper、MySQL 语义的导入/搜索/CLI 调用、Dockerfile、docker-compose.yml、.env.example、.dockerignore、README/ops/architecture/reference 文档和 MySQL-compatible 单元测试；额外把 `.env` 加入 `.dockerignore`，避免构建镜像时带入本地密钥。
- **Verification evidence**: `uv run pytest tests/ -v` 通过，11 个测试全部 pass；`docker compose config` 通过；`docker compose up --build -d` 成功构建并启动；`docker compose ps` 显示 `mysql` healthy 且 `app` running；`curl -I http://127.0.0.1:8501` 返回 HTTP 200；`docker compose exec -T app uv run python -c "from src.db import init_db; print(init_db())"` 返回 `True`；临时 smoke 导入 `数据库_副本/设备参数信息汇总.xls` / `Sheet1` 到 MySQL 后导入 10 行，搜索返回 5 条，并清理了临时 smoke 子表。
- **Related commits**: not a git repository in this workspace.

## 2026-06-12 字段名搜索与结果高亮

- **Spec summary**: 在双关键词搜索基础上，将字段名纳入关键词匹配范围，并在结果中高亮命中的字段名和内容片段。两个关键词继续使用同一行 AND 语义，命中位置可以是字段名或单元格内容。
- **Key decisions**: 字段名来自 `column_mapping_json` 中的原始 Excel 字段名，不改数据库结构；模糊搜索对字段名和内容使用包含匹配，精确搜索使用等值匹配；结果增加按关键词拆分的 `field_matches` 与 `value_matches`；UI 改为逐字段 HTML 渲染并先 escape 原始字段名、内容和关键词，防止 Excel 内容执行 HTML。
- **Plan outcome**: fully completed。更新了 `src/search.py`、`src/app.py`、`tests/test_search.py`、`README.md` 和 `docs/ops.md`；未改变导入流程、数据库结构或架构文档。
- **Verification evidence**: `uv run pytest tests/ -v` 通过，14 个测试全部 pass；`.venv/bin/streamlit run src/app.py --server.headless true --server.port 8502` 成功启动；浏览器 DOM 检查确认应用渲染、搜索页签存在，且 `搜索方式`、`关键词 1`、`关键词 2` 均可见。
- **Related commits**: not a git repository in this workspace.

## 2026-06-12 双关键词搜索

- **Spec summary**: 搜索页从单关键词扩展为支持关键词 1 和可选关键词 2，并固定交互顺序为先选择搜索方式，再输入关键词。两个关键词使用同一搜索方式，且按同一行 AND 关系匹配。
- **Key decisions**: 两个关键词必须同时命中同一行，避免 OR 搜索导致结果过宽；关键词 2 为空时保持单关键词行为；`search_records()` 兼容旧的字符串参数并新增列表关键词输入；结果增加 `matched_keywords`，显示每个关键词命中的字段。
- **Plan outcome**: fully completed。更新了 `src/search.py`、`src/app.py`、`tests/test_search.py`、`README.md` 和 `docs/ops.md`；未改变数据库结构和导入流程。
- **Verification evidence**: `uv run pytest tests/ -v` 通过，10 个测试全部 pass；`.venv/bin/streamlit run src/app.py --server.headless true --server.port 8502` 成功启动；浏览器 DOM 检查确认搜索页签存在，且 `搜索方式` 位于 `关键词 1` 和 `关键词 2` 之前。
- **Related commits**: not a git repository in this workspace.

## 2026-06-12 文件级子表导入与搜索

- **Spec summary**: 将售后参数搜索工具从统一 `records` 表改为“一个 Excel 文件中选择一个 sheet，导入为一个数据库子表”的模型。导入由用户在 Streamlit 中命名数据表、预览前三行并选择字段行，搜索按模糊或精确模式跨已登记子表返回完整命中行。
- **Key decisions**: 使用 `data_tables` 元数据表登记用户表名、内部安全表名、来源文件、sheet、字段行和字段映射，避免直接信任用户输入拼接 SQL；每次只导入用户选择的一个 sheet；子表字段全部按 `TEXT` 存储，优先保留 Excel 原貌；搜索通过动态 SQL 扫描登记子表，模糊搜索用 `LIKE`，精确搜索用单元格等值匹配；旧 `records`/FTS5 流程不再作为主 UI 路径。
- **Plan outcome**: fully completed。实现了元数据 schema、安全标识符、选中 sheet 预览与导入、动态子表创建、跨子表搜索、Streamlit 导入/搜索页签、显式参数 CLI、README/运维文档和新测试；额外将 Streamlit 表格宽度参数更新为 `width="stretch"` 以消除启动警告。
- **Verification evidence**: `uv run pytest tests/ -v` 通过，6 个测试全部 pass；用临时库 `/private/tmp/db-plan-verify.db` 从 `数据库_副本/设备参数信息汇总.xls` 的 `Sheet1` 以第 1 行为字段行导入 10 行，模糊搜索 `Pro` 返回 8 条且精确搜索 `Pro 95 S` 返回 1 条完整行；`.venv/bin/streamlit run src/app.py --server.headless true --server.port 8502` 成功启动，首次浏览器 DOM 检查确认标题、导入页签、搜索页签、文件选择和字段行选择均渲染；第二次浏览器复查被浏览器安全策略阻止，未绕过。
- **Related commits**: not a git repository in this workspace.

## 2026-06-11 售后参数搜索工具

**状态**: 已完成

**目标**: 把 `数据库_副本` 中的 9 个 Excel 文件导入 SQLite，为售后工程师提供跨文件参数搜索的 Web 界面。

**方案**: Python + uv + SQLite(FTS5) + Streamlit。每周全量重建数据库，自动备份旧数据库。

**关键决策**:
1. 使用统一的 `records` 表 + 提取维度列，支持跨文件统一搜索和分类筛选。
2. 保留 `raw_json` 原始行数据，避免复杂 Excel 格式在清洗中丢失。
3. 全量重建而不是增量更新，简化更新逻辑。
4. uv 管理环境和依赖，便于内网服务器复现部署。
5. 使用 SQLite FTS5 全文索引，关键词含特殊字符时自动清理保证安全。

**实现文件**:
- `pyproject.toml`
- `src/config.py`, `src/db.py`, `src/importer.py`, `src/extractor.py`, `src/search.py`, `src/app.py`
- `scripts/import_data.py`
- `tests/test_search.py`
- `README.md`, `docs/ops.md`, `docs/references.md`

**验证结果**: `uv run pytest tests/ -v` 5 个测试全部通过；Streamlit AppTest 验证搜索界面正常；导入脚本成功导入 237 条记录。

**实现偏差**:
- 默认数据源路径调整为项目根目录下的 `数据库_副本`。
- 注册证文件表头行识别为索引 2。
- 增加 FTS5 关键词清理和维度提取精确匹配保护。

---

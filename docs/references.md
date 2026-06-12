# 参考文档

## Streamlit
- 用于快速构建数据应用界面，提供 `st.text_input`、`st.selectbox`、`st.dataframe`、`st.expander` 等组件。
- 官方文档：https://docs.streamlit.io/
- 关键 API：
  - `st.text_input(label)`：单行文本输入
  - `st.selectbox(label, options)`：下拉选择
  - `st.dataframe(df)`：交互式表格
  - `st.expander(label)`：可折叠容器，用于展开原始详情

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
- 目标迁移方向：使用 MySQL 8 替代 SQLite 文件数据库，通过 Docker Compose 同时启动数据库服务和 Streamlit 应用服务。
- 官方文档：
  - Docker Compose services / `depends_on` / `healthcheck`: https://docs.docker.com/reference/compose-file/services/
  - MySQL Docker Official Image: https://hub.docker.com/_/mysql
  - SQLAlchemy MySQL dialect / PyMySQL URL form: https://docs.sqlalchemy.org/en/20/dialects/mysql.html
- 关键约定：
  - Compose 中使用 `mysql:8.4` 或同一主版本的 MySQL 官方镜像，配置 `MYSQL_ROOT_PASSWORD`、`MYSQL_DATABASE`、`MYSQL_USER`、`MYSQL_PASSWORD` 初始化数据库。
  - `mysql` 服务提供 `healthcheck`，`app` 服务通过 `depends_on: condition: service_healthy` 等数据库可用后启动。
  - Python 侧推荐使用 `pymysql` 或 SQLAlchemy MySQL dialect；本项目若保持轻量 DB helper，可直接使用 `pymysql.cursors.DictCursor`，参数占位符从 SQLite 的 `?` 改为 MySQL 的 `%s`。
  - 动态表名和列名仍必须使用内部生成的安全标识符；MySQL 标识符使用反引号包裹，禁止直接使用用户输入。
  - 中文数据和 Excel 字段名使用 `utf8mb4` 字符集与 `utf8mb4_unicode_ci` 或 MySQL 8 默认 utf8mb4 collation。

## uv
- Python 包和环境管理工具，替代 pip/conda。
- 官方文档：https://docs.astral.sh/uv/
- 关键命令：
  - `uv sync`：按 `pyproject.toml` 安装依赖
  - `uv run <command>`：在虚拟环境中运行命令
  - `uv export`：导出 `requirements.txt` 用于离线部署

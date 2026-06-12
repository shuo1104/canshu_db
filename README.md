# 售后参数搜索工具

把用户上传的 Excel 文件按“一个文件中的一个 sheet = 一个数据库子表”的方式导入 MySQL，并通过 Streamlit 提供关键词搜索界面。导入时由用户命名数据表、预览前三行、选择哪一行作为数据库字段；搜索时支持字段名和内容的关键词匹配，并输出命中关键词所在行的完整信息。

## 运行方式

推荐使用 Docker Compose 启动完整环境：

```bash
cp .env.example .env
docker compose up --build
```

启动后访问：

```text
http://localhost:8501
```

Compose 会启动两个服务：

- `mysql`：MySQL 8 数据库，数据持久化在 `mysql_data` volume。
- `app`：Streamlit 应用，连接 MySQL，并在 Web 页面接收 Excel 上传。

## 配置

`.env` 中可配置端口和数据库账号：

```env
APP_PORT=8501
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

## 导入数据

SQLite 数据不会自动迁移到 MySQL。部署后请从 Excel 源文件重新导入：

1. 打开 Web 界面的「数据导入」模式。
2. 上传一个 `.xls` 或 `.xlsx` 文件。
3. 如果文件里有多个 sheet，选择其中一个作为本次导入的子表。
4. 输入数据表名称。
5. 查看前三行预览。
6. 选择哪一行作为数据库字段。
7. 点击「创建数据表并导入」。

如果同名数据表已存在，可以勾选「如果同名数据表已存在，则替换它」后重新导入。

## 搜索数据

在 Web 界面的「搜索」模式中：

- 输入「关键词 1」。
- 系统会先用关键词 1 搜索，并从命中结果的完整行里提取字段名候选。
- 可以手动输入「关键词 2」，也可以点击字段候选把它填入关键词 2。
- 每个关键词只要出现在同一行的任意字段名或单元格内容中，就返回整行信息。
- 同时输入两个关键词时，两个关键词是 AND 关系：同一行必须同时命中关键词 1 和关键词 2。

搜索结果会显示数据表名称、来源文件、sheet 名称、命中字段、关键词命中字段和完整行内容，并高亮命中的字段名和内容片段。

## CLI 导入

主要导入方式是 Web 上传。需要自动化时，可以在 app 环境中显式指定文件、sheet、表名和字段行；这种方式可继续使用挂载到容器内的 `数据库_副本/`：

```bash
docker compose exec app uv run python scripts/import_data.py \
  --file 数据库_副本/设备参数信息汇总.xls \
  --sheet Sheet1 \
  --table-name 设备参数 \
  --header-row 0
```

`--header-row` 使用从 0 开始的行号：`0` 表示第一行，`1` 表示第二行，`2` 表示第三行。加 `--replace` 可替换同名数据表。

## 本地开发

如果不用 Docker 运行 app，需要先提供一个可访问的 MySQL，并设置连接环境变量：

```bash
APS_DB_HOST=127.0.0.1 \
APS_DB_PORT=3306 \
APS_DB_NAME=aftersales \
APS_DB_USER=aftersales \
APS_DB_PASSWORD=aftersales_password \
uv run streamlit run src/app.py
```

运行测试：

```bash
uv run pytest tests/ -v
```

## 项目结构

```text
.
├── 数据库_副本/             # 可选 CLI Excel 数据源目录
├── docker-compose.yml      # MySQL + Streamlit 编排
├── Dockerfile              # Streamlit 应用镜像
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
│   └── app.py              # Streamlit 界面
└── tests/
    └── test_search.py
```

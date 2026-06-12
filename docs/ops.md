# 运维更新说明

## 部署

首次部署：

```bash
cp .env.example .env
docker compose up --build -d
```

查看服务状态：

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f mysql
```

默认访问地址：

```text
http://localhost:8501
```

## 数据持久化

MySQL 数据保存在 Docker volume `mysql_data` 中。普通重启不会丢数据：

```bash
docker compose restart
```

停止服务但保留数据：

```bash
docker compose down
```

删除数据库数据会清空所有导入结果，执行前需要确认：

```bash
docker compose down -v
```

## 定期更新流程

数据源新增 Excel 文件后，优先通过 Web 界面上传导入。当前模型是“一个 Excel 文件中选择一个 sheet，导入为一个数据库子表”。

### 1. 启动 Web 工具

```bash
docker compose up -d
```

### 2. 导入一个子表

在「数据导入」模式中：

1. 上传 `.xls` 或 `.xlsx` 文件。
2. 选择本次要导入的一个 sheet。
3. 输入数据表名称。
4. 根据前三行预览选择字段行。
5. 点击「创建数据表并导入」。

如果需要导入同一个 Excel 文件里的多个 sheet，请重复以上步骤，并为每个 sheet 使用不同的数据表名称。

SQLite 旧数据库不会自动迁移；部署 MySQL 后请从 Excel 源文件重新导入。

### 3. 验证导入结果

在「搜索」模式中输入「关键词 1」，确认页面能返回完整行信息并高亮命中内容。页面会从关键词 1 的命中结果中提取字段名候选，可以点击候选填入「关键词 2」继续缩小结果。关键词会同时搜索字段名和单元格内容；两个关键词是同一行 AND 匹配。

也可以进入 MySQL 查看已登记的数据表：

```bash
docker compose exec mysql mysql \
  -u"$APS_DB_USER" -p"$APS_DB_PASSWORD" "$APS_DB_NAME" \
  -e "SELECT display_name, source_file, sheet_name FROM data_tables;"
```

## 可选 CLI 导入

自动化场景可以使用 CLI，但必须显式指定文件、sheet、表名和字段行：

```bash
docker compose exec app uv run python scripts/import_data.py \
  --file 数据库_副本/设备参数信息汇总.xls \
  --sheet Sheet1 \
  --table-name 设备参数 \
  --header-row 0
```

`--header-row` 使用从 0 开始的行号。加 `--replace` 可以替换同名数据表。

## 回滚

如果新版本 app 有问题但 MySQL 数据可保留：

```bash
docker compose down
```

然后回退代码或镜像，再重新启动：

```bash
docker compose up --build -d
```

如果某个子表导入有问题，在「数据导入」里用同名数据表勾选替换后重新导入。

## 故障排查

### app 连接不上 MySQL

- 检查 `docker compose ps` 中 `mysql` 是否 healthy。
- 检查 `.env` 中 `APS_DB_NAME`、`APS_DB_USER`、`APS_DB_PASSWORD` 是否和 Compose 配置一致。
- 查看 `docker compose logs mysql` 和 `docker compose logs app`。

### 无法上传或读取 Excel

- 确认文件后缀是 `.xls` 或 `.xlsx`。
- 确认文件不是加密工作簿，且目标 sheet 能被 pandas/openpyxl 读取。
- 如果上传后 sheet 列表或前三行预览报错，查看 `docker compose logs app` 中的具体异常。

### 导入失败：数据表名称已存在

- 换一个数据表名称。
- 或勾选「如果同名数据表已存在，则替换它」后重新导入。

### 搜索无结果

- 确认至少导入过一个数据表。
- Web 搜索适合输入部分关键词，会同时匹配字段名和单元格内容。
- 如果输入了两个关键词，确认这两个关键词确实出现在同一行中；需要扩大范围时先清空关键词 2。
- 如果关键词 2 字段候选为空，说明关键词 1 没有命中任何已导入行，或命中行没有可展示字段。

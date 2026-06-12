# 交接说明

---

后端功能主要分为数据导入（小程序不负责此功能）、搜索（关键词 1、关键词 2 候选和关键词 2）和返回数据高亮。搜索范围包含数据表名称、字段名和单元格内容。

## 1. 服务地址与端口

后端服务端口固定为：

```text
4573
```

局域网访问地址：

```text
http://<服务器IP>:4573
```

用途区分：

| 地址                          | 用途                 |
| --------------------------- | ------------------ |
| `http://<服务器IP>:4573/`      | React 管理页面，包含搜索页   |
| `http://<服务器IP>:4573/api/*` | 小程序和前端调用的 JSON API |
| `http://<服务器IP>:4573/docs`  | FastAPI 自动接口文档     |

后端默认已开启 CORS，允许前端或小程序开发环境访问。生产如需收紧，可通过 `ALLOWED_ORIGINS` 环境变量配置。

---

## 2. 需要对接的接口

| 接口                       | 方法  | 用途                   |
| ------------------------ | --- | -------------------- |
| `/api/health`            | GET | 健康检查                 |
| `/api/search`            | GET | 搜索设备参数               |
| `/api/search/candidates` | GET | 根据关键词 1 返回关键词 2 候选字段 |

小程序只需要以上三个接口。

---

## 3. 接口详情

### 3.1 健康检查

```http
GET http://<服务器IP>:4573/api/health
```

返回：

```json
{"status": "ok"}
```

---

### 3.2 搜索

```http
GET http://<服务器IP>:4573/api/search?keyword1=Pro2&keyword2=UV
```

参数：

| 字段         | 必填  | 说明                    |
| ---------- | --- | --------------------- |
| `keyword1` | 是   | 第一个关键词                |
| `keyword2` | 否   | 第二个关键词                |
| `limit`    | 否   | 最多返回条数，默认 100，最大 1000 |

返回示例：

```json
[
  {
    "table_id": 1,
    "display_name": "设备参数",
    "table_name": "dt_shebei_canshu_a1b2c3d4e5",
    "source_file": "设备参数信息汇总.xls",
    "sheet_name": "Sheet1",
    "row_id": 7,
    "matched_columns": ["设备型号", "光源"],
    "matched_keywords": {
      "Pro2": {"table_matches": [], "field_matches": [], "value_matches": ["设备型号"]},
      "UV": {"table_matches": [], "field_matches": [], "value_matches": ["光源"]}
    },
    "row": {
      "设备型号": "Pro2",
      "光源": "385nm UV-LED",
      "功率": "400W"
    }
  }
]
```

搜索规则：

- `fuzzy`：数据表名称、字段名或单元格内容包含关键词即可。
- `exact`：数据表名称、字段名或单元格内容等于关键词。
- 大小写不敏感，和 MySQL 当前 `utf8mb4_unicode_ci` 规则保持一致。
- `keyword1` 和 `keyword2` 是 AND 关系：同一行必须同时命中两个关键词。
- 当一个关键词是字段名、另一个关键词是值时，后端会在该字段内筛这个值。
- `row` 是完整行数据，`matched_columns` 是命中的字段名，可用于前端高亮。

---

### 3.3 关键词 2 候选字段

```http
GET http://<服务器IP>:4573/api/search/candidates?keyword1=Pro2
```

参数：

| 字段               | 必填  | 说明                   |
| ---------------- | --- | -------------------- |
| `keyword1`       | 是   | 第一个关键词               |
| `max_candidates` | 否   | 最多返回候选数，默认 50，最大 200 |

返回示例：

```json
["设备型号", "光源", "功率", "XY 分辨率/精度"]
```

用途：用户输入 `keyword1` 后，小程序可以展示候选字段按钮；点击候选字段后，把该字段填入 `keyword2` 再调用 `/api/search`。

---

## 4. 前端页面开发说明

当前仓库已有 React 管理页面：

| 页面      | 路由  | 文件                                  |
| ------- | --- | ----------------------------------- |
| 搜索页     | `/` | `frontend/src/pages/SearchPage.tsx` |
| API 客户端 | -   | `frontend/src/api.ts`               |

前端调用约定：

- 页面里统一调用 `frontend/src/api.ts`。
- API base 为 `/api`。
- 开发环境由 Vite proxy 转发到 `http://localhost:4573`。
- 生产环境由 FastAPI 直接托管 `frontend/dist`，不需要单独部署前端服务。

若只做小程序页面，可以参考 React 搜索页的数据结构和交互，不需要改 React 管理页。

---

## 5. 页面映射建议

| 小程序页面  | 接口                                     | 展示重点                                                        |
| ------ | -------------------------------------- | ----------------------------------------------------------- |
| 搜索首页   | `/api/search/candidates`、`/api/search` | 关键词输入、候选字段、结果数量                                             |
| 搜索结果列表 | `/api/search`                          | `display_name`、`source_file`、`sheet_name`、`matched_columns` |
| 搜索结果详情 | `/api/search` 返回的单条 `row`              | 完整字段和值，命中字段高亮                                               |

高亮建议：

- 数据表名称在 `matched_keywords[*].table_matches` 中时，结果标题可高亮。
- 字段名在 `matched_columns` 中时，整行字段可高亮。
- 若需要更细的关键词命中信息，可读取 `matched_keywords` 中的 `table_matches`、`field_matches`、`value_matches`。

---

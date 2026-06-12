# Architecture

## Main Features

- Interactive Excel import: users upload one Excel file, choose one sheet, enter a table name, and choose one of the first three rows as the database field row.
- Dynamic MySQL storage: each import creates one child table with generated safe column names and records its original metadata in `data_tables`.
- Cross-table search: keyword search scans registered child tables and returns the complete matched row with source context and highlighted matches.
- Keyword field candidates: keyword 1 results are used to extract row field names that can be selected as keyword 2.
- Docker deployment: Docker Compose runs a MySQL service and a FastAPI app service that serves the React build with persistent MySQL volume storage.

## Main Code Modules

- `src/config.py`: project paths and MySQL environment-variable configuration.
- `src/db.py`: MySQL connection handling, `data_tables` metadata schema, safe SQL identifier helpers, child-table creation, row insertion, and table registration.
- `src/importer.py`: Excel path/file-like reading, sheet listing, first-three-row preview, header-to-column mapping, and selected-sheet import orchestration.
- `src/search.py`: registered table discovery, search over every child table, and field-candidate extraction from search results.
- `src/api.py`: FastAPI routes for search, candidate fields, Excel preview/import, and serving the React frontend.
- `frontend/src`: React pages and API client for upload import and search workflows.
- `scripts/import_data.py`: optional explicit-argument CLI import path for automation.
- `docker-compose.yml`: MySQL + FastAPI service orchestration.
- `Dockerfile`: multi-stage React build and FastAPI runtime container.

## Data Flow

```text
Browser-uploaded Excel file + selected sheet
    -> frontend React import page
    -> src.api import endpoints
    -> src.importer preview/header selection
    -> src.db MySQL child table + data_tables metadata
    -> src.search dynamic table scan
    -> src.search keyword 2 field candidates
    -> frontend React highlighted result display
```

## Deployment Flow

```text
browser
    -> app container (FastAPI :4573 serving React dist)
    -> mysql container (:3306)
    -> mysql_data Docker volume
```

## Storage Model

`data_tables` is the source of truth for user-visible table metadata. Child tables use generated internal names such as `dt_<slug>_<hash>` and generated columns such as `c001`; the original Excel field names are preserved in `column_mapping_json` and restored for search result display.

MySQL uses `utf8mb4` and stores every imported Excel cell as `TEXT` to preserve source values without type inference.

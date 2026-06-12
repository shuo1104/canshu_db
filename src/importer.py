"""Excel preview and selected-sheet import helpers."""
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd

from src.config import DATA_DIR, DB_CONFIG, MySQLConfig
from src.db import (
    create_child_table,
    delete_data_table,
    drop_child_table,
    get_connection,
    get_data_table_by_display_name,
    init_db,
    insert_child_rows,
    make_column_mapping,
    make_table_name,
    register_data_table,
)

ExcelSource = str | Path | BinaryIO


def clean_text(value: Any) -> str:
    """Normalize a cell value to searchable text."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def list_excel_files(data_dir: Path = DATA_DIR) -> list[Path]:
    if not data_dir.exists():
        raise FileNotFoundError(f"数据源目录不存在: {data_dir}")
    return [
        path
        for path in sorted(data_dir.iterdir())
        if path.is_file() and path.suffix.lower() in (".xls", ".xlsx")
    ]


def _prepare_excel_source(excel_source: ExcelSource) -> ExcelSource | str:
    if hasattr(excel_source, "seek"):
        excel_source.seek(0)
        return excel_source
    if isinstance(excel_source, Path):
        return str(excel_source)
    return excel_source


def resolve_source_file_name(
    excel_source: ExcelSource,
    source_file_name: str | None = None,
) -> str:
    if source_file_name:
        return Path(source_file_name).name
    if isinstance(excel_source, (str, Path)):
        return Path(excel_source).name
    object_name = getattr(excel_source, "name", None)
    if object_name:
        return Path(str(object_name)).name
    return "uploaded.xlsx"


def list_sheet_names(excel_source: ExcelSource) -> list[str]:
    return pd.ExcelFile(_prepare_excel_source(excel_source)).sheet_names


def read_sheet_rows(excel_source: ExcelSource, sheet_name: str) -> list[list[str]]:
    df = pd.read_excel(
        _prepare_excel_source(excel_source),
        sheet_name=sheet_name,
        header=None,
        dtype=object,
        keep_default_na=True,
    )
    if df.empty:
        return []
    return [[clean_text(value) for value in row] for row in df.values.tolist()]


def get_sheet_preview(
    excel_source: ExcelSource,
    sheet_name: str,
    preview_rows: int = 3,
) -> list[list[str]]:
    return read_sheet_rows(excel_source, sheet_name)[:preview_rows]


def build_column_mapping_from_header(header_values: list[str]) -> list[dict]:
    return make_column_mapping(header_values)


def get_data_rows_below_header(
    excel_source: ExcelSource,
    sheet_name: str,
    header_row_index: int,
) -> tuple[list[str], list[list[str]]]:
    rows = read_sheet_rows(excel_source, sheet_name)
    if header_row_index < 0 or header_row_index >= len(rows):
        raise ValueError("字段行超出表格范围")

    header = rows[header_row_index]
    data_rows = []
    for row in rows[header_row_index + 1 :]:
        if any(cell.strip() for cell in row):
            data_rows.append(row)
    return header, data_rows


def import_selected_sheet(
    file_path: ExcelSource,
    sheet_name: str,
    display_name: str,
    header_row_index: int,
    db_config: MySQLConfig = DB_CONFIG,
    replace_existing: bool = False,
    source_file_name: str | None = None,
) -> dict:
    display_name = display_name.strip()
    if not display_name:
        raise ValueError("数据表名称不能为空")

    init_db(db_config)
    header, data_rows = get_data_rows_below_header(file_path, sheet_name, header_row_index)
    column_mapping = build_column_mapping_from_header(header)
    if not column_mapping:
        raise ValueError("字段行没有可用列")

    resolved_source_file = resolve_source_file_name(file_path, source_file_name)
    table_name = make_table_name(display_name, resolved_source_file, sheet_name)

    with get_connection(db_config) as conn:
        existing = get_data_table_by_display_name(conn, display_name)
        try:
            if existing:
                if not replace_existing:
                    raise ValueError(f"数据表名称已存在: {display_name}")
                drop_child_table(conn, existing["table_name"])
                delete_data_table(conn, existing["table_name"])

            create_child_table(conn, table_name, column_mapping)
            inserted = insert_child_rows(conn, table_name, column_mapping, data_rows)
            register_data_table(
                conn=conn,
                display_name=display_name,
                table_name=table_name,
                source_file=resolved_source_file,
                sheet_name=sheet_name,
                header_row_index=header_row_index,
                column_mapping=column_mapping,
            )
        except Exception:
            drop_child_table(conn, table_name)
            conn.rollback()
            raise
        else:
            conn.commit()

    return {
        "display_name": display_name,
        "table_name": table_name,
        "source_file": resolved_source_file,
        "sheet_name": sheet_name,
        "header_row_index": header_row_index,
        "columns": column_mapping,
        "row_count": inserted,
    }

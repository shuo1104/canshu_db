"""MySQL schema, safe identifiers, and dynamic child-table helpers."""
import hashlib
import json
import re
from contextlib import contextmanager
from typing import Iterable

from src.config import DB_CONFIG, MySQLConfig


SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


CREATE_DATA_TABLES_TABLE = """
CREATE TABLE IF NOT EXISTS `data_tables` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `display_name` VARCHAR(255) NOT NULL UNIQUE,
    `table_name` VARCHAR(128) NOT NULL UNIQUE,
    `source_file` VARCHAR(512) NOT NULL,
    `sheet_name` VARCHAR(255) NOT NULL,
    `header_row_index` INT NOT NULL,
    `column_mapping_json` JSON NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"""


@contextmanager
def get_connection(config: MySQLConfig = DB_CONFIG):
    """Open a MySQL connection with dict rows."""
    import pymysql
    import pymysql.cursors

    conn = pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        charset=config.charset,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    try:
        yield conn
    finally:
        conn.close()


def init_db(config: MySQLConfig = DB_CONFIG) -> bool:
    """Initialize database metadata tables."""
    with get_connection(config) as conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_DATA_TABLES_TABLE)
        conn.commit()
    return True


def quote_identifier(identifier: str) -> str:
    """Quote a MySQL identifier after validating it is internally generated."""
    if not SAFE_IDENTIFIER_RE.fullmatch(identifier):
        raise ValueError(f"Unsafe SQL identifier: {identifier}")
    return f"`{identifier}`"


def make_table_name(display_name: str, source_file: str, sheet_name: str) -> str:
    """Create a stable, safe internal table name from user-visible inputs."""
    base = re.sub(r"[^A-Za-z0-9]+", "_", display_name).strip("_").lower()
    if not base:
        base = "table"
    if base[0].isdigit():
        base = f"t_{base}"
    digest = hashlib.sha1(
        f"{display_name}\0{source_file}\0{sheet_name}".encode("utf-8")
    ).hexdigest()[:10]
    return f"dt_{base[:36]}_{digest}"


def make_column_mapping(headers: Iterable[str]) -> list[dict]:
    """Map original Excel headers to safe internal column names."""
    mapping = []
    seen_labels: dict[str, int] = {}
    for index, header in enumerate(headers, start=1):
        label = str(header).strip()
        if not label:
            label = f"未命名列{index}"

        count = seen_labels.get(label, 0) + 1
        seen_labels[label] = count
        display_label = label if count == 1 else f"{label}_{count}"

        mapping.append(
            {
                "original": display_label,
                "column": f"c{index:03d}",
                "source_index": index - 1,
            }
        )
    return mapping


def get_data_tables(conn) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, display_name, table_name, source_file, sheet_name,
                   header_row_index, column_mapping_json, created_at
            FROM data_tables
            ORDER BY created_at DESC, id DESC
            """
        )
        return list(cursor.fetchall())


def get_data_table_by_display_name(conn, display_name: str) -> dict | None:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM data_tables WHERE display_name = %s", (display_name,)
        )
        return cursor.fetchone()


def decode_column_mapping(table_meta: dict) -> list[dict]:
    value = table_meta["column_mapping_json"]
    if isinstance(value, str):
        return json.loads(value)
    return value


def drop_child_table(conn, table_name: str) -> None:
    with conn.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {quote_identifier(table_name)}")


def delete_data_table(conn, table_name: str) -> None:
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM data_tables WHERE table_name = %s", (table_name,))


def create_child_table(
    conn,
    table_name: str,
    column_mapping: list[dict],
) -> None:
    columns_sql = []
    for column in column_mapping:
        columns_sql.append(f"{quote_identifier(column['column'])} TEXT")
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE {quote_identifier(table_name)} (
                `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                {", ".join(columns_sql)}
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """
        )


def insert_child_rows(
    conn,
    table_name: str,
    column_mapping: list[dict],
    rows: list[list[str]],
) -> int:
    columns = [column["column"] for column in column_mapping]
    placeholders = ", ".join(["%s"] * len(columns))
    columns_sql = ", ".join(quote_identifier(column) for column in columns)
    sql = (
        f"INSERT INTO {quote_identifier(table_name)} "
        f"({columns_sql}) VALUES ({placeholders})"
    )

    values = []
    for row in rows:
        values.append(
            [
                row[column["source_index"]] if column["source_index"] < len(row) else ""
                for column in column_mapping
            ]
        )

    if values:
        with conn.cursor() as cursor:
            cursor.executemany(sql, values)
    return len(values)


def register_data_table(
    conn,
    display_name: str,
    table_name: str,
    source_file: str,
    sheet_name: str,
    header_row_index: int,
    column_mapping: list[dict],
) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO data_tables (
                display_name, table_name, source_file, sheet_name,
                header_row_index, column_mapping_json
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                display_name,
                table_name,
                source_file,
                sheet_name,
                header_row_index,
                json.dumps(column_mapping, ensure_ascii=False),
            ),
        )

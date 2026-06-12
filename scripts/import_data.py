"""Optional non-interactive MySQL import entry point.

Primary import is the Streamlit UI:
    docker compose up --build

CLI example:
    uv run python scripts/import_data.py \
        --file 数据库_副本/设备参数信息汇总.xls \
        --sheet Sheet1 \
        --table-name 设备参数 \
        --header-row 0
"""
import argparse
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.importer import import_selected_sheet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="导入一个 Excel 文件中的一个 sheet 为一个 MySQL 数据库子表。"
    )
    parser.add_argument("--file", type=Path, help="Excel 文件路径")
    parser.add_argument("--sheet", help="要导入的 sheet 名称")
    parser.add_argument("--table-name", help="用户可见的数据表名称")
    parser.add_argument(
        "--header-row",
        type=int,
        help="字段行索引，0 表示第一行，1 表示第二行，2 表示第三行",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="如果同名数据表已存在，则替换它",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    required = [args.file, args.sheet, args.table_name, args.header_row]
    if any(value is None for value in required):
        print("主要导入方式是 Web 界面。")
        print("请运行: docker compose up --build")
        print("如需 CLI 导入，请同时提供 --file --sheet --table-name --header-row。")
        return 0

    try:
        result = import_selected_sheet(
            file_path=args.file,
            sheet_name=args.sheet,
            display_name=args.table_name,
            header_row_index=args.header_row,
            replace_existing=args.replace,
        )
    except Exception as exc:
        print(f"导入失败: {exc}")
        return 1

    print(
        f"成功导入 {result['row_count']} 行到数据表 {result['display_name']} "
        f"({result['source_file']} / {result['sheet_name']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

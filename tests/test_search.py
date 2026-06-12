"""MySQL-compatible import/search unit tests."""
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from src.app import highlight_text
from src.db import make_column_mapping, make_table_name, quote_identifier
from src.importer import (
    get_data_rows_below_header,
    get_sheet_preview,
    list_sheet_names,
    resolve_source_file_name,
)
from src.search import (
    build_keyword_conditions,
    extract_field_candidates,
    row_to_search_result,
    search_records,
)


def write_workbook(target) -> None:
    with pd.ExcelWriter(target, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                ["标题", "", ""],
                ["型号", "型号", ""],
                ["Pro2", "设备参数", "光强A<script>"],
                ["ProS", "材料参数", "光强B"],
                ["Ultra", "设备参数", "光强C"],
            ]
        ).to_excel(writer, index=False, header=False, sheet_name="设备")
        pd.DataFrame([["忽略"], ["不导入"]]).to_excel(
            writer, index=False, header=False, sheet_name="其他"
        )


def make_workbook(path: Path) -> None:
    write_workbook(path)


def make_workbook_stream(name: str = "uploaded.xlsx") -> BytesIO:
    stream = BytesIO()
    write_workbook(stream)
    stream.name = name
    stream.seek(0)
    return stream


def sample_mapping() -> list[dict]:
    return make_column_mapping(["型号", "型号", ""])


def sample_table_meta() -> dict:
    return {
        "id": 7,
        "display_name": "设备参数",
        "table_name": "dt_device",
        "source_file": "sample.xlsx",
        "sheet_name": "设备",
    }


def test_preview_and_sheet_selection(tmp_path):
    workbook = tmp_path / "sample.xlsx"
    make_workbook(workbook)

    assert list_sheet_names(workbook) == ["设备", "其他"]
    preview = get_sheet_preview(workbook, "设备")

    assert preview == [
        ["标题", "", ""],
        ["型号", "型号", ""],
        ["Pro2", "设备参数", "光强A<script>"],
    ]


def test_file_like_preview_and_sheet_selection_can_be_reused():
    workbook = make_workbook_stream("web-upload.xlsx")

    assert list_sheet_names(workbook) == ["设备", "其他"]
    preview = get_sheet_preview(workbook, "设备")
    header, rows = get_data_rows_below_header(workbook, "设备", 1)

    assert preview[0] == ["标题", "", ""]
    assert header == ["型号", "型号", ""]
    assert rows[0] == ["Pro2", "设备参数", "光强A<script>"]
    assert resolve_source_file_name(workbook) == "web-upload.xlsx"
    assert resolve_source_file_name(workbook, "用户上传.xlsx") == "用户上传.xlsx"


def test_rows_below_selected_header_drop_empty_rows(tmp_path):
    workbook = tmp_path / "sample.xlsx"
    make_workbook(workbook)

    header, rows = get_data_rows_below_header(workbook, "设备", 1)

    assert header == ["型号", "型号", ""]
    assert len(rows) == 3
    assert rows[0] == ["Pro2", "设备参数", "光强A<script>"]


def test_column_mapping_handles_duplicate_and_empty_headers():
    mapping = sample_mapping()

    assert mapping == [
        {"original": "型号", "column": "c001", "source_index": 0},
        {"original": "型号_2", "column": "c002", "source_index": 1},
        {"original": "未命名列3", "column": "c003", "source_index": 2},
    ]


def test_mysql_identifier_quoting_and_table_name_safety():
    table_name = make_table_name("设备 参数 !", "sample.xlsx", "设备")

    assert table_name.startswith("dt_")
    assert "!" not in table_name
    assert quote_identifier(table_name) == f"`{table_name}`"

    with pytest.raises(ValueError):
        quote_identifier("bad`; DROP TABLE data_tables; --")


def test_build_keyword_conditions_uses_mysql_placeholders_for_values():
    where_clause, params, field_matches = build_keyword_conditions(
        sample_mapping(), ["Pro", "光强A"], "fuzzy"
    )

    assert where_clause == (
        "(`c001` LIKE %s OR `c002` LIKE %s OR `c003` LIKE %s) AND "
        "(`c001` LIKE %s OR `c002` LIKE %s OR `c003` LIKE %s)"
    )
    assert params == ["%Pro%", "%Pro%", "%Pro%", "%光强A%", "%光强A%", "%光强A%"]
    assert field_matches == {"Pro": [], "光强A": []}


def test_field_name_match_short_circuits_that_keyword():
    where_clause, params, field_matches = build_keyword_conditions(
        sample_mapping(), ["型号", "Pro2"], "fuzzy"
    )

    assert where_clause == "1=1 AND (`c001` LIKE %s OR `c002` LIKE %s OR `c003` LIKE %s)"
    assert params == ["%Pro2%", "%Pro2%", "%Pro2%"]
    assert field_matches == {"型号": ["型号", "型号_2"], "Pro2": []}


def test_exact_field_name_match_uses_equality_semantics():
    where_clause, params, field_matches = build_keyword_conditions(
        sample_mapping(), ["型号"], "exact"
    )

    assert where_clause == "1=1"
    assert params == []
    assert field_matches == {"型号": ["型号"]}


def test_row_to_search_result_reports_field_and_value_matches():
    mapping = sample_mapping()
    _, _, field_matches = build_keyword_conditions(mapping, ["型号", "Pro2"], "fuzzy")

    result = row_to_search_result(
        table_meta=sample_table_meta(),
        mapping=mapping,
        row_dict={"id": 1, "c001": "Pro2", "c002": "设备参数", "c003": "光强A"},
        keywords=["型号", "Pro2"],
        mode="fuzzy",
        field_matches_by_keyword=field_matches,
    )

    assert result["row"] == {
        "型号": "Pro2",
        "型号_2": "设备参数",
        "未命名列3": "光强A",
    }
    assert result["matched_keywords"] == {
        "型号": {"field_matches": ["型号", "型号_2"], "value_matches": []},
        "Pro2": {"field_matches": [], "value_matches": ["型号"]},
    }


def test_extract_field_candidates_orders_by_frequency_then_first_seen():
    results = [
        {"row": {"型号": "Pro2", "光强": "A", "材料": "铝"}},
        {"row": {"型号": "ProS", "材料": "钢", "电压": "220V"}},
        {"row": {"型号": "Ultra", "光强": "C", "备注": ""}},
    ]

    assert extract_field_candidates(results) == ["型号", "光强", "材料", "电压", "备注"]
    assert extract_field_candidates(results, max_candidates=3) == ["型号", "光强", "材料"]


def test_search_records_rejects_invalid_mode_before_connecting():
    with pytest.raises(ValueError, match="mode must be"):
        search_records("Pro2", mode="contains")


def test_search_records_empty_keyword_returns_without_connecting():
    assert search_records(["", "  "], mode="fuzzy") == []


def test_highlight_text_escapes_html_before_marking():
    highlighted = highlight_text("光强A<script>", ["光强A"], "fuzzy")

    assert "<script>" not in highlighted
    assert "&lt;script&gt;" in highlighted
    assert '<mark class="search-hit">光强A</mark>' in highlighted

"""Streamlit import and search interface."""
import html
import re
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import streamlit as st

from src.importer import (
    get_sheet_preview,
    import_selected_sheet,
    list_sheet_names,
)
from src.search import extract_field_candidates, list_registered_tables, search_records


LOGO_PATH = "src/assets/logo.png"

st.set_page_config(
    page_title="售后参数搜索",
    page_icon=LOGO_PATH,
    layout="wide",
    initial_sidebar_state="expanded",
)
st.logo(LOGO_PATH)


def _preview_dataframe(preview_rows: list[list[str]]) -> pd.DataFrame:
    width = max((len(row) for row in preview_rows), default=0)
    normalized = [row + [""] * (width - len(row)) for row in preview_rows]
    index = [f"第 {i + 1} 行" for i in range(len(normalized))]
    columns = [f"列 {i + 1}" for i in range(width)]
    return pd.DataFrame(normalized, index=index, columns=columns)


def _active_keywords(keywords: list[str]) -> list[str]:
    return [keyword.strip() for keyword in keywords if keyword and keyword.strip()]


def highlight_text(text: object, keywords: list[str], mode: str) -> str:
    """Return escaped HTML with matched keyword text wrapped in mark tags."""
    raw_text = "" if text is None else str(text)
    active_keywords = _active_keywords(keywords)
    if not raw_text or not active_keywords:
        return html.escape(raw_text)

    if mode == "exact":
        escaped_text = html.escape(raw_text)
        if raw_text in active_keywords:
            return f'<mark class="search-hit">{escaped_text}</mark>'
        return escaped_text

    pattern = re.compile(
        "|".join(re.escape(keyword) for keyword in sorted(active_keywords, key=len, reverse=True))
    )
    parts = []
    last_index = 0
    for match in pattern.finditer(raw_text):
        if match.start() > last_index:
            parts.append(html.escape(raw_text[last_index : match.start()]))
        parts.append(
            f'<mark class="search-hit">{html.escape(match.group(0))}</mark>'
        )
        last_index = match.end()
    if last_index < len(raw_text):
        parts.append(html.escape(raw_text[last_index:]))
    return "".join(parts)


def _is_matched(text: object, keywords: list[str], mode: str) -> bool:
    raw_text = "" if text is None else str(text)
    active_keywords = _active_keywords(keywords)
    if not raw_text or not active_keywords:
        return False
    if mode == "exact":
        return raw_text in active_keywords or any(kw in raw_text for kw in active_keywords)
    pattern = re.compile(
        "|".join(re.escape(keyword) for keyword in active_keywords)
    )
    return bool(pattern.search(raw_text))


def render_highlighted_row(row: dict, keywords: list[str], mode: str) -> None:
    rows_html = []
    for field_name, value in row.items():
        if not str(value).strip():
            continue
        highlighted_field = highlight_text(field_name, keywords, mode)
        highlighted_value = highlight_text(value, keywords, mode)
        is_matched = _is_matched(field_name, keywords, mode) or _is_matched(
            value, keywords, mode
        )
        row_class = "search-row matched-row" if is_matched else "search-row"
        rows_html.append(
            f'<tr class="{row_class}">'
            f'<td class="search-field">{highlighted_field}</td>'
            f'<td class="search-value">{highlighted_value}</td>'
            "</tr>"
        )

    if not rows_html:
        return

    st.markdown(
        """
        <style>
        .result-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
        }
        .result-table td {
            border-top: 1px solid rgba(49, 51, 63, 0.12);
            padding: 0.45rem 0.5rem;
            vertical-align: top;
        }
        .result-table tr:first-child td {
            border-top: none;
        }
        .result-table .search-field {
            font-weight: 650;
            width: 12rem;
            white-space: nowrap;
        }
        .result-table .matched-row {
            background: #fff0f1;
        }
        .search-hit {
            background: #ffd4d6;
            color: inherit;
            border-radius: 0.2rem;
            padding: 0.05rem 0.12rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<table class="result-table">{ "".join(rows_html) }</table>',
        unsafe_allow_html=True,
    )


def render_import_tab() -> None:
    render_tables_expander()
    uploaded_file = st.file_uploader("上传 Excel 文件", type=["xls", "xlsx"])
    if uploaded_file is None:
        st.info("上传一个 Excel 文件后，可以选择子表、字段行并创建数据库表。")
        return

    selected_file_name = uploaded_file.name

    try:
        sheet_names = list_sheet_names(uploaded_file)
    except Exception as exc:
        st.error(f"读取工作表失败: {exc}")
        return

    selected_sheet = st.selectbox("选择一个子表", sheet_names)
    display_name = st.text_input("数据表名称", value=Path(selected_file_name).stem)

    try:
        preview_rows = get_sheet_preview(uploaded_file, selected_sheet)
    except Exception as exc:
        st.error(f"读取前三行失败: {exc}")
        return

    if not preview_rows:
        st.warning("这个子表没有可导入的数据。")
        return

    st.dataframe(_preview_dataframe(preview_rows), width="stretch")
    row_options = list(range(len(preview_rows)))
    header_row_index = st.radio(
        "选择哪一行为数据库字段",
        row_options,
        format_func=lambda idx: f"第 {idx + 1} 行",
        horizontal=True,
    )
    replace_existing = st.checkbox("如果同名数据表已存在，则替换它")

    if st.button("创建数据表并导入", type="primary"):
        try:
            result = import_selected_sheet(
                file_path=uploaded_file,
                sheet_name=selected_sheet,
                display_name=display_name,
                header_row_index=header_row_index,
                replace_existing=replace_existing,
                source_file_name=selected_file_name,
            )
        except Exception as exc:
            st.error(f"导入失败: {exc}")
        else:
            st.success(
                f"已导入 {result['row_count']} 行到数据表「{result['display_name']}」。"
            )
            st.cache_data.clear()


@st.cache_data
def load_registered_tables() -> list[dict]:
    return list_registered_tables()


def render_search_tab() -> None:
    tables = load_registered_tables()
    if not tables:
        st.info("请先在「数据导入」中创建至少一个数据表。")
        return

    mode = "fuzzy"
    st.session_state.setdefault("keyword_2_value", "")

    def _set_keyword_2(field_name: str) -> None:
        st.session_state["keyword_2_value"] = field_name

    col1, col2 = st.columns(2)
    with col1:
        keyword_1 = st.text_input("关键词 1")
    with col2:
        keyword_2 = st.text_input("关键词 2（可选）", key="keyword_2_value")

    if not keyword_1.strip():
        return

    keyword_1_results = search_records(keyword=[keyword_1], mode=mode, limit=100)
    field_candidates = extract_field_candidates(keyword_1_results, max_candidates=24)
    if field_candidates:
        st.caption("从关键词 1 结果字段中选择关键词 2")
        candidate_columns = st.columns(4)
        for index, field_name in enumerate(field_candidates):
            candidate_columns[index % 4].button(
                field_name,
                key=f"keyword2_candidate_{index}_{field_name}",
                on_click=_set_keyword_2,
                args=(field_name,),
            )

    keyword_2 = st.session_state["keyword_2_value"]
    keywords = _active_keywords([keyword_1, keyword_2])
    if len(keywords) == 1:
        results = keyword_1_results
    else:
        results = search_records(keyword=keywords, mode=mode, limit=100)
    st.write(f"找到 **{len(results)}** 条结果")

    for result in results:
        with st.container(border=True):
            st.markdown(f"**{result['display_name']}**")
            st.caption(
                f"来源: {result['source_file']} / {result['sheet_name']} / 第 {result['row_id']} 行"
            )
            if result["matched_columns"]:
                st.caption("命中字段: " + "、".join(result["matched_columns"]))
            if result.get("matched_keywords"):
                keyword_lines = []
                for keyword, matches in result["matched_keywords"].items():
                    detail_parts = []
                    if matches["field_matches"]:
                        detail_parts.append(
                            "字段名 " + "、".join(matches["field_matches"])
                        )
                    if matches["value_matches"]:
                        detail_parts.append(
                            "内容 " + "、".join(matches["value_matches"])
                        )
                    keyword_lines.append(f"{keyword}: {'；'.join(detail_parts)}")
                st.caption("关键词命中: " + "；".join(keyword_lines))
            render_highlighted_row(result["row"], keywords, mode)


def render_tables_expander() -> None:
    tables = load_registered_tables()
    if not tables:
        return
    with st.expander("已导入数据表", expanded=False):
        for table in tables:
            st.caption(
                f"{table['display_name']} / {table['source_file']} / {table['sheet_name']}"
            )


def main() -> None:
    mode = st.segmented_control(
        "模式",
        ["数据导入", "搜索"],
        default="数据导入",
        label_visibility="collapsed",
    )
    if mode == "搜索":
        render_search_tab()
    else:
        render_import_tab()


if __name__ == "__main__":
    main()

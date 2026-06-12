"""Search registered dynamic child tables."""
from typing import Literal, Sequence

from src.config import DB_CONFIG, MySQLConfig
from src.db import (
    decode_column_mapping,
    get_connection,
    get_data_tables,
    init_db,
    quote_identifier,
)

SearchMode = Literal["fuzzy", "exact"]


def list_registered_tables(db_config: MySQLConfig = DB_CONFIG) -> list[dict]:
    init_db(db_config)
    with get_connection(db_config) as conn:
        return get_data_tables(conn)


def _cell_matches(value: str, keyword: str, mode: SearchMode) -> bool:
    normalized_value = value.casefold()
    normalized_keyword = keyword.casefold()
    if mode == "exact":
        return normalized_value == normalized_keyword
    return normalized_keyword in normalized_value


def _normalize_keywords(keyword: str | Sequence[str]) -> list[str]:
    if isinstance(keyword, str):
        raw_keywords = [keyword]
    else:
        raw_keywords = list(keyword)
    return [item.strip() for item in raw_keywords if item and item.strip()]


def _matching_field_names(
    mapping: list[dict],
    keyword: str,
    mode: SearchMode,
) -> list[str]:
    return [
        column["original"]
        for column in mapping
        if _cell_matches(column["original"], keyword, mode)
    ]


def _matching_table_names(
    table_meta: dict,
    keyword: str,
    mode: SearchMode,
) -> list[str]:
    display_name = table_meta.get("display_name") or ""
    if _cell_matches(display_name, keyword, mode):
        return [display_name]
    return []


def build_keyword_conditions(
    mapping: list[dict],
    keywords: list[str],
    mode: SearchMode,
    table_matches_by_keyword: dict[str, list[str]] | None = None,
) -> tuple[str, list[str], dict[str, list[str]]]:
    field_matches_by_keyword = {
        keyword_item: _matching_field_names(mapping, keyword_item, mode)
        for keyword_item in keywords
    }
    table_matches_by_keyword = table_matches_by_keyword or {}

    if len(keywords) == 2:
        first_keyword, second_keyword = keywords
        first_fields = field_matches_by_keyword[first_keyword]
        second_fields = field_matches_by_keyword[second_keyword]
        first_tables = table_matches_by_keyword.get(first_keyword, [])
        second_tables = table_matches_by_keyword.get(second_keyword, [])
        if not first_tables and not second_tables and bool(first_fields) != bool(second_fields):
            value_keyword = second_keyword if first_fields else first_keyword
            field_names = first_fields or second_fields
            field_name_set = set(field_names)
            restricted_columns = [
                column for column in mapping if column["original"] in field_name_set
            ]
            column_conditions = []
            params: list[str] = []
            for column in restricted_columns:
                column_sql = quote_identifier(column["column"])
                if mode == "exact":
                    column_conditions.append(f"{column_sql} = %s")
                    params.append(value_keyword)
                else:
                    column_conditions.append(f"{column_sql} LIKE %s")
                    params.append(f"%{value_keyword}%")
            return f"({' OR '.join(column_conditions)})", params, field_matches_by_keyword

    keyword_conditions = []
    params: list[str] = []
    for keyword_item in keywords:
        field_matches = field_matches_by_keyword[keyword_item]
        table_matches = table_matches_by_keyword.get(keyword_item, [])
        if table_matches:
            keyword_conditions.append("1=1")
            continue
        if field_matches:
            keyword_conditions.append("1=1")
            continue

        column_conditions = []
        for column in mapping:
            column_sql = quote_identifier(column["column"])
            if mode == "exact":
                column_conditions.append(f"{column_sql} = %s")
                params.append(keyword_item)
            else:
                column_conditions.append(f"{column_sql} LIKE %s")
                params.append(f"%{keyword_item}%")
        keyword_conditions.append(f"({' OR '.join(column_conditions)})")

    return " AND ".join(keyword_conditions), params, field_matches_by_keyword


def row_to_search_result(
    table_meta: dict,
    mapping: list[dict],
    row_dict: dict,
    keywords: list[str],
    mode: SearchMode,
    field_matches_by_keyword: dict[str, list[str]],
    table_matches_by_keyword: dict[str, list[str]] | None = None,
) -> dict:
    full_row = {}
    matched_columns = []
    matched_keywords = {}
    table_matches_by_keyword = table_matches_by_keyword or {}
    for column in mapping:
        value = row_dict.get(column["column"]) or ""
        full_row[column["original"]] = value
        for keyword_item in keywords:
            keyword_matches = matched_keywords.setdefault(
                keyword_item,
                {"table_matches": [], "field_matches": [], "value_matches": []},
            )
            table_matches = table_matches_by_keyword.get(keyword_item, [])
            if table_matches:
                keyword_matches["table_matches"].extend(table_matches)
            if column["original"] in field_matches_by_keyword[keyword_item]:
                matched_columns.append(column["original"])
                keyword_matches["field_matches"].append(column["original"])
            if _cell_matches(value, keyword_item, mode):
                matched_columns.append(column["original"])
                keyword_matches["value_matches"].append(column["original"])

    matched_keywords = {
        keyword_item: {
            "table_matches": list(dict.fromkeys(matches["table_matches"])),
            "field_matches": list(dict.fromkeys(matches["field_matches"])),
            "value_matches": list(dict.fromkeys(matches["value_matches"])),
        }
        for keyword_item, matches in matched_keywords.items()
        if matches["table_matches"] or matches["field_matches"] or matches["value_matches"]
    }

    return {
        "table_id": table_meta["id"],
        "display_name": table_meta["display_name"],
        "table_name": table_meta["table_name"],
        "source_file": table_meta["source_file"],
        "sheet_name": table_meta["sheet_name"],
        "row_id": row_dict["id"],
        "matched_columns": list(dict.fromkeys(matched_columns)),
        "matched_keywords": matched_keywords,
        "row": full_row,
    }


def extract_field_candidates(
    results: list[dict],
    max_candidates: int = 50,
) -> list[str]:
    """Return row field names ordered by match relevance, frequency, and first sighting."""
    field_stats: dict[str, dict[str, int]] = {}
    first_index = 0
    for result in results:
        row = result.get("row") or {}
        for field_name in row:
            if field_name not in field_stats:
                field_stats[field_name] = {"count": 0, "first_index": first_index}
                first_index += 1
            field_stats[field_name]["count"] += 1

        matched_keywords = result.get("matched_keywords") or {}
        for matches in matched_keywords.values():
            for field_name in matches.get("value_matches", []):
                if field_name in field_stats:
                    field_stats[field_name]["match_count"] = (
                        field_stats[field_name].get("match_count", 0) + 1
                    )
            for field_name in matches.get("field_matches", []):
                if field_name in field_stats:
                    field_stats[field_name]["field_match_count"] = (
                        field_stats[field_name].get("field_match_count", 0) + 1
                    )

    ordered_fields = sorted(
        field_stats,
        key=lambda item: (
            -field_stats[item].get("match_count", 0),
            -field_stats[item].get("field_match_count", 0),
            -field_stats[item]["count"],
            field_stats[item]["first_index"],
        ),
    )
    return ordered_fields[:max_candidates]


def search_records(
    keyword: str | Sequence[str],
    mode: SearchMode = "fuzzy",
    limit: int = 100,
    db_config: MySQLConfig = DB_CONFIG,
) -> list[dict]:
    """Search every registered child table and return full matched rows."""
    keywords = _normalize_keywords(keyword)
    if not keywords:
        return []
    if mode not in ("fuzzy", "exact"):
        raise ValueError("mode must be 'fuzzy' or 'exact'")

    init_db(db_config)
    results: list[dict] = []

    with get_connection(db_config) as conn:
        for table_meta in get_data_tables(conn):
            mapping = decode_column_mapping(table_meta)
            if not mapping:
                continue

            table_matches_by_keyword = {
                keyword_item: _matching_table_names(table_meta, keyword_item, mode)
                for keyword_item in keywords
            }
            where_clause, params, field_matches_by_keyword = build_keyword_conditions(
                mapping, keywords, mode, table_matches_by_keyword=table_matches_by_keyword
            )

            sql = (
                "SELECT * FROM "
                f"{quote_identifier(table_meta['table_name'])} "
                f"WHERE {where_clause} "
                "ORDER BY id"
            )
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            for row in rows:
                results.append(
                    row_to_search_result(
                        table_meta=table_meta,
                        mapping=mapping,
                        row_dict=row,
                        keywords=keywords,
                        mode=mode,
                        field_matches_by_keyword=field_matches_by_keyword,
                        table_matches_by_keyword=table_matches_by_keyword,
                    )
                )
                if len(results) >= limit:
                    return results

    return results

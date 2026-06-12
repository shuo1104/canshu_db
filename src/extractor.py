"""从原始行数据中提取关键搜索维度。"""
import re
from typing import Optional

# 列名别名映射
DEVICE_MODEL_ALIASES = [
    "设备型号",
    "设备",
    "具体型号",
    "配套打印设备",
]

MATERIAL_NAME_ALIASES = [
    "材料的选择",
    "材料",
    "产品全称",
    "产品系列",
    "产品名称",
]

APPLICATION_TYPE_ALIASES = [
    "应用类型",
    "核心应用场景",
    "应用场景",
]


def _normalize(text: str) -> str:
    """归一化列名：去空格、去换行、统一中文标点。"""
    return text.strip().replace(" ", "").replace("\n", "").replace("/", "")


def _find_value(raw: dict, aliases: list[str]) -> Optional[str]:
    """根据别名列表从原始字典中查找第一个非空值。

    对单字别名（如“设备”“材料”）要求精确匹配，避免误匹配到其他列名中。
    """
    for key in raw:
        normalized_key = _normalize(key)
        for alias in aliases:
            normalized_alias = _normalize(alias)
            if not normalized_alias:
                continue

            # 单字/短别名要求精确匹配，防止“设备”匹配到“打印前设备/材料状态准备工作”
            if len(normalized_alias) <= 2:
                if normalized_key == normalized_alias:
                    value = raw[key].strip()
                    if value and value not in ("/", "NaN"):
                        return value
                continue

            # 长别名允许列名包含整个别名短语
            if normalized_alias in normalized_key or normalized_key in normalized_alias:
                value = raw[key].strip()
                if value and value not in ("/", "NaN"):
                    return value
    return None


def _truncate(text: str, max_length: int = 200) -> str:
    """截断过长文本，避免维度列太宽。"""
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


def extract_dimensions(raw: dict) -> dict:
    """提取设备型号、材料名称、应用类型。"""
    device_model = _find_value(raw, DEVICE_MODEL_ALIASES)
    material_name = _find_value(raw, MATERIAL_NAME_ALIASES)
    application_type = _find_value(raw, APPLICATION_TYPE_ALIASES)

    return {
        "device_model": _truncate(device_model) if device_model else None,
        "material_name": _truncate(material_name) if material_name else None,
        "application_type": _truncate(application_type) if application_type else None,
    }


def extract_from_record(record: dict) -> dict:
    """对单条记录补充维度字段。"""
    raw = record.get("raw_dict", {})
    dims = extract_dimensions(raw)
    record.update(dims)
    record.pop("raw_dict", None)
    return record

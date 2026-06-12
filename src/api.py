"""FastAPI backend for after-sales parameter search."""
import io
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.importer import get_sheet_preview, import_selected_sheet, list_sheet_names
from src.search import extract_field_candidates, search_records

SearchMode = Literal["fuzzy", "exact"]

app = FastAPI(title="售后参数搜索 API")

_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
origins = [origin.strip() for origin in _allowed_origins.split(",") if origin.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials="*" not in origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class KeywordMatches(BaseModel):
    table_matches: list[str] = Field(default_factory=list)
    field_matches: list[str] = Field(default_factory=list)
    value_matches: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    table_id: int
    display_name: str
    table_name: str
    source_file: str
    sheet_name: str
    row_id: int
    matched_columns: list[str]
    matched_keywords: dict[str, KeywordMatches]
    row: dict[str, str]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/search", response_model=list[SearchResult])
def search(
    keyword1: str = Query(..., description="第一个关键词"),
    keyword2: str | None = Query(None, description="第二个关键词（可选）"),
    mode: SearchMode = Query("fuzzy", description="匹配模式：fuzzy 或 exact"),
    limit: int = Query(100, ge=1, le=1000, description="最多返回条数"),
) -> list[dict]:
    keywords = [keyword for keyword in [keyword1, keyword2] if keyword is not None]
    try:
        return search_records(keyword=keywords, mode=mode, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"搜索失败: {exc}") from exc


@app.get("/api/search/candidates", response_model=list[str])
def candidates(
    keyword1: str = Query(..., description="第一个关键词"),
    max_candidates: int = Query(50, ge=1, le=200, description="最多返回候选数"),
) -> list[str]:
    try:
        results = search_records(keyword=[keyword1], mode="fuzzy", limit=1000)
        return extract_field_candidates(results, max_candidates=max_candidates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取候选字段失败: {exc}") from exc


class SheetListResponse(BaseModel):
    sheets: list[str]


class PreviewResponse(BaseModel):
    preview: list[list[str]]


class ImportResponse(BaseModel):
    display_name: str
    table_name: str
    source_file: str
    sheet_name: str
    header_row_index: int
    row_count: int


def _read_uploaded_file(upload_file: UploadFile) -> tuple[bytes, str]:
    filename = upload_file.filename or "uploaded.xlsx"
    content = upload_file.file.read()
    return content, filename


def _excel_stream(content: bytes) -> io.BytesIO:
    return io.BytesIO(content)


@app.post("/api/import/analyze", response_model=SheetListResponse)
def import_analyze(file: UploadFile = File(...)) -> dict[str, list[str]]:
    try:
        content, filename = _read_uploaded_file(file)
        stream = _excel_stream(content)
        stream.name = filename
        sheets = list_sheet_names(stream)
        return {"sheets": sheets}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"读取 Excel 失败: {exc}") from exc


@app.post("/api/import/preview", response_model=PreviewResponse)
def import_preview(
    file: UploadFile = File(...),
    sheet_name: str = Form(...),
) -> dict[str, list[list[str]]]:
    try:
        content, filename = _read_uploaded_file(file)
        stream = _excel_stream(content)
        stream.name = filename
        preview = get_sheet_preview(stream, sheet_name)
        return {"preview": preview}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"预览失败: {exc}") from exc


@app.post("/api/import", response_model=ImportResponse)
def import_sheet(
    file: UploadFile = File(...),
    sheet_name: str = Form(...),
    display_name: str = Form(...),
    header_row_index: int = Form(..., ge=0),
    replace_existing: bool = Form(False),
) -> dict:
    try:
        content, filename = _read_uploaded_file(file)
        stream = _excel_stream(content)
        stream.name = filename
        result = import_selected_sheet(
            file_path=stream,
            sheet_name=sheet_name,
            display_name=display_name,
            header_row_index=header_row_index,
            replace_existing=replace_existing,
            source_file_name=filename,
        )
        return {
            "display_name": result["display_name"],
            "table_name": result["table_name"],
            "source_file": result["source_file"],
            "sheet_name": result["sheet_name"],
            "header_row_index": result["header_row_index"],
            "row_count": result["row_count"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导入失败: {exc}") from exc


_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_frontend_index = _frontend_dist / "index.html"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str) -> FileResponse:
        static_file = (_frontend_dist / full_path).resolve()
        if (
            full_path
            and _frontend_dist in static_file.parents
            and static_file.is_file()
        ):
            return FileResponse(static_file)
        if _frontend_index.is_file():
            return FileResponse(_frontend_index)
        raise HTTPException(status_code=404, detail="Not Found")

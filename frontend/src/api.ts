import type { CandidatesResponse, ImportResult, SearchResponse } from './types'

const API_BASE = '/api'

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `请求失败: ${response.status}`
    try {
      const payload = await response.json()
      if (payload.detail) {
        message = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail)
      }
    } catch {
      // ignore
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export async function searchRecords(
  keyword1: string,
  keyword2?: string,
  limit = 100,
): Promise<SearchResponse> {
  const params = new URLSearchParams({ keyword1, limit: String(limit) })
  if (keyword2) {
    params.set('keyword2', keyword2)
  }
  const response = await fetch(`${API_BASE}/search?${params.toString()}`)
  return handleResponse<SearchResponse>(response)
}

export async function fetchCandidates(
  keyword1: string,
  maxCandidates = 50,
): Promise<CandidatesResponse> {
  const params = new URLSearchParams({ keyword1, max_candidates: String(maxCandidates) })
  const response = await fetch(`${API_BASE}/search/candidates?${params.toString()}`)
  return handleResponse<CandidatesResponse>(response)
}

export async function analyzeSheets(file: File): Promise<string[]> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await fetch(`${API_BASE}/import/analyze`, {
    method: 'POST',
    body: formData,
  })
  const payload = await handleResponse<{ sheets: string[] }>(response)
  return payload.sheets
}

export async function previewSheet(file: File, sheetName: string): Promise<string[][]> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('sheet_name', sheetName)
  const response = await fetch(`${API_BASE}/import/preview`, {
    method: 'POST',
    body: formData,
  })
  const payload = await handleResponse<{ preview: string[][] }>(response)
  return payload.preview
}

export async function importSheet(
  file: File,
  sheetName: string,
  displayName: string,
  headerRowIndex: number,
  replaceExisting = false,
): Promise<ImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('sheet_name', sheetName)
  formData.append('display_name', displayName)
  formData.append('header_row_index', String(headerRowIndex))
  formData.append('replace_existing', String(replaceExisting))
  const response = await fetch(`${API_BASE}/import`, {
    method: 'POST',
    body: formData,
  })
  return handleResponse<ImportResult>(response)
}

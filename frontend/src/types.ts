export interface KeywordMatches {
  table_matches: string[]
  field_matches: string[]
  value_matches: string[]
}

export interface SearchResult {
  table_id: number
  display_name: string
  table_name: string
  source_file: string
  sheet_name: string
  row_id: number
  matched_columns: string[]
  matched_keywords: Record<string, KeywordMatches>
  row: Record<string, string>
}

export interface ImportResult {
  display_name: string
  table_name: string
  source_file: string
  sheet_name: string
  header_row_index: number
  row_count: number
}

export type SearchResponse = SearchResult[]
export type CandidatesResponse = string[]

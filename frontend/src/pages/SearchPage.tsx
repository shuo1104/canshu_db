import { useEffect, useState } from 'react'
import { AlertCircle, FileSearch, Search, Sparkles } from 'lucide-react'
import { fetchCandidates, searchRecords } from '../api'
import { Highlight } from '../components/Highlight'
import type { SearchResult } from '../types'

export function SearchPage() {
  const [keyword1, setKeyword1] = useState('')
  const [keyword2, setKeyword2] = useState('')
  const [candidates, setCandidates] = useState<string[]>([])
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const activeKeywords = [keyword1, keyword2].filter((k) => k.trim().length > 0)

  useEffect(() => {
    setError(null)
    if (!keyword1.trim()) {
      setCandidates([])
      setResults([])
      return
    }

    let cancelled = false
    setLoading(true)
    Promise.all([
      fetchCandidates(keyword1),
      searchRecords(keyword1, keyword2 || undefined),
    ])
      .then(([candidateList, searchResults]) => {
        if (cancelled) return
        setCandidates(candidateList)
        setResults(searchResults)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [keyword1, keyword2])

  return (
    <div className="page">
      <header className="page__header">
        <h1 className="page__title">搜索设备参数</h1>
      </header>

      <section className="card">
        <div className="input-row">
          <div style={{ position: 'relative', flex: 1 }}>
            <Search
              size={18}
              style={{
                position: 'absolute',
                left: 12,
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--color-text-tertiary)',
              }}
            />
            <input
              type="text"
              placeholder="关键词 1"
              value={keyword1}
              onChange={(e) => setKeyword1(e.target.value)}
              className="input"
              style={{ paddingLeft: 40 }}
            />
          </div>
          <div style={{ position: 'relative', flex: 1 }}>
            <Sparkles
              size={18}
              style={{
                position: 'absolute',
                left: 12,
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--color-text-tertiary)',
              }}
            />
            <input
              type="text"
              placeholder="关键词 2（可选）"
              value={keyword2}
              onChange={(e) => setKeyword2(e.target.value)}
              className="input"
              style={{ paddingLeft: 40 }}
            />
          </div>
        </div>

        {candidates.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: 8 }}>
              从「关键词 1」的结果里，选择一个字段来进一步筛选：
            </div>
            <div className="candidate-list">
              {candidates.map((field) => (
                <button
                  key={field}
                  type="button"
                  onClick={() => setKeyword2(field)}
                  className="candidate-chip"
                >
                  {field}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      {loading && (
        <div className="status-row">
          <span className="text-primary">●</span>
          正在搜索，请稍候…
        </div>
      )}

      {error && (
        <div className="alert alert--error">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {!loading && keyword1.trim() && (
        <div className="status-row">
          找到 <strong>{results.length}</strong> 条结果
          {keyword2 && (
            <>，关键词组合：{keyword1} + {keyword2}</>
          )}
        </div>
      )}

      {!keyword1.trim() && !loading && (
        <div className="card card--quiet empty-state">
          <FileSearch size={40} color="var(--color-text-tertiary)" />
          <div className="empty-state__title">开始搜索</div>
        </div>
      )}

      {keyword1.trim() && !loading && results.length === 0 && !error && (
        <div className="card card--quiet empty-state">
          <FileSearch size={40} color="var(--color-text-tertiary)" />
          <div className="empty-state__title">没有找到结果</div>
          <div className="empty-state__hint">
            试试换一个关键词，或减少关键词数量。如果还没导入数据，请先前往「数据导入」上传 Excel。
          </div>
        </div>
      )}

      <div>
        {results.map((result) => (
          <article key={`${result.table_id}-${result.row_id}`} className="result-card">
            <h2 className="result-card__title">{result.display_name}</h2>
            <div className="result-card__meta">
              <span>来源: {result.source_file}</span>
              <span>子表: {result.sheet_name}</span>
              <span>第 {result.row_id} 行</span>
            </div>
            {result.matched_columns.length > 0 && (
              <div className="result-card__meta" style={{ marginBottom: 12 }}>
                <span className="text-primary">命中字段: {result.matched_columns.join('、')}</span>
              </div>
            )}
            <table className="result-table">
              <tbody>
                {Object.entries(result.row).map(([field, value]) => {
                  if (!String(value).trim()) return null
                  const isMatched = result.matched_columns.includes(field)
                  return (
                    <tr
                      key={field}
                      className={isMatched ? 'result-table__row--matched' : undefined}
                    >
                      <td className="result-table__field">
                        <Highlight text={field} keywords={activeKeywords} />
                      </td>
                      <td>
                        <Highlight text={String(value)} keywords={activeKeywords} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </article>
        ))}
      </div>
    </div>
  )
}

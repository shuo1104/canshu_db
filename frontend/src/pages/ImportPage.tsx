import { ChangeEvent, useState } from 'react'
import { AlertCircle, CheckCircle, FileUp, Loader2, Sheet, Tag } from 'lucide-react'
import { analyzeSheets, importSheet, previewSheet } from '../api'

type ImportStatus = 'ready' | 'loading' | 'importing' | 'success' | 'error'

interface ImportItem {
  id: string
  file: File
  sheets: string[]
  selectedSheet: string
  displayName: string
  preview: string[][]
  headerRowIndex: number
  status: ImportStatus
  rowCount?: number
  error?: string
}

function fileNameToDisplayName(fileName: string): string {
  return fileName.replace(/\.[^.]+$/, '')
}

function fileId(file: File, index: number): string {
  return `${file.name}-${file.size}-${file.lastModified}-${index}`
}

export function ImportPage() {
  const [items, setItems] = useState<ImportItem[]>([])
  const [replaceExisting, setReplaceExisting] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const updateItem = (id: string, patch: Partial<ImportItem>) => {
    setItems((current) =>
      current.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    )
  }

  const handleFiles = async (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files ?? [])
    setError(null)
    setSuccess(null)
    setItems([])

    if (selectedFiles.length === 0) return

    setLoading(true)
    const nextItems: ImportItem[] = []

    for (const [index, selectedFile] of selectedFiles.entries()) {
      const id = fileId(selectedFile, index)
      try {
        const sheetList = await analyzeSheets(selectedFile)
        const firstSheet = sheetList[0] ?? ''
        const previewRows = firstSheet ? await previewSheet(selectedFile, firstSheet) : []
        nextItems.push({
          id,
          file: selectedFile,
          sheets: sheetList,
          selectedSheet: firstSheet,
          displayName: fileNameToDisplayName(selectedFile.name),
          preview: previewRows,
          headerRowIndex: 0,
          status: 'ready',
        })
      } catch (err) {
        nextItems.push({
          id,
          file: selectedFile,
          sheets: [],
          selectedSheet: '',
          displayName: fileNameToDisplayName(selectedFile.name),
          preview: [],
          headerRowIndex: 0,
          status: 'error',
          error: err instanceof Error ? err.message : String(err),
        })
      }
    }

    setItems(nextItems)
    setLoading(false)
  }

  const handleSheetChange = async (id: string, sheetName: string) => {
    const item = items.find((candidate) => candidate.id === id)
    if (!item) return

    updateItem(id, {
      selectedSheet: sheetName,
      preview: [],
      headerRowIndex: 0,
      status: 'loading',
      error: undefined,
    })

    try {
      const rows = await previewSheet(item.file, sheetName)
      updateItem(id, {
        preview: rows,
        status: 'ready',
      })
    } catch (err) {
      updateItem(id, {
        status: 'error',
        error: err instanceof Error ? err.message : String(err),
      })
    }
  }

  const handleImportAll = async () => {
    const importableItems = items.filter((item) => item.status !== 'loading')
    if (importableItems.length === 0) {
      setError('请先上传 Excel 文件')
      return
    }
    const invalidItem = importableItems.find(
      (item) => !item.selectedSheet || !item.displayName.trim() || item.status === 'error',
    )
    if (invalidItem) {
      setError(`请检查「${invalidItem.file.name}」的子表和数据表名称`)
      return
    }

    setLoading(true)
    setError(null)
    setSuccess(null)

    let successCount = 0
    let failedCount = 0

    for (const item of importableItems) {
      updateItem(item.id, {
        status: 'importing',
        error: undefined,
        rowCount: undefined,
      })

      try {
        const result = await importSheet(
          item.file,
          item.selectedSheet,
          item.displayName.trim(),
          item.headerRowIndex,
          replaceExisting,
        )
        successCount += 1
        updateItem(item.id, {
          status: 'success',
          rowCount: result.row_count,
          displayName: result.display_name,
        })
      } catch (err) {
        failedCount += 1
        updateItem(item.id, {
          status: 'error',
          error: err instanceof Error ? err.message : String(err),
        })
      }
    }

    setLoading(false)
    if (failedCount > 0) {
      setError(`已导入 ${successCount} 个文件，${failedCount} 个文件失败`)
    } else {
      setSuccess(`已成功导入 ${successCount} 个文件`)
    }
  }

  return (
    <div className="page">
      <header className="page__header">
        <h1 className="page__title">导入 Excel 数据</h1>
      </header>

      <section className="card">
        <label className="upload-zone">
          <FileUp size={32} color="var(--color-primary)" />
          <div className="upload-zone__title">
            {items.length > 0 ? `已选择 ${items.length} 个文件` : '点击或拖拽上传 Excel 文件'}
          </div>
          <div className="upload-zone__hint">支持批量选择 .xls、.xlsx 文件</div>
          <input
            type="file"
            accept=".xls,.xlsx"
            multiple
            className="upload-zone__input"
            onChange={handleFiles}
          />
        </label>
      </section>

      {loading && items.length === 0 && (
        <div className="status-row">
          <Loader2 size={16} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
          正在读取文件…
        </div>
      )}

      {items.length > 0 && (
        <section className="card">
          <div className="batch-toolbar">
            <label className="batch-toolbar__replace">
              <input
                type="checkbox"
                checked={replaceExisting}
                onChange={(event) => setReplaceExisting(event.target.checked)}
              />
              <span>如果同名数据表已存在，则替换它</span>
            </label>
            <button
              type="button"
              onClick={handleImportAll}
              disabled={loading || items.some((item) => item.status === 'loading' || item.status === 'importing')}
              className="button button--primary"
            >
              {loading ? (
                <>
                  <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                  导入中…
                </>
              ) : (
                '批量导入'
              )}
            </button>
          </div>

          <div className="import-list">
            {items.map((item) => (
              <article key={item.id} className="import-item">
                <div className="import-item__header">
                  <div>
                    <h2 className="import-item__title">{item.file.name}</h2>
                    {item.status === 'success' && (
                      <div className="import-item__status import-item__status--success">
                        已导入 {item.rowCount ?? 0} 行
                      </div>
                    )}
                    {item.status === 'error' && item.error && (
                      <div className="import-item__status import-item__status--error">
                        {item.error}
                      </div>
                    )}
                    {(item.status === 'loading' || item.status === 'importing') && (
                      <div className="import-item__status">
                        {item.status === 'loading' ? '正在读取预览…' : '正在导入…'}
                      </div>
                    )}
                  </div>
                </div>

                <div className="import-grid">
                  <div className="field">
                    <label className="field__label">
                      <Sheet size={16} style={{ verticalAlign: 'text-bottom', marginRight: 6 }} />
                      选择子表
                    </label>
                    <select
                      value={item.selectedSheet}
                      onChange={(event) => handleSheetChange(item.id, event.target.value)}
                      className="select"
                      disabled={item.status === 'loading' || item.status === 'importing'}
                    >
                      {item.sheets.map((sheet) => (
                        <option key={sheet} value={sheet}>
                          {sheet}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="field">
                    <label className="field__label">
                      <Tag size={16} style={{ verticalAlign: 'text-bottom', marginRight: 6 }} />
                      数据表名称
                    </label>
                    <input
                      type="text"
                      value={item.displayName}
                      placeholder={fileNameToDisplayName(item.file.name)}
                      onChange={(event) => updateItem(item.id, { displayName: event.target.value })}
                      className="input"
                      disabled={item.status === 'importing'}
                    />
                  </div>
                </div>

                {item.preview.length > 0 && (
                  <div className="field">
                    <div className="field__label">前三行预览（选择哪一行为数据库字段）</div>
                    <table className="data-table">
                      <tbody>
                        {item.preview.map((row, rowIndex) => (
                          <tr key={rowIndex}>
                            <td style={{ width: '8rem', whiteSpace: 'nowrap' }}>
                              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                                <input
                                  type="radio"
                                  name={`headerRow-${item.id}`}
                                  checked={item.headerRowIndex === rowIndex}
                                  onChange={() => updateItem(item.id, { headerRowIndex: rowIndex })}
                                  disabled={item.status === 'importing'}
                                />
                                第 {rowIndex + 1} 行
                              </label>
                            </td>
                            {row.map((cell, cellIndex) => (
                              <td
                                key={cellIndex}
                                className={item.headerRowIndex === rowIndex ? 'data-table__selected' : undefined}
                              >
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      )}

      {error && (
        <div className="alert alert--error">
          <AlertCircle size={18} />
          {error}
        </div>
      )}
      {success && (
        <div className="alert alert--success">
          <CheckCircle size={18} />
          {success}
        </div>
      )}
    </div>
  )
}

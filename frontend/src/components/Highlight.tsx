import { Fragment } from 'react'

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

interface HighlightProps {
  text: string
  keywords: string[]
}

export function Highlight({ text, keywords }: HighlightProps) {
  const activeKeywords = keywords
    .map((k) => k.trim())
    .filter((k) => k.length > 0)

  if (activeKeywords.length === 0 || !text) {
    return <>{text}</>
  }

  const pattern = new RegExp(`(${activeKeywords.map(escapeRegExp).join('|')})`, 'gi')
  const parts = text.split(pattern)

  return (
    <>
      {parts.map((part, index) => {
        const isMatch = activeKeywords.some(
          (keyword) => part.toLowerCase().includes(keyword.toLowerCase()),
        )
        if (isMatch) {
          return <mark key={index}>{part}</mark>
        }
        return <Fragment key={index}>{part}</Fragment>
      })}
    </>
  )
}

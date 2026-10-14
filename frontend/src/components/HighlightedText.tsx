import React from 'react'
import type { FactEvidence, RiskFlag } from '../api/types'

interface HighlightedTextProps {
  text: string
  facts: FactEvidence[]
  flags?: RiskFlag[]
}

interface SpanMatch {
  start: number
  end: number
  type: 'fact' | 'risk'
  label: string
  source?: string
  claim?: string
}

export function HighlightedText({ text, facts, flags = [] }: HighlightedTextProps): JSX.Element {
  // Find all match ranges for facts and risk claims
  const matches: SpanMatch[] = []

  // Match facts
  for (const fact of facts) {
    if (!fact.value || fact.value.length < 2) continue
    let pos = 0
    while ((pos = text.indexOf(fact.value, pos)) !== -1) {
      matches.push({
        start: pos,
        end: pos + fact.value.length,
        type: 'fact',
        label: fact.label || fact.key,
        source: fact.source,
      })
      pos += fact.value.length
    }
  }

  // Match risk claims
  for (const flag of flags) {
    if (flag.customer_claim && flag.customer_claim.length >= 3) {
      let pos = 0
      while ((pos = text.toLowerCase().indexOf(flag.customer_claim.toLowerCase(), pos)) !== -1) {
        matches.push({
          start: pos,
          end: pos + flag.customer_claim.length,
          type: 'risk',
          label: flag.code,
          claim: flag.customer_claim,
        })
        pos += flag.customer_claim.length
      }
    }
  }

  // Sort matches by start position
  matches.sort((a, b) => a.start - b.start)

  // Discard overlapping matches (first come first served)
  const nonOverlapping: SpanMatch[] = []
  let lastEnd = 0
  for (const m of matches) {
    if (m.start >= lastEnd) {
      nonOverlapping.push(m)
      lastEnd = m.end
    }
  }

  // Build rendered fragments
  const fragments: React.ReactNode[] = []
  let currentIndex = 0

  nonOverlapping.forEach((match, idx) => {
    // Leading plain text
    if (match.start > currentIndex) {
      fragments.push(text.slice(currentIndex, match.start))
    }

    const matchedText = text.slice(match.start, match.end)

    if (match.type === 'fact') {
      fragments.push(
        <span
          key={`fact-${idx}`}
          data-testid="fact-highlight"
          title={`Verified Fact: ${match.label} (Source: ${match.source})`}
          style={{
            backgroundColor: '#ecfdf5',
            color: '#065f46',
            borderBottom: '2px solid #10b981',
            padding: '1px 3px',
            borderRadius: '2px',
            fontWeight: 600,
            cursor: 'help',
          }}
        >
          {matchedText}
          <span
            style={{
              fontSize: '0.65rem',
              color: '#047857',
              marginLeft: '3px',
              fontWeight: 400,
              verticalAlign: 'super',
            }}
          >
            [src: {match.source}]
          </span>
        </span>
      )
    } else {
      fragments.push(
        <span
          key={`risk-${idx}`}
          data-testid="risk-highlight"
          title={`Risk Flag: ${match.label} - Unverified claim: "${match.claim}"`}
          style={{
            backgroundColor: '#fef3c7',
            color: '#92400e',
            borderBottom: '2px dashed #f59e0b',
            padding: '1px 4px',
            borderRadius: '2px',
            fontWeight: 600,
            cursor: 'help',
          }}
        >
          {matchedText}
          <span
            style={{
              fontSize: '0.65rem',
              color: '#b45309',
              marginLeft: '3px',
              fontWeight: 700,
            }}
          >
            ⚠️
          </span>
        </span>
      )
    }

    currentIndex = match.end
  })

  // Trailing plain text
  if (currentIndex < text.length) {
    fragments.push(text.slice(currentIndex))
  }

  return (
    <div
      style={{
        whiteSpace: 'pre-wrap',
        fontFamily: 'inherit',
        fontSize: '0.875rem',
        lineHeight: 1.5,
        color: '#1f2937',
      }}
    >
      {fragments}
    </div>
  )
}

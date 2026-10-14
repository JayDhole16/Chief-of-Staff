import React, { useState } from 'react'
import type { Deal } from '../api/types'
import { formatINR, formatDateTime } from '../utils/formatters'

export interface PipelineViewProps {
  deals: Deal[]
  isLoading?: boolean
  error?: Error | null
  onRefresh?: () => void
}

export function PipelineView({
  deals,
  isLoading = false,
  error = null,
  onRefresh,
}: PipelineViewProps): JSX.Element {
  const [filter, setFilter] = useState<'all' | 'quiet' | 'active'>('all')

  const quietDeals = deals.filter((d) => d.is_quiet || (d.days_quiet && d.days_quiet > 0))
  const activeDeals = deals.filter((d) => !d.is_quiet && d.stage !== 'won')

  const filteredDeals =
    filter === 'quiet' ? quietDeals : filter === 'active' ? activeDeals : deals

  const totalPaise = deals.reduce((acc, d) => acc + d.value_paise, 0)

  return (
    <div
      data-testid="pipeline-view"
      style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
    >
      {/* Header Summary */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#ffffff',
          padding: '1rem',
          borderRadius: '0.5rem',
          border: '1px solid #e5e7eb',
        }}
      >
        <div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase' }}>
            Pipeline Value ({deals.length} Deals)
          </div>
          <div
            data-testid="total-pipeline-value"
            style={{ fontSize: '1.25rem', fontWeight: 700, color: '#111827' }}
          >
            {formatINR(totalPaise)}
          </div>
        </div>

        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={isLoading}
            style={{
              padding: '0.375rem 0.75rem',
              fontSize: '0.75rem',
              backgroundColor: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            {isLoading ? '...' : '↻ Refresh'}
          </button>
        )}
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button
          type="button"
          onClick={() => setFilter('all')}
          style={{
            flex: 1,
            padding: '0.5rem',
            fontSize: '0.75rem',
            fontWeight: 600,
            borderRadius: '0.375rem',
            border: 'none',
            backgroundColor: filter === 'all' ? '#3b82f6' : '#e5e7eb',
            color: filter === 'all' ? '#ffffff' : '#374151',
            cursor: 'pointer',
          }}
        >
          All ({deals.length})
        </button>
        <button
          type="button"
          data-testid="filter-quiet"
          onClick={() => setFilter('quiet')}
          style={{
            flex: 1,
            padding: '0.5rem',
            fontSize: '0.75rem',
            fontWeight: 600,
            borderRadius: '0.375rem',
            border: 'none',
            backgroundColor: filter === 'quiet' ? '#d97706' : '#fef3c7',
            color: filter === 'quiet' ? '#ffffff' : '#92400e',
            cursor: 'pointer',
          }}
        >
          Quiet Sweeps ({quietDeals.length})
        </button>
        <button
          type="button"
          onClick={() => setFilter('active')}
          style={{
            flex: 1,
            padding: '0.5rem',
            fontSize: '0.75rem',
            fontWeight: 600,
            borderRadius: '0.375rem',
            border: 'none',
            backgroundColor: filter === 'active' ? '#10b981' : '#d1fae5',
            color: filter === 'active' ? '#ffffff' : '#065f46',
            cursor: 'pointer',
          }}
        >
          Active ({activeDeals.length})
        </button>
      </div>

      {error && (
        <div
          data-testid="pipeline-error"
          style={{
            padding: '0.75rem',
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            borderRadius: '0.375rem',
            fontSize: '0.8125rem',
          }}
        >
          Error loading pipeline: {error.message}
        </div>
      )}

      {/* Deal Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {filteredDeals.map((deal) => {
          const isQuiet = deal.is_quiet || (deal.days_quiet && deal.days_quiet > 0)
          return (
            <div
              key={deal.id}
              data-testid="deal-card"
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid #e5e7eb',
                borderRadius: '0.5rem',
                padding: '0.875rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: '#111827' }}>
                    {deal.title}
                  </div>
                  {deal.contact_name && (
                    <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                      {deal.contact_name} {deal.contact_email ? `(${deal.contact_email})` : ''}
                    </div>
                  )}
                </div>

                <span
                  style={{
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    padding: '0.2rem 0.5rem',
                    borderRadius: '9999px',
                    backgroundColor:
                      deal.stage === 'won'
                        ? '#d1fae5'
                        : deal.stage === 'meeting_scheduled'
                        ? '#e0f2fe'
                        : '#f3f4f6',
                    color:
                      deal.stage === 'won'
                        ? '#065f46'
                        : deal.stage === 'meeting_scheduled'
                        ? '#0369a1'
                        : '#374151',
                  }}
                >
                  {deal.stage.replace('_', ' ')}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: '#047857' }}>
                  {formatINR(deal.value_paise)}
                </div>

                {/* Quiet Chip */}
                {isQuiet && (
                  <span
                    data-testid="quiet-chip"
                    style={{
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      backgroundColor: '#fef3c7',
                      color: '#b45309',
                      border: '1px solid #fde68a',
                      padding: '0.15rem 0.45rem',
                      borderRadius: '0.25rem',
                    }}
                  >
                    💤 Quiet {deal.days_quiet}d
                  </span>
                )}
              </div>

              {deal.last_interaction && (
                <div style={{ fontSize: '0.7rem', color: '#9ca3af' }}>
                  Last interaction: {formatDateTime(deal.last_interaction)}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

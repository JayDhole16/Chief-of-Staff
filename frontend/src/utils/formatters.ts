/**
 * Formatting utilities for Chief of Staff frontend.
 * Pure functions: INR currency formatting, date/time formatting.
 */

const inrFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

/** Format whole rupees in Indian notation (e.g. 1250000 -> "₹12,50,000"). */
export function formatRupees(rupees: number): string {
  return inrFormatter.format(Math.round(rupees || 0))
}

/** Format integer paise in Indian notation (e.g. 125000000 paise -> "₹12,50,000"). */
export function formatINR(paise: number): string {
  return formatRupees(Math.floor(paise / 100))
}

/** Format an ISO timestamp as a short local date and time. */
export function formatDateTime(isoString: string): string {
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return isoString
    return new Intl.DateTimeFormat('en-IN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    }).format(d)
  } catch {
    return isoString
  }
}

/** Relative time such as "3m ago", "2d ago". */
export function timeAgo(isoString: string): string {
  const d = new Date(isoString)
  if (isNaN(d.getTime())) return ''
  const seconds = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000))
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  return formatDateTime(isoString)
}

/** Compact token counts: 1234 -> "1.2k". */
export function formatTokens(n: number): string {
  if (!n) return '0'
  if (n < 1000) return String(n)
  if (n < 1_000_000) return `${(n / 1000).toFixed(1)}k`
  return `${(n / 1_000_000).toFixed(2)}M`
}

export const STAGE_LABELS: Record<string, string> = {
  lead: 'Lead',
  qualified: 'Qualified',
  proposal_sent: 'Proposal sent',
  negotiating: 'Negotiating',
  won: 'Won',
  lost: 'Lost',
}

/**
 * Formatting utilities for Chief of Staff frontend.
 * Pure functions: INR currency formatting, date/time formatting.
 */

/**
 * Format integer paise into standard Indian Rupee notation (e.g. 125000000 paise -> "₹12,50,000").
 */
export function formatINR(paise: number): string {
  const rupees = Math.floor(paise / 100)
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(rupees)
}

/**
 * Format ISO timestamp into human-readable IST / local time.
 */
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


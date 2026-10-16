/**
 * Polling hook: interval-based refetch with pause on visibility change,
 * exponential backoff on error, cancel on unmount.
 */

import { useEffect, useRef, useState } from 'react'

export interface UsePollingOptions {
  interval: number // ms between polls
  onFetch: () => Promise<void>
  onError?: (error: Error) => void
}

export function usePolling({ interval, onFetch, onError }: UsePollingOptions): {
  isLoading: boolean
  error: Error | null
  retry: () => void
} {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const backoffRef = useRef(1) // Exponential backoff multiplier

  const onFetchRef = useRef(onFetch)
  onFetchRef.current = onFetch

  const onErrorRef = useRef(onError)
  onErrorRef.current = onError

  const poll = async () => {
    try {
      setIsLoading(true)
      setError(null)
      await onFetchRef.current()
      backoffRef.current = 1 // Reset backoff on success
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err))
      setError(error)
      onErrorRef.current?.(error)
      backoffRef.current = Math.min(backoffRef.current * 2, 10) // Cap at 10x
    } finally {
      setIsLoading(false)
      scheduleNextPoll()
    }
  }

  const scheduleNextPoll = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    const delay = interval * backoffRef.current
    timeoutRef.current = setTimeout(() => {
      poll()
    }, delay)
  }

  const handleVisibilityChange = () => {
    if (document.hidden) {
      // Pause polling when tab is hidden
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    } else {
      // Resume polling when tab becomes visible
      poll()
    }
  }

  useEffect(() => {
    // Initial poll
    poll()

    // Listen to visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange)

    // Cleanup on unmount
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [interval])


  return {
    isLoading,
    error,
    retry: () => {
      backoffRef.current = 1
      poll()
    },
  }
}

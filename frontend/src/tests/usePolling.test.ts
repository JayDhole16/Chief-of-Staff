/**
 * Tests for usePolling hook: interval, pause on hidden, backoff, cleanup.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { usePolling } from '../hooks/usePolling'

describe('usePolling', () => {
  beforeEach(() => {
    vi.clearAllTimers()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('calls onFetch on mount', async () => {
    const onFetch = vi.fn().mockResolvedValue(undefined)

    renderHook(() => usePolling({ interval: 5000, onFetch }))

    expect(onFetch).toHaveBeenCalledTimes(1)
  })

  it('polls at specified interval', async () => {
    const onFetch = vi.fn().mockResolvedValue(undefined)

    renderHook(() => usePolling({ interval: 5000, onFetch }))

    expect(onFetch).toHaveBeenCalledTimes(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
    expect(onFetch).toHaveBeenCalledTimes(2)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
    expect(onFetch).toHaveBeenCalledTimes(3)
  })

  it('implements exponential backoff on error', async () => {
    const error = new Error('Test error')
    const onFetch = vi
      .fn()
      .mockRejectedValueOnce(error)
      .mockResolvedValue(undefined)

    const { result } = renderHook(() =>
      usePolling({ interval: 1000, onFetch })
    )

    expect(result.current.error).toBe(null)

    // First fetch fails
    await act(async () => {
      await Promise.resolve()
    })
    expect(result.current.error).toBe(error)

    // Next poll should be delayed (backoff = 2x: 2000ms)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000) // 1x interval passes, no second fetch
    })
    expect(onFetch).toHaveBeenCalledTimes(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000) // Reach 2x delay
    })
    expect(onFetch).toHaveBeenCalledTimes(2)
  })



  it('pauses when document is hidden', () => {
    const onFetch = vi.fn().mockResolvedValue(undefined)

    renderHook(() => usePolling({ interval: 5000, onFetch }))

    expect(onFetch).toHaveBeenCalledTimes(1)

    // Simulate hiding document
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    })

    document.dispatchEvent(new Event('visibilitychange'))
    vi.advanceTimersByTime(5000)

    // Should not have called onFetch again (paused)
    expect(onFetch).toHaveBeenCalledTimes(1)
  })

  it('resumes when document becomes visible', () => {
    const onFetch = vi.fn().mockResolvedValue(undefined)

    renderHook(() => usePolling({ interval: 5000, onFetch }))

    expect(onFetch).toHaveBeenCalledTimes(1)

    // Hide document
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    })

    document.dispatchEvent(new Event('visibilitychange'))

    // Show document again
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    })

    document.dispatchEvent(new Event('visibilitychange'))

    // Should fetch immediately when visible again
    expect(onFetch).toHaveBeenCalledTimes(2)
  })

  it('calls onError callback', async () => {
    const error = new Error('Test error')
    const onFetch = vi.fn().mockRejectedValue(error)
    const onError = vi.fn()

    renderHook(() => usePolling({ interval: 5000, onFetch, onError }))

    await act(async () => {
      await Promise.resolve()
    })

    expect(onError).toHaveBeenCalledWith(error)
  })

  it('exposes retry function', async () => {
    const error = new Error('Test error')
    const onFetch = vi
      .fn()
      .mockRejectedValueOnce(error)
      .mockResolvedValue(undefined)

    const { result } = renderHook(() =>
      usePolling({ interval: 5000, onFetch })
    )

    await act(async () => {
      await Promise.resolve()
    })
    expect(result.current.error).toBe(error)

    // Retry should reset backoff and fetch immediately
    await act(async () => {
      result.current.retry()
      await Promise.resolve()
    })

    expect(onFetch).toHaveBeenCalledTimes(2)
  })

})

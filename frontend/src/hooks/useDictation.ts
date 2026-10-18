/**
 * Speech-to-text dictation using the browser's Web Speech API (Chrome, Edge, Safari).
 * Streams interim results while the user speaks and reports clear errors for
 * denied microphone access, missing microphones and unsupported browsers.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

interface SpeechAlternative {
  transcript: string
}
interface SpeechResult {
  isFinal: boolean
  0: SpeechAlternative
}
interface SpeechResultEvent {
  resultIndex: number
  results: ArrayLike<SpeechResult>
}
interface SpeechErrorEvent {
  error: string
}
interface SpeechRecognitionLike {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  onresult: ((event: SpeechResultEvent) => void) | null
  onerror: ((event: SpeechErrorEvent) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}
type SpeechRecognitionCtor = new () => SpeechRecognitionLike

function getRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === 'undefined') return null
  const w = window as unknown as { SpeechRecognition?: SpeechRecognitionCtor; webkitSpeechRecognition?: SpeechRecognitionCtor }
  return w.SpeechRecognition || w.webkitSpeechRecognition || null
}

const ERROR_MESSAGES: Record<string, string> = {
  'not-allowed': 'Microphone access was blocked. Allow the microphone for this site in your browser settings and try again.',
  'service-not-allowed': 'Speech recognition is blocked in this browser. Allow the microphone or use Chrome / Edge.',
  'audio-capture': 'No microphone was found. Connect a microphone and try again.',
  'no-speech': "I didn't hear anything. Try again and speak after the mic turns green.",
  network: 'The speech service could not be reached. Check your connection and try again.',
  'language-not-supported': 'English speech recognition is not available in this browser.',
}

export interface DictationHandlers {
  /** Called with the full transcript so far (final + interim) while listening. */
  onTranscript: (text: string, isFinal: boolean) => void
  /** Called once when listening stops, with the final transcript. */
  onStop?: (finalText: string) => void
}

export function useDictation({ onTranscript, onStop }: DictationHandlers) {
  const [listening, setListening] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const finalRef = useRef('')
  const handlers = useRef({ onTranscript, onStop })
  handlers.current = { onTranscript, onStop }

  const supported = getRecognitionCtor() !== null

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
  }, [])

  const start = useCallback(() => {
    setError(null)
    const Ctor = getRecognitionCtor()
    if (!Ctor) {
      setError('Voice dictation is not supported in this browser. Use Chrome, Edge or Safari.')
      return
    }
    if (typeof window !== 'undefined' && window.isSecureContext === false) {
      setError('Voice dictation needs a secure (https) page.')
      return
    }
    const recognition = new Ctor()
    const lang = typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('en') ? navigator.language : 'en-US'
    recognition.lang = lang
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1
    finalRef.current = ''

    recognition.onresult = (event) => {
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        const text = result[0]?.transcript ?? ''
        if (result.isFinal) finalRef.current = `${finalRef.current} ${text}`.trim()
        else interim += text
      }
      const combined = `${finalRef.current} ${interim}`.trim()
      handlers.current.onTranscript(combined, interim === '')
    }
    recognition.onerror = (event) => {
      if (event.error === 'aborted') return
      setError(ERROR_MESSAGES[event.error] ?? `Dictation stopped: ${event.error}`)
    }
    recognition.onend = () => {
      setListening(false)
      recognitionRef.current = null
      handlers.current.onStop?.(finalRef.current)
    }

    try {
      recognition.start()
      recognitionRef.current = recognition
      setListening(true)
    } catch (err) {
      setError(`Could not start the microphone: ${String(err)}`)
    }
  }, [])

  const toggle = useCallback(() => {
    if (listening) stop()
    else start()
  }, [listening, start, stop])

  useEffect(() => () => recognitionRef.current?.abort(), [])

  return { supported, listening, error, start, stop, toggle, clearError: () => setError(null) }
}

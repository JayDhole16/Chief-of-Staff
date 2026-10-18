/**
 * Grounded chat with the founder's chief of staff, powered by the founder's own API key.
 * The agent can look up contacts and calendar events and prepare emails, WhatsApp
 * messages and calendar changes, which the user confirms on cards in the chat.
 * Supports voice dictation into the input box. Conversations persist per user.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { apiCall, APIClientError, errorMessage } from '../api/client'
import type { ChatMessage, ChatResponse, ChatSession } from '../api/types'
import type { DashboardContext } from '../pages/DashboardPage'
import { LogoStar, MicIcon, PlusIcon, SendIcon, TrashIcon } from '../components/Icons'
import { ActionCard } from '../components/ActionCard'
import { useDictation } from '../hooks/useDictation'
import { Markdown } from '../components/ui'
import { timeAgo } from '../utils/formatters'

const STARTER_PROMPTS = [
  'Which deals need a follow-up this week?',
  'Send a follow-up email to my quietest deal',
  "What's on my calendar tomorrow?",
  'Set a reminder for client check-in tomorrow at 3 PM',
]

const AUTOSEND_KEY = 'cos.dictation.autosend'

function joinText(base: string, addition: string): string {
  return [base.trim(), addition.trim()].filter(Boolean).join(' ')
}

export function ChatView({ ctx }: { ctx: DashboardContext }): JSX.Element {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [needsKey, setNeedsKey] = useState(!ctx.user.active_llm_provider)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const dictationBase = useRef('')
  const [autoSend, setAutoSend] = useState(() => {
    try {
      return localStorage.getItem(AUTOSEND_KEY) === '1'
    } catch {
      return false
    }
  })

  const loadSessions = useCallback(() => {
    apiCall<{ sessions: ChatSession[] }>('/chat/sessions')
      .then((res) => setSessions(res.sessions))
      .catch(() => undefined)
  }, [])

  useEffect(loadSessions, [loadSessions])

  useEffect(() => {
    setNeedsKey(!ctx.user.active_llm_provider)
  }, [ctx.user.active_llm_provider])

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, sending])

  const openSession = async (id: string) => {
    setError(null)
    setActiveId(id)
    try {
      const res = await apiCall<ChatSession & { messages: ChatMessage[] }>(`/chat/sessions/${id}`)
      setMessages(res.messages)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const newChat = () => {
    setActiveId(null)
    setMessages([])
    setError(null)
    inputRef.current?.focus()
  }

  const deleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await apiCall(`/chat/sessions/${id}`, { method: 'DELETE' })
      if (id === activeId) newChat()
      loadSessions()
    } catch (err) {
      ctx.notify(errorMessage(err), 'error')
    }
  }

  const send = async (text: string) => {
    const message = text.trim()
    if (!message || sending) return
    setError(null)
    setSending(true)
    setInput('')
    const optimistic: ChatMessage = { id: `local-${Date.now()}`, role: 'user', content: message, created_at: new Date().toISOString() }
    setMessages((prev) => [...prev, optimistic])
    try {
      const res = await apiCall<ChatResponse>('/chat', { method: 'POST', body: { message, session_id: activeId } })
      setMessages((prev) => [...prev.filter((m) => m.id !== optimistic.id), res.user_message, { ...res.reply, actions: res.actions }])
      if (res.actions.length > 0) ctx.refreshApprovals()
      if (res.session_id !== activeId) {
        setActiveId(res.session_id)
        loadSessions()
      }
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id))
      setInput(message)
      if (err instanceof APIClientError && err.code === 409) setNeedsKey(true)
      setError(errorMessage(err))
    } finally {
      setSending(false)
    }
  }

  const dictation = useDictation({
    onTranscript: (text) => setInput(joinText(dictationBase.current, text)),
    onStop: (finalText) => {
      const full = joinText(dictationBase.current, finalText)
      setInput(full)
      if (autoSend && finalText.trim()) void send(full)
      else inputRef.current?.focus()
    },
  })

  const toggleDictation = () => {
    if (!dictation.listening) dictationBase.current = input
    dictation.toggle()
  }

  const changeAutoSend = (value: boolean) => {
    setAutoSend(value)
    try {
      localStorage.setItem(AUTOSEND_KEY, value ? '1' : '0')
    } catch {
      // preference is only kept for this page
    }
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send(input)
    }
  }

  return (
    <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
      <aside
        style={{
          width: '260px',
          flexShrink: 0,
          borderRight: '1px solid var(--border-hairline)',
          backgroundColor: 'var(--bg-sidebar)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div style={{ padding: '1rem' }}>
          <button type="button" className="cos-btn cos-btn-primary" style={{ width: '100%' }} onClick={newChat}>
            <PlusIcon size={16} /> New chat
          </button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 0.6rem 1rem' }}>
          {sessions.length === 0 && <div className="cos-dim" style={{ fontSize: '0.78rem', padding: '0.5rem' }}>No conversations yet.</div>}
          {sessions.map((s) => (
            <div
              key={s.id}
              role="button"
              tabIndex={0}
              onClick={() => openSession(s.id)}
              onKeyDown={(e) => e.key === 'Enter' && openSession(s.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '0.4rem',
                padding: '0.55rem 0.65rem',
                borderRadius: '9px',
                cursor: 'pointer',
                backgroundColor: s.id === activeId ? '#0C1A14' : 'transparent',
                border: s.id === activeId ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
                marginBottom: '2px',
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: '0.8rem', color: s.id === activeId ? 'var(--emerald-glow)' : 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.title}</div>
                <div className="cos-dim" style={{ fontSize: '0.68rem' }}>{timeAgo(s.updated_at)}</div>
              </div>
              <button type="button" onClick={(e) => deleteSession(s.id, e)} aria-label={`Delete ${s.title}`} title="Delete chat" style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: '2px', flexShrink: 0 }}>
                <TrashIcon size={14} />
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <header style={{ height: '56px', padding: '0 1.5rem', display: 'flex', alignItems: 'center', gap: '0.65rem', borderBottom: '1px solid var(--border-hairline)', backgroundColor: 'var(--bg-surface)', flexShrink: 0 }}>
          <div style={{ width: '30px', height: '30px', borderRadius: '50%', backgroundColor: '#081C13', border: '1px solid rgba(16, 185, 129, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--emerald-glow)' }}>
            <LogoStar size={15} />
          </div>
          <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#FFFFFF' }}>Chief of Staff</span>
          <span className="cos-dim" style={{ fontSize: '0.75rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            · {sessions.find((s) => s.id === activeId)?.title ?? 'New conversation'}
          </span>
          <span style={{ marginLeft: 'auto' }} className={`cos-badge ${ctx.user.active_llm_provider ? 'cos-badge-green' : ''}`}>
            {ctx.user.active_llm_provider ? `AI: ${ctx.user.active_llm_provider}` : 'No AI key'}
          </span>
        </header>

        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
          <div style={{ maxWidth: '760px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {needsKey && (
              <div className="cos-alert cos-alert-warn" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
                <span>Chat runs on your own AI provider key. Add one to start, and every token is billed to your account, not ours.</span>
                <button type="button" className="cos-btn cos-btn-primary cos-btn-sm" onClick={() => ctx.navigate('keys')}>
                  Add API key
                </button>
              </div>
            )}

            {messages.length === 0 && !sending && (
              <div style={{ textAlign: 'center', padding: '3rem 1rem 1rem' }}>
                <div style={{ display: 'inline-flex', width: '52px', height: '52px', borderRadius: '18px', backgroundColor: '#091510', border: '1px solid rgba(16, 185, 129, 0.4)', color: 'var(--emerald-glow)', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }} className="glow-emerald-sm">
                  <LogoStar size={26} />
                </div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#FFFFFF' }}>How can I help, {ctx.user.name.split(' ')[0]}?</div>
                <div className="cos-muted" style={{ fontSize: '0.84rem', marginTop: '0.35rem' }}>I answer from your live deals, approvals and activity.</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'center', marginTop: '1.5rem' }}>
                  {STARTER_PROMPTS.map((p) => (
                    <button key={p} type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => send(p)} disabled={needsKey}>
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) => (
              <div key={m.id} className="chat-msg-animate" style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                <div
                  style={{
                    maxWidth: '85%',
                    padding: '0.75rem 1rem',
                    borderRadius: m.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                    backgroundColor: m.role === 'user' ? 'var(--bg-user-bubble)' : 'var(--bg-ai-bubble)',
                    border: `1px solid ${m.role === 'user' ? 'rgba(16, 185, 129, 0.3)' : 'var(--border-hairline)'}`,
                    fontSize: '0.88rem',
                    lineHeight: 1.6,
                    color: 'var(--text-main)',
                    wordBreak: 'break-word',
                  }}
                >
                  {m.role === 'assistant' ? <Markdown text={m.content} /> : <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>}
                  {m.role === 'assistant' && m.meta?.tool_calls && m.meta.tool_calls.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginTop: '0.55rem' }}>
                      {m.meta.tool_calls.map((t, i) => (
                        <span key={i} className={`cos-badge ${t.ok ? '' : 'cos-badge-red'}`} title={t.summary} style={{ textTransform: 'none' }}>
                          {t.ok ? '✓' : '✗'} {t.name.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  )}
                  {m.actions?.map((a) => (
                    <ActionCard
                      key={a.ref}
                      proposal={a}
                      onDecided={(message, ok) => {
                        ctx.notify(message, ok ? 'ok' : 'error')
                        ctx.refreshApprovals()
                      }}
                      onOpenApprovals={() => ctx.navigate('approvals')}
                    />
                  ))}
                  {m.role === 'assistant' && m.model && (
                    <div className="cos-dim" style={{ fontSize: '0.66rem', marginTop: '0.5rem' }}>
                      {m.provider} · {m.model}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {sending && (
              <div style={{ display: 'flex', gap: '4px', padding: '0.75rem 1rem', backgroundColor: 'var(--bg-ai-bubble)', border: '1px solid var(--border-hairline)', borderRadius: '16px', width: 'fit-content' }} aria-label="Assistant is typing">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            )}
            {error && <div className="cos-alert cos-alert-error">{error}</div>}
          </div>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            void send(input)
          }}
          style={{ padding: '1rem 1.5rem 1.25rem', borderTop: '1px solid var(--border-hairline)', backgroundColor: 'var(--bg-console)' }}
        >
          {dictation.error && (
            <div className="cos-alert cos-alert-error" role="alert" style={{ maxWidth: '760px', margin: '0 auto 0.6rem', display: 'flex', justifyContent: 'space-between', gap: '0.75rem' }}>
              <span>{dictation.error}</span>
              <button type="button" onClick={dictation.clearError} aria-label="Dismiss" style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}>
                ×
              </button>
            </div>
          )}
          <div style={{ maxWidth: '760px', margin: '0 auto', display: 'flex', gap: '0.6rem', alignItems: 'flex-end' }}>
            <button
              type="button"
              className={`cos-btn cos-btn-ghost${dictation.listening ? ' cos-mic-live' : ''}`}
              onClick={toggleDictation}
              disabled={sending || needsKey}
              aria-pressed={dictation.listening}
              aria-label={dictation.listening ? 'Stop dictation' : 'Start voice dictation'}
              title={dictation.supported ? (dictation.listening ? 'Stop dictation' : 'Dictate (speak in English)') : 'Voice dictation needs Chrome, Edge or Safari'}
              style={{ height: '46px', width: '46px', padding: 0, flexShrink: 0 }}
            >
              <MicIcon size={18} />
            </button>
            <textarea
              ref={inputRef}
              className="cos-textarea"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={
                needsKey
                  ? 'Add an API key to start chatting'
                  : dictation.listening
                    ? 'Listening... speak now, click the mic to stop'
                    : 'Ask, or tell me to email, WhatsApp or schedule... (Enter to send)'
              }
              rows={1}
              aria-label="Message"
              style={{ minHeight: '46px', maxHeight: '180px' }}
              disabled={sending}
            />
            <button type="submit" className="cos-btn cos-btn-primary" disabled={sending || !input.trim()} aria-label="Send" style={{ height: '46px', width: '46px', padding: 0 }}>
              <SendIcon size={18} />
            </button>
          </div>
          <label style={{ maxWidth: '760px', margin: '0.45rem auto 0', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.72rem', color: 'var(--text-dim)', cursor: 'pointer' }}>
            <input type="checkbox" checked={autoSend} onChange={(e) => changeAutoSend(e.target.checked)} />
            Send automatically when I stop dictating
          </label>
        </form>
      </section>
    </div>
  )
}

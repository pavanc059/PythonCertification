import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  X, Send, Loader2, Trash2, Bot, User,
  ChevronDown, Sparkles,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  streamChat, getChatHistory, clearChatHistory,
  type ChatMessage,
} from '@/api/assistant'

// ─── Types ────────────────────────────────────────────────────────────────────

interface LocalMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Convert server ChatMessage to LocalMessage */
function fromServer(m: ChatMessage): LocalMessage {
  return { id: m.id, role: m.role, content: m.content }
}

// ─── Message bubble ───────────────────────────────────────────────────────────

function Bubble({ msg }: { msg: LocalMessage }) {
  const isUser = msg.role === 'user'
  return (
    <div className={cn('flex gap-2 items-start', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div className={cn(
        'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[10px]',
        isUser ? 'bg-[#6366f1]/20 text-[#6366f1]' : 'bg-amber-500/15 text-amber-400',
      )}>
        {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
      </div>

      {/* Content */}
      <div className={cn(
        'max-w-[80%] rounded-xl px-3 py-2 text-sm leading-relaxed',
        isUser
          ? 'bg-[#6366f1] text-white rounded-tr-none'
          : 'bg-[#1a2235] text-[#e2e8f0] rounded-tl-none',
      )}>
        {msg.streaming ? (
          <span>
            {msg.content}
            <span className="inline-block ml-0.5 h-3.5 w-0.5 bg-amber-400 animate-pulse align-middle" />
          </span>
        ) : (
          <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
        )}
      </div>
    </div>
  )
}

// ─── Suggested prompts ────────────────────────────────────────────────────────

const SUGGESTIONS = [
  'Why did my portfolio value change today?',
  'Why did AutoPilot buy a stock?',
  'What was the analysis before the last trade?',
  'Show my recent trading activity',
  'How are my auto-trade bots performing?',
]

// ─── Main widget ──────────────────────────────────────────────────────────────

export function AssistantWidget() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [unread, setUnread] = useState(0)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const qc = useQueryClient()

  // Load history on first open
  const { data: history } = useQuery({
    queryKey: ['assistant', 'history'],
    queryFn: getChatHistory,
    enabled: open,
    staleTime: 0,
  })

  useEffect(() => {
    if (history && messages.length === 0) {
      setMessages(history.map(fromServer))
    }
  }, [history])

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100)
      setUnread(0)
    }
  }, [open])

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || isStreaming) return
    setInput('')

    // Add user bubble
    const userMsg: LocalMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: trimmed,
    }
    setMessages((prev) => [...prev, userMsg])

    // Add streaming assistant bubble
    const assistantId = `a-${Date.now()}`
    setMessages((prev) => [...prev, { id: assistantId, role: 'assistant', content: '', streaming: true }])
    setIsStreaming(true)

    await streamChat(
      trimmed,
      (chunk) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: m.content + chunk } : m
          )
        )
      },
      () => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, streaming: false } : m
          )
        )
        setIsStreaming(false)
        qc.invalidateQueries({ queryKey: ['assistant', 'history'] })
        if (!open) setUnread((n) => n + 1)
      },
      (err) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: `⚠️ Error: ${err}`, streaming: false }
              : m
          )
        )
        setIsStreaming(false)
      },
    )
  }, [isStreaming, open, qc])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const handleClear = async () => {
    await clearChatHistory()
    setMessages([])
    qc.invalidateQueries({ queryKey: ['assistant', 'history'] })
  }

  return (
    <>
      {/* ── Chat panel ────────────────────────────────────────────── */}
      {open && (
        <div className="fixed bottom-24 right-4 z-50 flex flex-col w-[360px] max-h-[560px] rounded-2xl border border-[#1f2d40] bg-[#0d1321] shadow-2xl overflow-hidden">

          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#1f2d40] bg-[#111827]">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-amber-500/15">
                <Sparkles className="h-3.5 w-3.5 text-amber-400" />
              </div>
              <div>
                <p className="text-sm font-bold text-[#f1f5f9]">Tradewell AI</p>
                <p className="text-[10px] text-[#475569]">Your portfolio assistant</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleClear}
                className="p-1.5 rounded-lg text-[#475569] hover:text-red-400 hover:bg-red-500/10 transition-colors"
                title="Clear history"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="p-1.5 rounded-lg text-[#475569] hover:text-[#f1f5f9] hover:bg-[#1a2235] transition-colors"
              >
                <ChevronDown className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
            {messages.length === 0 && (
              <div className="space-y-3">
                <p className="text-xs text-[#475569] text-center">
                  Ask me anything about your portfolio, bots, or trade history.
                </p>
                <div className="space-y-1.5">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => sendMessage(s)}
                      className="w-full text-left text-xs px-3 py-2 rounded-lg border border-[#1f2d40] text-[#94a3b8] hover:bg-[#1a2235] hover:text-[#f1f5f9] transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((msg) => (
              <Bubble key={msg.id} msg={msg} />
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="border-t border-[#1f2d40] p-3 bg-[#111827]">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your portfolio…"
                rows={1}
                disabled={isStreaming}
                className="flex-1 resize-none rounded-xl border border-[#1f2d40] bg-[#0a0e1a] px-3 py-2 text-sm text-[#f1f5f9] placeholder-[#475569] focus:outline-none focus:border-[#6366f1]/50 disabled:opacity-50 max-h-24 overflow-y-auto"
                style={{ fieldSizing: 'content' } as React.CSSProperties}
              />
              <button
                type="button"
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || isStreaming}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#6366f1] hover:bg-[#818cf8] text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isStreaming
                  ? <Loader2 className="h-4 w-4 animate-spin" />
                  : <Send className="h-4 w-4" />}
              </button>
            </div>
            <p className="mt-1.5 text-[10px] text-[#334155] text-center">
              Shift+Enter for new line · Enter to send
            </p>
          </div>
        </div>
      )}

      {/* ── Floating bubble ───────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'fixed bottom-6 right-[5.5rem] z-50 flex h-14 w-14 items-center justify-center',
          'rounded-full shadow-lg transition-all duration-200',
          open
            ? 'bg-[#1f2d40] text-[#94a3b8]'
            : 'bg-[#6366f1] text-white hover:bg-[#818cf8] hover:scale-105',
        )}
        aria-label="Toggle assistant"
      >
        {open ? (
          <X className="h-5 w-5" />
        ) : (
          <>
            <Sparkles className="h-5 w-5" />
            {unread > 0 && (
              <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                {unread}
              </span>
            )}
          </>
        )}
      </button>
    </>
  )
}

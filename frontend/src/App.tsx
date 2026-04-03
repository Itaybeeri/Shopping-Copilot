import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, ShoppingBag } from 'lucide-react'
import Message from './components/Message'
import ProductDetail from './components/ProductDetail'
import DebugPanel, { type DebugEvent } from './components/DebugPanel'
import type { ChatMessage, Product } from './types'

const SUGGESTIONS = [
  'Show me smartphones under $500',
  'What categories do you have?',
  'Find me beauty products',
]

function ChatApp() {
  const initialCategory = new URLSearchParams(window.location.search).get('category')
  const initialSearch = new URLSearchParams(window.location.search).get('search')

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [debugEvents, setDebugEvents] = useState<DebugEvent[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const debugIdRef = useRef(0)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const scrollRafRef = useRef<number | null>(null)
  const isNearBottomRef = useRef(true)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const autoTriggered = useRef(false)

  async function createSession(): Promise<string> {
    const res = await fetch('/api/session', { method: 'POST' })
    const data = await res.json()
    setSessionId(data.session_id)
    return data.session_id
  }

  useEffect(() => { createSession() }, [])

  const scheduleScroll = useCallback(() => {
    if (!isNearBottomRef.current) return
    if (scrollRafRef.current) cancelAnimationFrame(scrollRafRef.current)
    scrollRafRef.current = requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    })
  }, [])

  function handleScroll() {
    const el = scrollContainerRef.current
    if (!el) return
    isNearBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120
  }

  useEffect(() => {
    const last = messages[messages.length - 1]
    if (last?.role === 'user') {
      isNearBottomRef.current = true
      scheduleScroll()
    }
  }, [messages.length])

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return

    const userMsg: ChatMessage = { role: 'user', content: text }
    const history = [...messages, userMsg]
    setMessages(history)
    setInput('')
    setLoading(true)

    const productsRef: { current: Product[] } = { current: [] }
    const categoriesRef: { current: any[] } = { current: [] }
    const textRef: { current: string } = { current: '' }
    let rafPending = false

    function flushToState(done = false) {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: textRef.current,
          products: productsRef.current,
          categories: categoriesRef.current,
          streaming: !done,
        }
        return updated
      })
      scheduleScroll()
      rafPending = false
    }

    setMessages([...history, { role: 'assistant', content: '', streaming: true }])

    try {
      const sid = sessionId ?? await createSession()
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sid, message: text }),
      })

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const lines = decoder.decode(value).split('\n')
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6)
          if (data === '[DONE]') { flushToState(true); break }

          const parsed = JSON.parse(data)
          if (parsed.type === 'tool_call') {
            setDebugEvents(prev => [...prev, {
              id: debugIdRef.current++,
              type: 'tool_call',
              tool: parsed.tool,
              args: parsed.args,
              timestamp: new Date().toLocaleTimeString(),
            }])
          } else if (parsed.type === 'tool_result') {
            setDebugEvents(prev => [...prev, {
              id: debugIdRef.current++,
              type: 'tool_result',
              tool: parsed.tool,
              count: parsed.count,
              url: parsed.url,
              payload: parsed.payload,
              timestamp: new Date().toLocaleTimeString(),
            }])
          } else if (parsed.type === 'categories') {
            categoriesRef.current = parsed.categories
            flushToState()
          } else if (parsed.type === 'products') {
            productsRef.current = parsed.products
            flushToState()
          } else if (parsed.type === 'text') {
            textRef.current += parsed.content
            if (!rafPending) {
              rafPending = true
              requestAnimationFrame(() => flushToState())
            }
          }
        }
      }
    } catch {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = { ...updated[updated.length - 1], content: 'Something went wrong. Please try again.' }
        return updated
      })
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  useEffect(() => {
    if (autoTriggered.current) return
    if (initialCategory) {
      autoTriggered.current = true
      window.history.replaceState({}, '', '/')
      sendMessage(`Show me products in ${initialCategory}`)
    } else if (initialSearch) {
      autoTriggered.current = true
      window.history.replaceState({}, '', '/')
      sendMessage(`Show me products with tag: ${initialSearch}`)
    }
  }, [])

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Chat area */}
      <div className="flex flex-col flex-1 min-w-0 px-4">
        <header
          className="flex items-center gap-3 py-5 border-b border-white/8 cursor-pointer"
          onClick={() => {
            if (sessionId) fetch(`/api/session/${sessionId}`, { method: 'DELETE' })
            setMessages([]); setInput(''); setDebugEvents([])
            window.history.replaceState({}, '', '/')
            createSession()
          }}
        >
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center">
            <ShoppingBag size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-white">Shopping Copilot</h1>
            <p className="text-xs text-white/40">Powered by AI</p>
          </div>
        </header>

        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto py-6 flex flex-col gap-6"
        >
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center flex-1 gap-6 text-center">
              <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
                <ShoppingBag size={28} className="text-indigo-400" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white mb-1">What are you looking for?</h2>
                <p className="text-sm text-white/40">Ask me anything about products</p>
              </div>
              <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                {SUGGESTIONS.map(s => (
                  <button
                    key={s}
                    onClick={() => sendMessage(s)}
                    className="px-4 py-2 rounded-full bg-[#1e1e2a] border border-white/10 text-sm text-white/70 hover:border-indigo-500/50 hover:text-white transition-all duration-200"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => <Message key={i} message={m} />)
          )}

          {loading && messages[messages.length - 1]?.content === '' && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-[#2a2a38] border border-white/10 flex items-center justify-center">
                <div className="flex gap-1">
                  {[0, 1, 2].map(i => (
                    <span
                      key={i}
                      className="w-1 h-1 rounded-full bg-white/40"
                      style={{ animation: `blink 1.2s ${i * 0.2}s infinite` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <div className="py-4 border-t border-white/8">
          <div className="flex items-end gap-3 bg-[#1a1a24] border border-white/10 rounded-2xl px-4 py-3 focus-within:border-indigo-500/50 transition-colors">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about products..."
              rows={1}
              dir={/[\u0590-\u05FF]/.test(input) ? 'rtl' : 'ltr'}
              className="flex-1 bg-transparent text-sm text-white placeholder-white/30 resize-none outline-none max-h-32"
              style={{ fieldSizing: 'content' } as React.CSSProperties}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || loading}
              className="shrink-0 w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center disabled:opacity-30 hover:bg-indigo-500 transition-colors"
            >
              <Send size={14} className="text-white" />
            </button>
          </div>
        </div>
      </div>

      {/* Debug panel */}
      <DebugPanel events={debugEvents} />
    </div>
  )
}

export default function App() {
  if (new URLSearchParams(window.location.search).has('id')) {
    return <ProductDetail />
  }
  return <ChatApp />
}

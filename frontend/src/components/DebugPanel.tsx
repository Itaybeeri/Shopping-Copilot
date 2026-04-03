import { ExternalLink, ChevronDown, ChevronUp, Terminal, FileJson } from 'lucide-react'
import { useState } from 'react'

export interface DebugEvent {
  id: number
  type: 'tool_call' | 'tool_result'
  tool: string
  args?: Record<string, unknown>
  count?: number
  url?: string
  payload?: unknown
  timestamp: string
}

const TOOL_COLORS: Record<string, string> = {
  search_products: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
  get_products_by_category: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
  get_categories: 'text-green-400 bg-green-400/10 border-green-400/20',
  search_by_tag: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  search_by_field: 'text-orange-400 bg-orange-400/10 border-orange-400/20',
  sort_products: 'text-rose-400 bg-rose-400/10 border-rose-400/20',
  get_more_products: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20',
}

function JsonPayload({ data }: { data: unknown }) {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
      >
        <FileJson size={12} />
        {open ? 'Hide JSON payload' : 'Show JSON payload'}
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>
      {open && (
        <pre className="mt-2 text-xs text-white/50 bg-black/40 rounded-lg p-2 overflow-x-auto max-h-64 overflow-y-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  )
}

function EventRow({ event }: { event: DebugEvent }) {
  const [open, setOpen] = useState(false)
  const color = TOOL_COLORS[event.tool] ?? 'text-white/50 bg-white/5 border-white/10'
  const isCall = event.type === 'tool_call'

  return (
    <div className="border border-white/6 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/4 transition-colors text-left"
      >
        <span className={`text-xs font-mono px-1.5 py-0.5 rounded border ${color}`}>
          {isCall ? '→ call' : '← result'}
        </span>
        <span className="text-xs text-white/70 font-medium flex-1 truncate">{event.tool}</span>
        <span className="text-xs text-white/25 shrink-0">{event.timestamp}</span>
        {open ? <ChevronUp size={12} className="text-white/30 shrink-0" /> : <ChevronDown size={12} className="text-white/30 shrink-0" />}
      </button>

      {open && (
        <div className="px-3 pb-3 flex flex-col gap-3 border-t border-white/6">
          {isCall && event.args && (
            <div>
              <p className="text-xs text-white/30 mt-2 mb-1">Arguments</p>
              <pre className="text-xs text-white/60 bg-black/30 rounded-lg p-2 overflow-x-auto">
                {JSON.stringify(event.args, null, 2)}
              </pre>
            </div>
          )}

          {!isCall && (
            <div className="mt-2 flex flex-col gap-2">
              <p className="text-xs text-white/60 bg-black/30 rounded-lg p-2">
                {event.count !== undefined ? `${event.count} items returned` : 'No items'}
              </p>
              {event.payload !== undefined && <JsonPayload data={event.payload} />}
            </div>
          )}

          {event.url && (
            <div>
              <p className="text-xs text-white/30 mb-1">API URL</p>
              <a
                href={event.url.startsWith('http') ? event.url : undefined}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 bg-black/30 rounded-lg p-2 break-all transition-colors"
              >
                <ExternalLink size={10} className="shrink-0" />
                {event.url}
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function DebugPanel({ events }: { events: DebugEvent[] }) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className={`flex flex-col border-l border-white/8 bg-[#0d0d11] transition-all duration-300 ${collapsed ? 'w-10' : 'w-80'} shrink-0`}>
      <div
        className="flex items-center gap-2 px-3 py-4 border-b border-white/8 cursor-pointer hover:bg-white/4 transition-colors"
        onClick={() => setCollapsed(c => !c)}
      >
        <Terminal size={14} className="text-indigo-400 shrink-0" />
        {!collapsed && <span className="text-xs font-semibold text-white/60 uppercase tracking-widest flex-1">Debug</span>}
        {!collapsed && <span className="text-xs text-white/25">{events.length} events</span>}
      </div>

      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
          {events.length === 0 ? (
            <p className="text-xs text-white/25 text-center mt-8">No events yet.<br />Send a message to see the flow.</p>
          ) : (
            events.map(e => <EventRow key={e.id} event={e} />)
          )}
        </div>
      )}
    </div>
  )
}

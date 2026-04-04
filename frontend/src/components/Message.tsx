import { memo } from 'react'
import ReactMarkdown from 'react-markdown'
import { Bot, User, ChevronDown } from 'lucide-react'
import ProductCard from './ProductCard'
import CategoryChips from './CategoryChips'
import type { ChatMessage } from '../types'

function detectDir(text: string): 'rtl' | 'ltr' {
  return /[\u0590-\u05FF]/.test(text) ? 'rtl' : 'ltr'
}

function Message({ message, onShowMore }: { message: ChatMessage; onShowMore?: () => void }) {
  const isUser = message.role === 'user'
  const dir = message.content ? detectDir(message.content) : 'ltr'

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white
        ${isUser ? 'bg-indigo-600' : 'bg-[#2a2a38] border border-white/10'}`}>
        {isUser ? <User size={14} /> : <Bot size={14} />}
      </div>

      <div className={`flex flex-col gap-3 max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Category chips */}
        {message.categories && message.categories.length > 0 && (
          <CategoryChips categories={message.categories} />
        )}

        {/* Product grid - shown ABOVE text */}
        {message.products && message.products.length > 0 && (
          <div className="flex flex-col gap-3 w-full max-w-4xl">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {message.products.map((p, i) => (
                <ProductCard key={p.id} product={p} index={i} />
              ))}
            </div>
            {onShowMore && (
              <button
                onClick={onShowMore}
                className="flex items-center gap-2 self-center px-4 py-2 rounded-full bg-[#1e1e2a] border border-white/10 text-sm text-white/60 hover:border-indigo-500/50 hover:text-indigo-400 transition-all duration-200"
              >
                <ChevronDown size={14} />
                Show more results
              </button>
            )}
          </div>
        )}

        {/* Text bubble */}
        {message.content && (
          <div
            dir={dir}
            className={`px-4 py-3 rounded-2xl text-sm leading-relaxed
            ${isUser
              ? 'bg-indigo-600 text-white rounded-tr-sm'
              : 'bg-[#1e1e2a] text-white/85 border border-white/8 rounded-tl-sm'
            }`}>
            {isUser || message.streaming ? (
              <span className="whitespace-pre-wrap">{message.content}</span>
            ) : (
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className={`mb-2 last:mb-0 ${dir === 'rtl' ? 'text-right' : 'text-left'}`}>{children}</p>,
                  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                  ul: ({ children }) => <ul className={`list-disc mb-2 space-y-1 ${dir === 'rtl' ? 'pr-4 text-right' : 'pl-4 text-left'}`}>{children}</ul>,
                  ol: ({ children }) => <ol className={`list-decimal mb-2 space-y-1 ${dir === 'rtl' ? 'pr-4 text-right' : 'pl-4 text-left'}`}>{children}</ol>,
                  li: ({ children }) => <li className="text-white/85">{children}</li>,
                  h3: ({ children }) => <h3 className="font-bold text-white text-base mb-1">{children}</h3>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default memo(Message)
import { Star, Tag } from 'lucide-react'
import type { Product } from '../types'

export default function ProductCard({ product, index }: { product: Product; index: number }) {
  const discounted = product.discountPercentage > 0
  const finalPrice = discounted
    ? product.price * (1 - product.discountPercentage / 100)
    : product.price

  function openDetail() {
    window.open(`/?id=${product.id}`, '_blank')
  }

  return (
    <div
      onClick={openDetail}
      role="button"
      className="cursor-pointer animate-card-in bg-[#1a1a24] border border-white/8 rounded-2xl overflow-hidden flex flex-col hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-500/10 transition-all duration-300 group"
      style={{ animationDelay: `${index * 60}ms`, animationFillMode: 'both' }}
    >
      <div className="relative h-44 bg-[#111118] overflow-hidden">
        <img
          src={product.thumbnail}
          alt={product.title}
          className="w-full h-full object-contain p-3 group-hover:scale-105 transition-transform duration-500"
        />
        {discounted && (
          <span className="absolute top-2 right-2 bg-rose-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
            -{Math.round(product.discountPercentage)}%
          </span>
        )}
      </div>

      <div className="p-4 flex flex-col gap-2 flex-1">
        <h3 className="text-sm font-semibold text-white leading-snug line-clamp-2">{product.title}</h3>
        <p className="text-xs text-white/50 line-clamp-2 leading-relaxed">{product.description}</p>

        <div className="flex items-center gap-1 mt-auto pt-1">
          <Star size={11} className="text-amber-400 fill-amber-400" />
          <span className="text-xs text-white/60">{product.rating.toFixed(1)}</span>
          <span className="text-white/20 mx-1">·</span>
          <Tag size={11} className="text-white/30" />
          <span className="text-xs text-white/40 capitalize">{product.category}</span>
        </div>

        <div className="flex items-baseline gap-2 mt-1">
          <span className="text-lg font-bold text-indigo-400">${finalPrice.toFixed(2)}</span>
          {discounted && (
            <span className="text-xs text-white/30 line-through">${product.price.toFixed(2)}</span>
          )}
        </div>
      </div>
    </div>
  )
}

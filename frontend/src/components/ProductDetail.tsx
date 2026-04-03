import { useEffect, useState } from 'react'
import { Star, Tag, Package, Truck, ShieldCheck, ArrowRight } from 'lucide-react'
import type { Product } from '../types'

function detectDir(text: string): 'rtl' | 'ltr' {
  return /[\u0590-\u05FF]/.test(text) ? 'rtl' : 'ltr'
}

export default function ProductDetail() {
  const params = new URLSearchParams(window.location.search)
  const id = params.get('id')
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState(false)

  const [selectedImage, setSelectedImage] = useState<string | null>(null)

  useEffect(() => {
    if (!id) { setError(true); return }
    fetch(`https://dummyjson.com/products/${id}`)
      .then(r => r.json())
      .then(data => { setProduct(data); setSelectedImage(data.thumbnail) })
      .catch(() => setError(true))
  }, [id])

  if (error) return <div className="text-white p-8">Product not found.</div>
  if (!product) return (
    <div className="min-h-screen bg-[#0f0f13] flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
    </div>
  )

  const dir = detectDir(product.title + product.description)
  const discounted = product.discountPercentage > 0
  const finalPrice = discounted
    ? product.price * (1 - product.discountPercentage / 100)
    : product.price

  return (
    <div dir={dir} className="min-h-screen bg-[#0f0f13] text-white px-4 py-10 max-w-4xl mx-auto">
      <div className="grid md:grid-cols-2 gap-10">

        {/* Images */}
        <div className="flex flex-col gap-3">
          <div className="bg-[#1a1a24] rounded-2xl overflow-hidden h-80 flex items-center justify-center border border-white/8">
            <img src={selectedImage ?? product.thumbnail} alt={product.title} className="max-h-full max-w-full object-contain p-6" />
          </div>
          {product.images && product.images.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1">
              {product.images.map((img, i) => (
                <img
                  key={i}
                  src={img}
                  alt={`${product.title} ${i + 1}`}
                  onClick={() => setSelectedImage(img)}
                  className={`w-16 h-16 object-contain rounded-xl bg-[#1a1a24] border shrink-0 p-1 cursor-pointer transition-all duration-200
                    ${selectedImage === img ? 'border-indigo-500' : 'border-white/8 hover:border-white/30'}`}
                />
              ))}
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex flex-col gap-5">
          <div>
            {product.brand && <p className="text-xs text-indigo-400 uppercase tracking-widest mb-1">{product.brand}</p>}
            <h1 className="text-2xl font-bold text-white leading-snug">{product.title}</h1>
            <div className="flex items-center gap-2 mt-2">
              <Star size={14} className="text-amber-400 fill-amber-400" />
              <span className="text-sm text-white/70">{product.rating.toFixed(1)}</span>
              <span className="text-white/20">·</span>
              <Tag size={13} className="text-white/30" />
              <span
                onClick={() => window.open(`/?category=${encodeURIComponent(product.category)}`, '_self')}
                className="text-sm text-indigo-400 capitalize cursor-pointer hover:text-indigo-300 transition-colors"
              >
                {product.category}
              </span>
            </div>
          </div>

          <p className="text-sm text-white/60 leading-relaxed">{product.description}</p>

          {/* Price */}
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-bold text-indigo-400">${finalPrice.toFixed(2)}</span>
            {discounted && (
              <>
                <span className="text-base text-white/30 line-through">${product.price.toFixed(2)}</span>
                <span className="bg-rose-500/20 text-rose-400 text-xs font-bold px-2 py-0.5 rounded-full">
                  -{Math.round(product.discountPercentage)}% OFF
                </span>
              </>
            )}
          </div>

          {/* Meta */}
          <div className="grid grid-cols-2 gap-3">
            {product.availabilityStatus && (
              <div className="bg-[#1a1a24] border border-white/8 rounded-xl p-3 flex items-center gap-2">
                <Package size={14} className="text-indigo-400 shrink-0" />
                <span className="text-xs text-white/60">{product.availabilityStatus}</span>
              </div>
            )}
            {product.shippingInformation && (
              <div className="bg-[#1a1a24] border border-white/8 rounded-xl p-3 flex items-center gap-2">
                <Truck size={14} className="text-indigo-400 shrink-0" />
                <span className="text-xs text-white/60">{product.shippingInformation}</span>
              </div>
            )}
            {product.warrantyInformation && (
              <div className="bg-[#1a1a24] border border-white/8 rounded-xl p-3 flex items-center gap-2 col-span-2">
                <ShieldCheck size={14} className="text-indigo-400 shrink-0" />
                <span className="text-xs text-white/60">{product.warrantyInformation}</span>
              </div>
            )}
          </div>

          {product.tags && product.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {product.tags.map(tag => (
                <span
                  key={tag}
                  onClick={() => window.open(`/?search=${encodeURIComponent(tag)}`, '_self')}
                  className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-white/50 cursor-pointer hover:border-indigo-500/50 hover:text-indigo-400 transition-all duration-200"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          <a
            href={`https://dummyjson.com/products/${product.id}`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 text-sm text-indigo-400 hover:text-indigo-300 transition-colors mt-auto"
          >
            View raw data <ArrowRight size={14} />
          </a>
        </div>
      </div>
    </div>
  )
}

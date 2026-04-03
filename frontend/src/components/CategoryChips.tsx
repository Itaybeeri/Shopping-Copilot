import type { Category } from '../types'

export default function CategoryChips({ categories }: { categories: Category[] }) {
  function handleClick(slug: string) {
    window.open(`/?category=${encodeURIComponent(slug)}`, '_self')
  }

  return (
    <div className="flex flex-wrap gap-2">
      {categories.map(cat => (
        <button
          key={cat.slug}
          onClick={() => handleClick(cat.slug)}
          className="px-3 py-1.5 rounded-full bg-[#1e1e2a] border border-white/10 text-sm text-white/70 capitalize hover:border-indigo-500/50 hover:text-indigo-400 hover:bg-indigo-500/10 transition-all duration-200"
        >
          {cat.name}
        </button>
      ))}
    </div>
  )
}

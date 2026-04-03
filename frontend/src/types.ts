export interface Product {
  id: number
  title: string
  description: string
  price: number
  discountPercentage: number
  rating: number
  stock: number
  category: string
  brand?: string
  thumbnail: string
  images?: string[]
  tags?: string[]
  availabilityStatus?: string
  shippingInformation?: string
  warrantyInformation?: string
}

export interface Category {
  slug: string
  name: string
  url: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  products?: Product[]
  categories?: Category[]
  streaming?: boolean
}

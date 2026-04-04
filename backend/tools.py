import time
import httpx

BASE_URL = "https://dummyjson.com/products"
LIMIT = 8
CACHE_TTL = 300  # seconds (5 minutes)

_cache: dict[str, tuple[any, float]] = {}


def _get(key: str):
    entry = _cache.get(key)
    if entry and time.time() - entry[1] < CACHE_TTL:
        return entry[0]
    return None


def _set(key: str, value):
    _cache[key] = (value, time.time())


async def search_products(query: str, max_price: float | None = None, min_price: float | None = None, min_rating: float | None = None, max_rating: float | None = None) -> dict:
    key = f"search:{query.lower()}:{min_price}:{max_price}:{min_rating}:{max_rating}"
    if cached := _get(key):
        return cached
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/search", params={"q": query, "limit": 100})
        r.raise_for_status()
        data = r.json()
    products = data["products"]
    if max_price is not None:
        products = [p for p in products if p["price"] <= max_price]
    if min_price is not None:
        products = [p for p in products if p["price"] >= min_price]
    if min_rating is not None:
        products = [p for p in products if p.get("rating", 0) >= min_rating]
    if max_rating is not None:
        products = [p for p in products if p.get("rating", 0) <= max_rating]
    result = {"products": products[:LIMIT], "total": len(products)}
    _set(key, result)
    return result


async def get_products_by_category(slug: str, max_price: float | None = None, min_price: float | None = None, min_rating: float | None = None, max_rating: float | None = None) -> dict:
    key = f"category:{slug.lower()}:{min_price}:{max_price}:{min_rating}:{max_rating}"
    if cached := _get(key):
        return cached
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/category/{slug}", params={"limit": 100})
        r.raise_for_status()
        data = r.json()
    products = data["products"]
    if max_price is not None:
        products = [p for p in products if p["price"] <= max_price]
    if min_price is not None:
        products = [p for p in products if p["price"] >= min_price]
    if min_rating is not None:
        products = [p for p in products if p.get("rating", 0) >= min_rating]
    if max_rating is not None:
        products = [p for p in products if p.get("rating", 0) <= max_rating]
    result = {"products": products[:LIMIT], "total": len(products)}
    _set(key, result)
    return result


async def get_categories() -> list:
    key = "categories"
    if cached := _get(key):
        return cached
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/categories")
        r.raise_for_status()
        result = r.json()
    _set(key, result)
    return result


async def search_by_tag(tag: str) -> dict:
    key = f"tag:{tag.lower()}"
    if cached := _get(key):
        return cached
    async with httpx.AsyncClient() as client:
        r = await client.get(BASE_URL, params={"limit": 0})
        r.raise_for_status()
        all_products = r.json()["products"]
    tag_lower = tag.lower()
    matched = [p for p in all_products if any(tag_lower in t.lower() for t in p.get("tags", []))]
    result = {"products": matched[:LIMIT], "total": len(matched)}
    _set(key, result)
    return result


async def search_by_field(field: str, value: str) -> dict:
    key = f"field:{field.lower()}:{value.lower()}"
    if cached := _get(key):
        return cached
    async with httpx.AsyncClient() as client:
        r = await client.get(BASE_URL, params={"limit": 0})
        r.raise_for_status()
        all_products = r.json()["products"]
    value_lower = value.lower()
    matched = [p for p in all_products if value_lower in str(p.get(field, "")).lower()]
    result = {"products": matched[:LIMIT], "total": len(matched)}
    _set(key, result)
    return result


async def filter_in_memory(min_rating: float | None = None, max_rating: float | None = None, max_price: float | None = None, min_price: float | None = None) -> dict:
    """Marker function — actual filtering happens in stream_chat using last products in session."""
    return {"filter": {"min_rating": min_rating, "max_rating": max_rating, "max_price": max_price, "min_price": min_price}}


async def sort_products(sort_by: str, order: str = "asc", skip: int = 0) -> dict:
    key = f"sort:{sort_by}:{order}:{skip}"
    if cached := _get(key):
        return cached
    async with httpx.AsyncClient() as client:
        r = await client.get(BASE_URL, params={"limit": LIMIT, "skip": skip, "sortBy": sort_by, "order": order})
        r.raise_for_status()
        result = r.json()
    _set(key, result)
    return result


async def get_more_products(context: str, skip: int) -> dict:
    key = f"more:{context.lower()}:{skip}"
    if cached := _get(key):
        return cached
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/search", params={"q": context, "limit": LIMIT, "skip": skip})
        r.raise_for_status()
        result = r.json()
    _set(key, result)
    return result


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search for products by keyword with optional filters. Use when the user mentions product names or descriptive terms. Extract price/rating constraints separately — do NOT include them in the query string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword only (e.g. 'smartphones', 'laptop')"},
                    "max_price": {"type": "number", "description": "Maximum price filter"},
                    "min_price": {"type": "number", "description": "Minimum price filter"},
                    "min_rating": {"type": "number", "description": "Minimum rating filter e.g. 4"},
                    "max_rating": {"type": "number", "description": "Maximum rating filter e.g. 3 for 'below 3'"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_products_by_category",
            "description": "Get products from a specific category. PREFER this over search_products when the user mentions a known category. Supports price and rating filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Category slug e.g. smartphones, beauty, laptops"},
                    "max_price": {"type": "number", "description": "Maximum price filter"},
                    "min_price": {"type": "number", "description": "Minimum price filter"},
                    "min_rating": {"type": "number", "description": "Minimum rating filter e.g. 4"},
                    "max_rating": {"type": "number", "description": "Maximum rating filter e.g. 3 for 'below 3'"},
                },
                "required": ["slug"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_categories",
            "description": "Get all available product categories.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_by_tag",
            "description": "Find products by a specific tag.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {"type": "string", "description": "Tag to filter by e.g. 'face powder'"}
                },
                "required": ["tag"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_by_field",
            "description": "Search products by a specific field value such as brand, sku, availabilityStatus.",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "description": "Field name e.g. 'brand', 'availabilityStatus'"},
                    "value": {"type": "string", "description": "Value to search for e.g. 'IWC'"},
                },
                "required": ["field", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_in_memory",
            "description": "Filter the results ALREADY shown to the user. Use when the user wants to narrow down current results by rating or price — do NOT fetch new data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_rating": {"type": "number", "description": "Keep only products with rating >= this value"},
                    "max_rating": {"type": "number", "description": "Keep only products with rating <= this value e.g. 4 for 'below 4'"},
                    "max_price": {"type": "number", "description": "Keep only products with price <= this value"},
                    "min_price": {"type": "number", "description": "Keep only products with price >= this value"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sort_products",
            "description": "Sort the results ALREADY shown to the user by price or rating. Use when user asks to sort current results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sort_by": {"type": "string", "description": "Field to sort by: 'price' or 'rating'"},
                    "order": {"type": "string", "description": "'asc' for lowest first, 'desc' for highest first"},
                },
                "required": ["sort_by", "order"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_more_products",
            "description": "Get more results for a previous search query. Use when the user asks to see more products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "context": {"type": "string", "description": "The original search query"},
                    "skip": {"type": "integer", "description": "Number of products to skip (8 for page 2, 16 for page 3)"},
                },
                "required": ["context", "skip"],
            },
        },
    },
]

TOOL_MAP = {
    "search_products": search_products,
    "get_products_by_category": get_products_by_category,
    "get_categories": get_categories,
    "search_by_tag": search_by_tag,
    "search_by_field": search_by_field,
    "filter_in_memory": filter_in_memory,
    "sort_products": sort_products,
    "get_more_products": get_more_products,
}

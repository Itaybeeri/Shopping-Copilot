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


async def search_products(query: str, max_price: float | None = None, min_price: float | None = None) -> dict:
    key = f"search:{query.lower()}:{min_price}:{max_price}"
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
    result = {"products": products[:LIMIT], "total": len(products)}
    _set(key, result)
    return result


async def get_products_by_category(slug: str, max_price: float | None = None, min_price: float | None = None) -> dict:
    key = f"category:{slug.lower()}:{min_price}:{max_price}"
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
            "description": "Search for products by keyword with optional price filtering. Use when the user mentions product names, brands, or descriptive terms. Extract price constraints separately into min_price/max_price — do NOT include price in the query string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword only, no price (e.g. 'smartphones', 'laptop', 'face cream')"},
                    "max_price": {"type": "number", "description": "Maximum price filter e.g. 500 for 'under $500'"},
                    "min_price": {"type": "number", "description": "Minimum price filter e.g. 100 for 'over $100'"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_products_by_category",
            "description": "Get products from a specific category with optional price filtering. PREFER this over search_products when the user mentions a known category name like smartphones, beauty, laptops, groceries, furniture etc. Extract price constraints into min_price/max_price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Category slug e.g. smartphones, beauty, laptops, groceries, furniture"},
                    "max_price": {"type": "number", "description": "Maximum price filter e.g. 500 for 'under $500'"},
                    "min_price": {"type": "number", "description": "Minimum price filter e.g. 100 for 'over $100'"},
                },
                "required": ["slug"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_categories",
            "description": "Get all available product categories. Use when the user asks what categories or types of products are available.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_by_tag",
            "description": "Find products by a specific tag. Use when the user asks for products with a specific tag.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {"type": "string", "description": "The tag to filter products by e.g. 'face powder', 'beauty'"}
                },
                "required": ["tag"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_by_field",
            "description": "Search products by any specific field value such as brand, sku, availabilityStatus, shippingInformation, warrantyInformation. Use when the user asks for a specific brand or other product attribute.",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "description": "Product field to search in e.g. 'brand', 'sku', 'availabilityStatus'"},
                    "value": {"type": "string", "description": "Value to search for e.g. 'IWC', 'In Stock', 'Ships overnight'"},
                },
                "required": ["field", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sort_products",
            "description": "Get products sorted by a field. Use when user asks for cheapest, most expensive, highest rated, or wants products sorted by price or rating.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sort_by": {"type": "string", "description": "Field to sort by: 'price' or 'rating'"},
                    "order": {"type": "string", "description": "'asc' for cheapest/lowest first, 'desc' for most expensive/highest first"},
                    "skip": {"type": "integer", "description": "Number of products to skip for pagination, default 0"},
                },
                "required": ["sort_by", "order"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_more_products",
            "description": "Get more results for a previous search query. Use when the user asks to see more products or next page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "context": {"type": "string", "description": "The original search query to paginate"},
                    "skip": {"type": "integer", "description": "Number of products to skip (e.g. 8 for second page, 16 for third)"},
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
    "sort_products": sort_products,
    "get_more_products": get_more_products,
}

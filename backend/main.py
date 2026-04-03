import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

from tools import TOOL_DEFINITIONS, TOOL_MAP

load_dotenv()

app = FastAPI()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """You are a friendly and enthusiastic shopping copilot. Help users discover products they'll love.
Always use the available tools to fetch real product data before responding.
Product results are already displayed as visual cards to the user — do NOT list or repeat product names, prices or details in your text response.
Categories are displayed as clickable chips — do NOT list category names in your text response. Just write one short sentence like 'Here are all available categories:'
Instead, write a short warm intro (1-2 sentences) before the results, and optionally a brief closing tip.
Format your responses using markdown. If the user writes in Hebrew, respond entirely in Hebrew.
Tool selection rules:
- If the user mentions a known category (smartphones, beauty, laptops, groceries, furniture, etc.) — ALWAYS use get_products_by_category, never search_products
- If the user mentions a price constraint (under $X, over $X, less than $X) — pass it as max_price or min_price, never include price in the query string
- If the user mentions a specific tag — use search_by_tag
- If the user wants sorted results (cheapest, highest rated) — use sort_products
- If the user asks for more results — use get_more_products
- For all other keyword searches — use search_products
Never make up product data — always use tool results."""


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


async def run_tool(name: str, arguments: str) -> str:
    args = json.loads(arguments)
    result = await TOOL_MAP[name](**args)
    return json.dumps(result)


async def stream_chat(messages: list[dict]):
    conversation = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    while True:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            stream=False,
        )

        message = response.choices[0].message

        if message.tool_calls:
            conversation.append(message)
            for tc in message.tool_calls:
                args = json.loads(tc.function.arguments)
                # Stream tool call event to frontend
                yield f"data: {json.dumps({'type': 'tool_call', 'tool': tc.function.name, 'args': args})}\n\n"
                tool_result = await run_tool(tc.function.name, tc.function.arguments)
                result_data = json.loads(tool_result)
                if isinstance(result_data, list):
                    count = len(result_data)
                elif isinstance(result_data, dict):
                    count = len(result_data.get('products', []))
                else:
                    count = 0
                yield f"data: {json.dumps({'type': 'tool_result', 'tool': tc.function.name, 'count': count, 'url': _tool_url(tc.function.name, args), 'payload': result_data})}\n\n"
                conversation.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })
            continue

        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation,
            stream=True,
        )

        products = []
        categories = []
        for msg in reversed(conversation):
            if msg.get("role") == "tool":
                data = json.loads(msg["content"])
                if isinstance(data, list):
                    categories = data
                elif "products" in data:
                    products = data["products"]
                break

        if categories:
            yield f"data: {json.dumps({'type': 'categories', 'categories': categories})}\n\n"

        if products:
            yield f"data: {json.dumps({'type': 'products', 'products': products})}\n\n"

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield f"data: {json.dumps({'type': 'text', 'content': delta})}\n\n"

        yield "data: [DONE]\n\n"
        break


def _tool_url(name: str, args: dict) -> str:
    base = "https://dummyjson.com/products"
    if name == "search_products":
        url = f"{base}/search?q={args.get('query')}&limit=100"
        if args.get('max_price'): url += f" (max ${args.get('max_price')})"
        if args.get('min_price'): url += f" (min ${args.get('min_price')})"
        return url
    if name == "get_products_by_category":
        url = f"{base}/category/{args.get('slug')}?limit=100"
        if args.get('max_price'): url += f" (max ${args.get('max_price')})"
        if args.get('min_price'): url += f" (min ${args.get('min_price')})"
        return url
    if name == "get_categories":        return f"{base}/categories"
    if name == "search_by_tag":         return f"{base}?limit=0 (filter tag: {args.get('tag')})"
    if name == "search_by_field":        return f"{base}?limit=0 (filter {args.get('field')}: {args.get('value')})"
    if name == "sort_products":         return f"{base}?limit=8&sortBy={args.get('sort_by')}&order={args.get('order')}"
    if name == "get_more_products":     return f"{base}/search?q={args.get('context')}&limit=8&skip={args.get('skip')}"
    return base


@app.post("/api/chat")
async def chat(req: ChatRequest):
    messages = [m.model_dump() for m in req.messages]
    return StreamingResponse(stream_chat(messages), media_type="text/event-stream")


# Serve React static build in production
static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/")
    async def serve_root():
        return FileResponse(static_dir / "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(static_dir / "index.html")

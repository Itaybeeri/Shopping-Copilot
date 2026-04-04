import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
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

_sessions: dict[str, list[dict]] = {}

SYSTEM_PROMPT = """You are a friendly and enthusiastic shopping copilot. Help users discover products they'll love.
Always use the available tools to fetch real product data before responding.
Product results are already displayed as visual cards to the user — do NOT list or repeat product names, prices or details in your text response.
Categories are displayed as clickable chips — do NOT list category names in your text response. Just write one short sentence like 'Here are all available categories:'
Instead, write a short warm intro (1-2 sentences) before the results, and optionally a brief closing tip.
Format your responses using markdown. If the user writes in Hebrew, respond entirely in Hebrew.
Tool selection rules:
- If the user mentions a known category (smartphones, beauty, laptops, groceries, furniture, etc.) — ALWAYS use get_products_by_category, never search_products
- If the user mentions a price constraint (under $X, over $X, less than $X) — pass it as max_price or min_price, never include price in the query string
- If the user mentions a rating constraint (above X, more than X stars) — pass it as min_rating; (below X, less than X stars) — pass it as max_rating
- If the user mentions a specific tag — use search_by_tag
- If the user wants to sort or filter the CURRENT results (by rating, price etc.) — ALWAYS use filter_in_memory or sort_products, NEVER call search_products or get_products_by_category again. This applies when the user says things like 'only show', 'filter', 'מתחת ל', 'מעל', 'פחות מ', 'יותר מ' after already seeing results.
- If the user asks for more results — use get_more_products
- For all other keyword searches — use search_products
Never make up product data — always use tool results."""

SUMMARY_THRESHOLD = 10


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/api/session")
async def create_session():
    session_id = str(uuid.uuid4())
    _sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return JSONResponse({"session_id": session_id})


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    _sessions.pop(session_id, None)
    return JSONResponse({"ok": True})


async def run_tool(name: str, arguments: str) -> str:
    args = json.loads(arguments)
    result = await TOOL_MAP[name](**args)
    return json.dumps(result)


def _get_last_products(conversation: list) -> list:
    """Extract the most recent ORIGINAL API product list, skipping in-memory operations."""
    for msg in reversed(conversation):
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
        if role == "tool":
            try:
                content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                data = json.loads(content)
                if isinstance(data, dict) and data.get("in_memory"):
                    continue
                if isinstance(data, dict) and "products" in data:
                    return data["products"]
            except Exception:
                pass
    return []


def sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def _maybe_summarize(conversation: list[dict]) -> None:
    """Summarize old messages once conversation exceeds threshold, keeping full tool sequences intact."""
    exchanges = [m for m in conversation if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
    if len(exchanges) < SUMMARY_THRESHOLD:
        return

    system_msg = conversation[0]

    transcript = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in conversation[1:]
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content")
    )

    summary_response = await client.chat.completions.create(
        model="gpt-5.4-mini",
        messages=[
            {"role": "system", "content": "Summarize the following shopping conversation concisely in 3-5 sentences. Focus on what the user was looking for, filters applied, and what was shown."},
            {"role": "user", "content": transcript},
        ],
        stream=False,
    )
    summary = summary_response.choices[0].message.content

    # Find the last complete user→assistant exchange (no dangling tool calls)
    # Walk backwards to find a clean assistant message (no tool_calls) and its preceding user message
    safe_tail = []
    i = len(conversation) - 1
    while i >= 1 and len(safe_tail) < 4:
        msg = conversation[i]
        if not isinstance(msg, dict):
            i -= 1
            continue
        role = msg.get("role")
        # Only include clean user/assistant messages — skip tool messages and assistant messages with tool_calls
        if role in ("user", "assistant") and not msg.get("tool_calls"):
            safe_tail.insert(0, msg)
        i -= 1

    conversation.clear()
    conversation.append(system_msg)
    conversation.append({"role": "system", "content": f"[Conversation summary so far]: {summary}"})
    conversation.extend(safe_tail)


async def stream_chat(session_id: str, user_message: str):
    conversation = _sessions.get(session_id)
    if conversation is None:
        yield sse({"type": "text", "content": "Session not found."})
        yield "data: [DONE]\n\n"
        return

    conversation.append({"role": "user", "content": user_message})
    assistant_text = ""

    while True:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=conversation,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            stream=False,
        )

        message = response.choices[0].message

        if message.tool_calls:
            conversation.append(message.model_dump())

            # Collect all filter_in_memory calls and merge into one operation
            filter_args_merged: dict = {}
            regular_calls = []
            for tc in message.tool_calls:
                args = json.loads(tc.function.arguments)
                if tc.function.name == "filter_in_memory":
                    filter_args_merged.update({k: v for k, v in args.items() if v is not None})
                else:
                    regular_calls.append(tc)

            if filter_args_merged:
                yield sse({"type": "tool_call", "tool": "filter_in_memory", "args": filter_args_merged})
                last_products = _get_last_products(conversation)
                filtered = list(last_products)
                if filter_args_merged.get("min_rating") is not None:
                    filtered = [p for p in filtered if p.get("rating", 0) >= filter_args_merged["min_rating"]]
                if filter_args_merged.get("max_rating") is not None:
                    filtered = [p for p in filtered if p.get("rating", 0) <= filter_args_merged["max_rating"]]
                if filter_args_merged.get("max_price") is not None:
                    filtered = [p for p in filtered if p["price"] <= filter_args_merged["max_price"]]
                if filter_args_merged.get("min_price") is not None:
                    filtered = [p for p in filtered if p["price"] >= filter_args_merged["min_price"]]
                result_data = {"products": filtered, "total": len(filtered), "in_memory": True}
                tool_result = json.dumps(result_data)
                yield sse({"type": "tool_result", "tool": "filter_in_memory", "count": len(filtered), "url": f"(filtered in memory: {filter_args_merged})", "payload": result_data})
                for tc in message.tool_calls:
                    if tc.function.name == "filter_in_memory":
                        conversation.append({"role": "tool", "tool_call_id": tc.id, "content": tool_result})

            for tc in regular_calls:
                args = json.loads(tc.function.arguments)
                yield sse({"type": "tool_call", "tool": tc.function.name, "args": args})

                if tc.function.name == "sort_products":
                    last_products = _get_last_products(conversation)
                    if last_products:
                        reverse = args.get("order", "asc") == "desc"
                        sort_key = args.get("sort_by", "price")
                        sorted_products = sorted(last_products, key=lambda p: p.get(sort_key, 0), reverse=reverse)
                        result_data = {"products": sorted_products, "total": len(sorted_products), "in_memory": True}
                        tool_result = json.dumps(result_data)
                        yield sse({"type": "tool_result", "tool": tc.function.name, "count": len(sorted_products), "url": f"(sorted in memory by {sort_key} {args.get('order', 'asc')})", "payload": result_data})
                        conversation.append({"role": "tool", "tool_call_id": tc.id, "content": tool_result})
                        continue

                tool_result = await run_tool(tc.function.name, tc.function.arguments)
                result_data = json.loads(tool_result)
                count = len(result_data) if isinstance(result_data, list) else len(result_data.get("products", []))
                yield sse({"type": "tool_result", "tool": tc.function.name, "count": count, "url": _tool_url(tc.function.name, args), "payload": result_data})
                conversation.append({"role": "tool", "tool_call_id": tc.id, "content": tool_result})
            continue

        stream = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=conversation,
            stream=True,
        )

        products = []
        categories = []
        for msg in reversed(conversation):
            if isinstance(msg, dict) and msg.get("role") == "tool":
                data = json.loads(msg["content"])
                if isinstance(data, list):
                    categories = data
                elif "products" in data:
                    products = data["products"]
                break

        if categories:
            yield sse({"type": "categories", "categories": categories})
        if products:
            yield sse({"type": "products", "products": products})

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                assistant_text += delta
                yield sse({"type": "text", "content": delta})

        conversation.append({"role": "assistant", "content": assistant_text})
        await _maybe_summarize(conversation)
        yield "data: [DONE]\n\n"
        break


def _tool_url(name: str, args: dict) -> str:
    base = "https://dummyjson.com/products"
    if name == "search_products":
        url = f"{base}/search?q={args.get('query')}&limit=100"
        if args.get("max_price"): url += f" (max ${args.get('max_price')})"
        if args.get("min_price"): url += f" (min ${args.get('min_price')})"
        return url
    if name == "get_products_by_category":
        url = f"{base}/category/{args.get('slug')}?limit=100"
        if args.get("max_price"): url += f" (max ${args.get('max_price')})"
        if args.get("min_price"): url += f" (min ${args.get('min_price')})"
        return url
    if name == "get_categories":    return f"{base}/categories"
    if name == "search_by_tag":     return f"{base}?limit=0 (filter tag: {args.get('tag')})"
    if name == "search_by_field":   return f"{base}?limit=0 (filter {args.get('field')}: {args.get('value')})"
    if name == "sort_products":     return f"(sorted in memory by {args.get('sort_by')} {args.get('order')})"
    if name == "get_more_products": return f"{base}/search?q={args.get('context')}&limit=8&skip={args.get('skip')}"
    return base


@app.post("/api/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(stream_chat(req.session_id, req.message), media_type="text/event-stream")


static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/")
    async def serve_root():
        return FileResponse(static_dir / "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(static_dir / "index.html")

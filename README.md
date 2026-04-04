# Shopping Copilot

An AI-powered shopping assistant that helps users discover products through a conversational interface. Built with FastAPI (Python) on the backend and React + TypeScript on the frontend.

## Prerequisites

- Python 3.9+
- Node.js 18+
- An OpenAI API key

## Setup

**1. Add your API key**

```powershell
copy backend\.env.example backend\.env
```

Edit `backend\.env` and set your `OPENAI_API_KEY`.

**2. Run setup (once)**

```powershell
.\setup.ps1
```

This checks all prerequisites (Node.js 18+, Python 3.9+, npm, pip, .env), installs all dependencies, and builds the React frontend.

**3. Run the app**

```powershell
.\run.ps1
```

Open http://localhost:8000 in your browser.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│                                                         │
│   ┌─────────────────────┐   ┌─────────────────────┐    │
│   │      Chat UI        │   │    Debug Panel      │    │
│   │  (React + Tailwind) │   │  (tool call trace)  │    │
│   └────────┬────────────┘   └──────────┬──────────┘    │
│            │  POST /api/chat (SSE)      │               │
└────────────┼───────────────────────────┼───────────────┘
             │                           │
┌────────────▼───────────────────────────▼───────────────┐
│                   FastAPI (Python)                      │
│                                                         │
│   ┌─────────────────────────────────────────────────┐  │
│   │              stream_chat()                      │  │
│   │   Agentic loop: call OpenAI → execute tools     │  │
│   │   → stream SSE events back to browser           │  │
│   └──────────────────┬──────────────────────────────┘  │
│                      │                                  │
│   ┌──────────────────▼──────────────────────────────┐  │
│   │              tools.py                           │  │
│   │   In-memory cache (TTL: 5 min)                  │  │
│   │   8 tool functions → DummyJSON API calls        │  │
│   └──────────────────┬──────────────────────────────┘  │
└─────────────────────-┼──────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────┐
│              DummyJSON API (dummyjson.com)               │
│              194 products, 35 categories                 │
└─────────────────────────────────────────────────────────┘
```

### Request flow

```
1. Browser calls POST /api/session on load → receives a session_id
2. User types a message
3. Browser POSTs to /api/chat with session_id + message only (no history)
4. FastAPI looks up the conversation history from the server-side session store
5. Appends the user message and calls OpenAI (gpt-5.4-mini) with tool definitions
6. OpenAI decides which tool to call based on user intent
7. Backend executes the tool (checks cache → calls DummyJSON if needed)
8. Tool result is added to conversation and OpenAI is called again
9. OpenAI generates a text response
10. Backend streams SSE events to the browser:
    - tool_call  → debug panel shows which tool was called + args
    - tool_result → debug panel shows result count + API URL + JSON payload
    - products   → chat renders product cards
    - categories → chat renders clickable category chips
    - text       → chat streams the AI text response
11. Assistant reply is saved back to the session store
12. Stream ends with [DONE]
13. On chat reset → browser calls DELETE /api/session/{id} and creates a new session
```

---

## Project Structure

```
├── backend/
│   ├── main.py          # FastAPI app, SSE streaming, agentic loop
│   ├── tools.py         # Tool functions, cache, tool definitions
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   └── src/
│       ├── App.tsx              # Router + ChatApp component
│       ├── types.ts             # Shared TypeScript types
│       └── components/
│           ├── Message.tsx      # Chat bubble (text + products + categories)
│           ├── ProductCard.tsx  # Product card widget
│           ├── ProductDetail.tsx # Full product detail page
│           ├── CategoryChips.tsx # Clickable category pills
│           └── DebugPanel.tsx   # Right-side tool call inspector
│
├── setup.ps1    # One-time setup with preflight checks
├── run.ps1      # Single command to start the app
└── README.md
```

---

## Backend Components

### `main.py`

The FastAPI application. Responsibilities:

- Serves the pre-built React frontend as static files (single port, single process)
- Exposes `POST /api/session` to create a new session (returns a UUID session_id)
- Exposes `DELETE /api/session/{id}` to clear a session on chat reset
- Exposes `POST /api/chat` which accepts `session_id` + `message` and returns a `StreamingResponse` (SSE)
- Maintains server-side conversation history in `_sessions` dict — the browser never sends history
- Runs the **agentic loop**: calls OpenAI → executes tool calls → loops until no more tool calls → streams final response
- Intercepts `sort_products` and `filter_in_memory` calls to operate on the last API results in memory — no extra DummyJSON call needed
- Multiple `filter_in_memory` calls in the same turn are merged into one combined filter operation
- Implements **conversation summary memory**: after every 10 exchanges, summarizes the conversation history and replaces it with a compact summary to keep the context window small
- Streams 5 SSE event types: `tool_call`, `tool_result`, `products`, `categories`, `text`
- The system prompt contains explicit tool selection rules to guide the model

### `tools.py`

All product data fetching logic. Responsibilities:

- Defines 8 tools exposed to the OpenAI model
- Implements a **TTL-based in-memory cache** (5 minutes) — repeated queries skip DummyJSON entirely
- All price, rating, and field filtering is done locally after fetching (DummyJSON has no filter API)

#### Tool reference

| Tool                       | DummyJSON endpoint                  | When triggered                              | Notes                                                                  |
| -------------------------- | ----------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------- |
| `search_products`          | `/products/search?q=`               | Generic keyword search                      | Supports `min_price` / `max_price` / `min_rating` / `max_rating`       |
| `get_products_by_category` | `/products/category/{slug}`         | User mentions a category name               | Preferred over search when category is known. Supports all filters     |
| `get_categories`           | `/products/categories`              | User asks what's available                  | Returns list rendered as clickable chips                               |
| `search_by_tag`            | `/products` (all, filtered locally) | User mentions a tag                         | Fetches all 194 products, filters by tag match                         |
| `search_by_field`          | `/products` (all, filtered locally) | User mentions brand, SKU, availability etc. | Filters any product field by value                                     |
| `filter_in_memory`         | No API call                         | User refines current results                | Filters last API results by rating/price without a new fetch           |
| `sort_products`            | No API call                         | User asks to sort current results           | Sorts last API results in memory by price or rating                    |
| `get_more_products`        | `/products/search?skip=`            | User asks for more results                  | Paginates previous search with skip offset                             |

#### Cache behavior

- Cache is **server-side only** (Python in-memory dict), not stored in the browser
- Cache key includes all query parameters (e.g. `category:smartphones:None:500`)
- Cache is cleared on server restart
- All users share the same cache

---

## Frontend Components

### `App.tsx`

Top-level router. If `?id=` is in the URL it renders `ProductDetail`, otherwise renders `ChatApp`.

`ChatApp` manages:

- Conversation display state (`messages`) — UI only, history lives on the server
- Session lifecycle: creates a session on mount via `POST /api/session`, deletes it on reset
- Sends only `{ session_id, message }` per request — no history in the payload
- SSE stream parsing — routes each event type to the correct state update
- Debug events state passed to `DebugPanel`
- Auto-trigger on `?category=` or `?search=` URL params (used when navigating back from product detail)
- Header click resets the entire chat, deletes the old session and creates a new one

### `Message.tsx`

Renders a single chat message. Handles:

- User messages: plain text bubble (right-aligned)
- Assistant messages: category chips + product grid + markdown text (left-aligned)
- Product grid shows a **Show more** button on the last message to trigger pagination
- RTL detection: if the text contains Hebrew characters (`\u0590-\u05FF`), sets `dir="rtl"` on the bubble
- During streaming: renders plain `<span>` to avoid ReactMarkdown re-parsing on every token. Switches to full markdown rendering only when streaming is complete

### `ProductCard.tsx`

Renders a single product in the grid. Shows:

- Product image with hover zoom
- Discount badge (if applicable)
- Title, description (truncated), rating, category
- Final price with original price struck through if discounted
- Clicking opens the product detail page in a new tab (`/?id={id}`)

### `ProductDetail.tsx`

Full product detail page rendered at `/?id={id}`. Behavior:

- Fetches complete product data from `https://dummyjson.com/products/{id}` on load (guarantees all fields)
- Shows a spinner while loading
- Image gallery: clicking a thumbnail updates the main image with active border highlight
- RTL detection applied to the entire page
- Clicking the **category** navigates back to chat and auto-searches that category
- Clicking a **tag** navigates back to chat and auto-searches that tag
- Shows: brand, title, rating, category, description, price + discount, availability, shipping, warranty, tags

### `CategoryChips.tsx`

Renders the list of categories returned by `get_categories` as clickable pill buttons. Clicking a chip navigates to `/?category={slug}` which auto-triggers a category search in the chat.

### `DebugPanel.tsx`

Collapsible right-side panel showing the full tool call trace for every message. Each event row shows:

- `→ call` — tool name, arguments, timestamp
- `← result` — item count, clickable API URL, expandable JSON payload viewer
- Color-coded per tool type
- Collapses to a thin strip by clicking the terminal icon

---

## Technical Choices & Tradeoffs

**Server-side session store** — Conversation history is stored in a Python in-memory dict on the backend, keyed by a UUID session_id. The browser only sends `session_id + message` per request, not the full history. This reduces payload size and keeps conversation state off the client.

In production this would be replaced with a **centralized session store** such as:
- **Redis** — fast, TTL-based expiry, works across multiple server instances
- **DynamoDB / Firestore** — persistent sessions that survive server restarts
- **PostgreSQL** — if you need full conversation history for analytics or replay

The current in-memory dict is cleared on server restart and is not safe for multi-process deployments (e.g. multiple uvicorn workers would each have their own isolated dict).

**OpenAI function calling for intent detection** — The model decides which tool to call based on the user's message. No manual NLP, keyword parsing, or regex needed. Tool selection rules in the system prompt guide edge cases (e.g. always prefer `get_products_by_category` over `search_products` when a category name is mentioned).

**SSE streaming** — Server-Sent Events allow the backend to stream tool call events, product data, and text incrementally. The frontend renders product cards before the text response is complete.

**In-memory sort and filter** — `sort_products` and `filter_in_memory` never call DummyJSON. They operate on the last API result already stored in the session conversation. This means follow-up requests like "sort by rating" or "show only those above 4 stars" are instant and free. Multiple filter conditions in the same message are merged into one pass. Importantly, each filter/sort always operates on the **original API result**, not on a previously filtered list — so switching from "above 4" to "below 4" always works correctly.

**Conversation summary memory** — After every 10 user+assistant exchanges, the backend calls OpenAI once to summarize the conversation into 3-5 sentences, then replaces the full history with that summary + the last 2 clean exchanges. This keeps the context window small regardless of conversation length and reduces token cost per request. The summarization only keeps clean `user`/`assistant` messages in the tail — never assistant messages with pending tool calls — to avoid OpenAI rejecting requests with unmatched `tool_call_id` errors.

**Client-side price and rating filtering** — DummyJSON has no filter API. The backend fetches up to 100 results and filters locally by `min_price`, `max_price`, `min_rating`, and `max_rating`. This is fast enough for a 194-product catalog.

**Local tag/field filtering** — Same approach: fetch all products, filter in Python. Acceptable for this dataset size.

**ReactMarkdown only after streaming** — During streaming, text is rendered as a plain `<span>` to avoid expensive re-parsing on every token. ReactMarkdown is applied once when the stream is complete, eliminating flicker.

**Results capped at 8** — Keeps the UI clean and avoids overwhelming the user. The `get_more_products` tool allows pagination on demand.

---

## Why not MCP?

MCP (Model Context Protocol) is a standardized protocol for exposing tools to AI agents — think of it as a plugin system where tools live in a separate server process and any MCP-compatible agent can connect to them.

### Why we chose our approach

For a self-contained shopping copilot, MCP would be over-engineering. Our approach is simpler, faster to build, and easier to run locally with a single command.

MCP adds real value when:
- You want to **reuse tools across multiple agents or apps** — e.g. the same DummyJSON tools used by a voice assistant, a web app, and a mobile app simultaneously
- You're building a **platform** where third parties can plug in their own tool servers
- You have **multiple teams** owning different tool servers independently
- You need **dynamic tool discovery** — the orchestrator connects to whatever MCP servers are available at runtime

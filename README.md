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
│   │   7 tool functions → DummyJSON API calls        │  │
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
1. User types a message
2. Browser POSTs to /api/chat with conversation history
3. FastAPI calls OpenAI (gpt-5.4-mini) with tool definitions
4. OpenAI decides which tool to call based on user intent
5. Backend executes the tool (checks cache → calls DummyJSON if needed)
6. Tool result is added to conversation and OpenAI is called again
7. OpenAI generates a text response
8. Backend streams SSE events to the browser:
   - tool_call  → debug panel shows which tool was called + args
   - tool_result → debug panel shows result count + API URL + JSON payload
   - products   → chat renders product cards
   - categories → chat renders clickable category chips
   - text       → chat streams the AI text response
9. Stream ends with [DONE]
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
- Exposes `POST /api/chat` which returns a `StreamingResponse` (SSE)
- Runs the **agentic loop**: calls OpenAI → executes tool calls → loops until no more tool calls → streams final response
- Streams 5 SSE event types: `tool_call`, `tool_result`, `products`, `categories`, `text`
- The system prompt contains explicit tool selection rules to guide the model

### `tools.py`

All product data fetching logic. Responsibilities:

- Defines 7 tools exposed to the OpenAI model
- Implements a **TTL-based in-memory cache** (5 minutes) — repeated queries skip DummyJSON entirely
- All price filtering is done locally after fetching (DummyJSON has no price filter API)

#### Tool reference

| Tool                       | DummyJSON endpoint                  | When triggered                              | Notes                                                                  |
| -------------------------- | ----------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------- |
| `search_products`          | `/products/search?q=`               | Generic keyword search                      | Supports `min_price` / `max_price` filtering                           |
| `get_products_by_category` | `/products/category/{slug}`         | User mentions a category name               | Preferred over search when category is known. Supports price filtering |
| `get_categories`           | `/products/categories`              | User asks what's available                  | Returns list rendered as clickable chips                               |
| `search_by_tag`            | `/products` (all, filtered locally) | User mentions a tag                         | Fetches all 194 products, filters by tag match                         |
| `search_by_field`          | `/products` (all, filtered locally) | User mentions brand, SKU, availability etc. | Filters any product field by value                                     |
| `sort_products`            | `/products?sortBy=&order=`          | User asks for cheapest / highest rated      | Uses DummyJSON native sort params                                      |
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

- Full conversation state (`messages`)
- SSE stream parsing — routes each event type to the correct state update
- Debug events state passed to `DebugPanel`
- Auto-trigger on `?category=` or `?search=` URL params (used when navigating back from product detail)
- Header click resets the entire chat

### `Message.tsx`

Renders a single chat message. Handles:

- User messages: plain text bubble (right-aligned)
- Assistant messages: category chips + product grid + markdown text (left-aligned)
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

**Single process, single port** — FastAPI serves both the API and the pre-built React frontend. No reverse proxy needed, one command to run.

**OpenAI function calling for intent detection** — The model decides which tool to call based on the user's message. No manual NLP, keyword parsing, or regex needed. Tool selection rules in the system prompt guide edge cases (e.g. always prefer `get_products_by_category` over `search_products` when a category name is mentioned).

**SSE streaming** — Server-Sent Events allow the backend to stream tool call events, product data, and text incrementally. The frontend renders product cards before the text response is complete.

**Client-side price filtering** — DummyJSON has no price filter API. The backend fetches up to 100 results and filters locally. This is fast enough for a 194-product catalog.

**Local tag/field filtering** — Same approach: fetch all products, filter in Python. Acceptable for this dataset size.

**ReactMarkdown only after streaming** — During streaming, text is rendered as a plain `<span>` to avoid expensive re-parsing on every token. ReactMarkdown is applied once when the stream is complete, eliminating flicker.

**No conversation memory** — The full conversation history is sent with every request (stateless backend). Suitable for a local demo; would need a session store for production.

**Results capped at 8** — Keeps the UI clean and avoids overwhelming the user. The `get_more_products` tool allows pagination on demand.

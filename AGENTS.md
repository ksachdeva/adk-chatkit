# adk-chatkit

## 🎯 Purpose

This is a **Python library + example application** that bridges **OpenAI's [chatkit-js](https://github.com/openai/chatkit-js)** (a frontend chat UI library) with **Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/)** — enabling you to build ADK-powered AI agents that expose a chatkit-compatible API.

It uses and extends `openai/chatkit-python` by providing:
- `ADKStore` that wraps `BaseSessionService`
- A function (`stream_agent_response`) that translates ADK events into chatkit events
- Support for rendering **widgets** (rich UI components in chat)
- Support for **client tools** (triggering JavaScript functions in the browser)

---

## 📦 Core Library — `adk-chatkit`

Located in `adk-chatkit/src/adk_chatkit/`, the key public exports are:

| Symbol | File | Purpose |
|---|---|---|
| `ADKStore` | `_store.py` | Wraps ADK's `BaseSessionService` to implement chatkit's `Store` interface — handles threads, messages, widgets, and client tool calls |
| `stream_agent_response` | `_response.py` | Translates ADK streaming events into chatkit `ThreadStreamEvent`s |
| `ADKChatKitServer` | `_server.py` | Base server class for implementing chatkit-compatible agents |
| `ADKContext` / `ADKAgentContext` | `_context.py` | Context objects carrying app/user/thread info through the pipeline. `ADKAgentContext.client_tool_call` holds the single client tool call issued in one agent turn (chatkit supports at most one per turn) |
| `ChatkitRunConfig` | `_context.py` | Run config for ADK with SSE streaming mode |
| `stream_event` | `_context.py` | Low-level helper for emitting any `ThreadStreamEvent` from a tool |
| `stream_widget` | `_context.py` | Helper for emitting rich widget UI items into the chat thread |
| `issue_client_tool_call` | `_context.py` | Helper for triggering browser-side JavaScript tool executions |
| `serialize_widget_item` | `_widgets.py` | Serialization utility for widget state |
| `ClientToolCallState` | `_client_tool_call.py` | Tracks state of in-progress client tool calls |

---

## 🧩 Key Concepts

### Widgets
Agents can render rich UI components (e.g., a weather card) directly in the chat by calling `stream_widget()`. Widget state is persisted in ADK session state, keyed by the function call ID that produced the widget.

### Client Tools
Agents can trigger JavaScript functions in the browser (e.g., switching the UI theme) via `issue_client_tool_call()`. These run client-side and allow bidirectional agent ↔ browser interaction.

### Session ↔ Thread Mapping
ADK sessions map directly to chatkit threads. Session state is used to store widget data (`CHATKIT_WIDGET_STATE_KEY`) and client tool call metadata (`CHATKIT_CLIENT_TOOL_CALLS_KEY`), which allows them to be reconstructed when loading thread history.

### Hidden Messages
User messages prefixed with `[HIDDEN]` are filtered out from thread item history, allowing internal/system prompts to be injected without surfacing them in the chat UI.

---

## 🛠️ Example Application

A full monorepo example lives in `examples/`, consisting of a Python backend and a React frontend.

### Backend (`examples/backend/`)

Built with **FastAPI** + **Google ADK**. Uses **Dishka** for dependency injection.

**Agents available:**

| Agent | Description |
|---|---|
| `facts` | Fact recording, weather widgets, theme switching (client tool) |
| `airline` | Airline reservation management — change seat, add bags |
| `knowledge` | Answers questions from files/vector store with citations |
| `widgets` | Widget gallery demonstrating all supported widget types |
| `cat` | Cat Lounge — cozy themed conversational agent |
| `news` | News guide agent |
| `metro` | Metro map agent |

Run the backend:
```bash
uv run poe run-example-backend
# FastAPI dev server at http://localhost:8000
```

### Frontend (`examples/frontend/`)

Built with **Vite + React + TypeScript + Tailwind CSS**.

**Routes:**

| Route | Agent |
|---|---|
| `/customer-support` | Airline agent |
| `/guide` | Facts & Guide agent |
| `/federal` | Knowledge Assistant agent |
| `/widget-gallery` | Widget Gallery agent |
| `/cozy-cat` | Cat Lounge agent |
| `/news-guide` | News Guide agent |
| `/metro-map` | Metro Map agent |

Run the frontend:
```bash
uv run poe run-example-frontend
# Vite dev server at http://localhost:5173
```

---

## 🔧 Tooling & Configuration

| Tool | Purpose |
|---|---|
| `uv` | Python package manager and workspace manager |
| `poethepoet` (`poe.toml`) | Task runner for common dev commands |
| `ruff` | Python linting and formatting (target: Python 3.11+, line length 120) |
| `mypy` (strict mode) | Static type checking |
| `pytest` + `pytest-asyncio` | Async-capable testing |
| `pre-commit` | Git hooks for code quality |
| `Vite` + `npm` | Frontend dev server and bundler |

### Workspace Structure

```
adk-chatkit/                   ← repo root
├── adk-chatkit/               ← installable Python library (uv workspace member)
│   └── src/adk_chatkit/       ← core library source
├── examples/
│   ├── backend/               ← FastAPI backend (uv workspace member)
│   │   └── src/backend/
│   │       ├── agents/        ← per-agent implementations
│   │       └── api/           ← HTTP route handlers
│   └── frontend/              ← Vite/React frontend
│       └── src/
├── assets/                    ← screenshots and documentation images
├── pyproject.toml             ← root workspace config (ruff, mypy, poe)
├── poe.toml                   ← task definitions
└── uv.lock                    ← locked dependency graph
```

---

## 🚀 Quick Start

```bash
# 1. Open in VS Code devcontainer (sets up all dependencies automatically)

# 2. Configure environment
cp .env.example .env
# Fill in API keys and settings

# 3. Run the backend
uv run poe run-example-backend

# 4. Run the frontend (separate terminal)
uv run poe run-example-frontend
```

---

## 📌 Notes & TODOs

- **Attachments/artifacts** are not yet supported (`save_attachment`, `load_attachment`, `delete_attachment` all raise `NotImplementedError`)
- `delete_thread_item` is a no-op — ADK session events are append-only and individual events cannot be deleted

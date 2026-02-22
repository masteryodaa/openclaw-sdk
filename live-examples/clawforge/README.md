# ClawForge -- AI App Builder

An Emergent-style AI app builder platform powered by the [OpenClaw SDK](https://pypi.org/project/openclaw-sdk/).

Users describe what they want to build, and AI agents plan, build, and review the project autonomously.

## Architecture

```
Browser (Next.js :3000)  ->  FastAPI Backend (:8200)  ->  openclaw-sdk  ->  OpenClaw Gateway
```

- **Backend**: FastAPI with routers/controllers/helpers pattern
- **Frontend**: Next.js 14 + shadcn/ui (dark theme)
- **Database**: SQLite via aiosqlite (zero-config)
- **Streaming**: SSE for real-time chat and build events

## SDK Features Demonstrated

| Feature | Usage |
|---|---|
| `OpenClawClient.connect()` | Gateway lifecycle management |
| `Agent.execute()` / `execute_stream()` | Chat with streaming |
| `Pipeline` | Planner -> Builder -> Reviewer chain |
| `Supervisor` | Multi-agent delegation |
| `CostTracker` | Per-project cost tracking |
| `Templates` | Pre-built project starters |
| `Guardrails` | Input validation |
| `CallbackHandler` | Build audit trail |
| `GitHubConnector` | Export to GitHub |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenClaw running at `ws://127.0.0.1:18789/gateway`

### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
# -> http://127.0.0.1:8200
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# -> http://localhost:3000
```

### Usage

1. Open http://localhost:3000
2. Type a project description (e.g., "Build a todo app with FastAPI")
3. Click "Start Building" -- creates a project and opens the workspace
4. Chat with your AI agent in the left panel
5. Click "Build" to run the multi-agent pipeline
6. View generated files in the right panel
7. Check the Billing page for cost breakdown

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/projects` | List projects |
| POST | `/api/projects` | Create project |
| GET | `/api/projects/{id}` | Get project |
| PATCH | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project |
| POST | `/api/chat` | Send message (blocking) |
| POST | `/api/chat/stream` | Send message (SSE) |
| POST | `/api/build/stream` | Build project (SSE) |
| GET | `/api/files/{project_id}` | List files |
| GET | `/api/templates` | List templates |
| POST | `/api/templates/create` | Create from template |
| GET | `/api/billing/summary` | Billing summary |
| GET | `/api/billing/project/{id}` | Project costs |
| POST | `/api/export/github` | Export to GitHub |

## Project Structure

```
clawforge/
  backend/
    main.py                 # FastAPI entry point
    requirements.txt
    app/
      routers/              # Thin route definitions
      controllers/          # Business logic (SDK orchestration)
      helpers/              # Gateway, database, SSE utilities
      models/               # Pydantic request/response models
  frontend/
    app/                    # Next.js pages
      page.tsx              # Home (prompt-first landing)
      projects/             # Project list
      workspace/[id]/       # Two-panel workspace
      templates/            # Template gallery
      billing/              # Cost dashboard
    components/             # React components
    lib/                    # API client, types, SSE
```
